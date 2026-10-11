"""One four-input closing diagnostic. Not installed in the product."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import native_eval as ev
import receipt_eval as receipt
import focused_eval as focused
from extended_eval import inspect_history
from seven_eval import QUALIFICATION
from product_tools.contracts import strict_json

LIMITS = {"native_cap": 4, "parallel": 2, "seconds": 420, "automatic_retry": False}
DATA = "data/business/lg-research-v3"
SPECS = [
    ("preference", "F01", "B502S33", 1,
     "B502S33의 냉동실 정리 안내를 만들려고 해. 리뷰의 ‘현재 잘 사용하고 있어요’와 ‘냉장고는 넉넉한게 좋은듯해요’를 합쳐서 ‘이 모델 냉동실이 넉넉해서 만족한다’고 써도 될까? 냉동실이 좁지만 두 명이 쓰기에는 괜찮다는 의견과 함께 원문에 맞게 해석하고, 새 부품 없이 할 수 있는 안내를 하나만 제안해줘."),
    ("expectation", "F02", "S836GBB122", 1,
     "S836GBB122 고객이 청소 때문에 불편을 겪고 있다는 보고서를 쓰려 해. 도어 청소가 쉬울 것 같다는 후기만으로 실제 불편과 개선 효과를 판단해도 될까? 높이360mm 용기가 들어가는 선반 간격과 청소시간20% 절감을 확정해 달라는 요청도 함께 검토해줘. 확인된 자료로 가능한 결론과 보류해야 할 결론을 나누고, 근거가 없으면 제안 수를 채우지 않아도 돼."),
    ("product-1", "F03", "T876MQQ012", 2,
     "식품이 있는 중·하단과 구석으로 빛이 잘 안 내려온다는 T876MQQ012 의견을 보고, 장보기 전 식재료 확인 절차를 기획해줘. 이번에는 식품 위치와 기존 선반 사용 방식을 바꿔도 되지만 새 부품은 추가하지 않을게. 개선안은 두 개 이내로 하고, 설명서의 선반 조작·내부 청소 절차와 실제 후기의 적용 범위를 구분해 각각 해당 원문 위치를 남겨줘."),
    ("followup", "F04", "T876MQQ012", 1,
     "방금 T876MQQ012 검토를 이어갈게. 이제 식품을 다른 칸으로 옮기거나 선반을 접거나 높이를 바꾸지 않을 거야. 추가 부품 금지는 유지하고 한 가지 안만 남겨줘. 이 조건에서 실제로 못 하는 일도 밝히고, 앞선 제안·검토·출처 기록을 보존해줘. 선반 조작과 내부 청소를 인용했다면 서로 다른 절차의 문서 위치를 다시 확인해줘."),
]


def select_jobs(plan, names, started):
    if plan["limits"] != LIMITS or len(plan["jobs"]) != 4:
        raise ValueError("Closing diagnostic must contain exactly four frozen inputs")
    if not 1 <= len(names) <= 2 or len(names) != len(set(names)):
        raise ValueError("Select one or two distinct inputs")
    jobs = {j["name"]: j for j in plan["jobs"]}
    if any(n not in jobs or n in started for n in names) or len(started) + len(names) > 4:
        raise ValueError("Unknown/already attempted input; failures consume slots")
    if "followup" in names and len(names) != 1:
        raise ValueError("Run followup alone after a delivered parent")
    return [jobs[n] for n in names]


def private_report(report):
    report = report.resolve()
    if not report.is_relative_to((ev.ROOT / ".harness").resolve()):
        raise ValueError("Records must remain in ignored .harness")
    return report


def prepare(report, specs=None, data_path=DATA):
    report = private_report(report)
    report.mkdir(parents=True, exist_ok=False)
    source = ev.freeze(ev.ROOT, report / "source")
    runner = {p.name: ev.sha(p) for p in Path(__file__).parent.glob("*.py")}
    shutil.copytree(Path(__file__).parent, report / "runner", ignore=shutil.ignore_patterns("__pycache__"))
    base = Path(tempfile.mkdtemp(prefix="lg-closure-"))
    jobs = []
    for name, identifier, model, cap, question in (SPECS if specs is None else specs):
        workspace = base / ("product-1" if name == "followup" else name)
        if name != "followup":
            ev.load_installer(report / "source").install(workspace)
            sync = subprocess.run(["uv", "sync", "--locked"], cwd=workspace, capture_output=True, timeout=120)
            if sync.returncode:
                raise RuntimeError("Locked workspace sync failed")
        case = {"id": identifier, "model_id": model, "turns": [question],
                "constraints": {"max_concepts": cap, "hardware_allowed": False, "exclude_pains": []}}
        data = ev.Dataset(workspace / data_path)
        prompt = receipt.prompt(case, "product", data_path) + QUALIFICATION
        if name == "followup":
            prompt += "\n실제 추가 질문이다. 같은 native 대화·업무 session_id와 prior_turn_id로 이어가고 이전 후보를 변경·삭제하지 않는다."
        jobs.append({"name": name, "case": case, "arm": "product", "workspace": str(workspace),
                     "data_path": data_path, "data_fingerprint": data.fingerprint, "prompt": prompt,
                     "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "fault": None})
    ev.dump(report / "prepared.json", {"jobs": jobs, "source": source, "runner": runner, "limits": LIMITS,
        "evaluation_kind": "newly authored nonblind diagnostic; not independent held-out/general accuracy",
        "full_cost": None, "human_time": None})
    ev.dump(report / "seal.json", {"prepared_sha256": ev.sha(report / "prepared.json")})


def run(report, names):
    report = private_report(report)
    lock = report / "running.lock"
    with lock.open("x") as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    try:
        if ev.sha(report / "prepared.json") != strict_json((report / "seal.json").read_text())["prepared_sha256"]:
            raise ValueError("Frozen plan changed")
        plan = strict_json((report / "prepared.json").read_text(encoding="utf-8"))
        focused.verify_source(report, plan)
        for name, expected in plan["runner"].items():
            if ev.sha(Path(__file__).parent / name) != expected or ev.sha(report / "runner" / name) != expected:
                raise ValueError("Runner drift: " + name)
        started = {p.name.removesuffix("-started.json") for p in report.glob("*-started.json")}
        jobs = select_jobs(plan, names, started)
        for job in jobs:
            if job["name"] == "followup":
                parent = strict_json((report / "product-1/result.json").read_text(encoding="utf-8"))
                if parent["acceptance"] != "contract_and_delivery_passed":
                    ev.dump(report / "followup-not-run.json", {"status": "not_run", "reason": "Parent not delivered; no replacement input"})
                    return []
                job["native_id"] = parent["execution"]["native_id"]
                job["previous_usage"] = parent["execution"]["rollout"]["cumulative_usage"]
                job["before_history"] = inspect_history(Path(job["workspace"]))
            with (report / (job["name"] + "-started.json")).open("x", encoding="utf-8") as stream:
                json.dump({"at": datetime.now(timezone.utc).isoformat(), "limits": LIMITS, "job": job,
                           "prepared_sha256": ev.sha(report / "prepared.json"), "runner_sha256": ev.sha(Path(__file__))}, stream, ensure_ascii=False)
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda j: focused.one(report, j), jobs))
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "run"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--jobs", nargs="+", default=[])
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(args.report)
    else:
        run(args.report, args.jobs)
