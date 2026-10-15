"""First-run diagnostics must distinguish local setup from native permissions."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeReadinessTests(unittest.TestCase):
    def invoke(self, doctor, arguments):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["product-doctor.py", *arguments]), contextlib.redirect_stdout(output):
            code = doctor.main()
        return code, json.loads(output.getvalue())

    def test_wrong_python_stops_before_auth_storage_or_dependency_checks(self):
        for relative in ("adapters/codex/templates/product-doctor.py", "adapters/common/product-doctor.py"):
            doctor = load(relative, "unsupported_runtime_doctor")
            with mock.patch.object(sys, "version_info", (3, 14, 0)), \
                    mock.patch.object(doctor.subprocess, "run") as run, \
                    mock.patch.object(doctor, "reporting_dependencies") as dependencies:
                code, result = self.invoke(doctor, [])
            self.assertEqual(code, 1)
            self.assertEqual(result["readiness"], "unsupported_python")
            self.assertFalse(result["python"]["supported"])
            run.assert_not_called()
            dependencies.assert_not_called()

    def test_codex_local_stage_succeeds_without_cli_and_never_checks_auth(self):
        installer = load("adapters/codex/install.py", "setup_codex_installer")
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_codex_doctor")
        with tempfile.TemporaryDirectory(prefix="lg-setup-local-") as temporary:
            target = Path(temporary) / "codex"
            installer.install(target)
            with mock.patch.object(doctor, "ROOT", target), \
                    mock.patch.object(doctor.shutil, "which", return_value=None), \
                    mock.patch.object(doctor, "reporting_dependencies", return_value={}), \
                    mock.patch.object(doctor.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
                code, result = self.invoke(doctor, ["--local-only"])
            self.assertEqual(code, 0)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][1:], ["product-tools/cli.py", "doctor"])
            self.assertEqual(result["runtime"]["login_status"], "not_checked_local_only")
            self.assertEqual(result["native_permissions"], "unverified")
            self.assertEqual(result["workspace_storage"], "local_process_checked")

    def test_broken_optional_claude_cli_does_not_block_gui_local_setup(self):
        installer = load("adapters/common/install.py", "setup_claude_installer")
        doctor = load("adapters/common/product-doctor.py", "setup_claude_doctor")
        with tempfile.TemporaryDirectory(prefix="lg-setup-gui-") as temporary:
            target = Path(temporary) / "claude"
            installer.install(target, "claude")
            for arguments, expected in (([], 0), (["--require-native"], 1)):
                with mock.patch.object(doctor, "ROOT", target), \
                        mock.patch.object(doctor.shutil, "which", return_value="claude"), \
                        mock.patch.object(doctor, "reporting_dependencies", return_value={}), \
                        mock.patch.object(doctor.subprocess, "run", side_effect=[OSError("unavailable CLI"), subprocess.CompletedProcess([], 0, "", "")]):
                    code, result = self.invoke(doctor, arguments)
                self.assertEqual(code, expected)
                self.assertTrue(result["errors"] if arguments else result["warnings"])
                self.assertEqual(result["runtime"]["authentication"], "unobserved")
                self.assertEqual(result["model_access"], "unverified")

    def test_codex_signed_in_stage_checks_cli_and_local_tool_without_claiming_model_access(self):
        installer = load("adapters/codex/install.py", "setup_signed_in_installer")
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_signed_in_doctor")
        with tempfile.TemporaryDirectory(prefix="lg-setup-signed-in-") as temporary:
            target = Path(temporary) / "codex"
            installer.install(target)
            responses = [subprocess.CompletedProcess([], 0, "codex-cli test", ""),
                         subprocess.CompletedProcess([], 0, "", "Logged in using ChatGPT"),
                         subprocess.CompletedProcess([], 0, "", "")]
            with mock.patch.object(doctor, "ROOT", target), \
                    mock.patch.object(doctor.shutil, "which", return_value="codex"), \
                    mock.patch.object(doctor, "reporting_dependencies", return_value={}), \
                    mock.patch.object(doctor.subprocess, "run", side_effect=responses) as run:
                code, result = self.invoke(doctor, [])
            self.assertEqual(code, 0)
            self.assertEqual(run.call_count, 3)
            self.assertEqual(result["readiness"], "cli_status_checked")
            self.assertEqual(result["runtime"]["login_status"], "Logged in using ChatGPT")
            self.assertEqual(result["native_permissions"], "unverified")
            self.assertEqual(result["model_access"], "unverified")

    def test_local_storage_failure_cannot_be_reported_as_ready(self):
        installer = load("adapters/codex/install.py", "setup_failed_storage_installer")
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_failed_storage_doctor")
        with tempfile.TemporaryDirectory(prefix="lg-setup-storage-") as temporary:
            target = Path(temporary) / "codex"
            installer.install(target)
            with mock.patch.object(doctor, "ROOT", target), \
                    mock.patch.object(doctor, "reporting_dependencies", return_value={}), \
                    mock.patch.object(doctor.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "storage error")):
                code, result = self.invoke(doctor, ["--local-only"])
            self.assertEqual(code, 1)
            self.assertEqual(result["workspace_storage"], "failed")
            self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
