---
name: needs-structuring
description: "확보한 실제 후기에서 현재 제품의 불편·사용 맥락·상충 의견을 원문 근거에 연결해 정리할 때 사용한다."
---

# 불편 구조화

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. 각 원문을 관측 불편/긍정/기대/이전 제품/불명확으로 분류하고 상충 의견·서로 다른 사용 조건을 보존한다. 페이지 연결 사례는 구매/정확 모델 확인과 구분하여 귀속 한계를 적는다. 불편이 없으면 빈 pains와 부족 사유이며 개수를 채우지 않는다.

pains의 id/text/source_ids와 claim_checks를 작성한다. literal 원문 지지와 모델 귀속·대표성의 불확실성을 분리한다. qualification 양식은 review-and-revise/references/payload.md에 있다. 판단은 네이티브 모델, 코드 검사는 구조만이다.

같은 후기의 문장도 실사용 관측/현재 사용 긍정/일반 선호/미래 기대를 나누어 적는다. 선호 속성의 실제 만족, 예상 기능의 실제 효과, 다른 수납부의 경험을 추론해 추가하지 않는다. 긍정이나 선호는 상충·한계 설명에 쓰며 그 자체를 pains로 채우지 않는다.

인용은 연속 원문 구간을 그대로 쓰며 떨어진 문장을 한 인용문으로 합치지 않는다. 증상과 함께 실제 기능 영향·발생 조건·회피 가능성·유보를 보존한다. 판단을 바꾸는 중간의 긍정·조건·유보는 생략하지 않는다. 확인하지 못한 문맥이 제안의 필요성·적용 범위에 영향을 주면 assumptions/qualification/decision_notes에 한계를 적고, 핵심 전제 근거가 부족하면 held로 남긴다. 빈도는 관측한 고유 후기 ID·자료 범위·분모와 함께 보고하고 독립 고객 수나 전체 발생률로 일반화하지 않는다.

정확한 bundle refs를 재조회하지 않는다. 누락/잘림/새 출처에만 select_evidence, 단독 실행·refs 변경·불일치 진단에는 validate_source_refs를 실제 실행한다. 전체 업무는 최종 저장이 검사한다.

실행: `uv run python skills/needs-structuring/scripts/run.py OP --input JSON_PATH`. OP: select_evidence/validate_source_refs.
