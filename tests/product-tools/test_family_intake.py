"""Real store/export range checks; synthetic reasoning examples aren't AI quality."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, planning_input
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.planning import review_product_result
from product_tools.state import StateStore
from product_tools.tools import ProductTools


class FamilyIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-family-test-")
        self.workspace = Path(self.temp.name)
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            path = self.workspace / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        self.data = Dataset(ROOT / "data/business/lg-kitchen-v4")
        self.tools = ProductTools(self.data)
        self.store = StateStore(self.workspace / "runtime-data/test.sqlite", self.data)
        self.conversation = Conversation(self.store, self.workspace)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def open(self, family="refrigerator", **extra):
        return self.conversation.open_request_bundle({"question": "냉장고 사용 불편을 찾아 개선안을 제안해 줘.",
            "user_submitted": True, "product_family": family, **extra})

    def test_three_family_inputs_start_without_model_and_one_model_is_not_whole_family(self):
        for family, count in (("refrigerator", 3), ("microwave", 1), ("dishwasher", 1)):
            with self.subTest(family=family):
                response = self.open(family)
                value = response["turn"]["input"]
                self.assertEqual(value["scope_mode"], "family_catalog")
                self.assertEqual(len(value["model_scope"]), count)
                self.assertEqual(response["bundle"]["model_scope"], value["model_scope"])
                self.assertEqual(response["bundle"]["coverage"], "catalog_cases_only")
                self.assertIn("일반화하지", value["context"])

    def test_family_followup_keeps_all_scopes_constraints_and_historical_export(self):
        first = self.open()["turn"]
        exported = self.conversation.export_session({"session_id": first["session_id"]})
        path = self.workspace / exported["path"]
        raw = path.read_bytes()
        second = self.conversation.open_request({"question": "청소 문제는 제외하고 한 개만 제안해 줘.", "user_submitted": True,
            "session_id": first["session_id"], "prior_turn_id": first["turn_id"],
            "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": ["청소"]}})["turn"]
        self.assertEqual(second["input"]["model_scope"], first["input"]["model_scope"])
        self.assertEqual(second["input"]["scope_mode"], "family_catalog")
        self.assertEqual(second["input"]["constraints"]["max_concepts"], 1)
        self.assertFalse(self.store.get_turn(first["session_id"], first["turn_id"])["valid"])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), exported["sha256"])

    def test_user_can_narrow_family_to_model_and_switch_family_without_transfer(self):
        first = self.open()["turn"]
        second = self.conversation.open_request({"question": "B502S33만 자세히 봐줘.", "user_submitted": True,
            "model_id": "B502S33", "session_id": first["session_id"], "prior_turn_id": first["turn_id"]})["turn"]
        self.assertEqual(second["input"]["scope_mode"], "exact_model")
        self.assertEqual([s["model_id"] for s in second["input"]["model_scope"]], ["B502S33"])
        third = self.open("dishwasher", session_id=first["session_id"], prior_turn_id=second["turn_id"])["turn"]
        self.assertEqual(third["input"]["scope_mode"], "family_catalog")
        self.assertEqual([s["model_id"] for s in third["input"]["model_scope"]], ["DUBJ2EA"])

    def test_unspecified_product_still_asks_without_creating_fake_turn(self):
        pending = self.conversation.open_request({"question": "사용 불편을 찾아 줘.", "user_submitted": True})
        self.assertEqual(pending["status"], "needs_input")
        exported = self.conversation.export_session({"session_id": pending["session_id"]})
        value = json.loads((self.workspace / exported["path"]).read_text(encoding="utf-8"))
        self.assertEqual(value["turns"], [])
        self.assertEqual(value["requests"][0]["response"], pending)

    def test_narrowing_preserves_selected_prior_snapshot_despite_new_ambiguity(self):
        first = self.open()["turn"]
        original = next(m for m in self.data.models if m["model_id"] == "B502S33")
        extra = {**original, "document_version": "new-fixture-snapshot"}
        self.data.models.append(extra)
        self.data.scopes.add(canonical({k: extra[k] for k in ("model_id", "model_version", "document_version")}))
        second = self.conversation.open_request({"question": "그중 B502S33만 봐줘.", "model_id": "B502S33", "user_submitted": True,
            "session_id": first["session_id"], "prior_turn_id": first["turn_id"]})["turn"]
        self.assertEqual(second["input"]["model_scope"], [s for s in first["input"]["model_scope"] if s["model_id"] == "B502S33"])

    def test_conflicting_family_model_and_missing_exact_selection_are_not_auto_resolved(self):
        with self.assertRaises(ToolError):
            self.open("microwave", model_id="B502S33")
        response = self.open("refrigerator", scope_mode="exact_model")
        self.assertEqual(response["status"], "needs_input")
        with self.assertRaises(ToolError):
            self.open("microwave", scope_mode="family_catalog", model_id="MWJ25E")

    def test_bundle_has_all_model_scopes_and_global_source_and_byte_bounds(self):
        response = self.open()
        bundle = response["bundle"]
        self.assertIsNone(bundle["scope"])
        self.assertLessEqual(len(bundle["records"]), 40)
        self.assertLessEqual(len(bundle["evidence_refs"]), 40)
        self.assertLess(len(canonical(response).encode("utf-8")), 65536)
        self.assertEqual({r["model_id"] for r in bundle["evidence_refs"]}, {s["model_id"] for s in bundle["model_scope"]})
        self.assertEqual(len(bundle["retrieval"]["product_fact"]["per_scope"]), 3)
        for ref in bundle["evidence_refs"]:
            self.assertEqual(ref, self.data.reference(self.data.source(ref["source_id"])))

    def test_catalog_snapshot_ambiguity_or_excess_requires_narrowing_not_silent_selection(self):
        original = copy.deepcopy(self.data.models)
        self.data.models.append({**original[0], "document_version": "ambiguous-fixture"})
        self.data.scopes.update(canonical({k: m[k] for k in ("model_id", "model_version", "document_version")}) for m in self.data.models)
        with self.assertRaises(ToolError) as caught:
            self.tools.prepare_planning_input({"session_id": "test", "request_key": "first", "product_family": "refrigerator"})
        self.assertEqual(caught.exception.code, "needs_input")
        self.data.models = original + [{**original[0], "model_id": "EXTRA" + str(n)} for n in range(3)]
        self.data.scopes.update(canonical({k: m[k] for k in ("model_id", "model_version", "document_version")}) for m in self.data.models)
        with self.assertRaises(ToolError) as caught:
            self.tools.prepare_planning_input({"session_id": "test", "request_key": "second", "product_family": "refrigerator"})
        self.assertEqual(caught.exception.code, "needs_input")

    def example(self):
        planning = self.open()["turn"]["input"]
        a, b = planning["model_scope"][:2]
        review_a = self.data.retrieve("review", a)["records"][0]
        fact_a = self.data.retrieve("product_fact", a)["records"][0]
        fact_b = self.data.retrieve("product_fact", b)["records"][0]
        ids = [review_a["source_id"], fact_a["source_id"], fact_b["source_id"]]
        def claim(cid, source):
            return {"id": cid, "text": "단위 계약시험 문장, 실사용 기획 결과가 아님", "source_ids": [source]}
        result = {"status": "held", "pains": [claim("p", ids[0])], "existing_features": [claim("fa", ids[1]), claim("fb", ids[2])],
            "remaining_pains": [claim("r", ids[0])], "concepts": [{**claim("c", ids[0]), "requirements": ["시험"], "requires_hardware": False, "assumptions": ["시험"]}],
            "assumptions": ["합성 판단 시험"], "evidence_refs": [self.data.reference(r) for r in (review_a, fact_a, fact_b)],
            "validation_findings": ["판단 시험용"], "revisions": 0, "usage_summary": {"status": "unknown"}}
        assessment = {"claim_checks": [{"claim_id": c["id"], "source_ids": c["source_ids"], "support_status": "supported", "scope_relation": "current_model", "rationale": "단위 계약시험"}
            for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in result[key]],
            "feature_matches": [{"remaining_pain_id": "r", "pain_id": "p", "feature_source_ids": [ids[1]], "resolution": "unresolved", "rationale": "단위 계약시험"}],
            "concept_links": [{"concept_id": "c", "remaining_pain_ids": ["r"], "duplicates_existing": False, "geometry_required": False, "geometry_known": False, "geometry_source_ids": [], "rationale": "단위 계약시험"}]}
        return planning, result, assessment, ids

    def test_cross_model_claim_is_rejected_even_with_valid_individual_refs(self):
        planning, result, assessment, ids = self.example()
        result["concepts"][0]["source_ids"].append(ids[2])
        with self.assertRaises(ToolError) as caught:
            self.tools.validate_result_contract(planning, result)
        self.assertEqual(caught.exception.code, "scope_mismatch")

    def test_other_models_feature_cannot_resolve_pain(self):
        planning, result, assessment, ids = self.example()
        assessment["feature_matches"][0]["feature_source_ids"] = [ids[2]]
        with self.assertRaises(ToolError) as caught:
            review_product_result(self.data, {"input": planning, "result": result, "assessment": assessment})
        self.assertEqual(caught.exception.code, "scope_mismatch")

    def test_other_models_dimensions_cannot_justify_concept(self):
        planning, result, assessment, ids = self.example()
        assessment["concept_links"][0].update(geometry_required=True, geometry_known=True, geometry_source_ids=[ids[2]])
        with self.assertRaises(ToolError) as caught:
            review_product_result(self.data, {"input": planning, "result": result, "assessment": assessment})
        self.assertEqual(caught.exception.code, "scope_mismatch")

    def test_legacy_input_without_mode_still_readable(self):
        value = self.tools.prepare_planning_input({"model_id": "MWJ25E", "session_id": "old", "request_key": "old"})["input"]
        value.pop("scope_mode")
        planning_input(value)
        self.data.check_input(value)


if __name__ == "__main__":
    unittest.main()
