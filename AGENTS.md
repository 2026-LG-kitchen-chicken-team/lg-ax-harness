# 공통 개발 지침

2026-10-12 교수 피드백·새 방향: 사용자 전달 피드백은 docs/decisions/professor-feedback-20261012.md를 따른다. HTML 중심의 읽기 좋은 보고서·공통 코드 렌더링·병목 계측 후 시간 단축·출품 검증 모델/추론 수준 고정이 향후 목표다. 현재 v0.9.1의 DOCX/PDF 기본 전달을 HTML 구현 완료로 바꾸지 않는다. 1차 오프라인 코드 측정은 docs/validation/professor-feedback-latency-20261012.md이며 실제 전체 업무의 단계별 병목/개선률은 미측정이다. 제품/웹 팀 소유 범위는 유지한다.

2026-10-12 기록 추가: docs/validation/team-runs/records/20261012-team-mail-progress-review.md에 대겸·길웅의 LG 메일 본문·진행 보고·원격 확인 상태를 구분해 보존했다. docs/references/harness-competition-strategy-20261012.md의 우승 전략은 사용자 제공 미검증 인용 자료이며 공식 요구·채택 지시가 아니다. 무제한 성공 반복·서브에이전트 4~5개 필수/가산점·미측정 효과 주장으로 기존 계약을 변경하지 않는다.

2026-10-12 최신 담당 결정: 황대겸은 제품 v0.7.0 이후 개선, 최길웅은 웹과 Codex·Claude 연동, 정이량은 발표자료·시연영상 담당이다. docs/decisions/team-ownership-20261012.md와 docs/plans/presentation-video-handoff-20261012.md를 따른다. 이 채팅은 발표·영상 제작 지원/근거 정리를 우선하며 팀원 제품/웹 코드를 중복 수정하지 않는다. 원격 v0.8.0/v0.9.0 게시를 확인했으나 이번 담당 기록 작업에서 새 native/보고서 회귀를 수행한 것은 아니다. 촬영 버전·실제 웹 연결·같은 실행 로그/산출물·수치를 인수한 뒤 최종 자료에 반영한다. 과거 v7.4 성공 수치를 새 버전으로 재사용하지 않는다. 기존 웹 PM 황대겸과 최길웅의 구현 담당은 구분한다.

2026-10-12 실제 제품 완료 기준 정정·인수: 합성 목업 출력은 실제 상품기획 하네스 완료 근거가 아니다. B502S33·MWJ25E의 새 실제 자료 조사→분석·기획→검토→저장→자료집/보고서 전달은 docs/validation/real-products-20261012.md/JSON을 우선한다. 실제 Codex 업무 2건과 최종 소스의 보존 입력 재생 2건을 구분한다. 제품별 XLSX4·DOCX·PDF와 Windows 실제109쪽/30시트 검수를 확인했으며 기획은 실물/효과 검증 전 조건부안이다. 의미 자동 인증·실물 구현·효과 측정·Claude 새 AI 인수·영상/최종 접수 완료로 확대하지 않는다. 아래 문단은 당시 이력이다.

2026-10-12 최신 작업 마감: product-planning-v7.4의 원문/요약/AI 판단·보류 decision_notes·후기 맥락/집계·관측 시간·실제 취소 지침을 보완하고 동일45파일 원본으로 제한 회귀/독립 검토를 종료했다. Codex 실제10건8통과/2실패, Claude3건2통과/1실패, R06미실행1건이다. docs/validation/quality-regression-20261012.md/JSON과 token-bonus-20261012.md/JSON을 우선한다. 최종 pointer 전달·420초 timeout·Claude 문맥/지표/귀속 한계를 전부 해결한 것으로 바꾸지 않는다. 보류 판정 통과는 업무 해결 완료가 아니다. 일반 코드 취소 쓰기 차단/timeout 기록 복구는 native/backend 중단 인증이 아니다. 사람 비교·Gemini 제외, 웹/관찰 화면·영상/발표/리허설·최종 접수는 별도다. 아래 버전별 문단은 당시 이력이다.

2026-10-11 최신 v7.2 인수는 `docs/validation/claude-codex-v72-20261011.md`/JSON을 우선한다. Codex·Claude Desktop 각각4입력/3대화가 실제 저장·전달에 일치했다(초안2/기획 보류5/turn 없는 조사 보류1). 전부 업무 해결·의미 품질 통과로 바꾸지 않는다. Claude A03 공식문구 귀속, 네 입력 자체시간 오류, A02 후기 맥락/효과지표, A04 접근 복구 안내의 미확인을 보존한다. baseline Claude의 전체 원질문 누락 실패와 이전 timeout은 그대로다. 제품180·평가128·자산 검사 exit0, 실제 native8은 최종 키 접미사 수정 전 동결본이다. 최종 키 수정/설치 설명을 native 재인수한 것으로 확대하지 않는다. Desktop 성공은 독립 CLI 인증이나 개발용 Claude 위임 인수와 별개다. 이하 버전별 현재/대기 설명은 당시 이력이다.

2026-10-11 최신 사용자 결정: 사람 대비 절감효과 측정은 제외한다. 추가 사람 측정·회신 재촉·완료 대기를 하지 않는다. AI 자체 실행시간·토큰·오류·근거·품질 검증은 유지하며 사람 절감률은 주장하지 않는다. docs/decisions/effect-scope-20261011.md가 과거 사람 비교 계획에 우선한다.

## 최신 변경 — 2026-10-11

최길웅의 Claude v0.3.0 네 입력 회신·export4개·실행 요약을 접수했다. `docs/validation/team-runs/records/20261011-claude-mail-review.md`의 지문·저장 내부·출처 제한 검토와 최초 중복 판단/공식 문구 귀속 오류를 따른다. 아래 회신 대기는 접수 전 이력이다. 최신 v6.1 Claude 제품군10입력·전체 native 전달/품질/요청별 usage·별도 개발용 Claude 위임은 미완료다. 보고상 recorded_calls0/unknown을 실제 호출0으로 바꾸거나 구버전 네 입력을 최신 회귀와 합산하지 않는다.

일반 제품명 입력은 product-planning-v6.1에 구현했다. `docs/validation/family10-20261011.md`의 실제10입력/8대화는 초안4/보류3/확인3이며 정의한 판정10개를 통과했다. 이전 v6.0의50입력/40대화는 `docs/validation/regression50-20261011.md`를 따른다. 최신 버전60개 통과로 합산하지 않는다. 제품147·평가117개 코드 검사는 실제 exit0다. 등록5모델 범위·모델별 근거 귀속·보유 모델 미확인 적합/안전 확인을 유지한다. baseline/미사용 평가/효과/Claude native/최종 제출의 완료로 바꾸지 않는다.

세 제품군 내부 구현/4입력 인수/독립 검토·제품 v0.3.0 배포와12쪽 발표 초안을 완료했다. 현재 근거는 `docs/validation/kitchen-progress-20261011.md`, 배포·다음 작업은 `docs/validation/product-v0.3.0.md`다. 최길웅 Claude 환경 검증 요청은 사용자 초안 승인 후 발송했고 결과 회신을 기다린다. 영상/리허설/사람 효과/Claude native/최종 접수는 미완료다.

팀 메일에서 신진하의 수신 기본값은 기존 Gmail 발신 헤더로 확인한 Gmail이다. 과거 네이버 주소를 새 메일/전체 회신에 재사용하지 않는다. 실제 수신 주소와 메일 ID는 Git 제외 `.harness/team-contacts.json`·메일 기록을 확인한다. 이미 보낸 메일의 이력은 보존하고 자동 재발송하지 않는다.

출품 업무는 냉장고·전자레인지·식기세척기의 실제 사용 불편 기반 상품기획으로 확대한다. 제안서 예시는 범위 제한이 아니다. 기본 자료는 lg-kitchen-v4(5모델·8후기·26사실)다. Codex가 제출 기준이며 Gemini 활성 지원/설치/패키징은 철회했다. Claude native 인수는 이번 보완 완료 뒤 최길웅에게 메일 요청·정이량에게 결과 회신하는 후순위다. 웹팀은 현재 개발 중이라는 사용자 보고이며 원본 미수신/미검토를 미착수로 바꾸지 않는다. 웹 PM 황대겸의 소유 범위를 유지한다. docs/decisions/kitchen-scope-20261011.md가 아래 과거 상태의 지원 목표를 갱신한다. 평가/시연/효과/접수 완료는 실제 증거로 판단한다.

이 레포는 새로운 LG AX 출품 프로젝트와 이를 만드는 Codex·Claude Code 개발 체계를 담는다. 개발 체계와 출품 Agent·Skill·runtime을 구분한다.

## 현재 상태와 원본

- 최신 사용자 승인(2026-10-11): 요청 기반 조사·신규 모델 등록으로 확장했다. 기본 출품 catalog는 data/business/empty이며 특정 등록 사례를 자동 선택하지 않는다. open_request로 원문 보존 → 실제 조사/등록 → 같은 request의 resolve_request_bundle을 사용한다. 과거 v4 자료/평가 결과는 재현용이다. 최신 구현·검증·외부 의존성 상태는 docs/validation/request-driven-20261011.md를 우선한다. Claude 중복 미확인 null·공식 원문/해석 분리 지침을 적용한다. 아래 과거 단계 설명은 해당 버전의 이력이다.

- 2026-10-10에 OpenSpec을 교체하고 Codex 중심 개발 역할·Skill·검사 실행기를 구축했다. 실제 인수검사 상태는 `docs/validation/development-harness.md`를 따른다. Codex 업무 설치·실제 연결은 docs/validation/codex-product.md를 따르며 Claude/Gemini·심사 품질/효과·최종 제출은 미완료다.
- 요구 원본은 `docs/competition-requirements.md`, 기술 결정은 `docs/decisions/stack-selection.md`, 개발 체계 작업 상태 원본은 `docs/plans/development-harness.md`다.
- 출품 실행·시연 계약은 `docs/plans/product-harness.md`, AI 직접 입력 평가는 `docs/evaluation/judge-input-cases.md`다.
- 출품 실행은 공통 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 각각 연결하는 방식으로 사용자가 선택했다. `docs/decisions/product-runtime.md`를 따른다. 초기 경로에 자체 모델 API 실행기나 Codex 내부 호출 실행기를 추가하지 않는다. 세 환경의 지원 목표와 실제 검증 상태를 구분한다.
- 사용자가 제공한 연구원 컨설팅은 `docs/consultation/2026-10-10.md`를 따른다. 업무·시연 자료는 실제 제품·리뷰이며 합성 자료는 계약·오류 시험 전용이다. 사용자에게 상세 불편 입력을 강제하지 않고 모델 선택에서 AI가 실제 근거로 불편을 찾아야 한다. 정확한 해당 모델 사양·외형/내부 치수 구분과 시간·공수 효과 검증을 유지한다.
- 공통 자료·입출력·상태 코드는 `product-tools/`, 계약은 `docs/contracts/common-tools.md`다. Codex 설치/자동발견·정상/후속/보류/오류 저장을 확인했다. 현재 실제 자료 충분성·청소/내부 치수·AI 품질/효과 평가와 Claude/Gemini native 연결은 미완료다.
- 시각화는 `docs/plans/observability-viewer.md`의 별도 프로그램에서 제공하며 후순위다.
- Codex 개발 체계 D01-D05와 업무 설치 S02a를 검증했다. 다음 우선순위는 실제 AI 심사 입력·baseline·품질/효과 평가 S05 및 자료 부족 보강이며 팀원 Claude 인수 D06b와 출품 Claude/Gemini는 별도다. 시각화 도구·수집·화면 작업은 후순위이며 개발 체계 인수검사의 선행 조건이 아니다. 기존 실행기에 연결하는 React Flow UI도 후속 후보일 뿐 현재 채택·구현하지 않는다.
- OpenSpec 파일·Skill·명령·초기 검사 도구는 제거했다. 새로운 작업을 OpenSpec 절차로 시작하지 않는다.
- 계획·정적 검사·라이브러리 호환성 검사를 네이티브 개발 Agent 동작이나 출품 AI 품질 통과로 설명하지 않는다.

## 범위

- 기존 LG 작업물의 코드·설계·프롬프트·Skill·MCP·자료팩·가공 데이터·평가·UI를 가져오거나 재사용하지 않는다. 공식 요구와 공개 OSS는 출처·버전을 밝혀 참고한다.
- 확인된 공식 요구, 팀 아이디어, 사용자 선택, 새 설계, 미확인 사항을 구분한다.
- 심사 질문은 출품용 AI에 직접 넣는 업무 요청·추가 질문·예외 입력이다. 발표자 질의응답과 섞지 않는다.
- 사용자 예산은 현재 300,000원이다. 채택 기록의 예산 배분은 계획이며 실제 사용량·청구·모델 접근 가능성을 가정하지 않는다.

## 개발·위임

- 시작·인수인계 시 요구·결정·작업 목록, git status/diff, 실제 검사 결과를 읽는다.
- 메인 부모가 작업 목적·의존성·입력 지문·Skill·소유 파일·완료 검사·실행 상한을 배정하고 결과를 통합한다.
- 한 checkout의 파일·Git 쓰기는 한 작성자가 담당한다. 병렬 작성이 필요하면 독립 worktree를 사용하고 공통 계약·병합은 부모가 관리한다.
- 읽기 전용 역할은 배정된 작성 작업으로 전환하기 전 코드를 변경하지 않는다. 소유 범위 필드를 실제 파일 권한으로 설명하지 않는다.
- 실제 네이티브 도구가 반환한 ID·상태·중단 결과만 기록한다. 장부 스크립트가 Agent 실행·메시지 전달을 대신한다고 가정하지 않는다.
- 모든 전문가를 항상 호출하지 않는다. 역할·모델 설정은 작업 필요와 실제 환경 한도에 맞춘다.
- Claude는 자신의 Agent·Skill·위임 도구를 사용한다. Codex와 Claude를 한 자동 실행 팀으로 엮지 않는다.

## 구현·검증

- 검사는 실제 명령 실행·exit code·결과를 남긴다. 실패·timeout·미실행을 성공으로 바꾸지 않는다.
- 출품의 업무 수정 최대 2회와 모델·Tool의 기술 재시도·Agent turn 제한을 구분한다.
- 필요한 원문과 모델·문서 버전 필터를 유지한다. source_id 형식 검사만으로 근거의 의미를 통과시키지 않는다.
- 개발 사용량과 출품 사용량을 분리한다. 미측정 토큰은 미측정으로 기록하고 전체 모델 호출을 비용에 포함한다.
- 개발·시연의 별도 관찰 프로그램은 실제 Agent·Skill·Tool 이벤트를 표시한다. Skill을 Agent로 늘려 표시하지 않고 구조 정의·실행·저장 기록 재생을 구분한다. 관찰 수집·표시는 일반 코드로 처리하고 시각화용 모델 호출·프롬프트·로그 문맥을 추가하지 않는다.
- API key·개인 설정·원문 실행 로그·SQLite·의존성 환경은 Git에 넣지 않는다. 재현에 필요한 새 합성 원본·코드·계약·잠금 파일은 관리한다.
- 변경 완료 보고에는 바뀐 내용, 실제 검사, 결과와 제한을 적는다. 현재 개발 체계 검사는 `docs/validation/development-harness.md`, 이전 라이브러리 호환성 범위는 `docs/validation/library-compatibility.md`에서 확인한다.

## 파일·도구 관리

- OSS는 고정 원본·LICENSE/NOTICE·파일 목록·수정 내역을 관리한다. Windows symlink 지원이나 upstream 설치 성공을 가정하지 않는다.
- 개발 Skill 원본은 `.agents/skills/`, Claude 사본은 `.claude/skills/`에서 관리한다. `python dev-harness/cli.py sync-claude --check`로 차이를 검사한다. 출품 Skill은 `skills/`다.
- 프로젝트 설정만 변경하며 사용자 전역 Skill·설정·다른 레포를 변경하지 않는다.
- 재귀 삭제·이동 전 최종 절대 경로가 의도한 레포 안에 있는지 검증한다.

현재 사용 상태는 `README.md`, 다음 구축 작업은 `docs/plans/development-harness.md`를 읽는다.

<!-- codex-harness:start -->
## Codex 개발 실행

실질 개발은 `.agents/skills/harness/SKILL.md`를 적용한다. 메인이 목적·의존성·입력 지문·역할·필요 Skill·소유 파일·실제 완료 명령·시간/호출 상한을 배정한다. 현재 runtime이 custom role 선택을 제공하지 않으면 역할 TOML의 developer_instructions와 최신 packet을 네이티브 생성/위임 메시지에 넣는다. 이 경로는 TOML sandbox·모델 설정 자동 적용을 증명하지 않는다. 읽기 전용 역할은 코드를 수정하지 않는다.

장부는 `python dev-harness/cli.py ledger`, 실제 검사는 `check`, receipt 포함 최종 검증은 `complete --run RUN`으로 수행한다. 장부가 Agent나 메시지를 실행하는 것은 아니다. 실제 반환 ID·native 결과·관찰 상태만 기록한다. `interrupt_agent`는 turn 중단이며 close가 아니다. close 도구가 없으면 idle 세션을 재사용한다. 상세 실행 계약은 `.agents/skills/harness/references/project-workflow.md`를 읽는다.
<!-- codex-harness:end -->

<!-- codex-harness:domain:start -->
## LG AX 개발 목적

공식 요구와 신규 팀 아이디어를 토대로 출품 Agent·Skill을 개발·평가·제출한다. 개발 역할 6개와 Skill 9개는 출품 Agent 수나 업무 Skill 수를 뜻하지 않는다. 심사 입력은 출품 AI에 직접 넣으며 토큰/품질 감사는 evaluator + evaluate-harness, MCP/Tool 호출 계약은 harness-architect + harness-design이 담당한다. 출품 네이티브 실행 방식 선택과 업무 구현·모델별 검증은 구분하며 현재 개발 완료 조건에 UI를 추가하지 않는다.
<!-- codex-harness:domain:end -->
