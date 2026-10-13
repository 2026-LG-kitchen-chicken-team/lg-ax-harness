"""Request-clock and literal-evidence regressions; all observations are code fixtures.

Set PRODUCT_WORKFLOW_TEST_ROOT to audit one other checkout as the sole import
source. Fixtures and SQLite files always remain in this test's own scratch.
There is no network request, native AI execution, or real product investigation.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TEST_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("PRODUCT_WORKFLOW_TEST_ROOT", TEST_ROOT)).resolve()
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.web_evidence import WebEvidence
from product_tools.workflow import WorkflowAudit


def held_fixture():
    return {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [],
            "assumptions": [], "evidence_refs": [], "validation_findings": ["Synthetic contract fixture lacks product evidence."],
            "revisions": 0, "usage_summary": {"status": "unknown"}}


class ProductWorkflowTests(unittest.TestCase):
    def setUp(self):
        scratch = TEST_ROOT / "runtime-data"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-unit-", dir=scratch)
        self.root = Path(self.temp.name).resolve()
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        self.started = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
        self.now = self.started
        self.clock = patch("product_tools.workflow.utc_now", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.store = StateStore(self.root / "runtime-data/product.sqlite", Dataset(ROOT / "data/business/empty"))
        self.conv = Conversation(self.store, self.root)
        self.original = {"question": "  테스트 제품 WF-TEST\n제품명만 입력한 원문  ",
                         "user_submitted": True, "session_id": "original-session", "request_key": "original-question"}
        self.request = self.conv.open_product_workflow({**self.original, "budget_seconds": 1800})
        self.research = self.request["research_id"]
        self.audit = WorkflowAudit(self.store.db, self.root)
        self.web = WebEvidence(self.store.path, self.root)

    def tearDown(self):
        self.web.close()
        self.store.close()
        self.assertTrue(self.root.is_relative_to((TEST_ROOT / "runtime-data").resolve()))
        self.temp.cleanup()

    def error(self, code, operation, *args, **kwargs):
        with self.assertRaises(ToolError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def record(self, kind, data, key=None, research=None):
        return self.conv.record_workflow_event({"research_id": research or self.research,
            "event_key": key or "event-" + str(self.audit.status(self.research)["event_count"]),
            "kind": kind, "data": data})

    def plan(self):
        return self.record("research_plan", {"product_name": "WF-TEST code fixture",
            "coverage": ["positive", "negative", "long_term", "conditions", "counterexamples"],
            "source_plan": ["Exact model manual", "Complete review context", "Counterexamples"]}, "whole-product-plan")

    def capture(self, page, body, url="https://reviews.example.org/wf-test", research=None, observed=None):
        with patch("product_tools.web_evidence.datetime") as observed_clock:
            observed_clock.now.return_value = observed or self.now
            return self.web.collect({"research_id": research or self.research, "page_id": page,
                "url": url, "observed_text": body, "native_tool_name": "unit_fixture_no_browser_executed"}, True)

    def review(self, snapshot, body, review_id="RID-1", source_ids=None, **extra):
        return {"snapshot_id": snapshot["snapshot_id"], "text": body, "review_id": review_id,
            "source_ids": ["review-source"] if source_ids is None else source_ids,
            "disposition": "retained", "reason": "Literal unit fixture, not customer evidence", **extra}

    def scan(self, snapshot, reviews, *, key="review-scan", source_type="review_list", **extra):
        return self.record("source_scan", {"source_url": snapshot["url"], "page_label": "Fixture page 1",
            "status": "observed", "reviews": reviews, "reason": "Fixture observed without network",
            "snapshot_ids": [snapshot["snapshot_id"]], "source_type": source_type, **extra}, key)

    def stop(self, research=None):
        return self.record("research_stop", {"code": "completion_time_reserve",
            "basis": "Reserve measured time for analysis, review and files",
            "new_findings": [], "remaining_scope": ["Unobserved paths remain unobserved"]}, "actual-stop", research)

    def test_original_product_name_and_request_are_preserved_on_replay(self):
        stored = self.store.db.execute("SELECT payload FROM conversation_requests").fetchone()[0]
        self.assertEqual(json.loads(stored), self.original)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 0)
        self.now += timedelta(seconds=45)
        replay = self.conv.open_product_workflow({**self.original, "budget_seconds": 1800})
        self.assertEqual(replay["research_id"], self.research)
        self.assertEqual(replay["workflow"]["started_at"], self.started.isoformat())
        self.assertEqual(replay["workflow"]["elapsed_seconds"], 45)
        self.assertEqual(self.store.db.execute("SELECT payload FROM conversation_requests").fetchone()[0], stored)
        self.error("request_conflict", self.conv.open_product_workflow, {**self.original, "question": "rewritten pain"})

    def test_whole_request_budget_cannot_reset_extend_or_shrink_after_restart(self):
        self.assertEqual(self.request["workflow"]["budget_seconds"], 1800)
        self.now += timedelta(seconds=70)
        self.web.close()
        self.store.close()
        self.store = StateStore(self.root / "runtime-data/product.sqlite", Dataset(ROOT / "data/business/empty"))
        self.conv = Conversation(self.store, self.root)
        self.audit = WorkflowAudit(self.store.db, self.root)
        self.web = WebEvidence(self.store.path, self.root)
        replay = self.conv.open_product_workflow({**self.original, "budget_seconds": 1800})
        self.assertEqual((replay["workflow"]["started_at"], replay["workflow"]["elapsed_seconds"]),
                         (self.started.isoformat(), 70))
        self.error("workflow_conflict", self.conv.open_product_workflow, {**self.original, "budget_seconds": 1200})
        for invalid in (True, 299, 1801):
            self.error("invalid_input", self.conv.open_product_workflow, {**self.original, "budget_seconds": invalid})
        self.assertEqual(self.audit.status(self.research)["deadline"], (self.started + timedelta(seconds=1800)).isoformat())

    def test_twenty_minute_checkpoint_records_first_actual_observation(self):
        self.now = self.started + timedelta(seconds=1199)
        self.assertIsNone(self.audit.status(self.research)["twenty_minute_checkpoint"])
        self.now = self.started + timedelta(seconds=1207)
        checkpoint = self.audit.status(self.research)["twenty_minute_checkpoint"]
        self.assertEqual(checkpoint["due_at_seconds"], 1200)
        self.assertEqual(checkpoint["observed_at"], self.now.isoformat())
        self.assertEqual((checkpoint["elapsed_seconds"], checkpoint["remaining_seconds"]), (1207, 593))
        self.now += timedelta(seconds=60)
        self.assertEqual(self.audit.status(self.research)["twenty_minute_checkpoint"], checkpoint)

    def test_older_untimed_request_cannot_be_relabelled_as_fresh(self):
        old_input = {"question": "Original older fixture", "user_submitted": True,
                     "session_id": "old-session", "request_key": "old-question"}
        old = self.conv.open_request(old_input)
        self.error("workflow_late_start", self.conv.open_product_workflow, old_input)
        self.seed_delivery()
        self.store.db.execute("UPDATE conversation_requests SET turn_id='fixture-turn' WHERE session_id='old-session'")
        self.error("workflow_late_start", self.audit.start, old["research_id"])
        self.assertFalse(self.audit.active(old["research_id"]))

    def test_snapshots_from_other_requests_and_unjournaled_ids_are_rejected(self):
        foreign = self.conv.open_request({"question": "Another explicit fixture request", "user_submitted": True,
            "session_id": "foreign-session", "request_key": "foreign-question"})
        captured = self.capture("foreign", "Foreign fixture only", research=foreign["research_id"])
        self.error("workflow_snapshot_scope", self.audit.snapshot, self.research, captured["snapshot_id"])
        self.error("workflow_snapshot_scope", self.audit.snapshot, self.research, "not-journaled")
        self.error("research_not_registered", self.conv.workflow_status, {"research_id": "invented-research"})

    def test_before_run_and_after_deadline_observations_are_not_counted(self):
        for index, observed in enumerate((self.started - timedelta(microseconds=1),
                                           self.started + timedelta(seconds=1800, microseconds=1))):
            captured = self.capture("outside-" + str(index), "Timing fixture", observed=observed)
            self.error("workflow_snapshot_time", self.audit.snapshot, self.research, captured["snapshot_id"])
        for index, observed in enumerate((self.started, self.started + timedelta(seconds=1800))):
            captured = self.capture("boundary-" + str(index), "Inclusive boundary fixture", observed=observed)
            self.assertEqual(self.audit.snapshot(self.research, captured["snapshot_id"])["observed_at"], observed.isoformat())

    def test_snapshot_tampering_does_not_become_literal_review_evidence(self):
        captured = self.capture("tamper", "RID-1 exact fixture")
        path = self.web.base / (captured["snapshot_id"] + ".json")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["text"] = "Replacement fixture"
        path.write_text(canonical(value), encoding="utf-8")
        self.error("snapshot_integrity", self.audit.snapshot, self.research, captured["snapshot_id"])

    def test_snapshot_embedded_identity_must_match_journal_and_filename(self):
        captured = self.capture("embedded-id", "RID-1 unchanged retained fixture")
        path = self.web.base / (captured["snapshot_id"] + ".json")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["snapshot_id"] = "different-embedded-identity"
        # Body-only fingerprint remains valid, so this specifically exercises
        # the embedded-ID check rather than a changed text/timestamp check.
        self.assertEqual(fingerprint({k: v for k, v in value.items() if k != "snapshot_id"}), captured["snapshot_id"])
        path.write_text(canonical(value), encoding="utf-8")
        self.error("snapshot_integrity", self.audit.snapshot, self.research, captured["snapshot_id"])
        self.assertEqual(self.web.db.execute("SELECT snapshot_id FROM web_pages").fetchone()[0], captured["snapshot_id"])

    def test_original_stop_gate_blocks_resolution_and_collection(self):
        resolve = {"session_id": self.original["session_id"], "request_key": self.original["request_key"],
            "expected_request_version": 0, "event_key": "resolve-original", "selection": {
                "model_id": "AX-R301", "model_version": "1.0", "document_version": "manual-r1"}}
        self.error("workflow_research_open", self.conv.resolve_request, resolve)
        foreign = self.conv.open_product_workflow({"question": "Foreign fixture", "user_submitted": True,
            "session_id": "foreign-session", "request_key": "foreign-question"})
        self.stop(foreign["research_id"])
        self.error("workflow_research_open", self.conv.resolve_request, resolve)
        original_bytes = self.store.db.execute("SELECT payload FROM conversation_requests WHERE session_id=?",
                                               (self.original["session_id"],)).fetchone()[0]
        self.stop()
        self.error("workflow_collection_closed", self.capture, "after-stop", "Should not be observed")
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0], 0)
        self.web.close()
        self.store.close()
        self.store = StateStore(self.root / "runtime-data/product.sqlite", Dataset(ROOT / "data/synthetic/kitchen-v1"))
        self.conv = Conversation(self.store, self.root)
        self.audit = WorkflowAudit(self.store.db, self.root)
        self.web = WebEvidence(self.store.path, self.root)
        resolved = self.conv.resolve_request(resolve)
        self.assertEqual(resolved["turn"]["input"]["question"], self.original["question"])
        self.assertEqual(self.store.db.execute("SELECT payload FROM conversation_requests WHERE session_id=?",
                                              (self.original["session_id"],)).fetchone()[0], original_bytes)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 1)

    def test_expiry_blocks_fresh_collection_without_consuming_an_attempt(self):
        self.now += timedelta(seconds=1801)
        self.assertTrue(self.audit.status(self.research)["expired"])
        self.error("workflow_collection_closed", self.capture, "late", "Late unit fixture")
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0], 0)
        self.record("research_stop", {"code": "whole_budget_expired", "basis": "Measured deadline passed",
            "new_findings": [], "remaining_scope": ["No new observation accepted"]}, "expired-stop")

    def test_source_scan_requires_a_plan_literal_quote_id_and_matching_url(self):
        captured = self.capture("review", "RID-1 Positive fixture. Qualified fixture.")
        literal = self.review(captured, "Positive fixture.")
        self.error("workflow_plan_missing", self.scan, captured, [literal])
        self.plan()
        self.error("quote_mismatch", self.scan, captured, [{**literal, "text": "invented criticism"}])
        self.error("workflow_review_identity", self.scan, captured, [{**literal, "review_id": "RID-NOT-OBSERVED"}])
        self.error("workflow_review_identity", self.scan, captured, [{**literal, "source_ids": []}])
        wrong = {**captured, "url": "https://reviews.example.org/other-product"}
        self.error("workflow_snapshot_scope", self.scan, wrong, [literal])
        self.assertEqual(self.audit.status(self.research)["event_count"], 1)

    def test_split_review_and_duplicate_observations_are_one_known_identity(self):
        self.plan()
        captured = self.capture("split", "RID-1 First literal fragment. Second literal fragment.")
        fragments = [self.review(captured, "First literal fragment.", source_ids=["split-a", "split-b"]),
                     self.review(captured, "Second literal fragment.", source_ids=["split-c"])]
        self.scan(captured, fragments + [{**fragments[0], "disposition": "duplicate", "reason": "Same observed reviewer"}])
        self.audit.record({"research_id": self.research, "event_key": "analysis", "kind": "analysis_scope",
            "data": {"source_ids": ["split-a", "split-b", "split-c"], "scope_note": "Three records, one review"}},
            SimpleNamespace(sources={sid: {} for sid in ("split-a", "split-b", "split-c")}))
        counts = self.audit.counts(self.audit.events(self.research), {"split-c"})
        provider = counts["providers"][0]
        self.assertEqual((provider["reviewed_unique_review_total"], provider["valid_unique_review_total"],
                          provider["analysed_known_unique_review_ids"], provider["proposal_used_known_unique_review_ids"]), (1, 1, 1, 1))
        self.assertEqual(provider["retained_literal_observation_count"], 2)
        self.assertEqual(provider["exclusions"], {"duplicate": 1})
        self.assertEqual(counts["analysed_source_record_count"], 3)
        self.assertIn("never independent customers", provider["counts_are"])

    def test_identity_unknown_remains_null_and_unanalysed_usage_is_unknown(self):
        self.plan()
        captured = self.capture("unknown", "Observed fixture with no stable review identifier")
        self.scan(captured, [self.review(captured, "Observed fixture", review_id=None)])
        provider = self.audit.status(self.research)["counts"]["providers"][0]
        self.assertIsNone(provider["reviewed_unique_review_total"])
        self.assertIsNone(provider["valid_unique_review_total"])
        self.assertIsNone(provider["proposal_used_known_unique_review_ids"])
        self.assertEqual((provider["reviewed_identity_unknown_observations"], provider["retained_identity_unknown_observations"]), (1, 1))
        rows = next(b for b in self.audit.report_section(self.research, self.store.dataset)["blocks"] if b["type"] == "table")["rows"]
        self.assertEqual((rows[0][1], rows[0][4], rows[0][5]), ("미확인", "미확인", "미확인"))

    def test_same_host_different_url_id_collision_stays_identity_unknown(self):
        self.plan()
        body = "RID-1 Shared literal ID and identical observed fixture"
        first = self.capture("namespace-a", body, url="https://reviews.example.org/product-a")
        second = self.capture("namespace-b", body, url="https://reviews.example.org/product-b")
        self.scan(first, [self.review(first, body, source_ids=["namespace-a"])], key="namespace-scan-a")
        self.scan(second, [self.review(second, body, source_ids=["namespace-b"])], key="namespace-scan-b")
        provider = self.audit.counts(self.audit.events(self.research), {"namespace-a", "namespace-b"})["providers"][0]
        self.assertEqual(provider["namespace_ambiguous_literal_ids"], ["RID-1"])
        self.assertIsNone(provider["reviewed_unique_review_total"])
        self.assertIsNone(provider["valid_unique_review_total"])
        self.assertEqual((provider["reviewed_known_unique_ids"], provider["retained_known_unique_review_ids"]), (0, 0))
        self.assertEqual((provider["reviewed_identity_unknown_observations"],
                          provider["retained_identity_unknown_observations"],
                          provider["proposal_used_identity_unknown_observations"]), (2, 2, 2))
        self.assertEqual(provider["proposal_used_known_unique_review_ids"], 0)
        # Ambiguous identity must not erase either original URL or full quote.
        self.assertEqual({s["url"] for s in self.audit.review_sources(self.research)}, {first["url"], second["url"]})
        self.assertTrue(all(s["text"] == body for s in self.audit.review_sources(self.research)))

    def test_document_scan_is_not_a_zero_review_survey_but_observed_empty_list_is_zero(self):
        self.plan()
        document = self.capture("doc", "Exact-model manual fixture", url="https://manual.example.org/wf-test")
        self.scan(document, [], source_type="manual", key="manual-scan")
        empty_list = self.capture("empty-list", "No review entries visible", url="https://reviews.example.org/empty")
        self.scan(empty_list, [], source_type="review_list", key="empty-review-list", list_total=0)
        providers = {p["provider"]: p for p in self.audit.status(self.research)["counts"]["providers"]}
        self.assertIsNone(providers["manual.example.org"]["reviewed_unique_review_total"])
        self.assertEqual(providers["reviews.example.org"]["reviewed_unique_review_total"], 0)
        self.assertEqual(providers["manual.example.org"]["retained_literal_observation_count"], 0)

    def test_full_literal_context_is_kept_and_catalog_import_requires_matching_audit(self):
        self.plan()
        body = "RID-1 WF-TEST. 만족합니다. 다만 조건 A에서 불편합니다. 조건 B에서는 괜찮습니다."
        captured = self.capture("full", body)
        observation = self.review(captured, body, source_ids=["review-source"], text_coverage="full_review_observed",
            model_option="WF-TEST", usage_conditions="조건 A와 조건 B", positive_context="만족합니다.",
            qualified_context="조건 B에서는 괜찮습니다.", published_date=None, purchase_date=None)
        self.scan(captured, [observation])
        self.scan(captured, [observation], key="re-observed-same-review")
        sources = self.audit.review_sources(self.research)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["text"], body)
        self.assertIn("full_review_observed", sources[0]["model"])
        self.assertIn("게시일: 미확인", sources[0]["model"])
        self.assertIn("만족합니다.", sources[0]["model"])
        entry = {"kind": "review", "source_id": "review-source", "snapshot_id": captured["snapshot_id"],
                 "support_quote": "다만 조건 A에서 불편합니다."}
        self.audit.check_review_import(self.research, entry)
        for change in ({"source_id": "unplanned-source"}, {"snapshot_id": "wrong-snapshot"},
                       {"support_quote": "AI summary replacing original"}):
            self.error("workflow_review_audit_missing", self.audit.check_review_import, self.research, {**entry, **change})
        self.error("workflow_review_audit_missing", self.web.import_evidence, self.store.dataset,
            {"research_id": self.research, "data_version": "new-fixture-v1", "observations": [{**entry, "source_id": "unplanned-source"}]})
        self.error("workflow_snapshot_scope", self.web.import_evidence, self.store.dataset,
            {"data_version": "new-fixture-v1", "observations": [entry]})

    def test_event_replay_cannot_rewrite_observations_and_analysis_ids_must_exist(self):
        self.plan()
        event = {"research_id": self.research, "event_key": "analysis", "kind": "analysis_scope",
                 "data": {"source_ids": ["observed"], "scope_note": "Only observed catalog record"}}
        self.error("workflow_analysis_scope", self.audit.record, event, SimpleNamespace(sources={}))
        first = self.audit.record(event, SimpleNamespace(sources={"observed": {}}))
        self.assertEqual(self.audit.record(event)["event_count"], first["event_count"])
        changed = copy.deepcopy(event)
        changed["data"]["source_ids"] = ["invented"]
        self.error("workflow_conflict", self.audit.record, changed, SimpleNamespace(sources={"invented": {}}))

    def test_analysis_wrong_catalog_reports_repair_without_recording_failed_event(self):
        self.plan()
        event = {"research_id": self.research, "event_key": "repairable-analysis", "kind": "analysis_scope",
                 "data": {"source_ids": ["observed"], "scope_note": "Read from an explicitly selected local catalog"}}
        before = self.audit.events(self.research)
        with self.assertRaises(ToolError) as caught:
            self.audit.record(event, SimpleNamespace(sources={}))
        self.assertEqual(caught.exception.code, "workflow_analysis_scope")
        self.assertIn("0 records", str(caught.exception))
        self.assertIn("--data", str(caught.exception))
        self.assertIn("local catalogs are supported", str(caught.exception))
        self.assertEqual(self.audit.events(self.research), before)
        self.audit.record(event, SimpleNamespace(sources={"observed": {}}))
        events = [row for row in self.audit.events(self.research) if row["event_key"] == "repairable-analysis"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["data"]["source_ids"], ["observed"])

    def test_catalog_link_requires_review_kind_matching_url_and_literal_text(self):
        self.plan()
        body = "RID-1 Positive fixture. Qualified fixture."
        captured = self.capture("catalog-review", body)
        self.scan(captured, [self.review(captured, body)])
        source = {"kind": "review", "text": "Qualified fixture.", "origin": {"source_url": captured["url"]}}
        self.audit.check_catalog(self.research, SimpleNamespace(sources={"review-source": source}))
        for bad_source in (None, {**source, "kind": "product_fact"},
                           {**source, "origin": {"source_url": "https://reviews.example.org/other"}},
                           {**source, "text": "Fabricated catalog meaning"}):
            sources = {} if bad_source is None else {"review-source": bad_source}
            self.error("workflow_review_audit_missing", self.audit.check_catalog, self.research,
                       SimpleNamespace(sources=sources))
        self.stop()
        self.error("workflow_review_audit_missing", self.conv.resolve_request, {
            "session_id": self.original["session_id"], "request_key": self.original["request_key"],
            "expected_request_version": 0, "event_key": "resolve-unknown-catalog",
            "selection": {"model_id": "WF-TEST"}})
        paths = self.seed_delivery()
        self.error("workflow_review_audit_missing", self.conv.record_workflow_event, self.finish_event(paths))
        self.assertIsNone(self.audit.status(self.research)["finished_at"])

    def test_status_preview_does_not_discard_full_request_export_events(self):
        self.plan()
        self.web.configure({"research_id": self.research, "max_pages": 8, "reason": "Eight explicit unit pages"})
        for index in range(8):
            captured = self.capture("manual-" + str(index), "Unit manual topic " + str(index),
                                    url="https://manual.example.org/topic" + str(index))
            self.scan(captured, [], key="scan-" + str(index), source_type="manual")
        provider = self.audit.status(self.research)["counts"]["providers"][0]
        self.assertEqual((provider["scan_count"], provider["source_url_count"]), (8, 8))
        self.assertEqual((len(provider["scans"]), len(provider["source_urls"])), (6, 6))
        exported = self.conv.export_session({"session_id": self.original["session_id"]})
        payload = json.loads((self.root / exported["path"]).read_text(encoding="utf-8"))
        scans = [event for event in payload["requests"][0]["workflow_events"] if event["kind"] == "source_scan"]
        self.assertEqual(len(scans), 8)
        self.assertEqual(scans[0]["data"]["source_url"], "https://manual.example.org/topic0")

    def seed_delivery(self, version=2):
        # SQLite/byte fixtures isolate saved-state/path/hash binding, not AI
        # review, semantic sufficiency, or DOCX/PDF rendering.
        turn = "fixture-turn"
        planning = json.loads((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
        planning.update(session_id=self.original["session_id"], request_key=self.original["request_key"],
                        question=self.original["question"], data_version=self.store.dataset.version)
        self.store.db.execute("""INSERT INTO turns(turn_id,session_id,request_key,input_json,context_hash,dataset_hash,
            code_hash,status,valid,result_version,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (turn, self.original["session_id"], self.original["request_key"], canonical(planning), "fixture-context",
             self.store.dataset.fingerprint, self.store.code_hash, "completed", 1, 2, self.now.isoformat()))
        result = {"concepts": []}
        self.store.db.execute("INSERT INTO results VALUES(?,?,?,?,?,?,?)", (turn, "fixture-result", canonical(result),
            fingerprint(result), 2, self.now.isoformat(), canonical({"contract_valid": True})))
        self.store.db.execute("UPDATE conversation_requests SET turn_id=? WHERE session_id=?", (turn, self.original["session_id"]))
        paths = ["runtime-data/deliverables/fixture/" + name for name in
                 ("product.xlsx", "reviews.xlsx", "market.xlsx", "charts.xlsx", "report.docx", "report.pdf")]
        hashes = {}
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("Byte fixture only: " + name).encode("utf-8"))
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.store.db.execute("INSERT INTO reader_deliveries VALUES(?,?,?,?,?)",
            (turn, version, "fixture-plan", canonical({"ready": True,
             "workflow_audit_hash": self.audit.report_audit_hash(self.research)}), canonical(hashes)))
        return paths

    def finish_event(self, paths, key="finish"):
        return {"research_id": self.research, "event_key": key, "kind": "finish",
            "data": {"delivered_paths": paths, "layout_review": {"status": "not_run", "scope": "Byte fixtures; rendering not run"}}}

    def test_finish_rejects_stale_version_changed_hash_subset_and_invalid_turn(self):
        paths = self.seed_delivery(version=1)
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths))
        self.store.db.execute("UPDATE reader_deliveries SET result_version=2")
        report = self.root / paths[-1]
        original = report.read_bytes()
        report.write_bytes(original + b" altered")
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths))
        report.write_bytes(original)
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths[:-1]))
        self.store.db.execute("UPDATE turns SET valid=0")
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths))
        self.assertIsNone(self.audit.status(self.research)["finished_at"])

    def test_finish_matches_normalized_current_paths_and_freezes_measured_end(self):
        paths = self.seed_delivery()
        normalized = [name.replace("/fixture/", "/fixture/../fixture/./") for name in paths]
        normalized[0] = str((self.root / paths[0]).resolve())
        self.now += timedelta(seconds=1700)
        finished = self.conv.record_workflow_event(self.finish_event(normalized))
        self.assertEqual((finished["finished_at"], finished["elapsed_seconds"], finished["expired"]),
                         (self.now.isoformat(), 1700, False))
        self.now += timedelta(seconds=500)
        self.assertEqual(self.audit.status(self.research)["elapsed_seconds"], 1700)
        self.assertEqual(self.conv.record_workflow_event(self.finish_event(normalized))["finished_at"], finished["finished_at"])
        self.error("workflow_finished", self.record, "checkpoint", {"remaining_tasks": ["New task after finish"]}, "late-event")

    def test_layout_pass_declaration_is_not_image_inspection_certification(self):
        paths = self.seed_delivery()
        event = self.finish_event(paths)
        event["data"]["layout_review"] = {"status": "passed", "scope": "Caller claims image review"}
        finished = self.conv.record_workflow_event(event)
        review = finished["layout_review"]
        self.assertEqual(review["declared_status"], "passed")
        self.assertEqual(review["verification_status"], "not_verified")
        self.assertIsNone(review["verified_image_inspection"])
        self.assertEqual(self.audit.events(self.research)[-1]["data"]["layout_review"], event["data"]["layout_review"])

    def test_no_layout_event_does_not_claim_review_or_zero_defects(self):
        review = self.audit.status(self.research)["layout_review"]
        self.assertEqual(review["declared_status"], "not_run")
        self.assertIsNone(review["scope"])
        self.assertIsNone(review["verified_image_inspection"])

    def test_finish_rejects_external_path_and_unready_receipt(self):
        paths = self.seed_delivery()
        outside = self.root / "outside-runtime.pdf"
        outside.write_bytes(b"External to runtime-data")
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event([str(outside), *paths[1:]]))
        self.store.db.execute("UPDATE reader_deliveries SET response=?", (canonical({"ready": False}),))
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths))

    def test_old_reader_cannot_finish_after_new_analysis_journal_event(self):
        self.plan()
        paths = self.seed_delivery()
        prior_hash = self.audit.report_audit_hash(self.research)
        self.record("checkpoint", {"remaining_tasks": ["Final QA"]}, "qa-checkpoint")
        self.assertEqual(self.audit.report_audit_hash(self.research), prior_hash)
        file_hashes = self.store.db.execute("SELECT file_hashes FROM reader_deliveries").fetchone()[0]
        self.audit.record({"research_id": self.research, "event_key": "later-analysis", "kind": "analysis_scope",
            "data": {"source_ids": ["later-observed-source"], "scope_note": "Newly reported analysis scope"}},
            SimpleNamespace(sources={"later-observed-source": {}}))
        self.assertNotEqual(self.audit.report_audit_hash(self.research), prior_hash)
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, self.finish_event(paths))
        self.assertIsNone(self.audit.status(self.research)["finished_at"])
        self.assertEqual(self.store.db.execute("SELECT result_version FROM turns").fetchone()[0], 2)
        self.assertEqual(self.store.db.execute("SELECT file_hashes FROM reader_deliveries").fetchone()[0], file_hashes)
        for name, digest in json.loads(file_hashes).items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)

    def test_finished_workflow_blocks_new_candidate_but_preserves_same_key_replay(self):
        paths = self.seed_delivery()
        finished = self.conv.record_workflow_event(self.finish_event(paths))
        stored = self.store.db.execute("SELECT payload FROM results WHERE result_key='fixture-result'").fetchone()[0]
        replay = self.store.save_result(self.original["session_id"], "fixture-turn", "fixture-result",
                                       json.loads(stored), 2, response_mode="receipt")
        self.assertTrue(replay["accepted"])
        self.assertEqual(replay["turn"]["result_version"], 2)
        self.assertEqual(replay["receipt"]["result_sha256"], fingerprint(json.loads(stored)))
        self.error("workflow_finished", self.store.save_result, self.original["session_id"], "fixture-turn",
                   "new-candidate-after-finish", json.loads(stored), 2)
        self.error("result_conflict", self.store.save_result, self.original["session_id"], "fixture-turn",
                   "fixture-result", {"concepts": ["Changed original candidate"]}, 2)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM results").fetchone()[0], 1)
        self.assertEqual(self.store.db.execute("SELECT payload FROM results").fetchone()[0], stored)
        self.assertEqual(self.audit.status(self.research)["finished_at"], finished["finished_at"])

    def test_late_finished_save_replay_uses_actual_file_confirmation_time(self):
        self.stop()
        self.web.close()
        self.store.close()
        self.store = StateStore(self.root / "runtime-data/product.sqlite", Dataset(ROOT / "data/synthetic/kitchen-v1"))
        self.conv = Conversation(self.store, self.root)
        self.audit = WorkflowAudit(self.store.db, self.root)
        self.web = WebEvidence(self.store.path, self.root)
        turn = self.conv.resolve_request({"session_id": self.original["session_id"], "request_key": self.original["request_key"],
            "expected_request_version": 0, "event_key": "resolve-file-clock", "selection": {
                "model_id": "AX-R301", "model_version": "1.0", "document_version": "manual-r1"}})["turn"]
        payload = {"session_id": turn["session_id"], "turn_id": turn["turn_id"], "result_key": "reviewed-held-fixture",
            "result": held_fixture(), "expected_result_version": 0,
            "assessment": {"claim_checks": [], "feature_matches": [], "concept_links": []},
            "report": True, "open_folder": False}

        def create(workspace, planning, result, sources, **options):
            self.assertEqual(Path(workspace), self.root)
            self.assertFalse(options["open_folder"])
            directory = self.root / "runtime-data/deliverables/current-reader"
            directory.mkdir(parents=True)
            files = []
            for name in ("product.xlsx", "reviews.xlsx", "market.xlsx", "charts.xlsx", "report.docx", "report.pdf"):
                path = directory / name
                path.write_bytes(("File confirmation fixture only: " + name).encode())
                files.append({"path": str(path), "kind": path.suffix[1:], "title": name})
            return {"ready": True, "directory": str(directory), "files": files, "checks": {"errors": []}}

        with patch("product_tools.delivery.create_deliverables", side_effect=create) as render:
            self.now = self.started + timedelta(seconds=1000)
            first = self.conv.save_and_export(payload)
            self.assertTrue(first["report_ready"])
            self.assertTrue(first["workflow_files_within_budget"])
            self.assertEqual(first["workflow_file_confirmation_at"], self.now.isoformat())
            files = first["report"]["files"]
            digests = {f["path"]: hashlib.sha256(Path(f["path"]).read_bytes()).hexdigest() for f in files}
            self.now = self.started + timedelta(seconds=1700)
            self.conv.record_workflow_event(self.finish_event([f["path"] for f in files]))
            self.now = self.started + timedelta(seconds=1801)
            replay = self.conv.save_and_export(payload)
        self.assertTrue(replay["save"]["accepted"])
        self.assertTrue(replay["report_ready"])
        self.assertTrue(replay["report"]["reused"])
        self.assertFalse(replay["workflow_files_within_budget"])
        self.assertEqual(replay["workflow_file_confirmation_at"], self.now.isoformat())
        self.assertEqual(replay["workflow"]["elapsed_seconds"], 1700)
        self.assertFalse(replay["workflow"]["expired"])
        self.assertEqual(replay["save"]["turn"]["result_version"], 1)
        self.assertEqual(replay["report"]["files"], files)
        self.assertEqual(render.call_count, 1)
        self.assertEqual({name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in digests}, digests)


class StandaloneWorkflowCompatibilityTests(unittest.TestCase):
    def test_empty_web_workflow_tables_do_not_break_standalone_state_store(self):
        scratch = TEST_ROOT / "runtime-data"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="legacy-workflow-unit-", dir=scratch) as temporary:
            workspace = Path(temporary).resolve()
            database = workspace / "state.sqlite"
            web = WebEvidence(database, workspace)
            try:
                web.collect({"research_id": "legacy-fixture", "page_id": "fixture-page",
                    "url": "https://fixtures.example.org/legacy", "observed_text": "Legacy unit fixture only",
                    "native_tool_name": "unit_fixture_no_browser_executed"}, True)
                self.assertEqual(web.db.execute("SELECT COUNT(*) FROM product_workflows").fetchone()[0], 0)
                self.assertIsNone(web.db.execute("SELECT name FROM sqlite_master WHERE name='conversation_requests'").fetchone())
            finally:
                web.close()
            store = StateStore(database, Dataset(ROOT / "data/synthetic/kitchen-v1"))
            try:
                planning = json.loads((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
                turn = store.start_turn(planning, True)
                saved = store.save_result(planning["session_id"], turn["turn_id"], "standalone-held-fixture", held_fixture(), 0)
                self.assertTrue(saved["accepted"])
                self.assertEqual((saved["turn"]["status"], saved["turn"]["result_version"]), ("held", 1))
                self.assertIsNone(store.db.execute("SELECT name FROM sqlite_master WHERE name='conversation_requests'").fetchone())
                self.assertEqual(store.db.execute("SELECT COUNT(*) FROM product_workflows").fetchone()[0], 0)
                self.assertEqual(store.db.execute("SELECT COUNT(*) FROM results").fetchone()[0], 1)
            finally:
                store.close()
                self.assertTrue(workspace.is_relative_to(scratch.resolve()))


class RetrievalOffsetTests(unittest.TestCase):
    def setUp(self):
        (TEST_ROOT / "runtime-data").mkdir(exist_ok=True)

    def test_twenty_record_batch_is_not_the_investigation_endpoint(self):
        exact = {"model_id": "WF-CATALOG", "model_version": "v1", "document_version": "fixture-doc"}
        other = {**exact, "model_id": "WF-OTHER"}
        with tempfile.TemporaryDirectory(prefix="large-offset-unit-", dir=TEST_ROOT / "runtime-data") as scratch:
            base = Path(scratch)
            models = [{**scope, "name": "Generated pagination fixture", "product_family": "refrigerator", "synthetic": True}
                      for scope in (exact, other)]
            records = []
            for index in range(26):
                body = "Pagination unit fixture " + str(index)
                records.append({**(exact if index < 25 else other), "source_id": "fixture-review-" + str(index),
                    "kind": "review", "data_version": "workflow-offset-fixture", "location": "Generated fixture row",
                    "text": body, "synthetic": True, "sha256": hashlib.sha256(body.encode()).hexdigest(),
                    "origin": {"source_url": None, "retrieved_date": "2026-10-12", "published_date": None,
                               "representation": "synthetic", "model_matching": "fictional",
                               "purchase_verified": None, "sponsorship": None}})
            files = {"models.json": canonical(models).encode(),
                     "sources.jsonl": ("\n".join(canonical(record) for record in records) + "\n").encode()}
            for name, raw in files.items():
                (base / name).write_bytes(raw)
            manifest = {"data_version": "workflow-offset-fixture", "synthetic": True, "purpose": "test_only",
                "created_date": "2026-10-12", "provenance": "Generated unit data; no customer observations",
                "model_count": 2, "scope_count": 2, "review_count": 26, "fact_count": 0,
                "files": [{"path": name, "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in files.items()]}
            (base / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
            data = Dataset(base)
            first = data.retrieve("review", exact, limit=20)
            second = data.retrieve("review", exact, limit=20, offset=first["next_offset"])
            self.assertEqual((first["total"], len(first["records"]), first["next_offset"]), (25, 20, 20))
            self.assertEqual((second["total"], len(second["records"]), second["next_offset"]), (25, 5, None))
            self.assertEqual([s["source_id"] for s in first["records"] + second["records"]],
                             ["fixture-review-" + str(index) for index in range(25)])
            self.assertTrue(all(record["model_id"] == exact["model_id"] for record in first["records"] + second["records"]))
            self.assertTrue(base.resolve().is_relative_to((TEST_ROOT / "runtime-data").resolve()))

    def test_all_offset_batches_and_cache_preserve_exact_scope_and_unknown_feature(self):
        data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        exact = {"model_id": "AX-R301", "model_version": "1.0", "document_version": "manual-r1"}
        expected = [s["source_id"] for s in data.sources.values() if s["kind"] == "review"
                    and all(s[k] == v for k, v in exact.items())]
        self.assertGreater(len(expected), 1)
        with tempfile.TemporaryDirectory(prefix="offset-unit-", dir=TEST_ROOT / "runtime-data") as scratch:
            store = StateStore(Path(scratch) / "state.sqlite", data)
            try:
                actual, offset = [], 0
                while True:
                    page = store.retrieve("review", exact, limit=1, offset=offset)
                    self.assertFalse(page["cache_hit"])
                    self.assertEqual(page["offset"], offset)
                    self.assertEqual(page["total"], len(expected))
                    self.assertEqual(page["scope"], exact)
                    self.assertEqual(page["records"][0]["content_trust"], "untrusted_source_data")
                    actual.extend(s["source_id"] for s in page["records"])
                    cached = store.retrieve("review", exact, limit=1, offset=offset)
                    self.assertTrue(cached["cache_hit"])
                    self.assertEqual(cached["records"], page["records"])
                    if page["next_offset"] is None:
                        self.assertFalse(page["truncated"])
                        break
                    self.assertTrue(page["truncated"])
                    offset = page["next_offset"]
                self.assertEqual(actual, expected)
                self.assertEqual(len(set(actual)), len(expected))
                beyond = store.retrieve("review", exact, limit=1, offset=len(expected))
                self.assertEqual((beyond["records"], beyond["total"], beyond["next_offset"]), ([], len(expected), None))
                unknown = store.retrieve("product_fact", exact, feature_key="unobserved_feature", offset=2)
                self.assertEqual(unknown["feature_presence"], "not_documented")
                cli_spec = importlib.util.spec_from_file_location("workflow_test_cli", ROOT / "product-tools/cli.py")
                cli = importlib.util.module_from_spec(cli_spec)
                cli_spec.loader.exec_module(cli)
                via_cli = cli.dispatch(data, store, "retrieve_reviews", {"scope": exact, "limit": 1, "offset": 1})
                self.assertEqual(via_cli["records"][0]["source_id"], expected[1])
                self.assertTrue(via_cli["cache_hit"])
                for invalid in (True, -1, 1000001):
                    with self.assertRaises(ToolError) as caught:
                        store.retrieve("review", exact, offset=invalid)
                    self.assertEqual(caught.exception.code, "invalid_input")
                self.assertEqual(store.db.execute("SELECT COUNT(*) FROM retrieval_cache").fetchone()[0], len(expected) + 2)
            finally:
                store.close()
                self.assertTrue(Path(scratch).resolve().is_relative_to((TEST_ROOT / "runtime-data").resolve()))


if __name__ == "__main__":
    unittest.main()
