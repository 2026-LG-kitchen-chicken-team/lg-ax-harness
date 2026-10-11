# 제품 v0.5.0 시험판 배포 검증

2026-10-11 제품만 담은 [product-v0.5.0](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.5.0)을 prerelease로 배포했다. 최종 제출·실제 AI 품질 인수 완료를 뜻하지 않는다.

## 원본과 첨부물

- 구현·보고 원본 main: `b0b41f8c647c5db9ab3845c6f15893cde90402d7`
- 제품 태그 commit: `17ec1b6b50b7466b74c2a609b407ac0db91bbea4`
- 제품 tree: `9b94cdc16841fc27ce2ec12fd6f7054766fd9fc6`
- ZIP: `lg-ax-harness-product-v0.5.0.zip`, 133607 bytes
- ZIP SHA-256: `7232d45b741f01448f3cbba880397fddb0d7073a46b84cf3f2a1dff3dafb9084`
- 별도 `SHA256SUMS.txt`를 함께 첨부했다.

태그는 부모 이력이 없는 제품 전용 스냅샷이다. 68개 파일 모두 ZIP과 태그의 파일명·바이트가 일치한다. manifest는 자신을 제외한 67개 파일을 기록한다. 기본 자료는 business-empty-v1의 빈 모델·출처·manifest 3개다. 개발 체계·평가 질문·원문 실행 로그·SQLite·인증·사용자 PDF·팀원 첨부물은 제품 배포에서 제외했다.

## 실제 확인

제품 unit174개, 기존 평가 도구117개, 신규 평가 도구28개 exit0다. 이는 코드 검사 수이며 AI 질문 통과 개수가 아니다. 제품 receipt는 `20d789ba670749ac9e858b8423e33908`이고 독립 리뷰에서 현재 입력63개와 로그 지문을 대조했다.

새 폴더에서 잠금 환경 설치·Codex doctor를 확인했다. Claude는 사본 설치·공통 Tool/doctor까지 확인했고 readiness는 local_only, native_verified는 false다. 자산검사 exit0이며 제품 Agent1개·Skill6개다.

최종 독립 문서 리뷰의 77개 입력·검사 receipt·원본 진단6건 지문을 확인했다. 개발 장부 `request-driven-doc-final-20261011`의 `complete`는 exit0, errors=[]다. 이전 차단 리뷰와 수정 이력도 보존했다.

원격 태그가 제품 commit을 가리키고, 공개된 릴리스가 isPrerelease=true / isDraft=false임을 확인했다. 첨부 ZIP과 체크섬을 새 임시 폴더에 다시 다운로드했으며 다운로드 SHA·첨부 체크섬·GitHub asset digest가 위 SHA와 모두 일치한다. 다운로드·릴리스 조회·원격 태그 조회 명령은 모두 exit0이다.

## 범위와 다음 검증

동결 v7.0 실제 AI 진단5개는 완료1·시간 초과3·후속 미실행1이었다. 별도 복구1회는 성공했지만 원래 실패를 바꾸지 않는다. 이후 v7.1에는 검토 ID 타입 오류와 Windows export 파일명 문제 및 기존 양식 상한 지침을 수정했다. 최신 v7.1 native 재인수는 미완료다. [상세 구현·진단](request-driven-20261011.md)과 [열린 이슈5개 검토](open-issues-20261011.md)를 따른다. 원격 이슈를 닫거나 댓글을 발송하지 않았다.

신규 조사 지연·최종 전달 안정화, 최신 Claude 환경 검증, 미수신 팀 웹 구현 연결이 남아 있다. Gemini는 지원에서 제외했다. [사용자 결정](../decisions/effect-scope-20261011.md)에 따라 사람 대비 절감효과 측정·팀원 측정 대기는 현재 작업에서 제외한다. AI 실행시간·토큰·오류·품질은 계속 검증하며 미측정 절감률·전체 청구액을 주장하지 않는다.
