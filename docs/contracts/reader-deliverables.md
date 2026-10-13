# 사람이 읽는 자료집과 보고서 계약

2026-10-13 최신: 웹팀의 작업 화면·보고서 HTML에 현재 정형결과/원문/근거/검토·조사이력을 전달한다. 기본 save_and_export(report:false)의 web_ready/web_result를 확인하고 prepare_web_result로 같은 버전 복구한다. PDF/DOCX 생성·이미지검수는 기본 필수가 아니며 아래 파일규칙은 명시 report:true 호환 경로다. [웹 데이터 계약](web-result.md)을 우선한다. 신규기본1800초는 성능목표가 아닌 안전상한이고 natural-completion-v1 정책으로 전량전달/신고검토와 최종90초예약을 유지한다. 과거300/600초요청/이력은 변경하지 않는다.

2026-10-12 사용자 정정에 따라 하네스 완료는 실제 제품의 새 자료 조사→분석→검토→저장→독자용 보고서 전달로 확인한다. 수정07 합성 목업의 출력 검수는 실제 업무 완료 증거가 아니다. 페이지 수·목차·파일 개수는 고정하지 않는다. 실제 업무 데이터와 수행한 조사만 구성하고, 사용자가 요청했지만 수행하지 못한 항목에만 사유를 적는다.

## 공통 입출력

`report_plan`은 모델과 무관한 내부 작성 데이터다. 사람이 받는 폴더에는 종류별 XLSX, 설명이 필요한 DOCX, 최종 DOCX/PDF만 둔다. JSON·로그·검수 결과·중복 원문·자료 안내 TXT·HTML은 runtime-data의 내부 경로에 둔다. 자료 원문은 XLSX에 보존하고 클릭 가능한 출처와 원문 셀로 연결한다. source_id는 내부 연결에만 쓰며 독자용 표에는 표시하지 않는다.

`report_plan` 형식: `{title, summary, sources, sections, unfulfilled_requests?}`. summary는 문단 문자열 배열이다. sources는 `{id, kind, title, text, url?, location?, model?, synthetic?}` 배열이고 kind는 자료 종류(예: review/product_document/market/survey/interview/usability/other)다. sources에는 실제 확보한 원문 또는 저장 발췌만 넣는다. sections는 `{title, blocks}` 배열이다. blocks는 다음 중 하나다.

- paragraph: `{type:"paragraph", text, source_ids?, style?}`. style은 `body`(기본) 또는 실제 원문 인용용 `quote`다. summary와 paragraph의 `**핵심 결론·숫자**`, `*보조 강조*`는 본문 서식으로 렌더링한다. 임의 HTML은 실행하지 않는다. 자료집 원문에는 이 서식 해석을 적용하지 않는다.
- table: `{type:"table", title, columns, rows, source_ids?, total_rows?, highlight_cells?}`. columns는 문자열 배열, rows는 같은 길이의 문자열/숫자 행 배열, total_rows는 0부터 시작하는 행 번호, highlight_cells는 `[행,열]` 배열이다.
- chart: `{type:"chart", title, chart_type, labels, series, unit?, source_ids, caption?, highlights?}`. chart_type은 bar/line/pie/donut/scatter이고 series는 `{name, values, x_values?}` 배열이다. highlights는 `[계열,점]` 배열이다. 수치 없는 자료에 그래프를 만들거나 없는 수치를 채우지 않는다. pie/donut은 전체 구성에만 쓴다.
- 컨셉·시연 이미지 생성/삽입 기능은 제외한다. `image` block은 지원하지 않는다. 실제 자료를 집계한 `chart`는 계속 지원한다.

unfulfilled_requests는 `{request, reason}` 배열이며 실제 원문 요청과 수행 불가 사유만 포함한다. 일반 미확인 필드를 자동으로 나열하지 않는다. 자유로운 절·문단·표·도표 조합을 허용한다. 원문을 바꾸지 않고 수치/인원/비율 같은 병렬 정보는 `151명 / 62.9%`처럼 쓴다.

## 작성과 렌더링

- 흰 본문·검정 글자·회색 보조선. 중요한 숫자와 해당 막대/점/부채꼴은 B42318로 강조한다.
- 표별 제목·옅은 회색 머리글·외곽/내부 선·합계 윗선을 통일한다. 합계의 대상·분자·분모가 명확한 같은 표 행을 사용한다. 리뷰 복수 분류의 언급 합계를 독립 고객 비율로 바꾸지 않는다.
- 그래프별 제목/단위, 본체/축/옅은 눈금선, 핵심 결과를 구획으로 나눈다. 차트 종류는 데이터에 맞추고 필요한 범례와 출처를 표시한다.
- 제목·소제목은 굵기와 크기로 구별하고 본문 행간·문단 간격을 통일한다. 강조는 중요한 결론·숫자에 한정한다. 실제 원문 인용은 들여쓰기와 회색 서식으로 구별하고 표현을 고치지 않는다.
- Excel의 바깥 여백·열 폭·행 높이·줄바꿈·정렬·인쇄 범위를 설정한다. Word는 표 머리글 반복과 적절한 행 유지, 도표·출처 연결, 여백을 관리한다.
- 수정07의 목업 원문·수치는 새 결과에 복사하지 않는다. 원문 인용·출처를 보존하며 문단·표·그래프 수치의 일치와 레이아웃을 검수한다.
- 본문 출처는 문서 전체의 첫 인용 순서로 부여한 짧은 `[1], [2]` 번호다. 번호는 해당 DOCX/PDF의 끝 `출처 목록`으로 연결된다. 목록에는 자료명과 중복되지 않는 원문 위치, 모델/문서/관측 정보, 웹 URL 및 정확한 원문 XLSX 파일/시트/셀 링크를 남긴다. 전체 원문과 상세 provenance는 원문 XLSX에 그대로 보존한다. 같은 source_id를 한 번 등재하며 같은 URL의 다른 evidence record를 합치지 않는다. 공개 report_plan 스키마와 source_ids를 유지하고 번호는 렌더러가 결정한다.
- 보고서 출력 profile이 바뀌면 같은 저장 버전으로 새 파일을 생성한다. 이전 보고서와 업무 후보/평가는 보존하며 같은 profile의 정상 파일은 재사용한다. 내부 citation destination과 정확한 원문 셀 연결을 구조 검증하고 실제 페이지도 검수한다.

## 코드 경계

`product_tools.reporting.validate_report_plan(plan)`은 경로/구조/숫자/출처 연결을 검사한다. `render_report(plan, destination)`은 목적 폴더에 결과 파일을 생성하고 `{ready, directory, files, checks}`를 반환한다. files는 `{path, kind, title}` 배열이다. 의존성이 없거나 실제 파일 생성에 실패하면 ready=false/명확한 오류를 반환하고 완성된 PDF가 있는 것처럼 표시하지 않는다. 렌더러 내부 검수 기록은 목적 폴더 밖에 둔다.

`product_tools.delivery.build_report_plan(planning, result, sources, authored_plan=None)`은 원래 업무와 저장 결과의 현재 범위에 맞춰 기본 보고서를 만들거나 모델 작성 계획을 검증해 사용한다. 원문 출처는 검증된 전달 sources와 대조하고 모델이 추가 원문·통계를 꾸며 넣지 않도록 한다. `create_deliverables(workspace, planning, result, sources, authored_plan=None, open_folder=True)`은 결과 폴더를 준비하고 renderer를 호출한다. 폴더 열기는 성공 후 Windows 탐색기에서 수행하며 셸 문자열을 조립하지 않는다. 지원하지 않는 OS에서는 생성된 경로를 반환한다. 새 결과 폴더를 만들고 기존 결과를 덮어쓰지 않는다. 요청/turn/저장 버전 연결 및 완료 상태 확인은 부모 Conversation 통합이 담당한다.

save_and_export의 기존 6필드·JSON 감사 export·receipt·수정 한도·현재 버전/취소 검사를 보존한다. 내부 JSON과 독자용 산출물은 별개다. 보고서 옵션을 받아 저장된 유효한 현재 결과에만 파일 제작을 연결한다. 제작 오류는 저장 성공을 취소하지 않고 별도 보고하며 복구가 가능해야 한다. 재시도·같은 후보 재생에서 이미 생성한 결과를 중복 생산/중복 열기 하지 않는다. authored_plan은 별도 내부 파일로 전달할 수 있어 업무 저장 JSON의 256KiB 계약을 전체 보고서 분량 제한으로 쓰지 않는다.

## 시장·경쟁 맥락 원문 연결

save_and_export와 deliver_result의 선택 `report_sources_path`는 runtime-data 안의 JSON `{research_id,sources}`를 가리킨다. sources 항목은 `{id,snapshot_id,kind,title,quote,location,subject,scope_note}`다. kind는 market/product_document/survey/interview/usability/other이며 대상 제품 리뷰는 정확 모델 catalog에 등록한다. quote는 저장 snapshot의4000자 이하 정확 연속 발췌다. subject는 실제 자료 대상(예: 전국 일반가구, 경쟁 제품 정확 모델), scope_note는 보고서에 적용할 수 있는 범위와 한계다.

현재 turn의 유일한 원래 요청과 research_id가 일치하고 해당 요청의 web_pages journal에 snapshot이 등록되어 있어야 한다. snapshot 지문과 정확 발췌를 검증한 뒤 URL·관찰 시각·관측 방식을 원본에서 가져온다. 호출자가 URL이나 가상 원문을 추가하지 못한다. 이 맥락 자료는 보고서·종류별 자료집만 보강하며 ProductResult의 타깃 모델 evidence_refs/불편/기존 기능/개선안 검증을 대신하지 않는다. 경쟁 제품 기능을 대상 제품의 부재 증거로 쓰지 않는다. source의 대상·적용 범위·관찰 시각·관측 한계를 자료집에 표시한다. 재생에서도 snapshot·발췌를 다시 검증하고 출처/이미지/계획이 바뀌면 기존 파일을 보존하며 새 보고서를 생성한다.

## 환경과 검증

Codex·Claude는 같은 공통 코드와 업무 Skill을 사용한다. 제품 환경에 문서 의존성 설치 안내·잠금·doctor를 반영하고 전역 설정/인증을 수정하지 않는다. Claude 파일 설치/스키마/로컬 코드 검증과 실제 Claude native AI 인수를 구분한다. 현재 승인된 테스트는 Codex에서 서로 다른 접근 가능한 모델로 제한된 같은 입력 비교이며 과거 품질 통과 수와 합산하지 않는다. 컨셉·시연 이미지 생성/삽입은 제품 보고서 기능에 포함하지 않는다.
