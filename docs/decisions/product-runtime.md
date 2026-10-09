# 출품 실행 방식 결정

결정일: 2026-10-10. 사용자가 선택한 출품 실행 방식의 기록이다. 구현·호환성·품질 검증 완료 보고가 아니다. [공식 요구와 사용자 조건](../competition-requirements.md), [업무 계약](../plans/product-harness.md), [작업 상태](../plans/development-harness.md)를 함께 따른다.

## 사용자 선택

공통 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 각각 연결한다. 실행자는 검증된 환경 중 하나를 설치·인증하고 출품 폴더에서 자연어로 업무 요청과 후속 질문을 입력한다. 기존 Agent 실행기가 모델 연결과 기본 Agent 실행을 담당한다.

우리 코드가 모델 API를 직접 호출하는 독립 실행 프로그램과, 우리 실행기가 내부에서 Codex를 호출하는 방식은 초기 출품 실행 경로로 채택하지 않는다. 설치·준비 검사·자료 조회·결과 검증을 위한 일반 코드 CLI는 이 선택과 양립한다. 원격 모델 통신은 해당 실행기에서 발생하므로 오프라인·무과금 실행이라는 뜻이 아니다.

## 공통 업무와 환경별 연결

- 공통 원본: `skills/`의 출품 업무 Skill5개+조건부외부조사1개, 새로 수집한 실제 제품·고객 리뷰, 조회·검증 코드, 입력·근거·결과·상태 계약, 같은 심사 입력 평가 사례. [컨설팅](../consultation/2026-10-10.md)에 따라 합성 자료는 시험 전용으로 분리한다.
- 환경별 연결: 업무 진입 지침, Skill 설치·발견, Tool 명령과 경로, 작업 권한, 추가 질문과 상태 연결, 실제 관측 가능한 기록과 사용량.
- 각 환경이 같은 Skill 형식을 읽는 것과 같은 업무를 올바르게 수행하는 것은 별도로 검사한다. 서브에이전트·권한·훅·사용량 기능까지 공통이라고 가정하지 않는다.
- 출품의 초기 Agent는 상품기획 역할 한 개다. 업무 Skill 5개를 Agent 5개로 늘리지 않으며 개발 역할 6개·Skill 9개를 출품 구성으로 설치하지 않는다.
- 실행 상태·수정 상한·근거·결과 계약은 우리 코드로 검증한다. 실행기가 내부적으로 수행하는 모델 호출·재시도 전체를 우리 코드가 통제한다고 주장하지 않는다. 관측하지 못한 사용량은 미측정으로 남긴다.

## 설치·실행 설계

공통 자료·입출력·상태 도구의 로컬 구현은 [공통 도구 계약](../contracts/common-tools.md)을 따른다. 업무 Skill 원본과 세 환경의 파일 설치기를 구현했다. Codex는 [실제 native 인수](../validation/codex-product.md), Claude/Gemini는 [파일·공통 Tool 준비 검사](../validation/portable-product.md)를 기록했으며 두 환경의 실제 발견·업무/예외는 미검증이다. 사용자 입력은 모델 선택 중심이며 내부 세션·요청 키·버전은 어댑터/도구가 관리한다.

Codex는 개발 레포에서 `uv run python adapters/codex/install.py --target NEW_ABSOLUTE_FOLDER`로 새 별도 폴더를 만든다. 그 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`, `codex`를 실행한다. [설치 계약](../contracts/codex-product.md)을 따른다. Claude/Gemini는 각각 `adapters/claude/install.py`, `adapters/gemini/install.py`로 서로 다른 새 폴더를 만들며 [환경별 준비 계약](../contracts/portable-product.md)에 따라 실행자 자신의 CLI 설치·인증·신뢰/동의·native 인수가 추가로 필요하다.

1. 실행자가 지원 목록에서 Agent 실행기 하나를 선택해 설치하고 자신의 계정으로 인증한다.
2. 출품 ZIP을 개발 레포 밖의 별도 폴더에 풀고 공통 업무 코드의 고정 의존성을 설치한다.
3. 프로젝트 범위 설치 도구가 선택한 실행기의 발견 위치에 업무 Skill의 정규 파일 사본과 업무 지침을 배치한다. 사용자 전역 설정·Skill을 변경하지 않고 symlink를 필수로 요구하지 않는다.
4. 준비 검사로 파일·데이터 지문/버전·공통 Tool·발견 가능한 CLI 버전을 확인한다. 인증·Skill 발견·Tool 권한·실제 업무는 별도 native 인수로 확인한다. CLI가 없어 local_only인 결과를 지원 완료로 표시하지 않는다.
5. 그 폴더에서 실행기를 열고 자연어 업무 요청을 입력한다. 추가 질문은 기존 실행과 연결하며 제품·자료 버전 변경 시 관련 결과를 무효화한다.
6. 실제 결과·근거·상태를 공통 코드로 확인하고 실행 기록을 보존한다. 내부 기록을 모델 문맥으로 반복 전달하지 않는다.

Codex의 프로젝트 발견 위치는 `.agents/skills/`, Claude Code는 `.claude/skills/`, Gemini CLI는 문서에 명시된 후보 중 `.gemini/skills/`를 이번 adapter 경로로 사용한다. 원본 `skills/` 전체와 생성 사본의 버전·지문을 관리한다. 이 경로는 출품 설치 폴더 안에서만 사용하며 현재 개발 Skill 폴더를 덮어쓰지 않는다.

로그인 인증과 프로젝트 상대 데이터 경로를 기본으로 설계한다. 환경변수·외부 MCP·플러그인은 실제 연결에 필요한 경우에만 추가한다. 인증·계정 이용량은 실행자가 준비하며 개인 인증 파일을 ZIP에 넣지 않는다. 심사자의 실제 설치·인증 가능 여부는 미확인이며 README만으로 해결되었다고 간주하지 않는다.

## 지원 목표와 검증 순서

| 환경 | 목표 | 출품 업무의 현재 검증 상태 |
|---|---|---|
| Codex | 첫 구현·전체 업무·다중 턴·예외·Skill 개별 실행 | Windows0.162.0 전체 접근 모드에서 실제 설치·발견·첫/후속/보류/확인 요청·오류/저장/export 확인. [S05 제한된 비교·추가 입력](../validation/s05-followup.md) 수행. workspace-write 준비 오류와 전체 비용·효과·일반화 미검증 유지 |
| Claude Code | 공통 업무 원본을 환경별로 연결하고 동일 평가 수행 | 파일 설치·공통 Tool·잠금 환경 준비 통과. 로그인/발견·업무·예외·대화/usage native 미검증; 개발 D06b와 별개 |
| Gemini CLI | 공통 업무 원본을 환경별로 연결하고 동일 평가 수행 | 파일 설치·공통 Tool·잠금 환경 준비 통과. 로그인/폴더 신뢰/Skill 동의·실제 발견/업무/예외/usage 미검증 |

Codex부터 실제 업무를 검증하고 Claude Code, Gemini CLI 순서로 확장한다. 설치 파일만 있거나 정적 검사만 통과한 환경은 지원 완료로 표시하지 않는다. 모델 이름·설정·실행기 버전을 기록하고 정상·근거 부족·모델 혼동·추가 질문·Tool 실패를 각 환경에서 실제 실행한다. 검증 실패나 계정 접근 부재는 미검증/실패로 남긴다. 세 실행기를 한 자동 팀으로 묶거나 실패 시 다른 제공사로 자동 전환하지 않는다.

## 비용과 관찰

예산 제약은 유지한다. 사용자는 Codex 크레딧 62,000개 보유 및 본인 Claude·Google 이용 자원 부재를 알렸다. 사용자 진술이며 현재 잔액·유효기간·모델 접근은 미검증이다. 팀원의 Claude 개발 환경과 사용자 본인의 이용 자원을 구분한다. 크레딧을 토큰 수·실행 횟수·모델 API 잔액으로 환산하지 않는다. 개발 사용량과 출품 평가 사용량은 별도로 기록한다.

시각화는 별도 관찰 프로그램의 후순위 작업이다. 설치·시연·질문 입력을 위해 자체 웹 화면이나 모델 API 직접 연결을 추가하지 않는다. 공통 Tool의 실제 실행 기록과 환경별로 관측한 이벤트만 내보내며 관측하지 못한 Agent·Skill·메시지를 만들어 표시하지 않는다.

## 공식 기능 근거

- [Codex Skill 발견·호출](https://learn.chatgpt.com/docs/build-skills), [Codex 설치·로그인](https://learn.chatgpt.com/docs/codex/cli)
- [Claude Code Skill과 확장](https://code.claude.com/docs/en/skills), [Claude 설치·인증](https://code.claude.com/docs/en/quickstart)
- [Gemini CLI Skill 발견·설치](https://geminicli.com/docs/cli/using-agent-skills/), [Gemini 인증](https://geminicli.com/docs/get-started/authentication/)

공식 문서의 지원 기능은 구현 가능성의 근거이며 우리 업무의 동작·품질·토큰 절감 실증을 대신하지 않는다.
