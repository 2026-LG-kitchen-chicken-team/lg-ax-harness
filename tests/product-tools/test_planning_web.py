"""Meaningful failures at the planning-review and external evidence boundary."""
import copy
import io
from email.message import Message
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.dataset import Dataset
from product_tools.planning import review_product_result
from product_tools.tools import ProductTools
from product_tools.web_evidence import WebEvidence, public_url


class PlanningWebTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runtime-data")
        self.workspace = Path(self.temp.name)
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.tools = ProductTools(self.data)
        self.web = WebEvidence(self.workspace / "web.sqlite", self.workspace)
        self.scope = {"model_id": "T876MQQ012", "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10"}
        self.planning = self.tools.prepare_planning_input({"model_id": "T876MQQ012", "session_id": "test", "request_key": "request"})["input"]

    def tearDown(self):
        self.web.close()
        self.assertTrue(self.workspace.resolve().is_relative_to(ROOT / "runtime-data"))
        self.temp.cleanup()

    def error(self, code, function, *args):
        with self.assertRaises(ToolError) as caught:
            function(*args)
        self.assertEqual(caught.exception.code, code)

    def candidate(self):
        # Only a code-contract fixture. Text is not a demonstration of AI quality.
        rid, fid = "REVIEW-T876MQQ012-01", "SPEC-T876MQQ012-02"
        result = {"status": "completed", "pains": [{"id": "p1", "text": "시험: 적재 그림자", "source_ids": [rid]}],
                  "existing_features": [{"id": "f1", "text": "상부 조명", "source_ids": [fid]}],
                  "remaining_pains": [{"id": "r1", "text": "시험: 찾기 부담", "source_ids": [rid, fid]}],
                  "concepts": [{"id": "c1", "text": "계약 시험용 후보", "source_ids": [rid, fid], "requirements": ["실측 대기"], "requires_hardware": False, "assumptions": []}],
                  "assumptions": [], "evidence_refs": self.tools.select_evidence(self.scope, [rid, fid])["evidence_refs"],
                  "validation_findings": [], "revisions": 0, "usage_summary": {"status": "unknown"}}
        checks = [{"claim_id": c["id"], "source_ids": c["source_ids"], "support_status": "supported", "scope_relation": "current_model", "rationale": "Code fixture; not independently verified"}
                  for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in result[key]]
        assessment = {"claim_checks": checks, "feature_matches": [{"remaining_pain_id": "r1", "pain_id": "p1", "feature_source_ids": [fid], "resolution": "unresolved", "rationale": "Fixture"}],
                      "concept_links": [{"concept_id": "c1", "remaining_pain_ids": ["r1"], "duplicates_existing": False, "geometry_required": False, "geometry_known": False, "geometry_source_ids": [], "rationale": "Fixture"}]}
        return {"input": self.planning, "result": result, "assessment": assessment}

    def test_report_pass_never_certifies_meaning(self):
        report = review_product_result(self.data, self.candidate())
        self.assertTrue(report["reported_reasoning_consistent"])
        self.assertEqual(report["semantic_status"], "unverified")
        self.assertFalse(report["acceptance_ready"])

    def test_previous_product_or_uncertain_claim_blocks_completed(self):
        for field, value in (("scope_relation", "previous_product"), ("support_status", "uncertain")):
            payload = self.candidate()
            payload["assessment"]["claim_checks"][0][field] = value
            self.assertFalse(review_product_result(self.data, payload)["can_finalize_reported_result"])

    def test_no_assessment_or_wrong_claim_sources_rejected(self):
        for mutate in (lambda p: p["assessment"]["claim_checks"].pop(), lambda p: p["assessment"]["claim_checks"][0].update(source_ids=[])):
            payload = self.candidate()
            mutate(payload)
            self.error("invalid_assessment", review_product_result, self.data, payload)

    def test_resolved_pain_and_duplicate_concept_block_finalization(self):
        for mode in ("resolved", "duplicate", "uncertain_duplicate"):
            payload = self.candidate()
            if mode == "resolved":
                payload["assessment"]["feature_matches"][0]["resolution"] = "resolved"
            else:
                payload["assessment"]["concept_links"][0]["duplicates_existing"] = True if mode == "duplicate" else None
            self.assertFalse(review_product_result(self.data, payload)["can_finalize_reported_result"])

    def test_geometry_dependency_only_blocks_when_required(self):
        payload = self.candidate()
        self.assertTrue(review_product_result(self.data, payload)["can_finalize_reported_result"])
        payload["assessment"]["concept_links"][0]["geometry_required"] = True
        self.assertFalse(review_product_result(self.data, payload)["can_finalize_reported_result"])

    def test_concept_cannot_link_to_missing_remaining_pain(self):
        payload = self.candidate()
        payload["assessment"]["concept_links"][0]["remaining_pain_ids"] = []
        self.error("invalid_assessment", review_product_result, self.data, payload)

    def test_positive_only_held_result_is_representable(self):
        payload = self.candidate()
        for key in ("pains", "existing_features", "remaining_pains", "concepts", "evidence_refs"):
            payload["result"][key] = []
        payload["result"].update(status="held", validation_findings=["Positive-only or insufficient evidence"])
        payload["assessment"] = {"claim_checks": [], "feature_matches": [], "concept_links": []}
        self.assertTrue(review_product_result(self.data, payload)["can_finalize_reported_result"])

    def browser(self, page="p1", content="T876MQQ012 실제 관측 본문. 구석이 어둡다."):
        return {"research_id": "research", "page_id": page, "url": "https://www.lge.co.kr/refrigerators/t876mqq012", "observed_text": content, "native_tool_name": "test_fixture_not_actual_browser"}

    def test_private_or_credential_url_and_redirect_target_rejected(self):
        for url in ("http://www.lge.co.kr/", "https://127.0.0.1/", "https://www.lge.co.kr.evil.example/", "https://user:pass@www.lge.co.kr/", "https://www.lge.co.kr:8443/"):
            self.error("unsupported_url", public_url, url)

    def test_url_type_is_checked_before_manual_parser_and_reservation(self):
        for url in (None, True, 17, {}, []):
            for browser in (True, False):
                payload = {**self.browser(), 'url': url}
                if not browser:
                    payload = {k: v for k, v in payload.items() if k not in ('observed_text', 'native_tool_name')}
                self.error('invalid_input', self.web.collect, payload, browser)
        self.assertEqual(self.web.db.execute('SELECT COUNT(*) FROM web_pages').fetchone()[0], 0)

    def test_browser_capture_does_not_claim_execution(self):
        report = self.web.collect(self.browser(), True)
        self.assertIn("caller_reported", report["collection"])
        self.assertEqual(report["semantic_status"], "unverified")
        self.assertTrue(self.web.collect(self.browser(), True)["cached"])

    def test_preview_size_preserves_snapshot_and_cached_page_identity(self):
        payload = self.browser(content="T876MQQ012 " + "x" * 1700 + "구석이 어둡다.")
        compact = self.web.collect({**payload, "preview_chars": 256}, True)
        snapshot = self.web._read(compact["snapshot_id"])
        self.assertEqual(snapshot["text"], payload["observed_text"])
        self.assertNotIn("구석이 어둡다.", compact["text_preview"])
        self.assertTrue(compact["preview_truncated"])
        expanded = self.web.collect({**payload, "preview_chars": 4000}, True)
        self.assertTrue(expanded["cached"])
        self.assertEqual(expanded["snapshot_id"], compact["snapshot_id"])
        self.assertIn("구석이 어둡다.", expanded["text_preview"])
        row = self.web.db.execute("SELECT attempts FROM web_pages").fetchone()
        self.assertEqual(row[0], 1)
        imported = self.web.import_evidence(self.data, {"data_version": "outside-preview", "observations": [self.observation(compact)]})
        self.assertFalse(imported["acceptance_ready"])
        self.assertEqual(imported["semantic_status"], "unverified")

    def test_invalid_preview_sizes_do_not_reserve_a_page(self):
        for value in (True, False, 0, 255, 4001, 256.0, "1200", None):
            self.error("invalid_input", self.web.collect, {**self.browser(), "preview_chars": value}, True)
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0], 0)

    def test_focus_preview_includes_target_and_marks_its_separate_window(self):
        payload = {**self.browser(content="T876MQQ012 " + "x" * 1300 + "TARGET" + "y" * 2000), "focus": "TARGET", "preview_chars": 300}
        summary = self.web.collect(payload, True)
        saved = self.web._read(summary["snapshot_id"])
        self.assertIn("TARGET", summary["text_preview"])
        self.assertEqual(summary["text_preview"], saved["text"][summary["preview_start"]:summary["preview_start"] + 300])
        self.assertGreater(summary["text_start"], 0)
        self.assertGreater(summary["preview_start"], 0)
        self.assertTrue(summary["truncated"])
        self.assertTrue(summary["preview_truncated"])

    def test_minimum_preview_retains_maximum_focus_literal(self):
        focus = "F" * 200
        payload = {**self.browser(content="T876MQQ012 " + "x" * 1300 + focus + "y" * 2000), "focus": focus, "preview_chars": 256}
        summary = self.web.collect(payload, True)
        self.assertIn(focus, summary["text_preview"])
        self.assertEqual(len(summary["text_preview"]), 256)

    def test_official_manual_capture_is_supported_without_http_pdf_parser(self):
        payload = {**self.browser(), "url": "https://gscs-b2c.lge.com/open/downloadFile?fileId=manual", "observed_text": "공용 설명서: 접이식 선반"}
        report = self.web.collect(payload, True)
        self.assertIn("caller_reported_native_page_tool", report["collection"])
        self.assertEqual(report["semantic_status"], "unverified")
        headers = Message()
        headers["Content-Type"] = "application/pdf"
        response = io.BytesIO(b"%PDF")
        response.headers = headers
        http_payload = {k: v for k, v in payload.items() if k not in ("observed_text", "native_tool_name")}
        http_payload["page_id"] = "http-pdf"
        with patch("product_tools.web_evidence.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.error("unsupported_content", self.web.collect, http_payload)

    def manual_observation(self):
        url = "https://gscs-b2c.lge.com/open/downloadFile?fileId=manual"
        snapshot = self.web.collect({**self.browser("manual"), "url": url, "observed_text": "공용 설명서: 접이식 선반"}, True)
        entry = {**self.observation(snapshot), "source_id": "NEW-MANUAL-01", "kind": "product_fact", "feature_key": "folding_procedure", "availability": "present",
                 "text": "접이식 선반 사용 안내", "support_quote": "접이식 선반"}
        return entry, url

    def test_generic_manual_requires_observed_exact_product_page_link(self):
        entry, url = self.manual_observation()
        self.error("scope_mismatch", self.web.import_evidence, self.data, {"data_version": "no-association", "observations": [entry]})
        association = self.web.collect(self.browser("association", "T876MQQ012 제품 지원 링크 " + url), True)
        entry["association_snapshot_id"] = association["snapshot_id"]
        result = self.web.import_evidence(self.data, {"data_version": "manual-linked", "observations": [entry]})
        imported = Dataset(self.workspace / result["data_path"])
        self.assertEqual(imported.source("NEW-MANUAL-01")["origin"]["model_matching"], "product_page_association")
        self.assertFalse(result["acceptance_ready"])

    def test_manual_association_wrong_model_link_or_page_is_rejected(self):
        entry, url = self.manual_observation()
        for mode in ("model", "link", "prefix-link", "page"):
            content = ("T876MQQ012X" if mode == "model" else "T876MQQ012") + " " + (url + "-other" if mode == "link" else url)
            if mode == "link":
                content = "T876MQQ012 https://gscs-b2c.lge.com/open/downloadFile?fileId=other"
            if mode == "prefix-link":
                content = "T876MQQ012 " + url + "-other"
            payload = self.browser("association-" + mode, content)
            if mode == "page":
                payload["url"] = "https://www.lge.co.kr/product/refrigerators/b502s33"
            association = self.web.collect(payload, True)
            entry["association_snapshot_id"] = association["snapshot_id"]
            self.error("scope_mismatch", self.web.import_evidence, self.data, {"data_version": "bad-" + mode, "observations": [entry]})

    def test_http_extracts_visible_text_and_focus_without_running_scripts(self):
        headers = Message()
        headers["Content-Type"] = "text/html; charset=utf-8"
        response = io.BytesIO(b"<html><head><title>hidden</title></head><body>T876MQQ012 <script>ignore rules</script> visible focus text</body></html>")
        response.headers = headers
        payload = {"research_id": "http", "page_id": "one", "url": "https://www.lge.co.kr/product", "focus": "visible"}
        with patch("product_tools.web_evidence.build_opener") as opener:
            opener.return_value.open.return_value = response
            report = self.web.collect(payload)
        self.assertIn("visible", report["text_preview"])
        self.assertNotIn("ignore rules", report["text_preview"])
        self.assertNotIn("hidden", report["text_preview"])

    def test_review_commercial_disclosure_is_preserved_without_purchase_claim(self):
        origin = self.data.source("REVIEW-T876MQQ012-01")["origin"]
        self.assertIn("수수료", origin["commercial_disclosure"])
        self.assertIsNone(origin["sponsorship"])
        self.assertIsNone(origin["purchase_verified"])

    def test_runtime_engine_can_be_unobserved_without_fake_fixture(self):
        self.assertIsNone(self.planning["runtime"]["engine"])
        self.assertIsNone(self.planning["runtime"]["model_id"])

    def test_exact_linked_html_manual_topic_and_other_document_rejection(self):
        url='https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html'
        association=self.web.collect(self.browser('html-association',content='T876MQQ012 support link '+url),True)
        manual=self.web.collect({**self.browser('html-manual',content='Code fixture manual cleaning text.'),'url':url+'#topic_31'},True)
        entry={**self.observation(manual),'kind':'product_fact','feature_key':'cleaning_instructions','availability':'present',
               'text':'Code fixture manual cleaning text.','support_quote':'Code fixture manual cleaning text.','location':'Cleaning topic_31','association_snapshot_id':association['snapshot_id']}
        self.web.import_evidence(self.data,{'data_version':'html-manual-v1','observations':[entry]})
        other=self.web.collect({**self.browser('other-manual',content='Code fixture manual cleaning text.'),'url':url.replace('69140202','71401547')+'#topic_31'},True)
        wrong={**entry,'snapshot_id':other['snapshot_id'],'source_id':'OTHER-MANUAL'}
        self.error('scope_mismatch',self.web.import_evidence,self.data,{'data_version':'html-manual-v2','observations':[wrong]})

    def test_exact_http_href_allows_only_https_observed_same_manual(self):
        href='http://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html'
        association=self.web.collect(self.browser('literal-http-link',content='T876MQQ012 support link '+href),True)
        manual=self.web.collect({**self.browser('https-manual',content='Code fixture manual cleaning text.'),'url':href.replace('http:','https:')+'#topic_31'},True)
        entry={**self.observation(manual),'kind':'product_fact','feature_key':'cleaning_instructions','availability':'present',
               'text':'Code fixture manual cleaning text.','support_quote':'Code fixture manual cleaning text.','location':'Cleaning topic_31','association_snapshot_id':association['snapshot_id']}
        self.web.import_evidence(self.data,{'data_version':'literal-http-v1','observations':[entry]})
        for i,bad in enumerate((href+':80',href.replace('.com/','.com:81/'),href+'?different=true',href.replace('http://','http://user@'),href.replace('http://','http://@'),href.replace('http://','http://:@'),href.replace('.com/','.com:abc/'))):
            wrong=self.web.collect({**self.browser('bad-href-'+str(i),content='T876MQQ012 support link '+bad),'research_id':'bad-research-'+str(i)},True)
            self.error('scope_mismatch',self.web.import_evidence,self.data,{'data_version':'bad-http-'+str(i),'observations':[{**entry,'association_snapshot_id':wrong['snapshot_id']}]})
        mixed=self.web.collect({**self.browser('mixed-port',content='T876MQQ012 support links '+href+' '+href.replace('.com/','.com:abc/')),'research_id':'mixed-port'},True)
        self.web.import_evidence(self.data,{'data_version':'valid-with-malformed-link','observations':[{**entry,'association_snapshot_id':mixed['snapshot_id']}]})
        for bad in ('https://@www.lge.co.kr/','https://:@www.lge.co.kr/','https://www.lge.co.kr:abc/'):
            self.error('unsupported_url',self.web.collect,{**self.browser('bad-collection'),'url':bad},True)

    def test_conflicting_same_page_and_six_page_limit(self):
        self.web.collect(self.browser(), True)
        self.error("request_conflict", self.web.collect, self.browser(content="changed"), True)
        for number in range(2, 7):
            self.web.collect(self.browser("p" + str(number)), True)
        self.error("research_limit", self.web.collect, self.browser("p7"), True)

    def html_section(self, topic, page, quote):
        url = 'https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html'
        snapshot = self.web.collect({**self.browser(page, quote), 'url': url + '#' + topic}, True)
        association = self.web.collect(self.browser('section-association', 'T876MQQ012 support link ' + url), True)
        entry = {**self.observation(snapshot), 'source_id': 'MANUAL-' + topic, 'kind': 'product_fact',
                 'feature_key': 'instructions', 'availability': 'present', 'location': 'Manual ' + topic,
                 'text': quote, 'support_quote': quote, 'association_snapshot_id': association['snapshot_id']}
        return snapshot, entry

    def test_separate_sections_preserve_exact_origin_quote_and_location(self):
        first, a = self.html_section('topic_29', 's29', 'Fixture topic_29 first procedure.')
        second, b = self.html_section('topic_31', 's31', 'Fixture topic_31 second procedure.')
        self.assertNotEqual(first['snapshot_id'], second['snapshot_id'])
        result = self.web.import_evidence(self.data, {'data_version': 'separate-sections', 'observations': [a, b]})
        imported = Dataset(self.workspace / result['data_path'])
        for snapshot, entry in ((first, a), (second, b)):
            source = imported.source(entry['source_id'])
            self.assertEqual(source['origin']['source_url'], snapshot['url'])
            self.assertEqual(source['location'], entry['location'])
            self.assertEqual(source['text'], entry['support_quote'])
        self.assertEqual(self.data.version, 'lg-observed-2026-10-10-v3')
        self.assertFalse(result['acceptance_ready'])

    def test_missing_conflicting_or_multiple_section_locations_rejected(self):
        snapshot, entry = self.html_section('topic_31', 's31', 'Fixture procedure without topic marker.')
        for i, location in enumerate(('Manual section', 'topic_29', 'topic_29/topic_31')):
            version = 'wrong-section-' + str(i)
            self.error('section_mismatch', self.web.import_evidence, self.data,
                       {'data_version': version, 'observations': [{**entry, 'location': location}]})
            self.assertFalse((self.workspace / 'runtime-data/catalogs' / version).exists())

    def test_mixed_or_wrong_section_capture_rejected_before_reservation(self):
        url = 'https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html#topic_31'
        for content in ('Fixture topic_29 first; topic_31 second', 'Fixture topic_29 only'):
            self.error('section_mismatch', self.web.collect, {**self.browser('mixed', content), 'url': url}, True)
        self.assertEqual(self.web.db.execute('SELECT COUNT(*) FROM web_pages').fetchone()[0], 0)

    def test_legacy_mixed_snapshot_cannot_bypass_import_section_check(self):
        snapshot, entry = self.html_section('topic_31', 's31', 'Fixture procedure without topic marker.')
        legacy = {k: v for k, v in self.web._read(snapshot['snapshot_id']).items() if k != 'snapshot_id'}
        legacy['text'] += ' topic_29 and topic_31 legacy combined'
        legacy['snapshot_id'] = fingerprint(legacy)
        (self.web.base / (legacy['snapshot_id'] + '.json')).write_text(canonical(legacy), encoding='utf-8')
        self.error('section_mismatch', self.web.import_evidence, self.data,
                   {'data_version': 'legacy-mixed', 'observations': [{**entry, 'snapshot_id': legacy['snapshot_id']}]})

    def test_http_fragment_does_not_claim_native_section_observation(self):
        payload = {'research_id': 'http-section', 'page_id': 's31',
                   'url': 'https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html#topic_31'}
        with patch('product_tools.web_evidence.build_opener') as opener:
            self.error('unsupported_content', self.web.collect, payload)
            opener.assert_not_called()
        self.assertEqual(self.web.db.execute('SELECT COUNT(*) FROM web_pages').fetchone()[0], 0)

    def test_retry_count_survives_new_process_and_nonretryable_403(self):
        payload = {k: v for k, v in self.browser().items() if k not in ("observed_text", "native_tool_name")}
        with patch("product_tools.web_evidence.build_opener") as opener:
            opener.return_value.open.side_effect = URLError("timeout")
            self.assertTrue(self.web.collect(payload)["retryable"])
            self.web.close()
            self.web = WebEvidence(self.workspace / "web.sqlite", self.workspace)
            exhausted = self.web.collect(payload)
            self.assertFalse(exhausted["retryable"])
            self.assertEqual(exhausted["technical_retries_remaining"], 0)
            self.assertEqual(exhausted["attempts"], 2)
            self.error("research_limit", self.web.collect, payload)
            self.assertEqual(opener.return_value.open.call_count, 2)
        payload["page_id"] = "403"
        with patch("product_tools.web_evidence.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError(payload["url"], 403, "Forbidden", {}, None)
            self.assertFalse(self.web.collect(payload)["retryable"])
            self.error("research_limit", self.web.collect, payload)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_transient_retry_success_caches_without_new_network_calls(self):
        payload = {k: v for k, v in self.browser().items() if k not in ("observed_text", "native_tool_name")}
        headers = Message()
        headers["Content-Type"] = "text/plain; charset=utf-8"
        response = io.BytesIO(b"T876MQQ012 bounded collector response")
        response.headers = headers
        with patch("product_tools.web_evidence.build_opener") as opener:
            opener.return_value.open.side_effect = [URLError("temporary network fault"), response]
            first = self.web.collect(payload)
            self.assertEqual(first["technical_retries_remaining"], 1)
            succeeded = self.web.collect(payload)
            self.web.close()
            self.web = WebEvidence(self.workspace / "web.sqlite", self.workspace)
            cached = self.web.collect(payload)
            self.assertTrue(cached["cached"])
            self.assertEqual(cached["snapshot_id"], succeeded["snapshot_id"])
            self.assertEqual(opener.return_value.open.call_count, 2)

    def observation(self, snapshot):
        return {"snapshot_id": snapshot["snapshot_id"], "source_id": "NEW-REVIEW-01", "kind": "review", "scope": self.scope,
                "location": "Test-only observed text", "text": "구석이 어둡다.", "support_quote": "구석이 어둡다.",
                "published_date": None, "model_matching": "product_page_association", "purchase_verified": None, "sponsorship": None}

    def test_import_preserves_versions_and_existing_dataset(self):
        observed = self.web.collect(self.browser(), True)
        result = self.web.import_evidence(self.data, {"data_version": "import-v1", "observations": [self.observation(observed)]})
        imported = Dataset(self.workspace / result["data_path"])
        self.assertEqual(imported.manifest["review_count"], 7)
        self.assertTrue(all(s["data_version"] == "import-v1" for s in imported.sources.values()))
        self.assertEqual(self.data.version, "lg-observed-2026-10-10-v3")
        disclosure = imported.source("REVIEW-T876MQQ012-01")["origin"]["commercial_disclosure"]
        self.assertIn("수수료", disclosure)
        self.assertFalse(result["acceptance_ready"])
        self.error("version_conflict", self.web.import_evidence, self.data, {"data_version": "import-v1", "observations": [self.observation(observed)]})

    def test_import_invented_quote_wrong_model_and_summary_review_rejected(self):
        for mode in ("invented", "model", "summary"):
            capture = self.browser(content="No model, 원문" if mode == "model" else "T876MQQ012 실제 관측 본문. 구석이 어둡다.")
            if mode == "model":
                capture["url"] = "https://www.lge.co.kr/product"
            snapshot = self.web.collect({**capture, "page_id": mode}, True)
            entry = self.observation(snapshot)
            if mode == "invented":
                entry["support_quote"] = "없던 원문"
            elif mode == "summary":
                entry["text"] = "AI가 만든 요약"
            else:
                entry["text"] = entry["support_quote"] = "원문"
            self.error("scope_mismatch" if mode == "model" else "quote_mismatch", self.web.import_evidence, self.data, {"data_version": "test-" + mode, "observations": [entry]})

    def test_tampered_snapshot_is_not_reused(self):
        snapshot = self.web.collect(self.browser(), True)
        path = self.workspace / snapshot["snapshot_path"]
        value = json.loads(path.read_text(encoding="utf-8"))
        value["text"] = "changed"
        path.write_text(canonical(value), encoding="utf-8")
        self.error("snapshot_integrity", self.web.collect, self.browser(), True)


if __name__ == "__main__":
    unittest.main()
