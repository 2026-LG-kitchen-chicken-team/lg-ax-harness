# 출품 근거 검토자 불변 packet

직접 파일 읽기 실패를 관측하면 부모가 verify한 동일 불변 candidate/원문 JSONL을 같은 자식에게 native 메시지로 전달할 수 있다. binding·청크 순서/총수·전체 본문을 유지하며 input_mode=parent_supplied_text, file_read_status=failed|not_run, parent_verified_sha와 child_verified_sha=unknown을 구분한다. 누락/잘림은 partial이다. 부모 제공 본문 독해는 직접 파일 읽기/SHA 검증이 아니며 새 Agent·권한 변경·추가 조사·deadline 연장을 하지 않는다. 반환 후 동일 packet을 재검증한다.

`prepare_review_packet` 입력은 `{session_id,turn_id,candidate_path,packet_key}`다. `candidate_path`는 runtime-data 내부256KiB 이하 현재 후보 파일이며 UTF-8 변환 후에도256KiB 이하다. `session_id,turn_id,result_key,result,expected_result_version,assessment` 여섯 필드와 기존 선택 report 필드를 사용한다. 후보의 의미 정답·assessment 통과·완성도를 요구하지 않는다. 후보 session/turn/예상 저장 버전은 실제 현재 상태와 일치해야 한다. 원본 사본은 그대로 보존하고 사람이 읽는 packet은512KiB까지 허용하며 자동으로 근거나 문장을 자르지 않는다.

코드는 원본 바이트 SHA256과 immutable candidate copy를 runtime-data/review-packets에 보존한다. 후보에 인용한 전체 등록 source records도 별도 불변 JSONL로 보존하며 evidence_sources_path/evidence_sources_sha256/evidence_source_count를 packet/반환 결속에 포함한다. reviewer는 이 원문 JSONL의 관련 전체 본문을 읽고 후보 주장/조건과 대조하며 packet/candidate의 중복 인용을 전량 재독해하지 않는다. packet에는 같은 request의 question/context·code/data·정확 모델/문서 scope·현재 저장 버전, 후보·제약·원문 지문 진단을 결속한다. 후보에 쓰지 않은 catalog·전체 대화·Skill을 복사하지 않고 qualification·불확실성·정답을 자동 생성하지 않는다. 원래 후보 파일이 수정돼도 child가 읽은 불변 사본은 바뀌지 않는다. 같은 packet_key는 동일 후보 바이트/입력/현재 binding만 재생한다.

`verify_review_packet` 입력은 `{session_id,turn_id,packet_path,packet_sha256}`다. 보존 packet/candidate/원문JSONL SHA와 source count, 등록 이력, 현재 request/turn/version/code/data/context/정확 scope를 대조한다. hash 변경·새 저장 버전·취소/실패·다른 session·stale context는 ToolError이고 늦은 reviewer 결과로 현재 저장 버전을 바꾸지 않는다.

`ready`는 불변 handoff와 현재 binding을 확인했다는 뜻이다. `candidate_source_refs_valid`와 `reference_diagnostic`는 원문 ID/scope/location/SHA/quote의 별도 구조 진단이다. 잘못되거나 부족한 근거의 후보도 읽기 전용 검토할 수 있다. 진단 실패 시 후보 인용을 검증된 사실로 취급하지 않으며 `reference_checks.actual_catalog_metadata`는 실제 catalog의 기대 metadata로 별도 구분한다. `semantic_status=unverified`, `acceptance_ready=false`이며 의미 승인·결과 저장·실제 child 실행 인증을 하지 않는다. 반환에는 packet/candidate 경로·지문·binding·진단만 있고 후보 본문을 다시 출력하지 않는다.

메인은 packet 준비 → 실제 native child에 불변 packet_path와 packet/candidate SHA·evidence_sources_path/evidence_sources_sha256/evidence_source_count 전달 → child 결과 수신 → 같은 packet 검증 → 판단/수정/저장을 수행한다. 후보를 수정하면 새 packet_key로 다시 준비한다. 실제 child ID/시간/사용량과 결과를 별도로 보존하며 Tool 성공만으로 위임했다고 설명하지 않는다. 부모 packet의 전체 deadline/최종90초 예약과 업무 수정 최대2회는 별도 계약이다.

자식은 불변 packet/candidate_copy와 관련 원문만 읽고 compact findings를 먼저 반환한다. 실제 spawn 응답 시각부터 최대180초이며 작업deadline은 min(spawn응답시각+180초, 전체deadline-최종90초)다. 준비 시간을 자식 예산에서 빼지 않는다. 원문 전체 폭은 부모가 보존하고 자식의 미검토 범위는 따로 기록한다. 파일/전체 평가보고서 작성이나 추가 위임·저장은 하지 않는다. 반환 형식은 연구 위임 계약의 compact 객체이며 별도 코드 schema 승인이나 의미 자동 인증을 뜻하지 않는다.
