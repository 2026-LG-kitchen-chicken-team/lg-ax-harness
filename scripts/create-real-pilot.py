"""Reproduce a small observed-source snapshot, not live review scraping."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = "lg-observed-2026-10-10-v1"
URL = "https://www.lge.co.kr/product/refrigerators/s836gbb122?modelId=MD10559848&pdpType=PURCHASE"
SCOPE = {"model_id": "S836GBB122", "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10"}

def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

def main():
    target = (ROOT / "data/business/lg-pilot-v1").resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise ValueError("Output must stay inside repository")
    target.mkdir(parents=True, exist_ok=True)
    facts = [
        ("SPEC-S836GBB122-01", "dimensions_capacity", "present", "제품 스펙/기본 사양·크기·용량", "2도어 양문형. 외형 W×H×D는 913×1790×913 mm. 전체 832 L, 냉장 524 L, 냉동 308 L. 내부 치수와 선반 간격은 이 자료에서 확인되지 않았다."),
        ("SPEC-S836GBB122-02", "glass_shelves", "present", "제품 스펙/냉장실·냉동실 사양", "냉장실과 냉동실 강화유리 선반은 각각 3개로 기재되어 있다. 이 정보는 분리 가능 여부나 선반 간격을 입증하지 않는다."),
        ("SPEC-S836GBB122-03", "magic_space", "present", "제품 스펙/상세기능", "매직스페이스가 기재되어 있다. 고객 불편이 모두 해소된다는 의미는 아니다."),
        ("SPEC-S836GBB122-04", "door_cooling_plus", "explicitly_absent", "제품 스펙/상세기능/도어쿨링⁺", "이 모델의 제품 스펙에서 도어쿨링⁺가 X로 표시되어 있다. 다른 모델의 시험 조건이나 기능 설명을 이 모델에 적용하지 않는다."),
    ]
    reviews = [
        ("REVIEW-S836GBB122-01", "리뷰/자동 닫힘 언급/본문 발췌", "특히 자동 담힘 기능 좋아요."),
        ("REVIEW-S836GBB122-02", "리뷰/홈바·도어 청소 기대 언급/본문 발췌", "홈바가 커져서 사용하기 훨씬 편리해졌어요. 도어가 글라스 소재라 청소 또한 손쉽고 깔끔하게 할 수 있을거 같아요."),
        ("REVIEW-S836GBB122-03", "리뷰/문 닫힘 언급/본문 발췌", "조용하게 닫치는군요."),
    ]
    sources = []
    for source_id, feature, availability, location, body in facts:
        sources.append({**SCOPE, "source_id": source_id, "kind": "product_fact", "feature_key": feature,
                        "availability": availability, "location": location, "text": body})
    for source_id, location, body in reviews:
        sources.append({**SCOPE, "source_id": source_id, "kind": "review", "location": location, "text": body})
    for source in sources:
        source.update(data_version=VERSION, synthetic=False, sha256=hashlib.sha256(source["text"].encode("utf-8")).hexdigest(),
                      origin={"source_url": URL, "retrieved_date": "2026-10-10", "published_date": None,
                              "representation": "excerpt" if source["kind"] == "review" else "factual_summary",
                              "model_matching": "product_page_association" if source["kind"] == "review" else "explicit_model_verified",
                              "purchase_verified": None, "sponsorship": None})
    models = [{**SCOPE, "name": "LG 디오스 AI 오브제컬렉션 냉장고 (양문형, 매직스페이스)", "product_family": "refrigerator", "synthetic": False,
               "dimensions_mm": {"width": 913, "height": 1790, "depth": 913}, "capacity_l": 832,
               "layout": {"door_count": 2, "arrangement": "side_by_side", "internal_dimensions_mm": None, "shelf_spacing_mm": None},
               "spec_source_id": "SPEC-S836GBB122-01"}]
    (target / "models.json").write_text(dump(models), encoding="utf-8", newline="\n")
    (target / "sources.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n" for s in sources), encoding="utf-8", newline="\n")
    files = [{"path": name, "sha256": hashlib.sha256((target / name).read_bytes()).hexdigest()} for name in ("models.json", "sources.jsonl")]
    (target / "manifest.json").write_text(dump({"data_version": VERSION, "synthetic": False, "purpose": "business", "created_date": "2026-10-10",
        "provenance": "Newly observed official LG product-page specification summaries and three customer-review excerpts. Not AI review summaries. Positive convenience/expectation evidence only; no verified present-model pain, publication date, purchase verification or sponsorship status. Snapshot excerpt hashes are not full-webpage hashes.",
        "model_count": 1, "scope_count": 1, "review_count": 3, "fact_count": 4, "files": files}), encoding="utf-8", newline="\n")
    print(json.dumps({"data_version": VERSION, "models": 1, "reviews": 3, "facts": 4, "pain_evidence": "insufficient"}))

if __name__ == "__main__":
    main()
