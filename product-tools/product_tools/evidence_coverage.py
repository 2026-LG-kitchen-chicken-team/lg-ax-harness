"""Observed delivery and caller-reported review, bound to an immutable turn.

Counts certify neither claim support nor representative product coverage.
"""
from .contracts import canonical, fail, fingerprint, identifier, integer, obj, strict_json, text
from .state import now


class EvidenceCoverage:
    def __init__(self, store):
        self.store = store
        store.db.execute("""CREATE TABLE IF NOT EXISTS evidence_deliveries(
                turn_id TEXT NOT NULL, binding TEXT NOT NULL, delivery_key TEXT NOT NULL,
                source_id TEXT NOT NULL, source_sha256 TEXT NOT NULL, observed_at TEXT NOT NULL,
                PRIMARY KEY(turn_id,binding,delivery_key,source_id))""")
        store.db.execute("""CREATE TABLE IF NOT EXISTS evidence_reviews(
                turn_id TEXT NOT NULL, binding TEXT NOT NULL, review_key TEXT NOT NULL,
                payload TEXT NOT NULL, observed_at TEXT NOT NULL,
                PRIMARY KEY(turn_id,binding,review_key))""")

    def context(self, session_id, turn_id):
        row = self.store.row(session_id, turn_id)
        if not self.store.fresh(row):
            fail("stale_context", "Coverage cannot be reused after data/code/context invalidation")
        if row["status"] in ("cancelled", "failed"):
            fail("terminal_turn", "Cancelled/failed turns cannot accept evidence delivery or review")
        planning = strict_json(row["input_json"])
        scopes = {canonical(s) for s in planning["model_scope"]}
        selected = [s for s in self.store.dataset.sources.values()
                    if canonical({k: s[k] for k in ("model_id", "model_version", "document_version")}) in scopes]
        binding = fingerprint({"session_id": session_id, "turn_id": turn_id,
                               "context_hash": row["context_hash"], "data_version": self.store.dataset.version,
                               "dataset_sha256": self.store.dataset.fingerprint, "code_sha256": self.store.code_hash,
                               "scopes": planning["model_scope"]})
        return binding, selected

    def delivered(self, session, turn, refs, delivery_key):
        binding, selected = self.context(session, turn)
        allowed = {s["source_id"]: s for s in selected}
        identifier(delivery_key, "delivery_key")
        for ref in refs:
            source = allowed.get(ref["source_id"])
            if not source or self.store.dataset.reference(source) != ref:
                fail("scope_mismatch", "Only complete matching original references count as delivered")
        with self.store.transaction():
            for ref in refs:
                self.store.db.execute("INSERT OR IGNORE INTO evidence_deliveries VALUES(?,?,?,?,?,?)",
                    (turn, binding, delivery_key, ref["source_id"], ref["sha256"], now()))
        return binding

    def read_evidence_batch(self, payload):
        obj(payload, ("session_id", "turn_id"), ("offset", "limit", "source_ids", "max_bytes"))
        session, turn = payload["session_id"], payload["turn_id"]
        binding, selected = self.context(session, turn)
        if "source_ids" in payload:
            ids = payload["source_ids"]
            if not isinstance(ids, list) or len(ids) > 1000 or any(not isinstance(sid, str) for sid in ids) or len(set(ids)) != len(ids):
                fail("invalid_input", "source_ids must be distinct IDs with at most 1000 items")
            for sid in ids:
                identifier(sid, "source_id")
            mapping = {s["source_id"]: s for s in selected}
            if any(sid not in mapping for sid in ids):
                fail("scope_mismatch", "Requested source is outside the turn's exact scopes")
            selected = [mapping[sid] for sid in ids]
        offset = integer(payload.get("offset", 0), "offset", 0, len(selected))
        limit = integer(payload.get("limit", 20), "limit", 1, 20)
        maximum = integer(payload.get("max_bytes", 60000), "max_bytes", 4096, 63000)
        refs = []
        result = {"session_id": session, "turn_id": turn, "binding": binding,
                  "data_version": self.store.dataset.version, "dataset_fingerprint": self.store.dataset.fingerprint,
                  "offset": offset, "total": len(selected), "evidence_refs": refs,
                  "next_offset": None, "byte_limited": False, "semantic_status": "unverified",
                  "content_trust": "untrusted_source_data"}
        for source in selected[offset:offset+limit]:
            refs.append(self.store.dataset.reference(source))
            result["next_offset"] = offset+len(refs) if offset+len(refs) < len(selected) else None
            if len(canonical(result).encode("utf-8")) > maximum:
                refs.pop()
                result["byte_limited"] = True
                result["next_offset"] = offset+len(refs)
                break
        if not refs and offset < len(selected):
            fail("output_limit", "One complete source exceeds this byte budget; increase max_bytes without truncating original text")
        key = "batch-" + fingerprint([binding, payload, refs])
        result["delivery_key"] = key
        # Headroom includes the eventual CLI envelope and delivery key.
        while refs and len(canonical(result).encode("utf-8")) > maximum:
            refs.pop()
            result["byte_limited"] = True
            result["next_offset"] = offset+len(refs)
        if not refs and offset < len(selected):
            fail("output_limit", "One complete source exceeds this byte budget")
        result["delivery_key"] = "batch-" + fingerprint([binding, payload, refs])
        self.delivered(session, turn, refs, result["delivery_key"])
        return result

    def record_evidence_review(self, payload):
        obj(payload, ("session_id", "turn_id", "review_key", "records"))
        session, turn = payload["session_id"], payload["turn_id"]
        binding, selected = self.context(session, turn)
        key = identifier(payload["review_key"], "review_key")
        records = payload["records"]
        if not isinstance(records, list) or not 1 <= len(records) <= 100:
            fail("invalid_input", "Review report requires 1..100 source dispositions")
        allowed = {s["source_id"] for s in selected}
        delivered = self._delivered(turn, binding)
        seen = set()
        for record in records:
            obj(record, ("source_id", "disposition", "reason"))
            sid = identifier(record["source_id"], "source_id")
            if sid in seen or sid not in allowed:
                fail("scope_mismatch", "Disposition must identify one distinct in-scope source")
            seen.add(sid)
            if record["disposition"] not in ("reviewed", "excluded"):
                fail("invalid_input", "Disposition must be reviewed or excluded")
            text(record["reason"], "review or exclusion rationale", 2000)
            if record["disposition"] == "reviewed" and sid not in delivered:
                fail("evidence_not_delivered", "Review cannot be reported before full original delivery")
        raw = canonical(payload)
        with self.store.transaction():
            old = self.store.db.execute("SELECT payload FROM evidence_reviews WHERE turn_id=? AND binding=? AND review_key=?", (turn, binding, key)).fetchone()
            if old and old[0] != raw:
                fail("review_conflict", "An immutable review key cannot replace its earlier report")
            if not old:
                self.store.db.execute("INSERT INTO evidence_reviews VALUES(?,?,?,?,?)", (turn, binding, key, raw, now()))
        return self.evidence_coverage({"session_id": session, "turn_id": turn})

    def _delivered(self, turn, binding):
        return {r[0] for r in self.store.db.execute("SELECT source_id FROM evidence_deliveries WHERE turn_id=? AND binding=?", (turn, binding))}

    def history(self, turn):
        return {"deliveries": [dict(r) for r in self.store.db.execute("SELECT * FROM evidence_deliveries WHERE turn_id=? ORDER BY observed_at,rowid", (turn,))],
                "review_reports": [{**dict(r), "payload": strict_json(r["payload"])} for r in self.store.db.execute("SELECT * FROM evidence_reviews WHERE turn_id=? ORDER BY observed_at,rowid", (turn,))]}

    def evidence_coverage(self, payload):
        obj(payload, ("session_id", "turn_id"))
        binding, selected = self.context(payload["session_id"], payload["turn_id"])
        delivered = self._delivered(payload["turn_id"], binding)
        reviewed, excluded = set(), set()
        for row in self.store.db.execute("SELECT payload FROM evidence_reviews WHERE turn_id=? AND binding=? ORDER BY observed_at,rowid", (payload["turn_id"], binding)):
            for record in strict_json(row[0])["records"]:
                (reviewed if record["disposition"] == "reviewed" else excluded).add(record["source_id"])
        ids = {s["source_id"] for s in selected}
        unresolved = ids - reviewed - excluded
        missing = ids - delivered
        return {"binding": binding, "selected_count": len(ids), "delivered_count": len(ids & delivered),
                "caller_reviewed_count": len(ids & reviewed), "caller_excluded_count": len(ids & excluded),
                "missing_delivery_count": len(missing), "unresolved_count": len(unresolved),
                "missing_delivery_ids": sorted(missing)[:20], "unresolved_ids": sorted(unresolved)[:20],
                "ids_preview_limit": 20, "detail_operation": "export_session", "structurally_complete": not missing and not unresolved,
                "delivery_scope": "complete registered reference text; product_fact factual_summary may be a stored summary, not its full source snapshot",
                "semantic_status": "unverified", "counts_are": "catalog source records, not customers or sufficiency",
                "review_status": "caller-reported meaning/disposition; not independently certified"}

    def evidence_inventory(self, payload):
        result = self.evidence_coverage(payload)
        _, selected = self.context(payload["session_id"], payload["turn_id"])
        result["by_scope_kind"] = [{"scope": strict_json(scope), "kind": kind,
                                   "registered": sum(canonical({k: s[k] for k in ("model_id", "model_version", "document_version")}) == scope and s["kind"] == kind for s in selected)}
                                  for scope in sorted({canonical({k: s[k] for k in ("model_id", "model_version", "document_version")}) for s in selected})
                                  for kind in ("review", "product_fact")]
        result["content_coverage"] = "positive/negative/long-term/conditions/manual/specification diversity requires semantic investigation"
        result["collected_observations_operation"] = "workflow_status counts / export_session workflow_events; collection is distinct from catalog registration"
        return result

    def require_complete(self, session, turn):
        result = self.evidence_coverage({"session_id": session, "turn_id": turn})
        if not result["structurally_complete"]:
            fail("evidence_coverage_incomplete", "Complete original delivery and caller review/exclusion for all selected catalog records, or hold with scope limits")
