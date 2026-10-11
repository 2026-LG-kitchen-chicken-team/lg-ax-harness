"""Immutable question -> research journal -> exact-source turn, no question parser."""
import json
from pathlib import Path
import shutil
import sqlite3
from unittest.mock import patch
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore


class ResearchRequests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            dst = self.root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dst)
        self.db = self.root / "runtime-data/product.sqlite"
        self.use_data("data/business/empty")

    def use_data(self, path):
        if hasattr(self, "store"):
            self.store.close()
        self.store = StateStore(self.db, Dataset(ROOT / path))
        self.conv = Conversation(self.store, self.root)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def start(self, **extra):
        return self.conv.open_request({"question": "원래 질문 " + uuid.uuid4().hex,
                                      "user_submitted": True, **extra})

    def event(self, request, **extra):
        return {"session_id": request["session_id"], "request_key": request["request_key"],
                "expected_request_version": request["request_version"], "event_key": uuid.uuid4().hex, **extra}

    def test_empty_catalog_known_selection_requests_research_without_fake_turn(self):
        p = self.start(model_id="MODEL-" + uuid.uuid4().hex)
        self.assertEqual(p["status"], "research_required")
        self.assertIsNone(p["turn_id"])
        self.assertEqual(self.store.db.execute("select count(*) from turns").fetchone()[0], 0)

    def test_pending_can_export_hold_and_unknown_usage_without_turn(self):
        p = self.start(product_family="new-family-" + uuid.uuid4().hex)
        held = self.conv.record_request_research(self.event(p, status="held", reason="Observed access failure", observation_refs=[]))
        self.assertEqual(held["request_version"], 1)
        out = self.conv.export_session({"session_id": p["session_id"]})
        value = json.loads((self.root / out["path"]).read_text(encoding="utf-8"))
        self.assertEqual(value["turns"], [])
        self.assertEqual(value["requests"][0]["events"][0]["input"]["status"], "held")
        self.assertEqual(value["requests"][0]["research_usage"]["status"], "unknown")

    def test_resolution_keeps_original_and_is_idempotent(self):
        p = self.start()
        original = self.store.db.execute("select payload from conversation_requests").fetchone()[0]
        self.use_data("data/business/lg-research-v3")
        event = self.event(p, selection={"model_id": "B502S33"})
        first = self.conv.resolve_request_bundle(event)
        self.assertTrue(first["bundle"]["evidence_refs"])
        again = self.conv.resolve_request_bundle(event)
        self.assertEqual(first["turn"]["turn_id"], again["turn"]["turn_id"])
        self.assertEqual(self.store.db.execute("select payload from conversation_requests").fetchone()[0], original)
        self.assertEqual(first["turn"]["input"]["question"], json.loads(original)["question"])

    def test_stale_writer_and_rewritten_event_rejected(self):
        p = self.start()
        event = self.event(p, status="researching", reason="Observed source", observation_refs=["snapshot-one"])
        self.conv.record_request_research(event)
        self.conv.record_request_research(event)
        for bad in ({**event, "reason": "rewritten"}, self.event(p, status="held", reason="stale", observation_refs=[])):
            with self.assertRaises(ToolError):
                self.conv.record_request_research(bad)
        self.assertEqual(self.store.db.execute("select count(*) from request_events").fetchone()[0], 1)

    def test_research_id_is_stable_and_session_scoped(self):
        a = self.start(session_id="a", request_key="question-1")
        b = self.start(session_id="b", request_key="question-1")
        self.assertNotEqual(a["research_id"], b["research_id"])
        replay = self.conv.current_request({"session_id": "a", "request_key": "question-1"})
        self.assertEqual(a["research_id"], replay["research_id"])

    def test_resolution_cannot_change_original_selection_or_conditions(self):
        p = self.start(model_id="original")
        for selection in ({"model_id": "replacement"}, {"question": "rewritten"}, {"constraints": {}}):
            with self.assertRaises(ToolError):
                self.conv.resolve_request(self.event(p, selection=selection))
        self.assertEqual(self.store.db.execute("select request_version from conversation_requests").fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("select count(*) from request_events").fetchone()[0], 0)

    def test_resolution_cannot_reset_bound_turn(self):
        p = self.start()
        self.use_data("data/business/lg-research-v3")
        self.conv.resolve_request(self.event(p, selection={"model_id": "B502S33"}))
        with self.assertRaises(ToolError) as ctx:
            self.conv.resolve_request(self.event({**p, "request_version": 1}, selection={"model_id": "T876MQQ012"}))
        self.assertEqual(ctx.exception.code, "request_already_bound")

    def test_initial_pending_is_locked_against_concurrent_research_writer(self):
        other = sqlite3.connect(self.db, timeout=0, isolation_level=None)
        original = self.conv._pending
        def interleave(*args):
            with self.assertRaises(sqlite3.OperationalError):
                other.execute("UPDATE conversation_requests SET request_version=99")
            return original(*args)
        try:
            with patch.object(self.conv, "_pending", side_effect=interleave):
                request = self.start()
            self.assertEqual(request["request_version"], 0)
        finally:
            other.close()

    def test_nested_transaction_rollback_preserves_outer_atomicity(self):
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.start()
                raise RuntimeError("fault after inner commit")
        self.assertEqual(self.store.db.execute("select count(*) from conversation_requests").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
