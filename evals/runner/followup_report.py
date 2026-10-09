"""Audit preserved follow-up runs; source/operation checks are not semantic judging."""
import argparse
import json
from pathlib import Path
import native_eval as ev
import extended_eval as ex
import audit_report


DELEGATION=("spawn_agent","followup_task","send_message","fork_thread","create_thread")


def delegation(functions):
    if functions is None:
        return None
    return sum(n for k,n in functions.items() if any(k.endswith(name) for name in DELEGATION))


def command_outputs(trace):
    if not trace.exists():
        return []
    values=[]
    for line in trace.read_text(encoding="utf-8",errors="replace").splitlines():
        try:
            event=json.loads(line)
        except ValueError:
            continue
        item=event.get("item",{})
        if event.get("type")=="item.completed" and item.get("type")=="command_execution":
            values.append(item)
    return values


def audit_extension(report):
    plan=json.loads((report/"prepared.json").read_text(encoding="utf-8"))
    result=json.loads((report/"results.json").read_text(encoding="utf-8"))
    frozen_intact=all(ev.sha(report/"source-after"/name)==digest for name,digest in plan["source_after"].items())
    rows=[]
    skipped_turns=0
    observed_processes=0
    for planned,job in zip(plan["jobs"],result["jobs"],strict=True):
        if (planned["name"],planned["case"]["id"],planned["arm"],planned["mode"])!=(job["name"],job["case_id"],job["arm"],job["mode"]):
            raise ValueError("Job identity/order changed")
        missing=len(planned["prompts"])-len(job["observations"])
        if missing<0 or missing!=job["not_executed_turns"]:
            raise ValueError("Executed/missing turn count changed")
        skipped_turns+=missing
        current=ex.installed_integrity(report/"source-after",Path(job["workspace"]),planned["injection"]) if job["arm"]!="baseline" else None
        for position,observation in enumerate(job["observations"]):
            index=observation["turn_index"]
            if index!=position or observation["source_bundle_sha256"]!=planned["sources_sha256"]:
                raise ValueError("Turn order/source bundle changed")
            observed_processes+=type(observation.get("process_id")) is int
            trace=report/job["name"]/f"turn-{index}"/"native.jsonl"
            parsed=ev.parse_cli(trace) if trace.exists() else None
            hashes_match=trace.exists() and observation.get("stdout_sha256") is not None and ev.sha(trace)==observation["stdout_sha256"]
            identity_match=parsed is not None and parsed["native_id"]==observation.get("native_id")
            calls=observation.get("turn_function_calls")
            delegated=delegation(calls)
            outputs=command_outputs(trace)
            fault_seen=any("temporary_unavailable" in o.get("aggregated_output","") for o in outputs)
            note_seen=any("untrusted-source.txt" in o.get("command","") and "TEST_ONLY SYNTHETIC" in o.get("aggregated_output","") for o in outputs)
            termination=observation.get("termination") or {}
            rows.append({"job":job["name"],"case_id":job["case_id"],"arm":job["arm"],"mode":job["mode"],"turn_index":index,
                         "native_id":observation.get("native_id"),"status":observation["status"],"exit_code":observation.get("exit_code"),
                         "seconds":observation.get("elapsed_seconds"),"usage":observation.get("usage"),
                         "trace_hash_matches":hashes_match,"trace_identity_matches":identity_match,"installed_files_intact":current is None or not current["errors"],
                         "contract_valid":(observation.get("structural_check") or {}).get("contract_valid",False),
                         "result_status":(observation.get("answer") or {}).get("result",{}).get("status"),
                         "saved_answer_matches":observation.get("saved_answer_matches"),"operational_saved":observation.get("operational_saved"),
                         "new_business_turn_count":observation.get("new_business_turn_count"),"previous_candidates_preserved":observation.get("previous_candidates_preserved"),
                         "resume_identity_matches":observation.get("resume_identity_matches"),"baseline_no_tools":observation.get("baseline_no_tools"),
                         "turn_delegation_calls":delegated,"single_agent_observed":delegated==0 if delegated is not None and observation.get("rollout",{}).get("metadata") else None,
                         "source_bundle_sha256":observation["source_bundle_sha256"],"mode_test":
                         {"fault_fired":job.get("fault_fired"),"fault_error_delivered":fault_seen,"attack_note_delivered":note_seen,
                          "attack_sentinel_written":job.get("attack_sentinel_written"),"owned_deadline_termination_verified":observation["status"]=="timeout" and termination.get("exit_code")==0 and termination.get("process_exit") is not None,
                          "business_cancelled_proven":False},"semantic_review":"independent review required"})
    histories=[]
    for job in result["jobs"]:
        if job["case_id"]=="S05-R06" and job["arm"]=="after":
            history=job.get("history") or {}
            turns=history.get("turns") or []
            histories.append({"job":job["name"],"business_turns":len(turns),"one_session":len({t["session_id"] for t in turns})==1,
                              "old_turn_invalidated":len(turns)==2 and turns[0]["valid"]==0,"new_turn_valid":len(turns)==2 and turns[1]["valid"]==1,
                              "revisions":[t["revision_count"] for t in turns],"result_versions":[t["result_version"] for t in turns]})
    scope_groups={}
    for row in rows:
        if row["mode"]=="normal":
            scope_groups.setdefault((row["case_id"],row["turn_index"]),set()).add(row["source_bundle_sha256"])
    value={"observations":rows,"histories":histories,"frozen_source_intact":frozen_intact,"same_source_bundles":all(len(v)==1 for v in scope_groups.values()),
           "actual_invocations":observed_processes,"not_executed_turns":skipped_turns,"reported_usage_totals":ev.usage_totals([r["usage"] for r in rows]),
           "whole_agent_billing_coverage":"unknown","actual_cash_cost":None,"human_effort":None,"quality_superiority_proven":False,"cost_savings_proven":False,
           "scope":"Explicit user preference plus CLI flag; no observed delegation does not guarantee Tool unavailability. Separate synthetic note read, transient Tool process failure, and native deadline termination; no business cancel API."}
    ev.dump(report/"audit.json",value)
    if not rows or observed_processes!=result["actual_invocations"]:
        raise ValueError("Missing or inconsistent execution observations")
    if not frozen_intact or not value["same_source_bundles"] or not all(r["installed_files_intact"] and r["trace_hash_matches"] and r["trace_identity_matches"] for r in rows):
        raise ValueError("Saved trace/source/installed evidence failed integrity audit")
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat",type=Path,required=True)
    parser.add_argument("--extended",type=Path,required=True)
    args=parser.parse_args()
    for path in (args.repeat.resolve(),args.extended.resolve()):
        if not path.is_relative_to(ev.ROOT/".harness"):
            raise ValueError("Audit project-local ignored reports only")
    repeat=audit_report.audit(args.repeat.resolve())
    extended=audit_extension(args.extended.resolve())
    print(json.dumps({"repeat_executions":repeat["executions_succeeded"],"repeat_contracts":repeat["contract_passes"],"extended_rows":len(extended["observations"]),
                      "integrity_audit_passed":True,"semantic_review":"separate","whole_agent_billing_coverage":"unknown"}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
