---
name: implement-and-check
description: "배정된 파일을 구현하고 실제 검사 명령·종료 코드·로그·남은 문제를 반환할 때 사용한다."
---

# implement-and-check

소유 파일·의존성·acceptance를 확인하고 한 작성자 원칙을 따른다. 최소 구현 후 `python dev-harness/cli.py check --run RUN --task TASK --input <관련파일> -- <명령과 인수>`를 실제 실행한다. 실패/timeout/output_limit/not_run을 성공으로 바꾸지 않는다. 관련 입력·코드가 바뀌면 해당 receipt는 다시 실행한다. 결과에 변경 파일·receipt 경로·실제 exit code·남은 항목을 넣고 부모가 통합한다. 검사 명령을 썼다는 사실만으로 검사를 통과했다고 하지 않는다.

예상 밖 실패나 같은 호출 반복이 발생하면 추측 수정·재실행을 멈추고 원래 목표, 마지막 성공/실패 명령과 실제 exit/status/receipt, cwd·branch·관련 입력 지문, 이미 쓴 시도와 남은 상한을 보존한다. 논리·상태·환경·권한/정책 중 원인 가설을 적고 이를 구분하는 최소 검사 하나를 먼저 수행한다. 확인된 원인에만 최소 수정 후 관련 경로를 재검사하며 최초 실패를 새 성공으로 덮지 않는다. 원래 run/task와 시간·호출 상한을 유지하고, 정책 거절·사용자 취소를 설치·권한 변경·새 실행으로 우회하지 않는다.
