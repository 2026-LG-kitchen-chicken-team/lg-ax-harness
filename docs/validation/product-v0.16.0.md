# product-v0.16.0 심사위원 ZIP 배포 인수

2026-10-16 [시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.16.0)을 게시한 뒤 원격 asset·자동 Source ZIP·main 파일을 다시 내려받아 대조했다. [통합·실행 검사](judge-bundle-T-20261016.md), [기계 기록](product-v0.16.0.json), [심사위원 실행 안내](../contracts/judge-test.md).

- 심사위원은 **lg-ax-judge-product-v0.16.0.zip 하나**를 새 폴더에 풀어 사용한다. root README·judge.py·런처8개·codex/·claude/로 총205파일이다. 실행 결과·venv는 각 환경 폴더에 생성된다.
- 제품 소스128파일, 심사 ZIP205파일, SHA256SUMS의 원격 다운로드가 로컬 검증 원본과 raw byte 동일하다. 소스 ZIP에서 동일 심사 ZIP 재생성도 확인했다.
- GitHub 자동 Source ZIP도 제품 소스128파일과 raw byte 동일하다. 태그 `b124fc1ec5740f98e06a9e0c582858a8daefe9d6`는 부모0인 제품 snapshot이다. 개발 체계·평가/발표 자료·원본 로그·인증·DB·캐시는 포함하지 않는다.
- 개발 provenance `d47d36187ccd5a8e714ed76966824ee59fee8cc6`, PR15 main `d8df1347e1d96ab6fd022dabb7a9c06c81a06fc1`의 제품/설치 101경로가 같은 Git blob이다. 이전 릴리즈와 팀원 branch는 보존한다.
- 심사 ZIP SHA256: `fbbb473cdd281976bf7d1985256cdfbb924b082f51a32f2a4b8a42a3dde657a3`.
- 같은 ZIP의 Windows 로컬 CI21/21·ZIP단독준비11/11·실제 MXC를 통과했다. 실제 Codex 입력2건은 정상 Tool 호출1건과 필수 입력 누락 오류/중단1건으로 구분했다. 일반 실행·업무품질 성공2건으로 합산하지 않는다.

PR13/14는 PR15에 통합했다. PR10/11은 이미 인수한 구현과 후속 보완을 유지하고 오래된 PR을 정리했으며 PR7의 별도 서버 방식은 채택하지 않았다. branch 자체는 삭제하지 않았다. 실제 최종 상태와 head는 JSON에 기록한다.

Claude는 새 ZIP의 설치·훅·GUI prepare를 확인했다. 새 AI 업무·브라우저 렌더/클릭·실제 macOS/Linux 실행은 이번 검증 범위에 포함하지 않는다. 원격 Actions를 로컬 통과로 바꾸지 않는다. 발표·영상·대회 최종 접수는 별도다.
