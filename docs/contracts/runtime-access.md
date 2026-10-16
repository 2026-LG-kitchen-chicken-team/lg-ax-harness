# 출품 실행 권한과 화면 준비

2026-10-15 공식 문서 기준이다. 설치기는 사용자 계정·전역 설정·Windows 보안 설정을 변경하지 않는다. 이 파일은 실행자가 선택할 권한을 설명하며 설치만으로 권한이 적용됐다는 증거는 아니다.

## 심사 실행자 첫 설정

질문은 Codex 또는 Claude Desktop **Code**에서 입력한다. 결과 HTML은 저장된 기획을 읽는 화면이다. 실행자 본인의 Code 사용 가능 계정·모델 이용 한도가 필요하며 별도 LLM API key·필수 MCP/플러그인·팀 계정 공유는 필요 없다.

1. [uv](https://docs.astral.sh/uv/getting-started/installation/)와 선택한 실행기를 공식 안내로 설치한다. Codex는 [CLI 설치 안내](https://learn.chatgpt.com/docs/codex/cli), Claude GUI는 [Desktop 시작 안내](https://code.claude.com/docs/en/desktop-quickstart)를 따른다. Python은 이 프로젝트의 잠금 조건인 **3.12**를 사용한다.
2. 이미 준비된 제품 ZIP을 풀어 `product-install.json`이 있는 폴더라면 그 폴더를 사용한다. 전체 개발 소스를 받은 경우에만 소스 폴더에서 아래 둘 중 하나를 실행해 **존재하지 않는 외부 폴더**에 제품을 설치한다. 기존 제품 상태를 덮어쓰지 않는다.

```powershell
# 전체 소스에서 Codex 사본을 만들 때
uv run --python 3.12 --no-project python adapters/codex/install.py --target "$env:USERPROFILE/Documents/LG-AX-Judge-Codex"
# 또는 Claude 사본을 만들 때
uv run --python 3.12 --no-project python adapters/claude/install.py --target "$env:USERPROFILE/Documents/LG-AX-Judge-Claude"
```

3. 선택한 제품 폴더에서 `uv sync --locked --python 3.12`를 실행한다. uv가 해당 Python을 준비할 수 있으며 회사 정책으로 다운로드가 막히면 실행자가 허용된 Python3.12 설치 경로를 지정한다. 기본 `python`이 3.14여도 이 단계 뒤에는 **`uv run python`**으로 실행한다.
4. Codex는 `uv run python product-doctor.py --local-only` → `codex login`(이미 로그인했다면 생략) → `codex login status` → `uv run python product-doctor.py` 순서다. Windows에서는 CLI0.162.0 이상으로 `uv run python product-doctor.py --check-sandbox`도 실행한다. 로그인 결과만 확인하고 인증 파일은 제출하지 않는다. Claude GUI는 `uv run python product-doctor.py` 후 앱의 **Code → Local → 이 제품 폴더**를 기본 작업 폴더로 선택한다. Claude CLI의 부재/미인증과 Desktop Code 인증은 별개다.
5. 아래 실행기별 권한·모델을 확인하고 첫 세션에서 짧은 준비 진단을 요청한다. 로컬 doctor 성공만으로 실행기의 승인·네트워크·모델 접근 성공이라고 표시하지 않는다.

```text
상품기획은 아직 시작하지 말고 이 프로젝트의 실행 준비만 확인해 줘.
프로젝트 지침과 설치된 업무 Skill을 확인하고,
현재 세션의 터미널 도구로 product-doctor.py를 실행해 줘(Windows Codex는 .venv\Scripts\python.exe, 그 외는 uv run python).
공개 공식 제품 페이지 한 곳에 실제 접근 가능한지도 확인해 줘.
파일/SQLite, 웹 도구, 터미널 HTTP의 성공과 실패를 구분해 알려줘.
권한이 필요하면 정상 승인 절차를 요청하고 설정을 자동으로 넓히지는 마.
```

준비가 되면 `냉장고 사용 불편을 실제 리뷰에서 찾아 개선안을 제안해 줘.`처럼 자연어로 질문한다. 제품군 탐색에 제품코드·Skill 명령·내부 세션 ID를 강제하지 않는다. 사용한 모델·effort·권한과 진단 결과를 함께 남기며 원문 실행 로그/DB는 공개 저장소에 올리지 않는다.

### 막힐 때 확인할 순서

제품의 uv 캐시는 `pyproject.toml`의 `tool.uv.cache-dir = "runtime-data/.uv-cache"`로 작업 폴더 안에 둔다. 실제 MXC 검사에서 기본 AppData 캐시의 임시 파일 저장이 거절된 사례를 보완했다. [uv 공식 캐시 우선순위](https://docs.astral.sh/uv/concepts/cache/#cache-directory)에 따라 사용자가 `UV_CACHE_DIR`/`--cache-dir`를 별도로 지정하면 그 경로가 우선하므로 동일 작업 폴더의 쓰기 허용 범위를 확인한다. 전역 환경변수를 자동 변경하지 않는다.

| 증상 | 확인 및 조치 |
| --- | --- |
| `uv`/Codex 명령을 찾지 못함 | 공식 설치 후 새 터미널을 열고 PATH를 확인한다. Claude GUI 사용에는 `claude` 명령이 없어도 된다. |
| Python 버전/문서 의존성 오류 | 제품 폴더에서 `uv sync --locked --python 3.12` 후 `uv run python product-doctor.py`를 실행한다. |
| 기존 폴더/상위 Git 저장소 때문에 설치 거절 | 새 외부 폴더를 지정한다. 기존 DB·프로젝트 지침을 지우거나 덮어쓰지 않는다. |
| Codex `helper_unknown_error: setup refresh had errors` | 이 PC의 실제 로그에서는 기존 backend가 실행 중 Computer Use runtime의 ACL 갱신 대상을 열다가 Win32 공유 위반32로 실패했다. 호환 Windows에서는 아래 MXC 명령과 `--check-sandbox`로 준비한다. 다른 PC도 같은 원인이라고 단정하지 않는다. [공식 Windows 진단](https://learn.chatgpt.com/docs/windows/windows-sandbox)의 로그/정책을 대조하며 프로세스 강제 종료나 ACL 완화는 하지 않는다. |
| `--check-sandbox`의 `[WinError 5] ...data\business\empty` 또는 `sandbox.uv_run`의 `Failed to query Python interpreter ... (os error 5)` | 폴더 ACL 문제가 아니다. 2026-10-16 한 Windows PC(표시 빌드26300.9457, Codex CLI0.162.1과 0.162.0-alpha.17.2)의 MXC는 AppContainer·Low 토큰으로 실행됐다. 목록·읽기·작업 폴더 쓰기는 됐지만 볼륨 이름 조회(`\\.\MountPointManager`, `QueryDosDevice`)가 거부되어 `GetFinalPathNameByHandle`의 DOS/GUID 이름이 모든 경로에서 Win32 5였다. 공통 Tool은 링크가 없는 경로에서만 같은 경로를 쓰도록 보완했다. `uv run`은 인터프리터 확인에서 같은 거부로 멈추므로 Codex 제품 지침은 Windows 업무 Tool을 uv 대신 `.venv\Scripts\python.exe`로 실행한다. `--check-sandbox`의 venv Python 단계가 통과하면 `sandbox.uv_run` 실패는 참고 기록이다. 모델이 이 지침대로 실행하는지는 실제 세션 기록으로 확인한다. 같은 검사가 통과한 다른 환경의 차이는 확인하지 못했다. IT가 준비한 기존 backend가 있으면 `--check-sandbox --sandbox-backend configured`로 확인한 뒤 그 backend로 실행한다. ACL 완화·전체 접근·전역 설정 변경으로 우회하지 않는다. |
| 명령이 `blocked by policy` 또는 승인 대기 | `/permissions`와 실제 거절/승인 출처를 확인한다. 읽기 전용·approval never를 정상 요청별 승인과 혼동하지 않는다. 전체 접근으로 자동 재실행하지 않는다. |
| Claude의 기존 로컬 환경 항목 사용 불가 | 입력을 보내기 전에 새 Code 세션의 환경 목록에서 Local과 제품 폴더를 다시 선택한다. 같은 항목 선택으로 실패하면 앱의 정상 재시작/공식 지원 경로로 확인한다. 인증 성공이나 제품 업무 실패로 단정하지 않는다. |
| 공개 사이트에서 HTTP 오류/차단 | 관측한 URL·상태/오류·시각을 기록한다. 웹 검색 가능 여부와 터미널 HTTP 가능 여부를 구분하고, 원문을 얻지 못한 것을 조사 완료로 표시하지 않는다. |

pip 대체 경로는 Python3.12가 이미 설치된 경우의 선택이다. 제품 폴더에서 실행하며 PowerShell 실행 정책 변경이나 전역 패키지 설치가 필요 없다.

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r product-tools/requirements.lock
.venv/Scripts/python.exe product-doctor.py
```

## Codex

제품 설치 폴더를 기본 작업 폴더로 연다. 먼저 `uv sync --locked`와 `uv run python product-doctor.py`를 실행한다. 권장은 `gpt-6.1-sol`/`medium`이며 모델 접근 가능성은 본인 계정에서 확인한다.

```powershell
# Windows: 아래 진단이 성공한 같은 제품 폴더에서
uv run python product-doctor.py --check-sandbox
codex --search --sandbox workspace-write --ask-for-approval on-request --config 'windows.sandbox="mxc"' --model gpt-6.1-sol --config 'model_reasoning_effort="medium"'
```

MXC는 [공식 Windows sandbox 안내](https://learn.chatgpt.com/docs/windows/windows-sandbox)의 호환 Windows11 기능과 조직 정책이 필요하다. 최소 도입 빌드26100.9278/26200.9278만으로 개별 장치의 기능을 보증하지 않으므로 실제 진단 결과를 사용한다. 설치된 프로젝트 설정의 `features.prefer_mxc=true`는 호환 시 선호 설정이며 부모 approval·작업 폴더 경계·조직 정책을 해제하지 않는다. 위 명령은 Windows 전용이며 Linux/macOS에서는 Windows 진단과 `windows.sandbox` 옵션을 제외한다.

`--check-sandbox`는 업무 Tool과 같은 제품 venv Python(`.venv\Scripts\python.exe`)으로 로컬 doctor·SQLite를 실제 sandbox 프로세스 안에서 검사하며 이 단계가 통과해야 성공이다. 같은 doctor를 `uv run python`으로도 한 번 실행해 `sandbox.uv_run`에 기록하지만 Windows 업무 명령은 uv를 거치지 않으므로 성공 조건이 아니다(`required:false`). 모델·웹·브라우저를 호출하지 않으며 성공하면 `native_permissions=sandbox_process_checked`로 표시한다. MXC 오류 시 원래 오류를 반환하고 전체 접근/다른 backend로 자동 재시도하지 않는다. 호환되지 않는 장치에서는 실행자/IT가 허용된 기존 sandbox를 정상 준비한 뒤 `--check-sandbox --sandbox-backend configured`로 명시해 검사한다. 이는 기존 설정을 사용하며 전역 설정을 변경하지 않는다.

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

대시보드는 별도 관찰 프로그램이며 현재 제품 설치기와 심사위원용 ZIP에 실행 파일5개를 포함한다. `web/prototypes/agent-office/README.md`를 따라 같은 제품 폴더에 연결한다. Claude는 `office.py install --claude <제품폴더>`, Codex는 실행 **전에** `office.py codex --harness <제품폴더> --wait --until-complete`를 별도 터미널에서 실행한다. 대시보드 HTML은 해당 제품 폴더의 `runtime-data/agent-office/index.html`이다. Codex follower를 나중에 켜서 이전 로그를 읽은 경우는 실시간 관측과 구분한다. 업무가 끝난 뒤 저장 기록 재생을 현재 실행 중으로 표시하지 않는다. 심사 ZIP의 준비·질문·결과 확인은 [사용자 테스트 안내](judge-test.md)를 따른다.

대시보드의 오래된 기록이 있으면 처음에 재생 모드가 선택될 수 있다. 실행 관찰을 시작할 때 화면의 `실시간`을 선택하거나 `index.html#mode=live`로 연다. 새 사건 파일이 갱신됐다는 사실과 사용자가 선택한 화면 모드는 구별한다. 결과 웹은 자동 데이터 갱신용 `runtime-data/visual-viewer/index.html`을 사용한다. 내보낸 단일 보고서 HTML·수동 JSON 열기는 고정 산출물이며 자동 갱신 화면이 아니다.
