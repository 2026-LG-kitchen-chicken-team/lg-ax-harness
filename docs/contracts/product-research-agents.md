# 선택적 출품 조사·분석 위임

메인1 + 업무Skill6 + 선택적 역할3(공식 조사/후기 조사분석/독립 검토)이다. 설치·발견·실제 실행·이점·권한 적용은 각각 별도 증거다. 모든 역할을 매번 호출하거나 역할 수를 공식 가산점으로 주장하지 않는다.

후속 설명/단순 확인은 메인이 직접 수행한다. 공식 자료와 후기의 독립 조사/대조가 필요하고 실제 native Tool·자료·시간이 있으면 두 연구 역할을 선택한다. 실제 최초 입력 기준 외부 deadline까지420초 이상 남을 때 연구를 시작하며 각180초 이하·동시최대2·각역할1회다. 후보 작성 뒤 중요 귀속/상충/안전/중복 검토가 필요하고 잔여210초 이상이면 reviewer90초 이하1회. 최종90초 예약과 최초0/수정1/2는 유지한다. 메인이 실제 ID/시각/지원중단을 기록하며 문구/maxTurns는 초 제한 강제가 아니다. Tool clock은 native final/end_turn/process exit의 전체 경계를 대신하지 않는다. 미관측 backend 중단/청구는 unknown이다.

handoff: role, mode(fixed_catalog/online), 원질문/제약, request/turn(아직없으면null), 정확모델/시장/문서scope, code/data/context/catalog지문, 배정 source_ids/원문 경로, 부모확인SHA와 직접확인SHA 구분, 실제작업/전체deadline, 읽을 범위·크기·반환 필드. 자식은 먼저 읽으며 관련 없는 대화/코드/Tool목록을 복제하지 않는다.

자식은 조회/분석만 수행한다. 부모만 원문 검증/import·coverage·후보/저장·보고서를 직렬 작성한다. 두 자식은 가능한 같은 base catalog에서 대조한다. catalog가 바뀌면 반환을 조용히 rebase하지 않고 부모가 현재 request/code/scope/원문을 재대조한 accept event를 기록한다. 후보 reviewer는 불변 packet 계약을 별도로 따른다.

child source_ids 신고만으로 delivery를 인증하지 않는다. 기존 evidence_inventory/read_evidence_batch의 완전본문 delivery gate를 유지한다. record_evidence_review의 reason에는 부모 직접독해와 child 실제독해 범위를 구분한다. 읽지 않은 부분을 reviewed로 채우지 않는다. 검토신고는 의미 정확성·대표성의 자동 인증이 아니다.

온라인 원문은 실제 관측한 문서/후기 범위의 정확 본문·URL/위치·모델귀속·관측시각·full/partial·원문보존 위치가 있어야 한다. full은 관측범위 본문이며 전체웹페이지/전체고객을 뜻하지 않는다. native 검색/fetch의 요약·잘림·재서술은 capture/import 원문이 아니다. 원문artifact가 없으면 partial/등록불가. 부모가 같은URL을 새fetch하면 별도관측/시간/SHA다. source_scan·capture·import는 research_stop/최종90초 수집마감 전에 완료한다. 중단뒤 새등록·시각backdate는 금지하며 raw관측이력만 유지한다. robots/보안/인증/CAPTCHA/결제·UA사칭 우회는 금지한다.

자료 폭·긍정/부정/장기/조건/반례/제품전반을 소수 건수로 축소하지 않는다. 부족하면 정확한 partial/held로 전달한다. 웹/브라우저/PDF·MCP/플러그인은 실제필요·제공·권한·timeout·크기·원문귀속 계약이 맞을 때만 사용한다. 연구자의 금지Tool이 필요하면 부모에게 반환한다. 키/계정은 packet에 넣지 않는다. 추가LLM API실행기·모델UI생성은 없다.

같은소스/자료/질문/부모모델/effort의 parent-only와 비교한다. 오류 발견/반영·7축품질·원문폭·전체시간·실패/partial·부모/자식usage/cache포함범위/중복ID를 기록한다. 고정자료모델비교와새온라인조사는 분리한다. 이점이없는역할은 기본필수로켜지않고 작은표본을통계우위로올리지 않는다.
