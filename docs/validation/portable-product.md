# Claude·Gemini 설치 사본의 실제 로컬 검사

2026-10-10. [설치 계약](../contracts/portable-product.md). 두 runtime 사본을 각각 새 Temp 폴더에 만들고 사본별54개 파일의 지문을 확인했다. 두 사본은 업무 Skill6개만 제공하며 개발 역할·평가 corpus·원문 로그·전역 설정을 설치하지 않는다.

`evals/runner/check_portable.py`를 실제 실행했다. Claude/Gemini 모두 새 폴더 설치·manifest 지문·`uv sync --locked`·auth-free product-doctor의 공통 Tool 검사 exit0이다. PATH에서 해당 native CLI를 발견하지 못했고 readiness=local_only, authentication/model=unobserved, native_discovery=unverified로 기록했다. 로그인/신뢰/Skill 동의/실제 모델 호출·후속 대화·품질·사용량은 미실행이다.

일반 회귀에는 각 profile의 고유 Skill 위치·지침 import·문서 링크·공통 wrapper 실제 doctor, 기존 상태 덮어쓰기 거부·파일/profile 변조 감지를 포함했다. 이것은 native 지원 통과가 아니다.

원본은 Git 제외 `.harness/portable-validation.json`, 실제 검사 receipt와 stdout/stderr다. Temp 폴더는 해당 JSON에 남으며 자동 삭제하지 않았다. Codex 기존 설치 폴더/DB와 사용자 전역 환경을 변경하지 않았다. 새 환경에서도 같은 준비 검사를 실행한 뒤 별도 native 인수 결과를 추가해야 S02b/c 및 S03b2를 완료할 수 있다. 개발 D06b도 아직 별도 미완료다.
