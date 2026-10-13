---
name: concept-writing
description: "실제 근거와 기존 기능 대조로 확인된 남은 불편에 대해 조건을 지키는 상품기획 콘셉트를 작성할 때 사용한다."
---

# 기획 초안

독자용 문서의 표현은 [보고서 작성](../review-and-revise/references/report-writing.md)을 적용한다. 컨셉·시연 이미지를 생성하거나 보고서에 삽입하지 않는다. 사용 장면과 개선안은 근거가 연결된 문장·표로 설명하고, 기획 가설과 실제 제품/효과를 구별한다.

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. 사용자 수량은 상한이며 근거가 부족하면 빈 안/보류를 허용한다. 각 concept은 remaining_pain·원문·제품 사실을 연결한다. 기존 기능 복제, 금지 행동/하드웨어, 미확인 기능 부재, 내부 치수·개선율 추정을 제외한다.

id/text/source_ids/requirements/requires_hardware/assumptions와 concept_links를 작성한다. 요구사항은 검증할 사용자 과업·측정 항목이며 달성 효과가 아니다. 조건부 기획이면 result와 concept의 assumptions에 미확인 귀속/기능 해소/중복 한계를 남긴다. 치수 의존성은 이 선언으로 우회하지 못한다. 양식은 review-and-revise/references/payload.md다.

요구사항에는 사용자가 수행할 행동과 관측 가능한 완료·실패 조건을 적는다. 개선한다/편리해진다는 표현만으로 완료 기준을 대신하지 않는다. 원문에서 확인하지 못한 작업 조건·효과는 기획/시험 가정으로 구분하고 실제 후기의 관측값으로 귀속하지 않는다.

각 concept에 implementation_steps(실행 주체/프로토타입/확인 순서)와 validation_plan을 추가한다. validation_plan 필드는 metric/baseline/method/success_criterion/business_value/status이고 status는 planned_not_measured만 허용한다. 기존 작업 대비 무엇을 측정할지, 같은 과업·완료 품질로 어떻게 비교할지 적는다. 숫자 목표는 가설로 명시하고 미측정 절감률을 실적처럼 쓰지 않는다. 제안서 예시에 없는 실제 불편도 처리하며 다른 제품군의 근거를 대신 쓰지 않는다.

validation_plan의 기존 baseline/method/metric/success_criterion 안에서 시험 전 고정할 사용자 과업·대상과 양·초기 상태·모델/버전·사용 환경/숙련 조건·완료 품질을 적는다. 기존 기능을 실제 사용한 대조 조건과 제안 적용 조건을 같은 과제/조건으로 비교한다. 반복 단위·분모·순서와 관측할 오류·추가 조작·회피·실패 검출 및 중단 기준을 명시한다. 만족한 사용자 경험·안전·장기/반례 조건의 악화를 성공으로 세지 않는다. 시험 후 유리한 조건만 고르지 않으며, 기준선 미측정은 측정 예정으로 두고 목표/표본은 사전 결정 또는 미정으로 표시한다. 서로 다른 조건/완료 품질을 개선률로 비교하지 않는다.

전체 업무의 최종 저장이 구조/refs/제약을 검사한다. 단독 실행·불일치 진단에는 validate_constraints/validate_source_refs를 실제 실행한다. 실행: `uv run python .agents/skills/concept-writing/scripts/run.py OP --input JSON_PATH`. 생성과 원문 검토는 네이티브 모델이다.

최종 표현에서도 연결한 각 원문이 주장 주어·대상·조건·비교절을 직접 지지해야 한다. 원문 미명시 위치·매체·조건은 unknown으로 유지하고 다른 후기의 조건을 옮기지 않는다. 기존 안내가 있어도 노출/이해 불편은 별도 근거가 필요하다. 검증은 대리 지표와 실제 과업 품질·오판·실패 탐지를 구분한다.
