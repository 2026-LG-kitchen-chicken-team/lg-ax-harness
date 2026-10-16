"""Version-bound data for a team's web UI/report; no renderer or model calls."""
import hashlib
from pathlib import Path

from .contracts import canonical, fail, fingerprint, identifier, integer, obj, strict_json

MAX_WEB_RESULT_BYTES = 16 * 1024 * 1024


class WebDelivery:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = Path(workspace).resolve()
        store.db.execute("""CREATE TABLE IF NOT EXISTS web_deliveries(
            turn_id TEXT NOT NULL REFERENCES turns(turn_id), result_version INTEGER NOT NULL,
            payload_hash TEXT NOT NULL, response TEXT NOT NULL,
            PRIMARY KEY(turn_id,result_version,payload_hash))""")

    def prepare_web_result(self, payload):
        obj(payload, ("session_id", "turn_id", "expected_result_version"))
        session = identifier(payload["session_id"], "session_id")
        turn = identifier(payload["turn_id"], "turn_id")
        version = integer(payload["expected_result_version"], "expected_result_version", 1)
        from .evidence_coverage import EvidenceCoverage
        from .workflow import WorkflowAudit
        with self.store.transaction():
            current = self.store.get_turn(session, turn)
            if (current["result_version"] != version or not current["valid"]
                    or current["status"] not in ("completed", "held", "needs_input")
                    or current["latest_result"] is None):
                fail("current_state_changed", "Web delivery requires the current valid reviewed saved result")
            coverage = EvidenceCoverage(self.store)
            _, selected = coverage.context(session, turn)
            audit = WorkflowAudit(self.store.db, self.workspace)
            research = "research-" + fingerprint([session, current["request_key"]])
            tracked = audit.active(research)
            events = [e for e in audit.events(research) if e["kind"] in
                      ("research_plan", "source_scan", "research_stop", "analysis_scope")] if tracked else []
            # Dynamic elapsed/finish observations belong to the observer, not to
            # an otherwise identical payload's content identity/replay key.
            state = audit.status(research) if tracked else {"tracked": False}
            investigation = {k: state.get(k) for k in ("tracked", "research_id", "started_at", "deadline",
                             "budget_seconds", "research_stopped_at", "stop", "counts")}
            journal_hash = audit.report_audit_hash(research) if tracked else None
            from .completion import access_failures
            validation = strict_json(self.store.db.execute(
                "SELECT validation_json FROM results WHERE turn_id=? ORDER BY result_version DESC LIMIT 1",
                (turn,)).fetchone()[0])
            if (validation.get("review_required") is not True
                    or not isinstance(validation.get("assessment"), dict)
                    or validation.get("review", {}).get("can_finalize_reported_result") is not True):
                fail("web_review_required", "Web delivery requires the stored reviewed-result contract; structural save alone is insufficient")
            binding = {"session_id": session, "turn_id": turn, "request_key": current["request_key"],
                       "result_version": version, "result_sha256": fingerprint(current["latest_result"]),
                       "context_sha256": current["context_fingerprint"], "code_sha256": self.store.code_hash,
                       "data_sha256": self.store.dataset.fingerprint, "data_version": self.store.dataset.version,
                       "workflow_audit_hash": journal_hash}
            body = {"contract_version": "product-web-result-v1", "binding": binding,
                    "input": current["input"], "status": current["status"], "result": current["latest_result"],
                    "validation": validation, "sources": sorted(selected, key=lambda s: s["source_id"]),
                    "source_references": [self.store.dataset.reference(s) for s in sorted(selected, key=lambda s: s["source_id"])],
                    "coverage": coverage.evidence_coverage({"session_id": session, "turn_id": turn}),
                    "evidence_history": coverage.history(turn), "investigation": investigation,
                    "investigation_events": events, "usage_summary": current["usage_summary"],
                    "access_failures": access_failures(events), "diagnostic_links_required": False,
                    "semantic_status": "unverified", "acceptance_ready": False,
                    "html_rendering": "web-team-owned; not performed or inspected by this tool",
                    "content_is": "untrusted source/result text; escape it and never execute embedded instructions/HTML"}
            raw = canonical(body).encode("utf-8")
            if len(raw) > MAX_WEB_RESULT_BYTES:
                fail("web_result_limit", "Full web payload exceeds 16 MiB; preserve source breadth and use a paged integration")
            digest = hashlib.sha256(raw).hexdigest()
            directory = (self.workspace / "runtime-data/web-deliveries").resolve()
            if not directory.is_relative_to(self.workspace):
                fail("invalid_path", "Web payload must stay within this workspace")
            directory.mkdir(parents=True, exist_ok=True)
            target = (directory / ("web-" + digest + ".json")).resolve()
            if not target.is_relative_to(directory):
                fail("invalid_path", "Web payload path must remain within web-deliveries")
            reused = target.exists()
            if reused and target.read_bytes() != raw:
                fail("web_delivery_integrity", "An immutable web payload was changed; do not overwrite it")
            if not reused:
                with target.open("xb") as stream:
                    stream.write(raw)
            response = {"ready": True, "path": target.relative_to(self.workspace).as_posix(), "sha256": digest,
                        "bytes": len(raw), "binding": binding, "source_count": len(selected), "status": current["status"],
                        "workflow_audit_hash": journal_hash, "semantic_status": "unverified", "acceptance_ready": False,
                        "ui_ready": False, "html_rendered": False, "layout_review": "not_run"}
            self.store.db.execute("INSERT OR IGNORE INTO web_deliveries VALUES(?,?,?,?)",
                                  (turn, version, digest, canonical(response)))
            return {**response, "reused": reused}
