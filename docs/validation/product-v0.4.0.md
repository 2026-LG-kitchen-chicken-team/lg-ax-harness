# 제품 v0.4.0 시험판 배포 검증

2026-10-11. [제품 v0.4.0](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.4.0)을 prerelease로 발행했다. 모델코드 없는 제품군·축약명 입력과 후속 전체 범위/제외 조건 유지, 명시 모델 선택 시 좁히기가 제품 변경이다. 등록5모델 사례 범위이며 임의 새 모델 자동 조사/등록·매 요청 최신 조사·팀 웹 실행 연결은 추가하지 않았다.

| 식별 | 실제 값 |
|---|---|
| main provenance | `ca16e2b3db63e19c64102c9c00da94b4fce01121` |
| 제품만의 parentless snapshot | `38f60f2b9caa74164200fcfe64bd89bfdd17b7d5` |
| 제품 tree | `4db02d5c828a9d3402b893f2ae3666624ce22c0a` |
| ZIP | `lg-ax-product-v0.4.0-codex-source.zip` |
| ZIP SHA-256 | `91a1589736175bd1cb0de12fd101b48fd56416d37e6f8dcb497991cd466919d7` |
| 첨부물 | 위 ZIP·`SHA256SUMS.txt`만 |
| 파일 | ZIP/원격 tree68, manifest67항목 |

원격 tag commit·부모0·tree·첨부 이름·재다운로드 ZIP/SHA 목록·모든 원격 blob와 ZIP 바이트를 실제 대조했다. LICENSE/NOTICE를 보존하며 개발 역할/Skill/장부·평가 입력/runner·원문 로그·SQLite·인증·의존성 환경·관찰 화면·미완성 영상은 제품 tree/ZIP에 없다. 공식 최종 제출이 아니다.

로컬 제품147·평가117·assets 실제 exit0, 독립 코드 검토, 원본 prompt/native/stderr/결과·리뷰·export/SQLite·공개 집계·동결 코드·ZIP의 task-bound 통합 감사와 독립 완료 검토를 확인했다. guard receipt는20입력/작업/시도 지문·명령/exit0·잘림 없는 로그를 대조했고 당시 `complete`는 errors=[]였다. 이후 이 배포 기록은 새 문서 변경이며 앞선 receipt를 이 문서의 검사로 재사용하지 않는다. 기존 기록 명령 오류·초기 거절·표현 비교 실패도 보존했다.

[v6.0의50문항](regression50-20261011.md)은50입력/40대화·초안18/보류27/확인5다. 이번 [v6.1 별도10문항](family10-20261011.md)은10입력/8대화·초안4/보류3/확인3이며 각각 정의한 의미 판정을 통과했다. 최신 버전60개 통과로 합산하지 않는다. 알려진 짧은 저장 근거·공개 진단 질문의 제한이며 조건부 초안의 효용·시장성 실증과 구분한다.

새 Temp 폴더 추출·CRC/파일 SHA·`uv sync --locked`·Codex doctor·별도 Claude 파일 설치를 실제 재현했다. Claude native는 미검증이고 Gemini 활성 지원은 철회했다. 원격 CI/모든 OS·새 실행자의 native 인수는 이 검사에 포함하지 않는다.

설치는 새 폴더에 ZIP을 풀고 `uv sync --locked`, `uv run python product-doctor.py`, `codex`를 실행해 자연어로 묻는다. 이전 DB·실패·후보를 덮어쓰지 않는다. 현재 등록 자료는 v4의5모델/8후기/26사실이며 부족한 청소/건조 불편·내부 치수·미확인 물리 안전은 보류/확인한다. 전체 backend 청구·baseline 대비 절감·사람 효과·미사용 평가·Claude native·시연 영상·최종 접수는 미완료다.

현재50/10 공개 보고서가 기준이다. 별도 생성된 `*-reviewed-20261011` 복제 문서4개는 원본을 보존하고 이번 main 커밋에서 제외했다. 원문 실행 로그·비공개 receipt/키는 Git 제외다. 웹 PM의 로컬 작업은 원본 미업로드·미검토이며 [자료 정책 검토](web-data-analysis-20261011.md)의 제안은 미채택이다.
