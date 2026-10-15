# product-v0.15.0 심사위원용 ZIP 배포 인수

2026-10-15 [시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.15.0)을 게시하고 main 제품 파일·원격 ZIP·checksum·자동 source ZIP을 실제 다시 내려받아 대조했다. [기계 기록](product-v0.15.0.json), [실제 업무/관찰/검사](integrated-judge-S-20261015.md), [사용자 테스트 안내](../contracts/judge-test.md)를 따른다.

- **심사위원 ZIP195파일**은 Codex/Claude 사전준비 폴더·업무 Skill6·선택 역할3·공통 Tool·결과/보고서 뷰어·별도 대시보드·설치 안내만 포함한다. 개발 체계·평가·원문 조사 자료·개인 DB/로그·인증·캐시·Node 빌드 도구를 제외했다.
- 원격 심사 ZIP SHA256 `ccf2386fb70f6f73692eb3b9f1cffd2ac7bba9e50c9276b9729513b30b16deb8`. 제품 소스 ZIP119파일과 SHA256SUMS도 로컬 원본과 같은 바이트다. GitHub 자동 Source ZIP119개도 원 바이트와 같다.
- 태그는 부모 없는 제품 snapshot `c85153b46ce08fda3b4aaa30e73647b6a9ae754e`이고 코드 provenance는 `3cf62939689aa21564b162ab8d2f855c30d32a66`다. PR9 main `d462bb924f55edc0629c4b0feaa5e5b85d761b9c`의 제품/설치89경로가 같은 Git blob이다. 기존 태그와 primary 발표자료 수정은 보존했다.
- 심사 ZIP을 새 폴더에 풀어 **원 레포 없이** 두 setup·무결성·viewer상태·Claude observer상태·실제 MXC sandbox9명령 exit0를 인수했다. 다운로드한 원격 asset은 원시 바이트가 그 로컬 시험 ZIP과 동일하다.

최종 local CI21/21·skip0, 실제 Codex5입력, 전체81본문·refs28, native 검토자 반환·보완2건·현재 결과/웹 파일·실제 관측결속2건은 별도 인수 기록과 범위를 맞췄다. 일반 helper를 Skill로 표시하지 않고 데이터/이력은 유지한다. 충분한 등록본문 재사용 검사를 고유고객·시장대표성·원페이지 전량·실물효과 인증으로 확대하지 않는다.

Claude 새 GUI 업무는 물리 Esc 중단으로 미발송이다. 브라우저 렌더/클릭·Codex 정상 hook trust는 사용자 단계이며 이번 코드·설치·파일 연결 성공에 포함하지 않는다. 원격 Actions와 로컬 CI를 구분하며 대회 발표/영상·최종 접수는 이 시험판 게시의 완료 항목이 아니다.
