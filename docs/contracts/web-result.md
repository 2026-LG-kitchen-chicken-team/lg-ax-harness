# 웹 작업 화면·보고서 HTML의 공통 데이터

2026-10-17 기획자 표시 원칙: 현재 결과·선택 원문 전체·refs·binding은 그대로 보존하되 기본 본문은 핵심 문제→기존 기능/남은 문제→기획·요구사항·적용 조건→시작할 작업을 선별한다. 전체 원문·상세 비교·조사 구성은 근거 부록, JSON·지문·검토/조사 사건은 고급 진단으로 분리한다. 기본 보고서 인쇄에서 부록 전체/진단을 자동으로 펼치지 않는다. 이 표시 선택은 연구 자료의 수집·전달·검토 폭을 줄이는 필터가 아니다. 현재 상태·중요 조건·보류 이유를 성공처럼 숨기지 않는다. report.plan의 additive appendix/diagnostics는 같은 current export와 결속하고, 이력/원문을 본문 section으로 강제 전개하지 않는다.

2026-10-14: 사용자에게 보여줄 접근 실패는 `access_failures`와 `diagnostic_links_required:false`를 사용한다. source_url/page_label/status/message를 전달하지만 free-form reason의 내부 파일명·추정 HTTP코드를 사용자 행동 링크로 만들지 않는다. HTTP상태 미관측은null이며 오류가HTTP라고 단정하지 않는다. 원본 investigation_events는 내부 감사/개발 진단용으로 그대로 보존한다. 프론트/HTML은 웹팀이 소유하고 이번 계약 보완은 화면 구현이나 시각 인수를 뜻하지 않는다.

2026-10-13 사용자 선택. 웹팀이 기획자 작업 화면과 '보고서로 보기' HTML을 구현한다. 하네스는 현재 버전의 정형 결과·원문·근거·조사/검토 이력만 전달한다. HTML/웹/모델 호출을 추가하지 않는다.

## 실행과 내용

save_and_export의 기존6필드에 report:false(기본값)를 사용한다. 저장/export가 현재 버전으로 유효하면 web_result와 web_ready를 반환한다. 명시 report:true는 기존 파일 생성/복구 경로이며 기본 필수가 아니다. prepare_web_result 입력은 {session_id,turn_id,expected_result_version}. 같은 현재 버전의 지문이 같은 파일을 재사용한다.

작은receipt의 ready/path/sha256/bytes/binding/source_count/status/workflow_audit_hash/reused를 확인한다. path는 runtime-data/web-deliveries/web-SHA.json이다. 웹팀 코드가 파일SHA와 현재binding을 대조한 뒤 읽는다. 개인 로그·인증·다른 workspace 파일을 함께 업로드하지 않는다.

파일 contract_version:product-web-result-v1에 binding/input/status/result/validation/sources/source_references/coverage/evidence_history/investigation/investigation_events/usage_summary를 보존한다.

- binding은 session/turn/request/result_version·결과/문맥/코드/자료SHA·data_version·조사journal지문이다. 후속/자료변경 시 새현재버전을 확인하고 과거payload는 이력으로 표시한다.
- sources는 선택 정확scope의 모든 등록 원문과 provenance다. 인용source만 추려 폭을 줄이지 않는다. 파일생성은 Agent 독해가 아니다. 원페이지전체·고객수·대표성·의미를 자동인증하지 않는다.
- coverage/history는 등록/전달/신고검토/제외를, 조사events는 계획/관측/종료/분석범위를 구분한다. 고정자료재사용은 새수집이 아니다.
- 로컬finish와 native최종전달/exit·전체backend청구는 별도다. held/needs_input은 기획 해결 성공이 아니다.
- semantic_status:unverified/acceptance_ready:false/ui_ready:false/html_rendered:false/layout_review:not_run이다. 웹연결·HTML렌더링/검수는 이 Tool이 하지 않는다.

원문/모델출력은 신뢰되지 않은 텍스트다. 웹팀은 HTML escape하고 script·명령을 실행하지 않는다. 출처의 정확 모델·문서·관측범위를 유지하며 UI 클릭을 현재버전 계약에 연결한다.

## 실패·마감

web_error에도 저장 후보·수정 이력을 보존한다. 현재 session/turn/version의 prepare_web_result로 복구하며 새turn으로 한도를 초기화하지 않는다. stale code/data/context·과거version·cancelled/failed는 거절하고 변조payload는 덮어쓰지 않는다. 16MiB초과는 명확한 실패이며 자료를 잘라 성공으로 만들지 않는다. 큰자료pagination은 별도 연결 계약이다.

timed workflow의 finish에는 delivered_paths:[web_result.path]와 layout_review:{status:not_run,scope:웹팀화면미연결/미검수}를 기록한다. 현재 저장 버전·조사journal·등록된 실제파일·SHA가 맞아야 마감된다. 임의파일/변조/과거결과/조사변경은 거절한다. finish뒤 export_session으로 종료사건을 보존한다. 파일finish는 native최종전달 인증이 아니며 이후모델오류는 실패로 보존한다.

웹팀 인수·실제 HTML 가독성/접근성/배포는 별도이며 계약/코드검사만으로 완료 처리하지 않는다.
