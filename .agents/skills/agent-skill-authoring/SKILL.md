---
name: agent-skill-authoring
description: "배정된 개발 또는 출품 Skill의 호출 조건·지침·코드·Tool·단독 실행을 작성할 때 사용한다."
---

# agent-skill-authoring

하나의 업무와 호출 조건을 정의한다. 개발 Skill은 `.agents/skills/`, 출품 업무 Skill은 `skills/`에 둔다. SKILL.md에는 짧은 name/description과 핵심 절차를 쓰고 상세 계약은 필요한 참조로 옮긴다. 발견·본문 로딩·스크립트 실행은 서로 다른 증거다. 실제 코드/Tool 연결, 정상/예외 입출력과 단독 재실행을 검사한다. 필요한 참조만 로드하고 Skill을 별도 Agent처럼 늘려 표현하지 않는다.
