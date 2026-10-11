# 출품 상품기획 Agent·Skill 계약

2026-10-11: 냉장고·전자레인지·식기세척기 지원과 Gemini 철회/Claude 후순위는 [최신 결정](../decisions/kitchen-scope-20261011.md)을 따른다. 새 concept에는 implementation_steps·validation_plan(metric/baseline/method/success_criterion/business_value/status=planned_not_measured)을 포함한다. 실제 효과를 자체 인증하지 않는다. 기존 assessment·최대2수정·조건부 초안/치수 보류 규칙은 유지한다.

2026-10-10. 업무 생성과 해석은 네이티브 모델, 조회·출처·버전·저장 검사는 Python 일반 코드다. [Agent 지침](../../agents/product-planning.md), [Skill 목록](../../skills/manifest.json), [공통 Tool](common-tools.md)을 연결한다. 개발 체계의6역할·9Skill과 별도다. Agent1개·업무Skill5개·조건부 외부조사Skill1개를 채택했다. Skill6개는 서브에이전트6개를 뜻하지 않는다.

## 구현과 지원 상태

출품 지침 원본과 Skill 본문·실행 wrapper·검토 Tool을 작성했다. wrapper는 원본/설치 경로를 모두 찾는 일반 코드다. Codex 설치·대화 Tool은 [계약](codex-product.md), 실제 발견·업무 실행은 [검증 기록](../validation/codex-product.md)을 따른다. Claude/Gemini 인수는 S02에서 별도로 진행한다. 지침이나 정적 검사가 완료되었다고 실제 모델의 불편 해석·기획 품질을 통과시킨 것은 아니다.

## assessment

`review_product_result` 입력은 `{input: PlanningInput, result: ProductResult, assessment: ...}`다. ProductResult 원본은 변경하지 않는다. assessment는 모델이 원문을 대조해서 작성하는 아래3개 배열이다.

선택 decision_notes의 refs·한 모델 snapshot·상한은 공통 계약이 검사한다. note의 basis는 모델 신고이며 claim_checks를 대신하지 않는다. 원문 직접 인용/요약/AI 해석과 보류 사유의 의미는 별도 답변 검토로 확인한다. note를 추가해 completed의 concept/불편 연결 규칙을 우회할 수 없다.

- `claim_checks`: 모든 pains/existing_features/remaining_pains/concepts의 claim마다 `{claim_id, source_ids, support_status, scope_relation, rationale}`. source_ids는 claim과 동일 순서. support_status는 supported/unsupported/uncertain, scope_relation은 current_model/previous_product/unclear.
- `feature_matches`: remaining_pain마다 `{remaining_pain_id, pain_id, feature_source_ids, resolution, rationale}`. 원래 관측 불편과 인용된 제품 사실을 연결한다. resolution은 resolved/partially_resolved/unresolved/uncertain. resolved 또는 uncertain인 문제는 completed 제안의 남은 불편으로 확정하지 않는다.
- `concept_links`: concept마다 `{concept_id, remaining_pain_ids, duplicates_existing, geometry_required, geometry_known, geometry_source_ids, rationale}`. duplicates_existing은 boolean/null. 치수가 필요한 안은 geometry_known=true와 해당 사실 출처가 필요하다. 치수 종류·원문 의미·추정 오류는 실제 원문 검토가 담당한다.

원문 의미의 판단은 코드에 하드코딩하지 않는다. 코드가 판정하는 것은 필드·ID·원문 인용·검토 누락·보고된 불확실성·출처 종류·연결 정합성이다. `can_finalize_reported_result`는 그 보고에 따른 상태이며 `semantic_status=unverified`, `acceptance_ready=false`를 유지한다. 부정확한 해석을 supported라고 적는 오류는 별도 AI 평가·독립 원문 검토에서 찾아야 한다.

v5.3은 기획 초안 완료와 모델 귀속/실물/효과 검증 완료를 구분한다. claim_checks에 선택 qualification={basis,limitations,original_statement_supported}를 추가했다. basis=page_linked_example은 실제 page association 리뷰를 인용하는 pain만, conditional_draft는 assumptions를 가진 remaining_pain/concept만 허용한다. page_linked_example에는 원문 관측의 자기보고 true가 필요하다. conditional_draft는 원문에서 직접 관측되지 않은 제안에 false를 유지할 수 있으며 실제 전제 근거·한계 배열·assumptions·unsupported와 previous_product 배제가 필요하다. false를 true로 바꿔 통과시키지 않는다. 2026-10-11 독립 평가에서 두 의미가 섞여 정직한 baseline 제안이 거절되는 결함을 확인해 계약을 수정했으며, 당시 실패 기록은 보존한다. 모델 귀속 unclear/uncertain을 지우지 않고 제한적인 초안을 저장할 수 있다. conditional_draft인 remaining_pain의 해소 uncertain과 concept의 중복 null도 가설로만 허용하며 resolved/중복true/치수 의존성 부족은 차단한다. 결과의 completion_scope=planning_draft_only이며 원문·귀속·한계의 실제 의미는 독립 검토한다. qualification 생략은 기존 동작이다.

`save_and_export` 입력은 {session_id,turn_id,result_key,result,expected_result_version,assessment}. 실제 저장 검사를 receipt 방식으로 실행하고 거절 후보도 이력/export에 보존한다. {save,delivery_ready,export,export_error}를 반환하며 최신 accepted/valid 후보와 export 성공 때만 delivery_ready다. export 실패는 저장을 취소하지 않고 별도 export_session으로 복구한다. 과거 accepted key 재생·외부 상태 변경은 완료로 전달하지 않는다. 이 결합은 모델 호출이 없는 일반 코드이며 독립 기존 API도 유지한다.

## 실제 업무 순서와 재개

정확한 모델 자료 조회→필요 시 외부 조사·새 dataset 확정→내부 입력·start_turn→불편 구조화→기존 기능 대조→근거 있는 후보→원문 검토·코드 검사→후보 저장이다. open_request가 첫 입력의 내부 식별자를 만들고 current_request가 재개 시 보존한다.

이미 시작한 turn은 data_version을 내부적으로 변경해 새 키로 초기화하지 않는다. 공통 상태 코드는 stale_context로 오래된 결과 저장을 거부한다. 후보 생성 뒤 추가 자료가 필요하면 같은 버전에서 사유를 저장하고 실제 새 사용자 입력으로 다음 turn을 연결한다. 초기 조사 단계에 원문 지문·자료 버전이 확정되지 않으면 생성 결과를 재사용하지 않는다.

최초 생성0·수정1·2와 Tool 기술 재시도는 별도다. 실제 업무는 save_reviewed_result로 실패 후보와 assessment를 저장해 시도 횟수를 유지한다. save_result는 하위 구조 검사 호환 경로다. semantic 검토에서 보류가 필요한 후보는 상태와 validation_findings를 반영해 저장한다. 이 전이 지침의 네이티브 준수는 실제 통합 평가에서 검증한다.

사용자가 진행 중인 업무를 취소하면 cancel_turn으로 후보 없이 상태를 종료한다. 기존 후보·수정·사용량을 보존하고 현재 결과 재사용과 추가 저장/등록 호출을 막는다. 실제 실행기·원격 모델의 중단 관측은 별도이며 로컬 취소 receipt에서 추정하지 않는다. 명시적 새 사용자 입력만 새 turn을 만들 수 있다.

결과에는 원문 링크와 위치, 현재 제품의 실제 불편·상충 의견, 기존 기능과 남은 문제, 조건을 지킨 제안, 미확인 항목을 표시한다. 실제 구매/협찬·고객 수·시장성·내부 치수·개선 효과를 추정하지 않는다.
