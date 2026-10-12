# 제품 v0.8.2 시험판

사용자가 요청한 자료 폭 유지·시간 개선·선택적 출품 위임을 반영한 시험판이다. 기존0.8.1/0.9.x 태그와 첨부물을 덮어쓰지 않는다. 프론트·HTML은 팀 소유로 변경하지 않았다.

## 첨부물과 실제 확인

- `lg-ax-harness-product-v0.8.2.zip`:94파일, SHA256 `3cec96e56e0bf02db06f8f811ecee2020329300279134c31eccc6fd5853da1b6`.
- `SHA256SUMS.txt`: 위 ZIP의 실제 지문.
- 제품 manifest: `c33959da127e36409c75d32680199cbcbf230cf80f92446bcc9421d9b96d363f`.
- 새 추출의93manifest 항목·파일 SHA 일치, uv 잠금 설치·doctor exit0, ZIP에서 별도 Claude76파일 재설치/check exit0.
- 제품338검사·평가143검사 모두통과/skip0, asset·독립 코드검토. 실제 정상/후속/예외 범위는 [검증 MD](evidence-throughput-20261012.md)와 [동반 JSON](evidence-throughput-20261012.json)을 따른다.

제품만의 별도 부모 없는 Git snapshot에 같은94파일 바이트를 담아 태그를 연결한다. provenance branch commit과 snapshot SHA, 원격 태그/첨부 다운로드 확인은 발행 후 기록한다. main을 자동 병합하거나 팀원 PR을 수정하지 않는다.

## 동작과 지원 범위

일괄 등록·전체 원문 전달/검토 장부·600초 workflow·불변 reviewer packet·취소/종료 후 등록 거절을 제공한다. 메인1/업무Skill6/선택적 근거 검토자1이며 자체 LLM API를 추가하지 않는다. 기본catalog는empty이고 실제92후기+20사실 평가 자료는 ZIP에 넣지 않는다. 새 업무에서 실제 근거를 조사·등록하거나 충분한 해당 자료를 재사용해야 한다.

본 시험의48자료는 Codex6.1-sol/medium507.375초, paid Claude Desktop Code Sonnet5.5/medium359.776초에 저장·문서·최종 전달했다. 마지막 답변 지침 수정 뒤의 동일 세션 설명 후속은 Codex70.110초/Claude19.488초이며, 최신 전체 정상 업무 재인수로 확대하지 않는다. Claude child45.005초의 독립 검토는partial이고 최초 답변/문서의 시간·알림음 해소 표현 제한을 보존한다. 물리 문서 화면 검수·대표성 있는 새 조사5~10분·큰 미사용 반복 평가·backend청구·웹팀 연결·영상/발표/최종접수는 별도 미완료다. Gemini·사람비교는 제외한다.

## 설치

새 폴더에 ZIP을 풀어 `uv sync --locked`와 `uv run python product-doctor.py`를 실행하고 Codex에서 해당 폴더를 연다. 검증한 운영 기준 설정은gpt-6.1-sol/medium이며 보편적 최적성을 입증한 것은 아니다. 정확한 계정의 실제 모델 제공 목록에서 선택한다.

Claude Desktop Code는 ZIP의 `adapters/claude/install.py --target 새폴더`로 별도 사본을 준비하고 그 폴더를 Code 로컬 세션에 연결한다. standalone CLI 설치·로그인은 GUI 경로의 필수 조건이 아니다. 별도 CLI를 선택한 경우에만 해당 인증을 한다. 기존 세션·DB·출력 폴더를 자동 덮어쓰지 않는다.
