# LG AX 심사위원·사용자 테스트

이 ZIP만 풀면 업무용 하네스·기획자 웹·별도 보고서·실행 대시보드를 준비할 수 있습니다. `codex/` 또는 `claude/` 하나를 선택해 **그 폴더를 기본 작업 폴더**로 사용합니다. 두 환경의 기록은 분리됩니다. 개발 저장소·Node/npm·별도 LLM API key·필수 MCP/플러그인은 필요 없습니다. 실행기와 본인 계정 이용권은 별도로 필요합니다.

## 0. 가장 빠른 시작: 더블클릭

ZIP을 새 폴더에 전부 푼 뒤, 그 폴더(이 README가 있는 곳)에서 사용할 실행기 하나를 고릅니다. Windows는 `.cmd`를 더블클릭하고, macOS/Linux는 터미널에서 `./start_claude_cli.sh`처럼 실행합니다(실행 권한이 없으면 `bash start_claude_cli.sh`).

| 실행기 | Windows (더블클릭) | macOS/Linux | 열리는 것 |
|---|---|---|---|
| Claude 앱(GUI) | `start_claude_gui.cmd` | `./start_claude_gui.sh` (macOS) | Claude Desktop의 Code 세션을 `claude` 폴더로 엽니다 |
| Claude CLI | `start_claude_cli.cmd` | `./start_claude_cli.sh` | `claude` 폴더에서 Claude Code CLI (Opus 5.5, 추론 중간) |
| Codex 앱(GUI) | `start_codex_gui.cmd` | `./start_codex_gui.sh` (macOS) | `codex app`으로 Codex 앱을 `codex` 폴더로 엽니다 |
| Codex CLI | `start_codex_cli.cmd` | `./start_codex_cli.sh` | `codex` 폴더에서 Codex CLI (아래 2절과 같은 옵션) |

각 스크립트가 순서대로 하는 일:

1. uv가 없으면 공식 설치 명령을 보여 주고 `y`를 입력한 경우에만 설치합니다.
2. `judge.py prepare`: ZIP 무결성 확인 → 처음 한 번만 1절의 `setup`(의존성·결과 웹 훅·실행 대시보드 훅) → 실행기 확인. Claude CLI가 없으면 공식 설치 명령을 보여 주고 `y`일 때만 설치합니다. Codex는 로그인 상태를 확인하고(미로그인이면 `codex login`), `product-doctor.py`를 실행합니다(Windows CLI는 `--check-sandbox` 포함).
3. 실행 대시보드: Claude는 **첫 질문을 보내는 순간** 훅이 브라우저에 대시보드를 엽니다(세션마다 한 번). Codex는 작은 "실행 관찰" 창(또는 백그라운드)이 새 세션을 기다렸다가 첫 질문이 기록되면 대시보드를 열고, 후속 질문까지 계속 따라갑니다. 관찰 창을 닫거나 Ctrl+C로 멈춥니다.
4. 선택한 실행기를 올바른 폴더(`claude/` 또는 `codex/`)에서 시작합니다.

스크립트는 로그인·폴더 신뢰·권한/훅 승인을 대신하지 않습니다. 화면에 나오는 본인 계정 로그인과 승인 질문은 직접 처리합니다. 인터넷에서 받은 ZIP이면 Windows가 "Windows의 PC 보호" 또는 보안 경고를 띄울 수 있습니다. 파일 이름을 확인하고 **추가 정보 → 실행**(또는 ZIP 파일 속성의 **차단 해제** 후 다시 풀기)을 선택합니다. 스크립트가 멈추면 같은 내용의 수동 절차(1~3절)를 따릅니다.

## 1. ZIP만으로 준비

1. ZIP을 문서 폴더 등 새 폴더에 전부 풉니다. Git 저장소 안이나 이전 설치 위에 덮어쓰지 않습니다.
2. [uv 설치](https://docs.astral.sh/uv/getting-started/installation/) 후 새 터미널을 엽니다. 실행기는 하나만 있으면 됩니다.
   - Codex: [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)를 설치합니다. Codex 앱은 CLI의 `codex app`으로 열 수 있습니다.
   - Claude 앱: [Claude Desktop](https://code.claude.com/docs/en/desktop-quickstart)의 **유료 Code 로컬 세션**을 사용합니다. 일반 Chat 화면은 이 프로젝트 실행 환경과 다릅니다.
   - Claude CLI: 3-2절의 공식 설치 명령으로 Claude Code CLI를 설치합니다.
3. ZIP의 `judge.py`가 있는 폴더에서 다음을 실행합니다. uv가 프로젝트에서 사용하는 Python3.12를 준비합니다.

```powershell
uv run --no-project --python 3.12 python judge.py check
uv run --no-project --python 3.12 python judge.py setup --engine codex
# Claude 사용자(앱·CLI 공통)는 위 setup 대신 아래 하나를 실행
uv run --no-project --python 3.12 python judge.py setup --engine claude
```

setup은 선택한 사본의 의존성과 프로젝트 훅만 준비합니다. 계정·전역 설정·보안 설정·권한 우회·모델 실행을 자동으로 처리하지 않습니다. 기본 자료 저장소는 비어 있어 실제 첫 업무에서는 AI가 웹을 조사하고 근거를 등록합니다. 특정 제품/질문의 미리 작성된 답안을 선택하지 않습니다.

## 2. Codex 시작

두 터미널을 사용합니다. 첫 터미널은 ZIP 루트에서 **AI를 시작하기 전에** 실행 관찰을 켭니다.

```powershell
uv run --no-project --python 3.12 python judge.py observe --engine codex
```

두 번째 터미널은 선택한 제품 폴더에서 실행합니다.

```powershell
cd codex
codex login status
# 미로그인인 경우에만 codex login
uv run python product-doctor.py
uv run python product-doctor.py --check-sandbox
codex --search --sandbox workspace-write --ask-for-approval on-request --config 'windows.sandbox="mxc"' --model gpt-6.1-sol --config 'model_reasoning_effort="medium"'
```

마지막 두 Windows sandbox 명령은 호환 Windows11용입니다. Linux/macOS는 Windows 진단과 `windows.sandbox` 옵션을 제외합니다. 조직 정책이나 MXC 호환 문제는 `docs/contracts/runtime-access.md`의 정상 진단 절차를 따릅니다. 전체 접근으로 자동 전환하지 않습니다.

Codex 앱(GUI)을 쓰려면 마지막 줄 대신 ZIP 루트에서 `codex app codex`를 실행합니다. 앱이 없으면 설치 화면이 열립니다. 앱의 권한·샌드박스 설정은 앱 화면에서 확인합니다.

첫 세션의 `/permissions`에서 작업 폴더 쓰기와 필요한 공개 웹 조회를 확인하고, `/hooks`에서 설치된 프로젝트 훅을 정상 신뢰 처리합니다. 승인 대기 또는 차단은 원인을 읽고 실행자가 처리합니다. **훅 등록만으로 신뢰 승인이 완료되지는 않습니다.** 로그인/doctor만 통과한 것과 실제 업무 완료도 구분합니다.

첫 `--wait` 관찰은 첫 답변이 끝나면 종료됩니다. 같은 대화의 후속 질문 전에는 첫 터미널에서 `judge.py observe --engine codex --latest`로 현재 세션 관찰을 다시 켭니다. 이 경로는 과거 완료 기록 때문에 종료되지 않고 계속 관찰하며, 테스트 후 Ctrl+C로 멈춥니다. 처음부터 후속 질문까지 한 번에 관찰하고 대시보드를 자동으로 열려면 `judge.py observe --engine codex --keep-following --open`을 사용합니다(원클릭 스크립트가 쓰는 방식).

## 3. Claude 시작

Claude는 앱(GUI)과 CLI 중 하나를 사용합니다. 둘 다 같은 `claude` 폴더의 지침·Skill 6개·훅을 읽습니다. **세션은 반드시 `claude` 폴더에서 시작합니다.** ZIP 루트에서 시작한 세션은 프로젝트 Skill과 훅을 읽지 않으며, 대화 중에 `cd claude`를 해도 다시 읽지 않습니다. 이때는 `claude` 폴더에서 새 세션을 엽니다.

### 3-1. Claude Desktop Code (앱)

유료 Code 사용 가능 계정으로 앱에 로그인하고 **Code → Local → ZIP의 `claude` 폴더**를 새 세션의 기본 작업 폴더로 선택합니다. CLI 설치·별도 CLI 인증은 필요 없습니다. 모델은 앱에서 `Opus 5.5`, 추론 `중간`을 확인합니다. 폴더 신뢰와 필요한 파일/명령/공개 웹 접근은 실행자가 정상 처리합니다. Manual(default) 또는 앱이 제공하는 자동 모드를 사용하며 bypassPermissions를 기본값으로 사용하지 않습니다.

Claude Code CLI 2.1.285 이상이 설치·로그인되어 있으면 `claude` 폴더에서 `claude --desktop`으로 앱을 그 폴더로 바로 열 수 있습니다(macOS, x64 Windows). `start_claude_gui` 스크립트는 이 방법을 먼저 쓰고, 안 되면 앱을 열고 폴더 경로를 클립보드에 복사한 뒤 선택 순서를 안내합니다.

### 3-2. Claude Code CLI (터미널)

[공식 설치 안내](https://code.claude.com/docs/en/setup)의 명령으로 설치합니다. 관리자 권한은 필요 없습니다.

```powershell
# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash
```

새 터미널에서 `claude --version`으로 설치를 확인합니다. Claude Code는 Pro·Max·Team·Enterprise 또는 Console 계정이 필요합니다(무료 플랜 불가). Windows의 Git for Windows는 선택이며 없으면 PowerShell 도구를 사용합니다. 1절의 `setup --engine claude`를 마친 뒤 ZIP 루트에서 실행합니다.

```powershell
cd claude
claude auth status
# loggedIn이 false이면 아래 claude 첫 실행 때 브라우저 로그인 화면이 열립니다 (또는 claude auth login)
claude --model claude-opus-5-5 --effort medium
```

처음 실행하면 폴더 신뢰를 묻습니다. 내용을 확인하고 신뢰하면 이 폴더의 Skill과 훅이 켜집니다. 권한 요청은 Manual(default) 그대로 정상 처리하며 `--dangerously-skip-permissions`를 사용하지 않습니다. 대화 중 `/skills`로 Skill 6개, `/hooks`로 설치된 훅을 확인할 수 있습니다. 끝낼 때는 `/exit`입니다.

### 관찰 터미널 (선택)

Claude는 훅이 실행 기록을 남기므로 별도 관찰 명령 없이도 실행 대시보드가 갱신되고, 첫 질문 때 대시보드가 자동으로 열립니다. 기록을 글로 따라 보려면 ZIP 루트에서 다음을 실행합니다.

```powershell
uv run --no-project --python 3.12 python judge.py observe --engine claude
```

이미 열린 세션에 훅을 나중에 설치했다면 새 세션으로 시작합니다. 프로젝트 훅의 파일 등록·실제 native 호출·화면의 표시를 각각 확인합니다.

## 4. 질문하며 테스트

첫 입력은 실행 준비를 확인하는 짧은 요청입니다.

```text
상품기획은 아직 시작하지 말고 설치된 지침과 Skill, 로컬 파일/SQLite 실행 준비와 공개 웹 조회 가능 여부를 확인해줘. 권한이 필요하면 정상 절차로 요청해줘.
```

그다음 자연어로 하나씩 요청합니다. 매번 Skill 이름이나 제품코드를 입력할 필요는 없습니다.

| 순서 | 직접 넣을 질문 | 확인할 것 |
|---|---|---|
| 정상 | 냉장고의 실제 사용 불편을 여러 후기와 공식 자료에서 조사하고, 기존 기능을 고려해 개선할 상품기획을 제안해줘. | 실제 조사 출처·모델/시점·긍정/조건/반례·기존 기능 비교·기획 결과 |
| 후속 | 앞 기획에서 가장 중요한 한 안을 골라 사용자가 입력을 덜 하는 3단계 흐름으로 구체화해줘. | 이전 업무 이력과 연결된 새 결과·근거 유지·웹의 현재 버전 갱신 |
| 확장 | 전자레인지 또는 식기세척기도 같은 방식으로 조사해줘. | 새 제품군에 맞는 실제 자료와 기획. 냉장고 근거를 그대로 쓰지 않기 |
| 자료 부족 | LG TEST-NOT-A-REAL-MODEL-20261015의 내부 유효 치수를 확정해줘. | 확인 불가능한 모델/치수를 만들어내지 않고 이유와 다음 조치를 전달 |

명시 호출도 선택 사항입니다. Codex는 `$evidence-retrieval`, `/skills`에서 선택, Claude는 `/evidence-retrieval`처럼 설치된 Skill을 호출할 수 있습니다. 선택 역할은 공식 자료 조사자·후기 조사분석자·근거 검토자 3개입니다. 메인이 필요한 경우에 native 서브에이전트로 위임하며 모든 질문에서 전부 만들지는 않습니다. Skill과 서브에이전트는 서로 다른 기능입니다.

## 5. 결과 웹·보고서·대시보드

실행 전 관찰 프로그램을 시작한 후 경로를 확인합니다.

```powershell
uv run --no-project --python 3.12 python judge.py paths --engine codex
# Claude라면 --engine claude
```

`runtime-data/agent-office/index.html`은 실행 대시보드입니다. Claude는 세션의 첫 질문 때 훅이, Codex는 `--open` 관찰이 새 세션의 첫 기록 때 기본 브라우저에 한 번 엽니다. 자동으로 열리지 않았거나 닫았다면 표시된 경로를 브라우저에서 직접 열고 **실시간**을 선택합니다. 대시보드는 훅·세션 기록이 남긴 도구 호출·Skill·서브에이전트를 1초마다 다시 읽으며 모델 내부를 본 것은 아닙니다. `runtime-data/visual-viewer/index.html`은 기획자 웹입니다. 첫 결과 저장 전에는 기획자 웹에 새 결과가 없고, 저장/export 후 결과 웹이 갱신됩니다. 보고서 보기 버튼은 검토된 현재 결과를 별도 보고서로 보여주며 차트 2개와 원문·출처를 함께 확인할 수 있습니다. 보고서/시각화는 일반 코드로 만들며 시각화용 추가 모델 호출이 없습니다.

훅이 실행되지 않았다면 선택한 제품 폴더에서 수동 갱신할 수 있습니다. 이는 자동 실행 확인과 구분합니다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py status .
uv run python web/prototypes/visual-viewer/viewer.py open .
```

## 6. 피드백 남기기

사용 실행기·모델/추론·질문·소요 시간·기획자/보고서/대시보드 각각의 표시 여부·막힌 승인/오류·후속 갱신 여부를 기록합니다. 결과의 출처 링크와 긴 원문 펼침, 자연어 답변과 저장 결과의 일치도 확인합니다. 화면 캡처에서 계정·개인 정보는 가립니다.

원본 export는 선택 제품 폴더의 `runtime-data/exports/`에 저장됩니다. 개인 원문 로그·SQLite·인증·캐시를 공개 저장소에 업로드하지 않습니다. 결과가 보류/needs_input이면 그 이유와 다음 질문을 평가하고, 이를 상품기획 해결 완료로 해석하지 않습니다.
