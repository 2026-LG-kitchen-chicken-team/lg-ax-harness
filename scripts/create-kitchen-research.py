"""Reproduce observed short excerpts and official factual summaries, no crawl."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION="lg-observed-2026-10-11-kitchen-v4"
PAGES={
    "MWJ25E":"https://www.lge.co.kr/product/microwaves-and-ovens/mwj25e?modelId=MD09144829&pdpType=PURCHASE",
    "DUBJ2EA":"https://www.lge.co.kr/product/dishwashers/dubj2ea?modelId=MD08748356&pdpType=PURCHASE",
}


def main():
    target=ROOT/"data/business/lg-kitchen-v4"
    if target.exists():
        raise ValueError("Immutable dataset already exists; create a new version for changes")
    previous=ROOT/"data/business/lg-research-v3"
    models=json.loads((previous/"models.json").read_text(encoding="utf-8"))
    records=[{**json.loads(line),"data_version":VERSION} for line in (previous/"sources.jsonl").read_text(encoding="utf-8").splitlines()]
    models.extend([
        {"model_id":"MWJ25E","model_version":"unspecified","document_version":"pdp-snapshot-2026-10-11",
            "name":"LG 전자레인지 MWJ25E","product_family":"microwave","synthetic":False,
            "capacity_l":25,"dimensions_mm":{"width":476,"height":272,"depth":370},"spec_source_id":"SPEC-MWJ25E-01"},
        {"model_id":"DUBJ2EA","model_version":"unspecified","document_version":"pdp-snapshot-2026-10-11",
            "name":"LG 디오스 식기세척기 DUBJ2EA (단종)","product_family":"dishwasher","synthetic":False},
    ])
    def record(mid,kind,number,location,content,url,published=None,feature=None):
        value={"source_id":("REVIEW" if kind=="review" else "SPEC")+"-"+mid+"-"+number,"kind":kind,
            "model_id":mid,"model_version":"unspecified","document_version":"pdp-snapshot-2026-10-11",
            "data_version":VERSION,"location":location,"text":content,"synthetic":False,
            "sha256":hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "origin":{"source_url":url,"retrieved_date":"2026-10-11","published_date":published,
                "representation":"excerpt" if kind=="review" else "factual_summary",
                "model_matching":"explicit_model_verified","purchase_verified":None,"sponsorship":None}}
        if feature:
            value.update(feature_key=feature,availability="present")
        records.append(value)
    for mid,number,feature,location,content in [
        ("MWJ25E","01","dimensions_capacity","제품 상세 스펙/용량·크기",
         "용량25L, 가용용량13L. 외형(W×H×D)476×272×370mm. 조리실 내부 크기322×228×335mm. 내부 크기는 입구 유효 폭/회전 가능한 용기 크기/안전 여유를 보증하지 않는다."),
        ("MWJ25E","02","touch_popup_control","제품 상세 스펙/조작부",
         "조작부는 글라스 터치와 팝업 다이얼이다. 링의 고정 성능이나 소비자 불편 해소율을 측정한 사실은 아니다."),
        ("MWJ25E","03","smart_inverter","제품 상세 스펙/성능·기능",
         "스마트 인버터를 지원하고 정격 고주파 출력은1000W다. 특정 용기/음식의 안전성·가열 균일성을 이 수치만으로 확정할 수 없다."),
        ("DUBJ2EA","01","place_settings_installation","제품 상세 스펙/식기수·설치",
         "12인용이며 빌트인 전용이다. 인원수는 내부 치수·특정 식기 적재 가능 크기를 뜻하지 않는다."),
        ("DUBJ2EA","02","true_steam","제품 상세 스펙/세척 기능",
         "100℃ 트루스팀을 지원한다. 기능 존재만으로 모든 눌어붙은 음식의 제거·사전 작업 불필요를 보증하지 않는다."),
        ("DUBJ2EA","03","automatic_door_drying","제품 상세 스펙/건조 기능",
         "자동 문열림 건조를 지원한다. 이 건조 기능은 세척 잔여물의 제거 여부를 대신 입증하지 않는다."),
        ("DUBJ2EA","04","catalog_lifecycle","페이지 제품 상태·제품 상세 스펙 기준일",
         "페이지는 단종 제품으로 표시하고 스펙 기준일2025-04-22를 명시한다. 현재 판매 중인 모델이나 현재 시장 전체로 일반화하지 않는다."),
    ]:
        record(mid,"product_fact",number,location,content,PAGES[mid],feature=feature)
    record("MWJ25E","review","01","본문 후반/팝업 다이얼 마감 설명; 자기 수령품 한정",
        "제가 받은 것만 이런건지는 모르겠는데, 팝업 다이얼 버튼 주변에 저 하얀 링 부분이, 제대로 고정이 안되어서 좀만 건들어도 흔들 거리며 소리가 나더라구요.",
        "https://i-blubird.tistory.com/908","2022-04-21")
    record("DUBJ2EA","review","01","LG 설치·사용 이후/설거지 결과물; 이전 SK매직 경험과 구분",
        "계란 눌어붙은 거 같은 거는 완전히 제거 안되는 것은 똑같아서, 그런건 미리 수세미로 긁어주고 넣어줘야 하는 건 똑같더군요.",
        "https://i-blubird.tistory.com/518","2021-03-22")
    target.mkdir(parents=True)
    (target/"models.json").write_text(json.dumps(models,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    (target/"sources.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n" for r in records),encoding="utf-8",newline="\n")
    manifest={"data_version":VERSION,"synthetic":False,"purpose":"business","created_date":"2026-10-11",
        "provenance":"New-project v3 refrigerator sources preserved; new exact LG MWJ25E/DUBJ2EA official factual summaries and observed short public personal review excerpts. Same reviewer for the two added appliances; purchase/sponsorship unverified. DUBJ2EA discontinued. No old LG project data. No full-page snapshot or live crawl in this script.",
        "model_count":len({m["model_id"] for m in models}),"scope_count":len(models),
        "review_count":sum(r["kind"]=="review" for r in records),"fact_count":sum(r["kind"]=="product_fact" for r in records),
        "files":[{"path":name,"sha256":hashlib.sha256((target/name).read_bytes()).hexdigest()} for name in ("models.json","sources.jsonl")]}
    (target/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"data_version":VERSION,"models":len(models),"reviews":manifest["review_count"],"facts":manifest["fact_count"]}))


if __name__=="__main__":
    main()
