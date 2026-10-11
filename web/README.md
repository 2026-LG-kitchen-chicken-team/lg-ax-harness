# Kitchen · CLI 시각 자료 뷰어

웹 PM은 황대겸 한 명이며 화면·기술·일정과 인수 기준은 [웹 협업 지침](AGENTS.md)을 따른다. 하네스의 냉장고·전자레인지·식기세척기 결과 연결은 [공유 계약](../docs/contracts/team-web-kitchen.md)을 기준으로 검토한다. 이 업로드는 기존 로컬 시각 자료 뷰어 구현이며, 최신 하네스의 제품군·구현 단계·검증 계획 필드까지 실제 화면 인수를 완료했다는 의미는 아니다.

사용자 선택: **원래 CLI에서 입력·실행하고, 시각 자료만 브라우저 한 페이지에서 본다.** 첫 새 자료가 생길 때 브라우저를 자동으로 열고 이후 자료는 같은 페이지에 추가한다. CLI만 시작했을 때는 빈 브라우저를 띄우지 않는다. 웹 입력창·LLM 실행 API·내장 터미널은 제거했다.

## 동작

원래 CLI → 저장 파일/공식 native hook의 공개 시각 자료 → 읽기 전용 localhost 뷰어.

조회·새로고침·필터·확대·다운로드는 CLI나 모델을 실행하지 않는다. SessionStart는 연결 프로그램만 준비한다. PostToolUse의 공개 이미지·근거 조회 데이터, 작업 폴더의 새 시각 파일, Stop의 명시적 Markdown 이미지를 자동 표시한다. hook은 추가 모델 문맥·도구·권한·저장 결과를 변경하지 않는다.

## 현재 PC

개인 설정은 `.harness/viewer.json`이다. 독립 Codex 하네스 폴더의 `.codex/hooks.json`과 Claude 폴더의 `.claude/settings.local.json`에 뷰어만 연결했다. 기존 프로젝트 hook·권한을 보존하며 전역 로그인·모델 설정은 수정하지 않는다.

연결한 하네스 폴더에서 평소처럼 **codex**를 실행한다. CLI가 요구하는 최초 프로젝트/hook 신뢰 검토는 유지한다. 필요하면 `/hooks`에서 로컬 뷰어 hook을 한 번 검토·신뢰한다. 신뢰 우회 옵션은 사용하지 않는다. Claude 로그인 환경은 미검증, Gemini는 사용자 요청대로 현재 native 설치·실행 검증에서 제외했다.

## 다른 PC

Python 3.12 이상과 기존 CLI만 사용한다. 뷰어는 Python 표준 라이브러리로 실행되며 npm·xterm·PTY 설치는 필요 없다. LLM 모델과 Skill은 원래 CLI에서 사용한다.

개인 `.harness/viewer.json` 예:

```json
{
  "workspaces": ["C:/AX-runtimes/codex", "C:/AX-runtimes/claude"],
  "watch": [
    {"label": "하네스 결과", "path": "C:/AX-runtimes/codex/runtime-data/exports"},
    {"label": "시각 자료", "path": "C:/AX-runtimes/codex/runtime-data/visuals"},
    {"label": "Claude 결과", "path": "C:/AX-runtimes/claude/runtime-data/exports"}
  ]
}
```

처음 한 번 프로젝트 연결:

```powershell
python web/server.py --install-hook codex --workspace C:/AX-runtimes/codex
python web/server.py --install-hook claude --workspace C:/AX-runtimes/claude
```

관찰 프로그램은 CLI가 hook을 실행할 때 준비·재사용한다. 새 자료가 생기고 페이지가 연결되지 않았을 때 브라우저를 열며 반복된 자료마다 탭을 만들지 않도록 제한한다. 열린 페이지는 약 1.5초마다 갱신한다.

hook을 지원하지 않거나 비활성화한 CLI에서는 파일 뷰어만 직접 실행할 수 있다:

```powershell
python web/server.py --watch C:/AX-runtimes/output --auto-open
```

여러 `--watch` 폴더도 같은 화면에 모인다. [로컬 화면](http://127.0.0.1:8765/). 파일 표시는 모델에 종속되지 않는다. 자동 시작/도구 수집은 실제 native hook과 공개 payload에 한정된다.

## 표시와 한계

- PNG/JPEG/WebP/GIF/SVG, 로컬 HTML과 JS/CSS/JSON 자원, CSV/TSV, JSON, 브라우저가 지원하는 PDF를 표시한다. HTML의 외부 CDN·네트워크·폴더 밖 자원은 연결하지 않는다. 단일 HTML 또는 같은 폴더의 로컬 자원으로 생성해야 한다.
- 실제 조회 행을 표로 표시한다. CSV의 유한한 수치 열을 비교할 수 있으며 누락을 0으로 만들지 않는다. 처음 200행·최대 40열을 미리 보고 전체 원본을 다운로드한다.
- 하네스 export는 저장 상태·무효화, 불편·기존 기능·남은 불편·기획안, 요구사항·가정·보류 사유·근거를 표시한다. 최신 파일도 **저장 당시 snapshot**이며 현재 CLI·최종 전달·의미 품질 인증이 아니다. 과거 요청·후보도 같은 페이지에 있다.
- 실제 반환된 HTTPS 이미지는 제공처에서 직접 표시한다. 모델 내부에서만 본 자료는 공개 파일·이미지 주소·도구 반환이 없으면 표시할 수 없다. 시각화용 LLM 호출·인과관계·시장 효과 추정은 추가하지 않는다.
- 저장된 export는 바로 표시하고 등록한 작업 폴더의 다른 위치에 새로 생긴 시각 파일도 자동 수집한다. 작업 폴더의 기존 이미지와 일반 JSON 입력·설정은 자동으로 가져오지 않는다.
- 파일당 20MiB, HTML 합계 32MiB/64자원, 폴더당 최근 80개, 보관 240버전/512MiB 한도를 표시한다. 임시 쓰기·누락·조회 오류는 재확인하며 업무 완료·실패로 바꾸지 않는다.
- HTML은 `allow-scripts`만 주는 iframe과 CSP sandbox에서 실행한다. 앱 접근·상위 이동·폼 전송은 허용하지 않는다. 원본 bytes와 SHA256을 보관하며 이전 미리보기를 덮어쓰지 않는다.

검증은 [COVERAGE](COVERAGE.md), 협업 원본은 [AGENTS](AGENTS.md)를 따른다.
`runtime-data/product.sqlite`의 기존 retrieval_cache도 읽기 전용으로 확인합니다. 자료 지문을 대조해 저장된 조회 표를 누적하며, 이를 특정 현재 요청의 결과로 추정하지 않습니다. 업무 DB와 캐시를 수정하지 않습니다. 분류는 자료·근거 / 분석·비교 / 개선 기획안 / 검토 결과 / 시각 자료이며 이전 버전도 같은 페이지에서 조회합니다.

이 분류는 기존 업무 Skill의 근거 조회·외부 조사, 불편 구조화·기존 기능 대조, 기획안 작성, 검토·저장 결과를 묶은 것입니다. 저장된 결과 필드로 분류하며 Skill 실행 자체를 관측했다는 뜻은 아닙니다. 설정·인증·로그 폴더와 중첩 비공개 JSON 필드·표 열은 자동 표시 대상에서 제외합니다.

현재 실제 native 인수는 기존 B502S33 Codex 환경이다. 최신 main의 세 제품군 결과·추가 필드 화면 대조와 사람이 읽기 쉬운 생성 문장/용어 개선은 후속 확인 항목이다. 기존 결과·원문·DB를 업로드하거나 문장 개선을 적용한 것으로 설명하지 않는다.
