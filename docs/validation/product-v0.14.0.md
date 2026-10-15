# product-v0.14.0 제품 전용 시험판 배포 인수

2026-10-14 [v0.14.0 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.14.0)을 게시하고 원격 제품 ZIP·체크섬·GitHub 자동 소스 ZIP을 다시 내려받아 대조했다. [기계 기록](product-v0.14.0.json), [M2 실제 품질/역할/웹 인수](quality-role-web-integration-20261014.md), [실제 코드 검사](quality-web-code-M2-20261014.md)를 따른다. 이전 시험판/태그는 보존했다.

- 제품 ZIP108파일·content manifest107항목·설치86파일·공통 업무 자산55개. 메인1·업무 Skill6·선택 역할3이며 기본 catalog는empty다.
- 원격 ZIP과 체크섬은 로컬 고정 후보와 같은 바이트다. 자동 소스 ZIP의108파일도 같은 원 바이트다. 제품 태그는 부모 없는 snapshot `8d5a26bb0607aec9bd94e795b1397eda3cadfcff`를 가리킨다.
- ZIP SHA256: `a67fc2649da93cce5d5295332860078d469ed850de93357dcacc41f413318a4e`.
- canonical manifest: `2275cdd7722ca7ff7d24aebbe520dcd2ac41bb7deb49a5ef4f49c89cee3e21ff`. 코드 provenance는 `48e907a5a61088908eb3a9e4ccad4265b45e19f2`다.
- 원격 대조 helper는 실제 exit0. 공개 기록에는 SHA/범위만 남기고 원 로그·자료·인증·개인 경로를 넣지 않았다. 개발 체계·평가 자료·별도agent-office는 제품 ZIP에서 제외했다.

현재 저장에서 최종 답변을 투영하고, 명시적 후속 질문의 이전 turn 연결과 취소 뒤 늦은 쓰기 차단을 보완했다. 기획자 화면·별도 보고서 HTML에 현재 전체 binding·웹 파일 SHA·저장 검토 gate를 적용한다. 전체 선택 원문·출처·조사/검토 이력을 전달하며 화면 렌더링은 일반 코드여서 추가 모델 호출0회다. 팀원 디자인을 유지했다.

제품443/443·웹105/105·자산55·개발 validate 실제 exit0 및 ZIP 설치/잠금 의존성/doctor 인수를 확인했다. M2의 정상/후속/선택 역할·미확인 치수·접근 거절·취소는 **ZIP과 같은 canonical 바이트의 격리 native 설치**에서 실행했다. 이 원격 ZIP을 새 native 업무로 실행한 것은not_run이며 CLI 인증·Desktop 실제 실행·doctorlocal_only의 범위를 구분한다. 보류·취소는 상품기획 해결 완료가 아니다.

Claude 부모 단독 A/F의 같은 국소 P2는 기록에 유지하고 선택 역할 결과의 실제 보완·반환·메인 반영을 인수했다. 전체 backend/자식 청구·의미 자동 인증·실물 효과·대표성·최종 대회 접수는 인증하지 않는다. 원격 CI는 계정 지출 한도로 미시작이다.

인수 PR10 head1576a6c2·PR11 head7c8e61b3 이력과 최소 연결은 `codex/evidence-complete`의 [PR9](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/9)에 반영했다. 마감 조회에서 PR10은34ec4a49까지8커밋 더 진행됐으며 그 새 화면/웹 연결 변경은 이 고정 시험판에 포함하지 않았다. main을 변경하거나 최신 PR10 전체를 인수했다고 설명하지 않는다. 다음 팀원 인계에서는 겹치는 웹 연결과 실시간 hook 검증을 우선한다.
