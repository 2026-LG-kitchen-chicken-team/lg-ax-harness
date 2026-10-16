---
name: concept-writing
description: "실제 근거와 기존 기능 대조로 확인된 남은 불편에 대해 조건을 지키는 상품기획 콘셉트를 작성할 때 사용한다."
user-invocable: true
---

# 기획 초안

## 호출 조건과 지침

자연어 요청의 자동 선택이 기본이며 Codex `$concept-writing`(`/skills`), Claude `/concept-writing` 명시 호출도 같은 업무 경로를 쓴다. 현재 업무 문맥에 같은 본문·지문이 없거나 문맥/버전이 바뀌면 판단 전에 `get_work_instructions`로 `concept-writing`와 필요한 `main`만 선택해 실제 본문을 받는다.

이미 같은 지침이 문맥에 있으면 재독해하지 않고 동일 문맥·지문의 `known_context` 신고를 사용한다. 실행은 `uv run python skills/concept-writing/scripts/run.py get_work_instructions --input runtime-data/instructions.json`이며 입력·증거 구분은 프로젝트 루트 `docs/contracts/instruction-loading.md`를 따른다.

반환 receipt는 코드 반환 근거이고 독해·적용·이해 인증이 아니다.

## 입력과 출력

단독 실행이면 프로젝트 루트 agents/product-planning.md의 공통 안전 규칙을 먼저 읽는다. 이미 문맥에 있으면 유지한다. 사용자 수량은 상한이며 근거가 부족하면 빈 안/보류를 허용한다. 각 concept은 remaining_pain·원문·제품 사실을 연결한다. 기존 기능 복제, 금지 행동/하드웨어, 미확인 기능 부재, 내부 치수·개선율 추정을 제외한다.

id/text/source_ids/requirements/requires_hardware/assumptions와 concept_links를 작성한다. 요구사항은 검증할 사용자 과업·측정 항목이며 달성 효과가 아니다. 조건부 기획이면 result와 concept의 assumptions에 미확인 귀속/기능 해소/중복 한계를 남긴다. 치수 의존성은 이 선언으로 우회하지 못한다. 양식은 review-and-revise/references/payload.md다.

## 절차: 요구사항과 구현·검증 계획

절마다 대상·조건·시점·매체를 같은 연결 source 원문과 대조한다. 명시하지 않은 속성·장소·인과는 AI 해석/미확인으로 남긴다. 제안한 과업·작동 장소·효과를 후기나 제조사의 관측 사실로 귀속하지 않는다.

요구사항에는 사용자가 수행할 행동과 관측 가능한 완료·실패 조건을 적는다. 개선한다/편리해진다는 표현만으로 완료 기준을 대신하지 않는다. 원문에서 확인하지 못한 작업 조건·효과는 기획/시험 가정으로 구분하고 실제 후기의 관측값으로 귀속하지 않는다.

각 concept에 implementation_steps(실행 주체/프로토타입/확인 순서)와 validation_plan을 추가한다. validation_plan 필드는 metric/baseline/method/success_criterion/business_value/status이고 status는 planned_not_measured만 허용한다.

기존 작업 대비 무엇을 측정할지, 같은 과업·완료 품질로 어떻게 비교할지 적는다. 숫자 목표는 가설로 명시하고 미측정 절감률을 실적처럼 쓰지 않는다.

제안서 예시에 없는 실제 불편도 처리하며 다른 제품군의 근거를 대신 쓰지 않는다.

## 검토: 조건·분모·품질

validation_plan의 기존 baseline/method/metric/success_criterion 안에서 시험 전 고정할 사용자 과업·대상과 양·초기 상태·모델/버전·사용 환경/숙련 조건·완료 품질을 적는다. 기존 기능을 실제 사용한 대조 조건과 제안 적용 조건을 같은 과제/조건으로 비교한다.

반복 단위·순서·사전 배정한 전체 시도와 실패·중단·포기·회피·미확인 처리를 구체화한다. validation_plan의 선택 evaluation_protocol:{unit,failed_or_stopped,unknown}에 짧게 보완할 수 있다.

상세 분모/처리 계획은 업무 개선 항목이며 생략만으로 기존 조건부 초안을 일괄 실패로 만들지 않는다. 실제 과업 완료품질·오판·실패 미검출과 추가 조작·안전 악화·중단 기준을 함께 판정한다.

만족한 사용자 경험·안전·장기/반례 조건의 악화를 성공으로 세지 않는다. 시험 후 유리한 조건만 고르지 않으며, 기준선 미측정은 측정 예정으로 두고 목표/표본은 사전 결정 또는 미정으로 표시한다.

서로 다른 조건/완료 품질을 개선률로 비교하지 않는다.

선택 condition_controls는 시험 전에 고정할 조건 설명 배열이고, guardrail_metrics는 {metric,method,non_regression_criterion} 배열이다. 전체 사전 배정 시도에 실패·중단·미응답을 포함하고 미확인을 따로 남긴다.

오안내·완료품질 저하·실패 미검출을 개선 지표와 함께 비교한다. 기존 기본 필드·evaluation_protocol은 호환하며 새 필드 없이도 조건부안을 저장할 수 있다.

planning_quality_diagnostics의 scope=structural_only/blocking=false는 필드 누락 안내다. 필드 존재는 계획 타당성·실측 인증이 아니다.

최종 표현에서도 연결한 각 원문이 주장 주어·대상·조건·비교절을 직접 지지해야 한다. 원문 미명시 위치·매체·조건은 unknown으로 유지하고 다른 후기의 조건을 옮기지 않는다. 기존 안내가 있어도 노출/이해 불편은 별도 근거가 필요하다. 검증은 대리 지표와 실제 과업 품질·오판·실패 탐지를 구분한다.

## 완료·실패와 실행

전체 업무의 최종 저장이 구조/refs/제약을 검사한다. 단독 실행·불일치 진단에는 validate_constraints/validate_source_refs를 실제 실행한다. 실행: `uv run python skills/concept-writing/scripts/run.py OP --input JSON_PATH`. 생성과 원문 검토는 네이티브 모델이다.

국소 표현/검증 계획 보완과 핵심 근거 오류는 영향 범위를 구분한다. 전자는 보완 항목이며 그 자체로 업무 전체 실패를 뜻하지 않는다. 최종 전달은 현재 저장 버전의 completion_summary.text를 유지하고 새 사실·조건·매체를 추가하지 않는다.

## 명시 파일 출력

명시 파일 출력의 독자용 문서 표현은 [보고서 작성](../review-and-revise/references/report-writing.md)을 적용한다. 컨셉·시연 이미지를 생성하거나 보고서에 삽입하지 않는다. 사용 장면과 개선안은 근거가 연결된 문장·표로 설명하고, 기획 가설과 실제 제품/효과를 구별한다.
