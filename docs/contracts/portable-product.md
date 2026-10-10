# Claude Code·Gemini CLI 출품 사본 준비

2026-10-10. 공통 업무 Skill6개·Python·실제 v3 자료를 유지하고 프로젝트 Skill 위치와 시작 지침만 환경별로 연결한다. 기존 Codex 설치기는 그대로 유지한다. `adapters/common/install.py`는 Codex의 검증된 원본 파일 목록/지문 검사를 사용하며 새 폴더 제한·저장소 경계·기존 상태 보존·정규 파일 복사를 적용한다.

| 실행기 | 업무 Skill | 시작 지침 | 현재 지원 범위 |
|---|---|---|---|
| Codex | .agents/skills | AGENTS.md | 기존 native 인수 + 별도 실제 입력 평가 기록 |
| Claude Code | .claude/skills | CLAUDE.md → @AGENTS.md | 사본·링크·공통 Tool 준비; native 미검증 |
| Gemini CLI | .gemini/skills | GEMINI.md → @AGENTS.md | 사본·링크·공통 Tool 준비; native 미검증 |

Claude의 프로젝트 Skill·import는 [Skill 문서](https://code.claude.com/docs/en/skills)와 [메모리 문서](https://code.claude.com/docs/en/memory)를 따른다. 개인·관리 지침과 이름 충돌을 실제 발견 검사에서 확인하고 프로젝트 파일이 [Tool 권한](https://code.claude.com/docs/en/permissions)을 강제한다고 설명하지 않는다.

Gemini의 [Skill 발견·활성화 동의](https://geminicli.com/docs/cli/using-agent-skills/), [GEMINI.md import](https://geminicli.com/docs/cli/gemini-md/), [폴더 신뢰](https://geminicli.com/docs/cli/trusted-folders/)를 따른다. 한 설치 사본에 .gemini/skills와 .agents/skills를 중복 설치하지 않는다. 동의·신뢰·권한을 설치기가 자동 우회하지 않는다.

```powershell
uv run python adapters/claude/install.py --target C:/YOUR-NEW-CLAUDE-PRODUCT-FOLDER
uv run python adapters/gemini/install.py --target C:/YOUR-NEW-GEMINI-PRODUCT-FOLDER
```

새 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`, 해당 CLI를 실행한다. doctor 기본값은 파일/버전/공통 Tool 검사이며 인증을 읽거나 모델을 호출하지 않는다. CLI 부재면 local_only, 존재하면 native_version_only다. `--require-native`는 CLI 부재를 실패로 보고한다. version 실행 실패도 실패로 보존하며 로그인·Skill 발견·Tool 권한 성공으로 바꾸지 않는다. 실행자 CLI 설치/로그인과 환경별 실제 인수는 별도다.

공통 source/설치 SHA와 변환 내역은 product-install.json에 남는다. 원문·DB·인증·개인 설정·의존성 환경은 제출하지 않는다. 개발용 Agent6개/Skill9개는 이 사본에 설치하지 않는다. 모델/API 실행기나 실행기 사이의 자동 위임도 추가하지 않는다.

실제 인수에는 native Skill 발견/동의, 첫 질문·같은 대화 후속 질문, needs_input/held, 실제 오류, 저장·export·수정 한도, 관측 가능한 모델/사용량이 필요하다. 현재 PC PATH에서 두 CLI를 찾지 못했으며 설치·로그인·실제 inference를 진행하지 않았다. 준비 완료와 native 지원 완료를 구분한다. 팀원의 Claude 개발 인수 D06b는 이 출품 준비 S02b와 별도다.
