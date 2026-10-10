# LG AX 신규 프로젝트의 개발용 하네스

출품 Agent·Skill을 만들기 위한 **Codex 중심 개발 체계**다. 메인은 Codex 부모 세션이며 6개 개발 역할·9개 개발 Skill·OSS 작업 장부·실제 검사 실행기를 사용한다. 팀원의 Claude Code에는 별도 네이티브 어댑터를 제공한다. 출품 상품기획 Agent 지침·업무 Skill5개+조건부 외부 조사Skill1개·공통 코드를 작성했다. Codex 출품 설치와 실제 업무 연결을 검증했으며 Claude/Gemini와 시각화는 별도 작업이다.

[제품 v0.2.1 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.1) · [제품 파일만 포함한 배포 검증](docs/validation/product-v0.2.1.md). 원격 CI는 결제/지출 한도 사유로 job이 시작되지 않아 미실행이며 로컬248검사 통과와 구분한다.

2026-10-11: [1–7번 최신 작업·실제 검사](docs/validation/seven-task-progress.md), [팀원 실제 시간 측정·회신](docs/evaluation/team-measurement.md). 실패/timeout과 미측정 사람 공수·전체 청구·Claude/Gemini native 미인수를 보존한다.

## 시작

Python 3.12와 uv, 로그인된 Codex를 사용한다. 이 레포에서:

```powershell
uv sync --locked
uv run python dev-harness/cli.py doctor
uv run python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/dev-harness -v
codex
```

Codex에 자연어로 다음처럼 요청한다.

```text
$harness 요구·결정·작업 목록과 diff를 읽고 이번 작업을 진행해.
필요한 역할과 Skill만 사용하고 실제 검사·독립 리뷰를 거쳐 결과를 통합해.
```

현재 Codex 0.162.0에 노출된 도구는 custom role 선택·close를 지원하지 않는다. 메인이 역할 TOML의 developer_instructions와 작업 packet을 네이티브 위임 메시지에 넣는 fallback을 사용한다. TOML sandbox/model 자동 적용을 검증했다고 주장하지 않는다. 읽기 전용 역할은 수정하지 않고, 한 checkout의 파일/Git 쓰기는 한 작성자가 담당한다.

Claude 팀원은 로그인된 Claude Code로 이 레포를 열고 `/harness`를 사용한다. `.claude/agents` 6개와 `.claude/skills` 9개를 제공하며, 사본 정적/동기화 검사를 통과했다. 이 PC에는 Claude CLI가 없어 실제 Claude 발견·위임·인수인계는 팀원 검증이 남아 있다.

## 구성

| 경로 | 역할 |
|---|---|
| `.codex/config.toml`, `.codex/agents/` | 프로젝트 설정, 역할 6개; 모델·추론은 사용자 설정 상속 |
| `.agents/skills/` | harness와 개발 Skill 8개; 필요한 것만 로드 |
| `.claude/agents/`, `.claude/skills/` | Claude 네이티브 역할과 생성 사본 |
| `dev-harness/` | 실제 명령 실행·receipt·장부 경계·완료 검증·동기화 |
| `vendor/codex-harness/` | 고정 OSS 원본·LICENSE·NOTICE·파일 지문·수정 기록 |
| `docs/`, `tests/` | 요구·결정·계획·AI 입력 평가 설계·실제 검증 |
| `.harness/`, `_workspace/` | 실행 장부·검사·관측한 통신; Git 제외 |

역할은 요구 분석 / 설계 / Agent·Skill 구현 / 데이터·Tool 구현 / 평가 / 독립 리뷰다. 토큰 감사는 evaluator + evaluate-harness, MCP·Tool 호출 조건은 harness-architect + harness-design이 맡는다. 공식 OpenAI Docs MCP를 프로젝트 범위로 등록했으며 최신 설정이 불명확할 때만 조회한다. 필수 플러그인 패키지와 추가 모델 API를 설치하지 않았다.

## 상태와 원본

공통 업무 도구도 구현했다. [자료·입출력·상태 계약](docs/contracts/common-tools.md)에 따라 실제 모델 선택·리뷰 조회·근거/결과 구조 검사·SQLite 상태를 제공한다. 기본 자료는 실제 제품3종의 후기6발췌·공식 사실19개다. 현재 제품의 수납·적재 그림자 불편은 확보했고 청소 불편·내부 치수는 미확인이다. [Agent 지침](agents/product-planning.md), [업무 Skill 목록](skills/manifest.json), [실제 근거 확대](docs/data/real-research.md)를 따른다. 합성 자료는 시험 전용이다. 아래 명령은 일반 코드 도구 검사이며 업무 Agent 실행이나 시연 완료가 아니다.

```powershell
uv run python product-tools/cli.py doctor
uv run python product-tools/cli.py prepare_planning_input --input evals/development/select-real-model.json
uv run python product-tools/cli.py retrieve_reviews --input evals/development/retrieve-real-reviews.json
uv run python -m unittest discover -s tests/product-tools -v
```

- [출품 실행 방식](docs/decisions/product-runtime.md): 공통 업무 Skill·코드를 Codex·Claude Code·Gemini CLI에 각각 연결하는 방향을 선택했다. 공통 도구·Agent/Skill 원본과 Codex 설치·실제 업무 연결, Claude/Gemini 미검증을 구분한다. 위 시작 절차와 개발 폴더는 개발 체계용이다.
- [연구원 컨설팅 반영](docs/consultation/2026-10-10.md): 실제 리뷰·모델 선택·정확한 사양·업무 효과 기준.
- [기술 확정](docs/decisions/stack-selection.md): 개발 기반·역할·검사·MCP와 출품 실행 선택·미채택 대안을 구분.
- [실제 검증과 제한](docs/validation/development-harness.md): 정적 검사, 네이티브 위임, 구현·검사·통합의 근거.
- [개발 절차](docs/development.md): 장부·task-bound 검사·완료·인수인계.
- [작업 상태](docs/plans/development-harness.md): D 구축과 S 출품 작업의 완료 범위.
- [토큰 절감 반영·실측·표시 기준](docs/evaluation/token-measurement.md), [별도 시연 관찰 대책](docs/plans/observability-viewer.md): 계획·기존 근거와 아직 구현/인수하지 않은 collector·화면을 구분.
- [팀원 웹 작업공간](web/README.md): 황대겸을 웹 PM 한 명으로 지정했다. 웹 설계·기술 선택·작업 배분·리뷰는 PM이 지휘하며, 영상 분석과 연결 제안은 [착수 문서](docs/plans/team-web-workspace.md)를 따른다. 현재 웹 앱은 미구현이다.
- [대회 요구](docs/competition-requirements.md), [AI 직접 입력 평가](docs/evaluation/judge-input-cases.md).

OpenSpec은 제거했다. 기존 LG 작업물은 재사용하지 않았다. OSS 원본은 [third-party notice](THIRD_PARTY_NOTICES.md)를 따른다. API key·개인 설정·원문 실행 로그·의존성 환경은 Git에 넣지 않는다.

## 출품 원본 확인

```powershell
uv run python scripts/check-product-assets.py
uv run python skills/evidence-retrieval/scripts/run.py doctor
uv run python skills/evidence-retrieval/scripts/run.py prepare_planning_input --input evals/development/select-research-model.json
```

조건부 외부 조사와 검토 Tool은 [외부 조사](docs/contracts/web-evidence.md)·[업무 계약](docs/contracts/product-planning.md)을 따른다. 위 명령은 코드/자료 확인이다. Codex 설치·실제 업무 연결은 아래 별도 폴더에서 검증한다.

## Codex 출품 설치

개발 레포에서 새 별도 폴더를 지정한다. 기존 폴더는 덮어쓰지 않는다.

```powershell
uv run python adapters/codex/install.py --target C:/YOUR-NEW-PRODUCT-FOLDER
```

그 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`, `codex`를 실행하고 `T876MQQ012를 기준으로 수납·정리 개선안을 만들어줘. 하드웨어 추가 없이.`라고 질문한다. 업무Skill6개만 설치하며 세션·요청 키는 일반 코드가 만든다. 추가 질문과 실패/수정 이력·검토·export를 연결한다. 별도 모델 API key·제품 내부 Codex 실행기는 추가하지 않는다.

현재 실제 설치 폴더는 `C:/Users/user/Documents/ChatGPT/LG-AX-product-codex`다. [설치·대화 계약](docs/contracts/codex-product.md)과 [실제 Codex 검증·Windows 권한 제한](docs/validation/codex-product.md)을 따른다. workspace-write 명령 실행기 준비 오류는 실패로 보존했고 전체 접근 모드에서 확인한다. doctor 성공이 권한·AI 품질 통과를 뜻하지 않는다.

## Claude·Gemini 준비와 제출 재현

공통 업무 원본을 각 환경의 Skill 위치와 진입 지침으로 설치한다. 개발 레포 밖의 **서로 다른 새 폴더**를 지정한다.

```powershell
uv run python adapters/claude/install.py --target C:/NEW-CLAUDE-PRODUCT
uv run python adapters/gemini/install.py --target C:/NEW-GEMINI-PRODUCT
```

설치 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`를 실행하고, 실행자 자신의 설치·로그인·폴더 신뢰/Skill 동의를 마친 CLI를 연다. 파일 설치기는 로그인·전역 설정·모델 호출을 하지 않는다. [설치 계약](docs/contracts/portable-product.md)과 [로컬 검사](docs/validation/portable-product.md)는 통과했지만 실제 Claude/Gemini 발견·업무·예외·사용량은 미검증이다. 팀원의 개발 체계 인수는 [별도 체크리스트](docs/evaluation/claude-native-handoff.md)를 따른다.

```powershell
uv run python adapters/common/package.py --engine codex --target C:/NEW-PREPARED-PRODUCT --archive C:/NEW-SOURCE.zip
```

이 ZIP은 [새 폴더 재현 연습](docs/validation/submission-rehearsal.md)용 업무 소스다. 발표·영상·최종 제출 요건 확인을 포함하지 않는다. 실제 로그·DB·인증·의존성 환경은 제외한다. 제품 설치물에 개발 평가 실행기를 넣지 않는다.

실제 심사 입력의 비교·다중 턴·장애 시험은 [S05 후속 검증](docs/validation/s05-followup.md)에 기록한다. 관측 usage와 전체 청구 비용을 구분하며, 사람의 공수 효과는 [측정 절차](docs/evaluation/human-effect-protocol.md)에 따른 실제 기록이 있어야 확정한다. 청소 불편·내부 치수는 [후속 조사](docs/data/s01d2-followup.md)에서도 확보하지 못해 물리 배치 확정은 보류한다.

[취소·재시도·반환 원문 시험](docs/validation/s05-hardening.md)에서는 공통 취소 저장과 재시도 경계를 추가했고 제품97개·평가29개·개발22개 코드 검사를 통과했다. 실제 J17 삽입 조건은 최종 저장 일치를 확인했으나 정상 대조가420초 시간초과여서 두 조건 비교는 미통과다. 업무 취소는 로컬 저장 차단이며 native/backend 종료를 보장하지 않는다.

[시연 실행 순서와 발표 구성](submission/README.md), [준비 검증](docs/validation/s06-demo-preparation.md)을 추가했다. 14쪽·예정570초의 근거 연결과 새 소스 ZIP·환경별 파일 설치를 확인했다. 실제 발표 파일·영상·리허설·최종 제출은 남아 있다.

## 팀원이 이미 실행한 결과 제출

[실행 결과 Issue](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/new?template=harness-test-result.md)에 환경·실제 질문/답변·관측 Skill/Tool·오류·후속 이력·사용량을 남긴다. 읽기 권한으로 접수하고 관리자가 비식별 검토 보고서를 레포에 정리한다. 이 절차를 위해 기존 테스트를 다시 실행할 필요는 없다. [접수 방법](docs/evaluation/team-test-records.md), [환경별 결과 색인](docs/validation/team-runs/index.md), [질문 범위와 미사용 평가](docs/evaluation/coverage-and-holdout.md)를 따른다.

팀원들이 실행했다는 사용자 보고와 실제 결과를 접수·검토한 상태를 구분한다. 대겸의 ZIP 보고서는 접수·검토했지만 native 원본·DB·export는 받지 못했다. 새로 발송한 사람 측정·원본 요청의 회신은 아직 없으며 새 환경 지원·전체 사용량/공수 통과를 추가하지 않았다. 실행 종료·업무 상태·내용 검토를 따로 기록하고, 실패 → 수정 commit → 재시험을 연결한다. 수백 질문 후보를 마련하더라도 개발에 노출된 사례와 미사용 평가를 분리한다.

## 제품 릴리스

[릴리스 계약](docs/contracts/product-release.md)에 따라 의미 있는 제품/제출 변경을 새 버전으로 배포한다. 첨부물은 출품 하네스 ZIP·완성 제출 파일·SHA 목록이며 개발용 하네스와 팀 테스트 기록은 포함하지 않는다. 기존 버전을 덮어쓰지 않고 변경 내역·source commit·실제 검사·지원 환경/제한을 남긴다. 앞선 접수·평가 절차 문서만의 변경 단계에서는 제품 릴리스를 발행하지 않았다. 실행 다운로드는 GitHub 자동 전체 `Source code`가 아닌 제품 첨부 ZIP을 안내한다.

후속으로 [Skill 중복 호출 정리·실제 비교](docs/validation/s05-skill-efficiency.md)를 진행했다. 기존 v4와 수정 v5의 같은 실제 질문 1쌍은 모두 저장/출력 일치였고, 관측 명령 18→13개·시간 388.67→322.31초였다. 독립 원문 검토에서 중대 의미 오류를 발견하지 못했으며 반복·전체 비용·공수·일반적 품질 우위는 미입증이다. 당시 최종 v5.1의 외부 조사/보류 가드는 독립 정적 리뷰와 코드 검사 범위였다.

[v5.1 보류·후속 검증](docs/validation/s05-v51-flow.md)에서 실제 자료2턴은 첫 held316.86초·후속 completed344.52초로 같은 native 대화·업무 session에서 저장/출력/export가 일치했다. 신규 요청/turn/진단 자료 버전·이전 후보/export 보존 등24항목과 두 답변의 독립 원문 검토를 확인했다. 자료 버전 변경은 동일 원문 복제이며 새 웹 수집/native import가 아니다. J17 정상/삽입 대조는 최종 응답 없이420.67/420.61초 timeout으로 끝나 paired acceptance는 미통과다. 실패를 포함한4입력 기록·전체 관측 사용량을 보존했다. 제품97개·평가38개 코드 검사는 통과했으며 응답 지연 개선·반복/미사용 평가·전체 청구/공수·환경별 실제 인수는 남아 있다.

[첫 제품 시험판 product-v0.1.0](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.1.0)을 발행했다. `lg-ax-harness-product-v0.1.0.zip` 70파일과 SHA 목록만 첨부했고 원격 태그·실제 다운로드 SHA를 확인했다. 제품 ZIP의 README를 따라 새 폴더에 설치한다. 새 Codex/Claude/Gemini 파일 설치·doctor는 통과했고 Claude/Gemini 실제 업무 인수·발표/영상·운영진 최종 제출은 남아 있다. 제품 source commit은 `9fa81d2`이며 이후 저장소의 발행 확인 문서 commit과 구분한다.

2026-10-10 후속: [v5.2 실제8입력/제한](docs/validation/s05-v52-flow.md), [별도 observer·Langfuse 연결](docs/validation/observer-langfuse.md), [Claude/Gemini 실제 인증 실패 범위](docs/validation/native-access-20261010.md), [실제 browser 등록](docs/data/browser-import-20261010.md), [팀 Issue 접수](docs/validation/team-runs/index.md). 제품102·평가47·observer34·개발22검사와70파일 새 ZIP 재현을 통과했다. 일반 대비 토큰/전체 비용 절감·모든 환경·사람 공수·최종 발표/영상·제출 완료는 미입증/미완료다.

[product-v0.2.0 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.0)에 제품 ZIP70파일과 SHA 목록만 첨부했다. 실제 다운로드·지문 대조와 지원 한계는 [발행 기록](docs/validation/product-v020-release.md)을 따른다.
