---
name: feature-comparison
description: "원문으로 확인한 불편을 같은 냉장고 모델의 기존 기능·사용 조건과 대조해 남은 문제를 판단할 때 사용한다."
---

# 기존 기능 대조

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. exact 스펙을 우선하고 공용 설명서의 해당 부품/적용 모델을 확인한다. 각 pain을 제품 사실과 비교하여 resolved/partially_resolved/unresolved/uncertain과 원문 대조 이유를 적는다. 서로 다른 사용 조건을 합쳐 부분 해소를 단정하지 않는다.

existing_features/remaining_pains와 feature_matches를 작성한다. 불확실한 남은 문제는 확정 사실이 아닌 한계가 있는 조건부 기획 가설로만 다룬다. 물리 배치의 내부 치수 부족은 보류한다. 양식은 review-and-revise/references/payload.md다.

bundle 사실을 유지한다. 추가/잘림/문서 변경과 단독 실행 때만 정확 scope로 필요한 조회를 한다. 실행: `uv run python .agents/skills/feature-comparison/scripts/run.py OP --input JSON_PATH`. OP: match_product_scope/retrieve_product_facts/select_evidence. 의미는 네이티브 모델이 판단한다.
