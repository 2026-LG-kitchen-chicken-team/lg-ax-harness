"""Synthetic contracts are tested here. Native delegation is validated separately."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dev-harness"))
sys.path.insert(0, str(ROOT / ".agents/skills/harness/scripts"))
from checks import run_check, safe_path, verify_receipt, write_json
from cli import checked_result, ledger, packet, complete, task_info, task_binding
from sync import sync_skills
from run_state import init_run, start_task, record_result, update_agent, resume_run
from run_checks import validate_completion


class TempCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-dev-check-")
        self.root = Path(self.temp.name).resolve()
        (self.root / "input.txt").write_text("version one", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, code, **kwargs):
        return run_check(self.root, [sys.executable, "-c", code], inputs=["input.txt"], **kwargs)


class ExecutionChecks(TempCase):
    def test_real_success_and_receipt(self):
        data, relative = self.execute("print('actual output')")
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(verify_receipt(self.root, relative)["status"], "passed")
        self.assertIn("actual output", safe_path(self.root, data["logs"]["stdout.log"]["path"]).read_text())

    def test_failure_cannot_complete(self):
        data, relative = self.execute("import sys; sys.exit(7)")
        self.assertEqual((data["status"], data["exit_code"]), ("failed", 7))
        with self.assertRaises(ValueError):
            verify_receipt(self.root, relative)

    def test_timeout_cannot_complete(self):
        data, relative = self.execute("import time; time.sleep(20)", timeout=0.2)
        self.assertEqual(data["status"], "timeout")
        with self.assertRaises(ValueError):
            verify_receipt(self.root, relative)

    def test_timeout_cleanup_failure_still_records(self):
        if sys.platform == "win32":
            with patch("checks.subprocess.run", side_effect=subprocess.TimeoutExpired("taskkill", 10)):
                data, relative = self.execute("import time; time.sleep(20)", timeout=0.1)
        else:
            with patch("checks.os.killpg", side_effect=OSError("cleanup failed")):
                data, relative = self.execute("import time; time.sleep(20)", timeout=0.1)
        self.assertEqual(data["status"], "timeout")
        self.assertIn("cleanup", data["error"])
        self.assertIsNotNone(data["exit_code"])
        self.assertTrue(safe_path(self.root, relative).is_file())

    def test_missing_executable_is_not_run(self):
        data, _ = run_check(self.root, [str(self.root / "nonexistent-command")])
        self.assertEqual(data["status"], "not_run")
        self.assertIsNone(data["exit_code"])

    def test_output_limit_cannot_pass(self):
        data, relative = self.execute("print('x'*2000)", max_output_bytes=100)
        self.assertEqual(data["status"], "output_limit")
        with self.assertRaises(ValueError):
            verify_receipt(self.root, relative)

    def test_stale_input_rejected(self):
        _, relative = self.execute("print('ok')")
        (self.root / "input.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inputs changed"):
            verify_receipt(self.root, relative)

    def test_tampered_log_rejected(self):
        data, relative = self.execute("print('ok')")
        safe_path(self.root, data["logs"]["stdout.log"]["path"]).write_text("altered")
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            verify_receipt(self.root, relative)

    def test_path_escape_rejected(self):
        for path in ("../outside", str(self.root.parent / "outside")):
            with self.assertRaises(ValueError):
                safe_path(self.root, path)

    def test_reparse_escape_rejected(self):
        link = self.root / "linked"
        if sys.platform == "win32":
            command = ["powershell", "-NoProfile", "-Command",
                       f"New-Item -ItemType Junction -Path '{link}' -Target '{self.root.parent}' | Out-Null"]
            result = subprocess.run(command, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            link.symlink_to(self.root.parent, target_is_directory=True)
        try:
            with self.assertRaises(ValueError):
                safe_path(self.root, "linked/outside.txt")
        finally:
            if sys.platform == "win32":
                link.rmdir()
            else:
                link.unlink()

class LedgerChecks(TempCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / ".agents/skills/harness/scripts", self.root / ".agents/skills/harness/scripts")
        (self.root / ".codex/agents").mkdir(parents=True)
        (self.root / ".codex/config.toml").write_text("[agents]\nmax_concurrent_threads_per_session=3\n")
        shutil.copy2(ROOT / ".codex/agents/evaluator.toml", self.root / ".codex/agents/evaluator.toml")

    def plan(self, overlap=False):
        tasks = []
        for name in ("first", "next"):
            tasks.append({"id": name, "role": "evaluator", "dependencies": [] if overlap or name == "first" else ["first"],
                          "ownership": ["outputs/shared" if overlap else "outputs/" + name], "inputs": ["input.txt"],
                          "context": {"skill_paths": [], "decisions": []}, "acceptance": ["actual check"], "required": True})
        write_json(self.root / "plan.json", {"objective": "synthetic ledger test", "tasks": tasks})
        init_run(self.root, self.root / "plan.json", "run-one")

    def finish(self, task="first"):
        output = self.root / "outputs" / task
        output.parent.mkdir(exist_ok=True)
        output.write_text("actual fixture artifact")
        _, receipt = self.execute("print('ledger fixture check')", binding=task_binding("run-one", task_info(self.root, "run-one", task)))
        data = {"run_id": "run-one", "task_id": task, "status": "completed", "summary": "synthetic test result",
                "artifacts": ["outputs/" + task], "checks": [{"name": "executed fixture", "required": True,
                "receipt": receipt}], "issues": []}
        write_json(self.root / (task + "-result.json"), data)
        path = checked_result(self.root, task + "-result.json")
        record_result(self.root, "run-one", task, path)

    def test_overlap_blocks_second_writer(self):
        self.plan(overlap=True)
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        with self.assertRaisesRegex(ValueError, "ownership|overlap"):
            start_task(self.root, "run-one", "next", "fixture-agent-b")

    def test_fabricated_pass_without_receipt_rejected(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        write_json(self.root / "result.json", {"run_id": "run-one", "task_id": "first", "status": "completed", "checks": [
            {"name": "made up", "status": "passed", "evidence": "PASS", "required": True}]})
        with self.assertRaisesRegex(ValueError, "receipt"):
            checked_result(self.root, "result.json")

    def test_dependencies_failure_propagates(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        data = {"run_id": "run-one", "task_id": "first", "status": "failed", "summary": "fixture failure",
                "artifacts": [], "checks": [{"name": "fixture", "status": "failed", "evidence": "exit 7"}], "issues": ["failure"]}
        write_json(self.root / "result.json", data)
        record_result(self.root, "run-one", "first", self.root / "result.json")
        with self.assertRaises(ValueError):
            start_task(self.root, "run-one", "next", "fixture-agent-b")

    def test_idle_required_then_reused(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        with self.assertRaisesRegex(ValueError, "idle"):
            start_task(self.root, "run-one", "next", "fixture-agent-a")
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        start_task(self.root, "run-one", "next", "fixture-agent-a")

    def test_other_task_receipt_rejected(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        start_task(self.root, "run-one", "next", "fixture-agent-a")
        result = json.loads((self.root / "first-result.json").read_text())
        result["task_id"] = "next"
        write_json(self.root / "wrong-result.json", result)
        with self.assertRaisesRegex(ValueError, "task attempt"):
            checked_result(self.root, "wrong-result.json")

    def test_resume_changed_input_invalidates_dependents(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        start_task(self.root, "run-one", "next", "fixture-agent-a")
        self.finish("next")
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        self.assertEqual(validate_completion(self.root, self.root / ".harness/runs/run-one"), [])
        before = (self.root / ".harness/runs/run-one/plan.json").read_bytes()
        (self.root / "input.txt").write_text("version two")
        resumed = resume_run(self.root, "run-one", "run-two")
        self.assertEqual(resumed["reused"], [])
        self.assertEqual(set(resumed["pending"]), {"first", "next"})
        self.assertEqual(before, (self.root / ".harness/runs/run-one/plan.json").read_bytes())

    def test_packet_includes_role_instruction(self):
        self.plan()
        self.assertIn("심사위원", packet(self.root, "run-one", "first"))

    def test_ledger_external_plan_rejected(self):
        with self.assertRaises(ValueError):
            ledger(self.root, ["init", "--plan-file", "../outside.json", "--run-id", "x"])

    def test_completion_and_resume_recheck_receipts(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        result = json.loads((self.root / ".harness/runs/run-one/task-first/result.json").read_text())
        receipt = json.loads(safe_path(self.root, result["checks"][0]["receipt"]).read_text())
        safe_path(self.root, receipt["logs"]["stdout.log"]["path"]).write_text("changed after acceptance")
        self.assertTrue(any("fingerprint" in error for error in complete(self.root, "run-one")))
        self.assertEqual(ledger(self.root, ["resume", "--run", "run-one", "--new-run", "after-tamper"]), 0)
        plan = json.loads((self.root / ".harness/runs/after-tamper/plan.json").read_text())
        self.assertTrue(all(task["status"] == "pending" for task in plan["tasks"]))

    def test_unchanged_resume_reuses_real_receipt(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        self.assertEqual(ledger(self.root, ["resume", "--run", "run-one", "--new-run", "unchanged"]), 0)
        from cli import receipt_issues
        plan = json.loads((self.root / ".harness/runs/unchanged/plan.json").read_text())
        self.assertEqual(plan["tasks"][0]["status"], "completed")
        self.assertEqual(receipt_issues(self.root, "unchanged"), {})

    def test_completion_rechecks_binding(self):
        self.plan()
        start_task(self.root, "run-one", "first", "fixture-agent-a")
        self.finish()
        update_agent(self.root, "run-one", "fixture-agent-a", "idle", "synthetic observation")
        result = json.loads((self.root / "first-result.json").read_text())
        path = safe_path(self.root, result["checks"][0]["receipt"])
        receipt = json.loads(path.read_text())
        receipt["binding"]["task_id"] = "other"
        write_json(path, receipt)
        self.assertTrue(any("accepted task attempt" in error for error in complete(self.root, "run-one")))


class SyncChecks(unittest.TestCase):
    def test_sync_and_drift_detection(self):
        with tempfile.TemporaryDirectory(prefix="lg-sync-") as directory:
            root = Path(directory)
            shutil.copytree(ROOT / ".agents/skills", root / ".agents/skills")
            self.assertEqual(sync_skills(root), [])
            self.assertEqual(sync_skills(root, check=True), [])
            target = root / ".claude/skills/evaluate-harness/SKILL.md"
            target.write_text("drift")
            self.assertTrue(sync_skills(root, check=True))


if __name__ == "__main__":
    unittest.main()
