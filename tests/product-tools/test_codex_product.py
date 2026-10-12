"""Product installation/isolation and conversation state boundary checks."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore

spec = importlib.util.spec_from_file_location("product_installer", ROOT / "adapters/codex/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ProductInstallTests(unittest.TestCase):
    def test_isolated_install_has_only_business_skills_and_works_after_move(self):
        with tempfile.TemporaryDirectory(prefix="lg-product-install-") as temporary:
            base = Path(temporary).resolve()
            target = base / "product"
            installer.install(target)
            self.assertEqual(installer.check(target)["errors"], [])
            self.assertFalse((target / ".claude").exists())
            self.assertTrue((target / ".codex/config.toml").is_file())
            self.assertEqual([p.name for p in (target / ".codex/agents").glob('*.toml')],['product-evidence-reviewer.toml'])
            self.assertEqual(len(list((target / ".agents/skills").glob("*/SKILL.md"))), 6)
            for skill in (target / ".agents/skills").glob("*/SKILL.md"):
                for link in re.findall(r"\]\(([^)]+)\)", skill.read_text(encoding="utf-8")):
                    self.assertTrue((skill.parent / link).is_file(), link)
            moved = base / "moved-product"
            self.assertEqual(target.parent, base)
            self.assertEqual(moved.parent, base)
            shutil.move(str(target), str(moved))
            p = subprocess.run([sys.executable, ".agents/skills/evidence-retrieval/scripts/run.py", "doctor"], cwd=moved, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse(json.loads(p.stdout)["result"]["synthetic"])

    def test_existing_target_and_development_repo_are_not_modified(self):
        with self.assertRaises(ValueError):
            installer.install(ROOT / "runtime-data/not-a-product-install")
        with tempfile.TemporaryDirectory(prefix="lg-product-existing-") as temporary:
            target = Path(temporary)
            keep = target / "keep.txt"
            keep.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                installer.install(target)
            self.assertEqual(keep.read_text(), "keep")

    def test_installed_modified_file_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lg-product-drift-") as temporary:
            target = Path(temporary) / "product"
            installer.install(target)
            (target / "AGENTS.md").write_text("changed", encoding="utf-8")
            self.assertTrue(installer.check(target)["errors"])


class ProductConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-conversation-")
        self.workspace = Path(self.temp.name).resolve()
        for relative in ("skills/manifest.json", "agents/product-planning.md"):
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        self.data = Dataset(ROOT / "data/business/lg-research-v3")
        self.store = StateStore(self.workspace / "runtime-data/test.sqlite", self.data)
        self.conversation = Conversation(self.store, self.workspace)

    def tearDown(self):
        self.store.close()
        self.assertTrue(self.workspace.name.startswith("lg-conversation-"))
        self.temp.cleanup()

    def open(self):
        return self.conversation.open_request({"question": "모델 선택 중심 실제 요청", "model_id": "T876MQQ012", "user_submitted": True})["turn"]

    def held(self, revision=0):
        return {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [], "assumptions": [], "evidence_refs": [], "validation_findings": ["Test-only missing evidence"], "revisions": revision, "usage_summary": {"status": "unknown"}}

    def test_first_request_generates_handle_and_resume_does_not_reset(self):
        turn = self.open()
        self.store.save_result(turn["session_id"], turn["turn_id"], "first", self.held(), 0, {"claim_checks": [], "feature_matches": [], "concept_links": []})
        current = self.conversation.current_request({"session_id": turn["session_id"], "request_key": turn["request_key"]})["turn"]
        self.assertEqual(current["turn_id"], turn["turn_id"])
        self.assertEqual(current["result_version"], 1)
        self.assertIsNone(current["input"]["runtime"]["model_id"])

    def test_followup_preserves_conditions_and_historical_result(self):
        turn = self.open()
        self.store.save_result(turn["session_id"], turn["turn_id"], "first", self.held(), 0)
        next_request = self.conversation.open_request({"question": "추가 질문", "session_id": turn["session_id"], "prior_turn_id": turn["turn_id"], "user_submitted": True})
        self.assertEqual(next_request["turn"]["input"]["constraints"], turn["input"]["constraints"])
        self.assertEqual(next_request["previous"]["result"]["status"], "held")
        self.assertEqual(next_request["turn"]["result_version"], 0)
        self.assertFalse(self.store.get_turn(turn["session_id"], turn["turn_id"])["valid"])
        self.assertIn("historical", next_request["previous"]["use"])
        self.assertTrue(next_request["previous"]["valid_before_request"])
        self.assertFalse(next_request["previous"]["valid_for_current_context"])

    def test_followup_does_not_inherit_unobserved_model_runtime(self):
        initial = self.conversation.open_request({"question": "first", "model_id": "T876MQQ012", "user_submitted": True,
                      "runtime": {"engine": "codex", "engine_version": "test", "model_id": "test-model", "settings_fingerprint": "test-settings"}})["turn"]
        follow = self.conversation.open_request({"question": "follow", "session_id": initial["session_id"], "prior_turn_id": initial["turn_id"], "user_submitted": True})["turn"]
        self.assertIsNone(follow["input"]["runtime"]["model_id"])
        self.assertIsNone(follow["input"]["runtime"]["settings_fingerprint"])

    def test_large_review_is_exported_without_duplicating_cli_response(self):
        turn = self.open()
        result = self.held()
        source_id = "SPEC-T876MQQ012-02"
        result["existing_features"] = [{"id": "fact" + str(i), "text": "Fixture " + "x" * 950, "source_ids": [source_id]} for i in range(20)]
        result["evidence_refs"] = self.store.tools.select_evidence(turn["input"]["model_scope"][0], [source_id])["evidence_refs"]
        assessment = {"claim_checks": [{"claim_id": c["id"], "source_ids": c["source_ids"], "support_status": "supported", "scope_relation": "current_model", "rationale": "Test only " + "x" * 950} for c in result["existing_features"]], "feature_matches": [], "concept_links": []}
        for revision in range(3):
            result["revisions"] = revision
            saved = self.store.save_result(turn["session_id"], turn["turn_id"], "large-" + str(revision), result, revision, assessment)
            self.assertTrue(saved["accepted"])
            self.assertLess(len(json.dumps(saved).encode("utf-8")), 65536)
            self.assertNotIn("assessment", saved["validation"])
            self.assertNotIn("assessment", saved["turn"]["last_validation"])
        exported = self.conversation.export_session({"session_id": turn["session_id"]})
        value = json.loads((self.workspace / exported["path"]).read_text(encoding="utf-8"))
        self.assertEqual(value["turns"][0]["candidates"][0]["validation"]["assessment"], assessment)

    def test_large_followup_retransmission_returns_current_result_only(self):
        turn = self.open()
        large = self.held()
        large["assumptions"] = ["Test only " + "x" * 950 for _ in range(20)]
        assessment = {"claim_checks": [], "feature_matches": [], "concept_links": []}
        self.store.save_result(turn["session_id"], turn["turn_id"], "large-first", large, 0, assessment)
        request = {"question": "follow", "session_id": turn["session_id"], "prior_turn_id": turn["turn_id"], "request_key": "large-follow", "user_submitted": True}
        follow = self.conversation.open_request(request)["turn"]
        self.store.save_result(follow["session_id"], follow["turn_id"], "large-second", large, 0, assessment)
        resumed = self.conversation.open_request(request)
        self.assertTrue(resumed["reused_request"])
        self.assertNotIn("result", resumed["previous"])
        self.assertFalse(resumed["previous"]["valid_for_current_context"])
        self.assertLess(len(json.dumps(resumed).encode("utf-8")), 65536)

    def test_ambiguous_model_can_be_resolved_and_followup_can_select_new_version(self):
        self.store.close()
        data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store = StateStore(self.workspace / "runtime-data/versions.sqlite", data)
        self.conversation = Conversation(self.store, self.workspace)
        unknown = self.conversation.open_request({"question": "test", "model_id": "AX-R301", "user_submitted": True})
        self.assertEqual(unknown["status"], "needs_input")
        turn = self.conversation.open_request({"question": "test version selection", "model_id": "AX-R301", "model_version": "2.0", "document_version": "manual-r2", "session_id": unknown["session_id"], "user_submitted": True})["turn"]
        scope = turn["input"]["model_scope"][0]
        self.assertEqual(scope["document_version"], "manual-r2")
        alternative = next(m for m in data.models if m["model_id"] == "AX-R301" and m["document_version"] != "manual-r2")
        follow = self.conversation.open_request({"question": "test document changed", "session_id": turn["session_id"], "prior_turn_id": turn["turn_id"], "model_version": alternative["model_version"], "document_version": alternative["document_version"], "user_submitted": True})["turn"]
        self.assertEqual(follow["input"]["model_scope"][0]["document_version"], alternative["document_version"])
        self.assertFalse(self.store.get_turn(turn["session_id"], turn["turn_id"])["valid"])

    def test_unknown_model_requires_research_without_fake_turn(self):
        result = self.conversation.open_request({"question": "미확인 모델", "model_id": "NONEXISTENT", "user_submitted": True})
        self.assertEqual(result["status"], "research_required")
        self.assertIsNone(result["turn_id"])
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM turns").fetchone()[0], 0)
        self.assertEqual(self.conversation.current_request({k: result[k] for k in ("session_id", "request_key")})["status"], "research_required")

    def test_bundle_exact_sources_once_and_replay_preserves_counter(self):
        payload = {"question": "storage", "model_id": "B502S33", "session_id": "bundle", "request_key": "one", "user_submitted": True}
        first = self.conversation.open_request_bundle(payload)
        scope = first["turn"]["input"]["model_scope"][0]
        refs = first["bundle"]["evidence_refs"]
        self.assertTrue(refs)
        self.assertTrue(all(all(r[k] == v for k,v in scope.items()) for r in refs))
        self.assertTrue(all("text" not in r and "quote" not in r for r in first["bundle"]["records"]))
        turn = first["turn"]
        saved = self.store.save_result(turn["session_id"], turn["turn_id"], "held", self.held(), 0,
                                      {"claim_checks": [], "feature_matches": [], "concept_links": []}, require_review=True)
        again = self.conversation.open_request_bundle(payload)
        self.assertEqual(again["turn"]["result_version"], saved["turn"]["result_version"])
        self.assertTrue(again["reused_request"])

    def test_bundle_stale_terminal_and_exhausted_preserve_handle(self):
        payload = {"question": "storage", "model_id": "T876MQQ012", "session_id": "bundle", "request_key": "stale", "user_submitted": True}
        first = self.conversation.open_request_bundle(payload)["turn"]
        other = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.store.dataset = other
        stale = self.conversation.open_request_bundle(payload)
        self.assertFalse(stale["turn"]["valid"])
        self.assertEqual(stale["turn"]["turn_id"], first["turn_id"])
        self.assertIsNone(stale["bundle"])
        self.store.dataset = self.data
        for state, version in (("failed", 0), ("cancelled", 0), ("held", 3)):
            self.store.db.execute("UPDATE turns SET status=?,result_version=? WHERE turn_id=?", (state,version,first["turn_id"]))
            resumed = self.conversation.open_request_bundle(payload)
            self.assertIsNone(resumed["bundle"])
            self.assertEqual(resumed["turn"]["result_version"], version)

    def test_large_bundle_keeps_handle_omitted_ids_and_utf8_bound(self):
        original = self.data.reference
        self.data.reference = lambda record: {**original(record), "quote": "큰 원문" * 13000}
        bundle = self.conversation.open_request_bundle({"question": "size", "model_id": "T876MQQ012", "user_submitted": True})
        self.assertTrue(bundle["turn"]["turn_id"])
        self.assertTrue(bundle["bundle"]["byte_truncated"])
        self.assertTrue(bundle["bundle"]["omitted_source_ids"])
        self.assertLess(len(json.dumps({"ok":True,"result":bundle},ensure_ascii=False).encode()),65536)

    def test_missing_or_null_review_counts_and_cannot_upgrade_duplicate(self):
        from cli import dispatch
        turn = self.open()
        payload = {"session_id":turn["session_id"], "turn_id":turn["turn_id"], "result_key":"no-review", "result":self.held(), "expected_result_version":0}
        saved = dispatch(self.data, self.store, "save_reviewed_result", payload)
        self.assertFalse(saved["accepted"])
        self.assertEqual(saved["turn"]["result_version"],1)
        self.assertFalse(dispatch(self.data,self.store,"save_reviewed_result",payload)["accepted"])
        null = dispatch(self.data,self.store,"save_reviewed_result",{**payload,"result_key":"null-review","result":self.held(1),"expected_result_version":1,"assessment":None})
        self.assertFalse(null["accepted"])
        self.assertEqual(null["turn"]["result_version"],2)
        lower = self.store.save_result(turn["session_id"],turn["turn_id"],"lower",self.held(2),2)
        self.assertTrue(lower["accepted"])
        with self.assertRaises(ToolError):
            self.store.save_result(turn["session_id"],turn["turn_id"],"lower",self.held(2),2,require_review=True)

    def test_invalid_review_counts_and_session_export_preserves_failed_candidate(self):
        turn = self.open()
        for revision in range(3):
            saved = self.store.save_result(turn["session_id"], turn["turn_id"], "bad-" + str(revision), self.held(revision), revision, {"claim_checks": [{"invalid": True}], "feature_matches": [], "concept_links": []})
            self.assertFalse(saved["accepted"])
        exhausted = self.store.save_result(turn["session_id"], turn["turn_id"], "fourth", self.held(2), 3, {"claim_checks": [], "feature_matches": [], "concept_links": []})
        self.assertEqual(exhausted["reason"], "business_revision_limit")
        current = self.conversation.current_request({k: turn[k] for k in ("session_id", "request_key")})["turn"]
        self.assertEqual(current["result_version"], 3)
        exported = self.conversation.export_session({"session_id": turn["session_id"]})
        value = json.loads((self.workspace / exported["path"]).read_text(encoding="utf-8"))
        self.assertEqual(len(value["turns"][0]["candidates"]), 3)
        self.assertFalse(value["turns"][0]["candidates"][0]["validation"]["contract_valid"])
        self.assertIsNone(value["usage_summary"]["totals"]["input_tokens"])

    def test_changed_request_and_false_user_submission_rejected(self):
        for payload in ({"question": "internal retry", "user_submitted": False}, {"question": "follow", "user_submitted": True, "prior_turn_id": "turn-any"}):
            with self.assertRaises(ToolError):
                self.conversation.open_request(payload)
        first = {"session_id": "fixed", "request_key": "same", "question": "first", "user_submitted": True}
        self.conversation.open_request(first)
        with self.assertRaises(ToolError):
            self.conversation.open_request({**first, "question": "changed"})


if __name__ == "__main__":
    unittest.main()
