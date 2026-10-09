# LG AX 신규 하네스 개발

Codex와 Claude Code로 새로운 LG AX 프로젝트를 개발하기 위한 초기 개발 체계다. OpenSpec이 요구사항·설계·작업 기록을 관리하고, 저장소의 검사 프로그램이 실제 검증 결과를 남긴다.

출품용 Agent·Skill·업무 구현은 아직 없다. 그 업무, 언어, 모델과 실행 구조는 별도 결정한다. 기존 LG 작업물은 재사용하지 않는다.

## 시작

Node.js 22 이상과 Git이 필요하다. 다음 명령은 저장소 루트에서 실행한다.

```powershell
npm ci
npm run doctor
npm run check -- --tool codex
npm run report
```

Claude가 작업하는 경우 검사에 `--tool claude`를 사용한다. 이 표기는 작업 도구를 기록하며 해당 도구를 자동 실행하거나 로그인시키지 않는다.

## 자연어로 개발하기

- Codex에서는 `openspec-propose` Skill을 선택하거나 `$openspec-propose`로 새로운 변경을 정의한다.
- Claude Code에서는 `/opsx:propose`로 변경을 정의한다.
- 요구사항·설계·작업 목록을 확인한 뒤 Codex의 `$openspec-apply-change` 또는 Claude의 `/opsx:apply`로 구현한다.
- 실제 검사를 실행하고 결과와 diff를 검토한다. 도구를 바꾸어 이어받을 때도 같은 변경 문서를 읽는다.

CLI는 `npm run spec -- list`, `npm run spec -- status --change <작업-id>`처럼 고정된 로컬 버전으로 실행한다. `status`는 계획 문서의 준비 상태이며 코드 구현·테스트 완료를 의미하지 않는다.

## 저장소 구성

| 경로 | 역할 |
|---|---|
| `AGENTS.md`, `CLAUDE.md` | 공통 개발 규칙과 도구별 연결 |
| `.agents/skills/`, `.claude/` | OpenSpec이 생성한 도구별 Skill·명령 |
| `openspec/` | 요구사항과 변경 작업의 원본 |
| `dev-harness/`, `tests/dev-harness/` | 환경 확인·검사·JSON 보고서와 자체 테스트 |
| `reports/` | 생성된 검사 결과, Git 제외 |
| `.github/workflows/check.yml` | Windows·Linux 자동 검사 |

출품 코드와 업무 평가 디렉터리는 업무·스택 결정 후 추가한다. 개발용 시각화 화면은 만들지 않는다.

## 현재 확인 범위

OpenSpec의 양쪽 연결 파일이 생성되어 있다. 실제 CLI·Skill 인식과 인수인계 검증은 `openspec/changes/bootstrap-development-harness/tasks.md`에 기록한다. 도구가 설치되지 않은 환경에서는 그 도구의 실제 실행 검증을 완료했다고 보지 않는다.

OpenSpec 1.14.1의 하위 `braces` 의존성에는 현재 미패치 보안 경고가 있다. 기능 검사와 보안 audit 결과를 구분한다. 자세한 사용법과 제한은 [개발 안내](docs/development.md)를 읽는다.
