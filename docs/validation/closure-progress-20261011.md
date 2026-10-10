# 수정 마감과 다음 단계

2026-10-11 KST. 사용자의 반복 작업 지적에 따라 [정한 범위](../evaluation/closure-protocol-20261011.md)를 한 차례 실행하고 조사 종료/완료/외부 의존을 분리한다. 기존 [9입력 결과](focused-progress-20261011.md)와 원래 실패·timeout을 덮어쓰지 않는다.

## 닫은 수정

- HTML 설명서는 절별 실제 URL·page_id·본문 snapshot을 사용한다. capture/import에서 명시 topic과 URL/location 충돌·복수/누락을 거부하며 과거 혼합 snapshot도 우회하지 못한다. HTTP는 hash 절을 선택하지 못하므로 native 본문 capture를 요구한다. 표식 검사 자체는 실제 관측/원문 의미의 증명이 아니다.
- 메인 Agent와 needs-structuring Skill은 같은 후기의 실사용 관측·일반 선호·미래 기대를 문장별로 나눈다. 특정 모델 속성의 만족/불편/효과로 확대하지 않는다. 의미 분류를 일반 코드나 알려진 답안 문자열로 하드코딩하지 않았다.
- 웹 평가의 실제 prompt는 case 제약 전체 JSON과 qualification을 보존한다. 과거 WEB-02의 max_concepts 누락 실패는 그대로 남기고 새 prompt 회귀검사로 누락을 막는다. 이번에 native 웹을 다시 조사하지 않는다.

## 실제 AI 평가

제품 v5.5·실제 v3 자료·runner12파일·source41파일을 동결했다. prepared SHA `1fb1fb39c1176e5e132a93ab5ec0cc18ddfb28c9698f0f93d9ff8a67055a2393`, 최대4입력/동시2/각420초/자동 재실행0이다. 신규 작성·알려진 원문과 오류 계열의 비맹검 진단이며 독립 held-out/미래 심사 성공률이 아니다.

| 입력 | 실행·계약 | 의미 검토 |
|---|---|---|
| F01 B502 경험/선호 | exit0·196.70초·저장/최종 전달 일치 | 14/14. 일반 사용 긍정·넉넉한 제품 선호·좁음/2인 수용 구분 |
| F02 S836 청소 기대/치수/효과 | exit0·239.70초·held·제안0 저장/최종 일치 | 14/14. 홈바 편의 경험과 청소 기대 분리, 360mm/20% 보류 |
| F03 T876 장보기 확인/출처 | exit0·315.36초·기획 초안2개 전달 | 14/14. 선반 p17/p17–18와 청소 p19·공용 부품 조건 구분 |
| F04 같은 대화의 조건 변경 | exit0·217.92초·같은 native/session·새 turn·prior·이력 보존 | 14/14. 위치 고정·선반 조작 금지 반영, 확인/미확인 기록의 제한된 초안 |

F03의 최초 저장은 usage_summary 계약 밖 필드로 거절됐다. 같은 turn에서 수정1회 후 승인되었고 이전 후보/거절 이력을 유지한다. 코드/도구 계약 통과, 기획 초안 completed, 실물/시장/효과 검증을 구분한다. 의미 점수는 승인·supported 자기보고가 아니라 frozen 원문과 답변/export를 독립 대조한 진단이다.

4입력/3실제 native 세션을 종료했다. 후속 이후 부모 turn은 현재 valid=false·latest_result=null이지만 과거 후보2개/result/assessment/출처·부모 export SHA를 보존한다. 이전 제안의 현재 유효성과 역사적 보존을 구분한다. 전체 관측 input1,037,455(그중 cache927,360), noncache110,095, output38,188(그중 reasoning10,910)이다. 같은 세션의 최신 누적을 한 번만 집계했고 후속 delta는 input236,911/cache215,680/output9,077/reasoning2,221로 이미 합계에 포함된다. model은 관측 gpt-6.1-sol/ultra이며 제공사 metadata·backend 전체 호출·청구·사람 시간은 미측정이다. 새 baseline을 실행하지 않았으므로 이 수치를 절감률·우위로 사용하지 않는다.

독립 리뷰가 발견한 runner 경계2개는 동결 실행 종료 뒤 수정했다. 부모 usage/ID가 미관측 또는 불일치면 후속 delta를 unknown으로 남기고 followup 단독 선택을 강제한다. 이번 실제 부모 usage는 관측됐고 followup는 단독 실행했으므로 원래4개 결과의 경계 우회는 없었다. 원래 runner12개/질문·실패 기록을 보존하고 이 수정은 코드 회귀로 검증했다. 종료 후 URL 비문자 입력을 파서보다 먼저 검증하는1줄도 추가했다. native4개는 수정 전 동결 v5.5로 실행했고 최종 ZIP의 이 입력 경계는 추가 코드 검사로 확인한 범위다. AI를 다시 실행하지 않았다.

감사는 원본 prompt/trace/error SHA·동결 source/runner·최종/export/제약/후속을 대조했다. 최초 감사의 raw CRLF 파일과 준비 LF 문자열 SHA 비교 실패(exit1)는 보존했다. 수정 감사는 원래 실행 raw SHA와 정규화된 정확 prompt를 각각 검사했고 native 재실행/원래 결과 덮어쓰기는0이다.

## 관찰 준비 착수

별도 수집기를 F03 CLI 로그에 local-only로 연결했으나 summary 파일 교체에서 WinError5·exit1을 관측했다. 첫 연결 실패와 원래 partial32건/기록을 보존한다. 원인 프로세스/백신/잠금의 상세는 미확인이다. 업무 AI는 영향 없이 계속돼 정상 종료했다.

저장 교체만 최초1+재시도2회·대기50/100ms로 제한하고 지속/다른 오류는 전파한다. 저장 오류 뒤 cleanup의 재저장을 생략해 상한을 유지한다. 이전 target·완성 tmp·journal을 보존하며 업무/모델 재실행은 없다. 관련 observer38검사와 실제 동일 F03 CLI의 **저장 기록 replay** exit0을 확인했다. 새 output에서45사건·CLI Tool 반환18/실패1·완료 usage를 읽었고 HTTP 전송/모델 요청/추가 문맥0이다. Cloud 재연결/live 화면/전체 Agent 메시지 graph/30초 녹화 인수를 뜻하지 않는다. CLI 단독 범위여서 native_usage/noncache 등 미관측 항목은 null이다.

## 검사와 제한

최종 관련 검사는 제품125/evaluation90/observer38=253개이며 자산/새 ZIP70파일·manifest69 SHA·새 추출·잠금 설치·공통 Skill doctor·Claude adapter 소스 재설치 exit0을 확인한다. 실행기/URL 경계 수정 전 제품124/evaluation89와 이전 package는 과거 기록으로 유지한다. 새 product receipt `31a86425aeb74702abaff17c544501fd`, evaluation `daf7d48f3d0f4df8b4ff8fc20e9b53e2`, assets `ca3b5a0c1a4c444f975f1949140f81a3`, package `a9d224a92c454cd2ad8f196030424279`, observer `37040e9159e34ebdbf35fd9d4ab5ff8a`, replay `515cf61334524ee295bf5677b52b8fd0`를 보존한다. 설치 검사는 Claude/Gemini native 업무 인수가 아니다.

## 종료와 다음 작업

이번 3모델 자료 조사 단계는 종료했다. 신규 청소 불편·내부 유효 치수·선반 간격은 확보하지 못한 상태를 보존하며 관련 요청을 보류한다. 새 실제 자료가 확보될 때 새 버전으로 보강한다. 원하는 효과가 나올 때까지 검색·AI 실행을 반복하지 않는다. 총 토큰/비용 절감, 품질 우위, 실제 사람 공수 효과는 미입증이다.

다음 내부 작업은 별도 관찰 화면의 가독성·장애/누락 표시와30초 실제 녹화 → 발표/영상 제작 → 최종 제출 재현이다. 팀 회신/실제 사람 시간/전체 청구·Claude/Gemini 인증·최종 제출 규격은 외부 의존으로 분리한다. 팀원 로컬 웹 분석은 제외한다. 이 마감을 전체 대회 요구·제출 완료라고 설명하지 않는다.
