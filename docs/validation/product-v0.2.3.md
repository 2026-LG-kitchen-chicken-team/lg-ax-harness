# 제품 v0.2.3 시험판 배포 검증

2026-10-11 KST. [제품 v0.2.3](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.3)는 웹 설명서 절별 출처·후기의 경험/선호/기대 구분을 보완한 시험판이다. [수정 마감 기록](closure-progress-20261011.md)과 [한 차례 평가 계약](../evaluation/closure-protocol-20261011.md)을 따른다. 공식 최종 제출·전 환경 지원 완료가 아니다.

| 항목 | 확인한 값 |
|---|---|
| main provenance | `ac6a558eeacd2ee53cd9de1a9d3fd3695bcd9d0c` |
| 제품 태그의 실제 commit | `cccdd44c2220b8b0c9268e97559a1725b091544b` |
| 제품 tree | `7428d2a89198e11ad399249b5d7bfaa8e4b10131` |
| ZIP | `lg-ax-product-v0.2.3-codex-source.zip` ·124,947bytes |
| ZIP SHA256 | `47371b63e0016566c1725882833aea1ccac3daf2f28ffdb31f1f4852d0ecbb92` |
| 파일 |70개 ·제출 manifest69개 SHA/CRC 일치 |
| GitHub 상태 |draft=false ·prerelease=true |

ZIP과 부모 없는 제품 Git tree의 모든 경로·원본 byte가 같다. 원격 태그 commit과 잘림 없는 재귀 tree70개를 확인했고, 업로드 뒤 ZIP·SHA256SUMS.txt를 새 폴더로 내려받아 byte/SHA/GitHub asset digest를 대조했다. 자동 Source code도 개발 체계를 제외한 제품 snapshot이다. LICENSE/NOTICE·잠금 파일·업무 Agent/Skill·공통 코드·실제 v3 자료·세 adapter 안내를 포함하며 개발 체계·평가/관찰 코드·원본 로그·DB·인증·의존성 환경은 제외한다.

관련 실제 로컬 검사는 제품125/evaluation90/observer38=253개, 자산·새 ZIP 추출/잠금 설치/공통 Skill doctor/portable adapter 소스 재설치 exit0이다. 실제 reviewer `/root/seven_final_review`가 최신 입력/receipt와 동결4입력/3native 세션·제약/출처/후속 이력·사용량·ZIP 범위를 읽기 전용으로 검토했다. 마감 장부 `closure-review-20261011`의 complete errors=[]와 binding receipt `36b5305eb9644cf086d927172a9aa27c`를 보존한다. primary를 idle/closed로 조작하지 않았다.

위 장부 완료는 구현 커밋 전 검토 시점의 결과다. 이후 이 배포 기록·README 현재 링크·작업 원본의 첫 요약을 실제 완료에 맞게 갱신했으며 제품 코드/ZIP은 바꾸지 않았다. 제품 snapshot byte 대조 receipt `1b7bdfe5039d4f81bd1c0cc665be5a97`, 업로드·재다운로드·원격 태그/tree/asset digest 대조 receipt `11a9e113b1e14659b92dd8434d11a5c3`도 exit0이다.

구현 커밋의 원격 CI run `38072066492`는 Ubuntu/Windows 모두 steps0·failure다. 실제 annotation이 계정 결제 또는 지출 한도 사유로 시작하지 못했다고 안내했다. 로컬 통과를 원격 CI 통과로 바꾸지 않으며 결제/한도는 변경하지 않았다.

native4개는 최종 URL 비문자 입력 검증1줄을 넣기 전 동결 v5.5로 실행했다. 해당 최종 경계와 종료 후 runner 경계2개는 코드 검사로 검증했고 AI를 재실행하지 않았다. 각14/14 의미 점수는 신규 작성·알려진 원문의 비맹검 진단이며 일반 정확도·품질 우위·총 토큰/비용 절감·사람 공수 효과를 뜻하지 않는다. 기존 실패/timeout/원래 관찰 partial 기록을 보존한다. 관찰45사건은 저장 기록 local replay이며 실제 화면/녹화 인수와 다르다.

청소 불편·내부 유효 치수·선반 간격과 Claude/Gemini native 인수·전체 청구/사람 시간·최종 제출 규격은 미확인이다. 현재 자료 조사 단계는 종료했으며 부족한 요청은 보류한다. 다음 내부 작업은 별도 관찰 화면의 가독성/장애 표시·30초 실제 녹화 → 발표/영상 → 최종 제출 재현이다. 이전 큰 작업 제목을 반복해서 현재 남은 작업으로 제시하지 않는다. 이전 릴리스는 덮어쓰지 않고 업데이트는 새 폴더에 설치한다.
