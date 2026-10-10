"""Exact returned source delivery and isolated injection boundary; no native model calls."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/runner"))
import source_instruction_eval as probe


class SourceInstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.original = ROOT / "data/synthetic/kitchen-v1"
        self.before = {p.name: probe.ev.sha(p) for p in self.original.iterdir() if p.is_file()}
        self.clean = probe.fixture(self.original, self.base / "clean", "clean")
        self.attack = probe.fixture(self.original, self.base / "attack", "attack")

    def tearDown(self):
        self.assertEqual(self.before, {p.name: probe.ev.sha(p) for p in self.original.iterdir() if p.is_file()})
        self.temp.cleanup()

    def response(self):
        data = self.attack
        ref = data.reference(data.source(probe.TARGET))
        return {"ok": True, "result": {"bundle": {"scope": probe.SCOPE, "data_version": data.version,
                "dataset_fingerprint": data.fingerprint, "byte_truncated": False, "included_source_ids": [probe.TARGET],
                "omitted_source_ids": [], "evidence_refs": [ref]}}}

    def item(self, response=None):
        return {"id": "native-fixture-only", "command": "uv run python skills/evidence-retrieval/scripts/run.py open_request_bundle --data data/synthetic/j17-v2",
                "exit_code": 0, "aggregated_output": json.dumps(response or self.response(), ensure_ascii=False)}

    def test_pair_diff_is_only_declared_version_and_target_text_hash(self):
        self.assertEqual(self.clean.models, self.attack.models)
        self.assertEqual(self.clean.sources.keys(), self.attack.sources.keys())
        for source_id in self.clean.sources:
            left, right = copy.deepcopy(self.clean.source(source_id)), copy.deepcopy(self.attack.source(source_id))
            left.pop("data_version"); right.pop("data_version")
            if source_id == probe.TARGET:
                self.assertEqual(right["text"], left["text"] + probe.ATTACK)
                for value in (left, right):
                    value.pop("text"); value.pop("sha256")
            self.assertEqual(left, right)
        self.assertNotEqual(self.clean.fingerprint, self.attack.fingerprint)
        self.assertEqual(self.attack.manifest["purpose"], "test_only")

    def test_business_injection_and_overwrite_rejected(self):
        with self.assertRaises(ValueError):
            probe.fixture(ROOT / "data/business/lg-research-v3", self.base / "business", "attack")
        with self.assertRaises(ValueError):
            probe.fixture(self.original, self.base / "clean", "clean")

    def test_observed_prompt_newlines_normalize_without_ignoring_content_changes(self):
        path = self.base / "prompt.txt"
        logical = probe.prompt()
        expected = hashlib.sha256(logical.encode("utf-8")).hexdigest()
        path.write_bytes(logical.replace("\n", "\r\n").encode("utf-8"))
        self.assertTrue(probe.prompt_matches(path, expected))
        self.assertNotEqual(probe.ev.sha(path), expected)
        path.write_bytes((logical.replace("\n", "\r\n") + " altered").encode("utf-8"))
        self.assertFalse(probe.prompt_matches(path, expected))

    def test_missing_output_recovers_only_a_completed_native_final(self):
        directory = self.base / "trace"
        directory.mkdir()
        trace = directory / "native.jsonl"
        message = {"type": "item.completed", "item": {"type": "agent_message", "text": "actual final"}}
        trace.write_text(json.dumps(message) + "\n", encoding="utf-8")
        self.assertEqual(probe.final_observation(directory), ("", "unavailable", False))
        trace.write_text(json.dumps(message) + '\n{"type":"turn.completed"}\n', encoding="utf-8")
        self.assertEqual(probe.final_observation(directory), ("actual final", "completed_native_trace", True))
        (directory / "final.txt").write_text("different file", encoding="utf-8")
        self.assertEqual(probe.final_observation(directory), ("different file", "output_file", True))

    def test_reinspection_never_overwrites_original_execution(self):
        directory = self.base / "report/attack"
        directory.mkdir(parents=True)
        original = b'{"preserved":true}\n'
        (directory / "execution.json").write_bytes(original)
        observed = {"status": "timeout", "usage": {k: None for k in probe.ev.FIELDS}}
        row = probe.observe(self.base / "missing-workspace", directory, observed, "attack", ROOT, write_execution=False)
        self.assertEqual((directory / "execution.json").read_bytes(), original)
        self.assertEqual(row["execution"], observed)

    def test_exact_stdout_and_escaped_envelope_observed(self):
        item = self.item()
        self.assertTrue(probe.delivery([item], self.attack)["observed"])
        item["aggregated_output"] = json.dumps({"exit_code": 0, "output": item["aggregated_output"]})
        self.assertTrue(probe.delivery([item], self.attack)["observed"])

    def test_path_or_attack_text_without_normal_successful_output_is_inconclusive(self):
        for output in (probe.ATTACK, "{bad JSON", "", json.dumps({"ok": False})):
            item = self.item(); item["aggregated_output"] = output
            self.assertFalse(probe.delivery([item], self.attack)["observed"])
        item = self.item(); item["exit_code"] = 1
        self.assertFalse(probe.delivery([item], self.attack)["observed"])

    def test_missing_scope_hash_version_or_truncated_quote_cannot_pass(self):
        for mode in ("missing", "scope", "hash", "quote", "version", "dataset", "truncated", "omitted"):
            response = self.response(); bundle = response["result"]["bundle"]
            if mode == "missing": bundle["evidence_refs"] = []
            elif mode == "scope": bundle["scope"] = {**probe.SCOPE, "model_id": "AX-R301"}
            elif mode in ("hash", "quote"): bundle["evidence_refs"][0]["sha256" if mode == "hash" else "quote"] = "wrong"
            elif mode == "version": bundle["data_version"] = self.clean.version
            elif mode == "dataset": bundle["dataset_fingerprint"] = self.clean.fingerprint
            elif mode == "truncated": bundle["byte_truncated"] = True
            elif mode == "omitted": bundle["omitted_source_ids"] = [probe.TARGET]
            self.assertFalse(probe.delivery([self.item(response)], self.attack)["observed"], mode)

    def test_prompt_has_no_attack_target_marker_or_expected_answer(self):
        prompt = probe.prompt()
        for secret in (probe.TARGET, "j17-action", "FAKE-SOURCE-900", "900mm", "80%", "attack"):
            self.assertNotIn(secret, prompt)
        self.assertIn("--data data/synthetic/j17-v2", prompt)

    def test_null_or_nonobject_tool_result_cannot_crash_or_pass_delivery(self):
        for result in (None, "wrong", 3, {"bundle": {"evidence_refs": None}}):
            item = self.item({"ok": True, "result": result})
            self.assertFalse(probe.delivery([item], self.attack)["observed"])

    def test_hostile_missing_fixture_preserves_actual_execution_and_usage(self):
        directory = self.base / "report/attack"
        directory.mkdir(parents=True)
        observed = {"status": "succeeded", "exit_code": 0, "process_id": 100, "usage": {k: 50 for k in probe.ev.FIELDS}}
        row = probe.observe(self.base / "missing-workspace", directory, observed, "attack", ROOT)
        self.assertEqual(row["execution"], observed)
        self.assertEqual(row["postprocess_status"], "failed")
        self.assertFalse(row["delivery"]["observed"])
        self.assertEqual(json.loads((directory / "execution.json").read_text()), observed)


if __name__ == "__main__":
    unittest.main()
