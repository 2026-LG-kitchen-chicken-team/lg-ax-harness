@AGENTS.md

이 레포에는 Codex 중심 개발 체계와 팀원의 Claude Code 어댑터가 있다. OpenSpec Skill·명령은 제거했으며 새 작업에 사용하지 않는다.

Claude용 6개 역할은 `.claude/agents/`, 개발 Skill 9개는 `.claude/skills/`에 있다. `/harness`를 적용하고 자신의 네이티브 Agent 도구로 필요한 역할만 위임한다. `.agents/skills/`를 직접 발견한다고 가정하지 않는다. 공통 원본에서 정규 파일 사본을 생성하며 `python dev-harness/cli.py sync-claude --check`로 drift를 검사한다. 모델은 inherit이며 Agent tools로 읽기 전용/작성 역할을 구분한다. Skill allowed-tools나 소유 필드를 OS 권한으로 설명하지 않는다.

현재 로컬에 Claude CLI·로그인 환경이 없어 실제 발견·위임·인수인계를 실행하지 못했다. 파일/동기화 정적 검증과 팀원 네이티브 검증을 구분한다. 현황은 `docs/validation/development-harness.md`, 인수 절차는 `docs/development.md`를 따른다. Codex와 하나의 자동 실행 팀으로 엮지 않는다.
