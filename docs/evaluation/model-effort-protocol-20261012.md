# 모델·추론 수준·구조 비교 — 사전 판정 기준

2026-10-12 사용자 승인. 최신 대겸 인수본 product-v0.8.1을 기준으로 원인 분리와 권장 설정을 검토한다. 이전 high 고정안은 비교 기준 중 하나이며 최종 채택이 아니다. 이 파일의 계획을 실행/품질 통과로 설명하지 않는다.

## 최신 사용자 조건 — 자료 폭 유지, 목표 5분 / 상한 10분

- 시간 단축을 위해 후기 건수나 자료조사 범위를 극소수·국소 범위로 줄이지 않는다. 긍정/부정, 사용 조건, 장기 사용, 반례, 여러 원출처와 공식 사양/설명서의 접근·누락·중복·모델 귀속을 기록한다. 단순 건수를 대표성·충분성 통과로 바꾸지 않는다.
- 대겸의 기존 20/49후기 실행 원본은 사용자 확인상 없다. 재요청하지 않는다. 해당 1800초 실행의 상세 원인은 unavailable이며 새 실제 조사로 진단한다.
- 앞선 아래 screening 중 D 입력 네 설정만 실제 실행했다. 발췌 후기1건/사양요약4건의 진단이며 최종 권장·조사 충분성 평가가 아니다. 남은 소규모 B/Claude screening은 이 조건 이후 실행하지 않았다.
- 새 온라인 `LIVE61M`: 빈 catalog, 일반 전자레인지 질문, 목표300초, **native 시작→최종 응답→process exit 전체 외부 상한600초**. 파일 생성 또는 workflow.finish만으로 성공 처리하지 않는다. 실패·시간초과와 전체 관측 사용량을 남긴다.
- 제품 Tool의 내부 budget_seconds는 현재1200~1800초다. 외부600초 제한과 별개이며 제품/원격 backend 전체에600초 통제가 구현됐다고 주장하지 않는다. 상한 내 자료 부족은 축소 수집으로 숨기지 않고 불충분·보류로 보고한다.
- 충분히 확보한 동일 자료를 고정한 모델 비교와 빈 catalog의 실제 조사 e2e를 분리한다. 웹 조사 중 얻은 자료는 비공개 원본으로 보존하고, 모델 추천에는 조사 범위 충족·반복·환경 인증 확인이 추가로 필요하다.
- 아래420초/두 입력/14설정은 최초 계획 이력이다. 신규 온라인 실행의 상한은600초이며 진단 단일표본 수치를 전체 제품군의 속도·품질 우위로 일반화하지 않는다.

## 동결 입력과 비교 범위

- main `e6f4653dabae80412337131445c164b41bcaaf0c`, 제품 source `aef85804cdf61295c6253bd4c6479e43bb18d929`, ZIP SHA `cd5eefabeb46e7585891d44da00c7387e00ec3c9b0085bead52f474197b9eae2`.
- 각 실행은 새 독립 설치·새 DB, 동일 실제 보존 자료 `data/business/lg-kitchen-v4`. 이 자료는 신규 프로젝트에서 수집한 원문 발췌이며 현재 웹 전체나 새로운 조사의 대용이 아니다.
- Screening D: “DUBJ2EA의 실제 사용 후기를 근거로 기존 기능과 남는 불편을 비교하고, 새 부품 없이 가능한 개선안 1개와 검증 계획을 제안해줘.”
- Screening B: “B502S33의 실제 사용 후기를 근거로 기존 기능과 남는 불편을 비교하고, 새 부품 없이 가능한 개선안 1개와 검증 계획을 제안해줘.”
- 모든 설정에 같은 중립 실행 조건을 추가한다: 보존 자료만 조회, 기존 Agent/Skill/Tool 사용, 기획·검토·저장·실제 보고서 전달, 미확인 보류, 새 웹/API/소스 변경 금지. 정답·출처 위치·기대 업무 상태는 알려주지 않는다.
- 별도 전자레인지·후속·빈 catalog 온라인 조사 확인은 screening 수치와 구분한다. 개발자가 작성한 공개 평가 입력이며 blind holdout으로 부르지 않는다.

## 후보 설정과 실제 가용성

| 제공사 실행기 | 요청 후보 | 비교 목적 |
|---|---|---|
| Codex 0.162.0 | GPT-5.6 Sol medium | 다른 모델의 같은 effort |
| Codex 0.162.0 | GPT-6.1 Sol low / medium / high | 같은 모델의 effort만 변경 |
| Claude Code 2.1.296 | sonnet medium / opus medium / opus high | 동일 effort 모델 비교와 같은 모델 effort 비교 |

Codex 후보는 공식 모델 문서와 로컬 모델 목록에서 확인했고 실제 성공/관측 모델은 실행마다 별도로 확인한다. Claude alias는 실제 실행의 resolved model을 기록해야 하며 미인증/접근 거절은 미실행/접근 실패다. 같은 effort 이름이 제공사·모델 사이의 같은 연산량을 뜻하지 않는다. 실제 effort가 관측되지 않거나 cap/fallback이 있으면 그 한계를 표시한다.

[OpenAI GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Claude 모델·effort](https://code.claude.com/docs/en/model-config), [Claude CLI](https://code.claude.com/docs/en/cli-reference)를 2026-10-12 열어 확인했다. 공식 기능 지원은 이 계정의 실행 성공·최적 설정을 입증하지 않는다.

## 실험 분리와 상한

1. **모델/effort:** 현재 단일 Agent, 웹/뷰어 훅/서브에이전트 off, 동일 기획 입력으로 설정만 비교한다. 순차 실행·두 문항에서 설정 순서를 뒤집고 캐시 관측을 보존한다.
2. **일반 코드 렌더링/HTML:** 보존한 실제 report_plan/export를 최신 동결 코드로 오프라인 재생한다. 모델 호출·온라인 조사 없이 자료 변환·DOCX/PDF·검사·HTML 제작을 각각 측정한다. 브라우저 실제 paint 시간은 별도이며 HTML 파일 생성 시간과 같다고 가정하지 않는다.
3. **선택적 서브에이전트:** 모델/effort 후보를 정한 뒤 동일 조건에서 현재 구조와 독립 근거 검토자 최대1명을 비교한다. 실제 위임 ID/결과/통합·실패를 관측해야 하며 역할 정의만으로 실행을 인증하지 않는다.
4. **온라인 e2e:** 빈 catalog에서 조사부터 최종 종료까지 별도 관측한다. 외부 접근/조사 차이를 고정 근거 모델 비교와 합산하지 않는다.

전체 native 부모 실행 최대30회, 입력당420초, 자동 재실행0, 기본 동시 실행1. 실패·timeout도 분모에 남긴다. 기술 관측 오류의 DB 재읽기·지문 대조는 새 AI 재실행이 아니다. 실행 상한은 평가 runner의 제한이며 제품 모든 backend의 종료/예산 통제로 설명하지 않는다.

## 품질과 선택 규칙

7축: 목적/제약, 모델/버전, 불편→기능→제안, 출처 의미/맥락, 미확인/보류, 최종/저장 정합, 실행/검증 계획. 축별0/1/2, 사전 정당한 N/A만 제외한14점 환산이다. 근거 부족으로 정당하게 보류한 응답과 기획 완료를 별도 집계한다.

필수 gate는 환산12/14 이상, 적용 축0점 없음, 중대 오류0, 현재 valid 저장·export·최종 전달 일치다. 원문 왜곡·모델 전이·공식 문구 오귀속·근거 없는 안전/효과 확정·소스/설정 임의 변경은 중대 오류다. 파일 생성은 의미 정확성/실물 효과 인증이 아니다.

설정·시간·usage를 가린 질문/원문/후보/저장·최종 dossier를 독립 검토한다. 성공한 응답만 골라 평가하지 않는다. 후보 반복 확인에서 평균 점수 손실≤0.5/14, 문항별 손실≤1/14, 새 중대/출처/전달 결함 없음이 “품질 차이 작음”의 운영 기준이다. 작은 표본의 선택 기준이며 통계적 동등성·전 제품군의 우월성을 입증하지 않는다.

빠른 설정도 품질 gate를 통과해야 한다. 서로 다른 모델을 테스트하지 않은 숫자 구간(예: 5.6~6.1 전체)으로 묶어 권장하지 않는다. 실제 확인한 모델·effort의 명시 집합과 업무/자료/환경 범위만 권장한다. 모두 gate 미충족이면 추천을 보류한다.

## 계측·발표 기록

- 실행 시작·native 최초 Tool·기획/저장/파일·최종 답변·process exit는 서로 다른 경계다.
- Tool 시작/완료·exit/error·중첩/미완료 span, 데이터/source/install 지문, 요청/관측 모델·effort, 원질문·후속·캐시·실패를 보존한다.
- Tool 사이의 잔여 시간에는 모델 추론/생성·API/네트워크·런타임 대기가 섞인다. 이 값을 전부 “추론 시간”으로 표시하지 않는다.
- 원시 시간·범위·중앙값과 실패 분모를 제공한다. 단일 관측을 일반적인 p50·속도 우위로 확대하지 않는다.
- Codex input은 cached input을 포함하고 output은 reasoning을 포함한다. 이 하위 항목을 다시 더하지 않는다. Claude는 final/modelUsage의 제공사별 정의로 별도 기록하며 스트림의 중복 cumulative를 합산하지 않는다.
- 실제 자식 사용량의 포함 범위가 확인되기 전에는 부모/자식 각각과 coverage를 표시한다. 전체 backend 호출·청구·관측되지 않은 값은 unknown이다.
- 원문 로그/DB/개인 계정은 로컬 비공개 보존. 공개 Git에는 코드·프로토콜·비개인 수치/지문·한계를 남긴다. 사람 비교는 제외한다.

## 평가 도구 재현 방법

`evals/runner/model_effort_eval.py`는 개발 평가 도구이며 제품 ZIP에 넣지 않는다. 최신 제품 ZIP을 별도 새 폴더에 설치·doctor 확인한 뒤 아래 plan의 경로를 실제 환경에 맞춰 지정한다. CLI는 해당 구독 계정으로 인증돼 있어야 한다. 웹 접근 권한/자료 충분성·상한 내 성공은 별도 판정이다.

```json
{
  "mode": "fresh_online_e2e",
  "workspace_root": "../isolated-evaluation-jobs",
  "run_root": ".harness/evaluation-example/native",
  "sources": {"codex": "../isolated-installed-product"},
  "codex": "codex",
  "timeout_seconds": 600,
  "target_seconds": 300,
  "jobs": [{
    "id": "unique-new-attempt",
    "provider": "codex",
    "model": "gpt-6.1-sol",
    "effort": "medium",
    "product": "unspecified",
    "question": "실제 사용 근거로 요청한 제품군의 기존 기능과 남는 불편을 조사하고 개선안과 검증 계획을 제안해줘."
  }]
}
```

`python evals/runner/model_effort_eval.py --plan PLAN.json --provider codex`를 실행한다. source/job/log 폴더는 새 격리 경로이며 `.venv`·runtime-data는 source에서 복사하지 않는다. 네 진단과 이번 온라인 실행의 초기 runner는 orchestration exit0여도 case timeout을 기록했지만, 수정한 runner는 native 비성공/관측 실패를 exit1로 반환한다. JSON의 native 상태·현재 저장·의미 품질·최종 전달을 별도로 확인한다. 중복 ID는 실행 전에 거절하고 이미 시도한 job은 자동 재실행하지 않는다. 전체30부모 입력의 계획 상한은 backend 모델 호출수와 다르다.

`evals/runner/profile_report.py --workspace WORKSPACE --plan SAVED_REPORT_PLAN --export SAVED_EXPORT --viewer PINNED_BUILD_VIEW --out NEW_OUTPUT`는 저장 입력을2회 오프라인 재출력해 단계별 시간·지문을 남긴다. 해당 제품의 locked Python 의존성 환경으로 실행하고 입력을 덮지 않는다. 새 HTML/자료집에 실제 원문이 포함되므로 출력은 Git 제외 경로에 둔다. 브라우저를 열거나 모델/웹을 호출하지 않는다. 함수 내부 구간은 inclusive이므로 합산하지 않는다.
