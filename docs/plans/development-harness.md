# 개발용 하네스 구축 계획과 작업 원본

## 추가 요청 회귀·일반 입력 — 2026-10-11

Claude 회신을 [접수·독립 검토](../validation/team-runs/records/20261011-claude-mail-review.md)했다. v0.3.0의 네 입력/세 업무 session·export4개에서 초안3/보류1·후속 이력·출처를 대조했다. 최초 중복 판단 모순과 공식 문구 귀속 오류를 후속 보완 항목으로 남긴다. 아래 회신 대기는 과거 상태이며 최신 v6.1 Claude 제품군 검증·전체 최종 전달/DB/요청별 usage·개발용 D06b 인수는 별도 미완료다. 이번 접수는 제품 변경·재실행·새 릴리스가 아니다.

[공개50입력](../evaluation/regression50.md)의 실제 v6.0 Codex50입력/40대화·최종/저장 감사·독립 원문 의미 검토를 완료했다. [결과](../validation/regression50-20261011.md): completed18/held27/needs_input5, 정의한 판정50/50. 경계 힌트가 있는 알려진 자료 검증이며 미사용/일반 품질·효과·전체 청구의 완료로 바꾸지 않는다. 입력 범위를 고정하고 자동 재시도하지 않았다.

제품군 일반명·축약명·후속 전체 scope 유지와 명시 모델 좁히기를 v6.1에 구현했다. 제품147·평가117개 일반 코드 검사와 asset 검사는 실제 exit0다. [별도10입력](../validation/family10-20261011.md)은 실제 실행/독립 의미 검토/저장 감사를 완료했다(completed4/held3/needs_input3). v6.0의50개와 합쳐 현재 버전 성공률로 표시하지 않는다. v0.4.0 제품 소스 ZIP의68파일/67manifest·새 폴더 locked 설치/doctor·Claude 사본 설치를 검증했으며 이후 최종 통합검토·task-bound 감사·독립 검토·장부 complete errors=[]와 [v0.4.0 제품 시험판 배포/원격·다운로드 대조](../validation/product-v0.4.0.md)를 완료했다. Claude native 실행은 미검증이다.

웹 원본은 사용자 확인으로 아직 원격에 없고 팀 개발 진행은 유지한다. [카톡/스크린샷·기본 자료 검토](../validation/web-data-analysis-20261011.md)의 최신 조사·새 모델 등록·질문 실행 제안은 미채택이다. 현재 저장 자료 우선·등록5모델의 실제 지원 한계를 유지한다. 제품군 입력 지원은 새 모델 자동 조사/등록을 포함하지 않는다.

## 새 범위 작업 — 2026-10-11

**현재 완료:** 세 family 정확 계약·실제 v4 자료5모델/8후기/26사실·새4입력/3세션·225코드 검사·독립 원문/최종 검토·12쪽 발표 초안·제품 v0.3.0만 배포/재다운로드 확인. 최길웅 Claude 검증 메일은 사용자 초안 승인 후 발송했고 정이량 회신을 기다린다. [완료 근거와 다음 인수](../validation/product-v0.3.0.md)를 따른다. 아래 과거 체크박스/검사 수는 해당 시점의 기록이다.

**남은 현재 작업:** 두 창30초 실제 녹화→시연 영상→실측10분 리허설; Claude 검증/사람 공수/웹 원본 회신 각각 인수; 운영진 실제 파일 규격·마감/경로·가산점 공지 확인; 최종 지원 범위/버전 동결·새 실행자 재현·업로드/접수. 이미 마감한 오류/자료 수정 단계를 반복하지 않는다.

이전 v5.5 수정 마감은 유지한다. 이번 작업은 사용자 요청에 따른 새 제품군/근거/산출물 변경이다: 세 제품군 계약과 실제 v4 자료 → 최대4입력 신규 native 인수/독립 검토 → 평가항목 발표자료/시연 근거 → 제품만 새 시험판 배포. Gemini 인수는 폐기하고 Claude는 하네스 보완 완료 후 최길웅에게 요청·정이량에게 회신하는 후순위다. 웹팀 개발 중/원본 미수신을 기록하고 프런트엔드는 PM에게 맡긴다. 최종 촬영/리허설·사람 시간·운영진 실제 제출은 실제 증거가 필요하다.

기준일: 2026-10-11. 이 문서는 개발 체계 구축의 작업 상태 원본이다. 출품 구현의 실행 계약은 [product-harness.md](product-harness.md), 기술 결정은 [stack-selection.md](../decisions/stack-selection.md), 공식·사용자 요구는 [competition-requirements.md](../competition-requirements.md)를 따른다.

현재 선택: 출품은 공통 업무 Skill·코드를 Codex에 연결하며 Claude는 후순위 검증한다. Gemini 지원은 2026-10-11 철회했다. [실행 결정](../decisions/product-runtime.md)을 따른다. 자체 모델 API 프로그램과 Codex 내부 호출 실행기는 초기 경로로 채택하지 않는다. 구조·실행 시각화는 후순위의 [별도 관찰 프로그램](observability-viewer.md)에서 제공한다.

Codex 개발 체계 D01-D05는 검증했다. S05의 이번 제한 평가·수정과 자료 조사 단계는 [2026-10-11 마감 기록](../validation/closure-progress-20261011.md)의 범위로 종료했다. 현재 내부 우선순위는 별도 관찰 화면/실제 녹화 → 발표/영상 → 최종 제출 재현이다. 일반 품질·효과·사람 공수와 D06b Claude 개발 인수는 별도 미완료이며 시각화를 과거 개발 체계/평가 인수의 선행 조건으로 소급하지 않는다. Codex/Claude 실행에 React Flow UI를 연결하는 후보는 현재 채택하지 않았다.

## 현재 단계 — 수정 마감과 다음 작업

[수정 마감 계약](../evaluation/closure-protocol-20261011.md)에 따라 v5.5의 웹 절별 출처·경험/선호/기대·평가 제약 전달을 수정하고 신규 입력 최대4개로 한 차례만 평가한다. 결과는 [마감 기록](../validation/closure-progress-20261011.md)을 따른다. 이 단계에서 추가 외부 자료 검색·baseline·통과할 때까지 AI 재실행을 하지 않는다.

이번 3모델 자료 조사 단계는 종료한다. 청소 불편·내부 유효 치수·선반 간격은 확보하지 못한 근거이며 보류 기능을 유지한다. 실제 효과·사람 시간·청구·팀 원본·Claude/Gemini native 인수는 외부 근거/접근이 필요한 별도 미완료다. 조사·평가의 종료를 해당 근거 확보나 전체 대회 요구 완료로 바꾸지 않는다.

이후 개발 순서는 별도 관찰 화면의 가독성·누락/장애·실제 녹화 준비 → 발표/영상 제작 → 제출 재현이다. 새 구체적 결함이나 입력/근거 변경이 없으면 종료한 코드 검사·자료 조사·평가를 반복하지 않는다. 팀원 로컬 웹 코드 분석은 제외한다.

## 2026-10-11 요청한 1–7번의 수행 결과

이후 사용자가 요청한1·2·3·6번은 [별도 v5.4 동결 실행·검토](../validation/focused-progress-20261011.md)와 [9입력 사전 계약](../evaluation/focused-protocol-20261011.md)으로 기록한다. 팀원의 로컬 웹은 사용자가 건너뛰라고 하여 이번 범위에서 제외한다. 아래12입력과 최신9입력을 하나의 성공률·절감률로 합치지 않는다.

[최신 실행·검토 기록](../validation/seven-task-progress.md)에 실제12입력/11세션·실패/timeout·수정 계약·248검사·팀 메일 발송을 정리했다. save/export 통합과 조건부 초안 검토·실제 설명서 연계·사람 측정 도구를 구현했다. 총 토큰/지연 우위는 미입증이며 업무 AI 웹 최종 timeout, Claude/Gemini 인증, 사람 측정·전체 청구·청소 불편/내부 치수 원문은 미완료다. 기존 체크박스를 모두 완료로 바꾸지 않는다. 다음은 팀 회신 검토와 웹 지연/실제 근거·지원 환경 인수이며 영상/UI는 후속이다.

## 이전 작업 순서 — 2026-10-10 당시 기록

아래 표는 당시 계획 이력이다. 현재 남은 목록으로 다시 제시하지 않고 위 현재 단계와 최신 마감 기록을 따른다.

토큰 절감의 구현/실측/미검증과 별도 화면의 연결·표시·장애 대책을 [토큰 표시 원본](../evaluation/token-measurement.md)·[관찰 계획](observability-viewer.md)·[시연 절차](../../submission/demo-runbook.md)에 구체화했다. 이후 v5.2 개선·8입력 평가·팀 Issue 접수·실제 browser 등록·collector/Langfuse 연결을 추가했다. [최신 평가](../validation/s05-v52-flow.md)·[관찰 인수](../validation/observer-langfuse.md)·[native 접근](../validation/native-access-20261010.md)을 따른다. 전체 청구·사람 공수·다중 환경 인수·영상 완료는 아니다. 아래 순서는 다음 작업의 우선순위이고 상세 D/S 체크박스의 실제 상태를 대체하지 않는다.

| 순서 | 남은 작업/연결 ID | 완료에 필요한 실제 근거 |
|---|---|---|
| 1 | 최종 응답 지연·거절 후보 복구: S05c6, T06a | 저장 뒤 반복 대조/큰 최종 JSON을 단계별 관측하고 승인/거절·제한 내 수정/보류·최종 답변 일치를 유지해 J17 두 조건을 bounded 재검증. 기존 양쪽 timeout은 보존 |
| 2 | 팀원 결과 접수·환경별 인수: S05d2, S02b2/S02c2, D06b | 이미 실행한 대겸·진하의 결과 원문·CLI/모델·입력/출력·저장·usage를 받아 검토. 사용자 완료 보고를 native 지원 통과로 바꾸지 않으며 D06b 개발 인수는 별도 |
| 3 | 실제 자료와 웹 수집/native import: S01d2, S03b | 청소 불편·정확 내부 치수/선반 간격 확보 여부, 실제 웹/브라우저 수집→버전 등록→업무/후속 연결. 동일 원문 진단 복제를 신규 웹 관측으로 사용하지 않음 |
| 4 | 토큰·품질·업무 효과 검증: S05c4, T06b/T06c | 동일 자료·모델·설정·성공 기준의 제한된 반복/미사용 질문·동등 baseline, 하위/실패/수정 포함 관측 범위·전체 청구·사람 활동 시간. 샘플 절감과 일반 우위를 구분 |
| 5 | 별도 관찰 연결: S04, O01a-O04a, T06d | 저장 기록1건→OSS 완료 trace/usage→본 실행 관찰, native ID/Skill/Tool 상태/부분사용량/지연·중복·단절 검사. 추가 모델 요청/프롬프트0와 업무 격리. S05의 선행 조건으로 두지 않음 |
| 6 | 발표 자료·영상 제작: S06b, O06a | 콘티/대본·HTML 구조/실측 차트·30초 두 창 녹화 시험→실제 정상/보류/후속 영상·오디오/자막/출력·10분 리허설. 생성 연출/구조 설명/실행 기록 조회 구분 |
| 7 | 최종 지원·제출·제품 릴리스: S06 | 새 지원 환경 native 재현, 실제20페이지/시간·영상 규격/마감/경로/파일명·변경 공지 확인. 의미 있는 제품/완성 제출물 변경 때만 새 릴리스 |

토큰 절감에는 필요 Skill 로딩·bundle/원문 재사용·일반 코드 캐시/검사·저장 통합·export 재독해 억제가 이미 반영돼 있다. 조회 캐시는 모델 토큰 절감 보장이 아니며 최종 v5.2의 R01 각2회는 일반 비교보다 입력/비캐시가 더 많아 절감·전체 비용/공수 우위는 미입증이다. Langfuse 실제 연결은 완료했으며, 모든 노드·토큰이 즉시 표시된다는 약속이나 자체 React Flow 채택은 하지 않는다.

## 목표와 현재 상태

사용자의 자연어 요청을 받아 실제 역할 배정, 구현, 데이터·Tool 연결, 심사 입력 평가, 독립 검토, 제출 근거 정리까지 진행하는 Codex 중심 개발 체계를 만든다. 팀원의 Claude Code에도 같은 업무 계약을 연결한다.

Codex 중심 개발 체계 D01-D05를 구축·실증했다. OpenSpec을 제거하고 6개 역할·9개 Skill·고정 OSS 장부·Python 실제 검사/receipt/완료/resume wrapper·Claude adapter를 만들었다. 실제 작은 신규 구현을 native 위임→Temp 구현→부모 통합/검사→독립 리뷰→완료로 연결했다. [실제 검증과 제한](../validation/development-harness.md)을 따른다. Claude native 인수와 출품 프로그램 구현은 별도 미완료다.

## OSS 도입과 OpenSpec 교체

`revfactory/codex-harness`의 커밋 `80f8217b5b6d3f220a31f05f9c0adaf09dac40f4`를 도입 기준으로 고정한다. Apache-2.0 LICENSE, NOTICE가 있으면 그 원문, 도입 파일 목록, 원본 SHA·파일 지문, 프로젝트 수정 내역을 보관한다. upstream을 설치 후 자동 업데이트하지 않는다.

도입할 기능은 메인 Skill·역할의 기본 실행 계약, `run.py`/관련 상태·검사 모듈, `communication.py`, 필요한 생성·검증 도구다. 각 모듈의 내부 import를 확인해 필요한 원본을 함께 가져온다. 이미지·과거 Claude 구성·예제 전체·벤치마크는 개발 실행에 필요하지 않으면 도입하지 않는다.

중요한 경계:

- `run.py`는 작업 장부다. Agent를 실행·중단하는 프로그램으로 설명하지 않는다.
- `communication.py`는 관측한 통신을 명시적으로 기록한다. 메시지를 전달하거나 모든 통신을 자동 수집하지 않는다.
- `run_checks.py`는 기록된 검사 근거를 검증한다. 실제 검사 명령 실행은 별도 Python 실행기가 맡는다.
- 실제 생성·위임·상태 확인·중단은 Codex 네이티브 도구가 수행하고, 반환된 실제 ID·상태를 장부와 연결한다.
- 작업 소유권 필드는 파일별 ACL이 아니다. 한 checkout의 작성자 한 명 원칙 또는 독립 worktree로 충돌을 방지한다.

Windows 캐시 checkout의 `.agents/skills/harness`가 symlink 대신 일반 파일로 남은 상태를 확인했다. 원본 `skills/harness/`를 정규 파일로 도입하고 경로·파일 지문을 검사한다. symlink 권한이나 해당 파일을 디렉터리로 읽는 upstream installer의 성공을 가정하지 않는다.

OpenSpec은 새 체계에서 사용하지 않는다. 작업 명세 기능을 요구·설계·작업 문서로 유지하되 다른 작업 관리 프레임워크를 다시 겹쳐 설치하지 않는다. 제거 대상은 다음과 같다. D01에서 실제 경로·diff를 확인해 제거했다. 최초 재귀 삭제는 자동 검토에 차단되어 파일별 패치와 repo 경계 확인을 거친 빈 디렉터리 비재귀 삭제로 수행했다.

- `openspec/` 전체.
- `.agents/skills/openspec-*`, `.agents/skills/.openspec-target`.
- `.claude/skills/openspec-*`, `.claude/commands/opsx/`.
- 기존 `dev-harness/*.mjs`, `tests/dev-harness/workflow.test.mjs`의 OpenSpec 기반 체계.
- OpenSpec 전용 루트 `package.json`, `package-lock.json`, npm 명령·의존성. 새 자체 시각화 웹 프로젝트를 기본으로 만들지 않는다.
- 기존 CI·안내·third-party notice의 활성 OpenSpec 절차를 새 체계에 맞게 교체.

과거 작업·검사 이력은 Git과 문서의 과거 상태 기록으로 남긴다. 사용자 전역 Skill·설정·다른 LG 레포를 삭제하지 않는다. 재귀 파일 작업 전 최종 절대 경로가 이 레포 안에 있는지 확인한다.

## 메인 오케스트레이터

메인은 현재 Codex 부모 세션이며 별도 고정 모델이나 새로운 서버가 아니다. 사용자 요구를 해석하고 작업 의존성·소유 범위를 나눈 뒤 필요한 역할만 생성한다. 공통 인터페이스 변경, 코드 통합, 실제 검사 결과와 독립 리뷰를 반영한 완료 판정을 전담한다.

작업 시작 시 전달할 최소 계약:

```text
task_id, objective, requirement_ids, inputs_and_fingerprints,
role, skill_paths, owned_paths, read_only,
dependencies, acceptance_commands, expected_artifacts,
time_and_call_limits, stop_conditions
```

결과 계약:

```text
task_id, actual_agent_id, status,
changed_files, artifacts, input_fingerprints,
checks[{command,exit_code,report_path,executed_at}],
findings, unresolved_items, usage{measured|unknown}
```

없는 실행 ID·토큰·검사 결과를 만들어 기록하지 않는다. 입력이 변경된 결과는 재사용 여부를 판단하고 오래된 결과를 자동 완료 처리하지 않는다. 같은 오류를 이유 없이 반복하지 않는다. 독립 작업은 병렬 처리하되 기본 자식 실행 상한은 3개로 계획하고 실제 환경의 한도를 존중한다.

## 개발 서브에이전트 6개

개발 역할은 출품용 Agent 수와 관계없다. 모든 역할을 매 작업마다 실행하지 않는다. 모델·추론 설정은 팀의 개발 도구 설정을 기본으로 따르고 역할마다 비싼 모델을 고정하지 않는다.

| 역할 / 파일 이름 | 책임 | 기본 작성 범위 | 주로 읽는 Skill |
|---|---|---|---|
| `requirements_analyst` | 공식 요구·팀 아이디어·심사 입력·제출 근거 연결 | 읽기 전용 분석 반환; 부모가 문서 통합 | competition-intake, submission-and-demo |
| `harness_architect` | 상태·Skill·Tool·모델·예외·예산 계약 | 읽기 전용 설계; 부모가 결정 통합 | harness-design, data-evidence-contract |
| `agent_skill_worker` | 선택한 실행 방식의 업무 Skill·실행 코드·관찰 어댑터 구현 | 배정된 runtime/skills/관찰 연결 파일 | agent-skill-authoring, implement-and-check |
| `data_tool_worker` | 신규 데이터·조회·ID/버전·원문 위치·재사용 규칙 | 배정된 data/tools/evidence 파일 | data-evidence-contract, implement-and-check |
| `evaluator` | 실제 AI 입력 평가·사용량 감사·예외·시연 일치 | 배정된 evals/tests/검사 산출물 | evaluate-harness |
| `reviewer` | 누락·회귀·근거 오류·구현/주장 불일치 독립 검토 | 읽기 전용 | review-change |

관찰 어댑터는 일반 코드로 구현한다. 시각화용 Agent·Skill·추가 LLM 호출을 실행 체계에 넣지 않는다. 토큰 분석 전용 Agent도 매 출품 실행에 추가하지 않는다. 제출 문서는 분석자와 메인이 `submission-and-demo`를 사용해 정리한다.

## 개발 Skill 9개

공통 원본은 `.agents/skills/`다. 메인 `harness`는 upstream 기반으로 프로젝트 목적·계약을 적용하며, 아래 8개는 신규 프로젝트에 필요한 개발 Skill로 실제 작성했다. 각 Skill은 역할·사용 조건·핵심 절차와 필요한 참조만 담는다.

| Skill | 구체적 산출·검증 |
|---|---|
| `harness` | 요구·의존성·소유 범위로 작업 분해, 실제 네이티브 실행과 장부 연결, 결과 통합·인수인계 |
| `competition-intake` | 공식/미확인/아이디어/새 결정 분리, 요구→구현→평가→제출 연결 |
| `harness-design` | 상태 전이·중단·보류·업무 수정/기술 재시도·모델·Tool 호출 계약 |
| `data-evidence-contract` | 신규 원문·모델·버전·근거 ID, 검색 필터·캐시 무효화·출처 검증 |
| `agent-skill-authoring` | 출품 Skill의 SKILL.md와 코드·Tool·실행 방법 연결, 단독 재실행 |
| `implement-and-check` | 배정된 구현과 실제 명령 실행, 실패·미실행 결과를 그대로 전달 |
| `evaluate-harness` | AI 직접 입력·대화 평가, 출처/오류/수정/사용량/시연 실제 기록 |
| `review-change` | 독립 diff 검토, 증거·재현 입력·실질적 누락·수정 필요성 보고 |
| `submission-and-demo` | 코드·Skill·README·ZIP·발표·영상에서 같은 기능·근거를 확인 |

`judge-question-suite`, `token-quality-audit`는 별도 Skill을 늘리는 대신 evaluate-harness의 참조·평가 모드로 묶는다. `tool-routing`은 harness-design의 Tool 계약 참조로 둔다. 실제 기능·사용 조건이 달라져 분리할 이유가 생기면 그때 분리한다.

upstream validator가 Codex 문서의 Claude 경로를 구형 구성으로 판단할 수 있으므로 Codex 전용 계약과 공통·Claude 어댑터 검사 범위를 분리한다. 모든 문서에 같은 검사를 적용해 인수인계를 차단하지 않는다.

## Claude Code 연결

- `.claude/agents/*.md`에는 같은 6개 개발 역할을 Claude YAML frontmatter·도구 설정으로 포팅한다. Codex TOML을 이름만 바꿔 복사하지 않는다.
- `.claude/skills/`는 공통 개발 Skill에서 생성하는 정규 파일 사본이다. 공식 문서에 명시되지 않은 `.agents/skills` 직접 탐색을 가정하지 않는다.
- Windows symlink 없이 동기화·drift 검사를 수행하고, 도구별 실행 방식이 다른 부분은 작은 어댑터로 관리한다.
- Claude가 Codex 네이티브 도구를 호출하게 하지 않는다. Claude는 자신의 위임 도구를 사용하고 같은 작업·결과 계약을 기록한다.
- 팀원은 요구·계획·diff·실제 검사 근거를 읽고 이어간다. 같은 checkout의 동시 쓰기를 허용하지 않는다.
- 현재 로컬 PATH·표준 경로에서 Claude CLI를 발견하지 못한 상태다. 정적 구성 완료와 팀원 환경의 실제 발견·위임·검사·인수인계 완료를 구분한다.

## 목표 폴더 구조

개발 체계와 product-tools/data/evals 공통 기반, 업무 Skill과 세 환경의 파일 설치 adapter를 작성했다. Codex native 업무를 검증했으며 Claude/Gemini는 파일·공통 Tool 준비 검사만 통과했다. 관찰 화면·발표/영상·최종 제출은 후속 범위다. 환경별 업무 설치는 개발 레포 밖의 출품 폴더에 배치한다.

```text
AGENTS.md / CLAUDE.md / README.md
.codex/config.toml
.codex/agents/                 # 6개 Codex 역할 TOML
.agents/skills/                # upstream 기반 harness + 프로젝트 개발 Skill 8개
.claude/agents/                # 같은 역할의 Claude 어댑터
.claude/skills/                # 공통 원본에서 생성·차이 검사
dev-harness/                  # 실제 검사 실행·동기화·doctor·upstream 연결
vendor/codex-harness/          # 도입 원본·LICENSE·파일 목록·patch 기록
docs/competition-requirements.md
docs/decisions/               # 기술·정책 결정
docs/plans/                   # 구축 계획과 작업 원본
docs/evaluation/              # AI 입력 평가 설계
docs/validation/              # 실제 검증 범위·한계
product-tools/                # 공통 업무 상태·자료 조회·근거·결과 검증 코드
adapters/                     # Codex/Claude/Gemini 업무 지침·설치·준비 검사
skills/                       # 업무 Skill 5개+조건부 외부 조사1개; 개발 Skill과 구분
observability/                # 일반 코드 수집·외부 관찰 도구 연결; 자체 UI 아님
data/business/                # 실제 제품·후기 발췌·관측 출처·데이터 버전
data/synthetic/               # 신규 계약·오류 시험 자료; 업무·시연 근거 금지
evals/                        # 개발 사례와 별도 평가 입력·실제 runner
tests/                        # 개발 체계·업무 계약·관찰 연결 검사
submission/                   # README·시연 시나리오·발표 원본·ZIP manifest
.harness/runs/                # 개발 실행 장부; Git 제외
runtime-data/                 # 출품 SQLite·로그; Git 제외
```

## 작업 목록과 완료 조건

### 이번 계획 작업

- [x] P01 심사 질문의 뜻을 AI 직접 입력으로 정정하고 평가 입력 설계에 반영.
- [x] P02 공식 안내·제안서·사용자 요구를 분리하고 원문 지문 기록.
- [x] P03 실행·모델·UI·이벤트·저장·검사·MCP 기술 선택과 대안 조건 기록.
- [x] P04 LangGraph·SQLite의 Windows 라이브러리 호환성 실검사와 범위 기록.
- [x] P05 과거 React Flow 후보 조합의 설치·타입·빌드 검사와 범위 기록. 내장 UI 채택 철회 후에도 검사 사실만 보존.
- [x] P06 개발 역할·Skill·메인·Claude 연결·OpenSpec 교체·인수 기준 정의.
- [x] P07 사용자와 실행·계정·비용·설치·재현을 비교한 뒤 공통 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 연결하는 방향을 선택. [결정 기록](../decisions/product-runtime.md). 선택 완료이며 실제 업무·세 환경 지원 검증 완료는 아님.
- [ ] P08 [후순위] 개발 체계 구축 후 OSS 관찰 도구와 기존 실행기에 연결하는 React Flow UI 후보를 비교. 실제 연결·표현·지연·운영 부담을 O01-O06 기준으로 검증해 선택.

### 개발용 하네스 구축

- [x] D01 고정 upstream의 LICENSE/NOTICE/import·파일 목록을 확인하고 정규 파일로 도입. OpenSpec 생성물·초기 체계를 레포 안에서 교체. 공통 문서·Git 제외·CI를 갱신.
- [x] D02 Codex 프로젝트 설정·6개 역할 TOML·9개 Skill 구성. 공식 문서와 설치된 Codex 버전의 실제 지원 형식을 검사. 기본 `name`/`description`/`developer_instructions`와 환경별 설정을 확인.
- [x] D03 Python doctor·실제 명령 실행·결과 보고·작업 계약 검사·Claude 동기화 도구 구현. subprocess의 실패·timeout·출력 제한을 결과와 연결.
- [x] D04 새 Codex 세션에서 Skill 발견→첫 자식 생성→실제 ID/위임→결과→상태/중단 확인→검사→독립 리뷰→통합을 작은 새 작업으로 실증. 실제 작업·검사 기록을 남기되 외부 관찰 도구 연결은 완료 조건으로 요구하지 않음.
- [x] D05 중복 쓰기, 미실행 검사, 실패 전파, 입력 변경 뒤 재개, 오래된 결과 재사용 거부, 실제 자식 취소를 검사. 정적 파일 검사와 네이티브 동작 검사를 구분.
- [x] D06a Claude Agent6개·Skill9개 사본 구성·정적/drift 검사 완료.
- [ ] D06b 팀원 Claude 환경에서 새 세션·Skill 발견·위임·실제 검사·Codex→Claude 인수인계 확인. 현재 PC에 Claude CLI/로그인 환경이 없어 미실행.

### 출품 구현으로 이어지는 작업

- [ ] S01 실제 모델·문서·고객 리뷰의 업무 자료와 개발/평가 입력을 준비. [컨설팅](../consultation/2026-10-10.md)에 따라 합성 시연 계획 교체; 실제 고객 불편 근거 충분성은 아직 미완료.
  - [x] S01a PlanningInput/EvidenceRef/ProductResult 및 provenance·무효화 계약 구현.
  - [x] S01b 실제 pilot 모델1개·사양 요약4개·표시 고객 후기 발췌3개, 합성 시험 모델3개·리뷰40개 분리. 개별 구매·작성일·협찬 미확인 표시.
  - [x] S01c 별도 개발 입력2개·합성 예외 입력18개·실제 자료 입력3개 작성. 실제 모델 평가/runner 완료 아님.
  - [ ] S01d 실제 자료 확대.
    - [x] S01d1 실제3모델·후기6발췌·공식 사실19개로 확대. B502S33 수납과 T876MQQ012 적재 그림자 경험·정확한 스펙·연결 공용 설명서 대조. [확인 범위](../data/real-research.md).
    - [ ] S01d2 현재 모델 청소 불편 원문·내부 치수·선반 간격 확보. 미확인 항목을 요구하는 물리 설계/효과 확정 금지.
- [x] T01 공통 모델 선택·정확한 조회·근거·결과 구조 검사·SQLite 상태·멱등성·조회 캐시·후보 수정 상한·관측 사용량 기록 구현. [계약](../contracts/common-tools.md). 로컬 코드 검사 범위이며 실제 Agent/Skill/의미 판정·강제 native 호출 제어는 아님.
- [x] S02a Codex 출품 설치·준비 검사·native 업무Skill6개 발견·실제 모델/누적 usage·첫 질문/후속/자료 부족·오류 복구를 확인. Windows Codex0.162.0 전체 접근 모드 인수이며 workspace-write 준비 실패·비용 미측정은 [검증 기록](../validation/codex-product.md)에 보존. Claude/Gemini나 AI 품질 통과를 포함하지 않음.
- [ ] S02b Claude Code 업무 사본·지침·Tool/권한·대화 상태 연결을 구현하고 같은 업무·예외 평가 수행. 개발 D06b 검증과 구분.
  - [x] S02b1 .claude/skills 업무6개·CLAUDE.md→AGENTS.md·설치 manifest/지문·새 폴더 잠금 환경·auth-free doctor 검사. [실제 준비 범위](../validation/portable-product.md).
  - [ ] S02b2 팀원 환경의 인증/신뢰/권한·Skill 발견·실제 업무/후속/예외·usage 인수. [개발 인수와 구분한 체크리스트](../evaluation/claude-native-handoff.md).
- S02c **지원 철회(2026-10-11 사용자 결정)**. 아래 설치/실패는 당시 기록이며 추가 native 인수/지원 목표에서 제외한다. 신규 Gemini 설치/패키징을 거부하고 기존 외부 사본·실패는 보존한다.
  - [x] S02c1 .gemini/skills 업무6개·GEMINI.md→AGENTS.md·설치 manifest/지문·새 폴더 잠금 환경·auth-free doctor 검사.
  - [ ] S02c2 실행자 환경의 인증/폴더 신뢰/Skill 동의·실제 발견/업무/예외·대화/usage 인수.
- [ ] S03 단일 상품기획 Agent·업무 Skill 5개+조건부 외부 조사1개·보류/수정·출처·추가 입력 연결.
  - [x] S03a Agent 지침·Skill6개·실행 wrapper·지문 manifest·의미 검토 기록 정합성 Tool·외부 관측/버전 등록 코드 구현. 정적/일반 코드 검사는 환경별 native 인수가 아님.
  - [ ] S03b S02 실제 설치 환경에서 조건부 Skill 호출·상태 저장·추가 질문·보류/수정·전체 호출 관측 연결 검증. 네이티브 모델 판단의 심사 품질 평가는 S05.
    - [x] S03b1 Codex 실제 첫 입력→조건부 외부 근거→기획→실패 후보/수정1회→저장/export, 같은 native 대화 후속 입력, 긍정/기대만 있는 자료의 held, 미확인 모델 needs_input/no fake turn, native 명령/Tool 오류 복구. 성공 CLI usage 누적/차이를 기록하고 실패 미측정을 보존. native 전체 backend 비용·Claude/Gemini 연결은 포함하지 않음.
    - [ ] S03b2 Claude에서 동일 업무/예외와 관측 범위를 검증. 하네스 보완 완료 후 최길웅에게 메일 요청·정이량 회신, 접근 불가 시 후순위. Gemini 제외.
- [ ] S04 [후순위] 화면 방식을 선택한 뒤 일반 코드로 실제 이벤트·ID·상태를 관찰 도구/UI에 연결. 구조·실행·근거·메시지 관측 범위·재접속·재생·실행 격리를 검사. 현재 화면을 구현하지 않으며 S05 업무 평가의 선행 조건으로 두지 않음.
- [ ] S05 실제 심사 입력·다중 턴·원문 지시문 공격·오류·동일 조건 baseline 평가. turn별 수정 및 invocation별 기술 재시도 상한을 검사. 전체 Agent+하위 호출·실패 비용과 미측정을 구분하고 동일 평가 묶음의 요구 충족률·총비용으로 토큰 절감 검증.
  - [x] S05a 개발용 native 평가 runner·격리/동결/실패·미측정/누적차이 경계 검사, 실제 자료 질문6개와 독립 원문 검토 방식 구현. 출품 모델 호출기 추가 아님.
  - [x] S05b 실제 R01/R04 두사례 × 이전/개선/일반 프롬프트6회 실행·저장 일치·source 감사·독립 의미검토. [결과와 한계](../validation/s05-pilot.md). 세션 관측 입력36.5% 감소이나 자식 사용량/현금 비용/우위 미입증, baseline 양식 안내 부족과 구조 실패 보존.
  - [ ] S05c 보완 계약의 baseline·반복측정·native single-agent 제어·R02/03/05/06·원문 지시문·실제 장애/취소·전체 비용/인간 공수 검증. 옵션/검사 코드만으로 실제 통과를 표시하지 않음.
    - [x] S05c1 보완 양식6회 재비교·source/저장 감사·익명 독립 원문 검토. 관측 세션 입력 감소와 시간 증가를 함께 기록하고 baseline 대비 우위는 미입증. 옵션만으로 위임 제거는 실패로 보존. [후속 기록](../validation/s05-followup.md).
    - [x] S05c2 나머지4사례·native 재개와 조건 변경/이력·명시한 단일 Agent 선호의 실제 관측·독립 원문 검토. 제품 저장 일치, 일반2건 unused_evidence 구조 실패도 보존.
    - [x] S05c3 test_only 지시문 파일·일회성 wrapper 장애·owned CLI deadline 시험. 실제 전달/복구/프로세스 종료 범위이며 반환 근거 속 공격·업무 cancelled 지원·전체 재시도 한도는 별도 미완료.
    - [ ] S05c4 전체 Agent/backend 실패 포함 청구 및 실제 사람 활동 시간·요구 충족률·반복 일반화 검증. [공수 측정 절차](../evaluation/human-effect-protocol.md).
    - [x] S05c5 로컬 업무 `cancel_turn`·영수증/이력·멱등성·terminal/오래된 turn·재접속·늦은 관측·저장 경합, 웹 수집 최초+재시도1회 경계를 일반 코드 검사. native/backend 중단·재시도 강제 제어 검증은 아님. [취소·재시도 검증](../validation/s05-hardening.md).
    - [x] S05c6 정상 반환 원문과 지시문 삽입을 같은 질문으로 실제2회 비교. 이전 삽입 조건 구조/저장 일치와 정상420초 timeout을 보존. 후속 [v5.1 재검증](../validation/s05-v51-flow.md)의 두 조건 모두 정상 Tool 전달은 확인했지만 최종 응답 전420.67/420.61초 timeout으로 paired acceptance 미통과. 저장 후보와 최종 응답을 구분하며 제한된4입력 후 자동 재시도하지 않음. 이후 [v5.2](../validation/s05-v52-flow.md)의 별도 사전 상한8입력 중 J17 두 조건390.01/370.19초에 최종 전달·저장·무해화·독립 의미 검토를 완료. 과거 timeout은 유지하고 공격 해석의 작은 결함·일반화 미검증을 보존.
    - [x] S05d1 읽기 권한 팀원의 실제 실행 접수 Issue 양식·비식별 보고서/환경별 색인·오류/수정/검토 이력·개발/회귀/미사용 평가 절차 작성. [접수 계약](../evaluation/team-test-records.md), [범위와 미사용 평가](../evaluation/coverage-and-holdout.md). 수동 기록 체계이며 실제 개별 결과 인수·자동 수집·품질 통과가 아님.
    - [ ] S05d2 팀원이 이미 실행한 결과 접수·원문/저장 대조·환경별 결함 분류·수정/회귀·미사용 묶음 평가. 사용자가 대겸·진하의 완료를 확인했고 결과 위치는 팀원에게 확인 중이라고 답함. [실제 Issue2개/업무 입력3개](../validation/team-runs/index.md)를 접수하고 발췌/환경/오류를 검토했다. 작성자 ginaginaring의 실명은 미확인으로 대겸·진하 각각의 인수라고 단정하지 않는다. 원본 export/native 파일·사용량 미첨부로 무결성은 inconclusive, v5.2 팀 재시험은 미실행. 수백 후보 수와 실제 실행 수·비용을 분리하고 평가 상한을 먼저 정함.
    - [x] S05e Skill 중복 호출 지침 개선·동일 실제 질문의 제한된 native 비교·독립 의미 검토. [실제 기록](../validation/s05-skill-efficiency.md). v4/v5 두 실행 구조·저장 일치와 원문 의미 검토, 최종 v5.1 source/manifest·제품97/평가29·ZIP 재현 완료. 알려진 1사례 1회씩의 관측이며 v5.1 외부 조사/보류 native·제외불편 해석·반복/미사용 평가·전체 비용/공수·J17 paired acceptance는 별도 미완료.
    - [x] S05f 실제 자료2턴의 v5.1 보류 복구→조건 완화·동일 원문 진단 버전 재등록→후속 연결 검증. [결과/제한](../validation/s05-v51-flow.md). same native/session·신규key/turn/version·이전 후보/export 보존·질문/scope/제약·저장/출력/export 대조24항목 true와 두 답변 독립 원문 검토 완료. 실제 웹 수집/native import·반복/미사용 평가·전체 비용/공수와 J17 paired acceptance는 포함하지 않음.
- [ ] S06 README를 따라 새 환경에서 실행·Skill 재실행·ZIP 재현을 확인하고 실제 실행으로 발표·영상 작성. 발표자료 20페이지·발표 10분/질의응답 5분을 검사하고 제출 직전 영상 규격·실제 마감 시각·제출 경로·파일명·변경 공지를 확인.
  - [x] S06a 업무 source ZIP70파일 manifest·새 Temp 추출·uv 잠금 환경·공통 Skill doctor·ZIP 내부 소스의 새 Claude 사본 설치를 실증. [재현 연습](../validation/submission-rehearsal.md). native 신규 환경·영상·최종 제출 완료가 아님.
  - [ ] S06b 발표/영상·최종 지원 환경 재현·운영진 제출 규격/마감/공지 대조.
  - [x] S06c 시연 실행 순서·14쪽/예정570초 발표 구성·요구/근거 연결과 구조 검사, 최신 업무 소스 ZIP70파일 및 Claude/Gemini 새 폴더 설치/doctor 재확인. [준비 기록](../validation/s06-demo-preparation.md). 실제 발표/영상/리허설·native 환경 인수 완료는 아님.
  - [x] S06d1 [제품 릴리스 계약](../contracts/product-release.md) 작성: 의미 있는 출품/제출 변경만 버전별 첨부·SHA·변경 내역·검사/지원 상태로 배포. 개발 체계/평가/팀 기록 제외, 기존 배포 덮어쓰기 금지. 현재 문서 변경은 릴리스 대상 아님.
  - [x] S06d2 의미 있는 제품 변경 후 실제 새 버전 첨부물 빌드·검토·재현·GitHub Release 발행/다운로드 SHA 확인. [product-v0.1.0 prerelease](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.1.0)의 제품 ZIP70파일·SHA 목록만 첨부했고 source/tag commit `9fa81d2`·원격 notes·실제 다운로드 SHA/각파일을 대조했다. [발행 근거](../validation/s05-skill-efficiency.md). 공식 최종 제출·모든 환경 품질 인수와 별도다.

개발용 하네스의 완료 기준은 D01-D05 실증이다. Claude native 지원 검증 완료는 D06b 실제 팀원 검증을 추가로 요구한다. D06a는 adapter 파일 제공·정적 동기화 완료다. 출품 완료는 S01-S06 및 공식 제출 요구를 실제로 충족해야 한다. 계획·정적 검사·라이브러리 smoke test만으로 어느 완료도 주장하지 않는다.

## 도입 근거

- [고정 codex-harness](https://github.com/revfactory/codex-harness/tree/80f8217b5b6d3f220a31f05f9c0adaf09dac40f4)
- [Codex 네이티브 역할](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex Skill 발견](https://learn.chatgpt.com/docs/build-skills)
- [Claude 네이티브 역할](https://code.claude.com/docs/en/sub-agents), [Claude Skill](https://code.claude.com/docs/en/skills)


## 이번 구축 결과

실제 인수검사: CLI 신규9Skill 발견·상한3 읽기, persistent부모/자식 생성·검사·메시지·interrupt, 실제 Temp 신규 usage helper8검사·부모통합검사·독립review, Skill변경 결과등록거부·새run resume·fresh packet 재위임·idle관찰·complete errors=[]를 확인했다. 개발 helper22tests와 OSS/Claude동기화 정적검사는 실제 exit0이다. custom role 자동 선택/sandbox/model 적용과 close는 이 runtime에서 미검증이다. 이후 P07에서 출품 네이티브 실행 방향을 선택했다. 환경별 업무·모델 검증(S02a-c), 관찰 화면(P08), 출품 S01-S06은 여전히 별도 미완료다.

## Codex 출품 설치·실제 업무 연결 추가

[인수 기록](../validation/codex-product.md)에 따라 Codex 전용 별도 설치, 자동 Skill 발견, 정상/후속/보류/미확인 모델·실제 오류와 저장/export를 실증했다. 공통 도구75검사·독립 리뷰를 연결했다. 설치 프로그램은 모델을 호출하지 않으며 실제 모델은 실행자가 연 Codex다. 샌드박스 지원 제한·미측정 비용·품질/토큰 효과 미평가를 유지한다.

후속으로 [S05 비교/예외](../validation/s05-followup.md), [Claude/Gemini 로컬 준비](../validation/portable-product.md), [소스 ZIP 재현](../validation/submission-rehearsal.md)을 추가했다. 당시75검사와 이후82검사 checkpoint를 구분한다. 현재 검사는 상단의 2026-10-11 기록을 따른다. 청소 불편·내부 치수의 [추가 조사](../data/s01d2-followup.md)도 확보 실패로 보존했다. native portability·전체 비용·사람 공수·시장 신규성·최종 제출을 완료로 바꾸지 않는다.

당시 v5.2 checkpoint는 제품102개·평가47개·observer34개·개발22개다. 최신 검사 범위와 수치는 상단의 2026-10-11 기록을 따른다. 이전82/18 및97/29 기록은 당시 결과로 보존한다. S05e의 Skill 중복 호출 개선과 알려진1쌍의 독립 원문 검토 후 S06d2 첫 제품 시험판을 배포했다. S05f에서 v5.1 실제2턴의 보류/후속·진단 버전 변경·이력 보존과 독립 의미 검토를 확인했지만 J17 두 조건은 최종 응답 전 시간초과로 S05 전체는 미완료다. 다음 우선순위는 저장 뒤 큰 최종 응답/반복 검사의 지연을 별도 계약으로 개선하고, 팀 개별 결과 접수/환경별 인수·실제 웹 수집/native import·제한된 반복/미사용 평가를 수행하는 것이다. 전체 비용·사람 공수·실제 발표/영상 작업은 별도 미완료다.

팀 실행을 접수할 저장소 양식과 환경별 검토 색인을 마련했다. 다음 판단은 실제 팀 보고서에 근거한다. 양식 구축을 팀원의 실행 결과·환경 인수 완료로 집계하지 않으며 공개된 질문을 미사용 평가로 바꾸지 않는다.

## 다섯 우선 작업의 이번 실행 결과

- 최종 전달: v5.2 compact receipt·bounded findings·오래된 키 방어·BOM 지원과 제품102/평가47 회귀 완료. J172조건 모두 제한 안에 최종 전달. 실제 거절 후보의 새 native 수정 흐름 반복·모든 timeout 제거는 별도이며 기존 실패를 보존했다.
- 환경: 팀 Issue2개/3입력의 제한된 발췌 검토 완료. Claude Code 사용 가능한 인증 없음, Gemini CLI0.63.0은 실제 개인 OAuth 후 서버 거부. S02b2/c2·S03b2·D06b 및 팀 원본 인수는 미완료.
- 자료: 실제 정확 공식 PDP 관측→capture/import→새v4→N01 native 조회/저장/export 연결 완료. 신규 청소 불편/내부 치수는0건으로 S01d2는 미완료. AI 스스로 browser 수집 Skill을 호출한 신규 시험은 별도.
- 평가: 사전8입력/420초/동시2/자동재시도0의 종료·최종 전달 완료. 하네스6개 계약통과, 일반2개 검토계약실패; 의미검토 점수와 분리. R01 하네스 평균 입력은 일반의4.64배로 절감 미입증. 전체 청구·사람 공수·큰 미사용 묶음은 미완료.
- 관찰: 별도 collector·34검사·실제 본 실행 tail·Langfuse25span 수락/화면 완료. 모델 요청/추가문맥0의 코드 경계를 유지. 전체 Agent/메시지 graph·Claude/Gemini·완전한 on/off 반복·30초 녹화는 미완료. 작은 HTML 토큰 위젯은 후속 제안으로만 기록.

갱신된 다음 순서는 (1) 사용 가능한 native 환경/팀 원본을 확보할 때 재인수, (2) 의미의 모델 연결·조건 결합 결함과 입력 토큰 증가 원인 개선을 일반 규칙으로 설계하고 사전 제한된 미사용 평가, (3) 전체 청구/사람 활동 시간의 동등 업무 측정, (4) 실제 청소·내부 치수 확보 또는 보류 범위 유지, (5) 별도 화면 가독성·30초 녹화와 발표/영상·최종 제출 확인이다. 외부 인증/실물 자료의 부재를 코드 완료나 실패0으로 바꾸지 않는다.
