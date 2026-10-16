# 공통 자료·입출력·상태 도구

2026-10-16 실행 문맥 보완: CLI `export_session`에서만 `--data`를 생략한 경우, 그 session의 최신 실제 turn에 저장한 workspace 내부 상대 catalog 경로를 사용한다. 경로와 기존 data/code 지문을 다시 확인하며 다른 catalog·전역 최신 자료를 선택하지 않는다. 명시한 `--data`는 그대로 적용한다. 과거 turn에 경로 결속이 없거나 파일이 이동/변경된 경우에는 정확한 `--data`를 지정하도록 안내하고 실패를 보존한다. 경로 결속은 내부 SQLite 메타데이터이며 export에 개인 절대 경로를 추가하지 않는다. 새 요청 시작·자료 import·다른 operation의 기본 자료 선택은 바꾸지 않는다. 새 범위와 실제 후속의 `prior_scope` 계약은 [workflow](product-workflow.md)를 따른다.

2026-10-14 보완: `save_and_export`는 현재 검토 저장 결과에서 일반 코드로 만든 `completion_summary`를 함께 반환한다. 별도 `get_completion_summary({session_id,turn_id,expected_result_version})`로 같은 현재 버전의 텍스트·불변 파일/SHA를 재조회할 수 있다. 새로운 사실을 생성하거나 전체 원문을 다시 모델에 넣지 않는다. 응답 크기 때문에 text가 생략되면 text_omitted/detail_operation을 확인한다. 기본 최종 답변은 이 text의 기획·조건 범위를 유지한다. 코드는 네이티브 최종 자유문장을 가로채지는 않으며 실제 최종 전달은 별도 대조한다.

접근 실패는 코드가 만든 access_failures로 간단히 알리고, 사용자에게 진단 파일 방문을 요구하지 않는다. free-form reason에서 HTTP코드나 파일 링크를 추정하지 않는다. 원래 실패 원문/사건은 내부 이력에 보존한다. 이후 같은 URL을 관측한 경우 ‘아직 접근 못한 자료’로 표시하지 않는다. validation_plan의 선택 evaluation_protocol:{unit,failed_or_stopped,unknown}은 실물 시험 준비를 돕는 항목이며 없다는 이유만으로 유효한 조건부 기획을 모두 실패 처리하지 않는다. 실측 효과나 수치 개선율을 주장하기 전에는 전체 시도·실패·중단·미확인 처리까지 확인한다.

2026-10-13 최신: 웹팀의 작업 화면·보고서 HTML에 현재 정형결과/원문/근거/검토·조사이력을 전달한다. 기본 save_and_export(report:false)의 web_ready/web_result를 확인하고 prepare_web_result로 같은 버전 복구한다. PDF/DOCX 생성·이미지검수는 기본 필수가 아니며 아래 파일규칙은 명시 report:true 호환 경로다. [웹 데이터 계약](web-result.md)을 우선한다. 신규기본1800초는 성능목표가 아닌 안전상한이고 natural-completion-v1 정책으로 전량전달/신고검토와 최종90초예약을 유지한다. 과거300/600초요청/이력은 변경하지 않는다.

브랜드/시장 미지정 새 요청은 국내 LG 대상 기본 정책을 저장한다. set_request_scope_policy는 {session_id,request_key,policy}이며 policy의 mode는 explicit_model(model_id,user_quote), explicit_brand_market(brand,user_quote,market?,market_quote?) 또는 explicit_market(market,market_quote,user_quote)다. 시장만 지정하면 기본 LG 브랜드를 유지한다. quote는 실제 원질문의 연속 부분이어야 한다. 연결 전 기본 정책만 명시 의도로 변경할 수 있다. 같은 공유 검사는 대상 등록·request 연결·후보 저장에 적용한다. 명시 시장은 AI 해석의 원문 근거를 남기며 언어/모델 prefix로 판매국을 자동 인증하지 않는다. legacy 정책 없는 과거 이력과 합성 코드 자료는 이 기본 정책의 새 업무 인수로 설명하지 않는다.

export의 turns와 candidates에는 기존 result/evidence_refs/payload/hash를 바꾸지 않는 source_metadata 배열을 추가한다. 정확 catalog reference 전체가 일치할 때만 kind=review/product_fact를 연결하며 과거/미확인 참조는 kind:null이다. 모델/문서/data 버전·source_id·SHA와 binding을 함께 보존한다. manual은 현 catalog에서 product_fact로 등록되어 있으며 문서 종류를 접두어/URL로 추정하지 않는다.

제품명으로 시작하는 새 실제 업무의 open_product_workflow/record_workflow_event/workflow_status와 전체 시계·literal 후기·출처별 수량·종료/분석/전달 계약은 [같은 요청의 조사·전달](product-workflow.md)을 따른다. retrieve_reviews/retrieve_product_facts는 선택 offset(기본0)과 next_offset으로20개 이하 반환 batch를 순회한다. batch 크기는 조사 완료 기준이 아니다.

2026-10-11 현재 계약: product_family는 개방된 식별자이며 exact catalog 모델과 일치해야 한다(family_mismatch). runtime engine은 codex/claude/fixture/null이며 Gemini 신규 요청은 거부한다. concept의 선택 필드 implementation_steps와 validation_plan(metric/baseline/method/success_criterion/business_value/status)을 검사한다. 새 업무 지침은 둘 다 작성하며 status는 planned_not_measured만 허용한다. planning_detail_complete는 필드 존재만 확인하며 효과/평가 통과 인증이 아니다. 구버전 결과는 호환하고 없으면 false다. 기본 자료는 빈 data/business/empty이며 신규 자료는 실제 관측 후 등록한다. v4는 과거 시험 자료다. 아래 날짜별 내역은 당시 기록이다.

Python 3.12 표준 라이브러리 JSON·hashlib·SQLite로 구현했다. 추가 모델 API·Agent 실행 루프·벡터 DB·플러그인·MCP는 필요하지 않다. 현재 소규모 자료는 모델·버전 필터와 문자 검색으로 처리한다. 검색 품질·자료량이 이를 넘으면 같은 계약을 유지하며 조회 구현을 바꾼다. 기존 LG 작업물은 재사용하지 않았다.

## 자료 계약과 사용 범위

- `data/business/lg-pilot-v1/`: 실제 S836GBB122 모델 1개, 공식 사양 요약 4개, 실제 표시 후기 발췌 3개. 새로 읽은 [LG 공식 제품 원문](https://www.lge.co.kr/product/refrigerators/s836gbb122?modelId=MD10559848&pdpType=PURCHASE)을 근거로 작성했다. 현재 모델 불편 근거는 부족하다.
- `data/synthetic/kitchen-v1/`: 신규 가상 모델 3개·버전 범위 4개·설명서 항목 12개·리뷰 40개. `purpose=test_only`. 출품 업무·시장 수요·시연 효과의 근거로 사용하지 않는다.
- 각 자료는 `manifest.json`, `models.json`, `sources.jsonl` 전체 지문·수량·중복·타입·모델 범위 검사를 통과해야 적재된다. 동일 `data_version`으로 내용이 바뀌면 기존 DB가 거부한다. 변경 자료는 새 버전을 부여한다.
- 원문 발췌의 `sha256`은 보존된 UTF-8 발췌 문자열의 지문이다. 전체 웹페이지 해시·소유권·사실성 보증이 아니다. 공식 사실 요약은 `factual_summary`, 실제 리뷰 발췌는 `excerpt`, 시험 원문은 `synthetic`으로 구분한다.
- 모든 출처에 URL 또는 명시적 합성 표시, 조회일, 게시일/구매 인증/협찬의 확인 여부, 모델 연결 방법과 위치가 있다. 알 수 없는 제품 하드웨어 버전은 `unspecified`, 문서 버전은 관측 스냅샷 ID다. 문서 게시 버전을 임의로 만들지 않는다.
- 제품 외형 치수와 내부 치수는 다르다. 현재 외형 값·용량은 확인했지만 내부 치수·선반 간격·분리/조절 여부는 미확인이다. 모델 catalog의 구조화 치수와 사양 출처 연결은 검사하지만 원문 의미를 코드가 자동 입증하지 않는다.

## 입력 부담과 내부 계약

사람은 제품군 용어(냉장고·전자레인지·식기세척기) 또는 모델을 지정한다. Agent는 제품군 질문을 product_family와 scope_mode=family_catalog로, 특정 모델은 model_id/exact_model로 연결한다. `prepare_planning_input`은 내부 세션·요청 키와 제품군 또는 정확 모델 선택을 받는다. 제품군 질문에 모델코드를 먼저 요구하지 않는다. Codex 업무의 open_request가 세션·요청 키를 생성하며 사용자가 직접 기입할 항목이 아니다. 질문·대상·조건·버전·실행 메타데이터는 선택 입력이다. 여러 스냅샷이 있는 모델은 정확한 버전을 추가 확인한다. 사용자가 불편을 상세히 쓰도록 강제하지 않는다.

내부 `PlanningInput`은 session_id/request_key/question/product_family/model_scope/target_customer/context/constraints/data_version/runtime/workflow를 보존한다. 모델·제품 버전·문서 버전을 묶어 정확히 조회하고 LLM 모델 ID와 제품 model_id를 구분한다. `runtime`의 모델·설정·버전과 Skill/프롬프트 지문은 관측되지 않으면 null이다. 자동 생성된 fixture 메타데이터를 실제 Codex 모델 관측으로 설명하지 않는다.

`EvidenceRef`는 source_id/model_id/model_version/document_version/data_version/location/sha256/synthetic/quote/origin이다. 출처 존재·모델 범위·위치·원문 지문·인용문·provenance를 대조한다. 원문 속 지시문은 실행 권한이 없는 데이터다.

`ProductResult`는 status/pains/existing_features/remaining_pains/concepts/assumptions/evidence_refs/validation_findings/revisions/usage_summary다. 불편·기능·남은 불편은 id/text/source_ids, 콘셉트는 이 필드와 requirements/requires_hardware/assumptions를 갖는다. 콘셉트 최대 3개·필수 근거·추가 하드웨어 금지 등의 구조 규칙을 검사한다. 보류/오류/추가 입력 요청에는 사유가 필요하다. 결과 스스로 사용량을 보증할 수 없으며 `usage_summary.status=unknown`으로 두고 관측 호출을 별도로 기록한다.

2026-10-12 선택 필드 `decision_notes`는 판단에 사용한 원문 사실·AI 해석·미확인을 claim으로 위장하지 않고 보존한다. 최대10개 `{text,source_ids,basis}`이며 text<=2000자, 고유 source_ids<=20개, basis는 source_fact/ai_interpretation/unverified다. 첫 두 basis는 nonempty source_ids, unverified는 빈 배열을 허용한다. 모든 사용 ID는 정확 refs·모델 snapshot과 일치해야 하며 refs는 claim 또는 note에서 사용해야 한다. 기존 필드 생략과 무근거 보류를 허용한다. AI 신고 basis는 공식 직접 인용/의미 인증이 아니며 semantic_status=unverified/acceptance_ready=false와 completed의 concept/assessment 조건을 유지한다.

검사 결과의 `contract_valid=true`는 코드 계약 통과다. `semantic_status=unverified`, `acceptance_ready=false`를 함께 반환한다. 반대 주장에 실제 출처를 붙이는 오류, 기존 기능 중복, 제외 불편의 의미, 제조 가능성, 시장 효과는 별도 근거 검토·실제 AI 평가가 필요하다. `completed`도 제출자가 요청한 업무 상태이며 심사 품질 통과를 뜻하지 않는다.

## 호출·크기·오류 계약

실행: `uv run python product-tools/cli.py OPERATION --input JSON_FILE`. UTF-8을 권장하며 UTF-8 BOM과 명시적 UTF-16 LE/BE BOM도 file/stdin에서 해석한다. BOM 없는 UTF-16·ANSI는 추정하지 않고 오류로 반환한다. 원본과 UTF-8 변환 후 각각256KiB 한도·중복 키·엄격한 JSON 검사를 유지한다. 기본 자료는0모델·0출처의 data/business/empty이고 기본 DB는 Git에서 제외한 `runtime-data/product.sqlite`다. stdin JSON도 가능하다. `--data`로 시험 자료를 명시할 수 있다. CLI DB는 이 프로젝트의 `runtime-data/` 아래만 허용한다. 사용자 전역 설정·인증·다른 레포를 바꾸지 않는다.

| Tool | JSON 입력 | 출력/오류 |
|---|---|---|
| list_models | product_family | 모델 이름·정확 scope·자료 버전/지문·모델별 원문 수; catalog_cases_only, 독립 고객 수 아님 |
| doctor | 없음 또는 `{}` | 지문·모델·수량·business/test_only·검사 범위 |
| open_request / current_request / export_session | [Codex 대화 계약](codex-product.md) | 자동 handle·실제 추가 질문·동일 요청 재개·전체 이력 export |
| save_reviewed_result | session_id/turn_id/result_key/result/assessment/expected_result_version, 선택 response_mode | 구조와 검토 정합성·실패 시도 기록; full(기본) 또는 receipt 응답; 의미 품질 미검증 |
| prepare_planning_input | 모델·세션·요청 키, 선택 질문/조건 | 내부 입력·공식 모델 정보; unknown_model/unknown_scope/needs_input |
| retrieve_reviews / retrieve_product_facts | 정확한 scope, 선택 query/limit/feature_key | 원문·origin·지문·조회 범위·빈 조회/잘림·캐시 여부. 리뷰에는 feature_key 없음 |
| select_evidence / match_product_scope | scope와 source_ids / scope | 정확한 근거 또는 scope_mismatch/source_not_found |
| validate_source_refs | evidence_refs, model_scope | 구조 통과·의미 미검증 또는 reference_mismatch/quote_mismatch |
| validate_constraints / validate_result_contract | input, result | 공통 구조·조건 검사. 의미·효과·공간 실현 가능성은 미검증 |
| start_turn / get_turn | input+user_submitted / session_id+turn_id | 멱등 새 요청/기존 요청·상태·이력·usage·무효화 |
| save_result | session_id/turn_id/result_key/result/expected_result_version | 최초/수정 결과 시도·검증 실패를 함께 저장, accepted/reason·현재 상태 |
| record_usage | session_id/turn_id/call | 알려진 subtotal과 미측정 개수, 전체성 미검증 |
| cancel_turn | session_id/turn_id/cancel_key/reason/expected_result_version/user_submitted | 후보 없는 로컬 취소·멱등 receipt. native/backend 중단은 별도 미확인 |
| begin_invocation / finish_invocation | 세션/turn/호출 ID/Tool·요청 지문 또는 종료 상태 | 호출자 보고 장부. Tool을 실행·취소하거나 네이티브 호출을 통제하지 않음 |

문자 조회는 literal 부분 문자열 검색이다. 입력256KiB, 내부 planning12KiB, 후보 결과128KiB다. 일반 조회·bundle·receipt 출력은64KiB이며 상세 상태(get_turn/current_request/open_request/save_result/save_reviewed_result)만256KiB다. 일반 업무는 receipt와 export 경로를 받아 큰 결과를 대화 문맥에 반복하지 않는다. 원문 파일 각1MiB, 조회 최대20건, query 최대200자다. JSON 중복 키·NaN/Infinity·bool 숫자·미지 필드를 거부한다. SQLite 잠금 대기5초, 실제 검사 명령은 부모 check의30–120초 상한으로 실행한다. 조건부 HTTP 관측·native 본문 기록·새 버전 등록을 추가했다. 별도 [외부 조사 계약](web-evidence.md)의 지원 형식·socket timeout·native 브라우저 미포함 범위를 따른다.

종료코드 0은 명령 실행 성공이고 1은 구조화 오류다. 후보 결과가 rejected/held여도 저장 명령 자체가 완료되면 0이며 `accepted=false`와 reason을 확인해야 한다. unknown_model/unknown_scope, 유효 범위의 empty, 파일 무결성 오류, 근거 불일치, 저장 실패, stale_context는 서로 다른 상태다. 출력 초과 시 output_limit을 반환한다.

## SQLite 상태와 재사용

`UNIQUE(session_id,request_key)`를 유지한다. 같은 키·동일 입력 재전송은 기존 turn·수정 횟수를 반환하고 같은 키·다른 입력은 충돌이다. `user_submitted=true`는 호출자의 진술이며 사용자 인증·승인 증명이 아니다. 실제 Codex 첫 입력·후속 입력 연결은 [native 검증](../validation/codex-product.md)을 따른다. Claude/Gemini 검증은 남아 있다.

최초 후보는 revision 0, 수정 후보는 1·2다. **검증에 실패한 후보도 시도로 기록**하고 새 result_key·재접속으로 한도를 초기화하지 않는다. 같은 result_key·동일 결과는 멱등, 다른 결과는 충돌이다. 세 번의 후보 이후 더 제출하면 보류하고 이력·실패 사유를 유지한다. 결과 버전은 낙관적 동시 갱신 검사에 사용하며 트랜잭션 실패는 후보·카운터를 함께 롤백한다. 복구할 수 없는 malformed JSON/크기 초과는 Tool 입력 오류이며 후보로 적재되지 않는다.

새 요청 키를 가진 실제 추가 입력은 새 turn을 만든다. 질문·조건·제품/문서·자료·규칙·Skill/프롬프트·모델 설정·코드 지문 변화는 과거 결과를 보수적으로 전체 무효화한다. 단계별 부분 무효화는 아직 구현하지 않았다. 과거 입력·시도·관측 usage는 보존하며 오래된 결과를 최신 결과로 반환하지 않는다. 결과와 조회 캐시는 저장 지문을 대조한다. 이 로컬 DB는 서명·인증 경계가 아니다.

입력·결과 기록의 재개와 생성 결과의 업무 재사용은 구분한다. 실제 모델·설정·버전 또는 Skill/프롬프트 지문이 미관측이면 기록을 조회할 수 있어도 `business_reuse_eligible=false`다. 결과 자동 재사용이나 LLM 호출 생략을 구현했다고 설명하지 않는다.

자료 조회 캐시는 자료·조회 조건·코드 지문을 사용한다. 다른 질문이어도 같은 자료 조회를 재사용할 수 있지만 이것은 LLM 결과 캐시나 토큰 절감 실증이 아니다. 실제 Agent가 필요한 근거만 읽는지는 후속 통합 평가에서 확인한다.

등록된 invocation은 첫 시도와 재시도 가능한 실패 후 한 번의 기술 재시도를 허용하고 같은 ID 재개 시 횟수를 유지한다. turn당 등록40개 상한은 장부에 적용된다. 실제 Tool 실행 경로·네이티브 모델 호출의 강제 상한은 이 장부만으로 보장하지 않는다. 사용량은 호출 ID별 보고된 input/output/cache/reasoning/cost를 성공·실패 모두 합산한다. unknown은 null이고 실제 0과 구분한다. 전체 네이티브 호출·비용이 관측되지 않아 잔여 예산이나 절감률은 계산하지 않는다.

cancel_turn은 명시적 사용자 취소의 호출자 보고를 세션·turn에 연결한다. 같은 cancel_key·사유·expected_result_version 재전송은 최초 기록을 반환하고 다른 취소 요청은 cancel_conflict다. BEGIN IMMEDIATE 안에서 버전을 확인해 취소와 후보 저장 경쟁을 직렬화한다. pending/needs_revision/held 등 미종료 업무를 cancelled로 닫고 후보·revision/result_version·이력·usage·running invocation은 변경하지 않는다. 오래된 미종료 turn도 취소할 수 있지만 valid=false를 유지한다. completed/failed/이미 결과 형식으로 cancelled인 종료 turn은 소급 변경하지 않는다. 취소 이후 신규·동일 후보 재저장과 신규/재시도 invocation을 거절하며 latest_result는 숨기고 과거 후보는 export에서 보존한다. 종료·후보3회 소진 turn도 등록 호출을 더 시작하지 않는다. 기존 호출의 늦은 finish/usage는 계속 기록하되 업무를 되살리지 않는다. 반환 scope=local_business_write_barrier, native_execution_controlled=false, backend_stop_observed=null은 실제 실행기 중단/권한 제어를 뜻하지 않는다. 직접 네이티브 Tool/HTTP 경로 우회까지 이 장부가 차단한다고 설명하지 않는다.

## 실제 사용과 재현

```powershell
uv run python product-tools/cli.py doctor
uv run python product-tools/cli.py prepare_planning_input --input evals/development/select-real-model.json
uv run python product-tools/cli.py retrieve_reviews --input evals/development/retrieve-real-reviews.json
uv run python -m unittest discover -s tests/product-tools -v
```

시험 자료 조회는 `uv run python product-tools/cli.py --data data/synthetic/kitchen-v1 --db runtime-data/synthetic-tests.sqlite retrieve_reviews --input evals/development/retrieve-reviews.json`처럼 목적을 명시한다. 자료 재생성은 scripts/create-real-pilot.py와 create-synthetic-data.py로 가능하며 외부 사이트를 자동 조회하지 않는다. 실제 source snapshot의 변경은 새 data_version을 요구한다.

개발 사례 2개와 합성 예외 평가18개는 계약/실패 시험용이다. 실제 자료 평가3개는 긍정 의견의 불편 조작·내부 치수 추정·효과 수치 조작을 거부하는지 확인하기 위한 별도 입력이다. 모델 실행·평가 runner·시간/공수 baseline은 아직 미구현/미측정이다. 업무 Skill·네이티브 설치·의미 판정·자료 충분성·시연 완성을 이 검사로 대신하지 않는다.

## 2026-10-10 출품 Skill·외부 조사 추가

현재 기본 catalog는 실제 lg-research-v3(3모델·6후기·19사실)다. 최초 pilot과 기존 검사 이력은 보존한다. Agent/Skill 원본6개·실행 wrapper와 Codex 설치·대화 Tool을 작성했다. 실제 Codex 발견·업무 연결은 native 검증 기록을 따르며 Claude/Gemini 인수는 별도다. `review_product_result`의 입력/판정 한계는 [상품기획 계약](product-planning.md), fetch_web_page/capture_web_page/import_web_evidence는 [외부 조사 계약](web-evidence.md)을 따른다. 자료 버전은 초기 조사 후 확정하고 이미 시작된 turn은 새 키로 초기화하지 않는다.

S05 추가: open_request_bundle은 open_request와 동일 입력/멱등 계약이며 정확한 scope의 리뷰·사실 원문을 한 번 반환한다. 종류 metadata와 원문 refs를 분리하고 조회20개/종류·응답 바이트 상한의 잘림/누락 ID를 명시한다. 자료 충분성은 판단하지 않는다. 큰 현재 결과는 handle과 detail 조회 안내를 유지한다. save_reviewed_result는 assessment 검사를 transaction 안에서 필수로 수행하여 null/필드 누락도 유효 JSON 후보이면 실패 이력과 수정 횟수에 남긴다. 마지막 저장 응답의 turn을 다음 저장/최종 상태에 사용하며 충돌/재개/외부 변경에만 재조회한다. 원문 의미 검토는 생략하지 않는다.

## 제품군 입력 추가(2026-10-11)

PlanningInput의 선택 scope_mode는 exact_model/family_catalog다. 구버전 입력은 유지한다. family_catalog는 같은 제품군의 명시적 model_scope(최대5개)를 보존한다. 빈 범위·복수 스냅샷·5개 초과는 좁혀야 하며 첫 모델/첫5개를 자동 선택하지 않는다. 식별자 없는 후속은 제품군 범위를 유지하고 명시적 모델 선택만 축소한다. 다른 제품군 선택은 해당 자료로 새 범위를 만든다.

각 pain/existing_feature/remaining_pain/concept의 근거는 한 exact scope에만 귀속한다. pain→remaining→feature 대조, concept→remaining→geometry 연결도 같은 scope로 검사한다. 가족 결과는 모델별 제한 사례를 모은 기획이며 전체 제품군 공통 문제·발생률·시장 수요를 입증하지 않는다. 치수/보유 제품 안전 판단은 정확 모델 및 내부 치수 등이 확인될 때만 한다. 전자레인지/식기세척기 등록 모델이 각각1개라는 자료 한계를 밝혀야 한다.

## 빈 후보 양식 추가(v7.2)

open_request_bundle/resolve_request_bundle 응답의 candidate_template은 현재 turn의 handle/version과 빈 result/assessment를 제공한다. status는 빈 값이므로 그대로 저장하면 거절되고 시도에 포함된다. AI가 실제 판단으로 채워야 한다. result_limits는 기존 배열/크기 상한 안내이며 질문/제품/답안을 선택하지 않는다. 후보3회 소진·실패·취소·오래된 turn에는 양식을 반환하지 않으며 같은 version의 재조회는 같은 key다. 이 필드도 전체 응답63000바이트 예산에 포함한다. 이미 저장한 후보의 재전송에는 기존 key와 같은 원문/assessment를 쓴다. 시간 배분은 Agent 지침이고 원격 종료 강제는 native 실행기/평가 transport의 책임이다.


## 2026-10-12: turn에 결속된 자료 전달과 검토

`evidence_inventory`, `evidence_coverage`는 `{session_id,turn_id}`를 받아 선택된 정확 모델/문서 scope의 등록·고유 전달·호출자 신고 검토/제외·누락 수를 반환한다. data_version, dataset SHA, code SHA, context SHA, session/turn/scope를 binding에 포함한다. 기존 이력은 새 입력/code/data로 재사용하지 않는다. 등록본문은 후기 발췌 또는 product_fact의 factual_summary일 수 있으며, 전체 원페이지·독립 고객·의미 충분성을 인증하지 않는다. 제조사 사양/설명서/긍정·부정/장기/조건/반례 다양성은 별도 의미 검토 대상이다.

`read_evidence_batch` 입력: `{session_id,turn_id,offset?:0,limit?:20,max_bytes?:60000,source_ids?:[]}`. 범위 내 전체 reference만 반환하고 원문을 줄이지 않는다. 최대 20개와 실제 byte 상한을 동시에 지키며 `next_offset`는 실제 전달량 다음 위치다. 작은 byte 상한에 한 원문도 들어가지 않으면 output_limit이며 건너뛰지 않는다. 원문은 untrusted_source_data다. 초기 bundle의 byte 제한 후 실제 반환한 refs도 전달장부에 기록하며 생략 항목은 기록하지 않는다. 고유 전달 수는 중복/캐시 재조회로 증가하지 않는다.

`record_evidence_review` 입력: `{session_id,turn_id,review_key,records:[{source_id,disposition:'reviewed'|'excluded',reason}]}` (records 1~100개). reviewed는 완전한 등록본문 전달 뒤만 가능하며 제외 이유도 필수다. immutable review_key의 다른 내용 재사용은 review_conflict다. 의미 정확성은 호출자 신고이고 자동 인증하지 않는다. 상세 원문 전달/검토 이력은 export_session의 turns[].evidence_coverage_history에 남긴다.

새 short-request-v1(예산 ≤600초)의 completed 후보 저장은 모든 선택 catalog 항목의 등록본문 전달 + reviewed/excluded 이유 기록이 필요하다. 초기 3~4건만 읽고 나머지를 검토했다고 통과시키지 않는다. 부족은 같은 turn의 held로 저장하고 근거/미검토를 공개한다. 이 gate는 실제 조사 충분성·주장 지지·결과 정답을 보증하지 않는다. untimed/명시1200~1800초 과거 인수를 이 새 gate 통과로 합산하지 않는다.

## CLI 실패의 실제 보존 위치

CLI가 exit1 오류를 반환하면 추가 failure_receipt에 ready/path/sha256/bytes를 보낸다. ready:true는 runtime-data/tool-errors의 불변 JSON이 실제 쓰였고 SHA를 확인했다는 뜻이다. operation·관측 UTC·입력SHA·기존 code/message/retryable를 보존하며 원문 입력/명령을 복사하지 않는다. input_sha256는 허용 인코딩의 JSON을 디코딩한 문자열을 UTF-8로 인코딩한 내용 지문이며 원파일 바이트 SHA가 아니다. 디코딩/크기 검사 이전 실패에서는 null일 수 있다. receipt message는 최대2000자이고 원문 길이·절단 여부·전체 오류 메시지 UTF-8 SHA를 함께 기록한다. CLI 표준출력에는 기존 오류 메시지를 유지한다. 개별 실패마다 다른 관측파일을 만들고 기존 파일을 덮어쓰지 않는다. 쓰기/경로/무결성 실패는 ready:false로 남기며 원래 CLI 오류와 exit1을 유지한다. shell/모델/브라우저 실패 전체를 이 receipt가 수집했다고 가정하지 않는다. semantic/HTML/native중단 인증이 아니다.
