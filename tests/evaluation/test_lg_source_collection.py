"""Boundary/attribution checks for the development-only public corpus adapter."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('lg_collection',ROOT/'evals/runner/collect_lg_sources.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)

class CollectionTests(unittest.TestCase):
    def test_spec_only_not_navigation_or_generic_faq(self):
        raw='<nav>제품 상세 스펙 unrelated</nav><div class="spec_container"><img src="a"/><div>내부 치수 1</div><div>외형 치수 2</div></div><div>Other model FAQ</div>'
        self.assertEqual(collector.spec_section(raw),'내부 치수 1 외형 치수 2')

    def test_no_spec_fallback_when_section_absent(self):
        self.assertEqual(collector.spec_section('<p>제품 상세 스펙</p>generic page'),'')

    def test_full_sku_retained_and_ambiguous_ld_rejected(self):
        raw='<script type="application/ld+json">{"@type":"Product","sku":"ABC.CKOR"}</script>'
        sku,quote=collector.sku_header(raw)
        self.assertEqual(sku,'ABC.CKOR');self.assertIn('ABC.CKOR',quote)
        with self.assertRaises(ValueError):collector.sku_header(raw+raw)

    def test_review_parent_does_not_override_individual_model(self):
        raw='<li data-model-id="MD2" data-review-id="R1"><em>구매 일자</em>2026.01.01<p class="message">실제 문장</p></li>'
        row=collector.review_rows(raw)[0]
        self.assertEqual(row['publisher_product_id'],'MD2')
        self.assertEqual(row['text'],'실제 문장')
        self.assertNotIn('full_review',row['text_coverage'])

    def test_dom_related_model_is_not_selected_as_exact_scope(self):
        mixed='<aside data-product-code="OTHER.CKOR"></aside><main data-product-code="ACTUAL.CKOR"></main>'
        with self.assertRaises(ValueError):collector.sku_header(mixed)
        same='<aside data-product-code="ACTUAL.CKOR"></aside><main data-product-code="ACTUAL.CKOR"></main>'
        self.assertEqual(collector.sku_header(same)[0],'ACTUAL.CKOR')
        conflicting='<main data-product-code="OTHER.CKOR"></main><script type="application/ld+json">{"@type":"Product","sku":"ACTUAL.CKOR"}</script>'
        with self.assertRaises(ValueError):collector.sku_header(conflicting)

    def test_missing_review_model_stays_unknown(self):
        row=collector.review_rows('<li data-review-id="R2"><p class="message">A</p></li>')[0]
        self.assertIsNone(row['publisher_product_id'])

    def test_review_body_never_crosses_its_li_boundary(self):
        raw='<li data-review-id="R1" data-model-id="MD1"></li><footer><p class="message">Unrelated footer</p></footer>'
        self.assertEqual(collector.review_rows(raw),[])
        nested='<li data-review-id="R2" data-model-id="MD2"><ul><li>rating</li></ul><p class="message">Actual body</p></li><footer><p class="message">Other</p></footer>'
        self.assertEqual(collector.review_rows(nested)[0]['text'],'Actual body')
        self.assertEqual(collector.review_rows('<li data-review-id="R3"><p class="message">unclosed</p>'),[])

    def test_robot_permission_depends_on_actual_channel_identity(self):
        lines=['User-agent: *','Disallow: /mkt/review/','User-agent: ChatGPT-User','Allow: /']
        url='https://example.org/mkt/review/MD2/list'
        self.assertFalse(collector.robots_permission(lines,url))
        self.assertTrue(collector.robots_permission(lines,url,agent='ChatGPT-User'))
        self.assertTrue(collector.robots_permission(lines,'https://example.org/mkt/api/review/MD2/count'))

if __name__=='__main__':unittest.main()
