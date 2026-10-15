# LG AX Claude Code 상품기획

@AGENTS.md

현재 업무 재개는 active-workflow의 원래 handle/request/research_id를 사용한다. 사용자가 새 후속 업무를 명시하면 open_product_workflow에 같은 business session_id, 이전 실제 prior_turn_id, 새 question 원문과 새 request_key를 전달하고 반환된 후속 handle을 현재 업무로 유지한다. 이전 완료 결과·수정 횟수·finish 시계는 역사적 참조이며 새 문맥의 valid 여부와 구별한다. 실패/timeout 때문에 같은 업무를 새 request/turn으로 만들거나 기존 시계를 초기화하지 않는다.

업무 Skill은 이 프로젝트의 `.claude/skills/`다. 실제 발견·적용 경로를 확인한다. 개인·관리 Skill과 이름이 충돌하면 자동으로 동일 지침이 적용됐다고 가정하지 않는다.
Claude 자신의 모델·Tool을 사용하고 Codex 또는 다른 모델을 내부 실행하지 않는다. 허용된 셸에서 Python wrapper를 호출한다. 프로젝트 지침은 실행 권한을 강제하지 않는다.
이 설치 사본의 native 발견·대화·보류·오류·사용량 검증은 아직 미완료다. 설정·권한·로그인을 자동 우회하지 않는다.

현재 결과의 최종 전달은 completion_summary.text를 유지한다. 선택 역할의 작업 시계는 실제 native 생성 응답 시각부터 최대180초이며 전체deadline의 최종90초를 남긴다. reviewer는 불변 원문 JSONL/후보 주장을 읽고 시작 ack와 compact findings를 우선한다. 긴 평가보고서나 파일을 요구하지 않는다. 접근 실패는 원URL의 관측 실패와 영향으로 알리고 상세 오류 파일 방문을 요구하지 않는다. 이 지침은 실제 권한/중단/독해를 자동 인증하지 않는다.

자연어 요청에 맞는 Skill 자동 활성화가 기본이다. `/evidence-retrieval`, `/needs-structuring`, `/review-and-revise` 등 설치된6개 이름의 명시 호출도 같은 업무 경로다. `@` subagent 선택은 `.claude/agents`의 선택 역할이며 Skill과 다르다. 현재 문맥에 필요한 본문이 없으면 `get_work_instructions`로 선택 지침만 받고, 동일 문맥/지문은 known_context 신고로 재독해를 생략한다. 반환과 이해·적용은 구분한다.
