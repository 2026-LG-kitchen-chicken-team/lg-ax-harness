# 비공개 설치·제품 전용 배포 인수

2026-10-16 사용자 승인에 따라 [제품 전용 저장소](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-agent)를 **비공개**로 만들고 AI 설치 요청문·Windows PowerShell·macOS/Linux Bash 설치 도구를 배포했다. [기계 기록](private-installer-20261016.json), [일정·공개 범위](../decisions/private-distribution-20261016.md), [설치 안내 원본](../../adapters/common/distribution/README.md).

## 실제 변경과 배포

- `installer-v0.1.0` 시험판은 install.py·install.ps1·install.sh·README·agent.md·체크섬6자산이다. 심사 제품은 변경 없이 `product-v0.16.1`을 내려받는다.
- 개발 저장소 이력을 가져오지 않았다. 배포 main에는 설치 코드·안내5파일만 있으며 제품 소스 태그는 부모0의128파일 snapshot이다. README/agent.md가 AI 설치 범위·계정·폴더·정상 승인·오류 조치를 안내한다.
- 비공개 `gh` 인증과 명시적 `public` 경로를 구분한다. 인증 토큰 출력/저장·공개 fallback·모델 호출·GUI 실행은 없다. 설치기는 체크섬·내부 파일 지문·경로·크기를 확인하고 새 폴더만 사용한다.
- 기존 product-v0.16.1 자산3개는 새 원격에서 다시 내려받아 원래 파일과 raw byte 동일함을 확인했다. 자동 Source ZIP128파일도 동일하다. 개발 저장소 기존 릴리즈는 수정하지 않았다.

## 실제 검사

- 단위14검사 통과: 인증 실패·비밀 출력 차단·공개 transport mock·checksum/내부 SHA/버전 불일치·경로 탈출·symlink·파일 추가·대소문자 충돌·기존 폴더 보존·setup 실패 보존.
- Windows PowerShell5.1: Codex와 Claude 각각 실제 인증 다운로드→205파일 검증→설치 준비와204파일 bundle check, 총4명령 exit0.
- WSL Ubuntu24.04: 같은 두 엔진을 Linux 파일시스템에 실제 설치·검사, 총4명령 exit0.
- 게시 후 README의 `gh api` 한 줄 진입 명령도 Windows Codex·Ubuntu Claude 각각 실행해 prepared:true/205파일 확인,2명령 exit0.
- 익명 GitHub HTTP404와 격리된 무인증 gh exit4를 확인했다. 전역 인증을 로그아웃하지 않았다. 제품·개발 저장소 모두 private다.
- 독립 읽기 전용 검토의 미해결 P1/P2는0이며 네 설치 폴더의 managed204파일과 원본을 직접 대조했다.

최초 Windows 시험은 환경에서 Get-FileHash 명령을 찾지 못해 exit1이었다. .NET SHA256으로 바꾸고 두 엔진을 다시 실제 설치했다. 구버전 Bash의 빈 배열/nounset 호환 문제도 문자열 flag 방식으로 수정했다. 실패 기록은 로컬 원본에 보존한다. macOS 실기, 공개 상태의 비인증 성공 다운로드, AI 업무 및 GUI 화면은 이번 통과 범위가 아니다. 설치 소요시간은 캐시·로컬 환경이 포함돼 성능 우위나 AI 토큰 절감률로 쓰지 않는다.

## 공개 예약

사용자 제공 운영자료의 **10/20 18:00 KST 제출 마감**에 따라 **2026-10-21 09:00 KST**에 제품 저장소만 한 번 공개하도록 앱 예약 `lg-ax`를 갱신했다. 공개 전 refs·파일·자산 지문이 이 기록과 일치하는지 확인한다. 개발 저장소 lg-ax-harness는 비공개를 유지한다. 현재 공개한 것은 아니며 대회 제출·접수 완료도 아니다. 앱 예약 실행 환경이 사용 가능한 상태여야 실제 작업이 수행된다.

발표·영상에는 AI 설치 요청 붙여넣기/한 줄 명령 → 비공개 다운로드·무결성 확인 → 준비 완료 → 첫 질문으로 연결되는 도입 장면을 사용한다. 설치 편의성과 동일 버전 재현성을 실제 화면으로 보여준다.
