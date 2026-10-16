# 심사위원용 ZIP을 실행·배포 폴더 구조의 기준으로 고정

결정일: 2026-10-16 (Asia/Seoul)
근거: 사용자가 열린 PR 검토 중 “앞으로의 폴더 구조는 심사위원용 zip으로 픽스하자”라고 지정했다.

## 적용 구조

```text
심사위원 ZIP 루트/
├── README.md
├── judge.py
├── bundle-manifest.json
├── start_codex_cli.cmd / .sh
├── start_codex_gui.cmd / .sh
├── start_claude_cli.cmd / .sh
├── start_claude_gui.cmd / .sh
├── codex/
│   ├── AGENTS.md · .agents/skills/ · .codex/
│   ├── product-tools/ · agents/ · skills/ · data/
│   ├── web/prototypes/visual-viewer/ · agent-office/
│   └── runtime-data/  # 사용자 실행 시 생성
└── claude/
    ├── CLAUDE.md · .claude/skills/ · .claude/agents/
    ├── product-tools/ · agents/ · skills/ · data/
    ├── web/prototypes/visual-viewer/ · agent-office/
    └── runtime-data/  # 사용자 실행 시 생성
```

이 트리는 상위 경로·책임을 나타낸다. 실제 배포 파일의 전체 목록과 SHA는 bundle-manifest.json을 기준으로 한다. start_* 8개는 PR #13에서 인수해 v0.16 통합본에 포함했다. 이전 v0.15.0에는 없으며 새 버전의 설치·검사와 구분한다.

## 기준

- 설치 안내, 최초 질문, 후속 질문, 오류 복구, 결과 웹·보고서·관찰 화면 검사는 새로 압축을 푼 이 구조에서 수행한다.
- Codex는 codex/, Claude Code는 claude/를 처음부터 세션의 작업 폴더로 연다. ZIP 루트 세션에서 나중에 cd하는 것을 프로젝트 지침·훅 로드와 같은 것으로 취급하지 않는다.
- 공통 업무 Skill·도구 원본에서 두 실행 환경을 생성하고 버전·무결성 검사를 유지한다. 사용자 전역 설정·인증을 ZIP에 포함하지 않는다.
- README.md는 심사위원 실행 안내다. 개발 체계·평가 문제·개인 로그·실제 조사 원문·SQLite·의존성 캐시는 배포 ZIP에 넣지 않는다. runtime-data와 .venv는 설치·실행 중 각 엔진 폴더에 생성한다.
- 새 기능은 이 ZIP만 받은 사용자가 실행 가능한지 인수한다. 저장소를 clone해야만 동작하는 경로를 심사위원 기본 절차에 추가하지 않는다. 실행기·uv·본인 계정 같은 외부 준비물은 README에 명시한다.
- 소스 제출 의무는 유지한다. 보조 제품 소스 ZIP을 제공하는 경우에도 같은 심사위원 ZIP을 재생성할 파일을 빠뜨리지 않는다.

이번 결정은 배포 구조의 기준을 확정한다. 개발 저장소를 배포 폴더로 재배치하지 않고 공통 원본에서 Codex·Claude 사본을 생성한다. 이전 PR 검토 결과는 docs/validation/open-pr-review-20261016.md, 실제 수정·인수는 docs/validation/judge-bundle-T-20261016.md, 원격 배포 결과는 docs/validation/product-v0.16.0.md에서 관리한다.
