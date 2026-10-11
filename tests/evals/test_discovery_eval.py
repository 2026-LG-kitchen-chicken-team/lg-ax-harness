"""Synthetic boundary tests; no product model, web or native invocation."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"evals/runner"))
import discovery_eval as probe
from product_tools.contracts import ToolError


def corpus():
    cases = [{"id":f"D{i}","chain_id":f"C{i}","parent_id":None,"question":f"새 모델의 요청 {i}",
              "model_id":f"NEW{i}","product_family":"refrigerator","constraints":{"max_concepts":1,"hardware_allowed":False,"exclude_pains":[]}}
             for i in range(1,5)]
    cases[0]["require_registration"] = True
    cases[1].update(chain_id="C1",parent_id="D1")
    return {"cases":cases,"existing_model_ids":["PREVIOUS"],"limits":copy.deepcopy(probe.LIMITS)}


class DiscoveryBoundaryTests(unittest.TestCase):
    def test_four_to_five_inputs_unique_parent_and_new_model_required(self):
        self.assertEqual(len(probe.validate_cases(corpus())),3)
        for alteration in ("count","duplicate","parent","already_known","prior_unknown","fault","budget","path"):
            c = corpus()
            if alteration=="count": c["cases"].pop()
            elif alteration=="duplicate": c["cases"][-1]["id"]="D1"
            elif alteration=="parent": c["cases"][1]["parent_id"]="WRONG"
            elif alteration=="already_known": c["existing_model_ids"].append("NEW1")
            elif alteration=="prior_unknown": c.pop("existing_model_ids")
            elif alteration=="fault": c["cases"][0]["synthetic_fault_injection"]=True
            elif alteration=="budget": c["limits"]["native_cap"]=6
            else: c["cases"][0]["id"]="../escape"
            with self.subTest(alteration=alteration),self.assertRaises((ValueError,ToolError)):
                probe.validate_cases(c)

    def test_prompt_preserves_question_constraints_without_expected_hints(self):
        c=corpus()["cases"][0]
        c.update(expected_terminal_states=["SECRET_MARKER"],required_behaviors=["SECRET_MARKER"],gold_concept="SECRET_MARKER")
        text=probe.build_prompt(c)
        self.assertIn(c["question"],text)
        self.assertIn('"max_concepts": 1',text)
        self.assertNotIn("SECRET_MARKER",text)
        self.assertNotIn("외부 웹/API",text)
        self.assertIn("data/business/empty",text)

    def test_web_search_is_global_and_resume_uses_actual_identity(self):
        command=probe.web_command("codex.exe",Path("workspace"),Path("final.txt"),"actual-parent")
        self.assertEqual(command[1],"--search")
        self.assertLess(command.index("--search"),command.index("exec"))
        self.assertIn("resume",command)
        self.assertEqual(command[-2:], ["actual-parent","-"])
        self.assertIn("multi_agent",command)
        self.assertNotIn("--model",command)

    def test_only_runtime_changes_are_allowed_code_skill_and_new_file_are_detected(self):
        with tempfile.TemporaryDirectory() as t:
            w=Path(t); (w/"skills").mkdir(); (w/"skills/SKILL.md").write_text("original")
            before=probe.protected_tree(w)
            (w/"runtime-data/catalogs/V1").mkdir(parents=True)
            (w/"runtime-data/catalogs/V1/manifest.json").write_text("runtime only")
            self.assertEqual(probe.protected_tree(w),before)
            (w/"skills/SKILL.md").write_text("changed")
            self.assertNotEqual(probe.protected_tree(w),before)
            (w/"skills/SKILL.md").write_text("original")
            (w/"skills/runtime-data").mkdir()
            (w/"skills/runtime-data/hidden.py").write_text("unauthorized nested code")
            self.assertNotEqual(probe.protected_tree(w),before)
            (w/"unapproved.py").write_text("new code")
            self.assertNotEqual(probe.protected_tree(w),before)

    def test_sqlite_wal_snapshot_preserves_committed_state_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as t:
            w=Path(t)/"workspace"; runtime=w/"runtime-data"; runtime.mkdir(parents=True)
            con=sqlite3.connect(runtime/"product.sqlite")
            try:
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("CREATE TABLE data(value TEXT)")
                con.execute("INSERT INTO data VALUES ('actual committed fixture')"); con.commit()
                before=con.execute("SELECT * FROM data").fetchall()
                hashes=probe.preserve_runtime(w,Path(t)/"snapshot")
                copied=sqlite3.connect(Path(t)/"snapshot/product.sqlite")
                try: self.assertEqual(copied.execute("SELECT * FROM data").fetchall(),before)
                finally: copied.close()
                self.assertIn("product.sqlite",hashes)
                self.assertNotIn("product.sqlite-wal",hashes)
                self.assertEqual(con.execute("SELECT * FROM data").fetchall(),before)
                with self.assertRaises(FileExistsError): probe.preserve_runtime(w,Path(t)/"snapshot")
            finally: con.close()

    def pending_fixture(self,root):
        w=root/"workspace"; runtime=w/"runtime-data"; (runtime/"exports").mkdir(parents=True)
        case=corpus()["cases"][0]
        payload={"question":case["question"],"request_key":"REQ","constraints":case["constraints"]}
        request={"session_id":"SESSION","request_key":"REQ","status":"held","turn_id":None,
                 "request_version":2,"reason":{"code":"research_unavailable"}}
        exported={"session_id":"SESSION","turns":[],"requests":[{"input":payload,"response":request,"turn_id":None}]}
        p=runtime/"exports/held.json"; p.write_text(json.dumps(exported),encoding="utf-8")
        pointer={"request":request,"export":{"path":"runtime-data/exports/held.json","sha256":probe.ev.sha(p)}}
        con=sqlite3.connect(runtime/"product.sqlite")
        con.execute("CREATE TABLE conversation_requests(session_id TEXT,request_key TEXT,payload TEXT,turn_id TEXT,response TEXT)")
        con.execute("INSERT INTO conversation_requests VALUES (?,?,?,?,?)",("SESSION","REQ",json.dumps(payload),None,json.dumps(request)))
        con.commit(); con.close()
        d=root/"output"; d.mkdir(); text=json.dumps(pointer)
        events=[{"type":"item.completed","item":{"type":"agent_message","text":text}},{"type":"turn.completed"}]
        (d/"native.jsonl").write_text("\n".join(json.dumps(e) for e in events),encoding="utf-8")
        (d/"final.txt").write_text(text,encoding="utf-8")
        observed={"status":"succeeded","exit_code":0,"turn_completed":True}
        return w,d,case,observed,pointer

    def test_pending_held_is_delivered_but_never_completed_planning(self):
        with tempfile.TemporaryDirectory() as t:
            w,d,c,o,p=self.pending_fixture(Path(t))
            value=probe.accept_delivery(w,d,o,c)
            self.assertEqual(value["acceptance"],"pending_request_delivered")
            self.assertFalse(value["planning_completed"])
            self.assertIsNone(value["answer"])
            value["runtime_snapshot"]=probe.preserve_runtime(w,d/"runtime-after")
            probe.audit_snapshot(d,value)
            con=sqlite3.connect(d/"runtime-after/product.sqlite")
            con.execute("UPDATE conversation_requests SET response='{}'"); con.commit(); con.close()
            with self.assertRaises(ValueError): probe.audit_snapshot(d,value)

    def test_timeout_cannot_pass_using_good_export_or_database(self):
        with tempfile.TemporaryDirectory() as t:
            w,d,c,o,p=self.pending_fixture(Path(t)); o["status"]="timeout"
            with self.assertRaises(ValueError): probe.accept_delivery(w,d,o,c)

    def test_pending_question_database_and_ambiguous_pointers_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            w,d,c,o,p=self.pending_fixture(Path(t))
            bad={**c,"question":"different user request"}
            with self.assertRaises(ValueError): probe.accept_delivery(w,d,o,bad)
            text=json.dumps(p)+"\n"+json.dumps({"receipt":{},"export":p["export"]})
            with patch.object(probe.receipt,"final_message",return_value=text),self.assertRaises(ValueError):
                probe.accept_delivery(w,d,o,c)
            con=sqlite3.connect(w/"runtime-data/product.sqlite")
            con.execute("UPDATE conversation_requests SET response='{}'"); con.commit(); con.close()
            with self.assertRaises(ValueError): probe.accept_delivery(w,d,o,c)

    def test_raw_rollout_unknown_is_not_zero_or_fabricated(self):
        self.assertEqual(probe.preserve_rollout(None,Path("unused"))["status"],"unknown")
        with tempfile.TemporaryDirectory() as t,patch.dict(probe.os.environ,{"CODEX_HOME":t}):
            self.assertEqual(probe.preserve_rollout("absent-native",Path(t))["status"],"unknown")
            sessions=Path(t)/"sessions"; sessions.mkdir()
            raw=sessions/"rollout-real-native.jsonl"; raw.write_text('{"fixture":true}\n',encoding="utf-8")
            target=Path(t)/"output"; target.mkdir()
            saved=probe.preserve_rollout("real-native",target)
            self.assertEqual(saved["sha256"],probe.ev.sha(raw))
            with self.assertRaises(ValueError): probe.preserve_rollout("real-native",target)

    def test_catalog_path_traversal_cannot_escape_runtime(self):
        for value in ("../outside","C:/outside","../../empty"):
            with self.subTest(value=value),self.assertRaises(Exception): probe.dataset_for(Path("unused"),value)

    def sealed_plan(self,report):
        c=corpus(); report.mkdir(); temporary=report/"temporary"; temporary.mkdir()
        jobs=[]
        for case in c["cases"]:
            text=probe.build_prompt(case)
            jobs.append({"name":case["id"],"case":case,"workspace":str(temporary/case["chain_id"]),"protected":{},
                         "prompt":text,"prompt_sha256":probe.hashlib.sha256(text.encode()).hexdigest()})
        probe.ev.dump(report/"cases.json",c)
        plan={"jobs":jobs,"source":{},"runner":{},"temporary_root":str(temporary),"cases_sha256":probe.ev.sha(report/"cases.json"),
              "limits":probe.LIMITS,"run_seconds":probe.RUN_SECONDS}
        probe.ev.dump(report/"prepared.json",plan)
        (report/"prepared.sha256").write_text(probe.ev.sha(report/"prepared.json"),encoding="ascii")
        return plan

    def test_sealed_plan_rejects_budget_prompt_and_file_tampering(self):
        with tempfile.TemporaryDirectory() as t:
            report=Path(t)/"report"; plan=self.sealed_plan(report)
            self.assertEqual(len(probe.verify_plan(report)["jobs"]),4)
            plan["jobs"][0]["prompt"]+=" changed"
            probe.ev.dump(report/"prepared.json",plan)
            with self.assertRaises(ValueError): probe.verify_plan(report)
            (report/"prepared.sha256").write_text(probe.ev.sha(report/"prepared.json"),encoding="ascii")
            with self.assertRaises(ValueError): probe.verify_plan(report)

    def test_audit_keeps_not_run_and_usage_unknown_and_binds_review_to_raw_result(self):
        with tempfile.TemporaryDirectory() as t:
            report=Path(t)/"report"; plan=self.sealed_plan(report); rows=[]
            for job in plan["jobs"]:
                directory=report/job["name"]; directory.mkdir()
                row={"job":job["name"],"case":job["case"],"acceptance":"not_run","semantic_review":"not_run"}
                probe.ev.dump(directory/"result.json",row); rows.append(row)
            probe.ev.dump(report/"results.json",{"results":rows,"native_attempts":0})
            result=probe.audit(report)
            self.assertEqual(result["native_attempts"],0)
            self.assertTrue(all(not r["overall_passed"] for r in result["outcomes"]))
            self.assertIsNone(result["usage"]["observed_session_totals"]["input_tokens"]["known_sum"])
            review=report/"review.json"
            probe.ev.dump(review,{"reviews":[{"id":"D1","raw_result_sha256":"wrong","scores":[2]*7,"critical_errors":[],"findings":[]}]})
            with self.assertRaises(ValueError): probe.audit(report,review)


if __name__=="__main__":
    unittest.main()
