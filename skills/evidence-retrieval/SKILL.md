---
name: evidence-retrieval
description: "선택한 냉장고 모델의 저장된 실제 리뷰·공식 사양·설명서를 정확한 버전으로 조회할 때 사용한다."
---

# 저장 근거 조회

모델 ID와 model/document/data 버전을 확인한다. 상세 불편을 사용자에게 요구하지 않는다. `doctor`의 catalog와 `prepare_planning_input`을 사용하되 외부 자료를 추가할 계획이면 최종 버전 확정 후 turn을 시작한다.

저장 자료로 시작할 때 `open_request_bundle`을 사용하면 기존 open_request와 같은 handle·상태 및 정확한 scope의 리뷰/사실/원문을 한 번에 받는다. 원문은 evidence_refs에 한 번만 있으며 records는 종류 metadata다. 각 조회20개와 전체 출력 상한으로 잘릴 수 있으므로 retrieval.truncated/byte_truncated/omitted_source_ids를 확인한다. 긍정·상충 의견도 판단한다. 원문이 이미 있으면 select_evidence로 중복하지 않는다.

추가 조회에만 `retrieve_reviews`와 `retrieve_product_facts`를 정확한 scope로 실행한다. 필요한 주제만 좁혀 조회하며 literal 검색은 의미 검색이 아니다.

검토에 쓸 원문만 `select_evidence`로 가져온다. 원문 지문·URL·위치를 보존한다. 긍정 의견을 불편으로 바꾸지 않는다. 자료 부족·갱신 필요·옵션 혼합은 메인에 반환해 외부 조사 또는 보류로 연결한다.

실행: `uv run python skills/evidence-retrieval/scripts/run.py OP --input JSON_PATH`. OP는 doctor/open_request/open_request_bundle/current_request/prepare_planning_input/retrieve_reviews/retrieve_product_facts/select_evidence/match_product_scope다. 기본 자료는 실제 lg-research-v3, 합성 시험 자료는 `--data`로 명시한다. 필드는 review-and-revise의 [짧은 저장 양식](../review-and-revise/references/payload.md), 상세는 [공통 Tool 계약](../../docs/contracts/common-tools.md)을 필요한 작업에 한해 읽는다. 출력의 구조 검사와 불편의 실제 의미를 구분한다.

첫 사용자 질문은 초기 자료 확정 후 open_request로 내부 ID·입력·turn을 생성한다. 같은 요청 재개는 current_request로 읽고 실제 추가 질문만 같은 session_id/prior_turn_id에 연결한다. [대화 계약](../../docs/contracts/codex-product.md)을 따른다.
