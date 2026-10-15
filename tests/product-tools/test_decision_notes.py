"""Decision-only evidence stays exact without certifying meaning or inventing claims."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'product-tools'))
from product_tools.contracts import ToolError
from product_tools.conversation import Conversation
from product_tools.dataset import Dataset
from product_tools.state import StateStore

class DecisionNotes(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for name in ('skills/manifest.json','agents/product-planning.md'):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        self.store=StateStore(self.root/'runtime-data/product.sqlite',Dataset(ROOT/'data/business/lg-kitchen-v4'))
        self.conv=Conversation(self.store,self.root)
        self.bundle=self.conv.open_request_bundle({'question':'계약 시험용 임의 요청','product_family':'refrigerator','user_submitted':True})
        self.value=self.bundle['candidate_template']
        self.value['result'].update(status='held',validation_findings=['내부 조건 미확인'])
        self.refs=self.bundle['bundle']['evidence_refs']
        self.ref=self.refs[0]

    def tearDown(self):self.store.close();self.tmp.cleanup()

    def authored(self,basis='source_fact'):
        value=copy.deepcopy(self.value)
        value['result']['decision_notes']=[{'text':'보유 자료 범위에서만 판단함','source_ids':[self.ref['source_id']],'basis':basis}]
        value['result']['evidence_refs']=[copy.deepcopy(self.ref)]
        return value

    def validate(self,value):
        return self.store.tools.validate_result_contract(self.bundle['turn']['input'],value['result'])

    def error(self,code,value):
        with self.assertRaises(ToolError) as caught:self.validate(value)
        self.assertEqual(caught.exception.code,code)

    def test_decision_only_evidence_save_export_preserves_exact_notes(self):
        value=self.authored('ai_interpretation');saved=self.conv.save_and_export(value)
        self.assertTrue(saved['delivery_ready'])
        raw=(self.root/saved['export']['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),saved['export']['sha256'])
        result=json.loads(raw)['turns'][0]['candidates'][0]['result']
        self.assertEqual(result,value['result']);self.assertEqual(result['pains'],[])
        self.assertEqual(self.validate(value)['semantic_status'],'unverified')
        self.assertFalse(self.validate(value)['acceptance_ready'])

    def test_note_only_held_completion_keeps_basis_and_exact_used_urls_locations(self):
        value = self.authored('source_fact')
        value['result']['decision_notes'] += [
            {'text': '근거의 적용 범위에 대한 시험용 해석', 'source_ids': [self.ref['source_id']], 'basis': 'ai_interpretation'},
            {'text': '실물 적용은 미확인', 'source_ids': [], 'basis': 'unverified'}]
        saved = self.conv.save_and_export(value)
        summary = saved['completion_summary']
        raw = (self.root / summary['path']).read_bytes()
        completion = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), summary['sha256'])
        self.assertEqual(completion['decision_notes'], value['result']['decision_notes'])
        self.assertEqual(completion['evidence_refs'], value['result']['evidence_refs'])
        self.assertEqual(completion['source_ids'], [self.ref['source_id']])
        self.assertEqual(completion['text_source_ids'], [self.ref['source_id']])
        self.assertGreater(len(self.refs), len(completion['source_ids']))
        for note in value['result']['decision_notes']:
            self.assertIn(note['text'], summary['text'])
        for detail in ('AI 분류', 'AI 해석', '미확인', self.ref['origin']['source_url'], self.ref['location']):
            # The basis label remains an AI report, including source_fact.
            self.assertIn(detail, summary['text'])
        self.assertNotIn(self.ref['quote'], summary['text'])
        self.assertEqual(completion['concepts'], [])
        self.assertEqual(completion['semantic_status'], 'unverified')
        self.assertFalse(completion['acceptance_ready'])

    def test_legacy_omission_and_unverified_without_sources(self):
        legacy=copy.deepcopy(self.value);legacy['result'].pop('decision_notes')
        self.assertTrue(self.validate(legacy)['contract_valid'])
        self.value['result']['decision_notes']=[{'text':'실제 근거 없음','basis':'unverified','source_ids':[]}]
        self.assertTrue(self.validate(self.value)['contract_valid'])

    def test_missing_reference_is_rejected(self):
        value=self.authored();value['result']['evidence_refs']=[];self.error('missing_evidence',value)

    def test_unused_reference_is_rejected(self):
        value=self.authored();value['result']['decision_notes']=[];self.error('unused_evidence',value)

    def test_wrong_hash_and_snapshot_are_rejected(self):
        for key in ('sha256','document_version'):
            value=self.authored();value['result']['evidence_refs'][0][key]='0'*64
            self.error('reference_mismatch',value)

    def test_discontinuous_quote_is_rejected(self):
        value=self.authored();quote=self.ref['quote']
        value['result']['evidence_refs'][0]['quote']=quote[:5]+'…'+quote[-5:]
        self.error('quote_mismatch',value)

    def test_note_cannot_mix_model_snapshots(self):
        other=next(r for r in self.refs if r['model_id']!=self.ref['model_id'])
        value=self.authored();value['result']['evidence_refs'].append(copy.deepcopy(other))
        value['result']['decision_notes'][0]['source_ids'].append(other['source_id'])
        self.error('scope_mismatch',value)

    def test_invalid_basis_duplicates_empty_and_bounds(self):
        for transform in (lambda n:n.update(basis='official_certified'),lambda n:n.update(source_ids=[]),lambda n:n.update(source_ids=[self.ref['source_id']]*2),lambda n:n.update(text='x'*2001)):
            value=self.authored();transform(value['result']['decision_notes'][0]);self.error('invalid_input',value)
        value=self.authored();value['result']['decision_notes']*=11;self.error('invalid_input',value)

    def test_note_does_not_replace_completed_concept(self):
        value=self.authored();value['result']['status']='completed';self.error('invalid_input',value)

if __name__=='__main__':unittest.main()
