"""Evidence omissions must not become successful native evaluation audits."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"evals/runner"))
import followup_report as report


class FollowupAuditTests(unittest.TestCase):
    def fixture(self,root):
        source=root/"source-after"
        source.mkdir()
        (source/"one.txt").write_text("test only frozen source",encoding="utf-8")
        directory=root/"job"/"turn-0"
        directory.mkdir(parents=True)
        trace=directory/"native.jsonl"
        trace.write_text(json.dumps({"type":"thread.started","thread_id":"observed-fixture"})+"\n",encoding="utf-8")
        planned={"name":"job","case":{"id":"fixture"},"arm":"baseline","mode":"normal","prompts":["question"],"sources_sha256":"fixture-source","injection":{}}
        observation={"turn_index":0,"process_id":123,"native_id":"observed-fixture","stdout_sha256":report.ev.sha(trace),"status":"failed",
                     "exit_code":3,"usage":{k:None for k in report.ev.FIELDS},"source_bundle_sha256":"fixture-source"}
        job={"name":"job","case_id":"fixture","arm":"baseline","mode":"normal","workspace":str(root/"workspace"),"observations":[observation],"not_executed_turns":0}
        report.ev.dump(root/"prepared.json",{"jobs":[planned],"source_after":{"one.txt":report.ev.sha(source/"one.txt")}})
        result={"jobs":[job],"actual_invocations":1}
        report.ev.dump(root/"results.json",result)
        return result

    def test_actual_failed_observation_is_preserved_without_quality_or_usage_claim(self):
        with tempfile.TemporaryDirectory(prefix="lg-followup-audit-") as tmp:
            root=Path(tmp)
            self.fixture(root)
            value=report.audit_extension(root)
            self.assertEqual(value["observations"][0]["status"],"failed")
            self.assertFalse(value["observations"][0]["contract_valid"])
            self.assertIsNone(value["reported_usage_totals"]["input_tokens"]["known_sum"])
            self.assertFalse(value["cost_savings_proven"])
            self.assertIsNone(value["observations"][0]["single_agent_observed"])

    def test_missing_execution_and_inconsistent_invocation_or_turn_evidence_fail(self):
        for change in ("missing","count","turn","source"):
            with self.subTest(change=change),tempfile.TemporaryDirectory(prefix="lg-followup-omission-") as tmp:
                root=Path(tmp)
                result=self.fixture(root)
                if change=="missing":
                    result["jobs"][0].update(observations=[],not_executed_turns=1)
                    result["actual_invocations"]=0
                elif change=="count":
                    result["actual_invocations"]=2
                elif change=="turn":
                    result["jobs"][0]["observations"][0]["turn_index"]=1
                else:
                    result["jobs"][0]["observations"][0]["source_bundle_sha256"]="different"
                report.ev.dump(root/"results.json",result)
                with self.assertRaises(ValueError):
                    report.audit_extension(root)


if __name__=="__main__":
    unittest.main()
