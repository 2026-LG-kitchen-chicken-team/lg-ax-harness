# 제안의 구현·검증 계획

이 문서는 시험 계획을 구체화하거나 누락을 보완할 때 읽는다. 구현 단계·검증 계획은 실제 업무 초안과 별개이며 “앞으로 만들어라”는 계획만으로 초안을 대신하지 않는다.

각 concept의 implementation_steps는 최대8개, 각1~1000자다. 첫 단계에 담당 역할·필요 입력·완료 산출물이 자연스럽게 드러나게 한다. 확정되지 않은 담당자 이름·성과를 만들지 않는다.

validation_plan은 metric/baseline/method/success_criterion/business_value/status 필드이고 status는 planned_not_measured만 허용한다. 같은 과업·모델/버전·대상과 양·초기 상태·환경/숙련·완료 품질에서 기존 기능을 실제 사용한 대조 조건과 제안을 비교한다. 목표 수치는 가설로 표시하며 실제 실적과 구별한다. 반복 단위·전체 사전 배정 시도에 실패·중단·포기·회피·미응답을 포함하고 미확인을 따로 남긴다. 시험 후 유리한 조건만 고르지 않는다.

선택 evaluation_protocol:{unit,failed_or_stopped,unknown}은 각1~1000자다. condition_controls는 고정할 조건1~10개(각1~1000자), guardrail_metrics는1~8개 {metric,method,non_regression_criterion}(각1~1000자)다. 과업 완료품질·오안내·실패 미검출·추가 조작·안전 악화를 개선 지표와 함께 판정하고 중단 조건을 적는다. 문의/반품 감소만으로 실제 고객 과업 품질을 대신하지 않는다.

이 상세는 기획 보완 항목이다. 구버전 누락은 읽기 호환하며 누락 자체로 전체 업무를 실패로 만들지 않는다. planning_quality_diagnostics는 structural_only/blocking=false인 필드 존재 진단이고 의미·실측 인증이 아니다. 미정 조건은 필요한 위치에 간결하게 남기되 일반 면책을 반복하지 않는다.
