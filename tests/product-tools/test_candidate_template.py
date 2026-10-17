"""Blank envelope cannot invent answers, reset revisions or escape bundle bounds."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'product-tools'))
from product_tools.contracts import ToolError, canonical
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.payload import candidate_template
from product_tools.state import StateStore


class CandidateTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ('skills/manifest.json', 'agents/product-planning.md'):
            p = self.root/name; p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/name, p)
        self.store = StateStore(self.root/'runtime-data/product.sqlite', Dataset(ROOT/'data/business/lg-kitchen-v4'))
        self.conv = Conversation(self.store, self.root)
        self.request = {'question': '임의 실제 질문', 'model_id': 'DUBJ2EA', 'user_submitted': True, 'request_key': 'one', 'session_id': 'one'}

    def tearDown(self): self.store.close(); self.tmp.cleanup()

    def test_blank_rejected_and_replay_keeps_same_version(self):
        first = self.conv.open_request_bundle(self.request)
        template = first['candidate_template']
        self.assertEqual(template['result']['status'], '')
        self.assertEqual(template, self.conv.open_request_bundle(self.request)['candidate_template'])
        self.assertFalse(self.conv.save_and_export(template)['save']['accepted'])
        next_value = self.conv.open_request_bundle(self.request)['candidate_template']
        self.assertEqual(next_value['expected_result_version'], 1)
        self.assertEqual(next_value['result']['revisions'], 1)
        self.assertNotEqual(next_value['result_key'], template['result_key'])

    def test_authored_hold_saves_and_keeps_unknown_usage(self):
        value = self.conv.open_request_bundle(self.request)
        template = value['candidate_template']
        template['result'].update(status='held', validation_findings=['실제 미확인 조건'])
        saved = self.conv.save_and_export(template)
        self.assertTrue(saved['delivery_ready'])
        self.assertEqual(template['planner_insights'], {'concept_titles': {}, 'summaries': {}})
        self.assertEqual(saved['web_result']['planner_insights']['status'], 'not_provided')
        self.assertFalse((self.root/'runtime-data/visual-viewer').exists())
        self.assertEqual(saved['export']['usage_summary']['status'], 'unknown')
        self.assertLess(len(canonical(value).encode()), 63001)

    def test_exhaustion_omits_template_without_resetting(self):
        for n in range(3):
            value = self.conv.open_request_bundle(self.request)
            self.conv.save_and_export(value['candidate_template'])
        value = self.conv.open_request_bundle(self.request)
        self.assertIsNone(value['bundle'])
        self.assertNotIn('candidate_template', value)
        self.assertEqual(value['turn']['result_version'], 3)

    def test_pure_helper_rejects_stale_terminal_and_bad_version(self):
        turn = self.conv.open_request_bundle(self.request)['turn']
        for extra in ({'valid': False}, {'status': 'failed'}, {'status': 'cancelled'}, {'result_version': True}, {'result_version': 3}):
            with self.assertRaises(ToolError): candidate_template({**turn, **extra})
        for version in range(3):
            value = candidate_template({**turn, 'result_version': version})
            value['result']['pains'].append({'text': 'local mutation'})
            self.assertEqual(candidate_template({**turn, 'result_version': version})['result']['pains'], [])

    def test_existing_custom_candidate_key_cannot_block_new_revision(self):
        first = self.conv.open_request_bundle(self.request)['candidate_template']
        first['result_key'] = 'candidate-1'
        first['result'].update(status='held', validation_findings=['첫 자료 부족'])
        self.assertTrue(self.conv.save_and_export(first)['save']['accepted'])
        next_value = self.conv.open_request_bundle(self.request)['candidate_template']
        self.assertNotEqual(next_value['result_key'], first['result_key'])
        self.assertEqual(next_value, self.conv.open_request_bundle(self.request)['candidate_template'])
        next_value['result'].update(status='held', validation_findings=['수정한 실제 미확인'])
        self.assertTrue(self.conv.save_and_export(next_value)['save']['accepted'])
        self.assertEqual(self.conv.open_request_bundle(self.request)['turn']['result_version'], 2)

    def test_multiple_custom_keys_avoid_collision_without_resetting_budget(self):
        for key in ('candidate-2-1', 'candidate-2'):
            value = self.conv.open_request_bundle(self.request)['candidate_template']
            value['result_key'] = key
            value['result'].update(status='held', validation_findings=['실제 부족'])
            self.assertTrue(self.conv.save_and_export(value)['save']['accepted'])
        value = self.conv.open_request_bundle(self.request)['candidate_template']
        self.assertEqual(value['expected_result_version'], 2)
        self.assertNotIn(value['result_key'], ('candidate-2-1', 'candidate-2'))


if __name__ == '__main__': unittest.main()
