"""Synthetic plan/scan/stop contracts; never executes native or HTTP research."""
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import subprocess
import shutil
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools import research_scope as scope
from product_tools.contracts import ToolError
from product_tools.dataset import Dataset, MAX_CATALOG_FILE_BYTES
spec = importlib.util.spec_from_file_location("workflow_fixture", Path(__file__).with_name("test_product_workflow.py"))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class ResearchScopeTests(unittest.TestCase):
    record = base.ProductWorkflowTests.record
    capture = base.ProductWorkflowTests.capture
    error = base.ProductWorkflowTests.error
    scan = base.ProductWorkflowTests.scan

    def setUp(self):
        base.ProductWorkflowTests.setUp(self)
        self.store.db.execute("UPDATE product_workflows SET research_policy=? WHERE research_id=?", (scope.POLICY, self.research))

    def tearDown(self):
        base.ProductWorkflowTests.tearDown(self)

    def plan(self):
        return self.record("research_plan", {"product_name": "Synthetic generic investigation",
            "coverage": ["positive", "negative", "long_term", "conditions", "counterexamples"],
            "source_plan": ["Manufacturer documents and external review sources"],
            "goals": [{"goal_id": kind, "kind": kind, "scope_note": "Synthetic required dimension"} for kind in sorted(scope.KINDS)]}, "plan")

    def stop_data(self, **changes):
        summary = scope.summary(self.audit.events(self.research))
        return {"code": "sufficient_evidence", "basis": "Conditional caller assessment, not automatic certification",
                "new_findings": [], "remaining_scope": summary["remaining_scope"],
                "remaining_goal_ids": summary["remaining_goal_ids"],
                "limitation_basis": "Unattempted and inaccessible dimensions are disclosed; conclusions require independent review", **changes}

    def test_no_plan_scan_cannot_assert_sufficiency(self):
        self.capture("new", "Synthetic generic identity")
        self.error("workflow_goal_missing", self.record, "research_stop", self.stop_data(), "stop")
        self.assertIsNone(self.audit.status(self.research)["research_stopped_at"])

    def test_unknown_goal_and_missing_binding_have_no_event(self):
        self.plan(); snap = self.capture("new", "Synthetic exact context")
        count = len(self.audit.events(self.research))
        self.error("workflow_goal_missing", self.scan, snap, [], key="missing")
        self.error("workflow_goal_unknown", self.scan, snap, [], key="unknown", goal_ids=["unknown"])
        self.assertEqual(len(self.audit.events(self.research)), count)

    def test_plan_without_actual_scans_cannot_stop_sufficient(self):
        self.plan(); self.capture("new", "Captured but not scanned")
        self.error("workflow_goal_unobserved", self.record, "research_stop", self.stop_data(), "stop")

    def test_remaining_goal_and_next_page_cannot_be_omitted(self):
        self.plan(); snap = self.capture("new", "Synthetic context")
        self.scan(snap, [], goal_ids=["external_reviews"], remaining_scope=["Next observed review page"])
        self.error("workflow_goal_omitted", self.record, "research_stop", self.stop_data(remaining_goal_ids=[]), "omit-id")
        self.error("workflow_goal_omitted", self.record, "research_stop", self.stop_data(remaining_scope=[]), "omit-page")
        self.error("invalid_input", self.record, "research_stop", self.stop_data(limitation_basis=None), "omit-impact")

    def test_inaccessible_conditional_stop_preserves_unattempted_and_can_complete_gate(self):
        self.plan(); self.capture("new", "Only retained identity")
        self.record("source_scan", {"source_url": "https://manual.example.org/unavailable", "page_label": "Publisher manual",
            "status": "inaccessible", "reviews": [], "reason": "Synthetic access failure",
            "goal_ids": ["manual"], "source_type": "manual"}, "failure")
        result = self.record("research_stop", self.stop_data(), "stop")
        states = {g["goal_id"]:g["state"] for g in result["research_scope"]["goals"]}
        self.assertEqual(states["manual"], "inaccessible")
        self.assertEqual(states["official_spec"], "pending")
        self.audit.require_scope_disclosure(self.research)
        self.assertIn("not semantic", result["research_scope"]["scope_validation"])

    def test_fixed_catalog_and_legacy_null_keep_stop_compatibility(self):
        self.record("research_stop", {"code":"sufficient_evidence", "basis":"Fixed registered catalog reused",
            "new_findings":[], "remaining_scope":[]}, "fixed")
        self.assertFalse(self.audit.status(self.research)["research_scope"]["required"])
        other = self.conv.open_product_workflow({"question":"Legacy synthetic", "session_id":"old", "request_key":"old", "user_submitted":True})
        research = other["research_id"]
        self.store.db.execute("UPDATE product_workflows SET research_policy=NULL WHERE research_id=?", (research,))
        self.capture("old", "Legacy observation", research=research)
        self.record("research_stop", {"code":"sources_exhausted", "basis":"Historic source scope", "new_findings":[], "remaining_scope":[]}, "legacy", research)
        self.assertFalse(self.audit.scope_required(research))

    def test_goal_scope_and_identity_are_immutable(self):
        self.plan()
        self.error("workflow_goal_conflict", self.record, "research_plan", {"product_name":"Synthetic", "coverage":["positive","negative","long_term","conditions","counterexamples"],
            "source_plan":[], "goals":[{"goal_id":"manual","kind":"manual","scope_note":"Changed scope"}]}, "replace")
        snap=self.capture("new", "Synthetic")
        self.error("workflow_goal_scope", self.scan, snap, [], goal_ids=["manual"], source_type="review_list")

    def test_catalog_reads_above_one_mib_but_rejects_above_finite_limit(self):
        path=self.root/"catalog";path.mkdir()
        data=b"x"*(1024*1024+1);(path/"sources.jsonl").write_bytes(data)
        dataset=object.__new__(Dataset);dataset.root=path
        self.assertEqual(dataset._read("sources.jsonl"), data)
        with (path/"sources.jsonl").open("wb") as stream:stream.truncate(MAX_CATALOG_FILE_BYTES+1)
        self.error("dataset_limit", dataset._read, "sources.jsonl")

    def test_completed_state_gate_requires_same_request_stop_disclosure(self):
        self.capture("new", "Synthetic observed identity")
        self.store.db.execute("UPDATE conversation_requests SET turn_id=? WHERE session_id=? AND request_key=?",
                              ("scope-gate-turn", self.original["session_id"], self.original["request_key"]))
        with patch("product_tools.evidence_coverage.EvidenceCoverage.require_complete"):
            self.error("workflow_research_open", self.store.require_evidence_coverage, self.original["session_id"], "scope-gate-turn")
            self.plan()
            self.record("source_scan", {"source_url":"https://manual.example.org/blocked", "page_label":"Synthetic inaccessible manual",
                "status":"inaccessible", "reviews":[], "reason":"Synthetic observed access failure", "goal_ids":["manual"], "source_type":"manual"}, "blocked")
            self.record("research_stop", self.stop_data(), "conditional-stop")
            self.store.require_evidence_coverage(self.original["session_id"], "scope-gate-turn")

    def test_large_status_preview_preserves_full_validation_scope(self):
        events = [{"kind":"research_plan", "data":{"goals":[{"goal_id":"goal-"+str(i), "kind":"manual", "scope_note":"x"*2000} for i in range(100)]}}]
        report=scope.summary(events); visible=scope.preview(report)
        self.assertEqual((visible["goal_count"],visible["remaining_goal_count"]),(100,100))
        self.assertEqual((len(visible["goals"]),len(visible["remaining_goal_ids"])),(10,20))
        self.assertEqual(len(report["remaining_goal_ids"]),100)
        self.assertLess(len(json.dumps(visible).encode("utf-8")),10000)

    def test_full_stop_scope_file_sha_and_current_scan_binding(self):
        self.plan();snap=self.capture("new", "Synthetic context")
        first=self.audit.status(self.research)["research_scope"]["stop_scope_file"]
        raw=(self.root/first["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),first["sha256"])
        full=json.loads(raw)
        self.assertEqual(len(full["remaining_goal_ids"]),6)
        self.scan(snap, [], goal_ids=["external_reviews"], remaining_scope=["Exact next page"])
        current=self.audit.status(self.research)["research_scope"]["stop_scope_file"]
        self.assertNotEqual(current["sha256"],first["sha256"])
        self.assertEqual((self.root/first["path"]).read_bytes(),raw)
        self.assertEqual(json.loads((self.root/current["path"]).read_bytes())["remaining_scope"],["Exact next page"])
        (self.root/current["path"]).write_text("{}",encoding="utf-8")
        self.error("workflow_scope_integrity", self.audit.status, self.research)

    def test_large_legal_plan_commits_with_bounded_response_and_full_scope_file(self):
        self.capture("large", "Synthetic observed identity")
        kinds=sorted(scope.KINDS)
        result=self.record("research_plan", {"product_name":"Generic large plan",
            "coverage":["positive","negative","long_term","conditions","counterexamples"], "source_plan":["Full declared scope"],
            "goals":[{"goal_id":"large-"+str(i),"kind":kinds[i%len(kinds)],"scope_note":"x"*2000} for i in range(100)]}, "large-plan")
        self.assertLess(len(json.dumps(result,ensure_ascii=False).encode("utf-8")),65536)
        descriptor=result["research_scope"]["stop_scope_file"]
        self.assertEqual(len(json.loads((self.root/descriptor["path"]).read_bytes())["remaining_goal_ids"]),100)
        self.assertEqual(len(scope.goals(self.audit.events(self.research))),100)

    def test_provider_remaining_scope_and_stop_are_bounded_without_journal_loss(self):
        self.plan();snap=self.capture("large-scan", "Synthetic exact source")
        remaining=["a"*1000+str(i) for i in range(100)]
        result=self.scan(snap, [], goal_ids=["external_reviews"], remaining_scope=remaining)
        self.assertLess(len(json.dumps(result,ensure_ascii=False).encode("utf-8")),65536)
        self.assertEqual(result["counts"]["providers"][0]["scans"][0]["remaining_scope_count"],100)
        self.assertEqual(len(scope.summary(self.audit.events(self.research))["remaining_scope"]),100)
        result=self.record("research_stop", self.stop_data(), "large-stop")
        self.assertLess(len(json.dumps(result,ensure_ascii=False).encode("utf-8")),65536)
        self.audit.require_scope_disclosure(self.research)

    def test_non_string_goal_kind_is_tool_error(self):
        for kind in ([], {}):
            with self.subTest(kind=kind):
                self.error("workflow_goal_invalid", self.record, "research_plan", {"product_name":"Synthetic", "coverage":["positive","negative","long_term","conditions","counterexamples"],
                    "source_plan":[], "goals":[{"goal_id":"bad","kind":kind,"scope_note":"Synthetic"}]}, "invalid-kind")

    def test_cli_large_plan_scan_stop_preserves_events_and_bounded_outputs(self):
        shutil.copytree(ROOT/"product-tools", self.root/"product-tools", ignore=shutil.ignore_patterns("__pycache__", ".venv"))
        self.store.db.execute("UPDATE product_workflows SET started_at=? WHERE research_id=?", (datetime.now(timezone.utc).isoformat(), self.research))
        self.store.db.commit()
        def call(operation,payload):
            cp=subprocess.run([sys.executable,"-X","utf8","-B",str(self.root/"product-tools/cli.py"),
                "--db",str(self.store.path),"--data",str(ROOT/"data/business/empty"),operation,"--input","-"],
                input=json.dumps(payload).encode("utf-8"),capture_output=True,timeout=30)
            self.assertEqual(cp.returncode,0,cp.stderr.decode("utf-8","replace")+cp.stdout.decode("utf-8","replace"))
            self.assertLess(len(cp.stdout),65536)
            self.assertTrue(json.loads(cp.stdout)["ok"])
        kinds=sorted(scope.KINDS)
        plan={"product_name":"Generic CLI large plan","coverage":["positive","negative","long_term","conditions","counterexamples"],
            "source_plan":["Multiple source and page roles"],"goals":[{"goal_id":"cli-"+str(i),"kind":kinds[i%len(kinds)],"scope_note":"x"*2000} for i in range(100)]}
        call("record_workflow_event",{"research_id":self.research,"event_key":"cli-plan","kind":"research_plan","data":plan})
        call("capture_web_page",{"research_id":self.research,"page_id":"cli-page","url":"https://reviews.example.org/cli-test",
            "observed_text":"Synthetic preserved CLI context","native_tool_name":"fixture_no_browser"})
        snapshot_id=self.store.db.execute("SELECT snapshot_id FROM web_pages WHERE page_id='cli-page'").fetchone()[0]
        remaining=["n"*1000+str(i) for i in range(100)]
        goal=next(g["goal_id"] for g in plan["goals"] if g["kind"]=="external_reviews")
        scan={"source_url":"https://reviews.example.org/cli-test","page_label":"Synthetic large scan","status":"observed","reviews":[],"reason":"Synthetic literal context",
            "snapshot_ids":[snapshot_id],"source_type":"review_list","goal_ids":[goal],"remaining_scope":remaining}
        call("record_workflow_event",{"research_id":self.research,"event_key":"cli-scan","kind":"source_scan","data":scan})
        report=scope.summary(self.audit.events(self.research))
        stop={"code":"sufficient_evidence","basis":"Conditional fixture conclusion","new_findings":[],"remaining_scope":report["remaining_scope"],
            "remaining_goal_ids":report["remaining_goal_ids"],"limitation_basis":"Declared scope remains unresolved; independent semantic review required"}
        call("record_workflow_event",{"research_id":self.research,"event_key":"cli-stop","kind":"research_stop","data":stop})
        self.assertEqual(len(scope.goals(self.audit.events(self.research))),100)
        self.assertEqual(len(scope.summary(self.audit.events(self.research))["remaining_scope"]),100)

    def test_malformed_goal_ids_do_not_raise_uncaught(self):
        self.plan();snap=self.capture("new", "Synthetic")
        self.error("workflow_goal_invalid", self.scan, snap, [], goal_ids=[{}])


if __name__ == "__main__":
    unittest.main()
