"""Request-bound clocks and literal collection audit; never calls an AI model."""
from datetime import datetime, timedelta, timezone
import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from .contracts import ToolError, canonical, fail, fingerprint, identifier, integer, obj, strict_json, text
from . import research_scope


def utc_now():
    return datetime.now(timezone.utc)


class WorkflowAudit:
    def __init__(self, db, workspace):
        self.db = db
        self.workspace = Path(workspace).resolve()
        db.execute("""CREATE TABLE IF NOT EXISTS product_workflows(
            research_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, budget_seconds INTEGER NOT NULL,
            research_stopped_at TEXT, finished_at TEXT, checkpoint TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS product_workflow_events(
            research_id TEXT NOT NULL, event_key TEXT NOT NULL, kind TEXT NOT NULL,
            observed_at TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(research_id,event_key))""")
        if "target_checkpoint" not in {r[1] for r in db.execute("PRAGMA table_info(product_workflows)")}:
            db.execute("ALTER TABLE product_workflows ADD COLUMN target_checkpoint TEXT")
        if "timing_policy" not in {r[1] for r in db.execute("PRAGMA table_info(product_workflows)")}:
            db.execute("ALTER TABLE product_workflows ADD COLUMN timing_policy TEXT")

        if "research_policy" not in {r[1] for r in db.execute("PRAGMA table_info(product_workflows)")}:
            db.execute("ALTER TABLE product_workflows ADD COLUMN research_policy TEXT")

    def request(self, research_id):
        identifier(research_id, "research_id")
        try:
            rows = self.db.execute("SELECT session_id,request_key,turn_id FROM conversation_requests").fetchall()
        except sqlite3.OperationalError:
            rows = []
        for row in rows:
            if research_id == "research-" + fingerprint([row[0], row[1]]):
                return row
        fail("research_not_registered", "Use the original saved request's research_id")

    def start(self, research_id, budget_seconds=1800, allow_new_bound_request=False):
        request = self.request(research_id)
        integer(budget_seconds, "budget_seconds", 300, 1800)
        row = self.db.execute("SELECT budget_seconds FROM product_workflows WHERE research_id=?", (research_id,)).fetchone()
        if not row and request[2] is not None and not allow_new_bound_request:
            fail("workflow_late_start", "Do not start a whole-request clock after binding an older untimed turn")
        if row and row[0] != budget_seconds:
            fail("workflow_conflict", "Original whole-request budget cannot be reset or extended")
        if not row:
            self.db.execute("INSERT INTO product_workflows(research_id,started_at,budget_seconds,timing_policy,research_policy) VALUES(?,?,?,?,?)",
                            (research_id, utc_now().isoformat(), budget_seconds, "natural-completion-v1", research_scope.POLICY))
        return self.status(research_id)

    def active(self, research_id):
        return self.db.execute("SELECT 1 FROM product_workflows WHERE research_id=?", (research_id,)).fetchone() is not None

    def request_turn_status(self, research_id):
        """Recognize registered terminal turns without requiring a timed workflow."""
        try:
            request = self.request(research_id)
        except ToolError as error:
            if error.code == "research_not_registered":
                return None  # Legacy standalone evidence has no request journal.
            raise
        if request[2] is None:
            return None
        row = self.db.execute("SELECT status FROM turns WHERE session_id=? AND turn_id=?",
                              (request[0], request[2])).fetchone()
        return row[0] if row else None

    def require_request_open(self, research_id):
        if self.request_turn_status(research_id) in ("cancelled", "failed"):
            fail("terminal_turn", "The original turn is cancelled/failed; no new collection or catalog writes")

    def collection_allowed(self, research_id):
        self.require_request_open(research_id)
        if not self.active(research_id):
            return
        state = self.status(research_id)
        if state["expired"] or state["finished_at"] or state["research_stopped_at"] or state["collection_reserve_active"]:
            fail("workflow_collection_closed", "Collection is closed; retain this request, save and deliver the observed scope")

    def snapshot(self, research_id, snapshot_id):
        self.request(research_id)
        if not self.db.execute("SELECT 1 FROM web_pages WHERE research_id=? AND snapshot_id=?", (research_id, snapshot_id)).fetchone():
            fail("workflow_snapshot_scope", "Snapshot must belong to the original request journal")
        path = self.workspace / "runtime-data/web-evidence" / (identifier(snapshot_id, "snapshot_id") + ".json")
        value = strict_json(path.read_text(encoding="utf-8"))
        check = {k: v for k, v in value.items() if k != "snapshot_id"}
        if value.get("snapshot_id") != snapshot_id or fingerprint(check) != snapshot_id:
            fail("snapshot_integrity", "Snapshot bytes do not match their identity")
        if self.active(research_id):
            clock = self.status(research_id)
            observed = datetime.fromisoformat(value["observed_at"])
            if not datetime.fromisoformat(clock["started_at"]) <= observed <= datetime.fromisoformat(clock["deadline"]):
                fail("workflow_snapshot_time", "Do not count before-run or after-budget observations in this request")
        return value

    def record(self, payload, dataset=None):
        obj(payload, ("research_id", "event_key", "kind", "data"))
        research = identifier(payload["research_id"], "research_id")
        key = identifier(payload["event_key"], "event_key")
        self.request(research)
        if not self.active(research):
            fail("workflow_not_started", "Start the product workflow before collection")
        kind, data = payload["kind"], payload["data"]
        if kind not in ("research_plan", "source_scan", "research_stop", "analysis_scope", "checkpoint", "finish"):
            fail("invalid_input", "Unknown workflow audit event")
        raw = canonical(payload)
        old = self.db.execute("SELECT payload FROM product_workflow_events WHERE research_id=? AND event_key=?", (research, key)).fetchone()
        if old:
            if old[0] != raw:
                fail("workflow_conflict", "Audit event identity cannot be reused for different input")
            return self.status(research)
        if self.status(research)["finished_at"]:
            fail("workflow_finished", "A finished workflow cannot accept new audit events")
        # A late failed observation can be audited without adding any observed
        # source. It does not reopen collection, import or a finished workflow.
        terminal_failure_audit = (kind == "source_scan" and isinstance(data, dict)
            and data.get("status") == "inaccessible" and not data.get("reviews")
            and not data.get("snapshot_ids") and self.request_turn_status(research) in ("cancelled", "failed"))
        if kind in ("research_plan", "source_scan") and not terminal_failure_audit:
            self.collection_allowed(research)
        if kind == "research_plan":
            obj(data, ("product_name", "coverage", "source_plan"), ("goals",))
            research_scope.validate_plan(data, self.events(research))
            text(data["product_name"], "product_name", 200)
            self._strings(data["coverage"], "coverage", 30)
            if not {"positive", "negative", "long_term", "conditions", "counterexamples"} <= set(data["coverage"]):
                fail("invalid_input", "Plan the whole product before selecting a pain")
            self._strings(data["source_plan"], "source_plan", 100)
        elif kind == "source_scan":
            from .web_evidence import public_url
            obj(data, ("source_url", "page_label", "status", "reviews", "reason"), ("snapshot_ids", "list_total", "remaining_scope", "source_type", "goal_ids"))
            research_scope.validate_scan(data, self.events(research), self.scope_required(research))
            public_url(data["source_url"])
            if not any(e["kind"] == "research_plan" for e in self.events(research)):
                fail("workflow_plan_missing", "Record whole-product coverage before source scans")
            if data["status"] not in ("observed", "inaccessible", "not_applicable"):
                fail("invalid_input", "Source scan status must be observed/inaccessible/not_applicable")
            text(data["page_label"], "page_label", 1000)
            text(data["reason"], "reason", 4000)
            if data.get("list_total") is not None:
                integer(data["list_total"], "list_total", 0, 10000000)
            self._strings(data.get("snapshot_ids", []), "snapshot_ids", 100)
            self._strings(data.get("remaining_scope", []), "remaining_scope", 100)
            if data.get("source_type", "unknown") not in ("product_document", "manual", "review_list", "market", "competitor", "unknown"):
                fail("invalid_input", "Unknown source type")
            if not isinstance(data["reviews"], list) or len(data["reviews"]) > 100:
                fail("invalid_input", "Record observations in batches; do not use a batch size as an investigation endpoint")
            if data["status"] == "observed" and not data.get("snapshot_ids") and not data["reviews"]:
                fail("workflow_snapshot_scope", "An observed source scan needs retained snapshot evidence")
            for snapshot_id in data.get("snapshot_ids", []):
                if self.snapshot(research, snapshot_id)["url"] != data["source_url"]:
                    fail("workflow_snapshot_scope", "Source scan URL must match each retained snapshot")
            for review in data["reviews"]:
                obj(review, ("snapshot_id", "text", "review_id", "source_ids", "disposition", "reason"),
                    ("published_date", "purchase_date", "model_option", "usage_conditions", "positive_context", "qualified_context", "text_coverage"))
                snapshot = self.snapshot(research, review["snapshot_id"])
                text(review["text"], "literal review", 16000)
                if review["text"] not in snapshot["text"]:
                    fail("quote_mismatch", "Audit review must be a literal contiguous retained observation")
                if snapshot["url"] != data["source_url"]:
                    fail("workflow_snapshot_scope", "Audit URL must match the observed snapshot URL")
                if review["review_id"] is not None:
                    text(review["review_id"], "review_id", 300)
                    if review["review_id"] not in snapshot["text"]:
                        fail("workflow_review_identity", "Keep review_id unknown unless the retained observation supports it")
                if review["disposition"] not in ("retained", "duplicate", "wrong_model", "wrong_option", "prior_product", "summary_only", "insufficient_context", "uncertain_identity"):
                    fail("invalid_input", "Unknown review disposition")
                text(review["reason"], "review disposition reason", 2000)
                self._strings(review["source_ids"], "source_ids", 100)
                if review["disposition"] == "retained" and not review["source_ids"]:
                    fail("workflow_review_identity", "Retained review needs its catalog source IDs; split long text without inventing more reviewers")
                for source_id in review["source_ids"]:
                    identifier(source_id, "source_id")
                for field in ("published_date", "purchase_date", "model_option", "usage_conditions", "positive_context", "qualified_context"):
                    if review.get(field) is not None:
                        text(review[field], field, 2000)
                if review.get("text_coverage", "partial") not in ("full_review_observed", "partial"):
                    fail("invalid_input", "Declare full-review observation or partial excerpt")
        elif kind == "research_stop":
            obj(data, ("code", "basis", "new_findings", "remaining_scope"), ("remaining_goal_ids", "limitation_basis"))
            if data["code"] not in ("completion_time_reserve", "sources_exhausted", "sufficient_evidence", "access_failure", "insufficient_evidence", "whole_budget_expired"):
                fail("invalid_input", "Distinguish the actual investigation stop reason")
            text(data["basis"], "stop basis", 8000)
            self._strings(data["new_findings"], "new_findings", 100)
            self._strings(data["remaining_scope"], "remaining_scope", 100)
            if self.scope_required(research):
                research_scope.validate_stop(data, self.events(research))
            if data["code"] == "whole_budget_expired" and not self.status(research)["expired"]:
                fail("workflow_stop_reason", "The whole-request clock has not expired")
            if self.db.execute("SELECT research_stopped_at FROM product_workflows WHERE research_id=?", (research,)).fetchone()[0]:
                fail("workflow_collection_closed", "Investigation stop is already recorded")
            self.db.execute("UPDATE product_workflows SET research_stopped_at=? WHERE research_id=?", (utc_now().isoformat(), research))
        elif kind == "analysis_scope":
            obj(data, ("source_ids", "scope_note"))
            self._strings(data["source_ids"], "source_ids", 1000)
            text(data["scope_note"], "analysis scope", 8000)
            if dataset is None or any(sid not in dataset.sources for sid in data["source_ids"]):
                count = len(dataset.sources) if dataset is not None else 0
                fail("workflow_analysis_scope", f"Analysis batch IDs are absent from the selected catalog ({count} records). "
                     "Pass the same --data catalog used by the current planning bundle; registered local catalogs are supported. "
                     "No analysis event was recorded. Check the actual selected catalog before retrying; do not invent an external-only restriction.")
        elif kind == "finish":
            obj(data, ("delivered_paths", "layout_review"))
            self._strings(data["delivered_paths"], "delivered_paths", 100)
            if not data["delivered_paths"]:
                fail("workflow_delivery_missing", "Finish requires actual retained delivery files")
            request = self.request(research)
            if request[2] is None:
                fail("workflow_delivery_missing", "Finish needs a reviewed saved turn and reader delivery")
            turn = self.db.execute("SELECT valid,result_version,status FROM turns WHERE turn_id=?", (request[2],)).fetchone()
            if not turn or not turn[0] or turn[2] not in ("completed", "held", "needs_input"):
                fail("workflow_delivery_missing", "Finish requires a current valid saved turn")
            paths = [(self.workspace / name).resolve() for name in data["delivered_paths"]]
            for path in paths:
                if not path.is_relative_to(self.workspace / "runtime-data") or not path.is_file():
                    fail("workflow_delivery_missing", "Delivered reader path must exist inside this workflow")
            deliveries = self.db.execute("SELECT response,file_hashes FROM reader_deliveries WHERE turn_id=? AND result_version=?", (request[2], turn[1])).fetchall()
            matched = False
            for delivered in deliveries:
                response = strict_json(delivered[0])
                hashes = strict_json(delivered[1])
                expected = {str((self.workspace / name).resolve()): digest for name, digest in hashes.items()}
                if (response.get("ready") and response.get("workflow_audit_hash") == self.report_audit_hash(research)
                        and set(map(str, paths)) == set(expected)):
                    matched = all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest for name, digest in expected.items())
            web_exists = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_deliveries'").fetchone()
            if not matched and web_exists:
                for delivered in self.db.execute("SELECT response FROM web_deliveries WHERE turn_id=? AND result_version=?", (request[2], turn[1])):
                    response = strict_json(delivered[0])
                    path = (self.workspace / response["path"]).resolve()
                    if (response.get("ready") and response.get("workflow_audit_hash") == self.report_audit_hash(research)
                            and set(map(str, paths)) == {str(path)}):
                        matched = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == response["sha256"]
                        if matched:
                            break
            if not matched:
                fail("workflow_delivery_missing", "Finish must match current saved-version reader files and hashes")
            obj(data["layout_review"], ("status", "scope"))
            if data["layout_review"]["status"] not in ("passed", "not_run", "failed"):
                fail("invalid_input", "Layout review state must be reported accurately")
            text(data["layout_review"]["scope"], "layout scope", 4000)
            self.finish(research)
        else:
            obj(data, ("remaining_tasks",))
            self._strings(data["remaining_tasks"], "remaining_tasks", 30)
        self.db.execute("INSERT INTO product_workflow_events VALUES(?,?,?,?,?)", (research, key, kind, utc_now().isoformat(), raw))
        return self.status(research)

    @staticmethod
    def _strings(values, name, limit):
        if not isinstance(values, list) or len(values) > limit or any(not isinstance(v, str) or not v.strip() for v in values):
            fail("invalid_input", name + " must be an array of nonempty strings")

    def events(self, research):
        return [{"observed_at": row[0], **strict_json(row[1])} for row in self.db.execute(
            "SELECT observed_at,payload FROM product_workflow_events WHERE research_id=? ORDER BY observed_at,rowid", (research,))]

    def status(self, research):
        row = self.db.execute("SELECT started_at,budget_seconds,research_stopped_at,finished_at,checkpoint,target_checkpoint,timing_policy FROM product_workflows WHERE research_id=?", (research,)).fetchone()
        if not row:
            return {"tracked": False, "reason": "legacy/request without a measured product workflow"}
        started = datetime.fromisoformat(row[0])
        deadline = started + timedelta(seconds=row[1])
        end = datetime.fromisoformat(row[3]) if row[3] else utc_now()
        elapsed = max(0, (end-started).total_seconds())
        events = self.events(research)
        legacy_short = row[6] is None and row[1] <= 600
        reserve = row[6] == "natural-completion-v1" or legacy_short
        if elapsed >= 1200 and not row[4]:
            checkpoint = {"observed_at": utc_now().isoformat(), "elapsed_seconds": round(elapsed, 3),
                          "due_at_seconds": 1200, "method": "first workflow tool observation at or after 20 minutes",
                          "remaining_seconds": max(0, round((deadline-utc_now()).total_seconds(), 3)),
                          "research_stopped": bool(row[2]), "recorded_events": len(events)}
            was_in_transaction = self.db.in_transaction
            self.db.execute("UPDATE product_workflows SET checkpoint=? WHERE research_id=?", (canonical(checkpoint), research))
            if not was_in_transaction and self.db.isolation_level is not None:
                self.db.commit()
        else:
            checkpoint = strict_json(row[4]) if row[4] else None
        target_checkpoint = strict_json(row[5]) if row[5] else None
        if legacy_short and elapsed >= 300 and target_checkpoint is None:
            target_checkpoint = {"observed_at": utc_now().isoformat(), "elapsed_seconds": round(elapsed, 3),
                                 "due_at_seconds": 300, "method": "first workflow tool observation at or after target",
                                 "remaining_seconds": max(0, round((deadline-end).total_seconds(), 3)),
                                 "research_stopped": bool(row[2]), "recorded_events": len(events)}
            was_in_transaction = self.db.in_transaction
            self.db.execute("UPDATE product_workflows SET target_checkpoint=? WHERE research_id=?", (canonical(target_checkpoint), research))
            if not was_in_transaction and self.db.isolation_level is not None:
                self.db.commit()
        counts = self.counts(events, self.used_sources(research))
        counts["provider_count"] = len(counts["providers"])
        counts["providers"] = counts["providers"][:6]
        counts["analysed_source_ids"] = counts["analysed_source_ids"][:20]
        for provider in counts["providers"]:
            provider["source_url_count"] = len(provider["source_urls"])
            provider["scan_count"] = len(provider["scans"])
            provider["detail_scope"] = "bounded URL/scan previews; full investigation events retained in export_session"
            provider["source_urls"] = [url[:150] for url in provider["source_urls"][-2:]]
            provider["namespace_ambiguous_literal_id_count"] = len(provider["namespace_ambiguous_literal_ids"])
            provider["namespace_ambiguous_literal_ids"] = [sid[:100] for sid in provider["namespace_ambiguous_literal_ids"][:5]]
            provider["scans"] = [{**scan, "page": scan["page"][:100], "reason": scan["reason"][:100],
                "goal_id_count": len(scan["goal_ids"]), "goal_ids": scan["goal_ids"][:5],
                "remaining_scope_count": len(scan["remaining_scope"]),
                "remaining_scope": [part[:100] for part in scan["remaining_scope"][:2]]} for scan in provider["scans"][-2:]]
        result = {"tracked": True, "research_id": research, "started_at": row[0], "deadline": deadline.isoformat(),
                "budget_seconds": row[1], "elapsed_seconds": round(elapsed, 3),
                "remaining_seconds": max(0, round((deadline-end).total_seconds(), 3)), "expired": end > deadline,
                "research_stopped_at": row[2], "finished_at": row[3], "twenty_minute_checkpoint": checkpoint,
                "timing_policy": row[6],
                "timing_contract": "natural-completion-safety-bound-v1" if row[6] else ("short-request-v1" if legacy_short else "legacy-explicit-budget"),
                "target_seconds": min(300, row[1]) if legacy_short else None, "final_delivery_reserve_seconds": 90 if reserve else None,
                "collection_deadline": (deadline-timedelta(seconds=90)).isoformat() if reserve else deadline.isoformat(),
                "collection_reserve_active": reserve and end >= deadline-timedelta(seconds=90),
                "target_checkpoint": target_checkpoint,
                "target_checkpoint_due": legacy_short and elapsed >= min(300, row[1]),
                "native_deadline_enforcement": "not provided; local tool policy and file-finish clock only; native final/process exit needs external runner",
                "research_seconds": round((datetime.fromisoformat(row[2])-started).total_seconds(), 3) if row[2] else None,
                "stop": next((e["data"] for e in reversed(events) if e["kind"] == "research_stop"), None),
                "layout_review": self.layout_review(events),
                "counts": counts, "event_count": len(events),
                "research_scope": {"policy": self.db.execute("SELECT research_policy FROM product_workflows WHERE research_id=?", (research,)).fetchone()[0],
                                   "required": self.scope_required(research), **research_scope.preview(research_scope.summary(events)),
                                   "stop_scope_file": self.scope_file(research, events) if self.scope_required(research) else None},
                "scope": "measured request clock and literal/caller-reported investigation journal; not semantic sufficiency certification"}
        if result["stop"]:
            stop = result["stop"]
            result["stop"] = {**stop, "basis": stop["basis"][:400],
                "new_findings_count": len(stop["new_findings"]), "new_findings": [v[:100] for v in stop["new_findings"][:5]],
                "remaining_scope_count": len(stop["remaining_scope"]), "remaining_scope": [v[:100] for v in stop["remaining_scope"][:5]],
                "remaining_goal_count": len(stop.get("remaining_goal_ids", [])), "remaining_goal_ids": stop.get("remaining_goal_ids", [])[:20],
                "limitation_basis": (stop.get("limitation_basis") or "")[:400], "detail_scope": "stop preview; complete immutable event in export_session"}
        # Complete fields remain in the immutable scope file and event journal.
        # Bound the whole status even after many legitimate providers/checkpoints.
        if len(canonical(result).encode("utf-8")) > 60000:
            result["counts"]["providers"] = []
            result["research_scope"]["goals"] = []
            result["status_detail_truncated"] = True
        if len(canonical(result).encode("utf-8")) > 60000:
            result["twenty_minute_checkpoint"] = None
            result["target_checkpoint"] = None
            result["status_detail_truncated"] = True
        return result


    @staticmethod
    def layout_review(events):
        """Expose a caller declaration, never certify native image inspection.

        File hashes establish delivery integrity, not image-tool use. Preserve
        the immutable journal; an external observer must inspect the native trace.
        """
        declared = next((e["data"]["layout_review"] for e in reversed(events)
                         if e["kind"] == "finish"), None)
        return {"declared_status": declared["status"] if declared else "not_run",
                "scope": declared["scope"] if declared else None,
                "verification_status": "not_verified",
                "verified_image_inspection": None,
                "basis": "caller declaration only; native image inspection not observed by this tool"}

    def used_sources(self, research):
        request = self.request(research)
        if request[2] is None:
            return None
        row = self.db.execute("SELECT payload FROM results WHERE turn_id=? ORDER BY result_version DESC LIMIT 1", (request[2],)).fetchone()
        if not row:
            return None
        return {sid for concept in strict_json(row[0]).get("concepts", []) for sid in concept.get("source_ids", [])}

    def counts(self, events, used_sources=None):
        providers, analysed = {}, set()
        for event in events:
            if event["kind"] == "analysis_scope":
                analysed.update(event["data"]["source_ids"])
            if event["kind"] != "source_scan":
                continue
            data = event["data"]
            provider = urlparse(data["source_url"]).hostname or data["source_url"]
            item = providers.setdefault(provider, {"source_urls": [], "scans": [], "observations": [], "exclusions": {}})
            if data["source_url"] not in item["source_urls"]:
                item["source_urls"].append(data["source_url"])
            item["scans"].append({"page": data["page_label"], "status": data["status"], "reason": data["reason"], "list_total": data.get("list_total"), "source_type": data.get("source_type", "unknown"), "goal_ids": data.get("goal_ids", []), "remaining_scope": data.get("remaining_scope", [])})
            item["observations"].extend({**r, "_source_url": data["source_url"]} for r in data["reviews"])
        result = []
        for provider, item in providers.items():
            known, retained, analysed_reviews, used_reviews, retained_texts = set(), set(), set(), set(), set()
            unknown, retained_unknown, used_unknown = 0, 0, 0
            observations = item.pop("observations")
            namespaces = {}
            for review in observations:
                if review["review_id"] is not None:
                    namespaces.setdefault(review["review_id"], set()).add(review["_source_url"])
            ambiguous = {key for key, urls in namespaces.items() if len(urls) > 1}
            for review in observations:
                key = review["review_id"]
                if key in ambiguous:
                    key = None
                if key is None:
                    unknown += 1
                else:
                    known.add(key)
                if review["disposition"] == "retained":
                    retained_texts.add(fingerprint([review["review_id"], review["text"]]))
                    if key is None:
                        retained_unknown += 1
                    else:
                        retained.add(key)
                        if set(review["source_ids"]) & analysed:
                            analysed_reviews.add(key)
                        if used_sources is not None and set(review["source_ids"]) & used_sources:
                            used_reviews.add(key)
                    if key is None and used_sources is not None and set(review["source_ids"]) & used_sources:
                        used_unknown += 1
                else:
                    item["exclusions"][review["disposition"]] = item["exclusions"].get(review["disposition"], 0) + 1
            result.append({"provider": provider, **item, "reviewed_known_unique_ids": len(known),
                           "namespace_ambiguous_literal_ids": sorted(ambiguous),
                           "reviewed_identity_unknown_observations": unknown,
                           "reviewed_unique_review_total": None if unknown or not known and not any(s["source_type"] == "review_list" and s["status"] == "observed" for s in item["scans"]) else len(known),
                           "retained_known_unique_review_ids": len(retained), "retained_identity_unknown_observations": retained_unknown,
                           "valid_unique_review_total": None if retained_unknown else len(retained),
                           "analysed_known_unique_review_ids": len(analysed_reviews),
                           "retained_literal_observation_count": len(retained_texts),
                           "proposal_used_known_unique_review_ids": None if used_sources is None else len(used_reviews),
                           "proposal_used_identity_unknown_observations": None if used_sources is None else used_unknown,
                           "counts_are": "review identities/observations, never independent customers or whole-product prevalence"})
        return {"providers": result, "analysed_source_ids": sorted(analysed), "analysed_source_record_count": len(analysed)}

    def report_section(self, research, dataset):
        status = self.status(research)
        events = self.events(research)
        # UI status is a bounded preview; reports use the complete preserved journal.
        counts = self.counts(events, self.used_sources(research))
        def number(value):
            return "미확인" if value is None else value
        rows = [[p["provider"], number(p["reviewed_unique_review_total"]), p["retained_literal_observation_count"],
                 sum(p["exclusions"].values()), number(p["valid_unique_review_total"]),
                 number(p["proposal_used_known_unique_review_ids"])] for p in counts["providers"]]
        scoped = set(dataset.sources)
        analysed = set(counts["analysed_source_ids"])
        blocks = [{"type": "paragraph", "text": "수집 항목·원문 발췌·고유 후기 ID·검토 페이지는 서로 다른 단위다. 아래 제외 수는 관측 처리 기록이며 고객 수가 아니다. 후기 고유 ID가 미확인인 출처의 고유 총수는 미확인으로 남겼다. 신고된 분류·문맥과 출처별 상세 이력은 보존 원문과 조사 기록에서 확인한다."}]
        if rows:
            blocks.append({"type": "table", "title": "출처별 이번 조사와 제안 사용 범위", "columns": ["출처", "검토 고유 후기", "보존 원문 관측", "제외 관측", "유효 고유 후기", "제안 사용 확인 ID"], "rows": rows})
        stop = next((event["data"] for event in reversed(events) if event["kind"] == "research_stop"), None)
        if stop:
            labels = {"completion_time_reserve": "분석·검토·파일 전달 시간 확보", "sources_exhausted": "조사한 접근 경로의 자료 소진",
                      "sufficient_evidence": "근거 충분 판단", "access_failure": "접근 실패", "insufficient_evidence": "자료 부족", "whole_budget_expired": "전체 시간 예산 종료"}
            blocks.append({"type": "paragraph", "text": "조사 종료: "+labels[stop["code"]]+". 근거: "+stop["basis"]})
            if stop["new_findings"]:
                blocks.append({"type": "paragraph", "text": "추가 조사에서 확인한 사항: "+"; ".join(stop["new_findings"])})
            if stop["remaining_scope"]:
                blocks.append({"type": "paragraph", "text": "남은 조사 범위: "+"; ".join(stop["remaining_scope"])})
            if stop.get("limitation_basis"):
                blocks.append({"type": "paragraph", "text": "남은 범위의 결론 영향과 조건: "+stop["limitation_basis"]})
            if stop.get("remaining_goal_ids"):
                blocks.append({"type": "paragraph", "text": "남은 조사 목표 ID: "+"; ".join(stop["remaining_goal_ids"])})
        blocks.append({"type": "paragraph", "text": f"등록 원문 항목 {len(scoped)}개 중 분석 범위를 신고한 항목 {len(scoped & analysed)}개. 미신고 항목 {len(scoped-analysed)}개는 전량 분석했다고 주장하지 않는다. ID 목록의 신고는 원문 의미 검토의 자동 인증이 아니다."})
        blocks.append({"type": "paragraph", "text": f"전체 업무 예산 {status['budget_seconds']}초. 조사 종료까지 {status['research_seconds'] if status['research_seconds'] is not None else '미확인'}초. 최종 답변과 종료의 실제 전체 시간은 실행 종료 기록으로 별도 확인한다."})
        return {"title": "이번 조사 범위와 자료 상태", "blocks": blocks}

    def finish(self, research):
        if self.active(research):
            self.db.execute("UPDATE product_workflows SET finished_at=COALESCE(finished_at,?) WHERE research_id=?", (utc_now().isoformat(), research))
        return self.status(research)

    def scope_file(self, research, events):
        # Immutable metadata for stop input; review bodies stay in their original
        # snapshots/journal. This does not shorten or replace collected evidence.
        report = research_scope.summary(events)
        value = {"research_id": research, "research_policy": research_scope.POLICY,
                 "workflow_audit_sha256": self.report_audit_hash(research),
                 "remaining_goal_ids": report["remaining_goal_ids"], "remaining_scope": report["remaining_scope"],
                 "goals": [{"goal_id": goal["goal_id"], "kind": goal["kind"], "state": goal["state"],
                            "remaining_scope": goal["remaining_scope"]} for goal in report["goals"]],
                 "scope": "complete declared stop metadata, not source bodies or semantic certification"}
        raw = canonical(value).encode("utf-8")
        if len(raw) > 16 * 1024 * 1024:
            fail("workflow_scope_limit", "Stop-scope metadata exceeds 16 MiB; retain full journal and disclose the limit")
        digest = hashlib.sha256(raw).hexdigest()
        base = (self.workspace / "runtime-data/research-scopes").resolve()
        if not base.is_relative_to(self.workspace / "runtime-data"):
            fail("invalid_path", "Scope metadata must stay in this workspace runtime-data")
        base.mkdir(parents=True, exist_ok=True)
        target = base / (digest + ".json")
        if target.exists():
            if not target.is_file() or target.resolve().parent != base or target.read_bytes() != raw:
                fail("workflow_scope_integrity", "Immutable scope metadata changed; retain the original journal")
        else:
            with target.open("xb") as stream:
                stream.write(raw)
        return {"path": target.relative_to(self.workspace).as_posix(), "sha256": digest, "bytes": len(raw),
                "content": "full remaining_goal_ids/remaining_scope and goal states; read selected JSON fields from file",
                "binding": "research_id + current workflow audit hash; prior file cannot authorize newer scan state"}

    def scope_required(self, research):
        row = self.db.execute("SELECT research_policy FROM product_workflows WHERE research_id=?", (research,)).fetchone()
        if not row or row[0] != research_scope.POLICY:
            return False
        table = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='web_pages'").fetchone()
        return bool(table and self.db.execute("SELECT 1 FROM web_pages WHERE research_id=? LIMIT 1", (research,)).fetchone())

    def require_scope_disclosure(self, research, finalizing=True):
        if self.scope_required(research):
            events = self.events(research)
            stop = next((e["data"] for e in reversed(events) if e["kind"] == "research_stop"), None)
            if stop is None:
                fail("workflow_research_open", "Record scope and actual stop before completing new web research")
            research_scope.validate_stop(stop, events, finalizing=finalizing)

    def require_stopped(self, research):
        if self.active(research) and not self.status(research)["research_stopped_at"]:
            fail("workflow_research_open", "Record investigation scope and actual stop reason before resolving analysis")
        self.require_scope_disclosure(research, finalizing=False)

    def check_review_import(self, research, entry):
        if not self.active(research) or entry.get("kind") != "review":
            return
        for event in self.events(research):
            if event["kind"] == "source_scan":
                for review in event["data"]["reviews"]:
                    if (review["disposition"] == "retained" and entry["source_id"] in review["source_ids"]
                            and entry["snapshot_id"] == review["snapshot_id"] and entry["support_quote"] in review["text"]):
                        return
        fail("workflow_review_audit_missing", "Journal the retained review identity, full/partial literal context and planned source IDs before import")

    def check_catalog(self, research, dataset):
        if not self.active(research):
            return
        for event in self.events(research):
            if event["kind"] != "source_scan":
                continue
            for review in event["data"]["reviews"]:
                if review["disposition"] != "retained":
                    continue
                for source_id in review["source_ids"]:
                    source = dataset.sources.get(source_id)
                    if (not source or source["kind"] != "review" or source["origin"]["source_url"] != event["data"]["source_url"]
                            or source["text"] not in review["text"]):
                        fail("workflow_review_audit_missing", "Retained source IDs must resolve to their actual literal review records in the final catalog")

    def report_audit_hash(self, research):
        return fingerprint([e for e in self.events(research) if e["kind"] in ("research_plan", "source_scan", "research_stop", "analysis_scope")])

    def review_sources(self, research):
        # Retain long/full observations in the reader library without using them
        # to bypass exact-model ProductResult catalog evidence validation.
        result, seen = [], set()
        for event in self.events(research):
            if event["kind"] != "source_scan":
                continue
            for review in event["data"]["reviews"]:
                if review["disposition"] != "retained":
                    continue
                snapshot = self.snapshot(research, review["snapshot_id"])
                digest = fingerprint([event["data"]["source_url"], review["review_id"], review["text"]])
                if digest in seen:
                    continue
                seen.add(digest)
                result.append({"id": "observed-review-"+digest, "kind": "review",
                    "title": "관측 고객 후기 · "+(review["review_id"] or "고유 ID 미확인"),
                    "text": review["text"], "url": snapshot["url"], "synthetic": False,
                    "location": "리뷰 "+(review["review_id"] or "미확인")+" / "+event["data"]["page_label"],
                    "model": "모델·옵션: "+(review.get("model_option") or "미확인")+" / 관찰일: "+snapshot["observed_at"]
                             +" / 게시일: "+(review.get("published_date") or "미확인")+" / 구매일: "+(review.get("purchase_date") or "미확인")
                             +" / 보존 범위: "+review.get("text_coverage", "partial")+" / 사용 조건: "+(review.get("usage_conditions") or "미확인")
                             +" / 긍정·유보: "+(review.get("positive_context") or "미확인")+"; "+(review.get("qualified_context") or "미확인")})
        return result
