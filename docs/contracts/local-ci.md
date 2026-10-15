# 로컬 CI 실행 계약

`scripts/local-ci.py`는 현재 호스트에서 실제 명령·종료 코드·입력과 로그 SHA256·receipt를 수집한다. Windows 결과는 Ubuntu 결과가 아니다. 원격 GitHub Actions 실행, native 모델·인증·의미 품질·브라우저/GUI 검수·release 게시를 인증하지 않는다.

## 실행

Python 3.12, uv의 절대 경로를 지정한다. extended에는 Node와 npm-cli.js도 필요하다. Vite 요구는 Node `^20.19.0 || >=22.12.0`이다. 다음은 레포 루트 PowerShell 예시이며 실제 설치 경로와 새 실행 이름을 사용한다.

```powershell
$ciPython = 'C:/path/to/python312/python.exe'
$ciUv = 'C:/path/to/uv.exe'
$ciNode = 'C:/Program Files/nodejs/node.exe'
$ciNpm = 'C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js'
& $ciPython scripts/local-ci.py --profile workflow --python $ciPython --uv $ciUv --install --output .harness/local-ci/windows-workflow-NEW
& $ciPython scripts/local-ci.py --profile extended --python $ciPython --uv $ciUv --node $ciNode --npm-cli $ciNpm --install --output .harness/local-ci/windows-extended-NEW
```

Ubuntu에서는 그 호스트의 Python 3.12·uv·Node·npm-cli.js 절대 경로를 지정하여 별도로 실행한다. npm 경로는 Node 옆 설치 또는 PATH의 실제 JS 진입점으로 찾을 수 없으면 명시해야 한다. OS별 shell·junction·Explorer 검사는 해당 플랫폼에서만 평가한다. Windows 웹 검사에는 cmd, Windows PowerShell, pwsh, Git Bash가 필요하며 System32의 WSL bash를 Git Bash로 대체하지 않는다.

출력 경로는 프로젝트 `.harness/` 아래 **존재하지 않는 디렉터리**여야 한다. 이전 결과를 덮지 않는다. `--install`은 새 출력 디렉터리의 `venv`에 hash 고정 Python 의존성을 설치하고 두 앱의 프로젝트 `node_modules`에 `npm ci`를 수행하는 명시 승인이다. 선택한 기존 Python 또는 전역 Python/npm에 패키지를 설치하지 않는다. npm/uv/pip의 일반 다운로드 캐시는 사용할 수 있다.

`--install`을 생략하면 pip 설치·npm ci·locked portable/package 재현은 `not_run`이며 **전체 판정은 실패**다. 이미 준비된 환경에서 실행 가능한 나머지 검사는 계속 수집한다. 설치를 건너뛴 결과를 전체 CI 통과로 바꾸지 않는다. `LG_REPORT_UV`·`LG_REPORT_PYTHON`은 설치 승인 시 선택한 uv·격리 Python으로 설정하여 어댑터 locked 설치 단위 검사가 조용히 빠지지 않게 한다. 승인 없이 실행하면 해당 변수를 자식에서 제거한다. Python 자동 다운로드는 차단하고 사용자 전역 설정을 수정하지 않는다.

## 검사 범위와 실패

`workflow`는 `.github/workflows/check.yml`의 여섯 run 명령을 고정 계약으로 비교한다. Python hash 설치, validate, dev-harness/product-tools/evaluation unittest, product assets가 필수다. 기존 check 명령의 120초 제한을 유지하며 바깥 receipt 수집에 30초 여유를 둔다. 설치는 최대600초다. 원격 run 명령이 달라지면 계약 불일치로 전체 실패하여 새 원격 필수 검사를 조용히 누락하지 않는다.

`extended`는 workflow 전체에 두 앱의 npm ci/build(각 최대600초), web(내부570/외부600초)·observer/evals 단위 검사, 새 portable/package 출력의 locked 설치 재현(각600초), 빌드 후 asset 검사를 추가한다. build 자체에 TypeScript 검사가 포함된다. eval 단위 검사와 실제 native 평가 실행기는 구분하며 후자는 호출하지 않는다. portable/package doctor의 로컬 CLI 버전 확인은 native inference 인수가 아니다.

각 단계가 실패·timeout·실행 불가·output_limit이어도 후속 단계를 계속 수집하고 전체는 실패한다. 도구/Python/격리 환경 사전 점검이 실패하면 관련 본 검사는 `not_run`과 이유를 남긴다. raw command 상태와 CI acceptance 상태를 구분한다. exit0이어도 0 tests, unittest 요약 누락, 미확인 skip 또는 누락된 skip 이유는 CI 통과가 아니다. 비Windows에서 명시된 Windows Explorer/junction/commandWindows/Windows PowerShell skip만 플랫폼 skip으로 허용한다. uv·Node·Git Bash·pwsh·빌드 결과 등 필수 도구 누락 skip은 실패다. 실제 test 수·skip 사유는 그 실행의 로그에서 수집한다.

실행은 독립 worktree에서 수행한다. 모든 Git 관리/비무시 untracked 입력의 시작·종료 SHA256과 HEAD·dirty 상태를 남긴다. `web/prototypes/` 아래 파일 및 `skills/manifest.json`의 빌드 전후 SHA256·변경 목록도 별도 기록한다. 빌드 결과 등 소스가 달라지면 전체 실패로 남기고 원인을 검토한다. manifest 자동 생성·변경 원복은 수행하지 않는다. 원래 dirty한 소스는 그 상태의 검사이며 순수 HEAD 검사라고 표현하지 않는다.

## 보존물

새 출력의 `report.json`은 호스트 OS·선택 도구 버전·실행 명령·실제 종료 코드·단계별 판정·skip 사유·입력 SHA256·Git 상태·자산 차이를 담는다. 각 단계 JSON과 receipt/stdout/stderr 사본을 함께 보존한다. 원본 receipt는 기존 `dev-harness/checks.py`가 `.harness/checks/<uuid>/`에 생성한다. unittest의 기존 CLI check receipt도 함께 보존한다. 이 로컬 기록은 서명된 보안 증명이 아니다.

명령 전체의 exit0과 report `status:passed`를 모두 확인해야 한다. 실패한 실행 경로를 재사용하지 말고 새 경로로 재실행한다. 실행기 구현 단위 검사는 `python -m unittest discover -s tests/dev-harness -p test_local_ci.py -v`이며 전체 제품·웹 CI 통과를 대신하지 않는다.
