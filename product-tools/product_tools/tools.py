"""Deterministic lookup and structural validation, never semantic certification."""
from .contracts import canonical, evidence_ref, fail, items, obj, planning_input, planning_quality_diagnostics, product_result

class ProductTools:
    def __init__(self, dataset):
        self.dataset = dataset

    def list_models(self, payload):
        obj(payload, ("product_family",))
        from .contracts import product_family
        family = product_family(payload["product_family"])
        models = [m for m in self.dataset.models if m["product_family"] == family]
        return {"product_family": family, "models": models, "data_version": self.dataset.version,
                "dataset_fingerprint": self.dataset.fingerprint, "coverage": "catalog_cases_only",
                "model_count": len({m["model_id"] for m in models}), "snapshot_count": len(models),
                "counts_are": "source records per snapshot, not independent customers or prevalence",
                "source_counts": [{"scope": {k: m[k] for k in ("model_id", "model_version", "document_version")},
                    **{kind: self.dataset.retrieve(kind, {k: m[k] for k in ("model_id", "model_version", "document_version")})["total"]
                       for kind in ("review", "product_fact")}} for m in models], "semantic_status": "unverified"}

    def prepare_planning_input(self, payload):
        from .contracts import identifier
        obj(payload, ("session_id", "request_key"), ("model_id", "product_family", "scope_mode", "model_scope", "model_version", "document_version", "question", "target_customer", "constraints", "runtime", "workflow"))
        mode = payload.get("scope_mode", "exact_model" if payload.get("model_id") else "family_catalog")
        if mode not in ("exact_model", "family_catalog"):
            fail("invalid_input", "Unknown scope_mode")
        if mode == "family_catalog":
            if any(k in payload for k in ("model_id", "model_version", "document_version")):
                fail("invalid_input", "Select a family catalog or one exact model, not both")
            catalog = self.list_models({"product_family": payload.get("product_family")})
            candidates = catalog["models"]
            if "model_scope" in payload:
                from .contracts import items, scope
                selected = items(payload["model_scope"], "model_scope", 5)
                for exact in selected:
                    scope(exact)
                    self.dataset.check_scope(exact)
                candidates = [m for m in candidates if any(all(m[k] == exact[k] for k in exact) for exact in selected)]
                if len(candidates) != len(selected):
                    fail("family_mismatch", "All preserved scopes must belong to the requested family")
            if not candidates:
                fail("research_required", "No observed sources for this family; research and register matching models before planning")
            if len(candidates) > 5 or len({m["model_id"] for m in candidates}) != len(candidates):
                fail("needs_input", "Catalog exceeds five models or has multiple snapshots; narrow the range/version")
            model = None
        else:
            if "model_scope" in payload:
                fail("invalid_input", "Exact model selection cannot supply a family range")
            identifier(payload.get("model_id"), "model_id")
            candidates = [m for m in self.dataset.models if m["model_id"] == payload["model_id"]
                          and all(m[k] == payload[k] for k in ("model_version", "document_version") if k in payload)]
            if not candidates:
                fail("unknown_model" if payload["model_id"] not in {m["model_id"] for m in self.dataset.models} else "unknown_scope", "Selected model/version is not in verified catalog")
            if len(candidates) != 1:
                fail("needs_input", "Model has multiple snapshots; select the exact product/document version")
            model = candidates[0]
            if "product_family" in payload and payload["product_family"] != model["product_family"]:
                fail("family_mismatch", "Selected model does not belong to the requested family")
        planning = {"session_id": payload["session_id"], "request_key": payload["request_key"],
                    "question": payload.get("question", "선택한 모델의 실제 사용 리뷰에서 불편을 찾아 기존 기능과 대조하고 근거 있는 상품·서비스 개선안을 제안해 줘."),
                    "product_family": candidates[0]["product_family"], "scope_mode": mode,
                    "model_scope": [{k: m[k] for k in ("model_id", "model_version", "document_version")} for m in candidates],
                    "target_customer": payload.get("target_customer", "미확인: 리뷰에 드러난 사용자 맥락만 사용"),
                    "context": ("제품군 요청: 등록된 모델별 제한 사례만 분석한다. 제품군 전체·모든 모델의 공통 불편이나 발생률로 일반화하지 않는다. 모델별 불편과 기능을 분리한다. " if mode == "family_catalog" else "모델 선택 중심 상품기획. ") + "자료에 없는 불편·내부 치수·시장 효과를 추정하지 않는다.",
                    "constraints": payload.get("constraints", {"max_concepts": 3, "hardware_allowed": True, "exclude_pains": []}),
                    "data_version": self.dataset.version,
                    "runtime": payload.get("runtime", {"engine": None, "engine_version": None, "model_id": None, "settings_fingerprint": None}),
                    "workflow": payload.get("workflow", {"rules_version": "product-contract-v1", "skill_fingerprint": None, "prompt_fingerprint": None})}
        planning_input(planning)
        self.dataset.check_input(planning)
        return {"input": planning, "model": model, "models": candidates,
                "review_count": sum(self.dataset.retrieve("review", s)["total"] for s in planning["model_scope"]),
                "runtime_metadata": "caller supplied or unobserved; native connection not verified", "semantic_status": "unverified"}

    def select_evidence(self, exact, source_ids):
        self.dataset.check_scope(exact)
        items(source_ids, "source_ids")
        if not source_ids:
            fail("invalid_input", "At least one source ID is required")
        result = []
        for source_id in source_ids:
            record = self.dataset.source(source_id)
            if any(record[k] != v for k, v in exact.items()):
                fail("scope_mismatch", "Source is outside requested model/version/document")
            result.append(self.dataset.reference(record))
        if len({r["source_id"] for r in result}) != len(result):
            fail("invalid_input", "Duplicate source ID")
        return {"evidence_refs": result, "structural_valid": True, "semantic_status": "unverified", "content_trust": "untrusted_source_data"}

    def validate_source_refs(self, refs, scopes):
        items(refs, "evidence_refs", 40)
        items(scopes, "model_scope", 5)
        if not scopes:
            fail("needs_input", "An exact model scope is required")
        for exact in scopes:
            self.dataset.check_scope(exact)
        allowed = {canonical(s) for s in scopes}
        used = set()
        for ref in refs:
            evidence_ref(ref)
            if ref["source_id"] in used:
                fail("invalid_input", "Duplicate evidence source ID")
            used.add(ref["source_id"])
            record = self.dataset.source(ref["source_id"])
            if canonical({k: record[k] for k in ("model_id", "model_version", "document_version")}) not in allowed:
                fail("scope_mismatch", "Evidence falls outside planning model scope")
            for key in ("model_id", "model_version", "document_version", "data_version", "location", "sha256", "synthetic", "origin"):
                if ref[key] != record[key]:
                    fail("reference_mismatch", f"Reference {key} differs from source")
            if ref["quote"] not in record["text"]:
                fail("quote_mismatch", "Quote must be an exact nonempty substring of source")
        return {"structural_valid": True, "checked_sources": len(refs), "semantic_status": "unverified",
                "acceptance_ready": False, "note": "Existence, scope, location, hash and quote checked; claim support needs independent review."}

    def validate_result_contract(self, planning, result):
        planning_input(planning)
        self.dataset.check_input(planning)
        product_result(result, planning)
        report = self.validate_source_refs(result["evidence_refs"], planning["model_scope"])
        referenced = {r["source_id"] for r in result["evidence_refs"]}
        used = set()
        for key in ("pains", "existing_features", "remaining_pains", "concepts"):
            for claim in result[key]:
                if not set(claim["source_ids"]) <= referenced:
                    fail("missing_evidence", "Each claim source ID must have an exact evidence reference")
                source_scopes = {canonical({k: self.dataset.source(s)[k] for k in ("model_id", "model_version", "document_version")}) for s in claim["source_ids"]}
                if len(source_scopes) != 1:
                    fail("scope_mismatch", "Each claim belongs to one exact model snapshot; separate cross-model claims")
                used.update(claim["source_ids"])
        for note in result.get("decision_notes", []):
            if not set(note["source_ids"]) <= referenced:
                fail("missing_evidence", "Each decision source ID must have an exact evidence reference")
            source_scopes = {canonical({k: self.dataset.source(s)[k] for k in ("model_id", "model_version", "document_version")}) for s in note["source_ids"]}
            if len(source_scopes) > 1:
                fail("scope_mismatch", "Each decision note belongs to one exact model snapshot")
            used.update(note["source_ids"])
        if referenced != used:
            fail("unused_evidence", "Unused citations must be removed to keep evidence focused")
        return {**report, "contract_version": "product-contract-v1", "contract_valid": True,
                "planning_detail_complete": bool(result["concepts"]) and all(
                    c.get("implementation_steps") and c.get("validation_plan") for c in result["concepts"]),
                "planning_detail_scope": "field presence only; no evaluation score or effect certification",
                "planning_quality_diagnostics": planning_quality_diagnostics(result),
                "decision_basis_scope": "model-reported labels only; not official quote or semantic certification",
                "semantic_checks_required": ["claim support", "decision note support and attribution", "existing-feature duplication", "excluded-pain meaning", "synthetic vs market interpretation", "manufacturing assumptions"]}
