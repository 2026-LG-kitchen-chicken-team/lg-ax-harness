# 심사위원 ZIP v0.16 통합·실제 인수

2026-10-16 PR #13 원클릭 시작과 PR #14 Windows MXC 보완을 통합했다. [이전 PR 검토](open-pr-review-20261016.md)의 결함을 수정했고 [폴더 기준](../decisions/judge-bundle-layout-20261016.md)을 적용했다. [기계 기록](judge-bundle-T-20261016.json)에 각 검사·지문·실패를 보존한다.

## 변경

- 제품 소스 ZIP에 런처 8개를 넣었다. 소스 ZIP만 추출해서 Codex·Claude 프로필 각각으로 동일 심사 ZIP을 실제 재생성한다.
- POSIX 관찰 실행은 execv로 실제 observer에 PID를 넘기고 launcher가 kill/wait한다. Windows의 waited subprocess·오류 반환은 유지한다.
- ZIP의 Unix 출처와 .sh 실행 권한을 지정하고 제거된 화면 모드 설명을 고쳤다.
- PR14의 Windows venv Python 경로를 사용하며 WinError5에 한해 제한된 경로 fallback을 적용한다. 링크/경계 검사는 유지한다. 전역 권한·인증을 바꾸지 않는다.

## 검사

- 동일 코드 `d47d36187ccd5a8e714ed76966824ee59fee8cc6`에서 Windows 로컬 확장 CI **21/21**. 실제 테스트는 개발35·제품482·평가146·웹133·관찰38·evals28개이며 각 OK/skip0다. 두 웹 빌드 후 소스·자산 변경0. 원격 Actions 결과와 구분한다.
- 제품 소스128파일, 심사 ZIP205파일. 소스 ZIP에서 심사 ZIP 재생성 raw byte 동일. 새 ZIP만 푼 폴더에서 무결성·두 엔진 설치·상태·prepare·실제 MXC 검사 **11/11 exit0**. 원 저장소 불필요.
- MXC에서 제품 venv Python·로컬 SQLite 실행 성공. 이번 PC에서는 선택 진단 uv run도 성공했다.
- 실제 Codex 입력1: doctor 성공, 제품군 없이 보낸 list_models는 필수 product_family 누락 invalid_input으로 거절됐다. 24.922초에 오류를 알리고 종료했다. 정상 조회 성공으로 계산하지 않는다.
- 별도 제품군 명시 입력2: doctor와 refrigerator list_models 각각 한 번 성공. 빈 catalog의 models[]를 29.750초에 전달했다. 두 입력 모두 workspaceWrite/on-request·networkfalse, 추가 승인0·자동 재발송0이다. 정상/실패 도구 사건과 세션 종료를 관찰했다.

입력1·2의 시간을 성능 비교나 상품기획 완료시간으로 사용하지 않는다. 관측 토큰은 JSON에 양쪽 모두 기록하며 비용/절감률로 환산하지 않는다. app-server는 실제 turn/completed 뒤 드라이버가 종료했으며 process code1과 업무 완료 사건을 혼동하지 않는다.

## 독립 검토와 범위

읽기 전용 reviewer가 diff·focused receipt·CI receipt·ZIP SHA·실제 native 증거를 대조했다. 수정 범위의 미해결 P1/P2는 발견되지 않았다. 실제 macOS/Linux 앱 실행, Claude 새 AI 업무, 브라우저 렌더·클릭·일반 세션 훅 신뢰는 이번 검사의 완료 항목이 아니다. 두 native 입력은 설치/Tool 진단이며 새 조사·상품기획 의미 품질·서브에이전트 효과 평가가 아니다.

배포 후 원격 ZIP·자동 Source·main 대조는 product-v0.16.0.md/JSON에 별도로 기록한다. 발표·영상·최종 접수와 팀원 발표자료 로컬 변경은 이번 제품 패키지 통합 범위 밖이다.
