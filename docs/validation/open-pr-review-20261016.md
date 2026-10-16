# 열린 PR 5건과 심사위원 ZIP 검토

검토일: 2026-10-16 (KST). 고정 main: `c98896422a05fae713a046e3b45e6efb36f29b20`.
검토 종료 직전 원격의 열린 PR 번호와 head가 시작 시점과 동일함을 다시 확인했다.
3개 읽기 전용 검토 역할과 부모의 로컬 재현을 병행했다. 제품 코드·기존 작업파일·계정·권한은 수정하지 않았다. PR 댓글·병합·닫기·릴리즈 업로드는 하지 않았다.

## 먼저 수정할 결함

1. **[P2, PR13] 제품 소스 ZIP에서 심사위원 ZIP 재생성 실패.** `package_judge.py:69–71`은 새 시작 스크립트 8개를 읽지만 `package.py`의 `ADAPTER_FILES`는 이 파일들을 포함하지 않는다. PR13에서 직접 생성한 심사위원 ZIP은 203파일로 정상이나, 별도 제품 소스 ZIP119파일을 추출해 재생성하면 `start_claude_gui.cmd` 누락으로 `FileNotFoundError`. 시작 스크립트를 소스 allowlist에도 포함하고 소스 추출→심사 ZIP 재생성 검사를 추가해야 한다.
2. **[P2, PR13] macOS/Linux 종료 시 실제 관찰 프로세스가 남는 구조.** `start_codex_cli.sh:21–23`와 GUI 스크립트는 `judge.py observe` PID만 종료한다. `judge.py:40–41`은 실제 `office.py`를 별도 자식으로 실행하므로 wrapper만 종료하면 follower가 계속 남아 동일 폴더의 lock을 점유한다. POSIX에서 exec로 PID를 넘기거나 자기 자식의 종료·회수를 보장해야 한다. 부모는 실제 PR13의 run 함수를 사용한 Windows 제한 재현에서 wrapper 종료 뒤 자식이 살아 있음을 확인했으며, 재현 자식은 5초 후 스스로 종료했다. 실제 POSIX 런처·브라우저는 실행하지 않았다.
3. **[P2, 기존 main 문서] 제거된 화면 모드 안내.** `web/prototypes/visual-viewer/README.md:131`은 app/slides 등13종을 안내하지만 실행 코드는 ops만 지원한다. 실제 `--standalone ... --mode app` 실행은 exit2/invalid choice였고 출력 파일은 생성되지 않았다. 현재 K·ops 안내로 맞춰야 한다. 이것은 PR14가 새로 만든 결함이 아니다.

추가 호환성 검토: PR13의 Windows ZIP은 `.sh` 항목에 0755를 넣으면서 `ZipInfo.create_system=0`을 유지한다. Unix 출처 값3까지 고정하는 편이 맞지만, 실제 macOS/Linux 압축 해제는 하지 않았으므로 확인된 설치 실패로 확대하지 않는다.

## PR별 판단

| PR | 고정 head | 검토 결과와 처리 제안 |
|---|---|---|
| [#14 Windows MXC·venv](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/14) | `c743029` | 재현 가능한 P1/P2 발견 없음. WinError5만 fallback, 존재·symlink/junction·containment 확인 유지. Windows 업무 Tool을 venv Python으로 실행하도록 지침·doctor를 맞췄다. 관련15검사 통과. 반영 후보이며 실제 새 전체 업무는 이번에 실행하지 않았다. |
| [#13 원클릭·ZIP README](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/13) | `f813b55` | README뿐 아니라 런처8개, setup 캐시, native 실행기 준비, 첫 질문 대시보드 열기, 대기 화면 안내를 변경했다. 위 두 P2 보완 후 통합 권장. |
| [#11 3D 관찰 화면](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/11) | `7c8e61b` | 34변경파일 중22개가 main과 원시바이트 동일. 나머지12개는 main의 후속 귀속·취소·개인정보 보완 등이 반영됐다. 의미 있는 미흡수 새 기능은 발견하지 못했다. 반영됨으로 정리·닫기 제안. |
| [#10 결과·보고서 화면](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/10) | `93783b7` | 47변경파일 중39개가 main과 원시바이트 동일. K·보고서·차트2개는 반영됐고 나머지는 후속 검토·출처·갱신 보완이다. 반영됨으로 정리·닫기 제안. |
| [#7 별도 로컬 웹 서버, draft](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/pull/7) | `5388f7a` | 서버 등9파일은 미흡수. 현재 viewer README에 기록된 미채택 결정과 일치한다. 현재 심사 ZIP의 실행 경로에 다시 넣지 않고 미채택 이력으로 닫기 제안. |

#10/#11은 #9 squash 이후 기능이 통합됐으므로 Git 조상 관계와 기능 반영을 구분한다. 현재 두 PR은 충돌 상태이며, 충돌을 옛 브랜치 내용으로 선택하면 다음 보완이 되돌아갈 수 있다.

- #10: 전체 source/result binding과 stored review, 최신 무효/취소 turn 유지, 보고서 단일 검토 turn 제한, 원문 인라인 펼침·인쇄, 늦은 web payload 갱신.
- #11: 시간대 겹침 대신 실제 업무 식별자 일치, 취소를 interrupted로 표시, 질문 원문을 관찰 파일에 복제하지 않기.

#13과 #14의 `git merge-tree` 결과는 `skills/manifest.json` 한 파일 충돌이다. 실제 병합하지 않았으며 통합 후 최종 원본으로 manifest를 재생성해야 한다.

## 현재 공개 ZIP과 새 변경의 차이

원격 v0.15.0 심사위원 ZIP을 다시 다운로드해 SHA `ccf2386fb70f6f73692eb3b9f1cffd2ac7bba9e50c9276b9729513b30b16deb8`와195파일을 확인했다. README는 현재 main과 같고 PR13과 다르다. start_* 파일은0개이며 PR14 `product_tools/paths.py`도 없다. 따라서 길웅의 새 변경은 PR에 있으며 공개 ZIP에는 아직 반영되지 않았다.

PR13에서 로컬로 시험 생성한 ZIP은203파일이며 README가 PR13의 `docs/contracts/judge-test.md`와 정확히 같다. 이 검토용 파일은 릴리즈로 게시하지 않았다.

## 실제 검사와 한계

- Python3.12.14: judge package5, 관찰42, 경로4, readiness11 = **62/62 통과**.
- 관찰 TypeScript 빌드 검사1개는 immutable Git snapshot에 node_modules가 없어 제외했다. 전체 CI나 전체 업무 통과 수치로 표시하지 않는다.
- 직접 ZIP 생성, 소스 ZIP 추출 후 재생성 실패, wrapper/자식 수명, 제거 모드 exit2를 별도로 확인했다.
- PR13/14 GitHub Actions는 실제 job steps가 빈 배열이며 billing/spending-limit 사유로 시작되지 않았다. 코드 검사 실패와 구분한다.
- 실제 새 Codex/Claude 상품기획, GUI/브라우저 표시, 실제 macOS/Linux 런처·압축 해제 검수는 이번 범위에서 수행하지 않았다. PR 작성자의 실행 보고를 부모가 새로 실행한 것으로 합산하지 않는다.
- 로컬 검사 명령·종료코드·로그 SHA receipt와 원격 head, 재현 결과는 동명 JSON에 기록했다. 모델 토큰 사용은 이번 로컬 일반 코드 검사에서 발생하지 않았다. 리뷰 에이전트 자체의 개발 토큰은 별도 미집계다.

## 사용자 추가 결정

앞으로 설치·실행·테스트·배포 폴더 구조는 심사위원용 ZIP으로 고정한다. [구조 결정](../decisions/judge-bundle-layout-20261016.md)을 따른다. README·judge.py·시작 스크립트·codex/·claude/를 기준으로 새 폴더 인수를 수행한다.

권장 후속 순서는 #14 반영 → #13 결함·현재 README 보완 → 통합 manifest 재생성 → 새 심사위원 ZIP만 추출한 설치/실행 검사 → 새 릴리즈 게시다. #7/#10/#11은 각각 미채택/반영 이력으로 정리한다. 이번에는 검토와 구조 결정 기록까지 완료했다.
