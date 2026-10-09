"""Development evaluator boundaries; stubs do not represent real model quality."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("native_eval", ROOT / "evals/runner/native_eval.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)
sys.path.insert(0, str(ROOT / "evals/runner"))
import audit_report


class EvaluationTests(unittest.TestCase):
    def test_cumulative_delta_and_unknown_are_not_summed(self):
        first = {k: 100 for k in ev.FIELDS}
        second = {k: 140 for k in ev.FIELDS}
        self.assertEqual(ev.usage_delta(second, first), {k: 40 for k in ev.FIELDS})
        self.assertEqual(ev.usage_delta(first, second), {k: None for k in ev.FIELDS})
        totals = ev.usage_totals([ev.usage_delta(first), ev.usage_delta(second, first), ev.usage_delta(None)])
        self.assertEqual(totals["input_tokens"], {"known_sum": 140, "unknown_runs": 1})
        self.assertIsNone(ev.usage_totals([ev.usage_delta(None)])["input_tokens"]["known_sum"])

    def test_postprocessing_failure_preserves_observed_execution_and_usage(self):
        observed = {"native_id":"real-observed-id", "status":"succeeded", "exit_code":0, "usage":{k:13 for k in ev.FIELDS}}
        failed = ev.retained_failure(observed, ValueError("test-only parse failure"))
        self.assertEqual(failed["status"], "runner_failed")
        self.assertEqual(failed["execution_status"], "succeeded")
        self.assertEqual(failed["native_id"], observed["native_id"])
        self.assertEqual(failed["usage"], observed["usage"])
        self.assertEqual(failed["exit_code"], 0)

    def test_native_rollout_failure_preserves_actual_process_and_cli_usage(self):
        code='import sys,json;sys.stdin.read();print(json.dumps({"type":"thread.started","thread_id":"observed-stub"}));print(json.dumps({"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":3}}))'
        with tempfile.TemporaryDirectory(prefix="lg-native-observation-test-") as tmp, patch.object(ev,"rollout_observation",side_effect=OSError("fixture log unavailable")):
            result=ev.execute([sys.executable,"-c",code],Path(tmp),"test only",Path(tmp)/"actual",5)
            self.assertEqual(result["status"],"succeeded")
            self.assertEqual(result["exit_code"],0)
            self.assertIsInstance(result["process_id"],int)
            self.assertEqual(result["native_id"],"observed-stub")
            self.assertEqual(result["usage"]["input_tokens"],12)
            self.assertEqual(result["usage"]["output_tokens"],3)
            self.assertTrue(result["observation_errors"])
            self.assertIsNone(result["rollout"]["metadata"])

    def test_audit_retains_failed_postprocessing_and_does_not_require_missing_fields(self):
        with tempfile.TemporaryDirectory(prefix="lg-eval-audit-") as tmp:
            report = Path(tmp)
            source = report / "source-after"
            source.mkdir()
            (source / "one.txt").write_text("test-only source", encoding="utf-8")
            directory = report / "one"
            directory.mkdir()
            trace = directory / "native.jsonl"
            trace.write_text(json.dumps({"type":"thread.started","thread_id":"observed-stub"})+'\n',encoding="utf-8")
            job = {"name":"one","arm":"baseline","case":{"id":"test"},"workspace":str(report / "empty"),"sources_sha256":"test-only-bundle"}
            audit_report.ev.dump(report / "prepared.json", {"jobs":[job],"source_after":{"one.txt":ev.sha(source / "one.txt")}})
            observation = ev.retained_failure({"status":"succeeded","native_id":"observed-stub","stdout_sha256":ev.sha(trace),"usage":{k:13 for k in ev.FIELDS}}, ValueError("fixture failure"))
            observation.update(case_id="test",arm="baseline")
            audit_report.ev.dump(report / "results.json", {"results":[observation],"config_matched":True})
            result = audit_report.audit(report)
            self.assertEqual(result["runner_failures"],1)
            self.assertEqual(result["executions_succeeded"],1)
            self.assertEqual(result["session_reported_usage_totals"]["input_tokens"]["known_sum"],13)
            row=result["observations"][0]
            self.assertFalse(row["contract_valid"])
            self.assertEqual(row["contract_error"],"postprocessing_incomplete")
            self.assertIsNone(row["exit_code"])
            self.assertIsNone(row["native_spawn_calls"])

    def test_baseline_gets_all_sources_and_no_rubric(self):
        data = ev.Dataset(ROOT / "data/business/lg-research-v3")
        case = json.loads((ROOT / "evals/judge/s05-cases.json").read_text(encoding="utf-8"))["cases"][0]
        bundle = ev.exact_sources(data, case["model_id"])
        prompt = ev.build_prompt(case, "baseline", bundle)
        for record in bundle["evidence_refs"]:
            self.assertIn(record["quote"], prompt)
            self.assertIn(record["sha256"], prompt)
        for key in ("expected", "forbidden", "source_ids"):
            case[key] = ["RUBRIC_SENTINEL"]
        self.assertNotIn("RUBRIC_SENTINEL", ev.build_prompt(case, "baseline", bundle))
        self.assertIn(ev.OUTPUT_CONTRACT, ev.build_prompt(case, "after", bundle))
        self.assertIn("assumptions와 validation_findings는 문자열 배열", prompt)
        self.assertIn("비어있지 않은 중복 없는 배열", prompt)

    def test_parser_uses_only_last_cumulative_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "trace"
            p.write_text('\n'.join(json.dumps(i) for i in [{"type":"thread.started","thread_id":"native"},{"type":"turn.completed","usage":{"input_tokens":10}},{"type":"turn.completed","usage":{"input_tokens":15}}]), encoding="utf-8")
            self.assertEqual(ev.parse_cli(p)["cumulative_usage"]["input_tokens"], 15)

    def test_failed_and_timeout_child_remain_failed_unknown_usage(self):
        with tempfile.TemporaryDirectory(prefix="lg-evaluation-test-") as tmp, patch.object(ev, "rollout_observation", return_value={"metadata": None, "cumulative_usage": None}):
            base = Path(tmp)
            failed = ev.execute([sys.executable,"-c","import sys;sys.stdin.read();sys.exit(3)"], base, "test only", base / "failed", 2)
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["exit_code"], 3)
            self.assertIsNone(failed["usage"]["input_tokens"])
            timed = ev.execute([sys.executable,"-c","import sys,time;sys.stdin.read();time.sleep(20)"], base, "test only", base / "timeout", 1)
            self.assertEqual(timed["status"], "timeout")
            self.assertTrue(timed["termination"]["needed"])
            self.assertIsNotNone(timed["termination"]["process_exit"])

    def test_final_json_parse_does_not_accept_partial_key_set(self):
        self.assertIsNone(ev.parse_answer('{"status":"completed"}'))
        self.assertEqual(ev.parse_answer('説明\n```json\n{"result":{},"assessment":{}}\n```'), {"result": {}, "assessment": {}})

    def test_baseline_web_tool_or_unknown_inventory_is_not_clean(self):
        self.assertIsNone(ev.baseline_clean({"rollout": {"metadata":None}}))
        self.assertFalse(ev.baseline_clean({"tool_items":{"web_search":1},"rollout":{"metadata":{"model":"test"}}}))
        self.assertFalse(ev.baseline_clean({"rollout":{"metadata":{"model":"test"},"builtin_tool_calls":{"web_search_call":1}}}))
        self.assertTrue(ev.baseline_clean({"tool_items":{},"rollout":{"metadata":{"model":"test"},"function_calls":{},"builtin_tool_calls":{}}}))

    def test_frozen_product_installs_no_eval_or_development_skills(self):
        with tempfile.TemporaryDirectory(prefix="lg-evaluation-frozen-") as tmp:
            base = Path(tmp)
            frozen = base / "source"
            hashes = ev.freeze(ROOT, frozen)
            self.assertFalse(any(p.startswith(("evals/", ".codex/", ".claude/")) for p in hashes))
            target = base / "product"
            ev.load_installer(frozen).install(target, root=frozen)
            self.assertEqual(len(list((target / ".agents/skills").glob("*/SKILL.md"))), 6)
            self.assertFalse((target / "evals").exists())


if __name__ == "__main__":
    unittest.main()
