# S05 실제 심사 입력·전후 비교 방법

2026-10-10. 개발 평가 도구는 [native_eval.py](../../evals/runner/native_eval.py)다. 출품 프로그램은 이 파일을 설치하거나 import하지 않는다. 기존 로그인으로 native Codex CLI를 시험하며 독립 LLM API 앱을 도입하지 않는다. 사용자의300,000원 예산과 Codex 계정 관측 usage를 현금/API 요금으로 환산하지 않는다.

## 자료·입력·비교 경계

[6사례](../../evals/judge/s05-cases.json)는 정상 기획, 기존 기능 중복, 상충 의견, 내부 치수 부족, 다른 모델 기능 혼동, 조건 변경 다중 턴이다. 심사위원이 출품 AI에 직접 넣는 업무 입력이며 발표자 질문 목록과 다르다. 기존 실제 v3 자료를 쓰는 새 질문이다. 새 자료 일반화 검증이나 운영진의 비공개 문제를 뜻하지 않는다.

최초 pilot은 S05-R01(B502S33 정상2인 냉동 정리)·R04(T876MQQ012 구체 용기 배치 확정 요구)의 단일 턴2개만 실행한다. 개선 전/후/강한 일반 프롬프트3조건으로6 CLI 입력, 각420초·동시2개 상한이다. R02/03/05/06, 원문 지시문 공격, 실제 Tool 장애 주입, 반복 측정은 후속이다. runner는 현재 다중 턴 live 실행을 거부하며 usage 차이 계산 코드 검사만 제공한다.

개선 전·후 제품 소스와 설치 사본 지문을 고정하고 새 임시 업무 폴더/DB/native 세션에서 실행한다. 기존 설치 업무 폴더와 DB를 수정하지 않는다. seed와 실행 시작 순서를 기록한다. 모든 조건은 같은 정확 모델·문서·data_version, 원문·URL·SHA·origin, 질문·추가 하드웨어 금지·동일 ProductResult/assessment 의무를 가진다. 외부 조사를 금지해 같은 저장 자료 범위를 유지한다. 전역 설정/Skill은 상속되므로 없는 것으로 가정하지 않는다. 실제 관측 모델/추론 설정이 다르면 동등 비교로 인정하지 않는다.

baseline은 같은 모델의 전체 저장 리뷰·사실을 결정적 코드로 제공한다. 정답 출처만 골라주지 않는다. 제품/개발 Skill·Agent·기존 결과·rubric을 폴더와 프롬프트에 넣지 않고, 강한 상품기획 지침과 중립적인 출력 계약을 한 사용자 입력에 제공한다. 모델이 Tool을 쓰면 실제 CLI item/rollout을 확인해 baseline 오염을 표시한다. Tool 관측 자체가 없으면 미확인이다. 제품 조건에는 설치·저장/export 운영 부담이 있으므로 토큰/시간 차이는 추론 품질과 운영 비용을 포함한 결과이며 순수 동일 프롬프트 최적화 실험으로 설명하지 않는다.

## 측정과 의미 검토

native_id, 실제 종료 코드, 경과 시간, 중단 PID/결과, prompt·자료·source SHA, 원문 결과와 실패 후보, 저장/최종 JSON 일치, CLI/rollout metadata와 관측 usage를 보존한다. 실패·timeout도 분모와 전체 사용량에 포함한다. 관측이 없으면 null이며0으로 바꾸지 않는다. 같은 session 누적 usage는 전후 차이로만 계산한다. cache는 input의 부분, reasoning은 output의 부분이므로 다시 합산하지 않는다. 한 CLI 입력은 내부 모델 여러 호출을 포함할 수 있다. 실제 backend별 호출수·청구액·인간 공수는 현재 미측정이다.

코드 계약검사는 필드·scope·source provenance·검토 기록 연결·저장 일치를 확인한다. accepted=true, supported 자기보고, semantic_status=unverified를 원문 의미 통과로 바꾸지 않는다. 별도 독립 검토에서 원문과 사용자 답변/저장 JSON을 대조하고 목적·제약, 모델 범위, 불편→기능→제안 연결, 출처 의미, 미확인/상충/보류, 상태 일치 각각0/1/2와 구체 메모를 남긴다. 출처 창작·모델 전이·기존 기능 재포장·치수/측정 효과 창작은 중대 오류로 표시한다. 적절한 보류는 성공이다. 팔을 감춘 출력 검토와 실제 운영 검토를 구분한다.

2사례·1회 결과는 반복·캐시·품질/비용 우위 입증이 아니다. 먼저 전체 결과·중대 오류·실패·미측정 범위를 보고하고 성공 사례별 token/time 차이를 부차적으로 제시한다. 기준선보다 저렴해도 원문·상충 근거·조건을 생략한 감소는 개선으로 인정하지 않는다.

## 실행

```powershell
python evals/runner/native_eval.py prepare --before BEFORE_SOURCE_FOLDER --run NEW_REPORT_NAME --case S05-R01 --case S05-R04
python evals/runner/native_eval.py run --report .harness/NEW_REPORT_NAME --timeout 420 --workers 2
```

prepare는 새 소스 snapshot과6개의 새 Temp 실행 폴더를 만들고 baseline을 분리한다. 같은 run을 재실행하지 않는다. 실패 실행도 남긴 뒤 원인을 검토하고 별도 명시한 후속 묶음을 사용한다. Python/uv/native Codex 설치·로그인은 개발 평가 환경의 전제다. 원문 실행 로그·prompt·SQLite·실행 폴더는 Git 제외이며 공유할 검증 보고서는 [pilot 기록](../validation/s05-pilot.md)에 작성한다. 전체 backend 비용 또는 공모전 전체 품질을 통과했다고 선언하지 않는다.

첫pilot 결과는 검증 기록에 남겼다. 초기 중립 출력 양식에는 root assumptions/validation_findings 문자열배열과 비어있지 않은 source_ids 조건의 명시가 부족했다. baseline 두 출력의 구조 실패는 하네스 의미 품질 우위를 입증하지 않는다. 실제 실행 당시 runner-executed.py를 보존하고 양식을 보완한6회 재비교를 수행했다. [후속 검증](../validation/s05-followup.md)을 따른다.

`--single-agent`가 전달하는 `--disable multi_agent` 옵션만으로는 세 제품 실행에서 실제 spawn 호출을 막지 못했다. 따라서 옵션 제어 검증을 실패로 기록했다. 후속 `extended_eval.py`는 사용자의 단일 Agent 선호를 프롬프트에 명시하고 실제 Tool 호출 차이를 따로 관측한다. 명시한 선호에 따라 위임하지 않았다는 관측은 Tool 제거·권한 차단을 입증하지 않는다. 전역 설정은 변경하지 않는다.

후속 실행은 고정6사례의 나머지 R02/03/05/06, 같은 native UUID의 실제 대화 재개, 별도 test_only 지시문 파일, 첫 open_request_bundle 프로세스의 일회성 기술 오류, 소유한 CLI의5초 deadline 중단이다. 공통 업무 자료에 공격 문장을 넣거나 반환 근거에 공격을 숨긴 시험은 아니며, CLI 중단은 업무 cancelled 상태 API의 구현 증명이 아니다. 최대15개의 첫/재개 CLI 입력·동시2개·입력당420초이며 자동 재시도를 하지 않는다. 이전·보완6회와 합쳐 이번 후속 작업 상한은21개다.

재개 전 해당 UUID의 누적 usage와 호출수를 읽고 재개 후 차이를 계산한다. 이전 관측이 없거나 UUID가 다르면 null로 남긴다. 저장 후보의 고정 결과/검토/요청 키를 대조해 이전 후보 보존과 변경 조건의 새 turn을 검증한다. 구조 검사는 의미 채점과 분리하며, `followup_report.py`는 trace/source 지문·실제 호출/미실행 수·설치 파일·주입 기록을 감사한다. 보고서가 없거나 turn/source/호출수가 일치하지 않으면 성공으로 채우지 않는다. 다음 명령은 기존 보존 결과의 감사이며 모델을 새로 실행하지 않는다.

```powershell
python evals/runner/followup_report.py --repeat .harness/s05-repeat-20261010 --extended .harness/s05-extended-v3-20261010
```
