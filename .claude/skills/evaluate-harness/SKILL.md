---
name: evaluate-harness
description: "출품 AI에 직접 넣는 심사 입력·예외·다중 턴·출처·전체 호출 토큰과 비용을 평가할 때 사용한다."
---

# evaluate-harness

`docs/evaluation/judge-input-cases.md`에서 정상/후속/예외 입력을 선택하고 실제 입력과 응답을 보존한다. 신규 fixture 계약 검사와 실제 모델 실행을 구분한다. 원문 의미·모델/버전·출처·보류/수정/종료를 독립 검토한다. [토큰 감사](references/token-quality-audit.md)로 모든 하위·실패·수정 호출을 포함하고 unknown을 0으로 바꾸지 않는다. 동일한 입력·성공 기준의 baseline과 품질/전체 사용량을 비교한다. 아직 없는 업무 runtime의 입력 사례를 통과했다고 보고하지 않는다.
