# 출품 상품기획 Agent·Skill 계약

2026-10-10. 업무 생성과 해석은 네이티브 모델, 조회·출처·버전·저장 검사는 Python 일반 코드다. [Agent 지침](../../agents/product-planning.md), [Skill 목록](../../skills/manifest.json), [공통 Tool](common-tools.md)을 연결한다. 개발 체계의6역할·9Skill과 별도다. Agent1개·업무Skill5개·조건부 외부조사Skill1개를 채택했다. Skill6개는 서브에이전트6개를 뜻하지 않는다.

## 구현과 지원 상태

출품 지침 원본과 Skill 본문·실행 wrapper·검토 Tool을 작성했다. wrapper는 원본 레포 기준 일반 코드다. Codex/Claude/Gemini 프로젝트 설치·발견·자동 선택·실제 업무 대화 인수는 S02에서 진행한다. 지침이나 정적 검사가 완료되었다고 실제 모델의 불편 해석·기획 품질을 통과시킨 것은 아니다.

## assessment

`review_product_result` 입력은 `{input: PlanningInput, result: ProductResult, assessment: ...}`다. ProductResult 원본은 변경하지 않는다. assessment는 모델이 원문을 대조해서 작성하는 아래3개 배열이다.

- `claim_checks`: 모든 pains/existing_features/remaining_pains/concepts의 claim마다 `{claim_id, source_ids, support_status, scope_relation, rationale}`. source_ids는 claim과 동일 순서. support_status는 supported/unsupported/uncertain, scope_relation은 current_model/previous_product/unclear.
- `feature_matches`: remaining_pain마다 `{remaining_pain_id, pain_id, feature_source_ids, resolution, rationale}`. 원래 관측 불편과 인용된 제품 사실을 연결한다. resolution은 resolved/partially_resolved/unresolved/uncertain. resolved 또는 uncertain인 문제는 completed 제안의 남은 불편으로 확정하지 않는다.
- `concept_links`: concept마다 `{concept_id, remaining_pain_ids, duplicates_existing, geometry_required, geometry_known, geometry_source_ids, rationale}`. duplicates_existing은 boolean/null. 치수가 필요한 안은 geometry_known=true와 해당 사실 출처가 필요하다. 치수 종류·원문 의미·추정 오류는 실제 원문 검토가 담당한다.

원문 의미의 판단은 코드에 하드코딩하지 않는다. 코드가 판정하는 것은 필드·ID·원문 인용·검토 누락·보고된 불확실성·출처 종류·연결 정합성이다. `can_finalize_reported_result`는 그 보고에 따른 상태이며 `semantic_status=unverified`, `acceptance_ready=false`를 유지한다. 부정확한 해석을 supported라고 적는 오류는 별도 AI 평가·독립 원문 검토에서 찾아야 한다.

## 실제 업무 순서와 재개

정확한 모델 자료 조회→필요 시 외부 조사·새 dataset 확정→내부 입력·start_turn→불편 구조화→기존 기능 대조→근거 있는 후보→원문 검토·코드 검사→후보 저장이다. 첫 입력의 내부 식별자는 메인/향후 adapter가 생성하고 재개 시 보존한다.

이미 시작한 turn은 data_version을 내부적으로 변경해 새 키로 초기화하지 않는다. 공통 상태 코드는 stale_context로 오래된 결과 저장을 거부한다. 후보 생성 뒤 추가 자료가 필요하면 같은 버전에서 사유를 저장하고 실제 새 사용자 입력으로 다음 turn을 연결한다. 초기 조사 단계에 원문 지문·자료 버전이 확정되지 않으면 생성 결과를 재사용하지 않는다.

최초 생성0·수정1·2와 Tool 기술 재시도는 별도다. 실패 후보도 save_result로 저장해 시도 횟수를 유지한다. semantic 검토에서 보류가 필요한 후보는 상태와 validation_findings를 반영해 저장한다. 이 전이 지침의 네이티브 준수는 실제 통합 평가에서 검증한다.

결과에는 원문 링크와 위치, 현재 제품의 실제 불편·상충 의견, 기존 기능과 남은 문제, 조건을 지킨 제안, 미확인 항목을 표시한다. 실제 구매/협찬·고객 수·시장성·내부 치수·개선 효과를 추정하지 않는다.
