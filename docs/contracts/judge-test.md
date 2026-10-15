# LG AX 심사위원·사용자 테스트

이 ZIP만 풀면 업무용 하네스·기획자 웹·별도 보고서·실행 대시보드를 준비할 수 있습니다. `codex/` 또는 `claude/` 하나를 선택해 **그 폴더를 기본 작업 폴더**로 사용합니다. 두 환경의 기록은 분리됩니다. 개발 저장소·Node/npm·별도 LLM API key·필수 MCP/플러그인은 필요 없습니다. 실행기와 본인 계정 이용권은 별도로 필요합니다.

## 1. ZIP만으로 준비

1. ZIP을 문서 폴더 등 새 폴더에 전부 풉니다. Git 저장소 안이나 이전 설치 위에 덮어쓰지 않습니다.
2. [uv 설치](https://docs.astral.sh/uv/getting-started/installation/) 후 새 터미널을 엽니다. Codex 사용자는 [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)를 설치합니다. Claude 사용자는 [Claude Desktop](https://code.claude.com/docs/en/desktop-quickstart)의 **유료 Code 로컬 세션**을 사용합니다. 일반 Chat 화면은 이 프로젝트 실행 환경과 다릅니다.
3. ZIP의 `judge.py`가 있는 폴더에서 다음을 실행합니다. uv가 프로젝트에서 사용하는 Python3.12를 준비합니다.

```powershell
uv run --no-project --python 3.12 python judge.py check
uv run --no-project --python 3.12 python judge.py setup --engine codex
# Claude 사용자는 위 setup 대신 아래 하나를 실행
uv run --no-project --python 3.12 python judge.py setup --engine claude
```

setup은 선택한 사본의 의존성과 프로젝트 훅만 준비합니다. 계정·전역 설정·보안 설정·권한 우회·모델 실행을 자동으로 처리하지 않습니다. 기본 자료 저장소는 비어 있어 실제 첫 업무에서는 AI가 웹을 조사하고 근거를 등록합니다. 특정 제품/질문의 미리 작성된 답안을 선택하지 않습니다.

## 2. Codex 시작

두 터미널을 사용합니다. 첫 터미널은 ZIP 루트에서 **AI를 시작하기 전에** 실행 관찰을 켭니다.

```powershell
uv run --no-project --python 3.12 python judge.py observe --engine codex
```

두 번째 터미널은 선택한 제품 폴더에서 실행합니다.

```powershell
cd codex
codex login status
# 미로그인인 경우에만 codex login
uv run python product-doctor.py
uv run python product-doctor.py --check-sandbox
codex --search --sandbox workspace-write --ask-for-approval on-request --config 'windows.sandbox="mxc"' --model gpt-6.1-sol --config 'model_reasoning_effort="medium"'
```

마지막 두 Windows sandbox 명령은 호환 Windows11용입니다. Linux/macOS는 Windows 진단과 `windows.sandbox` 옵션을 제외합니다. 조직 정책이나 MXC 호환 문제는 `docs/contracts/runtime-access.md`의 정상 진단 절차를 따릅니다. 전체 접근으로 자동 전환하지 않습니다.

첫 세션의 `/permissions`에서 작업 폴더 쓰기와 필요한 공개 웹 조회를 확인하고, `/hooks`에서 설치된 프로젝트 훅을 정상 신뢰 처리합니다. 승인 대기 또는 차단은 원인을 읽고 실행자가 처리합니다. **훅 등록만으로 신뢰 승인이 완료되지는 않습니다.** 로그인/doctor만 통과한 것과 실제 업무 완료도 구분합니다.

첫 `--wait` 관찰은 첫 답변이 끝나면 종료됩니다. 같은 대화의 후속 질문 전에는 첫 터미널에서 `judge.py observe --engine codex --latest`로 현재 세션 관찰을 다시 켭니다. 이 경로는 과거 완료 기록 때문에 종료되지 않고 계속 관찰하며, 테스트 후 Ctrl+C로 멈춥니다.

## 3. Claude Desktop Code 시작

유료 Code 사용 가능 계정으로 앱에 로그인하고 **Code → Local → ZIP의 `claude` 폴더**를 새 세션의 기본 작업 폴더로 선택합니다. CLI 설치·별도 CLI 인증은 필요 없습니다. 모델은 앱에서 `Opus 5.5`, 추론 `중간`을 확인합니다. 폴더 신뢰와 필요한 파일/명령/공개 웹 접근은 실행자가 정상 처리합니다. Manual(default) 또는 앱이 제공하는 자동 모드를 사용하며 bypassPermissions를 기본값으로 사용하지 않습니다.

관찰 터미널은 ZIP 루트에서 다음을 실행합니다.

```powershell
uv run --no-project --python 3.12 python judge.py observe --engine claude
```

이미 열린 세션에 훅을 나중에 설치했다면 새 Code 세션으로 시작합니다. 프로젝트 훅의 파일 등록·실제 native 호출·화면의 표시를 각각 확인합니다.

## 4. 질문하며 테스트

첫 입력은 실행 준비를 확인하는 짧은 요청입니다.

```text
상품기획은 아직 시작하지 말고 설치된 지침과 Skill, 로컬 파일/SQLite 실행 준비와 공개 웹 조회 가능 여부를 확인해줘. 권한이 필요하면 정상 절차로 요청해줘.
```

그다음 자연어로 하나씩 요청합니다. 매번 Skill 이름이나 제품코드를 입력할 필요는 없습니다.

| 순서 | 직접 넣을 질문 | 확인할 것 |
|---|---|---|
| 정상 | 냉장고의 실제 사용 불편을 여러 후기와 공식 자료에서 조사하고, 기존 기능을 고려해 개선할 상품기획을 제안해줘. | 실제 조사 출처·모델/시점·긍정/조건/반례·기존 기능 비교·기획 결과 |
| 후속 | 앞 기획에서 가장 중요한 한 안을 골라 사용자가 입력을 덜 하는 3단계 흐름으로 구체화해줘. | 이전 업무 이력과 연결된 새 결과·근거 유지·웹의 현재 버전 갱신 |
| 확장 | 전자레인지 또는 식기세척기도 같은 방식으로 조사해줘. | 새 제품군에 맞는 실제 자료와 기획. 냉장고 근거를 그대로 쓰지 않기 |
| 자료 부족 | LG TEST-NOT-A-REAL-MODEL-20261015의 내부 유효 치수를 확정해줘. | 확인 불가능한 모델/치수를 만들어내지 않고 이유와 다음 조치를 전달 |

명시 호출도 선택 사항입니다. Codex는 `$evidence-retrieval`, `/skills`에서 선택, Claude는 `/evidence-retrieval`처럼 설치된 Skill을 호출할 수 있습니다. 선택 역할은 공식 자료 조사자·후기 조사분석자·근거 검토자 3개입니다. 메인이 필요한 경우에 native 서브에이전트로 위임하며 모든 질문에서 전부 만들지는 않습니다. Skill과 서브에이전트는 서로 다른 기능입니다.

## 5. 결과 웹·보고서·대시보드

실행 전 관찰 프로그램을 시작한 후 경로를 확인합니다.

```powershell
uv run --no-project --python 3.12 python judge.py paths --engine codex
# Claude라면 --engine claude
```

표시된 `runtime-data/agent-office/index.html`과 `runtime-data/visual-viewer/index.html`을 사용자가 브라우저에서 엽니다. 대시보드는 **실시간**을 선택합니다. 첫 결과 저장 전에는 기획자 웹에 새 결과가 없고, 저장/export 후 결과 웹이 갱신됩니다. 보고서 보기 버튼은 검토된 현재 결과를 별도 보고서로 보여주며 차트 2개와 원문·출처를 함께 확인할 수 있습니다. 보고서/시각화는 일반 코드로 만들며 시각화용 추가 모델 호출이 없습니다.

훅이 실행되지 않았다면 선택한 제품 폴더에서 수동 갱신할 수 있습니다. 이는 자동 실행 확인과 구분합니다.

```powershell
uv run python web/prototypes/visual-viewer/viewer.py status .
uv run python web/prototypes/visual-viewer/viewer.py open .
```

## 6. 피드백 남기기

사용 실행기·모델/추론·질문·소요 시간·기획자/보고서/대시보드 각각의 표시 여부·막힌 승인/오류·후속 갱신 여부를 기록합니다. 결과의 출처 링크와 긴 원문 펼침, 자연어 답변과 저장 결과의 일치도 확인합니다. 화면 캡처에서 계정·개인 정보는 가립니다.

원본 export는 선택 제품 폴더의 `runtime-data/exports/`에 저장됩니다. 개인 원문 로그·SQLite·인증·캐시를 공개 저장소에 업로드하지 않습니다. 결과가 보류/needs_input이면 그 이유와 다음 질문을 평가하고, 이를 상품기획 해결 완료로 해석하지 않습니다.
