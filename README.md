# LG AX 신규 프로젝트의 개발용 하네스

2026-10-12 최종 변경은 사용자가 지정한 **0.8.1** 번호로 배포한다. 보고서의 컨셉·시연 이미지 기능을 제외하고 핵심 강조·제목 위계·인용 서식과 긴 원문 인쇄 높이를 보완한다. 선택형 저장 결과 뷰어는 기본 훅 미등록이며 출처 지문과 실행 경로를 검사한다. [실제 서식 검수·원문 보존·새 조사 시간 실패의 구분](docs/validation/report-style-20261012.md)을 따른다. main 반영과 릴리즈 확인 후 이번 작업을 종료한다. 아래 문단은 이전 인수·배포 기록이다.

2026-10-12 실제 제품 인수: **B502S33 냉장고·MWJ25E 전자레인지의 새 실제 조사→근거 분석·기획→검토→저장→원문 자료집·보고서 전달을 완료했다.** 실제 Codex 업무 2건의 조건부 초안과 제품별 XLSX4·DOCX·PDF를 보존하고, 수정한 최종 코드에서 같은 실제 입력을 재생해 확인했다. 최종 Windows PDF·Word·Excel109쪽/30시트와 원문 셀 링크135개를 검수했다. [실제 자료·실행·수정·검수 범위](docs/validation/real-products-20261012.md) · [SHA/사용량/실제 페이지 인수 기록](docs/validation/real-products-20261012.json). 기획은 실물 구현·효과 측정 전 조건부안이다. 합성 목업의 출력 검수로 하네스 완료를 판단했던 이전 선언은 정정하며, v0.8.0과 과거 실패 기록은 보존한다.

최신 제품 배포: [v0.9.1 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.9.1) · [제품 전용78파일·잠금 설치·원격/다운로드 무결성](docs/validation/product-v0.9.1.md). 본문 출처를 짧은 번호와 끝 목록으로 정리하고 정확한 원문 링크·페이지 배치·같은 저장 버전의 출력 갱신을 보완했다. [출처 표시·기존 실제 자료의101쪽 검수](docs/validation/compact-citations-20261012.md)는 새 조사나 제품명 한 줄 자동화 인수와 구분한다. 아래 v0.9.0을 포함한 버전별 문단은 당시 이력이다.

2026-10-12 자료집·보고서 출력: 승인된 수정07 목업의 표·그래프·출처·구획 기준을 공통 코드와 Skill에 반영했다. 종류별 원문 XLSX, 자유로운 절 구성의 DOCX/PDF, 실제 제공된 컨셉 이미지 삽입, 제작 실패 복구와 현재 저장 버전 확인을 제공한다. 모델 작성 보고서는 내부 `report_plan_path`로 전달하며 기본 가상 데이터를 넣지 않는다. 최종 Codex 동일 원본·동일 입력의 GPT-6.1 Sol/GPT-6 Luna 각각1회에서 저장과5파일 생성을 확인했다. 두 업무 상태는 근거 부족으로 held이며 개선안·실물 효과를 확정한 결과가 아니다. Claude 공통 설치·잠금 검증은 완료했고 새 보고서의 Claude AI 실행은 최길웅 후속이다. [구현·검수·모델별 실제 범위](docs/validation/reader-deliverables-20261012.md). Excel 원자료는 편집 가능하며 그래프는 보고 계획에서 재생성하는 이미지다.

2026-10-12 최신 작업 마감: 원문/요약/AI 판단 분리, 보류 decision_notes·후기 문맥/집계·실제 시간·원래 대상 취소를 보완하고 v7.4 동일 원본의 제한 회귀를 종료했다. **Codex10건 중8통과·2실패, Claude3건 중2통과·1실패, 기본 R06미실행1건**. 최종 pointer 전달 오류·신규 조사420초 timeout·Claude 문맥/지표/귀속 제한은 남았다. [구현·실제 결과·시간·한계](docs/validation/quality-regression-20261012.md) · [토큰 가산점의 실제 사건·관측 수치](docs/validation/token-bonus-20261012.md). 제품189·평가128·eval28개 코드 검사 exit0는 AI 전체 품질 통과가 아니다. 보류 진단 통과를 기획 완성으로 바꾸지 않는다. 아래 버전별 문단은 당시 이력이다.

2026-10-11 최신 v7.2: Codex·Claude Desktop Code 각각4입력/3대화의 실제 저장·최종 전달을 확인했다. 초안2/기획 보류5/조사 보류1이며 의미 품질 전체 통과가 아니다. 제품180·평가128개 및 새69파일 ZIP 설치/재설치 검사 exit0. 원질문/발췌 범위 지침과 빈 후보 양식·시간 배분을 보완했다. Claude의 최종 공식 문구 귀속·자체 시간 표시·후기 맥락/검증 지표·접근 복구 안내에는 한계가 남았다. [실제 결과·토큰·남은 작업](docs/validation/claude-codex-v72-20261011.md)을 현재 상태로 우선한다. 아래 날짜별 문단은 각 버전 당시의 이력이며 과거 미인수 상태·검사 수를 최신 결과와 합산하지 않는다. 사람 비교·Gemini는 제외하며 팀 웹 원본과 영상/최종 제출은 별도다.

2026-10-11 최신 v7.1: 빈 catalog에서 실제 질문→조사·등록→같은 요청 기획 경로를 구현하고 열린 이슈5건을 전수 검토해 #4/#5를 수정했다. 제품174·평가145개 일반 코드 검사 통과. 동결 v7.0 실제 진단은 완료1/시간초과3/미실행1, 별도 같은 요청 복구1건 완료이며 최신 v7.1 native·Claude·웹 연결 인수는 미완료다. 사람 대비 절감효과 측정은 사용자 선택으로 제외했다. [구현/진단 결과](docs/validation/request-driven-20261011.md) · [이슈 검토](docs/validation/open-issues-20261011.md). 아래 기록은 각 당시 버전의 이력이다.

2026-10-11 신규 요청 기반 경로(v7.0): 사용자가 새 모델 조사·등록까지 확장하도록 승인했다. 기본 설치는 빈 catalog이며 native AI가 질문을 해석해 실제 근거를 조사하고 정확 모델/출처를 등록한다. open_request 원문 보존 → 연구 사건 → 같은 요청 resolve_request_bundle → 기획/검토/저장으로 연결한다. 특정 질문·제품 enum·기본5모델 답안 선택 경로를 사용하지 않는다. Claude 중복 미확인 null·공식 원문/해석 분리 지침을 보완했다. 현재 구현/코드 검증과 실제 AI 검증은 [최신 작업 기록](docs/validation/request-driven-20261011.md)으로 구분한다. 아래 과거 기본자료·미채택·대기 설명은 당시 이력이다.

최신 제품 배포: [v0.7.0 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.7.0) · [제품 전용 스냅샷·원격/다운로드 검증](docs/validation/product-v0.7.0.md).69파일 ZIP·부모 없는 제품 태그의 바이트·다운로드/체크섬/GitHub digest를 실제 대조했다. 같은 v7.4 원본 제한 회귀의 Codex8/10·Claude2/3 통과와 실패 범위를 공개한다. 아래 v0.6.0 및 이전 검사 수치는 과거 checkpoint다.

2026-10-11 Claude 회신: [최길웅의 v0.3.0 네 입력·첨부 검토](docs/validation/team-runs/records/20261011-claude-mail-review.md). export4개·실행 요약을 접수해 초안3/보류1과 후속 이력·출처를 대조했다. 최초 중복 판단의 모순과 공식 문구 귀속 오류를 기록했다. 환경·시간은 팀원 보고이며 전체 native 최종문/DB/요청별 usage는 미접수다. 최신 v6.1 Claude 제품군10입력·전체 품질/비용 인수와 별도 개발용 Claude 위임 인수는 미완료다.

2026-10-11 추가 검증: [공개 AI 직접 입력50개 실제 회귀 결과](docs/validation/regression50-20261011.md). v6.0의50입력/40대화는 최종 전달·저장·독립 의미 판정을 통과했고 결과는 completed18/held27/needs_input5다. 모델코드 없는 냉장고·전자레인지·식기세척기와 축약명은 v6.1에 반영하고 [별도10입력/8대화](docs/validation/family10-20261011.md)로 검증했다(completed4/held3/needs_input3). 두 버전을 최신60개 통과로 합산하지 않는다. 제품147·평가117개 코드 검사는 실제 exit0다. 공개된 알려진 자료 평가이며 모든 업무 해결·미사용 평가·토큰 절감·효과 실증으로 해석하지 않는다. [팀 웹·기본 자료 논의](docs/validation/web-data-analysis-20261011.md)는 확인 사실과 미채택 제안을 구분한다. 해당 과거 버전은 저장 자료 우선·등록5모델 범위였다. 최신 신규 조사 경로는 상단 기록을 따른다.

최신 완료: [제품 v0.3.0 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.3.0) · [배포·다음 인수](docs/validation/product-v0.3.0.md) · [세 제품군/평가항목 보고](docs/validation/kitchen-progress-20261011.md). 제품135·평가90개 로컬 검사와 실제4입력/3세션,12쪽 발표 검토 초안을 확인했다. 최길웅에게 Claude 검증 요청 메일을 승인받아 발송했다. 영상·리허설·실제 효과·Claude native·최종 접수는 남아 있다. 원격 CI는 계정 결제/지출 제한으로 steps0 실패이며 로컬 검사와 구분한다.

2026-10-11 새 범위: **냉장고·전자레인지·식기세척기** 실제 불편과 기존 기능을 대조하는 상품기획 Agent. 기본 자료5모델·8후기·26사실, 구현 단계/효과 검증 계획을 저장한다. [최신 결정](docs/decisions/kitchen-scope-20261011.md)·[실제 자료와 한계](docs/data/kitchen-v4.md). Gemini 신규 지원을 제거하고 Claude는 하네스 보완 후 최길웅의 환경 검증/정이량 메일 회신으로 진행한다. 웹팀은 개발 중이며 구현 원본 접수·연결 검토는 별도다. 아래 릴리스/검사 숫자는 해당 과거 버전의 이력이다.

출품 Agent·Skill을 만들기 위한 **Codex 중심 개발 체계**다. 메인은 Codex 부모 세션이며 6개 개발 역할·9개 개발 Skill·OSS 작업 장부·실제 검사 실행기를 사용한다. 팀원의 Claude Code에는 별도 네이티브 어댑터를 제공한다. 출품 상품기획 Agent 지침·업무 Skill5개+조건부 외부 조사Skill1개·공통 코드를 작성했다. Codex 출품 설치와 실제 업무 연결을 검증했다. 제품군은 냉장고·전자레인지·식기세척기로 확대하며 Gemini는 철회, Claude native는 후순위다.

[제품 v0.2.3 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.3) · [제품 파일만 포함한 배포 검증](docs/validation/product-v0.2.3.md). 이번 관련 로컬253검사와4입력 실제 실행을 확인했다. 원격 CI 상태는 배포 기록을 따르며 로컬 통과와 구분한다. 이전 v0.2.2/205검사와 v0.2.1/248검사 기록은 보존한다.

2026-10-11: [1–7번 최신 작업·실제 검사](docs/validation/seven-task-progress.md), [팀원 실제 시간 측정·회신](docs/evaluation/team-measurement.md). 실패/timeout과 미측정 사람 공수·전체 청구·Claude/Gemini native 미인수를 보존한다.

후속1·2·3·6번은 [v5.4 실행·근거·비교 기록](docs/validation/focused-progress-20261011.md)과 [별도9입력 평가 계약](docs/evaluation/focused-protocol-20261011.md)을 따른다. 제품 웹 반환 preview를 원문 snapshot과 분리해 줄였다. 실제 자료 충분성·원래 평가 실패·총 청구/사람 공수의 미측정은 유지한다. 팀원 로컬 웹 작업은 이번 분석에서 제외했다.

## 시작

2026-10-11 수정 마감: [v5.5 네 입력·실제 검사·조사 종료](docs/validation/closure-progress-20261011.md), [한 차례 평가 계약](docs/evaluation/closure-protocol-20261011.md). 절별 출처·경험/선호/기대·평가 제약 전달을 수정하고 같은 대화의 후속 이력을 확인했다. 남은 개발 단계는 별도 관찰 화면/실제 녹화·발표/제출 재현이며, 근거/사람 시간/인증/전체 청구는 외부 의존으로 분리한다. 과거 큰 작업 제목을 현재 남은 목록으로 반복하지 않는다.

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

Claude 팀원은 로그인된 Claude Code로 이 레포를 열고 `/harness`를 사용한다. `.claude/agents` 6개와 `.claude/skills` 9개를 제공하며, 사본 정적/동기화 검사를 통과했다. 최신 출품용 업무4입력은 로그인된 Desktop Code에서 검증했고, 독립 CLI는 버전이 확인됐으나 로그인되지 않았다. 개발용 Claude 발견·위임·인수인계는 별도 미인수다.

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

공통 업무 도구도 구현했다. [자료·입출력·상태 계약](docs/contracts/common-tools.md)에 따라 실제 모델 선택·리뷰 조회·근거/결과 구조 검사·SQLite 상태를 제공한다. 현재 기본 자료v4는 실제5모델의 후기8발췌·공식 사실26개다. 이전 v3의3냉장고/6후기/19사실은 이력으로 보존한다. 냉장고의 청소 불편·내부 유효 치수와 식기세척기 내부 치수는 미확인이다. [Agent 지침](agents/product-planning.md), [업무 Skill 목록](skills/manifest.json), [세 제품군 근거와 한계](docs/data/kitchen-v4.md)를 따른다. 합성 자료는 시험 전용이다. 아래 명령은 일반 코드 도구 검사이며 업무 Agent 실행이나 시연 완료가 아니다.

```powershell
uv run python product-tools/cli.py doctor
uv run python product-tools/cli.py prepare_planning_input --input evals/development/select-real-model.json
uv run python product-tools/cli.py retrieve_reviews --input evals/development/retrieve-real-reviews.json
uv run python -m unittest discover -s tests/product-tools -v
```

- [출품 실행 방식](docs/decisions/product-runtime.md): 공통 업무 Skill·코드를 기존 실행기에 연결한다. 현재 Codex 주 실행/Claude 후순위이며 Gemini는 지원 철회했다. 공통 코드·파일 설치와 실제 native 업무 인수를 구분한다. 위 시작 절차와 개발 폴더는 개발 체계용이다.
- [연구원 컨설팅 반영](docs/consultation/2026-10-10.md): 실제 리뷰·모델 선택·정확한 사양·업무 효과 기준.
- [기술 확정](docs/decisions/stack-selection.md): 개발 기반·역할·검사·MCP와 출품 실행 선택·미채택 대안을 구분.
- [실제 검증과 제한](docs/validation/development-harness.md): 정적 검사, 네이티브 위임, 구현·검사·통합의 근거.
- [개발 절차](docs/development.md): 장부·task-bound 검사·완료·인수인계.
- [작업 상태](docs/plans/development-harness.md): D 구축과 S 출품 작업의 완료 범위.
- [토큰 절감 반영·실측·표시 기준](docs/evaluation/token-measurement.md), [별도 시연 관찰 대책](docs/plans/observability-viewer.md): 실제 collector/Langfuse 연결·저장 재생과 아직 남은 화면/녹화 인수를 구분.
- [팀원 웹 작업공간](web/README.md): 황대겸을 웹 PM 한 명으로 지정했다. 웹 설계·기술 선택·작업 배분·리뷰는 PM이 지휘하며, 영상 분석과 연결 제안은 [착수 문서](docs/plans/team-web-workspace.md)를 따른다. 웹팀은 개발 중이며 원격 구현 원본은 미업로드·미검토다.
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

## Claude 후순위 준비와 제출 재현

공통 업무 원본을 각 환경의 Skill 위치와 진입 지침으로 설치한다. 개발 레포 밖의 **서로 다른 새 폴더**를 지정한다.

```powershell
uv run python adapters/claude/install.py --target C:/NEW-CLAUDE-PRODUCT
```

설치 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`를 실행하고, 실행자 자신의 설치·로그인·폴더 신뢰/Skill 동의를 마친 CLI를 연다. 파일 설치기는 로그인·전역 설정·모델 호출을 하지 않는다. [설치 계약](docs/contracts/portable-product.md)과 [로컬 검사](docs/validation/portable-product.md)는 통과했고, [v0.3.0 팀원 회신](docs/validation/team-runs/records/20261011-claude-mail-review.md)으로 네 업무 입력의 저장 내부 기록·출처를 제한적으로 검토했다. 최신 v6.1 Claude 발견·업무·예외·전체 사용량 인수는 미완료이며 Gemini 활성지원은 철회했다. 팀원의 개발 체계 인수는 [별도 체크리스트](docs/evaluation/claude-native-handoff.md)를 따른다.

```powershell
uv run python adapters/common/package.py --engine codex --target C:/NEW-PREPARED-PRODUCT --archive C:/NEW-SOURCE.zip
```

이 ZIP은 [새 폴더 재현 연습](docs/validation/submission-rehearsal.md)용 업무 소스다. 발표·영상·최종 제출 요건 확인을 포함하지 않는다. 실제 로그·DB·인증·의존성 환경은 제외한다. 제품 설치물에 개발 평가 실행기를 넣지 않는다.

실제 심사 입력의 비교·다중 턴·장애 시험은 [S05 후속 검증](docs/validation/s05-followup.md)에 기록한다. 관측 usage와 전체 청구 비용을 구분하며, 사람 비교는 [최신 제외 결정](docs/decisions/effect-scope-20261011.md)에 따라 수행·회신 대기하지 않는다. AI 자체 시간·사용량·오류·근거 품질은 계속 검증한다. 청소 불편·내부 치수는 [후속 조사](docs/data/s01d2-followup.md)에서도 확보하지 못해 물리 배치 확정은 보류한다.

[취소·재시도·반환 원문 시험](docs/validation/s05-hardening.md)에서는 공통 취소 저장과 재시도 경계를 추가했고 제품97개·평가29개·개발22개 코드 검사를 통과했다. 실제 J17 삽입 조건은 최종 저장 일치를 확인했으나 정상 대조가420초 시간초과여서 두 조건 비교는 미통과다. 업무 취소는 로컬 저장 차단이며 native/backend 종료를 보장하지 않는다.

[시연 실행 순서와 발표 구성](submission/README.md), [준비 검증](docs/validation/s06-demo-preparation.md)을 추가했다. 14쪽·예정570초의 근거 연결과 새 소스 ZIP·환경별 파일 설치를 확인했다. 실제 발표 파일·영상·리허설·최종 제출은 남아 있다.

## 팀원이 이미 실행한 결과 제출

[실행 결과 Issue](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/new?template=harness-test-result.md)에 환경·실제 질문/답변·관측 Skill/Tool·오류·후속 이력·사용량을 남긴다. 읽기 권한으로 접수하고 관리자가 비식별 검토 보고서를 레포에 정리한다. 이 절차를 위해 기존 테스트를 다시 실행할 필요는 없다. [접수 방법](docs/evaluation/team-test-records.md), [환경별 결과 색인](docs/validation/team-runs/index.md), [질문 범위와 미사용 평가](docs/evaluation/coverage-and-holdout.md)를 따른다.

팀원들이 실행했다는 사용자 보고와 실제 결과를 접수·검토한 상태를 구분한다. 대겸의 ZIP 보고서는 접수·검토했지만 native 원본·DB·export는 받지 못했다. 과거 사람 측정 요청은 범위에서 제외해 추가 회신을 기다리지 않는다. 팀원 Claude 원본은 [최신 메일 검토](docs/validation/team-runs/records/20261011-claude-followup-mail-review.md)를 따르며 전체 backend 청구를 인증하지 않는다. 실행 종료·업무 상태·내용 검토를 따로 기록하고, 실패 → 수정 commit → 재시험을 연결한다. 수백 질문 후보를 마련하더라도 개발에 노출된 사례와 미사용 평가를 분리한다.

## 제품 릴리스

[릴리스 계약](docs/contracts/product-release.md)에 따라 의미 있는 제품/제출 변경을 새 버전으로 배포한다. 첨부물은 출품 하네스 ZIP·완성 제출 파일·SHA 목록이며 개발용 하네스와 팀 테스트 기록은 포함하지 않는다. 기존 버전을 덮어쓰지 않고 변경 내역·source commit·실제 검사·지원 환경/제한을 남긴다. 앞선 접수·평가 절차 문서만의 변경 단계에서는 제품 릴리스를 발행하지 않았다. 실행 다운로드는 GitHub 자동 전체 `Source code`가 아닌 제품 첨부 ZIP을 안내한다.

후속으로 [Skill 중복 호출 정리·실제 비교](docs/validation/s05-skill-efficiency.md)를 진행했다. 기존 v4와 수정 v5의 같은 실제 질문 1쌍은 모두 저장/출력 일치였고, 관측 명령 18→13개·시간 388.67→322.31초였다. 독립 원문 검토에서 중대 의미 오류를 발견하지 못했으며 반복·전체 비용·공수·일반적 품질 우위는 미입증이다. 당시 최종 v5.1의 외부 조사/보류 가드는 독립 정적 리뷰와 코드 검사 범위였다.

[v5.1 보류·후속 검증](docs/validation/s05-v51-flow.md)에서 실제 자료2턴은 첫 held316.86초·후속 completed344.52초로 같은 native 대화·업무 session에서 저장/출력/export가 일치했다. 신규 요청/turn/진단 자료 버전·이전 후보/export 보존 등24항목과 두 답변의 독립 원문 검토를 확인했다. 자료 버전 변경은 동일 원문 복제이며 새 웹 수집/native import가 아니다. J17 정상/삽입 대조는 최종 응답 없이420.67/420.61초 timeout으로 끝나 paired acceptance는 미통과다. 실패를 포함한4입력 기록·전체 관측 사용량을 보존했다. 제품97개·평가38개 코드 검사는 통과했으며 응답 지연 개선·반복/미사용 평가·전체 청구/공수·환경별 실제 인수는 남아 있다.

[첫 제품 시험판 product-v0.1.0](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.1.0)을 발행했다. `lg-ax-harness-product-v0.1.0.zip` 70파일과 SHA 목록만 첨부했고 원격 태그·실제 다운로드 SHA를 확인했다. 제품 ZIP의 README를 따라 새 폴더에 설치한다. 새 Codex/Claude/Gemini 파일 설치·doctor는 통과했고 Claude/Gemini 실제 업무 인수·발표/영상·운영진 최종 제출은 남아 있다. 제품 source commit은 `9fa81d2`이며 이후 저장소의 발행 확인 문서 commit과 구분한다.

2026-10-10 후속: [v5.2 실제8입력/제한](docs/validation/s05-v52-flow.md), [별도 observer·Langfuse 연결](docs/validation/observer-langfuse.md), [Claude/Gemini 실제 인증 실패 범위](docs/validation/native-access-20261010.md), [실제 browser 등록](docs/data/browser-import-20261010.md), [팀 Issue 접수](docs/validation/team-runs/index.md). 제품102·평가47·observer34·개발22검사와70파일 새 ZIP 재현을 통과했다. 일반 대비 토큰/전체 비용 절감·모든 환경·사람 공수·최종 발표/영상·제출 완료는 미입증/미완료다.

[product-v0.2.0 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.0)에 제품 ZIP70파일과 SHA 목록만 첨부했다. 실제 다운로드·지문 대조와 지원 한계는 [발행 기록](docs/validation/product-v020-release.md)을 따른다.
