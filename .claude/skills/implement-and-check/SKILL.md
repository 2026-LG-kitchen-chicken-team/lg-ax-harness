---
name: implement-and-check
description: "배정된 파일을 구현하고 실제 검사 명령·종료 코드·로그·남은 문제를 반환할 때 사용한다."
---

# implement-and-check

소유 파일·의존성·acceptance를 확인하고 한 작성자 원칙을 따른다. 최소 구현 후 `python dev-harness/cli.py check --run RUN --task TASK --input <관련파일> -- <명령과 인수>`를 실제 실행한다. 실패/timeout/output_limit/not_run을 성공으로 바꾸지 않는다. 관련 입력·코드가 바뀌면 해당 receipt는 다시 실행한다. 결과에 변경 파일·receipt 경로·실제 exit code·남은 항목을 넣고 부모가 통합한다. 검사 명령을 썼다는 사실만으로 검사를 통과했다고 하지 않는다.
