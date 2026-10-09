---
name: harness
description: "Codex 중심 개발 작업을 분해하고 네이티브 위임·검사·독립 리뷰·인수인계를 연결한다. 개발 체계를 구축하거나 이 레포의 실질 구현을 진행할 때 사용한다."
---

# harness

요구 원본, 기술 결정, 작업 목록, git status/diff를 먼저 읽는다. 필요한 역할만 선택하고 메인이 의존성·공통 계약·통합을 관리한다.

[실행 계약](references/project-workflow.md)을 읽고 작업 입력·지문·소유 파일·Skill·검사 명령·시간/호출 상한을 배정한다. 실제 네이티브 도구가 custom role을 지원하면 선택한다. 지원하지 않으면 `.codex/agents/<role>.toml`의 developer_instructions와 필요한 Skill·작업 packet을 생성 메시지에 전달한다. 이 fallback은 TOML의 sandbox/모델 설정을 자동 적용하지 않는다. 읽기 전용 역할은 변경하지 않고 부모가 결과를 기록한다.

작은 작업은 직접 처리한다. 실질 병렬 작업은 읽기 전용부터 배정하고 같은 checkout에 한 작성자만 둔다. 병렬 쓰기는 독립 worktree에서 한다. 실제 반환 ID만 등록하고 idle 세션을 재사용한다. runtime에 close가 없으면 interrupt를 close로 기록하지 않는다.

장부는 Agent를 실행하지 않는다. 네이티브 생성·메시지·관찰 후 [upstream 실행 안내](references/runtime-guide.md)의 장부에 연결한다. 실제 검사와 receipt 확인은 `python dev-harness/cli.py check` 및 `ledger result`로 수행한다. 통합 diff·실행 검사·독립 리뷰를 확인하고 완료/남은 항목을 보고한다.

필요한 역할/Skill만 읽어 문맥을 줄인다. 토큰 감사는 evaluator의 evaluate-harness 모드로 맡긴다. Tool 호출 설계는 harness-design을 사용한다. 시각화는 현재 후순위다.
