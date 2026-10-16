---
name: feature-comparison
description: "원문으로 확인한 불편을 같은 정확 모델의 기존 기능·사용 조건과 대조해 남은 문제를 판단할 때 사용한다."
user-invocable: true
---

# 기존 기능 대조

## 호출 조건과 지침

자연어 요청의 자동 선택이 기본이며 Codex `$feature-comparison`(`/skills`), Claude `/feature-comparison` 명시 호출도 같은 업무 경로를 쓴다. 현재 업무 문맥에 같은 본문·지문이 없거나 문맥/버전이 바뀌면 판단 전에 `get_work_instructions`로 `feature-comparison`와 필요한 `main`만 선택해 실제 본문을 받는다.

이미 같은 지침이 문맥에 있으면 재독해하지 않고 동일 문맥·지문의 `known_context` 신고를 사용한다. 실행은 `uv run python skills/feature-comparison/scripts/run.py get_work_instructions --input runtime-data/instructions.json`이며 입력·증거 구분은 프로젝트 루트 `docs/contracts/instruction-loading.md`를 따른다.

반환 receipt는 코드 반환 근거이고 독해·적용·이해 인증이 아니다.

## 입력과 출력

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. exact 스펙을 우선하고 공용 설명서의 해당 부품/적용 모델을 확인한다. 각 pain을 제품 사실과 비교하여 resolved/partially_resolved/unresolved/uncertain과 원문 대조 이유를 적는다. 서로 다른 사용 조건을 합쳐 부분 해소를 단정하지 않는다.

existing_features/remaining_pains와 feature_matches를 작성한다. 불확실한 남은 문제는 확정 사실이 아닌 한계가 있는 조건부 기획 가설로만 다룬다. 물리 배치의 내부 치수 부족은 보류한다. 양식은 review-and-revise/references/payload.md다.

product_family는 catalog의 정확 모델과 일치해야 한다. 다른 제품군/모델의 기능·불편을 섞지 않는다. 용량 L, 식기 인원수, 외형 치수, 조리실/선반 유효 공간은 서로 대체하지 않는다. 안전 관련 사용법은 해당 모델 공식 안내를 근거로 하며 새로운 가열/세척 성능을 검증된 사실로 만들지 않는다.

## 절차와 실행

bundle 사실을 유지한다. 추가/잘림/문서 변경과 단독 실행 때만 정확 scope로 필요한 조회를 한다. 실행: `uv run python skills/feature-comparison/scripts/run.py OP --input JSON_PATH`. OP: match_product_scope/retrieve_product_facts/select_evidence. 의미는 네이티브 모델이 판단한다.

## 검토: 기능·해소·중복의 구분

조건 축약 점검: existing_features의 text 자체에 기능/안내의 적용 대상·사용 모드·설정·환경과 해당 분기를 가르는 조건을 남긴다. 원문의 조건부 조치를 일반 명령으로 바꾸지 않는다. 조건을 concept.assumptions에만 적어 기존 기능의 무조건적 요약을 정당화하지 않으며, 같은 조건을 feature_matches·remaining_pains·제안에 연결한다. 조건이 미확인이면 해소 여부도 그 범위에서 uncertain으로 둔다.

중복 검증 자료가 없으면 duplicates_existing=null이며 false로 확정하지 않는다. factual_summary의 분석 문구를 공식 문구로 인용하지 않는다. 원문 support_quote가 말한 사실만 제조사에 귀속하고, 기능이 불편을 완전히 해결하는지는 별도 AI 판단으로 표시한다.

기능 부재는 정확한 모델·부품·버전의 원문이 그 부재를 직접 명시한 범위에서만 사실로 적는다. 다른 기능의 부정 표기·목록 미등재·현재 발췌의 누락으로 대상 기능의 부재를 추론하지 않는다. 필요한 적용 범위/설명서/조작 안내를 확인하지 못하면 대상 기능 유무는 미확인이다. 기능 존재, 해당 사용 조건에서의 불편 해소, 제안 중복/제외는 각각의 근거와 AI 판단을 적고 하나의 결론으로 압축하지 않는다.

최종 표현에서도 연결한 각 원문이 주장 주어·대상·조건·비교절을 직접 지지해야 한다. 원문 미명시 위치·매체·조건은 unknown으로 유지하고 다른 후기의 조건을 옮기지 않는다. 기존 안내가 있어도 노출/이해 불편은 별도 근거가 필요하다. 검증은 대리 지표와 실제 과업 품질·오판·실패 탐지를 구분한다.

제품명·SKU·설명서 표지는 정체성·문서 적용만 지지하며 기능 증명으로 쓰지 않는다. 기능 판단에는 그 기능을 설명하는 정확 모델 본문을 연결한다. 미등록 관측을 등록 완료 근거로 대체하지 않고, 적용 조건/공용 FAQ 경고와 실제 기능 해소의 미확인은 uncertain/held 또는 조건부 한계로 유지한다.

## 완료·실패

국소 표현/검증 계획 보완과 핵심 근거 오류는 영향 범위를 구분한다. 전자는 보완 항목이며 그 자체로 업무 전체 실패를 뜻하지 않는다. 최종 전달은 현재 저장 버전의 completion_summary.text를 유지하고 새 사실·조건·매체를 추가하지 않는다.

## 명시 파일 출력

명시 파일 출력의 독자용 비교 표는 [보고서 작성](../review-and-revise/references/report-writing.md)을 따른다. 비교 항목·정확 모델·단위·조건을 맞추고 각 자료명/원문 링크를 연결한다. 원문 미기재와 기능 부재, 제안과 제조사 설명을 구별해 읽을 수 있는 문장으로 적는다.
