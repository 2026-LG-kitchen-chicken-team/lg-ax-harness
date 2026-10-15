"""Failure persistence through actual CLI; not an AI answer-quality certificate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.error_receipts import preserve_failure


class FailureReceiptTests(unittest.TestCase):
    def test_actual_cli_failure_preserves_distinct_existing_files_without_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            code = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv.pop(1));import cli;cli.ROOT=Path(sys.argv.pop(1));raise SystemExit(cli.main())"
            command = [sys.executable, "-c", code, str(ROOT / "product-tools"), str(workspace),
                       "--data", str(ROOT / "data/business/empty"), "list_models"]
            responses = []
            for value in ({"private_marker": "never-store-this-input"}, {"wrong_other_field": 8}):
                completed = subprocess.run(command, input=json.dumps(value), capture_output=True, text=True, encoding="utf8")
                self.assertEqual(completed.returncode, 1)
                output = json.loads(completed.stdout)
                self.assertFalse(output["ok"])
                receipt = output["failure_receipt"]
                self.assertTrue(receipt["ready"])
                path = workspace / receipt["path"]
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt["sha256"])
                self.assertNotIn(b"never-store-this-input", raw)
                self.assertEqual(json.loads(raw)["error"], output["error"])
                self.assertEqual(json.loads(raw)["operation"], "list_models")
                self.assertEqual(json.loads(raw)["input_sha256"], hashlib.sha256(json.dumps(value).encode()).hexdigest())
                responses.append((path, raw))
            self.assertNotEqual(responses[0][0], responses[1][0])
            self.assertEqual(responses[0][0].read_bytes(), responses[0][1])
            self.assertEqual(responses[1][0].read_bytes(), responses[1][1])

    def test_unwritable_journal_keeps_original_error_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            error = {"code": "network_error", "message": "Actual failure", "retryable": False}
            with patch.object(Path, "mkdir", side_effect=OSError("blocked")):
                receipt = preserve_failure(Path(temporary), "fetch_web_page", error)
            self.assertFalse(receipt["ready"])
            self.assertIsNone(receipt["path"])
            self.assertEqual(error["code"], "network_error")

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            error = {"code": "scope_mismatch", "message": "Wrong model", "retryable": False}
            with patch.object(Path, "open", side_effect=FileExistsError("existing")):
                receipt = preserve_failure(Path(temporary), "import_web_evidence", error)
            self.assertFalse(receipt["ready"])
            self.assertIsNone(receipt["path"])

    def test_long_error_is_marked_and_original_message_digest_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            message = "범위오류 " * 800
            error = {"code": "tool_error", "message": message, "retryable": False}
            receipt = preserve_failure(Path(temporary), "import_web_evidence", error)
            self.assertTrue(receipt["ready"])
            value = json.loads((Path(temporary)/receipt["path"]).read_bytes())
            self.assertTrue(value["error_message"]["truncated"])
            self.assertEqual(value["error_message"]["original_chars"], len(message))
            self.assertEqual(value["error_message"]["original_utf8_sha256"], hashlib.sha256(message.encode("utf8")).hexdigest())
            self.assertEqual(error["message"], message)
            self.assertIn("not original file bytes", value["input_sha256_scope"])


if __name__ == "__main__":
    unittest.main()
