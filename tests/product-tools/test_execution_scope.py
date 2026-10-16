"""Bound export recovery and explicit new-task scope; local fixtures, no native/model calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.execution_context import operation_dataset
from product_tools.selection import SelectionPolicy
from product_tools.state import StateStore


class ExecutionScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for rel in ("skills/manifest.json", "agents/product-planning.md"):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        for source, target in (("data/business/lg-kitchen-v4", "data/business/bound"),
                               ("data/business/empty", "data/business/empty"),
                               ("data/synthetic/kitchen-v1", "data/synthetic/other")):
            shutil.copytree(ROOT / source, self.root / target)
        self.data = Dataset(self.root / "data/business/bound")
        self.path = self.root / "runtime-data/product.sqlite"
        self.store = StateStore(self.path, self.data, workspace=self.root)
        self.conv = Conversation(self.store, self.root)
        self.addCleanup(lambda: self.store.close())
        self.first = self.data.models[0]
        self.other = next(m for m in self.data.models if m["product_family"] != self.first["product_family"])

    def exact(self, model):
        return {k: model[k] for k in ("model_id", "model_version", "document_version")}

    def opened(self, **extra):
        return self.conv.open_product_workflow({"question": self.first["model_id"] + " fixture request",
            "user_submitted": True, "session_id": "scope", "request_key": "first",
            **self.exact(self.first), **extra})["turn"]

    def follow(self, prior, **extra):
        return {"question": "New user question", "user_submitted": True, "session_id": prior["session_id"],
                "request_key": "next", "prior_turn_id": prior["turn_id"], **extra}

    def error(self, code, callback):
        with self.assertRaises(ToolError) as error:
            callback()
        self.assertEqual(error.exception.code, code)
        return str(error.exception)

    def reload(self, data):
        self.store.close()
        self.store = StateStore(self.path, data, workspace=self.root)
        self.conv = Conversation(self.store, self.root)

    def test_timed_workflow_accepts_explicit_family_runtime_and_conditions(self):
        old = self.opened()
        runtime = {"engine": "fixture", "engine_version": None, "model_id": None, "settings_fingerprint": None}
        constraints = {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": []}
        response = self.conv.open_product_workflow(self.follow(old, product_family=self.other["product_family"],
            scope_mode="family_catalog", constraints=constraints, runtime=runtime))
        planning = response["turn"]["input"]
        self.assertEqual(planning["product_family"], self.other["product_family"])
        self.assertEqual(planning["constraints"], constraints)
        self.assertEqual(planning["runtime"], runtime)
        self.assertEqual(response["previous"]["turn_id"], old["turn_id"])

    def test_omitted_prior_scope_preserves_real_followup_scope_versions_constraints_policy(self):
        constraints = {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": ["fixture"]}
        old = self.opened(constraints=constraints)
        policy = SelectionPolicy(self.store.db).get("scope", "first")
        new = self.conv.open_product_workflow(self.follow(old))["turn"]
        self.assertEqual(new["input"]["model_scope"], old["input"]["model_scope"])
        self.assertEqual(new["input"]["constraints"], constraints)
        self.assertEqual(SelectionPolicy(self.store.db).get("scope", "next"), policy)

    def test_reference_only_waits_for_new_selection_and_does_not_inherit_policy(self):
        old = self.opened(constraints={"max_concepts": 1, "hardware_allowed": False, "exclude_pains": ["old"]})
        payload = self.follow(old, prior_scope="reference_only")
        pending = self.conv.open_product_workflow(payload)
        self.assertEqual(pending["status"], "needs_input")
        self.assertIsNone(pending["turn_id"])
        self.assertEqual(SelectionPolicy(self.store.db).get("scope", "next")["mode"], "project_default")
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 1)
        self.conv.record_workflow_event({"research_id": pending["research_id"], "event_key": "stop",
            "kind": "research_stop", "data": {"code": "sources_exhausted",
                "basis": "Fixed local test catalog only; no online collection was performed",
                "new_findings": [], "remaining_scope": []}})
        resolved = self.conv.resolve_request({"session_id": "scope", "request_key": "next",
            "expected_request_version": 0, "event_key": "resolve", "selection": self.exact(self.other)})
        self.assertEqual(resolved["turn"]["input"]["model_scope"], [self.exact(self.other)])
        self.assertEqual(resolved["turn"]["input"]["constraints"]["max_concepts"], 3)
        self.assertEqual(resolved["previous"]["turn_id"], old["turn_id"])
        original = json.loads(self.store.db.execute("SELECT payload FROM conversation_requests WHERE request_key='next'").fetchone()[0])
        self.assertEqual(original["prior_scope"], "reference_only")
        self.assertEqual(original["question"], payload["question"])

    def test_reference_only_same_product_is_new_work_without_inherited_conditions(self):
        old = self.opened(constraints={"max_concepts": 1, "hardware_allowed": False, "exclude_pains": ["old"]})
        payload = self.follow(old, prior_scope="reference_only", model_id=self.first["model_id"])
        response = self.conv.open_product_workflow(payload)
        self.assertNotEqual(response["turn"]["turn_id"], old["turn_id"])
        self.assertEqual(response["turn"]["input"]["constraints"]["max_concepts"], 3)
        again = self.conv.open_product_workflow(payload)
        self.assertEqual(again["turn"]["turn_id"], response["turn"]["turn_id"])
        self.error("request_conflict", lambda: self.conv.open_product_workflow({**payload, "prior_scope": "inherit"}))

    def test_bad_prior_mode_and_cross_session_do_not_create_requests_or_clocks(self):
        old = self.opened()
        self.error("invalid_input", lambda: self.conv.open_product_workflow(self.follow(old, prior_scope="guess")))
        self.error("turn_not_found", lambda: self.conv.open_product_workflow(self.follow(old, session_id="other", prior_scope="reference_only")))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM conversation_requests").fetchone()[0], 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM product_workflows").fetchone()[0], 1)

    def test_omitted_export_data_recovers_only_bound_internal_relative_catalog(self):
        old = self.opened()
        path = self.store.db.execute("SELECT dataset_path FROM turns").fetchone()[0]
        self.assertEqual(path, "data/business/bound")
        selected = operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"})
        self.assertEqual(selected.fingerprint, self.data.fingerprint)
        self.assertNotIn("dataset_path", self.store.get_turn("scope", old["turn_id"]))
        exported = self.conv.export_session({"session_id": "scope"})
        self.assertNotIn(str(self.root), (self.root / exported["path"]).read_text(encoding="utf-8"))

    def test_explicit_data_and_start_operations_are_never_replaced(self):
        self.opened()
        empty = self.root / "data/business/empty"
        self.assertEqual(operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"}, empty).root, empty)
        self.assertEqual(operation_dataset(self.root, self.path, "open_product_workflow", {}).root, empty)
        self.assertEqual(operation_dataset(self.root, self.path, "list_models", {}).root, empty)

    def test_legacy_missing_escaping_or_changed_binding_requires_explicit_data(self):
        self.opened()
        for invalid in (None, "../outside", str(self.root / "data/business/bound"), "data/missing"):
            with self.subTest(path=invalid):
                self.store.db.execute("UPDATE turns SET dataset_path=?", (invalid,))
                message = self.error("catalog_context_required", lambda: operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"}))
                self.assertIn("--data", message)
        self.store.db.execute("UPDATE turns SET dataset_path='data/business/bound',dataset_hash=?", ("0" * 64,))
        self.error("catalog_context_mismatch", lambda: operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"}))
        self.assertFalse((self.root / "runtime-data/exports").exists())

    def test_pending_new_request_does_not_replace_latest_bound_turn_or_invent_completion(self):
        old = self.opened()
        self.reload(Dataset(self.root / "data/business/empty"))
        pending = self.conv.open_request({"question": "separate unresolved task", "user_submitted": True,
            "session_id": "scope", "request_key": "pending"})
        self.assertIsNone(pending["turn_id"])
        self.assertEqual(operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"}).fingerprint, self.data.fingerprint)
        self.reload(self.data)
        exported = self.conv.export_session({"session_id": "scope"})
        value = json.loads((self.root / exported["path"]).read_text(encoding="utf-8"))
        self.assertEqual(value["turns"][-1]["state"]["turn_id"], old["turn_id"])
        waiting = next(r for r in value["requests"] if r["input"]["request_key"] == "pending")
        self.assertIsNone(waiting["turn_id"])
        self.assertEqual(waiting["response"]["status"], "needs_input")

    def test_legacy_schema_without_catalog_column_requires_explicit_data(self):
        self.opened()
        self.store.db.execute("ALTER TABLE turns DROP COLUMN dataset_path")
        self.error("catalog_context_required", lambda: operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"}))
        # Explicit legacy loading still works; reinitialization migrates only
        # the nullable internal column and does not fabricate the old path.
        self.reload(self.data)
        self.assertIsNone(self.store.db.execute("SELECT dataset_path FROM turns").fetchone()[0])

    def test_latest_cancelled_turn_selects_its_catalog_without_reviving_older_result(self):
        self.opened()
        other = Dataset(self.root / "data/synthetic/other")
        self.reload(other)
        new = self.conv.open_request({"question": "new fixture model", "user_submitted": True,
            "session_id": "scope", "request_key": "cancelled", **self.exact(other.models[0])})["turn"]
        self.store.cancel_turn("scope", new["turn_id"], "cancel", "explicit fixture cancellation", 0, True)
        selected = operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"})
        self.assertEqual(selected.fingerprint, other.fingerprint)
        exported = self.conv.export_session({"session_id": "scope"})
        last = json.loads((self.root / exported["path"]).read_text(encoding="utf-8"))["turns"][-1]["state"]
        self.assertEqual(last["status"], "cancelled")
        self.assertIsNone(last["latest_result"])

    def test_actual_cli_omission_preserves_saved_result_and_original_data_binding(self):
        old = self.opened()
        held = {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [],
            "assumptions": [], "evidence_refs": [], "validation_findings": ["Fixture only"], "revisions": 0,
            "usage_summary": {"status": "unknown"}}
        saved = self.store.save_result("scope", old["turn_id"], "held", held, 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, require_review=True)
        self.assertTrue(saved["accepted"])
        spec = importlib.util.spec_from_file_location("execution_scope_cli", ROOT / "product-tools/cli.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        output = io.StringIO()
        with patch.object(cli, "ROOT", self.root), patch.object(sys, "argv", ["cli.py", "export_session"]), \
                patch.object(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b'{"session_id":"scope"}'))), contextlib.redirect_stdout(output):
            code = cli.main()
        self.assertEqual(code, 0, output.getvalue())
        report = json.loads(output.getvalue())["result"]
        exported = json.loads((self.root / report["path"]).read_text(encoding="utf-8"))
        latest = exported["turns"][-1]
        self.assertTrue(latest["state"]["valid"])
        self.assertEqual(latest["state"]["latest_result"], held)
        self.assertEqual(latest["web_binding"]["data_sha256"], self.data.fingerprint)

    def test_catalog_recovery_does_not_revive_a_result_from_changed_code(self):
        old = self.opened()
        held = {"status": "held", "pains": [], "existing_features": [], "remaining_pains": [], "concepts": [],
            "assumptions": [], "evidence_refs": [], "validation_findings": ["Fixture only"], "revisions": 0,
            "usage_summary": {"status": "unknown"}}
        self.store.save_result("scope", old["turn_id"], "held", held, 0,
            {"claim_checks": [], "feature_matches": [], "concept_links": []}, require_review=True)
        self.store.db.execute("UPDATE turns SET code_hash=?", ("0" * 64,))
        selected = operation_dataset(self.root, self.path, "export_session", {"session_id": "scope"})
        self.assertEqual(selected.fingerprint, self.data.fingerprint)
        exported = self.conv.export_session({"session_id": "scope"})
        latest = json.loads((self.root / exported["path"]).read_text(encoding="utf-8"))["turns"][-1]
        self.assertFalse(latest["state"]["valid"])
        self.assertIsNone(latest["state"]["latest_result"])
        self.assertEqual(latest["candidates"][0]["result"], held)


if __name__ == "__main__":
    unittest.main()
