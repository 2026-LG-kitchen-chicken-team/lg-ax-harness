# 제품 v0.3.0 배포 확인 — 2026-10-11

세 제품군의 의미 있는 제품 변경으로 [product-v0.3.0 prerelease](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.3.0)를 발행했다. main 구현/자료/발표 초안 commit은 `600a06193f1ee9d9e7ff446824d8ee905bed8a9a`다. 아래 제품 snapshot과 이후 발행 확인 문서 commit은 별도다.

## 실제 제품 파일과 원격 확인

- 첨부: `lg-ax-product-v0.3.0-codex-source.zip`와 `SHA256SUMS.txt` 두 개만이다. ZIP SHA256 `73e66f09d7d0d075400a2ce1d7be01a7227385b53920c1fc1c5c5abc1552f3d5`.
- ZIP68파일/manifest67의 CRC·개별 SHA·새 추출·uv locked·공통 Tool doctor·ZIP 원본만으로 Claude 새 폴더 재설치를 확인했다. installer metadata는 local_only이며 Claude native 발견/로그인/업무 완료를 뜻하지 않는다.
- 제품 태그의 부모 없는 snapshot commit은 `b71acaa07573a0f24dbfbea0790f44a983f2a48b`, tree `a7160260875c9bd5654e050bbc6780a6ff4a38e2`다. 모든 Git blob byte가 ZIP과 일치하며 부모 commit이 없어 개발 이력이 들어가지 않는다.
- 원격 태그 commit·Git tree68파일을 조회하고 두 첨부물을 다시 내려받았다. 로컬/다운로드 byte, 두 asset의 크기·SHA digest·ZIP SHA 모두 일치했다.
- 6Skill 전체 폴더·업무 Agent/공통 코드·실제 v4 자료·잠금 파일·README·필수 LICENSE/NOTICE를 포함한다. 개발 체계·평가 입력/runner·관찰 프로그램·웹·원문 실행 로그/DB/인증·의존성 환경·발표 검토 초안은 제외했다. GitHub의 자동 Source code ZIP과 제품 첨부 ZIP을 구분한다.
- 실제 실행 없이 파일을 재포장하거나 전 환경 지원으로 설명하지 않는다. Gemini 설치/패키징은 제거됐으며 기존 외부 사본/실패 이력은 보존했다.

## 검사·검토와 한계

[구현·실제4입력·평가항목 대조](kitchen-progress-20261011.md)와 [자료 한계](../data/kitchen-v4.md)를 따른다. 제품135·평가 실행기90개 검사 exit0, 자산/Claude 파일 설치/소스ZIP/발표 계획 검사와 현재 입력·로그 SHA를 확인했다. frozen4입력/3세션·최종 저장/전달·K01 최초 거절/수정1회·불변 이력·사용량 원본은 유지했다. 알려진 원문에 대한 독립 의미7축14/14는 일반 정확도·실물/시장/효과를 인증하지 않는다. 최종 manual family 경계는 native freeze 이후 fixture 검사 범위다.

독립 reviewer `/root/seven_final_review`가 packet40입력 지문, 현재7receipt, ZIP/원문/export/DB/usage/발표 주장을 대조하고9읽기/guard 명령 exit0·추가 blocker 없음·write/native/API/cloud0을 보고했다. `kitchen-review-20261011`의 bound guard receipt `0c152dbb4a964d818f92d458011eadce`와 완료 검사 `errors=[]`를 관측했다. 이 checkpoint 뒤 문서에는 배포 결과/사용자 연락처 지시만 추가했고 제품 파일/ZIP은 변경하지 않았다. 개발 사용량은 unknown다.

발표 검토 초안12쪽 PPTX/독립 HTML·계획525초를 만들고 PPTX import/전체12쪽 render, 편집 가능한 표2개/차트1개·workbook·글꼴/구조를 검사했다. 브라우저에서 HTML12section·다음 이동과 오류 로그0을 확인했다. 실제 PowerPoint 재생·시연 녹화·리허설은 미실행이다. 발표 초안은 main에 있고 제품 릴리스에 넣지 않았다.

main `600a061`의 원격 [CI 실행](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38128105828)은 failure다. 계정 결제/지출 제한으로 작업이 시작되지 않았다는 annotation·steps0을 확인했으며 로컬225검사 통과와 구분한다. 계정 결제를 변경하지 않았다.

## 다음 인수

1. Claude: 하네스 보완 완료 후 최길웅에게 새 제품 설치/4개 입력 검증 메일을 사용자 초안 승인 후 실제 발송하고 SENT·수신/회신 헤더를 확인했다. 원본 결과는 정이량에게 메일 회신받는다. 현재 결과 회신/native 인수는 미완료다. 접근 불가 시 새 결제 없이 후순위다. 팀원 개발 체계 D06b와 출품 업무 검증은 별개다.
2. 실제 두 창30초 녹화→입력/판단/Skill·Tool/결과 시연 영상→실측10분 리허설. native Windows 녹화 제어를 이번 도구 환경에서 실행하지 못해 영상 인수는 미완료다.
3. 이미 요청한 사람 실제 공수/원본과 웹팀 구현 원본을 받아 동일 과업/표시 계약을 각각 검토한다. 웹팀 개발 중/원본 미수신을 구현 완료로 바꾸지 않는다.
4. 운영진 실제 마감/경로/영상 규격/가산점 확정 공지 확인→최종 버전 동결·새 실행자 재현→업로드/접수 확인.

신진하의 향후 팀 메일은 사용자 지시에 따라 기존 발신 헤더에서 확인한 Gmail로 고정했다. 개인 수신 설정·draft ID는 Git 제외 로컬 연락처/메일 기록에 저장하고 과거 네이버 발송 기록은 보존한다. 이미 보낸 메일을 자동 재발송하지 않았다.
