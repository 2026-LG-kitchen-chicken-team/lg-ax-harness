"""Regression budget/provenance guards; these are not fifty AI answers."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals/runner'))
import regression_eval as runner
import regression_report as reporter
from product_tools.conversation import Conversation
from product_tools.state import StateStore


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((ROOT / 'evals/judge/regression50.json').read_text(encoding='utf-8'))

    def test_fifty_inputs_include_preparation_and_ten_followups(self):
        chains = runner.validate_cases(self.corpus)
        self.assertEqual(len(chains), 40)
        self.assertEqual(sum(len(c) for c in chains.values()), 50)
        self.assertEqual(sum(c['parent_id'] is not None for c in self.corpus['cases']), 10)

    def test_missing_duplicate_wrong_parent_and_budget_drift_rejected(self):
        for alteration in ('missing', 'duplicate', 'parent', 'budget', 'fault'):
            c = copy.deepcopy(self.corpus)
            if alteration == 'missing': c['cases'].pop()
            elif alteration == 'duplicate': c['cases'][1]['id'] = 'R50-01'
            elif alteration == 'parent': c['cases'][5]['parent_id'] = 'R50-02'
            elif alteration == 'budget': c['limits']['native_cap'] = 51
            else: c['cases'][0]['synthetic_fault_injection'] = True
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                runner.validate_cases(c)

    def test_expected_rubric_not_in_submitted_prompt(self):
        c = copy.deepcopy(self.corpus['cases'][0])
        c['required_behaviors'] = ['EVALUATOR_SECRET_MARKER']
        c['expected_terminal_states'] = ['EVALUATOR_SECRET_MARKER']
        text = runner.build_prompt(c, self.corpus['data_path'])
        self.assertIn(c['question'], text)
        self.assertNotIn('EVALUATOR_SECRET_MARKER', text)

    def test_followup_uses_same_constraints_and_no_hidden_preparation(self):
        first, follow, reuse = (self.corpus['cases'][i] for i in (0, 5, 10))
        self.assertEqual(follow['parent_id'], first['id'])
        self.assertEqual(reuse['parent_id'], follow['id'])
        self.assertEqual(reuse['constraints'], follow['constraints'])

    def test_parent_without_actual_native_id_never_falls_back_to_fresh_session(self):
        case = self.corpus['cases'][5]
        for identity in (None, '', ' ', 3):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                runner.parent_identity(case, {'acceptance':'contract_and_delivery_passed','execution':{'native_id':identity}})
        self.assertEqual(runner.parent_identity(case, {'execution':{'native_id':'actual-parent'}}), 'actual-parent')
        self.assertIsNone(runner.parent_identity(self.corpus['cases'][0], None))


class UsageTests(unittest.TestCase):
    def row(self, name, identity, count):
        usage = runner.ev.usage_delta(None if count is None else {k: count for k in runner.ev.FIELDS})
        return {'job': name, 'execution': {'native_id': identity, 'usage': usage}}

    def test_same_session_cumulative_is_counted_once_failures_not_removed(self):
        rows = [self.row('1', 'a', 10), self.row('2', 'a', 25), self.row('3', 'b', 7)]
        rows[-1]['execution']['status'] = 'timeout'
        value = runner.session_usage(rows)
        self.assertEqual(value['observed_session_totals']['input_tokens']['known_sum'], 32)
        self.assertEqual(len(value['sessions']), 2)

    def test_later_unknown_is_not_replaced_with_earlier_success(self):
        value = runner.session_usage([self.row('1', 'a', 10), self.row('2', 'a', None), self.row('3', None, None)])
        self.assertIsNone(value['observed_session_totals']['input_tokens']['known_sum'])
        self.assertFalse(value['complete_native_usage'])
        self.assertEqual(value['attempts_without_native_id'], ['3'])

    def test_identity_mismatch_or_nonmonotone_delta_stays_unknown(self):
        for now, old, a, b in (({'input_tokens':2},{'input_tokens':5},'a','a'), ({'input_tokens':8},{'input_tokens':5},'a','b')):
            self.assertIsNone(runner.followup_usage(now, old, a, b)['input_tokens'])

    def test_launch_failure_preserves_partial_cli_usage_when_rollout_unavailable(self):
        with tempfile.TemporaryDirectory(prefix='lg-r50-partial-') as temp:
            directory = Path(temp)
            (directory / 'native.jsonl').write_text('partial trace', encoding='utf-8')
            partial = {'native_id':'a','turn_completed':False,'cumulative_usage':{'input_tokens':17}}
            with patch.object(runner.ev, 'execute', side_effect=OSError('collector failure')), \
                 patch.object(runner.ev, 'parse_cli', return_value=partial), \
                 patch.object(runner.ev, 'rollout_observation', side_effect=OSError('rollout unavailable')):
                value = runner.execute_preserving([], directory, 'question', directory, 1)
            self.assertEqual(value['status'], 'runner_failed')
            self.assertEqual(value['usage']['input_tokens'], 17)
            self.assertIn('observation_error', value)


class ClarificationTests(unittest.TestCase):
    def test_real_pending_export_live_db_match_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory(prefix='lg-r50-clarification-') as temp:
            workspace = Path(temp)
            data = runner.ev.Dataset(ROOT / 'data/business/lg-kitchen-v4')
            store = StateStore(workspace / 'runtime-data/product.sqlite', data)
            conversation = Conversation(store, workspace)
            question = '모델 미선택 요청'
            request = conversation.open_request_bundle({'question':question,'user_submitted':True})
            exported = conversation.export_session({'session_id':request['session_id']})
            text = json.dumps({'request':request,'export':exported}, ensure_ascii=False)
            job = {'case':{'question':question},'prompt':question}
            try:
                with patch.object(runner.receipt, 'final_message', return_value=text):
                    accepted = runner.accept_clarification(workspace, workspace, {}, job)
                self.assertEqual(accepted['terminal_status'], 'needs_input')
                with patch.object(runner.receipt, 'final_message', return_value=text), self.assertRaises(ValueError):
                    runner.accept_clarification(workspace, workspace, {}, {**job,'case':{'question':'changed'},'prompt':'changed'})
                pointer = json.loads(text)
                pointer['request']['reason']['code'] = 'forged'
                with patch.object(runner.receipt, 'final_message', return_value=json.dumps(pointer)), self.assertRaises(ValueError):
                    runner.accept_clarification(workspace, workspace, {}, job)
            finally:
                store.close()


class SemanticReportTests(unittest.TestCase):
    def test_na_is_not_filled_with_full_credit_and_critical_errors_block_pass(self):
        self.assertTrue(reporter.semantic_pass({'scores':[2,2,None,None,2,1,None], 'critical_errors':[]}))
        self.assertFalse(reporter.semantic_pass({'scores':[2,1,None,None,2,1,None], 'critical_errors':[]}))
        self.assertFalse(reporter.semantic_pass({'scores':[2,2,None,None,2,2,None], 'critical_errors':['invented model']}))
        self.assertFalse(reporter.semantic_pass({'scores':[2,2,2,2,2,2,0], 'critical_errors':[]}))

    def test_invalid_or_missing_semantic_scores_are_not_passed(self):
        for scores in ([2]*6, [2]*6+[True], [None]*7, [2]*6+[3]):
            with self.subTest(scores=scores), self.assertRaises(ValueError):
                reporter.semantic_pass({'scores':scores,'critical_errors':[]})


if __name__ == '__main__':
    unittest.main()
