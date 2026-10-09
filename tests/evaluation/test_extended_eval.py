"""Resume and declared real-process fault boundaries; no model inference."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"evals/runner"))
import extended_eval as ex


class ExtendedTests(unittest.TestCase):
    def test_resume_unknown_or_different_identity_never_recounts_first_turn(self):
        current={k:100 for k in ex.ev.FIELDS}
        self.assertEqual(ex.turn_usage(current,None,0,True),current)
        self.assertEqual(ex.turn_usage(current,None,1,True),{k:None for k in current})
        self.assertEqual(ex.turn_usage(current,{k:80 for k in current},1,True),{k:20 for k in current})
        self.assertEqual(ex.turn_usage(current,{k:80 for k in current},1,False),{k:None for k in current})
        self.assertIsNone(ex.count_delta({"one":2},None))
        self.assertIsNone(ex.count_delta({"one":1},{"one":2}))
        self.assertEqual(ex.count_delta({"one":3,"two":1},{"one":2}),{"one":1,"two":1})

    def test_baseline_followup_has_no_product_handle_instructions_or_rubric(self):
        case={"turns":["first","follow"],"expected":["LEAK_SENTINEL"],"constraints":{}}
        prompt=ex.prompt_for(case,"baseline",{},1)
        self.assertNotIn("prior_turn_id",prompt)
        self.assertNotIn("LEAK_SENTINEL",prompt)
        self.assertIn("같은 native 대화",prompt)
        self.assertIn("서브에이전트를 만들거나 작업을 위임하지 말 것",prompt)
        self.assertIn("prior_turn_id",ex.prompt_for(case,"after",{},1))

    def test_resume_command_is_explicit_uuid_and_stdin_no_last_or_ephemeral(self):
        command=ex.command_for("codex",Path("product"),Path("final"),"observed-uuid")
        self.assertEqual(command[-2:],["observed-uuid","-"])
        self.assertLess(command.index("-C"),command.index("resume"))
        self.assertLess(command.index("--sandbox"),command.index("resume"))
        self.assertIn("multi_agent",command)
        self.assertNotIn("--last",command)
        self.assertNotIn("--ephemeral",command)

    def test_candidate_identity_ignores_mutable_join_metadata_but_keeps_keys(self):
        candidate={"turn_id":"turn","candidate_version":1,"result_key":"key","result":{"status":"held"},"validation":{},"status":"held","turn_result_version":1}
        changed={**candidate,"status":"failed","turn_result_version":2}
        self.assertEqual(ex.candidate_fingerprints([candidate]),ex.candidate_fingerprints([changed]))
        self.assertNotEqual(ex.candidate_fingerprints([candidate]),ex.candidate_fingerprints([{**changed,"result_key":"other"}]))

    def test_actual_wrapper_fault_once_and_declared_integrity_only(self):
        with tempfile.TemporaryDirectory(prefix="lg-extended-fault-test-") as tmp:
            target=Path(tmp)/"product"
            ex.ev.load_installer(ROOT).install(target)
            injection=ex.inject(target,"tool_fault")
            wrapper=target/".agents/skills/evidence-retrieval/scripts/run.py"
            command=[sys.executable,str(wrapper),"open_request_bundle"]
            payload=json.dumps({"question":"test only","model_id":"B502S33","user_submitted":True})
            first=subprocess.run(command,cwd=target,input=payload,text=True,encoding="utf-8",capture_output=True,timeout=15)
            self.assertEqual(first.returncode,1)
            self.assertEqual(json.loads(first.stdout)["error"]["code"],"temporary_unavailable")
            second=subprocess.run(command,cwd=target,input=payload,text=True,encoding="utf-8",capture_output=True,timeout=15)
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertTrue(json.loads(second.stdout)["ok"])
            self.assertEqual(len(ex.inspect_history(target)["turns"]),1)
            self.assertFalse(ex.installed_integrity(ROOT,target,injection)["errors"])
            wrapper.write_text("unexpected tamper",encoding="utf-8")
            self.assertTrue(ex.installed_integrity(ROOT,target,injection)["errors"])

    def test_attack_note_is_separate_test_only_and_leaves_business_catalog_intact(self):
        with tempfile.TemporaryDirectory(prefix="lg-extended-note-test-") as tmp:
            target=Path(tmp)/"product"
            ex.ev.load_installer(ROOT).install(target)
            before=ex.ev.sha(target/"data/business/lg-research-v3/sources.jsonl")
            injection=ex.inject(target,"source_attack")
            self.assertFalse(injection["business_evidence"])
            self.assertEqual(before,ex.ev.sha(target/"data/business/lg-research-v3/sources.jsonl"))
            self.assertIn("TEST_ONLY",(target/injection["path"]).read_text(encoding="utf-8"))
            self.assertFalse(ex.installed_integrity(ROOT,target,injection)["errors"])


if __name__=="__main__":
    unittest.main()
