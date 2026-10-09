## Context

개발 실행은 Codex·Claude Code가 담당한다. OpenSpec은 공유 요구사항과 작업 기록을 제공하며 별도 LLM API 오케스트레이터를 추가하지 않는다. 출품 하네스의 스택을 이 선택으로 확정하지 않는다.

## Goals / Non-Goals

목표는 고정 버전 설치, 공유 지침, 실제 검사와 실패 결과 기록, 인수인계 가능한 변경 문서다. 출품 업무 평가나 실시간 에이전트 시각화는 이번 변경에 포함하지 않는다.

## Decisions

- OpenSpec 1.14.1을 로컬 devDependency로 고정하고 lockfile을 커밋한다.
- Codex는 `.agents/skills`, Claude는 `.claude/skills`와 `.claude/commands`를 사용한다. 생성 파일을 직접 수정하지 않는다.
- `AGENTS.md`가 공통 규칙의 원본이며 Claude는 이를 import한다.
- OpenSpec CLI wrapper는 전역 설정과 분리된 child-process 환경을 사용한다. 기존 전역 prompt 자동 migration 가능성이 있으면 중단한다.
- 작업 상태는 OpenSpec 문서, 검사 근거는 gitignored `reports/`다. 검사 report를 별도 task ledger로 사용하지 않는다.
- 실제 check는 명세 구조와 개발 하네스 테스트를 실행한다. 실행 오류·실패·미측정을 성공으로 처리하지 않는다.
- 초기에는 같은 checkout의 주 작성자를 하나로 정한다. 필요해진 병렬 작성은 독립 worktree로 확장한다.

## Risks / Trade-offs

- OpenSpec 구조 검사만으로 코드·업무 품질이 보장되지 않는다. 실제 검사를 별도로 실행한다.
- coding CLI가 없는 환경에서는 연결 파일 생성과 해당 도구의 실제 실행 검증을 구분한다.
- OpenSpec의 braces 의존성에 미패치 high advisory가 있다. audit를 통과했다고 보고하지 않고 현재 제한을 문서화한다.
- CI가 정상이어도 CLI 로그인·Skill 로딩·업무 평가까지 검증되는 것은 아니다.

## Migration Plan

신규 저장소에만 구성한다. 기존 LG 프로젝트의 파일, 설정, 데이터는 가져오지 않는다. OpenSpec 생성 파일과 npm 의존성은 버전 변경 시 diff와 검사를 통해 갱신한다.

## Open Questions

- 출품용 하네스가 수행할 업무와 완료 기준.
- 출품용 구현 언어, 실행 방식, 모델, 실제 업무 평가 기준.
- 현재 환경에서 Claude Code 실제 세션 실행 및 두 도구 간 인수인계 검증.
