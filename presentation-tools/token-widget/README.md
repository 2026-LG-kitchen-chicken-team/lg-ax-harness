# Token Lens — 발표·시연영상 전용 토큰 위젯

선택한 **실제 Codex·Claude JSONL 기록**의 입력·출력·캐시·경과 시간을 별도 로컬 창으로 보여준다. 제품 Agent의 기능이나 실행 조건이 아니며 **심사위원 ZIP·제품 설치·배포에는 포함하지 않는다.** 촬영하거나 모델을 호출하지 않는다. Python 표준 라이브러리와 저장소의 `observer.storage.JsonlReader`만 사용한다.

## 화면을 띄우기

이 저장소 루트에서 Python 3.11 이상을 사용한다. Windows에서는 `python`, macOS/Linux에서는 환경에 따라 `python3`를 사용한다. 로그 경로·native UUID는 촬영할 **특정 실행 기록**을 직접 선택한다. 가장 최근 대화를 자동 검색하지 않는다.

```sh
python presentation-tools/token-widget/widget.py --engine codex --session-id NATIVE_UUID --log /private/rollout.jsonl --mode live
```

터미널에 출력되는 `http://127.0.0.1:포트/`를 브라우저에서 연다. **별도 발표·촬영 창**으로 배치하거나 녹화 프로그램의 창 소스로 선택한다. 창 오른쪽 ‘작게 보기’로 네 카드만 강조할 수 있다. 모델/업무 프로세스와 별개이며 `Ctrl+C`는 위젯 서버만 종료한다. 외부 폰트·분석기·CDN·키·로그인은 사용하지 않는다.

기존 실행 기록을 보여줄 때는 `--mode replay`를 사용한다. 한 세션에 여러 업무가 있으면 해당 입력과 완료의 실제 UTC 시각을 지정한다. `REPLAY · 저장 기록` 표시를 유지한다.

```sh
python presentation-tools/token-widget/widget.py --engine claude --session-id NATIVE_UUID --log /private/session.jsonl --mode replay --since 2026-10-16T09:25:22.471Z --until 2026-10-16T09:35:22.880Z
```

명시적으로 확보한 하위 로그는 `--child LOG_SESSION_UUID /private/child.jsonl`로 최대 8개 연결한다. UUID는 그 로그에 실제 기록된 session ID다. Claude 하위 로그는 부모와 같은 session ID를 사용할 수 있으므로 파일명의 `agent-...`를 UUID로 바꾸지 않는다. 메인과 하위는 각각 표시하며 합계로 섞지 않는다. 이 도구가 Agent를 생성하거나 위임 관계를 추측하지 않는다. 하위 로그가 없으면 메인 수치를 전체 호출량이라고 설명하지 않는다.

## 숫자 읽기

| 카드/상태 | 의미 |
|---|---|
| Codex 입력 | 캐시 읽기가 포함된 native 입력. 캐시를 다시 더하지 않는다. |
| Claude 일반 입력 | 캐시 제외 입력. 캐시 읽기·생성은 별도 항목이다. 두 제공사의 입력 카드 숫자만으로 비용을 비교하지 않는다. |
| 출력 | 관측된 출력. 추론/생각 토큰이 포함돼 있으면 다시 더하지 않는다. |
| 캐시 읽기 | 로그에 보고된 캐시 토큰. 캐시 비율은 절감률·실제 청구액과 다르다. |
| 관측 경과 | 선택 로그에서 **마지막으로 시작한 task/실제 사용자 입력**부터 완료까지. 후속 업무는 시계를 새로 시작하며 Tool 반환은 새 업무가 아니다. 사용량의 세션/지정 구간 범위와 시간의 최신 업무 범위는 구분한다. native 시각이 없는 CLI JSON은 `—`다. |
| `—` | 미관측 값. 0으로 대체하거나 추정하지 않는다. |
| LIVE / REPLAY | 진행 중 로그 관측 / 저장 기록. 재생을 실시간 실행으로 설명하지 않는다. |

Codex의 고유 response ID 또는 누적 snapshot을 사용하며 둘을 합산하지 않는다. Claude는 같은 `message.id`의 마지막 usage를 한 번만 집계하며 내부 iteration·cache 세부·thinking을 중복 합산하지 않는다. CLI 종료 집계와 메시지 합계도 더하지 않는다. `--since` 사용 시 Codex 구형 누적 로그는 직전 snapshot과의 차이를 사용하며 직전 값이 없으면 ‘선택 세션 누적’으로 명시한다. 시각 필터에는 시각이 기록된 native rollout/프로젝트 로그를 선택한다.

## 관찰 범위와 검사

브라우저에는 허용된 숫자·고정 상태·검증한 UUID·모델 ID·시간만 전달한다. 원문 질문·답변·생각·명령·로컬 경로·API key는 전달하지 않는다. 서버는 `127.0.0.1`에만 열고 정확한 Host/Origin·경로만 받는다. 로그를 읽지 못하면 마지막 관측값과 관측 오류를 구분한다. 원본 로그를 수정하지 않으며 64MiB/한 줄4MiB 상한이 있다.

```sh
python -B -m unittest discover -s tests/presentation-tools -v
```

위 검사는 중복/누락/다른 세션/이전 업무/부분 줄/HTTP 경계와 제품 패키지 제외를 다룬다. 실제 화면 렌더링·촬영·모든 버전의 native 로그·최종 backend 청구 검증을 대신하지 않는다. 전체 청구 금액이나 절감률은 산출하지 않는다. Langfuse 상세 trace 전송과도 연결하지 않는다.
