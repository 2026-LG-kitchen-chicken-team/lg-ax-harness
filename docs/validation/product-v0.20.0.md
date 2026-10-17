# product-v0.20.0 배포·원격 바이트 인수

2026-10-18. [제품 저장소 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/tag/product-v0.20.0)과 [개발 저장소 제품 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.20.0)을 게시했다. 두 저장소의 비공개 상태·기존 공개 일정과 v0.19.0 자산은 유지했다. [기계 판독 기록](product-v0.20.0.json)에 원격 대조 결과를 남겼다.

| 파일 | bytes | SHA-256 |
|---|---:|---|
| lg-ax-harness-product-v0.20.0.zip | 23223612 | f7fe116b8ac36458a7d68e150b939f99b085a40a3f606ce8d106fabfcba3cb4c |
| lg-ax-judge-product-v0.20.0.zip | 25017930 | 81f6b50c8b65c03e585c86b014b2394d3e2d927911b15ec70c2ca71118822e79 |
| SHA256SUMS.txt | 198 | cdc98002c9b0b8ce31a3ea82d4937897663a788c6b5f8bdf30bcdb1a2083bbcd |

실행·설명서 소스 `d542c40e55579df0b19713f2532fd96450f2559d`에서 소스284파일·심사위원225파일을 만들었다. 제품 태그는 개발 이력 없이 부모0개의 `ddc270dbe86d326692a9bb6ce22af371447e07b8`를 가리킨다. 양쪽 원격 태그·부모0·자산3개의 이름/크기/GitHub digest·실제 재다운로드 SHA를 대조했다. 각 원격의 자동 Source code ZIP도 제품 원본284파일과 경로·바이트가 같다. 제품 저장소 README도 현재 ZIP 중심으로 갱신했다.

사용자는 **심사위원 ZIP 하나**를 받아 새 폴더에 풀고 루트 README를 따른다. README는 `docs/contracts/judge-test.md`와 바이트가 같고 manifest224파일·CRC·대소문자 충돌·경로·줄바꿈·Unix 실행 비트를 검사했다. 새 ZIP 추출에서 check→Codex setup→Claude setup→check 네 명령이 모두exit0였다. uv/Python3.12·본인 AI 계정은 필요하며 별도 모델 API key나 Node/npm은 필요 없다. uv 자체를 지우고 새 OS 설치부터 시험한 것은 아니다.

소스 ZIP에는 세 프론트의 원본146파일·잠금 파일·필요 정적 자산·LICENSE/NOTICE를 선택 포함했다. 이 최종 ZIP만 새 폴더에 추출해 공식 registry에서 npm ci/build 여섯 명령을 수행했고 모두exit0, HTML3/3이 위 기능 소스의 결과와 완전히 같았다. lock3개·원본146개가 불변이었다. 공장 HTML 용량 증가는 기존 시험판 대비 정적 아트4개 추가 내장이 주원인이며 원문·개인 자료 유입이 아니다.

최종 동결 기능 소스의 로컬 CI24/24를 통과했다. [AL 실제8개 CLI 비교·GUI/재생 구분](human-final-AL-20261018.md)과 [권장 모델 결정](../decisions/model-use-20261018.md)을 함께 따른다. Codex GUI2개 업무의 초기 연결 실패와 최종 코드의 같은 결과 재생은 보존한다. 새 Claude GUI 업무는 앱 제어 연결 부재로 실행하지 못했고, 앱 열기/CLI 성공으로 대체 인증하지 않는다. 다른 OS native·실제 현장 효과·촬영·최종 접수 완료로 확대하지 않는다.

독립 ZIP 감사에서 새 P1/P2는 발견하지 못했다. 일부 고급 내부 문서의 과거 개발 참조 링크는 남아 있으며 루트 사용설명서·첫 실행·핵심 결과 연결 경로와 구분해 기록했다. 원문 corpus·DB·인증·원본 실행 로그·개발 역할·평가 자료·발표용 Token Lens·의존성 환경은 배포에서 제외했다.
