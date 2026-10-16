---
name: review-change
description: "구현 diff와 실제 검사 결과를 독립적으로 검토하고 실질 결함을 보고할 때 사용한다."
---

# review-change

읽기 전용으로 요구·기술 결정·diff·실제 검사 receipt를 확인한다. 재현 입력·파일·영향으로 실행/출처/종료/권한/캐시/예산의 실질 결함을 보고한다. 구현과 완료 주장의 차이도 확인한다. 스타일보다 동작과 근거를 우선한다. 부모가 수정하면 관련 실패 경로만 재검토한다. 발견하지 못한 결함을 없다고 보장하지 않는다.

검토 시작 시 명시된 baseline commit과 현재 HEAD, staged·unstaged tracked 변경과 Git 비무시 untracked 파일을 분모로 고정한다. `git diff --cached --name-status -z --find-renames BASE --`, `git diff --name-status -z --find-renames --`, `git ls-files --others --exclude-standard -z`의 합집합을 쓰며 경로는 NUL로 구분한다. 삭제와 rename의 이전·현재 경로, 변경 계층·관련 blob·현재 파일 지문을 보존한다. ignored untracked는 Git 제외 정책에 따른 수집 범위 밖임을 명시한다.

경로별 reviewed/excluded/pending을 구분하고 excluded에는 사유와 확인 범위를 적는다. binary·생성물·다른 담당 소유라는 이유로 분모에서 조용히 지우지 않는다. 읽기 실패·미관측·다른 담당자의 검토 대기는 pending이며 전체 검토 완료로 표시하지 않는다. 검토 중 분모·관련 지문이 바뀌면 해당 부분을 다시 확인한다. 전체 경로 수와 reviewed/excluded/pending, 실제 검사 성공·실패·timeout·not_run을 구분해 보고한다. 삭제 경로를 파일 검사 입력에 억지로 넣지 말고 분모 manifest를 별도 artifact로 지문화한다. manifest의 지문은 실제 독해·의미 검토를 인증하지 않는다.
