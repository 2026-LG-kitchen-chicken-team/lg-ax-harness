# 제품 v0.8.0 시험판

자료집·보고서 제작과 실패 복구, 공통 Codex/Claude 작성 지침, 문서 의존성 잠금을 반영한 제품 전용 시험판이다. 상세 구현·실제 모델 결과·사용량·검수 범위는 [출력 검증](reader-deliverables-20261012.md)을 따른다. source 모델 비교와 최종 재인수의 원본을 구분한다.

## 준비한 제품과 무결성

| 항목 | 확인값 |
|---|---|
| 제품 source provenance | `018ee533cfd7e1bb5ab3da75a9b8f973f9702adb` |
| 부모 없는 제품 snapshot | `8e58057a5ec4910066a547ab62eee507669c3405` |
| 제품 tree | `181cc3878174d793ad2608c5bb591cfa34ca9aed` |
| ZIP | `lg-ax-harness-product-v0.8.0.zip` /78파일 |
| ZIP SHA256 | `fcf27e6fabae93b18f481902157fed811d46870f3ddab5a2dca7e3fc7aa93c00` |
| 공통 source manifest | `b68147d14d3c534e5b6b21028e6956425352644c7d4211e456eb8502acc37dbf` |
| 설치 manifest | `40278a3dd96a531e0ee80aae7771a72fca36a3f889fb477a49cc05c6afcf8bd5` |

ZIP의 CRC·중복/위험 경로·manifest77파일 SHA·빈 기본 catalog·필수 모듈/계약/잠금/라이선스를 확인했다. 개인/원문 실행 로그·DB·환경·개발 역할·평가 질문·합성 검수 예제는 제외했다. ZIP과 snapshot78파일을 각각 byte 대조했고 부모 commit이 없으며 main 작업 index가 변하지 않았음을 확인했다.

ZIP을 새 폴더에 추출해 Codex 잠금 설치/doctor를 실제 실행했고, ZIP 내부 adapter로 별도 Claude 폴더를 설치한 뒤 잠금 설치/doctor도 exit0였다. 이는 Claude AI 실제 작동 인수와 별개다. 제품229·평가128코드 검사(합계357)와 원문/배치 독립 검토를 통과했다.

## 지원과 제한

최신 GPT-6.1 Sol 실제1입력은 보류 분석의 저장/전달과5파일 생성을 확인했다. 두 모델 비교에서 Sol은 제한된 판독 검토를 통과했고 Luna는 요청 분류 누락/불확실한 남은 불편의 지적이 있어 부분 충족이다. 최종 원요청 이행 지침 보강 후 Luna·Claude의 새 AI 재인수는 미실행이다. 자동 의미 인증이나 전 제품군/미사용 평가 통과, 개선안·실물 효과·사람 대비 절감은 주장하지 않는다.

Excel 원자료는 편집 가능하다. 차트는 동일 렌더링 이미지이며 계획에서 재생성한다. 비Windows 한글 차트·영상/리허설·웹 연결·운영진 최종 규격/접수는 별도다. 과거 품질 실패·timeout·원격 CI 제한을 제거했다고 하지 않는다.

## 원격 반영

현재 파일은 로컬 준비 검증 기록이다. main 반영·원격 tag·Release 업로드·실제 다운로드 SHA 및 자동 tag archive의 byte 대조 결과는 실행 뒤 이 절에 추가한다. 기존 릴리스와 파일을 덮어쓰지 않는다.
