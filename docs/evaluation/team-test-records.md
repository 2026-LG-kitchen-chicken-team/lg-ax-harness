# 팀원 실행 결과의 접수·이력·검토

2026-10-10. 사용자는 팀원들이 실제 테스트를 진행했다고 알렸다. 개별 입력·출력·환경·로그 근거는 아직 이 레포의 접수 기록으로 전달되지 않았다. 이번 작업은 제출 양식·보관 위치·검토 계약을 마련하며 실제 결과나 native 지원 완료를 만들어 기록하지 않는다.

## 제출과 보관

팀원은 [실행 결과 Issue 작성](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/issues/new?template=harness-test-result.md)으로 제출한다. 한 환경의 한 대화/연속 입력을 한 Issue에 기록하고, 환경이나 모델이 바뀌면 분리한다. 읽기 역할도 Issue 작성·댓글을 사용할 수 있으므로 코드 쓰기 권한을 추가할 필요가 없다. 초대 수락과 실제 접근은 팀원 계정에서 확인한다. 조직 제한으로 제출이 막히면 기존 메일로 같은 양식을 보내고, 관리자가 접수 출처와 작성자를 명시해 기록한다.

관리자는 실제 결과와 민감 정보 제거를 확인한 후 [저장 위치](../validation/team-runs/README.md)에 정리한 보고서를 커밋한다. 이것은 원문 로그 업로드나 자동 수집 기능이 아니다. 원문 CLI trace·SQLite·인증·개인 설정은 실행자의 로컬에 보존하고 Git에 넣지 않는다. 필요한 실제 질문·답변 발췌, 오류/명령 관측, 출처 위치, 원본 파일 지문만 검토 보고서에 남긴다. 숨은 추론 전체를 수집할 필요는 없다.

| 위치 | 내용 | 작성자 |
|---|---|---|
| GitHub Issue | 실행자의 환경·실제 질문/출력 발췌·관측·오류·회신 | 읽기 권한 팀원 |
| `docs/validation/team-runs/records/<run-id>.md` | 접수 출처를 연결한 검토 보고서; 미검토 상태도 명시 | 관리자/현재 checkout 작성자 |
| `docs/validation/team-runs/index.md` | 환경·질문별 최신 접수/검토와 이전 시도 링크 | 관리자 |
| 실행자의 로컬 비공개 폴더 | 원본 trace·DB·원문 결과; 필요한 범위에서 원문 대조 | 실행자 |

파일명은 `YYYYMMDD-engine-login-attemptNN`처럼 구별한다. native UUID와 업무 session/turn ID가 있으면 따로 기록하며, 보고서 파일명을 실제 Agent ID로 설명하지 않는다. 민감 경로를 가려도 원문 지문·자료 버전·삭제 사실은 유지한다. 원본 지문은 해당 자료와의 연결 근거이며 서명/위변조 방지 증명이 아니다.

## 세 가지 상태를 분리

| 판정 | 기록 예 | 의미 |
|---|---|---|
| 실행 관측 | success/error/timeout/interrupted/not_run/unknown | CLI 응답·중단·종료 관측; 업무 정답 여부와 별개 |
| 업무 결과 | completed/held/needs_input/failed/cancelled/no_final/unknown | 답변 또는 실제 DB의 업무 상태; 두 값이 다르면 불일치로 기록 |
| 내용·계약 검토 | unreviewed/satisfied/defect/inconclusive | 질문 제약·출처 의미·저장 계약을 독립 대조한 결과 |

CLI exit 0, doctor 통과, 모델의 `accepted/supported` 표시를 내용 검토 통과로 바꾸지 않는다. 반대로 근거가 부족해 올바르게 보류한 답변은 기대 행동을 충족할 수 있다. 단순히 completed가 많다고 좋은 하네스로 평가하지 않는다. 이전 시간초과·일반 출력 계약 실패·수집 오류도 삭제하지 않는다.

## 필수 기록

1. 재현 식별: source commit, 설치 manifest 지문, 업무 자료/모델/문서 버전, 실행 날짜·시간대, 실행자, 이전 실행·시도 번호.
2. 환경: OS/Python, CLI/모델/추론 설정, 권한·신뢰/동의, 개인 Skill 충돌. 모르면 미확인으로 적는다. 다른 설정의 차이를 실행기 자체의 차이로 단정하지 않는다.
3. 질문·출력: 실제 문장, 동일 대화의 turn/변경 조건, 실제 답변 발췌·출처·보류 사유, 최종 응답 부재, 저장/export와 최종 답변 일치.
4. 실행 순서: 관측한 Agent/Skill/Tool·실제 ID·시각·명령·exit code·오류. Skill 파일 읽기와 Tool 실행을 구분하고 관측하지 못한 메시지를 만들어 채우지 않는다.
5. 오류·수정: 첫 실패, 재현 조건, 기술 재시도와 업무 수정 횟수, 재접속·조건 변경·취소, 이전 결과·비용 보존. UI/CLI 중단·로컬 취소·backend 중단은 별개다.
6. 검토·사용량: 주장과 원문 대조 메모, 검토자/날짜/판정, 결함→수정 commit→새 재시험 링크, 필드별 usage와 관측 범위·미측정 항목.

## 결과가 보이는 방식

GitHub Issue와 Markdown 보고서에서 실제 질문/답변 발췌, 실행 순서 표, 오류·검토·수정 연결을 읽고, index에서 같은 질문의 환경별 실행을 비교한다. [보고서 양식](../validation/team-runs/report-template.md)을 사용한다. 표의 빈 칸은 미수신/미관측으로 남긴다. 이번 작업은 GUI나 자동 환경별 통계를 추가하지 않았다.

재시도나 수정으로 결과가 좋아지더라도 실패한 최초 실행은 남긴다. 원본 보고서를 수정해 성공으로 덮지 않고 새 시도 보고서를 만들며, 단순 오기/추가 근거는 Issue 댓글·변경 이유·Git diff로 추적한다. 한 질문을 반복한 횟수와 독립 질문 수를 구분한다. 한 사용자 여러 turn도 독립 사용자 여러 명으로 세지 않는다.

사용량은 실제 카운터 정의를 확인한다. 캐시가 입력의 부분, reasoning이 출력의 부분인 경우 다시 더하지 않는다. 다른 실행기의 정의를 확인하지 못하면 필드별 관측값과 미확인을 그대로 남긴다. 세션 누적값은 동일 native ID의 전후 차이로만 turn 사용량을 계산한다. 누락·카운터 감소·다른 ID라면 미측정으로 남긴다. 실패·하위 호출 포함 여부가 미확인이면 전체 비용이라고 표현하지 않는다. 실행 시간·검토 시간·실제 사람 활동 시간을 분리한다.

환경 인수는 정상·후속·근거 부족·모델 혼동·도구 오류·저장/복구를 해당 환경에서 실제 확인해야 한다. 팀원 한 명의 정상 답변 한 건만으로 Claude/Gemini 전체 지원 완료를 표시하지 않는다. 수집한 결과는 [질문 범위와 미사용 평가](coverage-and-holdout.md)에 반영하며, 평가 질문·rubric·이 보고서를 업무용 설치물/프롬프트에 넣지 않는다.

근거: [GitHub 조직 저장소 역할](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization), [Issue template](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository). 현재 저장소의 Issues 활성화는 확인했지만 새 양식의 팀원 계정 제출은 아직 확인하지 않았다.
