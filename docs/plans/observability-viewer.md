# 별도 실행 관찰·시각화 도구 계획

기준일: 2026-10-10. 사용자의 정정에 따라 개발 과정과 최종 하네스 시연의 구조·실행 흐름은 별도 프로그램에서 관찰한다. 우리 하네스에 React Flow 화면을 내장하는 기존 채택은 철회한다. 이후 [Codex 별도 collector→Langfuse 실제 연결](../validation/observer-langfuse.md)을 인수했다. 아래 넓은 구조·다중 환경·시연 화면 계획의 완료와 구분한다.

## 현재 우선순위와 열린 후보

2026-10-11 수정 마감 이후에는 기존 collector/Langfuse를 사용한 두 창 표시·가독성·장애 대책·30초 실제 녹화를 다음 작업으로 삼는다. 앞 단계의 종료를 관찰 화면이나 영상 완료로 표시하지 않는다. 구조 설명/실제 사건/저장 재생, 개발 역할/출품 메인1개·Skill6개를 구분한다. 새 React Flow UI·LLM 호출을 이 준비의 선행 조건으로 추가하지 않는다. [마감 기록](../validation/closure-progress-20261011.md)과 [시연 절차](../../submission/demo-runbook.md)를 따른다.

사용자는 시각화가 현재 우선순위가 아니라고 명시했다. 개발용 하네스의 실제 역할·Skill·위임·구현·검사 체계 D01-D06를 먼저 구축한다. 관찰 프로그램 설치·UI 구현·수집 어댑터 실증은 후순위이며 개발 체계 완료나 업무 품질 평가의 선행 조건으로 두지 않는다. 지금은 실제 검사·작업 기록을 보존한다.

기존 내장 화면 채택 철회는 Codex/Claude 실행 방식에서 React Flow 화면이 불가능하다는 뜻이 아니다. 우리 UI에 React Flow를 넣고 기존 실행기의 이벤트를 연결하는 구성도 후속 후보로 검토할 수 있다. 이는 모델 API 직접 호출을 자동으로 요구하지 않으며 기존 Codex 앱 자체에 임의 화면을 추가할 수 있다는 주장과 구분한다. 현재 사용자의 질문은 가능성 확인이므로 React Flow·자체 UI를 다시 채택하거나 구현하지 않는다. 이전 별도 관찰 선호와 함께 후속 선택에서 비교한다.

## 확정한 경계

- 하네스 실행과 관찰 도구는 별도 프로세스·실행 수명으로 운영한다. 관찰 화면을 닫아도 업무 실행이 계속된다.
- 기존 공개 관찰 도구를 우선 검토한다. 새 자체 React Flow 앱을 만드는 것으로 사용자 요구를 바꾸지 않는다.
- 개발용 Codex/Claude 실행과 최종 하네스 실행을 모두 관찰 대상으로 삼되 실행 ID·역할·사용량을 분리한다.
- 관찰용 Agent·Skill이나 설명 생성용 LLM을 추가하지 않는다. 이미 존재하는 설정·이벤트·로그를 일반 코드로 수집·변환·표시한다.
- 관찰 로그를 모델의 입력·Tool 결과·대화 문맥에 되돌려 넣지 않는다. 화면 새로고침·열기·재생이 업무 요청이나 모델 호출을 만들지 않는다.
- 수집 실패가 업무 실패가 되지 않도록 비동기·제한된 큐·오류 격리를 설계한다. 누락·지연은 숨기지 않는다.

## 수집·표시 구조

```text
개발 세션 / 최종 하네스
  -> 런타임 이벤트·command hook·Tool wrapper·기존 로그
  -> 일반 코드 수집·ID 연결·내보내기 어댑터
  -> 별도 관찰 프로그램의 구조 그래프·trace tree·타임라인
```

구조 뷰는 Agent 역할 정의·Skill 목록·Tool 연결을 읽는다. 실행 뷰는 실제 시작·종료·실패·위임·반환·사용량 이벤트를 읽는다. 정의되어 있지만 이번 실행에 사용하지 않은 역할과 실제 실행된 역할을 구분한다. Skill 정의·본문 로딩·업무 실행은 서로 다른 상태다.

최소 수집 필드는 session/run/turn ID, 실제 agent ID·parent ID, invocation ID, entity 종류·이름, 이벤트 종류, 시각·상태·시도 횟수, 관측된 usage, 오류와 근거 참조다. 전달 메시지가 실제 관측된 경우에만 발신·수신·메시지 관계를 표시한다. 호출 순서나 부모·자식 관계만으로 메시지 교환을 만들어내지 않는다.

전체 사고 내용을 모델에게 생성시키지 않는다. 실제로 얻은 요청·Tool 입력·결과·상태를 짧은 코드 요약으로 표시하고 필요하면 원본 기록을 참조한다. 자격증명은 제외하고 로그의 개인정보·전송 범위를 관리한다.

## 런타임별 연결 후보와 한계

| 대상 | 먼저 확인할 경로 | 아직 보장하지 않는 것 |
|---|---|---|
| Codex | App Server의 turn/item 시작·완료 등 구조화 이벤트, 설치 버전의 지원 스키마 | 이미 열린 데스크톱 대화 자동 구독, 모든 자식·메시지·Skill 의미의 완전 수집 |
| Claude Code | command hooks의 SubagentStart/Stop, Pre/PostToolUse 및 지원되는 실행 기록 | 모든 내부 메시지·Skill 본문 로딩의 완전 수집, 팀원 설치 버전 호환 |
| 과거 독립 실행 대안 | 실행기 이벤트·Tool wrapper·OpenTelemetry/추적 SDK | 현재 초기 출품 경로로 채택되었다는 주장 |
| 선택한 출품 Codex/Claude/Gemini 실행 | 검증한 네이티브 관측 어댑터와 공통 Tool 이벤트 계약 | 연결·업무 검증 완료, 모든 정책·상태·usage 자동 보장 |

출품 실행 방식은 [공통 업무의 네이티브 실행](../decisions/product-runtime.md)으로 선택했으며 Codex CLI/rollout의 별도 관측 연결을 구현했다. Codex App Server를 이용해 새 실행을 연결하는 것과 현재 데스크톱 세션에 관찰자를 붙이는 것은 다르다. 현재 선택을 관찰용 자체 업무 실행기 구축으로 바꾸지 않는다. 환경별 실제 버전의 관측 범위를 먼저 실증하고 Gemini 경로도 별도 확인한다. 없는 이벤트는 미관측으로 남긴다. 공통 Tool은 wrapper로 시작·결과를 기록할 수 있지만 문서 읽기만으로 업무 실행을 단정하지 않는다.

## 별도 프로그램 후보

Langfuse를 우선 연결 검증 후보로 둔다. 별도 trace tree·Agent Graph를 제공하고, Agent 유형의 observation 또는 LangGraph 연결로 그래프를 구성한다. 시간·중첩으로 추론한 그래프는 실제 메시지 교환 그래프와 구분한다. 우리 Skill은 도구가 지원하는 observation 종류와 metadata로 구분하며 임의의 지원되지 않는 유형을 넘기지 않는다.

Langfuse를 Codex 사건·사용량 metadata의 상세 관찰 도구로 연결했다. 최종 발표 화면 구성과 전체 그래프 도구의 채택은 별도다. 실제 Codex/Claude 이벤트의 부모·자식·Tool·Skill 표현, 수집 지연, 발표 가독성, 로컬/클라우드 운영 부담을 확인한다. 기존 검토에서 확인한 조회 지연 때문에 매 순간 즉시 표시를 약속하지 않는다. 도구 자체의 저장·호스팅 비용과 LLM 토큰 비용도 구분한다. 기능을 확인하지 않은 클라우드 플랜이나 무거운 self-host를 자동 도입하지 않는다.

LangSmith Studio는 LangGraph 실행 후보의 진단 대안이며 모든 Codex/Claude 실행을 범용 관찰할 수 있다고 가정하지 않는다. 도구가 요구한 구조·실행 뷰를 충족하지 못하면 추가 후보를 비교한다. React Flow는 그림을 만드는 라이브러리이며 완성된 관찰 프로그램이 아니므로 기존 내장 UI 채택을 대체하는 기본값으로 두지 않는다.

## 비용과 인수 조건

별도 프로세스라는 이유만으로 토큰 절감이 보장되는 것은 아니다. 추가 모델 요청·추가 입력/출력이 없도록 연결해야 관찰 자체의 추가 LLM 토큰이 발생하지 않는다. command hook 출력·오류가 모델 문맥으로 들어가거나 관찰을 위해 모델이 추가 Tool을 호출하면 그 비용을 포함한다. SDK·수집·렌더링의 CPU·I/O·네트워크·저장·호스팅 비용은 별도로 기록한다.

- [ ] O01 실제 지원 버전에서 Codex·Claude·Gemini의 관측 가능한 이벤트·사용량·누락 범위를 작은 실행으로 각각 확인. 출품 업무 검증 순서에 맞춰 단계적으로 진행.
- [ ] O02 수집 어댑터가 실제 ID·parent·Tool·Skill 정보를 연결하고 모델 문맥에 데이터를 추가하지 않는지 확인.
- [ ] O03 별도 도구에서 구조 정의와 실제 실행·오류·반환·재생을 구분해 표시. 재생은 저장 기록이라고 표시.
- [ ] O04 관찰 on/off 실행의 모델 요청 수·입출력·usage를 비교. 관찰을 위한 추가 호출·프롬프트가 없다는 증거와 미측정을 분리.
- [ ] O05 관찰 프로그램 종료·단절·지연·재접속이 업무 상태나 모델 호출을 바꾸지 않는지 검사.
- [ ] O06 개발 세션과 최종 시연 모두에서 실제 흐름을 확인하고 선택한 도구·설치·연결·지연·한계를 기록.

## 공식 근거

- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Langfuse Agent Graphs](https://langfuse.com/docs/observability/features/agent-graphs)
- [Langfuse 추적 구조](https://langfuse.com/academy/tracing)

## 2026-10-10 시연 화면과 토큰 표시 대책

사용자가 추가로 요청한 **별도 화면을 띄운 시연 영상**의 구체화다. 작성 당시의 계획에 이어 collector·Langfuse 실제 연결/화면을 검증했다. 녹화·발표 가독성·전체 구조 그래프 인수는 아직 별도다. S05 업무 품질 개선을 먼저 진행하고 영상 최종 촬영 전에 O01-O06을 인수한다. [토큰 구현·실측·표시 원본](../evaluation/token-measurement.md)을 함께 따른다.

### 화면 구성

녹화 시 왼쪽 약60%는 기존 Codex의 실제 입력·Tool 수행·최종 답변, 오른쪽 약40%는 별도 관찰 도구의 같은 실행을 보여준다. 이 비율은 첫 가독성 시험의 제안이며 실제1920×1080 출력에서 한글·출처·숫자를 확인해 조정한다. 구조 소개와 상세 근거/수치는 해당 창을 전체 화면으로 확대한다.

| 별도 화면 영역 | 표시 내용 |
|---|---|
| 실행 식별 | 출품/개발 구분, 실제 run/native/session/turn ID, 관측 범위, 마지막 갱신 시각, live/기록 조회 |
| 구조·완료 단계 | 출품 Agent1개·Skill6개 정의와 이번 실행에서 실제 관측한 Skill/Tool. 정의만 있는 항목, 지침 로딩, 실제 Tool 완료를 구분 |
| 상태·근거 | accepted/status/valid, 실제 오류·수정·보류·출처 참조. 저장 승인과 최종 답변 완료는 별도 표시 |
| 사용량 | 입력 전체/그중 캐시/비캐시, 출력 전체/그중 reasoning, 부분/종료 관측, 전체 청구 미측정 |

출품에는 자동 서브에이전트 팀을 추가하지 않는다. 개발 위임을 소개하는 별도 장면에서만 실제 관측 ID·메시지를 표시한다. Skill을 Agent로 만들거나 호출 순서를 메시지 교환으로 그리지 않는다. trace에 없는 active 상태나 내부 사고를 화면용 모델에게 생성시키지 않는다.

### 연결 검증 경로

1. **기존 저장 기록1건부터 검증:** 실제 native ID가 있는 공개 `--json` 기록을 일반 코드로 읽어 개인정보·원문을 제외한 사건을 만든다. 현재 `evals/runner/native_eval.py`는 종료 후 파서이므로 그대로 라이브 수집 완료로 표현하지 않는다. 조회 캐시 hit도 실제 Tool 사건과 별도 metadata로 구분한다.
2. **Langfuse에 완료 사건을 연결:** 현재 공식 v4 계약의 OTLP/HTTP endpoint와 ingestion header, 실제 고정 SDK/서버 버전·LICENSE·호스팅을 확인한다. 임의 `skill` 타입을 보내지 않고 지원되는 span/chain과 `entity_kind=skill` metadata를 검토한다. Agent Graph의 중첩/시간 기반 연결은 실제 메시지와 다르다. 최소 연결이 목표 표현을 못 하면 후보를 추가 비교하고 자체 React Flow 앱을 자동 채택하지 않는다.
3. **본 시연 실행의 로그를 관찰:** 관찰자가 명시적으로 선택한 실행 ID·로그만 tail한다. 실행자 자신의 기존 Codex/CLI가 업무를 수행하며 observer는 모델·Codex를 내부 호출하지 않는다. 현재 데스크톱 대화에 자동 구독하는 기능은 검증하지 않았다. 직접 CLI 기록 경로와 설치 버전의 ID별 로그 경로를 먼저 확인하고 본 실행의 기록만 사용한다.
4. **실제 Tool/Skill 관계를 검증:** command 시작/완료와 wrapper의 operation·invocation·업무 handle을 연결한다. 공통 `begin_invocation` 장부만으로 실행을 증명하지 않는다. 경로/명령에서 매핑한 Skill은 `명령 기반 매핑`이라고 표시하고, 본문 파일 읽기는 `지침 로딩`으로 표시한다. 코드 경계 이벤트 추가가 필요하면 별도 제품 변경·검사·릴리스로 진행한다.

기본 사건 필드는 run_id/native_thread_id/session_id/turn_id/event_id/seq/source_timestamp/observed_timestamp/entity_kind/entity_name/invocation_id/parent_id/status/source_log_ref/coverage/usage_scope/usage_snapshot이다. trace ID와 업무 ID·native thread/Agent ID는 서로 다른 필드이며 관측되지 않은 값은 null로 둔다. 원문 대화·개인 경로·인증·DB 전체는 외부 도구에 보내지 않는다. 화면에도 허용한 사건·집계만 표시한다.

### 즉시 표시의 한계와 장애 대책

현재 Langfuse v4 문서는 완료된 span을 한 번 export하고 같은 ID를 반복 update-ingest하지 않도록 안내한다. SDK batching·서버 처리·UI 조회 지연도 있어 모든 시작 상태와 토큰이 매순간 즉시 보인다고 약속하지 않는다. 새 연결은 Python SDK4.7+/JS SDK5.4+와 `x-langfuse-ingestion-version: 4` 조건을 확인해야 하며, legacy ingestion의 Cloud 종료 예정일은2026-11-16이다. 이는 공식 지원 조건의 검토이며 이 레포의 패키지 채택/설치 기록이 아니다.

최소 시연에서는 왼쪽 실제 실행이 진행을 보여주고 오른쪽은 **마지막으로 관측·수집한 완료 단계와 사용량**을 보여준다. 중간 token snapshot이 해당 버전에서 실제 관측되면 갱신 시각·부분 관측을 붙인다. 종료값만 얻으면 종료 후 표시하며 모델에게 사용량을 질문하거나 화면을 위해 업무 Tool을 추가 호출하지 않는다. Langfuse에 native 집계를 단일 모델 generation으로 넣지 않고 [토큰 표시 계약](../evaluation/token-measurement.md)을 적용한다.

- 수집기는 로컬 기록을 먼저 보존하고 큐/파일 크기·전송 timeout을 제한한다. 중복 event ID/seq를 다시 합산하지 않고 누락·오래된 값·재접속은 배지로 표시한다. 수집 오류를 업무 stdout/stdin·프롬프트로 내보내지 않는다.
- observer 화면 새로고침·종료·전송 실패는 업무 PID/상태/모델 호출을 바꾸지 않아야 한다. on/off의 입력 지문·Tool 반환·실제 실행 trace를 대조한다. `관찰 코드가 만든 추가 요청0`과 미관측 전체 backend 호출 수를 구분한다.
- 영상 녹화는 원본 전체 실행을 보존한다. 실제 응답 지연·timeout·accepted=false를 녹화 편집으로 완료처럼 만들지 않는다. 배속/생략과 실제 경과 시간을 표시한다.
- 관찰 도구 단절 때는 실제 Codex 화면과 로컬 기록을 유지한다. 이후 종료 trace/결과를 보여주면 `실행 기록 조회`라고 표시한다. 시간순 애니메이션 재생은 구현·검증 전 제공한다고 약속하지 않는다.
- FocuSee Windows 설치 버전의 두 창 녹화·한글 가독성·커서/줌·출력은30초 시험으로 확인한다. 사용할 수 없으면 설치 확인된 OBS를 녹화 대안으로 시험한다. 이 대안도 실제 녹화·출력 인수 전에는 완료가 아니다.

### 다음 인수 항목

- [ ] O01a 고정 native 기록1건을 읽어 ID/Tool/오류/누적 사용량 변환, 원문·개인정보 제외와 중복 처리 검사. 새 모델 입력0회.
- [ ] O02a 기존 OSS 도구의 실제 계정/호스팅·버전·라이선스·연결·조회 지연 확인. Langfuse를 최초 검증 후보로 유지하되 최종 채택은 표현·비용·지연 인수 후 기록.
- [ ] O03a 단일 Agent/Skill/Tool·부분/종료 usage·저장 승인/답변 완료·기록 조회 구분을 실제 화면에서 검사. 구조 정의와 이벤트 관측을 따로 확인.
- [ ] O04a 본 실행 on/off·화면 새로고침/종료/재접속·큐 포화/전송 실패에서 업무 격리와 추가 모델 요청/프롬프트0 확인. 실행 상한을 먼저 배정하고 자동 재실행하지 않는다.
- [ ] O06a 30초 두 창 녹화·출력·개인정보 가림·한글/숫자 가독성 확인 후 정상/보류/후속 시연을 촬영. 공식 영상 규격·마감은 여전히 미확인.

추가 공식 근거: [v4 ingestion 계약](https://langfuse.com/integrations/native/opentelemetry/migration-to-v4), [public API](https://langfuse.com/docs/api-and-data-platform/features/public-api), [observation 타입](https://langfuse.com/docs/observability/features/observation-types), [usage/cost 계약](https://langfuse.com/docs/observability/features/token-and-cost-tracking), [마스킹](https://langfuse.com/docs/observability/features/masking), [self-host 구성](https://langfuse.com/self-hosting), [FocuSee 출력](https://focusee.imobie.com/guide/export-video.htm), [Windows 기능 범위](https://focusee.imobie.com/faq/editing-functions.htm).

## 실제 연결 후 상태

O01/O02의 Codex CLI/rollout 경로, O03의 실제 Tool/runtime/usage metadata, O05의 코드 수준 격리·단절/timeout 검사와 O06의 본 실행 tail→Cloud25span/화면은 [인수](../validation/observer-langfuse.md)했다. 전체 checkbox는 다중 환경·구조 정의/메시지 graph·발표 영상까지 포함하므로 모두 완료로 바꾸지 않는다. O04 완전한 on/off 비교, Claude/Gemini, 미관측 parent/메시지, 화면 가독성·녹화는 남는다.

작은 HTML 상태·토큰 위젯을 별도 브라우저/OBS Browser Source에 표시하는 사이드 검토를 접수했다. 이는 후속 제안이며 현재 구현·채택하지 않았다. 모델 호출 없이 journal을 읽고 live/replay·최신 관측·미측정과 cache/reasoning 포함 관계를 표시한다. Langfuse는 상세 사건 검토에 사용한다.
