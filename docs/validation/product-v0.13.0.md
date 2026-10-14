# product-v0.13.0 배포 인수

2026-10-14 [제품 전용 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.13.0)을 게시하고 원격 자산을 다시 내려받아 대조했다. [기계 검증 기록](product-v0.13.0.json)을 따른다. 공모전 최종 접수 완료는 아니다.

ZIP·체크섬 두 자산과 GitHub 자동 소스 ZIP의 108파일이 로컬 제품 패키지의 원 바이트와 일치했다. 릴리스 노트도 원파일과 같은 바이트다. 태그는 부모 없는 제품 전용 snapshot `590edd00b41d5c41ba2af36d6ed05d5cce87874f`를 가리키며 개발 체계·평가 질문·원문·DB·로그·인증은 제품 패키지에서 제외했다. 출품 코드 provenance는 `14dfa1a2d8b732258105e6725edeee7cfb94ff57`이다. main·웹·기존 태그를 변경하지 않았다.

- ZIP SHA256: `f72a08312991aac3f90161c3181823522cb8634bb0f711b328bf265463a6adfd`.
- L2 manifest: `9939e2472091eaf8f017e47eb1297a3b7e57beb48870c17307b9e6884db5edc5`. 원본55파일·설치86파일·기본 empty catalog다.
- 제품 검사419건 중418통과·1skip, 실제 exit0. 원 receipt·입력7개·로그2개를 현재 바이트로 대조했다. 설치·doctor5명령의 exit0과 원로그10개 지문도 다시 확인했다.
- 원격 인수 검사 receipt `e71cecff7d4f4d20a2a7bf019eae7f99`: exit0, 1.875초. 공개14회 기록의 결속·개인 원문 차단 검사 receipt `b53412339f504b6f9b1b3c1139a22a42`: exit0, 0.563초. 앞선 공개 검사기의 HTTPS 오탐 실패도 보존했고 제품 native 실패로 합산하지 않았다.

[219개 조사 인수](research-breadth-20261014.md), [14회 모델 비교](model-comparison-L2-20261014.md), [Codex·Claude 권장](../decisions/claude-runtime-20261014.md)에 실제 기획·현재 전달·국소 품질 한계·관측 사용량을 구분했다. 권장 설정은 Codex Astra/low와 Claude Desktop Code Opus5.5/높음이다. 고정 자료 기획에서 각각3/3·4/4 조건부 인수했으며 새 웹 조사 시간·통계적 최적 모델·시장 대표성 인증과는 구분한다.

새 비교 기록 커밋 `fa5419378da92711359c72ce924249e80b22ebf3`의 [원격 CI](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38526532571)는 failure다. 실제 job steps는 비어 있고 check-run `115728095749`의 annotation에는 계정 결제 실패 또는 지출 한도 때문에 작업을 시작하지 못했다는 안내가 있다. 이를 제품 테스트 실패나 CI 통과로 바꾸지 않는다. 위 로컬 검사와 원격 자산 대조는 별도 실제 실행 근거다.

배포 ZIP에서 native 모델을 다시 실행하거나 새 원격 clone의 Windows 기본 autocrlf checkout을 인수한 것은 아니다. 동일 바이트 재현은 ZIP을 기준으로 한다. HTML/UI·실물 효과·영상·발표·최종 접수는 별도이며 전체 backend/청구·개발 사용량은 unknown이다.
