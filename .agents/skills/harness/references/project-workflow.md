# 프로젝트 개발 실행 계약

부모는 요구/결정/작업 원본과 diff를 읽고 필요한 작업만 계획한다. 작업에는 id, role, dependencies, ownership, inputs, context.skill_paths, acceptance, required, max_attempts가 필요하다. 시간/호출 상한·중단 조건은 acceptance에 명시한다. 역할 TOML 자체도 inputs에 넣어 변경 시 무효화한다.

장부 원본은 upstream이며 `python dev-harness/cli.py ledger <명령>`이 경로와 완료 검사 receipt를 보강한다. `ledger init --plan-file .harness/plan.json --run-id NAME`, `ledger ready --run NAME` 후 실제 native 생성 ID를 `ledger start`에 기록한다. `packet --run NAME --task ID`가 역할 지침과 최신 input.md를 출력한다. native followup_task 또는 노출된 위임 도구로 packet을 전달한다. 문서만 출력한 것은 위임이 아니다.

통신은 scripts/communication.py로 recorded를 기록한 뒤 실제 native 전송을 수행하고 응답을 관찰해 sent/failed/received로 남긴다. 읽기 전용 역할은 부모에게 로그를 요청한다. helper는 메시지를 보내지 않는다.

검사는 `check --run NAME --task ID --input path -- command args`로 실행한다. JSON result의 required checks에는 name과 receipt(프로젝트 상대 경로)를 넣는다. completed 결과는 `ledger result`가 receipt의 실제 exit code, 상태, 로그·입력 지문을 확인해 upstream evidence로 변환한다. 로컬 감사 기록이며 보안상 위변조 방지 서명이 아니다.

실제 final/idle 관찰은 ledger agent --state idle로 기록한다. interrupt는 turn 중단이고 세션 closure가 아니다. closed는 실제 close 응답이 있는 runtime에서만 기록한다. idle 세션을 재사용하고 전체 등록 한도를 존중한다.

완료 전 `python dev-harness/cli.py complete --run NAME`으로 현재 receipt와 장부를 다시 검사한다. task/attempt/contract binding과 검사시각을 확인해 다른 작업 검사의 재사용을 거부한다. 실제 명령이 실행됐다는 사실만으로 해당 acceptance의 의미를 충족하는 것은 아니므로 독립 리뷰가 명령·관련 입력·검사 범위를 대조한다. 실제 검사·독립 리뷰·입력 freshness를 확인한다. resume은 이전 실행을 보존하며 변경 입력·산출물·계약의 결과와 후속 작업을 다시 실행한다. 개발 usage와 출품 usage를 분리하고 미측정은 unknown이다.
