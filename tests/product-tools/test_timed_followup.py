"""Completed A -> explicit timed F through actual local APIs; synthetic input only."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, strict_json
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.workflow import WorkflowAudit


class TimedFollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store = StateStore(self.root / "runtime-data/test.sqlite", self.data)
        self.addCleanup(self.store.close)
        self.conv = Conversation(self.store, self.root)
        self.audit = WorkflowAudit(self.store.db, self.root)
        self.now = datetime.now(timezone.utc)
        self.clock = patch("product_tools.workflow.utc_now", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.original = {"question": "합성 코드 계약 최초 업무 A", "user_submitted": True,
                         "session_id": "timed-lineage", "request_key": "A"}

    def error(self, code, callback):
        with self.assertRaises(ToolError) as error:
            callback()
        self.assertEqual(error.exception.code, code)

    def stop(self, research):
        self.conv.record_workflow_event({"research_id": research, "event_key": "stop", "kind": "research_stop", "data": {
            "code": "sufficient_evidence", "basis": "Fixed synthetic catalog API fixture only; no web observation",
            "new_findings": [], "remaining_scope": []}})

    def complete(self, turn, research):
        handle = {"session_id": turn["session_id"], "turn_id": turn["turn_id"]}
        refs, offset = [], 0
        while offset is not None:
            batch = self.conv.read_evidence_batch({**handle, "offset": offset, "limit": 20})
            refs.extend(batch["evidence_refs"])
            offset = batch["next_offset"]
        self.conv.record_evidence_review({**handle, "review_key": "fixture-all", "records": [
            {"source_id": ref["source_id"], "disposition": "reviewed", "reason": "Synthetic contract fixture; no semantic certification"}
            for ref in refs]})
        self.conv.record_workflow_event({"research_id": research, "event_key": "analysis", "kind": "analysis_scope", "data": {
            "source_ids": [ref["source_id"] for ref in refs], "scope_note": "Synthetic fixture registered source coverage"}})
        review = next(r for r in refs if self.data.source(r["source_id"])["kind"] == "review")
        fact = next(r for r in refs if self.data.source(r["source_id"])["kind"] == "product_fact")
        rid, fid = review["source_id"], fact["source_id"]
        result = {"status": "completed", "pains": [{"id": "p", "text": review["quote"], "source_ids": [rid]}],
            "existing_features": [{"id": "f", "text": fact["quote"], "source_ids": [fid]}],
            "remaining_pains": [{"id": "r", "text": "합성 계약용 조건부 전제", "source_ids": [rid]}],
            "concepts": [{"id": "c", "text": "합성 API 계약용 조건부 기획; 실제 제품 판단 아님", "source_ids": [rid, fid],
                "requirements": ["계약 시험"], "requires_hardware": False, "assumptions": ["합성 시험만 해당"]}],
            "assumptions": ["시장/구현/효과 인증이 아닌 합성 계약 시험"], "evidence_refs": [review, fact],
            "validation_findings": [], "revisions": 0, "usage_summary": {"status": "unknown"}}
        assessment = {"claim_checks": [{"claim_id": claim["id"], "source_ids": claim["source_ids"],
            "support_status": "supported", "scope_relation": "current_model", "rationale": "Synthetic reported-review fixture"}
            for key in ("pains", "existing_features", "remaining_pains", "concepts") for claim in result[key]],
            "feature_matches": [{"remaining_pain_id": "r", "pain_id": "p", "feature_source_ids": [fid], "resolution": "unresolved", "rationale": "Fixture only"}],
            "concept_links": [{"concept_id": "c", "remaining_pain_ids": ["r"], "duplicates_existing": False,
                "geometry_required": False, "geometry_known": False, "geometry_source_ids": [], "rationale": "Fixture only"}]}
        saved = self.conv.save_and_export({**handle, "result_key": "candidate-0", "expected_result_version": 0,
                                          "result": result, "assessment": assessment, "report": False})
        self.assertTrue(saved["save"]["accepted"])
        self.assertTrue(saved["web_ready"])
        self.assertEqual(saved["completion_summary"]["binding"]["result_version"], 1)
        finished = self.conv.record_workflow_event({"research_id": research, "event_key": "finish", "kind": "finish", "data": {
            "delivered_paths": [saved["web_result"]["path"]], "layout_review": {"status": "not_run", "scope": "Synthetic API test; no HTML UI"}}})
        self.assertIsNotNone(finished["finished_at"])
        return saved

    def completed_a(self):
        opened = self.conv.open_product_workflow(self.original)
        research = opened["research_id"]
        self.stop(research)
        model = self.data.models[0]
        selected = {key: model[key] for key in ("model_id", "model_version", "document_version")}
        bound = self.conv.resolve_request({"session_id": self.original["session_id"], "request_key": "A",
            "expected_request_version": 0, "event_key": "resolve", "selection": selected})
        saved = self.complete(bound["turn"], research)
        return bound["turn"], research, saved

    def new_f(self, a, **changes):
        return {"question": "  사용자 명시 새 후속 업무 F\n추가 조건 원문  ", "user_submitted": True,
                "session_id": a["session_id"], "request_key": "F", "prior_turn_id": a["turn_id"], **changes}

    def test_completed_a_then_new_timed_f_saves_finishes_and_preserves_a(self):
        a, research_a, saved_a = self.completed_a()
        clock_a = tuple(self.store.db.execute("SELECT * FROM product_workflows WHERE research_id=?", (research_a,)).fetchone())
        results_a = [tuple(row) for row in self.store.db.execute("SELECT * FROM results WHERE turn_id=?", (a["turn_id"],))]
        self.now += timedelta(seconds=30)
        payload = self.new_f(a)
        f = self.conv.open_product_workflow(payload)
        self.assertNotEqual(f["research_id"], research_a)
        self.assertNotEqual(f["turn"]["turn_id"], a["turn_id"])
        self.assertEqual(f["turn"]["session_id"], a["session_id"])
        self.assertEqual(f["turn"]["input"]["question"], payload["question"])
        self.assertEqual(f["previous"]["turn_id"], a["turn_id"])
        self.assertEqual(f["previous"]["result"], strict_json(self.store.db.execute("SELECT payload FROM results WHERE turn_id=?", (a["turn_id"],)).fetchone()[0]))
        self.assertEqual(f["workflow"]["started_at"], self.now.isoformat())
        self.assertEqual(f["turn"]["result_version"], 0)
        self.assertEqual(json.loads(self.store.db.execute("SELECT payload FROM conversation_requests WHERE turn_id=?", (f["turn"]["turn_id"],)).fetchone()[0])["prior_turn_id"], a["turn_id"])
        self.stop(f["research_id"])
        saved_f = self.complete(f["turn"], f["research_id"])
        self.assertEqual(saved_f["web_result"]["binding"]["turn_id"], f["turn"]["turn_id"])
        self.assertEqual(tuple(self.store.db.execute("SELECT * FROM product_workflows WHERE research_id=?", (research_a,)).fetchone()), clock_a)
        self.assertEqual([tuple(row) for row in self.store.db.execute("SELECT * FROM results WHERE turn_id=?", (a["turn_id"],))], results_a)
        prior = self.store.get_turn(a["session_id"], a["turn_id"])
        self.assertEqual((prior["status"], prior["result_version"], prior["revision_count"]), ("completed", 1, 0))
        self.assertEqual(saved_a["web_result"]["binding"]["turn_id"], a["turn_id"])

    def test_wrong_missing_and_cross_session_prior_fail_without_a_new_clock(self):
        a, _, _ = self.completed_a()
        cases = [("turn_not_found", self.new_f(a, prior_turn_id="turn-does-not-exist")),
                 ("turn_not_found", self.new_f(a, session_id="another-session")),
                 ("invalid_input", self.new_f(a, prior_turn_id={"invalid": "type"})),
                 ("user_input_required", self.new_f(a, user_submitted=False))]
        without_session = self.new_f(a)
        without_session.pop("session_id")
        cases.append(("invalid_input", without_session))
        for code, payload in cases:
            self.error(code, lambda: self.conv.open_product_workflow(payload))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM product_workflows").fetchone()[0], 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 1)

    def test_same_f_request_replay_and_expiry_cannot_reset_budget_or_input(self):
        a, research_a, _ = self.completed_a()
        payload = self.new_f(a, budget_seconds=600)
        f = self.conv.open_product_workflow(payload)
        self.now += timedelta(seconds=601)
        replay = self.conv.open_product_workflow(payload)
        self.assertEqual(replay["turn"]["turn_id"], f["turn"]["turn_id"])
        self.assertEqual(replay["workflow"]["started_at"], f["workflow"]["started_at"])
        self.assertTrue(replay["workflow"]["expired"])
        self.error("workflow_conflict", lambda: self.conv.open_product_workflow({**payload, "budget_seconds": 1800}))
        self.error("request_conflict", lambda: self.conv.open_product_workflow({**payload, "question": "same-key changed input"}))
        self.error("request_conflict", lambda: self.conv.open_product_workflow(self.new_f(a, request_key="A")))
        self.assertIsNotNone(self.audit.status(research_a)["finished_at"])
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 2)

    def test_evidence_skill_wrapper_forwards_the_explicit_prior_id(self):
        a, _, _ = self.completed_a()
        shutil.copytree(ROOT / "product-tools", self.root / "product-tools", ignore=shutil.ignore_patterns("__pycache__"))
        script = self.root / "skills/evidence-retrieval/scripts/run.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "skills/evidence-retrieval/scripts/run.py", script)
        payload = self.new_f(a)
        input_path = self.root / "runtime-data/new-followup.json"
        input_path.write_text(canonical(payload), encoding="utf-8")
        process = subprocess.run([sys.executable, str(script), "open_product_workflow", "--input", str(input_path),
            "--data", str(self.data.root), "--db", str(self.store.path)], cwd=self.root, capture_output=True,
            text=True, encoding="utf-8", timeout=10)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        response = strict_json(process.stdout)["result"]
        self.assertEqual(response["previous"]["turn_id"], a["turn_id"])
        self.assertNotEqual(response["turn"]["turn_id"], a["turn_id"])
        self.assertEqual(response["turn"]["input"]["question"], payload["question"])


if __name__ == "__main__":
    unittest.main()
