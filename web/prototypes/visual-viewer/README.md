# 저장 결과 시각자료 뷰어 — 참고용 시제품

2026-10-12 최길웅 제출. **웹 PM 황대겸의 기술·구조 결정 전 참고용 시제품**이며 채택·웹 통합·시연 인수 기록이 아니다. 팀이 공유한 Streamlit 고객 리뷰 분석 시연 영상(`KakaoTalk_20261009_191820838.mp4`, Git 제외)의 화면 느낌(남색 단계 사이드바, 어두운 지표 카드, Plotly풍 차트, 하단 단계 자막)을 참고해 새로 작성했다. 영상 앱의 코드는 가져오지 않았다. 대겸의 PR #7(`codex/local-harness-web`)은 사용자 결정에 따라 쓰지 않았고 코드도 가져오지 않았다. main·제품 ZIP 포함 여부는 [결정 요청 메모](RELEASE-MEMO.md)를 따른다.

## 기획자 설치 안내 (Claude Code·Codex 공용)

CLI에서 질문해 결과(export)가 저장되면 브라우저에 결과 화면이 자동으로 열린다. CLI 세션마다 처음 한 번만 열리고, 그 뒤 결과는 열린 화면이 2초 안에 바뀐다. 하네스 업무 방식(Agent·Skill·Tool·모델)은 그대로다.

준비: 설치된 하네스 폴더(Codex용 제품 폴더나 Claude 사본), uv와 Python 3.12(하네스 설치 조건과 같음), 이 뷰어가 들어 있는 폴더(이 레포 checkout).

**1. 설치 (하네스마다 한 번)** — 이 레포 폴더에서 PowerShell로, 하네스 폴더 경로를 꼭 적는다:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py install --claude C:/내-하네스-폴더
uv run python web/prototypes/visual-viewer/viewer.py install --codex C:/내-하네스-폴더
```

- 뷰어 파일 5개를 `<하네스>/web/prototypes/visual-viewer/`에 복사하고, 훅을 `.claude/settings.local.json`(Claude) 또는 `.codex/hooks.json`(Codex)에 **추가**한다. 기존 설정·다른 훅은 지우거나 순서를 바꾸지 않는다. 설정 파일이 JSON이 아니거나 UTF-8이 아니면(UTF-16·cp949) 아무것도 바꾸지 않고 멈춘다.
- 개발 레포(이 checkout)에는 설치하지 않는다. 경로를 빼먹으면 오류로 멈춘다.
- 훅 명령에는 개인 경로가 없다. 하네스 기준 상대 경로와 뷰어 파일 3개의 SHA-256 지문만 들어 있고 Python 3.12는 uv로 실행한다.
- 설치(재설치 포함) 순간에 이미 있던 export로는 브라우저를 띄우지 않는다. 보려면 아래 4번을 쓴다.

**2. Claude Code** — 하네스 폴더를 기본 작업 폴더로 Claude Code(Desktop의 Code 또는 터미널 `claude`)를 **새로** 열고 질문한다. export가 저장되면 브라우저가 열린다. 훅은 백그라운드(async)로 돌아 작업을 기다리게 하지 않는다.

**3. Codex** — 하네스 폴더에서 `codex --search`를 연다. 처음 한 번 프로젝트 신뢰를 허용하고, `/hooks`에서 `visual-viewer` 훅 명령을 확인한 뒤 신뢰(trust)한다. 신뢰 전에는 실행되지 않는다. 뷰어를 다시 설치해 파일이 바뀌면 명령의 지문이 바뀌므로 `/hooks`에서 다시 신뢰해야 한다. 신뢰 우회 옵션(`--dangerously-bypass-hook-trust`)은 쓰지 않는다. Codex는 반드시 하네스 폴더에서 시작한다.

- codex-cli 0.146은 async 훅을 지원하지 않아 Codex용 훅은 **동기**다. 셸 명령마다 약 0.65초, 새 export를 그릴 때 약 1초가 더 걸린다(아래 실제 검사). 부담되면 `/hooks`에서 끄거나 5번으로 해제한다.

**4. 안 열릴 때 직접 열기·상태 확인** — 하네스 폴더에서:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py open --latest
uv run python web/prototypes/visual-viewer/viewer.py status
```

- status: `registered`(훅 등록), `files_match_command`(설치 파일이 명령의 지문과 같음), `view_built`·`up_to_date`(화면을 실제로 만들었는지·최신 export인지), `baseline_only`(설치 때 본 것으로만 표시하고 아직 그리지 않음), `codex_features`(하네스·사용자 config.toml의 `[features] hooks`), `last_error`.

**5. 끄기** — 하네스 폴더에서 `uninstall --claude`, `--codex`, `--both` 중 하나. 이 뷰어의 훅만 지우고 다른 설정·화면·insights 파일은 남긴다. Codex에서는 다른 훅의 신뢰가 풀리지 않도록 뒤에 다른 훅이 있으면 빈 자리표시 `{"matcher": "Bash", "hooks": []}`를 남긴다(다시 설치하면 그 자리를 쓴다). Codex는 `/hooks`에서 잠시 끌 수도 있다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py uninstall --both
```

알아 둘 점

- 훅은 업무·모델·Tool을 호출하지 않고 출력이 없으며 항상 exit 0이다. 오류는 `runtime-data/visual-viewer/hook-error.log`에만 남는다.
- 화면(`index.html`, `view-data.js`)·훅 상태·로그·insights는 모두 `<하네스>/runtime-data/visual-viewer/`에 생긴다. 실제 결과이므로 Git·공개 자료에 넣지 않는다.
- 의견 묶음 도넛·구분별 막대·후기 원문 비교는 export에 없는 모델 해석이라 insights 파일(`runtime-data/visual-viewer/insights-<이름>.json`)이 있어야 그린다. 없거나 맞지 않으면 근거 대시보드 맨 위에 이유가 나온다.

## 파일과 동작

| 파일 | 역할 |
|---|---|
| `index.html` | 뷰어. 같은 폴더의 `view-data.js`를 읽어 그린다. 로컬 파일로 열면 2초마다 데이터 변경을 확인한다. |
| `build_view.py` | export와 insights를 읽어 `view-data.js`(필요하면 단일 HTML 보고서)를 만든다. 판단은 하지 않는다. |
| `hook.py` | Claude Code·Codex 공용 훅. 새 export가 생기면 화면 데이터를 다시 만들고, CLI 세션마다 처음 한 번 브라우저를 연다. |
| `viewer.py` | `install`·`uninstall`·`open --latest`·`status`. |

- 두 CLI 모두 PostToolUse 훅 입력 JSON을 stdin으로 준다. Claude는 `Bash|PowerShell`(async, 60초), Codex는 `Bash`(동기, 30초)에 등록한다. 세션 구분은 `claude:<session_id>`·`codex:<session_id>`다. 형식은 2026-10-12에 공식 문서([Codex hooks](https://learn.chatgpt.com/docs/hooks), [Claude Code hooks](https://code.claude.com/docs/en/hooks))로 확인했다. 문서는 Codex async 훅을 설명하지만 로컬 codex-cli 0.146.0은 "async hooks are not supported yet"로 건너뛰어서 Codex는 동기로 둔다.
- 등록되는 명령: `uv run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c "<hook.py 찾기·지문 확인·실행>" claude|codex <build_view.py 지문> <index.html 지문>`. Claude는 `CLAUDE_PROJECT_DIR`, Codex는 세션 폴더(하네스 폴더)에서 `web/prototypes/visual-viewer/hook.py`를 찾는다. hook.py는 SHA-256이 설치 때와 같을 때만 읽은 바이트 그대로 실행되고, build_view.py·index.html도 지문이 맞을 때만 쓴다. 다르거나 없으면 실행하지 않는다. 작업 폴더의 `.python-version`·`uv.toml`은 따르지 않는다. Git Bash·PowerShell·cmd에서 같은 뜻이 되도록 셸 특수문자를 쓰지 않는다.
- `hook.py`는 표준 라이브러리만 쓰고 stdout·stderr를 버린다. 새 export만 그리고, 두 번 읽지 못한 export는 로그에 한 번 남긴 뒤 export나 insights 파일이 바뀔 때까지 다시 시도하지 않는다. 여러 훅이 동시에 돌면 OS 파일 잠금(프로세스가 끝나면 저절로 풀림)으로 한 번만 만든다. 브라우저를 열기 전에 세션 기록부터 저장해 한 세션에서 두 번 열리지 않게 한다. 출력 폴더의 index.html은 그릴 때마다 지문을 확인한 원본으로 되돌린다.
- 승인된 유효 완료 결과는 근거 대시보드, 그 밖(turn 없는 최근 요청·무효·거절·보류·취소)은 요청·개요 화면을 먼저 보여준다.

### 보안 한계 (Codex 샌드박스와 함께 쓸 때)

Codex는 신뢰한 훅을 샌드박스 밖에서 실행한다. 지문 확인으로 샌드박스 안의 명령이 `hook.py`·`build_view.py`·`index.html`을 바꿔 훅을 통해 실행시키는 길은 막았다. 다만 Python 실행 파일은 uv가 고른 Python 3.12이며, 하네스에 `.venv`가 있으면 그 안의 `python.exe`가 선택된다(`--managed-python`을 줘도 같았다). `.venv`는 하네스 폴더 안이라 샌드박스 명령이 바꿀 수 있다. 그런 변경이 있으면 이 훅도(그 폴더에서 사람이 직접 실행하는 `uv run`과 마찬가지로) 바뀐 실행 파일을 샌드박스 밖에서 실행한다. 이 한계는 고치지 못했다. 명령에 사용자별 절대 경로를 넣지 않는다는 조건에서 작업 폴더 밖의 Python을 고정하는 방법을 찾지 못했다. 샌드박스를 보안 경계로 쓰는 환경에서는 Codex 훅을 설치하지 말거나 `/hooks`에서 꺼 둔다.

## 직접 만들기 (build_view.py)

```
python web/prototypes/visual-viewer/build_view.py --export <하네스 runtime-data/exports의 세션 JSON> --focus dashboard --open
```

- 기본은 이 폴더에 `view-data.js`가 생기고 `index.html`이 열린다. `--out-dir 폴더`를 주면 그 폴더에 `view-data.js`와 `index.html`을 둔다.
- `--standalone 경로`: 데이터를 넣은 단일 HTML. `--insights 파일`: 모델이 쓴 해석(의견 묶음·단계 자막·제외 사유 등). insights의 session_id·turn_id가 export와 다르면 쓰지 않고 경고한다. insights 없이도 결과 구조만으로 모든 화면을 그린다.
- 생성물(`view-data.js`, `report-*.html`, `*.tmp`, 훅 상태·로그)과 실제 결과의 insights는 이 폴더의 `.gitignore`로 제외한다. 실제 결과 예시는 Git이 아닌 메일·접근 제한 링크로 공유한다.

## 화면과 표시 원칙

요청·개요 / 근거 대시보드 / 후기 선별 / 기능 대조 / 제안 / 업무 기록 재생 / 근거 원문 / 내보내기의 8개 화면이다. [웹 연결 계약](../../../docs/contracts/team-web-kitchen.md)에 맞춰 다음을 표시한다.

- 모든 화면: `저장된 실행 결과`, 상태(`기획 초안 완료(completed)`·수정 필요·보류·입력 필요·조사 필요·진행 중·실패·취소), valid, `의미 검토 unverified · 인수 전`, 합성 자료면 `합성 시험 자료`, 화면 생성 경고 수.
- **현재 결과는 저장 도구가 승인한 결과(`state.latest_result`)뿐이다.** 거절 후보(`validation.contract_valid=false`·`error`)는 현재 결과·제안으로 그리지 않고 업무 기록의 후보 표에 `거절 · <code>`와 사유(error·review.findings)로 남긴다. 승인된 결과가 없으면 근거·대조·제안 화면은 비우고 이유를 적는다. 내보내기의 계약 검사는 저장 판정(`validation.contract_valid`)에서 읽는다.
- turn 없이 멈춘 요청(needs_input·research_required·held)이 마지막 turn 뒤에 있으면 상태 맨 앞에 `최근 요청 … · turn 없음`, 요청·개요 맨 위에 질문·멈춘 이유를 보이고 이전 turn은 `이전 결과`로 표시한다.
- 취소는 `state.cancellation`의 사유·취소 전 상태를 적고, 실행 중단은 확인되지 않았다고 표시한다. 무효 turn은 `invalidation_reason`을 그대로 적는다.
- turn 순서는 export의 순서(created_at)를 그대로 쓴다. 후보가 없는 turn도 제자리에 둔다.
- product_family는 냉장고·전자레인지·식기세척기로 표시하고 모르는 값은 `미지원(값)`으로 둔다. 제품군 요청(scope_mode `family_catalog`)은 `냉장고 제품군 N개 모델`로 쓰고 model_scope 전체와 결과 근거 모델을 보여준다. 자료 버전과 model_scope 원문을 바꾸지 않는다. 사용자가 뺀 불편(`constraints.exclude_pains`)을 요청 조건에 보인다.
- 불편→기존 기능→남은 불편→제안을 원문 ID로 연결한 열로 보여준다. 열 사이 화살표는 업무 순서이며 항목 간 관계는 assessment의 feature_matches·concept_links에 적힌 것만 표시한다.
- concept의 `implementation_steps`·`validation_plan`을 표시하고 없으면 `미작성`, `planned_not_measured`는 `검증 계획 · 실측 전`으로 둔다.
- v0.7.0의 `decision_notes`는 요청·개요 화면에 `판단 메모`(D1…)로 보여준다. basis는 `원문 사실`·`AI 해석`·`미확인`으로 옮기되 모델이 붙인 라벨이며 공식 인용·의미 검증이 아니라고 적는다. 근거 원문 표의 연결 항목에도 D 번호가 붙는다.
- 근거 유형: export의 evidence_refs에는 kind가 없다. source_id 접두어(REVIEW·REV=후기, MANUAL=설명서, SPEC=스펙, PART=소모품, DOC=문서)로 나누고, 관례가 아니면 원문 표현(`factual_summary`=제품 사실, `excerpt`=원문 발췌)으로만 나눈다. 원문 발췌를 후기라고 단정하지 않으며 그때 후기 근거 수는 `미확인`이다.
- 근거: source_id·인용·원문 발췌/사실 요약·위치·모델 범위·게시/관측일·구매/협찬(null은 미확인)·상업 고지(commercial_disclosure)·SHA·HTTPS 링크. export 경로는 `runtime-data/exports/<파일>`로만 보여주고 개인 절대 경로를 넣지 않는다.
- 구조 검사와 `planning_detail_complete`(필드 존재 검사)를 의미 품질 통과로 표시하지 않는다.
- 사용량: 기록이 없거나 미측정 호출이 섞이면 0으로 그리지 않고 차트를 생략한다. 합계가 일부 호출만이면 `부분 합계 · N건 중 M건 미측정`으로 적는다. 누적 값을 다시 더하지 않는다.
- insights의 의견 묶음은 `모델 해석`으로 표시하고 건수는 ID 목록 길이로 센다. 관측 건수를 발생률·시장 수요로 표시하지 않는다.
- 업무 turn이 없는 export는 요청 기록 화면만 만들고 멈춘 이유(response.reason·events)를 보인다.

## insights 형식

숫자는 가능한 한 source_id 목록으로 주고 건수는 스크립트가 센다. 최상위에 `session_id`와 `turn_id`(그 해석을 쓴 turn)를 넣는다. 훅·`open --latest`는 같은 session_id 중 turn_id가 현재 turn과 같은 파일, 없으면 turn_id가 없는 파일을 고른다. 다른 turn용이거나 가리키는 근거 ID가 현재 결과에 없으면 쓰지 않고 이유를 화면에 적는다. 고정 숫자에 `"verify_in": "assumptions"`를 주면 결과 원문에 그 숫자가 있는지 확인하고, 없으면 그 숫자를 그리지 않고 경고한다. UTF-8 BOM이 있어도 읽는다.

- `groups`: `[{key, label, tone, source_ids}]` 의견 묶음. 도넛·구분별 막대·원문 비교에 쓰인다.
- `facet`: `{title, order, values: {source_id: 구분값}}` 묶음을 나눌 구분(가구 구성 등).
- `kpis`, `funnel`: 항목마다 `value`(고정 숫자), `group`(묶음 건수), `evidence: "all"`, `evidence_prefix: "REVIEW"` 중 하나.
- `excluded`, `feature_tags`, `node_titles`, `concept_titles`, `concept_steps`(제안 원문과 글자까지 같아야 하며 다르면 그리지 않음), `unresolved`, `usage_note`, `captions`.
- `pages`: 모델이 블록을 직접 쓴 화면. `[{id, nav, icon, title, caption: {title, text}, blocks: [...]}]`

## 실제 검사 (2026-10-12, Windows 11, Python 3.12)

- origin/main `99576f0`(제품 v0.7.0 기록)을 이 브랜치에 로컬 병합한 상태에서 실행했다.
- `tests/web/test_visual_viewer.py` 37개: 실제 product-tools 저장·export 경로로 테스트 시점에 만든 **합성 시험 export**(`[합성 시험 자료]` 표시)로 세 제품군 완료, 보류, 거절 1회·3회, 완료 뒤 turn 없는 조사 보류, 사용량 미측정·일부 측정, 제품군 카탈로그, 제외 조건·취소·진행 중 turn, 거절 뒤 취소, 입력 필요, 합성 카탈로그(REV/DOC 접두어)를 확인했다. 훅의 새 export 판별·세션당 한 번 열기·BOM insights·실패 뒤 insights 수정 시 재시도·상태 쓰기 재시도·OS 잠금·지문이 다른 파일 미실행, 설치의 위치 보존·재설치 기준점·개발 레포 거부·UTF-16/cp949 거부·Codex `[features] hooks` 층별 확인도 포함한다. 설치된 정확한 훅 명령을 cmd·Git Bash·Windows PowerShell 5.1로 실행해 exit 0·stdout/stderr 0바이트를 확인했다(셸이나 uv가 없으면 이유를 적고 건너뛴다).
- 로컬 codex-cli 0.146.0에 `codex app-server`의 `hooks/list`만 보내(임시 폴더, 격리한 CODEX_HOME, 모델 호출 없음) 설치된 Codex 동기 훅이 경고 없이 발견되고, 해제·재설치 뒤 다른 훅의 신뢰가 유지되며(빈 자리표시), 뷰어 파일을 바꿔 재설치하면 `modified`(다시 신뢰 필요)로 바뀌는 것을 확인했다.
- 동기 Codex 훅 명령 전체 시간(셸 포함): 새 export가 없을 때 약 0.65초, 165KB export를 다시 그릴 때 약 1.0초.
- 실제 Claude Code·Codex 대화 세션에서 훅이 불리고 브라우저가 열리는지는 **아직 확인하지 않았다**(Codex·Claude 대화 실행과 실제 업무 질문은 이 작업 범위 밖). 확인 절차는 [결정 요청 메모](RELEASE-MEMO.md)에 있다.
- 이전 기록: 로컬 export 5개(Git 제외)와 헤드리스 Edge 1280px 8개 화면, 375px 가로 넘침 없음은 이 변경 전 버전에서 확인했다.

## 남은 제약

- 실제 Claude Code·Codex 대화 세션 개통, Codex 샌드박스 권한에서의 브라우저 열기는 사용자 확인 전이다. macOS·Linux는 시험하지 않았다.
- 위 보안 한계(`.venv` 실행 파일)는 남아 있다.
- 관리자 `requirements.toml`·managed 설정의 Codex hooks 끄기는 status가 확인하지 않는다.
- 제품 ZIP에는 아직 들어 있지 않다. 지금은 레포 checkout에서 하네스로 설치한다.
- `tests/web`는 레포 CI(`check.yml`)에 아직 없다. 넣을 때 uv 설치 단계가 없으면 셸 시험 3개는 이유를 적고 건너뛴다(메모 참고).
- 브라우저에서 export 파일을 직접 고르는 기능이 없다(view JSON 끌어 놓기만 지원).
- 동일 작성자 후기 중복은 export에 작성자 정보가 없어 자동으로 판별하지 않는다. insights나 검토 메모에 적힌 경우만 보인다.
- 실제 native 관찰(observer) 연결, 실시간 Tool 사건, 웹에서 질문 실행은 범위 밖이다.
