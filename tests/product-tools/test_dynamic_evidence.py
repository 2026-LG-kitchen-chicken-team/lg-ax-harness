"""Generated code fixtures, not real product observations or native AI evaluation."""
import copy
import hashlib
import io
from email.message import Message
import json
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical
from product_tools.dataset import Dataset
from product_tools.web_evidence import (MAX_PAGE_BYTES, NoRedirect, PublicHTTPSConnection,
                                       PublicHTTPSHandler, WebEvidence, public_url)


class DynamicEvidenceTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "runtime-data")
        self.workspace = Path(self.temp.name)
        self.web = WebEvidence(self.workspace / "web.sqlite", self.workspace)
        self.empty = Dataset(ROOT / "data/business/empty")
        self.mid = "RANDOM-" + uuid4().hex[:12]
        self.exact = {"model_id": self.mid, "model_version": "unspecified", "document_version": "fixture-snapshot-20261011"}
        self.model = {**self.exact, "name": "Generated contract fixture", "product_family": "air_purifier",
                      "synthetic": False, "spec_source_id": "identity",
                      "identity_review": {"source_id": "identity", "manufacturer": "Fixture maker",
                                          "authority": "manufacturer", "rationale": "Caller declaration in code fixture; not a verified manufacturer."}}
        self.quote = "Code fixture only. Model " + self.mid + " is listed."
        snapshot = self.capture(self.quote)
        self.entry = {"snapshot_id": snapshot["snapshot_id"], "source_id": "identity", "kind": "product_fact",
                      "scope": self.exact, "location": "Fixture identity section", "text": self.quote,
                      "support_quote": self.quote, "published_date": None, "model_matching": "explicit_model_verified",
                      "purchase_verified": None, "sponsorship": None, "feature_key": "product_identity", "availability": "present"}

    def tearDown(self):
        self.web.close()
        self.assertTrue(self.workspace.resolve().is_relative_to(ROOT / "runtime-data"))
        self.temp.cleanup()

    def capture(self, text, page="identity", url="https://manufacturer.example/variable/catalog?id=observed"):
        return self.web.collect({"research_id": "fixture", "page_id": page, "url": url,
                                 "observed_text": text, "native_tool_name": "test_fixture_not_actual_browser"}, True)

    def payload(self, version="dynamic-fixture-v1"):
        return copy.deepcopy({"data_version": version, "new_models": [self.model], "observations": [self.entry]})

    def error(self, code, action, *args):
        with self.assertRaises(ToolError) as caught:
            action(*args)
        self.assertEqual(caught.exception.code, code)

    def test_empty_catalog_has_no_claims_and_rejects_unknown_scope(self):
        self.assertEqual(self.empty.models, [])
        self.assertEqual(self.empty.sources, {})
        self.assertFalse(self.empty.synthetic)
        self.assertEqual(self.empty.manifest["fact_count"], 0)
        self.error("unknown_model", self.empty.retrieve, "product_fact", self.exact)

    def test_random_model_and_open_family_register_atomically_from_observed_quote(self):
        report = self.web.import_evidence(self.empty, self.payload())
        imported = Dataset(self.workspace / report["data_path"])
        self.assertEqual(imported.models, [self.model])
        self.assertEqual((report["added_models"], report["added_sources"]), (1, 1))
        self.assertFalse(report["acceptance_ready"])
        self.assertEqual(report["semantic_status"], "unverified")
        source = imported.source("identity")
        self.assertEqual(source["text"], self.quote)
        self.assertEqual(source["sha256"], hashlib.sha256(self.quote.encode()).hexdigest())
        self.assertEqual(source["origin"]["source_url"], "https://manufacturer.example/variable/catalog?id=observed")
        self.assertEqual(imported.retrieve("review", self.exact)["status"], "empty")
        self.assertEqual(imported.retrieve("product_fact", self.exact, query=self.mid)["total"], 1)
        self.assertEqual(imported.retrieve("product_fact", self.exact, query="missing fact")["total"], 0)
        self.error("unknown_scope", imported.retrieve, "product_fact", {**self.exact, "document_version": "different"})
        self.assertEqual(imported.retrieve("product_fact", self.exact, feature_key="internal_dimensions")["feature_presence"], "not_documented")
        self.assertEqual(self.empty.models, [])

    def test_existing_catalog_is_copied_and_fingerprint_changes(self):
        first = self.web.import_evidence(self.empty, self.payload())
        original = Dataset(self.workspace / first["data_path"])
        payload = self.payload("dynamic-fixture-v2")
        payload.pop("new_models")
        payload["observations"][0]["source_id"] = "another-fact"
        second = self.web.import_evidence(original, payload)
        merged = Dataset(self.workspace / second["data_path"])
        self.assertEqual(merged.models, original.models)
        self.assertNotEqual(merged.fingerprint, original.fingerprint)
        self.assertEqual(original.source("identity")["data_version"], first["data_version"])
        self.assertTrue(all(record["data_version"] == second["data_version"] for record in merged.sources.values()))
        self.error("version_conflict", self.web.import_evidence, original, payload)

    def test_identity_source_missing_wrong_kind_scope_or_review_is_rejected(self):
        for mutation in ("missing", "kind", "scope", "review", "absent"):
            payload = self.payload("bad-" + mutation)
            if mutation == "missing":
                payload["new_models"][0]["spec_source_id"] = "missing"
                payload["new_models"][0]["identity_review"]["source_id"] = "missing"
            elif mutation == "kind":
                payload["observations"][0]["kind"] = "review"
            elif mutation == "scope":
                payload["observations"][0]["scope"]["document_version"] = "tampered"
            elif mutation == "review":
                payload["new_models"][0]["identity_review"]["source_id"] = "other"
            else:
                payload["observations"][0]["availability"] = "explicitly_absent"
            with self.subTest(mutation=mutation):
                self.error("identity_mismatch", self.web.import_evidence, self.empty, payload)
                self.assertFalse((self.workspace / "runtime-data/catalogs" / payload["data_version"]).exists())

    def test_prefix_model_url_only_and_invented_identity_quote_are_rejected(self):
        for mutation in ("prefix", "url-only", "invented", "summary"):
            quote = "No observed identity" if mutation == "url-only" else self.quote.replace(self.mid, self.mid + "X")
            snapshot = self.capture(quote, mutation, "https://manufacturer.example/" + self.mid)
            payload = self.payload("bad-" + mutation)
            entry = payload["observations"][0]
            entry["snapshot_id"] = snapshot["snapshot_id"]
            if mutation in ("prefix", "url-only"):
                entry["text"] = entry["support_quote"] = quote
            if mutation == "summary":
                entry["text"] = "AI identity summary " + self.mid
            self.error("identity_mismatch", self.web.import_evidence, self.empty, payload)

    def test_new_model_cannot_add_guessed_specs_or_unobserved_hardware_version(self):
        for field, value in (("dimensions_mm", {"width": 123, "height": 123, "depth": 123}),
                             ("capacity_l", 42), ("layout", {})):
            payload = self.payload("bad-" + field)
            payload["new_models"][0][field] = value
            self.error("invalid_input", self.web.import_evidence, self.empty, payload)
        payload = self.payload("bad-hardware-version")
        payload["new_models"][0]["model_version"] = "invented-v2"
        payload["observations"][0]["scope"]["model_version"] = "invented-v2"
        self.error("identity_mismatch", self.web.import_evidence, self.empty, payload)

    def test_duplicate_or_conflicting_registered_identity_cannot_replace_catalog(self):
        report = self.web.import_evidence(self.empty, self.payload())
        original = Dataset(self.workspace / report["data_path"])
        self.error("invalid_dataset", self.web.import_evidence, original, self.payload("duplicate"))
        payload = self.payload("conflicting")
        payload["new_models"][0]["document_version"] = "new-observation"
        payload["new_models"][0]["product_family"] = "other_family"
        self.error("identity_mismatch", self.web.import_evidence, original, payload)

    def test_missing_snapshot_and_modified_snapshot_do_not_create_catalog(self):
        payload = self.payload("missing-snapshot")
        payload["observations"][0]["snapshot_id"] = "missing"
        self.error("snapshot_not_found", self.web.import_evidence, self.empty, payload)
        self.assertFalse((self.workspace / "runtime-data/catalogs/missing-snapshot").exists())
        path = self.web.base / (self.entry["snapshot_id"] + ".json")
        value = json.loads(path.read_text(encoding="utf-8"))
        value["text"] += " tampered"
        path.write_text(canonical(value), encoding="utf-8")
        self.error("snapshot_integrity", self.web.import_evidence, self.empty, self.payload())

    def test_invalid_late_record_rolls_back_catalog_files(self):
        payload = self.payload()
        payload["observations"][0]["published_date"] = "2026-99-99"
        self.error("invalid_input", self.web.import_evidence, self.empty, payload)
        self.assertFalse((self.workspace / "runtime-data/catalogs" / payload["data_version"]).exists())

    def test_changed_capture_content_does_not_reuse_cache(self):
        self.error("request_conflict", self.capture, self.quote + " changed")
        report = self.capture(self.quote)
        self.assertTrue(report["cached"])
        self.assertIn("caller_reported", report["collection"])


class PublicCollectionTests(unittest.TestCase):
    def error(self, code, action, *args):
        with self.assertRaises(ToolError) as caught:
            action(*args)
        self.assertEqual(caught.exception.code, code)

    def test_https_public_host_is_open_and_private_literals_are_rejected(self):
        for url in ("https://manufacturer.example/anything", "https://www.lge.co.kr.evil.example/"):
            self.assertEqual(public_url(url), url)  # Allowed address format does not certify manufacturer authority.
        for url in ("http://example.com", "https://127.0.0.1", "https://10.0.0.1", "https://169.254.169.254",
                    "https://[::1]", "https://[::ffff:127.0.0.1]", "https://[fc00::1]", "https://localhost",
                    "https://example.local", "https://user:pass@example.com", "https://@example.com",
                    "https://example.com:80", "https://example.com:443x", "https://example.com\\@127.0.0.1"):
            with self.subTest(url=url):
                self.error("unsupported_url", public_url, url)

    def test_dns_private_mixed_and_mapped_answers_are_rejected_before_connect(self):
        for addresses in (("127.0.0.1",), ("8.8.8.8", "10.0.0.1"), ("::ffff:127.0.0.1",), ("169.254.1.1",)):
            connection = PublicHTTPSConnection("manufacturer.example", timeout=8)
            answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses]
            with patch("product_tools.web_evidence.socket.getaddrinfo", return_value=answers), patch("product_tools.web_evidence.socket.socket") as create:
                self.error("unsupported_url", connection.connect)
                create.assert_not_called()

    def test_dns_is_resolved_once_and_pinned_socket_keeps_tls_hostname(self):
        context = Mock()
        connection = PublicHTTPSConnection("manufacturer.example", timeout=8, context=context)
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]
        with patch("product_tools.web_evidence.socket.getaddrinfo", return_value=answers) as resolve, patch("product_tools.web_evidence.socket.socket") as create:
            connection.connect()
            self.assertEqual(resolve.call_count, 1)
            create.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM, 6)
            create.return_value.connect.assert_called_once_with(("8.8.8.8", 443))
            create.return_value.settimeout.assert_called_once_with(8)
            context.wrap_socket.assert_called_once_with(create.return_value, server_hostname="manufacturer.example")
        handler = PublicHTTPSHandler()
        self.assertEqual(handler._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(handler._context.check_hostname)
        with patch.object(handler, "do_open") as open_connection:
            handler.https_open("request-fixture")
            open_connection.assert_called_once_with(PublicHTTPSConnection, "request-fixture", context=handler._context)
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://127.0.0.1/"))

    def test_tls_validation_failure_closes_pinned_socket(self):
        context = Mock()
        context.wrap_socket.side_effect = ssl.SSLCertVerificationError("fixture hostname mismatch")
        connection = PublicHTTPSConnection("manufacturer.example", timeout=8, context=context)
        answers = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700:4700::1111", 443, 0, 0))]
        with patch("product_tools.web_evidence.socket.getaddrinfo", return_value=answers), patch("product_tools.web_evidence.socket.socket") as create:
            with self.assertRaises(ssl.SSLCertVerificationError):
                connection.connect()
            create.return_value.connect.assert_called_once_with(answers[0][4])
            create.return_value.close.assert_called_once()

    def test_http_timeout_retry_and_capture_body_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            web = WebEvidence(Path(tmp) / "web.sqlite", Path(tmp))
            payload = {"research_id": "fixture", "page_id": "timeout", "url": "https://manufacturer.example/"}
            try:
                with patch("product_tools.web_evidence.build_opener") as opener:
                    opener.return_value.open.side_effect = TimeoutError("fixture timeout")
                    self.assertTrue(web.collect(payload)["retryable"])
                    self.assertFalse(web.collect(payload)["retryable"])
                    self.error("research_limit", web.collect, payload)
                    self.assertEqual(opener.return_value.open.call_count, 2)
                    self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 8)
                self.error("invalid_input", web.collect, {**payload, "page_id": "too-large", "observed_text": "x" * 16001, "native_tool_name": "fixture"}, True)
                response = io.BytesIO(b"x" * (MAX_PAGE_BYTES + 1))
                response.headers = Message()
                response.headers["Content-Type"] = "text/plain; charset=utf-8"
                with patch("product_tools.web_evidence.build_opener") as opener:
                    opener.return_value.open.return_value = response
                    self.error("page_limit", web.collect, {**payload, "page_id": "http-size"})
                    self.error("research_limit", web.collect, {**payload, "page_id": "http-size"})
                with patch("product_tools.web_evidence.build_opener") as opener:
                    opener.return_value.open.side_effect = HTTPError(payload["url"], 302, "redirect", {}, None)
                    self.assertFalse(web.collect({**payload, "page_id": "redirect"})["retryable"])
                    self.assertEqual(opener.return_value.open.call_count, 1)
            finally:
                web.close()


if __name__ == "__main__":
    unittest.main()
