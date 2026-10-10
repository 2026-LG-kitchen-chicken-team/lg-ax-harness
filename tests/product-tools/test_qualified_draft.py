"""Conservative uncertainty boundaries; fixtures are not semantic proof."""
import copy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import test_planning_web as _web
from product_tools.planning import review_product_result
from product_tools.contracts import ToolError

class QualifiedDraftTests(unittest.TestCase):
    setUp = _web.PlanningWebTests.setUp
    tearDown = _web.PlanningWebTests.tearDown
    candidate = _web.PlanningWebTests.candidate
    def qualified(self):
        p = self.candidate()
        # B502 reviews are page-linked; T876's explicit-model source must not be
        # mislabelled to make the qualifier pass.
        replacements={'REVIEW-T876MQQ012-01':'REVIEW-B502S33-01','SPEC-T876MQQ012-02':'SPEC-B502S33-01'}
        scope={'model_id':'B502S33','model_version':'unspecified','document_version':'pdp-snapshot-2026-10-10'}
        p['input']=self.tools.prepare_planning_input({'model_id':'B502S33','session_id':'test','request_key':'request'})['input']
        for section in ('pains','existing_features','remaining_pains','concepts'):
            for c in p['result'][section]: c['source_ids']=[replacements.get(s,s) for s in c['source_ids']]
        p['result']['evidence_refs']=self.tools.select_evidence(scope,list(replacements.values()))['evidence_refs']
        for c in p['assessment']['claim_checks']: c['source_ids']=[replacements.get(s,s) for s in c['source_ids']]
        p['assessment']['feature_matches'][0]['feature_source_ids']=['SPEC-B502S33-01']
        p['result']['assumptions'] = ['Page attribution and practical effect unverified']
        p['result']['concepts'][0]['assumptions'] = ['Conditional draft; duplicate verification incomplete']
        for c in p['assessment']['claim_checks']:
            if c['claim_id'] != 'f1':
                c.update(support_status='uncertain', scope_relation='unclear', qualification={
                    'basis':'page_linked_example' if c['claim_id']=='p1' else 'conditional_draft',
                    'limitations':['Exact-model/customer or hypothesis not verified'], 'original_statement_supported':True})
        p['assessment']['feature_matches'][0]['resolution'] = 'uncertain'
        p['assessment']['concept_links'][0]['duplicates_existing'] = None
        return p

    def test_honest_draft_retains_uncertainty_without_certifying_truth(self):
        report = review_product_result(self.data, self.qualified())
        self.assertTrue(report['can_finalize_reported_result'])
        self.assertEqual(report['qualified_claim_ids'], ['c1','p1','r1'])
        self.assertEqual(report['semantic_status'], 'unverified')
        self.assertFalse(report['acceptance_ready'])

    def test_unobserved_conditional_proposal_retains_false_and_all_boundaries(self):
        p = self.qualified()
        for c in p['assessment']['claim_checks']:
            if c['claim_id'] in ('r1', 'c1'):
                c['qualification']['original_statement_supported'] = False
        before = copy.deepcopy(p)
        report = review_product_result(self.data, p)
        self.assertTrue(report['can_finalize_reported_result'])
        self.assertEqual(p, before)
        self.assertEqual(report['semantic_status'], 'unverified')
        self.assertFalse(report['acceptance_ready'])
        for mutate in [lambda q:q['assessment']['claim_checks'][2].update(support_status='unsupported'),
                       lambda q:q['assessment']['claim_checks'][3].update(scope_relation='previous_product'),
                       lambda q:q['assessment']['feature_matches'][0].update(resolution='resolved'),
                       lambda q:q['assessment']['concept_links'][0].update(duplicates_existing=True),
                       lambda q:q['assessment']['concept_links'][0].update(geometry_required=True),
                       lambda q:q['result'].update(assumptions=[]),
                       lambda q:q['result']['concepts'][0].update(assumptions=[])]:
            q = copy.deepcopy(p); mutate(q)
            self.assertFalse(review_product_result(self.data, q)['can_finalize_reported_result'])

    def test_qualification_cannot_launder_unsupported_or_previous_product(self):
        for field, value in [('support_status','unsupported'),('scope_relation','previous_product')]:
            p = self.qualified(); p['assessment']['claim_checks'][0][field] = value
            self.assertFalse(review_product_result(self.data,p)['can_finalize_reported_result'])

    def test_exact_fact_uncertainty_cannot_be_laundered_as_page_pain(self):
        p=self.qualified(); c=p['assessment']['claim_checks'][1]
        c.update(support_status='uncertain',scope_relation='unclear',qualification=copy.deepcopy(p['assessment']['claim_checks'][0]['qualification']))
        self.assertFalse(review_product_result(self.data,p)['can_finalize_reported_result'])

    def test_missing_disclosures_or_source_support_blocks_qualified_draft(self):
        for mutate in [lambda p:p['result'].update(assumptions=[]),
                       lambda p:p['result']['concepts'][0].update(assumptions=[]),
                       lambda p:p['assessment']['claim_checks'][0]['qualification'].update(original_statement_supported=False)]:
            p=self.qualified();mutate(p)
            self.assertFalse(review_product_result(self.data,p)['can_finalize_reported_result'])

    def test_resolved_duplicate_and_geometry_still_block_qualified_draft(self):
        for mutate in [lambda p:p['assessment']['feature_matches'][0].update(resolution='resolved'),
                       lambda p:p['assessment']['concept_links'][0].update(duplicates_existing=True),
                       lambda p:p['assessment']['concept_links'][0].update(geometry_required=True)]:
            p=self.qualified();mutate(p)
            self.assertFalse(review_product_result(self.data,p)['can_finalize_reported_result'])

    def test_empty_or_unrecognized_qualification_rejected(self):
        for field,value in [('limitations',[]),('basis','verified_customer'),('original_statement_supported',1)]:
            p=self.qualified();p['assessment']['claim_checks'][0]['qualification'][field]=value
            with self.assertRaises(ToolError): review_product_result(self.data,p)

    def test_explicit_invalid_qualification_cannot_fall_back_to_supported(self):
        p=self.qualified();c=p['assessment']['claim_checks'][0]
        c.update(support_status='supported',scope_relation='current_model')
        c['qualification']['original_statement_supported']=False
        self.assertFalse(review_product_result(self.data,p)['can_finalize_reported_result'])
