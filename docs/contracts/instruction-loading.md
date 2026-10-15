# 필요한 지침의 본문 전달

자연어 업무 요청에서 native 실행기가 필요한 Skill을 선택하는 경로가 기본이다. Codex는 `/skills` 또는 `$evidence-retrieval` 같은 설치된 이름, Claude는 `/evidence-retrieval` 같은 이름으로 명시 호출할 수 있다. 두 경로 모두 같은6개 업무 Skill·공통 Tool을 사용한다. `product-planning`은 메인 지침이며7번째 Skill이 아니다. Claude의 `@` subagent 선택은 `.claude/agents`의 선택 역할이다. Codex 자식은 `.codex/agents`의 등록 역할명을 자연어로 지정하며 Codex `@agent` 명령을 만들지 않는다. 자동 선택을 막는 `disable-model-invocation:true`를 넣지 않는다. 실제 발견·권한·지원 문법은 native 버전의 관측 범위를 따른다.

[Codex 공식 안내](https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills) · [Claude Skills](https://code.claude.com/docs/en/skills) · [Claude subagents](https://code.claude.com/docs/en/sub-agents#invoke-subagents-explicitly)

## get_work_instructions

현재 업무의 판단에 필요한 본문이 문맥에 없을 때 먼저 호출한다. 이미 같은 본문이 문맥에 있으면 다시 읽지 않는다. 새 업무 요청·판단 범위로 문맥이 바뀌거나 지침 버전이 바뀌면 재전달한다. 지침을 받으려고 모든 Skill·역할을 로드하거나 도구 목록·파일 전체를 반복 출력하지 않는다. 별도 모델 호출·자체 API 실행기·가짜 슬래시 parser를 추가하지 않는다.

각 업무 Skill의 `scripts/run.py get_work_instructions --input runtime-data/instructions.json` 또는 공통 CLI를 쓴다. 이 operation은 catalog 선택·업무 DB 없이도 작동하며 기존 근거 bundle의64KiB 예산을 소비하지 않는다. 본문이 너무 크면 output_limit이며 본문이나 근거를 잘라 성공 처리하지 않는다. 필요한 ID를 나누어 요청한다.

```json
{"context_key":"actual-request-or-current-context-id","instruction_ids":["needs-structuring"]}
```

`context_key`는 호출자가 현재 실제 request/turn/context를 식별하여 제공한다. 다른 질문·판단 범위에는 같은 키를 재사용하지 않는다. 코드는 키 일치만 비교하며 실제 native 문맥의 유지/압축/상실을 인증하지 않는다. 단순 후속 설명이 같은 문맥을 유지하고 같은 지침이 남아 있으면 재반환하지 않는다. 문맥 압축으로 본문이 사라졌으면 known_context를 신고하지 않는다.

허용 ID는 `main`, `payload`와6개 Skill 이름이다: `evidence-retrieval`, `web-evidence-collection`, `needs-structuring`, `feature-comparison`, `concept-writing`, `review-and-revise`. `main`은 `agents/product-planning.md`, `payload`는 저장 양식이다. 역할·임의 파일 경로를 ID로 받지 않는다. 필요한 것만 선택하며 payload는 실제 후보 작성 시에만 받는다.

응답은 선택한 지침 각각의 `instruction_id/name`, `canonical_path`, 선택적 `native_path`, 실제 `returned_path`, 원본 바이트의 `source_sha256`, 반환 바이트의 `returned_body_sha256`, 본문 `body`, `manifest_sha256`을 포함한다. 설치본에서는 product-install의 원본 결속·실제 지문과 경로 변환을 함께 확인한다. native 사본은 명령/링크가 변환되어 원본 SHA와 다를 수 있다. 개발 소스에서는 canonical 본문을 사용한다. 설치·manifest는 로컬 무결성 근거이며 위변조 방지 서명이 아니다.

선택적 `expected_manifest_sha256`은 원하는 현재 manifest를 고정한다. 이미 문맥에 있다는 신고는 다음 형식으로 준다. 이전 응답 metadata에서 실제 값을 사용한다.

```json
{"context_key":"actual-request-or-current-context-id","instruction_ids":["needs-structuring"],"known_context":[{"instruction_id":"needs-structuring","context_key":"actual-request-or-current-context-id","manifest_sha256":"<64 hex>","source_sha256":"<64 hex>","returned_body_sha256":"<64 hex>"}]}
```

문맥 키·manifest·원본·반환 본문 SHA가 모두 같으면 `already_in_context_reported`이며 이 응답에 body를 넣지 않는다. 하나라도 달라지면 실제 본문을 반환한다. 신고가 있더라도 선택 파일의 무결성 검사를 생략하지 않는다. 응답의 receipt에는 실제 body를 반환한 ID와 신고로 생략한 ID 및 반환 payload SHA를 구분한다.

## 증거의 의미

- 디스크에서 선택 파일을 읽고 지문을 검사한 사실은 코드의 로드 관측이다.
- `returned_to_caller` receipt는 선택 본문/metadata를 코드가 반환한 범위다. stdout가 native Tool 결과로 전달됐는지는 실제 공개 Tool 응답·SHA로 추가 확인한다. 리다이렉트한 파일을 모델이 읽었다고 추정하지 않는다.
- `already_in_context_reported`는 호출자의 문맥 보유 신고이며 이번 본문 전달 사건이 아니다. applied/읽음/적용 신고도 별도 자기신고다.
- 원문 의미·지침 이해·출력 적용·품질은 독립 출력 검토로 판단한다. wrapper 호출·설치·지문·반환·신고만으로 자동 인증하지 않는다. 기존 semantic_status/acceptance_ready·모델/권한/시간/수정 상한을 변경하지 않는다.

초기 manifest 정체성·허용 ID·선택 원본/설치 변환·경로·출력 크기를 검증한다. 정션/심볼릭 링크, 절대/상위 경로, 파일 변조·잘못된 버전은 오류다. 공통코드는 지침 파일을 실행하지 않으며 추가 LLM·native Agent를 호출하지 않는다.
