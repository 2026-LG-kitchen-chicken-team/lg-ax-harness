# v0.10.0 기록 어댑터

기준은 `product-v0.10.0` (`cdf0e6e`)입니다. 기존 core·Skill·계약·설치 파일을 바꾸지 않고 세션 export 파일을 브라우저에서 읽습니다.

`src/catalog.ts`의 `nodes`는 `agents/product-planning.md`, `docs/contracts/product-research-agents.md`, `skills/manifest.json`의 메인 1·선택 역할 3·업무 Skill 6을 표현합니다. 카탈로그에 있다는 사실은 실제 호출의 증거가 아닙니다.

`createDemoTrace(): HarnessTrace`는 84초의 **합성 연출**입니다. 두 연구 역할의 병렬 위임·반환, 메인의 원문 등록, 여섯 Skill의 업무, 독립 검토, held gate, 동일 turn 수정과 저장을 보여줍니다. 측정된 업무 시간·사용량·실행 성공을 주장하지 않습니다.

`parseHarnessTrace(input: unknown): HarnessTrace`는 `export_session`이 `runtime-data/exports/`에 쓴 JSON **파일 본문**, 또는 화면의 내려받기로 저장한 정규화 `HarnessTrace`를 받습니다. `path`·`sha256`만 있는 Tool 응답 receipt는 원문이 아니므로 거절합니다. 원본을 `raw`로 보존하고 실제 관측 시각을 상대 초로 바꿔 정렬합니다.

정규화 trace 재입력은 `mode`·제목·session·시간·사건 ID/종류/노드/상태·설명·경고·지표·JSON 원본을 검증합니다. 사건은 1~25,000건, 시간축은 1초~365일, JSON은 25MB까지이며 시각이 뒤로 가거나 중복 ID·잘못된 노드·NaN·비JSON 원본이 있으면 거절합니다. `demo`는 `demo`로 유지하고 session·지표는 `null`이어야 합니다. 정규화 `recorded`의 노드 양끝은 모두 메인이어야 하며 위임·통신 연출을 추가할 수 없습니다.

세션 export 형식의 입력에 `synthetic:true` 또는 `schema_fixture:true`가 있으면 제목에 **[형식 검증용 합성]**을 붙이고 실제 실행 기록이 아니라는 경고를 남깁니다. `fixtures/format-fixture.json`은 화면·형식 검증용이며 제품 조사 실적이 아닙니다.

읽는 v0.10.0 필드는 다음과 같습니다.

| export 필드 | 화면에서 표현하는 범위 |
| --- | --- |
| `requests[].workflow.started_at` | 최초 업무 시계 시작 기록 |
| `requests[].workflow_events[]` | `observed_at`의 조사 journal. 메인 사건으로만 표현 |
| `requests[].events[]` / turn 전 `response` | 시각 없는 요청 version·보류 상태 metadata |
| `turns[].invocations[]` | `tool_name/status/attempts` 호출자 신고. 실행 시각이 없으므로 0초 metadata |
| `turns[].evidence_coverage_history.deliveries[]` | `observed_at`의 등록 원문 전달 기록 |
| `turns[].evidence_coverage_history.review_reports[]` | 검토/제외의 호출자 신고 |
| `turns[].state.result_history[]` | `created_at`의 후보 구조 승인 또는 거절·보존 |
| `turns[].state.cancellation` | 로컬 업무 쓰기 취소. native/backend 중단과 구분 |
| `usage_summary` | 기록 호출의 input+output 토큰. 일부 필드 미확인이면 `null` |

v0.10.0 export에는 native 서브에이전트 호출·실제 반환 ID·메시지 타임라인이 없습니다. 설치 설정, 역할 packet, `source_scan`, 문자열에 등장하는 역할명으로 위임이나 통신을 만들어내지 않습니다. 모르는 journal 종류도 메인 metadata로 보존합니다. 고유 operation의 Skill 소속은 설명에만 표시하고, 공유 operation은 소속 불명확으로 남깁니다. 시각 없는 기록으로 병렬 실행·실행 순서·소요 시간을 만들어내지 않습니다.

`metrics.evidence`는 전달 장부에 관측된 고유 `source_id` 수이며 고객 수·자료 충분성·의미 품질이 아닙니다. 전달 장부가 없으면 `null`입니다. `metrics.tokens`는 native 전체 사용량을 뜻하지 않습니다. 수집·저장·의미 검토·화면 검수·native 종료는 서로 다른 증거입니다.

파서는 파일 I/O·네트워크·업무 Tool 실행·DB 쓰기를 하지 않습니다. UI의 로컬 JSON 가져오기에만 연결하며 원본 필드는 화면 상세에 필요한 범위에서 읽습니다.

검증: `npm test`는 실제 exporter의 필드 구조, 시각 정렬, held 보존, 미측정 값, 가짜 위임 방지, 모호한 operation과 receipt 거절, 내려받은 trace 왕복, 잘못된 사건 검증과 합성 fixture 표시를 확인합니다. 테스트 fixture와 데모는 실제 제품 조사 실행 기록이 아닙니다.
