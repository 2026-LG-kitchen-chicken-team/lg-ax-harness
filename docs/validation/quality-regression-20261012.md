# 상품기획 품질 보완·동일 원본 제한 회귀

2026-10-12. [사전 계약](../evaluation/quality-regression-20261012.md)의 구현·실제 실행·독립 의미 검토를 종료했다. **Codex 실제10건 중8통과·2실패, Claude3건 중2통과·1실패, 기본 취소 R06 미실행1건**이다. 이번 단계의 작업 종료이며 모든 답변 결함 해결·기획 업무 완료·최종 제출 완료를 뜻하지 않는다. [비식별 원본 대조·수치 JSON](quality-regression-20261012.json)을 함께 읽는다.

## 구현과 검사

- 공식 support_quote의 연속 직접 인용, 저장 factual_summary, AI 판단을 구분한다. 선택 필드 `decision_notes`에 보류의 근거/미확인을 저장·검사·export하며 구버전 생략 입력과 호환한다. basis는 AI 신고이며 원문 의미 인증이 아니다.
- 후기의 사용 조건·기능 영향·긍정/회피·시점/귀속을 새 turn 전에 점검한다. 필요하면 같은 원URL의 주변 문단만 관측해 새 버전으로 등록하고 같은 요청에 연결한다. 시작된 turn의 자료 고정과 수정 상한을 유지한다.
- 취소는 실제 대상 상태를 바꾸고 원문을 reason에 보존한다. 기록용 새 업무 turn을 만들지 않고 실제 대상 `{cancellation,export}`를 전달한다. backend 중단은 별도 미확인이다.
- AI 자체 추정 시간을 쓰지 않는다. 아래 실제 관측 시간은 계획 일정·저장 시점과 구분한다.

제품189·평가128·eval28개 일반 코드 검사 exit0. 제품 검사에는 새 decision_notes 경계9개가 포함된다. 지침/manifest·Claude 사본 정합과 독립 일반 계약 검토를 완료했다. 코드 검사는 실제 AI 의미 품질 인증이 아니다. ZIP69파일/manifest68개, 새 폴더 locked 설치·doctor·Claude 사본 재설치 exit0는 패키징 검사 범위다.

최종 Agent `product-planning-v7.4`, 동결45파일 지문 `73ec3fc2ac5931ed70bba7785dc31ef52c24493c32b8128b16060326793697e9`. 실제 실행의 설치 보호파일과 runtime snapshot 지문을 대조했다. 제품 기본 catalog는 empty이며 알려진 근거 재사용 입력만 lg-kitchen-v4를 명시적으로 설치했다. 제품에 질문별 답안 분기·평가 기대값·등록5모델 기본 선택을 넣지 않았다.

## 동일 원본의 최종 실제 결과

기본13건과 실행 전에 선언한 C01 보충1건, 계획14건 중13건을 실행했다. Codex8개 native 대화·Claude2개 native 대화다. R05에 실제 turn이 없어 R06을 새 대화로 대신하지 않았으며, C01은 실제 R03 후속 취소로 별도 집계한다. 적용7축을 각0–2/사유 있는 null로 평가하고 환산12/14 이상·0점 없음·중대 오류 없음·엄격 JSON/전달 정합을 요구했다. timeout은 최종 답변이 없어 의미 판정 미실시다.

| 환경/입력 | 최종 상태·판정 | 의미 점수 /14 | 실제 시간(초) | 핵심 근거·제한 |
|---|---|---:|---:|---|
| Codex R01 | completed / 통과 | 14.0 | 293.74 | DUBJ2EA 실제 후기 문맥·공식 기능·AI 가설 분리; 효과는 계획 |
| Codex R02 | completed / 통과 | 14.0 | 289.67 | 일반 전자레인지 입력·MWJ25E 조건/긍정/회피 문맥 보존 |
| Codex R03 | needs_input / 통과 | 14.0 | 113.45 | 실제 후속·접시 형상/안전 미확인; 조건부 치수 계산과 적합 승인 구분 |
| Codex R04 | completed / 통과 | 14.0 | 346.64 | empty→정확 MW23GD 조사·등록→같은 요청 기획; 실패 import 수정 포함 |
| Codex R05 | succeeded / 실패 | 11.667 | 203.55 | 조사 보류 기록은 유효하지만 최종은 파일 링크뿐; 필수 inline JSON pointer 없음 |
| Codex R06 | not_run / 미실행 | 미실시 | — | R05 turn 없음·사전 조건 불충족; 실제 취소 성공으로 바꾸지 않음 |
| Codex U01 | completed / 통과 | 13.0 | 283.28 | 냉장고 기획의 반복 과업/수동 부담은 조건부 가설; 실제 효과 미측정 |
| Codex U02 | timeout / 실패 | 미실시 | 420.52 | 420초 timeout·최종 없음; 조사 held 저장은 답변 전달/기획 완료가 아님 |
| Claude R02 | completed / 실패 | 11.0 | 112.534 | 전달은 일치하나 후기 주변 문맥·결함 검출/오판정/조치 지표 부족 |
| Claude R03 | held / 통과 | 12.6 | 61.439 | 접시 적합성 보류 타당; 공식 저장 요약의 귀속 표현 일부 모호 |
| Claude U02 | held / 통과 | 13.0 | 127.578 | 정확 모델/긍정 후기 관측·불편 근거 부족으로 조사 held; 기획 미완료 |
| Codex V01 | completed / 통과 | 14.0 | 269.53 | 처음 실행한 식기세척기 표현·실제 경험과 과업 가설 구분 |
| Codex V02 | held / 통과 | 14.0 | 243.29 | 처음 실행한 상충 의견 표현·후기 레코드5/고유 URL2; 개선안 held |
| Codex C01 | cancelled / 통과 | 14.0 | 75.06 | 실제 R03 대상 취소·원래 이력 보존; backend 중단 미확인 |

보류의 근거·출처·후속 절차가 타당하면 해당 응답 진단은 통과할 수 있다. Claude U02의13/14와 Codex V02의14/14는 실제 개선안 완성 수치가 아니다. 모든 저장의 semantic_status=unverified·acceptance_ready=false를 유지한다. U01/U02는 v7.3에서 기실행한 재시험이고, V01/V02는 최종 원본에서 처음 실행한 공개 표현이다. 개발자에게 공개된 기존 자료 평가이며 blind holdout·미지의 고객 표본·공식 심사 문제로 확대하지 않는다.

## 확인된 미해결 결함

1. **Codex R05 최종 전달:** local JSON·request/export/DB는 일치하지만 마지막 답변이 파일 링크만 제공했다. inline pointer 요구를 충족하지 못해 실패다.
2. **Codex U02 조사 지연:** import scope_mismatch·브라우저 오류·보류 reason 길이 오류를 포함하고420.52초에 로컬 PID 트리를 종료했다. native turn.completed/최종 답변이 없다. 추가 모델 재실행0, backend 종료·후속 소비는 unknown이다.
3. **Claude R02 의미 품질:** 지침이 있어도 원URL 주변 문맥을 실제 관측하지 않아 기능 영향 없음·회피·가격/마감 유보를 충분히 반영하지 못했다. 결함 검출/누락·정상품 오판정·발견 후 적절 조치 지표도 부족했다.
4. **Claude R03 표현:** 저장된 공식 사양 요약과 AI 한계 문장을 귀속하는 방식이 일부 모호하다. 중대 공식 직접 인용 오류로 단정되지는 않았지만 완전 해결로 보고하지 않는다.

최종 원본을 다시 바꾸거나 성공할 때까지 반복해 이번 결과를 덮지 않았다. Codex를 제출 기준으로 유지하고 Claude는 제한 검증/후순위로 공개한다. 현 상태를 모든 질문/환경 품질 통과 또는 제출 평가 전 항목 충족으로 발표하지 않는다.

## 예외·이력의 일반 코드 확인

실제 C01 취소 저장본의 독립 복사본에서 기존 후보 재저장·새 후보 저장·새 Tool invocation3종을 시도했다. 모두 terminal_turn으로 거절됐고 후보/상태/행 수·원본 SHA는 보존됐다. [취소 후 쓰기 차단 기록](cancelled-write-probe-20261012.json).

실제 U02 timeout 저장본의 독립 복사본에서 current_request·export_session을 실행했다. 원질문·held/request_version2·request1/turn0·관측 web_pages4와 export SHA를 복구했고 기존 행 수·원본 SHA가 보존됐다. [시간초과 후 기록 조회](timeout-recovery-probe-20261012.json). 이는 일반 코드 기록 복구이며 native 최종 답변/기획 복구·backend 중단·U02 품질 통과가 아니다. 두 프로브의 추가 제품 모델 호출은0이다.

PDP InternalError·HTTP301·PDF screenshot 오류·초기 경로 누락·UnicodeDecodeError·scope_mismatch 등 실제 실패를 보존했다. 최종 답변 성공을 모든 Tool/명령 무오류로 바꾸지 않는다. export.requests.response는 마지막 요청 캐시일 수 있어 연결된 turn·resolve 사건·current_request를 함께 대조했다.

## 실제 시간·전체 관측 사용량

Codex 시간은 실행기 monotonic 시작→native 최종 종료로 프로세스 시작을 포함한다. Claude는 실제 user timestamp→main assistant end_turn이며 UI 시작 시간을 제외한다. 시간 경계가 달라 환경 속도 우열이나 사람 공수 절감으로 환산하지 않는다.

| 환경 | 관측 입력 | 그중 제공자 캐시 | 관측 출력 | 그중 reasoning | 범위 |
|---|---:|---:|---:|---:|---|
| Codex | 10,823,246 | 10,037,760 | 107,164 | 34,121 | 실패 포함·U02는 마지막 부분 관측 |
| Claude | 2,800,935 | 2,684,058 | 28,004 | 미제공 | 비캐시60+cache creation116,817+cache read2,684,058 |

Codex cache는 input의 부분이고 reasoning은 output의 부분이다. R02→R03→C01 같은 native 누적값은 차분해 중복 합산하지 않았다. Claude는 main assistant 고유 ID별 집계다. 전체 backend/sidechain·청구·단가·비용·개발 사용량은 unknown이다. Codex U02 input4,010,043/output15,257은 완료 turn 총량이 아닌 timeout 직전 마지막 관측이며 총 청구라고 쓰지 않는다. 조사에서 문맥이 누적돼 입력이 크게 증가한 한계도 남는다.

[토큰 가산점 구현·실제 사건·품질 제한](token-bonus-20261012.md)과 [수치/지문 JSON](token-bonus-20261012.json)에 연결했다. baseline의 동일 자료/모델/설정/완료 기준/캐시·순서 통제가 없어 일반 절감률·사람 절감률·가산점 획득을 주장하지 않는다.

## 선행 결과와 남은 제출 작업

v7.3 Codex8/Claude3은 별도 수치로 보존한다. 잘못된 취소 대상 pointer, Claude 최종 JSON 여분 괄호/접근 원인 과장/복구 안내 부족 등 선행 실패를 최종 성공률과 합산하지 않았다. 최초 수집기 디렉터리 충돌6건은 모델 시작 전 실패 원본으로 남겼다. native ID 없는 기록을 모델 호출0의 일반 근거로 쓰지 않는다. v7.2·과거50/10 입력도 이번 성공률에 합산하지 않는다.

현재 요청3항목의 구현·제한 회귀·토큰 근거 정리는 마감했다. 제품 시험판은 검증 범위와 실패를 공개해 배포한다. 남은 제출 작업은 최신 수치/제한을 발표자료에 반영, 별도 관찰 화면·실제 촬영/영상·10분 리허설, 웹팀 원본 접수 시 연결 검토, 운영진 최종 규격/접수와 새 실행자 재현이다. 사람 비교·Gemini는 제외한다. 최종 제출 전에 위 알려진 실패를 허용 지원 범위·시연 입력과 함께 결정해야 한다. 개발용 Claude 위임 인수는 출품 Desktop 업무 실행과 별개의 후순위다.
