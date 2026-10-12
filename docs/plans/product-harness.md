# 출품용 상품기획 하네스의 실행·시연 계약

2026-10-12 최신: [자료 폭·시간·선택 검토자 결정](../decisions/evidence-throughput-20261012.md)과 [실제 검증](../validation/evidence-throughput-20261012.md)을 우선한다. 메인1/업무Skill6/선택적 출품 근거 검토자1, 일괄 원문 등록·전체 전달/검토 장부·600초 workflow·불변 검토 packet을 구현했다.48자료 본 시험의 Codex507.375초/Claude GUI359.776초 저장·문서·최종 전달을 확인했다. 마지막 지침 보완 뒤 같은 세션 설명 후속은 별도이며 정상 업무 전체 재인수로 표시하지 않는다. 검토자 partial·물리검수not_run·대표성/빈catalog 신규 조사10분·최종 영상/접수 미완료를 유지한다. 아래 Agent1개/서브에이전트 미탑재/Claude 인증 대기는 당시 상태다. HTML·프론트는 웹팀 소유로 이번에 변경하지 않았다.

2026-10-12 최신 작업 마감: product-planning-v7.4의 원문/AI 해석·보류 출처·후기 문맥/집계·실제 시간·취소 대상 전달을 동일 원본으로 제한 평가했다. [최종 결과·한계](../validation/quality-regression-20261012.md)는 Codex10건8통과/2실패·Claude3건2통과/1실패·R06미실행1건이다. 기본 catalog는 empty·lg-kitchen-v4는 명시적 평가 seed다. 최종 전달 오류/420초 timeout/Claude 문맥·지표·귀속 문제를 해결 완료로 쓰지 않는다. 구조/코드 검사·native 의미·사업 효과·전체 청구·최종 제출은 서로 다른 판정이다. 현재 요청3항목은 종료했으며 발표/관찰·영상/웹·최종 접수는 별도다. 아래 버전별 내용은 이력이다.

2026-10-11 최신 v7.2: [실제 Codex·Claude 인수/한계](../validation/claude-codex-v72-20261011.md). 각4입력/3대화 저장·최종 전달을 대조했고 기획 해결과 의미 인증은 구분한다. 최신 기본 catalog는 empty이며 예전 v4는 평가 재현 자료다. 실제8입력 동결본과 최종 키 접미사 수정본을 구분한다. 토큰은 native main 관측이며 총 청구·전체 backend 사용량을 보증하지 않는다. Claude Desktop 인수는 CLI 인증/개발용 위임 인수가 아니다. 최신 남은 작업은 위 보고서를 따른다. 아래 문단은 각 버전 당시의 이력이다.

2026-10-11 최신 v7.1: 빈 catalog에서 실제 질문→조사·등록→같은 요청 기획 경로를 구현하고 열린 이슈5건을 전수 검토해 #4/#5를 수정했다. 제품174·평가145개 일반 코드 검사 통과. 동결 v7.0 실제 진단은 완료1/시간초과3/미실행1, 별도 같은 요청 복구1건 완료이며 최신 v7.1 native·Claude·웹 연결 인수는 미완료다. 사람 대비 절감효과 측정은 사용자 선택으로 제외했다. [구현/진단 결과](../validation/request-driven-20261011.md) · [이슈 검토](../validation/open-issues-20261011.md). 아래 기록은 각 당시 버전의 이력이다.

2026-10-11 신규 요청 기반 경로(v7.0): 사용자가 새 모델 조사·등록까지 확장하도록 승인했다. 기본 설치는 빈 catalog이며 native AI가 질문을 해석해 실제 근거를 조사하고 정확 모델/출처를 등록한다. open_request 원문 보존 → 연구 사건 → 같은 요청 resolve_request_bundle → 기획/검토/저장으로 연결한다. 특정 질문·제품 enum·기본5모델 답안 선택 경로를 사용하지 않는다. Claude 중복 미확인 null·공식 원문/해석 분리 지침을 보완했다. 현재 구현/코드 검증과 실제 AI 검증은 [최신 작업 기록](../validation/request-driven-20261011.md)으로 구분한다. 아래 과거 기본자료·미채택·대기 설명은 당시 이력이다.


## 현재 범위

2026-10-11 사용자 변경: 냉장고·전자레인지·식기세척기의 실제 불편 기반 상품기획. 제품군 일반명으로 시작하는 family_catalog와 특정 모델로 좁히는 exact_model을 구분한다. 제품군 후속은 전체 범위를 유지하고 각 주장·대조·기획의 근거는 같은 정확 모델/버전에 귀속한다. 일반 입력10개와 기존 모델코드50개는 버전별 별도 회귀다. 기본 lg-kitchen-v4·5모델/8후기/26사실, catalog family와 exact scope 일치 검사. Agent1개·업무5Skill+조건부 외부 조사1Skill 유지. 구현 단계와 검증 계획은 concept의 implementation_steps/validation_plan으로 저장하며 planned_not_measured만 허용한다. 구버전 결과 호환은 유지한다. Codex 기준, Gemini 철회, Claude native 후순위. 아래 냉장고3모델/세 실행기 내용은 이전 범위의 이력이며 최신 [결정](../decisions/kitchen-scope-20261011.md)·[v4 근거](../data/kitchen-v4.md)를 우선한다. 웹은 팀이 개발 중이고 원본 미수신 상태다.

기준일: 2026-10-10. 이것은 출품 구현 계획이며 개발용 Codex/Claude 체계가 아니다. [요구](../competition-requirements.md), [채택 스택](../decisions/stack-selection.md), [AI 평가 입력](../evaluation/judge-input-cases.md)을 연결한다.

사용자 선택: 공통 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 각각 연결한다. [실행 결정](../decisions/product-runtime.md)을 따른다. 출품 실행기 내부 모델 연결을 사용하고 자체 모델 API 프로그램·Codex 내부 호출 실행기는 초기 경로로 채택하지 않는다. 아래 업무·근거·예외 계약은 각 지원 환경에서 실제 구현·검증해야 한다. 구조·실행 시각화는 후순위의 [별도 관찰 프로그램](observability-viewer.md)에서 제공한다.

## 실행 책임

초기 업무 설계는 각 실행기의 메인 Agent가 상품기획 역할을 맡고 업무 Skill 5개와 조건부 외부 조사 Skill 1개를 사용하는 구성이다. Agent 원본은 agents/product-planning.md, Skill 원본은 skills/이며 본문·실행 wrapper를 작성했다. Codex 설치·발견·실제 업무 연결은 [인수 기록](../validation/codex-product.md)을 따르며 Claude/Gemini는 S02에 남는다. 모델이 기획 조건 해석·불편 구조화·후보·검토를 담당하고 제품 모델 ID·근거 ID·필수 필드·검색 필터·업무 상태·결과 검증·저장은 공통 코드가 처리한다. 환경별 업무 지침과 Skill/명령 Tool 연결로 같은 계약을 충족한다. 개발 역할 6개와 Skill 9개는 별도이며 세 실행기를 하나의 자동 팀으로 묶지 않는다.

업무 지침과 Tool은 허용된 입력·범위를 정의하고 코드에서 계약을 검사한다. 모든 Skill을 매번 읽거나 모든 단계의 LLM 호출을 강제하지 않는다. 자료 부족이면 추가 확인/보류, 기존 기능으로 충족되면 새 기능 후보 제외, 입력 변경이면 관련 단계부터 재검토한다. 실행기 자체의 모든 도구를 문서 지침만으로 기술적으로 제한했다고 주장하지 않는다. 단순 정해진 문장 출력이나 준비한 정답의 선택 프로그램으로 만들지 않는다.

## 업무 Skill

| 폴더 이름 | 실제 기능 | 주요 코드 Tool |
|---|---|---|
| `evidence-retrieval` | 같은 모델·버전의 리뷰·제품 자료 조회 | retrieve_reviews, retrieve_product_facts |
| `web-evidence-collection` | 저장 근거 부족·최신 요청·불명확한 모델 연결 시 외부 조사·새 버전 등록 | fetch_web_page, capture_web_page, import_web_evidence; 제공되는 native 검색/브라우저/PDF |
| `needs-structuring` | 원문에 연결된 불편·조건·상충 의견 정리 | select_evidence, validate_source_refs |
| `feature-comparison` | 기존 기능·사용 조건과 남은 불편 대조 | match_product_scope, retrieve_product_facts |
| `concept-writing` | 근거 있는 콘셉트 최대 3개·요구사항·가정 작성 | validate_constraints, validate_source_refs |
| `review-and-revise` | 중복·근거·모델 연결·가정 검사, 제한된 수정/보류 | validate_source_refs, validate_result_contract |

각 폴더의 SKILL.md에는 역할·사용 조건·입출력·실행 방법을 적고 필요한 코드·자료만 포함한다. 원본은 `skills/`이며 별도 출품 설치 폴더에 환경별 정규 사본을 생성한다. 설치 manifest가 이름·버전·원본 지문·환경별 Tool 명령을 연결한다. 현재 개발 `.agents/skills`와 `.claude/skills`를 덮어쓰지 않는다. 본문 로딩과 실제 Tool/업무 실행·완료·실패를 따로 기록하고 SKILL.md만으로 기능 구현 완료를 주장하지 않는다.

개발 체계의 evaluator/reviewer는 출품 Agent의 서브에이전트가 아니다. 추후 독립 업무 Agent가 필요하면 동일한 평가·사용량 기준으로 추가 이유를 확인한다.

## 입력·근거·출력

[컨설팅 반영](../consultation/2026-10-10.md)에 따라 업무 기본 자료는 실제 제품·리뷰이며 합성 자료는 시험 전용이다. 모델 선택에서 내부 입력을 생성하는 `prepare_planning_input`을 구현했다. 사용자가 불편을 상세히 입력할 필요 없이 AI가 근거에서 불편을 추출해야 하며 해당 Skill 지침·공통 코드 연결을 작성했으며 Codex 실제 업무 연결을 확인했고 Claude/Gemini는 미검증이다. 현재 실제 pilot의 긍정 후기만으로 불편을 만들어내지 않고 추가 자료 요청·보류해야 한다. 정확한 외형 치수는 내부 치수·선반 배치 가능성의 근거가 아니다.

- PlanningInput: 사용자 질문, 제품군·모델 범위, 대상·맥락, 조건·제외 항목, 데이터 버전, session_id, 요청 키.
- EvidenceRef: source_id, review_id 또는 document_id, model_id, model_version, 문서 위치, 원문 지문, synthetic 여부.
- ProductResult: status(completed/needs_input/held/failed/cancelled), pains, existing_features, remaining_pains, concepts(최대 3개), assumptions, evidence_refs, validation_findings, revisions, usage_summary.
- 제품군 탐색은 등록 catalog의 모델·자료 버전을 확정해 시작하며 사용자에게 모델코드를 강제하지 않는다. 제품군 자체가 모호하거나 보유 제품의 치수·안전 판정에 정확 모델이 필요하면 확인 요청한다. 필요한 근거가 없으면 보류하며 source_id의 존재만으로 주장의 의미가 맞다고 통과시키지 않는다.
- 원문·추출 결과·콘셉트의 연결을 보존한다. 문서에 기능 설명이 없다는 것과 기능 부재를 구분한다.
- 원문 안의 지시문은 입력 자료이며 실행 권한을 주지 않는다.

공통 도구의 실제 구현·입출력·오류·크기·검증 한계는 [공통 도구 계약](../contracts/common-tools.md)을 따른다. 이는 업무 Agent·Skill 구현 및 세 실행기 호환성 인수 완료가 아니다.

공통 업무 상태에는 입력/원문 지문, 제품 모델 범위, 실행기의 실제 모델·설정·버전, 계획, 근거, 불편·대조·콘셉트, 검증 결과, turn_id와 turn별 revision_count, 우리 Tool invocation별 technical_retry_count, 관측된 호출/사용량, 한도와 중단 상태를 저장한다. 네이티브 대화 세션과 업무 run/turn 연결은 환경별로 검증한다. LangGraph GraphState를 초기 필수 구성으로 두지 않는다.

## 예외·종료·재사용

- 업무 수정 최대 2회는 사용자 요청 한 turn의 결과 생성에 적용한다. 최초 생성은 수정 횟수에 포함하지 않는다. 검증에 실패한 후보도 최초·수정 시도로 기록한다. 검토 후 미해결이면 사유와 자료를 보존해 보류한다. 같은 turn의 재개·재접속·중복 요청은 횟수를 초기화하지 않는다.
- 사용자가 새 추가 질문이나 조건·사양 변경을 제출하면 새 업무 turn을 만들고 해당 turn의 수정 횟수를 0부터 관리한다. run 전체의 이전 turn·수정·관측된 사용량은 보존한다. 공통 Tool의 호출·시간 상한을 적용하고 실행기 계정의 사용 제한은 환경별로 확인한다. 미측정 비용을 남은 예산 계산에 임의로 채우지 않으며 내부 실패만으로 새 turn을 자동 생성하지 않는다.
- 우리 Tool의 기술 재시도는 논리적 invocation별 별도 상한·timeout을 갖는다. 초기에는 재시도 가능한 오류만 한 번 더 시도한다. 재개·중복 요청으로 같은 invocation의 재시도 횟수를 초기화하지 않는다. 네이티브 실행기의 내부 모델/API 재시도와 이 Tool 정책은 별개다.
- 네트워크 실패, 빈 조회, 잘못된 모델 ID, JSON 오류, 근거 부족을 같은 오류로 처리하지 않는다.
- 공통 Tool의 외부 작업에는 timeout과 업무 제한을 적용한다. 네이티브 모델 호출·재시도·중단은 실행기의 실제 지원 범위를 확인하고 우리 Tool 재시도와 구분한다. Skill 지침의 호출 상한만으로 실행기 내부 호출을 완전히 통제한다고 가정하지 않는다.
- 사용자 추가 질문은 이전 입력·출처·가정을 연결해 처리한다. 조건·제품 사양·자료 버전이 바뀌면 관련 결과를 무효화하고 필요한 단계만 다시 수행한다.
- 재사용 키는 원문/모델/문서 버전·규칙·Skill·프롬프트·모델 설정 지문을 포함한다. 필요한 원문만 다시 전달하고 정확한 모델 필터를 유지한다.
- 요청 키로 중복 실행을 방지한다. UI 재접속이나 기록 재생은 새 LLM 요청을 만들지 않는다.
- SQLite thread_id는 실행 상태 분리 키이며 인증·권한 경계가 아니다.

## 관찰 이벤트와 별도 시각화

선택한 네이티브 실행기가 업무 결과를 생성하고 실제 이벤트·로그 및 공통 Tool 기록을 일반 코드 수집기가 별도 관찰 프로그램으로 내보낸다. 관찰 도구를 위한 LLM·Agent·Skill을 추가하지 않는다. 로그를 모델 문맥에 되돌려 넣지 않는다. 환경별 관측 범위를 실제로 검증하고 실행별 ID와 관측 가능한 부모·자식·호출 ID를 유지한다. 관찰 연결은 업무 평가의 선행 조건이 아니다.

```text
schema_version, run_id, event_id, seq, timestamp,
invocation_id, parent_invocation_id,
entity_type(agent|skill|tool|model), entity_name,
event_type(started|result|error|retry|held|needs_input|
           cancel_requested|cancelled|finished),
attempt, input_summary, output_summary, source_refs,
usage(measured|null), duration_ms,
error{code,message,retryable}, payload_ref
```

메인·서브에이전트 위임을 실제로 구현하는 경우 `delegated`/`returned`와 실제 발신·수신 호출 ID를 추가한다. 시간상 앞뒤로 실행한 두 노드를 메시지 교환으로 꾸미지 않는다.

다음 HTTP API는 과거 독립 실행 후보의 설계 기록이며 현재 출품 경로에는 구현하지 않는다. 실제 업무용 웹/API 요구가 생기면 별도 변경으로 검토한다. 외부 관찰 프로그램 자체의 API와 구분한다.

| 조건부 업무 API | 역할 |
|---|---|
| POST /runs | 입력·요청 키로 실행 생성 |
| GET /runs/{id}/events | SSE, id/Last-Event-ID로 기존 실행 구독·누락 보충 |
| GET /runs/{id} | 결과·현재 상태·사용량 조회 |
| POST /runs/{id}/input | 추가 질문·변경 조건을 새 turn으로 연결 |
| POST /runs/{id}/cancel | 중단 요청; 실행기가 확인하면 cancelled |
| GET /runs/{id}/export | 실행 결과·이벤트를 JSON/JSONL로 내보내기 |

별도 관찰 프로그램에서 Agent/Skill/Tool 구조와 실행 관계·상태·오류·시간·관측된 사용량을 표시한다. 기존 OSS 도구를 우선 검토하고 자체 React Flow 내장 UI를 구축하지 않는다. 내부 사고 전체를 모델에게 생성시키지 않고 확인 가능한 실행 사실과 기존 입력·결과를 표시한다. 업무 결과는 선택한 실행 방식의 CLI·파일·기존 화면 등에서 제공할 수 있다.

성공·보류·오류·취소는 실제 이벤트로만 변경한다. 5개 Skill을 5개 Agent로 표시하지 않는다. 기록 재생은 "실행 기록 재생"으로 표시하고 LLM·업무 Tool을 호출하지 않는다. 외부 도구의 중첩·시간 추론 그래프를 실제 메시지 전달이라고 단정하지 않는다. 수집·표시 실패가 업무 실행을 중단시키지 않도록 격리한다.

## 검증·토큰 감사

선택한 코드 검사 도구로 입력·모델/근거/조건 계약·분기·업무 수정·기술 재시도·상태 저장·재사용 무효화·중복 요청·예산 정책을 검사한다. 실제 실행→외부 관찰 기록→구조·흐름 표시와 업무 결과의 일치를 검사한다. 관찰 on/off 모델 요청 수·입출력·usage, 관찰 도구 종료·단절·재생의 실행 격리를 확인한다. mock/fixture 시험과 실제 모델의 업무 평가를 별도 표시한다.

평가는 개발 예시와 별도 입력, 동일한 신규 자료·모델·조건을 사용하는 강한 단일 프롬프트 baseline과 비교한다. 출처의 정확성, 모델 연결 오류, 기존 기능 중복, 보류/추가 질문, 사용자 수정 시간, 완성 작업 시간·비용을 기록한다. 일부 반복 실행과 독립 근거 확인으로 우연한 성공·평가 편향을 점검한다. 품질 통과 사례의 상세 비교와 함께 동일 평가 묶음 전체의 요구 충족률·총비용·실패율을 보고하며 실패·재시도 비용을 빼지 않는다. 기대 행동이 보류·추가 질문인 사례는 그 행동과 근거를 충족하면 평가 성공이다.

토큰 합계에는 계획·후보·검토·수정·서브에이전트·요약 등 실제 발생한 모든 모델 호출을 포함한다. 캐시 토큰·생각 토큰은 제공사가 반환하는 범위를 기록한다. 미측정을 0으로 처리하지 않는다. 토큰 절감은 품질 기준을 유지한 동일 작업의 전후 기록으로 설명한다.

현재 효과 검증은 AI 자체 실행시간·토큰·오류/수정·근거·요구 충족도를 기록한다. 사람 직접 작업 시간 비교는 2026-10-11 결정으로 제외했다. 상대 절감률을 주장하려면 동일 모델·자료·성공 기준의 비교가 필요하며 미입증 절감률은 쓰지 않는다.

## 제출·시연 인수 조건

- 실행자 설치·인증·준비 검사·첫 질문·후속 질문·결과 확인 절차를 환경별로 실제 검증한다. 지원 목록에 검증한 실행기·모델·설정·OS 버전을 적고 미검증 환경을 통과로 표시하지 않는다. 출품 ZIP의 업무 지침·Skill은 개발 체계와 분리한다.
- 정상 요청, 기존 기능 중복, 근거 부족/모델 혼동, 추가 질문/사양 변경, 실제 Tool 오류를 준비한다. 모든 경우를 영상 길이에 억지로 넣지 않고 핵심 사례와 추가 실행 입력을 구분한다.
- 외부 관찰 화면·업무 결과·근거·실행 로그가 같은 실행을 가리키는지 확인한다.
- 관찰 도구 중단·재접속·기록 재생에서 이벤트 누락/중복과 LLM 중복 호출을 검사한다. 업무 취소·추가 질문은 업무 실행 인터페이스에서 처리한다.
- README에 Python/Node/의존성/데이터/모델 계정과 환경 변수를 명시한다. key·실제 개인 설정·계정 정보는 ZIP에 넣지 않는다.
- 공고의 발표자료 20페이지·발표 10분/질의응답 5분을 확인하고, 제출 직전 영상 규격·마감 시각·제출 경로·파일명·변경 공지를 요구 원본에 확정한다. 미확인 항목은 임의로 채우지 않는다.
- 새 환경에서 전체 흐름과 각 핵심 Skill의 재실행을 확인한다. 실행한 코드·데이터·Skill·모델 설정·프롬프트 버전을 기록한다.
- 발표·영상·ZIP은 실제 구현 범위와 검증 결과만 설명한다. mock 화면·라이브러리 호환성 stub을 출품 AI의 동작 근거로 사용하지 않는다.


## 이번 원본 구현 범위

상품기획 Agent1개·업무Skill5개+조건부외부조사1개, 일반 코드 wrapper·보고된 의미 검토 정합성 검사·HTTP관측/native본문기록/자료버전등록을 작성했다. 기본 실제 자료는3모델·후기6발췌·공식사실19개이며 [확인 한계](../data/real-research.md)를 따른다. S836GBB122 긍정-only 보류, 정확한 현재 불편·기존 기능 대조는 업무 지침으로 연결한다. Codex 별도 설치·native 자동발견·첫/후속 입력·보류/오류·저장/export와 관측 CLI 누적 사용량을 확인했다. [지원 제한](../validation/codex-product.md)을 따르며 Claude/Gemini(S02/S03b2), AI품질·효과(S05), 제출(S06)은 미완료다.

추가된 [S05 후속 검증](../validation/s05-followup.md)은 보완 baseline과 실제 추가 입력·예외를 한정된 자료/설정에서 비교한다. [취소·재시도 보강](../validation/s05-hardening.md)에서 로컬 업무 취소를 구현하고 일반 코드 경계를 확인했다. native/backend 중단을 보장하지 않는다. J17 반환 원문은 두 조건 실제 전달, 삽입 조건 최종 저장 일치를 확인했지만 정상 조건 timeout으로 비교 미통과다. 전체 청구·사람 공수·시장 신규성·일반화는 미검증이다. Claude/Gemini는 [설치 사본·공통 Tool 검사](../validation/portable-product.md)까지만 확인했으며 실제 로그인/발견/업무는 남아 있다. [시연 준비](../validation/s06-demo-preparation.md)는 구성·근거·새 ZIP 재현이며 실제 발표/영상·최종 제출 인수는 미완료다.
