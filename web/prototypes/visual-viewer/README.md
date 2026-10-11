# 저장 결과 시각자료 뷰어 — 참고용 시제품

2026-10-12 최길웅 제출. **웹 PM 황대겸의 기술·구조 결정 전 참고용 시제품**이며 채택·웹 통합·시연 인수 기록이 아니다. 팀이 공유한 Streamlit 고객 리뷰 분석 시연 영상(`KakaoTalk_20261009_191820838.mp4`, Git 제외)의 화면 느낌(남색 단계 사이드바, 어두운 지표 카드, Plotly풍 차트, 하단 단계 자막)을 참고해 새로 작성했다. 영상 앱의 코드는 가져오지 않았다. 대겸의 PR #7(`codex/local-harness-web`)은 사용자 결정에 따라 쓰지 않았고 코드도 가져오지 않았다. main·제품 ZIP 포함 여부는 [결정 요청 메모](RELEASE-MEMO.md)를 따른다.

## 기획자 설치 안내 (Claude Code·Codex 공용)

CLI에서 질문해 결과(export)가 저장되면 브라우저에 결과 화면이 자동으로 열린다. CLI 세션마다 처음 한 번만 열리고, 그 뒤 결과는 열린 화면이 2초 안에 바뀐다. 하네스 업무 방식(Agent·Skill·Tool·모델)은 그대로다.

준비: 설치된 하네스 폴더(Codex용 제품 폴더나 Claude 사본), uv, 이 뷰어가 들어 있는 폴더(이 레포 checkout).

**1. 설치 (하네스마다 한 번)** — 이 레포 폴더에서 PowerShell로:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py install --claude C:/내-하네스-폴더
uv run python web/prototypes/visual-viewer/viewer.py install --codex C:/내-하네스-폴더
```

- 뷰어 파일 5개를 `<하네스>/web/prototypes/visual-viewer/`에 복사하고, 훅을 `.claude/settings.local.json`(Claude) 또는 `.codex/hooks.json`(Codex)에 **추가**한다. 기존 설정·다른 훅은 지우지 않는다. 설정 파일이 JSON이 아니면 아무것도 바꾸지 않고 멈춘다.
- 훅 명령에는 개인 경로가 없다. 하네스 기준 상대 경로만 쓰고 Python은 uv로 실행한다.
- 설치 전에 있던 export로는 브라우저를 띄우지 않는다. 보려면 아래 4번을 쓴다.

**2. Claude Code** — 하네스 폴더를 기본 작업 폴더로 Claude Code(Desktop의 Code 또는 터미널 `claude`)를 **새로** 열고 질문한다. export가 저장되면 브라우저가 열린다.

**3. Codex** — 하네스 폴더에서 `codex --search`를 연다. 처음 한 번 프로젝트 신뢰를 허용하고, `/hooks`에서 `visual-viewer` 훅 내용을 확인한 뒤 신뢰(trust)한다. 신뢰 전에는 실행되지 않고, 훅 내용이 바뀌면 다시 신뢰해야 한다. 신뢰 우회 옵션(`--dangerously-bypass-hook-trust`)은 쓰지 않는다. Codex는 반드시 하네스 폴더에서 시작한다.

**4. 안 열릴 때 직접 열기·상태 확인** — 하네스 폴더에서:

```powershell
uv run python web/prototypes/visual-viewer/viewer.py open --latest
uv run python web/prototypes/visual-viewer/viewer.py status
```

**5. 끄기** — 하네스 폴더에서 `uninstall --claude`, `--codex`, `--both` 중 하나. 이 뷰어의 훅만 지우고 다른 설정과 화면·insights 파일은 남긴다. Codex는 `/hooks`에서 잠시 끌 수도 있다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py uninstall --both
```

알아 둘 점

- 훅은 Bash·PowerShell 명령이 끝날 때마다 백그라운드(async)로 약 0.5초 돌고, 새 export가 없으면 바로 끝난다. 업무·모델·Tool을 호출하지 않고 출력이 없으며 항상 exit 0이다. 오류는 `runtime-data/visual-viewer/hook-error.log`에만 남는다.
- 화면(`index.html`, `view-data.js`)·훅 상태·로그·insights는 모두 `<하네스>/runtime-data/visual-viewer/`에 생긴다. 실제 결과이므로 Git·공개 자료에 넣지 않는다.
- 의견 묶음 도넛·구분별 막대·후기 원문 비교는 export에 없는 모델 해석이라 같은 session_id의 insights 파일(`runtime-data/visual-viewer/insights-<이름>.json`)이 있어야 그린다. 없으면 근거 대시보드 맨 위에 안내가 나온다.

## 파일과 동작

| 파일 | 역할 |
|---|---|
| `index.html` | 뷰어. 같은 폴더의 `view-data.js`를 읽어 그린다. 로컬 파일로 열면 2초마다 데이터 변경을 확인한다. |
| `build_view.py` | export와 insights를 읽어 `view-data.js`(필요하면 단일 HTML 보고서)를 만든다. 판단은 하지 않는다. |
| `hook.py` | Claude Code·Codex 공용 훅. 새 export가 생기면 화면 데이터를 다시 만들고, CLI 세션마다 처음 한 번 브라우저를 연다. |
| `viewer.py` | `install`·`uninstall`·`open --latest`·`status`. |

- 두 CLI 모두 PostToolUse 훅 입력 JSON을 stdin으로 준다. Claude는 `Bash|PowerShell`, Codex는 `Bash`(Codex 셸 명령의 훅 이름)에 등록한다. 세션 구분은 `claude:<session_id>`·`codex:<session_id>`다. 형식은 2026-10-12에 공식 문서로 확인했다: [Codex hooks](https://learn.chatgpt.com/docs/hooks)(로컬 codex-cli 0.146.0), [Claude Code hooks](https://code.claude.com/docs/en/hooks)(로컬 2.1.289).
- 등록되는 명령(Claude): `uv run --no-project --quiet python -I -B -c "<hook.py 찾기·실행>" claude`. Claude는 `CLAUDE_PROJECT_DIR`, Codex는 세션 폴더(하네스 폴더)에서 `web/prototypes/visual-viewer/hook.py`를 찾고, 없으면 조용히 끝난다. Git Bash·PowerShell·cmd에서 같은 뜻이 되도록 셸 특수문자를 쓰지 않는다.
- `hook.py`는 표준 라이브러리만 쓰고 stdout·stderr를 버린다. 새 export만 그리고, 두 번 읽지 못한 export는 로그에 한 번 남긴 뒤 다시 시도하지 않는다. 동시에 여러 훅이 돌면 잠금 파일로 한 번만 만든다.
- 완료 결과는 근거 대시보드, 보류·입력 필요·turn 없음은 요청·개요 화면을 먼저 보여준다.

## 직접 만들기 (build_view.py)

```
python web/prototypes/visual-viewer/build_view.py --export <하네스 runtime-data/exports의 세션 JSON> --focus dashboard --open
```

- 기본은 이 폴더에 `view-data.js`가 생기고 `index.html`이 열린다. `--out-dir 폴더`를 주면 그 폴더에 `view-data.js`와 `index.html`을 둔다.
- `--standalone 경로`: 데이터를 넣은 단일 HTML. `--insights 파일`: 모델이 쓴 해석(의견 묶음·단계 자막·제외 사유 등). insights의 session_id가 export와 다르면 쓰지 않고 경고한다. insights 없이도 결과 구조만으로 모든 화면을 그린다.
- 생성물(`view-data.js`, `report-*.html`, `*.tmp`, 훅 상태·로그)과 실제 결과의 insights는 이 폴더의 `.gitignore`로 제외한다. 실제 결과 예시는 Git이 아닌 메일·접근 제한 링크로 공유한다.

## 화면과 표시 원칙

요청·개요 / 근거 대시보드 / 후기 선별 / 기능 대조 / 제안 / 업무 기록 재생 / 근거 원문 / 내보내기의 8개 화면이다. [웹 연결 계약](../../../docs/contracts/team-web-kitchen.md)에 맞춰 다음을 표시한다.

- 모든 화면: `저장된 실행 결과`, 상태(`기획 초안 완료(completed)`·보류·입력 필요·실패·취소), valid, `의미 검토 unverified · 인수 전`.
- product_family는 냉장고·전자레인지·식기세척기로 표시하고 모르는 값은 `미지원(값)`으로 둔다. 자료 버전과 model_scope 원문을 바꾸지 않는다.
- 불편→기존 기능→남은 불편→제안을 원문 ID로 연결한 열로 보여준다. 열 사이 화살표는 업무 순서이며 항목 간 관계는 assessment의 feature_matches·concept_links에 적힌 것만 표시한다.
- concept의 `implementation_steps`·`validation_plan`을 표시하고 없으면 `미작성`, `planned_not_measured`는 `검증 계획 · 실측 전`으로 둔다.
- v0.7.0의 `decision_notes`는 요청·개요 화면에 `판단 메모`(D1…)로 보여준다. basis는 `원문 사실`·`AI 해석`·`미확인`으로 옮기되 모델이 붙인 라벨이며 공식 인용·의미 검증이 아니라고 적는다. 근거 원문 표의 연결 항목에도 D 번호가 붙는다.
- 근거: source_id·인용·원문 발췌/사실 요약·위치·모델 범위·게시/관측일·구매/협찬(null은 미확인)·SHA·HTTPS 링크. export 경로는 `runtime-data/exports/<파일>`로만 보여주고 개인 절대 경로를 넣지 않는다.
- 과거 turn과 거절·수정 후보는 `역사적 기록`으로 남긴다. 구조 검사와 `planning_detail_complete`(필드 존재 검사)를 의미 품질 통과로 표시하지 않는다.
- 사용량 기록이 없으면 0이 아니라 `미측정`으로 두고 차트를 그리지 않는다. 누적 값을 다시 더하지 않는다.
- insights의 의견 묶음은 `모델 해석`으로 표시하고 건수는 ID 목록 길이로 센다. 관측 건수를 발생률·시장 수요로 표시하지 않는다.
- 업무 turn이 없는 export(조사 단계 보류)는 요청 기록 화면만 만들고 근거·제안 화면을 만들지 않는다.

## insights 형식

숫자는 가능한 한 source_id 목록으로 주고 건수는 스크립트가 센다. 최상위에 `session_id`를 넣으면 훅·`open --latest`가 같은 세션의 export에 자동으로 붙인다. 고정 숫자에 `"verify_in": "assumptions"`를 주면 결과 원문에 그 숫자가 있는지 확인하고, 없으면 warnings에 남긴다.

- `groups`: `[{key, label, tone, source_ids}]` 의견 묶음. 도넛·구분별 막대·원문 비교에 쓰인다.
- `facet`: `{title, order, values: {source_id: 구분값}}` 묶음을 나눌 구분(가구 구성 등).
- `kpis`, `funnel`: 항목마다 `value`(고정 숫자), `group`(묶음 건수), `evidence: "all"`, `evidence_prefix: "REVIEW"` 중 하나.
- `excluded`, `feature_tags`, `node_titles`, `concept_titles`, `concept_steps`(제안 원문과 글자까지 같아야 함), `unresolved`, `usage_note`, `captions`.
- `pages`: 모델이 블록을 직접 쓴 화면. `[{id, nav, icon, title, caption: {title, text}, blocks: [...]}]`

## 실제 검사 (2026-10-12, Windows 11, Python 3.12)

- origin/main `99576f0`(제품 v0.7.0 기록)을 이 브랜치에 로컬 병합한 상태에서 실행했다.
- `tests/web/test_visual_viewer.py` 17개: 실제 product-tools 저장·export 경로로 테스트 시점에 만든 **합성 시험 export**(`[합성 시험 자료]` 표시, 세 제품군 완료·보류·turn 없음)로 화면 생성, 판단 메모·구현 단계·검증 계획·insights 안내/일치/불일치, 훅의 새 export 판별·세션당 한 번 열기·잘못된 입력·깨진 export·잠금, 설치 병합·멱등·잘못된 JSON 거부·해제를 확인했다. 설치된 정확한 훅 명령을 cmd·Git Bash·PowerShell 5.1로 실행해 exit 0·stdout/stderr 0바이트를 확인했다.
- 제품 v0.7.0 ZIP(SHA-256 `89eba630…cfae5`)을 임시 폴더에 풀어 `install --both`와 합성 export로 훅을 돌렸다. 새 export가 없을 때 훅 명령 전체 시간은 약 0.55초, 다시 그릴 때 약 0.8초였다.
- 실제 Claude Code·Codex 세션에서 훅이 불리고 브라우저가 열리는지는 **아직 확인하지 않았다**(Codex 실행과 실제 업무 질문은 이 작업 범위 밖). 확인 절차는 [결정 요청 메모](RELEASE-MEMO.md)에 있다.
- 이전 기록: 로컬 export 5개(Git 제외)와 헤드리스 Edge 1280px 8개 화면, 375px 가로 넘침 없음은 이 변경 전 버전에서 확인했다.

## 남은 제약

- 실제 Claude Code·Codex 세션 개통, Codex `/hooks` 신뢰 화면과 async 훅의 Windows 동작, Codex 샌드박스 권한에서 브라우저 열기는 사용자 확인 전이다. macOS·Linux는 시험하지 않았다.
- 제품 ZIP에는 아직 들어 있지 않다. 지금은 레포 checkout에서 하네스로 설치한다.
- `tests/web`는 레포 CI(`check.yml`)에 아직 없다. 넣으려면 한 줄 추가가 필요하다(메모 참고).
- 브라우저에서 export 파일을 직접 고르는 기능이 없다(view JSON 끌어 놓기만 지원).
- 동일 작성자 후기 중복은 export에 작성자 정보가 없어 자동으로 판별하지 않는다. insights나 검토 메모에 적힌 경우만 보인다.
- 실제 native 관찰(observer) 연결, 실시간 Tool 사건, 웹에서 질문 실행은 범위 밖이다.
