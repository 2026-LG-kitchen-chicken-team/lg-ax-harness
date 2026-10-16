---
name: evidence-retrieval
description: "질문에서 지정하거나 해석한 제품군 또는 정확 모델의 실제 리뷰·공식 사양·설명서를 정확한 버전으로 조회할 때 사용한다."
user-invocable: true
---

# 저장 근거 조회

자연어 요청의 자동 선택이 기본이며 Codex `$evidence-retrieval`(`/skills`), Claude `/evidence-retrieval` 명시 호출도 같은 업무 경로를 쓴다. 현재 업무 문맥에 같은 본문·지문이 없거나 문맥/버전이 바뀌면 판단 전에 `get_work_instructions`로 `evidence-retrieval`와 필요한 `main`만 선택해 실제 본문을 받는다. 이미 같은 지침이 문맥에 있으면 재독해하지 않고 동일 문맥·지문의 `known_context` 신고를 사용한다. 실행은 `uv run python .agents/skills/evidence-retrieval/scripts/run.py get_work_instructions --input runtime-data/instructions.json`이며 입력·증거 구분은 프로젝트 루트 `docs/contracts/instruction-loading.md`를 따른다. 반환 receipt는 코드 반환 근거이고 독해·적용·이해 인증이 아니다.

국소 표현/검증 계획 보완과 핵심 근거 오류는 영향 범위를 구분한다. 전자는 보완 항목이며 그 자체로 업무 전체 실패를 뜻하지 않는다. 최종 전달은 현재 저장 버전의 completion_summary.text를 유지하고 새 사실·조건·매체를 추가하지 않는다.

## 전달·검토 범위 기록

초기 bundle 3~4개만 읽고 기획을 끝내지 않는다. 새조사는 자연 완료 측정이며 기본1800초는 안전 상한이고 마지막90초는 새수집을 닫아 전달을 준비한다. 명시 예산과 이미 시작된 시계는 변경하지 않으며 과거300/600초는 당시 요청 이력이다. 같은 session_id/turn_id와 최종 --data를 유지해 evidence_inventory/evidence_coverage로 등록·완전본문전달·호출자신고검토·제외·누락을 확인한다. 이는 전체 웹 원문이나 고객 수·의미 충분성 인증이 아니다.

read_evidence_batch 입력은 {session_id,turn_id,offset:0,limit:20}이고 선택 max_bytes(4096~63000)/source_ids를 허용한다. 반환 전체 reference는 줄이지 않으며 출력bytes에맞춰 실제 전달수/next_offset를 계산한다. next_offset가 null일 때까지 필요한 전체선택본문을 확인한다. initial bundle에서 실제 반환한 refs는 자동 전달장부에 기록되며 생략 refs는 기록되지 않는다. 중복전달은 고유source 수를 늘리지 않는다. 자료/code/version/context가 바뀌거나 취소되면 새coverage로 기존 검토를 재사용할 수 없다.

record_evidence_review 입력은 {session_id,turn_id,review_key,records:[{source_id,disposition:"reviewed" 또는 "excluded",reason:구체적판단/제외이유}]}다. reviewed는 전체등록본문을 전달받은후에만 신고한다. excluded도 신규 timing_policy:natural-completion-v1의 completed에서는본문전달이 필요하다. 초기사례밖의 긍정·부정·장기·조건·반례·설명서·사양의 의미/다양성은 AI가 실제 검토하고 부족을 표시한다. 의미미확인을 ID개수로 통과시키지 않는다. 모든선택catalog항목 전달·검토/제외기록이 없으면 completed를저장하지말고 같은turn의 held에 미검토범위를 남긴다. 기록은 export_session에 보존된다.


브랜드·시장 미지정 제품군의 기본 대상은 국내 LG 모델이다. 명확한 다른 모델/브랜드/시장 요청은 같은 request의 set_request_scope_policy에 literal user_quote를 보존하고 해석한다. 제조사 국내 제품 정체성을 먼저 확인하며 모델 prefix·검색순위·한국어 설명서만으로 브랜드/판매국을 추정하지 않는다. 국내 LG 후보의 선택은 실제 접근 근거에 따라 AI가 판단한다.

제품명에서 새 실제 조사를 시작할 때는 open_product_workflow를 사용하고 같은 요청의 record_workflow_event/workflow_status로 전체 예산·출처 이력·종료·분석 범위를 보존한다. 실행기 active-workflow.json이 있으면 원래 요청을 재사용한다. 상세 필드는 프로젝트 루트 docs/contracts/product-workflow.md다. 반환 bundle은 전체 조사원문이 아니며 turn결속 read_evidence_batch의 offset/next_offset로 등록본문을 순회한다. turn전 진단에는 retrieve_reviews/retrieve_product_facts를 사용할 수 있다. 분석하지 않은 항목을 전량 분석으로 표시하지 않는다.

명시 자료집 파일 출력에만 [보고서 작성](../review-and-revise/references/report-writing.md)의 실제 종류별 구성에 맞춘다. 확보한 원문·요약·모델/문서 버전·관측 범위·URL/위치를 보존하며 등록 ID는 내부 연결에만 사용한다. 비어 있는 조사 종류나 가상 통계로 파일을 채우지 않는다.

원래 질문의 제품 범위·목표·제약은 native AI가 판단한다. 제품군은 product_family/scope_mode=family_catalog, 정확 모델은 model_id로 명시하며 코드가 질문 키워드로 고르지 않는다. 기본 data/business/empty에는 제품·후기·정답이 없다. 필요한 자료·관측일·정확 버전을 확인하고 신규/부족/갱신이면 web-evidence-collection을 적용한다. 이미 충분한 저장 자료만 직접 재사용하며 현재 질문에 맞는 이유와 한계를 밝힌다.

조사 전 open_request로 실제 question/user_submitted:true를 저장하고 session_id/request_key/request_version을 유지한다. 선택 필드 없이 요청만 저장할 수도 있다. 미등록 선택은 research_required이다. record_request_research 입력은 {session_id,request_key,event_key,expected_request_version,status,reason,observation_refs:[]}이며 status는 researching/research_required/held/needs_input/failed다. snapshot ID는 실제 관측값만 기록한다. 조사후 resolve_request_bundle 입력은 {session_id,request_key,event_key,expected_request_version,selection:{model_id 또는 product_family,scope_mode}}이다. --data에는 import 응답의 data_path를 지정한다. 원질문/조건은 불변이며 이미 연결된 turn은 재연결할 수 없다. 동일 event_key 재전송은 같은 내용만 허용하고 충돌은 current_request로 확인한다. turn 전 보류도 export_session으로 이력을 내보낸다.

저장 자료로 시작할 때 `open_request_bundle`을 사용하면 기존 open_request와 같은 handle·상태 및 정확한 scope의 리뷰/사실/원문을 한 번에 받는다. 원문은 evidence_refs에 한 번만 있으며 records는 종류 metadata다. 단일 모델은 각 조회20개, 제품군은 모델 수로 분할한 전체 최대40개 원문과 출력 상한으로 잘릴 수 있으므로 retrieval.truncated/byte_truncated/omitted_source_ids를 확인한다. 긍정·상충 의견도 판단한다. 원문이 이미 있으면 select_evidence로 중복하지 않는다.

turn 전 외부 조사 필요성 판단과 bundle의 누락/잘림/추가 사실 조회에만 `retrieve_reviews`와 `retrieve_product_facts`를 정확한 scope로 실행한다. 필요한 주제만 좁혀 조회하며 literal 검색은 의미 검색이 아니다. 주요 기획 근거의 저장 발췌가 실제 영향·발생 조건·긍정/회피·유보·시점/모델 귀속을 판단할 만큼 충분한지 먼저 확인한다. 중요한 문맥이 발췌 밖일 가능성이 있으면 turn 전에 같은 원URL의 주변 문단만 제한적으로 관측·별도 등록하고 같은 request를 resolve_request_bundle로 연결한다. 전체 원문 수집을 강제하지 않는다.

truncated=false/omitted_source_ids 없음은 bundle 전달 범위의 완전성이다. 원페이지나 판단에 필요한 문맥 전체를 확인했다는 뜻이 아니다. 원문이 refs 내부에 한 번 있다는 원칙과 turn 전 부분 조회/최종 bundle 사이의 일부 텍스트 중복 가능성을 구분한다. 이미 받은 정확 refs의 반복 조회는 하지 않되 필요한 주변 문맥은 좁혀 관측한다. prior_turn_id 후속은 선택 생략만으로 조사 대기 상태가 보장되지 않으므로 현재 request/turn 상태를 확인한다.

bundle에 없는 검토 원문만 `select_evidence`로 가져온다. 이미 받은 정확한 원문 지문·URL·위치는 변형 없이 사용한다. 긍정 의견을 불편으로 바꾸지 않는다. turn 전 자료 부족·갱신 필요·옵션 혼합은 메인에 반환해 외부 조사 또는 보류로 연결한다. 시작 뒤 새 부족이면 원래 --data/자료 버전으로 held 사유를 저장·export하고, 새 자료 등록/반영은 다음 실제 추가 입력이 도착한 뒤 그 입력의 turn 시작 전에 한다. 이미 외부 변경으로 turn이 무효화됐으면 그 오류와 이력을 보존하며 실제 새 사용자 입력 없이 새 turn을 만들지 않는다.

실행: `uv run python .agents/skills/evidence-retrieval/scripts/run.py OP --input JSON_PATH`. OP는 evidence_inventory/read_evidence_batch/record_evidence_review/evidence_coverage/doctor/list_models/open_request/open_request_bundle/resolve_request/resolve_request_bundle/record_request_research/current_request/prepare_planning_input/retrieve_reviews/retrieve_product_facts/select_evidence/match_product_scope다. 기본 자료는 빈 catalog다. 조사해 등록한 catalog는 `--data`로 명시하고 과거 평가 자료는 시험 때만 따로 선택한다. 필드는 review-and-revise의 프로젝트 루트 skills/review-and-revise/references/payload.md, 상세는 프로젝트 루트 docs/contracts/common-tools.md을 필요한 작업에 한해 읽는다. 제품군은 catalog의 모델에서 정하며 다른 제품군 scope를 섞지 않는다. 출력의 구조 검사와 불편의 실제 의미를 구분한다.

첫 사용자 질문은 원문 그대로 보존한다. 실제 후속만 session_id/prior_turn_id로 연결하고 제품군 후속의 전체 scope를 유지한다. 조사 진행은 동일 request에 기록하며 새 사용자 질문으로 꾸미지 않는다.
