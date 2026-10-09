# 실제 시간·공수 비교 절차

2026-10-10. 현재 AI 실행 경과 시간은 관측하지만 사람의 직접 작업 시간·현금/크레딧 청구는 미측정이다. AI 실행 시간 차이를 사람 공수 절감률로 바꾸지 않는다. 평가자는 같은 실제 자료·모델·기획 조건·완료 기준의 R01 또는 R03을 사용한다.

사람의 기본 업무는 제공 원문 읽기 → 불편/상충 의견 정리 → 정확한 기존 기능 대조 → 근거와 미확인 사항을 붙인 제안이다. 필요하면 같은 강한 일반 프롬프트를 사용할 수 있으나 수동 업무와 일반 AI 보조 업무를 별도 조건으로 기록한다. 제품 하네스 결과·정답·rubric은 작업 전에 전달하지 않는다.

각 조건에서 전체 시작/완료 시각, 사람이 실제로 읽기·입력·근거 확인·수정에 쓴 활동 구간, 추가 입력 수·수정 수, 최종 파일·출처를 기록한다. 대기 시간을 활동 시간으로 채우거나 기억으로 추정하지 않는다. 첫 사용 설치 시간은 별도로 기록하고 설치 완료 업무의 시간과 합치지 않는다. 순서를 바꾼 반복이 가능하면 수행하고 불가능하면 표본 제한을 밝힌다.

독립 원문 평가가 같은 요구를 충족했는지 확인한 뒤 사람의 활동 시간·전체 완료 시간·실패율을 비교한다. 실패·중단·수정 비용도 전체 분모에 포함한다. 보류가 정답인 과제는 근거 있는 보류를 완료로 본다. 품질을 낮추거나 원문을 생략한 시간 감소를 효과로 계산하지 않는다.

```json
{
  "case_id": "S05-R01",
  "condition": "manual | general_ai | harness",
  "data_fingerprint": "actual fingerprint",
  "model_and_settings": null,
  "started_at": null,
  "finished_at": null,
  "human_activity_intervals": [],
  "human_active_seconds": null,
  "setup_seconds": null,
  "additional_inputs": null,
  "revisions": null,
  "result_artifact": null,
  "independent_quality": "pending",
  "observed_usage": null,
  "actual_charge_or_credit_change": null,
  "charge_attribution": "unverified"
}
```

원본 작업 기록은 runtime-data/.harness 등 Git 제외 위치에 저장한다. 공개 보고서에는 개인정보·인증·원문 로그 없이 검증 가능한 합계와 제한을 적는다. 개인별 실행 환경/구독 크레딧을 API 단가로 환산하지 않는다. 계정의 동시 개발 사용이 있으면 잔액 차감을 해당 업무 비용으로 단정하지 않는다.
