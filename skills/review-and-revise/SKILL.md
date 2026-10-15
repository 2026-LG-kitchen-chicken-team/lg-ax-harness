---
name: review-and-revise
description: "상품기획 후보의 원문 의미·모델·기존 기능 중복·가정·제약을 검토하고 최초 생성과 최대2회 수정을 저장할 때 사용한다."
user-invocable: true
---

# 검토·수정·저장

자연어 요청의 자동 선택이 기본이며 Codex `$review-and-revise`(`/skills`), Claude `/review-and-revise` 명시 호출도 같은 업무 경로를 쓴다. 현재 업무 문맥에 같은 본문·지문이 없거나 문맥/버전이 바뀌면 판단 전에 `get_work_instructions`로 `review-and-revise`와 필요한 `main`·`payload`만 선택해 실제 본문을 받는다. 이미 같은 지침이 문맥에 있으면 재독해하지 않고 동일 문맥·지문의 `known_context` 신고를 사용한다. 실행은 `uv run python skills/review-and-revise/scripts/run.py get_work_instructions --input runtime-data/instructions.json`이며 입력·증거 구분은 프로젝트 루트 `docs/contracts/instruction-loading.md`를 따른다. 반환 receipt는 코드 반환 근거이고 독해·적용·이해 인증이 아니다.

명시된 새 사용자 후속 업무는 같은 business session_id와 실제 prior_turn_id, 새 원질문/question·새 request_key로 open_product_workflow를 시작할 수 있다. open_product_workflow는 evidence-retrieval wrapper의 OP이며 이 Skill은 반환된 후속 현재 handle/version을 저장·finish에 사용한다. 이전 완료 결과·수정 횟수·완료 시계는 역사적 참조로 남고 새 문맥에서의 valid 여부와 구별한다. 같은 업무의 실패/timeout/저장 복구는 원래 request/turn/research_id를 유지하며 새 입력으로 한도를 우회하지 않는다. active-workflow 재개와 새 후속 업무를 구분해 현재 handle을 확인한다.

최종 답변은 save_and_export의 completion_summary.text를 그대로 전달한다. 누락 시 get_completion_summary({session_id,turn_id,expected_result_version})로 같은 현재 결과에서 얻는다. 추가 설명에도 저장된 기획 문구·조건·출처 범위를 유지하며 새 사실을 넣지 않는다. '검토 완료/확인 필요/기획 보류'를 고정 제목으로 붙이지 않는다. 내부 receipt와 status는 보존한다. 파일 생성·구조 검사와 실제 이미지 검수를 구분하며, contact sheet 생성이나 caller의 passed 신고만으로 화면 검수 완료라고 쓰지 않는다. 실제 이미지 도구로 확인한 범위만 설명한다.

명시 파일 출력에만 기존 코드 보고서를 먼저 사용한다. 별도 구성은 title/summary/sections와 sources:[]로 작성하며, 원문과 긴 메타데이터는 catalog에서 코드가 채운다. 정확 block.source_ids와 중요한 한계는 유지한다. 자료 폭·원문을 줄이거나 충돌하는 원문을 바꿔 시간을 단축하지 않는다.

독립 검토를 선택할 때 prepare_review_packet(session_id/turn_id/candidate_path/packet_key)으로 6필드 후보의 불변 사본을 만든다. packet_path/packet_sha256·evidence_sources_path/evidence_sources_sha256/evidence_source_count와 전체deadline을 전달한다. 자식은 후보 주장과 별도 원문 JSONL의 관련 전체 등록본문을 대조하고 읽은 binding/범위를 짧게 ack한다. packet/candidate의 중복 인용 재독해는 피한다. reviewer는 실제 spawn 응답 시각부터 최대180초, 전체deadline 안의 최종90초를 예약한 deadline으로 관측하며 준비 시간을 자식 시간에서 빼지 않는다. 짧은 findings를 먼저 받고 반환 뒤 verify_review_packet(session_id/turn_id/packet_path/packet_sha256)으로 현재 결속을 확인한다. packet ready는 원문 의미/후보 valid/save 승인 인증이 아니다. 수정은 별도 후보 파일에서 하고 불변 packet을 덮어쓰지 않는다.

명시 자료집·파일 보고서 요청에만 [보고서 작성](references/report-writing.md)을 읽고 작성한다. 공개 형식은 프로젝트 루트 docs/contracts/reader-deliverables.md다. 합성 목업 검수는 실제 제품 업무의 완료 증거가 아니다. 실제 조사→분석→검토→저장→보고서 전달을 확인하고 가상 내용·수치는 복사하지 않는다. report_plan은 실제 조사 범위에 따라 자유롭게 구성하고 별도 runtime-data 내부 파일로 전달할 수 있다.

메인 Agent의 공통 안전 규칙으로 원문을 대조해 result/assessment를 작성한다. 저장 필드는 프로젝트 루트의 skills/review-and-revise/references/payload.md를 읽는다. Skill이 .agents/skills 아래 발견돼도 docs는 프로젝트 루트 docs/contracts/다. 같은 본문/상세계약 재독해는 진단 때만 한다.

최초 후보를 저장하기 전 메인이 기존 자체 검토에서 각 pain의 연결 원문이 현재 대상의 어떤 부정 평가·실패·지장·부담을 직접 보고하는지 확인한다. 상태 관측·정상화 경과·조언·미래 기대만 있고 직접 보고된 영향이 없으면 확인된 불편에서 빼고 필요한 관측/가설을 decision_notes/assumptions로 옮긴다. "직접 불편 표현은 없지만" 같은 단서를 붙여도 pains에 남기면 불편으로 분류한 것이다. 원문이 지지하지 않는 원인·대상·시점·범위를 덧붙이지 않고, 조건부 제안의 한계가 근거 없는 pain을 정당화하지 않게 한다. 이 점검은 별도 필드·의무 서브에이전트·추가 모델 호출을 요구하지 않는다.

같은 점검에서 긍정 평가·조언·정상이라는 설명이 섞였다는 이유만으로 실제 부정 경험을 지우지 않는다. 직접 지지되는 불편과 그 조건·완화 맥락을 남기고, 제외는 해당 주장에만 적용한다. 나머지 근거가 기획을 지지하면 계속 검토하며, 핵심 전제가 사라진 안만 수정/보류한다. 저장·집계·최종 요약에도 같은 구분을 유지한다.

bundle의 candidate_template을 실제 판단으로 채운다. result_limits를 확인하고 Python json으로 파일 작성 뒤 save_and_export를 실행한다. 기본 report:false의 delivery_ready/web_ready와 현재 web_result 파일/SHA/binding을 확인한다. 양식·파일 생성은 의미 승인이나 HTML 연결을 인증하지 않는다.

미확인을 `supported`/`false`로 바꾸어 저장 검사를 통과시키지 않는다. 남은 불편·콘셉트가 근거에서 출발한 조건부 가설이면 payload.md의 `claim_checks.qualification`을 **최초 후보에서** 실제 한계와 함께 작성한다. `basis:"conditional_draft"`, `limitations`, `original_statement_supported`는 주장별 AI 판단이며 자동 기본값이 아니다. 원문에 없는 제안은 마지막 값을 false로 유지하고 support_status=uncertain·scope_relation=unclear·resolution=uncertain·duplicates_existing=null을 보존할 수 있다. 지지 근거가 없거나 이미 해결·중복·치수 부족이면 qualification으로 우회하지 않고 valid held를 작성한다. 조건부/페이지 연결 귀속이 있는 후보는 최초 저장 전에 review_product_result로 한 번 진단하고, 같은 거절 이유를 읽지 않은 채 수정 한도를 소진하지 않는다.

workflow의 elapsed_seconds는 시작부터 finish까지 모델 판단·Tool·대기를 포함한 경과시간이다. 개별 코드 실행시간이나 최종 모델 응답·GUI 전달까지 포함한 native 전체 시간으로 쓰지 않는다. 최종 응답까지 외부 관측이 없으면 전체 시간은 미측정으로 남긴다. 마지막 거절 후보가 held가 된 경우와 accepted/valid인 held는 구분한다. 보고서 실패는 같은 현재 버전의 deliver_result로 복구하며, 보류라서 항상 보고서를 만들 수 없다고 일반화하거나 새 요청으로 수정 한도를 초기화하라고 안내하지 않는다.

보류의 판단 근거도 decision_notes에 원문 사실·AI 해석·미확인으로 구분하고 정확 refs에 연결한다. 원문 직접 인용은 support_quote의 연속 구간이며 요약/판단은 공식 발언으로 표시하지 않는다. 후기의 실제 영향·발생/회피 조건·긍정·유보 문맥과 고유 후기 ID/분모를 확인한다. bundle의 truncated=false/누락 ID 없음만으로 원페이지나 판단 문맥 전체를 확인했다고 쓰지 않는다. 중요 문맥 미확인은 조건부 한계 또는 held에 반영한다. 최종 답변에도 이 구분과 사용한 URL/위치를 전달한다. 자체 추정 실행시간은 쓰지 않으며 외부 실제 기록이 없으면 미측정이다.

completion_summary는 같은 저장 버전의 decision_notes/basis와 사용한 URL/위치를 코드로 전달하고 JSON sidecar에 실제 전체 notes/refs를 보존한다. source_fact도 AI 분류로 유지하며 사용하지 않은 catalog를 사용 근거로 세지 않는다. 노트만 있는 held의 근거를 생략하거나 원문 전체를 모델에게 다시 작성시키지 않는다.

계획의 전체 사전 배정 시도 분모·실패/중단/미응답·미확인, 같은 과업·환경의 조건통제, 오안내·완료품질·실패 탐지 비퇴행을 함께 검토한다. 효율·해결 성과를 성공 조건으로 삼는 계획에서는 미확인·실패 비율 증가와 전체 배정건 기준 해결률·완료 품질 저하의 허용 한계 및 초과 시 수정·보류 조건을 같은 성공 조건에 연결하고, 별도 기록만으로 충족 처리하지 않는다. 대상 집단의 유지·실패 비율은 해당 집단을 사전에 정한 동일 분모로 비교하고, 결과에 따라 분모를 바꾸거나 다른 집단의 구성비로 대체하지 않는다. 선택 condition_controls/guardrail_metrics는 payload.md의 타입/범위를 따른다. planning_quality_diagnostics는 structural_only/blocking=false의 누락 안내다. 누락만으로 전체 기획을 거절하지 않고 필드 존재로 의미·측정·품질을 인증하지 않는다.

저장 크기를 조정한 뒤에는 바뀐 문장마다 각 절의 술어·정확 모델·조건·시점이 현재 연결 source_ids의 원문으로 지지되는지 다시 대조한다. 술어를 남기고 그 근거만 삭제하지 않는다. 여러 출처를 묶은 문장은 출처별로 나누거나 필요한 직접 근거를 모두 유지한다. 집계/제외/인과는 원문 직접사실과 구분해 AI 판단으로 표시한다. 긴 본문은 별도 report_plan으로 옮기되 자료 폭·원문·미확인·반례는 줄이지 않는다. 수정 후보와 현재 저장/export/보고서/최종의 주장 범위를 대조하고 미완문·수정 전 단정이 남지 않았는지 확인한다.

일반 업무는 기존6필드의 save_and_export(report:false)로 저장/export와 웹 정형 데이터 전달을 수행한다. web_ready/web_result.path/sha256/binding을 확인한다. 데이터에는 현재 결과·전체 선택 원문·출처·검토/조사 이력이 있고 웹팀이 작업 화면/보고서HTML을 만든다. PDF/DOCX/XLSX 생성·이미지검수는 기본 필수가 아니다. 명시 파일 요청에만 report:true와 기존 옵션/파일 생성·검수 규칙을 적용한다. 저장 accepted=false도 최초0/수정1/2를 소비하며 새 turn으로 초기화하지 않는다. semantic_status=unverified, acceptance_ready=false를 유지한다. 현재 completion_summary.text를 전달하고 실제 web/export 응답 위치를 유지한다. 요약은 일반 코드가 저장된 내용을 선택한 것이며 새 의미 승인이나 모델의 모든 출력 강제가 아니다.

재개·충돌은 current_request/get_turn, export 실패는 export_session으로 복구한다. 과거 실패 후보·검토·출처·usage는 export에 남고 원문 export 전체는 문맥에 재입력하지 않는다. 기존 save_reviewed_result(response_mode=receipt) → export_session도 호환한다. 실제 관측 호출만 record_usage로 남기고 전체 native usage라고 가정하지 않는다.

명시적 진행 중 취소는 새 업무 turn 없이 실제 대상의 현재 상태를 확인하고 cancel_turn(session_id/turn_id/cancel_key/reason/expected_result_version/user_submitted=true)을 호출한다. reason에 실제 취소 원문을 보존한다. 원문 기록이나 최종 응답을 위해 추가 followup turn을 만들지 않는다. 같은 취소 재생은 입력 그대로 유지한다. 후보·수정·usage 보존, 취소 뒤 저장/등록 금지, completed/failed 소급 취소 금지다. 최종 {cancellation,export}에는 실제 취소 대상 응답을 넣고 export의 대상 상태·후보 이력과 대조한다. 로컬 저장과 원격/native 실제 중단을 구분한다.

기본 웹 데이터 제작 실패는 현재 session/turn/result_version의 prepare_web_result로 복구한다. 기존 명시 파일 report:true의 제작 실패만 deliver_result와 해당옵션으로 복구한다. 복구는 새 업무 turn/기획 수정이 아니며 같은 버전은 중복 생성하지 않는다. 기본 실행은 화면·폴더를 자동 열지 않는다. web_ready는 HTML 렌더링·웹 연결·시각검수 인증이 아니다.

실행: `uv run python skills/review-and-revise/scripts/run.py OP --input JSON_PATH`. OP: save_and_export/prepare_web_result/deliver_result/save_reviewed_result/export_session/current_request/get_turn/record_usage/cancel_turn/prepare_review_packet/verify_review_packet/get_completion_summary. 진단: validate_result_contract/review_product_result/start_turn/save_result/begin_invocation/finish_invocation. 장부는 실제 Agent/Tool/원격 취소를 대신하지 않는다.

최종 절별 귀속 점검: 사실 문구를 쓰기 전에 연결 원문에서 각 절의 주어·술어·대상·조건·비교·시점·매체를 확인한다. 원문에 없는 속성은 사실에서 빼고 기획 가정으로 옮긴다. 다른 절·다른 후기의 조건을 전이하지 않고 장부·assessment·저장·최종 답변에 같은 귀속을 유지한다. 문의/반품 감소 같은 대리 지표와 실제 과업 완료품질·오판·실패 탐지를 구분하여 검증 계획을 작성한다. 기존 동등 안내의 존재만으로 노출 불편을 새로 확정하지 않는다.

최종 전달은 현재 completion_summary.text와 실제 응답 경로를 사용한다. 후기/자료 단위와 미확인을 강화하지 않는다. Tool 오류의 상세 receipt는 내부에 보존하며 사용자에게는 해당 원URL의 접근 실패/부분 관측과 실제 영향을 설명한다. HTTP code/원인이 관측되지 않았으면 만들지 않고, 없는 파일 경로·다른 사이트 오류 링크를 안내하지 않는다. 명시 catalog를 쓰는 호출에는 같은 --data를 유지한다. 국소 표현 오류와 핵심 전제 오류의 영향을 나누고, planned_not_measured 검증계획의 상세 분모/실패 처리는 보완 항목으로 남긴다. 그 항목만으로 전체 업무 실패를 선언하지 않는다.
