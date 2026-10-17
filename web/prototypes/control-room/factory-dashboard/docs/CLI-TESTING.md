# CLI에서 현재 공장 UI 테스트

이 PR의 코드는 lg-ax-harness 기존 web/prototypes/control-room/factory-dashboard 경로에 있습니다. 공장 UI는 현재 공개 Site 버전24과 같고, 기존 빌드가 만드는 기본 web/prototypes/agent-office/factory.html도 새 디자인으로 포함합니다. PR 생성만으로 이미 설치한 릴리즈가 업데이트되지는 않습니다.

## PR checkout에서 바로 보기

저장소 루트의 PowerShell:

```powershell
$dashboard = (Resolve-Path './web/prototypes/control-room/factory-dashboard').Path
Set-Location -LiteralPath $dashboard
npm.cmd ci
node ./node_modules/vite/bin/vite.js build
$product = 'C:/Users/user/Documents/Codex/LG-AX-product-v0.15.0-20261016/codex'
python "$dashboard/tools/start_release.py" --workspace "$product" --dist "$dashboard/dist" --port 8033
```

제품 경로는 본인이 실제로 설치한 codex 폴더의 절대 경로로 바꿉니다. 해당 설치본 README의 의존성·로그인·권한 준비가 필요합니다. 폴더명만으로 최신 릴리즈 버전을 선언하지 않습니다.

이 터미널을 켜 두고, 다른 터미널에서 같은 제품 폴더로 이동해 새 CLI 세션을 시작합니다.

```powershell
Set-Location -LiteralPath 'C:/Users/user/Documents/Codex/LG-AX-product-v0.15.0-20261016/codex'
codex --search --sandbox workspace-write --ask-for-approval on-request
```

CLI 입력란에 예를 들어 ‘냉장고 수납 불편을 실제 자료로 조사하고 기존 기능과 비교해 개선 아이디어 한 개를 제안해 줘’라고 요청합니다. 실행 옵션과 모델은 해당 설치본의 정상 안내를 따릅니다. 이 질문은 실제 사용자의 CLI 이용 한도로 실행되며 대시보드가 대신 모델을 호출하지 않습니다.

이미 켜 둔 CLI를 관찰하려면 첫 명령 끝에 `--latest`를 붙입니다. 기본값은 관찰기를 켠 뒤 시작하는 새 세션 대기입니다. 8033이 사용 중이면 본인이 시작한 예전 관찰 창에서 Ctrl+C로 종료하거나 다른 `--port`를 사용합니다. 원본 CLI나 관측 기록을 지우지 않습니다.

## 무엇을 확인하나

- 같은 공장 디자인에서 오른쪽 현재 작업·실행 주체·최근 사건이 실제 기록과 맞는지.
- 실제 Skill 작업이 관측될 때만 해당 구역이 커지고 역할별 동작을 하는지. 지침 읽기·CLI 진행 보고·실제 호출은 구분합니다.
- 다른 공간 선택이 실행 상태를 바꾸지 않는지. 병렬 확대는 실제 동시에 관측된 구역만 표시하는지.
- 실제 수가 없으면 집계 전/미제공인지. 종료·취소·대기·오류·연결 끊김을 구분하는지.

모든 질문에서 여섯 Skill을 순서대로 전부 실행할 필요는 없습니다. 원 관측기가 실제 시작/종료를 주지 않으면 완료 후 기록을 실시간 실행처럼 재연하지 않습니다.

## 릴리즈 기본 화면

`npm.cmd run build:office`는 저장소의 기존 생성 스크립트로 `web/prototypes/agent-office/factory.html`을 갱신합니다. 이 PR에 해당 산출물을 포함했습니다. 이후 공식 릴리즈를 패키징/게시하고 새로 설치해야 그 릴리즈의 기본 화면으로 사용됩니다. 기존 설치본을 이 PR 제출 작업에서 덮어쓰지 않습니다.

설치된 `runtime-data/agent-office/factory.html`은 별도 쿼리나 서버 연결 양식 없이 같은 폴더의 `live.js`를 자동으로 읽습니다. 공개 Site 빌드는 기존처럼 릴리즈 읽기 서버 연결을 기다리며, 기록 파일을 직접 선택할 때만 파일 보기로 전환합니다.

공개 chatgpt.site 주소만 열면 PC의 기록이 자동 연결되지는 않습니다. 현재 이 안내의 실제 연결 주소는 loopback입니다. 공개 주소 자동 연결의 추가 작업은 아직 배포/브라우저 인수하지 않았으며 이 PR에 포함하지 않았습니다. 다른 PC와 실시간 기록을 공유하는 중계도 추가하지 않습니다.

실제 CLI 상품기획 업무 인수는 사용자가 이후 수행합니다. 코드 검사·빌드·합성 관측 UI 확인은 실제 업무 성공을 대신하지 않습니다.
