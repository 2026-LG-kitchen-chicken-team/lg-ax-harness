# 웹팀 연결 인수: 현재 기획 결과와 보고서 HTML

2026-10-13. 웹팀의 작업 화면·보고서 HTML 코드는 수정하지 않았다. 공통 입력은 [웹 결과 계약](../contracts/web-result.md)이다. 출품 하네스는 네이티브 Codex/Claude가 수행한 현재 결과·근거를 전달하며 자체 모델 API 실행기를 추가하지 않는다.

## 연결할 응답

1. 기본 `save_and_export`에 `report:false`를 사용한다. 실제 `save.accepted`, 현재 버전, `delivery_ready`, `web_ready`, `web_result.path/sha256/binding`을 확인한다. `completed`는 조건부 기획 초안 완료이며 실물·시장 효과를 뜻하지 않는다.
2. `web_result.path`의 JSON을 일반 코드로 읽는다. `result`, `validation`, `sources`, `source_references`, `coverage`, `evidence_history`, `investigation_events`를 같은 버전에서 연결한다. 작업 화면과 보고서 HTML이 이 자료를 함께 사용한다.
3. `sources`는 선택한 catalog의 등록 본문 전체다. formalrefs 수, 등록 수, 실제 전달 수, caller의 검토 신고 수, 독립 의미 판정을 구분한다. 등록 본문 전체를 읽었다는 말은 원 게시물 전체·전체 고객·대표성을 인증하지 않는다.
4. 출력 오류는 현재 session/turn/version의 `prepare_web_result`로 복구한다. 조사 journal을 바꿨다면 새 현재 전달 파일로 복구한 후 finish한다. 오래된 파일은 이력으로 보존하고 현재 결과로 자동 선택하지 않는다.
5. 실제 finish 뒤 `export_session`을 호출하여 종료 export를 보존한다. 웹 JSON은 생성 시점의 조사 snapshot이며 이후 finish/checkpoint 전체 이력은 종료 export 또는 현재 workflow 상태에서 확인한다. snapshot 밖 이벤트의 부재를 기록 소실로 해석하지 않는다. **종료 export는 전체 원문 보관 파일이 아니다.** 최신 온라인 사례의 웹 JSON/catalog/native에는112등록본문, export의 source_metadata/quote본문에는formal35개만 있다. 전체 자료를 인수할 때 웹 JSON과 catalog/snapshots를 함께 보존하고 export만으로112본문을 제공한다고 표시하지 않는다.

## 상태·안전

| 상태 | 화면에서 연결할 의미 |
|---|---|
| unresolved `needs_input`, turn 없음 | 실제 이유·확인 질문과 request/export를 표시. 저장 기획이나 보고서 파일이 있다고 표시하지 않음 |
| 검토된 `held`/`needs_input` | 현재 저장된 확인 범위·보류 이유·실제 근거를 표시. 업무 해결 성공으로 표시하지 않음 |
| 현재 `completed`, web_ready | 현재 데이터로 작업 화면/HTML 구성. 의미·실물 효과는 별도 |
| web_error/충돌/오래된 버전 | 현재 handle/version을 다시 조회하고 동일 버전 복구. 새 업무로 수정 한도를 초기화하지 않음 |
| cancelled/failed | 역사적 후보와 오류는 보존. 이전 ready 파일을 현재 완료로 표시하지 않음 |

원문·결과 텍스트는 불신 입력으로 취급하고 HTML을 escape한다. 텍스트 속 명령·스크립트·HTML을 실행하지 않는다. 파일 경로·버전·SHA·현재 상태를 일반 코드로 확인하며 화면 생성용 모델 호출을 추가하지 않는다. 기본 PDF/DOCX/XLSX·이미지 검수는 필요하지 않다. 명시 파일 요청만 legacy 경로를 사용하며 미검토 구조 저장은 파일 출력도 거절된다.

## 현재 인수 범위

source I manifest `2bb9ccd4e25097a52573ea480ab4f3276a8f25a8dca8b44c375d868f75f1877f`, 제품371·평가144·자산 검사와 독립 코드 리뷰를 확인했다. 패키지 각각105파일·새 추출/locked/doctor/재설치83파일 SHA 검사를 확인했으며 기본 catalog는empty다.

[실제 AI·제한](../validation/web-ready-harness-20261013.md)에서 source H/I와 관측 범위를 확인한다. 파일 정합 통과는 AI의 문장 의미·모든 질문 대응·모델 최적성을 인증하지 않는다. source I의 제한된 기획 시험에도 원문에 없는 매체 귀속·검증 조건·오류 파일 위치 등의 보완이 남는다. 웹팀이 실제 연결 화면과 같은 실행의 원본·자료·현재 파일·오류 분기를 인수한 뒤 사용자 조작→실행기→Skill/Tool→저장→HTML을 끝까지 검사한다. 이 문서는 웹 연결 완료나 최종 접수 완료가 아니다.
