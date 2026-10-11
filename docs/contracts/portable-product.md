# Claude Code 출품 사본 준비

갱신2026-10-11. Codex가 주 제출 기준이고 Claude는 인증 가능한 환경에서 후순위로 인수한다. Gemini 신규 지원/설치/패키징은 철회했다. 과거 검사는 [당시 기록](../validation/portable-product.md)으로 보존한다.

공통 Agent1개·Skill6개·Python·실제 세 제품군 자료를 유지한다. Claude Skill 위치는 .claude/skills, 시작 지침은 CLAUDE.md → @AGENTS.md다. 공통 설치기는 source manifest/지문·새 폴더/저장소 경계·기존 상태 보존·정규 파일 복사를 검사한다.

```powershell
uv run python adapters/claude/install.py --target C:/YOUR-NEW-CLAUDE-PRODUCT-FOLDER
```

새 폴더에서 uv sync --locked와 uv run python product-doctor.py 후 자신의 Claude Code 설치·인증·폴더 신뢰/권한으로 claude를 실행한다. --require-native doctor는 CLI 부재를 실패로 보고한다. 기본 local_only와 CLI 버전 확인은 인증·발견·업무 지원 완료가 아니다.

native 인수는 Skill 발견·첫 요청·근거 부족·같은 대화 후속·오류·검토/저장/export·관측 모델/사용량을 확인한다. 사용자 요청에 따라 이번 보완 완료 후 최길웅에게 안내 초안을 보여주고 승인 후 발송한다. 결과는 정이량 메일로 회신받는다. 인증 환경이 없으면 blocked_access/후순위로 남긴다. 팀원 개발 체계 D06b와 출품 인수는 별개다.

설치기는 로그인·전역 설정·계정·권한·모델 호출을 하지 않는다. product-install.json은 SHA/변환을 기록한다. 인증·원문 로그·DB·개인 경로·의존성 환경은 Git/제품ZIP에 넣지 않는다. 개발6역할/9Skill·평가 실행기는 설치하지 않는다.
