# product-v0.16.1 사용설명서 문서 패치 배포 인수

2026-10-16 [시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.16.1)을 게시하고 원격 ZIP·자동 Source ZIP·main 파일·이전 v0.16.0 자산을 다시 내려받아 대조했다. [설명서](../contracts/judge-test.md), [패키지·독립 검사](judge-manual-U-20261016.md), [기계 기록](product-v0.16.1.json).

- 일반 사용자는 **lg-ax-judge-product-v0.16.1.zip 하나**를 새 폴더에 풀어 README를 따라간다. 제품 소개부터 준비·실행·첫 질문·결과 읽기·재사용·문제 해결까지 한 문서다.
- 제품 소스128파일·심사 ZIP205파일·SHA256SUMS가 원격 다운로드와 raw byte 동일하다. 소스 ZIP에서 동일 심사 ZIP도 재생성했다. 설명서 원본과 ZIP root/두 엔진의 설명서3사본이 동일하다.
- v0.16.0과 비교해 문서·문서 지문·패키지 메타데이터8파일만 변경했고197파일은 동일하다. 실행 코드·Skill·서브에이전트·모델 기본값은 유지했다.
- GitHub 자동 Source ZIP128파일은 제품 소스와 raw byte 동일하다. 태그 `70754579da4696e70c1ae1ebb4336e303500acdf`는 부모0인 제품 전용 snapshot이다. 개발 체계·평가·발표·원문 로그·인증·DB·캐시는 포함하지 않는다.
- 개발 소스 `5b1729c19247065d872ed5ac2d02b32d1cbae238`와 PR17 main `a9a6b5b37d702128b0b4dd9e76a80c8d642fcacb`의 제품·설치 101경로가 같은 Git blob이다.
- 패키지 단위 검사11개(judge9/source2), 자산 검사, ZIP 단독 Windows 준비11명령과 실제 MXC가 통과했다. 독립 읽기 전용 검토의 미해결 P1/P2는0이다.
- 심사 ZIP SHA256: `24e9d5db062545e43e0d5a975eb73f7b728fe034982db6caf6a808ff36537b6f`.
- 기존 v0.16.0 태그와 자산3개를 다시 받아 보존된 원본과 raw byte 동일함을 확인했다. 기존 파일을 교체하지 않았다.

문서 패치로서 새 모델 업무·GUI/브라우저 렌더·다른 운영체제 실행을 재검증한 것은 아니다. GitHub Actions는 계정 결제/사용한도 때문에 작업이 시작되지 않았고 로컬 패키지 검사와 구분한다. 발표·영상·대회 최종 접수는 별도다.
