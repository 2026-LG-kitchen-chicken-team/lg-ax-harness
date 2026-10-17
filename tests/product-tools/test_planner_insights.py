"""Authored display text delivery, not model/meaning/UI acceptance."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import test_web_delivery as web
import test_planning_web as planning
from product_tools.contracts import canonical


class PlannerInsightsTests(unittest.TestCase):
    setUp = web.WebDeliveryTests.setUp
    clock = web.WebDeliveryTests.clock

    def candidate(self, version=0):
        self.tools = self.store.tools
        self.scope = {"model_id": "T876MQQ012", "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10"}
        self.planning = self.current["input"]
        candidate = planning.PlanningWebTests.candidate(self)
        candidate["result"]["revisions"] = version
        return {**self.handle, "result_key": "candidate-" + str(version), "expected_result_version": version,
                "result": candidate["result"], "assessment": candidate["assessment"], "report": False}

    def authored(self):
        return {"concept_titles": {"c1": "찾기 동선 안내"},
                "summaries": {"r1": "적재 후 물품을 찾을 때 그림자 때문에 위치를 확인하기 어렵다는 시험용 해석.",
                              "c1": "물품을 찾는 사용자가 안내로 위치를 확인하도록 돕는 조건부 기획."}}

    def prepare(self, **extra):
        return self.conv.prepare_web_result({**self.handle, "expected_result_version": 1, **extra})

    def test_save_delivers_current_titles_summaries_without_changing_result_or_full_sources(self):
        candidate = self.candidate()
        before = copy.deepcopy(candidate["result"])
        saved = self.conv.save_and_export({**candidate, "planner_insights": self.authored()})
        self.assertTrue(saved["save"]["accepted"])
        self.assertTrue(saved["web_ready"])
        receipt = saved["web_result"]["planner_insights"]
        self.assertTrue(receipt["ready"])
        sidecar = self.root / receipt["path"]
        body = json.loads(sidecar.read_bytes())
        self.assertEqual(hashlib.sha256(sidecar.read_bytes()).hexdigest(), receipt["sha256"])
        self.assertEqual(body["binding"], saved["web_result"]["binding"])
        self.assertEqual(body["concept_titles"], self.authored()["concept_titles"])
        self.assertEqual(self.store.get_turn(**self.handle)["latest_result"], before)
        payload = json.loads((self.root / saved["web_result"]["path"]).read_bytes())
        selected = {s["source_id"] for s in self.data.sources.values() if s["model_id"] == self.scope["model_id"]}
        self.assertEqual({s["source_id"] for s in payload["sources"]}, selected)
        spec = importlib.util.spec_from_file_location("insights_viewer", ROOT / "web/prototypes/visual-viewer/build_view.py")
        viewer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(viewer)
        rendered = viewer.generate(self.root / saved["export"]["path"], out_dir=self.root / "runtime-data/visual-viewer",
                                   insights_dir=self.root / "runtime-data/visual-viewer")
        self.assertEqual(rendered["insights"], "matched")
        self.assertEqual(rendered["web_delivery"], "verified_binding")
        self.assertIn("찾기 동선 안내", (self.root / "runtime-data/visual-viewer/view-data.js").read_text(encoding="utf-8"))

    def test_binding_or_item_conflict_reports_display_failure_without_rejecting_result(self):
        invalid = [{"session_id": "other"}, {"turn_id": "other"}, {"binding": {}},
                   {"summaries": {"past-id": "다른 턴"}}, {"concept_titles": {"r1": "콘셉트 아님"}},
                   {"summaries": {"r1": 3}}]
        for fields in invalid:
            with self.subTest(fields=fields):
                saved = self.conv.save_and_export({**self.candidate(), "planner_insights": {**self.authored(), **fields}})
                self.assertTrue(saved["delivery_ready"])
                self.assertTrue(saved["web_ready"])
                self.assertFalse(saved["web_result"]["planner_insights"]["ready"])
        self.assertFalse(list((self.root / "runtime-data/visual-viewer").glob("insights-*.json")))

    def test_recovery_after_sidecar_write_failure_uses_saved_authored_text(self):
        with patch("product_tools.planner_insights.os.replace", side_effect=OSError("test disk failure")):
            saved = self.conv.save_and_export({**self.candidate(), "planner_insights": self.authored()})
        self.assertTrue(saved["web_ready"])
        self.assertFalse(saved["web_result"]["planner_insights"]["ready"])
        recovered = self.prepare()["planner_insights"]
        self.assertTrue(recovered["ready"])
        self.assertEqual(json.loads((self.root / recovered["path"]).read_bytes())["summaries"], self.authored()["summaries"])
        self.assertEqual(self.store.get_turn(**self.handle)["result_version"], 1)

    def test_same_version_conflict_and_corrupt_file_are_not_overwritten(self):
        saved = self.conv.save_and_export({**self.candidate(), "planner_insights": self.authored()})
        sidecar = self.root / saved["web_result"]["planner_insights"]["path"]
        original = sidecar.read_bytes()
        changed = self.authored()
        changed["concept_titles"]["c1"] = "바뀐 제목"
        response = self.prepare(planner_insights=changed)
        self.assertEqual(response["planner_insights"]["error"]["code"], "planner_insights_conflict")
        self.assertTrue(response["ready"])
        self.assertEqual(sidecar.read_bytes(), original)
        sidecar.write_bytes(original + b" altered")
        response = self.prepare()
        self.assertEqual(response["planner_insights"]["error"]["code"], "planner_insights_integrity")
        self.assertEqual(sidecar.read_bytes(), original + b" altered")

    def test_new_result_without_authored_text_never_inherits_previous_version(self):
        saved = self.conv.save_and_export({**self.candidate(), "planner_insights": self.authored()})
        old = saved["web_result"]["planner_insights"]
        new = self.conv.save_and_export(self.candidate(1))
        self.assertTrue(new["web_ready"])
        self.assertEqual(new["web_result"]["planner_insights"]["status"], "not_provided")
        self.assertNotEqual(old["binding"], new["web_result"]["binding"])

    def test_late_prepare_refreshes_export_after_atomic_sidecar_and_finish_keeps_binding(self):
        research, _ = self.clock()
        batch = self.conv.read_evidence_batch({**self.handle, "limit": 20})
        self.assertIsNone(batch["next_offset"])
        self.conv.record_evidence_review({**self.handle, "review_key": "fixture-review", "records": [
            {"source_id": ref["source_id"], "disposition": "reviewed", "reason": "Code fixture only; not semantic acceptance"}
            for ref in batch["evidence_refs"]]})
        saved = self.conv.save_and_export(self.candidate())
        self.assertTrue(saved["save"]["accepted"])
        order = []
        original_export = self.conv.export_session
        def observed_export(payload):
            self.assertEqual(len(list((self.root / "runtime-data/visual-viewer").glob("insights-*.json"))), 1)
            order.append("export_after_sidecar")
            return original_export(payload)
        with patch.object(self.conv, "export_session", side_effect=observed_export):
            response = self.prepare(planner_insights=self.authored())
        self.assertEqual(order, ["export_after_sidecar"])
        self.assertIn("export", response["planner_insights"])
        self.conv.record_workflow_event({"research_id": research, "event_key": "finish", "kind": "finish", "data": {
            "delivered_paths": [response["path"]], "layout_review": {"status": "not_run", "scope": "code test only"}}})
        self.assertEqual(self.prepare()["planner_insights"]["binding"], response["binding"])
        self.assertTrue(self.prepare()["planner_insights"]["reused"])

    def test_rejected_candidate_does_not_publish_display_text(self):
        candidate = self.candidate()
        candidate["assessment"]["concept_links"][0]["duplicates_existing"] = True
        saved = self.conv.save_and_export({**candidate, "planner_insights": self.authored()})
        self.assertFalse(saved["save"]["accepted"])
        self.assertFalse(saved["web_ready"])
        self.assertFalse((self.root / "runtime-data/visual-viewer").exists())

    def test_optional_display_text_diagnostic_never_certifies_its_meaning(self):
        from product_tools.planning import review_product_result
        candidate = self.candidate()
        report = review_product_result(self.data, {"input": self.current['input'], 'result': candidate['result'],
            'assessment': candidate['assessment'], 'planner_insights': self.authored()})
        self.assertTrue(report['can_finalize_reported_result'])
        self.assertEqual(report['planner_insights_review']['semantic_status'], 'unverified')


if __name__ == "__main__":
    unittest.main()
