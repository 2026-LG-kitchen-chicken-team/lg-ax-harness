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


class SandboxReadinessTests(unittest.TestCase):
    def venv(self, doctor):
        # Any existing interpreter stands in for the installed .venv/Scripts/python.exe.
        return mock.patch.object(doctor, "tool_python", return_value=Path(sys.executable))

    def test_mxc_probe_uses_managed_workspace_profile_and_tool_python(self):
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_mxc_probe")
        local = {"errors": [], "readiness": "local_only", "workspace_storage": "local_process_checked"}
        response = subprocess.CompletedProcess([], 0, json.dumps(local), "")
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(doctor.shutil, "which", return_value="uv"), \
                self.venv(doctor), mock.patch.object(doctor.subprocess, "run", return_value=response) as run:
            result = doctor.check_windows_sandbox("codex", "mxc")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["tool_python"], ".venv/Scripts/python.exe")
        self.assertEqual(result["uv_run"], {"status": "passed", "required": False, "exit_code": 0})
        self.assertEqual(run.call_count, 2)
        python, uv = (call.args[0] for call in run.call_args_list)
        for command in (python, uv):
            self.assertIn("windows.sandbox=mxc", command)
            self.assertIn("--include-managed-config", command)
            self.assertIn(":workspace", command)
            self.assertEqual(command[-1], "--local-only")
            self.assertNotIn("danger-full-access", command)
        self.assertEqual(python[python.index("--") + 1], sys.executable)
        self.assertEqual(uv[uv.index("--") + 1:], ["uv", "run", "python", "product-doctor.py", "--local-only"])

    def test_uv_launcher_failure_is_reported_but_not_required(self):
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_uv_probe")
        local = {"errors": [], "readiness": "local_only", "workspace_storage": "local_process_checked"}
        responses = [subprocess.CompletedProcess([], 0, json.dumps(local), ""),
                     subprocess.CompletedProcess([], 2, "", "error: Failed to query Python interpreter\n  Caused by: (os error 5)")]
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(doctor.shutil, "which", return_value="uv"), \
                self.venv(doctor), mock.patch.object(doctor.subprocess, "run", side_effect=responses) as run:
            result = doctor.check_windows_sandbox("codex", "mxc")
        self.assertEqual(result["status"], "passed")
        self.assertNotIn("error", result)
        self.assertEqual(result["workspace_storage"], "local_process_checked")
        self.assertEqual(result["uv_run"]["status"], "failed")
        self.assertFalse(result["uv_run"]["required"])
        self.assertIn("os error 5", result["uv_run"]["error"])
        self.assertEqual(run.call_count, 2)

    def test_missing_tool_python_stops_before_sandbox(self):
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_missing_venv_probe")
        with tempfile.TemporaryDirectory(prefix="lg-setup-no-venv-") as temporary, \
                mock.patch.object(sys, "platform", "win32"), mock.patch.object(doctor, "ROOT", Path(temporary)), \
                mock.patch.object(doctor.subprocess, "run") as run:
            result = doctor.check_windows_sandbox("codex", "mxc")
        self.assertEqual(result["status"], "failed")
        self.assertIn("uv sync --locked --python 3.12", result["error"])
        run.assert_not_called()

    def test_failed_probe_does_not_retry_or_fall_back_to_full_access(self):
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_failed_probe")
        response = subprocess.CompletedProcess([], 1, "", "windows sandbox failed: setup refresh had errors")
        with mock.patch.object(sys, "platform", "win32"), self.venv(doctor), \
                mock.patch.object(doctor.subprocess, "run", return_value=response) as run:
            result = doctor.check_windows_sandbox("codex", "mxc")
        self.assertEqual(result["status"], "failed")
        self.assertIn("setup refresh had errors", result["error"])
        self.assertEqual(run.call_count, 1)

    def test_successful_process_does_not_hide_local_storage_failure(self):
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_incomplete_probe")
        response = subprocess.CompletedProcess([], 0, json.dumps({"errors": ["storage failed"], "readiness": "local_only"}), "")
        with mock.patch.object(sys, "platform", "win32"), self.venv(doctor), \
                mock.patch.object(doctor.subprocess, "run", return_value=response) as run:
            result = doctor.check_windows_sandbox("codex", "mxc")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(run.call_count, 1)

    def test_old_cli_is_stopped_before_unsupported_sandbox_flags(self):
        installer = load("adapters/codex/install.py", "setup_old_cli_installer")
        doctor = load("adapters/codex/templates/product-doctor.py", "setup_old_cli_doctor")
        with tempfile.TemporaryDirectory(prefix="lg-setup-old-cli-") as temporary:
            target = Path(temporary) / "codex"
            installer.install(target)
            responses = [subprocess.CompletedProcess([], 0, "codex-cli 0.161.0", ""),
                         subprocess.CompletedProcess([], 0, "Logged in using ChatGPT", ""),
                         subprocess.CompletedProcess([], 0, "", "")]
            with mock.patch.object(doctor, "ROOT", target), mock.patch.object(doctor.shutil, "which", return_value="codex"), \
                    mock.patch.object(doctor, "reporting_dependencies", return_value={}), \
                    mock.patch.object(doctor.subprocess, "run", side_effect=responses), \
                    mock.patch.object(doctor, "check_windows_sandbox") as sandbox:
                code, result = RuntimeReadinessTests().invoke(doctor, ["--check-sandbox"])
            self.assertEqual(code, 1)
            self.assertIn("0.162.0", result["errors"][0])
            sandbox.assert_not_called()


if __name__ == "__main__":
    unittest.main()
