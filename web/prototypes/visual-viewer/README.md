# 2026-10-14 현재 결과 연결

현재 전달은 `export_session`의 마지막 turn에 있는 `web_binding`과 같은 불변 `runtime-data/web-deliveries/web-<sha256>.json`을 연결해야 표시한다. 저장 구조 검사만 통과한 후보, 취소된 마지막 turn, 다른 결과 버전·코드·자료·문맥·조사 지문은 현재 전달로 표시하지 않는다. 파일 바이트 SHA-256과 파일명도 대조한다. 파일이 없거나 맞지 않으면 현재 웹 전달 미검증 안내와 후보 이력을 유지한다. 연결 검증은 출처 의미 품질 인증이 아니다.

`build_view.py --export <export.json> --web-result <web-sha256.json> --web-result-sha256 <sha256> --standalone <report.html>`로 명시할 수 있다. 생략하면 export 옆의 web-deliveries에서 **정확한 binding**으로 찾으며 파일 수정 시각으로 선택하지 않는다. 기존 단일 HTML 출력은 유지하며 보기는 K 업무형 하나로 정리했다. 이 경로는 모델 호출을 추가하지 않는다.

근거 화면은 결과에 사용한 인용과 선택 등록본문 전체를 구분한다. 전체 등록본문, ID, 모델·문서·자료 버전, 전체 SHA-256, 위치와 origin을 접어 보기로 제공한다. 검토·조사 이력 화면도 같은 웹 JSON의 coverage/evidence_history/investigation_events를 표시한다. 등록본문은 원본 전체 문서 인증이 아니다.

`insights`에는 현재 export의 `web_binding` 전체를 `binding`으로 복사해야 한다. 같은 session_id·turn_id만 있는 해석은 적용하지 않는다. 같은 turn에서 결과나 조사 이력이 바뀌면 새 binding으로 검토·저장해야 한다. 기존 아래 설명 중 session/turn만으로 적용하는 기준은 이 조건으로 대체한다.

## 2026-10-12 통합 검토

PR #6 bdb187b 작성자의 최신 댓글은 Windows Codex 0.162.1 Stop와 Claude Code 2.1.289 실제 실행 성공을 보고합니다. 아래 이전 미확인 문구는 그 댓글 이전의 이력입니다. 이번 제품 통합에서는 원저장 payload를 유지한 source_metadata 종류 연결과 하위 연결 경로 검사를 추가하고 별도 회귀를 수행합니다. 실제 결과·설정·훅은 기본 패키지에 넣지 않으며 install은 사용자가 선택합니다. 원격에 올린 시제품과 최신 제품 업무의 새 native 인수를 구분합니다.

# 저장 결과 시각자료 뷰어 — 참고용 시제품

2026-10-12 최길웅 제출. **웹 PM 황대겸의 기술·구조 결정 전 참고용 시제품**이며 채택·웹 통합·시연 인수 기록이 아니다. 팀이 공유한 Streamlit 고객 리뷰 분석 시연 영상(`KakaoTalk_20261009_191820838.mp4`, Git 제외)의 화면 느낌(남색 단계 사이드바, 어두운 지표 카드, Plotly풍 차트, 하단 단계 자막)을 참고해 새로 작성했다. 영상 앱의 코드는 가져오지 않았다. 대겸의 PR #7(`codex/local-harness-web`)은 사용자 결정에 따라 쓰지 않았고 코드도 가져오지 않았다. main·제품 ZIP 포함 여부는 [결정 요청 메모](RELEASE-MEMO.md)를 따른다.

**2026-10-12 화면 재설계(브랜치 `web/visual-viewer-redesign`)**: 팀 피드백(발표 자료처럼 가독성 좋게, 많이 쓰는 UI 라이브러리 적극 사용)에 따라 화면을 Vite + React + TypeScript + Tailwind 4 + shadcn/ui 스타일 컴포넌트 + Unovis 차트로 다시 만들었다. 사용자가 후보(visx·Unovis·Magic UI SaaS 템플릿·shadcnblocks 관리자 템플릿)를 직접 보고 골랐고, 유료 키트는 쓰지 않았다(shadcn/ui·Magic UI 스타일 부품은 이 폴더에 직접 작성). 결과물은 여전히 **`index.html` 한 파일**이라 훅·설치·`build_view.py`·단일 HTML 보고서 방식은 그대로다. 첫 화면은 발표형 `한눈에 보기`(질문 → 현재 불편 → 기존 기능 대조 → 연결 → 제안 → 한계)이고 나머지 8개 화면은 관리 화면 스타일이다.

**2026-10-15 보기 하나로 정리(사용자 요청)**: 비교용으로 만든 13개 보기(A 앱 ~ M 모노+업무) 중 가장 최근에 다듬은 **K 업무형만 남기고** 나머지 12개를 지웠다. 화면 오른쪽 위 `보기` 전환 버튼을 없앴고, `build_view.py --mode ops`는 기존 설치 호출 호환용으로만 남겼다. 지운 보기만 쓰던 reveal.js·motion 패키지와 고쳐 쓴 Cult UI·Skiper UI 코드도 뺐다(`index.html` 1.40MB → 0.80MB). K의 모양은 그대로다: 지우기 전후 K의 다섯 화면·검색 창·ID 설명 카드·글자 크게·휴대폰 폭을 같은 자료로 찍어 픽셀 비교했고, 달라진 곳은 위쪽 줄의 보기 버튼 자리뿐이다.

## 기획자 설치 안내 (Claude Code·Codex 공용)

CLI에서 질문해 결과(export)가 저장되면 브라우저에 결과 화면이 자동으로 열린다(Claude Code는 export 직후, Codex는 답변이 끝날 때). CLI 세션마다 처음 한 번만 열리고, 그 뒤 결과는 열린 화면이 2초 안에 바뀐다. 하네스 업무 방식(Agent·Skill·Tool·모델)은 그대로다.

준비: 설치된 하네스 폴더(Codex용 제품 폴더나 Claude 사본), uv와 Python 3.12(하네스 설치 조건과 같음), 이 뷰어가 들어 있는 폴더(이 레포 checkout이나 ZIP으로 받은 사본).

**1. 설치 (하네스마다 한 번, 뷰어를 갱신할 때도 같은 명령)** — 이 레포 폴더에서 PowerShell로, 하네스 폴더 경로를 꼭 적는다:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py install --claude C:/내-하네스-폴더
uv run python web/prototypes/visual-viewer/viewer.py install --codex C:/내-하네스-폴더
```

- 뷰어 파일 5개를 `<하네스>/web/prototypes/visual-viewer/`에 복사하고, 훅을 `.claude/settings.local.json`(Claude) 또는 `.codex/hooks.json`(Codex)에 **추가**한다. 기존 설정·다른 훅은 지우거나 순서를 바꾸지 않는다. 설정 파일이 JSON이 아니거나 UTF-8이 아니면(UTF-16·cp949) 아무것도 바꾸지 않고 멈춘다.
- 개발 레포에는 설치하지 않는다(`dev-harness` 폴더로 알아본다. Git checkout이든 ZIP으로 받은 사본이든 같다). 경로를 빼먹으면 오류로 멈춘다.
- 훅 명령에는 개인 경로가 없다. 하네스 기준 상대 경로와 뷰어 파일 SHA-256 지문만 들어 있다. Python 3.12는 uv로 찾는다.
- 한 CLI만 다시 설치해도 공유 뷰어 파일이 바뀌면 이미 등록된 다른 CLI의 항목도 새 지문으로 맞춘다(Codex는 그 뒤 `/hooks`에서 다시 신뢰해야 돈다). 설치 출력에 그렇게 적힌다.
- 설치(재설치 포함) 순간에 이미 있던 export로는 브라우저를 띄우지 않는다. 보려면 아래 4번을 쓴다.

**2. Claude Code** — 하네스 폴더를 기본 작업 폴더로 Claude Code(Desktop의 Code 또는 터미널 `claude`)를 **새로** 열고 질문한다. export가 저장되면 브라우저가 열린다. 훅은 Bash·PowerShell 명령 뒤(PostToolUse) 백그라운드(async)로 돌아 작업을 기다리게 하지 않는다.

**3. Codex** — 하네스 폴더에서 `codex --search`를 연다. 처음 한 번 프로젝트 신뢰를 허용하고, `/hooks`에서 `visual-viewer` 훅(**Stop**, 동기 30초, 명령 `.codex\visual-viewer-hook.cmd codex <지문 4개>`)을 확인한 뒤 신뢰(trust)한다. 신뢰 전에는 실행되지 않는다. 뷰어 파일이 바뀌면(어느 CLI로 다시 설치했든) 명령의 지문이 바뀌므로 `/hooks`에서 다시 신뢰해야 한다. 신뢰 우회 옵션(`--dangerously-bypass-hook-trust`)은 쓰지 않는다. Codex는 반드시 하네스 폴더에서 시작한다.

- Codex 훅은 **답변이 끝날 때(Stop) 한 번** 돈다. 브라우저는 답변이 끝난 뒤 열린다. 셸 명령마다 도는 지연은 없다. 새 export가 없으면 Python을 시작하지 않고 끝난다(아래 실제 검사의 시간).
- 이전 버전(PostToolUse)으로 설치했다면 다시 설치하면 Stop으로 옮겨지고 명령이 바뀌므로 `/hooks`에서 다시 신뢰한다.
- uv나 Python 3.12를 시작하지 못해도 Codex 훅은 exit 0·무출력으로 끝나고(답변을 막거나 이어 가지 않는다) 그 오류는 `hook-start-error.log`에 남는다(마지막 실행분만, 정상 시작이면 빈 파일).
- **Codex는 자동으로 업데이트된다.** 버전에 따라 Windows에서 훅을 실행하는 셸이 바뀐다(0.146: cmd, 0.162.1: PowerShell). Codex·Claude Code를 업데이트한 뒤에는 아래 4번의 `selftest`를 실행하고 `/hooks`에서 훅이 `Trusted`인지 다시 본다.
- **알려진 환경 문제(뷰어와 무관)**: 2026-10-12 이 PC의 codex-cli 0.162.1에서 Windows 샌드박스 "setup refresh had errors"가 났다. 샌드박스 기록에 따르면 Codex 자신의 computer-use 런타임(node_repl) 프로세스가 `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\…\node_repl.exe`를 열어 두어 그 파일의 ACL을 바꾸지 못했다. 그러면 Codex가 모든 명령을 샌드박스 밖에서 실행할지 사용자에게 매번 묻는다. 기획자는 이 경우 질문마다 승인이 필요할 수 있다.

**4. 확인·직접 열기** — 하네스 폴더에서:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py selftest
uv run python web/prototypes/visual-viewer/viewer.py status
uv run python web/prototypes/visual-viewer/viewer.py open --latest
```

- selftest: 등록된 **정확한 훅 명령**을 이 PC의 각 셸(Codex: cmd·Windows PowerShell 5.1·pwsh, Claude: Git Bash·Windows PowerShell 5.1, macOS·Linux: sh·bash)에서 임시 사본과 합성 export로 실행해 셸마다 pass/fail을 보인다. 실제 화면·상태는 건드리지 않고 브라우저·모델을 쓰지 않는다. 없는 셸은 `skip`으로 적는다. CLI를 업데이트했거나 뷰어를 다시 설치한 뒤 실행한다.
- status: CLI마다 `registered`(올바른 이벤트·matcher에 등록), `misplaced`, `files_match_command`(설치 파일·실행기가 명령의 지문과 같음), `view_built`·`up_to_date`, `last_built`, `baseline_only`, `codex_features`·`codex_hooks_disabled`(하네스 설정이 사용자 설정보다 우선), `last_error`·`last_error_file`, 그리고 `cli_versions`(`codex --version`·`claude --version`)와 `version_warnings`(확인한 버전 `tested_versions`가 아니면 selftest·`/hooks` 재확인 안내).
- open --latest: 훅이 없거나 화면을 닫았을 때 가장 최근 export로 화면을 다시 만들고 연다.

**5. 끄기** — 하네스 폴더에서 `uninstall --claude`, `--codex`, `--both` 중 하나. 이 뷰어의 훅(과 Codex 실행기)만 지우고 다른 설정·화면·insights 파일은 남긴다. Codex는 신뢰가 위치(`이벤트:묶음:처리기` 번호)에 묶여 있어서, 뒤에 다른 훅이 있으면 그 번호를 지키는 자리표시를 남긴다: 묶음이면 `{"hooks": []}`, 같은 묶음 안 처리기면 `{"type": "command", "command": ""}`(Codex 시작 때 "skipping empty hook command" 경고가 보일 수 있다). 다시 설치하면 그 자리를 쓴다. Codex는 `/hooks`에서 잠시 끌 수도 있다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py uninstall --both
```

알아 둘 점

- 훅은 업무·모델·Tool을 호출하지 않고 출력이 없다. Codex 훅은 항상 exit 0이다. 훅의 오류는 `runtime-data/visual-viewer/hook-error.log`에, Codex에서 uv·Python이 시작조차 못 한 오류는 같은 폴더의 `hook-start-error.log`에만 남는다.
- 화면(`index.html`, `view-data.js`)·훅 상태·로그·insights는 모두 `<하네스>/runtime-data/visual-viewer/`에 생긴다. 실제 결과이므로 Git·공개 자료에 넣지 않는다.
- 의견 묶음 도넛·구분별 막대·후기 원문 비교는 export에 없는 모델 해석이라 insights 파일(`runtime-data/visual-viewer/insights-<이름>.json`)이 있어야 그린다. 없거나 맞지 않으면 근거 대시보드 맨 위에 기획자용 한 줄 이유가, 맨 아래 접힌 `운영 안내`에 파일 위치·session_id·turn_id가 나온다.

## 파일과 동작

| 파일 | 역할 |
|---|---|
| `index.html` | 뷰어(빌드 결과, 한 파일). 같은 폴더의 `view-data.js`를 읽어 그린다. 로컬 파일로 열면 2초마다 데이터 변경을 확인한다. 직접 고치지 않고 `app/`에서 다시 빌드한다. |
| `app/` | 뷰어 원본(Vite + React + TypeScript + Tailwind 4 + Unovis). `npm run build`가 JS·CSS를 넣은 한 파일을 `../index.html`로 쓴다. 설치는 이 폴더를 복사하지 않는다(`index.html`만 복사). |
| `build_view.py` | export와 insights를 읽어 `view-data.js`(필요하면 단일 HTML 보고서)를 만든다. 판단은 하지 않는다. |
| `hook.py` | Claude Code·Codex 공용 훅. 새 export가 생기면 화면 데이터를 다시 만들고, CLI 세션마다 처음 한 번 브라우저를 연다. |
| `viewer.py` | `install`·`uninstall`·`open --latest`·`status`·`selftest`. Windows Codex용 실행기 `.codex\visual-viewer-hook.cmd`도 설치 때 만든다. |

- Claude Code: PostToolUse `Bash|PowerShell`(async, 60초). 명령은 `uv run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c "<hook.py 찾기·지문 확인·실행>" claude <build_view.py 지문> <index.html 지문>`이고 `CLAUDE_PROJECT_DIR`에서 hook.py를 찾는다(Git Bash·PowerShell은 작업 폴더의 실행 파일을 찾지 않는다).
- Codex: **Stop**(동기, 30초, matcher 없음). openai/codex 소스로 확인했다(rust-v0.146.0·rust-v0.162.1의 `hooks/src/events/stop.rs`): Stop은 두 버전 모두 있고 입력은 `session_id`·`turn_id`·`cwd`·`transcript_path`·`model`·`permission_mode`·`stop_hook_active`·`last_assistant_message`다. **exit 0이고 stdout이 비어 있으면 아무 효과가 없다.** exit 2는 답변을 이어 가게 하고 그 밖의 코드는 "hook exited with code N"으로 보이므로 이 훅은 늘 exit 0·무출력이다. 0.146은 async 훅을 건너뛰고(0.162.1은 지원) 둘 다에서 돌도록 동기로 둔다. 작업 폴더는 세션 폴더다.
- Codex Windows 실행 방식(소스 확인): 0.146.0은 `COMSPEC /C "<명령>"`(raw 인자), 0.162.1은 세션의 사용자 셸로 실행하며 Windows 기본은 PowerShell(`pwsh`가 있으면 pwsh 7, 없으면 Windows PowerShell 5.1)이라 `<셸> -NoProfile -Command <명령>`이다. 세션 셸이 없으면 COMSPEC으로 돌아간다. 샌드박스로 감싸지 않고 세션 환경 변수만 넘긴 채 Job Object 안에서 실행한다. 그래서 `commandWindows`는 두 셸이 똑같이 읽는 `.codex\visual-viewer-hook.cmd codex <hook.py> <build_view.py> <index.html> <실행기> 지문`뿐이고, 셸 문법이 필요한 일은 실행기가 한다:
  1. 작업 폴더 실행 파일 검색을 끈다(`NoDefaultCurrentDirectoryInExePath`, 하네스에 심은 `uv.cmd`·`uv.bat` 무시).
  2. **빠른 길**: `runtime-data\exports`에서 가장 최근 export 이름이 hook.py가 마지막으로 처리한 이름(`runtime-data\visual-viewer\.hook-last-export`)과 같으면 Python 없이 끝낸다. 비교는 지연 확장으로 해서 그 파일 내용이 명령으로 해석되지 않는다. 다르거나 없거나 모르면 Python으로 넘어가므로 새 export를 건너뛰지 않는다. export 파일 이름은 내용 지문이라 이름이 같으면 내용도 같다.
  3. **인터프리터**: `%SystemRoot%\System32`로 옮겨 `uv python find --system --no-config --no-python-downloads 3.12`로 가상 환경이 아닌 Python 3.12(uv 관리 설치 우선, 없으면 시스템 설치)를 찾아 `-I -B`로 직접 실행하고 하네스 경로는 인자로 넘긴다. 하네스의 `.venv`·`.python-version`·`.pth`·`sitecustomize.py`는 쓰이지 않는다. `uv run`은 쓰지 않는다.
  4. hook.py 지문은 인자로 넘겨 Python이 실행 전에 확인한다. 출력은 버리고 시작 오류는 `hook-start-error.log`, 항상 `exit /b 0`. uv가 `.cmd` 껍데기여도 돌아온다.
- Codex macOS·Linux(`command`, sh): 같은 일(빠른 길, `/`에서 `uv python find --system`, 직접 실행, exit 0)을 sh 문법으로 한다.
- `.codex\`는 Codex 샌드박스가 쓰기를 막는 폴더다(샌드박스 기록의 deny ACE). Codex 신뢰 지문은 hooks.json의 명령만 덮지만 명령에 실행기 SHA-256이 들어 있어 설치가 실행기를 바꾸면 다시 신뢰가 필요하다. 실행기 자체는 실행할 때 검사하지 않는다(사용자 권한으로 실행기를 고치면 다시 신뢰 없이 실행된다).
- `hook.py`는 표준 라이브러리만 쓰고 stdout·stderr를 버린다. 새 export만 그리고, 두 번 읽지 못한 export는 로그에 한 번 남긴 뒤 export나 insights 파일이 바뀔 때까지 다시 시도하지 않는다(지문 불일치는 실패로 묶지 않는다). 여러 훅이 동시에 돌면 OS 파일 잠금으로 한 번만 만들고, `open`·`install`의 상태 기록도 같은 잠금을 쓴다. 브라우저를 열기 전에 세션 기록부터 저장해 한 세션에서 두 번 열리지 않게 한다. 출력 폴더의 index.html은 그릴 때마다 지문을 확인한 원본으로 되돌린다.
- 승인된 유효 완료 결과이고 turn 없이 멈춘 요청이 없으면 `한눈에 보기`, 그 밖에는 요청·개요 화면을 먼저 보여준다.

### 보안 범위 (Codex 샌드박스와 함께 쓸 때)

Codex는 신뢰한 훅을 샌드박스 밖에서, 사용자 권한으로 실행한다. 그래서 샌드박스 안의 명령이 바꿀 수 있는 파일을 훅이 실행하면 샌드박스를 벗어나는 길이 된다.

- 막은 길: `hook.py`·`build_view.py`·`index.html` 바꾸기(지문 확인), 하네스 폴더의 `uv.cmd`·`uv.bat`(실행기의 작업 폴더 검색 끄기), 실행기 바꾸기(`.codex\`는 샌드박스가 쓰지 못함), **하네스 `.venv`(어떤 파일이든)·`.pth`·`.python-version`·`sitecustomize.py`·`uv.toml`**(Codex 훅은 System32·`/`에서 가상 환경이 아닌 Python을 찾아 직접 실행), 빠른 길 표시 파일에 명령 넣기(지연 확장 비교). %TEMP%는 쓰지 않는다.
- 남는 범위: 인터프리터는 uv가 고른 가상 환경이 아닌 Python 3.12다(uv 관리 설치 우선). 샌드박스가 쓸 수 있는 폴더가 PATH에 있고 그 안에 가짜 python 3.12가 있으면 이론상 고를 수 있다. 훅은 샌드박스가 쓸 수 있는 `runtime-data`의 export·insights를 읽고(데이터로만) `runtime-data/visual-viewer`에 쓴다. 표시 파일을 고치면 빠른 길이 그리기를 건너뛰게 할 수는 있다(코드 실행은 아님).
- **Claude Code 명령은 그대로 `uv run`을 하네스에서 실행한다**: 하네스에 `.venv`가 있으면 그 Python을 쓴다. Windows의 Claude Code에는 이 경계를 둘 샌드박스가 없고(에이전트 명령이 이미 사용자 권한으로 돈다) 확인한 동작을 바꾸지 않으려고 그대로 두었다.

## 화면 고치기 (app/, Node 필요)

기획자는 Node가 필요 없다. 화면을 고치는 개발자만 Node 20 이상이 필요하다(확인: Node v24.16·npm 11.13).

```powershell
cd web/prototypes/visual-viewer/app
npm ci
npm run build   # 타입 검사 → vite build → scripts/publish.mjs가 ../index.html 한 파일을 쓴다
```

- `publish.mjs`는 `<script src="view-data.js" charset="utf-8"></script>` 태그를 그대로 한 번만 남기는지 확인한다(`--standalone`이 이 태그를 데이터로 바꾼다). 외부에서 불러오는 것은 Pretendard 글꼴 CSS(jsdelivr) 하나뿐이고, 인터넷이 없으면 맑은 고딕 등 시스템 글꼴로 보인다.
- `vite-plugin-singlefile`은 하위 패키지(braces) 취약점 경고 때문에 쓰지 않고 `publish.mjs`가 직접 합친다. 합칠 때 묶어 넣은 패키지의 라이선스 원문(중복 제거)을 `index.html` 끝 주석(THIRD-PARTY NOTICES)으로 붙인다. 의존성은 `package-lock.json`으로 고정한다(`npm audit` 0건).
- **K 업무형(사용자 선택, 2026-10-13~15)**: 뷰어의 하나뿐인 보기(`app/src/dash/`). 작은 글씨, 연회색 메뉴와 연초록 현재 화면, 메뉴의 `빠른 검색`(`/` 또는 Ctrl+K. 빈 검색 창에는 안내 글 없이 입력 칸과 키 안내만 둔다), 위치 줄과 화면 생성 시각, 화면 머리 카드의 아이콘·화면 순서와 `이름 : 값` 정보 줄(범위·불러온 자료·상태), 촘촘한 표(긴 ID·SHA-256·날짜 같은 열은 줄마다 `상세`로 접고 `접힌 열 모두 보기`로 편다), 대조 순서를 잇는 노선 줄과 세로 단계선, 화면 끝 이전·다음 화면 카드, 아래로 내리면 `맨 위로` 버튼. 막대 항목이 7개 이상이면 번호·항목·건수·작은 막대의 표로 보여 준다. 검색 결과를 누르면 그 화면의 해당 위치로 가서 초록 테두리로 알려 준다. P1·R1·C1·근거 ID 칩에 마우스를 올리거나 Tab으로 가면 저장된 원문 전체가 뜬다(`components/idtip.tsx`). 출처·파일 이름·세션 정보는 `출처`·`저장된 결과 파일`·`세션 정보` 표시에 마우스를 올리면 보인다(`components/hovernote.tsx`). `가+`는 글자를 12.5% 키운다. 그리기 전에 화면 쪽 사본만 바꾸고 `build_view.py`의 데이터는 그대로 둔다: 근거 대시보드와 근거 원문을 한 화면으로 합치고(`lib/merge.ts`), 기획 업무에 필요한 것만 남기고(`lib/prune.ts`: 한눈에 보기와 겹치는 후기 선별·기능 대조·제안 화면은 메뉴에서 빠지고 그 화면에만 있던 내용은 다른 화면으로 옮긴다), 합니다체 문장을 보고서체로 줄이고(`lib/voice.ts`, 인용·질문·모델이 쓴 결과 글은 그대로), 보이는 글에서 영어 필드 이름을 빼고(`lib/plain.ts`, 원래 값은 칩 설명·출처·접힌 열에 남는다), 초록 한 가지 색의 단계로 칠한다(`lib/ktone.ts`, 실패·경고는 붉은색·주황색 유지). 참고한 대시보드 그림의 사람 이름·사진·회사 로고·지난주 대비 증감·알림·업그레이드 안내처럼 결과에 없는 것은 넣지 않았다.
- **보고서로 보기(2026-10-15, 사용자 요청)**: K 머리줄의 `보고서로 보기` 버튼은 팀원 신진하가 만든 하네스 결과 보고서 양식(A4 문서형, 요청·범위부터 다음 실행까지의 장과 원자료 목록, `인쇄 / PDF`·`보고서 파일 저장`)을 화면 전체에 연다. 양식 파일은 `app/vendor/jinha-report/`에 받은 그대로 두고(받은 곳·지문은 `SOURCE.md`), `npm run build`가 한 파일 안에 넣는다(`app/scripts/jinha-report.mjs`: 스타일·스크립트를 문서 안에 넣고 호스팅이 덧붙인 스크립트와 외부 주소 링크를 뺀다). `build_view.py`가 `view-data.js`에 export와 지금 화면의 turn_id를 넣고(`report`), 보고서는 그 export를 직접 읽어 K와 같은 결과를 보인다. 보고서는 같은 출처 권한이 없는 격리된 iframe에서 돌아 K 화면과 파일에 닿지 않는다. 보고서 안의 숫자(항목 수·키워드별 언급 건수 등)는 이 양식이 브라우저에서 export로 센다(다른 화면의 숫자는 `build_view.py`가 센다). 이 양식은 export만으로는 그래프를 그리지 않고 보고서 계획(report_plan)의 chart 블록만 그린다. 그래서 그래프 두 개(사용자 선택)는 `build_view.py`가 근거 대시보드와 같은 기준으로 세어 양식의 report_plan 형식으로 넘긴다(`report.plan`): `근거 구성`(근거 종류별 건수, 도넛)과 `제안과 근거 연결`(제안별 source_ids 수, 막대, 연결 수가 효과·우선순위가 아니라는 설명 포함). 무효·취소 turn에는 그래프를 만들지 않는다. 하네스 v0.8+가 `runtime-data/deliverable-metadata/`에 남기는 보고서 계획은 본문 전체를 담고 있어 이 양식에 넣으면 본문이 두 번 나오므로 쓰지 않는다. 사이트 예시의 `불편의 분포`(사용 상황별)는 모델의 후기 분류가 있어야 하는 숫자라 만들지 않는다. 키워드는 띄어쓰기로 자른 낱말이라 조사가 붙은 말(예: `기능은`)과 영어 대명사도 따로 잡힌다. 뷰어 안에서 맞지 않는 `결과 불러오기`(다른 파일을 열면 K와 다른 결과가 된다)·`페이지 링크 복사`(원 사이트 주소)·`예시 다시 보기`·`하네스 결과 연결 방법`(없는 ZIP 링크)은 숨긴다. turn 없이 멈춘 요청 기록만 있는 export에는 버튼이 없다. `index.html`은 약 0.80MB → 0.94MB.
- **K 움직임(2026-10-14, 사용자 요청)**: K 업무형에 다섯 가지 움직임을 넣었다. 첫 화면 아래 블록이 보일 때 한 번 떠오름(0.45초), 핵심 숫자가 제자리로 내려앉음(0.36초, 카드마다 0.05초씩 최대 0.56초. 처음부터 최종 숫자이며 0부터 세지 않는다), 버튼 색 바뀜(0.15초)과 이전·다음 카드 들림·화살표 밀림(0.2초), 펼친 내용 나타남(0.24초), 검색 위치 테두리가 사라짐(0.3초). `prefers-reduced-motion: reduce`이면 모두 꺼지고(스크롤 이동도 즉시), 인쇄에서도 꺼진다. 움직임이 꺼져 있거나 스크립트가 돌지 않으면 아무것도 숨기지 않으며, 건너뛴 블록(End 키·검색 이동)도 바로 보인다. K의 차트는 자라나는 효과 없이 그린다. 규칙은 `index.css`의 "K motion".
- 화면은 `build_view.py`가 만든 블록을 그릴 뿐 세거나 판단하지 않는다. 새 블록(hero·story·claims·matches·flow·solutions·tiles)도 값은 모두 `build_view.py`가 정한다.
- `index.html`이 바뀌면 설치본의 지문도 바뀌므로 하네스마다 다시 설치하고 Codex는 `/hooks`에서 다시 신뢰한다.

## 직접 만들기 (build_view.py)

```
python web/prototypes/visual-viewer/build_view.py --export <하네스 runtime-data/exports의 세션 JSON> --focus dashboard --open
```

- 기본은 이 폴더에 `view-data.js`가 생기고 `index.html`이 열린다. `--out-dir 폴더`를 주면 그 폴더에 `view-data.js`와 `index.html`을 둔다.
- `--standalone 경로 --mode ops`: K 업무형의 공유용 단일 HTML을 만든다. `--mode ops`는 기존 설치 호출과의 호환 옵션이며 화면은 K 업무형 하나다.
- `--standalone 경로`: 데이터를 넣은 단일 HTML. `--insights 파일`: 모델이 쓴 해석(의견 묶음·단계 자막·제외 사유 등). insights는 현재 export의 전체 `web_binding`을 `binding`으로 포함해야 적용한다. 세션·turn만 맞거나 검토된 현재 웹 전달이 없으면 직접 지정해도 적용하지 않는다. insights 없이도 결과 구조만으로 모든 화면을 그린다.
- **웹 전달 파일(`product-web-result-v1`, 하네스 product v0.11+)**: 하네스가 검토 결과를 저장하면 `runtime-data/web-deliveries/web-<SHA-256>.json`도 쓴다. export가 `<하네스>/runtime-data/exports`에 있으면 build_view·훅이 옆 폴더에서 현재 export의 전체 `web_binding`과 저장 검토가 일치하는 파일을 찾아 함께 읽는다. 파일 이름이 내용의 SHA-256과 다르거나(경고), 결과가 지금 보여 주는 결과와 다르면(내보내기 화면에 안내) 쓰지 않는다. 읽으면 근거 원문 화면에 `등록 원문 전체`(선택한 등록 원문 모두와 결과 인용 여부, 전달·검토·제외 건수), 업무 기록 화면에 `조사 과정`(업무 시계·조사 계획·자료 훑기·분석 범위·조사 멈춤과 접근하지 못한 자료), 내보내기 화면에 `웹 전달 파일`(경로·SHA-256·결과·자료 버전)을 더한다. `--export 현재-export.json --web-result 파일 --web-result-sha256 바이트SHA256`으로 명시할 수 있다. 현재 저장 검토·결과 버전·코드·자료·문맥·조사 지문을 대조하기 위해 `--export`가 필요하다. 웹 파일만으로 현재 결과를 만들지 않는다. 원문·페이지 이름은 글자로만 보여 주고 링크는 HTTPS만 건다. 파일의 `html_rendering`(웹 팀 몫, 하네스가 하지 않음)·`content_is`(믿지 않는 글, 실행하지 않음)를 따르며, 이 표시도 의미 검토나 화면 검수가 아니다.
- 생성물(`view-data.js`, `report-*.html`, `*.tmp`, 훅 상태·로그)과 실제 결과의 insights는 이 폴더의 `.gitignore`로 제외한다. 실제 결과 예시는 Git이 아닌 메일·접근 제한 링크로 공유한다.

## 화면과 표시 원칙

한눈에 보기 / 요청·개요 / 근거 대시보드 / 후기 선별 / 기능 대조 / 제안 / 업무 기록 재생 / 근거 원문 / 내보내기의 9개 화면이다(화면 데이터 기준. K 업무형은 근거 대시보드와 근거 원문을 한 화면으로 합치고 후기 선별·기능 대조·제안을 메뉴에서 빼서 5개 화면을 보인다). [웹 연결 계약](../../../docs/contracts/team-web-kitchen.md)에 맞춰 다음을 표시한다.

- 모든 화면: `저장된 실행 결과`, 상태(`기획 초안 완료`·수정 필요·보류·입력 필요·조사 필요·진행 중·실패·취소), `유효`/`무효`(valid), `의미 검토 전 · 인수 전`(semantic_status unverified·acceptance_ready false), 합성 자료면 `합성 시험 자료`(보여줄 결과가 없어도 모든 후보·자료 버전에서 찾아 표시), 화면 생성 경고 수.
- 기획자 말: 사이드바 칩·자막·지표 설명은 한국어로만 쓰고 원래 값(`status: completed` 등)은 마우스를 올리면 보이는 설명(tip)에 둔다. 표·내보내기 화면처럼 자세한 곳은 `기획 초안 완료(completed)`처럼 원래 값을 함께 적는다. 파일 경로·session_id·turn_id·명령은 접힌 운영 안내와 세션 정보에만 둔다.
- **현재 결과는 저장 도구가 승인한 결과(`state.latest_result`)뿐이다.** 거절 후보(`validation.contract_valid=false`·`error`)는 현재 결과·제안으로 그리지 않고 업무 기록의 후보 표에 `거절 · <code>`와 사유(error·review.findings)로 남긴다. 승인된 결과가 없으면 근거·대조·제안 화면은 비우고 이유를 적는다. 내보내기의 저장 검사는 보여주는 결과의 검사, 없으면 마지막 후보의 검사를 `(마지막 거절 후보)`·`(마지막 저장 후보 · 현재 결과 아님)`·`(저장된 후보 없음)`으로 구분해 보인다.
- **turn 없이 멈춘 요청(needs_input·research_required·held 등)은 모두 상태 맨 앞과 요청·개요 맨 위에 보인다.** export에는 요청 시각이 없고 requests 순서도 시간 순서가 아니다. prior_turn_id가 마지막 turn인 요청만 `마지막 turn 뒤`라고 쓰고, 나머지는 `순서 미확인`으로 적는다. 어느 요청이 최신인지 고르지 않으며 이전 turn은 `마지막 turn …`으로 표시한다.
- 취소는 `state.cancellation`의 사유·취소 전 상태를 적고, 실행 중단은 확인되지 않았다고 표시한다. 모델이 쓴 `cancelled` 결과는 그 결과의 사유를 적는다.
- 무효 turn은 `invalidation_reason`을 그대로 적고, 무효 직전에도 승인 결과였던 것만 `무효 처리된 결과` 표시와 함께 보여준다(모든 결과 화면·후보 표·저장 검사). 그 뒤 거절된 후보가 있었으면 승인 결과가 없던 것으로 본다.
- turn 순서는 export의 순서(created_at)를 그대로 쓴다. 후보가 없는 turn도 제자리에 둔다.
- product_family의 냉장고·전자레인지·식기세척기는 한국어 표시명이다. 다른 제품군도 원래 식별자를 읽기 좋은 이름으로 표시하며, 이 세 제품군을 허용 목록으로 사용하지 않는다. 제품군 요청(scope_mode `family_catalog`)은 `냉장고 제품군 N개 모델`로 쓰고 model_scope 전체와 결과 근거 모델을 보여준다. 요청·개요의 큰 글씨 칸에는 짧은 값만 둔다: 모델은 결과 근거 모델이 하나면 그 모델, 아니면 `N개`, 범위는 `제품군`·`모델 지정`이고 원래 이름(`제품군 카탈로그`)은 설명 줄에 둔다. 긴 값은 글씨를 줄이고 한국어 낱말 중간에서 줄을 바꾸지 않는다. 자료 버전과 model_scope 원문을 바꾸지 않는다. 사용자가 뺀 불편(`constraints.exclude_pains`)을 요청 조건에 보인다.
- 불편→기존 기능→남은 불편→제안을 원문 ID로 연결한 열로 보여준다. 열 사이 화살표는 업무 순서이며 항목 간 관계는 assessment의 feature_matches·concept_links에 적힌 것만 표시한다.
- concept의 `implementation_steps`·`validation_plan`을 표시하고 없으면 `미작성`, `planned_not_measured`는 `검증 계획 · 실측 전`으로 둔다.
- v0.7.0의 `decision_notes`는 요청·개요 화면에 `판단 메모`(D1…)로 보여준다. basis는 `원문 사실`·`AI 해석`·`미확인`으로 옮기되 모델이 붙인 라벨이며 공식 인용·의미 검증이 아니라고 적는다. 근거 원문 표의 연결 항목에도 D 번호가 붙는다.
- 근거 유형: 근거에 `kind`(evidence_refs 또는 origin)가 있으면 그 값을 먼저 쓴다(review=후기, product_fact=제품 사실, manual=설명서, spec=스펙, part=소모품, document=문서, 그 밖의 값은 `미지원(값)`이고 후기로 세지 않는다). v0.7.0 export에는 kind가 없다(이슈 #8). 그때는 source_id 접두어(REVIEW·REV=후기, MANUAL=설명서, SPEC=스펙, PART=소모품, DOC=문서)로 나누고, 관례가 아니면 원문 표현(`factual_summary`=제품 사실, `excerpt`=원문 발췌)으로만 나눈다. 원문 발췌를 후기라고 단정하지 않는다. 후기로 분류된 근거가 없고 종류를 모르는 근거만 있으면 대시보드 지표는 `후기 근거 미확인` 대신 아는 것만 `원문 발췌 N건 · 후기인지 기록 없음`(회색)으로 쓰고, 유형 차트 아래에 쉬운 말로 이유를 적는다.
- 근거: source_id·인용·원문 발췌/사실 요약·위치·모델 범위·게시/관측일·구매/협찬(null은 미확인)·상업 고지(commercial_disclosure)·SHA·HTTPS 링크. export 경로는 `runtime-data/exports/<파일>`로만 보여주고 개인 절대 경로를 넣지 않는다.
- 구조 검사와 `planning_detail_complete`(필드 존재 검사)를 의미 품질 통과로 표시하지 않는다.
- 사용량: 기록이 없거나 미측정 호출이 섞이면 0으로 그리지 않고 차트를 생략한다. 합계가 일부 호출만이면 `부분 합계 · N건 중 M건 미측정`으로 적는다. 누적 값을 다시 더하지 않는다.
- 근거 대시보드는 insights 없이도 결과에 적힌 것만 센다: 검토 기록의 대조 판단(feature_matches의 resolution), 항목별 근거 확인(claim_checks의 support_status·모델 불명확), 제안 연결(concept_links), 출처 사이트(HTTPS source_url의 사이트 이름), 유형, 모델 연결 방식·게시일·수집일, 항목별 연결 근거. 검토 기록은 모델이 쓰고 저장 도구가 형식만 검사한 것이라고 적는다. 항목 종류(현재 불편·기존 기능·남은 불편·제안)는 ID 접두어가 아니라 결과의 어느 목록에 있는지로 정한다(v0.7.0 ID는 E1·R1·pain-tones처럼 관례가 없다). 비율·발생률·의견 묶음은 만들지 않는다.
- 한눈에 보기: 맨 위 숫자는 결과의 항목 수(근거·현재 불편·남은 불편·제안)이고, 불편·기능 카드의 인용은 그 항목의 근거 앞 2건을 저장된 그대로 보인다(나머지는 건수만). 연결도의 선은 검토 기록의 feature_matches(불편→남은 불편, 판단 라벨)와 concept_links(남은 불편→제안)에 적힌 것만 그리고, 같은 연결을 카드 안에 글자(`→ R1 · 불확실`)로도 적는다. 연결이 없는 항목은 선 없이 둔다. 제안 카드는 요구사항·구현 단계·검증 계획(`실측 전`)을 보이고 없으면 `미작성`이다. 마지막 `한계` 칸은 뒷받침된 항목 수, 모델 불명확 근거, 출처 사이트, 후기 여부 미기록, 의미 검토 전, 사용량 미측정을 보인다. 승인된 결과가 없으면 이 화면을 비우고 이유를 적는다. 살짝 올라오는 움직임과 C의 연결선 빛 효과는 꾸밈이며(인쇄·움직임 줄이기 설정이면 끔) 값을 바꾸지 않는다. 투명도·흐림을 쓰지 않고 숫자도 처음부터 실제 값이라, 효과가 멈춘 환경(인쇄·자동 캡처)에서도 내용이 그대로 보인다.
- insights의 의견 묶음은 `모델 해석`으로 표시하고 건수는 ID 목록 길이로 센다. 붙인 insights 파일 이름과 붙인 근거(turn_id 일치 등)를 대시보드에 적는다. 관측 건수를 발생률·시장 수요로 표시하지 않는다.
- 업무 turn이 없는 export는 요청 기록 화면만 만들고 요청마다 멈춘 이유(response.reason·events)를 보인다. 상태가 섞이면 한 상태로 안내하지 않는다.

## insights 형식

숫자는 가능한 한 source_id 목록으로 주고 건수는 스크립트가 센다. 최상위에 `session_id`와 `turn_id`(그 해석을 쓴 turn), 현재 export의 전체 `web_binding`을 복사한 `binding`을 넣는다. 훅·`open --latest`는 현재 검토된 웹 전달과 같은 binding인 파일만 적용한다. 다른 turn용이거나 가리키는 근거 ID가 현재 결과에 없거나 형식이 아래와 다르면 쓰지 않고 이유를 화면에 적는다. 고정 숫자에 `"verify_in": "assumptions"`를 주면 결과 원문에 그 숫자가 있는지 확인하고, 없으면 그 숫자를 그리지 않고 경고한다. UTF-8 BOM이 있어도 읽는다.

- `groups`: `[{key, label, tone, source_ids}]` 의견 묶음. 도넛·구분별 막대·원문 비교에 쓰인다.
- `facet`: `{title, order, values: {source_id: 구분값}}` 묶음을 나눌 구분(가구 구성 등).
- `kpis`, `funnel`: 항목마다 `value`(고정 숫자), `group`(묶음 건수), `evidence: "all"`, `evidence_prefix: "REVIEW"` 중 하나. funnel은 `label` 필수.
- `excluded`(`kind`·`ids`·`text`), `feature_tags`, `node_titles`, `concept_titles`, `concept_steps`(제안 원문과 글자까지 같아야 하며 다르면 그리지 않음), `unresolved`, `usage_note`, `captions`(화면 id별 `{title, text}`).
- `summaries`: `{항목 ID: 짧은 요약}` 모델이 쓴 항목별 요약(현재 불편·기존 기능·남은 불편·제안). 현재 결과에 있는 ID에만 붙는다. K 업무형은 카드·연결 차트·제안에 이 요약을 `요약` 표시와 함께 보이고, 저장된 원문 전체는 `전체 보기/접기` 버튼(키보드 포함)이나 ID 칩에서 확인한다(요약이 없으면 원문의 첫 문장을 자르지 않고 통째로 `첫 문장` 표시와 함께 보인다. 문장 중간에서 잘라 `…`로 끝내지 않는다, 2026-10-15 사용자 요청). 카드가 짧고 깔끔하게 끝나려면 모델이 이 요약을 써야 한다. 요약은 원문을 대신하지 않는다.
- `pages`: 모델이 블록을 직접 쓴 화면. `[{id, nav, icon, title, caption: {title, text}, blocks: [...]}]`

## 실제 검사 (2026-10-12, Windows 11, Python 3.12)

- origin/main `99576f0`(제품 v0.7.0 기록)을 이 브랜치에 로컬 병합한 상태에서 실행했다.
- **사용자 실제 확인(이전 커밋 db56d77)**: Claude Code 2.1.289와 Codex 0.162.1(`.codex` 실행기, 그때는 PostToolUse)에서 실제 질문 뒤 화면이 열렸다. 이번 Stop·빠른 길·인터프리터 변경 뒤 실제 대화 확인은 다시 해야 한다.
- `tests/web/test_visual_viewer.py` 54개(이 PC에 없는 pwsh 시험 1개는 이유를 적고 건너뜀): 실제 product-tools 저장·export 경로로 테스트 시점에 만든 **합성 시험 export**(`[합성 시험 자료]` 표시)로 세 제품군 완료, 보류, 거절 1회·3회, 승인 뒤 거절, turn 없는 후속(prior=마지막 turn·이전 turn·없음), turn 없는 요청 2건, 사용량 미측정·일부 측정, 제품군 카탈로그, 제외 조건·취소·진행 중 turn, 거절 뒤 취소, 보류 뒤 취소, 모델이 쓴 취소 결과, 무효 처리, 입력 필요, 합성 카탈로그(승인·거절)를 확인했다. 훅·설치 쪽은 새 export 판별·세션당 한 번 열기·표시 파일·BOM·형식이 틀린 insights·turn_id 없는 insights·재시도·OS 잠금·지문이 다른 파일 미실행과 로그, Codex Stop 등록·이전 PostToolUse 항목 이동, 위치 보존(묶음·처리기), 다른 CLI 재고정, 재설치 기준점, 개발 레포 사본 거부, UTF-16/cp949 거부, `[features] hooks` 우선순위, CLI 버전 경고, selftest(통과·실패)를 포함한다.
- 설치된 정확한 명령: Claude 명령을 cmd·Git Bash·Windows PowerShell 5.1로, Codex `commandWindows`를 0.146과 같은 `COMSPEC /C "<명령>"`와 0.162.1과 같은 `powershell.exe -NoProfile -Command <명령>`로, Codex `command`를 Git Bash의 sh로 실행해 exit 0·stdout/stderr 0바이트, 새 export 재생성, 빠른 길(새 export가 없으면 바꾼 hook.py도 실행되지 않음), 새 export는 빠른 길이 건너뛰지 않음, 하네스에 심은 `uv.cmd`·표시 파일 명령 미실행, 실패하는 uv·uv 없음에서도 exit 0과 `hook-start-error.log`, hook.py·build_view.py 지문 불일치와 깨진 export가 `hook-error.log`와 status `last_error`에 남음을 확인했다.
- **.venv 경로**: 하네스에 `uv venv`로 만든 `.venv`의 `site-packages\zz_probe.pth`, `.python-version`(3.11), `sitecustomize.py`를 심었다. 대조로 이전 방식(`uv run --no-project --python 3.12`를 하네스에서)은 `.pth`를 실행했다. Codex 명령(cmd·Windows PowerShell 5.1·sh)은 `VIRTUAL_ENV`가 그 `.venv`를 가리켜도 하나도 실행하지 않고 화면을 만들었다. `uv python find --system`은 작업 폴더·상위 폴더의 `.venv`와 `VIRTUAL_ENV`를 모두 건너뛰었다.
- 로컬 codex-cli 0.162.1에 `codex app-server`의 `hooks/list`만 보내(임시 폴더, 격리한 CODEX_HOME, 모델 호출 없음) Stop 항목(`:stop:0:0`, 동기 30초, Windows 명령 `.codex\visual-viewer-hook.cmd codex …`)이 경고 없이 발견되고, 이전 PostToolUse 항목이 Stop으로 옮겨지는 것을 확인했다. 앞선 검사에서 0.146.0·0.162.1의 `commandWindows`·위치별 신뢰 유지·`modified` 재신뢰·`[features] hooks` 우선순위를 확인했다.
- 시간(셸 포함, 이 PC): 셸 명령마다 도는 비용은 없다(Stop). 답변 끝에 새 export가 없을 때 cmd 약 0.15초, Windows PowerShell 5.1 약 0.7초(대부분 PowerShell 자체 시작), 새 export를 그릴 때 cmd 약 1.1초·PowerShell 약 1.6초. 예전 PostToolUse는 셸 명령마다 약 0.65초였다.
- 확인한 버전(`viewer.py status`의 `tested_versions`): Codex 0.162.1(실행 방식·hooks/list·실행기, 이전 커밋 실제 대화), 0.146.0은 소스로 Stop·실행 방식을 확인. Claude Code 2.1.289.
- 이전 기록: 로컬 export 5개(Git 제외)와 헤드리스 Edge 1280px 8개 화면, 375px 가로 넘침 없음은 이 변경 전 버전에서 확인했다.

## 남은 제약

- Stop·빠른 길·인터프리터 변경 뒤의 실제 Claude Code·Codex 대화 확인과 Codex 샌드박스 권한에서의 브라우저 열기는 사용자 확인 전이다. macOS·Linux는 시험하지 않았다(Codex `command`는 Git Bash의 sh로만 확인). pwsh 7은 이 PC에 없어 직접 실행해 보지 못했다(selftest가 있으면 실행한다). Windows에서 Codex 사용자 셸을 Git Bash로 바꾸면 실행기 경로(`.codex\…`)를 읽지 못한다.
- 위 "보안 범위"의 남는 범위(PATH의 가짜 python, runtime-data 데이터, Claude 명령의 `.venv`).
- Claude 명령은 셸이 Git Bash·PowerShell 중 무엇일지 몰라 감싸지 않았다. uv·Python 3.12가 없으면 async 훅이 0이 아닌 코드로 끝나며, Claude Code가 이를 어떻게 보이는지는 확인하지 않았다.
- CLI 업데이트로 훅 실행 방식이 또 바뀔 수 있다. 확인한 버전 밖이면 status가 경고하고, selftest로 이 PC의 셸에서 다시 확인한다(실제 CLI의 실행 방식 자체를 대신하지는 않는다).
- 관리자 `requirements.toml`·managed 설정의 Codex hooks 끄기는 status가 확인하지 않는다.
- 제품 ZIP에는 아직 들어 있지 않다. 지금은 레포 checkout이나 ZIP 사본에서 하네스로 설치한다.
- `tests/web`는 레포 CI(`check.yml`)에 아직 없다. 넣을 때 uv 설치 단계가 없으면 실제 uv를 쓰는 시험은 이유를 적고 건너뛴다(메모 참고).
- 브라우저에서 export 파일을 직접 고르는 기능이 없다(view JSON 끌어 놓기만 지원).
- 동일 작성자 후기 중복은 export에 작성자 정보가 없어 자동으로 판별하지 않는다. insights나 검토 메모에 적힌 경우만 보인다.
- 실제 native 관찰(observer) 연결, 실시간 Tool 사건, 웹에서 질문 실행은 범위 밖이다.

### 통합 보고서의 현재 결과 경계

보고서로 보기는 현재 저장 검토와 전체 `web_binding`·불변 웹 파일 SHA가 일치한 결과가 있을 때만 제공한다. 보고서 입력에는 그 turn만 남겨 다른 turn의 미검토 후보를 고를 수 없게 한다. 결과와 인용 refs는 저장된 그대로 전달하고, 선택한 등록 원문 전체(인용 안 한 자료 포함)·coverage·저장 검토·조사 이력·전체 validation_plan은 별도 구역에 보존한다. 기본 키워드 집계는 결과의 인용 범위이며 선택 원문 전체 건수나 고객 수가 아니다. 취소·무효·미검토·현재 전달 누락 상태에는 보고서 입력을 만들지 않는다. 원본 vendor 파일은 변경하지 않는다. 실제 브라우저·인쇄 화면 검수는 코드/빌드 검사와 별도다.
