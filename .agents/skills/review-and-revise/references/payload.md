# 짧은 저장 양식

bundle 응답의 candidate_template에는 현재 session_id/turn_id/result_key/expected_result_version/result/assessment가 들어 있다. 빈 status는 저장 불가이며 주장·원문 refs·검토·보류 이유는 AI가 작성한다. bundle 응답의 result_limits는 작성 상한 안내다. 복사 뒤 작성하며 현재 version이 바뀌면 오래된 양식으로 저장하지 않는다. 재생은 같은 key와 원문/assessment를 유지한다. 이 양식은 제품이나 질문을 선택하거나 답을 생성하지 않는다.

양식 참고이며 업무 정답·실제 실행 기록이 아니다. 일반 업무는 open_request_bundle → 원문 판단/assessment → save_and_export다. 선행 validate/review/get_turn은 진단에만 한다. save_and_export는 아래6필수 필드(assessment 포함)로 저장 검사와 export를 묶고 {save,delivery_ready,export,export_error}를 반환한다. response_mode 없이 receipt를 자동 사용한다. accepted=false도 후보가 저장되고 export된다. 최종 JSON은 {receipt:save.receipt,export}다. export_error는 저장을 되돌리지 않으며 export_session으로 복구한다. stale replay는 delivery_ready=false다. 기존 save_reviewed_result와 export_session은 별도 호출로도 사용한다.

open_request_bundle 입력: `{question:"실제 요청",model_id:"선택 모델",user_submitted:true}`. 후속에는 같은 session_id/prior_turn_id와 실제 추가 질문을 준다. constraints 기본값은 `{max_concepts:3,hardware_allowed:false,exclude_pains:[]}`. 전체 constraints를 지정할 때3필드를 모두 넣는다. bundle.scope는 조회 입력의 `scope`이며 PlanningInput의 배열 `model_scope`와 다르다. records는 종류 metadata, evidence_refs에 원문·URL·SHA가 한 번 들어 있다. omitted_source_ids/truncated이면 필요한 것만 좁혀 조회한다. 긍정/상충 의견을 누락하지 않는다.

save_reviewed_result 입력은6필수 필드와 선택 response_mode다. 일반 업무는 response_mode="receipt"를 사용한다:

```json
{"session_id":"도구의 값","turn_id":"도구의 값","result_key":"candidate-0","expected_result_version":0,"response_mode":"receipt","result":{"status":"held","pains":[],"existing_features":[],"remaining_pains":[],"concepts":[],"assumptions":[],"evidence_refs":[],"validation_findings":["실제 부족 근거와 이유"],"revisions":0,"usage_summary":{"status":"unknown"}},"assessment":{"claim_checks":[],"feature_matches":[],"concept_links":[]}}
```

이 빈 held는 부족 이유를 판단했을 때만 쓴다. completed에는 근거 있는 불편·기존 기능·남은 불편·콘셉트와 검토 연결이 필요하다. result<=32KiB, stdin/파일<=64KiB. refs는 claim 또는 decision_notes에서 사용한 source만 복사하며 사용하지 않으면 unused_evidence로 실패한다.

- 선택 필드 decision_notes: 최대10개 `{text,source_ids:["원문ID"],basis:"source_fact|ai_interpretation|unverified 중 한 값"}`. note별 text<=2000자, source_ids<=20개·중복 금지·정확한 한 모델 snapshot. source_fact/ai_interpretation은 nonempty IDs와 exact refs가 필요하고 unverified는 빈 IDs를 허용한다. 보류 판단에 사용한 사실과 AI 해석은 별도 note로 저장하며, 실제 근거가 전혀 없으면 미확인 이유만 남긴다. basis는 AI 신고이고 source_fact도 공식 직접 인용·의미 정확성 인증이 아니다. 기존 결과의 필드 생략은 호환하며 completed의 claim/assessment 조건을 대체하지 않는다.

- pains/existing_features/remaining_pains: `{id,text,source_ids:["원문ID"]}`. id는 전체 result 안에서 유일하다.
- concepts: 위3필드 + `{requirements:["검증 가능한 조건"],requires_hardware:false,assumptions:["미확인 조건"]}`. 최대3개이며 근거 없는 수량 채우기는 금지다. 각 concept의 requirements와 assumptions는 각각 최대10개, 각 항목은 최대1000자다. 중복 한계를 합쳐 간결하게 쓰되 중요한 미확인을 삭제하거나 확정값으로 바꾸지 않는다. result.assumptions 전체를 concept에 그대로 복제하지 말고 해당 제안의 조건만 포함한다.
- 새 업무의 concepts에는 `implementation_steps:["구현·인수 순서"]`와 `validation_plan:{metric,baseline,method,success_criterion,business_value,status:"planned_not_measured"}`도 작성한다. 구버전 초안은 선택 필드 없이 읽을 수 있으나 planning_detail_complete=false다. 이 값은 필드 존재 검사이며 효과·평가 충족 인증이 아니다. 검증 계획이 실제 고객 효과·사업 실적이라고 설명하지 않는다.
- claim_checks: 모든 claim마다 `{claim_id,source_ids,support_status:"supported|unsupported|uncertain 중 한 값",scope_relation:"current_model|previous_product|unclear 중 한 값",rationale:"원문 대조 이유"}`. source_ids 순서도 claim과 같아야 한다.
- feature_matches: 남은 불편마다 `{remaining_pain_id,pain_id,feature_source_ids:["인용한 제품 사실ID"],resolution:"resolved|partially_resolved|unresolved|uncertain 중 한 값",rationale}`.
- concept_links: concept마다 `{concept_id,remaining_pain_ids:["남은 불편ID"],duplicates_existing:null,geometry_required:false,geometry_known:false,geometry_source_ids:[],rationale}`. duplicates_existing는 미확인 null, 실제 중복 true, 확인된 비교 범위에서 비중복 false다. false에는 실제 비교 근거가 필요하며 미확인을 지우지 않는다. 치수 필요 시 실제 내부 치수 근거를 대조한다. 외형 치수는 대신 쓸 수 없다.

원문이 지지하는 문장과 정확 모델 귀속·대표성·기능 해소·중복 검증을 구분한다. claim_checks의 선택 qualification은 `{basis:"page_linked_example|conditional_draft",limitations:["실제 미확인 항목"],original_statement_supported:bool}`다. 이 값은 해당 주장 자체가 원문에 직접 관측됐는지를 뜻한다. page_linked_example에는 true가 필요하며은 origin.model_matching=product_page_association인 review를 인용하는 pain에만 쓴다. 정확 모델·구매 확인/전체 고객 사실로 바꾸지 않는다. conditional_draft는 remaining_pain/concept의 가설에만 쓴다. 원문에 없는 제안은 original_statement_supported=false를 정직하게 유지할 수 있으나 출발점 원문·주장 연결과 나머지 제약을 생략할 수 없다. result.assumptions와 concept.assumptions에 실제 한계를 남긴다. scope_relation=unclear/support_status=uncertain을 유지할 수 있고 기능 해소 uncertain·중복 null도 조건부 초안으로 표현할 수 있다. unsupported·previous_product 전이·이미 resolved·중복 true·내부 치수 의존성 부족은 이 선언으로 통과하지 못한다. qualification이 없으면 기존의 supported/current_model 규칙이다. 코드가 선언의 진실성을 증명하지 않는다.

expected_result_version은 응답 turn.result_version(첫0, 다음1, 다음2)이다. result.revisions는 최초0/수정1/2다. 같은 후보 재전송은 같은 result_key와 원문/assessment를 유지한다. accepted=false도 저장되고 한도를 소비한다. 응답 turn이 다음 저장과 최종 상태의 기준이며 accepted/status/valid를 반드시 확인한다. 실패/취소/수정 소진을 새 turn으로 우회하지 않는다. export_session 입력은 `{session_id:"값"}`이고 큰 export를 다시 읽지 않는다.

receipt 응답에는 전체 input/latest_result 대신 ID·버전·상태·검토 요약과 result/assessment 지문이 있다. review_summary.findings는 최대20개이며 생략 건수를 표시한다. accepted=false면 같은 turn에서 Python json으로 새 수정 파일을 작성하고 불확실 주장/제약을 실제 원문과 대조한다. 문자열 apply_patch 실패를 반복하지 않는다. 마지막 답변은 한국어 근거 요약과 `{receipt: 저장응답.receipt, export: export_session응답}`이다. 전체 result/assessment는 export 원문에 유지한다. 최신 상세값은 current_request/get_turn에서 복구할 수 있다. JSON 파일은 UTF-8을 우선 사용하며 Windows BOM 있는 UTF-8/UTF-16도 명시적 BOM 범위에서 허용한다. 인코딩 추정은 하지 않는다.

공식 원문 직접 인용은 support_quote와 대조한다. factual_summary는 저장 해석이며 공식 인용문이 아니다. 원문 사실/AI 해석/기획 가설을 구별하고 해석을 제조사 발언으로 저장하지 않는다. 조사 전 요청만 있고 turn이 없으면 record_request_research 후 export_session하고 {request:current_request의 실제 응답,export}로 전달한다.
