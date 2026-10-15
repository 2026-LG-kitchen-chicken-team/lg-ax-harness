# Q — 심사 실행 환경 준비

2026-10-15. 사용자 요청 **1번: 심사 실행 환경 정리**만 수행했다. 프론트 최신본 연결·화면 검수·새 상품기획 회귀·모델 비교·릴리스·main 병합·발표 제작은 수행하지 않았다. 실제 결과는 [JSON](judge-setup-Q-20261015.json), 실행 순서는 [권한 및 첫 설정 안내](../contracts/runtime-access.md)를 따른다. 이전 P/O native 업무 결과를 이번 설치 성공 건수에 더하지 않는다.

## 바뀐 내용

- Codex 제품 README를 Python3.12 잠금 설치 → 인증 없는 로컬 검사 → 본인 CLI 로그인/상태 확인 → 전체 doctor → 요청별 승인 실행 순서로 정리했다. 이미 로그인된 실행자는 재인증할 필요 없다.
- `product-doctor.py --local-only`를 추가해 Codex 설치/로그인 전에도 제품 지문·의존성·로컬 공통 Tool/SQLite를 확인한다. 인증 파일이나 사용자 전역 설정을 읽거나 변경하지 않는다.
- 두 doctor는 지원하지 않는 Python을 의존성·인증·DB 검사 전에 감지하고 Python3.12 실행 명령을 안내한다. 시스템 기본 Python3.14를 제품 Python과 혼동하지 않는다.
- Claude GUI 준비에 선택 CLI의 부재/오류가 장애가 되지 않도록 기본 doctor의 선택 CLI 오류는 경고로 분리했다. 명시한 `--require-native`에서는 CLI 오류를 실패로 유지한다. 이 옵션은 Desktop GUI의 필수 단계가 아니다.
- Claude 설치 README와 portable 계약을 Code → Local → 제품 기본 폴더 경로로 맞췄다. 설치·인증·모델·폴더 신뢰·부모 권한이 서로 다른 단계임을 명시했다.
- doctor가 확인한 로컬 저장과 native 권한·네트워크·모델 접근 미확인을 별도 필드로 출력한다. 짧은 native 준비 질문과 실제 오류별 조치를 설치되는 권한 안내에 넣었다.

## 실제 검사

| 검사 | 관측 결과 | 판정 범위 |
| --- | --- | --- |
| 새 외부 Codex/Claude 제품 폴더 | 문서의 uv `--no-project` 설치 명령으로 생성. 각6개 업무 Skill·3개 선택 역할, 개발 체계 제외 | 제품 사본 준비 |
| 각 `uv sync --locked --python 3.12` | Python3.12.10 및 잠금 의존성 설치 exit0 | 새 제품 폴더 로컬 환경 |
| Codex 로컬 및 로그인 상태 포함 doctor | errors0, SQLite/common Tool exit0, CLI0.162.0, `Logged in using ChatGPT` | 로컬 상태 및 기존 계정 인증 상태 확인. 모델 호출은 없음 |
| Claude 기본 doctor | CLI 미발견 상태에서도 errors0·local_only, SQLite/common Tool exit0 | Desktop용 제품 준비. GUI 인증·권한 확인을 대신하지 않음 |
| 시스템 Python3.14.7로 두 doctor 실행 | 둘 다 exit1·unsupported_python, 올바른 실행 경로 안내 | 의도한 실패 진단2건 |
| 설치 관련 전체 확인 | 기대 결과9/9 일치 | 위 양성7건 및 의도한 실패2건. 실제 AI 업무9건을 뜻하지 않음 |
| 신규 준비 진단 회귀 | 5개 검사 통과 | Python 오류 조기 중단·미인증 로컬 검사·정상 로그인 검사·선택 CLI 실패 분리·저장 실패 판정 |
| 기존 설치/잠금/격리 검사 | 9개 검사 통과, skip0 | 양쪽 실제 잠금 의존성 설치와 사본 경계/변경 검출 포함 |
| 제품 자산 검사 | exit0 | 현재 manifest와 파일 지문 |
| 별도 공개 URL HTTP 진단 | 일반 로컬 Python에서 lge.co.kr → /home HTTP200·첫 바이트 수신,0.218초 | 현재 PC의 일반 Python 네트워크. native 실행기/모든 사이트 접근 성공이 아님 |
| Codex Windows sandbox 프로세스 시작 | workspace-write/on-request, `cmd.exe /d /c ver`가 exit1·`helper_unknown_error: setup refresh had errors`,0.266초 | 모델 입력 이전 Windows sandbox 준비 실패. 권한 승인 성공이나 하네스 업무 실패로 세지 않음 |

처음 확인 중 새 Codex doctor의 인자 변수 충돌을 발견해 수정했다. 최초 실패 로그/폴더를 보존하고 새 외부 폴더에서9개 항목을 다시 확인했다. 이 재검사는 모델 요청 재발송이 아니다. 이번 새 native 모델 입력은 **0건**이다.

## 남는 실행 조건

설치와 권한 안내 정리·로컬 제품 준비는 위 범위에서 끝냈다. **현재 PC의 제한 권한 Codex 실제 첫 실행은 Windows sandbox 초기화 오류로 인수하지 못했다.** 일반 요청별 승인 설정에서도 프로세스 시작이 안 된다는 관측을 남기며, Windows 보안/ACL·전역 설정·계정을 바꾸거나 전체 접근으로 자동 전환하지 않았다. 오류 원인의 하네스 코드 귀속은 입증되지 않았다.

Claude Desktop의 새 Local 환경 선택·현재 GUI 계정/모델/권한은 이번에 새로 조작·검증하지 않았다. 현재 제공된 Computer Use는 native 앱 제어가 비활성화된 상태라 새 GUI 동작을 수행할 수 없었다. 이전 P의 실제 Opus5.5 후속 성공과 새 세션 환경 선택 오류는 그대로 보존한다. 정상 Local/폴더 재선택 및 앱의 공식 문제 해결 경로는 안내에 기록했다. CLI를 새로 설치하거나 인증을 변경하지 않았다.

두 실행기 모두 설치 완료만으로 모델 접근·Skill 자동 선택·공개 웹 자료 충분성·AI 품질을 인증하지 않는다. 최종 native 준비 진단과 새로운 프론트 연결/화면 인수는 그 작업의 실제 환경에서 별도로 확인한다.
