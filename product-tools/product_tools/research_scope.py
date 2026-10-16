"""Declared investigation goals and literal scan linkage; no sufficiency classifier."""
from .contracts import fail, identifier, obj, text

POLICY = "research-scope-v1"
KINDS = {"official_spec", "manual", "external_reviews", "next_pages", "conditions", "counterexamples"}


def goals(events):
    result = {}
    for event in events:
        if event["kind"] == "research_plan":
            for goal in event["data"].get("goals", []):
                result[goal["goal_id"]] = goal
    return result


def validate_plan(data, events):
    if "goals" not in data:
        return
    values = data["goals"]
    if not isinstance(values, list) or not 1 <= len(values) <= 100:
        fail("workflow_goal_invalid", "Plan goals in nonempty batches of at most 100")
    known, seen = goals(events), set()
    for goal in values:
        obj(goal, ("goal_id", "kind", "scope_note"), ("source_url",))
        gid = identifier(goal["goal_id"], "goal_id")
        if gid in seen or gid in known and known[gid] != goal:
            fail("workflow_goal_conflict", "A goal ID is immutable; do not replace its scope")
        seen.add(gid)
        if not isinstance(goal["kind"], str) or goal["kind"] not in KINDS:
            fail("workflow_goal_invalid", "Unknown investigation goal kind")
        text(goal["scope_note"], "goal scope", 2000)
        if "source_url" in goal:
            from .web_evidence import public_url
            public_url(goal["source_url"])


def validate_scan(data, events, required):
    ids = data.get("goal_ids", [])
    if required and not ids:
        fail("workflow_goal_missing", "Bind every new web scan to declared investigation goals")
    if not isinstance(ids, list) or any(not isinstance(gid, str) for gid in ids) or len(ids) > 100 or len(set(ids)) != len(ids):
        fail("workflow_goal_invalid", "goal_ids must be distinct strings, at most 100 per scan")
    known = goals(events)
    for gid in ids:
        identifier(gid, "goal_id")
        if gid not in known:
            fail("workflow_goal_unknown", "Scan goal is absent from this request's plan")
        goal = known[gid]
        if goal.get("source_url", data["source_url"]) != data["source_url"]:
            fail("workflow_goal_scope", "Scan URL differs from its exact planned source URL")
        expected = {"official_spec": "product_document", "manual": "manual", "external_reviews": "review_list"}.get(goal["kind"])
        if expected and data.get("source_type", "unknown") != expected:
            fail("workflow_goal_scope", "Scan source type differs from the planned document/review role")


def summary(events):
    known = goals(events)
    scans = {}
    for event in events:
        if event["kind"] != "source_scan":
            continue
        data = event["data"]
        for gid in data.get("goal_ids", []):
            scans.setdefault(gid, {})[data["source_url"]] = data
    rows = []
    for gid, goal in known.items():
        values = list(scans.get(gid, {}).values())
        remaining = sorted({s for scan in values for s in scan.get("remaining_scope", [])})
        inaccessible = [scan for scan in values if scan["status"] == "inaccessible"]
        state = ("pending" if not values else "inaccessible" if inaccessible else "partial" if remaining
                 else "not_applicable" if all(scan["status"] == "not_applicable" for scan in values) else "observed")
        rows.append({**goal, "state": state, "remaining_scope": remaining,
                     "scans": [{k: scan.get(k) for k in ("source_url", "source_type", "status", "reason", "remaining_scope", "list_total")} for scan in values]})
    return {"goals": rows, "remaining_goal_ids": sorted(row["goal_id"] for row in rows if row["state"] in ("pending", "partial", "inaccessible")),
            "unattempted_goal_ids": sorted(row["goal_id"] for row in rows if row["state"] == "pending"),
            "remaining_scope": sorted({s for row in rows for s in row["remaining_scope"]}),
            "scope_validation": "declared plan/scan linkage only; not semantic sufficiency, independence or representativity"}


def validate_stop(data, events, finalizing=False):
    report = summary(events)
    kinds = {goal["kind"] for goal in report["goals"]}
    if (finalizing or data["code"] in ("sufficient_evidence", "sources_exhausted")) and not KINDS <= kinds:
        fail("workflow_goal_missing", "Plan official specifications, manual, external reviews, next pages, conditions and counterexamples")
    if (finalizing or data["code"] in ("sufficient_evidence", "sources_exhausted")) and not any(e["kind"] == "source_scan" for e in events):
        fail("workflow_goal_unobserved", "Sufficiency/exhaustion needs actual scan records, not only a plan")
    ids = data.get("remaining_goal_ids", [])
    if not isinstance(ids, list) or any(not isinstance(gid, str) for gid in ids) or len(set(ids)) != len(ids):
        fail("workflow_goal_invalid", "remaining_goal_ids must be distinct declared IDs")
    if set(ids) != set(report["remaining_goal_ids"]):
        fail("workflow_goal_omitted", "Disclose every pending/partial/inaccessible goal; do not hide unattempted scope")
    if not set(report["remaining_scope"]) <= set(data["remaining_scope"]):
        fail("workflow_goal_omitted", "Disclose the scan's remaining pages/sections/conditions verbatim")
    if ids or data["remaining_scope"]:
        text(data.get("limitation_basis"), "remaining scope/conclusion impact", 8000)
    # A caller may justify a conditional conclusion despite inaccessible/pending
    # scope. The text is retained for independent review, never classified here.
    return report


def preview(report):
    """Bound status context only; validation and exported events remain complete."""
    rows = []
    for goal in report["goals"][:10]:
        row = {k: goal[k] for k in ("goal_id", "kind", "state")}
        row["scope_note_preview"] = goal["scope_note"][:120]
        row["scan_count"] = len(goal["scans"])
        row["remaining_scope_count"] = len(goal["remaining_scope"])
        row["scans_preview"] = [{"source_url_preview": scan["source_url"][:150],
            "status": scan["status"], "reason_preview": (scan.get("reason") or "")[:100],
            "remaining_scope_count": len(scan.get("remaining_scope") or [])} for scan in goal["scans"][-1:]]
        rows.append(row)
    return {"goals": rows, "goal_count": len(report["goals"]),
            "remaining_goal_ids": report["remaining_goal_ids"][:20],
            "remaining_goal_count": len(report["remaining_goal_ids"]),
            "unattempted_goal_ids": report["unattempted_goal_ids"][:20],
            "unattempted_goal_count": len(report["unattempted_goal_ids"]),
            "remaining_scope": [s[:100] for s in report["remaining_scope"][:20]],
            "remaining_scope_count": len(report["remaining_scope"]),
            "detail_operation": "export_session requests[].workflow_events retains full goals/scan/stop",
            "detail_scope": "bounded status previews; use complete events for stop IDs and verbatim remaining scope",
            "scope_validation": report["scope_validation"]}
