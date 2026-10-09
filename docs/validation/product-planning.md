# 실제 근거·상품기획 Agent/Skill 원본 검증

2026-10-10 Windows, Python 3.12.14. 사용자 요청의 실제 근거 확대와 출품 Agent·Skill 원본을 작성하고 업로드 전 검증했다. 개발용 하네스와 출품 원본은 별개다. [자료 확인 범위](../data/real-research.md), [업무 계약](../contracts/product-planning.md), [외부 조사 계약](../contracts/web-evidence.md), [남은 작업](../plans/development-harness.md)을 따른다.

## 작성 범위

- 실제 업무 자료: 제품3종, 고객 의견6발췌, 공식 사실19개. 청소 불편 원문·내부 mm·선반 간격은 미확인이다. 구매 인증·제품 협찬은 미확인 값을 유지하고 직접 발행 후기의 제휴 수수료 고지는 별도로 보존했다. v2는 초기 관측 이력, 기본 v3는 고지를 반영한 새 버전이다.
- 상품기획 main Agent 지침1개와 업무 Skill5개, 조건부 외부 조사 Skill1개. 실행 wrapper는 공통 Python Tool을 호출한다. Skill6개를 서브에이전트6개로 표시하지 않는다.
- 주장·현재 제품 범위·기존 기능과 남은 불편·제안 연결·기존 기능 중복·물리 치수 필요 여부에 관한 모델 작성 검토 기록의 정합성 검사. 코드가 원문 의미의 진실성을 증명하지 않는다.
- 승인 HTTPS host의 제한된 가시 텍스트 수집, native 페이지/PDF 관측 보고의 저장, 관측 인용·정확한 모델 연결 검사와 새로운 실행 catalog 등록. 검색/브라우저/PDF 실행 환경이나 MCP를 설치하는 프로그램은 아니다.
- 미관측 runtime.engine은 null로 남기고 fixture 모델로 채우지 않는다. 공용 설명서에는 같은 공식 제품 PDP의 정확한 모델과 동일한 설명서 URL을 관측한 association snapshot을 요구한다.

## 실제 검사

최종 로컬 run은 `product-source-20261010-003`, task는 `review-product`, 실제 native reviewer는 `/root/product_skill_design`이다. 부모만 파일·Git을 작성했다. 장부 스크립트가 reviewer를 생성하거나 메시지를 보낸 것은 아니다. 검사에 최신 코드·자료·계약 입력과 run/task/attempt/agent/contract binding을 연결했다.

| 명령 또는 검사 | 실제 결과 | 로컬 receipt |
|---|---|---|
| `python -m unittest discover -s tests/product-tools -v` | 63개 통과, exit0 | `.harness/checks/32d56c3c50174a349081bd0c94bc49a2/receipt.json` |
| `python -m unittest discover -s tests/dev-harness -v` | 22개 통과, exit0 | `.harness/checks/acbe91eb87e34c42a59ea5a1e62e1d8a/receipt.json` |
| `python scripts/check-product-assets.py` | Agent1/Skill6 지문·경로 일치, exit0 | `.harness/checks/33596b3c97ac4b7fa8f5fff21612dd43/receipt.json` |
| 개발 doctor | 개발 역할6/Skill9·Claude 사본·OSS 원본 검사, exit0 | `.harness/checks/5efa22e7fe604b5e8ae2b7e2db06973b/receipt.json` |
| 업무 Skill wrapper doctor | 실제3모델/6발췌/19사실, exit0 | `.harness/checks/13d12082db80491bbf639625ecee8fb0/receipt.json` |
| 업무 Skill wrapper 모델 선택 | 상세 불편 입력 없이 내부 입력 생성, exit0 | `.harness/checks/b7a810c72740469c969a44f01b24fbfc/receipt.json` |
| `git diff --cached --check` | exit0 | `.harness/checks/fde47ee47bde40b2a7e85d97270382dc/receipt.json` |
| staged 파일의 별도 checkout, autocrlf=false/true | 두 환경 모두 validator·asset·22/63시험·실제 catalog exit0 | `.harness/checks/5b4d7d375e304e188257afd3d310c37d/receipt.json` |

새 checkout 시험은 Windows에서 두 Git 줄바꿈 설정을 대조한 것이다. Linux OS 실행을 대체하지 않는다. 지문이 있는 Skill·Agent·공통 코드·계약·자료의 bytes를 .gitattributes로 보존한다. 초기 staged diff에서 CRLF 줄 끝 오인과 문서4개의 EOF 빈 줄을 확인해 프로젝트 whitespace 조건을 명시하고 EOF를 정리했다. 사용자 전역 Git 설정은 바꾸지 않았다.

시스템 skill-creator의 quick_validate도 PyYAML6.0.3 임시 도구 환경에서 Skill6개 모두 통과했다. 처음 번들 Python에는 yaml 모듈이 없어 실패했으며 임시 uv 실행으로 보완했다. 제품 의존성이나 사용자 전역 환경에는 PyYAML을 추가하지 않았다.

실제 `fetch_web_page`를 직접 발행 후기 URL에 실행해 HTTP 가시 텍스트 snapshot을 얻었다(exit0). snapshot ID는 `a43b3e977295c85cdeed399a9d2d34f5d931654c361203a4a46303e286bad24d`다. 원문·SQLite는 runtime-data에만 저장한다. 공식 PDF 직접 다운로드와 렌더 대조는 자료 확인 문서에 기록했다. native capture/import 경계 시험은 fixture를 사용하며 실제 브라우저 자동 제어 성공으로 바꾸지 않는다.

## 독립 사용·리뷰의 범위

별도 native `/root/product_forward_test`가 Agent/Skill 지침을 읽고 T876MQQ012 수납 정리 요청에서 실제 Tool을 사용했다. 원문 후기 조회·공식 기능 비교·근거/결과 계약·검토 보고 실행을 확인했다. 기존 접이식 선반을 신규 기능으로 제안하지 않고 하드웨어 추가 없는 사용 안내 후보를 작성했다. 읽기 전용 배정이라 상태 저장 없이 held로 반환했다. 최초 JSON 준비에서 null engine이 거부되는 문제와 후기의 제휴 고지를 발견했고 부모가 계약·v3 자료에 반영했다.

이 사용 점검은 지침을 명시적으로 제공한 것이다. 설치·자동 Skill 선택·상태 저장·다중 턴·전체 네이티브 업무 흐름을 검증하지 않았다. 전체 모델/토큰은 미관측으로 남긴다. 후보의 업무 효과나 심사 품질을 통과시킨 평가도 아니다.

첫 독립 리뷰는 공식 PDF host 누락을 실제 재현했고 `product-source-20261010-001`을 실패로 보존했다. host와 공용 설명서 연결을 수정한 뒤 후속 리뷰에서 중요한 미해결 결함이 없음을 확인했다. 다른 모델·PDP·링크/URL 접두어 거부, HTTP PDF 미지원, native 관측 보고·문서 적용의 한계, 수정 상한과 버전 불변성을 대조했다. Reviewer는 receipt의 실제 입력·로그 SHA와 binding을 확인했으며 suite를 다시 실행한 것으로 기록하지 않는다.

## 남은 범위와 업로드

환경별 출품 설치/자동 발견/권한/전체 상태 흐름은 S02/S03b, 실제 AI 심사 입력과 원문 의미·효과/시간/공수/토큰 절감 평가는 S05다. 팀원 Claude native 개발 체계 인수도 D06b에 남는다. 외부 관찰 화면·시연·제출 완료를 주장하지 않는다. `semantic_status=unverified`, `acceptance_ready=false`는 구조 검사와 의미 판정을 구분한다.

업로드 전 읽기 전용 감사에서 API key·개인 설정·원문 로그·SQLite·의존성 환경 유출이나 실제 업로드 보류 사유를 발견하지 못했다. .harness/runtime-data/.venv/.env/Claude 개인 설정은 Git 제외다. 사용자 컨설팅 이미지, 새 발췌/사실 요약·provenance·합성 시험 원본·코드·계약·잠금 파일·OSS 원본/고지와 검증 요약만 관리한다. 전체 개발 사용량은 unknown이며 별도 유료 모델 API는 호출하지 않았다. 원격 CI의 실제 결과는 GitHub 실행 기록으로 확인해야 한다.
