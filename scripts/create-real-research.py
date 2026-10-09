"""Reproduce newly observed excerpts/factual summaries. Does not crawl the web."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "lg-observed-2026-10-10-v3"
URLS = {
    "S836GBB122": "https://www.lge.co.kr/product/refrigerators/s836gbb122?modelId=MD10559848&pdpType=PURCHASE",
    "B502S33": "https://www.lge.co.kr/product/refrigerators/b502s33?modelId=MD09091859&pdpType=PURCHASE",
    "T876MQQ012": "https://www.lge.co.kr/product/refrigerators/t876mqq012?modelId=MD10681860&pdpType=PURCHASE",
}
BLOG = "https://min-inter.co.kr/wiki/lg-dios-t876mqq012-refrigerator-purchase/"
MANUAL = "https://gscs-b2c.lge.com/open/downloadFile?fileId=LuQhmLf8ZMxg8pHShCqA"


def main():
    original = ROOT / "data/business/lg-pilot-v1"
    target = (ROOT / "data/business/lg-research-v3").resolve()
    if not target.is_relative_to(ROOT.resolve()):
        raise ValueError("Dataset must stay inside project")
    target.mkdir(parents=True, exist_ok=True)
    models = json.loads((original / "models.json").read_text(encoding="utf-8"))
    sources = [{**json.loads(line), "data_version": VERSION} for line in (original / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
    for mid, name, capacity, dimensions, arrangement, doors in [
        ("B502S33", "LG 일반냉장고 샤인", 507, (780, 1800, 730), "top_freezer", 2),
        ("T876MQQ012", "LG 디오스 AI 오브제컬렉션 냉장고", 870, (914, 1787, 918), "french_door_bottom_freezer", 4),
    ]:
        models.append({"model_id": mid, "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10",
            "name": name, "product_family": "refrigerator", "synthetic": False, "capacity_l": capacity,
            "dimensions_mm": dict(zip(("width", "height", "depth"), dimensions)),
            "layout": {"door_count": doors, "arrangement": arrangement, "internal_dimensions_mm": None, "shelf_spacing_mm": None},
            "spec_source_id": "SPEC-" + mid + "-01"})
    facts = [
        ("S836GBB122", "05", "ice_maker_removal", "present", "상세/무빙도어 아이스메이커 및 스펙/얼음 시스템", "해당 모델은 무빙 도어 아이스메이커를 사용한다. 상세 설명은 제빙기를 떼거나 다시 장착하여 냉동 보관 공간을 활용하는 기능을 안내한다. 확보한 수납 기능이며 내부 간격이나 확보되는 추가 용량 수치는 확인되지 않았다."),
        ("S836GBB122", "06", "vegetable_drawer", "present", "스펙/냉장실 사양", "신선보관야채실과 신선야채실이 표기돼 있다. 청소를 위한 서랍 분리 방법과 치수는 이 스펙 표에서 확인되지 않았다."),
        ("S836GBB122", "07", "interior_lighting", "present", "스펙/냉장실·냉동실 사양", "냉장실과 냉동실 내부 조명이 Top으로 표시돼 있다. 위치 표기이며 실제 적재 상태의 밝기나 그림자 크기 측정값은 아니다."),
        ("B502S33", "01", "dimensions_capacity", "present", "스펙/용량·크기", "외형 폭780·높이1800·깊이730 mm. 전체507 L, 냉장376 L, 냉동131 L. 외형 치수는 내부 치수나 식품 배치 가능성을 입증하지 않는다."),
        ("B502S33", "02", "glass_shelves", "present", "스펙/냉장실 사양", "강화유리 선반이 적용돼 있다. 이 스펙 표는 선반의 분리 방법, 간격, 도어 최소 개방각을 명시하지 않는다."),
        ("B502S33", "03", "vegetable_drawer", "present", "스펙/냉장실 사양", "신선야채실이 적용돼 있다. 후기의 냉동실 수납 아쉬움은 냉장 야채실 기능으로 자동 해소된다고 판단할 수 없다."),
        ("B502S33", "04", "ice_maker", "present", "스펙/상세기능", "트위스트 방식 제빙기가 기재돼 있다. 본 자료로 해당 제빙기의 탈착 가능 여부를 확정하지 않는다."),
        ("T876MQQ012", "01", "dimensions_capacity", "present", "스펙/기본 사양·용량·크기", "4도어 상냉장·하냉동. 외형 폭914·높이1787·깊이918 mm. 전체870 L, 냉장503 L, 냉동367 L. 냉장칸 문열림 각도는135도로 표기되며 선반 분리 최소각을 뜻하지 않는다."),
        ("T876MQQ012", "02", "interior_lighting", "present", "스펙/냉장실·냉동실 사양", "냉장실 및 냉동실 내부조명은 Top으로 기재돼 있다. 조명이 있다는 사실은 적재 시 하단이 어둡다는 고객 경험의 해소나 조명 고장을 입증하지 않는다."),
        ("T876MQQ012", "03", "folding_shelf", "present", "스펙/냉장실 사양", "접이선반은1단, 강화유리 선반은4개로 기재돼 있다. 높이·깊이·간격을 확인하지 않아 특정 크기 용기의 수납을 보장하지 않는다."),
        ("T876MQQ012", "04", "storage_compartments", "present", "스펙/냉장실 사양", "신선야채실2개와 대용량 바스켓 및 신선플러스 트레이가 기재돼 있다. 내부 세부 치수와 실제 적재 배치의 공간 여유는 미확인이다."),
        ("T876MQQ012", "05", "multi_storage_corner", "explicitly_absent", "스펙/냉장실 사양/멀티수납코너", "해당 모델의 멀티수납코너는 미적용으로 표시돼 있다. 이 한 항목의 부재를 전체 수납 기능 부재로 확대하지 않는다."),
    ]
    reviews = [
        ("B502S33", "01", "리뷰/샤인 옵션/냉동실 수납 아쉬움과2인 사용 수용", "냉동실이 너무 좁기는 하지만 두명이 쓰기에는 괜찮은것같아요", URLS["B502S33"], None, "product_page_association"),
        ("B502S33", "02", "리뷰/샤인 옵션/현재 수납 긍정 평가", "현재 잘 사용하고 있어요. 냉장고는 넉넉한게 좋은듯해요.", URLS["B502S33"], None, "product_page_association"),
        ("T876MQQ012", "01", "8.3 내부 조명/현재 제품의 적재 그림자 경험", "선반과 식재료가 가리면 중·하단과 구석까지 빛이 잘 안 내려와", BLOG, "2026-07-21", "explicit_model_verified"),
    ]
    for mid, number, feature, availability, location, content in facts:
        sources.append({"source_id": "SPEC-" + mid + "-" + number, "kind": "product_fact", "model_id": mid,
            "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10", "data_version": VERSION,
            "location": location, "text": content, "synthetic": False, "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "origin": {"source_url": URLS[mid], "retrieved_date": "2026-10-10", "published_date": None,
                "representation": "factual_summary", "model_matching": "explicit_model_verified", "purchase_verified": None, "sponsorship": None},
            "feature_key": feature, "availability": availability})
    for mid, number, location, content, url, published, matching in reviews:
        sources.append({"source_id": "REVIEW-" + mid + "-" + number, "kind": "review", "model_id": mid,
            "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10", "data_version": VERSION,
            "location": location, "text": content, "synthetic": False, "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "origin": {"source_url": url, "retrieved_date": "2026-10-10", "published_date": published,
                "representation": "excerpt", "model_matching": matching, "purchase_verified": None, "sponsorship": None}})
    for number, feature, location, content in [
        ("01", "folding_shelf_operation", "MFL71401547 Rev.03_091025 p17/접이식 선반; PDP지원 연결·적용 모델 한정", "공용 설명서는 접이식 선반의 앞부분을 조금 들어 내부로 밀어 넣고, 되돌릴 때 앞으로 당기는 조작을 안내한다. T876MQQ012는 정확한 스펙 표에서 접이선반1단이 확인된다. 접힘 길이와 수납 가능 높이는 미확인이다."),
        ("02", "shelf_adjustment", "MFL71401547 Rev.03_091025 p17-18/냉장실 선반; 적용 부품 확인 필요", "공용 설명서는 선반을 들어 고리를 홈에서 빼고 원하는 높이의 홈에 다시 고정하는 절차를 안내한다. 유리 선반 분리 전 식품을 치우고 무게에 주의하도록 한다. 해당 부품 형태 확인이 필요하며 조절 간격 수치는 제공하지 않는다."),
        ("03", "component_cleaning", "MFL71401547 Rev.03_091025 p19/내부 청소; 공용 설명서", "공용 설명서의 내부 청소 안내는 구성품 분리 전 식품을 꺼내고 선반·바구니·고무 패킹을 물에 적신 부드러운 수건으로 닦은 다음 물기를 제거하는 절차를 설명한다. 이를 실제 고객의 청소 불편 또는 개선 시간의 증거로 사용하지 않는다."),
    ]:
        sources.append({"source_id": "MANUAL-T876MQQ012-" + number, "kind": "product_fact", "model_id": "T876MQQ012",
            "model_version": "unspecified", "document_version": "pdp-snapshot-2026-10-10", "data_version": VERSION,
            "location": location, "text": content, "synthetic": False, "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "origin": {"source_url": MANUAL, "retrieved_date": "2026-10-10", "published_date": "2025-09-22",
                "representation": "factual_summary", "model_matching": "product_page_association", "purchase_verified": None, "sponsorship": None},
            "feature_key": feature, "availability": "present"})
    for source in sources:
        if source["origin"]["source_url"] == BLOG:
            source["origin"]["commercial_disclosure"] = "글과 사이트에 파트너스 활동에 따른 수수료 수령 고지가 있다. 제품 협찬 여부는 별도 미확인이다."
    for name, content in (("models.json", json.dumps(models, ensure_ascii=False, indent=2) + "\n"),
                          ("sources.jsonl", "".join(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n" for s in sources))):
        (target / name).write_text(content, encoding="utf-8", newline="\n")
    manifest = {"data_version": VERSION, "synthetic": False, "purpose": "business", "created_date": "2026-10-10",
        "provenance": "Newly observed exact-model official facts plus original review excerpts; source meaning and purchase identity not automatically certified. Current storage pain exists for B502S33/T876MQQ012; cleaning pain and internal dimensions remain unconfirmed. Mixed-option mirror reviews excluded.",
        "model_count": 3, "scope_count": 3, "review_count": 6, "fact_count": 19,
        "files": [{"path": name, "sha256": hashlib.sha256((target / name).read_bytes()).hexdigest()} for name in ("models.json", "sources.jsonl")]}
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"data_version": VERSION, "models": 3, "reviews": 6, "facts": 19, "cleaning_pain": "unconfirmed", "internal_dimensions": "unconfirmed"}))


if __name__ == "__main__":
    main()
