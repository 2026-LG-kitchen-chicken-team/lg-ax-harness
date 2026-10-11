# 발표 초안 — 2026-10-11

2026-10-12: 아래12쪽은 과거 버전의 검토 초안이다. 최종 발표 전 [최신 품질 회귀](../../docs/validation/quality-regression-20261012.md)와 [토큰 가산점 근거](../../docs/validation/token-bonus-20261012.md)의 실제 수치·지원 범위로 갱신해야 한다. 사람 비교는 제외됐으며 과거 절감률이나 예정 측정을 최신 실적으로 발표하지 않는다. 이번 품질 작업은 PPTX/HTML/영상의 갱신·완료를 뜻하지 않는다.

`kitchen-planning.pptx`와 `presentation.html`은 같은 `slides.json`의12쪽 검토 초안이다.525초는 계획이며 실제 영상/리허설/접수는 미완료다. HTML을 브라우저에서 열어 방향키/버튼으로 이동하고 근거/발표 시간 항목을 확인한다. 추가 네트워크·모델 요청은 없다.

PPTX는 bundled `@oai/artifact-tool`2.8.89로 작성했다.20쪽 제한·12쪽package·table2개·chart1개/내장 수치 workbook·Malgun Gothic 글꼴·import/전체12쪽 PNG render를 확인했다. 결과 화면을 합성하지 않았으며 실제 실행 영상은 별도 촬영해야 한다. 실제 Microsoft PowerPoint 재생·영상 삽입·10분 리허설은 미실행이다.

`build-deck.mjs`의 환경변수는 `LG_PRESENTATION_SKILL`(Presentations skill 경로), `LG_RUNTIME_NODE_MODULES`(bundled packages), `LG_RUNTIME_PYTHON`(bundled Python)이다. bundled Node로 실행한다. 현재 최종 파일은 덮어쓰지 않는다. 수정 시 새 최종 파일명으로 내보내 구조/글꼴/import/12쪽 시각 검사를 다시 받는다. helper/원본은 개발·제출 자료 제작용이며 출품 runtime ZIP에 넣지 않는다.

데이터/평가/토큰 원본은 각 slide speaker notes와 HTML 근거 항목에 있다. 새3제품군 비맹검 진단과 과거 v5.4 R01각2회 비교를 섞지 않는다. 기대효과는 `planned_not_measured`이며 총 토큰/비용/사람 공수 우위는 미입증이다.
