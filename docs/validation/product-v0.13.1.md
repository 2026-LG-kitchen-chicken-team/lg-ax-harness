# product-v0.13.1 출처 링크 수정·최종 배포 인수

2026-10-14 [제품 전용 v0.13.1 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.13.1)을 게시하고 다시 내려받아 인수했다. [기계 기록](product-v0.13.1.json)을 따른다. 이번 단계의 최신 배포는 v0.13.1이다. [v0.13.0 기록](product-v0.13.0.md)과 기존 자산·태그를 보존했다.

최종 독립 검토에서 v0.13.0 THIRD_PARTY_NOTICES.md의 개발용 import-manifest.json·patches.json 상대 링크가 제품 ZIP 안에서 끊어진 P2를 발견했다. 두 주소를 고정 커밋의 실제 GitHub 주소로 바꿨고 API의 Git blob과 로컬 고정 객체를 대조했다. 저장소 접근 권한이 필요할 수 있다는 조건도 표시했다. LICENSE·NOTICE는 계속 패키지에 포함하며 실행 코드나 라이선스 파일 누락으로 확대하지 않는다.

원격 ZIP·체크섬 두 자산과 자동 소스 ZIP의 108개 파일은 로컬 수정본과 같은 원 바이트다. 릴리스 노트도 같은 바이트이며 제품 전용 태그는 부모 없는 snapshot `4185309b437ec0666d893fe6b786b0f9a9e389f6`를 가리킨다. 코드·메타데이터 provenance는 `9f79875fdf86806b34c51861a633dbdbc3ab5040`이다.

- ZIP SHA256: `1608d6994b4f8b0a13f4305005f7bc670e7130100f073e4479715e68f6c88123`.
- canonical manifest: `9939e2472091eaf8f017e47eb1297a3b7e57beb48870c17307b9e6884db5edc5`. 업무 원본55파일·설치86파일·기본 empty catalog는 유지한다.
- 이전 ZIP과 다른 것은 THIRD_PARTY_NOTICES.md·product-install.json·submission-source-manifest.json 3파일이다. 설치 본문에서 바뀐 것은 출처 안내1파일이며 업무 코드·Agent·Skill은 같은 바이트다.
- 이번 수정본으로 새 잠금 설치·Codex/Claude 설치·doctor5명령을 실행해 모두 exit0를 확인했다. 원로그10개 SHA를 보존했다. 원격 인수 receipt `b837abc15e95472094d2103c7a3d041e`는 실제 exit0·2.000초다.
- 이전 제품 코드419검사(418통과·1skip)와 collector10검사는 해당 실행 이력이다. 코드 검사 입력7개의 현재 바이트가 같음을 재확인했으며 새 전체419검사나 새 native 업무로 합산하지 않는다.

[219개 실제 조사](research-breadth-20261014.md), [14회 비교](model-comparison-L2-20261014.md), [권장 결정](../decisions/claude-runtime-20261014.md)은 같은 업무 소스의 실제 기록이다. Codex Astra/low 고정자료3/3과 Claude Desktop Code Opus5.5/높음 부모 단독4/4의 조건부 인수는 유지하며 전량 읽기·저장·최종 전달을 확인했다. 미충족2건·국소 의미/시험계획 상세 보완·대표성 미확인과 실제 시간 변동도 그대로 남는다.

이 ZIP의 새 native 업무, 새 원격 clone, Windows 기본 autocrlf checkout, HTML/UI·실물 효과·영상·발표·최종 접수는 이번 인수 범위가 아니다. 전체 backend/청구·개발 usage는 unknown이다. [v0.13.0 기록의 CI](product-v0.13.0.md)는 계정 결제/지출 한도 annotation으로 작업 미시작한 범위이며 로컬 검사·원격 자산 대조와 구분한다. main·웹·기존 태그는 수정하지 않았다.
