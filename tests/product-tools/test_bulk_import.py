"""Large generated originals and partial failure, never live customer evidence."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.bulk_import import BulkImporter
from product_tools.contracts import ToolError, canonical, strict_json
from product_tools.dataset import Dataset
from product_tools.web_evidence import WebEvidence
from product_tools.conversation import Conversation
from product_tools.state import StateStore
from product_tools.workflow import WorkflowAudit


class BulkImportTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runtime-data")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "runtime-data").mkdir()
        self.web = WebEvidence(self.root / "state.sqlite", self.root)
        self.addCleanup(self.web.close)
        self.importer = BulkImporter(self.web)
        self.empty = Dataset(ROOT / "data/business/empty")
        self.mid = "FIXTURE-"+uuid4().hex[:8]+".FULL"
        self.scope = {"model_id": self.mid, "model_version": "unspecified", "document_version": "fixture"}
        self.model = {**self.scope, "name": "Generated fixture only", "product_family": "microwave",
                      "synthetic": False, "spec_source_id": "identity",
                      "identity_review": {"source_id": "identity", "manufacturer": "Fixture",
                                          "authority": "manufacturer", "rationale": "Generated contract test, not a real manufacturer"}}
        self.quotes = ["Model "+self.mid+" observation "+str(i)+" "+"x"*2200 for i in range(36)]
        snapshots = []
        for offset in range(0, len(self.quotes), 6):
            snapshots.append(self.web.collect({"research_id": "fixture", "page_id": "original-"+str(offset),
                "url": "https://manufacturer.example/fixture", "observed_text": "\n".join(self.quotes[offset:offset+6]),
                "native_tool_name": "generated_fixture_no_browser"}, True))
        self.entries = [{"snapshot_id": snapshots[i//6]["snapshot_id"], "source_id": "identity" if i == 0 else "fact-"+str(i),
                        "kind": "product_fact", "scope": self.scope, "location": "Fixture section "+str(i),
                        "text": quote, "support_quote": quote, "published_date": None,
                        "model_matching": "explicit_model_verified", "purchase_verified": None, "sponsorship": None,
                        "feature_key": "product_identity" if i == 0 else "feature-"+str(i), "availability": "present"}
                        for i, quote in enumerate(self.quotes)]
        self.original = {"data_version": "bulk-test", "observations": self.entries[1:]+self.entries[:1], "new_models": [self.model]}
        self.path = self.root / "runtime-data/original.json"
        self.write()

    def tearDown(self):
        self.web.close()

    def write(self):
        self.path.write_text(canonical(self.original), encoding="utf-8")

    def run_import(self, key="bulk"):
        return self.importer.run(self.empty, {"input_path": "runtime-data/original.json", "import_key": key})

    def error(self, code, call, *args):
        with self.assertRaises(ToolError) as caught:
            call(*args)
        self.assertEqual(caught.exception.code, code)

    def test_large_file_identity_first_all_original_text_sha_and_order_preserved(self):
        self.assertGreater(self.path.stat().st_size, 65536)
        result = self.run_import()
        self.assertEqual(result["status"], "completed")
        self.assertEqual((result["completed_count"], result["unprocessed_count"]), (36, 0))
        self.assertEqual(result["input_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        catalog = Dataset(self.root / result["last_valid_catalog"])
        self.assertEqual(catalog.models[0]["model_id"], self.mid)
        for entry in self.entries:
            record = catalog.source(entry["source_id"])
            self.assertEqual(record["text"], entry["text"])
            self.assertEqual(record["sha256"], hashlib.sha256(entry["text"].encode()).hexdigest())
        audit = strict_json((self.root/result["audit_path"]).read_text(encoding="utf-8"))
        self.assertEqual(audit["registration_order_input_indices"][0], 35)
        self.assertEqual(audit["batches"][0]["source_ids"], ["identity"])
        self.assertTrue(all(len(b["source_ids"]) <= 10 for b in audit["batches"]))
        self.assertEqual((self.root/result["original_copy"]).read_bytes(), self.path.read_bytes())
        self.assertFalse(result["acceptance_ready"])

    def test_failure_after_identity_retains_valid_catalog_and_no_auto_retry(self):
        self.original["observations"][14]["scope"] = {**self.scope, "document_version": "wrong"}
        self.write()
        result = self.run_import()
        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["completed_count"], 11)
        self.assertEqual(result["unprocessed_count"], 25)
        self.assertIn("fact-15", result["failed_source_ids"])
        catalog = Dataset(self.root/result["last_valid_catalog"])
        self.assertEqual(len(catalog.sources), 11)
        replay = self.run_import()
        self.assertTrue(replay["cached"])
        self.assertEqual(replay["status"], "partial_failure")
        self.assertEqual(replay["last_valid_fingerprint"], result["last_valid_fingerprint"])
        self.assertEqual(len(list((self.root/"runtime-data/catalogs").iterdir())), 2)

    def test_input_change_and_outside_runtime_are_not_replayed(self):
        self.run_import()
        self.original["observations"][0]["text"] += " changed"
        self.write()
        self.error("import_conflict", self.run_import)
        self.error("invalid_path", self.importer.run, self.empty, {"input_path": "../outside.json", "import_key": "outside"})

    def test_exact_model_suffix_not_automatically_removed(self):
        self.original["observations"][1]["scope"] = {**self.scope, "model_id": self.mid.split(".")[0]}
        self.write()
        result = self.run_import()
        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["error"]["code"], "unknown_model")
        catalog = Dataset(self.root/result["last_valid_catalog"])
        self.assertEqual(catalog.models[0]["model_id"], self.mid)

    def test_duplicate_ids_fail_before_any_import(self):
        self.original["observations"][1]["source_id"] = self.original["observations"][0]["source_id"]
        self.write()
        self.error("invalid_input", self.run_import)
        self.assertFalse((self.root/"runtime-data/catalogs").exists())

    def test_missing_snapshot_is_a_retained_honest_failure(self):
        self.original["observations"][-1]["snapshot_id"] = "absent"
        self.write()
        result = self.run_import()
        self.assertEqual((result["status"], result["completed_count"]), ("failed", 0))
        self.assertEqual(result["error"]["code"], "snapshot_not_found")
        self.assertEqual(result["failed_source_ids"], ["identity"])

    def test_oversized_single_original_fails_without_text_shortening(self):
        self.original["observations"][-1]["text"] = "original-not-shortened" * 5000
        self.write()
        result = self.run_import()
        self.assertEqual((result["status"], result["completed_count"]), ("failed", 0))
        self.assertEqual(result["error"]["code"], "input_limit")
        self.assertEqual((self.root/result["original_copy"]).read_bytes(), self.path.read_bytes())

    def test_expired_original_workflow_blocks_registration_without_restarting_clock(self):
        store = StateStore(self.root/"state.sqlite", self.empty)
        self.addCleanup(store.close)
        conv = Conversation(store, self.root)
        start = datetime(2026, 10, 12, tzinfo=timezone.utc)
        with patch("product_tools.workflow.utc_now", return_value=start):
            request = conv.open_product_workflow({"question": "Expired fixture", "user_submitted": True,
                                                  "session_id": "expiry", "request_key": "expiry", "budget_seconds": 600})
        self.original["research_id"] = request["research_id"]
        self.write()
        with patch("product_tools.workflow.utc_now", return_value=start+timedelta(seconds=601)):
            result = self.run_import()
        self.assertEqual((result["status"], result["completed_count"]), ("failed", 0))
        self.assertEqual(result["error"]["code"], "workflow_expired")
        self.assertEqual(WorkflowAudit(store.db, self.root).status(request["research_id"])["started_at"], start.isoformat())

    def test_cancelled_original_turn_blocks_registration(self):
        store = StateStore(self.root/"state.sqlite", self.empty)
        self.addCleanup(store.close)
        conv = Conversation(store, self.root)
        request = conv.open_product_workflow({"question": "Cancelled fixture", "user_submitted": True,
                                             "session_id": "cancel", "request_key": "cancel"})
        store.db.execute("INSERT INTO turns(turn_id,session_id,request_key,input_json,context_hash,dataset_hash,code_hash,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                         ("cancel-turn", "cancel", "cancel", "{}", "fixture", self.empty.fingerprint, store.code_hash, "cancelled", datetime.now(timezone.utc).isoformat()))
        store.db.execute("UPDATE conversation_requests SET turn_id='cancel-turn' WHERE session_id='cancel'")
        self.original["research_id"] = request["research_id"]
        self.write()
        result = self.run_import()
        self.assertEqual((result["status"], result["completed_count"]), ("failed", 0))
        self.assertEqual(result["error"]["code"], "terminal_turn")

    def test_untimed_cancelled_and_failed_turns_cannot_register_a_new_catalog(self):
        store = StateStore(self.root/"state.sqlite", self.empty)
        self.addCleanup(store.close)
        conv = Conversation(store, self.root)
        request = conv.open_request({"question": "Untimed legacy fixture "+self.mid, "user_submitted": True,
                                     "session_id": "untimed", "request_key": "untimed"})
        conv.set_request_scope_policy({"session_id": "untimed", "request_key": "untimed",
                                       "policy": {"mode": "explicit_model", "model_id": self.mid, "user_quote": self.mid}})
        self.assertFalse(WorkflowAudit(store.db, self.root).active(request["research_id"]))
        store.db.execute("INSERT INTO turns(turn_id,session_id,request_key,input_json,context_hash,dataset_hash,code_hash,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                         ("untimed-turn", "untimed", "untimed", "{}", "fixture", self.empty.fingerprint, store.code_hash, "cancelled", datetime.now(timezone.utc).isoformat()))
        store.db.execute("UPDATE conversation_requests SET turn_id='untimed-turn' WHERE session_id='untimed'")
        self.original["research_id"] = request["research_id"]
        self.write()
        # Make the generated observations genuinely belong to the untimed
        # request. With the old clock-only guard these valid originals import.
        self.web.db.execute("UPDATE web_pages SET research_id=? WHERE research_id='fixture'", (request["research_id"],))
        self.web.db.commit()
        for terminal in ("cancelled", "failed"):
            with self.subTest(terminal=terminal):
                store.db.execute("UPDATE turns SET status=? WHERE turn_id='untimed-turn'", (terminal,))
                self.original["data_version"] = "untimed-"+terminal
                self.write()
                result = self.run_import("untimed-"+terminal)
                self.assertEqual((result["status"], result["completed_count"]), ("failed", 0))
                self.assertEqual(result["error"]["code"], "terminal_turn")
                self.assertIsNone(result["last_valid_catalog"])
                self.assertEqual(result["unprocessed_count"], 36)
                self.assertFalse((self.root/"runtime-data/catalogs").exists())


if __name__ == "__main__":
    unittest.main()
