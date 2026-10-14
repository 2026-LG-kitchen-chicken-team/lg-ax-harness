"""Business write cancellation races and late observations, without native stop claims."""
from concurrent.futures import ThreadPoolExecutor
import copy
import importlib.util
from pathlib import Path
import sys
import sqlite3
import shutil
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint, strict_json
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.conversation import Conversation
from product_tools.web_evidence import WebEvidence
from product_tools.workflow import WorkflowAudit


class CancellationResearchTests(unittest.TestCase):
    """Actual local APIs and retained fixtures; no HTTP or native browser call."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        for relative in ("skills/manifest.json", "agents/product-planning.md"):
            target = self.workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.store = StateStore(self.workspace / "runtime-data/cancel.sqlite", self.data)
        self.addCleanup(self.store.close)
        self.conv = Conversation(self.store, self.workspace)
        self.web = WebEvidence(self.store.path, self.workspace)
        self.addCleanup(self.web.close)
        self.audit = WorkflowAudit(self.store.db, self.workspace)
        self.url = "https://www.lge.co.kr/refrigerators/t876mqq012"
        self.body = "T876MQQ012 취소 장벽 계약 시험 본문."

    def start(self, timed=True):
        payload = {"question": "실제 제품 평가가 아닌 취소 API 계약 시험", "model_id": "T876MQQ012",
                   "session_id": "cancel-research-" + str(getattr(self, "request_count", 0)), "request_key": "original", "user_submitted": True}
        self.request_count = getattr(self, "request_count", 0) + 1
        if timed:
            payload.pop("model_id")
        response = (self.conv.open_product_workflow if timed else self.conv.open_request)(payload)
        self.original = payload
        self.research = "research-" + fingerprint([payload["session_id"], payload["request_key"]])
        model = next(m for m in self.data.models if m["model_id"] == "T876MQQ012")
        self.scope = {key: model[key] for key in ("model_id", "model_version", "document_version")}
        if "turn" in response:
            turn = response["turn"]
            self.handle = {"session_id": turn["session_id"], "turn_id": turn["turn_id"]}
        else:
            self.handle = None

    def capture(self, page):
        return self.web.collect({"research_id": self.research, "page_id": page, "url": self.url,
                                 "observed_text": self.body, "native_tool_name": "unit_fixture_no_browser"}, True)

    def cancel(self):
        if self.handle is None:
            remaining = self.audit.status(self.research)["research_scope"]["remaining_goal_ids"]
            self.conv.record_workflow_event({"research_id": self.research, "event_key": "stop", "kind": "research_stop", "data": {
                "code": "insufficient_evidence", "basis": "Local fixture only", "new_findings": [],
                "remaining_scope": ["Unobserved fixture scope"], "remaining_goal_ids": remaining,
                "limitation_basis": "Local API fixture does not establish product evidence"}})
            response = self.conv.resolve_request({"session_id": self.original["session_id"], "request_key": self.original["request_key"],
                "event_key": "resolve", "expected_request_version": 0, "selection": self.scope})
            self.handle = {"session_id": response["turn"]["session_id"], "turn_id": response["turn"]["turn_id"]}
        response = self.store.cancel_turn(**self.handle, cancel_key="cancel", reason="계약 시험 사용자 취소",
                                         expected_result_version=0, user_submitted=True)
        self.assertEqual(response["turn"]["status"], "cancelled")
        self.assertEqual(response["turn"]["result_version"], 0)

    def import_payload(self, captured, include_research=True):
        payload = {"data_version": "cancel-contract-fixture", "observations": [{
            "snapshot_id": captured["snapshot_id"], "source_id": "CANCEL-CONTRACT-FACT", "kind": "product_fact",
            "scope": self.scope, "location": "Local cancellation fixture", "text": self.body, "support_quote": self.body,
            "published_date": None, "model_matching": "explicit_model_verified", "purchase_verified": None,
            "sponsorship": None, "feature_key": "cancel-contract-fixture", "availability": "present"}]}
        if include_research:
            payload["research_id"] = self.research
        return payload

    def blocked(self, callback):
        try:
            unexpected = callback()
        except ToolError as error:
            self.assertEqual(error.code, "terminal_turn")
        else:
            self.fail("Cancelled turn permitted a new write: " + canonical(unexpected))

    def test_cancelled_timed_and_untimed_requests_block_new_capture(self):
        for timed in (True, False):
            with self.subTest(timed=timed):
                # Each case gets its own original request and clock.
                self.start(timed)
                self.cancel()
                self.blocked(lambda: self.capture("late-" + str(timed)))
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0], 0)

    def test_cancelled_single_import_blocks_catalog_write_and_retains_snapshot(self):
        self.start()
        captured = self.capture("before-cancel")
        self.cancel()
        self.blocked(lambda: self.web.import_evidence(self.data, self.import_payload(captured)))
        self.assertFalse((self.workspace / "runtime-data/catalogs/cancel-contract-fixture").exists())
        self.assertEqual(self.audit.snapshot(self.research, captured["snapshot_id"])["text"], self.body)

    def test_untimed_import_cannot_omit_cancelled_snapshot_request(self):
        self.start(False)
        captured = self.capture("before-cancel")
        self.cancel()
        self.blocked(lambda: self.web.import_evidence(self.data, self.import_payload(captured, False)))
        self.assertFalse((self.workspace / "runtime-data/catalogs/cancel-contract-fixture").exists())

    def test_cancel_preserves_read_replay_and_failure_audit_without_observed_sources(self):
        self.start()
        plan = {"research_id": self.research, "event_key": "plan", "kind": "research_plan", "data": {
            "product_name": "Local cancellation fixture", "coverage": ["positive", "negative", "long_term", "conditions", "counterexamples"],
            "source_plan": ["Local fixture"], "goals": [{"goal_id": "fixture", "kind": "official_spec", "scope_note": "Fixture only"}]}}
        self.conv.record_workflow_event(plan)
        captured = self.capture("before-cancel")
        self.cancel()
        scan = {"research_id": self.research, "event_key": "late-scan", "kind": "source_scan", "data": {
            "source_url": self.url, "page_label": "Local fixture", "status": "observed", "reviews": [],
            "snapshot_ids": [captured["snapshot_id"]], "source_type": "product_document", "goal_ids": ["fixture"], "reason": "Fixture only"}}
        self.blocked(lambda: self.conv.record_workflow_event(scan))
        self.assertEqual(self.conv.record_workflow_event(plan)["event_count"], 2)
        failure = copy.deepcopy(scan)
        failure.update(event_key="late-failure")
        failure["data"].update(status="inaccessible", snapshot_ids=[], reason="Caller-reported failure; no new observation")
        self.assertEqual(self.conv.record_workflow_event(failure)["event_count"], 3)
        self.assertEqual(self.store.get_turn(**self.handle)["status"], "cancelled")

    def test_open_request_still_collects_and_imports_without_new_cancel_api(self):
        self.start(False)
        captured = self.capture("open")
        imported = self.web.import_evidence(self.data, self.import_payload(captured))
        self.assertTrue((self.workspace / imported["data_path"]).is_dir())
        self.assertEqual(self.store.get_turn(**self.handle)["status"], "pending")

    def test_isolated_cli_normal_import_then_cancelled_import_keeps_json_errors(self):
        self.start(False)
        captured = self.capture("cli-before-cancel")
        shutil.copytree(ROOT / "product-tools", self.workspace / "product-tools", ignore=shutil.ignore_patterns("__pycache__"))
        command = [sys.executable, str(self.workspace / "product-tools/cli.py"), "--data", str(self.data.root),
                   "--db", str(self.store.path), "import_web_evidence"]
        payload = self.import_payload(captured, False)
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled):
                if cancelled:
                    self.cancel()
                payload["data_version"] = "cli-cancelled" if cancelled else "cli-normal"
                process = subprocess.run(command, input=canonical(payload), cwd=self.workspace,
                    capture_output=True, text=True, encoding="utf-8", timeout=10)
                self.assertEqual(process.returncode, 1 if cancelled else 0, process.stdout + process.stderr)
                self.assertNotIn("Traceback", process.stderr)
                response = strict_json(process.stdout)
                if cancelled:
                    self.assertEqual(response["error"]["code"], "terminal_turn")
                    self.assertFalse((self.workspace / "runtime-data/catalogs/cli-cancelled").exists())
                else:
                    self.assertTrue(response["ok"])
                    self.assertTrue((self.workspace / response["result"]["data_path"]).is_dir())


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.path = self.workspace / "state.sqlite"
        self.store = StateStore(self.path, self.data)
        self.planning = strict_json((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
        self.session = self.planning["session_id"]
        self.turn = self.store.start_turn(self.planning, True)["turn_id"]

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def candidate(self, status="held"):
        return {"status": status, "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [],
                "assumptions": [], "evidence_refs": [], "validation_findings": ["Test-only insufficient evidence"],
                "revisions": 0, "usage_summary": {"status": "unknown"}}

    def cancel(self, version=0, key="cancel-1", reason="User requested stop", explicit=True):
        return self.store.cancel_turn(self.session, self.turn, key, reason, version, explicit)

    def error(self, code, action, *args):
        with self.assertRaises(ToolError) as caught:
            action(*args)
        self.assertEqual(caught.exception.code, code)

    def test_cancel_reopen_idempotency_history_and_no_backend_claim(self):
        self.store.save_result(self.session, self.turn, "candidate-1", self.candidate(), 0)
        before = [tuple(r) for r in self.store.db.execute("SELECT * FROM results")]
        observed = self.cancel(1)
        self.assertFalse(observed["reused_cancellation"])
        self.assertEqual(observed["turn"]["status"], "cancelled")
        self.assertIsNone(observed["turn"]["latest_result"])
        self.assertEqual(observed["turn"]["result_version"], 1)
        self.assertEqual(observed["turn"]["revision_count"], 0)
        self.assertFalse(observed["native_execution_controlled"])
        self.assertIsNone(observed["backend_stop_observed"])
        self.store.close()
        self.store = StateStore(self.path, self.data)
        replay = self.cancel(1)
        self.assertTrue(replay["reused_cancellation"])
        self.assertEqual(replay["turn"]["cancellation"], observed["turn"]["cancellation"])
        self.assertEqual(before, [tuple(r) for r in self.store.db.execute("SELECT * FROM results")])
        self.error("cancel_conflict", self.cancel, 1, "different-key")
        self.error("cancel_conflict", self.cancel, 1, "cancel-1", "different reason")

    def test_cancel_requires_explicit_input_and_matching_version(self):
        self.error("user_input_required", self.cancel, 0, "cancel-1", "stop", False)
        self.error("state_conflict", self.cancel, 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM cancellations").fetchone()[0], 0)
        self.assertEqual(self.store.get_turn(self.session, self.turn)["status"], "pending")

    def test_cancel_closes_new_and_replayed_candidate_and_invocation_writes(self):
        candidate = self.candidate()
        self.store.save_result(self.session, self.turn, "candidate-1", candidate, 0)
        self.cancel(1)
        for key in ("candidate-1", "new-candidate"):
            self.error("terminal_turn", self.store.save_result, self.session, self.turn, key, candidate, 1)
        self.error("terminal_turn", self.store.invocation, self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)
        self.assertEqual(self.store.get_turn(self.session, self.turn)["result_version"], 1)

    def test_pending_invocation_and_late_usage_remain_observations(self):
        self.store.invocation(self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)
        self.cancel()
        row = self.store.db.execute("SELECT status FROM invocations").fetchone()
        self.assertEqual(row[0], "running")
        self.store.finish_invocation(self.session, self.turn, "inv-1", "succeeded", False)
        call = {"call_id": "call-1", "status": "failed", "input_tokens": None, "output_tokens": None,
                "cache_tokens": None, "reasoning_tokens": None, "cost_usd": None}
        self.store.record_usage(self.session, self.turn, call)
        self.store.record_usage(self.session, self.turn, call)
        state = self.store.get_turn(self.session, self.turn)
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(state["usage_summary"]["recorded_calls"], 1)
        self.assertIsNone(state["usage_summary"]["totals"]["input_tokens"])
        self.assertIsNone(state["cancellation"]["backend_stop_observed"])

    def test_cancel_stale_unfinished_turn_preserves_invalid_context(self):
        self.store.start_turn({**self.planning, "request_key": "new-user-input", "question": "Changed condition"}, True)
        state = self.cancel()["turn"]
        self.assertEqual(state["status"], "cancelled")
        self.assertFalse(state["valid"])
        self.assertIsNone(state["latest_result"])

    def test_terminal_turns_cannot_retroactively_cancel_or_start_calls(self):
        for status in ("completed", "failed", "cancelled"):
            self.store.db.execute("UPDATE turns SET status=? WHERE turn_id=?", (status, self.turn))
            self.error("terminal_turn", self.cancel)
            self.error("terminal_turn", self.store.invocation, self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)

    def test_failed_result_replay_retains_previous_idempotency_contract(self):
        candidate = self.candidate("failed")
        first = self.store.save_result(self.session, self.turn, "failed-result", candidate, 0)
        self.assertTrue(first["accepted"])
        self.store.close()
        self.store = StateStore(self.path, self.data)
        replay = self.store.save_result(self.session, self.turn, "failed-result", candidate, 0)
        self.assertEqual(first, replay)
        self.error("terminal_turn", self.store.save_result, self.session, self.turn, "new-result", candidate, 1)

    def test_cancel_transaction_rolls_back_receipt_and_state_on_storage_failure(self):
        self.store.save_result(self.session, self.turn, "held-result", self.candidate(), 0)
        before = self.store.get_turn(self.session, self.turn)
        self.store.db.execute("CREATE TRIGGER reject_cancel BEFORE UPDATE OF status ON turns WHEN NEW.status='cancelled' BEGIN SELECT RAISE(ABORT,'test cancellation write fault'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.cancel(1)
        self.assertEqual(self.store.get_turn(self.session, self.turn), before)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM cancellations").fetchone()[0], 0)

    def test_cross_session_cancel_finish_usage_do_not_mutate_rows(self):
        self.store.invocation(self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)
        call = {"call_id": "call-1", "status": "failed", "input_tokens": None, "output_tokens": None,
                "cache_tokens": None, "reasoning_tokens": None, "cost_usd": None}
        self.error("turn_not_found", self.store.cancel_turn, "different-session", self.turn, "cancel-1", "stop", 0, True)
        self.error("turn_not_found", self.store.finish_invocation, "different-session", self.turn, "inv-1", "failed", True)
        self.error("turn_not_found", self.store.record_usage, "different-session", self.turn, call)
        self.assertEqual(self.store.db.execute("SELECT status FROM invocations").fetchone()[0], "running")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM cancellations").fetchone()[0], 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM usage").fetchone()[0], 0)

    def test_failed_invocation_retry_is_blocked_after_cancellation(self):
        self.store.invocation(self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)
        self.store.finish_invocation(self.session, self.turn, "inv-1", "failed", True)
        self.cancel()
        self.error("terminal_turn", self.store.invocation, self.session, self.turn, "inv-1", "retrieve_reviews", "a" * 64)
        self.assertEqual(self.store.db.execute("SELECT attempts FROM invocations").fetchone()[0], 1)

    def test_real_conversation_reopen_preserves_cancelled_handle_without_new_turn(self):
        conversation = Conversation(self.store, ROOT)
        payload = {"question": "Test-only planning", "user_submitted": True, "model_id": "AX-R302",
                   "model_version": "1.0", "document_version": "manual-r1", "session_id": "conversation", "request_key": "question-1"}
        handle = conversation.open_request_bundle(payload)["turn"]
        self.store.cancel_turn("conversation", handle["turn_id"], "cancel-1", "stop", 0, True)
        self.store.close()
        self.store = StateStore(self.path, self.data)
        conversation = Conversation(self.store, ROOT)
        reopened = conversation.open_request_bundle(payload)
        self.assertEqual(reopened["turn"]["turn_id"], handle["turn_id"])
        self.assertEqual(reopened["turn"]["status"], "cancelled")
        self.assertIsNone(reopened["bundle"])
        self.assertEqual(conversation.current_request({"session_id": "conversation", "request_key": "question-1"})["turn"]["status"], "cancelled")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns WHERE session_id='conversation'").fetchone()[0], 1)
        next_turn = conversation.open_request({**payload, "request_key": "question-2", "question": "Real new user question", "prior_turn_id": handle["turn_id"]})["turn"]
        self.assertNotEqual(next_turn["turn_id"], handle["turn_id"])
        self.assertEqual(next_turn["result_version"], 0)

    def test_cancel_after_failed_candidate_does_not_reset_revision_budget(self):
        self.store.save_result(self.session, self.turn, "failed-1", {}, 0)
        self.store.save_result(self.session, self.turn, "failed-2", {}, 1)
        state = self.cancel(2)["turn"]
        self.assertEqual((state["result_version"], state["revision_count"]), (2, 1))
        self.assertEqual(len(state["result_history"]), 2)

    def test_save_cancel_race_serializes_with_no_late_candidate(self):
        barrier = threading.Barrier(2)
        def action(kind):
            store = StateStore(self.path, self.data)
            try:
                barrier.wait(timeout=10)
                if kind == "cancel":
                    return store.cancel_turn(self.session, self.turn, "cancel-1", "stop", 0, True)["turn"]["status"]
                return store.save_result(self.session, self.turn, "race-result", self.candidate(), 0)["turn"]["status"]
            except ToolError as exc:
                return exc.code
            finally:
                store.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel = pool.submit(action, "cancel")
            save = pool.submit(action, "save")
            results = (cancel.result(timeout=20), save.result(timeout=20))
        self.assertIn(results, (("cancelled", "terminal_turn"), ("state_conflict", "held")))
        state = self.store.get_turn(self.session, self.turn)
        self.assertEqual(state["result_version"], 0 if state["status"] == "cancelled" else 1)

    def test_cli_dispatch_and_export_include_cancellation_without_rewriting_candidate(self):
        spec = importlib.util.spec_from_file_location("product_cli_cancel_test", ROOT / "product-tools/cli.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = module.dispatch(self.data, self.store, "cancel_turn", {"session_id": self.session, "turn_id": self.turn,
                "cancel_key": "cancel-1", "reason": "stop", "expected_result_version": 0, "user_submitted": True})
        self.assertEqual(output["turn"]["status"], "cancelled")
        report = Conversation(self.store, self.workspace).export_session({"session_id": self.session})
        exported = strict_json((self.workspace / report["path"]).read_text(encoding="utf-8"))
        self.assertEqual(exported["turns"][0]["state"]["cancellation"], output["turn"]["cancellation"])
        self.assertEqual(exported["turns"][0]["candidates"], [])


if __name__ == "__main__":
    unittest.main()
