---
name: needs-structuring
description: "확보한 실제 후기에서 현재 제품의 불편·사용 맥락·상충 의견을 원문 근거에 연결해 정리할 때 사용한다."
---

# 불편 구조화

관련 원문이 bundle에 정확한 모델·자료 버전·위치·지문·인용으로 있으면 그대로 읽고 판단한다. 누락/잘림/새 출처에만 `select_evidence`로 추가 조회한다. 전체 업무의 `save_reviewed_result`가 원문 연결을 검사하므로 변형 없이 사용한 refs를 중간에 다시 검사할 필요는 없다. 단독 실행·refs 변경·불일치 진단에서는 `validate_source_refs`를 실제 실행한다. 원문 의미 대조는 항상 필요하며 코드 검사는 의미 판단이 아니다.

각 의견을 현재 제품의 관측 불편/긍정/사용 기대/이전 제품 경험/불명확으로 구분한다. 사용자 맥락과 반대 의견을 함께 적는다. 반복 인용과 같은 원문의 재게시를 독립 고객 수로 세지 않는다. 한 후기에서 시장 발생률을 계산하지 않는다.

현재 해당 모델의 불편만 ProductResult.pains에 넣고 id/text/source_ids를 보존한다. [업무 검토 계약](../../docs/contracts/product-planning.md)에 따라 support_status·scope_relation·rationale를 기록한다. 불명확·긍정만 있으면 빈 pains와 부족 사유를 반환해 조사/보류한다.

실행: `uv run python skills/needs-structuring/scripts/run.py OP --input JSON_PATH`. OP는 select_evidence/validate_source_refs다. 구조화는 실제 네이티브 모델이 수행하며 helper가 불편을 자동 생성하지 않는다.
