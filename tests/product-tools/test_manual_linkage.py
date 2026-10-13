"""Publisher-route contract fixtures; these are not customer or native AI data."""
import copy
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
from product_tools.web_evidence import WebEvidence, check_manual_section
from product_tools.workflow import WorkflowAudit


class ManualLinkageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.web = WebEvidence(self.workspace / "web.sqlite", self.workspace)
        self.web.db.execute("CREATE TABLE conversation_requests(session_id TEXT,request_key TEXT,turn_id TEXT)")
        self.web.db.execute("INSERT INTO conversation_requests VALUES('fixture','original',NULL)")
        self.web.db.commit()
        self.research = "research-" + fingerprint(["fixture", "original"])
        self.web.configure({"research_id": self.research, "max_pages": 30, "reason": "Synthetic contract fixture only"})
        self.data = Dataset(ROOT / "data/business/empty")
        self.scope = {"model_id": "FIXTURE100", "model_version": "unspecified", "document_version": "observed-20261013-manual-rev06"}
        self.root = "https://gscs-manual.lge.com/CVZ/MFL99999999/ko-kr/"
        self.main = self.root + "main.html"
        self.child = self.root + "topics/topic_20.html"
        self.loader = "https://gscs-manual.lge.com/assets/script.js"
        self.indexer = self.root + "res/js/indexer.js"
        self.index_raw = ('<meta id="PartNo" name="PartNo" content="MFL99999999">'
                          '<meta id="Rev" name="Rev" content="06">'
                          '<meta id="Language" name="Language" content="ko-kr">'
                          '<a href="#topic_20" data-uid="t_0001_r2">Section</a>'
                          '<script src="/assets/script.js"></script><script src="./res/js/indexer.js"></script>')
        self.loader_raw = ('"*":function(t){$(".content").load("topics/"+t+".html",f)};'
                           'var e=window.location.hash.substring(1);i="string"==typeof n[o]?decodeURIComponent(n[o]):n[o];')
        self.indexer_raw = 'indexer[1] = {"urlHash":`topic_20`,"topicId":`t_0001_r2`,"content":`fixture`};'
        self.child_raw = '<meta id="Topic_ID" name="Topic_ID" content="t_0001_r2"><p>Fixture section quote.</p>'
        self.original_time = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.count = 0

    def tearDown(self):
        self.web.close()
        self.temp.cleanup()

    def error(self, code, fn, *args):
        with self.assertRaises(ToolError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def raw_snapshot(self, url, raw, page=None):
        self.count += 1
        name = page or "raw-" + str(self.count)
        folder = self.workspace / "runtime-data/raw"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (name + ".txt")
        path.write_bytes(raw.encode("utf-8"))
        return self.web.collect({"research_id": self.research, "page_id": name, "url": url,
            "observed_text": raw, "native_tool_name": "synthetic contract replay; no browser execution",
            "source_literal": {"raw_path": path.relative_to(self.workspace).as_posix(),
                "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_url": url,
                "character_start": 0, "character_end": len(raw), "observed_at": self.original_time}}, True)

    def chain(self, index=None, loader=None, indexer=None, child=None):
        support = self.web.collect({"research_id": self.research, "page_id": "support", "url": "https://www.lge.co.kr/support/FIXTURE100",
            "observed_text": "FIXTURE100 manufacturer fixture " + self.main.replace("https:", "http:"),
            "native_tool_name": "synthetic contract fixture"}, True)
        section = self.raw_snapshot(self.child, child or self.child_raw, "child")
        parts = [self.raw_snapshot(self.main, index or self.index_raw, "index"),
                 self.raw_snapshot(self.loader, loader or self.loader_raw, "loader"),
                 self.raw_snapshot(self.indexer, indexer or self.indexer_raw, "indexer")]
        common = {"kind": "product_fact", "scope": self.scope, "published_date": None,
                  "model_matching": "product_page_association", "purchase_verified": None, "sponsorship": None,
                  "feature_key": "identity", "availability": "present"}
        identity = {**common, "source_id": "FIXTURE-IDENTITY", "snapshot_id": support["snapshot_id"], "location": "manufacturer fixture",
                    "text": "FIXTURE100 manufacturer fixture", "support_quote": "FIXTURE100 manufacturer fixture"}
        manual = {**common, "source_id": "FIXTURE-MANUAL", "snapshot_id": section["snapshot_id"], "location": "Section topic_20",
                  "text": "Fixture section quote.", "support_quote": "Fixture section quote.",
                  "association_snapshot_id": support["snapshot_id"], "manual_linkage_snapshot_ids": [p["snapshot_id"] for p in parts]}
        model = {**self.scope, "name": "Synthetic contract fixture", "product_family": "fixture", "synthetic": False,
                 "spec_source_id": identity["source_id"], "identity_review": {"source_id": identity["source_id"], "manufacturer": "LG",
                     "authority": "manufacturer", "rationale": "Synthetic contract fixture only; not business data"}}
        return {"data_version": "fixture-linked", "research_id": self.research, "observations": [identity, manual], "new_models": [model]}

    def test_import_preserves_direct_url_original_time_and_verified_chain_audit(self):
        payload = self.chain()
        result = self.web.import_evidence(self.data, payload)
        source = Dataset(self.workspace / result["data_path"]).source("FIXTURE-MANUAL")
        self.assertEqual(source["origin"]["source_url"], self.child)
        snapshot = self.web._read(payload["observations"][1]["snapshot_id"])
        self.assertEqual(snapshot["observed_at"], self.original_time)
        self.assertIn("replayed_at", snapshot)
        self.assertIn("native/HTTP execution not certified", snapshot["collection"])
        audit = json.loads((self.workspace / result["data_path"] / "import-audit.json").read_text())
        self.assertEqual(audit["manual_linkage_checks"][0]["topic_id"], "t_0001_r2")
        self.assertEqual(result["semantic_status"], "unverified")
        self.assertFalse(result["acceptance_ready"])

    def test_bulk_keeps_original_linkage_ids_and_registers_identity_first(self):
        payload = self.chain()
        payload["observations"].reverse()
        path = self.workspace / "runtime-data/original.json"
        path.write_text(canonical(payload), encoding="utf-8")
        result = BulkImporter(self.web).run(self.data, {"input_path": "runtime-data/original.json", "import_key": "fixture-bulk"})
        self.assertEqual(result["status"], "completed")
        audit = json.loads((self.workspace / result["last_valid_catalog"] / "import-audit.json").read_text())
        self.assertEqual(audit["input"]["observations"][0]["manual_linkage_snapshot_ids"], payload["observations"][0]["manual_linkage_snapshot_ids"])

    def test_actual_index_revision_overrides_no_caller_proof(self):
        payload = self.chain(index=self.index_raw.replace('content="06"', 'content="07"'))
        self.error("scope_mismatch", self.web.import_evidence, self.data, payload)

    def test_actual_topic_ids_and_index_href_must_all_agree(self):
        payload = self.chain(indexer=self.indexer_raw.replace("t_0001_r2", "t_0002_r2"))
        self.error("scope_mismatch", self.web.import_evidence, self.data, payload)

    def test_coordinated_metadata_forgery_cannot_replace_retained_raw(self):
        payload = self.chain()
        for sid in [payload["observations"][1]["snapshot_id"], payload["observations"][1]["manual_linkage_snapshot_ids"][-1]]:
            path = self.web.base / (sid + ".json")
            value = json.loads(path.read_text())
            value["text"] = value["text"].replace("t_0001_r2", "t_0002_r2")
            path.write_text(canonical(value))
        self.error("snapshot_integrity", self.web.import_evidence, self.data, payload)

    def test_retained_raw_change_is_detected_again_on_import(self):
        payload = self.chain()
        (self.workspace / "runtime-data/raw/index.txt").write_text(self.index_raw.replace('content="06"', 'content="77"'))
        self.error("snapshot_integrity", self.web.import_evidence, self.data, payload)

    def test_unreferenced_loader_cannot_be_declared_at_another_url(self):
        payload = self.chain()
        changed = self.raw_snapshot(self.loader.replace("assets", "unlisted"), self.loader_raw)
        payload["observations"][1]["manual_linkage_snapshot_ids"][1] = changed["snapshot_id"]
        self.error("scope_mismatch", self.web.import_evidence, self.data, payload)

    def test_missing_components_other_manual_and_unsupported_loader_fail(self):
        payload = self.chain(loader=self.loader_raw.replace('"topics/"', '"../topics/"'))
        self.error("scope_mismatch", self.web.import_evidence, self.data, payload)
        missing = copy.deepcopy(payload)
        missing["observations"][1]["manual_linkage_snapshot_ids"].pop()
        self.error("scope_mismatch", self.web.import_evidence, self.data, missing)
        other = copy.deepcopy(payload)
        wrong = self.raw_snapshot(self.main.replace("99999999", "88888888"), self.index_raw)
        other["observations"][1]["manual_linkage_snapshot_ids"][0] = wrong["snapshot_id"]
        self.error("scope_mismatch", self.web.import_evidence, self.data, other)

    def test_same_model_suffix_is_not_inherited_from_bare_support(self):
        payload = self.chain()
        manual = payload["observations"][1]
        manual["scope"] = {**self.scope, "model_id": "FIXTURE100.AKR"}
        snapshot = self.web._read(manual["snapshot_id"])
        self.error("scope_mismatch", self.web._check_manual_association, manual, snapshot, manual["scope"], ["https://www.lge.co.kr/support/FIXTURE100"])

    def test_other_request_snapshot_missing_research_and_expired_source_time_fail(self):
        payload = self.chain()
        absent = {k: v for k, v in payload.items() if k != "research_id"}
        self.error("workflow_snapshot_scope", self.web.import_evidence, self.data, absent)
        sid = payload["observations"][1]["manual_linkage_snapshot_ids"][0]
        self.web.db.execute("UPDATE web_pages SET research_id='different-request' WHERE snapshot_id=?", (sid,))
        self.error("workflow_snapshot_scope", self.web.import_evidence, self.data, payload)
        self.web.db.execute("UPDATE web_pages SET research_id=? WHERE snapshot_id=?", (self.research, sid))
        WorkflowAudit(self.web.db, self.workspace).start(self.research)
        self.error("workflow_snapshot_time", self.web.import_evidence, self.data, payload)

    def test_direct_topic_location_and_body_mixture_are_rejected(self):
        for body, location in (("topic_21", "topic_20"), ("body", "topic_20 topic_21"), ("body", "topic_21"), ("body", "missing")):
            self.error("section_mismatch", check_manual_section, self.child, body, location)
        for url in (self.child + "#topic_20", self.child + "?topic=20"):
            self.error("section_mismatch", check_manual_section, url, "body", "topic_20")

    def test_existing_hash_and_pdf_link_behavior_remains_exact(self):
        payload = self.chain()
        entry = payload["observations"][1]
        entry.pop("manual_linkage_snapshot_ids")
        section = self.web.collect({"research_id": self.research, "page_id": "legacy-hash", "url": self.main + "#topic_20",
            "observed_text": "Fixture section quote.", "native_tool_name": "synthetic section fixture"}, True)
        entry["snapshot_id"] = section["snapshot_id"]
        self.web.import_evidence(self.data, payload)
        other = self.web._read(section["snapshot_id"])
        other["url"] = other["url"].replace("99999999", "88888888")
        self.error("scope_mismatch", self.web._check_manual_association, entry, other, self.scope, ["https://www.lge.co.kr/support/FIXTURE100"])

    def test_raw_source_url_and_exact_window_are_checked_before_replay(self):
        source = self.raw_snapshot(self.indexer, self.indexer_raw)
        saved = self.web._read(source["snapshot_id"])
        base = {"research_id": self.research, "url": self.indexer, "observed_text": self.indexer_raw,
                "native_tool_name": "synthetic fixture", "source_literal": {k: saved["source_literal"][k] for k in
                   ("raw_path", "raw_sha256", "source_url", "character_start", "character_end", "observed_at")}}
        wrong_url = copy.deepcopy(base)
        wrong_url.update(page_id="wrong-url")
        wrong_url["source_literal"]["source_url"] = self.loader
        self.error("snapshot_integrity", self.web.collect, wrong_url, True)
        wrong_text = {**base, "page_id": "wrong-text", "observed_text": self.indexer_raw.replace("t_0001_r2", "t_0002_r2")}
        self.error("snapshot_integrity", self.web.collect, wrong_text, True)


if __name__ == "__main__":
    unittest.main()
