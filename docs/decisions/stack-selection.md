# 기술 스택 채택 기록

결정일: 2026-10-10. 범위: 신규 LG AX 프로젝트. 개발용 기술은 아래 확정 구성으로 실제 구축·검증했다. 사용자가 출품 실행 방식을 선택했으며 업무 구현·모델·환경별 검증·시각화는 별도로 남는다. 개발 체계 검증을 출품 AI 품질 통과로 바꾸지 않는다. 요구 원본은 [대회 요구와 범위](../competition-requirements.md)다.

최신 사용자 선택: 공통 출품 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 각각 연결한다. 설치·계정 인증 후 기존 실행기에서 자연어로 질문한다. [출품 실행 결정](product-runtime.md)의 지원 목표·검증 순서를 따른다. 모델 API 직접 호출 프로그램과 Codex 내부 호출 실행기는 초기 경로로 채택하지 않는다. 과거 독립 실행 후보의 패키지·검사 기록은 대안 검토 이력이며 현재 필수 의존성이 아니다. 시각화는 [별도 관찰 계획](../plans/observability-viewer.md)의 후순위다.

이번 공통 Tool 구현은 Python 3.12 표준 라이브러리 JSON·hashlib·SQLite·unittest를 채택했다. 작은 자료의 정확한 모델/버전 조회·타입·원문 지문·트랜잭션·멱등성을 실제 검사했고 추가 패키지는 설치하지 않았다. [공통 도구 계약](../contracts/common-tools.md)을 따른다. [컨설팅](../consultation/2026-10-10.md)에 따라 업무 자료는 실제 제품·리뷰, 합성 자료는 시험 전용이다. 벡터 검색이나 별도 Agent 프레임워크가 필요할 규모·업무가 확인되면 재검토한다.

최신 우선순위: 개발용 하네스 구축을 먼저 진행하고 시각화 선택·구현은 후순위로 둔다. Codex/Claude가 실행을 맡고 우리 React Flow UI가 이벤트를 표시하는 후보도 가능성 검토에 포함한다. 내장 화면 채택 철회를 기술적 불가능이나 영구 금지로 해석하지 않으며 현재 UI를 새로 채택하지 않는다.

## 선택 기준

같은 모델의 원문 대조, 근거 부족 보류, 업무 수정 최대 2회, 추가 입력에 따른 재검토, 실제 실행 시각화, 토큰·완성 작업 비용 측정, Windows 실행, 소스 ZIP 재실행을 기준으로 판단한다. 서브에이전트 수나 프레임워크의 인지도에 점수를 주지 않는다.

## 채택

| 영역 | 선택 | 선택 이유 / 검증 상태 |
|---|---|---|
| 개발용 기반 | `revfactory/codex-harness` + Codex 네이티브 서브에이전트 | 고정 commit 원본20파일·LICENSE/NOTICE·patch 기록을 도입. 6개 역할·9개 Skill·실제 native 위임/메시지/turn 중단·구현/검사/통합 확인. custom role 자동 적용 대신 지침 전달 fallback |
| Claude 개발 연결 | Claude 네이티브 Agent + 공통 개발 Skill의 프로젝트 사본 | 6개 Agent·9개 Skill 정규 사본 및 drift 검사를 구축. Codex와 별도 native 실행. 로컬 Claude CLI/인증 부재로 팀원 실제 인수는 미실행 |
| 개발 검사 환경 | Python 3.12.x + uv/uv.lock + stdlib subprocess/unittest | 3.12.14에서 실제 명령·실패·timeout·binding·stale·resume 검사. 모델 SDK와 별도; 새 Node/Web/LLM 서버 없음 |
| 출품 실행 제어 | 공통 업무 Skill·코드 + Codex/Claude Code/Gemini CLI의 네이티브 실행 | 사용자 선택. 업무 상태·근거·수정 계약은 공통 코드로 검증. 세 환경의 실제 업무 검증은 미완료 |
| 모델 연결 | 선택한 기존 실행기의 모델·인증 | 자체 모델 API SDK는 초기 필수 의존성이 아님. 모델·설정·실행기 버전을 환경별 기록 |
| Skill 설치 | 출품 원본 `skills/` + 환경별 프로젝트 사본 | 개발 Skill 경로와 분리된 출품 폴더에 설치. 정규 사본·지문 검사·준비 검사는 구현 예정 |
| 타입·계약 | Python 표준 라이브러리의 명시적 입력·결과·근거 validator | 실제 공통 도구·예외 시험 완료. 의미·사실성은 미검증. Pydantic v2는 과거 독립 실행 후보이며 현재 추가하지 않음 |
| 웹 API | 조건부 후보: FastAPI + Uvicorn | 업무용 웹/API 필요가 확인될 때 도입. 시각화만을 위해 만들지 않음 |
| 데이터·상태 | 신규 실제/시험 JSON·JSONL 자료, stdlib SQLite | 실제 조회·지문·버전·시도·수정·멱등·실패 rollback·사용량 기록 구현. 업무 기본 자료는 실제 pilot, 합성 자료는 시험 전용 |
| 시각화 | 별도 관찰 프로그램, Langfuse 우선 연결 검증 후보 | 기존 도구의 구조·실행 표현을 검증. 자체 React Flow 내장 UI 채택 철회 |
| 실행 기록 | 일반 코드 수집·ID 연결·외부 도구 내보내기 | 네이티브 이벤트/로그 또는 실행기 추적을 사용. SQLite/SSE는 독립 실행 후보의 구현안이지 모든 방식의 필수 조건이 아님 |
| 개발 검사 | stdlib unittest + 새 Python receipt/장부 wrapper | 실제 exit/log/입력 지문·task/attempt binding과 완료/resume 재검사. pytest/Ruff는 출품 코드 환경 결정 때 재검토 |
| 재현·제출 | 필요한 의존성 잠금, 데이터·모델·프롬프트 기록, ZIP 검사 | README로 새 환경에서 실행·Skill 재실행. 사용자 계정·개발 도구 의존성도 명시 |

초기 시연은 로컬 Windows 실행을 기준으로 한다. 서버 배포·Docker를 필수로 추가하지 않는다. SQLite를 다중 서버 운영까지 검증한 저장소로 설명하지 않는다.

## 실행 프레임워크 비교와 결정

| 후보 | 제공 기능 | 이번 결정 / 다시 검토할 조건 |
|---|---|---|
| LangGraph | 상태 그래프, 코드 처리와 LLM 판단 결합, 체크포인트, 스트리밍 | 초기 출품 경로 미채택. 과거 독립 실행 대안과 호환성 검사 기록을 보존 |
| Deep Agents | Skill 지연 로딩·컨텍스트 관리·파일 도구·서브에이전트의 기성 조합 | 현재 미채택. 긴 외부 조사·파일 작업·지속적 위임이 핵심이 되면 재검토. 기능·위임을 추가한 비용도 측정 |
| LangChain `create_agent` | 모델·Tool 루프와 미들웨어 | 초기 출품 경로 미채택. 네이티브 실행기와 별도 Agent 루프를 겹치지 않음 |
| Pydantic AI | 간결한 타입 기반 Agent·Tool·사용량 제한 | 현재 미채택. 단계 재개·추가 입력·그래프 분기가 불필요하고 한 번의 구조 출력으로 충분하면 대안 |
| Pydantic AI Harness | core에 Skill·계획·위임·컨텍스트 관리 추가 | 현재 미채택. 별도 패키지, 0.x API 변경 가능. Skill 본문 로딩과 스크립트 실행은 구분 |
| OpenAI Agents SDK | Tool 루프, 위임, 구조 출력, 기본 추적 | 현재 미채택. 작은 Tool 기반 Agent에는 적합하지만 이번 상태 그래프와 중복 실행 기반을 두지 않음 |
| CrewAI Crews/Flows | 역할별 팀, 상태·이벤트·분기 | 현재 미채택. 실제 독립 Agent 분리가 품질·비용 평가에서 필요하다고 확인될 때 재검토 |
| Microsoft Agent Framework | Agent/워크플로/Harness 조합, 체크포인트·추적 | 현재 미채택. 더 큰 다중 Agent·사람 확인·복원 요구가 생기면 검토 |
| LlamaIndex / Workflows | 문서 수집·검색, 이벤트 기반 실행 | 현재 미채택. 지금의 작은 모델별 원문 조회가 부족해질 때 검색 계층부터 검토 |
| smolagents | CodeAgent 또는 함수 도구 호출, managed agents | 현재 미채택. 상품기획에서 동적 코드 실행의 필요가 확인되지 않음 |
| eve | 파일 기반 TypeScript Agent·지속 실행 | 현재 미채택. TypeScript 중심 장기 실행·채널 연결이 주목적일 때 대안 |
| AutoGen | 기존 AgentChat/Core 체계 | 신규 도입하지 않음. 공식 저장소의 유지보수 모드·Agent Framework 이전 권고 반영 |

어느 후보도 답변 정확성, 우리 Skill의 실제 업무 구현, 토큰 절감, 심사 입력 대응을 자동 보장하지 않는다.

## 시각화·추적 결정

- 시각화는 개발·시연 때 실행하는 별도 관찰 프로그램으로 분리한다. 하네스의 실행 방식과 관찰 도구의 실행 방식은 독립적으로 판단한다.
- Langfuse를 기존 OSS 관찰 프로그램의 우선 연결 검증 후보로 둔다. 실제 부모·자식·Skill·Tool·메시지의 관측 범위, 가독성·지연·운영 부담을 확인하기 전 최종 채택을 주장하지 않는다.
- React Flow 기반 자체 내장 UI와 자체 SSE 시각화 서버의 기존 채택은 철회한다. 일반 코드 수집기가 외부 도구에 기록을 내보내며, 시각화를 위해 LLM 호출·프롬프트·로그 문맥을 추가하지 않는다.
- 공식 SDK 문서상 Langfuse 수집·조회 지연이 있으므로 실시간 표시 수준은 실제 연결 검사로 확인한다. 그래프의 시간·중첩 관계를 실제 메시지 전달로 단정하지 않는다.
- Langfuse self-host를 초기 필수 스택으로 설치하지 않는다. 현재 다수의 저장소·큐·서비스 의존성이 작은 로컬 시연의 필수 조건은 아니다.
- LangSmith Studio는 선택적인 LangGraph 디버깅 도구다. 소스 ZIP 실행이나 발표 화면의 필수 의존성으로 두지 않는다.
- AG-UI는 여러 UI·런타임의 공통 연결이 필요해질 때 어댑터로 검토한다. 현재 필수로 도입하지 않는다.
- Cytoscape.js는 React를 선택하지 않는 경우나 복잡한 그래프 탐색이 주목적이 될 때의 대안이다.
- 구조만 그린 그래프, 실제 이벤트, 저장 기록 재생을 화면에서 구분한다.

## 모델과 30만 원 예산

LLM은 GPT·Claude·Gemini처럼 답변을 생성하는 모델이다. 출품에서는 선택한 Codex·Claude Code·Gemini CLI의 모델 연결·인증을 사용한다. 환경별 실제 모델 접근·업무 품질·usage는 별도로 검증한다. 사용자는 비용 제약과 Codex 크레딧 62,000개 보유, 본인 Claude·Google 이용 자원 부재를 알렸다. 잔액·유효기간·계정 접근을 확인한 것은 아니며 토큰·호출 횟수·모델 API 잔액으로 환산하지 않는다.

ChatGPT 구독과 OpenAI API 사용은 별도 청구 체계다. Claude 채팅 구독과 Console API도 별도 제품이며 일부 플랜은 월별 API 크레딧 혜택이 있다. 개발 구독만으로 출품 프로그램의 API 사용 가능량·비용을 추정하지 않고 실제 계정의 크레딧·청구 조건을 확인한다.

다음 API 후보·가격·예산 배분은 이전 독립 실행 비교 기록이며 현재 모델 채택이나 API 구매·사용 계획이 아니다. 이 기록을 네이티브 실행기의 과금 계산에 사용하지 않는다. 모델 API 경로를 다시 검토할 때 공식 조건·가격·계정 접근을 재확인한다. 자동 모델 라우터·실패 시 다른 제공사 자동 전환은 초기 범위에 추가하지 않는다.

| 후보 | 공식 표준 단가: 100만 입력 / 출력 토큰 | 구현 조건 |
|---|---|---|
| `gpt-6.1-sol` | $2 / $10, 짧은 컨텍스트 Standard | Tool 호출은 Responses API. `use_responses_api=True` 명시 |
| `claude-sonnet-5-5` | $2 / $10 | 구조 출력/Tool 옵션 확인. 네이티브 citation과 JSON schema 출력의 조합 제약 확인 |
| `gemini-3.8-flash` | $0.75 / $3.75, 2026-12-31까지 | 이후 단가 변경. 생각 토큰·thought signature·어댑터 호환 확인 |

Budget 계획: 초기 모델 비교 30,000원 / 개발·회귀 평가 180,000원 / 시연·발표 60,000원 / 예비 30,000원. 총 300,000원이다. 예산 계획은 실제 지출이나 API 결제·연결 완료를 뜻하지 않는다. 원화 계산에는 실제 청구 환율·세금·수수료와 가격 기준일을 명시한다. 호출 가능 횟수는 완성 작업의 실제 토큰을 먼저 측정한 뒤 산정한다.

공통 계약·저장 검사는 fixture로 수행하고 네이티브 AI 평가는 별도로 기록한다. 미측정 토큰은 0이 아니라 미측정이다. 우리 Tool 호출·업무 수정 상한과 실행기 내부 모델 호출·기술 재시도는 구분한다. 네이티브 실행기에서 제공하는 한도·권한·사용량 기능을 실제 확인하며 외부 프로그램처럼 모든 호출 비용을 미리 예약·통제한다고 가정하지 않는다. 기존 API 예산 배분은 현재 적용하지 않으며 300,000원 제약 안의 환경별 평가 자원은 실제 접근·측정 후 정한다.

## MCP·플러그인 결정

| 범위 | 초기 선택 | 호출 조건 |
|---|---|---|
| 개발: OpenAI API/Codex 설정 | 공식 OpenAI Docs MCP 프로젝트 등록 완료; initialize/tools-list HTTP200 확인 | API·설정이 버전 의존적이거나 불명확할 때 search→관련 원문 조회. Codex는 search_openai_docs/fetch_openai_doc만 활성화. 실패 시 공식 웹 문서 조회 |
| 개발: 코드·Git·검사 | 로컬 CLI·실제 검사 실행 | 담당 작업 범위의 파일·diff·검사 결과가 필요할 때 |
| 개발: 관찰 도구 확인 | 기존 관찰 프로그램·지원되는 브라우저 검사 도구 | 외부 도구에서 실제 Agent·Skill·Tool 구조·실행 흐름을 확인할 때 |
| 출품: 리뷰·설명서·근거 조회 | 공통 조회·검증 코드 + 네이티브 실행기의 명령 Tool 연결 | 입력의 제품 모델·버전·기획 조건에 맞는 근거가 필요할 때. 환경별 명령·경로·권한을 실제 검사 |
| 출품: 외부 연결 | 초기 필수 MCP 없음 | 실제 외부 데이터/API가 필요해지면 같은 Tool 계약 뒤에 MCP 어댑터 추가 |
| 플러그인 패키징 | 초기 필수 플러그인 없음 | 단일 레포의 네이티브 Skill로 시작. 배포·연결의 명확한 필요가 생기면 검토 |

각 Tool은 목적, 허용 입력/범위, 출력 스키마, 근거 필드, 결과 크기 제한, timeout, retry, 실패 후 보류 경로를 갖는다. 개발 연결과 출품 연결의 자격증명·데이터·사용량을 섞지 않는다. 설치된 기존 LG 플러그인·MCP가 있다는 이유로 가져오지 않는다.

## 버전·라이선스·실증 범위

- Windows Python 3.12.14에서 `langgraph==1.2.14`, `langgraph-checkpoint-sqlite==3.1.1` 설치·분기·상태·동기/비동기 이벤트·재열기 검사를 통과했다. [검사 범위](../validation/library-compatibility.md).
- 해당 환경의 Pydantic은 2.14.0, langchain-core는 1.6.9였다. 잠금 파일은 실제 프로젝트 의존성을 함께 해석한 뒤 만든다.
- 과거 내장 UI 후보의 검사 버전은 `@xyflow/react==12.12.0`, React/React DOM 19.3.0, Vite 8.3.4이다. Node 22.23.2 Temp 환경의 타입·빌드 검사 사실은 보존하지만 해당 조합을 새 시각화 도구의 채택 근거로 사용하지 않는다.
- 개발용 upstream은 Apache-2.0. 실제 고정 버전은 commit `80f8217b5b6d3f220a31f05f9c0adaf09dac40f4`, Codex 인수검사는 CLI0.162.0이다. 원본은 vendor에 Git blob bytes로 보존하고 Windows dependency path 한 줄 패치는 patches.json에 기록했다. [개발 실제 검증](../validation/development-harness.md). LangGraph·LangChain·React Flow·React·Vite·FastAPI·Pydantic 핵심 패키지는 MIT 계열이며 실제 도입 시 라이선스 원문·고정 버전·수정 내역을 보관한다. Langfuse 기업용 경로는 별도 라이선스다.
- 출품 Tool 의존성과 실행기별 설치·발견·권한·모델 접근을 실제 검사하고 필요한 잠금 파일을 고정한다. 초기 경로에 제공사 API 패키지·웹 빌드를 자동 추가하지 않는다. GitHub main의 요구 조건을 배포된 패키지 조건으로 바꿔 설명하지 않는다.

## 공식 근거

- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), [실패·재시도·async timeout](https://docs.langchain.com/oss/python/langgraph/fault-tolerance), [checkpointer](https://docs.langchain.com/oss/python/langgraph/checkpointers)
- [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview), [Skills](https://docs.langchain.com/oss/python/deepagents/skills), [LangChain 계층](https://www.langchain.com/oss-overview)
- [Pydantic AI](https://github.com/pydantic/pydantic-ai), [Harness](https://pydantic.dev/docs/ai/harness/), [Harness Skills 제약](https://pydantic.dev/docs/ai/harness/skills/)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk), [CrewAI Flows](https://docs.crewai.com/en/concepts/flows), [Microsoft Agent Framework](https://github.com/microsoft/agent-framework), [AutoGen 상태](https://github.com/microsoft/autogen)
- [LlamaIndex Workflows](https://developers.llamaindex.ai/python/llamaagents/workflows/), [smolagents](https://huggingface.co/docs/smolagents/main/guided_tour), [eve](https://eve.dev/docs)
- [ChatOpenAI / Responses 연결](https://docs.langchain.com/oss/python/integrations/chat/openai), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [OpenAI 가격](https://developers.openai.com/api/docs/pricing)
- [ChatGPT/API 별도 청구](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform), [Claude 구독/Console API와 크레딧](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-is-claude-api-usage-billed-separately-from-my-paid-claude-plan)
- [Claude Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [Claude 구조 출력](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Google 가격](https://ai.google.dev/gemini-api/docs/pricing)
- [React Flow](https://reactflow.dev/learn), [Vite 환경](https://vite.dev/guide/), [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/), [uv lock](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Langfuse Agent Graphs](https://langfuse.com/docs/observability/features/agent-graphs), [수집 지연](https://python.reference.langfuse.com/langfuse), [self-host](https://langfuse.com/self-hosting), [라이선스](https://github.com/langfuse/langfuse/blob/main/LICENSE), [AG-UI](https://docs.ag-ui.com/introduction)
- [codex-harness 고정 원본](https://github.com/revfactory/codex-harness/tree/80f8217b5b6d3f220a31f05f9c0adaf09dac40f4), [Codex Agent](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex Skill](https://learn.chatgpt.com/docs/build-skills), [Claude Agent](https://code.claude.com/docs/en/sub-agents), [Claude Skill](https://code.claude.com/docs/en/skills), [OpenAI Docs MCP](https://developers.openai.com/learn/docs-mcp)


## 개발 기술 확정 범위

OpenSpec/초기 .mjs/npm체계는 실제 제거했다. 메인은 Codex 부모 세션이며 custom role 미노출 환경에서는 실제 네이티브 spawn/followup에 역할 본문·Skill·최신 packet을 넣는다. 자동 TOML sandbox/model 적용은 미검증이며 소유 계약을 ACL이라고 설명하지 않는다. 모델·추론은 사용자 기본값을 상속한다. 서버/추가 LLM API/시각화 패키지 없이 고정 codex-harness와 프로젝트 Python 보강 도구로 운영한다. Claude adapter는 구성·동기화 완료와 팀원 native 인수를 구분한다.

## 2026-10-10 외부 조사·출품 원본 채택

사용자 승인한 실제 자료 확대·출품 Skill 구현에서 조건부 web-evidence-collection을 기존 업무5Skill에 추가했다. Agent는1개다. stdlib urllib/html.parser/SQLite로 제한된 공개 HTTPS 텍스트 수집·관측 본문 저장·새 dataset 버전 등록을 구현했다. native 검색/브라우저/PDF는 실행 환경에 실제 제공될 때만 연결하며 필수 MCP·검색 API·브라우저 프레임워크·모델 SDK를 추가하지 않는다. 사용자가 원문 부족을 보완할 때 실제 모델/옵션·원문 의미와 도구 지원을 검증해야 한다. 세부 제약은 [외부 조사 계약](../contracts/web-evidence.md)을 따른다. Agent/Skill 지침·manifest·코드 wrapper 구현과 native 설치/발견·AI품질 검증을 구분한다.
