# 교수님 피드백 — 시간 지연 1차 탐색

2026-10-12 KST, source 확인 기준 `989fcc77e5611f7097bf0df804c0c435d900d802`. [새 방향](../decisions/professor-feedback-20261012.md)에 따라 시간 기록·Agent/Skill 지침·코드 렌더링 경로를 읽고 합성 fixture의 **오프라인 코드 렌더링만** 측정했다. 새 업무 AI·웹 조사·제품/웹 코드 변경을 하지 않았다.

## 실제 업무 전체 시간과 확인 한계

| 자료 | 시간 | 실제 확인 범위 |
|---|---|---|
| [B502S33 실행 기록](real-products-20261012.json) | 639.92초 | 기존 기록의 실제 Codex 업무 전체, 이번 세션에서 재실행하지 않음 |
| [MWJ25E 실행 기록](real-products-20261012.json) | 753.38초 | 같은 기존 기록의 별도 실제 업무. 모델은 설정 상속·독립 미관측 |
| [대겸 최신 메일](team-runs/records/20261012-team-mail-progress-review.md) 전자레인지 | 28분 43초 | 팀원 보고. 해당 새 실행의 단계별 원본 trace/보고서는 이번 탐색에서 대조하지 않음 |

자료/질문/소스/모델 설정이 다른 실행을 합쳐 평균·개선률을 계산하지 않는다. 위 기록만으로 조사·추론·파일 제작 각 구간의 비중을 알 수 없다. 최신 실제 실행의 병목 1위를 확정하지 않는다.

## 코드·지침에서 찾은 비용 후보

| 관측한 구조 | 확인 위치 | 다음 판단 |
|---|---|---|
| 화면 만드는 별도 업무 서브에이전트는 확인되지 않음 | [메인 Agent](../../agents/product-planning.md) | 출품은 메인1·업무 Skill6개. “HTML 그리는 에이전트 제거”를 이미 수행했다고 설명하지 않는다 |
| 보고서 계획을 AI가 작성할 수 있음 | [작성 지침](../../skills/review-and-revise/references/report-writing.md), [delivery.build_report_plan](../../product-tools/product_tools/delivery.py) | 긴 설명·원문 반복 작성이 추론/출력 시간을 늘릴 가능성. 기본 계획 생성도 이미 코드에 있어 재사용 후보 |
| 코드가 XLSX·DOCX·PDF를 순서대로 모두 생성 | [reporting.render_report](../../product-tools/product_tools/reporting.py) | HTML 우선·추가 형식 선택 생성은 가능한 개선 방향. 현재 코드의 주된 병목인지 실제 크기/실행에서 측정 필요 |
| 같은 chart가 XLSX/DOCX/PDF 경로에서 반복 처리 | [도표 코드](../../product-tools/product_tools/reporting.py) | 이번 fixture4차트에서 drawings12회·PNG8회. 같은 데이터/스타일 지문의 렌더 결과 재사용 후보이며 현 단계 절감 효과는 미입증 |
| 이미지 제작은 별도 가용 Tool 호출 가능 | [컨셉 이미지 지침](../../skills/concept-writing/references/concept-images.md) | 그림이 요청되거나 판단에 도움이 될 때만 실행. 웹 레이아웃/단순 도표에 이미지 생성 호출을 붙이지 않는다 |
| 모델/effort를 프로젝트 개발 설정에서 고정하지 않음 | [.codex 설정](../../.codex/config.toml) | 개발 설정은 상속. 출품 검증은 별도 명시 프로파일/메타데이터로 고정해야 한다 |

각 후보는 코드/지침 구조에 따른 판단이다. 호출별 경과시간이 없으므로 추론·검색·중복 조회가 전체 시간의 몇 %인지 추정하지 않았다.

## 실제 오프라인 렌더링 측정

고정된 현재 렌더러와 `tests/product-tools/test_reporting.py::example_plan`을 사용했다. 새로 만든 고객 자료가 아니라 기존 **계약 시험용 합성 fixture**다. 표·차트4개·출처2개를 포함하며 생성 파일은 XLSX3/DOCX1/PDF1, PDF5쪽이다. 실제 시장 결과·시연 완료 근거로 사용하지 않는다.

Python `3.12.14`, 로컬 번들 런타임. 네트워크·업무 모델 호출0. 실제 명령 exit0:

```powershell
& 'C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' '.harness/feedback-20261012/profile_renderer.py'
```

진단 script·원본 측정 JSON·합성 생성 파일은 Git 제외 `.harness/feedback-20261012/`에 보존한다. 비개인 측정 수치와 입력/소스 지문은 [동반 JSON](professor-feedback-latency-20261012.json)에 기록했다.

| 구간 | 첫 생성(초) | 같은 프로세스 두 번째 생성(초) |
|---|---:|---:|
| 전체 render_report | 0.6967 | 0.2389 |
| 의존성 import/_deps | 0.2646 | 0.0001 |
| XLSX 자료집/도표 생성 | 0.2827 | 0.0829 |
| DOCX 생성 | 0.0814 | 0.0799 |
| PDF 생성 | 0.0248 | 0.0220 |
| 구조/링크 검사 | 0.0382 | 0.0508 |
| 차트 구조 생성(drawings) | 0.0397 | 0.0027 |
| 차트 PNG 렌더링 | 0.1788 | 0.0891 |

함수별 값은 **inclusive**다. chart 시간은 XLSX/DOCX/PDF 내부에 포함되므로 행 전체를 더하지 않는다. 프로세스 시작·모델 추론·검색/수집·사람 화면 검수 시간은 측정 범위 밖이다. `ready=true`는 파일 생성/구조 확인이며 `semantic_status=unverified`, `visual_review=not_run`이다.

이 측정은 작은 fixture의 코드 렌더러가 초 단위 이하로 동작한다는 한정된 근거다. 실제 14~40쪽 보고서나 그 실행의 모델/검색 시간을 대신하지 않는다. HTML 전환만으로 10~28분 업무가 몇 초로 줄어든다고 주장할 수 없다.

## 다음 계측과 개선 우선순위

1. 실제 실행의 단계별 시간·반복 호출·오류·재시도·대기 span을 먼저 확보한다. 모델/effort·CLI·질문·자료·제품 버전을 고정한다.
2. AI가 저장 원문·이미 계산한 집계·기획 결과를 보고서 계획에 다시 길게 복사하는 부분과 중복 조회를 우선 확인한다. 원문 결합·집계·레이아웃은 코드로, 근거 판단·필요한 설명은 AI로 나눈다.
3. HTML 보고서 생성과 화면 표시를 공통 템플릿으로 구현하고 추가 형식은 필요할 때 생성한다. 실제 검증/출처 연결은 제거하지 않는다.
4. 동일 조건의 새 실제 실행에서 품질·시간·usage를 확인한 뒤 수치로 보고한다. 현재 탐색만으로 개선률·토큰 절감률·전체 병목 해결을 선언하지 않는다.

위는 탐색 결과와 후속 계획이다. 황대겸/최길웅의 제품·웹 작업과 겹치는 구현을 시작하거나 미병합 PR를 임의로 통합하지 않았다.
