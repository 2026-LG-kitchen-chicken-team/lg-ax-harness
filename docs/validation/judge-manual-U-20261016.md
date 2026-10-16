# v0.16.1 사용설명서 개편·패키지 인수

2026-10-16 사용자 승인 계획에 따라 심사위원 README를 「LG AX 상품기획 에이전트 사용설명서」로 개편했다. [설명서](../contracts/judge-test.md), [검사 기록](judge-manual-U-20261016.json).

- 한 문서에 소개·준비물·첫 실행·질문 예시·화면 역할·재사용/종료/보관·문제 해결을 순서대로 제공한다. 각 단계의 행동과 보이는 결과·다음 행동을 연결했다.
- Windows 앱/CLI와 Codex/Claude의 폴더·로그인·권한을 구분했다. 원클릭을 마치면 수동 설치를 반복하지 않는다. 수동 명령은 뒤쪽 부록으로 옮겼다.
- 공식 Codex 명령 문서, Claude Desktop/Setup, uv 설치 문서를 확인했다. Windows codex app 이후 수동 폴더 선택 가능성, Claude Code/Local과 GUI의 CLI 불필요를 설명한다. 모델 기본값은 변경하지 않았다.
- 원본 docs/contracts/judge-test.md와 ZIP root README·두 엔진의 설명서 사본이 raw byte 동일하다. 목차9링크·런처8개·상세 권한/도구 경로를 대조했다.
- focused judge package9/source package2/asset 검사 모두 exit0, 테스트 skip0. 각 receipt와 로그 SHA를 대조했다. 문서 패치이므로 전체 AI 회귀·웹 빌드를 반복하지 않았다.
- 새 ZIP만 풀어 두 엔진 설치·무결성·상태·prepare·실제 Windows MXC11명령 exit0. 원 저장소 없이 설치하며 모델 호출·브라우저 열기는0이다.
- 심사 ZIP205파일 중 문서/문서 지문/설치·bundle 메타데이터8개만 변경, 나머지197파일은 v0.16.0과 동일하다. 소스 ZIP128파일에서 동일 심사 ZIP 재생성을 확인했다.
- 실행 코드·Skill 내용·역할·런처·모델/권한 기본값은 유지했다. skills/manifest.json에서는 설명서 shared_file SHA 한 개만 바뀌었다.

소스 고정 커밋은 5b1729c19247065d872ed5ac2d02b32d1cbae238다. 독립 읽기 전용 리뷰가 문서·런처 계약과 실제 검사 범위를 대조했고 미해결 P1/P2는 없었다. 입력 지문 8개와 receipt/log SHA가 일치하며 개발 장부 complete도 errors[]로 종료했다. 이 문서 패치는 새 AI 업무·GUI/브라우저 물리 검수·다른 운영체제 실행 성공을 주장하지 않는다. 원격 다운로드 대조와 배포는 product-v0.16.1.md/JSON에 별도로 기록한다.
