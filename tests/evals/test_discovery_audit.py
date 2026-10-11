"""Synthetic extra-audit boundaries; no native, web or paid model calls."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "evals/runner"))
import discovery_audit as audit


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")


def case():
    return {"id":"D01","question":"새 모델을 검토해 주세요","model_id":"NEW1",
            "product_family":"microwave","constraints":{"max_concepts":1,"hardware_allowed":False,"exclude_pains":[]},
            "parent_id":None,"require_registration":True}


class ExtraAuditTests(unittest.TestCase):
    def test_case_and_actual_prompt_are_bound_not_only_observation_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); c=case(); job={"case":c,"prompt":"원 질문\n제약"}; row={"case":copy.deepcopy(c),"execution":{"status":"timeout"}}
            (d/"prompt.txt").write_text(job["prompt"],encoding="utf-8")
            self.assertTrue(audit.frozen_input(d,job,row))
            (d/"prompt.txt").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError): audit.frozen_input(d,job,row)
            row["case"]["constraints"]["max_concepts"]=2
            with self.assertRaises(ValueError): audit.frozen_input(d,job,row)

    def test_import_requires_command_exit_and_real_stdout_not_echo_or_boolean(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"native.jsonl"
            item={"command":"uv run python product-tools/cli.py import_web_evidence --input request.json","exit_code":0,"aggregated_output":json.dumps({"ok":True,"result":{"data_path":"runtime-data/catalogs/V1"}})}
            def emit(value): p.write_text(json.dumps({"type":"item.completed","item":{"type":"command_execution",**value}}),encoding="utf-8")
            emit(item); self.assertEqual(len(audit.import_responses(p)),1)
            for change in ({"exit_code":1},{"exit_code":False},{"command":"echo python product-tools/cli.py import_web_evidence"},{"aggregated_output":'{"ok":false,"result":{}}'}):
                emit({**item,**change}); self.assertEqual(audit.import_responses(p),[])

    def test_observed_identity_must_match_actual_native_trace(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); c=case(); job={"case":c,"prompt":"question"}; row={"case":c,"execution":{"native_id":"N1"}}
            (d/"prompt.txt").write_text("question",encoding="utf-8")
            (d/"native.jsonl").write_text('{"type":"thread.started","thread_id":"N2"}',encoding="utf-8")
            with self.assertRaises(ValueError): audit.frozen_input(d,job,row)

    def test_export_request_event_history_compared_to_readonly_sqlite(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); runtime=d/"runtime-after"; runtime.mkdir()
            con=sqlite3.connect(runtime/"product.sqlite")
            con.executescript("CREATE TABLE turns(session_id TEXT,turn_id TEXT); CREATE TABLE results(turn_id TEXT,result_key TEXT,result_version INTEGER,payload TEXT,validation_json TEXT); CREATE TABLE conversation_requests(session_id TEXT,request_key TEXT,payload TEXT,turn_id TEXT,request_version INTEGER); CREATE TABLE request_events(session_id TEXT,request_key TEXT,kind TEXT,version INTEGER,payload TEXT);")
            saved={"request_key":"R1","question":"original"}
            con.execute("INSERT INTO conversation_requests VALUES (?,?,?,?,?)",("S1","R1",json.dumps(saved),None,1))
            con.execute("INSERT INTO request_events VALUES (?,?,?,?,?)",("S1","R1","research",1,'{"status":"held"}'))
            con.commit(); con.close()
            exported={"session_id":"S1","turns":[],"requests":[{"input":saved,"turn_id":None,"request_version":1,"events":[{"kind":"research","version":1,"input":{"status":"held"}}]}]}
            before=audit.base.ev.sha(runtime/"product.sqlite")
            self.assertTrue(audit.stored_history(d,exported)); self.assertEqual(audit.base.ev.sha(runtime/"product.sqlite"),before)
            exported["requests"][0]["events"]=[]
            with self.assertRaises(ValueError): audit.stored_history(d,exported)

    def fixture(self,d):
        runtime=d/"runtime-after"; catalog=runtime/"catalogs/V1"
        model={"model_id":"NEW1","model_version":"unspecified","document_version":"WEB1","name":"Synthetic boundary model", "product_family":"microwave","synthetic":False,"spec_source_id":"SPEC1",
               "identity_review":{"source_id":"SPEC1","manufacturer":"LG","authority":"manufacturer","rationale":"fixture declaration"}}
        scope={k:model[k] for k in ("model_id","model_version","document_version")}
        body={"url":"https://example.org/fixture-new1","observed_at":"2026-10-11T00:00:00Z","text":"Synthetic NEW1 identity quote","collection":"caller_reported_native_page_tool; tool name is not proof of execution"}
        sid=audit.fingerprint(body); snapshot={**body,"snapshot_id":sid}
        quote=body["text"]
        source={"source_id":"SPEC1","kind":"product_fact",**scope,"text":quote,"sha256":hashlib.sha256(quote.encode()).hexdigest(),"origin":{"source_url":body["url"],"representation":"factual_summary"}}
        payload={"data_version":"V1","new_models":[model],"observations":[{"snapshot_id":sid,"source_id":"SPEC1","kind":"product_fact","scope":scope,"availability":"present","text":quote,"support_quote":quote}]}
        write(catalog/"import-audit.json",{"input":payload,"data_fingerprint":"DATA"})
        for name in ("manifest.json","models.json","sources.jsonl"): write(catalog/name,{"fixture":name})
        write(runtime/"web-evidence"/(sid+".json"),snapshot)
        response={"data_path":"runtime-data/catalogs/V1","data_version":"V1","added_models":1,"added_sources":1,"structural_valid":True}
        item={"type":"command_execution","command":"uv run python product-tools/cli.py import_web_evidence --input input.json","exit_code":0,"aggregated_output":json.dumps({"ok":True,"result":response})}
        (d/"native.jsonl").write_text(json.dumps({"type":"item.completed","item":item}),encoding="utf-8")
        data=SimpleNamespace(root=catalog,fingerprint="DATA",models=[model],sources={"SPEC1":source})
        row={"data_path":"runtime-data/catalogs/V1","data_fingerprint":"DATA"}
        self.bind(runtime,row)
        return data,row,payload,snapshot

    def bind(self,runtime,row):
        row["runtime_snapshot"]={p.relative_to(runtime).as_posix():audit.base.ev.sha(p) for p in runtime.rglob("*") if p.is_file()}

    def test_registration_binds_identity_snapshot_and_final_source(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); data,row,payload,snapshot=self.fixture(d)
            with patch.object(audit.base.ev,"Dataset",return_value=data):
                self.assertTrue(audit.registration(d,case(),row))
                original=copy.deepcopy(data.sources["SPEC1"])
                for field,value in (("sha256","wrong"),("text","NEW1 paraphrase")):
                    data.sources["SPEC1"][field]=value
                    with self.assertRaises(ValueError): audit.registration(d,case(),row)
                    data.sources["SPEC1"]=copy.deepcopy(original)
                data.models[0]["identity_review"]["source_id"]="OTHER"
                with self.assertRaises(ValueError): audit.registration(d,case(),row)

    def test_registration_rejects_path_only_unobserved_or_mutated_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); data,row,payload,snapshot=self.fixture(d)
            with patch.object(audit.base.ev,"Dataset",return_value=data):
                (d/"native.jsonl").write_text("",encoding="utf-8")
                with self.assertRaises(ValueError): audit.registration(d,case(),row)
                p=d/"runtime-after/web-evidence"/(snapshot["snapshot_id"]+".json")
                snapshot["text"]="changed"; write(p,snapshot)
                with self.assertRaises(ValueError): audit.registration(d,case(),row)
                self.bind(d/"runtime-after",row)
                with self.assertRaises(ValueError): audit.registration(d,case(),row)

    def test_held_scope_constraints_and_resolution_selection_are_not_all_na(self):
        c=case(); saved={"question":c["question"],"constraints":copy.deepcopy(c["constraints"])}
        self.assertTrue(audit.request_scope(c,saved,[])) # legitimate unresolved
        for alteration in ("constraints","model","family","version"):
            s=copy.deepcopy(saved); events=[]
            if alteration=="constraints": s["constraints"]["hardware_allowed"]=True
            elif alteration=="model": s["model_id"]="OTHER"
            elif alteration=="family": events=[{"input":{"selection":{"product_family":"dishwasher"}}}]
            else: events=[{"input":{"selection":{"model_scope":[{"model_id":"OTHER"}]}}}]
            with self.subTest(alteration=alteration),self.assertRaises(ValueError): audit.request_scope(c,s,events)

    def test_normal_followup_uses_original_request_prior_not_compiled_turn_input(self):
        exported={"requests":[{"turn_id":"T2","input":{"prior_turn_id":"T1","request_key":"R2"},"events":[]}],
                  "turns":[{"state":{"turn_id":"T2","input":{"model_id":"NEW1"}},"candidates":[]}]}
        saved,events=audit.selected_input(exported,{"pointer":{"receipt":{"turn_id":"T2"}}})
        self.assertEqual(saved["prior_turn_id"],"T1"); self.assertEqual(events[-1]["input"]["selection"]["model_id"],"NEW1")

    def test_followup_requires_native_session_prior_and_all_candidate_history(self):
        with tempfile.TemporaryDirectory() as temp:
            report=Path(temp); c={**case(),"parent_id":"D01"}; row={"job":"D02","execution":{"native_id":"N1"}}
            parent={"job":"D01","execution":{"native_id":"N1"},"pointer":{"receipt":{"turn_id":"T1"}}}
            previous={"session_id":"S1","turns":[{"state":{"turn_id":"T1"},"candidates":[{"result_key":"K1","result":{"status":"held"}}]}],"requests":[{"input":{"request_key":"R1"}}]}
            current=copy.deepcopy(previous); saved={"prior_turn_id":"T1"}
            start={"native_parent":"N1","command":["codex","exec","resume","N1","-"]}; write(report/"D02-started.json",start)
            with patch.object(audit,"export_snapshot",return_value=previous):
                self.assertTrue(audit.followup(report,report,c,row,parent,current,saved))
                for kind in ("native","session","prior","candidate","request","command"):
                    r=copy.deepcopy(row); e=copy.deepcopy(current); s=copy.deepcopy(saved); st=copy.deepcopy(start)
                    if kind=="native": r["execution"]["native_id"]="NEW_NATIVE"
                    elif kind=="session": e["session_id"]="NEW_SESSION"
                    elif kind=="prior": s["prior_turn_id"]="OTHER_TURN"
                    elif kind=="candidate": e["turns"][0]["candidates"]=[]
                    elif kind=="request": e["requests"]=[]
                    else: st["command"]=["codex","exec","N1"]
                    write(report/"D02-started.json",st)
                    with self.subTest(kind=kind),self.assertRaises(ValueError): audit.followup(report,report,c,r,parent,e,s)

    def test_empty_and_input_only_usage_are_incomplete_boolean_not_numeric(self):
        self.assertFalse(audit.usage_fields([],0)["observed_session_usage_fields_complete"])
        row={"job":"D01","execution":{"native_id":"N1","usage":{"input_tokens":100}}}
        self.assertFalse(audit.usage_fields([row],1)["observed_session_usage_fields_complete"])
        row["execution"]["usage"]={f:1 for f in audit.base.ev.FIELDS}; row["execution"]["usage"]["output_tokens"]=True
        self.assertFalse(audit.usage_fields([row],1)["observed_session_usage_fields_complete"])

    def test_usage_includes_failed_attempts_latest_unknown_and_missing_id(self):
        row={"job":"D01","execution":{"status":"timeout","native_id":"N1","usage":{f:1 for f in audit.base.ev.FIELDS}}}
        complete=audit.usage_fields([row],1)
        self.assertTrue(complete["observed_session_usage_fields_complete"]); self.assertFalse(complete["full_backend_usage_verified"])
        self.assertNotIn("complete_native_usage",complete)
        self.assertFalse(audit.usage_fields([row],2)["observed_session_usage_fields_complete"])
        later={"job":"D02","execution":{"status":"failed","native_id":"N1","usage":{}}}
        self.assertFalse(audit.usage_fields([row,later],2)["observed_session_usage_fields_complete"])
        later["execution"].pop("native_id")
        self.assertFalse(audit.usage_fields([row,later],2)["native_attempt_coverage"])

    def test_combined_pass_requires_extra_checks_and_keeps_failure_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            report=Path(temp); c=case(); row={"job":"D01","case":c,"execution":{},"acceptance":"failed"}
            (report/"D01").mkdir(); write(report/"prepared.json",{}); write(report/"results.json",{"native_attempts":0,"results":[row]})
            base_result={"outcomes":[{"overall_passed":True,"findings":[]}],"limits":[],"usage":{}}
            with patch.object(audit.base,"audit",return_value=base_result),patch.object(audit.base,"verify_plan",return_value={"jobs":[{"case":c,"prompt":"","name":"D01"}]}):
                result=audit.audit(report)
            self.assertFalse(result["overall_pass"]); self.assertEqual(len(result["outcomes"]),1)
            self.assertFalse(result["outcomes"][0]["additional_checks"]["observed_new_model_registration"])
            self.assertEqual(base_result["outcomes"][0]["findings"],[]) # no base mutation


if __name__ == "__main__":
    unittest.main()
