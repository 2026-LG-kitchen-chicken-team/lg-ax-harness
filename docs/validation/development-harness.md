# 개발용 하네스 실제 구축·인수검사

기준일 2026-10-10, Windows. 개발 체계 D01-D05 구축·실증을 완료했다. 출품 AI 업무 구현·품질·토큰 절감·시각화 완료를 뜻하지 않는다. Claude adapter 파일과 정적 검증은 완료했으나 팀원 native 인수는 미실행이다.

## 확정·구축

- OSS: revfactory/codex-harness `80f8217b5b6d3f220a31f05f9c0adaf09dac40f4` Apache-2.0, Git blob20파일·LICENSE·NOTICE·원본 지문 보존.
- 메인: Codex 부모 세션. Codex 역할6개, 개발 Skill9개, Claude 역할6개/Skill9개 정규 사본.
- Python3.12.x/uv/uv.lock, 새 stdlib check/receipt/ledger/complete/resume/sync 도구. 별도 LLM 서버·API 실행기·UI 없이 개발 도구 native 실행 사용.
- OpenSpec 파일/Skill/명령/초기 .mjs/npm체계 제거. 최초 재귀 삭제는 자동 검토에 거부되어 파일별 패치와 repo-bound 빈 디렉터리 비재귀 제거로 수행.
- 공식 OpenAI Docs MCP 프로젝트 등록. HTTP initialize/tools-list200, 공개 read-only 도구5개 확인. Codex에서 search/fetch2개만 활성화. Agent 세션 안 MCP 실제 호출과 Claude 등록 발견은 별도 미실증.

## 실제 검사 결과

| 검사 | 실제 결과 | 범위 |
|---|---|---|
| uv lock/sync | exit0, Python3.12.14 | 개발 helper의 표준 라이브러리 환경; 출품 SDK 잠금 아님 |
| 프로젝트 validator/doctor | exit0, 역할6/Skill9, errors=[] | 구조·링크·OSS 지문·Claude drift; 자동 역할 실행 증명 아님 |
| skill-creator quick_validate | 개발 Skill9개 각각 exit0 | 처음 PyYAML 부재와 Windows cp949 실패 후 uv --with PyYAML + UTF-8 child로 성공; 프로젝트 runtime 의존성 추가 안 함 |
| helper unit suite | 22개 모두 통과, exit0 | 실제 명령·실패·timeout/cleanup 실패·미실행·출력 제한·위변경 로그·stale 입력·path/junction·중복 쓰기·선행 실패·idle 재사용·receipt 누락/다른 task·완료후 binding변경·변경 후 resume·변경없는 결과 재사용·drift |
| OpenAI Docs MCP | initialize200/tools-list200 | 공개 endpoint 연결·도구 목록; 추가 모델 API 호출 아님 |
| Codex App Server 발견 | exit0, 신규9Skill 모두 scope=repo/enabled/errors=[]; 상한3 읽기 | 실제 새로운 프로젝트 Skill 발견 |
| persistent Codex native 시험 | exit0, 88.578초 | 실제 자식생성·Skill 읽기·Python checker exit0·메시지 수신·실행 중 interrupt 관찰 |
| 신규 구현 forward test | 실제 native 역할 fallback, Temp 신규 utility와8tests exit0 | 실패/unknown 호출 집계 synthetic 개발 작업; 출품 모델 사용량 수집 구현 아님 |
| 부모 통합·독립 검토 | integration exit0; 독립 reviewer 수정 요청 해결 | 부정 입력 fixture2건 보강 후 정상/unknown/실패/ID/token 검증 |
| ledger freshness/recovery | 최초 완료등록 exit1 stale Skill 거부 → blocked 기록 → 새run resume → 최신 packet 재위임 → completed/idle | 과거 실행을 보존하고 변경 작업 결과 재사용 거부 |
| 최종 완료 | complete --run dev-forward-002 exit0, errors=[] | 현재 bound receipt·로그·코드 지문·장부 검사 |

실제 명령은 `python dev-harness/cli.py check ... -- python -m unittest discover -s tests/dev-harness -v`, `validate`, `complete --run dev-forward-002`다. 검사 실행은 argv/shell=False·명시 cwd·시간 상한을 사용한다. completed receipt는 task/attempt/agent/contract·시각·관련 입력 지문과 연결한다. 명령이 acceptance 의미를 충분히 검사하는지는 독립 reviewer가 판단한다.

독립 검토로 수정한 구현 결함: (1) Windows upstream dependency path가 backslash가 되어 실패하던 한 줄을 as_posix로 패치, (2) 등록 뒤 receipt가 바뀌어도 upstream 단독 완료/resume가 통과하던 경계를 wrapper 재검사·무효화로 보강, (3) taskkill timeout에서 receipt 없이 자식이 남던 경로를 cleanup error 기록·직접 종료로 보강, (4) Git 줄바꿈 변환으로 원본/사본 지문이 깨질 수 있는 경로를 .gitattributes -text로 보존. 원본 vendor는 변경하지 않았고 adaptation manifest에 기록했다.

## 실제 native 식별자와 근거

별도 새 CLI 부모 `01a12175-fa0d-74f3-9c5f-80f8fcbd2828`, 자식 `01a12176-b393-7623-95e4-e2af6e99583d`, 네이티브 반환 이름 `/root/native_persistent_001`. 활성 자식 interrupt의 previous_status=running, 후속 list_agents=interrupted, 대기호출 aborted를 관측했다. **turn 중단이며 세션 closure가 아니다.**

현재 설치 Codex0.162.0의 spawn schema는 custom role 선택·close 인수를 노출하지 않는다. 역할 TOML developer_instructions와 Skill/packet을 메시지로 전달하는 fallback을 실제 사용했다. TOML sandbox/model 자동 적용과 역할메시지 exact-match는 검증하지 않았다. 원문 메시지 payload 일부가 저장 로그에서 암호문이므로 unknown으로 남겼다. ephemeral부모의 spawn은 rollout 부재로 실패했고 persistent부모로 원인을 수정해 성공했다. Windows native Get-Content 기본인코딩에서 일부 한국어 깨짐을 관측해 UTF-8 명시 지침을 추가했다.

개발 forward test는 실제 네이티브 `/root/agent_skill_design_review`를 명시적 agent_skill_worker 역할로 전환·위임했다. 작성은 지정 Temp에서만 수행했고 부모만 레포 통합 파일을 썼다. 독립 `/root/upstream_import_audit`는 reviewer 지침/Skill을 읽고 읽기 전용 검토했다. 장부가 이 Agent들을 생성·실행한 것은 아니다.

원문 로그/SQLite/개인 환경은 Git 제외한다. 로컬 증거:

- `.harness/checks/e8989570ff1b41908d339c21f1883174/receipt.json` 및 stderr.log: 최종 helper20검사 exit0.
- `.harness/checks/1c841cd9896b484f98d34c2f5b2550f1/receipt.json`: 새run bound 통합 exit0.
- `.harness/runs/dev-forward-001/`: stale 거부·blocked 과거 기록.
- `.harness/runs/dev-forward-002/`: 최신 packet·completed 결과·관찰 idle.
- `C:/Users/user/AppData/Local/Temp/lg-ax-native-codex-5f07380bfc7645c180dd72b74d245389/`: native-acceptance-report/persistent-acceptance-evidence/rollout·새9Skill 발견 근거.
- `C:/Users/user/AppData/Local/Temp/lg-dev-forward-qz4gu5ot/`: 실제 신규 helper·8tests·두 실행 receipt.

위 로컬 기록은 재현·감사 근거이며 서명된 보안 증명이 아니다. Git에는 소스·계약·OSS 지문·검사 코드와 이 요약만 관리한다.

## 사용량·남은 경계

개발 native 로그인 사용량과 출품 API 비용을 분리한다. 이번 native CLI 부모4회/자식1회를 실제 실행했고 해당 probe별 input/output/cache/reasoning 사용량은 Temp 보고서에 있다. 전체 루트·독립 리뷰·forward test 호출 usage는 일부 미측정이므로 전체 개발 비용/토큰과 절감률을 산출하지 않았다. 별도 유료 모델 API 호출은 하지 않았다. 300,000원 예산의 API 지출로 개발 구독 토큰을 환산하지 않는다.

Claude CLI/로그인 환경이 현재 PC에 없어 D06b의 새 세션 발견·위임·실제 실행·Codex→Claude 인수는 미실행이다. .claude 설정/사본은 전달 가능하고 정적/drift 검사는 통과했다. CI Windows/Ubuntu workflow는 구성했으며 원격 GitHub 실행은 미실행이다. 최종 업무 runtime/API/모델, 출품 데이터·AI 심사 입력 평가·제출·시각화는 P07/P08/S01-S06의 별도 작업이다. J01-J18은 설계 사례이며 이번 결과로 업무 AI 통과를 주장하지 않는다.

## 새 checkout 보존 검사

Windows Temp의 독립 Git index에서 core.autocrlf=false/true 두 방식으로 새 checkout을 만들었다. 두 checkout 모두 validator exit0과 당시 전체20tests exit0을 확인했다. 관리 Skill·Claude 사본·OSS bytes가 보존됐으며 user repo index는 변경하지 않았다. Linux OS 실제 실행은 아니며 원격 CI를 통과했다고 설명하지 않는다. 근거: `C:/Users/user/AppData/Local/Temp/lg-dev-fresh-checkout-i_24u6tb/result.json`. 이후 완료 binding/변경없는 결과 재사용2개를 추가해 로컬 최종22tests를 통과했다.

최종 README 명령 경로로 `uv sync --locked`, `uv run python dev-harness/cli.py doctor`, `sync-claude --check`, 22검사 실행, `complete --run dev-forward-002`를 다시 확인했다. 모두 exit0이며 JSON/packet 출력은 UTF-8을 명시한다. 문서 상대 링크33개와 git diff --check도 통과했다. 변경은 로컬 작업 트리에 있으며 커밋·푸시·원격 CI 실행은 하지 않았다.
