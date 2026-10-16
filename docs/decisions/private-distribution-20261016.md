# 비공개 설치 시험과 제품 전용 공개 전환

2026-10-16 사용자 결정: 비공개 상태에서 AI 설치 요청문·Windows PowerShell·macOS/Linux 설치 명령을 구현·시험하고 제출 마감 다음 날 공개 전환을 예약한다. 공개 대상 추가 질문에는 **제품 설치·배포 전용 저장소만 공개**를 선택했다.

- 개발 저장소 `2026-LG-kitchen-chicken-team/lg-ax-harness`는 계속 비공개다.
- 제품 전용 `2026-LG-kitchen-chicken-team/lg-ax-agent`를 별도 비공개 저장소로 만들었다. 개발 Git 이력을 가져오지 않고 제품 소스 snapshot과 설치 코드·안내만 저장한다.
- 기존 product-v0.16.1의 심사 ZIP·제품 소스 ZIP·checksum은 바이트 그대로 복제한다. 새 installer-v0.1.0은 이 제품 버전을 설치하는 보조 도구다. 실행 코드·Skill·서브에이전트·모델 기본값은 변경하지 않는다.
- 임시 공개 시험은 하지 않는다. GitHub CLI의 정상 인증 다운로드로 시험하고, 공개 전환 이후 경로는 명시적인 public 모드로 제공한다. 인증 실패를 공개 경로로 자동 우회하지 않는다.
- 제품 전용 공개는 공개 열람 허용이며, 전체 자체 코드의 오픈소스 라이선스를 새로 부여하는 결정은 아니다. 기존 제3자 LICENSE/NOTICE는 제품 패키지에서 보존한다.

## 마감 검색 결과와 예약 조건

초기 검색에서는 정확한 2차 제출 마감 날짜·시각을 확인하지 못했다. 이후 사용자가 제공한 「최신 개발·제출 상태 · 2026-10-14」 운영자료에서 **작품 제출 마감 2026-10-20 18:00 KST**를 확인했다. 아래는 초기 검색 범위이며 최신 날짜 판정은 사용자 제공 운영자료를 따른다.

| 원본 | 결과 |
|---|---|
| [공식 프로그램 공고](https://anchor.changwon.ac.kr/main/menu?do=sinform&gc=Program&program_id=VUlvrXMnryLR&psin_id=VUlvrXN53VEd&spod=s1) | 최초 접수9/28 18:00, 2차 **심사**10/21, 발표심사10/28. 2차 제출 마감 아님 |
| 사용자 제공 05_2차과제_제출및평가안내.pdf 2쪽 전체와 동일 첨부 PDF | 평가·제출물 안내만 있으며 제출일시 없음. SHA256 `c61fec7064674dbb4f4a6006a299c34c870ef2240b3a0f5d2e941c355777af24` |
| 담당자10/2 선발안내 및 대학·담당자 수신메일 검색 | 정확한 2차 제출 마감 확인 못함 |

최신 근거 파일은 사용자 첨부 `붙여넣은 텍스트.txt`(SHA256 `b497231728c07bcacb430ba34ced7da21dde174ff588277ac2046bcd562eb6d9`)다. 「지금 먼저 볼 것」의 “작품 제출 마감: 2026년 10월 20일 오후 6:00” 및 10/14 요약의10/20 18:00을 대조했다. 기록이 가리키는10/2 18:08 「2차 심사기준 공지」 원본 메일은 현재 연결 수신함에서 찾지 못했으므로 원본 메일 독립 검증으로 표현하지 않는다. 첨부에 남은20쪽 제한·시연 방식 미확인 등의 과거 문구는10/13 최신 운영진 공지로 대체한다.

**공개 예약은 2026-10-21 09:00 KST(UTC 2026-10-21 00:00)**, 제품 저장소만 대상으로 한 번 실행한다. 기존 마감 확인용 일일 예약 `lg-ax`를 이 일정으로 갱신했다. 그전에는 비공개를 유지한다. 공개 전 검증된 제품 전용 refs·파일·자산 지문과 대조하고 범위가 바뀌면 조치를 알린다. 대회 최종 접수와 공개 설정은 별개다. 예약 생성 결과·배포 대상 SHA·실제 검증은 `docs/validation/private-installer-20261016.md`와 JSON에 보존한다.

## 발표·영상 어필

설치 요청 붙여넣기 또는 한 줄 명령 → 인증된 제품 다운로드 → 체크섬·파일 확인 → 준비 완료 → 시작 파일 → 첫 질문 → 대시보드·결과 웹의 흐름을 보여준다. 실제 검증은 Windows PowerShell과 Ubuntu Linux의 Codex/Claude 설치 준비이며, macOS 실기는 미실행이다. 설치 편의성·환경 준비 자동화·버전 재현성으로 설명하고 이 측정을 AI 업무 시간·토큰 절감률로 전용하지 않는다.

근거: [GitHub CLI release download](https://cli.github.com/manual/gh_release_download), [GitHub 공개 범위 변경](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
