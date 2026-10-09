# 짧은 저장 양식

양식 참고이며 업무 정답·실제 실행 기록이 아니다. 일반적인 첫 저장은 open_request_bundle → 원문 판단/assessment → save_reviewed_result → export_session이다. 같은 상태를 선행 validate/review/get_turn으로 반복 확인할 필요 없다. 저장 자체가 구조·검토 기록을 검사한다. state_conflict/재개/외부 변경이면 current_request/get_turn을 읽는다.

open_request_bundle 입력: `{question:"실제 요청",model_id:"선택 모델",user_submitted:true}`. 후속에는 같은 session_id/prior_turn_id와 실제 추가 질문을 준다. constraints 기본값은 `{max_concepts:3,hardware_allowed:false,exclude_pains:[]}`. 전체 constraints를 지정할 때3필드를 모두 넣는다. bundle.scope는 조회 입력의 `scope`이며 PlanningInput의 배열 `model_scope`와 다르다. records는 종류 metadata, evidence_refs에 원문·URL·SHA가 한 번 들어 있다. omitted_source_ids/truncated이면 필요한 것만 좁혀 조회한다. 긍정/상충 의견을 누락하지 않는다.

save_reviewed_result 입력은6필드다:

```json
{"session_id":"도구의 값","turn_id":"도구의 값","result_key":"candidate-0","expected_result_version":0,"result":{"status":"held","pains":[],"existing_features":[],"remaining_pains":[],"concepts":[],"assumptions":[],"evidence_refs":[],"validation_findings":["실제 부족 근거와 이유"],"revisions":0,"usage_summary":{"status":"unknown"}},"assessment":{"claim_checks":[],"feature_matches":[],"concept_links":[]}}
```

이 빈 held는 부족 이유를 판단했을 때만 쓴다. completed에는 근거 있는 불편·기존 기능·남은 불편·콘셉트와 검토 연결이 필요하다. result<=32KiB, stdin/파일<=64KiB. refs는 사용한 source만 복사하며 인용만 늘리고 claim에서 사용하지 않으면 unused_evidence로 실패한다.

- pains/existing_features/remaining_pains: `{id,text,source_ids:["원문ID"]}`. id는 전체 result 안에서 유일하다.
- concepts: 위3필드 + `{requirements:["검증 가능한 조건"],requires_hardware:false,assumptions:["미확인 조건"]}`. 최대3개이며 근거 없는 수량 채우기는 금지다.
- claim_checks: 모든 claim마다 `{claim_id,source_ids,support_status:"supported|unsupported|uncertain 중 한 값",scope_relation:"current_model|previous_product|unclear 중 한 값",rationale:"원문 대조 이유"}`. source_ids 순서도 claim과 같아야 한다.
- feature_matches: 남은 불편마다 `{remaining_pain_id,pain_id,feature_source_ids:["인용한 제품 사실ID"],resolution:"resolved|partially_resolved|unresolved|uncertain 중 한 값",rationale}`.
- concept_links: concept마다 `{concept_id,remaining_pain_ids:["남은 불편ID"],duplicates_existing:false,geometry_required:false,geometry_known:false,geometry_source_ids:[],rationale}`. 치수 필요 시 실제 내부 치수 근거를 대조한다. 외형 치수는 대신 쓸 수 없다.

expected_result_version은 응답 turn.result_version(첫0, 다음1, 다음2)이다. result.revisions는 최초0/수정1/2다. 같은 후보 재전송은 같은 result_key와 원문/assessment를 유지한다. accepted=false도 저장되고 한도를 소비한다. 응답 turn이 다음 저장과 최종 상태의 기준이며 accepted/status/valid를 반드시 확인한다. 실패/취소/수정 소진을 새 turn으로 우회하지 않는다. export_session 입력은 `{session_id:"값"}`이고 큰 export를 다시 읽지 않는다.
