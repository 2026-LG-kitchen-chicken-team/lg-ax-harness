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

## 0.1.1 독립 리뷰 수정·실제 J17 재생

독립 reviewer가 Codex0.162.0의 `custom_tool_call`/`custom_tool_call_output`10쌍과 dual-source에서 생략된 마지막 verification 실패를 발견했다. 실제 원본의 field/type/ID/오류 marker만 로컬로 확인하고 수집·검사 코드를 수정했다. `function_call_output`의 nonzero exit/structured error도 code로 분류한다. CLI item과 rollout custom wrapper는 공유 call ID가 없어 임의 병합하지 않는다. 원문 args·output·개인 path·credentials는 출력이나 Git에 추가하지 않았다.

실제 native ID: `01a125d4-9a50-7232-b5ac-b28cffc32a58`. 원본 지문은 CLI `251c9a7e71305203b73c2a462df9d7c48cb529eab75e2a2b0650c746767a66df`, rollout `30e24ca39850cefaa87c2f9e5bdd259eed53f9ccdc0c851f977306dfed045dc8`다. 정확한 파일은 부모의 J17 attack `native.jsonl`과 이 ID의 기존 rollout이다. source 원문을 vendor하지 않았다.

`python -`에서 `observer.__main__.collect(..., environment={})`를 기존 두 원본에 직접 실행했다. `mode=replay`, 명시한 native ID, 새 temp output, `run_id=v011-rollout-only/v011-dual`로 처리한 실제 exit0 결과다. 로컬 output은 임시 폴더이고 cloud 환경은 빈 mapping으로 고정했다.

| 실제 재생 | 수집 사건 | source별 반환/오류 | 재접속 추가 사건 | 전송 설정 |
|---|---:|---|---:|---|
| rollout-only | 32 | custom Tool wrapper10개 반환, 오류2개 | 0 | configured=false |
| dual | 76 | CLI command item19개 반환·오류1개; rollout custom wrapper10개 반환·오류2개 | 0 | configured=false |

rollout 오류는34행 `structured_output_error`와106행 `tool_verification_failed`다. CLI17행은 `structured_exit_code`다. 이를 고유 업무 실패3회나 호출29회로 합산하지 않는다. source별 관측 결과이며 `merged_tool_execution_count=null`이다. CLI의 item ID와 rollout call ID가 일치하지 않아 wrapper와 내부 명령의 관계는 미관측이다. raw output의 오류 marker는 저장하지 않고 고정 error code/basis만 남긴다. redaction marker 검사 통과, reader 오류 없음이다.

누적 사용량의 부분 snapshot 사이에서 cache/reasoning이 null이 된 뒤 역행하는 사례를 별도 highwater로 거부한다. 최신 partial 표시는 null을 유지한다. 0.1.0 checkpoint는 예전 생략 offset을 지니므로 재사용을 거부하고 새 output에 원본을 재생한다.

최종 `python -m unittest discover -s tests/observer -v`는31개, exit0, 0.514초, OK였다. `git diff --check`도 exit0이다. 추가 native/model 입력0·cloud 요청0·설치0이며 실제 Langfuse 수락/UI 인수는 여전히 미실행이다.
