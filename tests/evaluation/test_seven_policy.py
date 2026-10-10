"""Fresh context cannot turn a rejected candidate into an approved result."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals/runner'))
import seven_eval as study


class PersistentPolicyTests(unittest.TestCase):
    def fixture(self):
        candidates = [{'result_key':f'candidate-{i}', 'candidate_version':i+1, 'result':{'revisions':i},
                       'validation':{'contract_valid':False}, 'status':'held'} for i in range(3)]
        history = [{'result_key':c['result_key'],'result_version':c['candidate_version'],
                    'result':copy.deepcopy(c['result']),'validation':copy.deepcopy(c['validation'])} for c in candidates]
        current = {'state':{'revision_count':2,'result_version':3,'status':'held','valid':True},'candidates':history}
        receipt = {'accepted':False,'valid':True,'status':'held','candidate_result_version':3,'current_result_version':3,
                   'result_key':'candidate-2','result_sha256':study.fingerprint(candidates[-1]['result'])}
        observations = [{'attempt':i,'injected':True,'mode':'persistent','candidate_sha256':study.fingerprint(c['result'])} for i,c in enumerate(candidates)]
        return [{'turns':[current]}, current, candidates, receipt, observations]

    def test_fresh_rejected_history_is_policy_success_only(self):
        args = self.fixture(); before = copy.deepcopy(args)
        report = study.persistent_policy(*args)
        self.assertTrue(report['passed'])
        self.assertEqual(args, before)
        self.assertFalse(args[3]['accepted'])
        self.assertEqual(args[1]['state']['status'], 'held')

    def test_stale_approved_or_unbounded_state_cannot_pass(self):
        for mutate in [lambda a:a[1]['state'].update(valid=False),
                       lambda a:a[3].update(valid=False),
                       lambda a:a[3].update(accepted=True),
                       lambda a:a[1]['state'].update(status='completed'),
                       lambda a:a[1]['state'].update(revision_count=3),
                       lambda a:a[2].pop(),
                       lambda a:a[0]['turns'].append(copy.deepcopy(a[1]))]:
            args=self.fixture(); mutate(args)
            self.assertFalse(study.persistent_policy(*args)['passed'])

    def test_changed_missing_or_unverified_candidates_cannot_pass(self):
        for mutate in [lambda a:a[2][-1]['result'].update(revisions=0),
                       lambda a:a[3].update(result_key='old'),
                       lambda a:a[3].update(result_sha256='wrong'),
                       lambda a:a[2][0]['validation'].update(contract_valid=True),
                       lambda a:a[2][0]['validation'].clear(),
                       lambda a:a[4].pop(),
                       lambda a:a[4][0].update(injected=False),
                       lambda a:a[4][1].update(attempt=0)]:
            args=self.fixture(); mutate(args)
            self.assertFalse(study.persistent_policy(*args)['passed'])

    def test_every_export_history_candidate_must_match_live_result_and_validation(self):
        for index in range(3):
            for mutate in [lambda h:h['result'].update(revisions=99),
                           lambda h:h.update(result_key='other'),
                           lambda h:h.update(result_version=99),
                           lambda h:h['validation'].update(contract_valid=True),
                           lambda h:h['validation'].update(unverified_extra=True)]:
                args=self.fixture(); mutate(args[1]['candidates'][index])
                self.assertFalse(study.persistent_policy(*args)['passed'])

    def test_json_type_aliases_are_changes_not_equal_history(self):
        for mutate in [lambda a:a[1]['candidates'][0]['result'].update(revisions=False),
                       lambda a:a[1]['candidates'][0].update(result_version=True),
                       lambda a:a[2][0].update(candidate_version=True),
                       lambda a:a[1]['state'].update(result_version=3.0),
                       lambda a:a[3].update(candidate_result_version=3.0),
                       lambda a:a[4][0].update(attempt=False)]:
            args=self.fixture(); mutate(args)
            self.assertFalse(study.persistent_policy(*args)['passed'])
        args=self.fixture()
        args[1]['candidates'][0]['validation']['observed_count']=0
        args[2][0]['validation']['observed_count']=False
        self.assertFalse(study.persistent_policy(*args)['passed'])
