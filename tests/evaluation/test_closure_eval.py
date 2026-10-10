"""Closing diagnostic budget and dependency guards; not AI quality tests."""
import sys
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/runner"))
import closure_eval


class ClosingBudgetTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"limits": dict(closure_eval.LIMITS), "jobs": [{"name": s[0]} for s in closure_eval.SPECS]}

    def test_no_retries_unknown_or_extra_input(self):
        for names, started in (([], set()), (["preference", "preference"], set()),
            (["unknown"], set()), (["preference"], {"preference"}),
            (["preference", "expectation", "product-1"], set()),
            (["product-1", "followup"], set()), (["expectation", "followup"], {"product-1"})):
            with self.assertRaises(ValueError):
                closure_eval.select_jobs(self.plan, names, started)
        self.assertEqual(closure_eval.select_jobs(self.plan, ["followup"], {"product-1"})[0]["name"], "followup")

    def test_budget_or_prepared_count_drift_rejected(self):
        self.plan["limits"]["native_cap"] = 5
        with self.assertRaises(ValueError):
            closure_eval.select_jobs(self.plan, ["preference"], set())
        self.plan["limits"] = dict(closure_eval.LIMITS)
        self.plan["jobs"].append({"name": "extra"})
        with self.assertRaises(ValueError):
            closure_eval.select_jobs(self.plan, ["preference"], set())
