"""Reader dependency installation and truthful local readiness checks."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load("adapters/codex/install.py", "reader_codex_install")
portable = load("adapters/common/install.py", "reader_portable_install")


class ReaderInstallTests(unittest.TestCase):
    def test_common_guidance_contract_and_locks_reach_both_runtimes(self):
        with tempfile.TemporaryDirectory(prefix="lg-reader-install-") as temporary:
            for engine, skill_folder in (("codex", ".agents/skills"), ("claude", ".claude/skills")):
                target = Path(temporary) / engine
                result = codex.install(target) if engine == "codex" else portable.install(target, engine)
                self.assertFalse(result["native_verified"])
                for relative in ("docs/contracts/reader-deliverables.md", "product-tools/requirements.in",
                                 "product-tools/requirements.lock", "skills/review-and-revise/references/report-writing.md"):
                    self.assertEqual((target / relative).read_bytes(), (ROOT / relative).read_bytes())
                self.assertFalse((target / "skills/concept-writing/references/concept-images.md").exists())
                self.assertEqual((target / skill_folder / "review-and-revise/references/report-writing.md").read_bytes(),
                                 (ROOT / "skills/review-and-revise/references/report-writing.md").read_bytes())
                self.assertEqual((target / "uv.lock").read_bytes(), (ROOT / "adapters/codex/templates/uv.lock").read_bytes())
                record = json.loads((target / "product-install.json").read_text(encoding="utf-8"))
                self.assertFalse(any(entry["path"].startswith("runtime-data/") for entry in record["files"]))
                checker = codex.check if engine == "codex" else portable.check
                self.assertEqual(checker(target)["errors"], [])

    def test_doctor_reports_missing_dependency_without_claiming_native_success(self):
        for relative in ("adapters/common/product-doctor.py", "adapters/codex/templates/product-doctor.py"):
            doctor = load(relative, "reader_doctor_" + str(len(relative)))
            original = doctor.importlib.import_module

            def imports(name):
                if name == "docx":
                    raise ImportError("Test-only unavailable dependency")
                return original(name)

            with mock.patch.object(doctor.importlib, "import_module", side_effect=imports):
                status = doctor.reporting_dependencies()
            self.assertFalse(status["python-docx"]["available"])
            self.assertIsNone(status["python-docx"]["version"])
            self.assertEqual(status["python-docx"]["error"], "ImportError")

    @unittest.skipUnless(os.environ.get("LG_REPORT_UV") and os.environ.get("LG_REPORT_PYTHON"),
                         "Set local uv/Python paths to verify locked dependency installation")
    def test_locked_install_imports_report_dependencies_in_each_isolated_runtime(self):
        with tempfile.TemporaryDirectory(prefix="lg-reader-locked-") as temporary:
            for engine in ("codex", "claude"):
                target = Path(temporary) / engine
                codex.install(target) if engine == "codex" else portable.install(target, engine)
                install = subprocess.run([os.environ["LG_REPORT_UV"], "sync", "--locked", "--python",
                                          os.environ["LG_REPORT_PYTHON"], "--no-python-downloads"],
                                         cwd=target, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual(install.returncode, 0, install.stderr)
                python = target / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
                check = subprocess.run([str(python), "-c",
                                        "import docx,openpyxl,reportlab,PIL,pypdf,json;"
                                        "import importlib.metadata as m;"
                                        "print(json.dumps({n:m.version(n) for n in ['python-docx','openpyxl','reportlab','Pillow','pypdf']}))"],
                                       cwd=target, capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(check.returncode, 0, check.stderr)
                versions = json.loads(check.stdout)
                self.assertEqual(versions, {"python-docx": "1.2.0", "openpyxl": "3.1.5", "reportlab": "4.4.9",
                                            "Pillow": "12.3.0", "pypdf": "6.10.0"})


if __name__ == "__main__":
    unittest.main()
