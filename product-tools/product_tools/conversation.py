"""Conversation handles and historical exports. Never invokes a model/runtime."""
import hashlib
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import subprocess
import uuid
from .contracts import MAX_BYTES, MAX_RESULT_BYTES, canonical, fail, fingerprint, identifier, integer, obj, strict_json, text
from .payload import candidate_template
from .paths import real_path


class Conversation:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = Path(workspace).resolve()
        store.db.execute("""CREATE TABLE IF NOT EXISTS conversation_requests(
            session_id TEXT NOT NULL, request_key TEXT NOT NULL, payload TEXT NOT NULL,
            turn_id TEXT, response TEXT, PRIMARY KEY(session_id,request_key))""")
        columns = {r[1] for r in store.db.execute("PRAGMA table_info(conversation_requests)")}
        if "request_version" not in columns:
            store.db.execute("ALTER TABLE conversation_requests ADD COLUMN request_version INTEGER NOT NULL DEFAULT 0")
        store.db.execute("""CREATE TABLE IF NOT EXISTS request_events(
            session_id TEXT NOT NULL, request_key TEXT NOT NULL, event_key TEXT NOT NULL,
            version INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(session_id,request_key,event_key),
            FOREIGN KEY(session_id,request_key) REFERENCES conversation_requests(session_id,request_key))""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS reader_deliveries(
            turn_id TEXT NOT NULL REFERENCES turns(turn_id), result_version INTEGER NOT NULL,
            plan_hash TEXT NOT NULL, response TEXT NOT NULL, file_hashes TEXT NOT NULL,
            PRIMARY KEY(turn_id,result_version,plan_hash))""")

    def open_product_workflow(self, payload):
        """One product-name request, empty-catalog compatible, measured from entry."""
        obj(payload, ("question", "user_submitted"), ("session_id", "request_key", "budget_seconds", "prior_turn_id"))
        from .contracts import integer
        integer(payload.get("budget_seconds", 1800), "budget_seconds", 300, 1800)
        from .workflow import WorkflowAudit
        audit = WorkflowAudit(self.store.db, self.workspace)
        with self.store.transaction():
            if payload.get("session_id") and payload.get("request_key"):
                existing = self.store.db.execute("SELECT 1 FROM conversation_requests WHERE session_id=? AND request_key=?", (payload["session_id"], payload["request_key"])).fetchone()
                if existing and not audit.active(self._research_id(payload["session_id"], payload["request_key"])):
                    fail("workflow_late_start", "An older untimed request cannot be relabelled as a fresh whole-request workflow")
            response = self.open_request({k: v for k, v in payload.items() if k != "budget_seconds"})
            research = response.get("research_id")
            if not research:
                turn = response["turn"]
                research = self._research_id(turn["session_id"], turn["request_key"])
            status = audit.start(research, payload.get("budget_seconds", 1800), allow_new_bound_request=True)
        return {**response, "research_id": research,
                "workflow": status,
                "next_action": "Interpret the original product name, investigate the whole exact product, then resolve this same request; do not ask for a pain when the product is clear"}

    def record_workflow_event(self, payload):
        from .workflow import WorkflowAudit
        if "data_path" in payload:
            obj(payload, ("research_id", "event_key", "kind", "data_path"))
            payload = {k: v for k, v in payload.items() if k != "data_path"} | {"data": self._read_report_plan(payload["data_path"])}
        with self.store.transaction():
            audit = WorkflowAudit(self.store.db, self.workspace)
            if payload.get("kind") == "finish":
                request = audit.request(payload["research_id"])
                if request[2] is not None:
                    turn = self.store.get_turn(request[0], request[2])
                    if not turn["valid"] or turn["latest_result"] is None:
                        fail("workflow_delivery_missing", "Finish requires the current fresh saved result")
                audit.check_catalog(payload["research_id"], self.store.dataset)
            return audit.record(payload, self.store.dataset)

    def workflow_status(self, payload):
        obj(payload, ("research_id",))
        from .workflow import WorkflowAudit
        audit = WorkflowAudit(self.store.db, self.workspace)
        audit.request(payload["research_id"])
        return audit.status(payload["research_id"])

    def set_request_scope_policy(self, payload):
        obj(payload, ("session_id", "request_key", "policy"))
        from .selection import SelectionPolicy
        with self.store.transaction():
            return SelectionPolicy(self.store.db).set(payload["session_id"], payload["request_key"], payload["policy"])

    def open_request_bundle(self, payload):
        """Open the same request and return exact local sources once, with bounds.

        No source sufficiency decision or model call happens here. Replaying a
        handle retains the existing state, including stale/terminal/exhausted.
        """
        response = self.open_request(payload)
        return self._bundle(response)

    def resolve_request_bundle(self, payload):
        return self._bundle(self.resolve_request(payload))

    def _bundle(self, response):
        if "turn" not in response:
            return response
        turn = response["turn"]
        if not turn["valid"] or turn["status"] in ("failed", "cancelled") or turn["result_version"] >= 3:
            return {**response, "previous": None, "bundle": None,
                    "bundle_unavailable": "stale/terminal/exhausted; preserve this handle and state, no new turn"}
        previous = response.get("previous")
        if previous:
            previous = {k: previous[k] for k in ("turn_id", "status", "use", "valid_for_current_context") if k in previous}
            previous["detail_operation"] = "get_turn/export_session; historical only"
        scopes = turn["input"]["model_scope"]
        scope = scopes[0] if len(scopes) == 1 else None
        bundle = {"data_version": self.store.dataset.version, "dataset_fingerprint": self.store.dataset.fingerprint,
                  "scope": scope, "model_scope": scopes, "scope_mode": turn["input"].get("scope_mode", "exact_model"),
                  "coverage": "catalog_cases_only", "synthetic": self.store.dataset.synthetic, "purpose": self.store.dataset.manifest["purpose"],
                  "semantic_status": "unverified", "content_trust": "untrusted_source_data",
                  "records": [], "evidence_refs": [], "retrieval": {}, "byte_truncated": False}
        for kind in ("review", "product_fact"):
            found_by_scope = [self.store.retrieve(kind, exact, limit=max(1, 20 // len(scopes))) for exact in scopes]
            bundle["retrieval"][kind] = ({k: found_by_scope[0][k] for k in ("status", "total", "truncated", "cache_hit")}
                if len(scopes) == 1 else {"per_scope": [{"scope": found["scope"], **{k: found[k] for k in ("status", "total", "truncated", "cache_hit")}} for found in found_by_scope],
                    "total": sum(f["total"] for f in found_by_scope), "truncated": any(f["truncated"] for f in found_by_scope),
                    "counts_are": "source records, not independent customers"})
            for found in found_by_scope:
                for record in found["records"]:
                    bundle["records"].append({k: record[k] for k in ("source_id", "kind", "model_id", "model_version", "document_version", "feature_key", "availability") if k in record})
                    bundle["evidence_refs"].append(self.store.dataset.reference(record))
        value = {"reused_request": response["reused_request"], "turn": turn, "previous": previous, "bundle": bundle,
                 "candidate_template": candidate_template(turn),
                 "result_limits": {"concepts": turn["input"]["constraints"]["max_concepts"],
                                   "claims_per_section": 20, "concept_requirements": 10,
                                   "concept_assumptions": 10, "implementation_steps": 8,
                                   "decision_notes": 10, "decision_source_ids": 20,
                                   "result_bytes": MAX_RESULT_BYTES,
                                   "template_status": "blank_invalid_until_authored",
                                   "semantic_status": "unverified"}}
        # Leave headroom for the CLI envelope; never hide a committed handle due
        # to large sources. The omitted IDs remain visible for targeted retrieval.
        while len(canonical(value).encode("utf-8")) > 60000 and bundle["evidence_refs"]:
            bundle["evidence_refs"].pop()
            bundle["byte_truncated"] = True
        if len(canonical(value).encode("utf-8")) > 60000:
            turn["latest_result"] = None
            turn["latest_result_omitted"] = "current_request/get_turn; response byte budget"
        bundle["included_source_ids"] = [r["source_id"] for r in bundle["evidence_refs"]]
        bundle["omitted_source_ids"] = [r["source_id"] for r in bundle["records"] if r["source_id"] not in bundle["included_source_ids"]]
        # At most 40 IDs; limit the whole envelope, not just individual quotes.
        while len(canonical(value).encode("utf-8")) > 63000 and bundle["evidence_refs"]:
            removed = bundle["evidence_refs"].pop()["source_id"]
            bundle["included_source_ids"].remove(removed)
            bundle["omitted_source_ids"].append(removed)
            bundle["byte_truncated"] = True
        from .evidence_coverage import EvidenceCoverage
        EvidenceCoverage(self.store).delivered(turn["session_id"], turn["turn_id"], bundle["evidence_refs"],
                                               "bundle-" + fingerprint([turn["context_fingerprint"], bundle["evidence_refs"]]))
        return value

    def evidence_inventory(self, payload):
        from .evidence_coverage import EvidenceCoverage
        return EvidenceCoverage(self.store).evidence_inventory(payload)

    def read_evidence_batch(self, payload):
        from .evidence_coverage import EvidenceCoverage
        return EvidenceCoverage(self.store).read_evidence_batch(payload)

    def record_evidence_review(self, payload):
        from .evidence_coverage import EvidenceCoverage
        return EvidenceCoverage(self.store).record_evidence_review(payload)

    def evidence_coverage(self, payload):
        from .evidence_coverage import EvidenceCoverage
        return EvidenceCoverage(self.store).evidence_coverage(payload)

    def historical(self, session_id, turn_id):
        state = self.store.get_turn(session_id, turn_id)
        latest = self.store.db.execute("SELECT payload,validation_json FROM results WHERE turn_id=? ORDER BY result_version DESC LIMIT 1", (turn_id,)).fetchone()
        return {"turn_id": turn_id, "status": state["status"], "valid_before_request": state["valid"],
                "use": "historical_reference_only; recheck changed conditions and citations",
                "input": state["input"], "result": strict_json(latest[0]) if latest else None,
                "validation": {k: v for k, v in strict_json(latest[1]).items() if k not in ("assessment", "review")} if latest else None}

    def open_request(self, payload):
        # Initial row and pending/bound state must be one snapshot too: a
        # research writer cannot commit between INSERT and initial _pending.
        with self.store.transaction():
            return self._open_request(payload)

    def _open_request(self, payload):
        obj(payload, ("question", "user_submitted"), ("model_id", "product_family", "scope_mode", "model_version", "document_version", "session_id", "request_key", "prior_turn_id", "constraints", "runtime"))
        text(payload["question"], "question")
        if payload["user_submitted"] is not True:
            fail("user_input_required", "Only a real user question creates a request; resume with current_request")
        session = identifier(payload.get("session_id", "session-" + uuid.uuid4().hex), "session_id")
        key = identifier(payload.get("request_key", "request-" + uuid.uuid4().hex), "request_key")
        if "prior_turn_id" in payload and "session_id" not in payload:
            fail("invalid_input", "A follow-up must preserve its session_id")
        if "prior_turn_id" in payload:
            identifier(payload["prior_turn_id"], "prior_turn_id")
        previous = self.historical(session, payload["prior_turn_id"]) if "prior_turn_id" in payload else None
        request = {**payload, "session_id": session, "request_key": key}
        raw = canonical(request)
        with self.store.transaction():
            old = self.store.db.execute("SELECT payload,turn_id,response FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
            if old and old[0] != raw:
                fail("request_conflict", "The same request handle has changed input")
            if not old:
                self.store.db.execute("INSERT INTO conversation_requests(session_id,request_key,payload) VALUES(?,?,?)", (session, key, raw))
                from .selection import SelectionPolicy
                SelectionPolicy(self.store.db).initialize(session, key, request)
        if old and old[1]:
            # A completed follow-up can have two near-limit results. Resuming needs
            # the current result only; keep the prior turn as a historical handle.
            prior_handle = ({k: previous[k] for k in ("turn_id", "status", "use")}
                            | {"valid_for_current_context": self.store.get_turn(session, previous["turn_id"])["valid"]}) if previous else None
            return {"reused_request": True, "turn": self.store.get_turn(session, old[1]), "previous": prior_handle}
        if old and old[2]:
            return self.current_request({"session_id": session, "request_key": key})
        return self._bind_request(session, key, payload, previous)

    def _bind_request(self, session, key, payload, previous):
        prior_input = previous["input"] if previous else {}
        family = payload.get("product_family", prior_input.get("product_family"))
        prior_family_mode = prior_input.get("scope_mode") == "family_catalog"
        family_mode = (payload["scope_mode"] == "family_catalog" if "scope_mode" in payload else
                       "model_id" not in payload and ("product_family" in payload or prior_family_mode))
        if payload.get("scope_mode") not in (None, "family_catalog", "exact_model"):
            fail("invalid_input", "Unknown scope_mode")
        model = payload.get("model_id")
        if not family_mode and model is None and "product_family" not in payload:
            model = prior_input.get("model_scope", [{}])[0].get("model_id") if not prior_family_mode else None
        prepared = {"session_id": session, "request_key": key, "question": payload["question"]}
        if family_mode:
            prepared.update(product_family=family, scope_mode="family_catalog")
            if "model_id" in payload or any(k in payload for k in ("model_version", "document_version")):
                fail("invalid_input", "Family range and exact model/version selection conflict")
            if previous and prior_family_mode and family == prior_input["product_family"]:
                prepared["model_scope"] = prior_input["model_scope"]
        elif model:
            prepared.update(model_id=model, scope_mode="exact_model")
            if "product_family" in payload:
                prepared["product_family"] = family
        else:
            return self._pending(session, key, "needs_input", "product_required", "Ask which product family or exact model is meant; a family request does not require a model code")
        if "constraints" in payload or "constraints" in prior_input:
            prepared["constraints"] = payload.get("constraints", prior_input.get("constraints"))
        if "runtime" in payload:
            prepared["runtime"] = payload["runtime"]
        version_keys = ("model_version", "document_version")
        prepared.update({k: payload[k] for k in version_keys if k in payload})
        if previous and not family_mode and not any(k in payload for k in version_keys):
            matching_scopes = [s for s in prior_input["model_scope"] if s["model_id"] == model]
            if len(matching_scopes) == 1:
                prepared.update({k: matching_scopes[0][k] for k in version_keys})
        # Hash maintained workflow files, never fill unknown model/settings with guesses.
        root = self.workspace
        workflow_files = [root / "skills/manifest.json", root / "agents/product-planning.md"]
        prompt = (root / "AGENTS.md") if (root / "product-install.json").exists() else root / "agents/product-planning.md"
        prepared["workflow"] = {"rules_version": "product-contract-v1", "skill_fingerprint": hashlib.sha256(b"".join(p.read_bytes() for p in workflow_files)).hexdigest(), "prompt_fingerprint": hashlib.sha256(prompt.read_bytes()).hexdigest()}
        try:
            planning = self.store.tools.prepare_planning_input(prepared)["input"]
        except Exception as exc:
            from .contracts import ToolError
            if not isinstance(exc, ToolError) or exc.code not in ("unknown_model", "unknown_scope", "needs_input", "research_required"):
                raise
            status = "needs_input" if exc.code == "needs_input" else "research_required"
            return self._pending(session, key, status, exc.code, str(exc))
        if previous:
            planning["context"] += " Previous turn " + previous["turn_id"] + " is historical reference; recheck user conditions."
        from .selection import SelectionPolicy
        scopes = planning["model_scope"]
        models = [m for m in self.store.dataset.models if any(all(m[k] == s[k] for k in s) for s in scopes)]
        SelectionPolicy(self.store.db).check(SelectionPolicy(self.store.db).get(session, key), models, self.store.dataset.sources.values(), self.store.dataset.synthetic)
        turn = self.store.start_turn(planning, True)
        if previous:
            previous["valid_for_current_context"] = self.store.get_turn(session, previous["turn_id"])["valid"]
        with self.store.transaction():
            self.store.db.execute("UPDATE conversation_requests SET turn_id=? WHERE session_id=? AND request_key=?", (turn["turn_id"], session, key))
        return {"reused_request": turn["reused_request"], "turn": turn, "previous": previous}

    def _pending(self, session, key, status, code, reason):
        from .selection import SelectionPolicy
        version = self.store.db.execute("SELECT request_version FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()[0]
        response = {"session_id": session, "request_key": key, "research_id": self._research_id(session, key), "request_version": version, "turn_id": None, "status": status, "reason": {"code": code, "message": reason}, "semantic_status": "unverified", "selection_policy": SelectionPolicy(self.store.db).get(session, key)}
        with self.store.transaction():
            self.store.db.execute("UPDATE conversation_requests SET response=? WHERE session_id=? AND request_key=?", (canonical(response), session, key))
        return response

    @staticmethod
    def _research_id(session, key):
        return "research-" + hashlib.sha256(canonical([session, key]).encode("utf-8")).hexdigest()

    def _event(self, payload, kind, action):
        session, key, event = (identifier(payload[k], k) for k in ("session_id", "request_key", "event_key"))
        integer(payload["expected_request_version"], "expected_request_version", low=0)
        raw = canonical(payload)
        with self.store.transaction():
            row = self.store.db.execute("SELECT * FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
            if not row:
                fail("request_not_found", "Unknown conversation request")
            old = self.store.db.execute("SELECT kind,payload FROM request_events WHERE session_id=? AND request_key=? AND event_key=?", (session, key, event)).fetchone()
            if old:
                if old[0] != kind or old[1] != raw:
                    fail("request_conflict", "Event key reused with different content")
                return self.current_request({"session_id": session, "request_key": key})
            if row["turn_id"]:
                fail("request_already_bound", "Use the existing turn; resolution cannot reset data or revision limits")
            if row["request_version"] != payload["expected_request_version"]:
                fail("request_version_conflict", "Reread current_request before changing this request")
            version = row["request_version"] + 1
            self.store.db.execute("INSERT INTO request_events VALUES(?,?,?,?,?,?)", (session, key, event, version, kind, raw))
            self.store.db.execute("UPDATE conversation_requests SET request_version=? WHERE session_id=? AND request_key=?", (version, session, key))
            return action(session, key, strict_json(row["payload"]))

    def record_request_research(self, payload):
        obj(payload, ("session_id", "request_key", "event_key", "expected_request_version", "status", "reason", "observation_refs"))
        if payload["status"] not in ("research_required", "researching", "held", "needs_input", "failed"):
            fail("invalid_input", "Unknown research status")
        text(payload["reason"], "reason")
        if not isinstance(payload["observation_refs"], list) or len(payload["observation_refs"]) > 20:
            fail("invalid_input", "observation_refs must be a bounded list of observed snapshot IDs")
        for ref in payload["observation_refs"]:
            identifier(ref, "observation_ref")
        # This journal does not invent API usage. Full native session counters
        # must be attached by the evaluator; exports mark this gap explicitly.
        return self._event(payload, "research", lambda s, k, original: self._pending(s, k, payload["status"], "research_observation", payload["reason"]))

    def resolve_request(self, payload):
        obj(payload, ("session_id", "request_key", "event_key", "expected_request_version", "selection"))
        obj(payload["selection"], (), ("model_id", "product_family", "scope_mode", "model_version", "document_version"))
        def bind(session, key, original):
            from .workflow import WorkflowAudit
            audit = WorkflowAudit(self.store.db, self.workspace)
            audit.require_stopped(self._research_id(session, key))
            audit.check_catalog(self._research_id(session, key), self.store.dataset)
            selection = payload["selection"]
            # Selection supplements the AI interpretation; never rewrite the
            # user's original question, constraints, runtime or follow-up link.
            for field in ("model_id", "product_family", "scope_mode", "model_version", "document_version"):
                if field in original and field in selection and original[field] != selection[field]:
                    fail("request_conflict", "Resolution contradicts an explicit original selection")
            merged = {**original, **selection}
            previous = self.historical(session, original["prior_turn_id"]) if "prior_turn_id" in original else None
            return self._bind_request(session, key, merged, previous)
        return self._event(payload, "resolution", bind)

    def current_request(self, payload):
        obj(payload, ("session_id", "request_key"))
        session, key = (identifier(payload[k], k) for k in ("session_id", "request_key"))
        row = self.store.db.execute("SELECT turn_id,response,request_version FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
        if not row:
            fail("request_not_found", "Unknown conversation request")
        if row[0]:
            return {"turn": self.store.get_turn(session, row[0]), "reused_request": True, "request_version": row[2], "research_id": self._research_id(session, key)}
        value = strict_json(row[1]) if row[1] else {"session_id": session, "request_key": key, "status": "pending", "turn_id": None}
        return {**value, "request_version": row[2], "research_id": self._research_id(session, key)}

    def export_session(self, payload):
        # Binding and history must describe one snapshot, including when the
        # web payload is written after this export by save_and_export.
        with self.store.transaction():
            return self._export_session(payload)

    def _export_session(self, payload):
        obj(payload, ("session_id",))
        session = identifier(payload["session_id"], "session_id")
        requests = list(self.store.db.execute("SELECT * FROM conversation_requests WHERE session_id=?", (session,)))
        turns = list(self.store.db.execute("SELECT * FROM turns WHERE session_id=? ORDER BY created_at,turn_id", (session,)))
        if not requests and not turns:
            fail("session_not_found", "Unknown business session")
        histories = []
        for row in turns:
            histories.append({"state": self.store.get_turn(session, row["turn_id"]),
                              "candidates": [{"result_key": r["result_key"], "result_version": r["result_version"], "result": strict_json(r["payload"]), "validation": strict_json(r["validation_json"])} for r in self.store.db.execute("SELECT * FROM results WHERE turn_id=? ORDER BY result_version", (row["turn_id"],))],
                              "usage": [strict_json(r[0]) for r in self.store.db.execute("SELECT payload FROM usage WHERE turn_id=?", (row["turn_id"],))],
                              "invocations": [dict(r) for r in self.store.db.execute("SELECT * FROM invocations WHERE turn_id=?", (row["turn_id"],))]})
            for candidate in histories[-1]["candidates"]:
                candidate["source_metadata"] = self._source_metadata(candidate["result"].get("evidence_refs", []))
            latest = histories[-1]["state"].get("latest_result")
            histories[-1]["source_metadata"] = self._source_metadata(latest.get("evidence_refs", []) if latest else [])
            from .evidence_coverage import EvidenceCoverage
            histories[-1]["evidence_coverage_history"] = EvidenceCoverage(self.store).history(row["turn_id"])
            from .workflow import WorkflowAudit
            state = histories[-1]["state"]
            audit = WorkflowAudit(self.store.db, self.workspace)
            research = self._research_id(session, state["request_key"])
            histories[-1]["web_binding"] = {
                "session_id": session, "turn_id": state["turn_id"], "request_key": state["request_key"],
                "result_version": state["result_version"], "result_sha256": fingerprint(latest) if latest else None,
                "context_sha256": state["context_fingerprint"], "code_sha256": self.store.code_hash,
                "data_sha256": self.store.dataset.fingerprint, "data_version": self.store.dataset.version,
                "workflow_audit_hash": audit.report_audit_hash(research) if audit.active(research) else None}
        value = {"session_id": session, "requests": [{"input": strict_json(r["payload"]), "turn_id": r["turn_id"], "request_version": r["request_version"], "response": strict_json(r["response"]) if r["response"] else None,
                 "events": [{"kind": e["kind"], "version": e["version"], "input": strict_json(e["payload"])} for e in self.store.db.execute("SELECT * FROM request_events WHERE session_id=? AND request_key=? ORDER BY version", (session, r["request_key"]))],
                 "research_usage": {"status": "unknown", "coverage": "not measured by request journal; native session evidence required"}} for r in requests],
                 "turns": histories, "usage_summary": self.store.usage_summary(session), "semantic_status": "unverified", "acceptance_ready": False}
        from .workflow import WorkflowAudit
        audit = WorkflowAudit(self.store.db, self.workspace)
        for request in value["requests"]:
            from .selection import SelectionPolicy
            request["selection_policy"] = SelectionPolicy(self.store.db).get(session, request["input"]["request_key"])
            research = self._research_id(session, request["input"]["request_key"])
            if audit.active(research):
                request["workflow"] = audit.status(research)
                request["workflow_events"] = audit.events(research)
        raw = canonical(value).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        base = (self.workspace / "runtime-data/exports").resolve()
        if not base.is_relative_to(self.workspace / "runtime-data"):
            fail("invalid_path", "Exports must stay in runtime-data")
        base.mkdir(parents=True, exist_ok=True)
        # Logical identifiers may contain ':'. Never put them in an OS filename:
        # Windows interprets that syntax as an alternate data stream, lost by ZIP.
        # The canonical body includes session_id, so the content digest binds it.
        path = base / ("export-" + digest + ".json")
        path.write_bytes(raw)
        return {"path": path.relative_to(self.workspace).as_posix(), "sha256": digest, "turn_count": len(turns), "request_count": len(requests), "usage_summary": value["usage_summary"], "semantic_status": "unverified"}

    def _source_metadata(self, references):
        # Saved result/reference bytes stay immutable; types are a separate join.
        result = []
        if not isinstance(references, list):
            return [{"kind": None, "binding": "invalid_reference_list"}]
        keys = ("source_id", "model_id", "model_version", "document_version", "data_version", "sha256")
        for index, ref in enumerate(references):
            if not isinstance(ref, dict) or any(k not in ref for k in keys) or not isinstance(ref["source_id"], str):
                result.append({"reference_index": index, "kind": None, "binding": "invalid_reference"})
                continue
            source = self.store.dataset.sources.get(ref["source_id"])
            matched = bool(source and self.store.dataset.reference(source) == ref)
            result.append({**{k: ref[k] for k in keys},
                           "reference_fingerprint": fingerprint(ref),
                           "kind": source["kind"] if matched else None,
                           "binding": "exact_current_catalog_reference" if matched else "historical_or_unavailable"})
        return result

    def save_and_export(self, payload):
        """One mechanical roundtrip. Rejections/history persist before export.

        Export failure cannot roll back a stored candidate. A caller can recover
        with current_request/export_session; a stale replay is never delivered.
        """
        fields = ("session_id", "turn_id", "result_key", "result", "expected_result_version", "assessment")
        obj(payload, fields, ("report", "report_plan_path", "report_sources_path", "open_folder"))
        options = self._report_options(payload)
        saved = self.store.save_result(**{k: payload[k] for k in fields}, require_review=True, response_mode="receipt")
        receipt = saved["receipt"]
        latest = (receipt["candidate_result_version"] == receipt["current_result_version"]
                  and receipt["candidate_result_version"] is not None and receipt["valid"] is True)
        response = {"save": saved, "delivery_ready": saved["accepted"] is True and latest, "export": None, "export_error": None}
        # Include rejected candidates too, so exhaustion/held final retains proof.
        try:
            # One SQLite snapshot across export and the final read. get_turn has
            # several SELECTs; an interleaving writer must not mix their versions.
            with self.store.transaction():
                response["export"] = self.export_session({"session_id": payload["session_id"]})
                current = self.store.get_turn(payload["session_id"], payload["turn_id"])
                if current["result_version"] != receipt["current_result_version"] or current["valid"] is not True or current["status"] != receipt["status"]:
                    response.update(delivery_ready=False, export_error={"code": "current_state_changed", "message": "Reread current_request/get_turn; exported history is preserved"})
        except (OSError, ValueError) as exc:
            response.update(delivery_ready=False, export_error={"code": "export_failed", "message": str(exc)[:512]})
        if options["report"]:
            response.update(report=None, report_ready=False, report_error=None)
            if response["delivery_ready"]:
                report = self._deliver_current(payload["session_id"], payload["turn_id"], receipt["current_result_version"], options)
                response.update(report=report, report_ready=report["ready"], report_error=report.get("error"))
        else:
            response.update(web_result=None, web_ready=False, web_error=None)
            if response["delivery_ready"]:
                try:
                    response["web_result"] = self.prepare_web_result({"session_id": payload["session_id"],
                        "turn_id": payload["turn_id"], "expected_result_version": receipt["current_result_version"]})
                    response["web_ready"] = response["web_result"]["ready"]
                except (OSError, ValueError, sqlite3.Error) as exc:
                    response["web_error"] = {"code": getattr(exc, "code", "web_delivery_failed"), "message": str(exc)[:512]}
        from .workflow import WorkflowAudit
        audit = WorkflowAudit(self.store.db, self.workspace)
        keys = self.store.db.execute("SELECT request_key FROM conversation_requests WHERE session_id=? AND turn_id=?", (payload["session_id"], payload["turn_id"])).fetchall()
        if len(keys) == 1:
            research = self._research_id(payload["session_id"], keys[0][0])
            if audit.active(research):
                response["workflow"] = audit.status(research)
                from .workflow import utc_now
                response["workflow_file_confirmation_at"] = utc_now().isoformat()
                response["workflow_files_within_budget"] = bool((response.get("report_ready") or response.get("web_ready")) and utc_now() <= datetime.fromisoformat(response["workflow"]["deadline"]))
        response.update(completion_summary=None, completion_error=None)
        if response["delivery_ready"]:
            try:
                response["completion_summary"] = self.get_completion_summary({"session_id": payload["session_id"],
                    "turn_id": payload["turn_id"], "expected_result_version": receipt["current_result_version"]})
            except (OSError, ValueError, sqlite3.Error) as exc:
                response["completion_error"] = {"code": getattr(exc, "code", "completion_failed"), "message": str(exc)[:512]}
        if response["completion_summary"] and len(canonical(response).encode("utf-8")) > MAX_BYTES:
            response["completion_summary"].pop("text", None)
            response["completion_summary"].update(text_omitted=True, detail_operation="get_completion_summary")
        return response

    def get_completion_summary(self, payload):
        from .completion import CompletionSummary
        return CompletionSummary(self.store, self.workspace).get_completion_summary(payload)

    def prepare_web_result(self, payload):
        from .web_delivery import WebDelivery
        return WebDelivery(self.store, self.workspace).prepare_web_result(payload)

    def _report_options(self, payload, recovery=False):
        report = payload.get("report", recovery)
        open_folder = payload.get("open_folder", True)
        if type(report) is not bool or type(open_folder) is not bool:
            fail("invalid_input", "report and open_folder must be booleans")
        if payload.get("report_plan_path") is not None:
            text(payload["report_plan_path"], "report_plan_path", 4096)
            if not report:
                fail("invalid_input", "report_plan_path requires report:true")
        if payload.get("report_sources_path") is not None:
            text(payload["report_sources_path"], "report_sources_path", 4096)
            if not report:
                fail("invalid_input", "report_sources_path requires report:true")
        return {"report": report, "open_folder": open_folder, "report_plan_path": payload.get("report_plan_path"),
                "report_sources_path": payload.get("report_sources_path")}

    def _read_report_plan(self, name):
        if name is None:
            return None
        path = Path(name)
        path = real_path(path if path.is_absolute() else self.workspace / path)
        allowed = (self.workspace / "runtime-data").resolve()
        if not allowed.is_relative_to(self.workspace) or not path.is_relative_to(allowed) or not path.is_file():
            fail("invalid_path", "Authored report plans must be files inside this workspace's runtime-data")
        # Report length has a separate, generous mechanical bound; the business
        # result's 256 KiB stdin limit is never applied to a report plan.
        if path.stat().st_size > 16 * 1024 * 1024:
            fail("report_plan_limit", "Authored report plan exceeds 16 MiB")
        return strict_json(path.read_text(encoding="utf-8-sig"))

    def _report_hashes(self, response):
        base = (self.workspace / "runtime-data/deliverables").resolve()
        if not base.is_relative_to(self.workspace):
            fail("invalid_path", "Reader files must stay inside this workspace")
        hashes = {}
        for item in response.get("files", []):
            path = Path(item["path"])
            path = real_path(path if path.is_absolute() else self.workspace / path)
            if not path.is_relative_to(base) or not path.is_file():
                fail("invalid_path", "Reader files must stay in runtime-data/deliverables")
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        if not hashes:
            fail("report_failed", "Renderer returned ready without reader files")
        return hashes

    def _read_report_sources(self, name, session, turn):
        if name is None:
            return []
        payload = self._read_report_plan(name)
        rows = self.store.db.execute("SELECT request_key FROM conversation_requests WHERE session_id=? AND turn_id=?", (session, turn)).fetchall()
        if len(rows) != 1:
            fail("report_source_scope", "Context requires the unique original request linked to this turn")
        from .web_evidence import WebEvidence
        web = WebEvidence(self.store.path, self.workspace)
        try:
            return web.report_sources(payload, self._research_id(session, rows[0][0]))
        finally:
            web.close()

    def _report_plan_hash(self, authored, context_sources=None, workflow_events=None):
        if authored is not None:
            if not isinstance(authored, dict) or not isinstance(authored.get("sections"), list):
                fail("invalid_report_plan", "Authored report must contain a sections array")
            for section in authored["sections"]:
                if not isinstance(section, dict) or not isinstance(section.get("blocks"), list):
                    fail("invalid_report_plan", "Report sections must contain block arrays")
                for block in section["blocks"]:
                    if not isinstance(block, dict):
                        fail("invalid_report_plan", "Report blocks must be objects")
                    if block.get("type") not in ("paragraph", "table", "chart"):
                        fail("invalid_report_plan", "Unknown report block")
        from .reporting import REPORTING_PROFILE
        return hashlib.sha256(canonical({"plan": authored, "context_sources": context_sources or [],
                                        "reporting_profile": REPORTING_PROFILE,
                                        "workflow_events": workflow_events or []}).encode("utf-8")).hexdigest()

    def _deliver_current(self, session, turn, version, options):
        """Bind files to a valid saved version and reuse intact output on replay.

        Rendering shares a SQLite write snapshot with current-state checks.
        A renderer error never rolls back the previously committed candidate.
        Explorer is opened only after the successful delivery receipt commits.
        """
        try:
            from .delivery import create_deliverables
            authored = self._read_report_plan(options["report_plan_path"])
            context_sources = self._read_report_sources(options.get("report_sources_path"), session, turn)
            from .workflow import WorkflowAudit
            audit = WorkflowAudit(self.store.db, self.workspace)
            request_keys = self.store.db.execute("SELECT request_key FROM conversation_requests WHERE session_id=? AND turn_id=?", (session, turn)).fetchall()
            if len(request_keys) == 1:
                research = self._research_id(session, request_keys[0][0])
                if audit.active(research):
                    context_sources += audit.review_sources(research)
            audit_events = [e for e in audit.events(research) if e["kind"] in ("research_plan", "source_scan", "research_stop", "analysis_scope")] if len(request_keys) == 1 and audit.active(research) else []
            plan_hash = self._report_plan_hash(authored, context_sources, audit_events)
            reused = False
            with self.store.transaction():
                current = self.store.get_turn(session, turn)
                if current["result_version"] != version or not current["valid"] or current["status"] not in ("completed", "held", "needs_input") or current["latest_result"] is None:
                    fail("current_state_changed", "Reader generation requires the current valid, reviewed saved result")
                validation = strict_json(self.store.db.execute(
                    "SELECT validation_json FROM results WHERE turn_id=? ORDER BY result_version DESC LIMIT 1",
                    (turn,)).fetchone()[0])
                if (validation.get("review_required") is not True
                        or not isinstance(validation.get("assessment"), dict)
                        or validation.get("review", {}).get("can_finalize_reported_result") is not True):
                    fail("reader_review_required", "Reader delivery requires the stored reviewed-result contract; structural save alone is insufficient")
                cached = self.store.db.execute("SELECT response,file_hashes FROM reader_deliveries WHERE turn_id=? AND result_version=? AND plan_hash=?", (turn, version, plan_hash)).fetchone()
                if cached:
                    response = strict_json(cached["response"])
                    try:
                        intact = self._report_hashes(response) == strict_json(cached["file_hashes"])
                    except (OSError, ValueError, KeyError):
                        intact = False
                    if intact:
                        reused = True
                if not reused:
                    scopes = current["input"]["model_scope"]
                    sources = [self.store.dataset.source(s["source_id"]) for s in self.store.dataset.sources.values()
                               if any(all(s[k] == scope[k] for k in ("model_id", "model_version", "document_version")) for scope in scopes)]
                    if len(request_keys) == 1 and audit.active(research):
                        from .delivery import build_report_plan
                        authored = build_report_plan(current["input"], current["latest_result"], sources + context_sources, authored)
                        authored["sections"].insert(0, audit.report_section(research, self.store.dataset))
                    response = create_deliverables(self.workspace, current["input"], current["latest_result"], sources + context_sources,
                                                   authored_plan=authored, open_folder=False)
                    if len(request_keys) == 1 and audit.active(research):
                        response["workflow_audit_hash"] = audit.report_audit_hash(research)
                    if response.get("ready") is not True:
                        return {**response, "ready": False, "error": response.get("error") or {"code": "report_failed", "message": "Reader files were not generated; see checks"}}
                    after = self.store.get_turn(session, turn)
                    if after["result_version"] != version or not after["valid"] or after["status"] != current["status"]:
                        fail("current_state_changed", "Saved state changed during reader generation; generated files are historical only")
                    hashes = self._report_hashes(response)
                    response.update(result_version=version, turn_id=turn, folder_opened=False)
                    self.store.db.execute("INSERT OR REPLACE INTO reader_deliveries VALUES(?,?,?,?,?)", (turn, version, plan_hash, canonical(response), canonical(hashes)))
            response = {**response, "reused": reused}
            if not reused and options["open_folder"] and os.name == "nt":
                try:
                    subprocess.Popen(["explorer.exe", response["directory"]])
                    response["folder_opened"] = True
                except OSError as exc:
                    response["folder_open_error"] = str(exc)[:512]
            return response
        except (ImportError, OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
            return {"ready": False, "directory": None, "files": [], "checks": {"errors": [str(exc)[:512]]},
                    "error": {"code": "report_storage_error" if isinstance(exc, sqlite3.Error) else getattr(exc, "code", "report_failed"),
                              "message": str(exc)[:512], "retryable": isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower()}}

    def deliver_result(self, payload):
        """Recover reader files from a reviewed stored result without resaving it."""
        obj(payload, ("session_id", "turn_id", "expected_result_version"), ("report_plan_path", "report_sources_path", "open_folder"))
        session = identifier(payload["session_id"], "session_id")
        turn = identifier(payload["turn_id"], "turn_id")
        version = integer(payload["expected_result_version"], "expected_result_version", 1)
        return self._deliver_current(session, turn, version, self._report_options(payload, recovery=True))
