"""Family evaluator proves full range plus final/live persistence, not AI quality."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evals/runner"))
import family_eval as probe
from product_tools.conversation import Conversation
from product_tools.state import StateStore


class FamilyDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-family-delivery-")
        self.workspace = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            path = self.workspace / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        for source in (ROOT / "product-tools/product_tools").glob("*.py"):
            path = self.workspace / "product-tools/product_tools" / source.name
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(source.read_bytes())
        self.data = probe.ev.Dataset(ROOT / "data/business/lg-kitchen-v4")
        self.store = StateStore(self.workspace / "runtime-data/product.sqlite", self.data)
        self.conversation = Conversation(self.store, self.workspace)
        self.case = json.loads((ROOT / "evals/judge/family10.json").read_text(encoding="utf-8"))["cases"][0]
        self.case["turns"] = [self.case["question"]]
        self.turn = self.conversation.open_request({"question": self.case["question"], "product_family": "refrigerator",
            "constraints": self.case["constraints"], "user_submitted": True})["turn"]
        result = {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [], "assumptions": [],
            "evidence_refs": [], "validation_findings": ["합성 코드 계약 시험"], "revisions": 0, "usage_summary": {"status": "unknown"}}
        saved = self.conversation.save_and_export({"session_id": self.turn["session_id"], "turn_id": self.turn["turn_id"], "result_key": "first",
            "result": result, "expected_result_version": 0, "assessment": {"claim_checks": [], "feature_matches": [], "concept_links": []}})
        self.pointer = {"receipt": saved["save"]["receipt"], "export": saved["export"]}
        self.directory = self.workspace / "trace"; self.directory.mkdir()
        self.observed = {"status": "succeeded", "exit_code": 0, "turn_completed": True}
        self.write(self.pointer)

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def write(self, pointer):
        events = [{"type": "item.completed", "item": {"type": "agent_message", "text": "계약 시험\n" + json.dumps(pointer, ensure_ascii=False)}}, {"type": "turn.completed"}]
        (self.directory / "native.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8")

    def check(self):
        return probe.accept_family(self.workspace, self.directory, self.observed, self.case, self.data, "product")

    def test_full_family_range_and_actual_export_live_candidate_agree(self):
        self.assertTrue(self.check()["stored_match"])
        self.assertEqual(len(probe.expected_scopes(self.data, self.case)), 3)

    def test_one_model_substitution_or_wrong_family_cannot_pass(self):
        for family, model, mode in (("refrigerator", "B502S33", "exact_model"), ("microwave", None, "family_catalog")):
            with self.subTest(family=family):
                self.case.update(product_family=family, model_id=model, scope_mode=mode)
                with self.assertRaises(ValueError): self.check()

    def test_bad_pointer_or_timeout_cannot_be_replaced_by_good_database(self):
        bad = copy.deepcopy(self.pointer); bad["export"]["sha256"] = "0" * 64
        self.write(bad)
        with self.assertRaises(ValueError): self.check()
        self.write(self.pointer); self.observed["status"] = "timeout"
        with self.assertRaises(ValueError): self.check()

    def test_live_dependency_change_invalidates_previously_good_family_receipt(self):
        self.assertTrue(self.check()["stored_match"])
        path = self.workspace / "product-tools/product_tools/tools.py"
        path.write_bytes(path.read_bytes() + b"\n# unit-test dependency change\n")
        with self.assertRaises(ValueError): self.check()

    def test_boolean_versions_are_not_aliases_for_integer_one(self):
        pointer = copy.deepcopy(self.pointer)
        pointer["receipt"].update(candidate_result_version=True, current_result_version=True)
        self.write(pointer)
        with self.assertRaises(ValueError): self.check()

    def test_live_false_cannot_replace_exported_zero_in_validation(self):
        raw = self.store.db.execute("SELECT validation_json FROM results WHERE turn_id=?", (self.turn["turn_id"],)).fetchone()[0]
        value = json.loads(raw)
        self.assertEqual(value["checked_sources"], 0)
        self.assertIs(type(value["checked_sources"]), int)
        value["checked_sources"] = False
        self.store.db.execute("UPDATE results SET validation_json=? WHERE turn_id=?", (json.dumps(value), self.turn["turn_id"]))
        with self.assertRaises(ValueError): self.check()

    def test_ten_cases_and_prompts_preserve_questions_without_expected_scope_leak(self):
        corpus = json.loads((ROOT / "evals/judge/family10.json").read_text(encoding="utf-8"))
        self.assertEqual(len(probe.validate_cases(corpus)), 8)
        for case in corpus["cases"]:
            prompt = probe.build_prompt(case, corpus["data_path"])
            self.assertIn(case["question"], prompt)
            self.assertNotIn("family_catalog", prompt)
            self.assertNotIn("expected_terminal_states", prompt)
            self.assertNotIn("전체 모델3개", prompt)

    def test_changed_parent_structure_cannot_misreport_eight_conversations(self):
        corpus = json.loads((ROOT / "evals/judge/family10.json").read_text(encoding="utf-8"))
        for case in corpus["cases"]:
            case.update(parent_id=None, chain_id=case["id"])
        with self.assertRaises(ValueError): probe.validate_cases(corpus)


if __name__ == "__main__": unittest.main()
