"""Synthetic publisher-fragment contract fixtures, never customer evidence."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.bulk_import import BulkImporter
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.dataset import Dataset
from product_tools.web_evidence import WebEvidence
from product_tools.workflow import WorkflowAudit


class ProductPageFragmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.web = WebEvidence(self.workspace / "fixture.sqlite", self.workspace)
        self.addCleanup(self.web.close)
        self.web.db.execute("CREATE TABLE conversation_requests(session_id TEXT,request_key TEXT,turn_id TEXT)")
        self.web.db.executemany("INSERT INTO conversation_requests VALUES(?,?,NULL)",
                               [("fixture", "original"), ("fixture", "foreign")])
        self.web.db.commit()
        self.research = "research-" + fingerprint(["fixture", "original"])
        self.foreign = "research-" + fingerprint(["fixture", "foreign"])
        WorkflowAudit(self.web.db, self.workspace).start(self.research)
        self.web.db.commit()
        self.web.configure({"research_id": self.research, "max_pages": 30,
                            "reason": "Synthetic contract fixtures only"})
        self.empty = Dataset(ROOT / "data/business/empty")
        self.scope = {"model_id": "FX900.CKOR", "model_version": "unspecified", "document_version": "fixture-document-v1"}
        self.url = "https://publisher.example.org/product/fx900?sku=FX900.CKOR&variant=A"
        self.identity_text = "FX900.CKOR manufacturer FixtureCo; synthetic document identity."
        self.identity = self.capture("identity", self.identity_text)
        self.identity_entry = self.observation(self.identity, self.identity_text, "IDENTITY", matching="explicit_model_verified")
        self.identity_entry["feature_key"] = "product_identity"
        self.model = {**self.scope, "name": "Synthetic contract product", "product_family": "fixture",
                      "synthetic": False, "spec_source_id": "IDENTITY",
                      "identity_review": {"source_id": "IDENTITY", "manufacturer": "FixtureCo",
                                          "authority": "manufacturer", "rationale": "Contract fixture, not actual business data"}}
        initial = self.web.import_evidence(self.empty, {"data_version": "fixture-identity",
            "research_id": self.research, "new_models": [self.model], "observations": [self.identity_entry]})
        self.data = Dataset(self.workspace / initial["data_path"])
        self.body = "Synthetic FAQ: feature behavior may differ by model; check the applicable manual."

    def capture(self, page, body, url=None, research=None):
        return self.web.collect({"research_id": research or self.research, "page_id": page,
            "url": url or self.url, "observed_text": body,
            "native_tool_name": "synthetic contract fixture; no browser or HTTP"}, True)

    def observation(self, snapshot, body, source="FRAGMENT", matching="product_page_association"):
        return {"snapshot_id": snapshot["snapshot_id"], "source_id": source, "kind": "product_fact",
                "scope": self.scope, "location": "Synthetic document section", "text": body, "support_quote": body,
                "published_date": None, "model_matching": matching, "purchase_verified": None, "sponsorship": None,
                "feature_key": "fixture_feature", "availability": "present"}

    def payload(self, fragment=None, association=None):
        fragment = fragment or self.capture("fragment", self.body)
        entry = self.observation(fragment, self.body)
        entry["association_snapshot_id"] = (association or self.identity)["snapshot_id"]
        return {"data_version": "fixture-fragments", "research_id": self.research, "observations": [entry]}

    def error(self, code, payload, data=None):
        with self.assertRaises(ToolError) as caught:
            self.web.import_evidence(data or self.data, payload)
        self.assertEqual(caught.exception.code, code)
        self.assertFalse((self.workspace / "runtime-data/catalogs" / payload["data_version"]).exists())

    def replace_fixture_time(self, snapshot, when, page):
        # Negative fixture fault injection, not a production observation replay.
        value = self.web._read(snapshot["snapshot_id"])
        value.pop("snapshot_id")
        value["observed_at"] = when
        sid = fingerprint(value)
        value["snapshot_id"] = sid
        (self.web.base / (sid + ".json")).write_text(canonical(value), encoding="utf-8")
        self.web.db.execute("UPDATE web_pages SET snapshot_id=? WHERE research_id=? AND page_id=?",
                            (sid, self.research, page))
        self.web.db.commit()
        return {"snapshot_id": sid}

    def test_three_literal_fragments_keep_warning_body_url_and_audit(self):
        entries = []
        for n, body in enumerate([self.body, "Synthetic output specification: 1000 W.",
                                  "Synthetic default setting note; applicability unverified."]):
            entry = self.observation(self.capture("fragment-" + str(n), body), body, "FACT-" + str(n))
            entry["association_snapshot_id"] = self.identity["snapshot_id"]
            entries.append(entry)
        payload = {"data_version": "fixture-three", "research_id": self.research, "observations": entries}
        result = self.web.import_evidence(self.data, payload)
        registered = Dataset(self.workspace / result["data_path"])
        for entry in entries:
            record = registered.source(entry["source_id"])
            self.assertEqual(record["text"], entry["text"])
            self.assertEqual(record["sha256"], hashlib.sha256(entry["text"].encode()).hexdigest())
            self.assertEqual(record["origin"]["source_url"], self.url)
            self.assertEqual(record["origin"]["model_matching"], "product_page_association")
        audit = json.loads((registered.root / "import-audit.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["input"], payload)
        self.assertEqual(len(audit["product_page_fragment_checks"]), 3)
        self.assertTrue(all(r["identity_source_sha256"] == self.data.source("IDENTITY")["sha256"]
                            for r in audit["product_page_fragment_checks"]))
        self.assertFalse(result["acceptance_ready"])
        self.assertEqual(result["semantic_status"], "unverified")
        self.assertEqual(self.empty.manifest["fact_count"], 0)

    def test_bulk_identity_first_preserves_originals_and_all_fragments(self):
        fragment = self.capture("bulk-fragment", self.body)
        entry = self.observation(fragment, self.body)
        entry["association_snapshot_id"] = self.identity["snapshot_id"]
        original = {"data_version": "fixture-bulk", "research_id": self.research,
                    "new_models": [self.model], "observations": [entry, self.identity_entry]}
        path = self.workspace / "runtime-data/bulk-original.json"
        path.write_text(canonical(original), encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result = BulkImporter(self.web).run(self.empty,
            {"input_path": "runtime-data/bulk-original.json", "import_key": "fixture-bulk"})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_count"], 2)
        self.assertEqual(result["input_sha256"], digest)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        final = Dataset(self.workspace / result["last_valid_catalog"])
        self.assertEqual(final.source("FRAGMENT")["text"], self.body)
        self.assertEqual(final.manifest["fact_count"], 2)

    def test_missing_association_does_not_infer_identity_from_URL(self):
        payload = self.payload()
        payload["observations"][0].pop("association_snapshot_id")
        self.error("scope_mismatch", payload)

    def test_unregistered_identity_cannot_be_declared_with_same_import(self):
        payload = self.payload()
        payload["new_models"] = [self.model]
        payload["observations"].append(self.identity_entry)
        self.error("scope_mismatch", payload, self.empty)

    def test_query_anchor_and_query_order_variations_fail_even_with_literal_href(self):
        for i, url in enumerate([self.url.replace("variant=A", "variant=B"), self.url + "#spec",
                                 self.url.replace("sku=FX900.CKOR&variant=A", "variant=A&sku=FX900.CKOR")]):
            with self.subTest(url=url):
                association = self.capture("association-" + str(i), self.identity_text + "\n" + url)
                fragment = self.capture("variant-" + str(i), self.body, url)
                self.error("scope_mismatch", self.payload(fragment, association))

    def test_same_observed_anchor_is_allowed_when_registered_identity_has_it(self):
        scoped = {**self.scope, "model_id": "FX901.CKOR"}
        url = self.url.replace("FX900", "FX901").replace("fx900", "fx901") + "#spec"
        body = "FX901.CKOR manufacturer FixtureCo; synthetic anchored identity."
        identity = self.capture("anchored-identity", body, url)
        identity_entry = self.observation(identity, body, "ANCHORED-ID", "explicit_model_verified")
        identity_entry.update(scope=scoped, feature_key="product_identity")
        model = {**self.model, **scoped, "spec_source_id": "ANCHORED-ID",
                 "identity_review": {**self.model["identity_review"], "source_id": "ANCHORED-ID"}}
        seed = self.web.import_evidence(self.data, {"data_version": "fixture-anchor-identity",
            "research_id": self.research, "observations": [identity_entry], "new_models": [model]})
        fragment = self.capture("anchored-fragment", self.body, url)
        payload = self.payload(fragment, identity)
        payload["observations"][0]["scope"] = scoped
        result = self.web.import_evidence(Dataset(self.workspace / seed["data_path"]), payload)
        self.assertEqual(Dataset(self.workspace / result["data_path"]).source("FRAGMENT")["origin"]["source_url"], url)

    def test_different_path_prefix_is_not_same_document(self):
        fragment = self.capture("child-path", self.body, self.url.replace("/fx900?", "/fx900/other?"))
        self.error("scope_mismatch", self.payload(fragment))

    def test_same_host_other_model_and_exact_scope_are_not_interchangeable(self):
        for i, changed in enumerate([{"model_id": "FX900I.CKOR"}, {"model_version": "revision2"},
                                     {"document_version": "other-document"}]):
            payload = self.payload(self.capture("scope-" + str(i), self.body))
            payload["observations"][0]["scope"] = {**self.scope, **changed}
            self.error("unknown_model" if "model_id" in changed else "unknown_scope", payload)
        wrong = self.capture("wrong-model-identity", "FX900I.CKOR manufacturer FixtureCo.")
        self.error("scope_mismatch", self.payload(association=wrong))

    def test_identity_requires_registered_literal_not_only_model_token(self):
        declared = self.capture("declared-identity", "FX900.CKOR is declared to apply here.")
        self.error("scope_mismatch", self.payload(association=declared))
        self.data.sources["IDENTITY"]["text"] += " altered"
        self.error("scope_mismatch", self.payload())

    def test_explicit_verified_or_review_cannot_use_product_fragment_path(self):
        for matching in ["explicit_model_verified"]:
            payload = self.payload()
            payload["observations"][0]["model_matching"] = matching
            self.error("scope_mismatch", payload)
        payload = self.payload()
        payload["observations"][0]["kind"] = "review"
        payload["observations"][0].pop("feature_key")
        payload["observations"][0].pop("availability")
        self.error("workflow_review_audit_missing", payload)

    def test_foreign_or_unbound_research_snapshots_fail(self):
        fragment = self.capture("foreign-fragment", self.body, research=self.foreign)
        self.error("workflow_snapshot_scope", self.payload(fragment))
        foreign_identity = self.capture("foreign-identity", self.identity_text, research=self.foreign)
        self.error("workflow_snapshot_scope", self.payload(association=foreign_identity))
        payload = self.payload()
        payload.pop("research_id")
        self.error("workflow_snapshot_scope", payload)

    def test_old_future_and_after_deadline_observation_times_fail(self):
        started = datetime.fromisoformat(WorkflowAudit(self.web.db, self.workspace).status(self.research)["started_at"])
        for i, when in enumerate([started - timedelta(seconds=1), datetime.now(timezone.utc) + timedelta(seconds=60),
                                  started + timedelta(seconds=1801)]):
            page = "time-" + str(i)
            fragment = self.capture(page, self.body)
            injected = self.replace_fixture_time(fragment, when.isoformat(), page)
            self.error("workflow_snapshot_time", self.payload(injected))

    def test_snapshot_and_quote_tampering_fail_without_catalog_creation(self):
        for field in ["text", "url", "observed_at"]:
            page = "tamper-" + field
            fragment = self.capture(page, self.body)
            path = self.web.base / (fragment["snapshot_id"] + ".json")
            value = json.loads(path.read_text(encoding="utf-8"))
            value[field] += " altered"
            path.write_text(canonical(value), encoding="utf-8")
            self.error("snapshot_integrity", self.payload(fragment))
        payload = self.payload()
        payload["observations"][0]["support_quote"] = "Synthetic fabricated quote."
        self.error("quote_mismatch", payload)

    def test_other_identity_source_cannot_replace_model_spec_source(self):
        alternate = self.capture("other-source", "FX900.CKOR secondary fact, not registered identity.")
        entry = self.observation(alternate, self.web._read(alternate["snapshot_id"])["text"], "SECONDARY")
        seeded = self.web.import_evidence(self.data, {"data_version": "fixture-secondary",
            "research_id": self.research, "observations": [entry]})
        self.error("scope_mismatch", self.payload(association=alternate), Dataset(self.workspace / seeded["data_path"]))

    def test_manual_chain_marker_cannot_bypass_fragment_policy(self):
        payload = self.payload()
        payload["observations"][0]["manual_linkage_snapshot_ids"] = []
        self.error("scope_mismatch", payload)

    def test_identity_authority_and_registered_source_binding_are_required(self):
        for i, changed in enumerate([{"authority": "retailer"}, {"source_id": "DECLARED-IDENTITY"}]):
            payload = self.payload(self.capture("authority-" + str(i), self.body))
            original = self.data.models[0]["identity_review"]
            self.data.models[0]["identity_review"] = {**original, **changed}
            try:
                self.error("scope_mismatch", payload)
            finally:
                self.data.models[0]["identity_review"] = original


if __name__ == "__main__":
    unittest.main()
