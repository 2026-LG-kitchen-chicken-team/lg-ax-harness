---
name: review-and-revise
description: "상품기획 후보의 원문 의미·모델·기존 기능 중복·가정·제약을 검토하고 최초 생성과 최대2회 수정을 저장할 때 사용한다."
---

# 검토·수정·저장

후보마다 원문을 대조해 [업무 검토 계약](../../docs/contracts/product-planning.md)의 assessment를 작성한다. 주장 출처가 있어도 반대 의미·이전 제품·다른 옵션이면 supported로 적지 않는다. 비용/효과 미측정도 유지한다.

`validate_result_contract`와 `review_product_result`를 실행한다. 보고된 해석의 누락·불확실성·기존 기능 중복·치수 부족을 확인하고 can_finalize_reported_result=false면 completed로 출력하지 않는다. 통과도 의미·제품 성능을 자동 입증하지 않는다.

`get_turn`으로 현재 result_version과 수정 횟수를 확인한 뒤 `save_result`에 최초0·수정1/2를 저장한다. 검증 실패 후보도 시도에 포함한다. 저장의 accepted=false/held를 숨기지 않는다. 같은 요청 재개에 키를 보존하고 기술 실패나 자료 변경으로 turn을 새로 만들어 한도를 우회하지 않는다.

초과·미해결은 held로 종료하고 확보 사실·부족 자료·다음 검증을 반환한다. 새 사용자 추가 질문에만 새 turn을 연결한다. 관측된 실제 전체 호출/실패 usage는 record_usage로 남기며 미관측은 null이다.

실행: `uv run python skills/review-and-revise/scripts/run.py OP --input JSON_PATH`. OP는 validate_result_contract/review_product_result/start_turn/get_turn/save_result/record_usage/begin_invocation/finish_invocation다. 호출 장부가 native Agent나 브라우저를 실행·취소하는 것은 아니다.
