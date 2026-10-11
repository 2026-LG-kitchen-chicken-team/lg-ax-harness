# 팀 웹 연결 인수 기준 — 요청 기반 조사 경로

2026-10-11. 팀 웹 구현 원본은 미수신이며 아래는 연결 계약이다. 구현·브라우저 시험을 통과했다는 기록이 아니다. 출품의 모델 실행은 사용자가 선택한 native Codex/Claude 경로를 유지한다. 웹에 자체 LLM API 실행기를 새로 채택하지 않는다.

| 실제 사건 | 웹에 전달할 값 | 표시 의미 |
|---|---|---|
| 자연어 요청 접수 | 원문 question, 실제 요청의 session/request handle | 제품군·모델·불편을 고정 버튼의 답안으로 치환하지 않음 |
| 조사 전 요청 저장 | open_request/current_request의 status, request_version, research_id | needs_input과 research_required를 구분. AI가 범위를 해석할 수 있으면 조사 진행 |
| 실제 조사 | native Tool/수집의 관측 사건, record_request_research | 관측 성공·실패·보류와 snapshot ID. 진행 애니메이션으로 가상 Agent/실행을 만들지 않음 |
| 근거 등록·요청 연결 | import 응답 data_path/data_version, resolve_request_bundle | 원문 질문은 그대로, 같은 요청에 한 번만 turn 연결. 원래 조건·수정 제한 유지 |
| 기획 검토·저장 | save_and_export.receipt, delivery_ready, export | accepted/valid/최신 버전이 맞을 때만 현재 답변으로 표시 |
| turn 이전 종료 | current_request와 export_session | 조사 보류·확인 요청. 기획 completed 또는 가짜 receipt로 표시하지 않음 |

모델/제품군 선택은 실제 요청의 해석이며 임의의 첫 등록 모델로 대체하지 않는다. 자료가 없는 첫 설치와 신규 모델에서도 동일 흐름을 따른다. 공식 원문·관측일·정확 모델/문서 버전·AI의 해석·가설을 구분해 보여 준다. 중복 여부가 null이면 미확인으로 표시하고 false로 변환하지 않는다.

연결 인수에는 원문 질문 → 실제 실행기의 native ID → 업무 session/request/turn → 원문 출처 → 저장 export와 SHA → 최종 화면을 한 사례 안에서 대조해야 한다. 같은 대화 후속, 조사 실패, 자료 부족, 재전송, 오래된 답변 재생도 확인한다. 업무 turn의 자료나 수정 상한을 브라우저 새로고침으로 초기화하지 않는다.

토큰은 실제 관측값과 coverage만 표시한다. 미측정은 0이 아니다. 실패/후속 호출을 포함한 native session 관측과 DB 일부 record_usage를 합산해 중복 계산하지 않는다. 원문 실행 로그·개인 경로·인증은 웹 응답이나 원격 저장소에 그대로 노출하지 않는다.

현재 확보한 근거는 공통 Tool의 코드 검사·독립 리뷰·제품 설치 검사다. 팀 웹의 저장소/브랜치 또는 소스가 들어온 뒤 실제 코드와 브라우저에서 이 경로를 확인해야 연결 완료로 바꿀 수 있다.
