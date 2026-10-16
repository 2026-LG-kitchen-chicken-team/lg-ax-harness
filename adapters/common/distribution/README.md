# LG AX 상품기획 에이전트 설치

냉장고·전자레인지·식기세척기의 실제 후기와 공식 자료를 조사하고 상품기획·근거·HTML 보고서로 정리하는 Codex·Claude Code용 하네스입니다. 이 저장소는 **제품 설치·배포 전용**이며 개발 저장소의 이력·팀 문서·개인 실행 기록을 포함하지 않습니다.

현재 제품은 **product-v0.17.0**, 설치 도구는 **installer-v0.1.2**입니다. 아래 명령은 제품 버전을 명시해 검증한 심사위원 ZIP을 그대로 내려받습니다. 설치 도구만 버전 없이 실행하면 이전 기본 제품을 받을 수 있으므로 아래 명령을 그대로 사용하세요. 업무 Skill·모델·기본 실행 설정은 바꾸지 않습니다.

## 설치 방법 선택

1. **AI에게 맡기기:** 아래 설치 요청문을 Codex 또는 Claude Code에 붙여넣습니다.
2. **터미널에서 설치:** 운영체제에 맞는 아래 명령을 실행합니다.
3. **ZIP으로 설치:** [제품 릴리즈](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/tag/product-v0.17.0)에서 `lg-ax-judge-product-v0.17.0.zip` 하나를 받아 모두 풀고 README를 읽습니다. GitHub CLI 없이 이미 받은 ZIP만으로도 사용 가능합니다.

현재 비공개 배포 단계에서는 저장소 읽기 권한이 있는 GitHub 계정이 필요합니다. 터미널 설치는 [GitHub CLI](https://cli.github.com/) 설치 후 `gh auth login`으로 로그인하세요. AI 계정 로그인과 GitHub 인증은 서로 다릅니다. 설치기는 인증 토큰을 출력하거나 제품 폴더에 저장하지 않습니다.

## AI에게 붙여넣기

```text
LG AX 상품기획 에이전트를 이 컴퓨터에 설치하고 준비 상태를 확인해줘.
https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/blob/main/agent.md 의 설치 지침을 따라줘.
비공개 접근이면 정상 GitHub CLI 인증으로 지침을 읽고, 권한이 없으면 알려줘.
운영체제와 사용할 Codex/Claude Code를 확인하고 새 폴더에 설치해줘.
기존 결과는 보존하고 로그인·폴더 신뢰는 나에게 안내해줘. 상품기획 질문은 아직 실행하지 마.
```

[AI 설치 지침](agent.md)은 설치·검사 범위와 실패 시 조치를 정합니다. 제품은 Codex·Claude Code용이며 다른 AI 실행기 지원을 뜻하지 않습니다.

## Windows PowerShell: 한 줄 설치

GitHub CLI가 설치·로그인된 PowerShell에서 실행합니다. 설치 중 uv가 없으면 공식 설치 여부를 묻습니다. Python 3.12와 필요한 제품 의존성은 자동 준비합니다.

```powershell
& ([scriptblock]::Create((gh api 'repos/2026-LG-kitchen-chicken-team/lg-ax-agent/contents/install.ps1?ref=installer-v0.1.2' -H 'Accept: application/vnd.github.raw+json' | Out-String))) -Engine codex -Version product-v0.17.0
```

Claude는 `-Engine codex`를 `-Engine claude`로 바꿉니다. 다른 버전은 `-Version` 값을 바꾸고, 설치 폴더는 `-Target 'C:\LGAX\new-install'`을 덧붙입니다. **이미 존재하는 폴더는 덮어쓰지 않습니다.**

## macOS / Linux Bash: 한 줄 설치

```bash
gh api 'repos/2026-LG-kitchen-chicken-team/lg-ax-agent/contents/install.sh?ref=installer-v0.1.2' -H 'Accept: application/vnd.github.raw+json' | bash -s -- --engine codex --version product-v0.17.0
```

Claude는 `--engine claude`로 바꾸고, 새 폴더는 `--target "$HOME/LGAX/new-install"`을 덧붙입니다. Linux는 CLI, macOS는 CLI 또는 앱 시작 파일을 사용합니다.

## 설치가 끝나면

1. `verified_files`와 `prepared: true`, 설치된 폴더가 표시됩니다. 처음에는 인터넷 다운로드가 있어 소요 시간이 달라집니다.
2. 설치 폴더의 `README.md`를 열고 `start_codex_cli` 또는 `start_claude_cli`를 실행합니다. Windows는 `.cmd`, macOS/Linux는 `bash 파일명.sh`입니다. Windows/macOS 앱 사용자는 같은 엔진의 `start_*_gui` 파일을 선택합니다.
3. 본인 AI 계정 로그인·작업 폴더 신뢰·필요 권한을 승인합니다. 설치기는 로그인하거나 업무 질문을 보내지 않습니다.
4. 첫 질문 뒤 진행 대시보드, 결과 저장 뒤 기획자 웹·보고서를 확인합니다. 화면이 열리는 조건과 수동 복구는 설치된 사용설명서에 있습니다.

위 명령의 기본 설치 위치는 명령을 실행한 폴더의 `LG-AX-product-v0.17.0-codex` 또는 `...-claude`입니다. 버전을 바꾸면 폴더명도 그 버전을 따릅니다. AI 작업 폴더는 그 안의 `codex/` 또는 `claude/`입니다.

## 업데이트·실패·보관

| 상황 | 조치 |
|---|---|
| GitHub 인증·권한 실패 | `gh auth status`로 상태를 확인하고 읽기 권한을 받습니다. 인증 실패를 공개 다운로드로 우회하지 않습니다. |
| 기존 폴더 오류 | 다른 **새 폴더**를 지정합니다. 이전 결과 폴더를 보관합니다. |
| 체크섬·파일 무결성 오류 | 실행을 중단합니다. 릴리즈 버전과 파일을 확인하고 다시 시도합니다. |
| 다운로드 후 준비 실패 | 추출된 폴더는 남아 있습니다. 그 안의 시작 파일을 실행하면 준비를 다시 진행합니다. |
| 다운로드만 원함 | PowerShell `-DownloadOnly`, Bash `--download-only`. 검증·추출까지만 수행합니다. |
| 새 버전 사용 | `Version`/`--version`에 정확한 새 버전을 지정해 별도 폴더에 설치합니다. 자동 DB 이전이나 강제 업데이트는 하지 않습니다. |

## 공개 전환 후 사용할 경로

**아래는 저장소 공개가 완료된 뒤에만 사용할 수 있습니다.** 공개 전에는 GitHub 인증 경로를 사용합니다. 공개 전환도 AI 제공사의 로그인·이용 권한을 대체하지 않습니다.

Windows:

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/download/installer-v0.1.2/install.ps1'))) -Transport public -Engine codex -Version product-v0.17.0
```

macOS/Linux:

```bash
curl -fsSL 'https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent/releases/download/installer-v0.1.2/install.sh' | bash -s -- --transport public --engine codex --version product-v0.17.0
```

공개 전환 일정과 실제 공개 여부는 별도로 확인합니다. 위 공개 경로는 실제 전환이 끝난 뒤에만 사용하세요.

## 배포 구성

- 제품 릴리즈: 기존 심사위원 ZIP·제품 소스 ZIP·SHA256SUMS. 원래 제품 버전과 바이트를 보존합니다.
- 설치 도구 릴리즈: `install.ps1`, `install.sh`, `install.py`, 이 README, `agent.md`, SHA256SUMS.
- Windows PowerShell과 macOS/Linux Bash 입구가 공통 Python 설치기를 사용합니다. 래퍼가 설치기 SHA를 검사하고 설치기가 제품 ZIP SHA와 내부 파일 지문을 다시 확인합니다.
- 공개 저장소라는 이유로 별도 오픈소스 라이선스를 부여한 것은 아닙니다. 기존 제품의 제3자 고지·LICENSE는 각 제품 패키지 안에 보존합니다.
