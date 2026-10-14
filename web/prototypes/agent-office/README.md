# LG AX 기획 사무실 · 관측 장치와 3D 화면

하네스가 **지금 무엇을 하고 있는지** 보여 주는 "기획 사무실"이다. 두 부분으로 되어 있다.

1. **관측 장치** (`observe.py`, `office.py`): Claude Code의 훅으로 도구 시작·끝, 연구 역할 위임·반환, 어느 Skill의 어느
   작업인지를 시각과 함께 남기고, 하네스 DB를 읽기 전용으로 잠깐 확인해 작업 일지·후보 저장 상태를 함께 적는다.
2. **사무실 화면** (`index.html`, 원본은 `app/`): 그 기록을 3D 사무실로 보여 준다. 방이나 사람을 누르면 하는 일·지금 상태·
   지금까지의 기록이 나온다. 실시간 보기와 기록 재생을 할 수 있다.

기준은 product v0.10.0(메인 1 · 선택 연구 역할 3 · 업무 Skill 6)이다. 역할·Skill 이름은 팀원 관제실
(`codex/control-room-v0.10.0`의 `src/catalog.ts`)과 같은 id를 쓴다.

## 설치 (하네스마다 한 번)

이 레포 폴더에서, 설치된 하네스 폴더 경로를 적는다.

```powershell
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py install --claude C:/내-하네스-폴더
```

- `observe.py`·`office.py`·`README.md`·`index.html`을 `<하네스>/web/prototypes/agent-office/`에, 화면(`index.html`)을
  기록 옆 `<하네스>/runtime-data/agent-office/`에 복사하고, `.claude/settings.local.json`에
  백그라운드(async) 훅 9개를 **추가**한다: PreToolUse·PostToolUse·PostToolUseFailure(모든 도구), UserPromptSubmit, Stop,
  SubagentStart, SubagentStop, SessionStart, SessionEnd. 다른 훅(시각자료 뷰어 등)과 설정은 그대로 둔다.
- 설정이 UTF-8 JSON 객체가 아니면 아무것도 바꾸지 않고 멈춘다. 개발 레포(`dev-harness` 폴더가 있는 곳)에는 설치하지 않는다.
- 다시 설치하면 이 장치의 훅만 새것으로 바뀐다. 끄기: `office.py uninstall --claude <폴더>` (기록 파일은 남긴다).
- 확인: `office.py status --claude <폴더>` · 화면 열기: `office.py open --claude <폴더>` · 글로 보기: `office.py watch --claude <폴더>`(새 기록을 한 줄씩 한글로 출력, 읽기만 함) · 자체 시험: `office.py selftest`(임시 사본에서 실제 훅 명령을 합성 입력으로 실행).

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
- Codex 연결(팀 `observer`의 기록 읽기)은 다음 단계다.
