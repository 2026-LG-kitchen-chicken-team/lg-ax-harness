"""Planner wording must reach web/report only from the verified current turn.

Synthetic contract fixtures; no business result, network or model inference.
"""
import json
from pathlib import Path
import tempfile
import unittest

from test_visual_viewer import Gen, build_view, read_view


class PlannerDecisionDeliveryTests(unittest.TestCase):
    def test_same_turn_wording_and_registered_scope_reach_both_outputs(self):
        with tempfile.TemporaryDirectory(prefix='planner-decisions-') as folder:
            root = Path(folder)
            g = Gen(root / 'workspace', 'data/business/lg-kitchen-v4')
            try:
                b = g.bundle('[합성 시험 자료] 기획 비교', model_id='MWJ25E')
                candidate = g.author(b['candidate_template'], b['turn']['input']['model_scope'][0],
                                     'REVIEW-MWJ25E-01', 'SPEC-MWJ25E-02')
                saved = g.conv.save_and_export(candidate)
                self.assertTrue(saved['save']['accepted'])
                export_path = g.work / saved['export']['path']
                export_bytes = export_path.read_bytes()
                export = json.loads(export_bytes)
                binding = build_view.current_export_turn(export)['web_binding']
                ins = {'session_id': candidate['session_id'], 'turn_id': candidate['turn_id'], 'binding': binding,
                       'concept_titles': {'c1': '[합성 시험 자료] 짧은 제안명'},
                       'summaries': {'c1': '[합성 시험 자료] 대상과 사용 변화의 요약',
                                     'r1': '[합성 시험 자료] 사용 상황에서 남은 불편'}}
                ins_path = root / 'insights.json'
                ins_path.write_text(json.dumps(ins), encoding='utf-8')
                result = build_view.generate(export_path, ins_path, 'auto', out_dir=root / 'view')
                self.assertEqual(result['insights'], 'matched')
                view = read_view(root / 'view')
                story = next(p for p in view['pages'] if p['id'] == 'story')
                hero = next(b for b in story['blocks'] if b['type'] == 'hero')
                concepts = next(b for b in story['blocks'] if b.get('key') == 'solution')['blocks'][0]['items']
                presentation = view['report']['plan']['presentation']
                self.assertEqual(concepts[0]['title'], ins['concept_titles']['c1'])
                self.assertEqual(concepts[0]['summary'], ins['summaries']['c1'])
                self.assertEqual(presentation['concepts']['c1']['background'], [ins['summaries']['r1']])
                self.assertEqual(presentation['concepts']['c1']['title'], concepts[0]['title'])
                self.assertEqual(presentation['concepts']['c1']['follow_up'], concepts[0]['follow_up'])
                self.assertIn('c1', concepts[0]['follow_up'])
                self.assertIn('필요 입력', concepts[0]['follow_up'])
                self.assertIn(candidate['session_id'], concepts[0]['follow_up'])
                self.assertIn(candidate['turn_id'], concepts[0]['follow_up'])
                self.assertIn('MWJ25E', concepts[0]['follow_up'])
                self.assertEqual(presentation['scope'], hero['scope'])
                scope = hero['scope']
                full_sources = view['report']['plan']['appendix']['sources']
                self.assertEqual(scope['reviews'] + scope['facts'] + scope['other'], len(full_sources))
                self.assertEqual(scope['models'], len({s['model_id'] for s in full_sources}))
                self.assertEqual(export_path.read_bytes(), export_bytes)
                # A title that belongs to another turn may never become a recommendation.
                ins['turn_id'] = 'other-turn'
                ins_path.write_text(json.dumps(ins), encoding='utf-8')
                result = build_view.generate(export_path, ins_path, 'auto', out_dir=root / 'wrong')
                self.assertEqual(result['insights'], 'other_turn')
                wrong = read_view(root / 'wrong')
                self.assertNotIn('[합성 시험 자료] 짧은 제안명', json.dumps(wrong, ensure_ascii=False))
                self.assertEqual(export_path.read_bytes(), export_bytes)
            finally:
                g.close()

    def test_nontext_title_is_rejected_instead_of_rendered_as_ui(self):
        self.assertIn('concept_titles', build_view.insights_shape_errors({'concept_titles': {'c1': {'html': '<img>'}}}))


if __name__ == '__main__':
    unittest.main()
