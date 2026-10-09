# 개발 체계 사용·검사·인수인계

Codex 부모가 작업을 관리하며 helper는 기록·검사를 담당한다. Claude는 별도 네이티브 실행을 사용한다. [검증 상태](validation/development-harness.md)와 [작업 목록](plans/development-harness.md)을 먼저 확인한다.

## 환경

Python 3.12.x, uv와 로그인된 개발 도구가 필요하다. `uv sync --locked` 후 `uv run python dev-harness/cli.py doctor`로 파일·동기화·OSS 지문을 검사한다. Windows에서 한국어 파일은 `Get-Content -Encoding utf8` 또는 UTF-8 명시 reader로 읽는다. 모델·추론·인증은 사용자 개발 환경을 상속하며 전역 설정을 수정하지 않는다.

## 역할과 Skill 선택

메인은 요구/결정/작업 목록/diff를 읽고 objective, requirement_ids, inputs_and_fingerprints, role, skill_paths, owned_paths, read_only, dependencies, acceptance_commands, expected_artifacts, time_and_call_limits, stop_conditions를 배정한다. 필요한 역할만 사용한다. 읽기 전용 분석자·설계자·리뷰어는 결과를 반환하고 부모가 문서와 기록을 쓴다. 작성 병렬화는 독립 worktree에서 한다.

Codex custom role 도구가 있으면 해당 역할을 선택한다. 현재 설치환경은 역할 선택 인수를 노출하지 않아 TOML developer_instructions + 필요한 Skill + 최신 packet을 `collaboration.spawn_agent`/`followup_task` 메시지로 전달한다. 실제 반환 ID만 기록한다. runtime의 close가 없는 상황에서 interrupt를 closed로 바꾸지 않는다. idle 세션을 재사용한다. fallback이 TOML sandbox 설정을 자동 적용하는 것은 아니다.

## 작업 장부와 실제 검사

메인이 프로젝트 안에 JSON plan을 작성한다. 각 task에는 id/role/dependencies/ownership/inputs/context/acceptance/required/max_attempts가 있다. 아래는 형식 예이며 실제 command와 파일은 배정한 작업에 맞춘다.

```json
{"objective":"새 업무 Tool 구현","tasks":[{"id":"tool","role":"data_tool_worker","dependencies":[],"ownership":["tools/"],"inputs":["docs/plans/product-harness.md",".codex/agents/data_tool_worker.toml"],"context":{"decisions":["한 작성자, 10분 상한"],"skill_paths":[".agents/skills/implement-and-check/SKILL.md"]},"acceptance":["정상·timeout·근거 부족 사례 실제 검사"],"required":true,"max_attempts":2}]}
```

```powershell
uv run python dev-harness/cli.py ledger init --plan-file .harness/plan.json --run-id RUN
uv run python dev-harness/cli.py ledger ready --run RUN
# 실제 네이티브 생성이 반환한 ID를 사용한다.
uv run python dev-harness/cli.py ledger start --run RUN --task TASK --agent-id ACTUAL_ID
uv run python dev-harness/cli.py packet --run RUN --task TASK
# 위 packet과 역할 지침을 실제 native 위임 도구로 전달한다.
uv run python dev-harness/cli.py check --run RUN --task TASK --input RELEVANT_FILE --timeout 120 -- ACTUAL_COMMAND ARG
```

check는 shell=False argv로 실제 실행하며 stdout/stderr/receipt를 `.harness/checks`에 저장한다. 실패·timeout·not_run·output_limit은 완료 근거로 통과하지 않는다. 출력은 종료 후 지정 크기로 잘라 보존하고 output_limit으로 표시한다. 실행 중 디스크 quota를 강제하는 기능은 아니다. Windows 후손 종료가 실패하면 error에 기록하며 직접 프로세스 종료를 시도한다.

검사 receipt는 run/task/attempt/actual agent/contract와 시작 시각, 입력 파일·로그 지문을 연결한다. 다른 task/attempt 검사와 입력 변경·로그 변경을 거부한다. 올바른 명령이 acceptance 의미를 충분히 검사하는지는 독립 리뷰에서 확인한다. 로컬 기록은 서명된 보안 증명이 아니다.

result JSON의 completed checks에는 name/required/receipt를 넣는다. run_id, task_id, status, summary, artifacts, checks, issues를 포함한다. 산출물은 기존/현재 mutable plan·registry·result 파일을 담지 않는다.

```powershell
uv run python dev-harness/cli.py ledger result --run RUN --task TASK --result-file .harness/result.json
# 실제 final/idle을 관찰한 뒤 기록한다.
uv run python dev-harness/cli.py ledger agent --run RUN --agent-id ACTUAL_ID --state idle --evidence ACTUAL_OBSERVATION
uv run python dev-harness/cli.py complete --run RUN
```

complete는 upstream 장부 검사와 현재 receipt를 다시 확인한다. upstream `validate.py --complete` 단독은 receipt 재검증을 대신하지 않는다. 완료 후 근거가 바뀌면 `ledger resume --run RUN --new-run NEW_RUN`으로 이전 기록을 보존하고 변경 결과·후속 작업을 재실행한다. wrapper는 손상/오래된 receipt의 작업 계약도 무효화한다. 실패·blocked 결과에도 실제 check status와 evidence를 명시한다.

`communication.py`는 observed 통신을 recorded→실제 native 전송→sent/failed→received 순서로 기록한다. 기록 helper가 메시지를 보내지 않는다. 읽기 전용 역할은 부모에게 로그를 요청한다. 세부 형식은 [실행 계약](../.agents/skills/harness/references/project-workflow.md)을 읽는다.

## 확인 명령

```powershell
uv run python dev-harness/cli.py validate
uv run python dev-harness/cli.py sync-claude --check
uv run python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/dev-harness -v
```

검사는 실제 exit code를 남긴다. 단위 검사의 synthetic agent ID와 native 인수검사의 실제 ID를 구분한다. 현재 검사 수·근거는 [검증 기록](validation/development-harness.md)을 따른다. CI Windows/Ubuntu workflow는 구성했으며 원격 실행 여부는 별도로 확인한다.

## Claude 인수 절차

Codex 작업 종료 후 요구/결정/작업 목록/diff/실제 checks/남은 문제를 전달한다. `uv run python dev-harness/cli.py sync-claude` 후 drift를 검사한다. Claude 팀원은 새 세션에서 `/harness` 발견, 필요한 `.claude/agents` 역할 호출, 작은 신규 fixture 작업·실제 command/exit/receipt, 독립 리뷰, Codex 결과 인수·추가 실행을 확인한다. 로그는 Git 밖에 보존하고 관찰 ID/도구/시각을 기록한다. Claude native 상태와 Codex registry의 동등 매핑을 검증 전에 가정하지 않는다. 현재 PC에 Claude CLI/인증 환경이 없어 이 native 인수는 미실행이다.
