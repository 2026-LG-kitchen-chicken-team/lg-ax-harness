"""Synthetic source transport/coverage checks; no semantic or native-AI claim."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint, strict_json
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.evidence_coverage import EvidenceCoverage
from product_tools.state import StateStore
from product_tools.tools import ProductTools
from product_tools.workflow import WorkflowAudit


class EvidenceCoverageTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runtime-data")
        self.root = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store = StateStore(self.root / "runtime-data/product.sqlite", self.data)
        self.conv = Conversation(self.store, self.root)
        self.cover = EvidenceCoverage(self.store)
        self.planning = strict_json((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
        self.session = self.planning["session_id"]
        self.turn = self.store.start_turn(self.planning, True)["turn_id"]
        self.handle = {"session_id": self.session, "turn_id": self.turn}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def error(self, code, call, *args):
        with self.assertRaises(ToolError) as caught:
            call(*args)
        self.assertEqual(caught.exception.code, code)

    def all_dispositions(self, disposition="reviewed"):
        _, selected = self.cover.context(self.session, self.turn)
        return [{"source_id": s["source_id"], "disposition": disposition,
                 "reason": "Synthetic fixture interpretation; semantic correctness is not certified"} for s in selected]

    def test_inventory_does_not_certify_unseen_or_semantic_coverage(self):
        result = self.cover.evidence_inventory(self.handle)
        self.assertGreater(result["selected_count"], 3)
        self.assertEqual(result["delivered_count"], 0)
        self.assertFalse(result["structurally_complete"])
        self.assertEqual(result["semantic_status"], "unverified")
        self.assertEqual(sum(x["registered"] for x in result["by_scope_kind"]), result["selected_count"])

    def test_batch_pagination_retains_all_text_and_duplicate_delivery_counts_once(self):
        offset, ids = 0, []
        while offset is not None:
            batch = self.cover.read_evidence_batch({**self.handle, "offset": offset, "limit": 2})
            again = self.cover.read_evidence_batch({**self.handle, "offset": offset, "limit": 2})
            self.assertEqual(batch, again)
            for ref in batch["evidence_refs"]:
                self.assertEqual(ref, self.data.reference(self.data.source(ref["source_id"])))
            ids += [r["source_id"] for r in batch["evidence_refs"]]
            offset = batch["next_offset"]
        result = self.cover.evidence_coverage(self.handle)
        self.assertEqual((len(ids), len(set(ids))), (result["selected_count"], result["selected_count"]))
        self.assertEqual(result["delivered_count"], result["selected_count"])
        self.assertEqual(result["caller_reviewed_count"], 0)
        self.assertFalse(result["structurally_complete"])

    def test_undelivered_review_rejected_and_exclusion_does_not_fake_delivery(self):
        records = self.all_dispositions()
        self.error("evidence_not_delivered", self.cover.record_evidence_review,
                   {**self.handle, "review_key": "first", "records": records})
        excluded = self.cover.record_evidence_review({**self.handle, "review_key": "exclude",
                                                     "records": self.all_dispositions("excluded")})
        self.assertEqual(excluded["unresolved_count"], 0)
        self.assertGreater(excluded["missing_delivery_count"], 0)
        self.assertFalse(excluded["structurally_complete"])

    def test_review_replay_key_conflict_and_complete_gate(self):
        self.cover.read_evidence_batch(self.handle)
        payload = {**self.handle, "review_key": "review", "records": self.all_dispositions()}
        result = self.cover.record_evidence_review(payload)
        self.assertTrue(result["structurally_complete"])
        self.assertEqual(self.cover.record_evidence_review(payload), result)
        changed = copy.deepcopy(payload)
        changed["records"][0]["reason"] = "A different rationale cannot replace history"
        self.error("review_conflict", self.cover.record_evidence_review, changed)
        self.cover.require_complete(self.session, self.turn)

    def test_wrong_scope_version_and_cancel_cannot_record_coverage(self):
        self.error("scope_mismatch", self.cover.read_evidence_batch,
                   {**self.handle, "source_ids": ["outside-model-source"]})
        self.store.code_hash = "changed"
        self.error("stale_context", self.cover.read_evidence_batch, self.handle)
        self.store.code_hash = self.store.row(self.session, self.turn)["code_hash"]
        self.store.db.execute("UPDATE turns SET status='cancelled' WHERE turn_id=?", (self.turn,))
        self.error("terminal_turn", self.cover.record_evidence_review,
                   {**self.handle, "review_key": "cancel", "records": []})

    def test_initial_bundle_records_only_actual_full_references(self):
        response = {"reused_request": False, "turn": self.store.get_turn(self.session, self.turn), "previous": None}
        bundle = self.conv._bundle(response)["bundle"]
        count = self.cover.evidence_coverage(self.handle)["delivered_count"]
        self.assertEqual(count, len(bundle["included_source_ids"]))
        self.assertEqual(self.cover.evidence_coverage(self.handle)["caller_reviewed_count"], 0)

    def test_completed_600_workflow_requires_all_reviewed_but_held_preserves_missing(self):
        request = self.planning["request_key"]
        self.store.db.execute("INSERT INTO conversation_requests(session_id,request_key,payload,turn_id) VALUES(?,?,?,?)",
                              (self.session, request, canonical({"question": "fixture"}), self.turn))
        research = "research-"+fingerprint([self.session, request])
        audit = WorkflowAudit(self.store.db, self.root)
        if not audit.active(research):
            self.store.db.execute("INSERT INTO product_workflows(research_id,started_at,budget_seconds) VALUES(?,?,?)",
                                 (research, datetime.now(timezone.utc).isoformat(), 600))
        self.error("evidence_coverage_incomplete", self.store.require_evidence_coverage, self.session, self.turn)
        self.cover.read_evidence_batch(self.handle)
        self.error("evidence_coverage_incomplete", self.store.require_evidence_coverage, self.session, self.turn)
        self.cover.record_evidence_review({**self.handle, "review_key": "all", "records": self.all_dispositions()})
        self.store.require_evidence_coverage(self.session, self.turn)
        self.store.db.execute("UPDATE product_workflows SET budget_seconds=1800 WHERE research_id=?", (research,))
        self.store.db.execute("DELETE FROM evidence_reviews")
        self.store.require_evidence_coverage(self.session, self.turn)

    def test_actual_completed_save_rejects_missing_coverage_and_same_turn_revision_can_pass(self):
        self.test_completed_600_workflow_requires_all_reviewed_but_held_preserves_missing()
        self.store.db.execute("UPDATE product_workflows SET budget_seconds=600")
        import test_tools as generated_fixture
        self.tools = ProductTools(self.data)
        candidate = generated_fixture.CommonToolsTests.result(self)
        saved = self.store.save_result(self.session, self.turn, "missing", candidate, 0)
        self.assertFalse(saved["accepted"])
        self.assertEqual(saved["reason"], "evidence_coverage_incomplete")
        self.cover.record_evidence_review({**self.handle, "review_key": "restored", "records": self.all_dispositions()})
        candidate["revisions"] = 1
        saved = self.store.save_result(self.session, self.turn, "corrected", candidate, 1)
        self.assertTrue(saved["accepted"])
        self.assertEqual(saved["turn"]["result_version"], 2)

    def test_adaptive_batch_preserves_long_quotes_without_skipping_offsets(self):
        catalog = self.root / "catalog"
        shutil.copytree(self.data.root, catalog)
        sources = [strict_json(x) for x in (catalog / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
        for source in sources:
            source["text"] = "긴원문계약시험" * 500
            source["sha256"] = hashlib.sha256(source["text"].encode("utf-8")).hexdigest()
        (catalog / "sources.jsonl").write_text("".join(canonical(s)+"\n" for s in sources), encoding="utf-8")
        manifest = strict_json((catalog / "manifest.json").read_text(encoding="utf-8"))
        for file in manifest["files"]:
            file["sha256"] = hashlib.sha256((catalog / file["path"]).read_bytes()).hexdigest()
        manifest["data_version"] = "new-long-fixture"
        for source in sources:
            source["data_version"] = manifest["data_version"]
        (catalog / "sources.jsonl").write_text("".join(canonical(s)+"\n" for s in sources), encoding="utf-8")
        for file in manifest["files"]:
            file["sha256"] = hashlib.sha256((catalog / file["path"]).read_bytes()).hexdigest()
        (catalog / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        self.store.close()
        self.data = Dataset(catalog)
        self.store = StateStore(self.root / "long.sqlite", self.data)
        self.cover = EvidenceCoverage(self.store)
        self.planning["data_version"] = self.data.version
        self.turn = self.store.start_turn(self.planning, True)["turn_id"]
        self.handle["turn_id"] = self.turn
        batch = self.cover.read_evidence_batch({**self.handle, "max_bytes": 18000})
        self.assertTrue(batch["byte_limited"])
        self.assertEqual(batch["next_offset"], len(batch["evidence_refs"]))
        self.assertLessEqual(len(canonical(batch).encode("utf-8")), 18000)
        self.assertEqual(batch["evidence_refs"][0]["quote"], "긴원문계약시험" * 500)


class ShortClockTests(unittest.TestCase):
    def test_early_finish_without_research_stop_closes_future_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StateStore(root/"state.sqlite", Dataset(ROOT/"data/business/empty"))
            try:
                conv = Conversation(store, root)
                start = datetime(2026, 10, 12, tzinfo=timezone.utc)
                with patch("product_tools.workflow.utc_now", return_value=start):
                    request = conv.open_product_workflow({"question": "Early-finish clock fixture", "user_submitted": True,
                                                         "session_id": "finished", "request_key": "finished"})
                audit = WorkflowAudit(store.db, root)
                with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=50)):
                    finished = audit.finish(request["research_id"])
                self.assertIsNone(finished["research_stopped_at"])
                self.assertFalse(finished["expired"])
                self.assertFalse(finished["collection_reserve_active"])
                with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=1000)):
                    self.assertEqual(audit.status(request["research_id"])["elapsed_seconds"], 50)
                    with self.assertRaises(ToolError) as caught:
                        audit.collection_allowed(request["research_id"])
                    self.assertEqual(caught.exception.code, "workflow_collection_closed")
            finally:
                store.close()

    def test_historical_600_target_300_reserve_90_no_budget_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StateStore(root / "state.sqlite", Dataset(ROOT / "data/business/empty"))
            self.addCleanup(store.close)
            conv = Conversation(store, root)
            start = datetime(2026, 10, 12, tzinfo=timezone.utc)
            original = {"question": "Fresh empty-catalog fixture", "user_submitted": True, "session_id": "clock", "request_key": "clock"}
            with patch("product_tools.workflow.utc_now", return_value=start):
                response = conv.open_product_workflow({**original, "budget_seconds": 600})
            audit = WorkflowAudit(store.db, root)
            # A row without the new policy is a preserved pre-migration clock.
            store.db.execute("UPDATE product_workflows SET timing_policy=NULL WHERE research_id=?", (response["research_id"],))
            with patch("product_tools.workflow.utc_now", return_value=start):
                response["workflow"] = audit.status(response["research_id"])
            self.assertEqual(response["workflow"]["budget_seconds"], 600)
            self.assertEqual(response["workflow"]["target_seconds"], 300)
            with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=300)):
                checkpoint = audit.status(response["research_id"])
                self.assertTrue(checkpoint["target_checkpoint_due"])
                self.assertEqual(checkpoint["target_checkpoint"]["elapsed_seconds"], 300)
            with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=510)):
                with self.assertRaises(ToolError) as caught:
                    audit.collection_allowed(response["research_id"])
                self.assertEqual(caught.exception.code, "workflow_collection_closed")
            with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=601)):
                self.assertTrue(audit.status(response["research_id"])["expired"])
                with self.assertRaises(ToolError) as caught:
                    conv.open_product_workflow({**original, "budget_seconds": 1800})
                self.assertEqual(caught.exception.code, "workflow_conflict")
            store.close()


if __name__ == "__main__":
    unittest.main()
