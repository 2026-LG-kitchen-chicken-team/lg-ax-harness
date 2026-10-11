"""Separate ten generic-product inputs; no edits or re-scoring of frozen fifty.

Uses the same bounded native transport and evidence helpers. Receipt verification
is explicit here because the earlier verifier intentionally accepts one model.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import native_eval as ev
import receipt_eval as receipt
from receipt_eval import final_message, final_object, artifact
from regression_eval import accept_clarification, execute_preserving, provider_denial, parent_identity, session_usage, build_prompt as base_prompt
from focused_eval import followup_linked, followup_usage
from extended_eval import command_for, inspect_history
from product_tools.contracts import fingerprint, strict_json
from product_tools.planning import review_product_result

LIMITS = {"native_cap": 10, "parallel": 2, "seconds": 420, "automatic_retry": False}
RUN_SECONDS = 4500
CLEANUP_SECONDS = 30


def build_prompt(case, data_path):
    return base_prompt(case, data_path).replace("모델 미선택·미등록으로 turn이 없으면", "제품 범위 미확정·보유 모델 미확인으로 turn이 없으면")


def expected_scopes(data, case):
    if not case["product_family"]:
        return []
    models = [m for m in data.models if m["product_family"] == case["product_family"] and
              (case["model_id"] is None or m["model_id"] == case["model_id"])]
    if not models or len(models) > 5 or len({m["model_id"] for m in models}) != len(models):
        raise ValueError("Frozen family catalog selection is empty, excessive or ambiguous")
    return [{k: m[k] for k in ("model_id", "model_version", "document_version")} for m in models]


def validate_cases(corpus):
    if len(corpus["cases"]) != 10 or corpus["limits"] != LIMITS:
        raise ValueError("Exactly ten separate inputs and fixed limits required")
    chains, seen = {}, set()
    for index, case in enumerate(corpus["cases"], 1):
        if case["id"] != f"G10-{index:02}" or not case["question"].strip():
            raise ValueError("Ordered unique original inputs required")
        chain = chains.setdefault(case["chain_id"], [])
        if case["parent_id"] != (chain[-1]["id"] if chain else None):
            raise ValueError("Actual immediate preceding parent required")
        if case["synthetic_fault_injection"] is not False:
            raise ValueError("No fault injection in this suite")
        if (case["product_family"] is None) != (case["expected_terminal_states"] == ["needs_input"]):
            raise ValueError("Separate owned-unknown/ambiguous clarification from catalog planning")
        if case["product_family"] and case["scope_mode"] != ("exact_model" if case["model_id"] else "family_catalog"):
            raise ValueError("Invalid expected scope mode")
        seen.add(case["id"]); chain.append(case)
    if len(chains) != 8:
        raise ValueError("Ten inputs in eight frozen conversations required")
    return chains

def accept_family(workspace, directory, observed, case, data, arm):
    """Verify delivered pointer against raw artifact AND latest live stored row."""
    text = final_message(directory, observed)
    return accept_family_text(workspace, text, case, data, arm)


def accept_family_text(workspace, text, case, data, arm):
    """Artifact audit only; caller must independently prove native final delivery."""
    if arm == "baseline":
        pointer = final_object(text, ("artifact",))
        answer = artifact(workspace, pointer["artifact"])
        if set(answer) != {"result", "assessment"}:
            raise ValueError("Baseline artifact schema mismatch")
        validation = ev.validate_answer(data, case, answer)
        if not validation.get("contract_valid") or not validation.get("can_finalize_reported_result"):
            raise ValueError("Baseline review not finalizable")
        return {"answer":answer,"summary":text,"validation":validation,"stored_match":None}
    pointer = final_object(text, ("receipt", "export"))
    receipt = pointer["receipt"]
    if any(type(receipt.get(k)) is not int or not 1 <= receipt[k] <= 3 for k in ("candidate_result_version", "current_result_version")):
        raise ValueError("Receipt versions must be integer candidate numbers, not booleans")
    if receipt["accepted"] is not True or receipt["valid"] is not True or receipt["candidate_result_version"] != receipt["current_result_version"]:
        raise ValueError("Rejected/stale candidate receipt")
    export = artifact(workspace, pointer["export"])
    if export["session_id"] != receipt["session_id"]:
        raise ValueError("Other session export")
    turns = [t for t in export["turns"] if t["state"]["turn_id"] == receipt["turn_id"]]
    if len(turns) != 1:
        raise ValueError("Missing/other turn export")
    state = turns[0]["state"]
    candidates = turns[0]["candidates"]
    latest = candidates[-1] if candidates else None
    if (not latest or type(state["result_version"]) is not int or type(latest["result_version"]) is not int or state["valid"] is not True or state["status"] != receipt["status"] or
            state["result_version"] != receipt["current_result_version"] or latest["result_version"] != state["result_version"] or
            latest["result_key"] != receipt["result_key"] or fingerprint(state["latest_result"]) != fingerprint(latest["result"])):
        raise ValueError("Receipt is not latest valid exported candidate")
    validation = latest["validation"]
    if (validation.get("contract_valid") is not True or validation.get("review_required") is not True or
            validation.get("review", {}).get("can_finalize_reported_result") is not True or
            fingerprint(latest["result"]) != receipt["result_sha256"] or
            fingerprint(validation.get("assessment")) != receipt["assessment_sha256"]):
        raise ValueError("Persisted review/hash mismatch")
    live = [r for r in ev.stored_candidates(workspace) if r["session_id"] == receipt["session_id"] and r["turn_id"] == receipt["turn_id"]]
    if (not live or live[-1]["candidate_version"] != receipt["current_result_version"] or live[-1]["turn_result_version"] != receipt["current_result_version"] or
            live[-1]["status"] != receipt["status"] or live[-1]["result_key"] != receipt["result_key"] or fingerprint(live[-1]["result"]) != fingerprint(latest["result"]) or fingerprint(live[-1]["validation"]) != fingerprint(validation)):
        raise ValueError("Live database differs from exported candidate")
    connection = ev.sqlite3.connect("file:" + (workspace / "runtime-data/product.sqlite").as_posix() + "?mode=ro",uri=True)
    try:
        current = connection.execute("SELECT valid,input_json,dataset_hash,code_hash,context_hash FROM turns WHERE session_id=? AND turn_id=?",(receipt["session_id"],receipt["turn_id"])).fetchone()
    finally: connection.close()
    code_dir = workspace / "product-tools/product_tools"
    files = sorted(code_dir.glob("*.py"))
    code_hash = hashlib.sha256(b"".join(p.name.encode() + b"\0" + p.read_bytes() for p in files)).hexdigest()
    if (not current or current[0] != 1 or fingerprint(strict_json(current[1])) != fingerprint(state["input"]) or current[2] != data.fingerprint or
            not files or current[3] != code_hash or current[4] != state["context_fingerprint"]):
        raise ValueError("Live context invalidated or dependency changed")
    scopes = state["input"]["model_scope"]
    expected_questions = {case["turns"][0]}
    if case.get("submitted_question"): expected_questions.add(case["submitted_question"])
    if (state["input"]["question"] not in expected_questions or scopes != expected_scopes(data, case) or state["input"]["product_family"] != case["product_family"] or state["input"].get("scope_mode") != case["scope_mode"] or state["input"]["constraints"] != case["constraints"]):
        raise ValueError("Question/model/constraints mismatch")
    if state["input"]["data_version"] != data.version:
        raise ValueError("Dataset version mismatch")
    answer = {"result":latest["result"],"assessment":validation["assessment"]}
    check = review_product_result(data, {"input": state["input"], **answer})
    if not check.get("contract_valid") or not check.get("can_finalize_reported_result"):
        raise ValueError("Independent contract recheck failed")
    return {"answer":answer,"summary":text,"validation":check,"stored_match":True,"pointer":pointer}


def prepare(report, cases_file):
    report = report.resolve()
    if report.exists() or not report.is_relative_to((ev.ROOT / ".harness").resolve()):
        raise ValueError("New private report below .harness required")
    corpus = strict_json(cases_file.read_text(encoding="utf-8"))
    chains = validate_cases(corpus)
    report.mkdir(parents=True)
    shutil.copyfile(cases_file, report / "cases.json")
    hashes = ev.freeze(ev.ROOT, report / "source")
    runners = {p.name: ev.sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    shutil.copytree(Path(__file__).parent, report / "runner", ignore=shutil.ignore_patterns("__pycache__"))
    data_path = corpus["data_path"]
    data = ev.Dataset(report / "source" / data_path)
    base = Path(tempfile.mkdtemp(prefix="lg-family10-")).resolve()
    jobs = []
    for chain_id, cases in chains.items():
        workspace = base / chain_id
        ev.load_installer(report / "source").install(workspace, root=report / "source")
        sync = subprocess.run(["uv", "sync", "--locked"], cwd=workspace, capture_output=True, timeout=120)
        if sync.returncode:
            raise RuntimeError("Locked workspace preparation failed: " + sync.stderr.decode(errors="replace")[-500:])
        for case in cases:
            prompt = build_prompt(case, data_path)
            jobs.append({"name": case["id"], "case": case, "workspace": str(workspace),
                         "data_path": data_path, "data_fingerprint": data.fingerprint,
                         "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    jobs.sort(key=lambda j: j["name"])
    ev.dump(report / "prepared.json", {"jobs": jobs, "source": hashes, "runner": runners,
        "cases_sha256": ev.sha(report / "cases.json"), "limits": LIMITS, "run_seconds": RUN_SECONDS,
        "kind": corpus["kind"], "official_questions": False, "independent_holdout": False,
        "billing": None, "human_time": None, "automatic_retry": False})
    (report / "prepared.sha256").write_text(ev.sha(report / "prepared.json"), encoding="ascii")
    return {"inputs": len(jobs), "conversations": len(chains), "report": str(report)}


def verify_plan(report):
    if ev.sha(report / "prepared.json") != (report / "prepared.sha256").read_text(encoding="ascii"):
        raise ValueError("Prepared plan seal changed")
    plan = strict_json((report / "prepared.json").read_text(encoding="utf-8"))
    corpus = strict_json((report / "cases.json").read_text(encoding="utf-8"))
    validate_cases(corpus)
    if plan["limits"] != LIMITS or plan["run_seconds"] != RUN_SECONDS or len(plan["jobs"]) != 10:
        raise ValueError("Prepared budget changed")
    if ev.sha(report / "cases.json") != plan["cases_sha256"]:
        raise ValueError("Frozen cases changed")
    if [job["case"] for job in plan["jobs"]] != corpus["cases"]:
        raise ValueError("Prepared jobs differ from the ten frozen cases")
    for job in plan["jobs"]:
        expected = build_prompt(job["case"], corpus["data_path"])
        if (job["name"] != job["case"]["id"] or job["data_path"] != corpus["data_path"]
            or job["prompt"] != expected or job["prompt_sha256"] != hashlib.sha256(expected.encode()).hexdigest()):
            raise ValueError("Prepared prompt/input differs from frozen protocol")
    for name, digest in plan["source"].items():
        if ev.sha(report / "source" / name) != digest:
            raise ValueError("Frozen product changed: " + name)
    for name, digest in plan["runner"].items():
        if ev.sha(report / "runner" / name) != digest or ev.sha(Path(__file__).parent / name) != digest:
            raise ValueError("Frozen/current runner changed: " + name)
    return plan


def run(report):
    plan = verify_plan(report)
    if any(p.parent != report for p in (ev.ROOT / ".harness").glob("*/running.lock")):
        raise ValueError("Another native regression is running; wait for its completion")
    lock = report / "running.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    try:
        if (report / "started.json").exists():
            raise ValueError("This frozen run was already attempted; no replacement/rerun")
        codex = shutil.which("codex")
        if not codex or (os.name == "nt" and Path(codex).suffix.lower() != ".exe"):
            raise RuntimeError("Native Codex executable required")
        version = subprocess.run([codex, "--version"], capture_output=True, timeout=15).stdout.decode().strip()
        ev.dump(report / "started.json", {"at": datetime.now(timezone.utc).isoformat(), "cli": version,
            "prepared_sha256": ev.sha(report / "prepared.json"), "limits": LIMITS, "run_seconds": RUN_SECONDS})
        deadline, halt = time.monotonic() + RUN_SECONDS, threading.Event()
        chains = {}
        for job in plan["jobs"]:
            chains.setdefault(job["case"]["chain_id"], []).append(job)

        def chain(jobs):
            rows, previous = [], None
            for job in jobs:
                directory, workspace = report / job["name"], Path(job["workspace"])
                row = {"job": job["name"], "case": job["case"], "acceptance": "not_run", "semantic_review": "pending"}
                if halt.is_set() or time.monotonic() >= deadline or (job["case"]["parent_id"] and (not previous or previous["acceptance"] != "contract_and_delivery_passed")):
                    directory.mkdir()
                    row.update(semantic_review="not_run", reason="provider_denial_or_run_deadline" if halt.is_set() or time.monotonic() >= deadline else "parent_delivery_or_contract_failed")
                    ev.dump(directory / "result.json", row)
                    rows.append(row)
                    previous = row
                    continue
                try:
                    native_id = parent_identity(job["case"], previous)
                except ValueError as exc:
                    directory.mkdir()
                    row.update(semantic_review="not_run", reason="parent_native_id_unavailable", observation_error=str(exc))
                    ev.dump(directory / "result.json", row)
                    rows.append(row)
                    previous = row
                    continue
                try:
                    before = inspect_history(workspace) if native_id else None
                except Exception as exc:
                    directory.mkdir()
                    row.update(semantic_review="not_run", reason="followup_history_unavailable", observation_error=str(exc))
                    ev.dump(directory / "result.json", row)
                    rows.append(row)
                    previous = row
                    continue
                previous_usage = None
                if native_id:
                    try:
                        previous_usage = ev.rollout_observation(native_id).get("cumulative_usage")
                    except Exception as exc:
                        row["previous_usage_error"] = str(exc)
                remaining = int(deadline - time.monotonic()) - CLEANUP_SECONDS
                if halt.is_set() or remaining <= 0:
                    directory.mkdir()
                    row.update(semantic_review="not_run", reason="provider_denial_or_run_deadline_before_launch")
                    ev.dump(directory / "result.json", row)
                    rows.append(row)
                    previous = row
                    continue
                seconds = min(420, remaining)
                command = command_for(codex, workspace, directory / "final.txt", native_id)
                with (report / (job["name"] + "-started.json")).open("x", encoding="utf-8") as handle:
                    json.dump({"at": datetime.now(timezone.utc).isoformat(), "command": command,
                        "prepared_sha256": ev.sha(report / "prepared.json"), "prompt_sha256": job["prompt_sha256"],
                        "max_seconds": seconds, "native_parent": native_id, "previous_usage": previous_usage}, handle)
                observed = execute_preserving(command, workspace, job["prompt"], directory, seconds)
                ev.dump(directory / "execution.json", observed)
                row.update(execution=observed, acceptance="failed", turn_usage=followup_usage(observed.get("rollout", {}).get("cumulative_usage"), previous_usage, observed.get("native_id"), native_id) if native_id else observed["usage"])
                try:
                    data, integrity = receipt.check_environment(report, {**job, "arm": "product"}, workspace)
                    row["installed_integrity"] = integrity
                    if job["case"]["product_family"] is None:
                        row.update(accept_clarification(workspace, directory, observed, job))
                    else:
                        case = {**job["case"], "turns": [job["case"]["question"]], "submitted_question": job["prompt"]}
                        row.update(accept_family(workspace, directory, observed, case, data, "product"))
                        row["terminal_status"] = row["answer"]["result"]["status"]
                        if job["case"]["parent_id"]:
                            exported = receipt.artifact(workspace, row["pointer"]["export"])
                            after = inspect_history(workspace)
                            row["followup_linked"] = followup_linked(before, after, exported, observed.get("native_id"), native_id)
                            if not row["followup_linked"]:
                                raise ValueError("Native/previous turn/session/candidate history did not link")
                    if row["terminal_status"] not in job["case"]["expected_terminal_states"]:
                        raise ValueError("Unexpected terminal state")
                    row["acceptance"] = "contract_and_delivery_passed"
                except Exception as exc:
                    row["acceptance_error"] = str(exc)
                    # Final text can still be reviewed after a structural failure.
                    try:
                        row["summary"] = receipt.final_message(directory, observed)
                    except Exception:
                        pass
                if provider_denial(observed, directory):
                    halt.set()
                ev.dump(directory / "result.json", row)
                print(json.dumps({"input": job["name"], "execution": observed["status"], "acceptance": row["acceptance"], "terminal": row.get("terminal_status"), "seconds": observed.get("elapsed_seconds"), "usage": row["turn_usage"]}), flush=True)
                rows.append(row)
                previous = row
            return rows

        results, chain_errors = [], []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(chain, jobs): jobs for jobs in chains.values()}
            for future in as_completed(futures):
                jobs = futures[future]
                try:
                    results.extend(future.result())
                except Exception as exc:
                    chain_errors.append(str(exc))
                    for job in jobs:
                        directory = report / job["name"]
                        path = directory / "result.json"
                        if path.exists():
                            results.append(strict_json(path.read_text(encoding="utf-8")))
                            continue
                        row = {"job": job["name"], "case": job["case"], "acceptance": "not_run",
                               "semantic_review": "not_run", "reason": "chain_runner_exception", "exception": str(exc)}
                        if (report / (job["name"] + "-started.json")).exists():
                            row.update(acceptance="failed", execution={"status":"runner_failed", "native_id":None, "usage":ev.usage_delta(None)})
                            # Preserve partial observations; never relaunch the input.
                            if (directory / "execution.json").exists():
                                row["execution"] = strict_json((directory / "execution.json").read_text(encoding="utf-8"))
                            elif (directory / "native.jsonl").exists():
                                try:
                                    partial = ev.parse_cli(directory / "native.jsonl")
                                    row["execution"].update(partial, usage=ev.usage_delta(partial.get("cumulative_usage")))
                                except Exception as error:
                                    row["observation_error"] = str(error)
                        ev.dump(path, row)
                        results.append(row)
        results.sort(key=lambda row: row["job"])
        summary = {"planned_inputs": 10, "planned_conversations": 8,
            "native_attempts": sum(bool(r.get("execution")) for r in results),
            "acceptance_counts": dict(Counter(r["acceptance"] for r in results)),
            "execution_counts": dict(Counter(r.get("execution", {}).get("status", "not_run") for r in results)),
            "semantic_review": "pending", "usage": session_usage(results),
            "results": results, "chain_errors": chain_errors, "provider_denial_observed": halt.is_set(),
            "independent_holdout": False, "official_questions": False, "automatic_retry": False}
        ev.dump(report / "results.json", summary)
        return {k: v for k, v in summary.items() if k not in ("results", "usage")}
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "run"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=ev.ROOT / "evals/judge/family10.json")
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to((ev.ROOT / ".harness").resolve()):
        raise ValueError("Private report path required")
    print(json.dumps(prepare(report, args.cases.resolve()) if args.operation == "prepare" else run(report), ensure_ascii=False))


if __name__ == "__main__":
    main()
