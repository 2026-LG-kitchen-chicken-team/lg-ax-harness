# LG AX Codex 상품기획 하네스

Python3.12, uv, Codex CLI와 실행자 자신의 Codex 로그인이 필요하다. 별도 LLM API key·환경변수·필수 MCP/플러그인은 요구하지 않는다. 모델 통신과 이용 한도는 Codex 계정에서 발생한다.

이 폴더에서 PowerShell/터미널을 열고:

```powershell
uv sync --locked
uv run python product-doctor.py
codex
```

첫 실행에서는 Codex가 안내하는 계정 로그인과 프로젝트 신뢰/권한 설정을 진행한다. 아직 CLI가 없다면 [공식 Codex 설치 안내](https://learn.chatgpt.com/docs/codex/cli)를 따른다. uv 설치는 [공식 안내](https://docs.astral.sh/uv/getting-started/installation/)를 따른다. 자동 설치 도구가 사용자 전역 설정이나 인증 파일을 변경하지 않는다.

첫 질문 예:

```text
T876MQQ012를 기준으로 수납·정리 개선안을 만들어줘. 하드웨어 추가 없이.
```

추가 질문 예:

```text
이전 안을 장보기 전에 쓰는 3단계 안내로 구체화해줘. 조건은 유지해.
```

내부 세션 ID·요청 키를 직접 입력할 필요 없다. 최종 요약과 실제 저장 영수증(receipt), export 경로·SHA를 확인한다. 전체 결과·의미 검토·원문 인용은 runtime-data/exports의 세션 JSON에 보존된다. 저장 승인만으로 의미 검토 통과를 보증하지 않는다. 근거 부족이면 보류, 모호한 모델이면 확인 요청을 반환한다. 개발용 역할6개/Skill9개는 이 폴더에 설치하지 않는다.

대화를 다시 열 때 Codex의 `codex resume`에서 해당 대화를 선택한다. 기록을 재개했다는 이유로 새 업무 turn을 시작하지 않는다. 모델/자료/조건이 바뀌면 과거 결과를 새 결과처럼 재사용하지 않는다. user/global Skill은 사용자의 설정에 따라 추가로 보일 수 있다.

doctor는 버전·로그인 상태·설치 파일 지문·실제 자료 조회를 확인한다. 자동 Skill 선택·AI 결과 품질·모든 Tool 권한을 보증하지 않는다. 지원/검증 범위는 원본 레포의 docs/validation/codex-product.md를 확인한다. 원문 로그·DB·개인 인증·의존성 환경은 공유하지 않는다.

현재 Windows 인수검사에서 workspace-write 모드는 Codex 명령 실행기 준비 오류로 실패했다. 전체 접근 모드에서 실제 업무 도구를 확인했으며 일반 샌드박스 지원을 통과시킨 것은 아니다. 실행 권한은 실행자가 Codex에서 선택한다. 설치 도구는 권한이나 전역 설정을 바꾸지 않는다.
