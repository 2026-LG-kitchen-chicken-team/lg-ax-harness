---
name: review-and-revise
description: "상품기획 후보의 원문 의미·모델·기존 기능 중복·가정·제약을 검토하고 최초 생성과 최대2회 수정을 저장할 때 사용한다."
---

# 검토·수정·저장

후보마다 원문을 대조해 [업무 검토 계약](../../docs/contracts/product-planning.md)의 assessment를 작성한다. 주장 출처가 있어도 반대 의미·이전 제품·다른 옵션이면 supported로 적지 않는다. 비용/효과 미측정도 유지한다.

보고된 해석의 누락·불확실성·기존 기능 중복·치수 부족을 확인한다. 저장 자체가 validate_result_contract와 review_product_result를 수행하므로 선행 호출은 진단이 필요할 때만 한다. 모델의 원문 검토와 assessment 작성은 필수다. can_finalize_reported_result=false면 completed로 출력하지 않는다. 통과도 의미·제품 성능을 자동 입증하지 않는다.

open_request_bundle 또는 마지막 save 응답의 turn.result_version을 사용해 `save_reviewed_result`에 result와 assessment를 함께 넣어 최초0·수정1/2를 저장한다. [짧은 저장 양식](references/payload.md)을 참고한다. state_conflict/재개/외부 변경 때만 get_turn/current_request로 재확인한다. 검증 실패 후보도 시도에 포함한다. 저장의 accepted=false/held를 숨기지 않는다. 같은 요청 재개에 키를 보존하고 기술 실패나 자료 변경으로 turn을 새로 만들어 한도를 우회하지 않는다.

일반 저장은 response_mode="receipt"로 중복 원문 반환을 줄인다. accepted=false면 review_summary.findings의 오류 코드·claim ID를 원문과 대조하고 같은 turn에서 수정1/2를 JSON 구조로 작성한다. 불확실을 임의 supported로 바꾸지 않는다. 최종 답변은 근거 요약과 마지막 저장 receipt·export 경로/SHA이며 전체 결과/assessment는 export에 보존한다. 상세 조회/원문 결과 요구에는 current_request/get_turn을 사용한다.

초과·미해결은 held로 종료하고 확보 사실·부족 자료·다음 검증을 반환한다. 새 사용자 추가 질문에만 새 turn을 연결한다. 관측된 실제 전체 호출/실패 usage는 record_usage로 남기며 미관측은 null이다.

사용자가 진행 중인 업무를 취소하면 현재 handle/version으로 `cancel_turn`을 호출한다. 입력은 session_id/turn_id/cancel_key/reason/expected_result_version/user_submitted=true다. 같은 취소 재전송은 같은 key·사유·version을 유지한다. 취소는 새 후보나 업무 수정을 만들지 않고 이후 후보 저장·등록 호출을 막는다. 기존 후보·호출·관측 usage는 이력에 남는다. completed/failed 종료 결과는 소급 취소하지 않는다. 네이티브 모델·브라우저의 실제 중단은 실행기의 중단 기능으로 별도 확인하며 cancel_turn 성공을 backend 중단 완료로 설명하지 않는다.

실행: `uv run python skills/review-and-revise/scripts/run.py OP --input JSON_PATH`. OP는 validate_result_contract/review_product_result/start_turn/get_turn/save_result/save_reviewed_result/current_request/export_session/record_usage/cancel_turn/begin_invocation/finish_invocation다. 호출 장부가 native Agent나 브라우저를 실행·취소하는 것은 아니다.

마지막 저장 응답의 accepted/status/valid와 receipt.candidate_result_version=current_result_version, 현재 handle·result_key·저장 지문을 확인하고 export_session으로 전체 세션을 파일에 내보낸다. 오래된 accepted key 재전송을 최신 결과로 쓰지 않는다. 버전 불일치나 상태 변경이면 최신 상세 상태를 조회한다. 외부 상태 변경이 없으면 같은 상태를 get_turn으로 다시 조회하지 않는다. 경로·SHA·건수만 읽고 export 원문을 문맥에 반복 전달하지 않는다. 최종 JSON은 `{receipt,export}`다. [대화 계약](../../docs/contracts/codex-product.md)을 따른다.
