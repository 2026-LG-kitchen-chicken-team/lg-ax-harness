# 2026-10-14 관찰 연결 보완

관찰 파일에는 질문 원문을 복제하지 않는다. DB의 요청·turn·조사 조회는 동일 업무 식별자로 연결하며, 네이티브 사건의 제품 Tool 응답에 기록된 session_id·turn_id·request_key가 DB binding과 모두 맞는 경우만 세션 연결을 표시한다. 시간대 겹침이나 서로 다른 전역 최신 기록은 연결 인증에 사용하지 않는다. 연결 근거가 없으면 미확인 상태를 유지한다.

Codex `turn_aborted`와 명시 interrupted Stop은 turn 취소 관측으로 표시한다. 열린 Tool 기록은 취소 관측 시점에 닫되 도구 종료 결과는 미확인으로 남긴다. 취소 이후 늦게 도착한 응답으로 취소 span을 정상 완료로 바꾸지 않는다. 기록이 끝난 열린 span도 결과 미확인이다. 이는 backend 프로세스 종료 인증이 아니다.

관찰·재생·가상 demo의 구분과 추가 모델 호출 0은 유지한다. 이 observer는 선택적인 레포 프로그램이며 제품 설치에 포함되었다고 가정하지 않는다. 실제 레포 경로에서 실행한다.

# LG AX 기획 사무실 · 관측 장치와 3D 화면

하네스가 **지금 무엇을 하고 있는지** 보여 주는 "기획 사무실"이다. 두 부분으로 되어 있다.

1. **관측 장치** (`observe.py`, `codex_follow.py`, `office.py`): Claude Code의 훅으로 도구 시작·끝, 연구 역할 위임·반환, 어느 Skill의 어느
   작업인지를 시각과 함께 남기고, 하네스 DB를 읽기 전용으로 잠깐 확인해 작업 일지·후보 저장 상태를 함께 적는다.
   Codex는 훅 대신 Codex가 남기는 세션 기록(rollout)을 따라가며 같은 형식으로 적는다.
2. **사무실 화면** (`index.html`, 원본은 `app/`): 그 기록을 3D 사무실로 보여 준다. 방이나 사람을 누르면 하는 일·지금 상태·
   지금까지의 기록이 나온다. 실시간 보기와 기록 재생을 할 수 있다.

기준은 product v0.10.0(메인 1 · 선택 연구 역할 3 · 업무 Skill 6)이다. 역할·Skill 이름은 팀원 관제실
(`codex/control-room-v0.10.0`의 `src/catalog.ts`)과 같은 id를 쓴다.

## 설치 (하네스마다 한 번)

이 레포 폴더에서, 설치된 하네스 폴더 경로를 적는다.

```powershell
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py install --claude C:/내-하네스-폴더
```

- `observe.py`·`office.py`·`README.md`·`index.html`·`factory.html`을 `<하네스>/web/prototypes/agent-office/`에, 두 화면
  (`factory.html` 실행 대시보드 = 공장 관제, `index.html` 3D 사무실)을 기록 옆 `<하네스>/runtime-data/agent-office/`에 복사하고,
  `.claude/settings.local.json`에
  백그라운드(async) 훅 9개를 **추가**한다: PreToolUse·PostToolUse·PostToolUseFailure(모든 도구), UserPromptSubmit, Stop,
  SubagentStart, SubagentStop, SessionStart, SessionEnd. 다른 훅(시각자료 뷰어 등)과 설정은 그대로 둔다.
- 설정이 UTF-8 JSON 객체가 아니면 아무것도 바꾸지 않고 멈춘다. 개발 레포(`dev-harness` 폴더가 있는 곳)에는 설치하지 않는다.
- 다시 설치하면 이 장치의 훅만 새것으로 바뀐다. 끄기: `office.py uninstall --claude <폴더>` (기록 파일은 남긴다).
- `--open-on-prompt`(심사위원 ZIP의 `judge.py setup --engine claude`가 사용): 세션의 **첫 질문**이 들어오면 훅이 실행 대시보드
  (`factory.html`, `--page office`면 3D 사무실)를 기본 브라우저로 한 번 연다(세션마다 한 번, `runtime-data/agent-office/auto-open.json`에
  화면 이름과 연 세션 ID만 남김). 훅은 정해진 두 파일 이름만 열고 경로는 받지 않는다. 화면 이름이 없는 예전 auto-open.json은 계속
  3D 사무실을 연다. 화면을 여는 프로그램의 출력은 버려 모델 문맥에 들어가지 않는다. 하위 에이전트 결과 전달·작업 알림은 질문으로
  세지 않는다. 끄기: 이 옵션 없이 다시 `install`(파일을 지움).
- 확인: `office.py status --claude <폴더>` · 화면 열기: `office.py open --claude <폴더> [--page factory|office]`(기본은 공장 관제) · 글로 보기: `office.py watch --claude <폴더>`(새 기록을 한 줄씩 한글로 출력, 읽기만 함) · 자체 시험: `office.py selftest`(임시 사본에서 실제 훅 명령을 합성 입력으로 실행).

## 실행 대시보드 · 공장 관제 (`factory.html`)

신진하 님의 KITCHEN AX 공장 관제 화면(`web/prototypes/control-room/factory-dashboard`)을 이 기록으로 그린다. 원본에서
`npm run build:office`가 JS·CSS·연구원 이미지를 넣은 파일 하나를 이 폴더의 `factory.html`로 만든다(직접 고치지 않는다).
`<하네스>/runtime-data/agent-office/factory.html`을 브라우저로 열면 서버·토큰 없이 옆의 `live.js`를 1초마다, 결과 화면의
`../visual-viewer/view-data.js`를 4초마다 다시 읽는다. 메뉴에서 실시간·기록 재생·데모(공장 자체의 가상 상품기획 엔진)를 고르고,
세션 고르기·기록 파일 열기(`events.jsonl`)·결과 화면 열기를 쓴다. 아래 막대로 1~64배속 재생, 빈 시간 건너뛰기, 시각 이동을 한다.
장면 링크: `factory.html#mode=replay&s=3&t=840&sel=structure&play=0`. 다섯 작업장은 Skill 명령 기록과 함께 하네스 DB의 조사
종료·분석 범위·저장 후보 개수, 검토 단계 명령을 근거로 진행을 표시한다. 니즈 구조화·기능 대조·콘셉트 작성은 별도 명령이 없어
단계 경계를 만들지 않고 "분석 구간"으로 함께 표시한다. 설치 버전은 `runtime-data/judge-setup.json`의 release를 따른다(없으면
"설치 버전 미확인").

## 사무실 화면 (2단계)

여는 법: `office.py open --claude <하네스 폴더>` 또는 `<하네스>/runtime-data/agent-office/index.html`을 브라우저로 직접 연다
(파일 하나, 서버 필요 없음). 화면은 옆의 `live.js`를 1초마다 다시 읽는다. 글꼴(Pretendard)만 인터넷에서 받고, 없으면
맑은 고딕으로 보인다. 아무것도 밖으로 보내지 않는다.

| 보기 | 내용 |
| --- | --- |
| 실시간 | 가장 최근 세션을 지금 시각으로 보여 준다. 마지막 기록이 15분 안이면 처음에 이 보기로 열린다. |
| 기록 재생 | 세션을 골라 1~64배속으로 재생한다. 아무 일도 없는 시간은 건너뛴다(끌 수 있음). 아래 띠를 누르면 그 시각으로 간다. |
| 데모 | 가상 기록(사이트 이름도 `*.example`)으로 움직임만 보여 준다. 화면 위에 항상 "데모"라고 표시한다. |

`live.js`에는 최근 사건 1500개만 있다. 더 긴 기록은 **기록 파일 열기**로 `events.jsonl`을 연다(이때 DB 정보는 없다).
특정 장면 링크: `index.html#mode=replay&s=2&t=95&sel=evidence-retrieval&play=0` (s = 세션 번호, t = 시작부터 초).

화면의 자리는 product v0.10.0 구조 그대로다: 가운데 메인 기획자, 뒤쪽 연구실 3개(공식 자료 조사·후기 조사·분석·독립 근거
검토), 오른쪽 Skill 방 6개, 왼쪽 명령 콘솔·파일 서가·접수창구·자료 보관소(DB), 앞쪽 출고실, 담장 밖 웹 거리.

| 보이는 것 | 뜻 | 근거 |
| --- | --- | --- |
| 빛 기둥·불꽃 | 그 방에서 지금 도구 호출이 진행 중 | 훅 PreToolUse~PostToolUse |
| 빛 알갱이 | 호출 시작(사람→방)과 끝(방→사람). 빨강은 실패나 저장 거절 | 훅, 저장 응답의 `accepted` |
| 점선 | 아직 끝나지 않은 호출 | 훅 |
| 연구실 로봇 | SubagentStart~SubagentStop 사이에만 나타남. 흐린 연구실은 이번 기록에서 부르지 않은 역할 | 훅 |
| 메인 "생각 중" | 질문에 답하는 중인데 도구를 쓰지 않는 시간. 모델 내부를 본 것이 아님 | 훅 UserPromptSubmit~Stop |
| 웹 거리 건물 | 실제로 연 사이트(호스트 이름만). "일지" 표시는 하네스 작업 일지에 적힌 사이트 | 훅, DB `source_scan` |
| 금색 | 하네스 DB에 적힌 값과 시각(업무 시계, 작업 일지, 저장된 후보의 개수) | DB 읽기 전용 |
| 불편 구조화·기능 대조·콘셉트 작성 방의 숫자 | 이 Skill들은 도구 호출이 거의 없어, 저장된 후보에 담긴 불편·기존 기능·남은 불편·콘셉트 수를 저장 시각에 보여 준다 | DB `results` |
| 바닥 점선 | Skill 설명 순서(안내선). 실제 기록이 아님 | — |

승인은 저장 계약 검사 통과이며 원문 의미·효과를 자동으로 증명하지 않는다. 시각은 훅이 받은 시각이다. 모르는 값은 "미측정"으로 둔다.

화면 고치기: `app/`에서 `npm ci` 후 `npm run build` (타입 검사 → Vite 빌드 → `scripts/publish.mjs`가 JS·CSS를 넣은 `../index.html`
한 파일과 제3자 라이선스 고지를 만든다). `index.html`을 직접 고치지 않는다. 설치(`office.py install`)가 이 파일을 하네스로 복사한다.

## Codex 따라가기 (3단계)

Codex에는 이 장치의 훅을 넣지 않는다(설정·`/hooks` 신뢰를 바꾸지 않는다). 대신 Codex가 스스로 남기는 세션 기록
`CODEX_HOME/sessions/YYYY/MM/DD/rollout-*.jsonl`(기본 `%USERPROFILE%\.codex`)을 **별도 터미널에서** 읽는다.

```powershell
# 먼저 켜 두기: 새 Codex 세션이 생기면 따라간다 (그다음 하네스 폴더에서 codex를 열고 질문)
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py codex --harness C:/내-하네스-폴더 --wait
# --open: 새 세션의 첫 기록이 들어오면 사무실 화면을 브라우저로 한 번 연다 (심사위원 ZIP 원클릭 시작이 사용)
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py codex --harness C:/내-하네스-폴더 --wait --open
# 이미 연 세션: 이 폴더의 가장 최근 세션을 따라간다
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py codex --harness C:/내-하네스-폴더 --latest
# 지난 세션: 목록을 보고 파일을 골라 한 번에 옮긴다
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py codex-sessions --harness C:/내-하네스-폴더
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py codex --harness C:/내-하네스-폴더 --rollout <rollout 파일> --once
```

- 고르는 법: `--wait`는 명령을 켠 뒤 이 폴더에서 새로 시작된 세션, `--rollout`은 그 파일, `--latest`는 **세션 기록 첫 줄(session_meta)의 작업 폴더가 이 하네스인** 가장 최근
  메인 세션이다. 다른 폴더의 세션·하위 에이전트 기록은 거절한다. 신원(session_meta의 id)을 확인하기 전 줄은 쓰지 않고,
  아직 줄바꿈이 오지 않은 마지막 줄은 읽지 않는다(팀 `observer/`와 같은 규칙).
- 연구 역할: Codex는 하위 에이전트마다 기록 파일을 따로 만든다. 첫 줄이 고른 세션을 부모로 적은 파일만 따라가고,
  `agent_role`이 `product_official_researcher`·`product_review_researcher`·`product_evidence_reviewer`면 그 연구실에,
  아니면 "다른 하위 에이전트"로 적는다.
- 멈춤: Ctrl+C, `--until-complete`(메인 답변과 하위 에이전트가 모두 끝나면), `--max-minutes`(기본 180). 다시 실행하면
  이어서 읽고 같은 사건을 두 번 적지 않는다(`runtime-data/agent-office/codex-follow.json`, 파일 이름·위치만 저장).
- 남기는 것은 Claude 쪽과 같다: 시각(**Codex 기록의 시각**, `ts_basis: codex_log`), 스레드·turn·호출 ID, 도구 종류,
  `run.py` 경로의 Skill·작업 이름, 프로그램 이름, 폴더 구역, 웹 호스트, 종료 상태·오류 코드, 저장 승인/거절. 질문·답변·
  추론·명령·출력·검색어·주소 경로·파일 이름과 내용은 남기지 않는다. 밖으로 보내지 않는다(팀 observer의 Langfuse 전송 없음).
- Claude와 다른 점: Codex 0.162는 명령을 코드 실행 묶음(`exec`) 안에서 돌리고, 명령 하나하나의 기록
  (`item_completed`의 CommandExecution·웹 검색·MCP·파일 변경)을 **끝난 뒤에** 쓴다. 그래서 실시간 화면에서는 명령이 끝날 때
  실제 시작 시각부터 그려지고, 그동안 메인은 "Codex 코드 실행 묶음"으로 보인다. 팀 `observer/`는 `exec` 안을 보지 않아
  Skill·작업 이름이 나오지 않기 때문에, 같은 규칙으로 이 기록까지 읽는 별도 읽기 프로그램을 두었다.

## 결과 화면 연결

출고실을 누르거나 위쪽의 **결과 화면 열기**를 누르면 시각자료 뷰어(`web/prototypes/visual-viewer`)가 만든
`runtime-data/visual-viewer/index.html`이 열린다. 사무실 화면은 옆 폴더의 `view-data.js`를 4초마다 다시 읽어 export 이름·
만든 시각·상태만 보여 준다(나머지 내용은 읽지 않는다). 뷰어가 없으면(`viewer.py install` 전이거나 결과가 아직 없으면)
버튼 대신 안내가 나온다. 뷰어는 가장 최근 export를 그리므로 재생 위치의 결과와 다를 수 있다. 관측 장치의 DB 확인에는
가장 최근 export의 파일 이름(내용 지문)·시각·개수도 들어간다.

## 하네스 동작을 바꾸지 않는 이유

- 백그라운드 훅이라 Claude Code가 기다리지 않는다. 훅은 아무것도 출력하지 않고 항상 exit 0이라 도구 호출을 막거나 바꿀 수 없다.
- 모델·업무 Tool을 부르지 않는다. 기록은 `<하네스>/runtime-data/agent-office/`에만 쓴다(Git에 넣지 않는 폴더).
- 훅 명령은 설치 때의 `observe.py` SHA-256이 맞을 때만 실행하고, 관련 폴더가 심볼릭 링크·정션이면 실행하지 않는다
  (시각자료 뷰어 훅과 같은 방식). Windows에서는 PowerShell 실행기가 uv의 Python 3.12로 `observe.py`를 돌린다.
- DB(`runtime-data/product.sqlite`)는 `mode=ro`로 열고 최대 0.2초만 기다린 뒤 바로 닫는다. 바쁘면 건너뛴다
  (하네스는 5초 제한의 쓰기 잠금을 쓰므로 길게 읽으면 하네스 저장이 실패할 수 있다). 하네스의 상태 도구는 부르지 않는다.

## 남기는 것과 남기지 않는 것

`events.jsonl` 한 줄 = 훅 호출 한 번. 남기는 것: 시각(`ts`, 훅이 받은 시각), 세션·프롬프트·하위 에이전트 ID, 도구 이름,
`tool_use_id`, 사건 종류, 대상(역할·Skill), 작업 이름, 근거 구분, 걸린 시간(`duration_ms`가 있을 때), 웹 열람 사이트의
**호스트 이름**, product-tools 오류 코드, 그리고 확인용으로 입력 **필드 이름**(값 아님).

남기지 않는 것: 질문·프롬프트 원문, 명령 원문, 도구 출력, 파일 내용, 검색어, 웹 주소의 경로·검색 조건, 파일 경로
(Skill 설명서 이름만 예외). DB에서는 최신 요청의 질문(최대 300자), 업무 시계, 작업 일지 종류·시각(사이트는 호스트만),
turn 상태·수정 횟수, 후보 수, 전달·검토한 근거 수, 취소 여부만 읽는다.

| 사건 `kind` | 무엇을 보고 | 근거 `basis` |
| --- | --- | --- |
| `delegate` | `Agent`(예전 이름 `Task`) 도구의 `subagent_type`이 연구 역할 | `observed` |
| `subagent` | SubagentStart/SubagentStop의 `agent_type` | `observed` |
| `skill_op` | Bash·PowerShell 명령의 `skills/<skill>/scripts/run.py <작업>` | `command_based_mapping` (실행 성공·의미 검토의 증거 아님) |
| `skill_load` | `Skill` 도구, `skills/<skill>/SKILL.md` 읽기 | `instruction_loaded` |
| `web` | WebFetch(호스트만)·WebSearch | `observed` |
| `request`·`turn_end`·`session` | UserPromptSubmit·Stop·SessionStart/End | `observed` |
| `shell` | 위가 아닌 셸 명령. 명령 원문 대신 각 부분의 첫 단어가 정해진 목록(ls·cat·python·Get-ChildItem 등)에 있을 때 그 이름만, 하네스의 `product-doctor.py`는 "설치 점검", 그 밖은 `other` | `observed` |
| `file` | Read·Write·Edit·Grep·Glob이 다룬 **폴더 구역**만(작업 기록·결과 내보내기·웹 근거 보관·문서·Skill 폴더·하네스 밖 등). 파일 이름은 남기지 않는다 | `observed` |

하위 에이전트 안의 도구 사건은 Claude Code가 주는 `agent_id`와 `agent_type`이 모두 있을 때만 그 역할의 행동으로 적는다.
호출 순서·시간 겹침으로 위임·메시지 관계를 만들지 않는다. 미측정 값은 0이 아니라 비워 둔다.

`office.py trace <하네스> --out trace.json`은 기록을 팀원 관제실의 사건 필드(`id, at, kind, source, target, label, detail,
status`)에 시각·근거를 더한 `mode: "observed"` JSON으로 바꾼다.

## 아직 확인하지 않은 것

- 실제 Claude Code 2.1.289 실행에서 필드 이름(특히 `Skill` 도구 입력, PostToolUse의 `tool_use_id`)과 하위 에이전트 사건이
  문서대로 오는지. 기록의 `keys`·`input_keys`로 확인한다.
- 백그라운드 PreToolUse가 모든 버전에서 지원되는지(문서에 사건별 목록이 없다). 지원되지 않아도 막지는 않는다.
- 연구 역할이 실제 업무에서 쓰인 실행과 저장이 승인된 실행은 아직 실제 기록으로 보지 못했다(데모와 합성 시험으로만 확인).
- 사양이 낮은 PC에서의 화면 속도. 브라우저가 WebGL을 쓰지 못하면 3D 화면이 나오지 않는다.
- Codex: 실제 0.162.1 기록(이 PC의 지난 세션 3개)으로 명령·웹·MCP·파일 기록을 확인했다. v0.10.0 연구 역할을 쓴 실제 Codex
  실행은 아직 보지 못했다. 하위 에이전트 기록에서 역할 이름이 `agent_role`(또는 `source.subagent.thread_spawn`)에 온다는 것은
  합성 기록으로만 시험했다.
