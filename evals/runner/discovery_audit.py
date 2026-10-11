"""Read-only extra audit of frozen discovery runs; never invokes a model or web.

Mechanical linkage is not source authority or semantic quality certification.
The original runner and its evidence remain unchanged; CLI writes a new sidecar.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3

import discovery_eval as base
from followup_report import command_outputs
from product_tools.contracts import fingerprint, strict_json
from product_tools.web_evidence import model_token


def load(path):
    return strict_json(path.read_text(encoding="utf-8"))


def unwrap(value):
    if isinstance(value, dict) and set(value) == {"ok", "result"}:
        if value["ok"] is not True:
            raise ValueError("Unsuccessful response envelope")
        return value["result"]
    return value


def export_snapshot(directory, row):
    pointer = unwrap(row["pointer"]["export"])
    path = base.relative_path(pointer["path"], "runtime-data/exports")
    target = directory / "runtime-after" / Path(*path.parts[1:])
    if base.ev.sha(target) != pointer["sha256"]:
        raise ValueError("Export snapshot SHA differs from final pointer")
    return load(target)


def frozen_input(directory, job, row):
    if fingerprint(row.get("case")) != fingerprint(job["case"]):
        raise ValueError("Actual result case differs from frozen prepared case")
    if row.get("execution"):
        # newline=None reproduces the runner's text input on Windows.
        if (directory / "prompt.txt").read_text(encoding="utf-8") != job["prompt"]:
            raise ValueError("Actual native prompt differs from frozen prepared prompt")
        identity = row["execution"].get("native_id")
        if identity and base.ev.parse_cli(directory / "native.jsonl").get("native_id") != identity:
            raise ValueError("Actual native trace identity differs from result observation")
    return True


def import_responses(trace):
    """Only successful actual CLI command events, never an echoed label."""
    responses = []
    entry = re.compile(r"(?:product-tools[/\\]cli\.py|web-evidence-collection[/\\]scripts[/\\]run\.py)\s+import_web_evidence(?:\s|$)")
    for item in command_outputs(trace):
        command = item.get("command", "")
        if (type(item.get("exit_code")) is not int or item["exit_code"] != 0
                or not entry.search(command) or not re.search(r"\bpython(?:\.exe)?\s+", command)
                or re.match(r"\s*(?:echo|write-output)\b", command, re.I)):
            continue
        for line in item.get("aggregated_output", "").splitlines():
            try:
                response = strict_json(line)
            except (ValueError, TypeError):
                continue
            if isinstance(response, dict) and response.get("ok") is True and isinstance(response.get("result"), dict):
                responses.append(response["result"])
    return responses


def registration(directory, case, row):
    if not case.get("require_registration"):
        return None
    path = base.relative_path(row.get("data_path", ""), "runtime-data/catalogs")
    if len(path.parts) != 3:
        raise ValueError("Required registration has no exact runtime catalog")
    runtime = directory / "runtime-after"
    def bound(path):
        relative = path.relative_to(runtime).as_posix()
        if row.get("runtime_snapshot", {}).get(relative) != base.ev.sha(path):
            raise ValueError("Required registration file has no matching preserved snapshot SHA")
    for name in ("manifest.json", "models.json", "sources.jsonl", "import-audit.json"):
        bound(runtime / Path(*path.parts[1:]) / name)
    final = base.ev.Dataset(runtime / Path(*path.parts[1:]))
    if row.get("data_fingerprint") != final.fingerprint:
        raise ValueError("Selected catalog fingerprint differs")
    final_audit = load(final.root / "import-audit.json")
    if final_audit.get("data_fingerprint") != final.fingerprint:
        raise ValueError("Final import-audit fingerprint differs")
    models = [m for m in final.models if m["model_id"] == case["model_id"]]
    if len(models) != 1 or models[0]["product_family"] != case["product_family"]:
        raise ValueError("Registered exact model/family differs from requested target")
    model = models[0]
    for field in ("model_version", "document_version"):
        if field in case and model[field] != case[field]:
            raise ValueError("Registered requested version differs")
    responses = import_responses(directory / "native.jsonl")
    def observed_import(payload, catalog):
        return payload.get("data_version") == catalog.name and any(
            r.get("data_path") == "runtime-data/catalogs/" + catalog.name
            and r.get("data_version") == payload.get("data_version")
            and type(r.get("added_models")) is int and r["added_models"] == len(payload.get("new_models", []))
            and type(r.get("added_sources")) is int and r["added_sources"] == len(payload["observations"])
            and r.get("structural_valid") is True for r in responses)
    if not observed_import(final_audit["input"],final.root):
        raise ValueError("Selected final catalog lacks matching successful actual import/stdout")
    errors = []
    # Later imports may add reviews without registering the identity again. Bind
    # the retained introducing catalog to the final identity and actual command.
    for audit_path in sorted((runtime / "catalogs").glob("*/import-audit.json")):
        audit = load(audit_path)
        payload = audit.get("input", {})
        introduced = [m for m in payload.get("new_models", []) if m.get("model_id") == case["model_id"]]
        if not introduced:
            continue
        try:
            for name in ("manifest.json", "models.json", "sources.jsonl", "import-audit.json"):
                bound(audit_path.parent / name)
            introduced_data = base.ev.Dataset(audit_path.parent)
            if audit.get("data_fingerprint") != introduced_data.fingerprint:
                raise ValueError("Introducing catalog fingerprint differs")
            if len(introduced) != 1 or fingerprint(introduced[0]) != fingerprint(model):
                raise ValueError("Final model differs from observed newly imported identity")
            version = payload["data_version"]
            expected_path = "runtime-data/catalogs/" + audit_path.parent.name
            if version != audit_path.parent.name or not any(
                    r.get("data_path") == expected_path and r.get("data_version") == version
                    and type(r.get("added_models")) is int and r["added_models"] == len(payload["new_models"])
                    and type(r.get("added_sources")) is int and r["added_sources"] == len(payload["observations"])
                    and r.get("structural_valid") is True for r in responses):
                raise ValueError("No matching successful actual import command/stdout")
            identity = model.get("identity_review", {})
            sid = model["spec_source_id"]
            if (model.get("synthetic") is not False or identity.get("source_id") != sid
                    or identity.get("authority") != "manufacturer" or not identity.get("manufacturer") or not identity.get("rationale")):
                raise ValueError("Missing declared same-source identity review")
            entries = [e for e in payload["observations"] if e.get("source_id") == sid]
            if len(entries) != 1:
                raise ValueError("Identity source is not a unique same-import observation")
            entry = entries[0]
            scope = {k: model[k] for k in ("model_id", "model_version", "document_version")}
            if (entry.get("kind") != "product_fact" or entry.get("scope") != scope
                    or entry.get("availability") != "present" or "association_snapshot_id" in entry):
                raise ValueError("Identity fact lacks exact observed scope")
            snapshot_id = entry["snapshot_id"]
            base.identifier(snapshot_id, "snapshot_id")
            snapshot_path = runtime / "web-evidence" / (snapshot_id + ".json")
            bound(snapshot_path)
            snapshot = load(snapshot_path)
            body = {k: v for k, v in snapshot.items() if k != "snapshot_id"}
            quote = entry.get("support_quote")
            if (snapshot.get("snapshot_id") != snapshot_id or fingerprint(body) != snapshot_id
                    or not isinstance(quote, str) or not quote or quote != entry.get("text")
                    or quote not in snapshot.get("text", "") or not model_token(model["model_id"], quote)
                    or (model["model_version"] != "unspecified" and not model_token(model["model_version"], quote))):
                raise ValueError("Exact spec identity quote/snapshot fingerprint is not linked")
            source = final.sources.get(sid, {})
            original_source = introduced_data.sources.get(sid, {})
            normalized = {k:v for k,v in source.items() if k != "data_version"}
            original_normalized = {k:v for k,v in original_source.items() if k != "data_version"}
            if (fingerprint(normalized) != fingerprint(original_normalized)
                    or any(source.get(k) != v for k,v in scope.items())
                    or source.get("kind") != "product_fact" or source.get("text") != quote
                    or source.get("sha256") != hashlib.sha256(quote.encode("utf-8")).hexdigest()
                    or source.get("origin", {}).get("source_url") != snapshot.get("url")
                    or source.get("origin", {}).get("representation") != "factual_summary"):
                raise ValueError("Final spec source differs from exact observed identity evidence")
            return True
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
    raise ValueError("No proven introducing import: " + "; ".join(errors))


def selected_input(exported, row):
    if "request" in row.get("pointer", {}):
        request = unwrap(row["pointer"]["request"])
        saved = next(r for r in exported["requests"] if r["input"]["request_key"] == request["request_key"])
        return saved["input"], saved.get("events", [])
    turn_id = row["pointer"]["receipt"]["turn_id"]
    turn = next(t for t in exported["turns"] if t["state"]["turn_id"] == turn_id)
    saved = next(r for r in exported["requests"] if r.get("turn_id") == turn_id)
    return saved["input"], saved.get("events", []) + [{"input":{"selection":turn["state"]["input"]}}]


def request_scope(case, saved, events):
    if saved.get("question") != case["question"]:
        raise ValueError("Saved original question differs")
    constraints = saved.get("constraints", {})
    if any(constraints.get(k) != v for k,v in case["constraints"].items()):
        raise ValueError("Saved explicit request constraints differ")
    selections = [saved] + [e.get("input", {}).get("selection", {}) for e in events]
    for selected in selections:
        scopes = selected.get("model_scope", [])
        for field in ("model_id", "product_family", "model_version", "document_version"):
            values = [selected[field]] if field in selected else []
            if field != "product_family":
                values += [s[field] for s in scopes if field in s]
            if field in case and any(value != case[field] for value in values):
                raise ValueError("Saved request/selection model, family or version differs")
    # A genuinely unresolved held request can omit selection. The question and
    # constraints still have to match; this is not registered-model success.
    return True


def candidates(exported):
    return {fingerprint({"turn_id":t["state"]["turn_id"], **c})
            for t in exported.get("turns", []) for c in t.get("candidates", [])}


def stored_history(directory, exported):
    """Compare every retained candidate/request/event with read-only SQLite."""
    connection = sqlite3.connect((directory/"runtime-after/product.sqlite").resolve().as_uri()+"?mode=ro",uri=True)
    try:
        session = exported["session_id"]
        actual_turns = {r[0] for r in connection.execute("SELECT turn_id FROM turns WHERE session_id=?",(session,))}
        if actual_turns != {t["state"]["turn_id"] for t in exported.get("turns", [])}:
            raise ValueError("Export turn history differs from stored session")
        for turn in exported.get("turns", []):
            actual = [{"result_key":r[0],"result_version":r[1],"result":strict_json(r[2]),"validation":strict_json(r[3])}
                      for r in connection.execute("SELECT result_key,result_version,payload,validation_json FROM results WHERE turn_id=? ORDER BY result_version",(turn["state"]["turn_id"],))]
            if fingerprint(actual) != fingerprint(turn.get("candidates", [])):
                raise ValueError("Export candidate history differs from stored original results")
        actual_requests = connection.execute("SELECT request_key,payload,turn_id,request_version FROM conversation_requests WHERE session_id=?",(session,)).fetchall()
        if {r[0] for r in actual_requests} != {r["input"]["request_key"] for r in exported.get("requests", [])}:
            raise ValueError("Export request history differs from stored session")
        for key,payload,turn_id,version in actual_requests:
            saved = next(r for r in exported["requests"] if r["input"]["request_key"] == key)
            events = [{"kind":r[0],"version":r[1],"input":strict_json(r[2])} for r in connection.execute(
                "SELECT kind,version,payload FROM request_events WHERE session_id=? AND request_key=? ORDER BY version",(session,key))]
            if (fingerprint(strict_json(payload)) != fingerprint(saved["input"]) or turn_id != saved.get("turn_id")
                    or version != saved.get("request_version") or fingerprint(events) != fingerprint(saved.get("events", []))):
                raise ValueError("Original request/version/event history differs from stored SQLite")
    finally:
        connection.close()
    return True


def followup(report, directory, case, row, parent, exported, saved):
    if not case.get("parent_id"):
        return None
    parent_id = parent.get("execution", {}).get("native_id")
    started = load(report / (row["job"] + "-started.json"))
    if (not parent_id or row.get("execution", {}).get("native_id") != parent_id
            or started.get("native_parent") != parent_id):
        raise ValueError("Followup native identity/start evidence differs")
    command = started.get("command", [])
    if not isinstance(command, list) or "resume" not in command or parent_id not in command:
        raise ValueError("Followup command does not resume actual parent")
    previous = export_snapshot(report / parent["job"], parent)
    previous_turn = parent.get("pointer", {}).get("receipt", {}).get("turn_id")
    if (not previous_turn or exported.get("session_id") != previous.get("session_id")
            or saved.get("prior_turn_id") != previous_turn):
        raise ValueError("Followup session/prior turn differs")
    if not candidates(previous).issubset(candidates(exported)):
        raise ValueError("Prior result candidate/history was removed or changed")
    old_requests = {fingerprint(r["input"]) for r in previous.get("requests", [])}
    if not old_requests.issubset({fingerprint(r["input"]) for r in exported.get("requests", [])}):
        raise ValueError("Prior request history was removed or changed")
    return True


def usage_fields(rows, reported_attempts):
    result = copy.deepcopy(base.session_usage(rows))
    result.pop("complete_native_usage", None)
    attempts = [r for r in rows if r.get("execution")]
    last = {}
    for row in attempts:
        identity = row["execution"].get("native_id")
        if identity:
            last[identity] = row["execution"].get("usage", {})
    fields_known = bool(last) and all(type(u.get(f)) is int and u[f] >= 0
                                     for u in last.values() for f in base.ev.FIELDS)
    coverage = bool(attempts) and type(reported_attempts) is int and len(attempts) == reported_attempts and not result["attempts_without_native_id"]
    result.update(observed_session_usage_fields_complete=bool(fields_known and coverage),
                  native_attempt_coverage=bool(coverage), mandatory_numeric_fields=list(base.ev.FIELDS),
                  full_backend_usage_verified=False)
    return result


def audit(report, review_file=None):
    original_audit = base.audit(report, review_file)
    plan = base.verify_plan(report)
    original = load(report / "results.json")
    rows = original["results"]
    result = copy.deepcopy(original_audit)
    by_id = {r["job"]:r for r in rows}
    for job,row,outcome in zip(plan["jobs"],rows,result["outcomes"],strict=True):
        directory = report / row["job"]
        checks = {}
        errors = []
        operations = [("frozen_case_and_actual_prompt", lambda: frozen_input(directory,job,row)),
                      ("observed_new_model_registration", lambda: registration(directory,job["case"],row))]
        if row.get("pointer"):
            def request_and_followup():
                exported = export_snapshot(directory,row)
                stored_history(directory,exported)
                saved,events = selected_input(exported,row)
                request_scope(job["case"],saved,events)
                followup(report,directory,job["case"],row,by_id.get(job["case"].get("parent_id")),exported,saved)
                return True
            operations.append(("saved_request_scope_and_followup_history",request_and_followup))
        else:
            checks["saved_request_scope_and_followup_history"] = None
        for name,operation in operations:
            try:
                checks[name] = operation()
            except (ValueError, KeyError, TypeError, OSError, StopIteration, sqlite3.Error) as exc:
                checks[name] = False
                errors.append(name + ": " + str(exc))
        passed = not errors and all(v is not False for v in checks.values())
        outcome.update(additional_checks=checks,additional_integrity_passed=passed,
                       overall_passed=bool(outcome["overall_passed"] and passed))
        outcome["findings"] += errors
    result["usage"] = usage_fields(rows,original["native_attempts"])
    result.update(overall_pass=bool(result["outcomes"]) and all(r["overall_passed"] for r in result["outcomes"]),
                  full_backend_usage_verified=False,product_execution_performed=False,
                  audit_kind="additional mechanical audit plus separately supplied semantic review",
                  audit_inputs={"prepared_sha256":base.ev.sha(report/"prepared.json"),
                                "results_sha256":base.ev.sha(report/"results.json"),
                                "auditor_sha256":base.ev.sha(Path(__file__)),
                                "review_sha256":base.ev.sha(review_file) if review_file else None})
    result["limits"] += ["Identity review declarations and saved page labels do not prove manufacturer authority or tool execution",
                         "factual_summary is caller-authored; exact identity quote linkage does not certify all product facts"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--review",type=Path)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to((base.ev.ROOT / ".harness").resolve()):
        raise ValueError("Private report below checkout .harness required")
    result = audit(report,args.review.resolve() if args.review else None)
    suffix = result["audit_inputs"]["auditor_sha256"][:12] + "-" + (result["audit_inputs"]["review_sha256"] or "unreviewed")[:12]
    artifact = report / ("discovery-additional-audit-" + suffix + ".json")
    with artifact.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    print(json.dumps({"artifact":str(artifact),"overall_pass":result["overall_pass"]},ensure_ascii=False))
    return int(not result["overall_pass"]) if args.review else int(any(not r["additional_integrity_passed"] for r in result["outcomes"]))


if __name__ == "__main__":
    raise SystemExit(main())
