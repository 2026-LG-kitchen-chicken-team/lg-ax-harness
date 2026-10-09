"""Boundary checks for common tools; no model/Agent quality or market claims."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError, canonical, fingerprint, planning_input, strict_json
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.tools import ProductTools

SCOPE = {"model_id": "AX-R301", "model_version": "1.0", "document_version": "manual-r1"}

class CommonToolsTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "runtime-data").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="tools-test-", dir=ROOT / "runtime-data")
        self.base = Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to((ROOT / "runtime-data").resolve()))
        self.data = Dataset(ROOT / "data/synthetic/kitchen-v1")
        self.tools = ProductTools(self.data)
        self.db_path = self.base / "state.sqlite"
        self.store = StateStore(self.db_path, self.data)
        self.planning = strict_json((ROOT / "evals/development/planning-input.json").read_text(encoding="utf-8"))

    def tearDown(self):
        self.store.close()
        self.assertTrue(self.base.is_relative_to((ROOT / "runtime-data").resolve()))
        self.temp.cleanup()

    def error(self, code, call, *args):
        with self.assertRaises(ToolError) as caught:
            call(*args)
        self.assertEqual(caught.exception.code, code)

    def start(self):
        return self.store.start_turn(self.planning, True)["turn_id"]

    def result(self, revision=0):
        ids = ["DOC-AX-R301-1.0-01", "REV-AX-R301-1.0-02"]
        refs = self.tools.select_evidence(SCOPE, ids)["evidence_refs"]
        return {"status": "completed", "pains": [{"id": "pain-1", "text": "음식 이동 부담", "source_ids": [ids[1]]}],
                "existing_features": [{"id": "feature-1", "text": "선반 분리", "source_ids": [ids[0]]}],
                "remaining_pains": [], "concepts": [{"id": "concept-1", "text": "계약 시험용 임시 정리 순서 제안", "source_ids": ids,
                    "requirements": ["시험용 필수 필드"], "requires_hardware": False, "assumptions": ["실제 제안 품질 미검증"]}],
                "assumptions": ["합성 자료 기반 코드 계약 시험"], "evidence_refs": refs,
                "validation_findings": [], "revisions": revision, "usage_summary": {"status": "unknown"}}

    def save(self, turn, result=None, key="result-0", expected=0):
        return self.store.save_result(self.planning["session_id"], turn, key, self.result() if result is None else result, expected)

    def changed_catalog(self, transform, version=None):
        destination = self.base / ("catalog-" + str(len(list(self.base.glob("catalog-*")))))
        shutil.copytree(self.data.root, destination)
        records = [strict_json(line) for line in (destination / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
        transform(records)
        manifest = strict_json((destination / "manifest.json").read_text(encoding="utf-8"))
        if version:
            manifest["data_version"] = version
            for record in records:
                record["data_version"] = version
        for record in records:
            record["sha256"] = hashlib.sha256(record["text"].encode("utf-8")).hexdigest()
        (destination / "sources.jsonl").write_text("".join(canonical(s) + "\n" for s in records), encoding="utf-8")
        manifest["review_count"] = sum(r["kind"] == "review" for r in records)
        manifest["fact_count"] = sum(r["kind"] == "product_fact" for r in records)
        for entry in manifest["files"]:
            entry["sha256"] = hashlib.sha256((destination / entry["path"]).read_bytes()).hexdigest()
        (destination / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
        return destination

    def call_cli(self, operation, payload=None, extra=()):
        command = [sys.executable, str(ROOT / "product-tools/cli.py"), "--db", str(self.base / "cli.sqlite"), *extra, operation]
        return subprocess.run(command, input=canonical(payload or {}), text=True, encoding="utf-8", capture_output=True, timeout=10, cwd=ROOT)

    def test_dataset_counts_and_test_only_purpose(self):
        self.assertEqual(self.data.manifest["review_count"], 40)
        self.assertEqual(len({m["model_id"] for m in self.data.models}), 3)
        self.assertEqual(self.data.manifest["purpose"], "test_only")

    def test_exact_filter_excludes_other_models_and_versions(self):
        result = self.data.retrieve("review", SCOPE)
        self.assertEqual(result["total"], 10)
        self.assertTrue(all(all(r[k] == v for k, v in SCOPE.items()) for r in result["records"]))

    def test_unknown_model_scope_and_valid_empty_are_distinct(self):
        self.error("unknown_model", self.data.retrieve, "review", {**SCOPE, "model_id": "MISSING"})
        self.error("unknown_scope", self.data.retrieve, "review", {**SCOPE, "model_version": "9.0"})
        self.assertEqual(self.data.retrieve("review", SCOPE, "이 문장은 없다")["status"], "empty")

    def test_feature_not_documented_is_not_absent(self):
        found = self.data.retrieve("product_fact", SCOPE, feature_key="odor_sensor")
        self.assertEqual(found["feature_presence"], "not_documented")

    def test_query_filter_does_not_make_existing_feature_undocumented(self):
        found = self.data.retrieve("product_fact", SCOPE, "없는 문자열", feature_key="removable_shelf")
        self.assertEqual(found["status"], "empty")
        self.assertEqual(found["feature_presence"], "present")

    def test_conflicting_facts_preserve_both_and_need_review(self):
        def conflict(records):
            record = copy.deepcopy(records[0])
            record.update(source_id="CONFLICT-01", availability="explicitly_absent", text="조건이 다른 자료는 선반 분리 불가라고 기재한다.")
            records.append(record)
        alternate = Dataset(self.changed_catalog(conflict))
        report = alternate.retrieve("product_fact", SCOPE, feature_key="removable_shelf")
        self.assertEqual(report["feature_presence"], "conflicting")
        self.assertEqual(report["total"], 2)

    def test_file_integrity_failure(self):
        path = self.changed_catalog(lambda r: None)
        (path / "models.json").write_text("[]", encoding="utf-8")
        self.error("dataset_integrity", Dataset, path)

    def test_duplicate_source_id_rejected(self):
        path = self.changed_catalog(lambda r: r.append(copy.deepcopy(r[0])))
        self.error("invalid_dataset", Dataset, path)

    def test_missing_and_cross_model_evidence_rejected(self):
        self.error("source_not_found", self.tools.select_evidence, SCOPE, ["DOES-NOT-EXIST"])
        self.error("scope_mismatch", self.tools.select_evidence, SCOPE, ["DOC-AX-R302-1.0-01"])

    def test_reference_location_hash_quote_origin_are_checked(self):
        original = self.result()["evidence_refs"][0]
        for field, changed, expected in (("location", "other", "reference_mismatch"), ("sha256", "f" * 64, "reference_mismatch"), ("quote", "원문에 없는 인용", "quote_mismatch"), ("origin", {**original["origin"], "retrieved_date": "2026-10-11"}, "reference_mismatch")):
            with self.subTest(field=field):
                self.error(expected, self.tools.validate_source_refs, [{**original, field: changed}], [SCOPE])

    def test_invalid_source_calendar_date_rejected(self):
        ref = self.result()["evidence_refs"][0]
        ref["origin"]["retrieved_date"] = "2026-02-31"
        self.error("invalid_input", self.tools.validate_source_refs, [ref], [SCOPE])

    def test_opposite_claim_does_not_pass_semantic_review(self):
        result = self.result()
        result["existing_features"][0]["text"] = "선반 분리는 불가능하다"
        report = self.tools.validate_result_contract(self.planning, result)
        self.assertTrue(report["contract_valid"])
        self.assertEqual(report["semantic_status"], "unverified")
        self.assertFalse(report["acceptance_ready"])

    def test_source_instructions_remain_untrusted_data(self):
        exact = {**SCOPE, "model_id": "AX-R302"}
        result = self.data.retrieve("review", exact, "모델 필터")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["records"][0]["model_id"], "AX-R302")
        self.assertEqual(result["records"][0]["content_trust"], "untrusted_source_data")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 0)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            self.error("invalid_json", strict_json, raw)

    def test_boolean_count_rejected(self):
        planning = copy.deepcopy(self.planning)
        planning["constraints"]["max_concepts"] = True
        self.error("invalid_input", planning_input, planning)

    def test_missing_input_and_unknown_fields_rejected(self):
        self.error("invalid_input", planning_input, {"question": "only"})
        self.error("invalid_input", planning_input, {**self.planning, "execute_shell": "anything"})

    def test_more_than_three_concepts_and_hardware_violation(self):
        result = self.result()
        result["concepts"] = [{**result["concepts"][0], "id": f"c-{i}"} for i in range(4)]
        self.error("invalid_input", self.tools.validate_result_contract, self.planning, result)
        result = self.result()
        result["concepts"][0]["requires_hardware"] = True
        self.error("constraint_violation", self.tools.validate_result_contract, self.planning, result)

    def test_unreferenced_claim_and_unused_evidence_rejected(self):
        result = self.result()
        result["pains"][0]["source_ids"] = ["DOC-AX-R303-1.0-01"]
        self.error("missing_evidence", self.tools.validate_result_contract, self.planning, result)
        result = self.result()
        result["evidence_refs"].append(self.data.reference(self.data.source("REV-AX-R301-1.0-03")))
        self.error("unused_evidence", self.tools.validate_result_contract, self.planning, result)

    def test_request_replay_and_reopen_preserve_turn_revision(self):
        turn = self.start()
        self.save(turn)
        self.save(turn, self.result(1), "result-1", 1)
        self.store.close()
        self.store = StateStore(self.db_path, self.data)
        repeat = self.store.start_turn(self.planning, True)
        self.assertTrue(repeat["reused_request"])
        self.assertEqual(repeat["turn_id"], turn)
        self.assertEqual(repeat["revision_count"], 1)

    def test_request_key_conflict_preserves_original_input(self):
        turn = self.start()
        self.error("request_conflict", self.store.start_turn, {**self.planning, "question": "새 질문"}, True)
        self.assertEqual(self.store.get_turn(self.planning["session_id"], turn)["input"], self.planning)

    def test_new_user_turn_invalidates_old_result_preserves_history(self):
        turn = self.start()
        self.save(turn)
        new = self.store.start_turn({**self.planning, "request_key": "new", "question": "조건 변경"}, True)
        self.assertEqual(new["revision_count"], 0)
        old = self.store.get_turn(self.planning["session_id"], turn)
        self.assertFalse(old["valid"])
        self.assertIsNone(old["latest_result"])
        self.assertEqual(len(old["result_history"]), 1)
        self.error("stale_context", self.store.start_turn, self.planning, True)

    def test_changed_runtime_and_prompt_fingerprints_invalidate(self):
        turn = self.start()
        new_input = copy.deepcopy(self.planning)
        new_input["request_key"] = "new"
        new_input["runtime"]["settings_fingerprint"] = "changed-setting"
        new_input["workflow"]["prompt_fingerprint"] = "changed-prompt"
        self.store.start_turn(new_input, True)
        self.assertFalse(self.store.get_turn(self.planning["session_id"], turn)["valid"])

    def test_same_data_version_cannot_hide_changed_sources(self):
        alternate = Dataset(self.changed_catalog(lambda r: r[0].update(text="새 원문")))
        self.error("data_version_reused", StateStore, self.db_path, alternate)

    def test_new_data_version_invalidates_state_and_retrieval_cache(self):
        turn = self.start()
        self.store.retrieve("review", SCOPE)
        alternate = Dataset(self.changed_catalog(lambda r: r[-1].update(text="개정 리뷰"), "synthetic-updated-v2"))
        self.store.close()
        self.store = StateStore(self.db_path, alternate)
        self.assertFalse(self.store.get_turn(self.planning["session_id"], turn)["valid"])
        self.assertFalse(self.store.retrieve("review", SCOPE)["cache_hit"])

    def test_retrieval_cache_reused_and_tamper_detected(self):
        self.assertFalse(self.store.retrieve("review", SCOPE)["cache_hit"])
        self.assertTrue(self.store.retrieve("review", SCOPE)["cache_hit"])
        self.store.db.execute("UPDATE retrieval_cache SET payload='{}'")
        self.error("cache_integrity", self.store.retrieve, "review", SCOPE)

    def test_initial_plus_two_revisions_then_held(self):
        turn = self.start()
        for version in range(3):
            response = self.save(turn, self.result(version), f"result-{version}", version)
            self.assertTrue(response["accepted"])
            self.assertEqual(response["turn"]["revision_count"], version)
        limit = self.save(turn, self.result(2), "result-3", 3)
        self.assertFalse(limit["accepted"])
        self.assertEqual(limit["reason"], "business_revision_limit")
        self.assertEqual(limit["turn"]["status"], "held")
        self.assertEqual(len(limit["turn"]["result_history"]), 3)

    def test_invalid_candidates_consume_revisions_and_store_failure_reasons(self):
        turn = self.start()
        for version in range(3):
            result = self.result(version)
            result["evidence_refs"][0]["sha256"] = "f" * 64
            response = self.save(turn, result, f"bad-{version}", version)
            self.assertFalse(response["accepted"])
            self.assertEqual(response["reason"], "reference_mismatch")
            self.assertEqual(response["turn"]["revision_count"], version)
            self.assertIsNone(response["turn"]["latest_result"])
        response = self.save(turn, self.result(2), "bad-3", 3)
        self.assertEqual(response["reason"], "business_revision_limit")
        self.assertEqual(response["turn"]["status"], "held")

    def test_result_key_replay_is_idempotent_conflict_is_rejected(self):
        turn = self.start()
        self.save(turn)
        replay = self.save(turn)
        self.assertEqual(replay["turn"]["result_version"], 1)
        changed = self.result()
        changed["assumptions"] = ["changed"]
        self.error("result_conflict", self.save, turn, changed)

    def test_unobserved_runtime_prevents_business_result_reuse(self):
        turn = self.start()
        response = self.save(turn)
        self.assertFalse(response["turn"]["business_reuse_eligible"])
        self.assertIsNotNone(response["turn"]["latest_result"])

    def test_optimistic_version_conflict(self):
        turn = self.start()
        self.save(turn)
        self.error("state_conflict", self.save, turn, self.result(1), "other", 0)
        self.assertEqual(self.store.get_turn(self.planning["session_id"], turn)["result_version"], 1)

    def test_transaction_rolls_back_partial_result_on_db_failure(self):
        turn = self.start()
        self.store.db.execute("CREATE TRIGGER refuse_update BEFORE UPDATE ON turns BEGIN SELECT RAISE(ABORT, 'injected storage failure'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            self.save(turn)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM results").fetchone()[0], 0)
        self.assertEqual(self.store.get_turn(self.planning["session_id"], turn)["result_version"], 0)

    def test_stored_result_tamper_rejected(self):
        turn = self.start()
        self.save(turn)
        changed = self.result()
        changed["concepts"][0]["text"] = "changed"
        self.store.db.execute("UPDATE results SET payload=?", (canonical(changed),))
        self.error("result_integrity", self.store.get_turn, self.planning["session_id"], turn)

    def test_session_isolation_and_internal_failure_cannot_create_turn(self):
        turn = self.start()
        self.error("turn_not_found", self.store.get_turn, "another-session", turn)
        self.error("user_input_required", self.store.start_turn, {**self.planning, "request_key": "retry"}, False)

    def test_retry_count_persists_and_is_separate_from_business_revision(self):
        turn = self.start()
        args = (self.planning["session_id"], turn, "inv-1")
        request = fingerprint({"scope": SCOPE})
        self.store.invocation(*args, "retrieve_reviews", request)
        self.store.finish_invocation(*args, "failed", True)
        self.store.close()
        self.store = StateStore(self.db_path, self.data)
        retried = self.store.invocation(*args, "retrieve_reviews", request)
        self.assertEqual(retried["attempts"], 2)
        self.store.finish_invocation(*args, "failed", True)
        self.error("retry_not_allowed", self.store.invocation, *args, "retrieve_reviews", request)
        self.assertEqual(self.store.get_turn(self.planning["session_id"], turn)["revision_count"], 0)

    def test_nonretryable_failure_and_registered_call_limit(self):
        turn = self.start()
        for number in range(40):
            args = (self.planning["session_id"], turn, f"inv-{number}")
            self.store.invocation(*args, "retrieve_reviews", "a" * 64)
            self.store.finish_invocation(*args, "failed", False)
        self.error("retry_not_allowed", self.store.invocation, self.planning["session_id"], turn, "inv-0", "retrieve_reviews", "a" * 64)
        self.error("tool_call_limit", self.store.invocation, self.planning["session_id"], turn, "inv-40", "retrieve_reviews", "a" * 64)

    def test_unknown_zero_failed_usage_and_observation_replay(self):
        turn = self.start()
        call = {"call_id": "call-1", "status": "failed", "input_tokens": 100, "output_tokens": 0, "cache_tokens": None, "reasoning_tokens": None, "cost_usd": "0.01"}
        self.store.record_usage(self.planning["session_id"], turn, call)
        self.store.record_usage(self.planning["session_id"], turn, call)
        other = {**call, "call_id": "call-2", "status": "succeeded", "input_tokens": None, "output_tokens": None, "cost_usd": None}
        summary = self.store.record_usage(self.planning["session_id"], turn, other)
        self.assertEqual(summary["recorded_calls"], 2)
        self.assertEqual(summary["totals"]["input_tokens"], 100)
        self.assertEqual(summary["totals"]["output_tokens"], 0)
        self.assertEqual(summary["unknown_counts"]["input_tokens"], 1)
        self.assertIsNone(summary["totals"]["cache_tokens"])
        self.assertEqual(summary["totals"]["cost_usd"], "0.01")
        self.assertIsNone(summary["remaining_budget"])
        self.assertEqual(summary["status"], "partially_measured")
        self.store.start_turn({**self.planning, "request_key": "new-usage-turn", "question": "다음 질문"}, True)
        self.assertEqual(self.store.usage_summary(self.planning["session_id"])["recorded_calls"], 2)

    def test_usage_invalid_types_and_call_conflict(self):
        turn = self.start()
        call = {"call_id": "call-1", "status": "failed", "input_tokens": None, "output_tokens": None, "cache_tokens": None, "reasoning_tokens": None, "cost_usd": None}
        self.error("invalid_input", self.store.record_usage, self.planning["session_id"], turn, {**call, "input_tokens": True})
        self.error("invalid_input", self.store.record_usage, self.planning["session_id"], turn, {**call, "cost_usd": "NaN"})
        self.store.record_usage(self.planning["session_id"], turn, call)
        self.error("usage_conflict", self.store.record_usage, self.planning["session_id"], turn, {**call, "status": "succeeded"})

    def test_real_dataset_and_low_input_model_selection(self):
        real = Dataset(ROOT / "data/business/lg-pilot-v1")
        tool = ProductTools(real)
        result = tool.prepare_planning_input({"model_id": "S836GBB122", "session_id": "x", "request_key": "k"})
        self.assertFalse(real.synthetic)
        self.assertEqual(result["review_count"], 3)
        self.assertEqual(result["model"]["dimensions_mm"], {"width": 913, "height": 1790, "depth": 913})
        self.assertIsNone(result["model"]["layout"]["internal_dimensions_mm"])
        self.assertEqual(result["input"]["model_scope"][0]["model_version"], "unspecified")

    def test_real_review_provenance_and_no_fake_purchase_verification(self):
        real = Dataset(ROOT / "data/business/lg-pilot-v1")
        reviews = real.retrieve("review", {"model_id": "S836GBB122", "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10"})
        self.assertTrue(all(r["origin"]["representation"] == "excerpt" and r["origin"]["source_url"].startswith("https://www.lge.co.kr/") for r in reviews["records"]))
        self.assertTrue(all(r["origin"]["purchase_verified"] is None for r in reviews["records"]))
        self.assertLessEqual(sum(len(r["text"].split()) for r in reviews["records"]), 25)

    def test_ambiguous_model_selection_requests_version(self):
        self.error("needs_input", self.tools.prepare_planning_input, {"model_id": "AX-R301", "session_id": "x", "request_key": "k"})

    def test_eval_fixtures_are_separate_and_reference_existing_sources(self):
        development = strict_json((ROOT / "evals/development/cases.json").read_text(encoding="utf-8"))
        evaluation = strict_json((ROOT / "evals/judge/cases.json").read_text(encoding="utf-8"))
        real_cases = strict_json((ROOT / "evals/judge/real-pilot-cases.json").read_text(encoding="utf-8"))
        self.assertFalse({c["user_turns"][0] for c in development["cases"]} & {c["user_turns"][0] for c in evaluation["cases"]})
        for dataset, cases in ((self.data, development), (self.data, evaluation), (Dataset(ROOT / "data/business/lg-pilot-v1"), real_cases)):
            for case in cases["cases"]:
                for ref in case["fixture_refs"]:
                    dataset.source(ref)
        self.assertEqual(evaluation["model_execution_status"], "not_run")

    def test_cli_default_real_doctor_and_error_exit(self):
        result = self.call_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(strict_json(result.stdout)["result"]["synthetic"])
        result = self.call_cli("prepare_planning_input", {"model_id": "NOT-A-MODEL", "session_id": "x", "request_key": "k"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(strict_json(result.stdout)["error"]["code"], "unknown_model")

    def test_cli_rejects_db_outside_project_runtime_folder(self):
        result = self.call_cli("doctor", extra=("--db", str(ROOT / "outside.sqlite")))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(strict_json(result.stdout)["error"]["code"], "invalid_path")
        self.assertFalse((ROOT / "outside.sqlite").exists())

if __name__ == "__main__":
    unittest.main()
