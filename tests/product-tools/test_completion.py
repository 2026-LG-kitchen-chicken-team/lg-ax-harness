"""Final delivery/version/failure boundaries with synthetic inputs; no AI."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.completion import access_failures
from product_tools.contracts import MAX_BYTES, ToolError, canonical, strict_json
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store = StateStore(self.root / "runtime-data/test.sqlite", self.data)
        self.addCleanup(self.store.close)
        self.conv = Conversation(self.store, self.root)
        planning = strict_json((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))
        self.turn = self.store.start_turn(planning, True)
        self.handle = {"session_id": planning["session_id"], "turn_id": self.turn["turn_id"]}
        ids = ["REV-AX-R301-1.0-02", "DOC-AX-R301-1.0-01"]
        refs = self.store.tools.select_evidence(planning["model_scope"][0], ids)["evidence_refs"]
        self.result = {"status":"completed", "pains":[{"id":"p1","text":"시험용 불편","source_ids":[ids[0]]}],
            "existing_features":[{"id":"f1","text":"시험용 기존 기능","source_ids":[ids[1]]}],
            "remaining_pains":[{"id":"r1","text":"시험용 남은 불편","source_ids":[ids[0]]}],
            "concepts":[{"id":"c1","text":"조건부 기획 문구를 그대로 유지한다.","source_ids":[ids[0]],
                "requirements":["실물 확인"],"requires_hardware":False,"assumptions":["적용 조건 미확인"],
                "validation_plan":{"metric":"과업 완료","baseline":"현재 기능","method":"동일 조건 비교",
                    "success_criterion":"오류 증가 없음","business_value":"기획 검증","status":"planned_not_measured"}}],
            "assumptions":["시험 입력이며 시장 근거가 아님"],"evidence_refs":refs,
            "validation_findings":[],"revisions":0,"usage_summary":{"status":"unknown"}}
        self.assessment={"claim_checks":[{"claim_id":c["id"],"source_ids":c["source_ids"],
            "support_status":"supported","scope_relation":"current_model","rationale":"합성 계약 시험"}
            for key in ("pains","existing_features","remaining_pains","concepts") for c in self.result[key]],
            "feature_matches":[{"remaining_pain_id":"r1","pain_id":"p1","feature_source_ids":[ids[1]],
                "resolution":"unresolved","rationale":"합성 대조 시험"}],
            "concept_links":[{"concept_id":"c1","remaining_pain_ids":["r1"],"duplicates_existing":False,
                "geometry_required":False,"geometry_known":False,"geometry_source_ids":[],"rationale":"합성 계약 시험"}]}

    def save(self, result=None):
        return self.conv.save_and_export({**self.handle,"result_key":"initial","expected_result_version":0,
            "result":result or self.result,"assessment":self.assessment})

    def summary(self, version=1):
        return self.conv.get_completion_summary({**self.handle,"expected_result_version":version})

    def error(self, code, callback):
        with self.assertRaises(ToolError) as raised: callback()
        self.assertEqual(raised.exception.code, code)

    def test_exact_saved_concept_and_conditions_used_without_new_fact_generation(self):
        response=self.save()
        summary=response["completion_summary"]
        self.assertTrue(summary["ready"])
        self.assertIn(self.result["concepts"][0]["text"],summary["text"])
        self.assertIn("적용 조건 미확인",summary["text"])
        self.assertNotIn("검토 완료",summary["text"])
        artifact=self.root/summary["path"]
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),summary["sha256"])
        value=json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(value["concepts"][0]["text"],self.result["concepts"][0]["text"])
        self.assertEqual(self.summary()["sha256"],summary["sha256"])
        self.assertEqual(self.store.get_turn(**self.handle)["result_version"],1)

    def test_wrong_current_version_and_changed_dependencies_are_rejected(self):
        self.save()
        self.error("current_state_changed",lambda:self.summary(2))
        for target, key in ((self.store, "code_hash"), (self.data, "fingerprint")):
            original = getattr(target, key)
            setattr(target, key, "changed")
            self.error("current_state_changed", self.summary)
            setattr(target, key, original)
        self.assertTrue(self.summary()["ready"])

    def test_modified_saved_result_or_immutable_completion_is_rejected(self):
        summary = self.save()["completion_summary"]
        artifact = self.root / summary["path"]
        artifact.write_bytes(b"{}")
        self.error("completion_integrity", self.summary)
        changed = copy.deepcopy(self.result)
        changed["concepts"][0]["text"] = "Changed after review"
        self.store.db.execute("UPDATE results SET payload=? WHERE turn_id=?", (canonical(changed), self.handle["turn_id"]))
        self.error("result_integrity", self.summary)

    def test_cancelled_held_result_cannot_reissue_completion(self):
        changed = copy.deepcopy(self.result)
        changed.update(status="held", validation_findings=["추가 근거 필요"])
        self.save(changed)
        self.store.cancel_turn(**self.handle, cancel_key="stop", reason="사용자 중단", expected_result_version=1, user_submitted=True)
        self.error("current_state_changed", self.summary)

    def test_held_concept_retains_the_saved_reason_in_final_delivery(self):
        changed=copy.deepcopy(self.result)
        changed["status"]="held"
        reason="정확 모델과 내부 치수가 미확인되어 적용 판정을 보류합니다."
        changed["validation_findings"]=[reason]
        response=self.save(changed)
        self.assertTrue(response["completion_summary"]["ready"])
        text=response["completion_summary"]["text"]
        self.assertIn(reason,text)
        self.assertIn(changed["concepts"][0]["text"],text)
        self.assertIn("추가 확인이 필요한",text)

    def test_plain_structural_save_does_not_become_reviewed_final_delivery(self):
        self.store.save_result(**self.handle,result_key="raw",result=self.result,expected_result_version=0)
        self.error("completion_review_required",self.summary)

    def test_planned_protocol_is_optional_but_cannot_claim_measured_effect(self):
        changed=copy.deepcopy(self.result)
        changed["concepts"][0]["validation_plan"]["evaluation_protocol"]={"unit":"전체 배정 과업",
            "failed_or_stopped":"실패와 중단 포함","unknown":"미확인 별도 보고"}
        self.assertTrue(self.save(changed)["delivery_ready"])

    def test_optional_planning_details_are_nonblocking_in_stored_receipt(self):
        changed = copy.deepcopy(self.result)
        response = self.save(changed)
        diagnostics = response["save"]["validation"]["planning_quality_diagnostics"]
        self.assertTrue(response["delivery_ready"])
        self.assertEqual(diagnostics["scope"], "structural_only")
        self.assertFalse(diagnostics["blocking"])
        self.assertEqual(diagnostics["concepts"], [{"concept_id": "c1", "missing_optional_fields":
            ["evaluation_protocol", "condition_controls", "guardrail_metrics"]}])
        self.assertEqual(self.store.get_turn(**self.handle)["latest_result"], changed)

    def test_typed_planning_controls_and_guardrails_stay_unmeasured(self):
        changed = copy.deepcopy(self.result)
        plan = changed["concepts"][0]["validation_plan"]
        plan.update(evaluation_protocol={"unit": "전체 배정 과업", "failed_or_stopped": "실패·중단도 전체 시도에 포함",
                                        "unknown": "미응답을 미확인으로 별도 보고"},
                    condition_controls=["같은 모델·버전·초기 상태·과업을 사전에 배정"],
                    guardrail_metrics=[{"metric": "오안내 및 과업 완료품질", "method": "실패 포함 동일 조건 비교",
                                        "non_regression_criterion": "오안내 증가와 완료품질 저하가 없을 것"}])
        response = self.save(changed)
        validation = response["save"]["validation"]
        self.assertTrue(response["delivery_ready"])
        self.assertEqual(validation["planning_quality_diagnostics"]["concepts"], [])
        self.assertEqual(validation["semantic_status"], "unverified")
        self.assertFalse(validation["acceptance_ready"])
        self.assertEqual(self.store.get_turn(**self.handle)["latest_result"]["concepts"][0]["validation_plan"], plan)

    def test_invalid_planning_detail_types_and_measurement_status_are_rejected(self):
        invalid = [("condition_controls", "동일 조건"), ("condition_controls", []),
                   ("condition_controls", [True]), ("guardrail_metrics", ["오류율"]),
                   ("guardrail_metrics", [{"metric": "오류율", "method": "동일 비교", "non_regression_criterion": True}]),
                   ("guardrail_metrics", [{"metric": "오류율", "method": "동일 비교", "non_regression_criterion": "악화 없음", "measured_value": 0}]),
                   ("evaluation_protocol", {"unit": "전체", "failed_or_stopped": "포함", "unknown": False}),
                   ("status", "measured")]
        for key, value in invalid:
            with self.subTest(field=key, value=value):
                changed = copy.deepcopy(self.result)
                changed["concepts"][0]["validation_plan"][key] = value
                self.error("invalid_input", lambda: self.store.tools.validate_result_contract(self.turn["input"], changed))

    def test_legacy_plan_omission_keeps_finalization_with_small_diagnostic(self):
        changed = copy.deepcopy(self.result)
        changed["concepts"][0].pop("validation_plan")
        response = self.save(changed)
        self.assertTrue(response["delivery_ready"])
        self.assertFalse(response["save"]["validation"]["planning_detail_complete"])
        self.assertEqual(response["save"]["validation"]["planning_quality_diagnostics"]["concepts"],
                         [{"concept_id": "c1", "missing_optional_fields": ["validation_plan"]}])

    def test_skill_wrapper_replays_current_completion_and_rejects_stale_version(self):
        self.result["decision_notes"] = [{"text": "계약 시험의 적용 한계", "basis": "ai_interpretation",
                                          "source_ids": [self.result["evidence_refs"][0]["source_id"]]}]
        expected = self.save()["completion_summary"]
        shutil.copytree(ROOT / "product-tools", self.root / "product-tools", ignore=shutil.ignore_patterns("__pycache__"))
        for relative in ("skills/manifest.json", "skills/review-and-revise/scripts/run.py"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        input_path = self.root / "summary-input.json"
        command = [sys.executable, "skills/review-and-revise/scripts/run.py", "get_completion_summary",
                   "--data", str(self.data.root), "--db", str(self.store.path), "--input", str(input_path)]
        for version, exit_code in ((1, 0), (2, 1)):
            input_path.write_text(canonical({**self.handle, "expected_result_version": version}), encoding="utf-8")
            process = subprocess.run(command, cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertEqual(process.returncode, exit_code, process.stdout + process.stderr)
            response = strict_json(process.stdout)
            if exit_code == 0:
                self.assertEqual(response["result"]["sha256"], expected["sha256"])
                self.assertEqual(response["result"]["text"], expected["text"])
            else:
                self.assertEqual(response["error"]["code"], "current_state_changed")

    def test_error_reason_is_not_a_user_link_or_invented_http_status(self):
        event={"kind":"source_scan","data":{"source_url":"https://example.com/a","page_label":"자료 A",
            "status":"inaccessible","reason":"runtime-data/wrong-http.json HTTP307","reviews":[]}}
        failures=access_failures([event])
        self.assertEqual(len(failures),1)
        self.assertIsNone(failures[0]["http_status"])
        self.assertNotIn("wrong-http",canonical(failures))
        self.assertFalse(failures[0]["diagnostic_link_required"])

    def test_recovered_source_is_not_reported_as_still_inaccessible(self):
        def event(status):return {"kind":"source_scan","data":{"source_url":"https://example.com/a",
            "page_label":"자료","status":status}}
        self.assertEqual(access_failures([event("inaccessible"),event("observed")]),[])
        self.assertEqual(len(access_failures([event("inaccessible"),event("inaccessible")])),1)
