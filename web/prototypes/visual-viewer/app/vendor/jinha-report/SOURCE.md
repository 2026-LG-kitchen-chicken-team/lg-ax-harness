# 보고서로 보기 양식 (신진하)

K 업무형의 `보고서로 보기`가 쓰는 보고서 화면이다. 팀원 신진하가 만든 하네스 결과 보고서 양식을 그대로 가져왔다.

- 받은 곳: https://kitchen-agent-evidence-report.tlswlsgk7174.chatgpt.site (2026-10-15, 사용자 요청으로 내려받음)
- 이 폴더의 다섯 파일은 받은 그대로다(바이트 동일). 고치지 않는다. 새 판이 나오면 다섯 파일을 통째로 바꾸고 아래 지문을 고친다.

| 파일 | SHA-256 |
|---|---|
| `index.html` | `cf04602eedbd575f809a2d579f124377c656020121024b1138f2a261d686b341` |
| `report-data-adapter.js` | `c1a1c695df64c1499453bafb3de1a4c203a8e76144fbfe03c11815cd31c1e8ab` |
| `report-app.js` | `7a80fcde06205ac9346ffb54fa79f919f33925778791e40e01dafc4f2469857d` |
| `styles.css` | `82703086419e566b1696e75d917e5f93b55d61cfd1f6b5f733defbf02df8d8c3` |
| `result-report.css` | `2ebfb7affc482ffd46ced0e1769b829b25111faae97f1a58ad60fe9ed6198596` |

## 빌드에서 바꾸는 것 (`vite.config.ts`의 `jinhaReport`)

`npm run build`가 다섯 파일을 한 HTML 문자열로 합쳐 뷰어 `index.html` 안에 넣는다. 원본 파일은 바꾸지 않고 합칠 때만 다음을 한다.

- 스타일 두 개와 스크립트 두 개를 파일 링크 대신 문서 안에 넣는다(뷰어는 한 파일이다).
- 호스팅이 덧붙인 Cloudflare 스크립트와 `canonical` 링크(외부 주소)를 뺀다.
- 뷰어 안에서는 쓰지 않는 버튼을 숨기는 스타일을 덧붙인다: `결과 불러오기`(다른 파일을 열면 K 화면과 다른 결과가 된다), `페이지 링크 복사`(원 사이트 주소를 복사한다), `예시 다시 보기`, `하네스 결과 연결 방법`(없는 연동 도구 ZIP 링크).

K는 `build_view.py`가 `view-data.js`에 넣은 export와 지금 보이는 turn_id를 `<script id="embedded-report">`에 넣어 격리된 iframe(sandbox, 같은 출처 권한 없음)으로 연다. 키워드 집계·근거 구성 같은 숫자는 이 양식이 브라우저에서 export로 직접 센다(뷰어의 다른 화면은 `build_view.py`가 센다).
