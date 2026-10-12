# 같은 제품명 요청의 실제 조사와 전달

일반 코드 도구는 모델을 호출하지 않는다. native AI가 실제 자료 조사·분석·본문 작성·의미 검토를 수행한다. 아래 journal은 시간·동일 요청·보존 문구의 기계 검증과 호출자 신고이며, 출처의 권위·조사 충분성·전체 후기 관측·의미 품질을 자동 인증하지 않는다. 재현 입력은 실제 새 조사 인수와 구분한다.

`open_product_workflow`: `{question,user_submitted:true,session_id?,request_key?,budget_seconds?}`. 기본1800초, 허용1200~1800초. 같은 handle의 원질문·시작 시각·예산은 재설정하지 않는다. 명확한 제품은 AI가 해석하며 질문 키워드로 catalog 답안을 고르지 않는다. 실행기가 최초 요청 응답만 active-workflow.json에 보존할 수 있다. 사전 조사 원문·답안은 넣지 않는다.

`workflow_status`: `{research_id}`. 최초 입력부터 조사·분석·저장·파일 전달까지 같은 시계다. 1200초 이후 첫 tool 관측을 checkpoint로 남기며 정확히20분에 검사했다고 바꾸지 않는다. finished_at은 파일과 신고 검수 완료 시점이고 최종 답변을 포함한 전체 실행 종료는 native 종료 기록에서 확인한다. 시간 초과 후 모은 자료를 같은 요청의 시간 내 자료로 넣을 수 없다.

`record_workflow_event`: `{research_id,event_key,kind,data}` 또는 `{research_id,event_key,kind,data_path}`. data_path는 runtime-data 내부 JSON이며 큰 조사 기록을 분리해 CLI64KiB 입력 한도를 피한다. 같은 event_key는 같은 내용으로만 재전송한다. 완료 후 새 사건을 기록하지 않는다.

- `research_plan`: `{product_name,coverage:[positive,negative,long_term,conditions,counterexamples],source_plan:[문자열]}`. 제품 전반 사양·설명서·다양한 후기 원출처/판매처와 다음 페이지 계획을 포함한다.
- `source_scan`: `{source_url,page_label,status:observed|inaccessible|not_applicable,reviews:[],reason,snapshot_ids?:[],list_total?:정수또는null,remaining_scope?:[],source_type?:product_document|manual|review_list|market|competitor|unknown}`. observed이면 같은 요청·같은 URL의 실제 snapshot이 필요하다. source_url은 실제 관측 URL이다.
- reviews 항목: `{snapshot_id,text,review_id:문자열또는null,source_ids:[],disposition:retained|duplicate|wrong_model|wrong_option|prior_product|summary_only|insufficient_context|uncertain_identity,reason,published_date?,purchase_date?,model_option?,usage_conditions?,positive_context?,qualified_context?,text_coverage?:full_review_observed|partial}`. text는 연속된 literal 최대16000자. 전체를 읽은 경우에만 full_review_observed라고 신고한다. 고유 ID는 보존 snapshot에 있어야 하며 원문과 어떤 후기가 연결되는지는 AI가 검토한다. 옵션/날짜/구매·협찬 미확인은 그대로 보존한다. retained의 source_ids에는 이후 import할 catalog 발췌ID를 미리 정한다. 긴 후기의 문맥은 journal/원문 자료집에 보존하고 catalog 발췌는4000자 이하로 나눌 수 있다. fragment를 서로 다른 고객으로 만들지 않는다.
- `research_stop`: `{code:completion_time_reserve|sources_exhausted|sufficient_evidence|access_failure|insufficient_evidence|whole_budget_expired,basis,new_findings:[],remaining_scope:[]}`. 접근한 범위·새 발견·반례와 남은 페이지/자료를 밝힌다. 시간/접근/자료 부족은 충분성으로 바꾸지 않는다. 이후 신규 수집은 닫힌다. 이미 관측한 batch의 등록·분석·전달은 이력을 유지한다.
- `analysis_scope`: `{source_ids:[],scope_note}`. 실제 분석한 등록 원문ID를 batch별로 기록한다. 누적 scope와 catalog 전량을 구분하며 부분 분석을 표시한다.
- `checkpoint`: `{remaining_tasks:[]}`. 실제 시계와 남은 작업 확인이다.
- `finish`: `{delivered_paths:[현재reader파일전부],layout_review:{status:passed|not_run|failed,scope}}`. 현재 valid 저장 버전·파일 집합·SHA를 확인한다. 상대·절대 경로 모두 runtime-data 내부여야 한다. 구조 검사만 했으면 전체 페이지 물리 검수를 passed로 신고하지 않는다. 마지막 export_session으로 종료 사건도 내보낸다.

capture/fetch/import 모두 원래 research_id를 사용한다. timed workflow의 import에는 research_id가 필수이며 snapshot은 원래 요청의 journal·시작~deadline 관측에 묶인다. retained 후기의 snapshot/source_id/quote가 조사 기록과 연결돼야 한다. import는10개 이하 batch마다 고유 data_version으로 기존 원문을 유지한다. 최종 import 후 조사 종료하고 그 최종 --data로 같은 request를 resolve한다. retrieve의 offset은0부터 시작하며 next_offset이 null일 때 해당 query/scope의 끝이다. 반환20개 제한은 조사 종료 기준이 아니다.

출처별 검토 고유 후기, 보존 literal 관측, 제외 처리 관측, 유효 고유 후기, 분석 항목, 제안 사용 고유 후기ID는 별도 단위다. 원 ID 미확인 시 고유 총수는 null이며 제외 처리 수는 고객 수가 아니다. 같은 host의 다른 원문 URL에 같은 literal 후기 ID가 있으면 ID namespace를 확정하지 않고 고유 집계에서 미확인으로 처리한다. 같은 URL의 분할 발췌·중복은 ID 하나로 유지한다. 공식 문서·시장·경쟁 자료는 후기/수요의 대체 근거가 아니다. journal과 full/partial 문맥은 최종 export/원문 자료집에 남기고 보고서에 조사 범위·중단 이유·남은 범위·분석 범위를 자동 추가한다. finish는 현재 조사/분석 journal digest에 연결한 보고서만 허용한다. 완료 후 새 후보 쓰기를 막고 같은 후보 재전송만 허용한다. 파일 출력 품질과 실제 조사 충분성은 각각 평가한다.
