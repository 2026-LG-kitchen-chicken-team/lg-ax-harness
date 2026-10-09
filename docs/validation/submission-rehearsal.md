# 출품 업무 소스 ZIP의 새 환경 재현 연습

2026-10-10. `adapters/common/package.py`는 선택한 업무 profile의 정규 파일·Skill 원본/설치 사본·공통 Python·실제 자료·계약·잠금 파일·LICENSE/NOTICE·원본 adapter/템플릿을 ZIP으로 만든다. submission-source-manifest.json에 포함 파일과 SHA를 기록한다. 원문 로그·SQLite·인증·전역 설정·의존성 환경·개발 역할·평가 정답/입력·첨부 PDF는 포함하지 않는다.

`evals/runner/check_package.py`를 실행해 **70개 파일의 Codex 업무 소스 연습 ZIP → 새 Temp 폴더 압축 해제 → 전체 파일 SHA 대조 → uv sync --locked → 업무 Skill wrapper doctor → ZIP 안의 원본으로 새 Claude 사본 재설치**를 실제 확인했다. 모두 exit0이고 파일 지문도 일치했다. native inference·새 세션 발견·시연 영상·발표 인수는 수행하지 않았다. 산출물은 최종 제출물이 아니라 재현 연습이다.

```powershell
uv run python adapters/common/package.py --engine codex --target C:/NEW-PREPARED-PRODUCT --archive C:/NEW-SOURCE.zip
```

대상 폴더와 ZIP은 기존 파일을 덮어쓰지 않는다. 레포 내부/설치 폴더 안의 archive 경로를 거부한다. 실제 ZIP과 Temp 폴더·SHA는 Git 제외 `.harness/submission-rehearsal.json`에 있다. 발표·영상·최종 ZIP의 기능 범위는 실제 검증 결과로 다시 고정해야 한다.

독립 리뷰에서 `adapters` 전체의 확장자 수집이 사적 메모를 포함할 가능성을 발견해 필요한14개 원본 파일을 명시한 목록으로 교체했다. Temp 원본에 시험용 사적 `.md`/`.py`/`.env` 및 runtime SQLite 파일을 놓고 ZIP에서 이름·내용이 제외되는 검사와 기존 archive 덮어쓰기 거부 검사를 통과했다. 교체 후 새 ZIP 재현도 실제 exit0이다. 현재 허용 원본 자체의 내용 검토를 생략할 수 있다는 뜻은 아니다.

2026-10-10에 [공식 공고](https://anchor.changwon.ac.kr/main/menu?do=sinform&gc=Program&program_id=VUlvrXMnryLR&psin_id=VUlvrXN53VEd&spod=s1)를 다시 열어 작동 Agent·Skill, 2차10월21일, 발표10월28일과 발표20쪽·10분/질의5분 안내를 확인했다. 해당 페이지에서는 영상 규격·실제 파일 마감 시각·제출 경로·파일명 규칙을 추가 확정하지 못했다. 변경 공지가 전혀 없다는 증명이 아니며 제출 직전 팀별 운영진 안내와 최신 공지를 대조해야 한다. S06 전체는 미완료다.
