"""Native delivery cannot be replaced with a saved candidate or stale receipt."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "evals/runner"))
import receipt_eval as probe
from product_tools.state import StateStore
from product_tools.conversation import Conversation


class ReceiptDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-delivery-")
        self.workspace = Path(self.temp.name)
        for name in ("skills/manifest.json","agents/product-planning.md"):
            path = self.workspace / name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes((ROOT / name).read_bytes())
        self.data = probe.ev.Dataset(ROOT / "data/business/lg-research-v3")
        for source in (ROOT / "product-tools/product_tools").glob("*.py"):
            target = self.workspace / "product-tools/product_tools" / source.name
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(source.read_bytes())
        self.store = StateStore(self.workspace / "runtime-data/product.sqlite",self.data)
        self.conv = Conversation(self.store,self.workspace)
        self.case = {"model_id":"B502S33","turns":["실제 새 질문"],"constraints":{"max_concepts":1,"hardware_allowed":False,"exclude_pains":[]}}
        self.turn = self.conv.open_request({"question":self.case["turns"][0],"model_id":"B502S33","constraints":self.case["constraints"],"user_submitted":True})["turn"]
        self.result = {"status":"held","pains":[],"existing_features":[],"remaining_pains":[],"concepts":[],"assumptions":[],"evidence_refs":[],"validation_findings":["근거 부족"],"revisions":0,"usage_summary":{"status":"unknown"}}
        self.assessment = {"claim_checks":[],"feature_matches":[],"concept_links":[]}
        self.saved = self.store.save_result(self.turn["session_id"],self.turn["turn_id"],"first",self.result,0,self.assessment,True,"receipt")
        self.pointer = {"receipt":self.saved["receipt"],"export":self.conv.export_session({"session_id":self.turn["session_id"]})}
        self.directory = self.workspace / "trace"; self.directory.mkdir()
        self.observed = {"status":"succeeded","exit_code":0,"turn_completed":True}
        self.write_final(self.pointer)

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def write_final(self,pointer,completed=True):
        events = [{"type":"item.completed","item":{"type":"agent_message","text":"보류 근거 설명\n" + json.dumps(pointer,ensure_ascii=False)}}]
        if completed: events.append({"type":"turn.completed"})
        (self.directory / "native.jsonl").write_text("\n".join(json.dumps(e,ensure_ascii=False) for e in events),encoding="utf-8")

    def check(self):
        return probe.accept(self.workspace,self.directory,self.observed,self.case,self.data,"product")

    def test_actual_latest_export_and_final_message_pass(self):
        accepted = self.check()
        self.assertTrue(accepted["stored_match"])
        self.assertEqual(accepted["answer"]["result"],self.result)

    def test_actual_cli_export_envelope_and_failed_envelope(self):
        self.write_final({"receipt":self.saved["receipt"],"export":{"ok":True,"result":self.pointer["export"]}})
        self.assertTrue(self.check()["stored_match"])
        self.write_final({"receipt":self.saved["receipt"],"export":{"ok":False,"result":self.pointer["export"]}})
        with self.assertRaises(ValueError): self.check()

    def test_timeout_or_missing_completed_final_is_failure_even_with_valid_db(self):
        for status in ("timeout","failed","incomplete"):
            self.observed["status"] = status
            with self.assertRaises(ValueError): self.check()
        self.observed["status"] = "succeeded"
        self.write_final(self.pointer,False)
        with self.assertRaises(ValueError): self.check()

    def test_wrong_export_sha_path_or_other_handle_are_rejected(self):
        for field,value in (("sha256","0" * 64),("path","../../outside.json")):
            pointer = json.loads(json.dumps(self.pointer)); pointer["export"][field] = value
            self.write_final(pointer)
            with self.assertRaises((ValueError,OSError)): self.check()
        pointer = json.loads(json.dumps(self.pointer)); pointer["receipt"]["turn_id"] = "another-turn"
        self.write_final(pointer)
        with self.assertRaises(ValueError): self.check()

    def test_old_accepted_replay_after_rejected_latest_is_not_final(self):
        rejected = {**self.result,"revisions":1}
        failed = self.store.save_result(self.turn["session_id"],self.turn["turn_id"],"bad",rejected,1,None,True,"receipt")
        self.assertFalse(failed["accepted"])
        old = self.store.save_result(self.turn["session_id"],self.turn["turn_id"],"first",self.result,0,self.assessment,True,"receipt")
        self.assertTrue(old["accepted"])
        self.assertNotEqual(old["receipt"]["candidate_result_version"],old["receipt"]["current_result_version"])
        self.write_final({"receipt":old["receipt"],"export":self.conv.export_session({"session_id":self.turn["session_id"]})})
        with self.assertRaises(ValueError): self.check()
        self.write_final(self.pointer) # Even the formerly correct older export is stale now.
        with self.assertRaises(ValueError): self.check()

    def test_question_or_constraints_mismatch_rejected(self):
        self.case["turns"] = ["다른 질문"]
        with self.assertRaises(ValueError): self.check()

    def test_invalidated_live_turn_cannot_use_previously_valid_export(self):
        self.conv.open_request({"session_id":self.turn["session_id"],"prior_turn_id":self.turn["turn_id"],"question":"새 조건의 실제 후속 질문","model_id":"B502S33","user_submitted":True})
        with self.assertRaises(ValueError): self.check()

    def test_environment_rejects_changed_prepared_dataset(self):
        job = {"arm":"product","data_path":"data/business/lg-research-v3","data_fingerprint":"0" * 64}
        with self.assertRaisesRegex(ValueError,"Prepared dataset changed"):
            probe.check_environment(ROOT,job,ROOT)

    def test_environment_rejects_changed_or_unverifiable_installation(self):
        job = {"arm":"product","data_path":"data/business/lg-research-v3","data_fingerprint":self.data.fingerprint}
        for value in ({"errors":["modified product file"]},{}):
            with patch.object(probe.ev,"load_installer",return_value=SimpleNamespace(check=lambda p:value)):
                with self.assertRaisesRegex(ValueError,"Installed product integrity failed"):
                    probe.check_environment(ROOT,job,ROOT)
        with patch.object(probe.ev,"load_installer",return_value=SimpleNamespace(check=lambda p:{"errors":[]})):
            data, checked = probe.check_environment(ROOT,job,ROOT)
            self.assertEqual(data.fingerprint,self.data.fingerprint)
            self.assertEqual(checked["errors"],[])


if __name__ == "__main__": unittest.main()
