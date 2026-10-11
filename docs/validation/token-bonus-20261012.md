# 토큰 가산점 구현·관측·품질 근거

2026-10-12. 공식 제출 안내 C06에 대응하는 구현과 실제 실행 사건을 연결한다. 정확한 가산점·전체 청구·비용·일반 절감률은 미확인이다. 사람 대비 절감효과는 측정/주장하지 않는다. 최종 관측 수치는 동일 원본의 [제한 회귀 기록](quality-regression-20261012.md)에 남긴다.

| 방법 | 구현 | 입증 범위와 제한 |
|---|---|---|
| 필요한 Skill·계약·문단만 읽기 | `agents/product-planning.md`, `skills/evidence-retrieval/SKILL.md`, `product-tools/product_tools/web_evidence.py` | 웹 원문 snapshot과 짧은 미리보기를 분리한다. 중요한 사용 조건·긍정·유보는 절감 목적으로 생략하지 않는다. 실행기의 모든 읽기를 강제로 차단하지 않는다. |
| 입력·자료 조회 통합 | `product-tools/product_tools/conversation.py`의 `open_request_bundle`/`resolve_request_bundle` | bundle의 원문은 refs에 한 번, records는 metadata다. 사전 부분 조회→최종 bundle에는 일부 중복 가능성이 있다. 필요한 주변 문맥의 추가 관측을 금지하지 않는다. |
| 일반 코드로 조회·검사·저장 | `product-tools/product_tools/state.py`, `conversation.py` | SQLite·지문·크기/형식 검사·멱등 저장·export에 별도 모델을 호출하지 않는다. 원문 의미 판단은 native AI와 독립 평가가 담당한다. |
| 큰 결과 반복 출력 억제 | `state.py`의 compact receipt, `save_and_export` | 전체 result/assessment는 export에 보존하고 현재 receipt·경로·SHA를 전달한다. 출력 바이트와 토큰 수는 다르다. |
| 정확 자료/지문에 따른 재사용 | `state.py` 조회 캐시, `web_evidence.py` snapshot 재사용 | 최종 Codex·Claude R03의 후기/사실 조회 `cache_hit=true`를 실제 확인했다. 웹 snapshot의 cached=true와 기획 결과 자동 재사용은 이번 지정 사례에서 미입증이다. 로컬 캐시 적중을 제공자 prompt cache나 비용 절감으로 귀속하지 않는다. |
| 수정·재시도 한정 | 공통 상태 계약·업무 수정 최대2회·웹 기술 재시도 계약 | 실패/거절도 이력과 사용량에 포함한다. native/backend 전체 호출·토큰 상한을 보장하는 기능은 아니다. |
| 별도 관측 | 평가 수집기와 기존 observer | 일반 코드가 실제 native 기록을 읽는다. 제품에 토큰 감사용 Agent·Skill·모델 요청을 추가하지 않는다. 전체 backend/청구 수집은 별도 미확인이다. |

## 실제 표시 방법

별도 시연 화면에는 버전/질문 구분, 입력 전체·그중 캐시·비캐시·출력·그중 reasoning·관측 시간·상태·관측 범위를 함께 표시한다. Codex 캐시는 input의 부분이며 reasoning은 output의 부분이다. Claude는 비캐시+cache creation+cache read가 관측 입력 전체다. 서로 다른 제공사의 캐시 필드를 같은 청구 단가로 환산하지 않는다.

같은 Codex native 세션은 마지막 유효 누적값을 한 번만 합산하고 후속 입력은 실제 종료값 차분으로 계산한다. Claude는 main assistant message ID 중복을 제거한다. 실패·수정·자료 보류를 제외하지 않는다. token_count snapshot 수·명령 수·Tool 수는 backend 모델 호출 수가 아니다. 업무 장부 `recorded_calls=0/unknown`은 실제 호출0을 의미하지 않는다.

baseline의 동일 자료·모델·설정·업무 완료 기준·캐시/순서 통제가 없는 이번 회귀에서 절감률은 계산하지 않는다. 기존 v4/v5 수치는 과거 별도 사례로 남기며 최신 성과로 재사용하지 않는다. 발표에서는 구현 방법, 실제 사용 사건, 관측 수치와 품질 한계를 함께 제시한다. 이 자료는 C06 근거 준비이며 운영진의 가산점 부여나 최종 접수를 보장하지 않는다.

## 실제 사건 연결

읽기 전용 평가자가 동결45파일·실제 native 사건·관측 사용량을 독립 대조했다. 아래 raw 기록은 개인 로그 보호를 위해 Git 제외하고 지문·사건 위치만 공개한다. 원문의 의미 판정은 [품질 기록](quality-regression-20261012.md)과 함께 읽는다.

| 방법 | 코드 위치 | 실제 사건과 범위 |
|---|---|---|
| 좁은 계약 조회 | `agents/product-planning.md:15` | Codex R01 `01a12ba6-f6ee-7913-a3ec-e8e85993d69f`, native.jsonl 22행/item_10, 관련 계약 `rg -n` exit0·2,308bytes. 같은 실행에서6Skill·추가 계약도 읽어 전체 문맥 최소화 완료는 미입증이다. |
| 통합 bundle | `conversation.py:25`·`:34`·`:55`·`:63` | Codex R03 `01a12ba0-ce04-7212-bef5-439769e6b49f`, native.jsonl 8행/item_3, records4개는 metadata·refs4개는 근거 원문, byte_truncated=false. 전체 원페이지 관측 인증은 아니다. |
| 저장/export·compact receipt | `state.py:218`·`:229`·`:289`, `conversation.py:292`·`:299` | Codex R01 native.jsonl 53행/item_27, save_and_export exit0·2,669bytes. latest_result 재출력 없이 현재 receipt/SHA·export를 반환했다. 바이트를 토큰 수·절감률로 환산하지 않는다. |
| 웹 preview | `web_evidence.py:173`·`:245` | Codex R01 native.jsonl 40행/item_19: preview3,200문자/start800/truncated=true/cached=false. R02 26행은2,200문자. 원본 snapshot을 보존하며 중요 조건은 추가 문맥 검토 대상이다. |
| 로컬 조회 캐시 적중 | `state.py:368` | Codex R03 8행 및 Claude R03 `f6e79532-f107-4f0f-bfcf-1898d92625fb`, claude-native.jsonl 96행의 실제 tool_result(`toolu_01NHHCfTTWhdUbW6iDQ4LY2p`) bundle 출력은 후기·사실 cache_hit=true.91행은 호출이며 결과가 아니다. business_reuse_eligible=false를 자동 기획 재사용으로 바꾸지 않는다. |
| 실패/수정 포함 | `state.py:263`, 상태·외부 조사 계약 | Codex R04 50행의 scope_mismatch import exit1→52행 수정 exit0를 보존했다. 후보 수정2회와 등록 기술 수정은 다른 한도이며, 최대 후보 소진·웹 재시도 상한 발동은 이번 로그에서 미관측이다. |
| 일반 코드 관측 | `evals/runner/native_eval.py:185`, `claude_trace.py:11`·`:93` | 실제 native 누적 usage와 Claude 고유 assistant ID를 읽어 집계했다. 별도 품질 검토 Agent는 개발 사용량이며 제품의 토큰 감사 호출로 더하지 않는다. 개발 사용량·전체 backend/청구는 unknown이다. |

## 최종 관측

동일 v7.4 Codex10건·Claude3건을 실제 실행했다. Codex8통과/2실패·Claude2통과/1실패이며 기본 R06은 미실행1건이다. 실패·보류·수정 사용량을 제외하지 않았다. [수치·실제 사건 지문 JSON](token-bonus-20261012.json)과 [품질/실제 시간](quality-regression-20261012.md)을 함께 제시한다.

| 환경 | 관측 입력 | 제공자 캐시 필드 | 관측 출력 | 제한 |
|---|---:|---|---:|---|
| Codex v7.4 | 10,823,246 | input 중 cached10,037,760 | 107,164 (그중 reasoning34,121) | U02 timeout 직전 마지막 부분 관측 포함·완료 turn 총 청구 아님 |
| Claude v7.4 | 2,800,935 | noncache60+creation116,817+read2,684,058 | 28,004 | main assistant 고유 메시지 집계·reasoning 별도 미제공 |
| Codex v7.3 별도 선행8건 | 7,789,481 | cached7,226,112 | 80,499 (reasoning26,995) | 최신 통과 수치와 합산하지 않음 |
| Claude v7.3 별도 선행3건 | 3,044,883 | noncache64+creation127,359+read2,917,460 | 32,262 | 최신 통과 수치와 합산하지 않음 |

조사/브라우저 실패와 반복 문맥 누적으로 입력이 큰 사례가 남는다. 로컬 캐시·bundle·compact receipt가 실제 작동했다는 근거는 있지만, 전체 실행의 토큰 절감·비용 최적화를 입증한 결과는 아니다. 제공사 캐시 비중을 하네스의 절감률로 사용하지 않는다. native/backend 전체 사용량·개발 비용·청구·baseline 절감률은 unknown이다.

이 기록은 C06에 제출할 구현·관측·품질 제한의 근거다. 발표 화면은 기존 별도 관찰 프로그램에서 원본 버전·관측 범위·실패/미측정 표기를 함께 표시해야 하며, 이번 작업에서 새 화면 연결/녹화를 완료했다는 뜻은 아니다.
