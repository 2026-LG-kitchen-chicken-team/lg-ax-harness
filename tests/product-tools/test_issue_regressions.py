"""GitHub #4/#5: malformed review persistence and portable export bytes."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).parent))
import test_planning_web as _web
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.planning import review_product_result
from product_tools.state import StateStore


class IssueRegressions(unittest.TestCase):
    candidate = _web.PlanningWebTests.candidate

    def setUp(self):
        _web.PlanningWebTests.setUp(self)
        self.store = StateStore(self.workspace / "product.sqlite", self.data)
        self.conv = Conversation(self.store, self.workspace)

    def tearDown(self):
        self.store.close()
        _web.PlanningWebTests.tearDown(self)

    def test_nested_review_ids_fail_as_contract_errors_before_hash_lookup(self):
        fields = [("feature_matches", "remaining_pain_id", False),
                  ("feature_matches", "pain_id", False),
                  ("feature_matches", "feature_source_ids", True),
                  ("concept_links", "concept_id", False),
                  ("concept_links", "remaining_pain_ids", True),
                  ("concept_links", "geometry_source_ids", True)]
        for section, field, array in fields:
            for invalid in ([], {}, True):
                with self.subTest(field=field, invalid=invalid):
                    payload = self.candidate()
                    payload["assessment"][section][0][field] = [invalid] if array else invalid
                    with self.assertRaises(ToolError) as caught:
                        review_product_result(self.data, payload)
                    self.assertEqual(caught.exception.code, "invalid_input")

    def test_malformed_review_preserves_three_attempts_replay_and_limit(self):
        payload = self.candidate()
        turn = self.store.start_turn(payload["input"], True)
        payload["assessment"]["feature_matches"][0]["remaining_pain_id"] = ["r1"]
        saved_inputs = []
        for revision in range(3):
            result = copy.deepcopy(payload["result"])
            result["revisions"] = revision
            request = {"session_id": turn["session_id"], "turn_id": turn["turn_id"],
                       "result_key": "rejected-" + str(revision), "expected_result_version": revision,
                       "result": result, "assessment": payload["assessment"]}
            response = self.conv.save_and_export(request)
            self.assertFalse(response["save"]["accepted"])
            self.assertEqual(response["save"]["reason"], "invalid_input")
            self.assertEqual(response["save"]["turn"]["result_version"], revision + 1)
            self.assertFalse(response["delivery_ready"])
            self.assertIsNotNone(response["export"])
            replay = self.conv.save_and_export(request)
            self.assertEqual(replay["save"]["receipt"], response["save"]["receipt"])
            saved_inputs.append(request)
        fourth = {**saved_inputs[-1], "result_key": "fourth", "expected_result_version": 3}
        response = self.conv.save_and_export(fourth)
        self.assertEqual(response["save"]["reason"], "business_revision_limit")
        self.assertEqual(response["save"]["turn"]["status"], "held")
        self.assertEqual(response["save"]["turn"]["result_version"], 3)
        exported = json.loads((self.workspace / response["export"]["path"]).read_bytes())
        candidates = exported["turns"][0]["candidates"]
        self.assertEqual(len(candidates), 3)
        self.assertEqual([c["result_key"] for c in candidates], [x["result_key"] for x in saved_inputs])
        self.assertTrue(all(c["validation"]["assessment"] == payload["assessment"] for c in candidates))

    def test_logical_session_ids_export_as_regular_copyable_zip_files(self):
        handles = []
        for session in ("audit:export-colon", "CON", "aux", "trailing.", "normal-session"):
            self.conv.open_request({"question": "제품을 아직 선택하지 않은 실제 요청",
                                    "session_id": session, "request_key": "request-1", "user_submitted": True})
            exported = self.conv.export_session({"session_id": session})
            path = self.workspace / exported["path"]
            self.assertIn(path.name, [p.name for p in path.parent.iterdir()])
            self.assertNotIn(":", path.name)
            raw = path.read_bytes()
            self.assertEqual(json.loads(raw)["session_id"], session)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), exported["sha256"])
            self.assertEqual(self.conv.export_session({"session_id": session})["path"], exported["path"])
            handles.append((path.name, raw))
        folder = self.workspace / "runtime-data/exports"
        copied = self.workspace / "ordinary-copy"
        shutil.copytree(folder, copied)
        archive = self.workspace / "ordinary.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for path in folder.iterdir():
                output.write(path, path.name)
        with zipfile.ZipFile(archive) as saved:
            for name, raw in handles:
                self.assertEqual(saved.read(name), raw)
                self.assertEqual((copied / name).read_bytes(), raw)
