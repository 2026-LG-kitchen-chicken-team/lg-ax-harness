# R — Windows sandbox 시작 오류 해결

2026-10-15. 사용자가 sandbox 오류의 실제 원인 해결과 심사 실행자의 재발 방지를 요청했다. 이 기록은 [이전 Q](judge-setup-Q-20261015.md)의 원인 미확인/제한 권한 시작 실패를 갱신한다. Q/P 원본과 실패 이력은 보존하며 상품기획 품질·웹 화면·Claude 새 GUI 세션을 이번에 새로 인수한 것으로 바꾸지 않는다. [기계 판독 결과](sandbox-fix-R-20261015.json)와 [설치/권한 안내](../contracts/runtime-access.md)를 함께 본다.

## 확인한 원인

이 PC의 Codex sandbox 로그에서 기존 backend가 runtime 읽기·실행 권한을 검증하던 중, 실행 중인 Computer Use `node_repl.exe`의 root-only ACL 갱신 대상을 열다가 **Win32 32 공유 위반**으로 실패했다. 같은 단계가 다른 작업 폴더에서 반복됐고, 이 실패가 setup refresh의 최종 errors 목록에 포함됐다. 사용자 프로필 경로의 다른 경고와 구분했다. Win32 5 권한 거부나 특정 프로세스 한 개의 잘못이라고 단정하지 않았다. 해당 실행 파일의 프로세스가32개인 시점과 ACL 읽기 성공은 관측했지만 잠금 핸들 소유자까지는 확인하지 않았다.

[공식 Windows sandbox 안내](https://learn.chatgpt.com/docs/windows/windows-sandbox)는 호환 장치에서 MXC를 권장한다. 이 장치의 Windows build26200.9711/25H2, Codex CLI0.162.0에서 전역 설정을 바꾸지 않는 공식 일회 MXC 진단이 `MXC_OK`·exit0으로 성공했다. 실행 중인 Computer Use를 종료하거나 Windows ACL/보안 설정을 완화하지 않았다.

그 뒤 실제 `uv run`을 같은 sandbox에서 실행하자 별개의 **AppData uv 캐시 저장 거부(Win32 5)**가 재현됐다. 설치 템플릿의 `tool.uv.cache-dir`를 `runtime-data/.uv-cache`로 지정해 작업 폴더 안에서 캐시를 사용하도록 고쳤다. 이는 uv의 [공식 캐시 설정](https://docs.astral.sh/uv/concepts/cache/#cache-directory)을 사용하며 전역 환경변수를 바꾸지 않는다. 초기 실패 R 폴더/로그와 수정 후 R2 새 설치를 분리해 보존했다.

## 제품에 반영한 예방 조치

- Codex 프로젝트 설정에 `features.prefer_mxc=true`를 넣었다. README의 Windows 실행 명령은 `windows.sandbox=mxc`를 해당 실행에 명시하고 workspace-write·요청별 승인을 유지한다.
- `product-doctor.py --check-sandbox`를 추가했다. CLI0.162.0 이상인지 확인하고 실제 managed `:workspace` sandbox 안에서 같은 Python의 `--local-only` doctor·SQLite를 실행한다. 기본 진단은 모델·웹 호출이 없다.
- sandbox 검사 실패는 원래 오류와 함께 반환하고 전체 접근이나 다른 backend로 자동 재시도하지 않는다. IT가 이미 준비한 기존 backend를 선택할 때만 실행자가 `--sandbox-backend configured`를 명시한다.
- uv 캐시를 허용된 작업 폴더 안에 둔다. 캐시·의존성 환경·실행 DB/로그는 제품 ZIP/Git에 포함하지 않는다. 사용자가 별도 캐시 경로를 지정한 경우 그 우선순위를 안내한다.
- MXC 기능/조직 정책/CLI 버전이 다른 PC는 실제 사전 검사 결과로 구분한다. 모든 Windows PC에서 초기 설정 없이 실행된다는 보장은 하지 않는다.

## 실제 실행 결과

| 확인 | 결과 |
| --- | --- |
| 공식 MXC 호환 명령 | `MXC_OK`, exit0,0.484초 |
| 최종 소스의 새 외부 제품 설치·잠금 의존성 설치 | 각각 exit0 |
| 새 제품의 `--check-sandbox` | errors0, sandbox status passed, SQLite 성공. 내부 sandbox 검사1.062초 |
| sandbox 안의 `uv run python product-doctor.py --local-only` | exit0/errors0,1.282초 |
| sandbox 파일/SQLite 경계 검사 | 작업 폴더 내부 읽기·쓰기·SQLite 성공, 외부의 별도 시험용 sibling 파일 쓰기는 PermissionError로 차단, 실제 파일 생성 없음 |
| 최종 R2 일반 코드 진단5항목 | 전부 exit0 |
| 실제 Codex 준비 질문1건 | `gpt-6.1-sol / medium`,11.547초, 터미널 명령1개 exit0, doctor errors0·common_tool_exit_code0, 최종 성공 답변 |
| 관련 로컬 검사 |30개 통과·skip0, 제품 자산 검사 exit0. 잠금 설치·격리·역할·패키징 포함 |

실제 native ID는 기계 판독 기록에 보존했다. CLI에는 on-request를 요청했지만 **비대화식 exec의 실제 turn_context는 approval never**, workspace-write, network_access false였다. 요청한 설정과 실제 관측 설정을 분리했으며 대화식 on-request 승인 창을 새로 조작해 인수한 것으로 설명하지 않는다. 이번 실제 native 성공은 제한 sandbox에서 첫 공통 Tool을 실행할 수 있다는 근거이며 새 상품기획 성공 건수가 아니다.

Windows Computer Use는 별도 `@oai/sky`에서 연결·창 목록 조회에 성공했다. 이전 Q에서 native 앱 제어를 사용할 수 없다고 단정한 설명은 정정한다. UI 입력은 수행하지 않았으며 이 도구의 Codex 화면/보안·권한 설정 자동 조작 금지는 유지했다. 실제 해결은 공식 sandbox 실행 경로와 프로젝트 캐시 설정으로 수행했다. 인증·사용자 전역 설정·프로세스 종료·관리자 요청은 변경/실행하지 않았다.

현재 실패했던 **제한 sandbox 시작·로컬 공통 Tool 실행 경로는 위 Windows/MXC 환경에서 해결됐다.** 새 프론트 연결·브라우저 화면·전체 기획 회귀·Claude 새 세션·제출 릴리스는 별도 작업으로 유지한다.
