# 제품 v0.2.1 시험판 배포 검증

2026-10-11 KST. [게시한 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.2.1)은 prerelease=true/draft=false다. 이전 v0.2.0을 교체하거나 최종 대회 제출로 처리하지 않았다.

조건부 기획 가설과 직접 관측 사실을 구분하는 qualification, `save_and_export`, 질문 원문 보존, 실제 PDP의 HTML 설명서 연계와 URL 경계가 제품 변경이다. 품질/지연/사용량·남은 한계는 [1–7번 실제 검증](seven-task-progress.md)을 따른다.

## 파일·출처·원격 확인

- 개발 원본 커밋: `64ad69c2d09eed4fb35e96761694536b9ed5ad16`.
- 제품만 담은 스냅샷 커밋: `aa6ec08db9d02474ea3e4cab5a036853a33cc433`, tree `bb37b8fcaacda10e126a544b794ac1f8035229be`.
- `product-v0.2.1`은 부모 없는 제품 스냅샷에 연결했다. main 브랜치의 개발 체계는 보존한다. GitHub 자동 Source code도 제품 tree만 담으며 개발 레포 전체 압축파일을 제출 파일로 배포하지 않는다.
- 첨부 ZIP: `lg-ax-product-v0.2.1-codex-source.zip`, 122,136bytes, SHA256 `b8aab86992611ed2ef0dcad52065b09518a879ddab3f12821da45865a28d645e`.
- 첨부 `SHA256SUMS`: 105bytes, SHA256 `094e081a6523ae96d653ef5efea4b299270f0284b162e42c2379794b64b23319`.

ZIP70파일/manifest69파일의 CRC·각 SHA, Git snapshot의 모든 blob byte와 ZIP 내용 일치, LICENSE/NOTICE 유지, 금지 개발/비공개 경로 부재를 확인했다. 필수 `vendor/codex-harness/LICENSE`와 `NOTICE`는 제외하지 않는다. 초기 과도한 vendor 경로 차단은 게시 전에 실패로 보존하고 이 두 파일만 정확히 허용하도록 교정했다. snapshot/API key·개인 환경·runtime DB/log·팀 메일/첨부·평가/측정 도구·개발 역할은 제품에 포함하지 않는다.

업로드 후 GitHub API를 재조회해 두 asset의 uploaded 상태·크기·digest, 원격 태그 commit, 원격 recursive tree70개 blob/path SHA의 로컬 snapshot 일치를 확인했다. ZIP에 대한 새 폴더 `uv sync --locked`·공통 Skill doctor·추출본 Claude adapter 재설치는 각각 exit0이며 native 모델 실행은 아니다.

## 검사와 독립 검토

로컬 product115/evaluation77/observer34/development22, 총248 tests 통과. 최신 제품 receipt `9e8bc6f5ed104493ba06a21bf5adfcf9`, 평가 `e1066af6935640e1961a82e61ccc217a`, snapshot 대조 `09cc856bb75b476ab649c097383efbac`는 exit0이며 독립 reviewer가 입력/로그 지문과 작업 바인딩을 확인했다. 원래 평가 수집기의 실패와 두 단계 이력/JSON 타입 경계 보강 기록도 보존한다.

현재 원격 CI는 [main64ad69c의 run38064705331](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38064705331)이 failure다. Ubuntu/Windows 두 job 모두 step0이고 GitHub annotation은 **계정 결제 또는 지출 한도 때문에 job이 시작되지 않았음**을 알렸다. 로그 조회는 log not found였다. GitHub Billing & plans 확인이 필요하며 결제·한도 변경은 하지 않았다. 로컬 테스트 통과를 원격 CI 통과로 설명하지 않는다. Ubuntu native 검증도 추가되지 않았다.

## 지원·효과 제한

Codex 실제 시험의 원래 전달 계약7통과/5실패와 업무 AI 웹 timeout은 유지한다. 수정 계약의 기존 artifact 재검사와 제품 단위 검사를 새 native 성공으로 바꾸지 않는다. Claude/Gemini는 adapter 일반 코드 준비와 실제 업무 지원을 구분하며 native 인수 미완료다. 사람 공수·전체 backend 청구·일반적 토큰/지연/품질 우위·청소 불편/정확 내부 치수 원문은 미검증이다. 팀원 측정·원본 회신을 메일로 요청했고 아직 접수하지 않았다.
