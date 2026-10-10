"""Fixed-phase input budget, not model quality tests."""
import sys
import copy
import json
from unittest.mock import patch
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/runner"))
import focused_eval


class FocusedBudgetTests(unittest.TestCase):
    def test_followup_missing_parent_or_identity_never_becomes_zero_baseline(self):
        current = {"input_tokens": 1200, "cached_input_tokens": 900, "output_tokens": 100, "reasoning_output_tokens": 30}
        previous = {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 80, "reasoning_output_tokens": 20}
        for prior, native, expected in ((None, "n", "n"), (previous, "other", "n"), (previous, None, None)):
            self.assertTrue(all(v is None for v in focused_eval.followup_usage(current, prior, native, expected).values()))
        self.assertEqual(focused_eval.followup_usage(current, previous, "n", "n"),
                         {"input_tokens": 200, "cached_input_tokens": 100, "output_tokens": 20, "reasoning_output_tokens": 10})

    def test_actual_web_prompt_preserves_all_case_constraints_and_qualification(self):
        case = {"turns": ["Actual web request"], "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": ["cleaning"]}}
        prompt = focused_eval.build_web_prompt(case, "data/business/test-path")
        self.assertTrue(prompt.startswith(case["turns"][0]))
        encoded = prompt.split("\n제약은 ", 1)[1].split("\n", 1)[0]
        self.assertEqual(json.loads(encoded), case["constraints"])
        self.assertIn("data/business/test-path", prompt)
        self.assertTrue(prompt.endswith(focused_eval.QUALIFICATION))

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
