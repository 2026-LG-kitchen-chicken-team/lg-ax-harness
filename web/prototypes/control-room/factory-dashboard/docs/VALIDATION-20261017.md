# 공장 UI 이전 검증 · 2026-10-17

대상은 `2026-LG-kitchen-chicken-team/lg-ax-harness`, 기준 main은 `ae291fa3c899d23866c28ffaba83a59190ba021a`입니다. 공개 Site 버전24의 승인 UI를 기존 `factory-dashboard`에 가져오고, 기존 생성기로 `agent-office/factory.html`을 갱신합니다. 원본 연구원 PNG를 보존합니다.

## 검사 결과

| 검사 | 결과 |
| --- | --- |
| `node --test --test-reporter=spec tests/*.test.mjs` (factory-dashboard) | 151/151 통과 |
| `node node_modules/vite/bin/vite.js build` | 통과 · 번들 크기 경고 있음 |
| `node node_modules/vite/bin/vite.js build --mode office` + `node scripts/publish-office.mjs` | 통과 · 단일 HTML 생성 |
| `python -B -m unittest backend.tests.test_release_reader backend.tests.test_release_activity -q` | 42개 실행, 1개 건너뜀, 실패 없음 |
| `python -B scripts/check-product-assets.py` | 오류 0개 |
| `tests/web/test_agent_office.py` + `tests/product-tools/*package.py` | 합성 관측·설치·패키지 61개 중 초기 59개 통과, 2개 실패. 아래 처리 내역 참조 |
| 단일 HTML 검사 `test_run_dashboard_is_one_file_that_reads_the_records_beside_it` 재실행 | 1/1 통과 |

처음 실행한 Python 검사는 샌드박스 임시 폴더 권한으로 실패해 같은 검사를 정상 임시 폴더에서 다시 실행했습니다. 이 테스트는 합성 CLI 로그와 임시 제품 폴더를 사용하며 실제 모델이나 사용자 업무를 실행하지 않습니다.

다시 실행한 61개 검사 중 단일 HTML 검사는 이전 이미지 3개를 고정 기대하고 있었습니다. 승인 UI의 7개 인라인 PNG와 원본 연구원 PNG 포함 여부를 검사하도록 갱신했고 해당 검사를 다시 통과했습니다. 나머지 한 검사는 기존 agent-office의 TypeScript 컴파일러(`app/node_modules/typescript/bin/tsc`)가 설치되어 있지 않아 컴파일/실행 부분을 수행하지 못했습니다. 이 기존 TypeScript 소스는 수정하지 않았으며 그 검사 통과를 주장하지 않습니다. 제품 패키지 검사 14개는 통과했습니다.

## 독립 검토에서 고친 문제

첫 검토에서 기본 설치 화면이 `serverStore`를 선택해 옆의 `live.js` 관측기를 시작하지 않는 P1을 발견했습니다. 설치용 `pollFiles:true` 저장소를 기본 선택하도록 수정했습니다. 공개 Site의 기본 서버 연결과 사용자가 여는 기록 보기는 유지합니다. 추가 회귀 검사는 기본 소스 선택, 실제 합성 기록 수신 및 세션 표시를 확인합니다. 생성 HTML도 이 수정으로 다시 빌드했습니다.

## 체크섬 정합성

`skills/manifest.json`에서 새 `factory.html`의 SHA256을 갱신했습니다. 기준 main에는 이미 `codex_follow.py`의 실제 파일과 manifest SHA256이 불일치했습니다. 파일 바이트를 기준 main과 대조해 동일함을 확인하고 SHA256만 바로잡았습니다. 관측기 Python·설치기·업무 Skill 코드는 변경하지 않았습니다.

## 미실행 범위

- 실제 상품기획 CLI 요청 및 모델 호출: **not_run**. 사용자가 PR 이후 인수합니다.
- 공개 Site에서 PC 기록 자동 연결의 추가 실험: **미포함·미배포**.
- 최초 PR 업로드 시 브라우저 인수는 **not_run**이었습니다. 이후 로컬 HTTP 실행에서 아래 이미지 경로 문제를 발견해 수정하고 데스크톱 브라우저에서 승인 연구원·여섯 작업실·배경 표시를 확인했습니다. 실제 file:// 브라우저 실행과 모바일 시각 인수는 **not_run**입니다.
- PR 병합, 새 공식 릴리즈 게시, 기존 설치본 교체: **미실행**.

실제 연결 순서는 [CLI-TESTING.md](CLI-TESTING.md)를 참고하세요. 진행 수·현재 Skill·담당 AI는 관측 기록에서만 표시하며 모션 예시는 실제 실행과 구분합니다.

## 로컬 HTTP 실행에서 발견한 이미지 문제

읽기 서버가 `assets/`만 제공해 공개 이미지 폴더인 `characters/`, `environment/`, `workshops/`와 모션 영상이 404가 됐습니다. 이미지가 로드되지 않으면 이전 기본 3D 도형이 남아 승인한 UI와 다르게 보였습니다.

명시한 UI dist 안에서 위 세 폴더의 바로 아래 PNG와 `media/` 바로 아래 MP4만 추가로 제공합니다. 다른 파일 형식·중첩 경로·경로 탈출·심볼릭 링크·다른 출처 차단 및 읽기 API 인증은 유지합니다. 클라이언트가 지원하는 `harness/team/motion/records/demo` 단일 view 쿼리만 허용합니다.

수정 후 `backend.tests.test_release_reader`와 `backend.tests.test_release_activity`는 **44개 실행, 1개 건너뜀, 실패 없음**입니다. 브라우저에서 기존 연구원 PNG·여섯 작업실·배경을 실제로 확인했습니다. 이 확인은 실제 새 상품기획 요청이나 모델 실행 검증을 뜻하지 않습니다.
