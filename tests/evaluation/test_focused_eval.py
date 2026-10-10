"""Fixed-phase input budget, not model quality tests."""
import sys
import copy
from unittest.mock import patch
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/runner"))
import focused_eval


class FocusedBudgetTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"jobs": [{"name": str(i)} for i in range(9)]}

    def test_duplicate_unknown_and_parallel_overflow_are_rejected(self):
        for names in ([], ["0", "0"], ["absent"], ["0", "1", "2"]):
            with self.assertRaises(ValueError):
                focused_eval.select_jobs(self.plan, names, set())

    def test_attempted_failures_consume_slots_and_are_never_retried(self):
        with self.assertRaises(ValueError):
            focused_eval.select_jobs(self.plan, ["0"], {"0"})
        with self.assertRaises(ValueError):
            focused_eval.select_jobs(self.plan, ["8"], {str(i) for i in range(9)})
        self.assertEqual(focused_eval.select_jobs(self.plan, ["8"], {str(i) for i in range(8)})[0]["name"], "8")

    def test_followup_uses_request_payload_and_retains_old_candidates(self):
        candidate = {"turn_id":"old","candidate_version":1,"result_key":"r1","result":{"status":"held"},"validation":{"contract_valid":True}}
        before = {"turns":[{"session_id":"s","turn_id":"old"}],"candidates":[candidate]}
        after = {"turns":before["turns"] + [{"session_id":"s","turn_id":"new","input":"{}"}],"candidates":[candidate]}
        exported = {"requests":[{"turn_id":"new","input":{"prior_turn_id":"old"}}]}
        self.assertTrue(focused_eval.followup_linked(before, after, exported, "native", "native"))
        wrong = copy.deepcopy(exported)
        wrong["requests"][0]["input"]["prior_turn_id"] = "wrong"
        self.assertFalse(focused_eval.followup_linked(before, after, wrong, "native", "native"))
        changed = copy.deepcopy(after)
        changed["candidates"][0]["result"]["status"] = "completed"
        self.assertFalse(focused_eval.followup_linked(before, changed, exported, "native", "native"))

    def test_once_policy_requires_real_injection_and_bounded_same_turn_history(self):
        candidates = [{"turn_id":"t","candidate_version":i+1,"result":{"revisions":i},"validation":{"contract_valid":i==1}} for i in range(2)]
        observations = [{"attempt":i,"mode":"once","injected":i==0,"candidate_sha256":focused_eval.fingerprint(c["result"])} for i,c in enumerate(candidates)]
        receipt = {"accepted":True,"valid":True,"current_result_version":2}
        self.assertTrue(focused_eval.once_recovery(candidates, observations, receipt, True))
        self.assertFalse(focused_eval.once_recovery(candidates, [], receipt, True))
        self.assertFalse(focused_eval.once_recovery(candidates, observations, receipt, False))
        bad = copy.deepcopy(observations)
        bad[0]["injected"] = False
        self.assertFalse(focused_eval.once_recovery(candidates, bad, receipt, True))
        changed = copy.deepcopy(candidates)
        changed[1]["turn_id"] = "other"
        self.assertFalse(focused_eval.once_recovery(changed, observations, receipt, True))

    def test_launch_exception_is_preserved_as_failed_unknown_usage(self):
        with patch.object(focused_eval.ev,"execute",side_effect=OSError("launch failed")):
            observed = focused_eval.safe_execute(["missing"], ROOT, "private question", ROOT/".harness/nonexistent-evaluation-directory")
        self.assertEqual(observed["status"],"runner_failed")
        self.assertIsNone(observed["exit_code"])
        self.assertTrue(all(v is None for v in observed["usage"].values()))
        self.assertIn("OSError",observed["exception"])

    def test_cli_usage_survives_unavailable_rollout_on_execution_error(self):
        parsed = {"native_id":"native","cumulative_usage":{"input_tokens":10,"output_tokens":4},"turn_completed":False}
        with patch.object(focused_eval.ev,"execute",side_effect=OSError("execution failed")), patch.object(Path,"exists",return_value=True), patch.object(focused_eval.ev,"parse_cli",return_value=parsed), patch.object(focused_eval.ev,"rollout_observation",side_effect=OSError("rollout missing")):
            observed = focused_eval.safe_execute(["missing"], ROOT, "private question", ROOT/".harness/mock-execution-directory")
        self.assertEqual(observed["status"],"runner_failed")
        self.assertEqual(observed["usage"]["input_tokens"],10)
        self.assertEqual(observed["usage"]["output_tokens"],4)
        self.assertIsNone(observed["usage"]["cached_input_tokens"])
        self.assertIn("rollout missing",observed["observation_error"])
