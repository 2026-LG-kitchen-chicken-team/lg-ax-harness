# 선택적 출품 조사·분석 위임

직접 파일 읽기 실패를 관측한 경우에만 부모가 지문을 확인한 동일 등록 원문과 binding을 같은 자식의 native 메시지로 전달할 수 있다. input_mode=parent_supplied_text, file_read_status=failed|not_run, parent_verified_sha, child_verified_sha=unknown을 분리하고 청크 순서/총수와 누락을 기록한다. 누락/잘림은 partial이고 직접 파일 독해나 자식 SHA 검증을 인증하지 않는다. 새 fetch·원문 재서술·Agent 추가·권한 완화·deadline 연장은 하지 않는다. reviewer는 같은 불변 후보/원문을 사용하고 부모가 반환 뒤 packet을 다시 검증한다.

메인1 + 업무Skill6 + 선택적 역할3(공식 조사/후기 조사분석/독립 검토)이다. 설치·발견·실제 실행·권한 적용·이점은 별도 증거다. 모든 역할을 매번 호출하지 않는다. 후속 설명/단순 확인은 메인이 직접 수행한다.

공식 자료와 후기의 독립 조사/대조가 필요하고 실제 native Tool·자료·시간이 있을 때 연구자 각1회·최대180초·동시최대2를 선택한다. 최초 입력의 전체deadline까지420초 이상 남아야 시작한다. 후보의 중요 귀속/상충/안전/중복 검토가 필요하면 reviewer1회·최대180초를 선택한다. 최대 작업시간과 최종90초를 남길 수 없는 위임은 생략한다. 최초0/수정1/2는 별도 저장 계약이다.

**자식 시계는 실제 spawn 응답을 받은 시각부터 시작한다.** 준비/packet 작성 시각에서 먼저 시작하지 않는다. 부모가 반환 ID와 spawn 응답 시각을 기록하고 작업deadline=min(spawn응답시각+180초, 전체deadline-최종90초)를 전달·관측한다. 문구/maxTurns는 초 제한 강제가 아니다. deadline/취소에는 짧은 partial 반환을 먼저 받고 실제 지원 중단을 호출·확인한다. backend 중단/청구는 미관측이면 unknown이다. close/maxThreads가 없으면 completed/idle/interrupted와 별도 역할 재사용 정책을 기록하고 거짓 close를 쓰지 않는다.

handoff는 role, mode(fixed_catalog/online), 원질문/제약, request/turn(없으면null), 정확모델/시장/문서scope, code/data/context/catalog 지문, 배정 source_ids/원문 경로, 부모 제공 SHA와 직접 확인 SHA 구분, 전체deadline과 실제 spawn 후 작업deadline, 읽을 범위·반환 형식을 포함한다. 자식은 먼저 배정 자료를 읽으며 관련 없는 대화/코드/Skill/도구 목록을 복제하지 않는다.

runtime이 custom role을 실제 제공하면 정확 역할을 선택한다. 제공하지 않으면 해당 역할 지침과 현재 handoff를 지원되는 native 생성 메시지에 넣고 fallback으로 기록한다. 이 경로가 TOML sandbox·모델·Tool 권한을 자동 적용한 것은 아니다. 역할 설정은 OS 강제 인증이 아니다. 필요한 native 위임/읽기 권한이 없으면 skipped/not_run으로 남긴다.

자식은 조회/분석만 하고 짧은 결과부터 반환하며 파일/전체 평가보고서를 작성하지 않는다. 부모만 원문 검증/import·coverage·후보·저장을 직렬 작성하고 전체 선택 원문 폭을 보존한다. 자식 source_ids 신고만으로 full delivery/의미 검토를 인증하지 않는다. 기존 inventory/batch gate와 실제 반환·독해 범위를 대조한다. 같은 base catalog를 우선하며 변경 후 반환은 현재 request/code/scope/원문을 부모가 재대조하고 accept event를 기록한다.

모든 역할은 각 절의 대상·조건·시점·매체를 그 절에 연결한 같은 source 원문과 대조한다. 명시없는 속성·장소·인과는 AI 해석/미확인으로 두고 다른 자료의 조건을 전이하지 않는다. 배정된 계획이 있으면 사전 배정 전체 시도 분모·실패/중단/미응답·미확인, 조건통제와 오안내·완료품질·실패 탐지 비퇴행을 확인한 범위로 반환한다. 선택 evaluation_protocol/condition_controls/guardrail_metrics의 미기재는 보완 권고이며 structural_only 진단·필드 존재를 의미·측정 인증이나 전체 업무 실패로 바꾸지 않는다.

부모는 실제 compact 반환의 findings/source 연결을 같은 원문과 대조하고 핵심 전제·국소 표현·계획보완의 영향을 구분해 현재 후보에 반영하거나 미반영 이유를 남긴다. 자식의 존재·역할 설정·시작 ack·장부 등록은 이 반환과 메인 반영을 대신하지 않는다. 저장된 decision_notes/basis와 사용한 refs는 같은 버전 completion에 보존되며, 전체 catalog 독해를 사용 근거 수나 의미 인증으로 세지 않는다.

reviewer는 불변 packet의 binding/candidate 주장과 evidence_sources_path/evidence_sources_sha256/evidence_source_count로 결속한 별도 원문 JSONL의 관련 source 전체 등록본문을 읽는다. packet/candidate의 중복 인용을 전량 재독해하지 않는다. 필요한 최소 읽기·검색 도구만 쓰고 실제 읽은 경로/binding/범위를 짧게 ack한 뒤 compact 결과를 우선한다. ack는 완료나 전량 독해 인증이 아니다. compact 반환은 {findings:[{claim_id,severity,source_ids,problem,suggested_correction}],checked_source_ids,unreviewed_source_ids,completion_status}이다. 핵심 전제 오류/국소 표현/검증 계획 보완의 영향을 구분한다. planned_not_measured 계획의 분모·실패/중단/미확인 처리 상세 부족만으로 업무 전체 실패를 선언하지 않는다. 반환 후 부모가 packet 결속·지적의 원문 지지·영향을 확인하고 반영/미반영 이유와 실제 상태를 기록한다.

온라인 관측은 정확 본문·URL/위치·모델귀속·시각·full/partial·실제 원문 위치를 보존한다. full은 관측범위 본문이며 전체 웹/고객/대표성을 뜻하지 않는다. native 요약/잘림/재서술은 등록 원문이 아니다. 원문 artifact가 없으면 partial/등록불가, 부모 새fetch는 별도관측/시간/SHA다. source_scan/capture/import는 research_stop 및 최종90초 수집마감 전까지다. 중단 뒤 새등록/backdate·인증/robots/CAPTCHA/UA사칭 우회는 금지한다.

접근 실패는 내부 원형 이력을 보존하고 사용자에게 사이트/원URL의 접근 실패·부분 관측과 영향을 설명한다. HTTP code/원인은 실제 그 URL 응답에서 확인된 경우만 쓰고 불명확하면 접근 실패다. 오류 파일 방문을 요구하거나 없는 파일/다른 URL의 HTTP 보조 링크를 만들지 않는다.

같은소스/자료/질문/부모모델/effort parent-only와 오류 발견/반영·품질·원문폭·전체시간·partial·관측usage 범위를 비교한다. 검토신고는 의미·대표성의 자동 인증이 아니며 작은 표본의 차이를 역할 효과로 단정하지 않는다. 고정 자료 비교와 새 온라인 조사는 분리하고 이점 미입증 역할을 기본 필수로 켜지 않는다.
