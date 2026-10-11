# 결정 요청: 시각자료 뷰어를 main·제품 ZIP에 넣을지

2026-10-12 · 작성 최길웅(Claude Code 보조) · 받는 사람 **정이량**(릴리스), **황대겸**(웹 PM)

## 결정할 것

1. **대겸**: PR #6의 `web/prototypes/visual-viewer`를 웹 PM 결정으로 main에 **참고 시제품**으로 병합할지. `web/`의 기술·구조는 PM 결정 사항이다.
2. **이량**: 다음 제품 릴리스 ZIP에 뷰어 5파일(`index.html`, `build_view.py`, `hook.py`, `viewer.py`, `README.md`)을 **선택 설치물**로 넣을지.

## 사실 (2026-10-12 기준)

- PR #6 브랜치에 origin/main `99576f0`(제품 v0.7.0 기록)을 로컬 병합하고 커밋했다. 아직 push하지 않았다.
- 뷰어는 저장된 export를 읽어 그리기만 한다. 업무 Agent·Skill·Tool·계약·자료, `skills/manifest.json`, 제품 doctor 대상 파일은 바꾸지 않았다.
- 훅(`hook.py`)은 표준 라이브러리만 쓰고 항상 exit 0이며 stdout·stderr가 없다. 업무·모델·Tool을 호출하지 않는다. 오류는 하네스의 `runtime-data/visual-viewer/hook-error.log`에만 남는다.
- 설치(`viewer.py install --claude|--codex <하네스>`)는 하네스의 `.claude/settings.local.json` 또는 `.codex/hooks.json`에 항목을 **추가**만 하고, 명령에는 개인 절대 경로가 없다. Codex 훅은 공식 형식(프로젝트 `.codex/hooks.json`, PostToolUse `Bash`)이며 `/hooks`에서 사람이 한 번 신뢰해야 돈다. 신뢰를 우회하지 않는다.
- 화면·insights·로그는 `runtime-data/`에만 생긴다(레포·제품 `.gitignore` 제외 대상). 테스트는 실행 중에 만드는 `[합성 시험 자료]` export만 쓴다. 실제 결과는 Git에 없다.
- 대겸의 PR #7(`codex/local-harness-web`)은 **사용자 결정으로 쓰지 않았다.** 코드를 가져오거나 옮기지 않았다.
- 검사: 새 `tests/web` 17개와 레포 CI 4개 명령을 로컬 Windows·Python 3.12에서 실행해 모두 exit 0이다. 원격 CI는 계정 결제 제한으로 시작되지 않으므로 로컬 결과만 있다.
- **아직 확인 안 함**: 실제 Claude Code·Codex 세션에서 훅이 불리고 브라우저가 열리는 것(아래 확인 절차), macOS·Linux, Codex 샌드박스 권한에서의 브라우저 열기.

## 선택지

| 안 | 내용 | 필요한 일 | 위험 |
|---|---|---|---|
| A | main 병합만, ZIP 제외 | PM 승인 후 PR #6 병합 | 기획자가 레포 checkout을 받아야 설치 가능 |
| B | main 병합 + ZIP에 선택 설치물 | `scripts/build-product-manifest.py`로 `skills/manifest.json`의 shared_files에 5파일 추가, 제품 README에 설치 한 단락, 새 minor 릴리스 | ZIP 파일 수·지문 변경, 릴리스 계약의 제품 범위 해석 필요 |
| C | 보류 | 없음 | 시연·기획자 사용 시 수동 `build_view.py` 실행 |

**권장: B, 단 훅은 기본 미등록.** ZIP에 들어가도 `viewer.py install`을 직접 실행해야만 훅이 생기므로 기존 업무 실행 방식은 그대로다. 저장 결과 재생은 제품 사용 범위(결과 확인)에 해당한다고 보지만, [릴리스 계약](../../../docs/contracts/product-release.md)의 "제품 파일" 해석은 이량이 판단한다. 시간이 부족하면 A로 병합하고 B는 다음 버전으로 미룬다.

## B를 고르면 할 일

1. 대겸 승인 후 PR #6 병합(웹 PM 범위).
2. 이량: manifest·제품 README 갱신, `check-product-assets.py`와 제품 테스트의 파일 수 기대값 확인, 새 제품 버전(호환 기능 추가라 minor) 발행 절차 진행.
3. `check.yml`에 `python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/web -v` 한 줄 추가(원격 CI가 다시 돌 때 대비).
4. 시연 PC에서 미리 아래 확인 절차를 끝내고 Codex `/hooks` 신뢰를 해 둔다.

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
```

해시는 `89EBA6307A7411AEFCEB79868F161BCAB369EEECFCA29ECDF3079A751CECFAE5`여야 한다.

- **Claude**: `C:\lgax-verify\claude`를 기본 작업 폴더로 Claude Code를 새로 열고 질문 하나(예: "전자레인지 사용 불편을 실제 리뷰에서 찾아 개선안을 제안해 줘.")를 한다. 답이 끝나 export가 저장되면 브라우저에 `runtime-data/visual-viewer/index.html`이 열려야 한다.
- **Codex**: `cd C:\lgax-verify\codex` 후 `codex --search`. 폴더 신뢰 → `/hooks`에서 `visual-viewer` 훅 확인·신뢰 → 질문 하나. export 저장 뒤 브라우저가 열려야 한다.
- 각 하네스에서 `uv run python web/prototypes/visual-viewer/viewer.py status`를 실행해 `registered: true`, `up_to_date: true`, `opened_sessions` 1 이상, `last_error: null`인지 본다. 안 열렸다면 `runtime-data/visual-viewer/hook-error.log`와 `open --latest`로 원인을 나눈다.
- 결과 보고에는 CLI 버전, 열린 화면의 상태 표시, status 출력을 남긴다. 실제 결과(export·화면·insights)는 Git·공개 자료에 넣지 않는다.
- 끝나면 `viewer.py uninstall --both <하네스>`로 끌 수 있다.
