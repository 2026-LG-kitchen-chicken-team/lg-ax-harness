---
name: review-and-revise
description: "상품기획 후보의 원문 의미·모델·기존 기능 중복·가정·제약을 검토하고 최초 생성과 최대2회 수정을 저장할 때 사용한다."
---

# 검토·수정·저장

자료집·최종 문서는 [보고서 작성](references/report-writing.md)을 읽고 작성한다. 공개 형식은 프로젝트 루트 docs/contracts/reader-deliverables.md다. 합성 목업 검수는 실제 제품 업무의 완료 증거가 아니다. 실제 조사→분석→검토→저장→보고서 전달을 확인하고 가상 내용·수치는 복사하지 않는다. report_plan은 실제 조사 범위에 따라 자유롭게 구성하고 별도 runtime-data 내부 파일로 전달할 수 있다.

메인 Agent의 공통 안전 규칙으로 원문을 대조해 result/assessment를 작성한다. 저장 필드는 프로젝트 루트의 skills/review-and-revise/references/payload.md를 읽는다. Skill이 .agents/skills 아래 발견돼도 docs는 프로젝트 루트 docs/contracts/다. 같은 본문/상세계약 재독해는 진단 때만 한다.

bundle 응답의 candidate_template을 복사해 실제 판단으로 채운다. status는 빈 값이며 AI가 결정해야 한다. result_limits로 작성 중 배열/크기 상한을 확인한다. 한 실행 명령에서 Python json으로 파일 작성 후 save_and_export를 호출할 수 있다. 현재 delivery_ready=true면 독자용 report_ready와 실제 파일을 확인해 결과 폴더를 전달한다. 양식 복사가 의미 검토나 최종 확인을 대신하지 않는다.

보류의 판단 근거도 decision_notes에 원문 사실·AI 해석·미확인으로 구분하고 정확 refs에 연결한다. 원문 직접 인용은 support_quote의 연속 구간이며 요약/판단은 공식 발언으로 표시하지 않는다. 후기의 실제 영향·발생/회피 조건·긍정·유보 문맥과 고유 후기 ID/분모를 확인한다. bundle의 truncated=false/누락 ID 없음만으로 원페이지나 판단 문맥 전체를 확인했다고 쓰지 않는다. 중요 문맥 미확인은 조건부 한계 또는 held에 반영한다. 최종 답변에도 이 구분과 사용한 URL/위치를 전달한다. 자체 추정 실행시간은 쓰지 않으며 외부 실제 기록이 없으면 미측정이다.

일반 업무는 save_and_export로 저장과 내보내기를 한 번 수행한다. 기존 입력6필드를 유지하며 제품 최종 출력에 report:true, 선택 report_plan_path/report_sources_path/open_folder를 추가한다. API 기본 report는 false이며 Skill에서는 명시적으로 파일 제작을 요청한다. report_plan_path는 내부 작성 파일이므로 전체 보고서를 업무 저장 JSON의 64KiB에 맞춰 잘라 넣지 않는다. 응답 save/delivery_ready/export/export_error와 독자용 report/report_ready/report_error를 별도로 확인한다. 저장은 원문 의미를 인증하지 않는다. accepted=false·검증 실패도 최초0/수정1/2에 포함하며 JSON 구조로 같은 turn에서 수정/held를 기록한다. 새 키/turn으로 한도를 우회하지 않는다. accepted/valid/현재 version과 delivery_ready, report_ready와 실제 파일을 확인한 뒤 결과 폴더·파일 설명·근거와 한계를 전달한다. receipt/export는 내부에 보존한다. 오류/거절/수정 소진을 성공으로 바꾸지 않는다.

재개·충돌은 current_request/get_turn, export 실패는 export_session으로 복구한다. 과거 실패 후보·검토·출처·usage는 export에 남고 원문 export 전체는 문맥에 재입력하지 않는다. 기존 save_reviewed_result(response_mode=receipt) → export_session도 호환한다. 실제 관측 호출만 record_usage로 남기고 전체 native usage라고 가정하지 않는다.

명시적 진행 중 취소는 새 업무 turn 없이 실제 대상의 현재 상태를 확인하고 cancel_turn(session_id/turn_id/cancel_key/reason/expected_result_version/user_submitted=true)을 호출한다. reason에 실제 취소 원문을 보존한다. 원문 기록이나 최종 응답을 위해 추가 followup turn을 만들지 않는다. 같은 취소 재생은 입력 그대로 유지한다. 후보·수정·usage 보존, 취소 뒤 저장/등록 금지, completed/failed 소급 취소 금지다. 최종 {cancellation,export}에는 실제 취소 대상 응답을 넣고 export의 대상 상태·후보 이력과 대조한다. 로컬 저장과 원격/native 실제 중단을 구분한다.

보고서 제작 실패는 업무 저장·수정 이력을 유지하고 같은 session_id/turn_id/expected_result_version의 deliver_result로 복구한다. 선택 report_plan_path/report_sources_path/open_folder를 전달한다. 복구를 새 업무 turn이나 기획 수정으로 세지 않으며 재생에서 기존 결과를 중복 생성·열기 하지 않는다. open_folder는 보고서 요청 시 기본 true이고 false로 생략할 수 있다. 실제 파일과 레이아웃 검수를 마친 후 결과 폴더를 연다.

실행: `uv run python .agents/skills/review-and-revise/scripts/run.py OP --input JSON_PATH`. OP: save_and_export/deliver_result/save_reviewed_result/export_session/current_request/get_turn/record_usage/cancel_turn. 단독 진단: validate_result_contract/review_product_result/start_turn/save_result/begin_invocation/finish_invocation. 장부는 Agent/Tool 실행·메시지·원격 취소를 대신하지 않는다.
