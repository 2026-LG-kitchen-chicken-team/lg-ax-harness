# 열린 이슈 전체 검토 — 2026-10-11

사용자 요청에 따라 GitHub API의 열린 이슈 전체 페이지와 모든 댓글을 읽었다. 5건(#1–#5), 댓글은 #3의1건이며 다른 이슈는0건이었다. 이슈의 주장과 직접 재현을 구분한다. 이 검토는 이슈 댓글 게시·닫기 작업을 포함하지 않는다.

| 이슈 | 판정 | 이번 조치와 남은 근거 |
|---|---|---|
| [#1 Codex B502S33 첫 질문·후속](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/1) | 과거 팀 실행 보고, 전체 인수 불충분 | 212초/113초는 화면 보고. 원본 export/native가 없어 전체 저장 무결성·usage 미확인. 최신 버전 성적으로 합치지 않음 |
| [#2 Codex T876MQQ012 자료 부족](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/2) | 발췌의 보류는 타당, 원본 검증 불충분 | 외형914mm로 내부 배치를 확정하지 않은 점 확인. 143초는 화면 보고. 내부 유효 치수·간섭 근거와 당시 원본 저장은 미확인 |
| [#3 Claude 같은 대화의 첫 질문·후속·자료 부족](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/3) | 팀 보고5turn, 독립 native 인수 미완료 | 본문·사용량 댓글을 대조. 같은 대화와 #2 새 대화를 동일 조건으로 비교하지 않음. 인용 이어붙임 정정·집계4→5·문서 적용·실패 이력·사용량 원본 필요 |
| [#4 assessment 타입 오류의 실패 이력 누락](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/4) | 현재 코드·v0.4.0 태그에서도 재현, 수정 완료 | 6개 연결 ID 위치를 set 조회 전에 검증. 유효 JSON의 잘못된 검토 타입은 계약 오류로 후보 이력에 기록하며 최초+수정2회 한도 유지 |
| [#5 콜론 session_id의 Windows ADS export](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/5) | 현재 코드·v0.4.0 태그에서도 재현, 수정 완료 | 파일명은 export-본문SHA.json, 본문 session_id는 유지. 일반 디렉터리·복사·ZIP 바이트/SHA와 구코드 DB의 콜론 세션 재export 확인 |

## #4/#5 직접 재현과 수정 검증

별도 읽기 전용 개발 Agent가 수정 전 current70f2a1d 및 로컬 product-v0.4.0 태그의 새 Temp 추출에서 실제 CLI 재현했다. 원격 첨부 ZIP을 새로 내려받은 재검사는 아니다. Windows/Python3.14.7에서 #4 네 번 모두 tool_error/TypeError와 version0/history[]를 확인했다. assessment=null 대조는 거절 후보 version1로 남았다. #5 반환 경로 직접 읽기는 SHA가 맞았으나 일반 열거·ZIP에는0바이트 audit 파일만 남았다.

수정 후에는 부모의 Python3.12 제품 전체174개와 신규3개 검사, 독립 Agent의 기존 DB 복사 CLI 재검증을 통과했다. 잘못된 ID18조합, 실패 후보3회(version1/2/3, 마지막held), 네 번째 business_revision_limit/history3, 동일 키 재전송 receipt, 콜론·예약어·마침표 세션명5종의 일반 파일·복사·ZIP 바이트를 확인했다. 일반 프로그래밍/DB 오류를 광범위하게 숨기는 TypeError catch는 추가하지 않았다.

기존 콜론 세션은 DB가 남아 있으면 새 버전의 export_session으로 다시 내보낼 수 있다. 이미 본문이 빠진 ZIP만으로 잃어버린 원문을 복원할 수 있다고 약속하지 않는다. 이전 파일·실패·세션을 자동 삭제하거나 덮어쓰지 않았다.

신규 test_issue_regressions의 최초 실행에서 직접 함수가 받지 않는 response_mode를 fixture에 넣어1건 실패했고, fixture를 실제 함수 계약으로 고친 뒤3건 통과했다. 제품 검증을 느슨하게 바꾼 것이 아니다. 전체174개 receipt:20d789ba670749ac9e858b8423e33908, 독립 재현·수정후 명령/응답은 private Temp에 보존했다.

## 팀 실행 기록의 해석

#3 [사용량 댓글](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/3#issuecomment-6099945979)의 합은97응답, 비캐시 입력194·캐시 생성269,976·캐시 읽기19,323,652·출력134,939, 경과1,608초다. 후속616초에는 승인 대기67초가 있다. 팀원 집계 보고이며 전체 호출·실패 포함 여부·청구액은 원본 없이 인증하지 않는다. [v0.3.0 메일 접수본](team-runs/records/20261011-claude-mail-review.md)의 네 입력/19응답과 별도 실행이므로 합산하지 않는다.

현행 BOM UTF-8/UTF-16 처리·CLI UTF-8 출력은 확인했다. 임의 사용자 스크립트의 인코딩까지 보장하지 않는다. 정적 수집기의 redirect 차단·PDF 비지원은 native 원문 도구 또는 정직한 보류로 처리할 경계다. snapshot 안의 인용 일치는 검사하지만, 호출자가 원문을 잘못 이어붙인 snapshot 자체의 진실성은 실제 native 원문 대조가 필요하다. 새 자료의 data_path 누락으로 생긴 지문 무효화를 우회하지 않는다. 잘못된 입력 필드·빈 native_tool_name 거절을 곧바로 코드 결함으로 분류하지 않는다.
