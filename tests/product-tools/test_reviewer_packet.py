"""Synthetic immutable reviewer handoff and stale-result boundaries; no AI."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, strict_json
from product_tools.dataset import Dataset
from product_tools.reviewer_packet import MAX_PACKET_BYTES, ReviewPackets
from product_tools.state import StateStore


class ReviewerPacketTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runtime-data")
        self.root = Path(self.temp.name)
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store = StateStore(self.root / "runtime-data/state.sqlite", self.data)
        planning = strict_json((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
        turn = self.store.start_turn(planning, True)
        self.handle = {"session_id": planning["session_id"], "turn_id": turn["turn_id"]}
        self.packets = ReviewPackets(self.store, self.root)
        refs = self.store.tools.select_evidence(planning["model_scope"][0], ["DOC-AX-R301-1.0-01", "REV-AX-R301-1.0-02"])["evidence_refs"]
        self.candidate = {**self.handle, "result_key": "candidate-0", "expected_result_version": 0,
                          "result": {"status": None, "evidence_refs": refs, "assumptions": ["Generated fixture only"]},
                          "assessment": None}
        self.path = self.root / "runtime-data/candidate.json"
        self.write()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def write(self):
        self.path.write_bytes(canonical(self.candidate).encode("utf-8"))

    def prepare(self, key="review-0"):
        return self.packets.prepare_review_packet({**self.handle, "candidate_path": "runtime-data/candidate.json", "packet_key": key})

    def verify(self, packet):
        return self.packets.verify_review_packet({**self.handle, "packet_path": packet["packet_path"], "packet_sha256": packet["packet_sha256"]})

    def error(self, code, call, *args):
        with self.assertRaises(ToolError) as caught:
            call(*args)
        self.assertEqual(caught.exception.code, code)

    def test_incomplete_candidate_can_be_reviewed_and_packet_replay_is_metadata_only(self):
        prepared = self.prepare()
        self.assertTrue(prepared["ready"])
        self.assertTrue(prepared["candidate_source_refs_valid"])
        self.assertNotIn("candidate", prepared)
        self.assertEqual(prepared["candidate_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(self.store.row(**self.handle)["result_version"], 0)
        self.assertTrue(self.prepare()["cached"])
        verified = self.verify(prepared)
        self.assertTrue(verified["ready"])
        self.assertFalse(verified["acceptance_ready"])
        self.assertEqual(verified["semantic_status"], "unverified")
        packet = strict_json((self.root / prepared["packet_path"]).read_text(encoding="utf-8"))
        self.assertNotIn("catalog", packet)
        self.assertNotIn("skills", packet)
        self.assertEqual(packet["candidate"], self.candidate)

    def test_source_file_replacement_does_not_change_preserved_candidate_and_key_conflicts(self):
        prepared = self.prepare()
        old = self.path.read_bytes()
        self.candidate["result"]["assumptions"] = ["Changed source file"]
        self.write()
        self.assertTrue(self.verify(prepared)["ready"])
        self.assertEqual((self.root / prepared["candidate_copy"]).read_bytes(), old)
        self.error("packet_conflict", self.prepare)
        other = self.prepare("review-1")
        self.assertNotEqual(other["candidate_sha256"], prepared["candidate_sha256"])

    def test_packet_hash_and_immutable_candidate_tampering_are_rejected(self):
        prepared = self.prepare()
        path = self.root / prepared["packet_path"]
        old = path.read_bytes()
        path.write_bytes(old+b" ")
        self.error("packet_integrity", self.verify, prepared)
        path.write_bytes(old)
        (self.root/prepared["candidate_copy"]).write_bytes(b"{}")
        self.error("packet_integrity", self.verify, prepared)

    def test_different_session_candidate_and_packet_are_rejected(self):
        self.candidate["session_id"] = "other"
        self.write()
        self.error("state_conflict", self.prepare)
        self.candidate["session_id"] = self.handle["session_id"]
        self.write()
        prepared = self.prepare()
        self.error("turn_not_found", self.packets.verify_review_packet,
                   {**self.handle, "session_id": "other", "packet_path": prepared["packet_path"], "packet_sha256": prepared["packet_sha256"]})

    def test_changed_result_version_rejects_late_packet_without_writing_results(self):
        prepared = self.prepare()
        self.store.db.execute("UPDATE turns SET result_version=1 WHERE turn_id=?", (self.handle["turn_id"],))
        self.error("state_conflict", self.verify, prepared)
        self.error("state_conflict", self.prepare, "late")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM results").fetchone()[0], 0)

    def test_stale_code_data_context_scope_and_cancel_invalidate_handoff(self):
        prepared = self.prepare()
        row = self.store.row(**self.handle)
        self.store.code_hash = "other-code"
        self.error("stale_context", self.verify, prepared)
        self.store.code_hash = row["code_hash"]
        original_hash = self.data.fingerprint
        self.data.fingerprint = "other-data"
        self.error("stale_context", self.verify, prepared)
        self.data.fingerprint = original_hash
        self.store.db.execute("UPDATE turns SET context_hash='new-context' WHERE turn_id=?", (self.handle["turn_id"],))
        self.error("state_conflict", self.verify, prepared)
        self.store.db.execute("UPDATE turns SET context_hash=?,status='cancelled' WHERE turn_id=?", (row["context_hash"], self.handle["turn_id"]))
        self.error("terminal_turn", self.verify, prepared)
        self.error("terminal_turn", self.prepare, "cancelled")

    def test_wrong_references_are_diagnostics_not_verified_facts_or_semantic_acceptance(self):
        self.candidate["result"]["evidence_refs"][0]["sha256"] = "0"*64
        self.write()
        prepared = self.prepare()
        self.assertTrue(prepared["ready"])
        self.assertFalse(prepared["candidate_source_refs_valid"])
        self.assertEqual(prepared["reference_diagnostic"]["error"]["code"], "reference_mismatch")
        expected = prepared["reference_diagnostic"]["reference_checks"][0]["actual_catalog_metadata"]
        self.assertNotEqual(expected["sha256"], "0"*64)
        self.assertTrue(self.verify(prepared)["ready"])
        self.assertFalse(self.verify(prepared)["candidate_source_refs_valid"])

    def test_paths_outside_runtime_and_packet_directory_are_rejected(self):
        outside = self.root / "outside.json"
        outside.write_bytes(self.path.read_bytes())
        self.error("invalid_path", self.packets.prepare_review_packet,
                   {**self.handle, "candidate_path": "outside.json", "packet_key": "outside"})
        self.error("invalid_path", self.packets.verify_review_packet,
                   {**self.handle, "packet_path": "runtime-data/candidate.json", "packet_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest()})

    def test_wrong_expected_scope_is_diagnostic_but_changed_turn_scope_invalidates(self):
        self.candidate["result"]["evidence_refs"][0]["model_version"] = "wrong"
        self.write()
        prepared = self.prepare()
        self.assertFalse(prepared["candidate_source_refs_valid"])
        row = self.store.row(**self.handle)
        planning = strict_json(row["input_json"])
        planning["model_scope"][0]["document_version"] = "unknown-document"
        self.store.db.execute("UPDATE turns SET input_json=? WHERE turn_id=?", (canonical(planning), self.handle["turn_id"]))
        self.error("unknown_scope", self.verify, prepared)

    def test_multiline_packet_keeps_exact_original_candidate_bytes_and_last_reference(self):
        original = self.path.read_bytes()
        prepared = self.prepare()
        packet_path = self.root / prepared["packet_path"]
        body = packet_path.read_bytes()
        self.assertIn(b"\n  ", body)
        self.assertGreater(body.count(b"\n"), 30)
        self.assertLessEqual(len(body), MAX_PACKET_BYTES)
        packet = strict_json(body.decode("utf-8"))
        self.assertEqual(packet["candidate"]["result"]["evidence_refs"][-1], self.candidate["result"]["evidence_refs"][-1])
        self.assertEqual((self.root / prepared["candidate_copy"]).read_bytes(), original)
        self.assertEqual(prepared["candidate_sha256"], hashlib.sha256(original).hexdigest())
        self.assertTrue(self.verify(prepared)["ready"])

    def test_utf16_and_malformed_reference_expansion_rejects_before_files_or_registration(self):
        # All expected metadata strings remain within the catalog field bounds.
        # This generated diagnostic fixture is neither a real catalog nor AI.
        source_id = "S"*96
        source = copy.deepcopy(next(iter(self.data.sources.values())))
        source.update(source_id=source_id, model_id="M"*96, model_version="V"*96,
                      document_version="D"*96, data_version="A"*96, location="위"*200)
        self.data.sources[source_id] = source
        self.candidate["result"] = {"status": None,
                                    "evidence_refs": [{"source_id": source_id, "quote": "bad fixture reference"} for _ in range(40)],
                                    "assumptions": [""]}
        # Fill the allowed original UTF-16 byte budget without exceeding it.
        low, high = 0, 32768
        while low < high:
            middle = (low+high+1)//2
            self.candidate["result"]["assumptions"] = ["가"*middle]
            if len(canonical(self.candidate).encode("utf-16")) <= 65536:
                low = middle
            else:
                high = middle-1
        self.candidate["result"]["assumptions"] = ["가"*low]
        raw = canonical(self.candidate).encode("utf-16")
        self.assertLessEqual(len(raw), 65536)
        self.assertGreater(len(raw), 65000)
        self.path.write_bytes(raw)
        self.error("input_limit", self.prepare)
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertFalse((self.root / "runtime-data/review-packets").exists())
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM product_review_packets").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
