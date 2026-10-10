---
name: concept-writing
description: "실제 근거와 기존 기능 대조로 확인된 남은 불편에 대해 조건을 지키는 상품기획 콘셉트를 작성할 때 사용한다."
---

# 기획 초안

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. 사용자 수량은 상한이며 근거가 부족하면 빈 안/보류를 허용한다. 각 concept은 remaining_pain·원문·제품 사실을 연결한다. 기존 기능 복제, 금지 행동/하드웨어, 미확인 기능 부재, 내부 치수·개선율 추정을 제외한다.

id/text/source_ids/requirements/requires_hardware/assumptions와 concept_links를 작성한다. 요구사항은 검증할 사용자 과업·측정 항목이며 달성 효과가 아니다. 조건부 기획이면 result와 concept의 assumptions에 미확인 귀속/기능 해소/중복 한계를 남긴다. 치수 의존성은 이 선언으로 우회하지 못한다. 양식은 review-and-revise/references/payload.md다.

전체 업무의 최종 저장이 구조/refs/제약을 검사한다. 단독 실행·불일치 진단에는 validate_constraints/validate_source_refs를 실제 실행한다. 실행: `uv run python skills/concept-writing/scripts/run.py OP --input JSON_PATH`. 생성과 원문 검토는 네이티브 모델이다.
