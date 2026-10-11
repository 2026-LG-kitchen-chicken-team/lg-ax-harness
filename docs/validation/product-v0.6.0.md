# 제품 v0.6.0 시험판 배포 검증

2026-10-11 [product-v0.6.0](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.6.0)을 prerelease로 게시하고 실제 원격 조회·새 폴더 다운로드까지 확인했다. 공모전 최종 접수와 의미 품질 전체 인수를 뜻하지 않는다. [공개 배포 지문 JSON](product-v0.6.0.json).

## 원본과 첨부물

- 구현·보고 원본 main: `b84d12aa8e9886e1de662beef66c615573fd8d49`
- 제품 태그 commit: `61cba3ebad6bc36fd0097dbb463255be80e001ac`
- 제품 tree: `4ae18319af916a26adc94365cf75379b7d64dc79`
- ZIP: `lg-ax-harness-product-v0.6.0.zip`, 137324 bytes, 69파일
- ZIP SHA-256: `21924707a2395ad4be5e4bf0299f2b823160f1325eaa1c4565a541ca31cbcaaf`
- 별도 `SHA256SUMS.txt`를 함께 첨부했다. manifest는 자신을 제외한68파일이다.

제품 스냅샷에는 공통 Agent1개·Skill6개·일반 코드/계약·설치기·잠금 파일·빈 catalog와 LICENSE/NOTICE만 넣었다. 개발 역할·평가 질문·실행 원문 로그·DB·키/계정 설정·팀 첨부물은 제외했다. 태그는 부모 없는 Git 스냅샷이며 69개 파일명·바이트가 ZIP과 일치한다. 제품 태그에는 개발 이력이 포함되지 않는다.

## 실제 확인과 설치

제품180·평가128·자산 검사, 새 폴더 잠금 설치·공통 Skill doctor·ZIP source만의 Claude 사본 재설치·Claude 사본 잠금 설치/doctor는 actual exit0다. 현재 입력·실제 로그·task-bound receipt를 독립 검토했고 코드 수정 재검토와 최종 보고 재검토의 장부 complete는 exit0 / errors=[]다. 앞선 키 충돌 차단·시간 상한 표현 차단 리뷰는 보존했다.

원격 태그가 위 제품 commit을 가리키고 isPrerelease=true / isDraft=false, 첨부물 두 개가 uploaded임을 확인했다. `gh api`·`git ls-remote`·`gh release download` 실제 exit0. ZIP과 체크섬을 새 임시 폴더에 재다운로드해 준비 원본·첨부 체크섬·GitHub asset digest가 일치함을 확인했다. 다운로드된 manifest의68개 파일과 제품 Git tree의69개 바이트도 다시 대조했다. 게시 시각은 2026-10-11T14:31:18Z, 다운로드 검증은 14:34:15Z다.

실행자는 첨부 ZIP을 새 폴더에 풀고 Python3.12·uv·자신의 Codex 인증 환경을 준비한다. 해당 폴더에서 `uv sync --locked`, `uv run python product-doctor.py`, `codex --search` 순서로 시작한다. 기존 DB/세션을 덮어쓰지 않는다. Claude Desktop Code는 ZIP의 README에 따라 새 Claude 사본을 설치하고 기본 작업 폴더로 선택한다. 실제 검증 환경의 권한·검색/웹 Tool 제공 조건이 있으며 설치 doctor만으로 AI 품질/자동 Skill 선택을 인증하지 않는다.

## 실제 AI 범위와 남은 검증

[v7.2 실제 검증과 한계](claude-codex-v72-20261011.md): 동결8입력/6대화의 저장·전달은 대조했고 초안2/기획 보류5/조사 보류1이다. 의미 품질 전체 통과가 아니다. Claude의 공식 문구 귀속·자체 시간 표시·후기 맥락/검증 지표·접근 복구 안내에 한계가 남는다. native8은 최종 키 접미사 수정 전 동결본이며 최종 수정은 코드 검사로 확인했다. Desktop의 제한 검증을 독립 CLI 인증·개발용 위임·모든 환경 지원으로 확대하지 않는다.

baseline 실패·이전 timeout·unknown 청구는 보존하고 사람 비교와 Gemini는 제외한다. Codex의 평가 transport 로컬 상한과 Claude prompt 예산/collector를 구분하며 Claude 자동 UI/backend 중단·실제 timeout Stop 인수는 미실시다. 미사용 업무 인수·팀 웹 원본 연결·별도 관찰 화면/녹화·발표/리허설·최종 규격 대조와 접수는 남아 있다.
