# Claude Code 출품 사본 준비

갱신2026-10-15. Codex와 Claude Desktop Code의 실제 인수 범위는 [최신 실행 기록](../validation/runtime-access-live-P-20261015.md)을 따른다. Gemini 신규 지원/설치/패키징은 철회했다. 과거 검사는 [당시 기록](../validation/portable-product.md)으로 보존한다.

공통 Agent1개·Skill6개·Python과 빈 기본 catalog를 유지한다. 실제 자료는 요청에 맞춰 조사·등록하며 과거 세 제품군 자료는 평가 재현용이다. Claude Skill 위치는 .claude/skills, 시작 지침은 CLAUDE.md → @AGENTS.md다. 공통 설치기는 source manifest/지문·새 폴더/저장소 경계·기존 상태 보존·정규 파일 복사를 검사한다.

```powershell
uv run python adapters/claude/install.py --target C:/YOUR-NEW-CLAUDE-PRODUCT-FOLDER
```

새 폴더에서 `uv sync --locked --python 3.12`와 `uv run python product-doctor.py`를 실행한다. GUI 사용자는 Claude Desktop의 **Code → Local**에서 본인 계정과 이 기본 작업 폴더·모델·권한을 선택한다. 별도 Claude CLI 설치·인증은 필요 없다. CLI 경로를 선택한 경우에만 자신의 CLI를 설치·인증하고 `claude`를 실행한다. `--require-native` doctor는 선택 CLI 진단이며 GUI의 선행 조건이 아니다. 기본 local_only와 CLI 버전 확인은 인증·발견·업무 지원 완료가 아니다. [심사 실행자 첫 설정](runtime-access.md)의 순서·오류별 조치를 따른다.

native 인수는 Skill 발견·첫 요청·근거 부족·같은 대화 후속·오류·검토/저장/export·관측 모델/사용량을 확인한다. 사용자 요청에 따라 이번 보완 완료 후 최길웅에게 안내 초안을 보여주고 승인 후 발송한다. 결과는 정이량 메일로 회신받는다. 인증 환경이 없으면 blocked_access/후순위로 남긴다. 팀원 개발 체계 D06b와 출품 인수는 별개다.

설치기는 로그인·전역 설정·계정·권한·모델 호출을 하지 않는다. product-install.json은 SHA/변환을 기록한다. 인증·원문 로그·DB·개인 경로·의존성 환경은 Git/제품ZIP에 넣지 않는다. 개발6역할/9Skill·평가 실행기는 설치하지 않는다.

2026-10-11 후속: 사용자가 로그인한 Claude Desktop Code에서 새 설치본의 실제 업무 검증을 진행했다. 범위와 남은 결함은 docs/validation/claude-codex-v72-20261011.md를 따른다. 외부 팀원 회신 대기와 별도 CLI 인증을 이 기록으로 완료 처리하지 않는다. 기존 메일 요청·구버전 결과는 이력이다.
