# 출품 실행 권한과 화면 준비

2026-10-15 공식 문서 기준이다. 설치기는 사용자 계정·전역 설정·Windows 보안 설정을 변경하지 않는다. 이 파일은 실행자가 선택할 권한을 설명하며 설치만으로 권한이 적용됐다는 증거는 아니다.

## Codex

제품 설치 폴더를 기본 작업 폴더로 연다. 먼저 `uv sync --locked`와 `uv run python product-doctor.py`를 실행한다. 권장은 `gpt-6.1-sol`/`medium`이며 모델 접근 가능성은 본인 계정에서 확인한다.

```powershell
codex --search --sandbox workspace-write --config 'approval_policy="on-request"' --model gpt-6.1-sol --config 'model_reasoning_effort="medium"'
```

`/permissions`에서 현재 부모 권한을 확인한다. 업무에는 제품 폴더의 `runtime-data`·DB·입출력 쓰기와 실제 웹 검색/조회가 필요하므로 부모 전체를 읽기 전용으로 실행하면 저장이 막힌다. 웹 검색 허용과 Python HTTP 명령의 네트워크 허용은 구별한다. 필요한 공개 URL 접근은 실행기의 실제 승인 안내에 따라 처리한다. Windows sandbox 초기화 오류는 Tool 실패로 남기며 전체 접근·훅 신뢰 우회로 자동 재실행하지 않는다.

**자식은 부모 sandbox/approval을 상속한다.** custom agent의 `sandbox_mode`/`approval_policy`는 이를 덮어쓰지 않는다. 세 역할은 조회·분석만 하고 부모만 직렬 저장한다는 업무 계약이다. 이 계약을 OS 읽기 전용 격리라고 표시하지 않는다. 강제된 별도 읽기 전용 프로세스가 필요한 배포는 별도 실행기/컨테이너 설계가 필요하며 현재 경로에 추가하지 않는다. 실제 모델/effort·도구·권한은 native 로그로 구분한다.

공식 근거: [서브에이전트 권한 상속](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex 권한](https://learn.chatgpt.com/docs/permissions).

## Claude Desktop Code

유료 계정으로 로그인된 앱의 **Code 로컬 세션**에서 제품 설치 폴더를 기본 작업 폴더로 선택한다. 일반 Chat이나 추가 접근 폴더 지정만으로 대신하지 않는다. 권장 모델은 `Opus 5.5`, UI 추론 수준 `중간`이다. CLI 설치·별도 로그인은 필수가 아니다.

`/permissions`에서 출처별 allow/ask/deny와 현재 모드를 확인한다. Manual(`default`)은 필요한 명령·파일 쓰기·웹 조회를 실행자가 확인하는 기준이다. 제공되는 `auto`는 실행기 분류기가 요청과 동작을 대조하는 선택이며 요청이 차단되면 이유를 확인한다. 단순 편집 허용(`acceptEdits`)은 모든 Python 명령/웹 요청 허용과 같지 않다. `bypassPermissions`를 기본으로 배포하지 않는다. 폴더 신뢰·앱 권한 요청은 실행자가 직접 처리한다.

메인은 공통 Python Tool로 `runtime-data`를 작성한다. 자식 검토자는 `Read, Glob, Grep`, 조사자는 여기에 `WebFetch, WebSearch`만 허용한다. `Bash, Write, Edit, Agent, Task, Skill, mcp__*`는 자식 도구 목록에서 제외한다. `permissionMode: default`는 부모가 auto/acceptEdits/bypassPermissions인 경우 부모 모드를 이기지 못하므로 도구 목록 제한과 구별한다. 이것을 Windows 파일 시스템 격리로 설명하지 않는다. Agent 호출을 전역/프로젝트에서 거부한 설정이 있으면 선택 역할은 실행되지 않으므로 실제 deny 출처를 확인한다.

공식 근거: [권한 규칙과 모드](https://code.claude.com/docs/en/permissions), [서브에이전트 도구·권한](https://code.claude.com/docs/en/sub-agents).

## 결과 웹과 실행 대시보드

결과 웹은 저장된 현재 결과를 표시한다. 첫 저장 전에는 새 기획이 없으며, 저장/export 후 `view-data.js`가 바뀌면 열어둔 화면이 갱신된다. 실행 대시보드는 그동안의 실제 Tool·Skill 작업·선택 역할 사건을 별도로 표시한다. 화면 생성·관찰은 일반 코드이고 추가 모델 호출이 없다.

제품 설치 폴더에서 결과 뷰어를 한 번 연결한다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py install --codex .
# Claude를 사용하는 폴더에서는 위 명령 대신 install --claude .
```

Codex는 정상 `/hooks` 신뢰 확인 뒤 Stop 훅, Claude는 프로젝트 PostToolUse 훅으로 갱신한다. `viewer.py open .`은 수동 열기 명령이다. 자동 브라우저 요청이 성공했다는 값도 화면 렌더링·클릭 검사와는 다르다. 자동 훅에서 `LGAX_VIEWER_NO_OPEN=1`이면 파일만 생성하고 브라우저를 요청하지 않는다. 수동 명령에서 브라우저 요청을 생략하려면 `viewer.py open --no-browser .`을 사용한다.

대시보드는 별도 소스 프로그램이므로 제품 설치기에 포함됐다고 가정하지 않는다. 개발 저장소의 `web/prototypes/agent-office/README.md`를 따라 같은 제품 폴더에 연결한다. Claude는 `office.py install --claude <제품폴더>`, Codex는 실행 **전에** `office.py codex --harness <제품폴더> --wait --until-complete`를 별도 터미널에서 실행한다. 대시보드 HTML은 해당 제품 폴더의 `runtime-data/agent-office/index.html`이다. Codex follower를 나중에 켜서 이전 로그를 읽은 경우는 실시간 관측과 구분한다. 업무가 끝난 뒤 저장 기록 재생을 현재 실행 중으로 표시하지 않는다.

대시보드의 오래된 기록이 있으면 처음에 재생 모드가 선택될 수 있다. 실행 관찰을 시작할 때 화면의 `실시간`을 선택하거나 `index.html#mode=live`로 연다. 새 사건 파일이 갱신됐다는 사실과 사용자가 선택한 화면 모드는 구별한다. 결과 웹은 자동 데이터 갱신용 `runtime-data/visual-viewer/index.html`을 사용한다. 내보낸 단일 보고서 HTML·수동 JSON 열기는 고정 산출물이며 자동 갱신 화면이 아니다.
