# 제품 v0.10.0 시험판 발행·원격 인수

2026-10-13 11:06:02 UTC 게시. [제품 릴리스](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.10.0)는 prerelease이며 운영진 최종 접수가 아니다. 변경·실제 AI·품질 제한은 [웹 전달 검증](web-ready-harness-20261013.md), [웹팀 인수](../plans/web-team-handoff-20261013.md)를 따른다.

## 무엇을 게시했는가

기본 현재 정형 결과·선택 등록본문 전체·출처·검토/조사 이력의 웹 JSON 전달, 동일 버전 복구와 SHA/journal 결속, 명시 legacy 파일의 stored review gate, 요청 기반 자료·선택 출품 역할3을 포함한다. 기본 PDF/DOCX 자동 생성·검수를 제외했으며 HTML/프론트와 자체 모델 API 실행기는 추가하지 않았다.

- 개발 소스 provenance: `182ee2e95f9ae4f8e5a21b835b714175b700b266`, `codex/evidence-complete`에 실제 푸시.
- 제품 전용 snapshot: `cdf0e6e1970c6e0b8d1cc728a6838dabf9188e29`, 부모0, tree `7b8d33a23cdd1edd85ffda3fa51cf51a47e4eb28`.
- 설치 core manifest raw SHA: `2bb9ccd4e25097a52573ea480ab4f3276a8f25a8dca8b44c375d868f75f1877f`.
- GitHub 자동 Source code ZIP은 Codex canonical105파일과 목록/원본 바이트가 정확히 같다. Claude는 같은 공통 core의 별도 설치 ZIP이다. main/웹팀 코드/기존 태그를 변경하지 않았다.

## 실제 첨부물·다운로드 검사

| 원격 첨부 | 파일 수 | 내려받은 SHA-256 |
|---|---:|---|
| `lg-ax-harness-codex-product-v0.10.0.zip` | 105 | `517ccf55a3f5d0ad279b1a19e8b16f9cd9ab52597b917d6f89af2b0c66525cd3` |
| `lg-ax-harness-claude-product-v0.10.0.zip` | 105 | `49e2c45ec0430db067e3f9aef152d8a71be6524ec659fb98b6b2662a280a4655` |
| `SHA256SUMS.txt` | 체크섬2행 | 로컬 발행본과 바이트 일치 |

원격3첨부·prerelease·태그 peeled commit·부모0을 직접 확인했다. 새 다운로드 폴더의 두 ZIP SHA/105파일과 자동 Source code105파일의 raw byte 비교 exit0이다. 첫 `gh release download --pattern/--archive` 동시 사용은 CLI 제한으로 exit1이었고 실제 두 명령으로 나눠 복구했다. 실패를 내려받기 성공으로 바꾸지 않았다.

새 폴더 추출·manifest/raw SHA·locked 설치·doctor·재설치83파일을 두 환경별로 확인했다. 추가 fresh Git checkout에서 `core.autocrlf=true`를 적용해 source57 raw SHA와 자산 검사 exit0도 확인했다. 원래 staged adapter4개 지문 실패는 `adapters/** -text`/실제 renormalize로 해결했다. 이 검사는 native AI·HTML 시각 인수가 아니다.

기본 catalog는empty이며 평가 corpus·개발 체계/장부·평가 질문/rubric/runner·로그/DB·인증·사용자 PDF는 없다. 소스 목록과 manifest·LICENSE/NOTICE·잠금 파일을 확인했다. 사용자 기존 미추적 평가 문서4개는 커밋에 포함하지 않았다.

## 검증 상태와 제한

로컬 제품371·평가144·자산 검사·독립 코드 인수를 확인했다. H14/I5 native 결과는 소스별로 분리하며 현재 I의 기획4건은 일부 충족, 모호 확인1건은 예외 처리 통과다. 원문 미명시 매체 귀속·후기 조건 전이·검증 조건·존재하지 않는 오류 로그 파일 안내는 남는다. 온라인110후기+2사실은 held이며 공식 상세3발췌가 미등록이다. 웹본문112와 export본문35는 다르며 전체 자료 인수에는 웹 JSON/catalog/snapshots가 필요하다.

현재 I 냉장고/식기세척기 native 재인수·후속/취소·모델 최종 권장·역할 이점·웹팀 실제 화면/HTML 가독성·영상/발표/리허설·접수는 미완료다. 전체 backend 청구·자식/부모 usage 중복 범위와 시장 대표성도 미확인이다. 새 ZIP 재현은 동결 설치 native 결과를 대신하거나 새 native 성공을 추가하지 않는다.

새 소스 commit의 [원격 CI](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38387660705) Windows/Ubuntu4 jobs(두 runs)는 계정 결제·사용 한도 문제로 작업 자체가 시작되지 않았다. source 실패나 원격 검사 통과로 표시하지 않았고 계정 결제/보호 규칙을 바꾸지 않았다. Ubuntu 이미지 변경 안내는 별도 플랫폼 공지이며 이번 실패 원인으로 바꾸지 않는다.

업데이트는 환경에 맞는 ZIP을 새 폴더에 풀고 README를 따른다. 이전 DB·세션·실패 이력을 덮어쓰지 않는다. 실제 제출물/발표·영상은 완성 후 명시한 파일만 추가하고 현재 패키지를 최종 접수로 표시하지 않는다.
