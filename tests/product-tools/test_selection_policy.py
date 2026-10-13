"""Independent policy-path tests. All pages/models are fictional code fixtures.

Source imports come only from PRODUCT_SELECTION_SOURCE_ROOT. Fixtures stay in
this isolated worktree; never run native AI, HTTP, or original business datasets.
"""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

TEST_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("PRODUCT_SELECTION_SOURCE_ROOT", str(TEST_ROOT))).resolve()
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.selection import SelectionPolicy
from product_tools.state import StateStore
from product_tools.web_evidence import WebEvidence


def held(refs=()):
    return {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [],
            "assumptions": [], "evidence_refs": list(refs), "validation_findings": ["Fictional policy code fixture only"],
            "decision_notes": [{"text": "Code fixture sources used only for export contract inspection",
                                "source_ids": [r["source_id"] for r in refs], "basis": "source_fact"}] if refs else [],
            "revisions": 0, "usage_summary": {"status": "unknown"}}


class SelectionPolicyTests(unittest.TestCase):
    def setUp(self):
        scratch = TEST_ROOT / "runtime-data"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="policy-", dir=scratch)
        self.root = Path(self.temp.name).resolve()
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        self.now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
        self.clock = patch("product_tools.workflow.utc_now", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.empty = Dataset(ROOT / "data/business/empty")
        self.store = StateStore(self.root / "runtime-data/product.sqlite", self.empty)
        self.conv = Conversation(self.store, self.root)
        self.web = WebEvidence(self.store.path, self.root)
        self.original = {"question": "전자레인지 사용 불편을 찾아 개선안을 제안해 줘.", "user_submitted": True,
                         "session_id": "policy-session", "request_key": "generic-microwave"}
        self.request = self.conv.open_product_workflow(self.original)
        self.serial = 0

    def tearDown(self):
        self.web.close()
        self.store.close()
        self.assertTrue(self.root.is_relative_to((TEST_ROOT / "runtime-data").resolve()))
        self.temp.cleanup()

    def error(self, code, fn, *args):
        with self.assertRaises(ToolError) as ctx:
            fn(*args)
        self.assertEqual(ctx.exception.code, code)

    def new_request(self, question, key="explicit", **fields):
        payload = {**self.original, "question": question, "request_key": key, **fields}
        # The product-name clock entry deliberately has no model_id field;
        # structured named-model input is the compatible open_request API.
        response = self.conv.open_request(payload) if fields else self.conv.open_product_workflow(payload)
        return payload, response

    def policy(self, original, value):
        return self.conv.set_request_scope_policy({"session_id": original["session_id"],
            "request_key": original["request_key"], "policy": value})

    def payload(self, model="LG-FIX-1", maker="LG전자", url="https://www.lge.co.kr/product/fixture", *, web=None, request=None):
        self.serial += 1
        web = web or self.web
        research = request["research_id"] if request else "legacy-fixture"
        literal = f"Fictional code fixture only: {maker} {model} exact identity. Not a real product observation."
        with patch("product_tools.web_evidence.datetime") as timer:
            timer.now.return_value = self.now
            snapshot = web.collect({"research_id": research, "page_id": "identity-"+str(self.serial), "url": url,
                "observed_text": literal, "native_tool_name": "unit_fixture_no_browser_executed"}, True)
        scope = {"model_id": model, "model_version": "unspecified", "document_version": "fixture-doc"}
        source = "arbitrary-identity-"+str(self.serial)
        entry = {"snapshot_id": snapshot["snapshot_id"], "source_id": source, "kind": "product_fact", "scope": scope,
            "location": "Fictional identity fixture", "text": literal, "support_quote": literal,
            "published_date": None, "model_matching": "explicit_model_verified", "purchase_verified": None,
            "sponsorship": None, "feature_key": "identity", "availability": "present"}
        registration = {**scope, "name": "Fictional "+model, "product_family": "microwave", "synthetic": False,
            "spec_source_id": source, "identity_review": {"source_id": source, "manufacturer": maker,
                "authority": "manufacturer", "rationale": "Code fixture only, never business evidence"}}
        result = {"data_version": "policy-version-"+str(self.serial), "observations": [entry], "new_models": [registration]}
        if request:
            result["research_id"] = request["research_id"]
        return result

    def legacy_dataset(self, **values):
        seed = WebEvidence(self.root / "runtime-data/seed.sqlite", self.root)
        try:
            payload = self.payload(web=seed, **values)
            reply = seed.import_evidence(self.empty, payload)
            return Dataset(self.root / reply["data_path"])
        finally:
            seed.close()

    def load(self, data):
        self.web.close()
        self.store.close()
        self.store = StateStore(self.root / "runtime-data/product.sqlite", data)
        self.conv = Conversation(self.store, self.root)
        self.web = WebEvidence(self.store.path, self.root)

    def stop(self, request):
        from product_tools.workflow import WorkflowAudit
        if not WorkflowAudit(self.store.db, self.root).active(request["research_id"]):
            return
        self.conv.record_workflow_event({"research_id": request["research_id"], "event_key": "stop",
            "kind": "research_stop", "data": {"code": "completion_time_reserve", "basis": "Fixture only",
                "new_findings": [], "remaining_scope": []}})

    def resolve(self, original, request, model):
        self.stop(request)
        return self.conv.resolve_request({"session_id": original["session_id"], "request_key": original["request_key"],
            "event_key": "resolve", "expected_request_version": request["request_version"], "selection": {"model_id": model}})

    def test_generic_default_is_auto_lg_kr_and_original_unchanged(self):
        self.assertEqual(self.request["selection_policy"], {"mode": "project_default", "brand": "LG전자", "market": "KR"})
        self.assertIsNone(self.request["turn_id"])
        raw = self.store.db.execute("SELECT payload FROM conversation_requests").fetchone()[0]
        self.assertEqual(json.loads(raw), self.original)

    def test_actual_toshiba_import_rejected_for_generic(self):
        payload = self.payload(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture", request=self.request)
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty, payload)
        self.assertFalse((self.root / "runtime-data/catalogs" / payload["data_version"]).exists())

    def test_actual_us_lg_import_rejected_for_generic(self):
        payload = self.payload(url="https://www.lg.com/us/fixture", request=self.request)
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty, payload)

    def test_lg_kr_import_bind_and_reviewed_save_pass(self):
        payload = self.payload(request=self.request)
        reply = self.web.import_evidence(self.empty, payload)
        self.load(Dataset(self.root / reply["data_path"]))
        turn = self.resolve(self.original, self.request, "LG-FIX-1")["turn"]
        # Identity-only fixture supports an honest held result, not invented
        # customer pain; positive policy-save behavior is independent of claims.
        result = held()
        saved = self.store.save_result(turn["session_id"], turn["turn_id"], "candidate", result, 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, True)
        self.assertTrue(saved["accepted"])

    def test_bind_rejects_foreign_catalog_even_without_import_policy(self):
        self.load(self.legacy_dataset(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture"))
        self.error("target_scope_mismatch", self.resolve, self.original, self.request, "TO-FIX-1")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 0)

    def test_save_rejects_lower_level_bind_bypass(self):
        self.load(self.legacy_dataset(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture"))
        planning = self.store.tools.prepare_planning_input({"session_id": self.original["session_id"],
            "request_key": self.original["request_key"], "question": self.original["question"], "model_id": "TO-FIX-1"})["input"]
        turn = self.store.start_turn(planning, True)
        self.store.db.execute("UPDATE conversation_requests SET turn_id=?", (turn["turn_id"],))
        self.error("target_scope_mismatch", self.store.save_result, turn["session_id"], turn["turn_id"], "blocked", held(), 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM results").fetchone()[0], 0)

    def test_us_lg_bind_and_save_reject_generic_lower_api_bypass(self):
        self.load(self.legacy_dataset(url="https://www.lg.com/us/fixture"))
        self.error("target_scope_mismatch", self.resolve, self.original, self.request, "LG-FIX-1")
        planning = self.store.tools.prepare_planning_input({"session_id": self.original["session_id"],
            "request_key": self.original["request_key"], "question": self.original["question"], "model_id": "LG-FIX-1"})["input"]
        turn = self.store.start_turn(planning, True)
        self.store.db.execute("UPDATE conversation_requests SET turn_id=?", (turn["turn_id"],))
        self.error("target_scope_mismatch", self.store.save_result, turn["session_id"], turn["turn_id"], "blocked-us", held(), 0)

    def test_touched_import_does_not_block_unrelated_legacy_model(self):
        old = self.legacy_dataset(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture")
        payload = self.payload(request=self.request)
        reply = self.web.import_evidence(old, payload)
        self.assertEqual(len(Dataset(self.root / reply["data_path"]).models), 2)

    def test_exact_original_model_override_auto_preserved_and_locked(self):
        original, request = self.new_request("TO-FIX-1 모델을 분석해 줘.", model_id="TO-FIX-1")
        self.assertEqual(request["selection_policy"]["mode"], "explicit_model")
        payload = self.payload(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture", request=request)
        reply = self.web.import_evidence(self.empty, payload)
        self.load(Dataset(self.root / reply["data_path"]))
        self.resolve(original, request, "TO-FIX-1")
        self.error("selection_policy_conflict", self.policy, original,
            {"mode": "explicit_model", "model_id": "LG-FIX-1", "user_quote": "LG-FIX-1"})

    def test_explicit_brand_market_preserved_with_literal_quote(self):
        original, request = self.new_request("Toshiba 미국 전자레인지를 분석해 줘.")
        policy = {"mode": "explicit_brand_market", "brand": "Toshiba", "market": "US",
                  "user_quote": "Toshiba", "market_quote": "미국"}
        self.assertEqual(self.policy(original, policy), policy)
        payload = self.payload(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture", request=request)
        self.assertTrue(self.web.import_evidence(self.empty, payload)["structural_valid"])
        self.error("selection_policy_conflict", self.policy, original,
            {"mode": "explicit_brand_market", "brand": "LG", "market": "KR", "user_quote": "Toshiba", "market_quote": "미국"})

    def test_explicit_us_market_must_reject_domestic_lg_import(self):
        original, request = self.new_request("LG 미국 전자레인지 모델을 분석해 줘.")
        self.policy(original, {"mode": "explicit_brand_market", "brand": "LG", "market": "US",
            "user_quote": "LG", "market_quote": "미국"})
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty, self.payload(request=request))

    def test_forged_market_interpretation_cannot_use_unrelated_quote(self):
        original, _ = self.new_request("Toshiba 전자레인지를 분석해 줘.")
        self.error("selection_policy_conflict", self.policy, original,
            {"mode": "explicit_brand_market", "brand": "Toshiba", "market": "US",
                "user_quote": "Toshiba", "market_quote": "전자레인지"})

    def test_forged_model_brand_quote_and_default_rewrite_rejected(self):
        for policy in ({"mode": "explicit_model", "model_id": "TO-FIX-1", "user_quote": "TO-FIX-1"},
                       {"mode": "explicit_brand_market", "brand": "Toshiba", "user_quote": "전자레인지"}):
            self.error("selection_policy_conflict", self.policy, self.original, policy)
        self.error("invalid_input", self.policy, self.original,
            {"mode": "project_default", "brand": "Toshiba", "market": "US", "user_quote": "전자레인지"})

    def test_export_kinds_are_sibling_metadata_and_payload_hash_stays(self):
        data = self.legacy_dataset()
        self.load(data)
        turn = self.resolve(self.original, self.request, "LG-FIX-1")["turn"]
        source = next(iter(data.sources.values()))
        ref = data.reference(source)
        original_ref = canonical(ref)
        result = held([ref])
        saved = self.store.save_result(turn["session_id"], turn["turn_id"], "metadata-candidate", result, 0)
        self.assertTrue(saved["accepted"])
        before = tuple(self.store.db.execute("SELECT payload,payload_hash FROM results").fetchone())
        exported = self.conv.export_session({"session_id": turn["session_id"]})
        body = json.loads((self.root / exported["path"]).read_text(encoding="utf-8"))
        candidate = body["turns"][0]["candidates"][0]
        self.assertEqual(candidate["source_metadata"][0]["kind"], "product_fact")
        self.assertEqual(candidate["result"], result)
        self.assertEqual(fingerprint(candidate["result"]), before[1])
        self.assertEqual(tuple(self.store.db.execute("SELECT payload,payload_hash FROM results").fetchone()), before)
        self.assertEqual(canonical(ref), original_ref)
        historic = copy.deepcopy(ref)
        historic["data_version"] = "unavailable-old-version"
        self.assertIsNone(self.conv._source_metadata([historic])[0]["kind"])
        wrong_quote = copy.deepcopy(ref)
        wrong_quote["quote"] = "Different quote"
        self.assertIsNone(self.conv._source_metadata([wrong_quote])[0]["kind"])

    def test_manual_fact_type_does_not_follow_source_id_prefix(self):
        data = self.legacy_dataset()
        self.load(data)
        source = copy.deepcopy(next(iter(data.sources.values())))
        source["source_id"] = "review-looking-manual-id"
        source["location"] = "Manual fixture"
        data.sources[source["source_id"]] = source
        ref = data.reference(source)
        self.assertEqual(self.conv._source_metadata([ref])[0]["kind"], "product_fact")
        review = copy.deepcopy(source)
        review["source_id"] = "document-looking-review-id"
        review["kind"] = "review"
        review["origin"]["representation"] = "excerpt"
        data.sources[review["source_id"]] = review
        self.assertEqual(self.conv._source_metadata([data.reference(review)])[0]["kind"], "review")

    def test_domestic_support_fact_cannot_launder_foreign_identity(self):
        payload = self.payload(url="https://www.lg.com/us/fixture", request=self.request)
        extra = self.payload(url="https://www.lge.co.kr/support/fixture", request=self.request)
        extra["observations"][0]["source_id"] = "domestic-nonidentity-fact"
        extra["observations"][0]["feature_key"] = "manual_instruction"
        payload["observations"].append(extra["observations"][0])
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty, payload)

    def test_market_only_us_keeps_lg_and_enforces_actual_import_bind_save(self):
        original, request = self.new_request("미국 전자레인지를 분석해 줘.", key="market-only-us")
        policy = {"mode": "explicit_market", "market": "US", "market_quote": "미국", "user_quote": "미국"}
        self.assertEqual(self.policy(original, policy), {**policy, "brand": "LG전자"})
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty, self.payload(request=request))
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty,
            self.payload(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/us/fixture", request=request))
        reply = self.web.import_evidence(self.empty, self.payload(url="https://www.lg.com/us/fixture", request=request))
        self.load(Dataset(self.root / reply["data_path"]))
        turn = self.resolve(original, request, "LG-FIX-1")["turn"]
        saved = self.store.save_result(turn["session_id"], turn["turn_id"], "us-held", held(), 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, True)
        self.assertTrue(saved["accepted"])
        raw = self.store.db.execute("SELECT payload FROM conversation_requests WHERE request_key=?", (original["request_key"],)).fetchone()[0]
        self.assertEqual(json.loads(raw), original)

    def test_market_only_kr_keeps_lg_without_brand_literal(self):
        original, request = self.new_request("한국 전자레인지를 분석해 줘.", key="market-only-kr")
        policy = {"mode": "explicit_market", "market": "KR", "market_quote": "한국", "user_quote": "한국"}
        self.assertEqual(self.policy(original, policy), {**policy, "brand": "LG전자"})
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty,
            self.payload(url="https://www.lg.com/us/fixture", request=request))
        self.error("target_scope_mismatch", self.web.import_evidence, self.empty,
            self.payload(model="TO-FIX-1", maker="Toshiba", url="https://www.toshiba.com/kr/fixture", request=request))
        self.assertTrue(self.web.import_evidence(self.empty, self.payload(request=request))["structural_valid"])

    def test_market_only_forged_literal_and_brand_override_rejected(self):
        original, _ = self.new_request("한국 전자레인지를 분석해 줘.", key="market-only-forged")
        for policy in (
            {"mode": "explicit_market", "market": "US", "market_quote": "미국", "user_quote": "한국"},
            {"mode": "explicit_market", "market": "US", "market_quote": "한국", "user_quote": "한국"},
            {"mode": "explicit_market", "market": "KR", "market_quote": "전자레인지", "user_quote": "한국"},
            {"mode": "explicit_market", "market": "KR", "market_quote": "한국", "user_quote": "한국", "brand": "Toshiba"}):
            with self.subTest(policy=policy):
                self.error("selection_policy_conflict", self.policy, original, policy)
        self.assertEqual(SelectionPolicy(self.store.db).get(original["session_id"], original["request_key"])["mode"], "project_default")

    def test_market_only_wrong_quote_types_are_tool_errors_and_do_not_write(self):
        original, _ = self.new_request("미국 전자레인지를 분석해 줘.", key="market-only-types")
        before = self.store.db.execute("SELECT payload FROM request_selection_policies WHERE request_key=?", (original["request_key"],)).fetchone()[0]
        for quote in (None, 1, [], {}):
            with self.subTest(quote=quote):
                with self.assertRaises(ToolError):
                    self.policy(original, {"mode": "explicit_market", "market": "US", "market_quote": quote, "user_quote": "미국"})
        after = self.store.db.execute("SELECT payload FROM request_selection_policies WHERE request_key=?", (original["request_key"],)).fetchone()[0]
        self.assertEqual(before, after)

    def test_metadata_fingerprint_binds_full_reference_not_six_identity_fields(self):
        data = self.legacy_dataset()
        self.load(data)
        ref = data.reference(next(iter(data.sources.values())))
        variants = [copy.deepcopy(ref) for _ in range(4)]
        variants[1]["quote"] += " Changed quote."
        variants[2]["location"] = "Another original location"
        variants[3]["origin"]["source_url"] = "https://www.lge.co.kr/product/different-fixture"
        before = canonical(variants)
        joined = self.conv._source_metadata(variants)
        self.assertEqual(joined[0]["kind"], "product_fact")
        self.assertTrue(all(item["kind"] is None for item in joined[1:]))
        self.assertEqual([item["reference_fingerprint"] for item in joined], [fingerprint(ref) for ref in variants])
        self.assertEqual(len({item["reference_fingerprint"] for item in joined}), 4)
        self.assertEqual(canonical(variants), before)

    def rejected_export_fixture(self, references, key):
        planning = self.store.tools.prepare_planning_input({"session_id": "malformed-export", "request_key": key,
            "question": "Fictional rejected candidate fixture only", "model_id": "LG-FIX-1"})["input"]
        turn = self.store.start_turn(planning, True)
        candidate = held()
        candidate["evidence_refs"] = copy.deepcopy(references)
        before = canonical(candidate)
        response = self.conv.save_and_export({"session_id": turn["session_id"], "turn_id": turn["turn_id"],
            "result_key": key, "result": candidate, "expected_result_version": 0,
            "assessment": {"claim_checks": [], "feature_matches": [], "concept_links": []}, "report": False})
        self.assertFalse(response["save"]["accepted"])
        self.assertFalse(response["delivery_ready"])
        self.assertIsNone(response["export_error"])
        stored = tuple(self.store.db.execute("SELECT payload,payload_hash FROM results WHERE turn_id=?", (turn["turn_id"],)).fetchone())
        self.assertEqual(stored, (before, fingerprint(candidate)))
        export = json.loads((self.root / response["export"]["path"]).read_text(encoding="utf-8"))
        saved = next(item for item in export["turns"] if item["state"]["turn_id"] == turn["turn_id"])["candidates"][0]
        self.assertEqual(canonical(saved["result"]), before)
        self.assertEqual(tuple(self.store.db.execute("SELECT payload,payload_hash FROM results WHERE turn_id=?", (turn["turn_id"],)).fetchone()), stored)
        return saved["source_metadata"]

    def test_malformed_reference_items_are_retained_and_export_is_total(self):
        data = self.legacy_dataset()
        self.load(data)
        ref = data.reference(next(iter(data.sources.values())))
        bad_id = copy.deepcopy(ref)
        bad_id["source_id"] = [ref["source_id"]]
        bad_model = copy.deepcopy(ref)
        bad_model["model_id"] = {"not": "a string"}
        refs = [None, "literal-invalid-ref", [], {}, bad_id, bad_model]
        metadata = self.rejected_export_fixture(refs, "malformed-items")
        self.assertEqual(len(metadata), len(refs))
        self.assertTrue(all(item["kind"] is None for item in metadata))
        self.assertEqual([item["reference_index"] for item in metadata[:5]], list(range(5)))
        self.assertEqual(metadata[5]["reference_fingerprint"], fingerprint(bad_model))

    def test_nonlist_reference_payloads_are_retained_and_export_is_total(self):
        self.load(self.legacy_dataset())
        for number, value in enumerate((None, "literal-not-a-list", {"source_id": "not-a-list"})):
            with self.subTest(value=value):
                self.assertEqual(self.rejected_export_fixture(value, "malformed-list-"+str(number)),
                    [{"kind": None, "binding": "invalid_reference_list"}])

    def prior_scope_fixture(self, mode="explicit_brand_market"):
        model, maker, url = "TO-FIX-1", "Toshiba", "https://www.toshiba.com/us/fixture"
        if mode == "explicit_market":
            original, request = self.new_request("미국 전자레인지 개선안을 검토해 줘.", key="prior-market")
            policy = {"mode": mode, "market": "US", "market_quote": "미국", "user_quote": "미국", "brand": "LG전자"}
            self.policy(original, policy)
            model, maker, url = "LG-FIX-1", "LG전자", "https://www.lg.com/us/fixture"
        elif mode == "explicit_model":
            original, request = self.new_request("TO-FIX-1 모델을 검토해 줘.", key="prior-model", model_id=model)
            policy = request["selection_policy"]
        else:
            original, request = self.new_request("Toshiba 미국 전자레인지 개선안을 검토해 줘.", key="prior-brand")
            policy = {"mode": mode, "brand": maker, "market": "US", "market_quote": "미국", "user_quote": maker}
            self.policy(original, policy)
        reply = self.web.import_evidence(self.empty, self.payload(model=model, maker=maker, url=url, request=request))
        self.load(Dataset(self.root / reply["data_path"]))
        turn = self.resolve(original, request, model)["turn"]
        saved = self.store.save_result(turn["session_id"], turn["turn_id"], "prior-held", held(), 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, True)
        self.assertTrue(saved["accepted"])
        return original, policy, turn

    def test_followup_without_new_scope_inherits_foreign_brand_and_original_quotes(self):
        prior, policy, turn = self.prior_scope_fixture()
        before = tuple(self.store.db.execute("SELECT payload,payload_hash FROM results WHERE turn_id=?", (turn["turn_id"],)).fetchone())
        original = {**self.original, "question": "앞선 조건에서 검증 계획을 더 보완해 줘.", "request_key": "followup-no-scope", "prior_turn_id": turn["turn_id"]}
        response = self.conv.open_request(original)
        current = response["turn"]
        self.assertEqual(SelectionPolicy(self.store.db).get(current["session_id"], original["request_key"]), policy)
        self.assertNotIn(policy["user_quote"], original["question"])
        self.assertEqual(current["input"]["model_scope"], turn["input"]["model_scope"])
        self.assertFalse(response["previous"]["valid_for_current_context"])
        saved = self.store.save_result(current["session_id"], current["turn_id"], "followup-held", held(), 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, True)
        self.assertTrue(saved["accepted"])
        self.assertEqual(tuple(self.store.db.execute("SELECT payload,payload_hash FROM results WHERE turn_id=?", (turn["turn_id"],)).fetchone()), before)
        export = self.conv.export_session({"session_id": current["session_id"]})
        requests = json.loads((self.root / export["path"]).read_text(encoding="utf-8"))["requests"]
        self.assertEqual(next(r["input"] for r in requests if r["input"]["request_key"] == prior["request_key"]), prior)
        followup = next(r for r in requests if r["input"]["request_key"] == original["request_key"])
        self.assertEqual(followup["input"], original)
        self.assertEqual(followup["selection_policy"], policy)

    def test_followup_same_explicit_family_inherits_prior_brand_scope(self):
        _, policy, turn = self.prior_scope_fixture()
        original = {**self.original, "question": "같은 전자레인지 제품군 검토를 보완해 줘.", "request_key": "followup-same-family", "prior_turn_id": turn["turn_id"], "product_family": "microwave"}
        current = self.conv.open_request(original)["turn"]
        self.assertEqual(current["input"]["scope_mode"], "family_catalog")
        self.assertEqual(current["input"]["model_scope"], turn["input"]["model_scope"])
        self.assertEqual(SelectionPolicy(self.store.db).get(current["session_id"], original["request_key"]), policy)

    def test_followup_market_only_and_named_model_policies_inherit(self):
        # Independent methods above cover full accepted save; these two policy
        # variants must also bind through the real follow-up entry point.
        for mode in ("explicit_market", "explicit_model"):
            with self.subTest(mode=mode):
                if mode == "explicit_model":
                    # A second session keeps the two independent prior inputs
                    # from reusing handles or relying on invalidated rows.
                    self.original = {**self.original, "session_id": "model-prior-session"}
                _, policy, turn = self.prior_scope_fixture(mode)
                original = {**self.original, "question": "같은 제품의 확인 항목을 보완해 줘.", "request_key": "followup-"+mode, "prior_turn_id": turn["turn_id"]}
                current = self.conv.open_request(original)["turn"]
                self.assertEqual(SelectionPolicy(self.store.db).get(current["session_id"], original["request_key"]), policy)
                self.assertEqual(current["input"]["model_scope"], turn["input"]["model_scope"])

    def test_followup_new_family_and_explicit_model_do_not_inherit_foreign_policy(self):
        _, old_policy, turn = self.prior_scope_fixture()
        original = {**self.original, "question": "이제 냉장고 개선안을 검토해 줘.", "request_key": "followup-new-family", "prior_turn_id": turn["turn_id"], "product_family": "refrigerator"}
        response = self.conv.open_request(original)
        self.assertIsNone(response["turn_id"])
        self.assertEqual(response["selection_policy"], {"mode": "project_default", "brand": "LG전자", "market": "KR"})
        original_model = {**self.original, "question": "이제 LG-NEW-FIX 모델을 검토해 줘.", "request_key": "followup-new-model", "prior_turn_id": turn["turn_id"], "model_id": "LG-NEW-FIX"}
        response = self.conv.open_request(original_model)
        self.assertIsNone(response["turn_id"])
        self.assertEqual(response["selection_policy"], {"mode": "explicit_model", "model_id": "LG-NEW-FIX", "user_quote": "LG-NEW-FIX"})
        self.assertEqual(SelectionPolicy(self.store.db).get(turn["session_id"], "prior-brand"), old_policy)

    def test_followup_cannot_inherit_another_sessions_prior_policy(self):
        _, _, turn = self.prior_scope_fixture()
        original = {**self.original, "session_id": "other-session", "question": "앞선 제품을 다시 검토해 줘.", "request_key": "cross-session-followup", "prior_turn_id": turn["turn_id"]}
        self.error("turn_not_found", self.conv.open_request, original)
        self.assertIsNone(SelectionPolicy(self.store.db).get("other-session", original["request_key"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
