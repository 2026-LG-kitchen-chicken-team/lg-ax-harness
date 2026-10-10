# observer 0.1.0 검사 기록

2026-10-10, Windows 독립 worktree `separate-observer`에서 실행했다. 부모 checkout·제품 코드·공통 설정·장부는 수정하지 않았다. 부모가 통합 후 해당 run의 실제 check receipt를 생성한다.

| 실제 명령 | 결과 |
|---|---|
| `python -m unittest discover -s tests/observer -v` | exit0, 25개, 0.482초, OK |
| `python -m observer --help` | exit0, 수집 전용 인수 표시 |
| `git diff --check` | exit0, 출력 없음 |

신규 출품 모델 입력0회, 모델 API 호출0회, 모델 SDK 의존0개, 구독/패키지 설치0회다. 개발 Agent의 사용량과 전체 backend 청구는 미측정이다. 실제 코드에는 native/model subprocess·업무 PID 제어·모델 문맥 쓰기 경로가 없다.

25개 검사는 선택 ID/중복/sequence/사용량 역행, cache/reasoning 부분량, 미관측 null, 원문·path·key 제외, 지침 로딩과 명령 mapping의 구분, 미완성 JSON, tail stop/time limit, source/output 충돌 방지, 로컬 상한/checkpoint, OTLP JSON/header/완료 span/1회 전송/큐 포화/실패 격리/최종 native metadata와 실제 loopback socket timeout을 포함한다. loopback timeout은 운영 HTTPS endpoint 검증을 통과한 어댑터에 test-only opener로 HTTP transport를 주입하며 실제 Langfuse 요청이 아니다.

Langfuse 공식 OTLP/v4 문서 검토는 완료했다. 실제 native 기록 재생·이미 열린 데스크톱 구독·클라우드 계정/서버 버전/수락·UI 조회·Agent Graph·on/off 전체 입력 지문 비교·녹화는 이 작업에서 실행하지 않았다. 부모가 따로 인수한다. credential 설정이 없으면 `configured=false`를 반환한다. 로컬 동시 작성, 로그 in-place 교체, turn별 usage 차이와 전체 비용 계산은 지원하지 않는다.
