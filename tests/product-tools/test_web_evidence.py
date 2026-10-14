"""Malformed single-import inputs stay structured before cancel/request tracking."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, strict_json
from product_tools.dataset import Dataset
from product_tools.web_evidence import WebEvidence


class SingleImportShapeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.web = WebEvidence(self.workspace / "runtime-data/shape.sqlite", self.workspace)
        self.addCleanup(self.web.close)

    def malformed_observations(self):
        return [None, "invalid", 7, True, {}, [], ["invalid"], [None], [7], [False], [[]], [{}]]

    def test_array_and_entry_shapes_raise_invalid_input_before_request_tracking(self):
        for observations in self.malformed_observations():
            with self.subTest(observations=observations):
                with self.assertRaises(ToolError) as error:
                    self.web.import_evidence(self.data, {"data_version": "shape-new-v1", "observations": observations})
                self.assertEqual(error.exception.code, "invalid_input")
        self.assertFalse((self.workspace / "runtime-data/catalogs/shape-new-v1").exists())

    def test_isolated_cli_returns_json_exit_one_for_malformed_arrays_and_entries(self):
        shutil.copytree(ROOT / "product-tools", self.workspace / "product-tools", ignore=shutil.ignore_patterns("__pycache__"))
        command = [sys.executable, str(self.workspace / "product-tools/cli.py"), "--data", str(self.data.root),
                   "--db", str(self.workspace / "runtime-data/cli-shape.sqlite"), "import_web_evidence"]
        for observations in ("invalid", {"source_id": "not-an-array"}, ["invalid"], [None], [{}]):
            with self.subTest(observations=observations):
                process = subprocess.run(command, input=canonical({"data_version": "shape-new-v1", "observations": observations}),
                    cwd=self.workspace, capture_output=True, text=True, encoding="utf-8", timeout=10)
                self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
                self.assertNotIn("Traceback", process.stderr)
                response = strict_json(process.stdout)
                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_input")
                self.assertIsNotNone(response["failure_receipt"])
        self.assertFalse((self.workspace / "runtime-data/catalogs/shape-new-v1").exists())


if __name__ == "__main__":
    unittest.main()
