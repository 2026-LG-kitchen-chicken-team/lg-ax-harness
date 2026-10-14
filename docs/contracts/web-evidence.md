# 조건부 외부 근거 조사 Tool

2026-10-13 보완: 같은 research/URL/focus HTTP 요청의 page_id 변경으로 재시도 상한을 초기화할 수 없다. 원래 ID를 유지한다. 실제 native browser/PDF 관측은 별도 ID/capture로 기록하고 앞선 HTTP 실패를 보존한다. Tool 이름 신고와 실제 native 도구 실행은 별도 관측이다. 다른 URL/focus/요청은 별도 근거 수집이며 의미적으로 같은 query 변형까지 인증하는 필터는 아니다. 기본 clock·허용 scope·페이지 예산은 유지한다.

2026-10-10. Python3.12 stdlib urllib/html.parser/SQLite를 채택했다. 별도 모델 API·검색 서비스 구독·MCP·플러그인 패키지는 추가하지 않는다. native 검색/브라우저/PDF Tool은 실제 제공되는 환경에서만 사용하며 설치·권한 검증은 S02에 남는다.

## 호출

`uv run python skills/web-evidence-collection/scripts/run.py OP --input JSON_PATH` 또는 공통 `product-tools/cli.py`로 실행한다. 기본 DB는 runtime-data/product.sqlite다. 원문 snapshot·새 catalog는 runtime-data에서 관리하며 Git에 넣지 않는다.

| OP | 입력 | 결과 |
|---|---|---|
| fetch_web_page | research_id/page_id/url, 선택 focus/preview_chars | 실제 HTTPS 페이지의 가시 텍스트 관측·지문·짧은 preview·snapshot_path 또는 unavailable |
| capture_web_page | research_id/page_id/url/observed_text/native_tool_name, 선택 focus/preview_chars | 호출자가 보고한 native 본문 snapshot. 실제 브라우저를 실행하지 않고 Tool 이름만으로 실행을 증명하지 않음 |
| import_web_evidence | 새 data_version, observations 배열, 선택 new_models 배열 | 관측 snapshot의 발췌·모델 연결 구조 검사 뒤 새 catalog 경로. 원문 의미·옵션 일치 미검증 |
| configure_web_research | 원래 요청 research_id/max_pages(6~100000)/reason | 저장된 요청에 연결된 조사 예산·변경 이력. 기존 페이지/실패/재시도 횟수 유지 |

HTTP·관측 URL은 공개 HTTPS 출처를 지원한다. 특정 쇼핑몰/모델의 host 허용 목록으로 제한하지 않는다. HTTP 수집은 사설/루프백/link-local/mapped 주소와 혼합 DNS 응답을 거부하고, DNS를 한 번 해석한 주소에 직접 연결한 뒤 원래 hostname으로 TLS를 검증한다. 기본 포트·인증정보 없음·redirect 자동 추적 없음·proxy 자동 사용 없음. 이것은 출처의 공식성 인증이 아니다. native capture는 실제 호출자가 보고한 본문을 보존하며 자체 네트워크 접근은 없다. 응답은 text/html·text/plain과 identity encoding만 받는다. PDF는 native 도구가 필요하다.

HTTP socket timeout8초, 응답 최대2MiB, 저장 본문 최대16000자, preview4000자. `focus`는 실제 페이지에서 일치하는 문자열 주변으로 창을 좁힌다. 잘린 snapshot은 전체 원문이 아니고 SHA는 저장 창/메타데이터 지문이다. DNS resolver 자체의 종료시간은 socket timeout으로 보장되지 않는다. 전체 실행의 엄격한 wall timeout은 외부 명령 실행기의 timeout으로 제공해야 한다. HTTP parser는 JavaScript·접근성 트리·동적 후기 목록을 실행하지 않는다.

같은 research_id의 기본 예산은6개 page_id이며, 실제 업무에 추가 설명서 절·후기 문맥·맥락 자료가 필요하면 configure_web_research로6~100000개까지 사유를 남겨 조정한다. 원래 open_request의 research_id인지 검증하고 누적 성공·실패 페이지 및 예산 변경 이력을 SQLite에 보존한다. 이미 시도한 페이지 수보다 줄이지 못하고 같은 page_id는 최초+transient오류 뒤 재시도1회를 유지한다. 원자적으로 등록하고 새 프로세스로 재개해도 유지한다. URL/내용이 바뀐 동일 키는 충돌한다. 성공 관측은 무결성 확인 후 재사용한다. 새 research_id를 내부적으로 만들어 같은 요청 상한을 우회하지 않도록 Agent 지침·실제 평가를 연결한다. native 검색/브라우저 내부 호출은 이 counter의 강제 대상이 아니다.

## observations

`preview_chars`는 정수256~4000(기본4000)이며 반환 미리보기만 줄인다. 저장 snapshot·SHA·실제 발췌 검증·page_id 수집 상한은 그대로다. `focus` 주변 미리보기의 `preview_start/preview_truncated`와 저장 본문의 `text_start/truncated`를 구분한다. 미리보기 크기 변경만으로 같은 페이지를 재수집하거나 지문을 바꾸지 않는다. 인용문이 미리보기에 없으면 snapshot의 필요한 부분만 읽는다.

항목마다 snapshot_id/source_id/kind/scope/location/text/support_quote/published_date/model_matching/purchase_verified/sponsorship이 필요하다. kind=product_fact이면 feature_key/availability를 추가한다. scope는 기존 또는 같은 import에서 등록하는 모델의 정확한3필드다.

`support_quote`는 관측 저장 본문의 정확한 부분 문자열이어야 한다. 고객 리뷰 text는 이 발췌와 같아야 한다. 사양 factual_summary의 해석이 인용으로 뒷받침되는지는 모델/검토자가 판단한다. 게시일·구매 인증·협찬은 미확인이면 null. model_matching은 product_page_association 또는 explicit_model_verified이며 호출자의 판단이다. 페이지에 모델 문자열이 있어도 옵션·이전 제품·복수 모델은 따로 대조해야 한다.

공용 설명서 본문·URL에 정확한 제품 모델이 없으면 `association_snapshot_id`를 추가한다. gscs-b2c.lge.com/open/downloadFile PDF와 공식 PDP에서 새로 확인한 gscs-manual.lge.com/문서군/MFL숫자/ko-kr/main.html (실제 CNZ·CVZ 등3자리 대문자 문서군) HTML의 product_fact를 지원한다. HTML fragment는 topic_숫자만 허용하고 같은 문서의 정확 기본 URL 연결을 요구한다. 다른 문서·query·제품 경로 연결로 대체하지 않는다. 별도 관측은 catalog의 정확 모델 product_fact에 연결된 제품 페이지이며 본문에 정확한 모델 토큰과 동일한 설명서 링크가 함께 있어야 한다. 실제 native PDP 관측에서 지원 링크 href를 확인해 capture_web_page observed_text에 포함한다. HTTP 가시 텍스트 추출은 href를 보존하지 않는다. model_matching은 product_page_association으로 남긴다. 호출자 연결 보고는 제조 버전·실제 Tool 실행·공용 문서 전체 기능 적용을 증명하지 않는다. 연결 snapshot ID와 입력은 import-audit에 보존된다.

기존 자료·출처를 덮어쓰지 않고 runtime-data/catalogs/새버전에 합쳐 저장한다. imported source의 모든 참조는 새 data_version으로 갱신된다. 결과의 structural_valid는 파일/계약 검사이며 semantic_status=unverified/acceptance_ready=false다. model·문서 범위와 주장의 진실성은 자동 보증하지 않는다.

원래 질문은 open_request에 먼저 저장한다. turn 생성 전 imported data_path를 공통 Tool의 --data로 지정하고 resolve_request_bundle로 같은 request를 연결한다. 이미 시작한 turn을 새 데이터/요청 키로 갈아끼워 수정 횟수를 초기화하지 않는다. import는 기존 turn을 변경하지 않으며 snapshot 변경·전체 코드 지문 변경은 과거 결과의 freshness를 무효화할 수 있다.

## 중단

### 실제 제품 조사에서 확인한 연결 경계 — 2026-10-12

제조사 지원 페이지에도 정확 설명서 링크가 있다. 같은 제조사 identity 출처 host의 모델별 지원 URL에 정확 모델 토큰이 있고 본문에도 그 모델과 실제 manual href가 함께 관측되면 association_snapshot_id로 연결한다. 다른 모델 접미부·다른 host·링크 없는 설명서는 거부한다. 지원 페이지의 링크를 원래 PDP에서 본 것처럼 붙여 넣지 않는다.

모델명이 없는 동일 사이트의 후기 팝업은 review에 association_snapshot_id를 줄 수 있다. association은 등록 model.spec_source_id의 정확 제품 URL이며 실제 모델명과 클릭 후 관측한 child URL을 보존한다. parent 제품 query의 명시 식별 key(modelId/productId/sku/itemId 우선순위) 중 정확히1개 값과 child 경로의 완전한 segment 또는 같은 query key의 값이 일치해야 한다. child 대응 query가 충돌하거나 식별 key가 없으면 scope_mismatch다. campaignId/reviewId 등 추적값은 제품 ID를 대신할 수 없다. 같은 site만 지원하며 원래 후기에는 없던 모델명을 추가하지 않는다. 이는 호출자 관측의 구조 연결이며 옵션·이전 제품·구매·대표성·실제 클릭 실행은 별도 검토한다. 실제 공개 review-id/data-model-id·옵션·클릭 관측은 원문 audit에 함께 보존한다.

HTML 설명서의 topic 없는 첫 화면은 모델 정보·표지 위치로 보존한다. fragment가 있는 실제 절은 같은 topic 표식을 요구하고 표지에 절 위치를 붙이거나 복수 절을 합치지 않는다. CNZ/CVZ 등3자리 제조사 문서군에 동일 규칙을 적용한다. 표지·지원·공용 문서의 연결이 하드웨어 제조 버전이나 모든 기능 적용을 보증하지 않는다.

실제 LG 후기 endpoint `/mkt/review/제품ID/pdpReviewListPopup`은 경로의 제품ID가 원래 parent와 일치해야 한다. 다른 제품 경로에 일치하는 query를 덧붙여도 거부한다. 경로·query 연결 검사와 실제 공개 DOM 옵션/제품ID 검토를 함께 사용한다.

### HTML 설명서 절 보존 — v5.5

실제로 선택한 절마다 별도 page_id·fragment URL·본문 snapshot을 관측한다. origin.source_url은 그 snapshot URL에서만 복사하며 location에서 새 URL을 추정하지 않는다. location에는 같은 topic_숫자 하나를 명시한다. capture 본문의 명시 topic이 여러 개이거나 URL과 다르면 section_mismatch, import의 location 누락/복수/불일치도 section_mismatch다. 기존 혼합 snapshot도 import 단계에서 거부한다. 일반 PDP/리뷰/PDF의 위치 규칙은 유지한다.

HTTP 요청은 hash fragment를 서버에 보내지 않으므로 gscs-manual의 fragment URL fetch를 unsupported_content로 거부한다. native 도구에서 실제 선택한 절의 본문만 capture한다. 표식 없는 본문 의미·실제 native 관측은 자동 검증하지 않으며 semantic_status=unverified를 유지한다. 과거 catalog·실행 결과는 덮어쓰지 않고 재관측 시 새 버전을 쓴다.

공식 B502S33 PDP의 HTML 설명서 링크는 현재 `http://`로 표시된다. 그 관측은 그대로 보존하고 같은 host·문서 경로·기본 포트·query/fragment 없음인 경우에 한해 실제 HTTPS로 읽은 설명서와 연결한다. 다른 문서·포트·인증정보는 거부하며 HTTP 수집이나 TLS 검증 해제는 허용하지 않는다.

### 보존 원문 index → loader → 직접 절 연결

직접 `/GROUP/MFLdigits/ko-kr/topics/topic_N.html` 원문을 지원 페이지의 `main.html` 링크와 연결할 때 observation의 선택 `manual_linkage_snapshot_ids`를 사용한다. `association_snapshot_id`는 기존 정확 모델 PDP/지원 관측이며, 모든 추가 ID는 같은 `research_id`의 불변 snapshot과 workflow 관측시간 검사를 통과해야 한다. 기존 main fragment/PDF 연결 경로도 유지한다. 일반 URL prefix나 caller의 proof 메타데이터만으로 연결하지 않는다.

추가 component는 실제 보존 HTML/JS의 완전한 literal window다. `capture_web_page`의 선택 `source_literal`은 `{raw_path,raw_sha256,source_url,character_start,character_end,observed_at}`이며 raw_path는 같은 workspace의 runtime-data 내부, raw는 2MiB 이하 UTF-8, window는 최대16000자다. 전체 raw SHA와 decoded Python 문자 offset의 exact substring 및 동일 원 URL을 검사하고 import 때 다시 확인한다. 원 시각은 observed_at, 저장 재생시각은 replayed_at에 각각 남긴다. 원문 재생은 `caller_reported_preserved_https_source_replay`이며 native 브라우저/HTTP 실행 인증이 아니다. 이 경로에는 focus를 적용하지 않는다. 원문·URL·시간의 publisher 귀속은 실제 수집 기록과 함께 검토한다.

좁은 publisher adapter는 index의 실제 PartNo/Rev/Language, 해당 scope.document_version 끝의 `revNN`, 완전한 `#topic_N` href, 실제 참조 script src, 같은 origin의 관측 loader, 같은 문서의 `res/js/indexer.js`, 실제 urlHash/topicId와 child Topic_ID를 결속한다. source window들은 같은 URL마다 동일 전체 raw SHA·원 관측시각을 가져야 한다. base routing, 누락/다른 문서/미참조 loader/불명확한 태그·topic 혼합은 거절한다. 관측한 두 loader route 형태와 hash decoder literal만 읽으며 JS 실행/eval은 하지 않는다. 절 URL의 query/fragment 추가와 location의 다른/복수 topic도 section_mismatch다. origin.source_url과 원 관측 URL은 그대로 보존한다. 검증 관계·component 지문·raw SHA/offset/시간은 catalog의 import-audit.json에 남기며 semantic_status=unverified를 유지한다. 연결 검사는 기능 적용·불편 해소·실물 적합성·의미 품질 인증이 아니다.

HTTP403/redirect/미지원 형식/빈 자료/옵션 혼합을 숨기지 않는다. 제공되는 native 브라우저/PDF로 확인하거나 한도 안에서만 재시도한다. 충분한 근거가 없으면 held/needs_input을 반환한다. 로그인·구매·후기 작성·사이트 외부 쓰기는 이 조사 범위가 아니다.

## 빈 설치와 신규 모델 등록 — v7.0

기본 data/business/empty는 0모델/0출처이며 등록된 시연 답변을 포함하지 않는다. new_models 항목은 {model_id,model_version,document_version,name,product_family,synthetic:false,spec_source_id,identity_review:{source_id,manufacturer,authority:"manufacturer",rationale}}이다. product_family는 식별자이며 특정 세 제품군 enum이 아니다. model_version은 원문으로 확인하지 못하면 unspecified, document_version은 실제 관측 스냅샷을 식별한다.

spec_source_id는 같은 import observations의 product_fact/availability:present와 정확 scope가 같아야 한다. text=support_quote이며 실제 snapshot에 정확 모델 토큰이 있어야 한다. 모델 버전을 주장하면 해당 토큰도 필요하다. 치수·용량·배치 추정 metadata는 새 모델 등록에서 거부한다. identity_review는 제조사 근거를 직접 대조한 호출자 선언이며 코드가 공식성을 인증하지 않는다.

기존 exact scope 덮어쓰기는 거부하며 최대20 scope, import당10개 관측이다. URL에 모델 문자열만 있는 것, 원문 없는 모델/출처 등록, source ID 재사용, 변조 snapshot은 거부한다. 모델·관측이 전부 검사를 통과해야 새 버전 폴더를 생성한다. 추후 저장 근거의 요약 문장은 공식 인용이 아니며 origin.support_quote로 돌아가 판단한다.


## 2026-10-12: 파일 기반 bulk import

`import_web_evidence_bulk` payload는 `{input_path:'runtime-data/...json',import_key, data_version?}`다. 파일은 기존 import의 `{data_version,observations,new_models?,research_id?}` 원본이며 최대 16MiB/1000 source observations/20 new exact scopes까지 읽는다. 명시 source_id는 중복 불가다. manufacturer identity의 spec_source_id observation을 먼저 별도 batch로 등록한 뒤 나머지 입력 상대 순서대로 최대10항목·64KiB 이하 batch로 전달한다. 각 immutable catalog version은 prefix-b0001 형식이며 원본 model/version/source_id/quote/location/journal을 수정하지 않는다. 정확 모델 접미부 자동 삭제나 원문 단축은 하지 않는다. 단일 항목이 기존 계약을 넘으면 실패를 남긴다.

이 API는 원래 research_id와 literal snapshot/review source_scan journal 확인을 기존 importer에 위임한다. 브랜드/옵션/공식 귀속의 의미 판정은 코드 인증이 아니다. 실제 후기·설명서 범위를 줄여 시간 목표를 맞추지 않는다. source records/고유 후기/독립 고객은 다른 단위다. 기존 catalog 상한(20 scopes, catalog file16MiB 등)을 확대했다고 주장하지 않는다.

응답에는 status, input_sha256, original_copy, audit_path, input_count, completed_count, unprocessed_count, failed_source_ids, last_valid_catalog/version/fingerprint가 있다. 원본 바이트·입력 순서·실제 등록 순서와 batch SHA/result/error를 runtime-data/bulk-imports에 보존한다. 각 batch는 원자적이며 실패 batch 전체 source_ids를 반환하고 정확 오류 항목은 미관측일 수 있다고 표시한다. 앞서 성공한 catalog는 남기고 failed/partial_failure 뒤 자동 재시작하지 않는다. 같은 import_key 재전송은 원본 SHA/시작catalog에 결속된 기존 결과만 반환하며 interrupted도 완료로 바꾸지 않는다. 최종 새catalog를 --data로 선택한 동일 request의 resolve_request_bundle을 사용하고 새 turn으로 한도를 우회하지 않는다.

## 동일 제품 문서의 분리 관측

product_fact가 모델명 없는 상세 조각이면 임의로 모델명을 덧붙이지 않는다. 등록된 모델의 spec_source_id 정체성 원문을 association_snapshot_id로 명시하고 model_matching=product_page_association을 쓴다. 두 원문의 URL 문자열(query순서/anchor 포함), 정확 scope, 동일 research에 실제 보존된 snapshot, 정체성 원문/지원인용/본문SHA와 비미래 관측시각을 코드가 확인한다. 등록 identity가 먼저 필요하며 bulk identity-first 경로를 사용한다. 다른 query/옵션/문서/조사·변조·선언만으로는 연결하지 않는다. 기존 PDF/topic/공용설명서 연결 경로는 별도 유지한다. 설명서 표지 자체가 spec_source_id인 정상 PDF/hash section도 실제 링크와 정확 모델의 기존 manual association으로 검증하며 PDP fragment의 exact anchor 정책으로 가로채지 않는다.

import-audit의 product_page_fragment_checks는 연결 검사의 identity source/SHA, snapshot IDs/본문SHA/시각/URL/scope를 보존한다. 이는 page association이며 특정 기능의 모델별 적용·공용 FAQ·원문 의미·실물 효과를 자동 인증하지 않는다. 제품마다 차이라는 경고·적용 미확인은 원문/판단에 유지한다. 원문 수를 줄이거나 bulk partial 실패를 새 요청/키로 성공처럼 바꾸지 않는다.

## 신규 조사 범위 연결

새 research-scope-v1 workflow의 실제 web_pages 시도가 있으면 [workflow 계약](product-workflow.md)의 goals/goal_ids 및 남은 범위 공개를 적용한다. 고정catalog 재사용의 web 시도0과 기존 NULL 정책은 소급 변경하지 않는다. 기본6페이지는 기술상 초기 예산이며 여러 출처·설명서 절·후속 페이지 계획에 맞춰 조사 초기에 같은 research_id로 configure_web_research한다. 6~100000 상한은 안전 장치의 허용 범위이며 목표 수나 충분성 기준이 아니다.

Catalog 파일은 각각 최대16MiB이며 정확scope20, import10/bulk1000, source4000자 등 다른 유한 계약은 유지한다. 원본 후기의 긴 문맥은 journal/snapshot에 보존하고 catalog는 같은 후기의 연속 발췌로 나눈다. source record 수는 고유 후기·독립 고객 수가 아니다. 파일/배치 제한 실패는 실제 부분성을 보존하며 조사범위를 조용히 줄이지 않는다.
