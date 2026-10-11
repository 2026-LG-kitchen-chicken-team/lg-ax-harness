"""Reader delivery preserves evidence and only exposes actual published files."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError
from product_tools.dataset import Dataset
from product_tools.delivery import build_report_plan, create_deliverables, _open_in_explorer


class ReportDelivery(unittest.TestCase):
    def setUp(self):
        self.dataset = Dataset(ROOT / "data/business/lg-kitchen-v4")
        self.source = next(s for s in self.dataset.sources.values() if s["kind"] == "review")
        self.scope = {k: self.source[k] for k in ("model_id", "model_version", "document_version")}
        self.planning = {"question": "불편에 맞는 개선안을 검토하고 제품 사진도 만들어 줘.",
                         "target_customer": "실제 사용자", "context": "확보한 해당 모델 근거 범위",
                         "model_scope": [self.scope], "data_version": self.dataset.version}
        self.result = {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [],
                       "concepts": [], "assumptions": [], "evidence_refs": [self.dataset.reference(self.source)],
                       "decision_notes": [{"text": "원문 범위에서 불편을 확인했으나 실물 검증은 보류한다.",
                                           "basis": "ai_interpretation", "source_ids": [self.source["source_id"]]}],
                       "validation_findings": ["제안의 효과는 아직 측정하지 않았다."]}

    def error(self, code, planning=None, result=None, sources=None, authored=None):
        with self.assertRaises(ToolError) as caught:
            build_report_plan(planning or self.planning, result or self.result,
                              sources if sources is not None else [self.source], authored)
        self.assertEqual(caught.exception.code, code)

    def authored(self):
        plan = build_report_plan(self.planning, self.result, [self.source])
        plan.update(title="사용자 맞춤 보고서", summary=["저장된 불편과 보류 범위를 검토한다."],
                    sections=[{"title": "직접 작성한 검토", "blocks": [
                        {"type": "paragraph", "text": "실제 발췌에 관한 해석", "source_ids": [self.source["source_id"]]}]}])
        return plan

    def test_default_preserves_actual_question_notes_original_and_versions(self):
        result_before = copy.deepcopy(self.result)
        plan = build_report_plan(self.planning, self.result, [self.source])
        self.assertEqual(plan["sources"][0]["text"], self.source["text"])
        self.assertEqual(plan["sources"][0]["url"], self.source["origin"]["source_url"])
        self.assertEqual(plan["sources"][0]["location"], self.source["location"])
        self.assertIs(plan["sources"][0]["synthetic"], False)
        for field in ("model_id", "model_version", "document_version", "data_version"):
            self.assertIn(self.source[field], plan["sources"][0]["model"])
        body = json.dumps(plan, ensure_ascii=False)
        self.assertIn(self.planning["question"], body)
        self.assertIn(self.result["decision_notes"][0]["text"], body)
        self.assertIn("기획 보류", body)
        self.assertNotIn("R400", body)
        self.assertNotIn("chart", body)
        self.assertFalse(any(s["title"].startswith("제안 ") for s in plan["sections"]))
        self.assertEqual(self.result, result_before)

    def test_complete_default_uses_saved_needs_features_concepts_and_unmeasured_plan(self):
        value = copy.deepcopy(self.result)
        value["status"] = "completed"
        for key in ("pains", "existing_features", "remaining_pains"):
            value[key] = [{"id": key, "text": "저장된 " + key, "source_ids": [self.source["source_id"]]}]
        value["concepts"] = [{"id": "concept", "text": "저장된 개선 제안", "source_ids": [self.source["source_id"]],
                              "requirements": ["사용 조건 유지"], "assumptions": ["시제품 전제"],
                              "implementation_steps": ["실물을 확인한다."],
                              "validation_plan": {"metric": "사용자 불편", "baseline": "현재 미측정",
                                                  "method": "동일 조건 비교", "success_criterion": "사전 결정",
                                                  "business_value": "불편 완화", "status": "planned_not_measured"}}]
        plan = build_report_plan(self.planning, value, [self.source])
        body = json.dumps(plan, ensure_ascii=False)
        for key in ("pains", "existing_features", "remaining_pains", "concepts"):
            self.assertIn(value[key][0]["text"], body)
        self.assertIn("효과 검증 계획 (미측정)", body)
        self.assertIn("현재 미측정", body)

    def test_authored_sections_preserved_and_optional_source_metadata_rebuilt(self):
        authored = self.authored()
        for key in ("url", "location", "model", "synthetic"):
            authored["sources"][0].pop(key)
        before = copy.deepcopy(authored)
        plan = build_report_plan(self.planning, self.result, [self.source], authored)
        self.assertEqual(plan["sections"], before["sections"])
        self.assertEqual(plan["summary"], before["summary"])
        self.assertEqual(plan["title"], before["title"])
        self.assertEqual(plan["sources"][0]["location"], self.source["location"])
        self.assertEqual(authored, before)

    def test_authored_fabricated_original_statistic_and_unknown_citation_rejected(self):
        for kind in ("review", "survey"):
            authored = self.authored()
            authored["sources"].append({"id": "made-up", "kind": kind, "title": "가공 원문", "text": "151명 / 62.9%"})
            self.error("report_source_integrity", authored=authored)
        authored = self.authored()
        authored["sections"][0]["blocks"][0]["source_ids"] = ["made-up"]
        self.error("report_source_integrity", authored=authored)

    def test_authored_changes_to_source_identity_or_text_rejected(self):
        for key, value in (("text", "다른 원문"), ("kind", "survey"), ("title", "가공 통계"),
                           ("url", "https://example.com/other"), ("location", "다른 위치"),
                           ("model", "다른 모델"), ("synthetic", True)):
            authored = self.authored()
            authored["sources"][0][key] = value
            with self.subTest(key=key):
                self.error("report_source_integrity", authored=authored)

    def test_original_text_hash_and_saved_reference_identity_rejected(self):
        changed = copy.deepcopy(self.source)
        changed["text"] += "가공"
        self.error("report_source_integrity", sources=[changed])
        for key in ("sha256", "document_version", "location", "synthetic"):
            value = copy.deepcopy(self.result)
            value["evidence_refs"][0][key] = True if key == "synthetic" else "0" * 64
            with self.subTest(key=key):
                self.error("report_source_integrity" if key != "synthetic" else "invalid_input", result=value)

    def test_saved_exact_substring_quote_accepted_but_spliced_quote_rejected(self):
        value = copy.deepcopy(self.result)
        quote = self.source["text"]
        value["evidence_refs"][0]["quote"] = quote[:5]
        self.assertEqual(build_report_plan(self.planning, value, [self.source])["sources"][0]["text"], quote)
        value["evidence_refs"][0]["quote"] = quote[:5] + "…" + quote[-5:]
        self.error("report_source_integrity", result=value)

    def test_other_model_or_data_version_source_rejected(self):
        other = next(s for s in self.dataset.sources.values() if s["model_id"] != self.source["model_id"])
        self.error("report_source_scope", sources=[self.source, other])
        changed = copy.deepcopy(self.source)
        changed["data_version"] = "another-version"
        self.error("report_source_scope", sources=[changed])

    def test_missing_original_and_saved_claim_reference_rejected(self):
        self.error("report_source_integrity", sources=[])
        value = copy.deepcopy(self.result)
        value["evidence_refs"] = []
        self.error("report_source_integrity", result=value)

    def test_synthetic_marking_preserved_and_real_url_not_invented(self):
        fixture = Dataset(ROOT / "data/synthetic/kitchen-v1")
        source = next(iter(fixture.sources.values()))
        planning = copy.deepcopy(self.planning)
        planning.update(model_scope=[{k: source[k] for k in self.scope}], data_version=fixture.version)
        value = copy.deepcopy(self.result)
        value["evidence_refs"] = [fixture.reference(source)]
        value["decision_notes"][0]["source_ids"] = [source["source_id"]]
        plan = build_report_plan(planning, value, [source])
        self.assertIs(plan["sources"][0]["synthetic"], True)
        self.assertNotIn("url", plan["sources"][0])

    def test_supplied_categories_and_missing_provenance_remain_distinct(self):
        originals = [{"id": "survey-original", "kind": "survey", "title": "제공된 설문", "text": "실제 제공된 원문"},
                     {"id": "interview-original", "kind": "interview", "title": "제공된 인터뷰", "text": "실제 인터뷰 원문", "synthetic": False}]
        result = {"status": "held", "evidence_refs": [], "decision_notes": [], "validation_findings": []}
        plan = build_report_plan(self.planning, result, originals)
        self.assertEqual(plan["sources"], originals)
        self.assertNotIn("synthetic", plan["sources"][0])

    def test_unfulfilled_only_quotes_actual_requested_work(self):
        authored = self.authored()
        authored["unfulfilled_requests"] = [{"request": "제품 사진도 만들어 줘", "reason": "이미지 생성 도구가 제공되지 않았다."}]
        plan = build_report_plan(self.planning, self.result, [self.source], authored)
        self.assertEqual(plan["unfulfilled_requests"], authored["unfulfilled_requests"])
        authored["unfulfilled_requests"][0]["request"] = "요청하지 않은 내부 치수"
        self.error("invalid_report_plan", authored=authored)

    def renderer(self, plan, destination):
        destination = Path(destination)
        self.assertFalse(destination.exists())
        destination.mkdir()
        files = []
        for kind in ("docx", "pdf"):
            path = destination / ("report." + kind)
            path.write_bytes(b"actual test publication")
            files.append({"path": str(path), "kind": kind, "title": "최종 보고서"})
        return {"ready": True, "directory": str(destination), "files": files,
                "checks": {"structure_verified": True, "semantic_status": "unverified", "errors": []}}

    def test_success_unique_reader_folders_and_metadata_outside_with_unsupported_os(self):
        module = types.ModuleType("product_tools.reporting")
        module.render_report = self.renderer
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": module}), patch("product_tools.delivery.sys.platform", "linux"), patch("product_tools.delivery.subprocess.Popen") as process:
            first = create_deliverables(temp, self.planning, self.result, [self.source])
            second = create_deliverables(temp, self.planning, self.result, [self.source])
            self.assertTrue(first["ready"])
            self.assertNotEqual(first["directory"], second["directory"])
            self.assertFalse(first["folder_opened"])
            process.assert_not_called()
            directory = Path(first["directory"])
            self.assertEqual({p.suffix for p in directory.iterdir()}, {".docx", ".pdf"})
            internal = Path(temp) / first["plan_path"]
            self.assertFalse(internal.is_relative_to(directory))
            self.assertEqual(json.loads(internal.read_text(encoding="utf-8"))["report_plan"]["sources"][0]["text"], self.source["text"])
            self.assertEqual(first["checks"]["semantic_status"], "unverified")
            self.assertEqual(first["errors"], [])

    def test_renderer_failure_visible_and_never_opens_folder(self):
        module = types.ModuleType("product_tools.reporting")
        failure = {"code": "pdf_generation_failed", "message": "PDF 생성 실패"}
        module.render_report = lambda plan, dest: {"ready": False, "directory": str(dest), "files": [], "checks": {"errors": [failure], "structure_verified": False}}
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": module}), patch("product_tools.delivery._open_in_explorer") as open_folder:
            result = create_deliverables(temp, self.planning, self.result, [self.source])
            self.assertFalse(result["ready"])
            self.assertEqual(result["errors"], [failure])
            open_folder.assert_not_called()

    def test_missing_renderer_dependency_and_false_publication_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": None}):
            result = create_deliverables(temp, self.planning, self.result, [self.source])
            self.assertFalse(result["ready"])
            self.assertEqual(result["errors"][0]["code"], "report_dependency_unavailable")
        module = types.ModuleType("product_tools.reporting")
        module.render_report = lambda plan, dest: {"ready": True, "directory": str(dest), "files": [{"path": str(dest / "missing.pdf"), "kind": "pdf", "title": "가공 완료"}], "checks": {}}
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": module}), patch("product_tools.delivery._open_in_explorer") as open_folder:
            result = create_deliverables(temp, self.planning, self.result, [self.source])
            self.assertFalse(result["ready"])
            self.assertEqual(result["errors"][0]["code"], "report_files_missing")
            open_folder.assert_not_called()

    def test_open_folder_false_skips_even_successful_publication(self):
        module = types.ModuleType("product_tools.reporting")
        module.render_report = self.renderer
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": module}), patch("product_tools.delivery._open_in_explorer") as open_folder:
            result = create_deliverables(temp, self.planning, self.result, [self.source], open_folder=False)
            self.assertTrue(result["ready"])
            self.assertFalse(result["folder_opened"])
            open_folder.assert_not_called()

    @unittest.skipUnless(sys.platform == "win32", "Windows Explorer invocation")
    def test_explorer_safe_argument_list_and_failure_is_separate_from_generation(self):
        with tempfile.TemporaryDirectory() as temp, patch("product_tools.delivery.subprocess.Popen") as process:
            directory = Path(temp) / "보고서 & 특수 문자"
            directory.mkdir()
            opened, error = _open_in_explorer(directory)
            self.assertTrue(opened)
            self.assertIsNone(error)
            args, kwargs = process.call_args
            self.assertEqual(args[0][1], str(directory))
            self.assertEqual(Path(args[0][0]).name.lower(), "explorer.exe")
            self.assertIs(kwargs["shell"], False)
        module = types.ModuleType("product_tools.reporting")
        module.render_report = self.renderer
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"product_tools.reporting": module}), patch("product_tools.delivery.subprocess.Popen", side_effect=OSError("Explorer unavailable")):
            result = create_deliverables(temp, self.planning, self.result, [self.source])
            self.assertTrue(result["ready"])
            self.assertEqual(result["folder_open_error"]["code"], "folder_open_failed")
            self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
