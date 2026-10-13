# 제품 v0.9.0 시험판

실제 B502S33·MWJ25E의 신규 조사 → 근거 분석·기획 → 검토 → 저장 → 원문 자료집·보고서 전달을 확인하고, 수집·근거 연결·정확 모델 검증·출력을 보완한 제품 전용 시험판이다. 합성 목업은 하네스 완료 근거로 사용하지 않았다. [실제 제품 인수](real-products-20261012.md)와 [파일·페이지·사용량 기록](real-products-20261012.json)이 이번 업무의 범위를 설명한다.

| 항목 | 확인값 |
|---|---|
| Source provenance | `5fe8981c022a49273d81b0dff6c0cb09ef87befd` |
| 부모 없는 제품 snapshot | `25cfd3fdeae419acd8e698aab1ab13ce1ab54877` |
| 제품 tree | `4a240cd9cf029e53f304985492240ebfa8853997` |
| 제품 ZIP | `lg-ax-harness-product-v0.9.0.zip` /78파일 /227122바이트 |
| ZIP SHA256 | `e37b7c21972644b977bfc84be7ef507f498a1d04564b722c32d5a8d7ad2baa9a` |
| 공통 source manifest | `3d790f846d806f9c64aba25a7c8755770827d9c1f56e41d3cb64413beee36873` |
| 설치 manifest | `145683fe9d4d66d2c5a8efb08c725705d25205577a8afbcb38a5b4f14e2bd21e` |

ZIP의 CRC·중복/위험 경로·manifest77파일 SHA·빈 기본 catalog·계약/잠금/라이선스를 확인했다. 새 폴더에 추출한 Codex와 ZIP의 portable adapter로 설치한 Claude 각각 `uv sync --locked`와 doctor가 exit0였다. Codex CLI0.162.1 로그인 상태와 문서 라이브러리 import를 확인했다. Claude Code2.1.278의 설치/버전·공통 Tool 범위만 확인했으며 인증·native 발견·새 AI 업무 인수를 추가로 주장하지 않는다.

제품 snapshot에는 부모 commit이 없다. ZIP과 snapshot78파일을 byte 대조했고 main 작업 index가 변하지 않았음을 확인했다. 개발 장부·평가/합성 예제·실제 원문 자료/보고서·개인 로그·DB·의존성 환경은 ZIP과 자동 tag archive에 넣지 않았다. 사용자용 보고서12파일은 로컬 전달 폴더에 별도로 보존했다.

## 원격 반영과 검증

Source와 실제 인수 기록을 main에 직접 push했다. [v0.9.0 릴리스](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.9.0)는 prerelease이며 ZIP과 SHA256SUMS를 새 파일로 첨부했다. 이전 릴리스·원본 업무 폴더·이전 출력 및 실패 기록을 덮어쓰지 않았다.

원격 annotated tag의 실제 peeled commit은 위 제품 snapshot과 일치한다. 릴리스를 다시 내려받아 ZIP SHA256·체크섬 파일·GitHub digest·asset size를 대조했다. GitHub 자동 tag archive도 직접 내려받아 root prefix를 제거한78파일 각각을 ZIP과 byte 대조했고 모두 일치했다.

최종 개발 인수 장부 `real-products-final-20261012`는 실제 기존 Agent ID를 재사용해 최신 packet의 입력·계약과 한정된 실제 근거를 재검토했다. 실행된 task별 receipt와 현재 지문을 확인한 `dev-harness/cli.py complete`는 errors[]·exit0였다. 원래 업무 AI2건과 보존 입력 재생2건을 구분한다. 최종 로컬 코드 검사는 제품239(1개 platform skip), 평가128, eval28, 개발22의 exit0다. 실제 보고서 검수는 Windows109쪽/30시트·원문 셀 링크135개 범위다. 실물 구현·기존 설정/펌웨어·고객 효과·다른 환경·Claude 새 AI 인수·영상/최종 접수는 별도다.

[Source push의 원격 CI](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/actions/runs/38198555618)는 Windows·Ubuntu 두 job 모두 failure·steps0다. 실제 annotation은 최근 계정 결제 실패 또는 지출 한도 증가 필요 때문에 job이 시작되지 않았다고 한다. 두 원인 중 어느 것인지는 확인하지 않았고 계정 결제·지출 설정은 변경하지 않았다. 로컬 검사 통과를 원격 CI 통과로 바꾸지 않는다.
