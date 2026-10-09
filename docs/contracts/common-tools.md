# 공통 자료·입출력·상태 도구

Python 3.12 표준 라이브러리 JSON·hashlib·SQLite로 구현했다. 추가 모델 API·Agent 실행 루프·벡터 DB·플러그인·MCP는 필요하지 않다. 현재 소규모 자료는 모델·버전 필터와 문자 검색으로 처리한다. 검색 품질·자료량이 이를 넘으면 같은 계약을 유지하며 조회 구현을 바꾼다. 기존 LG 작업물은 재사용하지 않았다.

## 자료 계약과 사용 범위

- `data/business/lg-pilot-v1/`: 실제 S836GBB122 모델 1개, 공식 사양 요약 4개, 실제 표시 후기 발췌 3개. 새로 읽은 [LG 공식 제품 원문](https://www.lge.co.kr/product/refrigerators/s836gbb122?modelId=MD10559848&pdpType=PURCHASE)을 근거로 작성했다. 현재 모델 불편 근거는 부족하다.
- `data/synthetic/kitchen-v1/`: 신규 가상 모델 3개·버전 범위 4개·설명서 항목 12개·리뷰 40개. `purpose=test_only`. 출품 업무·시장 수요·시연 효과의 근거로 사용하지 않는다.
- 각 자료는 `manifest.json`, `models.json`, `sources.jsonl` 전체 지문·수량·중복·타입·모델 범위 검사를 통과해야 적재된다. 동일 `data_version`으로 내용이 바뀌면 기존 DB가 거부한다. 변경 자료는 새 버전을 부여한다.
- 원문 발췌의 `sha256`은 보존된 UTF-8 발췌 문자열의 지문이다. 전체 웹페이지 해시·소유권·사실성 보증이 아니다. 공식 사실 요약은 `factual_summary`, 실제 리뷰 발췌는 `excerpt`, 시험 원문은 `synthetic`으로 구분한다.
- 모든 출처에 URL 또는 명시적 합성 표시, 조회일, 게시일/구매 인증/협찬의 확인 여부, 모델 연결 방법과 위치가 있다. 알 수 없는 제품 하드웨어 버전은 `unspecified`, 문서 버전은 관측 스냅샷 ID다. 문서 게시 버전을 임의로 만들지 않는다.
- 제품 외형 치수와 내부 치수는 다르다. 현재 외형 값·용량은 확인했지만 내부 치수·선반 간격·분리/조절 여부는 미확인이다. 모델 catalog의 구조화 치수와 사양 출처 연결은 검사하지만 원문 의미를 코드가 자동 입증하지 않는다.

## 입력 부담과 내부 계약

사람은 우선 모델을 선택한다. `prepare_planning_input`의 필수값은 `model_id`, 내부 세션·요청 키뿐이다. Codex 업무의 open_request가 세션·요청 키를 생성하며 사용자가 직접 기입할 항목이 아니다. 질문·대상·조건·버전·실행 메타데이터는 선택 입력이다. 여러 스냅샷이 있는 모델은 정확한 버전을 추가 확인한다. 사용자가 불편을 상세히 쓰도록 강제하지 않는다.

내부 `PlanningInput`은 session_id/request_key/question/product_family/model_scope/target_customer/context/constraints/data_version/runtime/workflow를 보존한다. 모델·제품 버전·문서 버전을 묶어 정확히 조회하고 LLM 모델 ID와 제품 model_id를 구분한다. `runtime`의 모델·설정·버전과 Skill/프롬프트 지문은 관측되지 않으면 null이다. 자동 생성된 fixture 메타데이터를 실제 Codex 모델 관측으로 설명하지 않는다.

`EvidenceRef`는 source_id/model_id/model_version/document_version/data_version/location/sha256/synthetic/quote/origin이다. 출처 존재·모델 범위·위치·원문 지문·인용문·provenance를 대조한다. 원문 속 지시문은 실행 권한이 없는 데이터다.

`ProductResult`는 status/pains/existing_features/remaining_pains/concepts/assumptions/evidence_refs/validation_findings/revisions/usage_summary다. 불편·기능·남은 불편은 id/text/source_ids, 콘셉트는 이 필드와 requirements/requires_hardware/assumptions를 갖는다. 콘셉트 최대 3개·필수 근거·추가 하드웨어 금지 등의 구조 규칙을 검사한다. 보류/오류/추가 입력 요청에는 사유가 필요하다. 결과 스스로 사용량을 보증할 수 없으며 `usage_summary.status=unknown`으로 두고 관측 호출을 별도로 기록한다.

검사 결과의 `contract_valid=true`는 코드 계약 통과다. `semantic_status=unverified`, `acceptance_ready=false`를 함께 반환한다. 반대 주장에 실제 출처를 붙이는 오류, 기존 기능 중복, 제외 불편의 의미, 제조 가능성, 시장 효과는 별도 근거 검토·실제 AI 평가가 필요하다. `completed`도 제출자가 요청한 업무 상태이며 심사 품질 통과를 뜻하지 않는다.

## 호출·크기·오류 계약

실행: `uv run python product-tools/cli.py OPERATION --input UTF8_JSON_FILE`. 기본 자료는 실제 lg-research-v3이고 기본 DB는 Git에서 제외한 `runtime-data/product.sqlite`다. stdin JSON도 가능하다. `--data`로 시험 자료를 명시할 수 있다. CLI DB는 이 프로젝트의 `runtime-data/` 아래만 허용한다. 사용자 전역 설정·인증·다른 레포를 바꾸지 않는다.

| Tool | JSON 입력 | 출력/오류 |
|---|---|---|
| doctor | 없음 또는 `{}` | 지문·모델·수량·business/test_only·검사 범위 |
| open_request / current_request / export_session | [Codex 대화 계약](codex-product.md) | 자동 handle·실제 추가 질문·동일 요청 재개·전체 이력 export |
| save_reviewed_result | session_id/turn_id/result_key/result/assessment/expected_result_version | 구조와 검토 정합성·실패 시도 기록; 의미 품질 미검증 |
| prepare_planning_input | 모델·세션·요청 키, 선택 질문/조건 | 내부 입력·공식 모델 정보; unknown_model/unknown_scope/needs_input |
| retrieve_reviews / retrieve_product_facts | 정확한 scope, 선택 query/limit/feature_key | 원문·origin·지문·조회 범위·빈 조회/잘림·캐시 여부. 리뷰에는 feature_key 없음 |
| select_evidence / match_product_scope | scope와 source_ids / scope | 정확한 근거 또는 scope_mismatch/source_not_found |
| validate_source_refs | evidence_refs, model_scope | 구조 통과·의미 미검증 또는 reference_mismatch/quote_mismatch |
| validate_constraints / validate_result_contract | input, result | 공통 구조·조건 검사. 의미·효과·공간 실현 가능성은 미검증 |
| start_turn / get_turn | input+user_submitted / session_id+turn_id | 멱등 새 요청/기존 요청·상태·이력·usage·무효화 |
| save_result | session_id/turn_id/result_key/result/expected_result_version | 최초/수정 결과 시도·검증 실패를 함께 저장, accepted/reason·현재 상태 |
| record_usage | session_id/turn_id/call | 알려진 subtotal과 미측정 개수, 전체성 미검증 |
| begin_invocation / finish_invocation | 세션/turn/호출 ID/Tool·요청 지문 또는 종료 상태 | 호출자 보고 장부. Tool을 실행·취소하거나 네이티브 호출을 통제하지 않음 |

문자 조회는 literal 부분 문자열 검색이다. 입력·출력 64KiB, 내부 planning 12KiB, 후보 결과 32KiB, 원문 파일 각 1MiB, 조회 최대20건, query 최대200자다. JSON 중복 키·NaN/Infinity·bool 숫자·미지 필드를 거부한다. SQLite 잠금 대기 5초, 실제 검사 명령은 부모 check의 30–120초 상한으로 실행한다. 조건부 HTTP 관측·native 본문 기록·새 버전 등록을 추가했다. 별도 [외부 조사 계약](web-evidence.md)의 지원 형식·socket timeout·native 브라우저 미포함 범위를 따른다.

종료코드 0은 명령 실행 성공이고 1은 구조화 오류다. 후보 결과가 rejected/held여도 저장 명령 자체가 완료되면 0이며 `accepted=false`와 reason을 확인해야 한다. unknown_model/unknown_scope, 유효 범위의 empty, 파일 무결성 오류, 근거 불일치, 저장 실패, stale_context는 서로 다른 상태다. 출력 초과 시 output_limit을 반환한다.

## SQLite 상태와 재사용

`UNIQUE(session_id,request_key)`를 유지한다. 같은 키·동일 입력 재전송은 기존 turn·수정 횟수를 반환하고 같은 키·다른 입력은 충돌이다. `user_submitted=true`는 호출자의 진술이며 사용자 인증·승인 증명이 아니다. 실제 Codex 첫 입력·후속 입력 연결은 [native 검증](../validation/codex-product.md)을 따른다. Claude/Gemini 검증은 남아 있다.

최초 후보는 revision 0, 수정 후보는 1·2다. **검증에 실패한 후보도 시도로 기록**하고 새 result_key·재접속으로 한도를 초기화하지 않는다. 같은 result_key·동일 결과는 멱등, 다른 결과는 충돌이다. 세 번의 후보 이후 더 제출하면 보류하고 이력·실패 사유를 유지한다. 결과 버전은 낙관적 동시 갱신 검사에 사용하며 트랜잭션 실패는 후보·카운터를 함께 롤백한다. 복구할 수 없는 malformed JSON/크기 초과는 Tool 입력 오류이며 후보로 적재되지 않는다.

새 요청 키를 가진 실제 추가 입력은 새 turn을 만든다. 질문·조건·제품/문서·자료·규칙·Skill/프롬프트·모델 설정·코드 지문 변화는 과거 결과를 보수적으로 전체 무효화한다. 단계별 부분 무효화는 아직 구현하지 않았다. 과거 입력·시도·관측 usage는 보존하며 오래된 결과를 최신 결과로 반환하지 않는다. 결과와 조회 캐시는 저장 지문을 대조한다. 이 로컬 DB는 서명·인증 경계가 아니다.

입력·결과 기록의 재개와 생성 결과의 업무 재사용은 구분한다. 실제 모델·설정·버전 또는 Skill/프롬프트 지문이 미관측이면 기록을 조회할 수 있어도 `business_reuse_eligible=false`다. 결과 자동 재사용이나 LLM 호출 생략을 구현했다고 설명하지 않는다.

자료 조회 캐시는 자료·조회 조건·코드 지문을 사용한다. 다른 질문이어도 같은 자료 조회를 재사용할 수 있지만 이것은 LLM 결과 캐시나 토큰 절감 실증이 아니다. 실제 Agent가 필요한 근거만 읽는지는 후속 통합 평가에서 확인한다.

등록된 invocation은 첫 시도와 재시도 가능한 실패 후 한 번의 기술 재시도를 허용하고 같은 ID 재개 시 횟수를 유지한다. turn당 등록40개 상한은 장부에 적용된다. 실제 Tool 실행 경로·네이티브 모델 호출의 강제 상한은 이 장부만으로 보장하지 않는다. 사용량은 호출 ID별 보고된 input/output/cache/reasoning/cost를 성공·실패 모두 합산한다. unknown은 null이고 실제 0과 구분한다. 전체 네이티브 호출·비용이 관측되지 않아 잔여 예산이나 절감률은 계산하지 않는다.

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
