"""Open category keys reach current web/report output; fixtures are synthetic only.

No browser, AI execution or network observation is used. Existing model names
and sample categories are not a production answer route or product allowlist.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_visual_viewer import Gen, ROOT, build_view, read_view


class GenericProductViewTests(unittest.TestCase):
    def test_new_categories_keep_model_scope_result_and_report_full_bodies(self):
        for family in ('coffee_machine', 'new-kitchen.category-2026'):
            with self.subTest(family=family), tempfile.TemporaryDirectory(prefix='lgax-generic-view-') as folder:
                work = Path(folder)
                catalog = work / 'catalog'
                catalog.mkdir()
                original = ROOT / 'data/synthetic/kitchen-v1'
                models = json.loads((original / 'models.json').read_text(encoding='utf-8'))
                model = next(m for m in models if m['model_id'] == 'AX-R302')
                model = {**model, 'product_family': family, 'name': '[합성 시험 자료] 새 제품군'}
                scopes = ('model_id', 'model_version', 'document_version')
                sources = [json.loads(row) for row in (original / 'sources.jsonl').read_text(encoding='utf-8').splitlines()]
                sources = [s for s in sources if all(s[k] == model[k] for k in scopes)]
                (catalog / 'models.json').write_text(json.dumps([model], ensure_ascii=False), encoding='utf-8')
                (catalog / 'sources.jsonl').write_text(''.join(json.dumps(s, ensure_ascii=False)+'\n' for s in sources), encoding='utf-8')
                manifest = json.loads((original / 'manifest.json').read_text(encoding='utf-8'))
                manifest.update(model_count=1, scope_count=1,
                                review_count=sum(s['kind'] == 'review' for s in sources),
                                fact_count=sum(s['kind'] == 'product_fact' for s in sources))
                for entry in manifest['files']:
                    entry['sha256'] = hashlib.sha256((catalog / entry['path']).read_bytes()).hexdigest()
                (catalog / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
                g = Gen(work / 'workspace', catalog)
                try:
                    bundle = g.bundle('새 제품군의 불편을 정리해줘.', product_family=family)
                    self.assertEqual(bundle['turn']['input']['product_family'], family)
                    self.assertEqual(len(bundle['turn']['input']['model_scope']), 1)
                    rid = next(s['source_id'] for s in sources if s['kind'] == 'review')
                    fid = next(s['source_id'] for s in sources if s['kind'] == 'product_fact')
                    value = g.author(bundle['candidate_template'], bundle['turn']['input']['model_scope'][0], rid, fid)
                    saved = g.conv.save_and_export(value)
                    self.assertTrue(saved['save']['accepted'], saved['save'])
                    export = g.work / saved['export']['path']
                    out = work / 'view'
                    summary = build_view.generate(export, None, 'auto', out_dir=out)
                    self.assertTrue(summary['ok'])
                    view = read_view(out)
                    report = view['report']
                    turn = report['export']['turns'][0]
                    self.assertEqual(turn['state']['input']['product_family'], family)
                    self.assertEqual(report['turn_id'], bundle['turn']['turn_id'])
                    self.assertEqual(turn['state']['latest_result'], value['result'])
                    self.assertEqual(len(report['export']['turns']), 1)
                    self.assertNotIn('미지원', build_view.family_label(family))
                    self.assertIn(family.replace('_', ' ').replace('-', ' '), json.dumps(view, ensure_ascii=False))
                    web = json.loads((g.work / saved['web_result']['path']).read_text(encoding='utf-8'))
                    self.assertEqual(report['plan']['appendix']['sources'], web['sources'])
                    text_blocks = [block.get('text') for section in report['plan']['sections'] for block in section['blocks']]
                    for source in web['sources']:
                        self.assertNotIn(source['text'], text_blocks)
                    self.assertEqual(turn['state']['latest_result']['evidence_refs'], web['result']['evidence_refs'])
                    frozen = export.read_bytes()
                    followup = g.conv.open_request_bundle({
                        'question': '[합성 시험 자료] 앞 기획을 더 구체화해줘.',
                        'session_id': value['session_id'], 'prior_turn_id': value['turn_id'],
                        'user_submitted': True})
                    self.assertEqual(followup['turn']['input']['product_family'], family)
                    self.assertEqual(followup['turn']['input']['model_scope'], bundle['turn']['input']['model_scope'])
                    self.assertEqual(export.read_bytes(), frozen)
                finally:
                    g.close()

    def test_unregistered_category_enters_research_instead_of_unsupported_route(self):
        with tempfile.TemporaryDirectory(prefix='lgax-unseen-family-') as folder:
            g = Gen(Path(folder), ROOT / 'data/business/empty')
            try:
                response = g.bundle('새 키친 제품의 실제 불편을 조사해줘.', product_family='new-kitchen-appliance')
                self.assertEqual(response['status'], 'research_required')
                self.assertNotIn('unsupported', json.dumps(response, ensure_ascii=False).lower())
            finally:
                g.close()

    def test_familiar_labels_are_display_aliases_and_not_a_support_gate(self):
        self.assertEqual(build_view.family_label('refrigerator'), '냉장고')
        self.assertEqual(build_view.family_label('microwave'), '전자레인지')
        self.assertEqual(build_view.family_label('dishwasher'), '식기세척기')
        self.assertEqual(build_view.family_label(None), '제품군 미지정')
        self.assertEqual(build_view.family_label('arbitrary.category'), 'arbitrary.category')


if __name__ == '__main__':
    unittest.main()
