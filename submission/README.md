# 제출 준비 원본

현재 제출 상태는 preparation_only다. [발표 구성](demo-plan.json)과 [실제 시연 절차](demo-runbook.md)를 작성했으며 발표 파일·영상·최종 제출은 미완료다. 코드·근거·검사와 맞는 내용을 준비하고 아직 관측하지 않은 기능·효과는 제외한다.

개발 레포에서 `uv run python scripts/check-submission-preparation.py`로 분량·시간 계획·C01~C09 근거 경로를 검사한다. 이는 영상 촬영·발표 리허설·파일 제출 완료 검사가 아니다.

최종 업무 소스는 README의 package 명령으로 새 ZIP에 만든다. ZIP 원본·manifest·LICENSE/NOTICE·Skill 폴더·잠금 파일을 새 환경에서 확인한다. 원문 실행 로그·SQLite·인증·전역 설정·개인정보·의존성 환경·개발 역할·평가 입력/runner·사용자 첨부 PDF를 포함하지 않는다. 현재 ZIP은 재현 연습이며 발표·영상은 별도로 준비한다.

최종 제출 전에 운영진에게 영상 규격·실제 마감 시각·제출 경로·파일명·변경 공지를 확인하고 요구 원본에 반영한다. 연락이나 업로드를 자동 수행하지 않는다. 준비 원본의 pending 항목을 모두 확인해야 최종 제출 완료를 판단할 수 있다.

의미 있는 출품 변경은 [제품 릴리스 계약](../docs/contracts/product-release.md)에 따라 새 버전으로 배포한다. 첨부물은 출품 하네스와 완성·검토한 실제 제출 파일만이며 개발 체계·평가·팀 결과는 제외한다. 앞선 접수 절차 문서만의 변경 단계에서는 새 릴리스를 발행하지 않았다. GitHub의 자동 전체 소스 아카이브와 별도 제품 첨부 ZIP을 구분한다.

후속 Skill 지침 개선의 [제품 v0.1.0 검증](../docs/validation/s05-skill-efficiency.md)에서 최종 v5.1 원본 70파일·manifest/SHA와 새 추출·Claude/Gemini 파일 설치/doctor를 확인했다. 첫 제품 prerelease 후보를 준비했으며 실제 발행 상태는 검증 기록을 따른다. 원본 ZIP의 `submission_source_rehearsal_not_final_submission` 표시를 유지한다. 발표/영상·운영진 최종 제출은 포함하지 않는다.
