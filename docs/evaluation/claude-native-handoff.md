# 팀원 환경의 Claude 인수 체크리스트

2026-10-10. 팀원의 Claude 개발 체계 D06b와 출품 업무 S02b/S03b2를 별도 실행한다. 현재 PC의 파일·공통 Python 검사는 native 발견/위임/모델 실행을 증명하지 않는다. 전역 설정·인증을 복사하거나 Codex와 Claude를 하나의 자동 팀으로 연결하지 않는다.

개발 인수는 푸시된 최신 소스를 팀원의 별도 checkout에 받는다. 원본 요구·결정·작업 상태·diff·실제 검사 보고서를 읽고 `uv sync --locked`, `uv run python dev-harness/cli.py doctor`, `uv run python dev-harness/cli.py sync-claude --check`를 실행한다. 팀원은 자신의 Claude 로그인·프로젝트 신뢰/권한을 설정한다. `/harness`에 작은 실제 작업을 요청해 .claude/agents의 필요한 역할 발견→native 위임 ID/결과→한 작성자의 구현/통합→실제 검사 receipt→독립 리뷰를 관측한다. 실제 기능을 모르면 설정/TOML이 자동 적용됐다고 기록하지 않는다.

출품 인수는 개발 레포 밖의 새 폴더를 `adapters/claude/install.py`로 만든다. 공통 Tool doctor 뒤 Claude 새 세션에서 업무 Skill6개의 발견 경로를 확인한다. 첫 질문·같은 대화 후속·모호한 모델 needs_input·치수 부족 held·실제 오류·실패 후보/최대 수정2회·저장/export를 확인한다. 개인/관리 Skill 이름 충돌과 실제 Tool 권한을 기록한다. 동일 심사 질문을 Gemini에서도 별도 검증한다.

인수 결과에는 source commit/manifest SHA, OS/CLI 버전, 관측 모델/설정/권한, 실제 native ID, 입력·출력·저장 상태, 검사 command/exit/receipt, 실패/미실행, 관측 usage 또는 null을 남긴다. 원문 로그·DB·계정 정보는 Git에 넣지 않는다. 현재는 팀원 native 실행 근거가 없으므로 D06b·S02b/c·S03b2를 완료로 표시하지 않는다.
