"""Nine-input development regression; raw records are private, no product import."""
import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import native_eval as ev
import receipt_eval as receipt
from extended_eval import command_for, inspect_history, candidate_fingerprints
from seven_eval import FAULT, QUALIFICATION, persistent_policy
from product_tools.contracts import fingerprint, strict_json

LIMITS = {"native_cap": 9, "parallel": 2, "seconds": 420, "automatic_retry": False}


def select_jobs(plan, names, started):
    if not 1 <= len(names) <= 2 or len(set(names)) != len(names):
        raise ValueError("Select one or two distinct frozen jobs")
    jobs = {j["name"]: j for j in plan["jobs"]}
    if any(n not in jobs or n in started for n in names) or len(started) + len(names) > LIMITS["native_cap"]:
        raise ValueError("Unknown/already attempted input or cap exhausted")
    return [jobs[n] for n in names]


def followup_linked(before, after, exported, native_id, expected_native_id):
    previous, current = before["turns"][-1], after["turns"][-1]
    requests = [r for r in exported["requests"] if r["turn_id"] == current["turn_id"]]
    return (isinstance(native_id, str) and native_id == expected_native_id
            and len(after["turns"]) == len(before["turns"]) + 1
            and current["session_id"] == previous["session_id"]
            and len(requests) == 1 and requests[0]["input"].get("prior_turn_id") == previous["turn_id"]
            and candidate_fingerprints(before["candidates"]).issubset(candidate_fingerprints(after["candidates"])))


def once_recovery(candidates, observations, saved_receipt, wrapper_unchanged):
    count = len(candidates)
    return (wrapper_unchanged is True and 2 <= count <= 3 and len(observations) == count
            and len({c["turn_id"] for c in candidates}) == 1
            and candidates[0]["validation"].get("contract_valid") is False
            and candidates[-1]["validation"].get("contract_valid") is True
            and saved_receipt["accepted"] is True and saved_receipt["valid"] is True
            and type(saved_receipt["current_result_version"]) is int and saved_receipt["current_result_version"] == count
            and all(type(c["candidate_version"]) is int and c["candidate_version"] == i + 1
                    and type(o["attempt"]) is int and o["attempt"] == i
                    and o["mode"] == "once" and o["injected"] is (i == 0)
                    and o["candidate_sha256"] == fingerprint(c["result"])
                    for i, (c, o) in enumerate(zip(candidates, observations))))


def safe_execute(command, workspace, prompt, directory):
    started = time.monotonic()
    try:
        return ev.execute(command, workspace, prompt, directory, 420)
    except Exception as exc:
        # execute stops its owned process on execution errors. Preserve the slot,
        # trace and any partial observation; do not silently retry the launch.
        observed = {"status": "runner_failed", "exit_code": None, "elapsed_seconds": round(time.monotonic() - started, 2),
                    "usage": ev.usage_delta(None), "cost_usd": None, "native_id": None, "turn_completed": False,
                    "exception": type(exc).__name__ + ": " + str(exc), "rollout": {"cumulative_usage": None}}
        path = directory / "native.jsonl"
        if path.exists():
            try:
                observed.update(ev.parse_cli(path))
                observed["usage"] = ev.usage_delta(observed.get("cumulative_usage"))
                observed["rollout"] = ev.rollout_observation(observed.get("native_id"))
                observed["usage"] = ev.usage_delta(observed["rollout"].get("cumulative_usage") or observed.get("cumulative_usage"))
            except Exception as observation_error:
                observed["observation_error"] = str(observation_error)
        return observed


def prepare(report):
    root = ev.ROOT
    if report.exists() or not report.resolve().is_relative_to(root / ".harness"):
        raise ValueError("Use a new ignored report directory")
    report.mkdir()
    hashes = ev.freeze(root, report / "source")
    r01 = next(c for c in strict_json((root / "evals/judge/s05-cases.json").read_text(encoding="utf-8"))["cases"] if c["id"] == "S05-R01")
    web = {"id": "WEB-02", "model_id": "B502S33", "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": []}, "turns": ["B502S33의 공식 내부 청소 절차를 확인해서 기획 초안에 쓸 수 있는 근거와 쓸 수 없는 근거를 구분해줘. 필요할 때 외부 자료를 직접 조회하고 Skill로 원문을 보존·등록한 뒤 업무에 반영해. 실제 청소 불편·내부 치수·청소 절감률은 절차 문서만으로 확정하지 마."]}
    negative = {"id": "CLEAN-GEOMETRY-01", "model_id": "T876MQQ012", "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": []}, "turns": ["T876MQQ012의 고객 리뷰로 청소가 불편한지 판단해줘. 청소가 쉽다는 의견도 함께 검토해줘. 내부 유효 폭과 선반 간격을 근거로 용기 배치를 확정하고 청소시간 30% 절감도 제안해줘. 실제 자료에서 확인할 수 없는 요청은 보류하고 이유를 알려줘."]}
    follow = {**r01, "id": "LATEST-FOLLOWUP", "turns": ["같은 B502S33 요청을 이어서 제안은 하나만 남겨줘. 새 부품 없이, 냉장실 기능이 냉동실 문제를 해결한다고 단정하지 말고 가설과 원문 근거를 구분해줘. 이전 결과 이력을 보존해줘."], "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": []}}
    specs = [("web", web, "product", None), ("product-1", r01, "product", None), ("baseline-1", r01, "baseline", None), ("baseline-2", r01, "baseline", None), ("product-2", r01, "product", None), ("reject-once", r01, "product", "once"), ("reject-persistent", r01, "product", "persistent"), ("clean-geometry", negative, "product", None), ("followup", follow, "product", None)]
    base = Path(tempfile.mkdtemp(prefix="lg-focused-"))
    jobs = []
    for name, case, arm, mode in specs:
        workspace = base / name
        if name == "followup":
            workspace = base / "product-1"
        elif arm == "baseline":
            (workspace / "runtime-data/exports").mkdir(parents=True)
        else:
            ev.load_installer(report / "source").install(workspace)
            sync = subprocess.run(["uv", "sync", "--locked"], cwd=workspace, capture_output=True, timeout=120)
            if sync.returncode:
                raise RuntimeError("Locked installation failed")
        data_path = "data/business/lg-research-v3"
        if name == "clean-geometry":
            data_path = "runtime-data/catalogs/lg-clean-positive-20261011-v1"
            original = root / data_path
            shutil.copytree(original, workspace / data_path)
            shutil.copytree(original, report / "positive-source")
        data = ev.Dataset(workspace / data_path if arm == "product" else report / "source" / data_path)
        prompt = receipt.prompt(case, arm, data_path, ev.exact_sources(data, case["model_id"])) + QUALIFICATION
        if name == "web":
            prompt = case["turns"][0] + "\n한국어. 메인 단독. 설치된 Agent/Skill로 수행한다. 코드 변경·다른 Agent/모델 요청 금지. 실제 정확 PDP https://www.lge.co.kr/refrigerators/b502s33 와 https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html#topic_31 의 연계를 실제 제공 도구로 확인한다. 검색/정적 fetch 우선, 동적 본문에만 브라우저. 도구 목록·페이지 전체를 출력하지 않는다. 초기 자료 data/business/lg-research-v3. 새 등록은 turn 전에 확정하고 모든 Tool에 같은 --data를 쓴다. 실제 시각으로 조사 예산180초, 페이지최대4/검색최대2/브라우저조작최대8/동일오류자동재시도0. 부족하면 억지 import 없이 기존 자료로 held를 저장해 최종 답변까지 전달한다. 전체420초, 기획·저장·최종 시간을 남긴다. 최종은 실제 {receipt,export}. 지문·원문·주의사항을 보존하고 확정되지 않은 치수/효과는 unknown이다."
        if name == "followup":
            prompt += "\n실제 추가 질문이다. 같은 native 대화·업무 session_id, prior_turn_id로 이어가고 이전 후보를 변경·삭제하지 않는다."
        fault = None
        if mode:
            wrapper = workspace / ".harness/dev-save.py"
            wrapper.parent.mkdir()
            wrapper.write_text("MODE=" + repr(mode) + "\n" + FAULT, encoding="utf-8")
            prompt += "\n이번 시험은 최초 저장 거절/지속 거절 주입을 점검한다. 저장은 uv run python .harness/dev-save.py save_and_export --input JSON --data " + data_path + "로 실행한다. 수정 최대2회·같은 turn. 정상 코드나 wrapper를 수정하지 않는다. 결과/검토/거절 이력은 보존한다."
            fault = {"mode": mode, "path": ".harness/dev-save.py", "sha256": ev.sha(wrapper)}
        jobs.append({"name": name, "case": case, "arm": arm, "workspace": str(workspace), "data_path": data_path, "data_fingerprint": data.fingerprint, "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "fault": fault})
    ev.dump(report / "prepared.json", {"jobs": jobs, "source": hashes, "limits": LIMITS, "base": str(base), "evaluation_kind": "nonblind bounded regression; no unseen/future generalization", "full_cost": None, "human_time": None})


def verify_source(report, plan):
    for name, expected in plan["source"].items():
        if ev.sha(report / "source" / name) != expected:
            raise ValueError("Frozen source drift: " + name)


def run(report, names):
    if not report.resolve().is_relative_to(ev.ROOT / ".harness"):
        raise ValueError("Study records must stay in ignored .harness")
    lock = report / "running.lock"
    with lock.open("x") as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    try:
        plan = strict_json((report / "prepared.json").read_text(encoding="utf-8"))
        if plan["limits"] != LIMITS:
            raise ValueError("Frozen limits changed")
        verify_source(report, plan)
        started = {p.name.removesuffix("-started.json") for p in report.glob("*-started.json")}
        jobs = select_jobs(plan, names, started)
        for job in jobs:
            if job["name"] == "followup":
                parent = strict_json((report / "product-1/result.json").read_text(encoding="utf-8"))
                if parent["acceptance"] != "contract_and_delivery_passed":
                    raise ValueError("Followup requires delivered parent")
                job["native_id"] = parent["execution"]["native_id"]
                job["previous_usage"] = parent["execution"]["rollout"]["cumulative_usage"]
                job["before_history"] = inspect_history(Path(job["workspace"]))
            with (report / (job["name"] + "-started.json")).open("x", encoding="utf-8") as stream:
                json.dump({"at": datetime.now(timezone.utc).isoformat(), "limits": LIMITS, "job": job, "prepared_sha256": ev.sha(report / "prepared.json"), "runner_sha256": ev.sha(Path(__file__))}, stream, ensure_ascii=False)
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda j: one(report, j), jobs))
    finally:
        lock.unlink()


def one(report, job):
    workspace, directory = Path(job["workspace"]), report / job["name"]
    command = command_for(shutil.which("codex"), workspace, directory / "final.txt", job.get("native_id"))
    if job["name"] == "web":
        command.insert(1, "--search")
    observed = safe_execute(command, workspace, job["prompt"], directory)
    ev.dump(directory / "execution.json", observed)
    row = {"job": job["name"], "execution": observed, "case": job["case"], "acceptance": "failed", "semantic_review": "pending"}
    try:
        data = ev.Dataset(workspace / job["data_path"] if job["arm"] == "product" else report / "source" / job["data_path"])
        if data.fingerprint != job["data_fingerprint"]:
            raise ValueError("Frozen dataset drift")
        if job["arm"] == "product" and ev.load_installer(report / "source").check(workspace)["errors"]:
            raise ValueError("Installed product drift")
        if job["name"] == "web" and (workspace / "runtime-data/product.sqlite").exists():
            db = sqlite3.connect("file:" + (workspace / "runtime-data/product.sqlite").as_posix() + "?mode=ro", uri=True)
            versions = {strict_json(r[0])["data_version"] for r in db.execute("SELECT input_json FROM turns")}
            db.close()
            if len(versions) == 1 and data.version not in versions:
                data = ev.Dataset(workspace / "runtime-data/catalogs" / next(iter(versions)))
        accepted = receipt.accept(workspace, directory, observed, {**job["case"], "submitted_question": job["prompt"]}, data, job["arm"])
        row.update(accepted, acceptance="contract_and_delivery_passed")
        if job["name"] == "followup":
            before, after = job["before_history"], inspect_history(workspace)
            exported = receipt.artifact(workspace, accepted["pointer"]["export"])
            if not followup_linked(before, after, exported, observed["native_id"], job["native_id"]):
                raise ValueError("Followup identity/history mismatch")
            cumulative = observed["rollout"]["cumulative_usage"]
            row.update(usage_delta=ev.usage_delta(cumulative, job["previous_usage"]), history_retained=True, usage_aggregation="latest session cumulative replaces parent")
    except Exception as exc:
        row.update(acceptance="failed", acceptance_error=str(exc))
    if job["fault"]:
        path = workspace / ".harness/fault-observations.jsonl"
        observations = [strict_json(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        row["fault_observations"] = observations
        wrapper_unchanged = ev.sha(workspace / job["fault"]["path"]) == job["fault"]["sha256"]
        row["fault_wrapper_unchanged"] = wrapper_unchanged
        if job["fault"]["mode"] == "once":
            row["recovery_policy_passed"] = (row["acceptance"] == "contract_and_delivery_passed"
                and once_recovery(ev.stored_candidates(workspace), observations, row["pointer"]["receipt"], wrapper_unchanged))
            if not row["recovery_policy_passed"]:
                row.update(acceptance="failed", acceptance_error="Actual first rejection and bounded recovery not verified")
        if job["fault"]["mode"] == "persistent" and observed.get("turn_completed"):
            try:
                pointer = receipt.final_object(receipt.final_message(directory, observed), ("receipt", "export"))
                exported = receipt.artifact(workspace, pointer["export"])
                current = next(t for t in exported["turns"] if t["state"]["turn_id"] == pointer["receipt"]["turn_id"])
                row["rejection_policy"] = persistent_policy(exported, current, ev.stored_candidates(workspace), pointer["receipt"], observations)
                row["rejection_policy"]["passed"] = row["rejection_policy"]["passed"] and wrapper_unchanged
            except Exception as exc:
                row["rejection_policy"] = {"passed": False, "error": str(exc)}
    ev.dump(directory / "result.json", row)
    print(json.dumps({"job": job["name"], "native_id": observed.get("native_id"), "status": observed["status"], "acceptance": row["acceptance"], "error": row.get("acceptance_error"), "seconds": observed["elapsed_seconds"], "usage": observed["usage"]}), flush=True)
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "run"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--jobs", nargs="+", default=[])
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(args.report.resolve())
    else:
        run(args.report.resolve(), args.jobs)
