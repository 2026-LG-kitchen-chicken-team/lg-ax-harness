# 출품 실행 방식

2026-10-11 신규 요청 기반 경로(v7.0): 사용자가 새 모델 조사·등록까지 확장하도록 승인했다. 기본 설치는 빈 catalog이며 native AI가 질문을 해석해 실제 근거를 조사하고 정확 모델/출처를 등록한다. open_request 원문 보존 → 연구 사건 → 같은 요청 resolve_request_bundle → 기획/검토/저장으로 연결한다. 특정 질문·제품 enum·기본5모델 답안 선택 경로를 사용하지 않는다. Claude 중복 미확인 null·공식 원문/해석 분리 지침을 보완했다. 현재 구현/코드 검증과 실제 AI 검증은 [최신 작업 기록](../validation/request-driven-20261011.md)으로 구분한다. 아래 과거 기본자료·미채택·대기 설명은 당시 이력이다.


갱신2026-10-11. 사용자 선택은 공통 상품기획 Agent·Skill·Python 코드를 기존 생성형 AI 실행기에 연결하는 방식이다. 별도 모델 API 프로그램·Codex 내부 호출 서버는 초기 경로로 추가하지 않는다. Codex/Claude 개발 도구와 출품 실행을 구분한다.

| 실행기 | 설치 위치 | 현재 상태 |
|---|---|---|
| Codex | .agents/skills, AGENTS.md | 주 제출 기준. Windows CLI0.162.0·Python3.12 실제 업무 기록. 세 제품군 신규 인수는 별도 기록 |
| Claude Code | .claude/skills, CLAUDE.md → @AGENTS.md | 사본/공통 Tool 준비. native 미인수·후순위. 보완 완료 후 최길웅에게 요청·정이량에게 결과 회신 |
| Gemini CLI | 신규 설치/패키지 제외 | 사용자 결정으로 철회. 과거 인증 실패·사본 준비 이력 보존 |

[최신 결정](kitchen-scope-20261011.md)이 과거 세 실행기 목표를 대체한다. Claude 접근이 없어도 Codex 제출 준비를 막지 않는다. 실행기를 자동 팀으로 묶거나 실패 시 다른 제공사로 자동 전환하지 않는다.

공통 구성은 Theme A 상품기획 Agent1개·업무5Skill+조건부 외부 조사1Skill이다. 냉장고·전자레인지·식기세척기 정확 모델/문서 scope와 catalog의 family를 검사한다. 필요한 Skill만 읽고 일반 코드가 조회·인용/지문·제약·저장·이력·재사용 무효화를 처리한다. 모델의 판단·원문 의미·실제 성능을 코드가 보증하지 않는다.

1. 실행자가 자신의 CLI·계정·폴더 신뢰·권한을 준비한다.
2. 제품 ZIP을 개발 레포 밖에 풀고 uv sync --locked와 uv run python product-doctor.py로 준비한다.
3. 설치 폴더에서 Codex를 열고 정확 모델을 포함한 자연어 업무를 요청한다. 상세 불편/내부ID는 입력할 필요 없다.
4. 같은 대화 후속은 업무 session/turn과 연결한다. 제품·자료·조건 변경은 이전 결과를 역사적 참조로 보존하고 새로 대조한다.
5. 결과·근거 URL/위치·검토·최신 receipt/export를 확인한다. 근거 부족/오류·수정 상한은 숨기지 않는다.

Codex는 adapters/codex/install.py --target NEW_ABSOLUTE_FOLDER, Claude는 adapters/claude/install.py --target OTHER_NEW_FOLDER를 사용한다. 원본 skills/ 전체와 발견 위치의 정규 사본을 관리한다. 전역 설정·계정·다른 레포를 바꾸지 않는다. [Codex 계약](../contracts/codex-product.md), [Claude 준비](../contracts/portable-product.md).

파일 설치/doctor 통과는 인증·Skill 발견·권한·AI 품질 통과가 아니다. native 내부 모델 재시도·전체 청구는 우리 Tool의 통제/관측 범위 밖일 수 있다. 관측하지 못한 사용량은 unknown이다. 사용자 예산300,000원과 보유 크레딧을 토큰/호출 수/API 잔액으로 환산하지 않는다.

별도 관찰 화면은 일반 코드 수집/표시이며 모델 호출·로그 문맥을 추가하지 않는다. 웹팀은 별도 PM이 개발 중이며 구현 원본 수신/연결 인수 전 지원 완료로 표시하지 않는다.

2026-10-10까지의 Claude/Gemini 기록은 [native 접근](../validation/native-access-20261010.md)과 [이전 사본 검사](../validation/portable-product.md)에 보존한다. 최신 활성 지원 목록으로 읽지 않는다.
