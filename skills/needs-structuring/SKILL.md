---
name: needs-structuring
description: "확보한 실제 후기에서 현재 제품의 불편·사용 맥락·상충 의견을 원문 근거에 연결해 정리할 때 사용한다."
---

# 불편 구조화

관련 원문을 `select_evidence`로 읽고 `validate_source_refs`로 모델·위치·지문·인용을 대조한다. 코드 검사는 의미 판단이 아니다.

각 의견을 현재 제품의 관측 불편/긍정/사용 기대/이전 제품 경험/불명확으로 구분한다. 사용자 맥락과 반대 의견을 함께 적는다. 반복 인용과 같은 원문의 재게시를 독립 고객 수로 세지 않는다. 한 후기에서 시장 발생률을 계산하지 않는다.

현재 해당 모델의 불편만 ProductResult.pains에 넣고 id/text/source_ids를 보존한다. [업무 검토 계약](../../docs/contracts/product-planning.md)에 따라 support_status·scope_relation·rationale를 기록한다. 불명확·긍정만 있으면 빈 pains와 부족 사유를 반환해 조사/보류한다.

실행: `uv run python skills/needs-structuring/scripts/run.py OP --input JSON_PATH`. OP는 select_evidence/validate_source_refs다. 구조화는 실제 네이티브 모델이 수행하며 helper가 불편을 자동 생성하지 않는다.
