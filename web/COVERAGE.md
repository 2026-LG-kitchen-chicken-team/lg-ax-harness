# 시각 자료 뷰어 검증 범위

2026-10-11 사용자 노선 변경으로 웹 입력·실행·내장 CLI를 삭제하고 원래 CLI의 시각 자료만 표시하도록 전환했다. 하네스 업무·Skill·Tool·자료·DB·로그인·LLM 설정은 변경하지 않는다. native 연결은 해당 하네스 폴더의 관찰 hook만 추가한다.

구현: server.py(읽기 전용 HTTP/파일 관찰/native hook), visuals.py(원본 snapshot), static/(한 페이지와 데이터 projection), tests/. 이전 adapter·실행 bridge·PTY·xterm·별도 입력·진행 화면·시험 파일·vendor manifest를 제거했다. 개발 기록과 실제 업무 자료는 보존했다.

자동 연결은 공식 [Codex hooks](https://learn.chatgpt.com/docs/hooks)와 [Claude Code hooks](https://code.claude.com/docs/en/hooks)의 SessionStart, PostToolUse, Stop 계약을 따른다. native 신뢰 검토는 유지하며 hook이 모델의 추가 문맥·권한·결과를 변경하지 않는다.

| 항목 | 범위 |
| --- | --- |
| 파일/HTTP | 실제 임시 폴더·원본 bytes·변경·재시작·HTML 자원·Host/Origin/CSP·읽기 전용 경로 |
| 데이터 projection | 보류·무효화·거절 후보·미확인값·요구사항/근거·행 미리보기 |
| hook 계약 | 프로젝트 설정 병합·멱등성·공개 근거 조회·이미지, 사고/프롬프트/일반 shell 기록 제외, 중첩 인증키·matrix 열·개인 설정 폴더 제외 |
| 실제 브라우저 | 인수 후 개인 .harness/viewer/qa/에 화면·지문 기록 |
| Codex native 자동 연결 | 인수 후 기록. fixture를 실제 callback 성공으로 설명하지 않음 |
| Claude 로그인 환경 | 사용자 요청대로 미실행. 공개 계약과 fixture만 검사 |
| Gemini | 사용자 요청대로 현재 native 설치·실행 검증 제외 |

파일 표시 성공은 결과 의미·실물 시뮬레이션·현재 DB 유효성·심사 품질을 입증하지 않는다.
실제 Codex CLI native 실행 1회(exit 0, thread 01a12b62-ebdb-7442-9d6f-9ed7674db47f): 기존 doctor 등록 수량 제품3·후기6·사실19 및 B502S33 리뷰2건을 조회하고 SVG/CSV/인터랙티브HTML 3개를 생성했다. 실제 SessionStart/PostToolUse/Stop callback, 새 파일 자동 등록, OS 브라우저 열기 반환을 기록했다. CLI만 시작했을 때는 브라우저를 열지 않았다. 실제 Node REPL의 비JSON pretty output은 임의로 파싱하지 않고, 동일 하네스의 지문 확인된 저장 조회 cache를 읽기 전용으로 표시한다. 현재 요청과의 연계는 추정하지 않는다. Python26건(25성공/OS symlink 권한1미실행), Node8건 성공, 실제 브라우저 HTML슬라이더95 유지·확대복귀·분류·390px폭·이전파일2버전을 확인했다. private QA 원본은 .harness/viewer/qa/. 모든 환경·미래 기능의 성공으로 확대하지 않는다.
