2026-10-12 최신 상태: PR #6의 bdb187b Stop 실제 성공은 작성자 댓글 보고입니다. 아래 미확인/push 전 문구는 과거 이력이며 제품 통합의 독립 검사는 별도로 기록합니다.

# 결정 요청: 시각자료 뷰어를 main·제품 ZIP에 넣을지

2026-10-12 · 작성 최길웅(Claude Code 보조) · 받는 사람 **정이량**(릴리스), **황대겸**(웹 PM)

## 결정할 것

1. **대겸**: PR #6의 `web/prototypes/visual-viewer`를 웹 PM 결정으로 main에 **참고 시제품**으로 병합할지. `web/`의 기술·구조는 PM 결정 사항이다.
2. **이량**: 다음 제품 릴리스 ZIP에 뷰어 5파일(`index.html`, `build_view.py`, `hook.py`, `viewer.py`, `README.md`)을 **선택 설치물**로 넣을지.

## 사실 (2026-10-12 기준)

- PR #6 브랜치에 origin/main `99576f0`(제품 v0.7.0 기록)을 병합했다. db56d77까지 push됐고, 이번 변경(Codex Stop·빠른 길·인터프리터·selftest)은 로컬 커밋이다. push는 사용자 승인 뒤에 한다.
- 뷰어는 저장된 export를 읽어 그리기만 한다. 업무 Agent·Skill·Tool·계약·자료, `skills/manifest.json`, 제품 doctor 대상 파일은 바꾸지 않았다.
- 훅(`hook.py`)은 표준 라이브러리만 쓰고 stdout·stderr가 없다. 업무·모델·Tool을 호출하지 않는다. Codex 항목은 uv·Python이 시작하지 못해도 exit 0·무출력으로 끝나도록 실행기로 감쌌다(Stop에서 exit 2면 Codex가 답변을 이어 가게 하고, 그 밖의 코드는 "hook exited with code N"으로 보인다). 오류는 하네스의 `runtime-data/visual-viewer/hook-error.log`에, Codex에서 uv·Python이 시작하지 못한 오류는 같은 폴더의 `hook-start-error.log`에만 남는다(status `last_error`는 둘 중 최근 것을 보인다).
- 설치(`viewer.py install --claude|--codex <하네스>`)는 하네스의 `.claude/settings.local.json` 또는 `.codex/hooks.json`에 항목을 **추가**만 하고 다른 훅의 위치도 바꾸지 않는다(Codex 신뢰 키가 위치 기반이라서). 명령에는 개인 절대 경로가 없고 뷰어 파일(Codex는 실행기까지)의 SHA-256이 들어 있어, 파일이 바뀌면 실행하지 않고(로그에 남김) Codex는 다시 신뢰를 요구한다. 한 CLI만 다시 설치해도 다른 CLI의 등록 항목을 새 지문으로 맞춘다. 개발 레포(.git이 없는 ZIP 사본 포함)에는 설치하지 않는다.
- **Codex 훅은 답변 끝(Stop)에 한 번, 동기로 돈다.** openai/codex rust-v0.146.0·rust-v0.162.1 소스(`hooks/src/events/stop.rs`)로 확인했다: Stop은 두 버전 모두 있고, 입력은 `session_id`·`turn_id`·`cwd`(세션 폴더)·`transcript_path`·`model`·`permission_mode`·`stop_hook_active`·`last_assistant_message`이며, exit 0·빈 stdout이면 아무 효과가 없다(exit 2는 답변을 이어 가게 한다). 0.146은 async 훅을 건너뛰므로("async hooks are not supported yet") 동기로 둔다. 그래서 **셸 명령마다 생기던 약 0.65초 지연이 없어졌고 브라우저는 답변이 끝난 뒤 열린다.** 새 export가 없으면 실행기(.cmd)가 Python을 시작하지 않고 끝낸다: cmd 약 0.15초, 0.162.1처럼 Windows PowerShell 5.1로 부르면 PowerShell 시작을 포함해 약 0.7초(답변마다 한 번). 새 export를 그릴 때 약 1.1~1.6초. 실행기는 가장 최근 export 이름이 hook.py가 남긴 표시와 다를 때·모를 때는 늘 Python으로 넘어가므로 새 export를 건너뛰지 않는다. **Codex는 자동 업데이트된다**: 0.146.0→0.162.1에서 Windows 훅 실행 셸이 cmd에서 PowerShell로 바뀌었다(소스 확인). 그래서 Windows 명령은 두 셸이 똑같이 읽는 `.codex\visual-viewer-hook.cmd codex <지문 4개>`뿐이다. 새 `viewer.py selftest`는 등록된 정확한 명령을 이 PC의 cmd·Windows PowerShell 5.1·pwsh(있으면)·Git Bash(Claude)에서 임시 사본·합성 export로 실행해 셸마다 pass/fail을 보이고, `viewer.py status`는 `codex --version`·`claude --version`이 확인한 버전(Codex 0.162.1, Claude Code 2.1.289) 밖이면 경고한다. CLI 업데이트 뒤에는 selftest와 `/hooks`를 다시 확인한다. 이번 변경으로 Codex 명령이 바뀌므로 `/hooks`에서 다시 신뢰해야 한다. Claude 훅은 확인된 async PostToolUse 그대로다.
- codex-cli 0.146.0과 0.162.1에 `codex app-server`의 `hooks/list`만 보내(임시 폴더·격리한 CODEX_HOME·모델 호출 없음) 동기 훅과 Windows용 `commandWindows`가 경고 없이 발견되고(0.162.1에서 Stop 항목 `:stop:0:0`, 이전 PostToolUse 항목은 재설치 때 Stop으로 옮겨짐), 해제·재설치 뒤 다른 묶음의 훅과 같은 묶음 뒤쪽 처리기의 신뢰가 유지되며, 뷰어 갱신 뒤 `modified`가 되고, 프로젝트 `[features] hooks`가 사용자 설정보다 우선하는 것을 확인했다. 실제 대화: db56d77(PostToolUse·실행기)에서 Claude Code 2.1.289와 Codex 0.162.1 모두 질문 뒤 화면이 열렸다(사용자 확인). 이번 Stop 버전의 실제 대화 확인은 아직이다.
- **보안 범위**: Codex는 신뢰한 훅을 샌드박스 밖에서 실행한다. 스크립트 변경은 지문으로, 하네스에 심은 `uv.cmd`·`uv.bat`은 실행기의 `NoDefaultCurrentDirectoryInExePath`로, 실행기 변경은 `.codex\`(샌드박스 쓰기 금지)와 명령 속 지문으로 막는다(실행 때 자체 검사는 하지 않는다). **하네스 `.venv` 경로를 닫았다**: Codex 훅은 `%SystemRoot%\System32`(macOS·Linux는 `/`)에서 `uv python find --system --no-config --no-python-downloads 3.12`로 가상 환경이 아닌 Python 3.12를 찾아 `-I -B`로 직접 실행하고 하네스 경로는 인자로 넘긴다. 하네스에 `.venv`(`.pth` 포함)·`.python-version`·`sitecustomize.py`를 심은 시험에서 이전 방식(`uv run`)은 `.pth`를 실행했고 새 Codex 명령(cmd·PowerShell 5.1·sh)은 하나도 실행하지 않았다. %TEMP%는 쓰지 않고, 빠른 길 표시 파일은 지연 확장으로 비교해 명령으로 해석되지 않는다. 남는 범위: (1) uv가 고르는 가상 환경이 아닌 Python 3.12(uv 관리 설치 우선)이므로, 샌드박스가 쓸 수 있는 폴더가 PATH에 있고 거기에 가짜 python 3.12가 있으면 이론상 고를 수 있다. (2) 훅은 runtime-data의 export·insights를 데이터로 읽고, 표시 파일을 고치면 그리기를 건너뛰게 할 수 있다(코드 실행은 아님). (3) Claude 훅 명령은 확인된 동작을 바꾸지 않으려고 하네스에서 `uv run`을 그대로 쓰므로 하네스 `.venv`를 쓴다(Windows Claude Code에는 이 경계를 둘 샌드박스가 없다). 샌드박스를 엄격한 보안 경계로 쓰는 환경이라면 (1)을 위해 PATH를 점검하거나 Codex 훅을 끈다(README "보안 범위").
- 화면·insights·로그는 `runtime-data/`에만 생긴다(레포·제품 `.gitignore` 제외 대상). 테스트는 실행 중에 만드는 `[합성 시험 자료]` export만 쓴다. 실제 결과는 Git에 없다.
- 대겸의 PR #7(`codex/local-harness-web`)은 **사용자 결정으로 쓰지 않았다.** 코드를 가져오거나 옮기지 않았다.
- 독립 리뷰 두 차례(23건, 재검증 15건)의 지적을 반영했다: 거절 후보를 현재 결과로 보이던 문제, turn 없는 요청(순서를 지어내지 않음), 취소·무효 사유, 미측정 사용량, 제품군 범위, insights의 turn 구분과 경고 표시, 다른 CLI 지문 재고정, Codex 명령 보강 등. 이번 변경(Stop·빠른 길·인터프리터·버전 경고·selftest)에는 새 시험을 더했다. 검사: `tests/web` 54개(이 PC에 없는 pwsh 시험 1개는 건너뜀)와 레포 CI 4개 명령을 로컬 Windows·Python 3.12에서 실행해 모두 exit 0이다. 원격 CI는 계정 결제 제한으로 시작되지 않으므로 로컬 결과만 있다.

## 선택지

| 안 | 내용 | 필요한 일 | 위험 |
|---|---|---|---|
| A | main 병합만, ZIP 제외 | PM 승인 후 PR #6 병합 | 기획자가 레포 checkout을 받아야 설치 가능 |
| B | main 병합 + ZIP에 선택 설치물 | `scripts/build-product-manifest.py`로 `skills/manifest.json`의 shared_files에 5파일 추가, 제품 README에 설치 한 단락, 새 minor 릴리스 | ZIP 파일 수·지문 변경, 릴리스 계약의 제품 범위 해석 필요 |
| C | 보류 | 없음 | 시연·기획자 사용 시 수동 `build_view.py` 실행 |

**권장: B, 단 훅은 기본 미등록.** ZIP에 들어가도 `viewer.py install`을 직접 실행해야만 훅이 생기므로 기존 업무 실행 방식은 그대로다. 저장 결과 재생은 제품 사용 범위(결과 확인)에 해당한다고 보지만, [릴리스 계약](../../../docs/contracts/product-release.md)의 "제품 파일" 해석은 이량이 판단한다. Codex 훅은 이제 답변 끝에 한 번만 돌고 하네스 `.venv` 경로도 닫았다. 다만 Codex가 자동 업데이트로 실행 방식을 바꿀 수 있으므로 시연·배포 안내에 업데이트 뒤 `selftest`·`/hooks` 확인을 넣기를 권한다. 시간이 부족하면 A로 병합하고 B는 다음 버전으로 미룬다.

## B를 고르면 할 일

1. 대겸 승인 후 PR #6 병합(웹 PM 범위).
2. 이량: manifest·제품 README 갱신, `check-product-assets.py`와 제품 테스트의 파일 수 기대값 확인, 새 제품 버전(호환 기능 추가라 minor) 발행 절차 진행.
3. `check.yml`에 `python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/web -v` 한 줄 추가. 실제 uv로 명령을 돌리는 셸 시험은 uv가 있어야 하므로 `astral-sh/setup-uv` 단계도 함께 넣는다(없으면 이유를 적고 건너뛴다). Windows runner에서만 도는 시험도 있다.
4. 시연 PC에서 미리 아래 확인 절차를 끝내고 Codex `/hooks` 신뢰를 해 둔다. 시연 전에 CLI가 업데이트됐으면 `viewer.py selftest`와 `/hooks`를 다시 확인한다.

## 확인 절차 (실제 CLI 개통, 사람이 실행)

새 폴더 `C:\lgax-verify`(상위에 `.git` 없음)에서 PowerShell로 진행한다.

```powershell
New-Item -ItemType Directory C:\lgax-verify
gh release download product-v0.7.0 -R 2026-LG-kitchen-chicken-team/lg-ax-harness -p lg-ax-harness-product-v0.7.0.zip -D C:\lgax-verify
Get-FileHash C:\lgax-verify\lg-ax-harness-product-v0.7.0.zip -Algorithm SHA256
Expand-Archive C:\lgax-verify\lg-ax-harness-product-v0.7.0.zip C:\lgax-verify\codex
cd C:\lgax-verify\codex
uv sync --locked
uv run python product-doctor.py
uv run python adapters/claude/install.py --target C:\lgax-verify\claude
cd C:\lgax-verify\claude
uv sync --locked
uv run python product-doctor.py
cd <PR #6 checkout 폴더>
uv run python web/prototypes/visual-viewer/viewer.py install --codex C:/lgax-verify/codex
uv run python web/prototypes/visual-viewer/viewer.py install --claude C:/lgax-verify/claude
cd C:\lgax-verify\codex
codex --version
uv run python web/prototypes/visual-viewer/viewer.py selftest --codex
cd C:\lgax-verify\claude
claude --version
uv run python web/prototypes/visual-viewer/viewer.py selftest --claude
```

해시는 `89EBA6307A7411AEFCEB79868F161BCAB369EEECFCA29ECDF3079A751CECFAE5`여야 한다. selftest는 `"ok": true`이고 셸마다 `pass`여야 한다(이 PC에 없는 셸은 `skip`). 실제 화면·상태·브라우저·모델은 쓰지 않는다.

- **Claude**: `C:\lgax-verify\claude`를 기본 작업 폴더로 Claude Code를 새로 열고 질문 하나(예: "전자레인지 사용 불편을 실제 리뷰에서 찾아 개선안을 제안해 줘.")를 한다. 답이 끝나 export가 저장되면 브라우저에 `runtime-data/visual-viewer/index.html`이 열려야 한다.
- **Codex**: `cd C:\lgax-verify\codex` 후 `codex --search`. 폴더 신뢰 → `/hooks`에서 `visual-viewer` 훅(**Stop**, 동기, 30초, 명령 `.codex\visual-viewer-hook.cmd codex …`)이 보이는지 확인하고 신뢰 → 질문 하나. 이전 버전(PostToolUse)을 신뢰했던 하네스는 다시 설치하면 Stop으로 옮겨지고 명령이 바뀌므로 다시 신뢰한다. 답변이 끝난 뒤 "Hook failed"가 보이면 실패다. **브라우저는 답변이 끝난 뒤** 열려야 한다(셸 명령 중에는 열리지 않는다). `/hooks`에 훅이 없으면 하네스·사용자 `config.toml`의 `[features] hooks`를 확인한다(하네스 설정이 우선). Claude 쪽을 나중에 다시 설치했다면 Codex `/hooks`에서 다시 신뢰해야 한다.
- 각 하네스에서 `uv run python web/prototypes/visual-viewer/viewer.py status`를 실행해 해당 CLI의 `registered: true`·`misplaced: 0`·`files_match_command: true`, `view_built: true`, `up_to_date: true`, `opened_sessions` 1 이상, `last_error: null`, `codex_hooks_disabled: false`, `version_warnings: []`(`cli_versions`가 확인한 버전)인지 본다. 안 열렸다면 `last_error_file`이 가리키는 `runtime-data/visual-viewer/hook-error.log`(훅 오류) 또는 `hook-start-error.log`(Codex에서 uv·Python 시작 실패)와 `open --latest`로 원인을 나눈다.
- **알려진 환경 문제(뷰어와 무관)**: 2026-10-12 이 PC의 codex-cli 0.162.1에서 Windows 샌드박스 "setup refresh had errors"가 났다. 샌드박스 기록에 따르면 Codex 자신의 computer-use 런타임(node_repl) 프로세스가 `%LOCALAPPDATA%\OpenAI\Codex\runtimes\cua_node\…\node_repl.exe`를 열어 두어 그 파일의 ACL을 바꾸지 못했다. 그러면 Codex가 모든 명령을 샌드박스 밖에서 실행할지 사용자에게 매번 묻는다. 기획자는 이 경우 질문마다 승인이 필요할 수 있다.
- 결과 보고에는 CLI 버전, selftest 결과, 열린 화면의 상태 표시, status 출력을 남긴다. CLI가 업데이트되면 selftest와 `/hooks`를 다시 확인한다. 실제 결과(export·화면·insights)는 Git·공개 자료에 넣지 않는다.
- 끝나면 `viewer.py uninstall --both <하네스>`로 끌 수 있다.
