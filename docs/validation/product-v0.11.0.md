# 제품 v0.11.0 시험판 게시와 원격 검증

2026-10-14 게시한 [제품 전용 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.11.0)이다. [원격 검증 JSON](product-v0.11.0.json)·[현재 품질 판정](J-final-assessment-20261014.md)을 함께 따른다. 최종 제출이나 모든 답변 품질 통과 버전이 아니다.

## 변경과 제품 범위

같은 공식 문서의 정확 URL/query/anchor·모델 identity·버전·관측 원문을 결속하는 발췌 경로와 설명서 분기를 보완했다. CLI 오류의 불변 receipt를 가능한 범위에서 기록하며 원래 오류와 exit를 유지한다. 메인과 Skill에는 원문 조건·현재/과거/기대·긍정 의견·기능 존재와 실제 해소·최종 답변 귀속·전체 시도 검증 계획을 명시했다. 형식 검사가 의미 검토를 대신하지 않는다.

기본 전달은 현재 웹 JSON과 전체 선택 원문·출처다. `report:false`이며 PDF/DOCX 자동 생성은 기본에서 제외한다. HTML 작업 화면과 별도 보고서 HTML은 웹팀 소유다. 자체 모델 API 실행기나 시각화용 모델 호출은 추가하지 않았다.

- 개발 provenance: `6fbe0fe432ef7372ee058ac119cd94a2866abd10`, `codex/evidence-complete`에 푸시했다.
- 제품 전용 snapshot: `5774e5ec71c2e47367e52701eef96240b69d1f38`, 부모0·106파일.
- J2 core manifest: `d88262b0381b42b6a6925adee72af7b0d4c098effab56a3be5f02e4e699f811e`, source53·설치84.
- 기존 main/웹팀 코드/태그는 변경하지 않았다. 평가 원문/질문·개발체계·원본 로그/DB·인증·사용자 PDF는 제품에 없다. 기본 catalog는 비어 있다.

## 첨부와 실제 설치 검사

첨부는 `lg-ax-harness-product-v0.11.0.zip`과 `SHA256SUMS.txt`다. 새 다운로드 폴더에서 ZIP 405,357바이트·106파일과 checksum 원본을 대조했다.

ZIP SHA-256: `9e90e0762356ba787c80dcb0750881f7aabc84ed348260ead5a7bc5e808e8733`.

원격 태그의 peeled commit·prerelease/비초안 상태·첨부2개·최종 릴리즈 설명 원본 바이트를 확인했다. GitHub 자동 Source code ZIP도 106파일 모두 첨부 제품 ZIP과 원본 바이트가 같다. 최초 설명 대조는 검사자의 `read_text` 줄바꿈 변환 때문에 실패했고, 실제 원격 UTF-8 바이트와 로컬 파일 바이트가 동일함을 확인했다. 릴리즈 수정이나 재업로드는 하지 않았다.

동일한 ZIP 내용으로 새 폴더의 locked 환경 설치·doctor·Claude 설치가 exit0이었다. 명시적으로 `core.autocrlf=false`를 적용한 로컬 체크아웃106파일도 ZIP과 같고 locked 설치/doctor exit0이다. 원격에서 받은 ZIP은 이 실제 설치본과 같지만, ZIP의 실제 AI 업무를 새로 실행한 것은 아니다. 새 원격 Git clone도 미실행이다.

**권장 설치는 첨부 ZIP이다.** 제품 snapshot은 `.gitattributes`가 없으며 기본 Windows `core.autocrlf=true` 변환은 원본 manifest와 불일치할 수 있다. 기본 줄바꿈 변환 체크아웃의 설치 통과를 주장하지 않는다. LICENSE/NOTICE·잠금 파일은 포함하며 NOTICE의 일부 개발 vendor 경로는 최소 제품 패키지에 없다.

## 실제 코드와 AI 검증

제품393·평가144·자산 실제 exit0, 입력/로그SHA freshness와 독립 코드 검토를 확인했다. 상위 모델 포함 최초13설정과 후속·예외·역할·자료조사까지 J의 실제26입력이 종료됐고 독립 의미 검토는23건이다. 정상 품질·보류·취소·실행 환경 거절을 단일 성공률로 합산하지 않는다. 이전45와 별도로 누적71·자동재발송0이며 잔여6은 미사용이다.

세 제품군 공통 권장 모델/추론 gate는 미충족이다. Astra low 첫 FR/MW/DW는14/14였지만 MW반복은 마지막 답변의 미명시 매체 귀속 때문에13/14다. FR2회는14/14이고 DW반복은 미완료다. Claude Opus5.5 중간/높음·Fable5.1 중간·Sonnet5.5 중간/높음을 실제 비교했으며 핵심 오류 또는 종료 누락 때문에 반복 후보를 선정하지 않았다. 빠른 실패를 권장하지 않는다.

보존115자료 분석은 전체 전달·현재 저장/web/finish/export·독립14/14였다. 새 live39자료도 원문·현재 버전 연결이 일치하나 검증계획의 전체 배정 분모·실패/중단/미확인 처리가 빠져13/14다. 생성된 조사 제한 기록의 실패4건에는 무관한 HTTP 보조 링크 귀속 P2도 남는다. 실제 실패 원문은 정확하며 기존 불변 결과를 수정해 통과로 바꾸지 않았다.

추가 선택 검토자는 실제 spawn/interrupt를 확인했지만 결과 반환0이다. 품질·시간·토큰 이점은 미입증이며 자식과 전체 backend 청구는 unknown이다. 시장 대표성·물리 효과·HTML 시각 인수·실제 녹화/편집·발표 삽입 재생·리허설·최종 접수도 별도다. 내부14점은 공식 점수나 완성도%가 아니다.

core commit의 원격 CI [push](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38422573819)·[PR](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38422581907) Windows/Ubuntu4 jobs는 결제·사용 한도 때문에 시작되지 않았다. 코드 실패나 원격 통과로 표시하지 않았고 결제·보호 설정을 변경하지 않았다.

업데이트는 새 폴더에서 수행하며 이전 DB/실패 이력을 덮어쓰지 않는다. [녹화 영상 600초 구성](../plans/recorded-demo-600-20261013.md)은 실제 제작·삽입·재생 검수를 기다리는 계획이다.
