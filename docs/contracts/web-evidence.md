# 조건부 외부 근거 조사 Tool

2026-10-10. Python3.12 stdlib urllib/html.parser/SQLite를 채택했다. 별도 모델 API·검색 서비스 구독·MCP·플러그인 패키지는 추가하지 않는다. native 검색/브라우저/PDF Tool은 실제 제공되는 환경에서만 사용하며 설치·권한 검증은 S02에 남는다.

## 호출

`uv run python skills/web-evidence-collection/scripts/run.py OP --input JSON_PATH` 또는 공통 `product-tools/cli.py`로 실행한다. 기본 DB는 runtime-data/product.sqlite다. 원문 snapshot·새 catalog는 runtime-data에서 관리하며 Git에 넣지 않는다.

| OP | 입력 | 결과 |
|---|---|---|
| fetch_web_page | research_id/page_id/url, 선택 focus/preview_chars | 실제 HTTPS 페이지의 가시 텍스트 관측·지문·짧은 preview·snapshot_path 또는 unavailable |
| capture_web_page | research_id/page_id/url/observed_text/native_tool_name, 선택 focus/preview_chars | 호출자가 보고한 native 본문 snapshot. 실제 브라우저를 실행하지 않고 Tool 이름만으로 실행을 증명하지 않음 |
| import_web_evidence | 새 data_version, observations 배열 | 관측 snapshot의 발췌·모델 연결 구조 검사 뒤 새 catalog 경로. 원문 의미·옵션 일치 미검증 |

HTTP·관측 URL 허용 host는 www.lge.co.kr/static.lge.co.kr/gscs-b2c.lge.com/gscs-manual.lge.com/min-inter.co.kr다. 새 출처가 필요하면 실제 원문과 접근 조건을 확인해 코드·검사·기록을 갱신한다. HTTPS 기본 포트만, 인증정보 없음, redirect 자동 추적 없음, proxy 자동 사용 없음. 응답은 text/html·text/plain과 identity encoding만 받는다. PDF는 native 도구로 읽으며 HTTP collector가 PDF를 지원한다고 설명하지 않는다.

HTTP socket timeout8초, 응답 최대2MiB, 저장 본문 최대16000자, preview4000자. `focus`는 실제 페이지에서 일치하는 문자열 주변으로 창을 좁힌다. 잘린 snapshot은 전체 원문이 아니고 SHA는 저장 창/메타데이터 지문이다. 전체 실행의 엄격한 wall timeout은 외부 명령 실행기의 timeout으로 제공해야 한다. HTTP parser는 JavaScript·접근성 트리·동적 후기 목록을 실행하지 않는다.

같은 research_id는 최대6개 page_id, 같은 page_id는 최초+transient오류 뒤 재시도1회다. SQLite에서 원자적으로 등록하고 새 프로세스로 재개해도 유지한다. URL/내용이 바뀐 동일 키는 충돌한다. 성공 관측은 무결성 확인 후 재사용한다. 새 research_id를 내부적으로 만들어 같은 요청 상한을 우회하지 않도록 Agent 지침·실제 평가를 연결한다. native 검색/브라우저 내부 호출은 이 counter의 강제 대상이 아니다.

## observations

`preview_chars`는 정수256~4000(기본4000)이며 반환 미리보기만 줄인다. 저장 snapshot·SHA·실제 발췌 검증·page_id 수집 상한은 그대로다. `focus` 주변 미리보기의 `preview_start/preview_truncated`와 저장 본문의 `text_start/truncated`를 구분한다. 미리보기 크기 변경만으로 같은 페이지를 재수집하거나 지문을 바꾸지 않는다. 인용문이 미리보기에 없으면 snapshot의 필요한 부분만 읽는다.

항목마다 snapshot_id/source_id/kind/scope/location/text/support_quote/published_date/model_matching/purchase_verified/sponsorship이 필요하다. kind=product_fact이면 feature_key/availability를 추가한다. scope는 현재 catalog의 정확한3필드다. 새로운 모델 자체의 catalog 확장은 공식 사양 확인 후 별도 변경으로 처리한다.

`support_quote`는 관측 저장 본문의 정확한 부분 문자열이어야 한다. 고객 리뷰 text는 이 발췌와 같아야 한다. 사양 factual_summary의 해석이 인용으로 뒷받침되는지는 모델/검토자가 판단한다. 게시일·구매 인증·협찬은 미확인이면 null. model_matching은 product_page_association 또는 explicit_model_verified이며 호출자의 판단이다. 페이지에 모델 문자열이 있어도 옵션·이전 제품·복수 모델은 따로 대조해야 한다.

공용 설명서 본문·URL에 정확한 제품 모델이 없으면 `association_snapshot_id`를 추가한다. gscs-b2c.lge.com/open/downloadFile PDF와 공식 PDP에서 새로 확인한 gscs-manual.lge.com/CNZ/MFL숫자/ko-kr/main.html HTML의 product_fact를 지원한다. HTML fragment는 topic_숫자만 허용하고 같은 문서의 정확 기본 URL 연결을 요구한다. 다른 문서·query·제품 경로 연결로 대체하지 않는다. 별도 관측은 www.lge.co.kr의 같은 모델 제품 페이지이며 본문에 정확한 모델 토큰과 동일한 설명서 링크가 함께 있어야 한다. 실제 native PDP 관측에서 지원 링크 href를 확인해 capture_web_page observed_text에 포함한다. HTTP 가시 텍스트 추출은 href를 보존하지 않는다. model_matching은 product_page_association으로 남긴다. 호출자 연결 보고는 제조 버전·실제 Tool 실행·공용 문서 전체 기능 적용을 증명하지 않는다. 연결 snapshot ID와 입력은 import-audit에 보존된다.

기존 자료·출처를 덮어쓰지 않고 runtime-data/catalogs/새버전에 합쳐 저장한다. imported source의 모든 참조는 새 data_version으로 갱신된다. 결과의 structural_valid는 파일/계약 검사이며 semantic_status=unverified/acceptance_ready=false다. model·문서 범위와 주장의 진실성은 자동 보증하지 않는다.

현재 turn 시작 전 imported data_path를 공통 Tool의 --data로 지정한다. 이미 시작한 turn을 새 데이터/요청 키로 갈아끼워 수정 횟수를 초기화하지 않는다. import는 기존 turn을 변경하지 않으며 snapshot 변경·전체 코드 지문 변경은 과거 결과의 freshness를 무효화할 수 있다.

## 중단

공식 B502S33 PDP의 HTML 설명서 링크는 현재 `http://`로 표시된다. 그 관측은 그대로 보존하고 같은 host·문서 경로·기본 포트·query/fragment 없음인 경우에 한해 실제 HTTPS로 읽은 설명서와 연결한다. 다른 문서·포트·인증정보는 거부하며 HTTP 수집이나 TLS 검증 해제는 허용하지 않는다.

HTTP403/redirect/미지원 형식/빈 자료/옵션 혼합을 숨기지 않는다. 제공되는 native 브라우저/PDF로 확인하거나 한도 안에서만 재시도한다. 충분한 근거가 없으면 held/needs_input을 반환한다. 로그인·구매·후기 작성·사이트 외부 쓰기는 이 조사 범위가 아니다.
