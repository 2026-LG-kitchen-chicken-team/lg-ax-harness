"""Cross-family source isolation and honest effect plans; no market claims."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"product-tools"))
from product_tools.contracts import ToolError, canonical, planning_input
from product_tools.dataset import Dataset
from product_tools.tools import ProductTools
from product_tools.web_evidence import WebEvidence


class KitchenFamilyTests(unittest.TestCase):
    def setUp(self):
        self.data=Dataset(ROOT/"data/business/lg-kitchen-v4")
        self.tools=ProductTools(self.data)

    def prepared(self,model):
        return self.tools.prepare_planning_input({"model_id":model,"session_id":"kitchen-test","request_key":"first"})["input"]

    def test_exact_model_determines_family_and_sources_remain_scoped(self):
        for model,family in (("B502S33","refrigerator"),("MWJ25E","microwave"),("DUBJ2EA","dishwasher")):
            with self.subTest(model=model):
                planning=self.prepared(model)
                self.assertEqual(planning["product_family"],family)
                self.data.check_input(planning)
                exact=planning["model_scope"][0]
                for kind in ("review","product_fact"):
                    result=self.data.retrieve(kind,exact)
                    self.assertGreater(result["total"],0)
                    self.assertTrue(all(r["model_id"]==model for r in result["records"]))

    def test_supported_but_wrong_family_and_mixed_scopes_rejected(self):
        planning=self.prepared("MWJ25E")
        planning["product_family"]="dishwasher"
        planning_input(planning)
        with self.assertRaisesRegex(ToolError,"Planning family"):
            self.data.check_input(planning)
        planning=self.prepared("MWJ25E")
        planning["model_scope"].append(self.prepared("B502S33")["model_scope"][0])
        with self.assertRaises(ToolError) as caught:
            self.tools.validate_result_contract(planning,{})
        self.assertEqual(caught.exception.code,"family_mismatch")

    def test_unsupported_family_and_withdrawn_runtime_rejected(self):
        planning=self.prepared("B502S33")
        planning["product_family"]="washing_machine"
        with self.assertRaises(ToolError) as caught:
            planning_input(planning)
        self.assertEqual(caught.exception.code,"unsupported_family")
        planning=self.prepared("B502S33")
        planning["runtime"]["engine"]="gemini"
        with self.assertRaises(ToolError):
            planning_input(planning)

    def test_cross_family_source_rejected(self):
        exact=self.prepared("DUBJ2EA")["model_scope"][0]
        with self.assertRaises(ToolError) as caught:
            self.tools.select_evidence(exact,["REVIEW-MWJ25E-01"])
        self.assertEqual(caught.exception.code,"scope_mismatch")

    def test_non_fridge_manual_association_matches_exact_family_and_document(self):
        with tempfile.TemporaryDirectory(prefix="lg-kitchen-manual-test-") as tmp:
            workspace=Path(tmp)
            web=WebEvidence(workspace/"web.sqlite",workspace)
            try:
                manual_url="https://gscs-b2c.lge.com/open/downloadFile?fileId=code-fixture"
                for mid,category in (("MWJ25E","microwaves-and-ovens"),("DUBJ2EA","dishwashers")):
                    scope=self.prepared(mid)["model_scope"][0]
                    snapshot=web.collect({"research_id":"fixture","page_id":mid+"-manual","url":manual_url,
                        "observed_text":"Code test fixture operation","native_tool_name":"fixture_not_actual_browser"},True)
                    for correct in (False,True):
                        association=web.collect({"research_id":"fixture","page_id":mid+str(correct),
                            "url":"https://www.lge.co.kr/product/"+(category if correct else "refrigerators")+"/"+mid.lower(),
                            "observed_text":mid+" "+manual_url,"native_tool_name":"fixture_not_actual_browser"},True)
                        entry={"snapshot_id":snapshot["snapshot_id"],"source_id":"FIXTURE-"+mid,"kind":"product_fact","scope":scope,
                            "location":"Code test only","text":"Code test fixture operation","support_quote":"Code test fixture operation",
                            "published_date":None,"model_matching":"product_page_association","purchase_verified":None,"sponsorship":None,
                            "feature_key":"fixture_operation","availability":"present","association_snapshot_id":association["snapshot_id"]}
                        payload={"data_version":"fixture-"+mid+str(correct),"observations":[entry]}
                        if correct:
                            self.assertFalse(web.import_evidence(self.data,payload)["acceptance_ready"])
                        else:
                            with self.assertRaises(ToolError) as caught:
                                web.import_evidence(self.data,payload)
                            self.assertEqual(caught.exception.code,"scope_mismatch")
            finally:
                web.close()

    def result(self):
        exact=self.prepared("MWJ25E")["model_scope"][0]
        source="REVIEW-MWJ25E-01"
        return {"status":"completed","pains":[],"existing_features":[],"remaining_pains":[],
            "concepts":[{"id":"c1","text":"코드 계약 시험용 초안","source_ids":[source],"requirements":["시험용 조건"],
                "requires_hardware":False,"assumptions":["실제효과 미검증"],"implementation_steps":["동일 조작 과업 프로토타입 시험"],
                "validation_plan":{"metric":"조작 과업 완료시간","baseline":"현행 안내","method":"동일 과업·품질로 비교",
                    "success_criterion":"목표는 시험 전에 합의","business_value":"조작 안내 개선 가설","status":"planned_not_measured"}}],
            "assumptions":["단위시험용, AI/고객 평가가 아님"],"evidence_refs":self.tools.select_evidence(exact,[source])["evidence_refs"],
            "validation_findings":[],"revisions":0,"usage_summary":{"status":"unknown"}}

    def test_optional_new_brief_is_structurally_complete_but_unverified(self):
        report=self.tools.validate_result_contract(self.prepared("MWJ25E"),self.result())
        self.assertTrue(report["planning_detail_complete"])
        self.assertFalse(report["acceptance_ready"])
        self.assertEqual(report["semantic_status"],"unverified")

    def test_legacy_brief_readable_and_never_claims_detail_complete(self):
        result=self.result()
        for field in ("implementation_steps","validation_plan"):
            result["concepts"][0].pop(field)
        self.assertFalse(self.tools.validate_result_contract(self.prepared("MWJ25E"),result)["planning_detail_complete"])

    def test_fabricated_measurement_and_empty_plan_rejected(self):
        for mutation in ("measured","empty","unknown_field"):
            result=self.result()
            if mutation=="measured":
                result["concepts"][0]["validation_plan"]["status"]="measured"
            elif mutation=="empty":
                result["concepts"][0]["implementation_steps"]=[]
            else:
                result["concepts"][0]["validation_plan"]["observed_saving_percent"]=30
            with self.subTest(mutation=mutation),self.assertRaises(ToolError):
                self.tools.validate_result_contract(self.prepared("MWJ25E"),result)


if __name__=="__main__":
    unittest.main()
