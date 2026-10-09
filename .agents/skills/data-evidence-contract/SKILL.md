---
name: data-evidence-contract
description: "신규 데이터·원문 근거·모델/버전 필터·캐시·조회 Tool을 만들거나 검토할 때 사용한다."
---

# data-evidence-contract

새 원문과 합성 여부·데이터 버전을 기록한다. 제품 model, document_version, source_id, page/section, 원문과 SHA256을 연결한다. 질문의 모델·버전 필터를 조회 전후 유지한다. 미기재/부재와 기존 기능/남은 불편을 구분한다. ID 형식 검사는 주장 의미의 근거 검사가 아니다. 입력·버전 변경 시 캐시/결과 재사용을 무효화하고 잘못된 모델·부족한 근거·원문 지시문 입력을 실제 검사한다. 기존 LG 자료를 가져오지 않는다.
