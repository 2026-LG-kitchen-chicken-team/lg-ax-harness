# v7.2 Codex·Claude 제한 회귀

수정 전7.1 동일 입력 각1회와 수정 후7.2 각4입력을 분리한다. 환경마다 최신4입력/3대화, 입력당420초, 자동 재실행0회다. 실패한 부모의 후속은 not_run이며 새 대화로 바꾸지 않는다. 공식 심사 문제나 blind holdout이 아니다. 사람 대비 절감효과는 사용자 결정으로 제외했다.

420초는 환경별 적용을 구분한다. Codex는 평가 transport의 로컬 timeout 설정이며 backend 종료 완전성을 보증하지 않는다. Claude는 prompt 작업 예산과2초 주기 collector의 시간초과 판정이다. 자동 UI/backend 강제중단 장치는 구현하지 않았으며 timeout이면 별도 UI Stop 관측이 필요하다. 이번 네 입력은 예산 안에 종료하여 Claude timeout/Stop 인수는 not_run이다.

| 입력 | 목적 | 초기 자료 |
|---|---|---|
| A01 | 실제 불편·기능 대조와 저장/최종 전달, 수정 전과 동일 업무 | 기존 v4 DUBJ2EA |
| A02 | 일반 '전자레인지' 입력을 정확한 모델별 제한 사례에 연결 | 기존 v4 |
| A03 | 같은 대화의 내부 치수 부족·그릇 적합 판단 | A02 자료/대화 유지 |
| A04 | 미등록 MW23GD를 실제 조사/등록하거나 이유 있는 보류로 전달 | 빈 catalog |

실행 전에 제품 원본/자료/각 prompt/보호 파일 지문을 ignored report에 동결한다. 제품 답안을 평가 코드에서 생성하지 않는다. 최신 설치본의 Agent1개·Skill6개로 업무를 실행하며 개발 reviewer는 별도다. Codex transport와 Claude Desktop native JSONL의 실제 최종 전달 증거를 각각 검사한다. Claude를 가짜 Codex event로 변환하지 않는다.

산출물 검사는 실제 원질문·receipt·export SHA·당시 SQLite·모델/자료/코드 지문과 기존 의미 계약을 대조한다. 의미 품질은 원문/근거/모델 귀속/공식문구와 해석/중복/불확실성을 독립 검토한다. accepted나 completed는 의미·실물·시장·효과 검증 인증이 아니다. timeout 후 저장만 존재해도 전달 성공으로 바꾸지 않는다.

Codex는 같은 native session 마지막 누적 usage를 합산하며 캐시/추론은 전체 입출력의 부분값이다. Claude는 native assistant message ID 중복을 제거하고 비캐시 입력·cache creation·cache read의 서로 다른 입력 항목을 합산한다. output의 thinking 부분이나 iterations를 다시 더하지 않는다. 미관측은 unknown/null이다. backend 전체 호출·청구·하위 에이전트 전체성은 이 관측만으로 입증하지 않는다. 환경간 모델·설정이 다르므로 모델 우열/범용 정확도/비용 절감률을 주장하지 않는다. 동일 환경 전후1회는 관측 변화이며 반복 통계가 아니다.

개선은 빈 후보 양식·작성 상한·조사/저장/전달 시간 배분과 원질문/발췌 범위 지침이다. 질문별 정답·고정 제품 선택·가상 후기·시각화용 모델 호출은 추가하지 않는다. 검증 결과와 남은 결함은 별도 최신 보고를 따른다.
