# 자연어·명시 Skill 호출 인수 — 2026-10-15

**자연어 업무를 기본으로 유지하면서, Codex와 Claude Code의 명시 Skill 호출을 실제로 확인했다.** 두 경로는 같은 6개 Skill과 공통 Tool을 사용한다. 메인 지침인 product-planning은 별도의 일곱 번째 Skill이 아니다. 필요한 역할만 native 서브에이전트로 위임하며, Skill과 Agent를 같은 개수로 세지 않는다.

AI의 대화 입력칸에는 다음처럼 입력한다. 터미널에서 실행할 셸 명령이 아니다.

| 용도 | Codex | Claude Code |
|---|---|---|
| 자동 선택 | `냉장고의 실제 후기를 살펴서 상품기획을 제안해줘.` | 같은 자연어 질문 |
| 근거 조회 명시 | `$evidence-retrieval 냉장고 등록 자료를 확인해줘.` | `/evidence-retrieval 냉장고 등록 자료를 확인해줘.` |
| 불편 구조화 명시 | `$needs-structuring 사용 조건과 상충 의견을 정리해줘.` | `/needs-structuring 사용 조건과 상충 의견을 정리해줘.` |
| 설치 Skill 목록 | `/skills` | `/` 뒤 설치된 Skill 이름 |

나머지 이름은 `web-evidence-collection`, `feature-comparison`, `concept-writing`, `review-and-revise`다. 매 질문에 이름을 붙일 필요는 없다. 자연어 요청을 해석한 메인이 필요한 지침과 기능을 선택한다. 공식 조사·후기 조사·근거 검토의 선택 역할도 필요성·native Tool·남은 시간에 따라 선택한다. Claude의 `@` subagent 선택 기능과 Skill 호출은 구분하고, Codex에는 확인되지 않은 `@agent` 문법을 만들지 않는다. 실제 선택기가 제공되지 않는 화면에서는 역할 이름을 자연어로 지정한다.

## 실제로 확인한 범위

- Codex CLI 0.162.0의 `$evidence-retrieval` 입력은 native 공개 user 기록에 전체 Skill 주입으로 이어졌다. 해당 본문이 설치 파일과 일치했다. `get_work_instructions` 1회가 main·evidence-retrieval·needs-structuring의 본문과 원본/반환 SHA·manifest SHA를 반환했다.
- Claude Desktop Code의 `/evidence-retrieval` 입력은 native의 command-message/name/args와 준비 질문을 정확히 대조했다. 실제 Skill 주입은 front matter를 제외한 설치 본문과 일치했다. wrapper의 `get_work_instructions` 실제 실행도 1회다. 원문/반환 SHA와 설치 파일이 일치했다.
- Codex에서 세 본문을 한 Tool 응답으로 받은 진단은 native 출력 상한으로 main 일부가 잘렸다. 두 Skill 본문은 전체가 남았다. Claude는 출력 미리보기 후 별도 Read로 main·needs-structuring 전체를 받았고, evidence-retrieval은 native 주입으로 받았다. 최초 미리보기나 파일 리다이렉트만으로 전체 독해를 인증하지 않았다.
- 두 진단 모두 실제 종료를 확인했고 설치 코드·전체 자료의 바이트는 바뀌지 않았다. 별도의 자연어 냉장고 업무도 실제 저장·최종 전달까지 종료됐고, 전체 56개 등록 원문을 보존한 독립 검토에서 핵심 요청을 충족했다. 모델/추론 비교와 다른 제품군의 인수는 별도 기록으로 정리한다.
- 자연어 공개 기록에서 Codex는 main·근거 조회·불편 구조화·기능 비교의 전체 본문 표시를 확인했다. 나머지는 파일 반환과 전체 재표시를 구분했다. Claude는 slash/Skill 주입 없이 필요한 지침을 선택했고, 최초 미리보기와 후속 Read를 대조해 현재 업무 지침 본문 범위를 확인했다. 자연어 자동 선택의 실제 동작 근거이며 모든 Skill이나 역할을 매번 강제한다는 뜻은 아니다.

`get_work_instructions`는 현재 필요한 본문만 선택해 전달한다. 같은 문맥·manifest·본문 지문이 이미 있다는 신고는 `already_in_context_reported`로 구분해 재반환을 생략한다. 문맥 압축으로 본문이 사라졌거나 문맥·버전이 달라지면 다시 전달한다. 본문 반환과 모델 이해를 자동으로 같은 사실로 인증하지 않는다. 실제 계약은 [지침 로딩](../contracts/instruction-loading.md)을 따른다. 전용 15개 검사와 [전체 로컬 CI](local-ci-20261015.md)를 통과했다.

고정 제품 manifest SHA-256은 `ec224fcfa37c73c65d2448a8c8f013ddd6dcde445ed38b056d38c4c6446223a8`다. 실제 native ID·원문 응답·설치 사본·지문·출력 잘림·별도 읽기 기록은 Git 밖 O 단계에 보존했다. 명시 호출 진단을 상품기획 성공률이나 모델 성능 비교 표본으로 섞지 않는다.

문법 근거: [OpenAI Skills](https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills), [Claude Skills](https://code.claude.com/docs/en/skills), [Claude subagents](https://code.claude.com/docs/en/sub-agents).
