"""Real-request collection budgets and snapshot-backed context boundaries."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.web_evidence import WebEvidence


class ResearchContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.web = WebEvidence(self.root / "test.sqlite", self.root)
        self.web.db.execute("CREATE TABLE conversation_requests(session_id TEXT,request_key TEXT)")
        self.web.db.execute("INSERT INTO conversation_requests VALUES('actual','request')")
        self.web.db.commit()
        self.research = "research-" + fingerprint(["actual", "request"])

    def tearDown(self):
        self.web.close()
        self.temp.cleanup()

    def capture(self, page, research=None, text="2024 households 8.04 million"):
        return self.web.collect({"research_id": research or self.research, "page_id": page,
            "url": "https://example.org/source", "observed_text": text,
            "native_tool_name": "fixture_native"}, browser=True)

    def error(self, code, operation, *args):
        with self.assertRaises(ToolError) as caught:
            operation(*args)
        self.assertEqual(caught.exception.code, code)

    def context(self, snapshot):
        return {"research_id": self.research, "sources": [{"id": "market", "snapshot_id": snapshot["snapshot_id"],
            "kind": "market", "title": "Household context", "quote": "8.04 million", "location": "Table 1",
            "subject": "General households", "scope_note": "Context only, not target demand"}]}

    def test_budget_amendment_keeps_attempts_keys_and_history_after_restart(self):
        for i in range(6):
            self.capture("page" + str(i))
        self.error("research_limit", self.capture, "page6")
        budget = {"research_id": self.research, "max_pages": 8, "reason": "Read exact manuals and context"}
        first = self.web.configure(budget)
        self.assertEqual(first["attempted_pages"], 6)
        self.assertTrue(self.web.configure(budget)["reused"])
        self.web.close()
        self.web = WebEvidence(self.root / "test.sqlite", self.root)
        self.capture("page6")
        self.error("request_conflict", self.capture, "page0", None, "changed")
        self.error("research_limit", self.web.configure, {**budget, "max_pages": 6})
        self.web.configure({**budget, "max_pages": 10, "reason": "Additional distinct primary sources"})
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_pages").fetchone()[0], 7)
        self.assertEqual(self.web.db.execute("SELECT COUNT(*) FROM web_research_budgets").fetchone()[0], 2)
        self.error("research_not_registered", self.web.configure, {**budget, "research_id": "invented"})
        for value in (True, 5, 100001):
            self.error("invalid_input", self.web.configure, {**budget, "max_pages": value})

    def test_context_is_exact_quote_of_same_request_and_retains_scope_origin(self):
        snapshot = self.capture("source")
        context = self.context(snapshot)
        records = self.web.report_sources(context, self.research)
        self.assertEqual(records[0]["text"], "8.04 million")
        self.assertEqual(records[0]["url"], "https://example.org/source")
        self.assertFalse(records[0]["synthetic"])
        self.assertIn("not target demand", records[0]["model"])
        self.assertIn(snapshot["observed_at"], records[0]["model"])
        wrong = copy.deepcopy(context)
        wrong["sources"][0]["quote"] = "invented statistic"
        self.error("report_source_integrity", self.web.report_sources, wrong, self.research)
        wrong["sources"][0]["quote"] = "8.04 million"
        wrong["sources"][0]["kind"] = "review"
        self.error("invalid_report_sources", self.web.report_sources, wrong, self.research)
        self.error("report_source_scope", self.web.report_sources, context, "another-request")
        foreign = self.capture("foreign", "another-request", "Foreign observed statistic")
        context["sources"][0].update(snapshot_id=foreign["snapshot_id"], quote="Foreign observed statistic")
        self.error("report_source_scope", self.web.report_sources, context, self.research)

    def test_unjournaled_or_tampered_snapshot_is_rejected(self):
        snapshot = self.capture("source")
        context = self.context(snapshot)
        path = self.web.base / (snapshot["snapshot_id"] + ".json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["text"] += " altered"
        path.write_text(canonical(raw), encoding="utf-8")
        self.error("snapshot_integrity", self.web.report_sources, context, self.research)

    def test_other_lg_manual_family_preserves_section_boundary(self):
        url = "https://gscs-manual.lge.com/CVZ/MFL68822525/ko-kr/main.html#topic_20"
        payload = {"research_id": self.research, "page_id": "manual", "url": url,
                   "observed_text": "Fixture topic_20 operation", "native_tool_name": "fixture_native"}
        snapshot = self.web.collect(payload, True)
        context = self.context(snapshot)
        context["sources"][0].update(kind="product_document", quote="Fixture topic_20 operation", location="topic_20")
        self.web.report_sources(context, self.research)
        context["sources"][0]["location"] = "topic_21"
        self.error("section_mismatch", self.web.report_sources, context, self.research)
        self.error("section_mismatch", self.web.collect, {**payload, "page_id": "mixed", "observed_text": "topic_20 and topic_21"}, True)

    def test_manual_landing_has_no_topic_but_topic_location_still_rejected(self):
        url = "https://gscs-manual.lge.com/CVZ/MFL68822525/ko-kr/main.html"
        snapshot = self.web.collect({"research_id": self.research, "page_id": "cover", "url": url,
            "observed_text": "Fixture MWJ25E applicable model", "native_tool_name": "fixture_native"}, True)
        context = self.context(snapshot)
        context["sources"][0].update(kind="product_document", quote="MWJ25E applicable model", location="Applicable models")
        self.web.report_sources(context, self.research)
        context["sources"][0]["location"] = "topic_20"
        self.error("section_mismatch", self.web.report_sources, context, self.research)

    def test_model_specific_manufacturer_support_binds_actual_manual_link(self):
        product = "https://www.lge.co.kr/microwaves-and-ovens/mwj25e"
        support = "https://www.lge.co.kr/support/product-MWJ25E"
        manual = "https://gscs-b2c.lge.com/open/downloadFile?fileId=fixture"
        association = self.web.collect({"research_id": self.research, "page_id": "support", "url": support,
            "observed_text": "MWJ25E manual " + manual, "native_tool_name": "fixture_native"}, True)
        snapshot = self.web.collect({"research_id": self.research, "page_id": "manual", "url": manual,
            "observed_text": "Fixture manual body", "native_tool_name": "fixture_native"}, True)
        entry = {"kind": "product_fact", "model_matching": "product_page_association", "association_snapshot_id": association["snapshot_id"]}
        self.web._check_manual_association(entry, snapshot, {"model_id": "MWJ25E"}, [product])
        wrong = self.web.collect({"research_id": self.research, "page_id": "wrong-support", "url": support.replace("MWJ25E", "MWJ25EI"),
            "observed_text": "MWJ25E manual " + manual, "native_tool_name": "fixture_native"}, True)
        self.error("scope_mismatch", self.web._check_manual_association, {**entry, "association_snapshot_id": wrong["snapshot_id"]}, snapshot, {"model_id": "MWJ25E"}, [product])

    def test_review_popup_preserves_model_less_quote_and_product_id_boundary(self):
        parent = "https://www.lge.co.kr/product/refrigerators/b502s33?modelId=MD123&pdpType=PURCHASE"
        child = "https://www.lge.co.kr/mkt/review/MD123/pdpReviewListPopup"
        association = self.web.collect({"research_id": self.research, "page_id": "parent", "url": parent,
            "observed_text": "B502S33 clicked reviews: " + child, "native_tool_name": "fixture_native"}, True)
        snapshot = self.web.collect({"research_id": self.research, "page_id": "popup", "url": child,
            "observed_text": "Fixture freezer is narrow", "native_tool_name": "fixture_native"}, True)
        entry = {"kind": "review", "model_matching": "product_page_association", "association_snapshot_id": association["snapshot_id"]}
        self.web._check_review_association(entry, snapshot, {"model_id": "B502S33"}, [parent])
        self.assertNotIn("B502S33", self.web._read(snapshot["snapshot_id"])["text"])
        bad = self.web.collect({"research_id": self.research, "page_id": "bad-parent", "url": parent,
            "observed_text": "B502S33 clicked reviews: " + child.replace("MD123", "MD456"), "native_tool_name": "fixture_native"}, True)
        other = self.web.collect({"research_id": self.research, "page_id": "other-popup", "url": child.replace("MD123", "MD456"),
            "observed_text": "Fixture freezer is narrow", "native_tool_name": "fixture_native"}, True)
        self.error("scope_mismatch", self.web._check_review_association, {**entry, "association_snapshot_id": bad["snapshot_id"]}, other, {"model_id": "B502S33"}, [parent])

    def test_tracking_ids_and_missing_product_id_cannot_link_other_model_review(self):
        self.web.configure({"research_id": self.research, "max_pages": 10, "reason": "Additional negative identity cases"})
        for i, (parent, child) in enumerate((
            ("https://www.lge.co.kr/refrigerators/b502s33?modelId=MD123&campaignId=SPRING", "https://www.lge.co.kr/review/MD456?campaignId=SPRING"),
            ("https://www.lge.co.kr/refrigerators/b502s33", "https://www.lge.co.kr/review/MD456"),
            ("https://www.lge.co.kr/refrigerators/b502s33?modelId=MD123", "https://www.lge.co.kr/review/MD123?modelId=MD456"),
            ("https://www.lge.co.kr/refrigerators/b502s33?modelId=MD123", "https://www.lge.co.kr/mkt/review/MD456/pdpReviewListPopup?modelId=MD123"),
        )):
            association = self.web.collect({"research_id": self.research, "page_id": "parent" + str(i), "url": parent,
                "observed_text": "B502S33 clicked reviews: " + child, "native_tool_name": "fixture_native"}, True)
            snapshot = self.web.collect({"research_id": self.research, "page_id": "child" + str(i), "url": child,
                "observed_text": "Fixture other product review", "native_tool_name": "fixture_native"}, True)
            entry = {"kind": "review", "model_matching": "product_page_association", "association_snapshot_id": association["snapshot_id"]}
            self.error("scope_mismatch", self.web._check_review_association, entry, snapshot, {"model_id": "B502S33"}, [parent])


if __name__ == "__main__":
    unittest.main()
