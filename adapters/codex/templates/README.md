# LG AX Codex 상품기획 하네스

질문의 제품군·정확 모델·불편에 맞춰 실제 리뷰와 제품 근거를 조사하고 개선 기획을 작성한다. 기본 자료는 빈 catalog이며 기존 예제 제품/답변은 설치하지 않는다. native 검색·웹 도구 사용이 가능한 실행 환경이 필요하다. 조사한 원문·관측일·모델/문서 버전은 runtime-data에 보존하며 재사용 범위를 밝힌다. 자료가 없거나 접근이 막히면 보류하고 원질문·실패 이력을 저장한다. 일부 사례를 제품군 전체 불편이나 발생률로 일반화하지 않는다. Codex가 주 실행기, Claude Desktop Code의 제한 회귀 범위는 릴리스 검증 기록을 확인, Gemini는 지원 철회다.

Python3.12, uv, Codex CLI와 실행자 자신의 Codex 로그인이 필요하다. 별도 LLM API key·환경변수·필수 MCP/플러그인은 요구하지 않는다. 모델 통신과 이용 한도는 Codex 계정에서 발생한다.

이 폴더에서 PowerShell/터미널을 열고:

```powershell
uv sync --locked
uv run python product-doctor.py
codex --search
```

`uv sync --locked`는 이 폴더의 잠금 파일로 python-docx·openpyxl·reportlab·Pillow·pypdf와 하위 의존성을 로컬 환경에 설치한다. 설치기는 전역 Python 패키지나 설정을 변경하지 않는다. pip 기반 환경은 `python -m pip install --require-hashes -r product-tools/requirements.lock`으로 같은 잠금 요구사항을 설치할 수 있다. 의존성 가져오기 검사는 파일 제작·레이아웃 검수나 실제 AI 업무 검증을 대신하지 않는다.

기본 결과는 save_and_export(report:false)의 웹 전달 데이터다. delivery_ready/web_ready와 현재web_result 파일SHA/binding을 확인하고 원문·근거·검토/조사 이력을 같은버전으로 전달한다. 웹팀이 작업 화면·HTML보고서를 만들며 이 실행은 PDF/DOCX·UI생성/이미지검수를 요구하지 않는다. 명시 파일요청에만 report:true와 기존옵션을 사용한다. 웹제작오류는 prepare_web_result로 같은session/turn/version복구, 명시파일오류만 deliver_result로복구한다. 포맷생성은 의미승인/HTML연결이 아니다.

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

doctor는 버전·로그인 상태·설치 파일 지문·실제 자료 조회를 확인한다. 자동 Skill 선택·AI 결과 품질·모든 Tool 권한을 보증하지 않는다. 지원/검증 범위는 원본 레포의 docs/validation/codex-product.md를 확인한다. 원문 로그·DB·개인 인증·의존성 환경은 공유하지 않는다.

저장된 결과를 읽는 선택형 시각자료 뷰어는 `web/prototypes/visual-viewer/README.md`를 따른다. 기본 설치에서는 자동 훅을 등록하지 않는다. 필요하면 `python web/prototypes/visual-viewer/viewer.py install --codex` 또는 `--claude`로 해당 폴더의 훅만 등록하고 CLI의 프로젝트 신뢰 설정을 확인한다. `status`, `open`, `uninstall`로 상태·화면·해제를 관리한다. 뷰어는 export를 읽으며 업무 질문이나 모델 실행을 대신하지 않는다. 원 개발 소스는 최길웅의 PR #6이고 이번 통합에서는 경로 검사와 출처 종류 메타데이터 연결을 보강했다.

현재 Windows 인수검사에서 workspace-write 모드는 Codex 명령 실행기 준비 오류로 실패했다. 전체 접근 모드에서 실제 업무 도구를 확인했으며 일반 샌드박스 지원을 통과시킨 것은 아니다. 실행 권한은 실행자가 Codex에서 선택한다. 설치 도구는 권한이나 전역 설정을 바꾸지 않는다.

## Claude Desktop Code에서 사용

제품 source에서 adapters/claude/install.py로 새 폴더에 Claude 사본을 만든다. 그 폴더에서 uv sync --locked와 product-doctor.py를 확인한 뒤, 로그인된 Claude Desktop의 Code에서 기본 작업 폴더로 선택하고 설치된 AGENTS.md/CLAUDE.md를 적용한다. 단순 추가 접근 폴더와 기본 작업 폴더는 구별한다. Claude 자체 로그인·권한은 사용자가 관리한다. Desktop에서의 실제 실행 검증은 별도 CLI의 로그인 검증을 대신하지 않는다. latest 지원 범위·실패·관측 사용량은 해당 제품 릴리스 기록을 따른다. doctor의 local_only/native_verified=false는 설치 검사만 했다는 뜻이며, 별도 실제 업무 기록을 자동 인증하지 않는다.
