# 신규 조사와 의미 오류 집중 회귀

입력 원본은 `evals/judge/discovery5.json`이며 5입력/4대화, 한 입력 최대420초, 자동 재실행0회다. 실제 실행 전에 prompt·제품 source·runner·원본 자료를 private report에 동결했다. 공식 심사 문제나 독립 blind holdout이 아니며 이 결과로 일반 정확도를 추정하지 않는다.

| 입력 | 검사 목적 | 초기 자료 |
|---|---|---|
| D01 MW23GD | 정확 모델 조사·실제 불편·기존 기능 대조·등록·기획 | 빈 catalog |
| D02 실제 후속 | 같은 대화/원문/이력 보존과 변경 제약 | D01 등록 자료 유지 |
| D03 MWJ25E | 미확인 중복을 false로 확정하는 오류 재발 여부 | 정당한 과거 v4 실제 원문 |
| D04 DUBJ2EA | AI 해석을 제조사의 공식 문구로 귀속하는 오류 재발 여부 | 정당한 과거 v4 실제 원문 |
| D05 H874GBC111 | 신규 모델 조사와 내부 치수 부족의 정직한 처리 | 빈 catalog |

새 모델의 실재 여부만 사전 확인했다([MW23GD 공식 페이지](https://www.lge.co.kr/microwaves-and-ovens/mw23gd), [H874GBC111 공식 페이지](https://www.lge.co.kr/refrigerators/h874gbc111)). 모델의 업무 답안·불편·근거 pack을 새 설치에 미리 넣지 않는다. D03/D04는 Claude에서 발견된 공통 의미 오류를 현재 Codex 구현으로 회귀하는 것이며 최신 Claude 실행 검증이 아니다.

7축은 기존 진단과 같은 목적/제약, 정확 모델/버전, 불편→기능→제안, 출처 의미, 미확인/보류, 최종·저장 정합, 실행/검증 계획이다. 각0–2 또는 근거 있는 N/A이며 적용축 환산12/14 이상·0점 없음·중대 오류 없음이 필요하다. 구조 검사 accepted=true만으로 원문 의미를 통과시키지 않는다. 오류 회귀의 핵심은 duplicates_existing=null 유지와 support_quote/factual_summary/AI해석의 구분이다.

새 자료는 실행 중 변경 가능하므로 입력 전후 원문·catalog·import-audit·DB backup·export를 보존한다. 제품 코드·Skill·빈 seed 변경은 실패다. 원문 입력과 실제 prompt, 실제 native ID, source 인용·모델 신원, 최종 pointer와 당시 DB를 대조한다. 보류를 기획 completed로 세지 않는다. 부모 전달 실패 시 예정된 후속을 새 대화로 바꾸지 않고 not_run으로 남긴다.

수집기 사용량의 전체성 명칭과 등록 경로 판정은 추가 감사를 거친다. 실패도 관측 사용량에 포함하고 unknown을0으로 만들지 않는다. native session의 누적 snapshot은 같은 session 마지막 값만 집계하며 실제 backend 모든 호출·청구·절감률·사람 효과는 별도 증거가 없으면 미입증이다.

시간 초과 후 같은 요청의 복구를 추가로 확인하는 경우에는 별도 단일 진단으로 기록한다. 기존 실패/미실행을 성공으로 덮어쓰지 않고 전체 소요·추가 입력·후속 누적 사용량을 분리한다. 원래 질문을 다시 실행하거나 답안을 주입하지 않는다.
