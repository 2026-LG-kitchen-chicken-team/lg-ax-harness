"""Conversation handles and historical exports. Never invokes a model/runtime."""
import hashlib
from pathlib import Path
import uuid
from .contracts import canonical, fail, identifier, obj, strict_json, text


class Conversation:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = Path(workspace).resolve()
        store.db.execute("""CREATE TABLE IF NOT EXISTS conversation_requests(
            session_id TEXT NOT NULL, request_key TEXT NOT NULL, payload TEXT NOT NULL,
            turn_id TEXT, response TEXT, PRIMARY KEY(session_id,request_key))""")

    def open_request_bundle(self, payload):
        """Open the same request and return exact local sources once, with bounds.

        No source sufficiency decision or model call happens here. Replaying a
        handle retains the existing state, including stale/terminal/exhausted.
        """
        response = self.open_request(payload)
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
        scope = turn["input"]["model_scope"][0]
        bundle = {"data_version": self.store.dataset.version, "dataset_fingerprint": self.store.dataset.fingerprint,
                  "scope": scope, "synthetic": self.store.dataset.synthetic, "purpose": self.store.dataset.manifest["purpose"],
                  "semantic_status": "unverified", "content_trust": "untrusted_source_data",
                  "records": [], "evidence_refs": [], "retrieval": {}, "byte_truncated": False}
        for kind in ("review", "product_fact"):
            found = self.store.retrieve(kind, scope, limit=20)
            bundle["retrieval"][kind] = {k: found[k] for k in ("status", "total", "truncated", "cache_hit")}
            for record in found["records"]:
                bundle["records"].append({k: record[k] for k in ("source_id", "kind", "feature_key", "availability") if k in record})
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
        obj(payload, ("question", "user_submitted"), ("model_id", "model_version", "document_version", "session_id", "request_key", "prior_turn_id", "constraints", "runtime"))
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
                self.store.db.execute("INSERT INTO conversation_requests VALUES(?,?,?,NULL,NULL)", (session, key, raw))
        if old and old[1]:
            # A completed follow-up can have two near-limit results. Resuming needs
            # the current result only; keep the prior turn as a historical handle.
            prior_handle = ({k: previous[k] for k in ("turn_id", "status", "use")}
                            | {"valid_for_current_context": self.store.get_turn(session, previous["turn_id"])["valid"]}) if previous else None
            return {"reused_request": True, "turn": self.store.get_turn(session, old[1]), "previous": prior_handle}
        if old and old[2]:
            return strict_json(old[2])
        prior_input = previous["input"] if previous else {}
        model = payload.get("model_id", prior_input.get("model_scope", [{}])[0].get("model_id"))
        if not model:
            return self._pending(session, key, "needs_input", "model_required", "Ask for an exact refrigerator model; do not request internal IDs")
        prepared = {"model_id": model, "session_id": session, "request_key": key, "question": payload["question"]}
        if "constraints" in payload or "constraints" in prior_input:
            prepared["constraints"] = payload.get("constraints", prior_input.get("constraints"))
        if "runtime" in payload:
            prepared["runtime"] = payload["runtime"]
        version_keys = ("model_version", "document_version")
        prepared.update({k: payload[k] for k in version_keys if k in payload})
        if previous and model == prior_input["model_scope"][0]["model_id"] and not any(k in payload for k in version_keys):
            prepared.update({k: prior_input["model_scope"][0][k] for k in ("model_version", "document_version")})
        # Hash maintained workflow files, never fill unknown model/settings with guesses.
        root = self.workspace
        workflow_files = [root / "skills/manifest.json", root / "agents/product-planning.md"]
        prompt = (root / "AGENTS.md") if (root / "product-install.json").exists() else root / "agents/product-planning.md"
        prepared["workflow"] = {"rules_version": "product-contract-v1", "skill_fingerprint": hashlib.sha256(b"".join(p.read_bytes() for p in workflow_files)).hexdigest(), "prompt_fingerprint": hashlib.sha256(prompt.read_bytes()).hexdigest()}
        try:
            planning = self.store.tools.prepare_planning_input(prepared)["input"]
        except Exception as exc:
            from .contracts import ToolError
            if not isinstance(exc, ToolError) or exc.code not in ("unknown_model", "unknown_scope", "needs_input"):
                raise
            return self._pending(session, key, "needs_input", exc.code, str(exc))
        if previous:
            planning["context"] += " Previous turn " + previous["turn_id"] + " is historical reference; recheck user conditions."
        turn = self.store.start_turn(planning, True)
        if previous:
            previous["valid_for_current_context"] = self.store.get_turn(session, previous["turn_id"])["valid"]
        with self.store.transaction():
            self.store.db.execute("UPDATE conversation_requests SET turn_id=? WHERE session_id=? AND request_key=?", (turn["turn_id"], session, key))
        return {"reused_request": turn["reused_request"], "turn": turn, "previous": previous}

    def _pending(self, session, key, status, code, reason):
        response = {"session_id": session, "request_key": key, "turn_id": None, "status": status, "reason": {"code": code, "message": reason}, "semantic_status": "unverified"}
        with self.store.transaction():
            self.store.db.execute("UPDATE conversation_requests SET response=? WHERE session_id=? AND request_key=?", (canonical(response), session, key))
        return response

    def current_request(self, payload):
        obj(payload, ("session_id", "request_key"))
        session, key = (identifier(payload[k], k) for k in ("session_id", "request_key"))
        row = self.store.db.execute("SELECT turn_id,response FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
        if not row:
            fail("request_not_found", "Unknown conversation request")
        if row[0]:
            return {"turn": self.store.get_turn(session, row[0]), "reused_request": True}
        return strict_json(row[1]) if row[1] else {"session_id": session, "request_key": key, "status": "pending", "turn_id": None}

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
        value = {"session_id": session, "requests": [{"input": strict_json(r["payload"]), "turn_id": r["turn_id"], "response": strict_json(r["response"]) if r["response"] else None} for r in requests],
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
