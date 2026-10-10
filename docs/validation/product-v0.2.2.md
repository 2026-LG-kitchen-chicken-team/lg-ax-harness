# 제품 v0.2.2 시험판 배포 검증

2026-10-11 KST. [제품 v0.2.2](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.2)는 웹 preview/조사 지침의 실질 변경을 검사·독립 리뷰한 시험판이다. 공식 최종 제출·전 환경 지원 완료가 아니다. 상세 업무 평가와 열린 항목은 [9입력 기록](focused-progress-20261011.md)을 따른다.

| 항목 | 확인한 값 |
|---|---|
| main provenance | `ed693b87af630ef8ea310ccdc91cd1b45f071eaa` |
| 제품 태그의 실제 commit | `c1163514642f7c76b4dac9cfcd4976b9373010d6` |
| 제품 tree | `1a357dcbaaf68b20baaab89dc191a0bd643586f9` |
| ZIP | `lg-ax-product-v0.2.2-codex-source.zip` ·124,173bytes |
| ZIP SHA256 | `7a46c2b1278a6b883fbbd77fc71f8c94d5544e6b051a72d760791e9d21dabfea` |
| 파일 |70개 ·제출 manifest69개 SHA/CRC 일치 |
| GitHub 상태 |draft=false ·prerelease=true |

ZIP과 제품 Git tree의 모든 경로·원본 byte가 같고 snapshot commit에 부모가 없음을 확인했다. 원격 태그 peeled commit도 같은 값이며 GitHub의 재귀 tree는 잘림 없이70개 제품 파일이다. 따라서 자동 Source code도 개발 체계를 제외한 제품 스냅샷이다. 업로드 뒤 ZIP과 SHA256SUMS.txt를 새 로컬 폴더로 내려받아 지문/byte를 재확인했으며 GitHub asset digest도 일치한다.

LICENSE/NOTICE·잠금 파일·공통 업무 Agent/Skill·코드·v3 실제 자료·세 adapter/설치 안내를 포함한다. 개발 역할/Skill·평가/사람 측정 도구·팀 보고서·원본 로그·SQLite·관찰 설정·메일/인증·의존성 환경은 제외한다. 추가 청소 긍정 catalog는 별도 연구 기록이며 기본 v3를 변경했다고 설명하지 않는다.

현재 관련 로컬 검사는 제품119+evaluation86=205개, assets·새 ZIP 추출/잠금 설치/공통 Skill doctor/Claude adapter 재설치·9native 관측 감사 exit0이다. 실제 읽기 전용 reviewer가 최종 지문·영수증·native 결과·제품 파일 제외와 한계를 확인했고, 별도 최신 리뷰 장부 `focused-review-20261011`의 complete 결과 errors=[]다. 초기 구현 전 review snapshot의 stale start 실패를 보존하고 생성된 산출물을 최신 별도 리뷰 입력으로 검증했다. 현재 부모 primary를 idle/closed로 조작하지 않았다.

원격 CI run `38069328153`의 Ubuntu/Windows job은 모두 steps0의 failure다. annotation은 계정 결제 또는 지출 한도 문제로 시작하지 못했다고 안내한다. 로컬 검사를 원격 CI 통과로 바꾸지 않으며 결제/한도 변경은 하지 않았다.

웹 원래 case 실패·section별 source URL 정밀도와 후속 경험/선호 표현의 잔여 한계, 실제 청소 불편/내부 치수·전체 청구·사람 공수·Claude/Gemini native 미인수를 유지한다. 이전 릴리스/태그/첨부는 덮어쓰지 않았다. 업데이트는 새 설치 폴더를 사용한다.
