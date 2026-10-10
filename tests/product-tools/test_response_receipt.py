"""Real persistence and encoding boundaries for compact native responses."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import MAX_BYTES, ToolError, canonical, decode_json_bytes, fingerprint, strict_json
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore


class UnicodeInputTests(unittest.TestCase):
    def test_windows_boms_preserve_korean_and_strict_keys(self):
        body = '{"question":"실제 냉장고 질문"}'
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-be"):
            raw = body.encode(encoding)
            if encoding == "utf-16-be": raw = b"\xfe\xff" + raw
            self.assertEqual(strict_json(decode_json_bytes(raw)), json.loads(body))
        with self.assertRaises(ToolError): strict_json(decode_json_bytes(b'\xef\xbb\xbf{"x":1,"x":2}'))

    def test_unsupported_encoding_and_both_byte_limits_are_rejected(self):
        for raw in (b"x" * (MAX_BYTES + 1), '{"x":"한"}'.encode("cp949"), ("한" * 22000).encode("utf-16")):
            with self.assertRaises(ToolError): decode_json_bytes(raw)


class CompactReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-receipt-")
        self.root = Path(self.temp.name)
        for rel in ("skills/manifest.json", "agents/product-planning.md"):
            p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT / rel).read_bytes())
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.store = StateStore(self.root / "runtime-data/test.sqlite", self.data)
        self.conversation = Conversation(self.store, self.root)
        self.turn = self.conversation.open_request({"question":"실제 요청", "model_id":"T876MQQ012", "user_submitted":True})["turn"]

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def result(self, revision):
        return {"status":"held", "pains":[], "existing_features":[], "remaining_pains":[], "concepts":[], "assumptions":[], "evidence_refs":[], "validation_findings":["미확인 자료 " + "한" * 800], "revisions":revision, "usage_summary":{"status":"unknown"}}

    def save(self, key, revision, assessment):
        return self.store.save_result(self.turn["session_id"], self.turn["turn_id"], key, self.result(revision), revision, assessment, require_review=True, response_mode="receipt")

    def test_compact_accepted_receipt_matches_actual_export_and_replay(self):
        assessment = {"claim_checks":[], "feature_matches":[], "concept_links":[]}
        saved = self.save("first", 0, assessment)
        self.assertTrue(saved["accepted"])
        self.assertNotIn("latest_result", saved["turn"]); self.assertNotIn("input", saved["turn"])
        self.assertEqual(saved["receipt"]["result_sha256"], fingerprint(self.result(0)))
        self.assertEqual(saved["receipt"]["assessment_sha256"], fingerprint(assessment))
        self.assertEqual(self.save("first", 0, assessment)["receipt"], saved["receipt"])
        exported = self.conversation.export_session({"session_id": self.turn["session_id"]})
        raw = (self.root / exported["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), exported["sha256"])
        candidate = json.loads(raw)["turns"][0]["candidates"][0]
        self.assertEqual(candidate["result"], self.result(0))
        self.assertEqual(candidate["validation"]["assessment"], assessment)

    def test_rejection_repair_and_exhaustion_preserve_attempts(self):
        first = self.save("bad", 0, None)
        self.assertFalse(first["accepted"]); self.assertEqual(first["turn"]["status"], "needs_revision")
        self.assertEqual(first["receipt"]["candidate_result_version"], 1)
        repaired = self.save("fixed", 1, {"claim_checks":[], "feature_matches":[], "concept_links":[]})
        self.assertTrue(repaired["accepted"]); self.assertEqual(repaired["turn"]["result_version"], 2)
        third = self.save("bad-third", 2, None)
        self.assertFalse(third["accepted"]); self.assertEqual(third["turn"]["status"], "held")
        fourth = self.save("too-many", 3, None)
        self.assertFalse(fourth["accepted"]); self.assertEqual(fourth["reason"], "business_revision_limit")
        self.assertIsNone(fourth["receipt"]["candidate_result_version"])
        self.assertEqual(len(self.store.get_turn(self.turn["session_id"],self.turn["turn_id"])["result_history"]), 3)

    def test_error_findings_are_bounded_without_entire_assessment(self):
        v = self.store.compact_validation({"assessment": {"huge":"private"}, "review": {"findings":["remaining_pain_not_supported:r" + str(i) for i in range(24)], "can_finalize_reported_result":False}})
        self.assertNotIn("assessment",v)
        self.assertEqual(len(v["review_summary"]["findings"]),20)
        self.assertEqual(v["review_summary"]["findings_omitted"],4)

    def combined(self, key, revision, assessment):
        return self.conversation.save_and_export({'session_id':self.turn['session_id'], 'turn_id':self.turn['turn_id'],
            'result_key':key,'result':self.result(revision),'expected_result_version':revision,'assessment':assessment})

    def test_combined_save_rejection_repair_and_stale_replay(self):
        rejected=self.combined('bad-combined',0,None)
        self.assertFalse(rejected['delivery_ready']);self.assertFalse(rejected['save']['accepted'])
        self.assertIsNotNone(rejected['export'])
        good={'claim_checks':[],'feature_matches':[],'concept_links':[]}
        repaired=self.combined('fixed-combined',1,good)
        self.assertTrue(repaired['delivery_ready'])
        self.combined('latest-combined',2,good)
        old=self.combined('fixed-combined',1,good)
        self.assertFalse(old['delivery_ready']); self.assertTrue(old['save']['accepted'])
        self.assertEqual(old['save']['receipt']['candidate_result_version'],2)
        self.assertEqual(old['save']['receipt']['current_result_version'],3)

    def test_combined_export_failure_keeps_real_candidate_and_recovers(self):
        good={'claim_checks':[],'feature_matches':[],'concept_links':[]}
        with patch.object(self.conversation,'export_session',side_effect=OSError('fixture disk failure')):
            saved=self.combined('export-failure',0,good)
        self.assertFalse(saved['delivery_ready']); self.assertTrue(saved['save']['accepted'])
        self.assertEqual(saved['export_error']['code'],'export_failed')
        self.assertEqual(self.store.get_turn(self.turn['session_id'],self.turn['turn_id'])['result_version'],1)
        recovered=self.combined('export-failure',0,good)
        self.assertTrue(recovered['delivery_ready']);self.assertIsNotNone(recovered['export'])

    def test_combined_final_reads_share_locked_sqlite_snapshot(self):
        good={'claim_checks':[],'feature_matches':[],'concept_links':[]}
        real=self.conversation.export_session
        observed=[]
        def export(p):
            observed.append(self.store.db.in_transaction)
            return real(p)
        with patch.object(self.conversation,'export_session',side_effect=export):
            saved=self.combined('snapshot',0,good)
        self.assertEqual(observed,[True]);self.assertTrue(saved['delivery_ready'])


if __name__ == "__main__": unittest.main()
