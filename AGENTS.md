# 공통 개발 지침

이 레포는 새로운 LG AX 출품 프로젝트와 이를 만드는 Codex·Claude Code 개발 체계를 담는다. 개발 체계와 출품 Agent·Skill·runtime을 구분한다.

## 현재 상태와 원본

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
