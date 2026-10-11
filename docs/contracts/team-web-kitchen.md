# 웹팀과 세 제품군 결과 연결

2026-10-11. 웹 PM 황대겸의 기술·화면·일정 결정을 유지한다. 사용자 보고로 웹팀 개발 진행은 확인됐으나 레포에서 실제 원본은 받지 못했다. 이 문서는 메인 하네스의 공유 계약이며 웹 화면 구현 완료 보고가 아니다.

기존 `export_session` JSON을 파일로 읽는 경우 `turns[].state.input`의 product_family/model_scope/data_version/constraints, `turns[].candidates[].result`와 validation, invocations/usage를 표시한다. 웹 자체 실행 서버나 모델 API 호출을 이번 변경으로 추가하지 않는다.

| 원본 | 표시·주의 |
|---|---|
| product_family | refrigerator=냉장고, microwave=전자레인지, dishwasher=식기세척기. 정확 모델과 일치, 모르는 값은 미지원 |
| model_scope | 모델·제조 버전·문서 버전. unspecified를 임의 제조 버전으로 바꾸지 않음 |
| pains/existing_features/remaining_pains/concepts | 원문ID로 연결한 불편→기존 기능→남은 문제→기획. Skill6개를 Agent6개로 그리지 않음 |
| concept.implementation_steps | 선택 배열. 새 결과는 구현 단계 포함. 없는 구버전은 ‘미작성’ |
| concept.validation_plan | metric/baseline/method/success_criterion/business_value/status. planned_not_measured=검증 계획·실측 전 |
| evidence_refs | source_id·quote·URL·location·게시/관측일·SHA·scope·구매/협찬 미확인. 링크는 HTTPS 검증, 원문 HTML 실행 금지 |
| state.valid/status/result_version, receipt | 현재 유효·기획 초안 완료/held/needs_input/failed/cancelled·후보 버전. 과거 후보는 ‘역사적 기록’ |
| validation | 구조/보고된 검토 정합성과 의미 정확성 구분. planning_detail_complete는 필드 존재 검사, 평가 통과 인증 아님 |
| usage_summary/usage | native 관측 범위·unknown/null 유지. 누적 snapshot 중복 합산 금지. 개발·출품 사용량 분리 |

모델을 바꾸는 후속에는 다른 제품의 사실을 전이하지 않는다. DUBJ2EA는 단종 사례이며 MWJ25E 공식 내부 치수를 용기 회전/가열 안전성으로 확대하지 않는다. 두 신규 리뷰는 동일 개인 작성자이며 고객2명으로 세지 않는다.

PM/팀 PR 연결 인수 기준: 세 family 명칭/출처/단종·미확인·미측정 표시, 정상/보류/오류/현재 무효/과거 후보 구분, 원문 scope와 링크/quote 대조, 새로고침·기록 재생·다운로드 모델 호출0. 기존 private 원문 로그/DB/export를 public 자산이나 Git에 넣지 않는다. 예제는 합성 시험용 표시를 유지하거나 공개 허용 자료만 비식별 검토해 사용한다. 원본 코드 도착 후 실제 화면과 export 일치를 검사한다.
