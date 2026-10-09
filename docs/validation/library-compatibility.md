# 라이브러리 호환성 검사 기록

검사일: 2026-10-10. 레포·전역 환경에 의존성을 설치하지 않고 별도 Windows Temp 환경에서 확인했다. 유료 LLM/API 호출은 0회다. 아래는 라이브러리 실행 호환성 증거이며 출품 Agent·개발 Agent 체계·AI 답변 품질·토큰 절감의 인수검사 결과가 아니다.

사용자 정정 이후 LangGraph는 독립 실행 후보로, React Flow 내장 UI는 철회한 과거 후보로 분류한다. 아래 검사 사실은 유지하지만 최종 실행 방식·별도 관찰 도구의 채택이나 연결 성공을 증명하지 않는다.

## LangGraph / SQLite

Python 3.12.14 64bit. `langgraph==1.2.14`, `langgraph-checkpoint-sqlite==3.1.1`을 wheel만 설치하고 `pip check` 통과. 함께 해석된 패키지는 checkpoint 4.2.0, langchain-core 1.6.9, Pydantic 2.14.0, sqlite-vec 0.1.9, aiosqlite 0.22.1이다.

| 검사 | 실제 결과 |
|---|---|
| 정상 결정적 상태 그래프 | completed 경로에 해당하는 accepted 상태, 수정 0회 |
| 자료 없음 | 즉시 held, review/revise 노드 미실행 |
| 1회 수정 | review→revise→review→accepted |
| 2회 수정 후 미해결 | 수정 2회, held 종료 |
| custom/updates 스트리밍 | 실제 node 이벤트·상태 변경 수신 |
| SQLite 닫기·재열기 | 상태 재조회 통과 |
| 별도 thread_id | 서로 다른 실행 상태 격리 통과 |
| AsyncSqliteSaver | 동시 두 실행의 이벤트·상태 격리, 재열기 통과 |

AI 판단은 결정적 코드로 모사했다. JSON 모델 출력·한국어 기획·실제 근거 정확도·API timeout·SSE·UI는 이 시험에서 평가하지 않았다.

로컬 재검토 근거:

- `C:/Users/user/AppData/Local/Temp/lg-ax-runtime-check-le5_20uf/probe_runtime.py`
- `C:/Users/user/AppData/Local/Temp/lg-ax-runtime-check-le5_20uf/probe.summary.json`
- `C:/Users/user/AppData/Local/Temp/lg-ax-runtime-check-le5_20uf/probe_async.py`
- `C:/Users/user/AppData/Local/Temp/lg-ax-runtime-check-le5_20uf/async_probe.summary.json`
- `C:/Users/user/AppData/Local/Temp/lg-ax-runtime-check-le5_20uf/requirements.freeze.txt`

Temp 파일은 제출물의 실행 의존성이 아니다. 실제 backend의 잠금 파일·의미 있는 인수검사로 이어서 대체한다.

## React Flow / React / Vite

Node 22.23.2, npm 10.9.8. React Flow 12.12.0, React/React DOM 19.3.0, Vite 8.3.4, TypeScript 7.0.2, React/DOM 타입 19.3.0을 고정한 작은 호환성 stub으로 검사했다. npm 캐시도 Temp 안에 두었다.

- 설치: `--ignore-scripts`로 통과.
- 최초 타입 검사: CSS import 타입 선언 누락으로 TS2882 실패.
- 수정: 표준 `src/vite-env.d.ts`에 `vite/client` 참조 추가. 검사 설정·의존성 완화 없이 해결.
- 수정 후 `tsc --noEmit`, Vite production build 통과.
- 해당 조합의 npm audit: 보고된 취약점 0개.
- Rolldown이 React Flow의 `use client` 지시문 관련 비차단 경고를 출력했다.

실제 브라우저 표시, Agent·Skill 실행, SSE, 재접속·취소·재생은 아직 미검증이다. 두 노드와 연결선의 stub을 출품 UI로 설명하지 않는다.

로컬 근거: `C:/Users/user/AppData/Local/Temp/lg-ax-reactflow-compat-be23344adf174874abf4e5784c6d4d10/`의 `result.json`, `verify.ps1`, `verify-vite-env.ps1`, `src/main.tsx`와 최초/수정 후 로그.

## 남은 실제 검사

1. Codex 네이티브 역할 발견·위임·중단·검사 결과·독립 리뷰 통합.
2. Claude 팀원 환경의 발견·위임·실제 검사·인수인계.
3. 초기 모델 계정 접근·Responses 어댑터·구조 출력·Tool·usage·오류 실제 연결.
4. 새 데이터와 실제 AI 심사 입력·추가 질문·품질·토큰·비용 평가.
5. 실제 실행→일반 코드 수집→별도 관찰 도구의 구조·흐름 표시. 수집 범위·지연·on/off 모델 호출·문맥·사용량·업무 격리·재접속·재생.
6. 잠금 파일과 README를 사용하는 새 환경에서 ZIP 전체 흐름·Skill 재실행.
