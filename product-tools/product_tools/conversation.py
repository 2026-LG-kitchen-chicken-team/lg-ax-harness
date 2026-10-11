"""Conversation handles and historical exports. Never invokes a model/runtime."""
import hashlib
from pathlib import Path
import uuid
from .contracts import canonical, fail, identifier, integer, obj, strict_json, text


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
        value = {"reused_request": response["reused_request"], "turn": turn, "previous": previous, "bundle": bundle}
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
        return value

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
        previous = self.historical(session, payload["prior_turn_id"]) if "prior_turn_id" in payload else None
        request = {**payload, "session_id": session, "request_key": key}
        raw = canonical(request)
        with self.store.transaction():
            old = self.store.db.execute("SELECT payload,turn_id,response FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
            if old and old[0] != raw:
                fail("request_conflict", "The same request handle has changed input")
            if not old:
                self.store.db.execute("INSERT INTO conversation_requests(session_id,request_key,payload) VALUES(?,?,?)", (session, key, raw))
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
        turn = self.store.start_turn(planning, True)
        if previous:
            previous["valid_for_current_context"] = self.store.get_turn(session, previous["turn_id"])["valid"]
        with self.store.transaction():
            self.store.db.execute("UPDATE conversation_requests SET turn_id=? WHERE session_id=? AND request_key=?", (turn["turn_id"], session, key))
        return {"reused_request": turn["reused_request"], "turn": turn, "previous": previous}

    def _pending(self, session, key, status, code, reason):
        version = self.store.db.execute("SELECT request_version FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()[0]
        response = {"session_id": session, "request_key": key, "research_id": self._research_id(session, key), "request_version": version, "turn_id": None, "status": status, "reason": {"code": code, "message": reason}, "semantic_status": "unverified"}
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
        value = {"session_id": session, "requests": [{"input": strict_json(r["payload"]), "turn_id": r["turn_id"], "request_version": r["request_version"], "response": strict_json(r["response"]) if r["response"] else None,
                 "events": [{"kind": e["kind"], "version": e["version"], "input": strict_json(e["payload"])} for e in self.store.db.execute("SELECT * FROM request_events WHERE session_id=? AND request_key=? ORDER BY version", (session, r["request_key"]))],
                 "research_usage": {"status": "unknown", "coverage": "not measured by request journal; native session evidence required"}} for r in requests],
                 "turns": histories, "usage_summary": self.store.usage_summary(session), "semantic_status": "unverified", "acceptance_ready": False}
        raw = canonical(value).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        base = (self.workspace / "runtime-data/exports").resolve()
        if not base.is_relative_to(self.workspace / "runtime-data"):
            fail("invalid_path", "Exports must stay in runtime-data")
        base.mkdir(parents=True, exist_ok=True)
        path = base / (session + "-" + digest + ".json")
        path.write_bytes(raw)
        return {"path": path.relative_to(self.workspace).as_posix(), "sha256": digest, "turn_count": len(turns), "request_count": len(requests), "usage_summary": value["usage_summary"], "semantic_status": "unverified"}

    def save_and_export(self, payload):
        """One mechanical roundtrip. Rejections/history persist before export.

        Export failure cannot roll back a stored candidate. A caller can recover
        with current_request/export_session; a stale replay is never delivered.
        """
        obj(payload, ("session_id", "turn_id", "result_key", "result", "expected_result_version", "assessment"))
        saved = self.store.save_result(**payload, require_review=True, response_mode="receipt")
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
        return response
