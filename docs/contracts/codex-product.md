# Codex 출품 설치·대화 Tool 계약

2026-10-10. 기존 실행기의 Codex 모델이 업무를 수행한다. 설치·조회·검토·저장·export는 Python3.12 stdlib 코드이며 모델 API 또는 Codex 내부 호출 프로그램이 아니다.

## 설치

개발 레포에서 `uv run python adapters/codex/install.py --target NEW_ABSOLUTE_FOLDER`를 실행한다. 개발 레포/상위 폴더/기존 target/상위 Git 프로젝트 안에는 설치하지 않는다. 출품용 AGENTS.md, canonical skills/, 설치 사본 .agents/skills/, Agent 원본·공통 코드·계약·실제 v3 자료·pyproject/uv.lock만 새 폴더에 배치한다. 개발 역할·개발 Skill·개인 설정·인증을 복사하지 않는다. symlink는 요구하지 않는다.

`product-install.json`은 원본 SHA·변환 후 SHA·변환 내용을 기록한다. 사본의 계약 링크와 명령을 .agents/skills 기준으로 바꾼다. wrapper는 상위 경로의 skills/manifest.json과 product-tools/cli.py를 찾아 원본/설치 위치 모두 지원한다. 기존 target을 덮어쓰지 않으며 실패 시 부분 생성 폴더는 검토를 위해 남긴다. manifest는 로컬 지문이며 보안 서명이 아니다.

새 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`, `codex`를 실행한다. Codex 로그인·프로젝트 신뢰·Tool 실행 권한은 실행자의 실제 환경에서 준비한다. 전역/user Skill이 추가로 발견될 수 있다. doctor는 파일·버전·로그인 상태·공통 조회만 확인하며 자동 Skill 선택·업무 품질을 증명하지 않는다. CLI 인수의 실제 결과는 별도 검증 기록으로 관리한다.

## 대화 Tool

모두 기존 product-tools/cli.py 또는 Skill wrapper의 operation이다. 공통 --data/--db와 UTF-8 stdin/--input 입력을 유지한다.

| operation | JSON 입력 | 결과/범위 |
|---|---|---|
| open_request | question, user_submitted=true; 선택 model_id/model_version/document_version/session_id/request_key/prior_turn_id/constraints/runtime | 내부 UUID·PlanningInput·turn 생성. 후속 입력은 같은 session과 이전 turn 연결. model/constraints 생략 시 이전 값 유지 |
| current_request | session_id, request_key | 동일 요청의 현재 turn 또는 needs_input. 새 turn/수정 카운터를 생성하지 않음 |
| save_reviewed_result | session_id, turn_id, result_key, result, assessment, expected_result_version | 구조·검토 기록 정합성 검사와 저장. rejected 후보도 최초0/수정1/2에 포함 |
| export_session | session_id | 요청·turn·실패 후보 원문·검토·usage/invocations를 runtime-data/exports JSON에 쓰고 경로/SHA/건수만 반환 |

`open_request`의 식별자를 사람이 입력할 필요 없다. 모델은 응답 handle을 대화 안에서 보존한다. 새 사용자 질문이 있을 때만 새 request_key를 만들고 자동 재개/오류/수정은 current_request로 읽는다. user_submitted는 호출자 진술이며 인증 경계가 아니다. 동일 키에 다른 질문/조건을 넣으면 request_conflict다. 모델 미확정이면 needs_input 요청만 기록하고 가짜 정확한 turn을 만들지 않는다.

새 질문·조건은 과거 turn을 무효화할 수 있다. previous는 역사적 참고용이고 현재 결과를 재사용하는 허가가 아니다. 새 데이터나 다른 모델은 관련 근거와 제안을 다시 검토한다. 같은 turn의 자료 변경으로 수정 횟수를 초기화하지 않는다.

검토 Tool은 모델이 작성한 assessment의 정합성을 검사한다. 잘못된 해석을 supported로 적는 오류를 자동 증명하지 않는다. 원래 save_result는 하위 구조 검사 경로로 보존하고 실제 업무 AGENTS/Skill은 save_reviewed_result를 사용한다. 전체 native 도구를 강제 차단하는 권한 시스템으로 설명하지 않는다.

상태가 failed/cancelled이거나 수정 한도 초과면 해당 turn을 새 요청 없이 재시작하지 않는다. DB/자료 적재 실패로 상태를 저장할 수 없다면 저장 실패를 설명한다. export는 과거 후보와 미측정 usage를 그대로 유지하고 일부 기록을 전체 네이티브 사용량으로 바꾸지 않는다. 큰 export 전체는 모델 문맥에 전달하지 않는다.

공식 근거: [Codex Skill 발견](https://learn.chatgpt.com/docs/build-skills), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [CLI 설치](https://learn.chatgpt.com/docs/codex/cli), [실제 exec/resume](https://learn.chatgpt.com/docs/non-interactive-mode). 문서를 2026-10-10 직접 조회했다.

대화 응답에는 전체 assessment를 중복하지 않고 검토 요약·최신 결과·짧은 이력만 반환한다. 전체 검토는 export에 보존한다. previous.valid_before_request는 전이 전 값, valid_for_current_context는 새 turn 생성 후 값이다. 추가 질문의 runtime은 이전 turn에서 상속하지 않고 이번 관측만 기록한다.

모델/문서 버전이 복수이면 실제 사용자 확인 뒤 새 요청에서 명시할 수 있다. 같은 모델의 두 버전을 모두 생략하면 이전 정확한 scope를 유지하고, 하나라도 지정하면 해당 선택으로 재조회한다. 중복 후속 요청 응답은 현재 결과와 이전 turn의 handle만 반환해 두 큰 결과를 중복하지 않는다.

S05 추가: open_request_bundle은 open_request와 동일 입력/멱등 계약이며 정확한 scope의 리뷰·사실 원문을 한 번 반환한다. 종류 metadata와 원문 refs를 분리하고 조회20개/종류·응답 바이트 상한의 잘림/누락 ID를 명시한다. 자료 충분성은 판단하지 않는다. 큰 현재 결과는 handle과 detail 조회 안내를 유지한다. save_reviewed_result는 assessment 검사를 transaction 안에서 필수로 수행하여 null/필드 누락도 유효 JSON 후보이면 실패 이력과 수정 횟수에 남긴다. 마지막 저장 응답의 turn을 다음 저장/최종 상태에 사용하며 충돌/재개/외부 변경에만 재조회한다. 원문 의미 검토는 생략하지 않는다.
