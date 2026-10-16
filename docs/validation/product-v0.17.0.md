# product-v0.17.0 배포·원격 바이트 인수

2026-10-16. [제품 설치·배포 저장소](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/tag/product-v0.17.0)와 [개발 저장소의 제품 릴리즈](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.17.0)에 시험판을 게시했다. 두 저장소는 비공개 상태를 유지하며 기존 product-v0.16.4 파일·태그는 보존했다. 공개 예약과 최종 대회 접수를 수행한 기록이 아니다.

| 파일 | 범위 | SHA256 |
|---|---|---|
| lg-ax-judge-product-v0.17.0.zip | 사용자가 받을 ZIP 하나·209파일·각 엔진99 | 780087faaeccadbb2614b60f58100cea5c2159b6f3432d814c3118b7f779012d |
| lg-ax-harness-product-v0.17.0.zip | 제품만의 재현용 원본130파일 | b67bcf5b396b6ffe8c7d0cd028ec9e1522355b7418cbb1b5c2603c4859ea8fa2 |
| SHA256SUMS.txt | 첨부 ZIP 두 개의 체크섬 | 7e4fe923805d2b013e21b7364d53bf017d3d934170871558b24b2df8690042d6 |

제품 원본93feec8a9085c353ef0722d76d35c533cfd56163에서 만든 부모 없는 스냅샷1784fc0a49e8e2050909da2b2db174424194dd54를 두 제품 태그에 연결했다. 두 저장소의 원격 tag 대상과 첨부 세 파일을 다시 내려받아 SHA·GitHub digest·크기를 대조했다. GitHub 자동 Source code ZIP도 디렉터리 항목을 제외한130개 실제 파일의 경로와 원바이트 SHA가 제품 source ZIP과 같다. 개발 이력·평가 원문·로그·DB·인증·의존성 캐시는 제품 태그/ZIP에 없다.

새 ZIP 단독 check→Codex setup→Claude setup→check 네 명령 exit0, 로컬 CI21/21단계 및 native/의미 품질의 실제 범위는 [Z 실행 인수](result-delivery-Z-20261016.md)를 따른다. 코드 검사925통과·1조건skip을 네 native 환경의 첫 시도 전부 성공으로 설명하지 않는다.

배포 저장소의 README와 agent.md는78b2223c56a7ac2e8aa187d3b9675a9e0ef846d0에서 현재 제품 버전을 명시하도록 갱신했다. installer-v0.1.2의 고정 코드·지문·과거 기본값은 바꾸지 않았다. 실제 README의 PowerShell 한 줄 명령을 `-Version product-v0.17.0`과 새 대상 폴더로 실행해 인증 다운로드·209파일 지문 확인·Codex 준비 완료(`prepared:true`)를 확인했다. 모델 입력0, 기존 파일 덮어쓰기0, 실행 정책 변경0이다. 다운로드한 `.ps1`을 직접 `-File`로 실행한 최초 진단은 Windows 실행 정책으로 막혔고, 그 실패는 보존했다. 안내된 인라인 명령과 파일 실행을 같은 결과로 취급하지 않는다.

현재 PR의 GitHub Actions Windows job은 steps0에서 실패했다. 실제 annotation은 계정 결제 실패 또는 사용한도 상향 필요라는 내용이었다(run38885157728/job116921006601). 설정이나 계정 한도를 바꾸지 않고 로컬 CI의 실제 결과를 사용했다. 이 Windows 시험으로 macOS/Linux의 실제 native 실행이나 브라우저 육안 검수를 인증하지 않는다.

기계 판독 결과는 [배포 JSON](product-v0.17.0.json), 발표·영상에 쓸 장면/수치는 [제작 인수](../plans/result-delivery-demo-evidence-20261016.md)에서 확인한다. 촬영은 수행하지 않았다.
