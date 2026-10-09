---
name: harness-design
description: "출품 Agent·Skill·Tool의 상태·실행·예외·재시도·비용 계약을 설계하거나 바꿀 때 사용한다."
---

# harness-design

`docs/plans/product-harness.md`와 기술 결정을 읽고 실행 환경에서 실제 가능한 기능을 확인한다. 입력/출력/보류/완료/중단, Skill 호출 조건, Tool 입출력·근거·크기·timeout·retry·실패 경로를 정의한다. [Tool 계약](references/tool-contract.md)을 필요한 연결에 적용한다. 업무 수정 최대 2회와 기술 재시도·개발 turn 상한을 구분한다. 직접 API·다중 Agent·시각화는 업무 요구와 측정 결과가 필요할 때 제안한다. 계약을 검사할 정상·예외 입력과 실제 명령을 함께 정의한다.
