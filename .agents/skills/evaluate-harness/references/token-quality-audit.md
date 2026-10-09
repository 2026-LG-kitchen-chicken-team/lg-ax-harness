# 품질과 토큰 감사

같은 입력/모델/설정/성공 기준으로 baseline과 비교한다. 호출별 run_id, agent_id, parent_id, skill/tool, input/output/cache/reasoning usage, 실패/재시도/수정, 가격 기준일을 보존한다. 실행 전체 합계에는 부모·자식·실패 호출을 모두 넣는다. 모델이 알려주지 않은 항목은 unknown이며 일부 측정을 전체 측정으로 바꾸지 않는다. 필요 Skill만 로드하고 deterministic 조회·검사를 코드로 처리하되 근거 원문과 버전 필터는 유지한다. 절감 결과는 요구 충족률/근거 품질/전체 토큰·비용으로 평가한다. 사용자 300,000원은 계획 한도이며 개발 구독 usage와 출품 API 청구는 별도다.
