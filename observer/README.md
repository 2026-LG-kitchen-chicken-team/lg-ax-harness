# 별도 native 사건 수집기 0.1.0

Python 표준 라이브러리만 사용하는 별도 프로세스다. 기존 Codex의 명시적으로 선택한 JSONL 파일을 읽으며 Codex·모델·업무 실행을 시작하거나 종료하지 않는다. 화면·React Flow·모델 SDK·관찰용 Agent·Skill은 추가하지 않는다. 원본 로그와 로컬 출력은 Git에 넣지 않는다.

## 로컬 기록 조회

레포 루트에서 기존 `codex exec --json` 출력 경로와 **그 로그에 기록된 native UUID**를 직접 선택한다. 이 명령은 새 업무 실행을 만들지 않는다.

```powershell
python -m observer replay --native-id 0199abcd-1234-7000-8000-123456789abc --run-id demo-replay --cli-log C:/private/native.jsonl --output .harness/observer/demo-replay
```

선택 ID의 rollout 경로를 이미 알고 있으면 `--rollout-log C:/private/rollout-ID.jsonl`을 추가한다. 디렉터리를 훑거나 가장 최근 세션을 임의 선택하지 않는다. 원본의 `thread.started.thread_id` 또는 `session_meta.payload.id`가 선택 UUID와 일치하기 전에는 사건을 수집하지 않는다. CLI와 rollout을 같이 선택하면 Tool 사건은 CLI에서, 누적 사용량은 rollout에서 얻어 동일 호출의 두 로그를 두 Tool로 늘리지 않는다. CLI가 `thread.started`를 포함하지 않는 resume 출력은 수집하지 않으며, ID가 있는 rollout을 선택한다.

```powershell
python -m observer tail --native-id 0199abcd-1234-7000-8000-123456789abc --run-id demo-live --cli-log C:/private/native.jsonl --rollout-log C:/private/rollout-ID.jsonl --output .harness/observer/demo-live --until-complete --max-seconds 600
```

`tail`은 마지막 **관측** snapshot을 로컬에 저장한다. `--until-complete`는 선택 로그의 종료 사건을 관측하면 수집기만 종료한다. 기본 실행 상한은 60초, 허용 범위는 0.01~3600초다. `Ctrl+C` 또는 `--stop-file C:/private/observer.stop`의 sentinel도 수집기만 멈춘다. native PID를 받거나 프로세스에 signal을 보내는 경로가 없다. 진행 중 마지막 JSON 줄은 newline이 올 때까지 해석하지 않는다. `replay`만 newline 없는 마지막 완성 JSON을 허용한다.

출력은 허용 metadata만 가진 `events.jsonl`, 로컬 재접속 checkpoint, `summary.json`, 전송 시도 ID 장부다. 기본 사건 journal 4MiB, 입력 파일 최대64MiB, 한 줄1MiB, 활성 ID512개, 큐128개이며 명시된 범위에서 설정할 수 있다. journal이 꽉 차면 오래된 사건을 버리고 checkpoint는 유지한다. 전송 시도 장부가 상한에 닿으면 추가 전송을 실패로 기록하며 기존 span을 재전송하지 않는다. 로컬 사건 저장과 checkpoint를 먼저 완료한 뒤 전송 큐에 넣는다. 원본 prompt·thought·command·stdout·원문 결과·개인 경로·자격증명·응답 오류 본문은 저장·전송하지 않는다. 로그 참조와 불투명 호출 ID는 SHA-256으로 가명 처리한다. 실제 UUID와 `item_N`은 유지한다.

## 의미와 사용량

- 파일 읽기 명령의 `SKILL.md`는 `instruction_loaded`다. Skill 스크립트 경로/알려진 operation은 `command_based_mapping`이다. 둘 다 Skill 실행 성공이나 의미 검토 통과의 증거가 아니다. 명령 완료·실패는 native Tool 사건의 상태다.
- CLI `turn.completed.usage`는 `cli_turn_reported`, rollout `token_count.info.total_token_usage`는 `native_session_cumulative`로 분리한다. 두 값을 더하지 않는다. 세션 누적 snapshot은 역행 없는 최신값으로 교체하고 snapshot들을 합산하지 않는다. 캐시는 입력의 일부, reasoning은 출력의 일부다. 비캐시 입력은 입력-캐시이며 둘 중 하나가 없으면 null이다.
- 부분 snapshot은 `partial`, 종료 사건 관측 시 `completed_observation`이다. 두 경우 모두 **선택한 native 로그의 부분 관측**이다. 미관측 turn ID·parent ID·CLI 버전·backend 호출 수·비용은 null이다. turn별 차이·부모/자식 전체 청구·가격·크레딧 환산은 만들지 않는다.
- source에 명시된 parent만 보존한다. 호출 순서·같은 세션·시간 중첩으로 메시지 전달이나 위임 관계를 만들지 않는다. 실제 Agent Graph/Skill 그래프·데스크톱 자동 구독·Claude/Gemini 수집은 미구현이다.
- checkpoint의 파일별 행 번호가 중복/오래된 재접속을 막는다. 원본 파일이 잘리거나 교체되면 오류가 기록되며 같은 출력 폴더에서 새 원본을 자동 이어 붙이지 않는다. 새 명시적 run/output을 사용한다. 같은 native ID에 여러 CLI 로그가 Tool ID를 재사용한 경우 source별로 구분한다. 입력 파일의 in-place 수정·동시 observer 작성은 지원하지 않는다.

## Langfuse v4 연결

계정/키/전송 endpoint를 설정하지 않으면 `export.configured=false`다. 성공으로 바꾸거나 계정을 설치하지 않는다. **외부 전송을 명시적으로 준비한 별도 PowerShell 세션**에서 `OBSERVER_OTLP_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`를 안전하게 설정한 뒤 위 수집 명령을 실행한다. credential 값을 명령 예제·로그·summary에 넣지 않는다.

`OBSERVER_OTLP_ENDPOINT`는 해당 계정의 정확한 HTTPS URL, 예를 들어 `https://cloud.langfuse.com/api/public/otel/v1/traces`다. 사용자정보·query·fragment·다른 경로·HTTP·redirect를 거부한다. Basic Auth와 `x-langfuse-ingestion-version: 4`, `application/json`으로 보낸다. 기본 HTTP timeout은2초(0.05~10초), 제한 큐가 찼으면 drop을 기록한다. 전송은 별도 daemon thread이며 실패/timeout/부분 수락을 카운터로 기록한다. observer 오류는 업무 stdin/stdout·프롬프트·Tool 결과에 되돌리지 않는다.

완료 사건만 완성된 span으로 구성하고 **동일 span의 전송 시도는1회**다. 시작/중간 사건과 사용량은 로컬에서만 갱신한다. 실패·drop·프로세스 종료 시 불확실하게 전송된 span을 재시도하지 않아 서버 중복을 피한다. durable 전송 시도 기록과 같은 output 폴더를 재사용하면 재접속에서 동일 span을 다시 보내지 않는다. 네트워크 ACK의 불확실성과 수집 중 crash에서 서버의 exactly-once 저장까지 보장하지 않는다. HTTP2xx도 부분 수락이 없음을 확인한 경우에만 `exported`로 기록하며 실제 UI 조회를 증명하지 않는다.

native 집계는 `langfuse.observation.metadata.native_usage_snapshot` 등 metadata에 둔다. `generation`, 모델별 usage/cost 속성은 보내지 않아 세션 집계를 한 모델 호출처럼 과금 계산하지 않는다. 관측된 원문 parent가 없으면 각 완료 사건은 같은 trace의 독립 span이다. 원문 전체 input/output은 의도적으로 제외하며 Langfuse의 업무 평가용 완전 canary/Agent Graph 인수를 주장하지 않는다.

2026-10-10 공식 문서를 확인했다. [OTLP endpoint·HTTP JSON](https://langfuse.com/integrations/native/opentelemetry), [v4 완료 span과1회 export](https://langfuse.com/integrations/native/opentelemetry/migration-to-v4) 계약을 구현했다. 공식 문서는 Python에 SDK를 권장하지만 이 어댑터는 승인된 모델 SDK/설치0 조건에서 직접 OTLP JSON만 사용한다. OSS 소스를 vendor하지 않았으며 설치 SDK 버전·서버 버전·유료 플랜·클라우드 화면 연결은 검증하지 않았다. [Codex --json](https://learn.chatgpt.com/docs/non-interactive-mode)의 사건 형식과 로컬 rollout 형식은 구분하며 rollout의 버전별 호환은 실제 기록 인수가 추가로 필요하다.

## 검사

```powershell
python -m unittest discover -s tests/observer -v
python -m observer --help
```

미관측 값, ID 불일치, 중복/역행 sequence, 누적 usage 역행, 캐시/reasoning 중복합산 방지, 부분량, 원문/개인 경로/키 제거, 미완성 JSON, tail 중단, 로컬 크기 상한, 전송 실패 격리, v4 payload/header/전송1회/큐 포화와 실제 loopback HTTP socket timeout을 검사한다. HTTP timeout 시험은 test-only opener로 loopback HTTP transport를 주입한다. 운영 endpoint의 HTTPS 검증과 redirect 차단은 유지한다. 이 검사는 실제 Codex 새 입력이나 실제 Langfuse 계정의 연결을 대신하지 않는다.
