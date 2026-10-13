# LG AX 기획 사무실 · 관측 장치 (1단계)

하네스가 **지금 무엇을 하고 있는지** 보여 줄 "기획 사무실" 화면의 첫 단계다. 이 단계는 화면 없이 **관측 기록**만 만든다.
Claude Code의 훅으로 도구 시작·끝, 연구 역할 위임·반환, 어느 Skill의 어느 작업인지를 시각과 함께 남기고, 하네스 DB를
읽기 전용으로 잠깐 확인해 작업 일지·후보 저장 상태를 함께 적는다. 3D 사무실 화면은 다음 단계에서 이 기록을 읽는다.

기준은 product v0.10.0(메인 1 · 선택 연구 역할 3 · 업무 Skill 6)이다. 역할·Skill 이름은 팀원 관제실
(`codex/control-room-v0.10.0`의 `src/catalog.ts`)과 같은 id를 쓴다.

## 설치 (하네스마다 한 번)

이 레포 폴더에서, 설치된 하네스 폴더 경로를 적는다.

```powershell
uv run --no-project --python 3.12 python web/prototypes/agent-office/office.py install --claude C:/내-하네스-폴더
```

- `observe.py`·`office.py`·`README.md`를 `<하네스>/web/prototypes/agent-office/`에 복사하고, `.claude/settings.local.json`에
  백그라운드(async) 훅 9개를 **추가**한다: PreToolUse·PostToolUse·PostToolUseFailure(모든 도구), UserPromptSubmit, Stop,
  SubagentStart, SubagentStop, SessionStart, SessionEnd. 다른 훅(시각자료 뷰어 등)과 설정은 그대로 둔다.
- 설정이 UTF-8 JSON 객체가 아니면 아무것도 바꾸지 않고 멈춘다. 개발 레포(`dev-harness` 폴더가 있는 곳)에는 설치하지 않는다.
- 다시 설치하면 이 장치의 훅만 새것으로 바뀐다. 끄기: `office.py uninstall --claude <폴더>` (기록 파일은 남긴다).
- 확인: `office.py status --claude <폴더>` · 실시간 보기: `office.py watch --claude <폴더>`(새 기록을 한 줄씩 한글로 출력, 읽기만 함) · 자체 시험: `office.py selftest`(임시 사본에서 실제 훅 명령을 합성 입력으로 실행).

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

하위 에이전트 안의 도구 사건은 Claude Code가 주는 `agent_id`와 `agent_type`이 모두 있을 때만 그 역할의 행동으로 적는다.
호출 순서·시간 겹침으로 위임·메시지 관계를 만들지 않는다. 미측정 값은 0이 아니라 비워 둔다.

`office.py trace <하네스> --out trace.json`은 기록을 팀원 관제실의 사건 필드(`id, at, kind, source, target, label, detail,
status`)에 시각·근거를 더한 `mode: "observed"` JSON으로 바꾼다.

## 아직 확인하지 않은 것

- 실제 Claude Code 2.1.289 실행에서 필드 이름(특히 `Skill` 도구 입력, PostToolUse의 `tool_use_id`)과 하위 에이전트 사건이
  문서대로 오는지. 기록의 `keys`·`input_keys`로 확인한다.
- 백그라운드 PreToolUse가 모든 버전에서 지원되는지(문서에 사건별 목록이 없다). 지원되지 않아도 막지는 않는다.
- Codex 연결(팀 `observer`의 기록 읽기)과 3D 화면은 다음 단계다.
