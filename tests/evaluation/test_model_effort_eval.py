"""Observer boundaries only; these local stubs do not measure AI quality."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evals/runner"))
import model_effort_eval as ev


class ObserverBoundaryTests(unittest.TestCase):
    def test_unsupported_delegation_rejected_before_workspace_or_process(self):
        cases=[({"provider":"claude","product_reviewer":True},{}),
               ({"provider":"claude","product_researchers":True},{}),
               ({"provider":"codex","product_reviewer":True},{"mode":"fresh_online_e2e"})]
        with tempfile.TemporaryDirectory(prefix="lg-effort-preflight-") as folder:
            for job,plan in cases:
                with patch.object(ev,"prepare_job") as prepare, patch.object(ev,"execute") as execute:
                    with self.assertRaises(ValueError):
                        ev.run_job(job,plan,Path(folder))
                    prepare.assert_not_called()
                    execute.assert_not_called()

    def test_progress_message_at_timeout_is_not_final_delivery(self):
        code = ('import json,sys,time;sys.stdin.read();'
                'print(json.dumps({"type":"item.completed","item":{"id":"progress","type":"agent_message","text":"working"}}),flush=True);'
                'time.sleep(30)')
        with tempfile.TemporaryDirectory(prefix="lg-effort-timeout-") as folder:
            root = Path(folder)
            result = ev.execute([sys.executable, "-c", code], root, "observer test", root / "run", .6)
            self.assertEqual(result["status"], "timeout")
            self.assertFalse(result["turn_completed"])
            self.assertFalse(result["final_delivery_observed"])
            self.assertTrue((root / "run/last-message.txt").exists())
            self.assertFalse((root / "run/final.txt").exists())
            self.assertTrue(result["termination"]["needed"])

    def test_turn_completion_and_exit_preserve_final_and_usage(self):
        code = ('import json,sys;sys.stdin.read();'
                'print(json.dumps({"type":"item.completed","item":{"id":"answer","type":"agent_message","text":"done"}}));'
                'print(json.dumps({"type":"turn.completed","usage":{"input_tokens":20,"output_tokens":4}}))')
        with tempfile.TemporaryDirectory(prefix="lg-effort-complete-") as folder:
            root = Path(folder)
            result = ev.execute([sys.executable, "-c", code], root, "observer test", root / "run", 5)
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(result["exit_code"], 0)
            self.assertTrue(result["final_delivery_observed"])
            self.assertEqual(result["reported_usage"]["input_tokens"], 20)
            self.assertEqual((root / "run/final.txt").read_text(), "done")

    def test_web_commands_overlap_and_missing_end_stay_distinct(self):
        spans, state = {}, {}
        for at, kind, identity, event_type in [(1,"web_search","web","item.started"),
                (2,"command_execution","cmd","item.started"), (4,"web_search","web","item.completed"),
                (5,"command_execution","cmd","item.completed"), (6,"web_search","pending","item.started")]:
            ev.observe_event({"type": event_type, "item": {"id": identity, "type": kind}}, at, spans, state)
        self.assertEqual(ev.interval_union_seconds(spans.values()), 4)
        self.assertEqual(spans["web"]["bucket"], "web_search")
        self.assertNotIn("ended", spans["pending"])

    def test_duplicate_job_ids_rejected_before_preparation(self):
        with tempfile.TemporaryDirectory(prefix="lg-effort-identities-") as folder:
            plan = Path(folder) / "plan.json"
            plan.write_text(json.dumps({"jobs": [{"id":"same"}, {"id":"same"}]}))
            with patch.object(sys, "argv", ["model_effort_eval", "--plan", str(plan), "--provider", "codex"]), patch.object(ev, "prepare_job") as prepare:
                with self.assertRaisesRegex(ValueError, "unique"):
                    ev.main()
                prepare.assert_not_called()

    def test_observation_failure_does_not_get_success_exit(self):
        with tempfile.TemporaryDirectory(prefix="lg-effort-observation-") as folder:
            plan = Path(folder) / "plan.json"
            plan.write_text(json.dumps({"run_root": str(Path(folder) / "runs"), "timeout_seconds":30,
                "jobs":[{"id":"job","provider":"codex"}]}))
            with patch.object(sys, "argv", ["model_effort_eval", "--plan", str(plan), "--provider", "codex"]), patch.object(ev, "run_job", return_value={"status":"succeeded", "observation_errors":["collector incomplete"]}):
                self.assertEqual(ev.main(), 1)

    def test_collector_error_cannot_certify_a_final_message(self):
        code = ('import json,sys;sys.stdin.read();'
                'print(json.dumps({"type":"item.completed","item":{"id":"answer","type":"agent_message","text":"done"}}));'
                'print(json.dumps({"type":"turn.completed","usage":{"input_tokens":20,"output_tokens":4}}));'
                'print(json.dumps({"type":"item.completed","item":"invalid observer fixture"}))')
        with tempfile.TemporaryDirectory(prefix="lg-effort-collector-") as folder:
            root = Path(folder)
            result = ev.execute([sys.executable, "-c", code], root, "observer test", root / "run", 5)
            self.assertTrue(result["turn_completed"])
            self.assertEqual(result["exit_code"], 0)
            self.assertFalse(result["observation_complete"])
            self.assertFalse(result["final_delivery_observed"])
            self.assertTrue(result["observation_errors"])
            self.assertFalse((root / "run/final.txt").exists())

    def test_database_observation_error_is_retained_in_integrated_receipt(self):
        with tempfile.TemporaryDirectory(prefix="lg-effort-database-") as folder:
            root = Path(folder)
            workspace = root / "workspace"
            (workspace / "skills").mkdir(parents=True)
            (workspace / "skills/manifest.json").write_text("{}")
            def stub_execute(args, cwd, prompt, directory, timeout):
                directory.mkdir(parents=True)
                (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
                (directory / "native.jsonl").write_text("observer-only stub\n")
                return {"status":"succeeded", "observation_errors":[], "elapsed_seconds":1,
                        "native_id":None, "reported_usage":None}
            job = {"id":"job", "provider":"codex", "model":"fixture", "effort":"medium", "product":"fixture", "question":"observer-only test"}
            with patch.object(ev, "prepare_job", return_value=workspace), patch.object(ev, "protected", return_value={}), patch.object(ev, "execute", side_effect=stub_execute), patch.object(ev, "stored", side_effect=ValueError("fixture incomplete DB")), patch.object(ev, "rollout_observation", return_value={}):
                result = ev.run_job(job, {"codex":"not-invoked", "timeout_seconds":30}, root / "runs")
            self.assertEqual(result["stored"]["error"], "fixture incomplete DB")
            self.assertIn("database observation: fixture incomplete DB", result["observation_errors"])
            self.assertFalse(result["observation_complete"])
            self.assertEqual(json.loads((root / "runs/job/result.json").read_text())["observation_errors"], result["observation_errors"])


if __name__ == "__main__":
    unittest.main()
