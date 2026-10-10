# 별도 관찰 수집과 Langfuse 실제 연결

2026-10-10. 사용자 승인 범위는 API 키 생성·로컬 비공개 보관과 실행 ID·Tool 종류/상태·지침 읽기·관측 사용량 전송이다. 원문 질문·답변·생각·명령·개인 경로는 제외했다. 이 기록은 출품 업무 품질이나 전체 청구 검증과 별도다.

## 구현과 검사

`observer/`는 Python 표준 라이브러리의 별도 `replay`/`tail` 프로세스다. 명시적으로 지정한 native UUID의 CLI JSONL 및 해당 rollout만 읽는다. 업무 프로세스를 실행·중단하거나 로그를 모델 문맥에 전달하는 경로는 없다. 실제 parent가 없는 사건을 메시지 교환·Agent Graph로 만들지 않는다. Skill 파일 읽기는 `instruction_loaded`, 알려진 명령의 Skill 연결은 `command_based_mapping`이다.

커밋 5b0d1ef/e96cbfb/5ce3d42를 독립 worktree에서 통합했다. 부모 및 독립 검토에서 observer 34검사 exit0을 확인했다. custom Tool 반환 누락, wrapper 오류 분류, 부분 누적값의 역행, 중첩 metadata 객체의 전송을 발견해 수정한 뒤 재검사했다. 두 원본의 ID를 추정 병합하지 않으므로 고유 Tool 총수는 미측정이다. 원문·키 제거, ID 불일치, 중복·재접속, queue/drop, 실제 loopback timeout, 전송 실패 격리가 검사 범위다.

## 실제 본 실행 tail과 클라우드

GitHub 로그인·이메일/프로필 읽기 및 키 생성은 각각 사용자가 승인했다. Cloud 화면에서 서버 v4.56.0, Hobby, `My Project`를 확인했다. AI 기능은 켜지 않았다. 자격증명은 Git 제외 `.harness/private/langfuse.env`에 보관했으며 키 값은 문서·명령 인수·원격 저장소에 기록하지 않았다.

관찰 실행 `compact-live-repeat-1`은 실제 출품 평가가 진행 중일 때 지정한 두 로그를 tail했고 native 종료 사건을 관측한 뒤 수집기만 종료했다. native `01a12617-3c15-7e70-bf38-7ba0c9d3c45d`, Codex0.162.0. 실제 명령 exit0, `stop_reason=observed_terminal_event`, reader 오류 없음.

| 관측 | 결과 |
|---|---|
| 허용 사건 | 55건 |
| CLI command 반환 / 관측 실패 | 11 / 0 |
| rollout custom Tool 반환 / 관측 실패 | 7 / 0 |
| 고유 Tool 수 / backend 모델 호출 수 / 현금 비용 | 모두 미측정 |
| v4 OTLP 큐 / export / drop / 실패 / 중복 | 25 / 25 / 0 / 0 / 0 |
| 종료 시 입력 / 그중 캐시 / 출력 / 그중 reasoning | 269,249 / 231,296 / 9,123 / 3,043 |
| 비캐시 입력 | 37,953 |
| 관찰자가 만든 모델 요청 / 추가 모델 문맥 | 코드 경로 및 실제 관찰에서 0 / 0 |

CLI turn 집계와 rollout 누적값은 같았지만 더하지 않았다. 누적 snapshot들도 합산하지 않았다. 비용·모델 generation 속성을 보내지 않으므로 Langfuse 기본 토큰·비용 열의 빈 값은 실패나 사용량0을 뜻하지 않는다. 사용량은 `native_usage_snapshot` metadata로 확인한다. Cloud의 environment 표기는 개발 관찰 공간이며 실제 대상의 출품/개발 구분은 run/native ID와 로컬 기록을 함께 따른다.

[실제 Tracing 화면](https://cloud.langfuse.com/project/cmv2g19wu1pdsad0ef01nm86z/traces)에서 native-observer Tool/runtime 사건과 metadata를 직접 확인했다. HTTP 수락만으로 화면 표시를 주장한 것이 아니다. 비공개 화면 증거와 summary/events/checkpoint는 `.harness/observer/`에 보존했다. 원문 로그는 Git에 넣지 않았다.

## 시연과 남은 범위

별도 창에서 Langfuse를 띄우고, 같은 실행 ID의 실제 입력·최종 답변은 기존 Codex 창에서 보여준다. 연결 장애 때 cloud0의 로컬 journal을 보존하고 `실행 기록 조회`라고 밝힌 재생을 사용한다. 녹화 오류로 업무를 자동 재실행하지 않는다. 자세한 명령은 [observer README](../../observer/README.md)다.

이번 인수는 Codex CLI/rollout·완료 span·metadata와 라이브 tail 연결이다. 모든 환경의 Skill 의미·하위 Agent·메시지 그래프, 기존 데스크톱 대화 자동 구독, Claude/Gemini 수집, 전체 청구, 관찰 on/off 무작위 반복 비교, 발표 가독성·30초 녹화는 미완료다. 완료 사건을 전송하므로 진행 중 상태는 로컬이 먼저 갱신되고 cloud에는 지연이 있다.

사이드 대화의 작은 HTML 상태·토큰 카드/OBS Browser Source는 후속 제안으로 접수했다. 추가 LLM 없이 기존 journal을 일반 코드로 읽고 live/replay·갱신 시각·미측정·캐시 부분집합을 표시하는 방향이다. 현재 채택·구현하지 않았다. Grafana/React Flow를 작은 위젯의 필수 의존성으로 추가하지 않는다.

공식 연결 근거: [OpenTelemetry/HTTP JSON](https://langfuse.com/integrations/native/opentelemetry), [v4 완료 span](https://langfuse.com/integrations/native/opentelemetry/migration-to-v4). 위젯 후보 근거: [OBS Browser Source](https://obsproject.com/kb/browser-source), [Langfuse Custom Dashboards](https://langfuse.com/docs/metrics/features/custom-dashboards).
