# M1 통합 코드 검사

2026-10-14, 소스 `9e7f37d` 및 canonical manifest `3c810cf1ff2726fe8f77649d32b28e540ebec1e28f41bd4d1fc3a235f9414889`에서 실행했다. [기계 기록](quality-web-code-M1-20261014.json)은 실제 검사 receipt와 입력·로그 SHA를 보존한다.

| 실제 검사 | 결과 | 경과시간 |
|---|---|---:|
| `python -m unittest discover -s tests/product-tools -v` | 439/439 통과, 생략 0 | 86.219초 |
| `python -m unittest discover -s tests/web -v` | 102/102 통과, 생략 0 | 68.860초 |
| `python scripts/check-product-assets.py` | 55개 canonical 자산 일치, exit 0 | 0.125초 |
| `python dev-harness/cli.py validate` | exit 0 | 0.469초 |

잠금 의존성을 설치한 격리 Python 3.12를 사용했고 제품 검사에는 `LG_REPORT_UV`와 `LG_REPORT_PYTHON`을 지정하여 설치 검사를 생략하지 않았다. 실제 receipt의 실행 파일 경로는 프로젝트 상대 경로다. 이 명령들의 새 출품 AI 입력은 0이다.

이 소스는 PR10(`1576a6c2a31d7a927bf73f02eaea4abf33202f80`)의 뷰어 및 PR11(`7c8e61b305e3424d0a5b3ac61dd203bbdfacbc71`)의 별도 관찰 화면과 현재 결과 binding 보완을 통합했다. 팀원의 화면 디자인을 재작성하지 않았다. 모델이 보고서 HTML을 매번 작성하는 경로 대신 일반 코드가 저장 데이터를 렌더링한다. 3D 관찰 화면은 별도 프로그램이며 제품 설치 목록에 자동 포함된다고 설명하지 않는다.

코드 검사는 실제 AI의 의미 품질·서브에이전트 기여·브라우저 화면 인수와 구분한다. 이 M1 이후 발견한 후속 요청 조건 충돌과 UI의 미확인 중복 표시 결함은 별도 보완 소스에서 검증하고, 이 검사 결과를 새 소스의 전체 통과로 바꾸지 않는다. 원격 CI는 계정 지출 한도로 시작되지 않았으며 로컬 결과와 구분한다.
