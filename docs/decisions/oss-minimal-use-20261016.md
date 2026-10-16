# 7개 저장소의 최소 활용 결정

2026-10-16. 개발용 하네스와 출품 상품기획 Agent를 교체하지 않는다. 운영 규모 확대나 다중 사용자 인프라를 채택 근거로 삼지 않았다. 다른 채팅의 추천 순위를 채택 결정으로 이어받지 않고 현재 코드·원문·실제 실행과 대조했다. 사용자 제공 수집 자료는 참고 원본이며 평가 결과는 [Y 실행 계약](../evaluation/quality-platform-Y-protocol-20261016.md)과 후속 실제 기록으로 판단한다.

| 저장소·확인 버전·조건 | 현재 연결점과 결정 |
|---|---|
| [ECC](https://github.com/affaan-m/ECC/tree/76aaa77df6adc5b889e689007bf99b9a4f74af34), MIT | `eval-harness`·`verification-loop`의 능력 평가/회귀 구분과 실제 검사 근거는 기존 evaluator·evaluate-harness·receipt와 겹친다. 기존 체계를 유지한다. 전체 역할·Hook·전역 설정을 중복 설치하지 않는다. |
| [Open Code Review](https://github.com/alibaba/open-code-review/tree/8eb8334), Apache-2.0 | 파일 목록·규칙·delegation 처리는 코드 검토용이다. staged/unstaged/untracked·rename/deletion을 빠뜨리지 않는 **검토 분모 방법**만 개발 `review-change`에 반영한다. CLI·의존성을 추가하지 않는다. 일부 처리나 exit0를 전체 코드 검토/상품기획 의미 검토 완료로 간주하지 않는다. |
| [agent-skills](https://github.com/addyosmani/agent-skills/tree/aeac41d4d005999432bb7312f7ff06383a91d59d), MIT | 디버깅의 원인 분리·재현/반증·수정 후 확인을 `implement-and-check`의 짧은 실패 절차에 반영한다. 관찰·브라우저 검수는 기존 실행 경로를 유지한다. 새로운 브라우저 자동화 설치나 접근 정책 우회는 하지 않는다. |
| [Claude Code](https://github.com/anthropics/claude-code/tree/03b5892), 자체 라이선스/이용 조건 | 기존 네이티브 실행기를 유지한다. `pr-review-toolkit`의 코드 예외·테스트 점검은 기존 reviewer와 겹치며 원문 의미를 인증하지 않는다. `feature-dev`의 반복 탐색/승인·다중 리뷰와 `plugin-dev`는 현재 제품 완료에 필요한 추가 흐름이 아니므로 설치하지 않는다. 이 저장소를 일반 MIT 코드 묶음으로 재배포하지 않는다. |
| [financial-services](https://github.com/anthropics/financial-services/tree/574ed36), Apache-2.0 | Market Researcher의 산업→기업 비교→투자 노트는 현재 제품 사용 불편의 판단과 거리가 있다. **도입 제외**. 산업/경쟁 축의 일반 방법은 기존 기능 비교로 충분하다. 기업 매출·거래배수·산업 성장률을 제품 모델 수요/판매량으로 바꾸지 않는다. 플러그인 다운로드는 금융·시장 데이터의 구독·접근권을 주지 않는다. |
| [knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins/tree/33eeda1e8fd856455b05479d13a0f85b5f803744), Apache-2.0 | 실제 `synthesize-research`·`competitive-brief`·`write-spec`와 가정/시험 방법을 기존 불편 구조화·기능 대조·콘셉트·검토에 대조했다. 핵심 가정의 반증과 첫 시험을 B로 비교했으나 **미채택·기존 업무 Skill 유지**. DW 쌍의 지침 전달 증거와 일관된 개선이 부족해 중단했다. FR-B에는 새6+1줄이 실제 반환됐다. [Y 결과](../validation/quality-platform-Y-20261016.md). 플러그인 전체·연결 서비스는 설치하지 않는다. |
| [Cursor plugins](https://github.com/cursor/plugins/tree/f713f14), 래퍼 MIT·각 플러그인/의존성 별도 조건 | Cursor 설치·실행을 추가하지 않는다. `cli-for-agent`·`agent-compatibility`의 파일 기반 CLI/설명·JSON 반환은 기존 Tool과 겹친다. 점수 산출을 실제 테스트 통과로 보지 않는다. Playwright/외부 MCP는 현재 도구 정책·인증·자료 접근을 해결하지 않으므로 도입 제외한다. Cursor 전용 등록/Hook 설정을 Codex·Claude 설정에 그대로 넣지 않는다. |

## 실제 반영과 채택 경계

개발 Skill의 절차는 독립적으로 다시 작성했다. upstream 코드·Skill 본문을 vendor하거나 새 실행 의존성을 설치하지 않았다. 기존 LICENSE/NOTICE를 삭제하지 않았으며 제품 ZIP에 개발 Skill이나 이 평가 문서를 넣지 않는다. 향후 실제 코드를 복사하면 별도 고정 파일 목록·수정 내역·LICENSE/NOTICE 검토가 필요하다.

개발 검사에서 발견한 **선택 검사 timeout/출력상한/미실행을 failed 하나로 축약하던 상태 변환**도 보완한다. 내부 장부의 허용 상태는 유지하면서 `receipt_status`에 원래 관측 상태를 보존하고 required 검사는 계속 거절한다. 이는 새 코드 리뷰 서비스를 도입한 효과가 아니라 현재 도구의 진단 정보 보완이다.

B의 중단/채택 기준은 Y 계약의4축·실제 원문·전달 퇴행 검사다. 긴 명세, 추가 질문, 반복 리뷰 또는 더 많은 Agent를 실행했다는 이유만으로 채택하지 않는다. 무료 파일 접근과 외부 유료 데이터/API 권한을 혼동하지 않으며, 이번 시험은 기존 유료 구독 실행기의 사용 범위 안에서만 한다.
