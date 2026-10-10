"""Synthetic timer/evidence contract tests; not real human or billing evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/measurement"))
from measurement import Store, atomic_create, billing_report, compare, prepare, report, timing, union_seconds, usage_report


def meta(condition="manual"):
    return {"participant": "member-a", "case_id": "S05-R01", "condition": condition,
            "data_version": "v3", "product_model": "B502S33",
            **{k: "a" * 64 for k in ("data_fingerprint", "case_file_sha256", "input_sha256", "completion_sha256", "product_sha256")},
            "model_and_settings": None if condition == "manual" else {"model": "test-model", "cli": "test", "cli_version": "1", "reasoning": "standard"},
            "learning_order": ["manual", "general_ai", "harness"], "attempt_index": 1}


def event(kind, n=0, clock="boot-a", **kwargs):
    return {"data": {"kind": kind, **kwargs}, "sample": {"utc": "2026-10-10T00:00:00+00:00", "clock_id": clock, "monotonic_ns": n * 1_000_000_000}}


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "private")
        self.store.create("one", meta(), True)

    def append(self, data, n=0, clock="boot-a", eid=None):
        return self.store.append("one", data, eid, True, {"utc": "2026-10-10T00:00:00+00:00", "clock_id": clock, "monotonic_ns": n * 1_000_000_000})

    def test_real_human_confirmation_is_required(self):
        with self.assertRaisesRegex(ValueError, "real participant"):
            self.store.append("one", {"kind": "start", "participant": "member-a", "phase": "read"})
        with self.assertRaises(ValueError):
            self.store.create("two", meta())

    def test_private_metadata_and_float_charges_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "private"):
            self.store.create("private", {**meta(), "email": "person@example.com"}, True)
        private = meta("harness")
        private["model_and_settings"]["model"] = "person@example.com"
        with self.assertRaises(ValueError):
            self.store.create("private-model", private, True)
        for amount in (0.1, "not-a-number"):
            with self.assertRaises(ValueError):
                self.append({"kind": "billing", "transaction_id": "a", "unit": "USD", "amount": amount, "attribution": "unverified"})

    def test_overlap_union_per_actor_and_zero(self):
        self.assertEqual(union_seconds([("a", "c", 0, 5_000_000_000), ("a", "c", 2_000_000_000, 8_000_000_000), ("b", "c", 0, 5_000_000_000)]), 13)
        self.assertEqual(union_seconds([]), 0)
        self.assertIsNone(union_seconds([("a", None, 0, 1)]))
        self.assertIsNone(union_seconds([("a", "c", 10, 1)]))

    def test_switch_pause_finish_distinguish_setup_wait(self):
        for kind, n, extra in [("start", 0, {"phase": "setup"}), ("start", 3, {"phase": "read"}),
                               ("start", 8, {"phase": "wait"}), ("start", 12, {"phase": "evidence"}),
                               ("pause", 15, {}), ("finish", 20, {"outcome": "completed", "result_sha256": "b" * 64, "additional_inputs": 0, "revisions": 0})]:
            self.append({"kind": kind, "participant": "member-a", **extra}, n)
        value = report(self.store, "one")
        self.assertEqual(value["timing"]["human_active_seconds"], 8)
        self.assertEqual(value["timing"]["setup_seconds"], 3)
        self.assertEqual(value["timing"]["wait_seconds"], 4)
        self.assertEqual(value["timing"]["wall_seconds"], 17)
        self.assertEqual(value["quality"]["verdict"], "pending")

    def test_open_clock_reset_and_reverse_are_unknown(self):
        start = event("start", 10, participant="member-a", phase="read")
        self.assertIsNone(timing([start])["human_active_seconds"])
        for ending in [event("finish", 20, clock="new", outcome="failed"), event("finish", 5, outcome="failed")]:
            result = timing([start, ending])
            self.assertIsNone(result["human_active_seconds"])
            self.assertIsNone(result["wall_seconds"])

    def test_immutable_duplicate_replay_and_conflict_preserved(self):
        data = {"kind": "start", "participant": "member-a", "phase": "read"}
        first = self.append(data, 1, eid="event-one")
        self.assertEqual(self.append(data, 9, eid="event-one"), first)
        with self.assertRaisesRegex(ValueError, "preserved"):
            self.append({**data, "phase": "edit"}, 9, eid="event-one")
        self.assertEqual(len(self.store.load("one")[1]), 1)
        self.assertEqual(report(self.store, "one")["conflict_attempts"], 1)
        with self.assertRaises(FileExistsError):
            atomic_create(self.store.path("one") / "metadata.json", {"overwritten": True})

    def test_tamper_chain_and_concurrent_writer_fail(self):
        self.append({"kind": "start", "participant": "member-a", "phase": "read"}, 1)
        lock = self.store.path("one") / ".write-lock"
        lock.mkdir()
        with self.assertRaises(FileExistsError):
            self.append({"kind": "pause", "participant": "member-a"}, 2)
        lock.rmdir()
        path = next((self.store.path("one") / "events").glob("*.json"))
        path.write_text(path.read_text(encoding="utf-8").replace('"read"', '"edit"'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "chain"):
            self.store.load("one")

    def test_finished_no_more_activity_and_result_required(self):
        with self.assertRaisesRegex(ValueError, "artifact"):
            self.append({"kind": "finish", "participant": "member-a", "outcome": "held"})
        self.append({"kind": "finish", "participant": "member-a", "outcome": "failed"}, 1)
        with self.assertRaisesRegex(ValueError, "finished"):
            self.append({"kind": "start", "participant": "member-a", "phase": "edit"}, 2)

    def test_billing_decimal_refund_duplicates_units_no_attribution(self):
        charge = {"transaction_id": "invoice-a", "unit": "USD", "amount": "0.10", "attribution": "verified"}
        billing = [event("billing", **charge), event("billing", **charge),
                   event("billing", transaction_id="invoice-refund", unit="USD", amount="-0.03", attribution="verified", refund_of="invoice-a"),
                   event("billing", transaction_id="window", unit="CREDIT:CODEX", amount="20", attribution="window_only")]
        result = billing_report(billing)
        self.assertEqual(result["units"]["USD"]["verified_attributed_amount"], "0.07")
        self.assertIsNone(result["units"]["CREDIT:CODEX"]["verified_attributed_amount"])
        self.assertEqual(result["duplicate_records_ignored"], 1)
        self.assertIsNone(result["actual_total_cost"])

    def test_billing_conflict_and_missing_not_zero(self):
        base = {"transaction_id": "a", "unit": "KRW", "amount": "0", "attribution": "verified"}
        self.assertEqual(billing_report([event("billing", **base)])["units"]["KRW"]["verified_attributed_amount"], "0")
        for other in [{**base, "amount": "1"}, {**base, "transaction_id": "b", "amount": None}]:
            self.assertIsNone(billing_report([event("billing", **base), event("billing", **other)])["units"]["KRW"]["verified_attributed_amount"])
        with self.assertRaisesRegex(ValueError, "concurrent"):
            self.append({"kind": "billing", **base, "evidence_sha256": "a" * 64, "concurrent_other_usage": True})

    def test_usage_latest_cumulative_no_double_count_unknown(self):
        base = {"source": "native", "scope_id": "anonymous-session", "coverage": "partial", "input_tokens": 10,
                "cached_input_tokens": 4, "output_tokens": 0, "reasoning_output_tokens": None, "snapshot_index": 1}
        result = usage_report([event("usage", **base), event("usage", **base), event("usage", **{**base, "input_tokens": 20, "snapshot_index": 2})])
        self.assertEqual(result["scopes"][0]["values"]["input_tokens"], 20)
        self.assertEqual(result["scopes"][0]["values"]["noncached_input_tokens"], 16)
        self.assertEqual(result["scopes"][0]["values"]["output_tokens"], 0)
        self.assertIsNone(result["scopes"][0]["values"]["reasoning_output_tokens"])
        self.assertIsNone(result["combined_total"])

    def test_usage_conflict_or_reverse_invalidates_scope(self):
        base = {"source": "native", "scope_id": "s", "coverage": "partial", "input_tokens": 10, "snapshot_index": 1}
        for other in [{**base, "input_tokens": 11}, {**base, "input_tokens": 9, "snapshot_index": 2}]:
            value = usage_report([event("usage", **base), event("usage", **other)])["scopes"][0]
            self.assertTrue(value["conflict_or_reverse"])
            self.assertIsNone(value["values"]["input_tokens"])

    def test_quality_missing_counts_and_mismatch_gate_reduction(self):
        value = report(self.store, "one")
        self.assertIsNone(compare(value, value)["human_active_reduction_percent"])
        baseline = {**value, "outcome": "completed", "additional_inputs": 0, "revisions": 0, "quality": {"verdict": "equivalent"},
                    "timing": {"human_active_seconds": 20, "wall_seconds": 25}, "conflict_attempts": 0}
        candidate = copy.deepcopy(baseline)
        candidate["metadata"]["condition"] = "harness"
        candidate["metadata"]["model_and_settings"] = {"model": "test"}
        candidate["timing"]["human_active_seconds"] = 10
        self.assertEqual(compare(baseline, candidate)["human_active_reduction_percent"], 50)
        candidate["metadata"]["data_fingerprint"] = "b" * 64
        self.assertIsNone(compare(baseline, candidate)["human_active_reduction_percent"])

    def test_prepare_exact_case_actual_fingerprints_no_expected_answers(self):
        path = Path(self.temp.name) / "kit"
        metadata = prepare(path, "member-a", "manual", ["manual", "general_ai", "harness"])
        task = json.loads((path / "task.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["case_id"], "S05-R01")
        self.assertEqual(task["product_model"], "B502S33")
        self.assertEqual(task["constraints"]["max_concepts"], 2)
        self.assertTrue(task["sources"])
        self.assertNotIn("expected", task)
        self.assertNotIn("rubric", task)

    def test_cli_requires_confirmation_and_reports_json_error(self):
        result = subprocess.run([sys.executable, str(ROOT / "evals/measurement/cli.py"), "--root", str(self.store.root), "start", "--run", "one", "--participant", "member-a", "--phase", "read"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["status"], "error")


if __name__ == "__main__":
    unittest.main()
