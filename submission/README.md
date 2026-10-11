# 제출 준비 원본

2026-10-11: 냉장고·전자레인지·식기세척기 기획의 **실제 발표 초안12쪽**을 [PPTX](presentation/kitchen-planning.pptx)와 [독립 HTML](presentation/presentation.html)로 작성했다. [내용 원본](presentation/slides.json), [발표 구성](demo-plan.json), [실제 시연 절차](demo-runbook.md), [평가항목 대조](../docs/validation/kitchen-progress-20261011.md)를 함께 관리한다. 현재 `preparation_only`: 영상·리허설·최종 접수는 미완료다.

계획525초는 실측 발표 시간이 아니다. PPTX의12쪽을 다시 import/render해 글자·표·차트를 확인했으며 표2개와 차트1개는 편집 가능하다. 실제 입력/Skill/Tool 화면 캡처를 꾸며 넣지 않았다. `uv run python scripts/check-submission-preparation.py`는 계획·경로·C01~C09 연결 검사이며 심사 점수나 촬영 완료를 인증하지 않는다.

최종 업무 소스는 README의 package 명령으로 새 ZIP을 만든다. ZIP의 manifest/SHA·LICENSE/NOTICE·Skill 전체 폴더·잠금 파일을 새 환경에서 확인한다. 원문 실행 로그·SQLite·인증·개인정보·의존성 환경·개발 역할·평가 입력/runner·첨부 PDF는 제외한다. 소스 시험판은 발표/영상·운영진 최종 제출과 별도다. [제품 릴리스 계약](../docs/contracts/product-release.md)을 따른다.

최신 제품군·Codex 실증과 Claude 파일 설치 검사를 구분한다. Gemini는 신규 지원에서 철회했으며 과거 실패/설치 기록은 보존한다. 웹팀은 개발 중이나 원본은 아직 인수하지 않았다. Claude 환경 검증은 하네스 보완 후 최길웅에게 요청하고 결과를 정이량에게 메일로 받는다.

운영진 최신 영상 규격·실제 마감·경로·파일명·변경 공지 확인, 실제 시연 영상/10분 리허설, 새 실행자 최종 재현과 업로드/접수 확인이 남는다.20쪽/10분/질의응답5분과 실제 파일 마감을 혼동하지 않는다. 사람 공수·전체 청구·시장/실물 효과는 미측정이며 기대효과와 확인 방법으로만 설명한다.

PPTX 재생성은 `build-deck.mjs`의 세 bundled runtime 환경변수로 수행하며 기존 최종 파일을 덮어쓰지 않는다. 편집이 필요하면 새 최종 파일명을 지정해 검사를 다시 받는다. 이는 제출 자료 제작 helper로서 출품 runtime/ZIP에 들어가지 않는다. 아래의 과거 제품 배포는 각 버전의 역사적 기록이다: v0.1.0→v0.2.3. 최신 세 제품군 릴리스와 검증은 저장소 상단의 기록을 따른다.
