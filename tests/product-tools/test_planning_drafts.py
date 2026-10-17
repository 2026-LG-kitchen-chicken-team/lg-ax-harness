"""Authored draft/decision identity, persistence and safety; no model quality claim."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import test_planner_insights as insights
import test_family_intake as family
from product_tools.contracts import ToolError, canonical
from product_tools.planning import review_product_result
from product_tools.reviewer_packet import ReviewPackets


class PlanningDraftTests(unittest.TestCase):
    setUp = insights.PlannerInsightsTests.setUp
    candidate = insights.PlannerInsightsTests.candidate

    def authored(self, version=0):
        value = self.candidate(version)
        value['result']['concepts'][0]['work_draft'] = {
            'title': '계약 시험용 요구사항 초안',
            'columns': ['사용 상황', '바꾸는 행동', '완료 기준'],
            'rows': [['위치 확인', '사용자가 보관 위치를 기록한다.', '기록한 위치를 다시 볼 수 있다.']]}
        value['result']['concepts'][0]['implementation_steps'] = ['기획자가 흐름을 검토하고 수정한다.']
        value['result']['planning_decision'] = {
            'summary': '사용 과업과 직접 연결되는 안부터 구체화한다.',
            'selected_concept_ids': ['c1'],
            'comparisons': [{'concept_id': 'c1', 'reason': '문제와 바뀌는 행동이 연결된다.',
                             'tradeoff': '현장 동선은 실제 확인한다.'}]}
        return value

    def invalid(self, mutation, code='invalid_input'):
        value = self.authored()
        mutation(value['result'])
        with self.assertRaises(ToolError) as error:
            self.store.tools.validate_result_contract(self.current['input'], value['result'])
        self.assertEqual(error.exception.code, code)

    def test_legacy_result_still_saves_without_new_fields(self):
        value = self.candidate()
        saved = self.conv.save_and_export(value)
        self.assertTrue(saved['save']['accepted'])
        self.assertNotIn('planning_decision', self.store.get_turn(**self.handle)['latest_result'])

    def test_decision_and_draft_survive_review_packet_current_export_web_completion(self):
        value = self.authored()
        original = copy.deepcopy(value['result'])
        path = self.root / 'runtime-data/candidate.json'
        path.write_bytes(canonical(value).encode())
        packets = ReviewPackets(self.store, self.root)
        packet = packets.prepare_review_packet({**self.handle, 'candidate_path': 'runtime-data/candidate.json',
                                                'packet_key': 'draft-review'})
        self.assertTrue(packet['ready'])
        body = json.loads((self.root / packet['packet_path']).read_bytes())
        self.assertEqual(body['candidate']['result'], original)
        self.assertTrue(packets.verify_review_packet({**self.handle, 'packet_path': packet['packet_path'],
                                                      'packet_sha256': packet['packet_sha256']})['ready'])
        saved = self.conv.save_and_export(value)
        self.assertTrue(saved['save']['accepted'])
        self.assertTrue(saved['web_ready'])
        self.assertEqual(self.store.get_turn(**self.handle)['latest_result'], original)
        exported = json.loads((self.root / saved['export']['path']).read_bytes())
        self.assertEqual(exported['turns'][-1]['candidates'][-1]['result'], original)
        web = json.loads((self.root / saved['web_result']['path']).read_bytes())
        self.assertEqual(web['result'], original)
        completion = json.loads((self.root / saved['completion_summary']['path']).read_bytes())
        self.assertEqual(completion['planning_decision'], original['planning_decision'])
        self.assertEqual(completion['concepts'][0]['work_draft'], original['concepts'][0]['work_draft'])
        self.assertEqual(web['binding']['result_sha256'], saved['completion_summary']['binding']['result_sha256'])
        self.assertNotIn('실제 제품 구현과 효과 측정 전', completion['text'])
        self.assertIn(original['planning_decision']['summary'], completion['text'])

    def test_comparison_only_can_select_nothing_without_draft(self):
        value = self.authored()
        value['result']['planning_decision']['selected_concept_ids'] = []
        del value['result']['concepts'][0]['work_draft']
        self.assertTrue(self.conv.save_and_export(value)['save']['accepted'])

    def test_two_user_selected_drafts_are_not_forced_to_one(self):
        value = self.authored()
        second = copy.deepcopy(value['result']['concepts'][0])
        second['id'] = 'c2'
        second['work_draft']['title'] = '두 번째 작성 초안'
        value['result']['concepts'].append(second)
        check = copy.deepcopy(value['assessment']['claim_checks'][-1]); check['claim_id'] = 'c2'
        value['assessment']['claim_checks'].append(check)
        link = copy.deepcopy(value['assessment']['concept_links'][0]); link['concept_id'] = 'c2'
        value['assessment']['concept_links'].append(link)
        decision = value['result']['planning_decision']
        decision['selected_concept_ids'].append('c2')
        decision['comparisons'].append({'concept_id': 'c2', 'reason': '별도 작업 흐름', 'tradeoff': '추가 확인'})
        self.assertTrue(self.conv.save_and_export(value)['save']['accepted'])

    def test_dangling_duplicate_or_incomplete_comparisons_are_rejected(self):
        mutations = [lambda d:d['planning_decision'].update(selected_concept_ids=['old']),
                     lambda d:d['planning_decision'].update(selected_concept_ids=['c1', 'c1']),
                     lambda d:d['planning_decision'].update(comparisons=[]),
                     lambda d:d['planning_decision']['comparisons'][0].update(concept_id='other'),
                     lambda d:d['planning_decision']['comparisons'].append(copy.deepcopy(d['planning_decision']['comparisons'][0]))]
        for mutation in mutations:
            with self.subTest(mutation=mutation): self.invalid(mutation)

    def test_decision_rejects_empty_summary_extra_keys_and_nontext(self):
        mutations = [lambda d:d['planning_decision'].update(summary=''),
                     lambda d:d['planning_decision'].update(approved=True),
                     lambda d:d['planning_decision']['comparisons'][0].update(reason=False),
                     lambda d:d['planning_decision']['comparisons'][0].update(measured_sales=100)]
        for mutation in mutations:
            with self.subTest(mutation=mutation): self.invalid(mutation)

    def test_draft_rejects_empty_ragged_duplicate_headers_and_nonstrings(self):
        mutations = [lambda x:x.update(rows=[]), lambda x:x.update(columns=[]),
                     lambda x:x.update(columns=['동일', '동일', '다른']),
                     lambda x:x.update(rows=[['두', '칸']]),
                     lambda x:x['rows'][0].__setitem__(0, None),
                     lambda x:x.update(authorised_by_company=True)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.invalid(lambda d:mutation(d['concepts'][0]['work_draft']))

    def test_draft_utf8_byte_and_item_limits(self):
        def huge(d):
            d['concepts'][0]['work_draft'].update(columns=['항목', '내용'],
                rows=[['가'*1000, '나'*1000] for _ in range(10)])
        self.invalid(huge, 'input_limit')
        self.invalid(lambda d:d['concepts'][0]['work_draft'].update(rows=[['a','b','c']]*21))
        self.invalid(lambda d:d['concepts'][0]['work_draft'].update(columns=['a']*7))

    def test_recovery_is_same_version_and_revised_body_preserves_prior_artifact(self):
        first = self.conv.save_and_export(self.authored())
        path = self.root / first['web_result']['path']; original = path.read_bytes()
        recovered = self.conv.prepare_web_result({**self.handle, 'expected_result_version': 1})
        self.assertEqual(recovered['path'], first['web_result']['path'])
        second = self.authored(1)
        second['result']['concepts'][0]['work_draft']['rows'][0][1] = '수정된 행동을 기록한다.'
        saved = self.conv.save_and_export(second)
        self.assertTrue(saved['save']['accepted'])
        self.assertEqual(self.store.get_turn(**self.handle)['result_version'], 2)
        self.assertNotEqual(first['web_result']['binding'], saved['web_result']['binding'])
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaises(ToolError):
            self.conv.prepare_web_result({**self.handle, 'expected_result_version': 1})

    def test_new_draft_does_not_bypass_duplicate_or_geometry_review(self):
        for key, change in [('duplicates_existing', True), ('geometry_required', True)]:
            value = self.authored()
            value['assessment']['concept_links'][0][key] = change
            report = review_product_result(self.data, {'input': self.current['input'],
                'result': value['result'], 'assessment': value['assessment']})
            self.assertFalse(report['can_finalize_reported_result'])

    def test_hardware_exclusion_still_rejects_hardware_concept(self):
        value = self.authored()
        value['result']['concepts'][0]['requires_hardware'] = True
        planning = copy.deepcopy(self.current['input'])
        self.assertTrue(planning['constraints']['hardware_allowed'])
        self.assertTrue(self.store.tools.validate_result_contract(planning, value['result'])['contract_valid'])
        planning['constraints']['hardware_allowed'] = False
        with self.assertRaises(ToolError) as error:
            self.store.tools.validate_result_contract(planning, value['result'])
        self.assertEqual(error.exception.code, 'constraint_violation')


class HardwarePolicyTests(unittest.TestCase):
    setUp = family.FamilyIntakeTests.setUp
    tearDown = family.FamilyIntakeTests.tearDown
    open = family.FamilyIntakeTests.open

    def test_new_request_default_allows_hardware_ideas(self):
        self.assertTrue(self.open()['turn']['input']['constraints']['hardware_allowed'])

    def test_explicit_exclusion_and_followup_inheritance_remain(self):
        first = self.open(constraints={'max_concepts': 2, 'hardware_allowed': False, 'exclude_pains': []})['turn']
        second = self.conversation.open_request({'question': '이 안을 더 구체화해 줘.', 'user_submitted': True,
            'session_id': first['session_id'], 'prior_turn_id': first['turn_id']})['turn']
        self.assertFalse(second['input']['constraints']['hardware_allowed'])
        self.assertEqual(second['input']['constraints'], first['input']['constraints'])

    def test_reference_only_new_scope_does_not_inherit_old_exclusion(self):
        first = self.open(constraints={'max_concepts': 1, 'hardware_allowed': False, 'exclude_pains': []})['turn']
        second = self.conversation.open_request({'question': '새 제품군을 검토해 줘.', 'user_submitted': True,
            'product_family': 'dishwasher', 'prior_scope': 'reference_only',
            'session_id': first['session_id'], 'prior_turn_id': first['turn_id']})['turn']
        self.assertTrue(second['input']['constraints']['hardware_allowed'])


if __name__ == '__main__': unittest.main()
