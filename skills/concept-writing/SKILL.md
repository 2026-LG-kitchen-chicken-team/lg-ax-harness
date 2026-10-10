---
name: concept-writing
description: "실제 근거와 기존 기능 대조로 확인된 남은 불편에 대해 조건을 지키는 상품기획 콘셉트를 작성할 때 사용한다."
---

# 근거 기반 기획안

남은 불편이 없거나 불확실하면 제안 개수를 채우지 않는다. 각 후보는 remaining_pain_id와 실제 원문·제품 사실을 연결하고 최대3개 범위에서 작성한다.

기존 기능의 재제안·미확인 기능 부재 단정·내부 치수 추정·미측정 개선율을 제외한다. 하드웨어 허용 조건을 지킨다. 물리적 배치가 필요한 안은 실제 내부/부품 치수·적용 구조를 확보해야 한다. 확보하지 못하면 가정과 보류 사유를 남긴다.

ProductResult.concepts에 id/text/source_ids/requirements/requires_hardware/assumptions를 작성하고, [업무 검토 계약](../../docs/contracts/product-planning.md)의 concept_links로 남은 불편·기존 기능 중복·치수 필요성을 기록한다. 요구사항에는 검증할 사용자 과업과 측정 항목을 포함하되 달성 효과로 발표하지 않는다.

전체 업무는 `save_reviewed_result`가 구조·출처·제약을 최종 검사하므로 원문 refs를 변형 없이 사용한 중간 후보에서 같은 검사를 반복하지 않는다. Skill 단독 실행·refs/조건 불일치 진단·최종 저장을 연결하지 않는 작업은 `validate_constraints`와 `validate_source_refs`를 실제 실행한다. 검사를 생략한 중간 후보를 완료/검증 통과로 설명하지 않는다. 원문 의미 검토·assessment와 최종 저장 검사는 필수다. 실행: `uv run python skills/concept-writing/scripts/run.py OP --input JSON_PATH`. OP는 validate_constraints/validate_source_refs다. 생성은 네이티브 모델이 담당한다.
