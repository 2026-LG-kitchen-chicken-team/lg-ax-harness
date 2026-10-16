# LG AX Codex 상품기획 하네스

질문의 제품군·정확 모델·불편에 맞춰 실제 리뷰와 제품 근거를 조사하고 개선 기획을 작성한다. 기본 자료는 빈 catalog이며 기존 예제 제품/답변은 설치하지 않는다. native 검색·웹 도구 사용이 가능한 실행 환경이 필요하다. 조사한 원문·관측일·모델/문서 버전은 runtime-data에 보존하며 재사용 범위를 밝힌다. 자료가 없거나 접근이 막히면 보류하고 원질문·실패 이력을 저장한다. 일부 사례를 제품군 전체 불편이나 발생률로 일반화하지 않는다. Codex가 주 실행기, Claude Desktop Code의 제한 회귀 범위는 릴리스 검증 기록을 확인, Gemini는 지원 철회다.

Python3.12, uv, Codex CLI와 실행자 자신의 Codex 로그인이 필요하다. 별도 LLM API key·환경변수·필수 MCP/플러그인은 요구하지 않는다. 모델 통신과 이용 한도는 Codex 계정에서 발생한다. 전체 준비 순서와 오류별 조치는 [심사 실행자 첫 설정](docs/contracts/runtime-access.md)을 따른다.

이 폴더에서 PowerShell/터미널을 열고:

```powershell
uv sync --locked --python 3.12
uv run python product-doctor.py --local-only
codex login
codex login status
uv run python product-doctor.py
# Windows: CLI 0.162.0 이상과 MXC 호환 환경을 실제 확인
uv run python product-doctor.py --check-sandbox
codex --search --sandbox workspace-write --ask-for-approval on-request --config 'windows.sandbox="mxc"' --model gpt-6.1-sol --config 'model_reasoning_effort="medium"'
```

처음에는 공식 안내에 따라 uv와 Codex CLI를 설치한다. `uv sync --locked --python 3.12`는 Python3.12와 잠금 의존성을 로컬 환경에 준비한다. 이미 로그인돼 있으면 `codex login`은 생략하고 `codex login status`를 확인한다. 설치기는 전역 Python 패키지나 설정을 변경하지 않는다. pip 대체 경로는 Python3.12 가상환경에서만 사용하며 실행 권한 안내의 명령을 따른다. 의존성 가져오기 검사는 파일 제작·레이아웃 검수나 실제 AI 업무 검증을 대신하지 않는다.

기본 결과는 save_and_export(report:false)의 웹 전달 데이터다. delivery_ready/web_ready와 현재 web_result의 SHA/binding을 확인하고 원문·근거·검토/조사 이력을 같은 버전으로 전달한다. 설치된 뷰어는 이 데이터를 일반 코드로 읽어 기획자 화면과 별도 단일 HTML 보고서를 만든다. AI에게 HTML 레이아웃을 다시 작성하게 하거나 PDF/DOCX·이미지 검수를 요구하지 않는다. 명시 파일 요청에만 report:true와 기존 옵션을 사용한다. 웹 데이터 오류는 prepare_web_result로 같은 session/turn/version을 복구하고, 명시 파일 오류만 deliver_result로 복구한다.

위 Sol/medium은 동일 자료 비교에서 채택한 테스트 프로파일이다. 사용 중인 계정의 `/model`에서 지원 여부를 확인한다. 다른 모델의 결과를 같은 검증 결과로 간주하지 않는다. 실행 옵션은 [공식 Codex 설정 안내](https://learn.chatgpt.com/docs/developer-settings#change-settings-for-one-run)를 따른다.

실행 권한과 별도 관찰 화면의 준비·실시간 갱신은 [실행 권한 안내](docs/contracts/runtime-access.md)를 따른다. 기본은 제품 작업 폴더 쓰기와 요청별 승인이다. 서브에이전트도 부모 권한을 상속하며 역할 지침의 읽기 전용은 별도 OS 샌드박스가 아니다. 일반 권한에서 실행기가 준비되지 않으면 그 오류를 해결한 뒤 진행하며 전체 접근으로 자동 전환하지 않는다.

화면 연결(제품 설치 폴더에서):

```powershell
uv run python web/prototypes/visual-viewer/viewer.py install --codex .
uv run python web/prototypes/visual-viewer/viewer.py open .
```

Codex의 `/hooks`에서 본인이 훅을 확인·신뢰한 후 실행하면 저장한 결과 화면을 갱신한다. 별도 보고서는 `uv run python web/prototypes/visual-viewer/build_view.py --export <현재 세션 JSON> --out-dir runtime-data/visual-viewer --standalone runtime-data/visual-viewer/report.html --mode ops`로 만든다. 생성은 추가 모델 호출 없이 수행한다. 선택 원문 전체와 결과에 인용한 근거를 구분하며 수정 전 해석은 현재 결과에 적용하지 않는다.

첫 실행에서는 Codex가 안내하는 계정 로그인과 프로젝트 신뢰/권한 설정을 진행한다. 아직 CLI가 없다면 [공식 Codex 설치 안내](https://learn.chatgpt.com/docs/codex/cli)를 따른다. uv 설치는 [공식 안내](https://docs.astral.sh/uv/getting-started/installation/)를 따른다. 자동 설치 도구가 사용자 전역 설정이나 인증 파일을 변경하지 않는다.

첫 질문 예:

```text
냉장고에서 사용자가 불편해하는 점을 찾아서 개선 아이디어 한 개만 제안해 줘.
전자레인지 사용 불편을 실제 리뷰에서 찾아 개선안을 제안해 줘.
식세기 건조가 불편한 사람들을 위해 어떻게 개선하면 좋을까?
```

추가 질문 예:

```text
냉동실 문제는 빼고 같은 냉장고 자료에서 다른 문제를 찾아 줘.
방금 조사한 모델 하나를 골라 앞서 정한 조건을 유지해 검토해줘.
```

내부 세션 ID·요청 키를 직접 입력할 필요 없다. 최종 요약과 실제 저장 영수증(receipt), export 경로·SHA를 확인한다. 기획 turn 이전 조사 보류는 receipt 대신 request 상태와 export를 전달한다. 전체 결과·의미 검토·원문 인용은 runtime-data/exports의 세션 JSON에 보존된다. 저장 승인만으로 의미 검토 통과를 보증하지 않는다. 근거 부족이면 보류, 제품군 자체가 모호하거나 보유 제품의 치수·안전 판단에 정확 모델이 필요하면 확인 요청을 반환한다. 제품군 탐색에 모델코드를 강제하지 않는다. 개발용 역할6개/Skill9개는 이 폴더에 설치하지 않는다.

대화를 다시 열 때 Codex의 `codex resume`에서 해당 대화를 선택한다. 기록을 재개했다는 이유로 새 업무 turn을 시작하지 않는다. 모델/자료/조건이 바뀌면 과거 결과를 새 결과처럼 재사용하지 않는다. user/global Skill은 사용자의 설정에 따라 추가로 보일 수 있다.

doctor의 `--local-only`는 CLI 설치·로그인 전에 로컬 설치를 확인한다. 기본 실행은 CLI 버전·로그인 상태도 확인한다. 두 경우 모두 파일 지문·의존성과 로컬 공통 Tool/SQLite를 검사하며 native 세션 권한·네트워크·모델 접근은 별도다. 자동 Skill 선택·AI 결과 품질·모든 Tool 권한을 보증하지 않는다. 지원/검증 범위는 원본 레포의 docs/validation/codex-product.md를 확인한다. 원문 로그·DB·개인 인증·의존성 환경은 공유하지 않는다.

저장된 결과를 읽는 선택형 시각자료 뷰어는 `web/prototypes/visual-viewer/README.md`를 따른다. 기본 설치에서는 자동 훅을 등록하지 않는다. 필요하면 `python web/prototypes/visual-viewer/viewer.py install --codex` 또는 `--claude`로 해당 폴더의 훅만 등록하고 CLI의 프로젝트 신뢰 설정을 확인한다. `status`, `open`, `uninstall`로 상태·화면·해제를 관리한다. 뷰어는 export를 읽으며 업무 질문이나 모델 실행을 대신하지 않는다. 원 개발 소스는 최길웅의 PR #6이고 이번 통합에서는 경로 검사와 출처 종류 메타데이터 연결을 보강했다.

Windows 제품 설정은 호환 장치에서 공식 권장 MXC를 선호한다. 위 Windows 명령은 MXC를 해당 실행에 명시하며 저장된 전역 설정을 바꾸지 않는다. Linux/macOS에서는 Windows 전용 진단과 `windows.sandbox` 옵션을 제외한다. `--check-sandbox`는 실제 sandbox 안에서 로컬 doctor/SQLite까지 실행하며 모델 호출은 없다. MXC 호환 실패는 자동으로 전체 접근이나 다른 backend로 전환하지 않고 원인과 공식 준비 절차를 안내한다. 이미 관리자가 준비한 기존 backend를 명시해 확인하려면 `--check-sandbox --sandbox-backend configured`를 사용하고 해당 조직 설정을 따른다.

이 PC의 과거 setup refresh 오류는 기존 sandbox의 실행 중 runtime 파일 ACL 갱신에서 Win32 공유 위반32가 발생한 사례다. 현재 MXC 경로의 실제 확인 범위와 별개로 과거 실패는 보존한다. 실행자는 `/permissions`와 실제 승인 요청을 확인하며 설치 도구는 권한·전역 설정·인증을 바꾸지 않는다.

uv의 캐시는 프로젝트 설정으로 `runtime-data/.uv-cache`에 둔다. Windows sandbox가 바꾸는 기본 AppData 캐시 경로에서 쓰기가 막히는 문제를 줄이며, 이 캐시와 의존성 환경은 제출 ZIP에 넣지 않는다. 사용자가 `UV_CACHE_DIR`를 따로 지정했다면 그 값이 우선하므로 작업 폴더 안의 허용 경로인지 확인한다.

## Claude Desktop Code에서 사용

제품 source에서 adapters/claude/install.py로 새 폴더에 Claude 사본을 만든다. 그 폴더에서 uv sync --locked와 product-doctor.py를 확인한 뒤, 로그인된 Claude Desktop의 Code에서 기본 작업 폴더로 선택하고 설치된 AGENTS.md/CLAUDE.md를 적용한다. 단순 추가 접근 폴더와 기본 작업 폴더는 구별한다. Claude 자체 로그인·권한은 사용자가 관리한다. Desktop에서의 실제 실행 검증은 별도 CLI의 로그인 검증을 대신하지 않는다. latest 지원 범위·실패·관측 사용량은 해당 제품 릴리스 기록을 따른다. doctor의 local_only/native_verified=false는 설치 검사만 했다는 뜻이며, 별도 실제 업무 기록을 자동 인증하지 않는다.

자연어 요청에 맞는 Skill 자동 선택이 기본이다. `/skills` 또는 `$evidence-retrieval` 등 설치된6개 이름으로 명시 호출해도 같은 업무 경로를 쓴다. product-planning은 메인 지침이고 별도7번째 호출 Skill이 아니다. 선택 자식은 .codex/agents의 product_official_researcher/product_review_researcher/product_evidence_reviewer 역할명을 자연어로 지정한다. Claude의 /Skill이름·@ subagent 선택과 구별하며 Codex @agent 명령을 만들지 않는다.
필요 본문이 현재 문맥에 없으면 get_work_instructions로 main/선택 Skill/payload만 받고 동일 문맥·지문은 known_context 신고로 중복 반환을 생략한다. 반환 receipt는 독해·이해·적용 인증이 아니다. docs/contracts/instruction-loading.md를 따른다.
공식 안내: https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills
