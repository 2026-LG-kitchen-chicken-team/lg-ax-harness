# product-v0.19.0 배포·원격 바이트 인수

2026-10-17. [제품 저장소 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/tag/product-v0.19.0)과 [개발 저장소 제품 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.19.0)을 게시했다. 두 저장소는 비공개이며 공개 예약·접근 권한은 변경하지 않았다. [기계 판독 기록](product-v0.19.0.json)에 원격 검사와 실제 한계를 남겼다.

| 첨부물 | bytes | SHA-256 |
|---|---:|---|
| lg-ax-harness-product-v0.19.0.zip | 6542247 | b209479925431f60ccbdd0ce8bc129c919589033dd16ad6bfcff347bd04f9640 |
| lg-ax-judge-product-v0.19.0.zip | 12991007 | 8dde5df749acd0406ad47cae3421250da1efe6ec33b59ca1ec6e9dd56cb9a0fa |
| SHA256SUMS.txt | 200 | 3bfc94c3b758dd6b9bc038493df7eb670e58e869bf299bc936e3e2948a45dcc4 |

제품 소스 `1db850235d9a29124f53a4c5fa7205f1a9d837e3`에서 제품 원본134파일·사용자용 ZIP217파일·각 엔진103파일을 만들었다. 제품 태그는 개발 이력 없이 부모0개의 `7e3728f2484085104de00f5ddba4ad50cf56b734`를 가리킨다. 양쪽 원격 태그·부모0·자산3개 이름/크기/GitHub digest와 실제 재다운로드 SHA를 모두 확인했다. 각 원격의 자동 Source code ZIP도 제품 원본134파일과 경로·바이트가 같다. 기존 v0.18.0 태그와 자산 digest는 변경되지 않았다.

ZIP의 사용설명서는 `docs/contracts/judge-test.md`와 바이트가 같고 manifest의 모든 파일별 SHA가 일치한다. 설명서 하단의 ‘설명서 적용: product-v0.17.0’는 시작 절차 재사용의 과거 기준이며 실제 bundle release는 v0.19.0이다. 본문의 기획 본문/부록/진단·현재 관제·원터치 안내 철회 내용은 갱신했다. 기본 catalog는 비어 있으며 개발 체계·평가·원문 로그·SQLite·인증·의존성 환경·발표용 위젯은 포함하지 않았다.

새 ZIP만 추출해 `check → setup --engine codex → setup --engine claude → check` 네 명령을 실행했고 모두 exit0다. 현재 준비에는 uv/Python3.12가 필요하다. **원터치 다운로드/AI 설치 요청문 안내 중단**과 ZIP 시작 파일의 준비물을 혼동하지 않는다. 제품 저장소 README/agent.md도 `5d4237c2c1cfb20665d2eaf8cc51c3b233b6f590`에서 ZIP 중심으로 갱신했다. 과거 installer 태그·코드는 보존했고 이번에는 한 줄 설치기를 실행하지 않았다.

[구현·CI·세 제품 결과 재생](planner-first-AB-20261017.md)은 별도 분모다. 로컬 CI24/24·Python951통과/OS조건skip1·관제JS112통과이며 ZIP 정적 독립감사에서 남은 기능 P1/P2는 없다. 새 네 환경의 실제 업무·자동 브라우저 표시·인쇄쪽수·다른 OS native 성공·최종 접수·촬영 완료로 확대하지 않는다. 모델 실용 권장과 기본값의 차이는 [모델 결정](../decisions/model-use-20261017.md)을 따른다.
