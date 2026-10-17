"""Check the completeness of model-authored reasoning; never certify its truth."""
from .contracts import fail, identifier, items, obj, text
from .tools import ProductTools


def qualification(record):
    """A declared limitation is not source truth; require an explicit bounded draft."""
    value = record.get("qualification")
    if value is None:
        return None
    obj(value, ("basis", "limitations", "original_statement_supported"))
    if value["basis"] not in ("page_linked_example", "conditional_draft") or type(value["original_statement_supported"]) is not bool:
        fail("invalid_assessment", "Unknown qualification basis/support")
    limits = items(value["limitations"], "limitations", 5)
    if not limits:
        fail("invalid_assessment", "A qualified claim must retain explicit limitations")
    for limit in limits:
        text(limit, "limitation", 500)
    return value


def review_product_result(dataset, payload):
    obj(payload, ("input", "result", "assessment"), ("planner_insights",))
    planning, result = payload["input"], payload["result"]
    structural = ProductTools(dataset).validate_result_contract(planning, result)
    assessment = obj(payload["assessment"], ("claim_checks", "feature_matches", "concept_links"))
    claims = {c["id"]: c for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in result[key]}
    cited = {r["source_id"] for r in result["evidence_refs"]}
    findings, checked, qualified = [], set(), {}
    pain_ids = {p["id"] for p in result["pains"]}
    draft_ids = {p["id"] for key in ("remaining_pains", "concepts") for p in result[key]}
    for check in items(assessment["claim_checks"], "claim_checks", 63):
        obj(check, ("claim_id", "source_ids", "support_status", "scope_relation", "rationale"), ("qualification",))
        claim_id = identifier(check["claim_id"], "claim_id")
        if claim_id not in claims or claim_id in checked:
            fail("invalid_assessment", "Unknown or duplicate claim assessment")
        checked.add(claim_id)
        if check["source_ids"] != claims[claim_id]["source_ids"]:
            fail("invalid_assessment", "Assessment must use the claim's exact ordered sources")
        if check["support_status"] not in ("supported", "unsupported", "uncertain") or check["scope_relation"] not in ("current_model", "previous_product", "unclear"):
            fail("invalid_assessment", "Unknown support/scope assessment")
        text(check["rationale"], "rationale")
        q = qualification(check)
        limited = False
        if q and check["support_status"] != "unsupported" and check["scope_relation"] != "previous_product":
            if q["basis"] == "page_linked_example" and claim_id in pain_ids and q["original_statement_supported"]:
                reviews = [dataset.source(s) for s in check["source_ids"] if dataset.source(s)["kind"] == "review"]
                limited = bool(reviews) and all(r["origin"]["model_matching"] == "product_page_association" for r in reviews)
            elif q["basis"] == "conditional_draft" and claim_id in draft_ids:
                # A proposal may honestly be absent from the source. Its cited
                # premise, assumptions and remaining feasibility checks still apply.
                limited = bool(result["assumptions"])
                if claim_id in {c["id"] for c in result["concepts"]}:
                    limited = limited and bool(claims[claim_id]["assumptions"])
        if limited:
            qualified[claim_id] = q
        elif q:
            findings.append("invalid_qualification:" + claim_id)
        if not limited and (check["support_status"] != "supported" or check["scope_relation"] != "current_model"):
            findings.append("unsupported_or_uncertain:" + claim_id)
    if checked != claims.keys():
        fail("invalid_assessment", "Every claim requires a support assessment")
    pain_ids = {p["id"] for p in result["pains"]}
    remaining_ids = {p["id"] for p in result["remaining_pains"]}
    def source_scope(source_id):
        record = dataset.source(source_id)
        return tuple(record[k] for k in ("model_id", "model_version", "document_version"))
    def claim_scope(claim_id):
        return source_scope(claims[claim_id]["source_ids"][0])
    for section, required_kind in (("pains", "review"), ("existing_features", "product_fact")):
        for claim in result[section]:
            if not any(dataset.source(s)["kind"] == required_kind for s in claim["source_ids"]):
                findings.append("wrong_evidence_kind:" + claim["id"])
    matched = set()
    for match in items(assessment["feature_matches"], "feature_matches"):
        obj(match, ("remaining_pain_id", "pain_id", "feature_source_ids", "resolution", "rationale"))
        rid = identifier(match["remaining_pain_id"], "remaining_pain_id")
        pain_id = identifier(match["pain_id"], "pain_id")
        if rid not in remaining_ids or rid in matched or pain_id not in pain_ids:
            fail("invalid_assessment", "Remaining pain must link to an observed pain exactly once")
        matched.add(rid)
        refs = items(match["feature_source_ids"], "feature_source_ids")
        for source_id in refs:
            identifier(source_id, "feature_source_id")
        if len(set(refs)) != len(refs) or not set(refs) <= cited:
            fail("invalid_assessment", "Feature comparison sources must be cited and unique")
        if any(dataset.source(s)["kind"] != "product_fact" for s in refs):
            fail("invalid_assessment", "Feature comparison needs product facts")
        exact = claim_scope(match["pain_id"])
        if claim_scope(rid) != exact or any(source_scope(s) != exact for s in refs):
            fail("scope_mismatch", "Pain, remaining pain and feature comparison must share one exact model snapshot")
        if match["resolution"] not in ("resolved", "partially_resolved", "unresolved", "uncertain"):
            fail("invalid_assessment", "Unknown feature resolution")
        text(match["rationale"], "rationale")
        if not refs or match["resolution"] == "resolved" or (match["resolution"] == "uncertain" and qualified.get(rid, {}).get("basis") != "conditional_draft"):
            findings.append("remaining_pain_not_supported:" + rid)
    if matched != remaining_ids:
        fail("invalid_assessment", "Every remaining pain needs a feature comparison")
    linked = set()
    concept_ids = {c["id"] for c in result["concepts"]}
    for link in items(assessment["concept_links"], "concept_links", 3):
        obj(link, ("concept_id", "remaining_pain_ids", "duplicates_existing", "geometry_required", "geometry_known", "geometry_source_ids", "rationale"))
        cid = identifier(link["concept_id"], "concept_id")
        if cid not in concept_ids or cid in linked:
            fail("invalid_assessment", "Unknown or duplicate concept linkage")
        linked.add(cid)
        needs = items(link["remaining_pain_ids"], "remaining_pain_ids")
        for remaining_id in needs:
            identifier(remaining_id, "remaining_pain_id")
        if not needs or len(set(needs)) != len(needs) or not set(needs) <= remaining_ids:
            fail("invalid_assessment", "Each concept must address an identified remaining pain")
        if link["duplicates_existing"] is not None and type(link["duplicates_existing"]) is not bool:
            fail("invalid_assessment", "duplicates_existing must be boolean or null")
        for field in ("geometry_required", "geometry_known"):
            if type(link[field]) is not bool:
                fail("invalid_assessment", field + " must be boolean")
        geometry = items(link["geometry_source_ids"], "geometry_source_ids")
        for source_id in geometry:
            identifier(source_id, "geometry_source_id")
        if len(set(geometry)) != len(geometry) or not set(geometry) <= cited:
            fail("invalid_assessment", "Geometry sources must be unique cited sources")
        if any(dataset.source(s)["kind"] != "product_fact" for s in geometry):
            fail("invalid_assessment", "Geometry support requires product facts")
        exact = claim_scope(cid)
        if any(claim_scope(r) != exact for r in needs) or any(source_scope(s) != exact for s in geometry):
            fail("scope_mismatch", "Concept, linked remaining pains and dimensions must share one exact model snapshot")
        text(link["rationale"], "rationale")
        if link["duplicates_existing"] is True or (link["duplicates_existing"] is None and qualified.get(cid, {}).get("basis") != "conditional_draft"):
            findings.append("duplicate_or_unchecked:" + cid)
        if link["geometry_required"] and (not link["geometry_known"] or not geometry):
            findings.append("geometry_unconfirmed:" + cid)
    if linked != concept_ids:
        fail("invalid_assessment", "Every concept requires linkage and feasibility assessment")
    return {**structural, "assessment_contract_valid": True, "reported_reasoning_consistent": not findings,
            "can_finalize_reported_result": result["status"] != "completed" or not findings,
            "findings": findings, "qualified_claim_ids": sorted(qualified), "completion_scope": "planning_draft_only",
            "semantic_status": "unverified", "acceptance_ready": False,
            **({"planner_insights_review": {"scope": "authored_display_text_not_source_evidence", "semantic_status": "unverified",
                "note": "Display binding/shape is checked at delivery; original-source comparison of titles and summaries remains required."}}
               if "planner_insights" in payload else {}),
            "note": "Checks the model's report, not whether its interpretation is true. Original-source evaluation remains required; planning_quality_diagnostics is nonblocking field presence only."}
