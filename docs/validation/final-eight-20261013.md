# 최종 1–8번 검증 기록

진행 중 기록. 완료·실패·미실행을 분리하며 [실행 결정](../decisions/final-eight-20261013.md)을 따른다. 2026-10-12 기록은 이전 버전의 이력으로 보존한다. 새 모델 비교 결과를 최신 전체 업무 인수로 합산하지 않는다.

## 코드와 소스 경계

출품 메인1/업무Skill6/선택적 역할3을 설치한다. 공식 자료와 후기 연구 역할·Codex TOML/Claude native Agent 사본·지문 검사를 추가하고, reviewer의 불변 packet 직접 독해와 정확 필드명, 단일 모델 사실의 범위와 조건/미확인 전달 지침을 보완했다. manifest 생성기도 현재 일괄/coverage/packet Tool 목록을 보존한다. HTML/프론트5파일은 수정하지 않았다.

- A: shared manifest `9d363bde27bcf94c253fac36df4ccfedb48858d8370e5f8c6e2c29b691d5bdf7`. 부모 단독 모델 비교용. 뒤의 packet 필드/일반 품질 지침 수정 이전이다.
- B: shared manifest `c0e7fec8dd7bed9938e57a69d4707fe86e12a9bc9da6599d89827b7fbfcb937c`. 최신 검증 소스. A 결과를 B native 인수로 설명하지 않는다.
- 실제 평가 자료:112건(후기92/사실20), catalog `c9792d24415d746ab1873343651352957598f33133c042ad0a6725ab8fb13654`. 세 제품군/10모델의 보존 자료이며 출품 기본 catalog와 ZIP에는 넣지 않는다.

최신 B 제품340검사/skip0/exit0/48.985초, 평가144검사/exit0/10.3632초, 자산 검사 errors0이다. receipt와 로그 지문은 동반 JSON에 보존한다. 잘못 선택한 기본 Python3.14의 docx/openpyxl 누락(2실패/7오류/skip1)을 보존했고 번들 Python/잠금 의존성으로 다시 검사했다. 환경 실패를 제품 결함이나 통과로 바꾸지 않는다.

## A의 모델/effort screening

같은 전자레인지4모델의48자료(후기40/사실8)를 모두 전달한다. Codex 네 입력의 실제 prompt 바이트 SHA는 `1f1b2943d7ec1c7b2724a6a58224a67530d60b1f349c0893d0505ff81abd6ec9`로 같다. Claude GUI의 동일 업무/중립 평가 조건 문구는 별도이며 제공사 간 완전히 동일한 prompt 실험은 아니다. 모델/시간을 점수 근거에 쓰지 않은 독립7축 검토이며 job label/부모 문맥이 보이는 한계상 완전 맹검 실험은 아니다.

| 설정 | 최종 경계까지 초 | 실제 결과 | 독립 품질 |
|---|---:|---|---|
| Codex gpt-6.1-sol / low |514.8834|현재completed/valid/v1·5파일/export/최종 전달|13/14,중대0|
| Codex gpt-6.1-sol / medium |561.4929|현재completed/valid/v1·5파일/export/최종 전달|14/14,중대0|
| Codex gpt-6-luna / high |600.5169|timeout·저장completed/v1 있으나 최종 전달 없음|end-to-end gate 실패|
| Claude GUI Sonnet5.5 / medium |218.392|native user→end_turn, 현재valid/v1·5파일/최종 전달|12/14,중대0|
| Claude GUI Opus5.5 / medium |355.975|native user→end_turn, 현재valid/v1·5파일/최종 전달|12/14,중대0|
| Codex gpt-6.1-sol / high |600.6297|timeout·저장completed/v1 있으나 최종 전달 없음|end-to-end gate 실패|
| Claude GUI Sonnet5.5 / high |433.064|native user→end_turn, 현재valid/v1·5파일/최종 전달|12/14,중대0|

각 설정1회이며 반복·타제품군·최신B/온라인/선택 위임 결과는 아직 이 표의 통과에 포함하지 않는다. 저장된 workflow question에는 평가 운영 조건을 섞어 저장한 사례도 있어 업무 원문 경계의 제한을 별도로 기록한다. 정의된 품질 차이 작음 기준을 충족하기 전에는 속도만으로 동등성을 주장하지 않는다.

LOW에는 단일 모델의 설치 사실을 여러 모델에 묶어 귀속하고 미확인 조건을 다르다고 압축한 경미 오류가 있었다. Sonnet 중간에는 사실/AI분류와 검증 조건의 구체성, Opus 중간에는 기능/안내 부재 표현과 baseline/성공 기준의 구체성 한계가 있었다. 더 빠른 설정의 이 차이를 숨기지 않는다. Luna timeout은 점수null·최종 전달 gate 실패이며 저장valid를 성공으로 보정하지 않는다.

Sonnet 높음도 사실/분석 일부 혼합·반례 직접 출처·검증 표본/목표/통제조건의 구체성 한계로12/14였다. 같은 최초 후보 v1의 보고서 실패를 `deliver_result`로 복구했고, Bash 긴 명령의 quote 오류·원문 출력 cp949 오류·진단 invalid_input이 관측됐다. 높은 effort의 시간이 전부 추론 연산으로 증가했다고 해석하지 않는다. 현재 한 사례에서 Sonnet 중간이 같은12/14로 더 빨랐고, Codex는 중간만14/14와600초 내 최종 전달을 함께 충족했다. 최신B/타제품군/반복 확인 전에 보편적 최적 설정이라고 부르지 않는다.

## 병목과 문서

LOW 완료 Tool wall union19.1350초, MEDIUM18.2387초다. stream disconnect 재시도도 관측했으며 차액에는 모델 추론/생성·네트워크·실행기 대기가 포함된다. 차액을 전부 추론 시간으로 표시하지 않는다.

보존한48자료 report plan/export의 일반 코드 재생은 report1.0074/0.5844초, 기존 HTML code0.1227/0.1145초/exit0다. 모델 호출0·새 HTML 개발0이며 브라우저 paint는 미측정이다. 중첩 구간을 합산하지 않는다. 이 자료에서 수백 초의 대부분이 일반 코드 렌더링1초 때문이라는 근거는 없다. 과거30분 실행 원본은 없어 원인 비율을 역산하지 않는다.

LOW PDF14쪽을 실제 PNG로 렌더링해 확인했고 관측한 잘림/겹침/누락0이다. 모델코드/단어 중간 줄바꿈·본문 위주의 가독성 한계는 남는다. 이는 HTML/프론트 개선 완료나 Windows Word/Excel 앱 검수가 아니다. LOW/MEDIUM/SONNET의 각5파일 SHA와 XLSX 계속행을 합친 원문48/48을 대조했다.

## 자료 보강과 남은 검증

새 정상 HTTPS19요청으로 support/설명서 topic/개인 사용기를 관측했다. 이전 원문과 중복1개를 제외한 추가 topic8개+사용기1개를 비공개 보존했다. 현재 catalog 등록0, 추가 저평점 본문0, 장기사용 인증0, exact SKU 적용/OCR 미검증이다. 112등록 자료에 합산하지 않는다. B502S33 실제 support 연결 설명서는 MFL69140202/18이며 다른 냉장고의 MFL71667705/12로 전이하지 않는다.

최신 B의 정상/일반 제품명·미등록 모델·후속·자료 부족·실제 HTTP 실패·취소·새 입력, 연구역할 실제 위임/반영/전체usage·비교 이점, 빈catalog 새 조사 전체, 최종 운영 설정은 별도 시험을 진행한다. 이전 정상/예외·작은 진단·유명한50문항의 결과를 최신 통과로 합산하지 않는다.

## 원격·배포

아직 이번 변경을 commit/push/새 시험판으로 배포하지 않았다. PR#9와 기존0.8.2를 보존한다. 기존 원격 CI는 계정 결제/지출 제한 때문에 jobs의 steps0으로 시작하지 못한 상태였으며, 최종 push 후 실제 상태를 확인한다. 로컬 검사와 원격 CI를 구분한다.
