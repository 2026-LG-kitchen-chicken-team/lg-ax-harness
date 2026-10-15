"""Local CI orchestration contracts, using real bounded subprocess receipts."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local_ci_entry", ROOT / "scripts/local-ci.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class LocalCITests(unittest.TestCase):
    def test_workflow_contract_and_extended_stages_keep_every_required_command(self):
        actual = ci.re.findall(r"^\s*- run: (.+)$", (ROOT / ".github/workflows/check.yml").read_text(), ci.re.MULTILINE)
        self.assertEqual(actual, ci.WORKFLOW)
        stages = ci.plan("workflow", "python", None, None, ".harness/new", True)
        self.assertEqual([" ".join(s["argv"]) for s in stages], actual)
        extended = ci.plan("extended", "python", "node", "npm-cli.js", ".harness/new", True)
        self.assertEqual(extended[:len(stages)], stages)
        self.assertEqual([s["suite"] for s in extended if s.get("suite")],
                         ["dev-harness", "product-tools", "evaluation", "web", "observer", "evals"])
        self.assertEqual(len([s for s in extended if s["id"].endswith("-ci")]), 2)
        self.assertTrue({"locked-portable", "locked-package"}.issubset({s["id"] for s in extended}))
        self.assertTrue(all(s["timeout"] <= 600 for s in extended if "timeout" in s))

    def test_install_is_explicit_and_does_not_silently_pass_required_stages(self):
        stages = ci.plan("extended", "python", "node", "npm-cli.js", ".harness/new", False)
        gated = [s["id"] for s in stages if s.get("not_run_reason")]
        self.assertEqual(gated, ["locked-python-dependencies", "visual-viewer-ci", "agent-office-ci", "locked-portable", "locked-package"])
        self.assertFalse(next(s for s in stages if s["id"] == "visual-viewer-build").get("not_run_reason"))

    def test_failed_command_is_preserved_and_next_command_still_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input.txt").write_text("owned fixture", encoding="utf-8")
            output = ci.new_output(root, ".harness/ci-run")
            failed = ci.execute_stage(root, output, {"id": "fails", "argv": [sys.executable, "-c", "import sys;print('failure evidence');sys.exit(7)"]}, ["input.txt"])
            passed = ci.execute_stage(root, output, {"id": "continues", "argv": [sys.executable, "-c", "print('continued')"]}, ["input.txt"])
            self.assertEqual((failed["status"], failed["exit_code"]), ("failed", 7))
            self.assertEqual(passed["status"], "passed")
            self.assertEqual(failed["inputs"], {"input.txt": ci.digest(root / "input.txt")})
            self.assertEqual(ci.digest(root / failed["receipt"]), failed["receipt_sha256"])
            self.assertIn("failure evidence", (root / failed["receipt_copy"]).with_name("stdout.log").read_text())
            self.assertEqual(json.loads((output / "fails.json").read_text())["exit_code"], 7)
            with self.assertRaises(FileExistsError):
                ci.new_output(root, ".harness/ci-run")

    def test_not_run_timeout_and_wrong_python_are_not_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = ci.new_output(root, ".harness/run")
            gated = ci.execute_stage(root, output, {"id": "not-run", "argv": ["never-launched"], "not_run_reason": "explicit --install missing"}, [])
            self.assertEqual(gated["status"], "not_run")
            self.assertIsNone(gated["receipt"])
            timeout = ci.execute_stage(root, output, {"id": "timeout", "timeout": .1, "argv": [sys.executable, "-c", "import time;time.sleep(5)"]}, [])
            self.assertEqual(timeout["status"], "timeout")
            wrong = ci.execute_stage(root, output, {"id": "wrong-version", "probe": "python", "argv": [sys.executable, "-c", "print('{\"version\":[3,14,0]}')"]}, [])
            self.assertEqual(wrong["command_status"], "passed")
            self.assertEqual(wrong["status"], "failed")
            observed = ci.execute_stage(root, output, {"id": "real-python", "probe": "python", "argv": [sys.executable, "-c", ci.PYTHON_PROBE]}, [])
            self.assertEqual(observed["observed"]["version"][:2], [3, 12])
            self.assertEqual(observed["status"], "passed")

    def test_skips_are_classified_by_actual_platform_and_reasons_cannot_disappear(self):
        log = "test_a (fixture.A) ... skipped 'Windows Explorer invocation'\ntest_b (fixture.B) ... skipped 'uv not on PATH: the exact command runs through uv'\nRan 2 tests in 0.0s\nOK (skipped=2)\n"
        linux = ci.skip_details(log, windows=False)
        self.assertEqual(linux["tests_run"], 2)
        self.assertEqual(len(linux["unexpected_skips"]), 1)
        self.assertTrue(linux["skip_reasons_complete"])
        self.assertEqual(len(ci.skip_details(log, windows=True)["unexpected_skips"]), 2)
        self.assertFalse(ci.skip_details("Ran 3 tests in 0s\nOK (skipped=1)", windows=False)["skip_reasons_complete"])

    def test_nested_unittest_receipt_detects_missing_dependency_skip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = ci.new_output(root, ".harness/nested")
            inner, relative = ci.run_check(root, [sys.executable, "-c", "import sys;sys.stderr.write(\"test_dep (fixture.Check) ... skipped 'missing required dependency'\\nRan 1 test in 0.0s\\nOK (skipped=1)\\n\")"])
            stage = {"id": "suite", "suite": "fixture", "argv": [sys.executable, "-c", "import json;print(json.dumps(" + repr({"receipt": relative}) + "))"]}
            result = ci.execute_stage(root, output, stage, [])
            self.assertEqual(result["command_status"], "passed")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["unittest"]["unexpected_skips"][0]["reason"], "missing required dependency")
            self.assertTrue((root / result["inner_receipt_copy"]).is_file())

    def test_output_paths_and_environment_are_confined_and_restored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path in ("../escape", "results/ci", str(root / "absolute")):
                with self.assertRaises(ValueError):
                    ci.new_output(root, path)
            with patch.dict(os.environ, {"LOCAL_CI_FIXTURE": "original"}):
                with ci.environment({"LOCAL_CI_FIXTURE": "child", "LOCAL_CI_MISSING": None}):
                    self.assertEqual(os.environ["LOCAL_CI_FIXTURE"], "child")
                self.assertEqual(os.environ["LOCAL_CI_FIXTURE"], "original")

    def test_asset_changes_include_deletions_without_rewriting_manifest(self):
        before = {"inputs": {"web/prototypes/visual-viewer/index.html": "old", "skills/manifest.json": "m", "README.md": "r"}}
        after = {"inputs": {"web/prototypes/visual-viewer/index.html": "new", "skills/manifest.json": "m", "README.md": "r"}}
        self.assertEqual(ci.changed(ci.assets(before), ci.assets(after)), [{"path": "web/prototypes/visual-viewer/index.html", "before_sha256": "old", "after_sha256": "new"}])
        self.assertEqual(ci.changed({"deleted": "sha"}, {}), [{"path": "deleted", "before_sha256": "sha", "after_sha256": None}])

    def test_overall_failure_continues_and_writes_actual_child_receipts(self):
        # Probe/source fixtures keep this an orchestration test, not a full CI run.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/check.yml").write_text("\n".join("- run: " + command for command in ci.WORKFLOW))
            snapshot = {"head": "fixture-only", "dirty": False, "inputs": {}, "git_commands": []}
            actual_execute = ci.execute_stage

            def execute(root, output, stage, inputs):
                if stage.get("probe"):
                    return {**stage, "status": "passed", "exit_code": 0}
                return actual_execute(root, output, stage, inputs)

            stages = [{"id": "first-fails", "argv": [sys.executable, "-c", "raise SystemExit(9)"]},
                      {"id": "second-runs", "argv": [sys.executable, "-c", "print('collected after failure')"]}]
            with patch.object(ci, "ROOT", root), patch.object(ci, "source_state", return_value=snapshot), \
                 patch.object(ci, "execute_stage", side_effect=execute), patch.object(ci, "plan", return_value=stages), \
                 patch.object(ci.shutil, "which", return_value=sys.executable):
                code = ci.main(["--python", sys.executable, "--uv", sys.executable, "--output", ".harness/run"])
            report = json.loads((root / ".harness/run/report.json").read_text())
            self.assertEqual((code, report["status"]), (1, "failed"))
            self.assertEqual([row["exit_code"] for row in report["stages"][-2:]], [9, 0])
            self.assertTrue(all(row["receipt"] for row in report["stages"][-2:]))


if __name__ == "__main__":
    unittest.main()
