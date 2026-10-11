"""Saved-version, failure recovery and replay boundaries for reader delivery."""
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore


class ReaderConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-reader-state-")
        self.root = Path(self.temp.name)
        for rel in ("skills/manifest.json", "agents/product-planning.md"):
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((ROOT / rel).read_bytes())
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.store = StateStore(self.root / "runtime-data/test.sqlite", self.data)
        self.conv = Conversation(self.store, self.root)
        self.turn = self.conv.open_request({"question": "불편 근거가 부족하면 보류해 줘", "model_id": "T876MQQ012", "user_submitted": True})["turn"]
        self.payload = {"session_id": self.turn["session_id"], "turn_id": self.turn["turn_id"], "result_key": "first", "expected_result_version": 0,
                        "result": {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [], "assumptions": [],
                                   "evidence_refs": [], "validation_findings": ["불편을 판단할 근거가 부족하여 보류한다."], "revisions": 0, "usage_summary": {"status": "unknown"}},
                        "assessment": {"claim_checks": [], "feature_matches": [], "concept_links": []}, "report": True, "open_folder": False}
        self.rendered = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def create(self, workspace, planning, result, sources, **options):
        self.assertFalse(options["open_folder"])
        self.assertTrue(all(s["model_id"] == "T876MQQ012" for s in sources))
        self.rendered += 1
        directory = self.root / "runtime-data/deliverables" / str(self.rendered)
        directory.mkdir(parents=True)
        path = directory / "보고서.pdf"
        path.write_bytes(b"fixture reader content")
        return {"ready": True, "directory": str(directory), "files": [{"path": str(path), "kind": "pdf", "title": "보고서"}], "checks": {"errors": []}}

    def recovery_payload(self, version=1, **options):
        return {"session_id": self.turn["session_id"], "turn_id": self.turn["turn_id"], "expected_result_version": version, "open_folder": False, **options}

    def test_intact_replay_and_recovery_reuse_files_without_rendering_again(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=self.create) as render:
            first = self.conv.save_and_export(self.payload)
            replay = self.conv.save_and_export(self.payload)
            recovered = self.conv.deliver_result(self.recovery_payload())
        self.assertTrue(first["report_ready"])
        self.assertFalse(first["report"]["reused"])
        self.assertTrue(replay["report"]["reused"])
        self.assertTrue(recovered["reused"])
        self.assertEqual(render.call_count, 1)
        self.assertEqual(self.store.get_turn(self.turn["session_id"], self.turn["turn_id"])["result_version"], 1)

    def test_failed_generation_preserves_committed_candidate_and_can_recover(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=OSError("fixture disk full")):
            failed = self.conv.save_and_export(self.payload)
        self.assertTrue(failed["save"]["accepted"])
        self.assertTrue(failed["delivery_ready"])
        self.assertFalse(failed["report_ready"])
        self.assertEqual(failed["report_error"]["code"], "report_failed")
        with patch("product_tools.delivery.create_deliverables", side_effect=self.create):
            self.assertTrue(self.conv.deliver_result(self.recovery_payload())["ready"])
        self.assertEqual(self.store.get_turn(self.turn["session_id"], self.turn["turn_id"])["result_version"], 1)

    def test_modified_reader_file_is_preserved_and_rebuilt_in_new_folder(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=self.create):
            first = self.conv.save_and_export(self.payload)["report"]
            original = Path(first["files"][0]["path"])
            original.write_bytes(b"manually changed")
            next_output = self.conv.deliver_result(self.recovery_payload())
        self.assertFalse(next_output["reused"])
        self.assertNotEqual(first["directory"], next_output["directory"])
        self.assertEqual(original.read_bytes(), b"manually changed")

    def test_old_version_and_cancelled_turn_never_deliver_cached_files(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=self.create):
            self.conv.save_and_export(self.payload)
            self.assertFalse(self.conv.deliver_result(self.recovery_payload(2))["ready"])
            self.store.cancel_turn(self.turn["session_id"], self.turn["turn_id"], "cancel", "사용자 취소", 1, True)
            self.assertFalse(self.conv.deliver_result(self.recovery_payload())["ready"])

    def test_report_plan_can_exceed_stdin_bound_but_cannot_escape_workspace(self):
        path = self.root / "runtime-data/authored.json"
        plan = {"title": "긴 문서", "summary": ["내용" * 40000], "sources": [], "sections": []}
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        self.assertGreater(path.stat().st_size, 65536)
        self.assertEqual(self.conv._read_report_plan("runtime-data/authored.json"), plan)
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaises(ToolError):
            self.conv._read_report_plan(str(outside))

    def test_six_field_calls_do_not_generate_documents_and_invalid_option_cannot_save(self):
        with self.assertRaises(ToolError):
            self.conv.save_and_export({**self.payload, "report": "true"})
        self.assertEqual(self.store.get_turn(self.turn["session_id"], self.turn["turn_id"])["result_version"], 0)
        old_api = {k: v for k, v in self.payload.items() if k not in ("report", "open_folder")}
        response = self.conv.save_and_export(old_api)
        self.assertTrue(response["delivery_ready"])
        self.assertNotIn("report", response)

    def test_database_report_error_keeps_successful_save_and_export_in_response(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=sqlite3.OperationalError("fixture report database locked")):
            response = self.conv.save_and_export(self.payload)
        self.assertTrue(response["save"]["accepted"])
        self.assertIsNotNone(response["export"])
        self.assertFalse(response["report_ready"])
        self.assertEqual(response["report_error"]["code"], "report_storage_error")
        self.assertTrue(response["report_error"]["retryable"])
        self.assertEqual(self.store.get_turn(self.turn["session_id"], self.turn["turn_id"])["result_version"], 1)

    def test_changed_image_bytes_regenerate_report_without_overwriting_prior_files(self):
        image = self.root / "runtime-data/concept.png"
        image.write_bytes(b"fixture image bytes one")
        plan = {"title": "컨셉", "summary": [], "sources": [], "sections": [
            {"title": "컨셉 모습", "blocks": [{"type": "image", "path": str(image), "caption": "테스트 이미지"}]}]}
        path = self.root / "runtime-data/authored.json"
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        payload = {**self.payload, "report_plan_path": "runtime-data/authored.json"}
        with patch("product_tools.delivery.create_deliverables", side_effect=self.create):
            first = self.conv.save_and_export(payload)["report"]
            image.write_bytes(b"fixture image bytes two")
            second = self.conv.deliver_result(self.recovery_payload(report_plan_path="runtime-data/authored.json"))
        self.assertFalse(second["reused"])
        self.assertNotEqual(first["directory"], second["directory"])
        self.assertTrue(Path(first["directory"]).is_dir())


if __name__ == "__main__":
    unittest.main()
