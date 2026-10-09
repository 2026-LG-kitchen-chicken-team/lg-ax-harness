"""Audit saved native observations and installation drift; makes no model calls."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import native_eval as ev


def audit(report):
    plan = json.loads((report / "prepared.json").read_text(encoding="utf-8"))
    observed = json.loads((report / "results.json").read_text(encoding="utf-8"))
    rows = []
    for job, result in zip(plan["jobs"], observed["results"], strict=True):
        if result["case_id"] != job["case"]["id"] or result["arm"] != job["arm"]:
            raise ValueError("Observation order/identity changed")
        directory = report / job["name"]
        trace_path = directory / "native.jsonl"
        traces = ev.parse_cli(trace_path) if trace_path.exists() else {"native_id": None, "command_items": None}
        id_mismatch = result.get("native_id") is not None and traces["native_id"] is not None and traces["native_id"] != result["native_id"]
        hash_mismatch = trace_path.exists() and result.get("stdout_sha256") is not None and ev.sha(trace_path) != result["stdout_sha256"]
        if id_mismatch or hash_mismatch:
            raise ValueError("Native trace identity/fingerprint changed")
        source = report / ("source-before" if job["arm"] == "before" else "source-after")
        workspace = Path(job["workspace"])
        installed = None if job["arm"] == "baseline" else ev.load_installer(source).check(workspace)
        integrity = installed is None or not installed["errors"]
        source_hashes = plan["source_before" if job["arm"] == "before" else "source_after"]
        frozen_intact = all(ev.sha(source / name) == digest for name, digest in source_hashes.items())
        counts = None
        if job["arm"] != "baseline" and (workspace / "runtime-data/product.sqlite").exists():
            db = workspace / "runtime-data/product.sqlite"
            connection = sqlite3.connect("file:" + db.as_posix() + "?mode=ro", uri=True)
            try:
                counts = {table: connection.execute("SELECT count(*) FROM " + table).fetchone()[0] for table in ("turns", "results", "conversation_requests")}
            finally:
                connection.close()
        usage = result.get("usage", ev.usage_delta(None))
        structural = result.get("structural_check") or {}
        rollout=result.get("rollout") or {}
        functions=rollout.get("function_calls")
        spawn_count=sum(n for k,n in functions.items() if k.endswith("spawn_agent")) if isinstance(functions,dict) and rollout.get("metadata") else None
        rows.append({"name": job["name"], "case_id": result["case_id"], "arm": result["arm"], "native_id": result.get("native_id") or traces["native_id"],
                     "runner_status": result.get("status", "unknown"), "execution_status": result.get("execution_status") or (result.get("status", "unknown") if result.get("status") != "runner_failed" else "unknown"),
                     "exit_code": result.get("exit_code"), "elapsed_seconds": result.get("elapsed_seconds"),
                     "trace_hash_checked": trace_path.exists() and result.get("stdout_sha256") is not None,
                     "command_items": traces["command_items"], "contract_valid": structural.get("contract_valid", False),
                     "contract_error": structural.get("reason", "postprocessing_incomplete" if not structural else None), "contract_error_message": structural.get("message"),
                     "saved_answer_matches": result.get("saved_answer_matches"), "operational_saved": result.get("operational_saved"),
                     "counts": counts, "baseline_no_tools": result.get("baseline_no_tools"), "source_bundle_sha256": job["sources_sha256"],
                     "installed_files_intact": integrity, "frozen_source_intact": frozen_intact, "usage": usage,
                     "noncached_input_tokens": usage["input_tokens"] - usage["cached_input_tokens"] if all(usage[k] is not None for k in ("input_tokens", "cached_input_tokens")) else None,
                     "native_spawn_calls": spawn_count, "child_usage": None, "aggregate_coverage": "unknown",
                     "cost_usd": None, "human_effort_seconds": None})
    equal_data = all(len({r["source_bundle_sha256"] for r in rows if r["case_id"] == case}) == 1 for case in {r["case_id"] for r in rows})
    baseline_prompts=[j.get("prompt", "") for j in plan["jobs"] if j["arm"]=="baseline"]
    explicit_contract=bool(baseline_prompts) and all("assumptions와 validation_findings는 문자열 배열" in p and "비어있지 않은 중복 없는 배열" in p for p in baseline_prompts)
    result = {"observations": rows, "same_source_bundles": equal_data, "observed_config_matched": observed["config_matched"],
              "contract_passes": sum(r["contract_valid"] for r in rows), "executions_succeeded": sum(r["execution_status"] == "succeeded" for r in rows),
              "runner_failures": sum(r["runner_status"] == "runner_failed" for r in rows),
              "session_reported_usage_totals": ev.usage_totals([r["usage"] for r in rows]), "child_usage": None, "aggregate_coverage": "unknown",
              "quality_superiority_proven": False, "cost_savings_proven": False, "semantic_review": "separate independent source review required",
              "prompt_contract_revision":"explicit-string-arrays-nonempty-claims-v2" if explicit_contract else "initial-or-unobserved",
              "baseline_limitation": "Explicit neutral contract observed in these baseline prompts; still small sample and unequal product operation burden, not superiority evidence." if explicit_contract else "Initial/unobserved common outline lacks confirmed explicit string-array/nonempty-source constraints; shape failures do not prove answer superiority."}
    ev.dump(report / "audit.json", result)
    if not equal_data or not all(r["installed_files_intact"] and r["frozen_source_intact"] for r in rows):
        raise ValueError("Source drift or unequal evidence detected")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(ev.ROOT / ".harness"):
        raise ValueError("Audit only project-local ignored report folders")
    value = audit(report)
    print(json.dumps({"source_audit_passed": True, "executions_succeeded": value["executions_succeeded"], "contract_passes": value["contract_passes"], "aggregate_coverage": "unknown"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
