# product-v0.18.0 배포·원격 바이트 인수

2026-10-16. [제품 설치 저장소](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/tag/product-v0.18.0)와 [개발 저장소의 제품 릴리즈](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.18.0)에 제품 시험판을 게시했다. 두 저장소는 비공개 상태이며 기존 product-v0.17.0 태그와 첨부물3개의 digest를 보존했다. 공개 예약·저장소 권한·계정 한도·최종 접수는 변경하지 않았다.

| 파일 | 범위 | SHA256 |
|---|---|---|
| lg-ax-judge-product-v0.18.0.zip | 사용자용 ZIP 하나·215파일·각 엔진102 | 070e984fdaa891886611151b947c222af165063743151f02eb2368d81a5f73c1 |
| lg-ax-harness-product-v0.18.0.zip | 제품 전용 원본133파일 | cf3de542ee807ebb6dd915037e81298795c391c83fd9ed16c1937b9c309e438f |

두 저장소에서 ZIP과 SHA256SUMS.txt를 다시 내려받아 실제 크기·SHA·GitHub digest와 대조했다. 원본 provenance는 `46ddc2d512e19284da1d683f4a149dccdce5a26c`, 부모 없는 제품 스냅샷은 `f599731b8d740b32d43d84de2b1589311696a88a`다. GitHub 자동 Source code ZIP도 최상위 디렉터리만 제외하면 제품 source의133파일과 경로·원바이트가 정확히 같다.

제품의 실제 추가3경로는 `execution_context.py`, `meaning-preservation.md`와 native Skill 참조 사본이다. 위젯·개발 체계·평가 원문·실행 로그·DB·인증·의존성 캐시는 제품 ZIP과 제품 태그에 없다. 기본 catalog는 비어 있다. 사용자 설명서는 원본 `judge-test.md`와 정확히 같다. 기존 설명서 하단 v0.17.0 표시는 재사용 안내의 적용 기준이며 bundle manifest의 release는 v0.18.0이다. 엔진별 설치 manifest는 source 지문과 파일별 SHA로 결속된다.

새 ZIP만 추출한 작업공간에서 check→Codex setup→Claude setup→check 네 명령 exit0를 확인했다. 별도 독립 검토에서도 파일 집합·manifest69·각 엔진 설치 지문·원본/변환 바이트·빈 catalog·제품 snapshot133개 blob을 대조했다. 이 준비 검사를 모델 로그인·계정 권한·native 발견·의미 품질 완료로 확대하지 않는다.

제품 저장소의 README와 agent.md는 `73ec4b1`에서 v0.18.0을 명시하도록 갱신했다. 고정 installer-v0.1.2의 코드·지문·과거 기본값은 바꾸지 않았다. 실제 Windows PowerShell 한 줄을 새 폴더와 `-Version product-v0.18.0`으로 실행해 비공개 인증 다운로드·215파일 확인·`prepared:true`·exit0를 확인했다. 모델 입력0, 기존 폴더 덮어쓰기0, 로그인/전역 보안정책 변경0이다.

[실행 보완·로컬 CI](execution-quality-AA-20261016.md)는21단계, 코드942개 중941통과·Windows 조건1skip이다. 발표 위젯14개 검사는 제품 밖에서 별도 통과했다. PR24의 Actions Windows job116968491543은 실제 steps0이며 계정 결제/사용한도 annotation으로 미시작했다. 계정 설정을 바꾸지 않고 로컬 CI 기록을 사용했다. 이 Windows 인수로 macOS/Linux native 성공이나 브라우저 육안 검수를 주장하지 않는다.

[기계 판독 인수 기록](product-v0.18.0.json)에 원격 자산·지문과 검사 범위를 남겼다. 동일 자료 모델/추론 비교는 별도 AA 계약의 진행 결과로 판정하며 기본 모델은 이번 배포에서 변경하지 않았다. 촬영은 수행하지 않았다.
