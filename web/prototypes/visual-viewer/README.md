# 저장 결과 시각자료 뷰어 — 참고용 시제품

2026-10-12 최길웅 제출. **웹 PM 황대겸의 기술·구조 결정 전 참고용 시제품**이며 채택·웹 통합·시연 인수 기록이 아니다. 팀이 공유한 Streamlit 고객 리뷰 분석 시연 영상(`KakaoTalk_20261009_191820838.mp4`, Git 제외)의 화면 느낌(남색 단계 사이드바, 어두운 지표 카드, Plotly풍 차트, 하단 단계 자막)을 참고해 새로 작성했다. 영상 앱의 코드는 가져오지 않았다.

## 하는 일과 하지 않는 일

- 기존 `export_session` JSON을 `build_view.py`(Python 표준 라이브러리)가 읽어 `view-data.js`를 만들고, `index.html`이 브라우저에서 그린다. 서버·설치·빌드가 없다.
- 화면은 **저장된 실행 결과의 재생**이다. 모델·업무·Tool을 다시 실행하지 않고, 새로고침·화면 전환·자동 갱신도 파일을 다시 읽을 뿐이다.
- 업무 흐름에 시각화 호출을 넣지 않는다. CLI 업무가 끝나 export가 생긴 뒤 사람이(또는 지시받은 AI가) 따로 실행한다.
- export의 `invocations`가 비어 있으면 Agent·Skill·Tool 사건을 그리지 않는다. 업무 Skill 6개는 구조 정의로만 소개하며 Agent 수로 그리지 않는다.
- 외부 요청은 Google Fonts 글꼴 파일뿐이다(업무 데이터 전송 없음). 막혀 있으면 시스템 글꼴로 표시한다. 링크는 HTTPS 원문만 표시한다.

## 실행

```
python web/prototypes/visual-viewer/build_view.py --export <하네스 runtime-data/exports의 세션 JSON> --focus dashboard --open
```

- 같은 폴더에 `view-data.js`가 생기고 `index.html`이 열린다. 로컬 파일로 연 브라우저는 2초마다 `view-data.js` 변경을 확인하므로, 열어 둔 채 다시 실행하면 화면이 바뀌고 `--focus` 화면으로 이동한다.
- `--standalone 경로`: 데이터를 넣은 단일 HTML. `--insights 파일`: 모델이 쓴 해석(의견 묶음·단계 자막·제외 사유 등). insights 없이도 결과 구조만으로 모든 화면을 그린다.
- 생성물(`view-data.js`, `report-*.html`)과 실제 결과의 insights는 이 폴더의 `.gitignore`로 제외한다. 실제 결과 예시는 Git이 아닌 메일·접근 제한 링크로 공유한다.

## 화면과 표시 원칙

요청·개요 / 근거 대시보드 / 후기 선별 / 기능 대조 / 제안 / 업무 기록 재생 / 근거 원문 / 내보내기의 8개 화면이다. [웹 연결 계약](../../../docs/contracts/team-web-kitchen.md)에 맞춰 다음을 표시한다.

- 모든 화면: `저장된 실행 결과`, 상태(`기획 초안 완료(completed)`·보류·입력 필요·실패·취소), valid, `의미 검토 unverified · 인수 전`.
- product_family는 냉장고·전자레인지·식기세척기로 표시하고 모르는 값은 `미지원(값)`으로 둔다. 자료 버전과 model_scope 원문을 바꾸지 않는다.
- 불편→기존 기능→남은 불편→제안을 원문 ID로 연결한 열로 보여준다. 열 사이 화살표는 업무 순서이며 항목 간 관계는 assessment의 feature_matches·concept_links에 적힌 것만 표시한다.
- concept의 `implementation_steps`·`validation_plan`을 표시하고 없으면 `미작성`, `planned_not_measured`는 `검증 계획 · 실측 전`으로 둔다.
- 근거: source_id·인용·원문 발췌/사실 요약·위치·모델 범위·게시/관측일·구매/협찬(null은 미확인)·SHA·HTTPS 링크.
- 과거 turn과 거절·수정 후보는 `역사적 기록`으로 남긴다. 구조 검사와 `planning_detail_complete`(필드 존재 검사)를 의미 품질 통과로 표시하지 않는다.
- 사용량 기록이 없으면 0이 아니라 `미측정`으로 두고 차트를 그리지 않는다. 누적 값을 다시 더하지 않는다.
- insights의 의견 묶음은 `모델 해석`으로 표시하고 건수는 ID 목록 길이로 센다. 관측 건수를 발생률·시장 수요로 표시하지 않는다.
- 업무 turn이 없는 export(조사 단계 보류)는 요청 기록 화면만 만들고 근거·제안 화면을 만들지 않는다.

## 실제 검사 (2026-10-12, Windows 11, Python 3.14·3.12)

- 로컬 export 5개(Git 제외)로 화면 생성: 기존 설치본 B502S33 세션(5 turn, 무효 4·현재 1), v0.3.0 DUBJ2EA(식기세척기)·MWJ25E(전자레인지, 1·2 turn)·B502S33 보류(근거 0). 모두 exit 0, warnings 0.
- 최신 export 형식 대응은 v0.3.0 export에 `requests[].events·research_usage`를 붙이고 `export-<sha>.json`으로 바꾼 **합성 변형**, 그리고 turns를 비운 **합성 조사 보류 변형**으로만 확인했다(exit 0). 실제 v0.6.0·v7.2 export로는 아직 실행하지 않았다.
- 헤드리스 Edge 1280px 화면 캡처로 8개 화면, 내장 브라우저 375px에서 가로 넘침 없음(scrollWidth 375)을 확인했다. 1920×1080 발표 출력은 따로 확인하지 않았다.
- `build_view.py --insights`의 고정 숫자 검사(`verify_in`)와 단계 문장 원문 대조로 B502S33 예시의 warnings 0을 확인했다.

## 남은 제약

- 브라우저에서 export 파일을 직접 고르는 기능이 없다. `build_view.py` 변환이 필요하다(화면은 view JSON 끌어 놓기만 지원).
- 동일 작성자 후기 중복은 export에 작성자 정보가 없어 자동으로 판별하지 않는다. insights나 검토 메모에 적힌 경우만 보인다.
- 차트 숫자에서 근거 원문 표로 바로 이동하는 기능은 없다. 차트 출처 줄·툴팁의 ID로 근거 원문 화면을 검색한다.
- 실제 native 관찰(observer) 연결, 실시간 Tool 사건, 웹에서 질문 실행은 범위 밖이다.
