# 길웅 화면 PR10·11 인수와 하네스 연결

사용자는 2026-10-14 길웅의 최신 메일을 확인하고 연동을 승인했다. 하네스 품질·선택 역할 작업과 연결 검증을 완료한 뒤 결과 메일 초안을 확인하는 순서를 유지한다. 같은 날 수신한 「[LG AX] 시각자료 뷰어 PR #10 올렸습니다 (최신 main 기준)」은 PR10의 뷰어/보고서와 별도 PR11의 기획 사무실을 안내했다.

- [PR10](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/10): 인수 head `1576a6c2a31d7a927bf73f02eaea4abf33202f80`. 13종 보기, J/K/M 근거 대시보드·원문 통합, 단일 카드 배치, LG 로고, 업무형 안내 문구.
- [PR11](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/11): 인수 head `7c8e61b305e3424d0a5b3ac61dd203bbdfacbc71`. 별도 3D 관찰 화면, Claude 훅/Codex 기록, 실제 재생과 가상 데모의 구분.
- CI의 실패 표시는 직접 확인한 annotation상 계정 결제/지출 한도로 job 미시작이다. 실행 검사 실패나 통과로 바꾸지 않는다. 팀원의 로컬 통과 보고와 이번 실제 로컬 인수 명령도 구분한다.

## 최소 연결 범위

디자인을 유지하고 export snapshot에 현재 기대 웹 binding을 넣는다. 뷰어는 같은 session/turn/request/result version과 result/context/code/data/audit 지문의 불변 웹 JSON을 선택하고, 저장된 검토 gate를 확인한다. 파일 이름·원 바이트 SHA도 대조한다. 최초 export→web 파일 생성 순서 때문에 파일 경로만 export하는 방식은 사용하지 않는다.

인용에 쓴 근거와 선택 등록 원문 전체를 나눠 표시한다. 선택 본문 전체·출처·모델/문서/자료 버전·SHA, 전달/검토 이력·조사 일지를 같은 결과에 연결한다. 기획자 화면과 단일 보고서 HTML은 같은 데이터를 일반 코드로 렌더링하며 화면을 만들기 위한 추가 모델 호출을 넣지 않는다.

같은 turn의 수정 전 insights는 session/turn만 맞아도 재사용하지 않는다. 전체 binding이 없거나 현재 것과 다르면 현재 해석으로 적용하지 않는다. 보류/취소/거절 이력은 보존한다.

별도 관찰 사본에서는 질문 원문을 복제하지 않고 최신 Tool 목록·실제 취소 사건과 열린 호출의 중단 상태를 맞춘다. 서로 다른 DB의 최신 workflow/request/turn을 시간 근접성만으로 같은 업무라고 인증하지 않는다. 역할 정의, 실제 native 호출/반환, 파일 재생, 가상 데모를 구분한다.

## 인수 순서

고정 core → PR10 → PR11 → 최소 연결 patch → manifest 재생성 → 실제 코드/설치 검사 → 동일 소스 native 업무/역할/예외 → 실제 화면/보고서 검수 → 결과·사용법 인계. 실질 변경·명령·시간·usage·원로그 지문은 별도 인수 기록에 남긴다. 이 문서는 착수 계약이며 구현·최종 접수 완료를 대신하지 않는다.
