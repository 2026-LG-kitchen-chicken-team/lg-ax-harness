# 제품 v0.8.1 시험판

사용자가 지정한 번호 **0.8.1**로 보고서 표현 개선과 이미 진행 중인 선택형 뷰어 통합을 마감한다. main과 릴리즈 게시 확인 후 이번 작업을 종료한다. 상세 실제 검수·원문 보존·시간 실패는 [보고서 표현 검증](report-style-20261012.md)을 따른다.

컨셉·시연 이미지 생성/삽입 경로를 제거했다. 핵심 굵기·제목 위계·인용 서식과 긴 원문의 인쇄 행 높이를 개선했다. 원문과 출처 번호·웹 URL·정확한 XLSX 셀을 유지한다. PR #6의 원저자 이력을 보존하고 뷰어의 출처 지문·하위 경로 검사, Windows UTF8 Python 경로 전달과 시작 경고 출력 처리를 보완했다. 기본 제품 설치는 훅을 등록하지 않는다.

| 항목 | 확인값 |
|---|---|
| 제품 source provenance | `aef85804cdf61295c6253bd4c6479e43bb18d929` |
| 부모 없는 제품 snapshot | `1046ccf301950e883992ea3f5dbdb0fc7ceadfb0` |
| ZIP | `lg-ax-harness-product-v0.8.1.zip`, 84파일, 330036바이트 |
| ZIP SHA256 | `cd5eefabeb46e7585891d44da00c7387e00ec3c9b0085bead52f474197b9eae2` |
| source manifest | `6d85b6c3083ec1aafe7fd2c8d5cdff5351f41819547b27481e4d34af7e9fa3e7` |
| 설치 manifest | `cef46a3a0c243cc77854d0df820087804942ac1bc2fe4da3c1df41821788c810` |
| 보고서 profile | `numbered-sources-v6` |

최종 소스에서 제품 298개·평가 128개·웹 64개·독립 설치 3개 검사 모두 PASS, skip 0이었다. 자산 검사 오류는 0이다. task-bound receipt의 입력·로그·binding을 재확인했고 독립 보고서 14개·뷰어 통합 10개 검사와 범위 한정 리뷰를 마쳤다. 장부 `final-v081-20261012`의 complete는 errors[]·exit0이다. 같은 검사의 재실행을 새 사례로 합산하지 않는다.

웹 검사는 uv와 실제 Python 3.12 설치 경로를 프로세스 환경에 지정한 Windows 실행이다. 한글·공백 경로, cmd·Windows PowerShell·pwsh, 원래 SHA pin과 격리 실행, 실패 무출력·exit0, junction/reparse 경로 거절을 확인했다. 사용자 전역 설정·인증을 변경하거나 일반 sandbox 지원을 인증하지 않았다. Claude 새 업무 AI 인수는 별도다.

ZIP CRC·중복/위험 경로·빈 초기 catalog·모든 파일 manifest SHA와 snapshot/ZIP byte 일치를 확인했다. 새 Codex 추출본과 portable Claude 사본에서 잠금 설치·doctor는 각각 exit0이었다. 원 index는 유지됐으며 실제 원문·보고서·로그·DB·전역 설정·의존성 환경을 제품 ZIP에 포함하지 않았다. 보고서 15개 전달 사본은 로컬에 보존하고 인계 SHA와 대조했다.

두 새 native 조사에서 파일이 생성됐지만 전체1800초 완료는 실패였다. 이 실패와 PDF의 한글 기울임 대체, 기존 CI 실행 환경/과금 한계, PR #7의 별도 draft를 보존한다. 로컬 코드 검사와 실제 업무 전체 성공·효과 측정·최종 대회 접수는 별개다. 기존 모든 릴리즈와 팀원의 원격 교수 피드백·메일·전략 참고 기록을 보존한다.
