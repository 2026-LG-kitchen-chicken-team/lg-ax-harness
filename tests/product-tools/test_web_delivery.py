"""Real web payload/version/finish checks; no UI, model or synthetic business success."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.workflow import WorkflowAudit


class WebDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-web-delivery-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.store = StateStore(self.root / "runtime-data/test.sqlite", self.data)
        self.addCleanup(self.store.close)
        self.conv = Conversation(self.store, self.root)
        self.current = self.conv.open_request({"question": "실제 요청을 변경하지 않는다", "model_id": "T876MQQ012", "user_submitted": True})["turn"]
        self.handle = {k: self.current[k] for k in ("session_id", "turn_id")}
        self.assessment = {"claim_checks": [], "feature_matches": [], "concept_links": []}

    def save(self, version=0, key="initial"):
        result = {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [],
                  "concepts": [], "assumptions": [], "evidence_refs": [],
                  "validation_findings": ["근거를 확인해야 한다. <script>원문은 실행하지 않는다</script>"],
                  "revisions": version, "usage_summary": {"status": "unknown"}}
        return self.conv.save_and_export({**self.handle, "result_key": key, "result": result,
            "expected_result_version": version, "assessment": self.assessment})

    def prepare(self, version=1):
        return self.conv.prepare_web_result({**self.handle, "expected_result_version": version})

    def error(self, code, function, *args):
        with self.assertRaises(ToolError) as raised:
            function(*args)
        self.assertEqual(raised.exception.code, code)

    def clock(self):
        research = "research-" + fingerprint([self.current["session_id"], self.current["request_key"]])
        audit = WorkflowAudit(self.store.db, self.root)
        audit.start(research, allow_new_bound_request=True)
        return research, audit

    def test_default_save_exports_all_selected_sources_without_renderer_or_model(self):
        with patch("product_tools.delivery.create_deliverables", side_effect=AssertionError("No file renderer")):
            saved = self.save()
        self.assertTrue(saved["delivery_ready"])
        self.assertTrue(saved["web_ready"])
        self.assertNotIn("report", saved)
        receipt = saved["web_result"]
        raw = (self.root / receipt["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt["sha256"])
        body = json.loads(raw)
        scoped = {s["source_id"] for s in self.data.sources.values() if s["model_id"] == "T876MQQ012"}
        self.assertEqual({s["source_id"] for s in body["sources"]}, scoped)
        self.assertEqual(body["result"], self.store.get_turn(**self.handle)["latest_result"])
        self.assertEqual(body["input"]["question"], "실제 요청을 변경하지 않는다")
        self.assertEqual(body["status"], "held")
        self.assertFalse(body["acceptance_ready"])
        self.assertFalse(receipt["ui_ready"])
        self.assertFalse(receipt["html_rendered"])
        self.assertEqual(body["coverage"]["caller_reviewed_count"], 0)
        self.assertIn("<script>", body["result"]["validation_findings"][0])
        self.assertFalse((self.root / "runtime-data/deliverables").exists())
        self.assertLess(len(canonical(saved).encode()), 65536)
        exported = json.loads((self.root / saved["export"]["path"]).read_bytes())
        self.assertEqual(exported["turns"][-1]["web_binding"], body["binding"])

    def viewer(self, saved, **extra):
        spec = importlib.util.spec_from_file_location("web_delivery_viewer", ROOT / "web/prototypes/visual-viewer/build_view.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        response = module.generate(self.root / saved["export"]["path"], out_dir=self.root / "runtime-data/view", **extra)
        raw = (self.root / "runtime-data/view/view-data.js").read_text(encoding="utf-8")
        view = json.loads(raw[raw.index("window.LGAX_VIEW = ") + len("window.LGAX_VIEW = "):].rstrip().rstrip(";"))
        return module, response, view

    def test_viewer_full_sources_and_history_have_exact_snapshot_binding(self):
        self.clock()
        saved = self.save()
        _, response, view = self.viewer(saved)
        self.assertEqual(response["web_delivery"], "verified_binding")
        body = json.loads((self.root / saved["web_result"]["path"]).read_bytes())
        evidence = next(p for p in view["pages"] if p["id"] == "evidence")
        rows = [row for block in evidence["blocks"] if block["type"] == "expander"
                for table in block["blocks"] for row in table.get("rows", [])]
        for source in body["sources"]:
            self.assertIn({"field": "text", "value": source["text"]}, rows)
            self.assertIn({"field": "sha256", "value": source["sha256"]}, rows)
        history = next(p for p in view["pages"] if p["id"] == "history")
        self.assertIn("조사 사건", json.dumps(history, ensure_ascii=False))

    def test_viewer_rejects_structural_only_and_missing_hash_or_changed_audit(self):
        saved = self.save()
        path = self.root / saved["web_result"]["path"]
        _, response, _ = self.viewer(saved, web_result_path=path, web_result_sha256="0" * 64)
        self.assertEqual(response["web_delivery"], "mismatch")
        path.write_bytes(path.read_bytes() + b" ")
        _, response, _ = self.viewer(saved)
        self.assertEqual(response["web_delivery"], "mismatch")
        exported = json.loads((self.root / saved["export"]["path"]).read_bytes())
        exported["turns"][-1]["candidates"][-1]["validation"]["review_required"] = False
        (self.root / saved["export"]["path"]).write_text(canonical(exported), encoding="utf-8")
        _, response, view = self.viewer(saved)
        self.assertEqual(response["web_delivery"], "not_reviewed_current")
        self.assertIn("현재 웹 전달 미검증", json.dumps(view, ensure_ascii=False))

    def test_same_turn_new_version_audit_and_cancel_never_reuse_past_payload_or_insights(self):
        research, audit = self.clock()
        old = self.save()
        binding = old["web_result"]["binding"]
        new = self.save(1, "new")
        module, response, _ = self.viewer(new, web_result_path=self.root / old["web_result"]["path"])
        self.assertEqual(response["web_delivery"], "mismatch")
        export = json.loads((self.root / new["export"]["path"]).read_bytes())
        self.assertEqual(module.classify_insights(export, {**self.handle, "binding": binding}), "unverified_binding")
        self.conv.record_workflow_event({"research_id": research, "event_key": "scope", "kind": "analysis_scope",
                                        "data": {"source_ids": [], "scope_note": "Same result changed audit"}})
        new["export"] = self.conv.export_session({"session_id": self.handle["session_id"]})
        _, response, _ = self.viewer(new)
        self.assertEqual(response["web_delivery"], "mismatch")
        self.store.cancel_turn(**self.handle, cancel_key="stop", reason="사용자 취소", expected_result_version=2, user_submitted=True)
        new["export"] = self.conv.export_session({"session_id": self.handle["session_id"]})
        _, response, _ = self.viewer(new)
        self.assertEqual(response["web_delivery"], "not_reviewed_current")

    def test_same_result_with_later_delivery_history_selects_only_matching_history(self):
        saved = self.save()
        self.conv.read_evidence_batch({**self.handle, "limit": 1})
        saved["export"] = self.conv.export_session({"session_id": self.handle["session_id"]})
        _, response, _ = self.viewer(saved)
        self.assertEqual(response["web_delivery"], "mismatch")
        current = self.prepare()
        self.assertEqual(current["binding"], saved["web_result"]["binding"])
        _, response, _ = self.viewer(saved)
        self.assertEqual(response["web_delivery"], "verified_binding")

    def test_replay_is_immutable_and_corruption_is_not_silently_overwritten(self):
        saved = self.save()["web_result"]
        self.assertTrue(self.prepare()["reused"])
        target = self.root / saved["path"]
        original = target.read_bytes()
        target.write_bytes(original + b" altered")
        self.error("web_delivery_integrity", self.prepare)
        self.assertEqual(target.read_bytes(), original + b" altered")
        self.assertEqual(self.store.get_turn(**self.handle)["result_version"], 1)

    def test_failed_export_and_web_write_preserve_saved_result_and_recover_same_version(self):
        with patch("product_tools.web_delivery.WebDelivery.prepare_web_result", side_effect=OSError("disk failure")):
            saved = self.save()
        self.assertTrue(saved["delivery_ready"])
        self.assertFalse(saved["web_ready"])
        self.assertEqual(saved["web_error"]["code"], "web_delivery_failed")
        self.assertTrue(self.prepare()["ready"])
        self.assertEqual(self.store.get_turn(**self.handle)["result_version"], 1)

    def test_stale_version_code_and_cancel_do_not_deliver_historical_candidate(self):
        self.save()
        self.save(1, "revision")
        self.error("current_state_changed", self.prepare, 1)
        self.store.code_hash = "changed-code"
        self.error("current_state_changed", self.prepare, 2)
        self.store.code_hash = self.store.row(**self.handle)["code_hash"]
        self.store.db.execute("UPDATE turns SET status='cancelled' WHERE turn_id=?", (self.handle["turn_id"],))
        self.error("current_state_changed", self.prepare, 2)

    def test_finish_accepts_only_current_intact_journal_bound_web_payload(self):
        research, audit = self.clock()
        response = self.save()
        self.assertTrue(response["workflow_files_within_budget"])
        saved = response["web_result"]
        event = {"research_id": research, "event_key": "finish-web", "kind": "finish", "data": {
            "delivered_paths": [saved["path"]], "layout_review": {"status": "not_run", "scope": "Web team UI not connected"}}}
        path = self.root / saved["path"]
        original = path.read_bytes()
        path.write_bytes(original + b" changed")
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, event)
        path.write_bytes(original)
        self.conv.record_workflow_event({"research_id": research, "event_key": "scope", "kind": "analysis_scope", "data": {
            "source_ids": [], "scope_note": "Caller report changed after export; regenerate delivery"}})
        self.error("workflow_delivery_missing", self.conv.record_workflow_event, event)
        current = self.prepare()
        event["data"]["delivered_paths"] = [current["path"]]
        finished = self.conv.record_workflow_event(event)
        self.assertIsNotNone(finished["finished_at"])
        self.assertEqual(finished["layout_review"]["verification_status"], "not_verified")
        self.assertTrue(self.prepare()["reused"])

    def test_new_safety_policy_keeps_full_delivery_review_gate_and_no_time_target(self):
        research, audit = self.clock()
        status = audit.status(research)
        self.assertEqual(status["budget_seconds"], 1800)
        self.assertEqual(status["timing_policy"], "natural-completion-v1")
        self.assertIsNone(status["target_seconds"])
        self.assertEqual(status["final_delivery_reserve_seconds"], 90)
        self.error("evidence_coverage_incomplete", self.store.require_evidence_coverage, self.handle["session_id"], self.handle["turn_id"])

    def test_structural_save_without_review_cannot_be_web_delivered(self):
        saved = self.save()
        self.store.db.execute("UPDATE results SET validation_json=? WHERE turn_id=?",
                             (canonical({"contract_valid": True, "review_required": False}), self.handle["turn_id"]))
        self.error("web_review_required", self.prepare)

    def test_explicit_legacy_delivery_cannot_bypass_stored_review(self):
        self.save()
        self.store.db.execute("UPDATE results SET validation_json=? WHERE turn_id=?",
                             (canonical({"contract_valid": True, "review_required": False}), self.handle["turn_id"]))
        with patch("product_tools.delivery.create_deliverables", side_effect=AssertionError("Unreviewed rendering forbidden")) as renderer:
            response = self.conv.deliver_result({**self.handle, "expected_result_version": 1})
        self.assertFalse(response["ready"])
        self.assertEqual(response["error"]["code"], "reader_review_required")
        renderer.assert_not_called()
        self.assertEqual(self.store.get_turn(**self.handle)["result_version"], 1)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM reader_deliveries").fetchone()[0], 0)

    def test_real_cli_recovery_parser_and_dispatch_match_the_saved_payload(self):
        saved = self.save()["web_result"]
        payload = {**self.handle, "expected_result_version": 1}
        # Exercise the real CLI parser/dispatcher in a subprocess, with only
        # its workspace root injected into this test's isolated scratch.
        code = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv.pop(1));import cli;cli.ROOT=Path(sys.argv.pop(1));cli.main()"
        process = subprocess.run([sys.executable, "-c", code, str(ROOT / "product-tools"), str(self.root),
            "--data", str(self.data.root), "--db", str(self.store.path), "prepare_web_result"],
            input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["sha256"], saved["sha256"])
