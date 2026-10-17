---
name: concept-writing
description: "실제 불편과 기존 기능 대조를 종합해 후보의 차이·선택 이유·편집 가능한 상품기획 초안을 작성할 때 사용한다."
user-invocable: true
---

# 상품기획과 실제 초안

## 호출과 입력

자연어 요청에 맞춰 자동 선택하며 Codex `$concept-writing`(`/skills`), Claude `/concept-writing`도 같은 경로다. main·이 Skill의 현재 본문이 없을 때만 get_work_instructions로 필요한 ID를 받는다. 같은 문맥·지문은 known_context로 재사용한다. 발견·본문 반환·실제 적용은 서로 다른 기록이다. 단독 실행은 main의 공통 규칙을 먼저 확인한다.

사용자 목적·남은 불편·정확 모델의 원문/제품 사실·기존 기능 대조를 입력으로 사용한다. 자료 폭·긍정/상반 경험을 줄이지 않는다. 특정 제품·질문의 정답을 선택하지 않는다.

## 작성

1. 고객 문제와 바뀌는 행동이 직접 연결되는 후보만 작성한다. 최대3개는 상한이며 약한 안으로 채우지 않는다. 기존 기능 복제·미기재를 기능 부재로 단정·금지 행동은 제외한다.
2. 일반 구체화 요청은 착수안 하나를 선택하고 이유·차이를 짧게 적는다. 사용자 선택을 우선하고, 비교만 요청하면 선택/초안을 생략할 수 있으며 복수 구체화 요청은 존중한다. result.planning_decision은 후보 비교·선택 이유다.
3. 선택안에는 실제 수정해 쓸 concept.work_draft를 작성한다. 요구사항표·서비스 흐름·질문표·기록 양식 등 요청에 맞는 본문을 제공하며 “추후 만들 것” 목록만으로 끝내지 않는다. 유형은 예시이며 세 제품군의 고정 양식이 아니다.
4. 관측 사실은 연결 원문으로, 새 설계는 제안으로, 후기 기반 예시는 예시로 자연스럽게 쓴다. 모르는 내부 담당자·기한·수치·효과를 사실로 채우거나 승인된 회사 양식으로 표시하지 않는다. 새 설계가 원문에 그대로 없다는 이유만으로 금지하지 않는다.
5. 제안과 한 문장 설명 → 고객 문제 → 의미 있는 차이 → 실제 초안 → 다음 행동 순으로 읽게 한다. 반복 일반 면책·자기 지시문·내부ID·JSON·검사 배지는 본문에 넣지 않는다. 필요한 모델 식별·조작 지원·치수·안전 조건은 해당 행동 가까이에 짧게 남긴다. 실제 근거가 없으면 불가능한 판단과 필요한 자료만 구체적으로 알리고 작성 가능한 부분은 제공한다.

새 요청은 하드웨어·서비스·UX를 함께 검토할 수 있다. 명시 hardware_allowed:false·제외조건·후속 상속은 지킨다. 치수/안전 근거 없이 실현성·물리 적합성을 단정하지 않는다. 외형 치수를 내부 치수로 쓰지 않는다.

제안의 text에도 핵심 적용 조건을 남긴다. 사건 순서·부정 범위를 보존하고 중요한 조건을 assumptions에만 숨기지 않는다.

공통 조사 범위와 대표성·효과 미측정 설명은 전체 조건에서 한 번 정리한다. 비교 요약은 하는 일, 선택 이유는 착수 근거, 고려할 점은 결정을 바꾸는 조건으로 나누어 같은 면책 문장을 반복하지 않는다. 제안 설명의 핵심 조건과 실제 초안의 확인 입력 칸은 유지한다.

## 결과와 검토 연결

concept의 id/text/source_ids/requirements/requires_hardware/assumptions와 concept_links를 유지한다. 각 제안에 implementation_steps와 validation_plan을 작성하고, 첫 단계는 담당 역할·필요 입력·완료 산출물을 분명히 한다. 행동·완료/실패 기준을 requirements에 적고, 선택안의 실제 초안은 실행·시험 계획과 구별한다. 세부 작성 시 [구현·검증 계획](references/validation-plans.md)을 읽는다. 결과의 정확한 크기·구조는 프로젝트 루트 [업무 초안 계약](../../docs/contracts/planning-drafts.md), 저장 양식은 review-and-revise/references/payload.md를 따른다.

같은 턴에서 기존 선택 planner_insights:{concept_titles:{콘셉트ID:"짧은 이름"},summaries:{현재항목ID:"한 문장"}}를 작성한다. 제목은 구별점, 요약은 대상·상황·변화를 적고 원문의 부정·사건 순서·조건을 보존한다. 새 사실/효과를 추가하지 않는다. 실제 work_draft와 planning_decision은 result 내부에 넣어 검토·저장하고 planner_insights로 우회하지 않는다. 화면용 별도 모델 호출은 추가하지 않는다.

의미 판단·새 초안 작성은 네이티브 모델의 일이다. 단독 구조 진단은 `uv run python skills/concept-writing/scripts/run.py OP --input JSON_PATH`의 validate_constraints/validate_source_refs, 전체 업무는 기존 review-and-revise 검토→save_and_export를 사용한다. 실제 스크립트 실행과 Skill 읽기를 구분한다.

## 마감

작성·압축 뒤 각 사실 절의 주어·대상·조건·시점·매체가 같은 원문에 있는지 확인한다. 다른 후기의 조건을 옮기거나 제안을 제조사 사실로 귀속하지 않는다. 핵심 전제 오류와 국소 표현/계획 보완의 영향을 구분한다. 저장된 같은 버전의 completion_summary.text와 실제 웹/보고서 경로를 전달한다. 파일 출력을 명시한 경우에만 기존 [보고서 작성](../review-and-revise/references/report-writing.md)을 적용하며 컨셉 이미지는 생성하지 않는다.
