# 짧은 저장 양식

bundle 응답의 candidate_template에는 현재 session_id/turn_id/result_key/expected_result_version/result/assessment가 들어 있다. 빈 status는 저장 불가이며 주장·원문 refs·검토·보류 이유는 AI가 작성한다. bundle 응답의 result_limits는 작성 상한 안내다. 복사 뒤 작성하며 현재 version이 바뀌면 오래된 양식으로 저장하지 않는다. 재생은 같은 key와 원문/assessment를 유지한다. 이 양식은 제품이나 질문을 선택하거나 답을 생성하지 않는다.

양식 참고이며 업무 정답·실제 실행 기록이 아니다. 일반 업무는 open_request_bundle → 원문 판단/assessment → save_and_export다. 선행 validate/review/get_turn은 진단에만 한다. save_and_export는 아래6필수 필드(assessment 포함)로 저장 검사와 export를 묶고 {save,delivery_ready,export,export_error,completion_summary}를 반환한다. response_mode 없이 receipt를 자동 사용한다. accepted=false도 후보가 저장되고 export된다. 내부 감사 JSON은 {receipt:save.receipt,export}다. export_error는 저장을 되돌리지 않으며 export_session으로 복구한다. stale replay는 delivery_ready=false다. 기존 save_reviewed_result와 export_session은 별도 호출로도 사용한다.

기본 최종 출력은 `report:false`의 검토된 현재 웹 JSON과 작은 receipt·completion_summary다. 최종 답변은 completion_summary.text를 그대로 전달한다. 누락 시 `get_completion_summary` 입력 `{session_id,turn_id,expected_result_version}`으로 같은 현재 저장 결과의 기획 문구·조건·출처에서 요약을 얻는다. Tool binding/version 검사는 새 의미 인증이나 모델 출력 전체 강제가 아니다. 사용자가 파일 출력을 명시한 경우에만 `report:true`로 기존 파일 제작을 요청한다. 선택 `report_plan_path`는 runtime-data 내부의 별도 작성 JSON 파일 경로, `open_folder`는 보고서 요청 시 기본 true인 폴더 열기 옵션이다. 전체 보고서를 아래 result에 끼워 넣거나 256KiB 때문에 줄이지 않는다. report/report_ready/report_error는 저장·export 상태와 별도로 확인한다. 작성 스키마와 파일 검수는 [보고서 작성](report-writing.md)을 따른다.

보고서 복구 OP `deliver_result`의 입력은 `{session_id, turn_id, expected_result_version, report_plan_path?, report_sources_path?, open_folder?}`다. 현재 저장 결과에서 복구하며 새 turn이나 업무 수정 횟수를 만들지 않는다. 실제 ready/files로 확인한 결과 폴더를 전달하고 내부 receipt/export는 보존한다.

open_request_bundle 입력: `{question:"실제 요청",model_id:"선택 모델",user_submitted:true}`. 후속에는 같은 session_id/prior_turn_id와 실제 추가 질문을 준다. constraints 기본값은 `{max_concepts:3,hardware_allowed:false,exclude_pains:[]}`. 전체 constraints를 지정할 때3필드를 모두 넣는다. bundle.scope는 조회 입력의 `scope`이며 PlanningInput의 배열 `model_scope`와 다르다. records는 종류 metadata, evidence_refs에 원문·URL·SHA가 한 번 들어 있다. omitted_source_ids/truncated이면 필요한 것만 좁혀 조회한다. 긍정/상충 의견을 누락하지 않는다.

save_reviewed_result 입력은6필수 필드와 선택 response_mode다. 일반 업무는 response_mode="receipt"를 사용한다:

```json
{"session_id":"도구의 값","turn_id":"도구의 값","result_key":"candidate-0","expected_result_version":0,"response_mode":"receipt","result":{"status":"held","pains":[],"existing_features":[],"remaining_pains":[],"concepts":[],"assumptions":[],"evidence_refs":[],"validation_findings":["실제 부족 근거와 이유"],"revisions":0,"usage_summary":{"status":"unknown"}},"assessment":{"claim_checks":[],"feature_matches":[],"concept_links":[]}}
```

이 빈 held는 부족 이유를 판단했을 때만 쓴다. completed에는 근거 있는 불편·기존 기능·남은 불편·콘셉트와 검토 연결이 필요하다. result<=128KiB, stdin/파일<=256KiB. refs는 claim 또는 decision_notes에서 사용한 source만 복사하며 사용하지 않으면 unused_evidence로 실패한다.

- 선택 필드 decision_notes: 최대10개 `{text,source_ids:["원문ID"],basis:"source_fact|ai_interpretation|unverified 중 한 값"}`. note별 text<=2000자, source_ids<=20개·중복 금지·정확한 한 모델 snapshot. source_fact/ai_interpretation은 nonempty IDs와 exact refs가 필요하고 unverified는 빈 IDs를 허용한다. 보류 판단에 사용한 사실과 AI 해석은 별도 note로 저장하며, 실제 근거가 전혀 없으면 미확인 이유만 남긴다. basis는 AI 신고이고 source_fact도 공식 직접 인용·의미 정확성 인증이 아니다. 기존 결과의 필드 생략은 호환하며 completed의 claim/assessment 조건을 대체하지 않는다.

- pains/existing_features/remaining_pains: `{id,text,source_ids:["원문ID"]}`. id는 전체 result 안에서 유일하다.
- concepts: 위3필드 + `{requirements:["검증 가능한 조건"],requires_hardware:false,assumptions:["미확인 조건"]}`. 최대3개이며 근거 없는 수량 채우기는 금지다. 각 concept의 requirements와 assumptions는 각각 최대10개, 각 항목은 최대1000자다. 중복 한계를 합쳐 간결하게 쓰되 중요한 미확인을 삭제하거나 확정값으로 바꾸지 않는다. result.assumptions 전체를 concept에 그대로 복제하지 말고 해당 제안의 조건만 포함한다.
- 새 업무의 concepts에는 `implementation_steps:["구현·인수 순서"]`와 `validation_plan:{metric,baseline,method,success_criterion,business_value,status:"planned_not_measured"}`도 작성한다. 구버전 초안은 선택 필드 없이 읽을 수 있으나 planning_detail_complete=false다. 이 값은 필드 존재 검사이며 효과·평가 충족 인증이 아니다. 검증 계획이 실제 고객 효과·사업 실적이라고 설명하지 않는다. 선택 `evaluation_protocol:{unit:"평가 단위·전체 시도 분모",failed_or_stopped:"실패/중단 처리",unknown:"미확인 처리"}`를 계획에 넣을 수 있다. 세 값은 짧은 설명이며 기존 결과는 필드 없이 호환한다. 세부 분모/실패 처리 미기재만으로 전체 기획을 일괄 실패로 판정하지 않는다.
- claim_checks: 모든 claim마다 `{claim_id,source_ids,support_status:"supported|unsupported|uncertain 중 한 값",scope_relation:"current_model|previous_product|unclear 중 한 값",rationale:"원문 대조 이유"}`. source_ids 순서도 claim과 같아야 한다.
- feature_matches: 남은 불편마다 `{remaining_pain_id,pain_id,feature_source_ids:["인용한 제품 사실ID"],resolution:"resolved|partially_resolved|unresolved|uncertain 중 한 값",rationale}`.
- concept_links: concept마다 `{concept_id,remaining_pain_ids:["남은 불편ID"],duplicates_existing:null,geometry_required:false,geometry_known:false,geometry_source_ids:[],rationale}`. duplicates_existing는 미확인 null, 실제 중복 true, 확인된 비교 범위에서 비중복 false다. false에는 실제 비교 근거가 필요하며 미확인을 지우지 않는다. 치수 필요 시 실제 내부 치수 근거를 대조한다. 외형 치수는 대신 쓸 수 없다.

원문이 지지하는 문장과 정확 모델 귀속·대표성·기능 해소·중복 검증을 구분한다. claim_checks의 선택 qualification은 `{basis:"page_linked_example|conditional_draft",limitations:["실제 미확인 항목"],original_statement_supported:bool}`다. 이 값은 해당 주장 자체가 원문에 직접 관측됐는지를 뜻한다. page_linked_example에는 true가 필요하며은 origin.model_matching=product_page_association인 review를 인용하는 pain에만 쓴다. 정확 모델·구매 확인/전체 고객 사실로 바꾸지 않는다. conditional_draft는 remaining_pain/concept의 가설에만 쓴다. 원문에 없는 제안은 original_statement_supported=false를 정직하게 유지할 수 있으나 출발점 원문·주장 연결과 나머지 제약을 생략할 수 없다. result.assumptions와 concept.assumptions에 실제 한계를 남긴다. scope_relation=unclear/support_status=uncertain을 유지할 수 있고 기능 해소 uncertain·중복 null도 조건부 초안으로 표현할 수 있다. unsupported·previous_product 전이·이미 resolved·중복 true·내부 치수 의존성 부족은 이 선언으로 통과하지 못한다. qualification이 없으면 기존의 supported/current_model 규칙이다. 코드가 선언의 진실성을 증명하지 않는다.

validation_plan에는 선택 `condition_controls:["시험 전 고정할 모델/버전·과업·환경·초기 상태·완료 품질"]`(1~10개, 항목1~1000자), `guardrail_metrics:[{metric:"오안내/품질 비퇴행 지표",method:"같은 조건에서 실패 포함 비교",non_regression_criterion:"악화가 없어야 할 기준"}]`(1~8개, 각3필드1~1000자)를 추가할 수 있다. 빈 배열·잘못된 타입·측정값/인증 필드는 허용하지 않으며 status는 기존 planned_not_measured만 허용한다. 실제 의미·시도 분모·실패/중단/미응답·미확인 처리는 AI가 판단하고 미정은 정직하게 설명한다. 기존 계획과 과거 결과는 새 필드 없이 호환한다. 반환 `planning_quality_diagnostics:{scope:"structural_only",blocking:false,concepts:[{concept_id,missing_optional_fields}],note}`는 선택 필드 존재 진단이며 전체 기획 실패나 의미·측정·계획 충족 인증이 아니다.

각 claim.text와 decision_notes 자체에 판단을 바꾸는 조건을 남기고 사건 순서·부정 범위를 원문과 맞춘다. existing_features의 조건을 concepts.assumptions에만 옮기거나 이전 미수행을 이후 수행에도 적용하지 않는다. 검토 신고/refs/SHA는 이 의미 보존의 인증이 아니다.

각 주장/노트 절의 대상·조건·시점·매체를 같은 연결 source 원문과 대조하고 명시없는 속성·장소·인과는 AI 해석/미확인으로 둔다. 현재 completion JSON은 저장된 전체 decision_notes/basis/refs를 보존하며 text에는 관련 판단·URL/위치를 전달한다. source_fact는 AI 신고 분류이고 전체 조회 catalog는 사용한 출처 수가 아니다. 장황한 원문·receipt를 최종 답변에 반복하지 않는다.

expected_result_version은 응답 turn.result_version(첫0, 다음1, 다음2)이다. result.revisions는 최초0/수정1/2다. 같은 후보 재전송은 같은 result_key와 원문/assessment를 유지한다. accepted=false도 저장되고 한도를 소비한다. 응답 turn이 다음 저장과 최종 상태의 기준이며 accepted/status/valid를 반드시 확인한다. 실패/취소/수정 소진을 새 turn으로 우회하지 않는다. export_session 입력은 `{session_id:"값"}`이고 큰 export를 다시 읽지 않는다.

receipt 응답에는 전체 input/latest_result 대신 ID·버전·상태·검토 요약과 result/assessment 지문이 있다. review_summary.findings는 최대20개이며 생략 건수를 표시한다. accepted=false면 같은 turn에서 Python json으로 새 수정 파일을 작성하고 불확실 주장/제약을 실제 원문과 대조한다. 문자열 apply_patch 실패를 반복하지 않는다. 마지막 답변은 현재 completion_summary.text와 실제 웹/export 경로다. 내부 `{receipt: 저장응답.receipt, export: export_session응답}`는 보존하며 사용자에게 오류 파일 방문을 요구하지 않는다. 전체 result/assessment는 export 원문에 유지한다. 최신 상세값은 current_request/get_turn에서 복구할 수 있다. JSON 파일은 UTF-8을 우선 사용하며 Windows BOM 있는 UTF-8/UTF-16도 명시적 BOM 범위에서 허용한다. 인코딩 추정은 하지 않는다.

공식 원문 직접 인용은 support_quote와 대조한다. factual_summary는 저장 해석이며 공식 인용문이 아니다. 원문 사실/AI 해석/기획 가설을 구별하고 해석을 제조사 발언으로 저장하지 않는다. 조사 전 요청만 있고 turn이 없으면 record_request_research 후 export_session하고 {request:current_request의 실제 응답,export}로 전달한다.
