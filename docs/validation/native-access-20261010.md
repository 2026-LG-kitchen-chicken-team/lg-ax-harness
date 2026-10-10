# Claude·Gemini 실제 접근 확인

2026-10-10. 사용자는 Windows에 있는 Claude/Gemini 실행 확인을 승인했다. 데스크톱 채팅 로그인과 로컬 Agent·Skill·Tool을 실행하는 native CLI 인수를 구분했다. 구독 결제·유료 API 전환·사용자 전역 설정 변경은 하지 않았다.

Claude 앱은 Free 계정과 Code 시작 안내를 표시했다. 사용할 수 있는 Claude Code CLI/인증은 확인하지 못했고 사용자가 유료 계정이 없다고 답했다. 출품 업무 입력0회, S02b2/S03b2/D06b는 미완료다. Claude 데스크톱 일반 채팅을 Skill 검증으로 대체하지 않았다. 팀원의 사용 가능한 Code 환경에서 설치·신뢰·발견·정상/후속/보류·사용량을 검증해야 한다.

Gemini 데스크톱 앱의 로그인은 확인했지만 그것이 Gemini CLI의 로컬 Skill 권한은 아니다. 공식 npm 패키지 `@google/gemini-cli@0.63.0`을 Git 제외 `.harness/native-env/gemini`에만 설치했다. 실제 설치 exit0, CLI version/help exit0. `GEMINI_CLI_HOME`을 별도 비공개 폴더로 지정하고 전역 설정을 변경하지 않았다. 개발 레포 신뢰를 부여하지 않은 인증 확인이다.

개인 Google 계정의 브라우저 OAuth는 인증 완료 화면까지 도달했지만 CLI 서버는 다음 메시지로 사용을 거부했다: `This client is no longer supported for Gemini Code Assist for individuals.` 이어 Antigravity 제품으로 이동하라는 안내가 표시됐다. 이는 **이 버전·이 계정의 실제 인증 실패**이며, 모든 Gemini 계정/버전의 정책으로 일반화하지 않는다. 터미널을 정상 종료한 exit0은 인증 성공이 아니다. 업무 입력0회, S02c2/S03b2는 미완료다.

[공식 인증 문서](https://geminicli.com/docs/get-started/authentication/)의 개인 OAuth 안내와 실제 서버 결과가 일치하지 않았다. 같은 오류가 보고된 [공식 저장소 Issue28229](https://github.com/google-gemini/gemini-cli/issues/28229), [Issue28745](https://github.com/google-gemini/gemini-cli/issues/28745)는 참고 신고이며 보편적 정책의 근거로 사용하지 않는다. 별도 Antigravity 실행 방식·API 키·구독을 자동 채택하지 않았다.

현재 제품 지원은 Codex의 실제 검증과 Claude/Gemini의 설치·auth-free doctor 검증을 구분해 안내한다. 위 두 환경은 재인수 가능한 인증 환경이 확보될 때 이어간다. 원본 계정·인증 파일·전체 로그는 Git에 저장하지 않는다.

## 1–7 작업의 재확인 — 2026-10-11 KST

기존 비공개 Gemini home과 CLI0.63.0에서 headless 로그인 진단을 새로 1회 실행했다. timeout30초, 실제 **exit55**, 서버의 같은 `This client is no longer supported` 거절을 받았다. 질문에 대한 최종 답변은 없었으며 출품 업무 입력은 여전히0회다. 진단 로그1496bytes의 SHA256은 `8ada1b23babba9b60c5632d22700740598f462b758a57b754e440d94c46dbfc1`이며 원본은 Git 제외다. 인증 파일 본문·계정 토큰은 읽거나 출력하지 않았다. 실패를 terminal 종료 성공이나 CLI 지원 성공으로 바꾸지 않는다.

Claude는 현재 사용할 수 있는 CLI를 찾지 못했고 사용자가 유료 계정이 없다고 확인했다. [공식 인증 안내](https://code.claude.com/docs/en/authentication)의 Code 접근 경로와 [Gemini 공식 인증 안내](https://geminicli.com/docs/get-started/authentication/)를 대조했지만 이 PC에서 인수 가능한 환경을 확보하지 못했다. 유료 계정·API로 자동 전환하지 않았으며 팀원 환경의 실제 native 결과 회신이 남는다.
