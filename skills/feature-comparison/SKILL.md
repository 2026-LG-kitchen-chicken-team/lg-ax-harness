---
name: feature-comparison
description: "원문으로 확인한 불편을 같은 냉장고 모델의 기존 기능·사용 조건과 대조해 남은 문제를 판단할 때 사용한다."
---

# 기존 기능 대조

bundle의 정확한 모델·문서 범위와 제품 사실을 사용한다. 모델 범위가 모호하거나 추가 사실·잘림·변경 문서를 확인할 때만 `match_product_scope/retrieve_product_facts/select_evidence`로 필요한 자료를 조회한다. 이미 받은 원문을 다시 조회하지 않는다. 단독 실행에서는 필요한 정확 scope와 사실을 먼저 확보한다. exact 스펙을 우선하고 공통 홍보 이미지·FAQ·적용 모델 한정 설명서를 현재 모델에 무조건 적용하지 않는다.

불편마다 기존 기능과 사용 조건을 대조해 resolved/partially_resolved/unresolved/uncertain을 판단하고 이유를 적는다. 기능 존재는 해결 완료가 아니다. not_documented는 부재가 아니고 conflicting이면 하나를 임의 선택하지 않는다.

근거가 있는 미해결 부분만 remaining_pains에 넣고 [업무 검토 계약](../../docs/contracts/product-planning.md)의 feature_matches로 원래 pain과 제품 출처를 연결한다. 치수·조절 간격·도어 개방 조건이 필요하지만 없으면 조사 또는 보류한다. 외형 값으로 내부를 추정하지 않는다.

실행: `uv run python skills/feature-comparison/scripts/run.py OP --input JSON_PATH`. OP는 match_product_scope/retrieve_product_facts/select_evidence다. 비교 의미는 네이티브 모델의 판단이며 코드 검색만으로 해결 판정하지 않는다.
