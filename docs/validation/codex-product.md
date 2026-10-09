# Codex 업무 설치·실제 실행 검증

2026-10-10. 사용자 요청의 Codex 출품 설치(S02a)와 전체 업무 연결(S03b) 검증이다. 개발 체계 검증과 AI 의미 품질·효과 평가(S05)는 별도다.

## 설치와 지원 범위

- Windows, Codex CLI 0.162.0, 로그인된 ChatGPT 계정. 모델/추론 설정을 변경하지 않았다. 실제 native turn_context에서 `gpt-6.1-sol`, `ultra`, provider openai를 관측했다.
- Python 3.12.14 개발 환경, 설치 폴더의 uv는 로컬 Python 3.12.10을 선택했다. product pyproject/uv.lock은 Python3.12·stdlib만 사용한다.
- 실제 설치 폴더: `C:/Users/user/Documents/ChatGPT/LG-AX-product-codex`. 개발 레포 밖의 새 폴더에 Agent1개·업무Skill5개+조건부외부조사1개를 정규 파일로 배치했다. 개발 역할6개/Skill9개·인증·개인 설정은 복사하지 않았다.
- `uv sync --locked`, `uv run python product-doctor.py`와 설치 지문 검사는 실제 실행한다. 준비 검사는 자동 Skill 호출·AI 품질을 대신하지 않는다.
- 글로벌 사용자 Skill은 native 환경에 함께 발견될 수 있다. 설치 도구는 프로젝트 파일만 쓰며 전역 설정을 수정하지 않는다.

## 실제 Codex 첫 업무

첫 입력은 Skill 이름/본문을 넣지 않은 자연어다.

```text
T876MQQ012를 기준으로 수납·정리 개선안을 만들어줘. 하드웨어 추가 없이, 실제 리뷰와 기존 제품 기능을 근거로 해줘.
```

일회성 개발 인수검사에서 `codex -a never exec --sandbox danger-full-access -C PRODUCT --skip-git-repo-check --json -o FINAL -`에 질문을 stdin으로 전달했다. 이 subprocess는 Git 제외된 개발 검사이며 제품 설치 코드·wrapper가 Codex나 모델 API를 내부 호출하는 구조가 아니다. 제출 사용자는 제품 폴더에서 `codex`를 열고 질문한다.

실제 native ID `01a12258-d70a-7610-bce1-ccb1ebc99b56`, exit0, 458.58초다. native 초기 Skill 목록에 업무6개가 발견됐고 본문 읽기와 실제 wrapper 실행을 별도 확인했다. scope 필드를 model_scope로 잘못 넣은 조회2개는 exit1 invalid_input으로 실패한 뒤 scope 입력으로 고쳤다. 저장 근거 부족에 조건부 외부조사를 사용하고 native 도구로 관측한 LG PDP 후기 발췌2개를 새 runtime catalog `lg-t876-storage-20261010-v1`로 등록했다. 관측 원문·실행 로그는 Git 제외다.

business session `session-98cc29764a50465694df59ddbeb525fe`, turn `turn-eff130e3042845b7be428b93dca8ae22`에 실제 PlanningInput→선택 근거→불편→기존 기능 대조→안1개→assessment→저장을 연결했다. 최초 candidate0는 unused_evidence로 거절됐고 result_version1/revision0로 남았다. 같은 turn candidate1은 추가 긍정·기대 후기2개를 remaining_pain R01의 상충 자료로 연결하고 주장/assessment에 해석 한계를 추가한 뒤 accepted=true/completed, result_version2/revision1로 저장됐다. 출처 삭제가 아니라 사용 관계 보완이었다. get_turn과 export_session도 실제 실행했다.

최종 응답은 원문 링크와 위치, 불편1건의 한계·수수료 고지, 미확인 내부 치수와 효과를 명시했다. ‘가림 점검·칸별 위치 메모’ 기획안을 작성했다. 현재 제품 불편을 이전 삼성 제품 온도 불량과 구분했다. 코드의 검토 통과는 모델의 의미 해석·실제 수요·효과를 인증하지 않는다.

첫 실행 뒤 독립 리뷰의 큰 응답 재전송·버전 선택 보강을 최종 원본에 반영했다. 첫 설치 버전은 `.harness/product-first-version`에 그대로 보존하고 새 설치에 이번 프로젝트의 runtime-data만 복사했다. 개인 인증·설정은 옮기지 않았다. 후속 실행은 최종 원본에서 검증한다. 초기 source manifest SHA는 로컬 install-version.json에 남는다.

## 같은 native 대화의 실제 후속 요청

```text
이전 안을 장보기 전에 쓰는 3단계 안내로 구체화해줘. 하드웨어 추가 금지 조건은 유지해.
```

`codex -a never exec --sandbox danger-full-access resume --skip-git-repo-check --json -o FINAL 01a12258-d70a-7610-bce1-ccb1ebc99b56 -`를 제품 폴더 cwd에서 실행했다. 동일 native ID, exit0, 184.97초다. 같은 business session의 새 turn `turn-b3c40bacba634a02a8aecb8d70e27ba2`, request_key 신규, 이전 turn 연결·조건 유지·previous.valid_for_current_context=false를 확인했다. 이전 실패/수정 이력은 보존했고 후속 최초 후보는 result_version1/revision0/completed다.

최종 응답은 실제 원문 근거와 ‘가려진 칸 확인→양/위치 기록→구매/재확인 목록 구분’의3단계를 제공했다. 미확인을 재고 없음으로 바꾸지 않고 추가 하드웨어·고정 배치·치수/효과 추정을 제외했다. 실제 review/validate/save/get_turn/export를 실행했다. 기존 전체 export를 모델에게 다시 로드하지 않았다.

## 실제 자료 부족·미확인 모델

- 저장 자료만 사용하는 S836GBB122 청소 요청: native ID `01a12263-ab49-7f12-ace2-1eab5aabbe9b`, exit0, 237.20초. 후기3개·공식 사실7개를 확인하고 긍정/기대 표현을 청소 불편으로 바꾸지 않았다. business session `session-f8500868ddfc4585a1f449eb7c24ebc3`, turn `turn-2022e0f763314fe482698668016a84d9`에서 pains/remaining_pains/concepts=[]·held, result_version2/revision1을 저장·재확인·export했다. 최초 후보의 unused_evidence 거절도 이력에 보존했다. 외부 검색 호출0건이다.
- 이 실행에서 큰 JSON 여러 개를 삽입한 Windows 명령은 os error206(파일 이름/확장명 너무 김), exit-1로 실패했다. 파일을 나눈 명령으로 같은 업무 turn에서 복구했다. 실제 Tool 입력/명령 오류와 업무 후보 수정 횟수는 별도다. 최종 제품 AGENTS에 파일별 저장·Python JSON 조합 지침을 추가했다.
- `LG-UNKNOWN-2026` 저장 자료 요청: native ID `01a12267-cbe5-77b0-bd66-440d6d8005a0`, exit0, 63.49초. `unknown_model`을 needs_input으로 기록하고 내부 ID 대신 정확한 모델을 확인했다. session `session-b180b37000b84b2aa69e6c66463b6e0a`에 request1개, PlanningTurn0개, export.turn_count=0이다. 현재 지원 catalog 밖 모델을 다른 제품으로 대체하지 않았고 외부 검색 호출0건이다.

위 정상/후속/보류/확인 요청은 설치·업무 연결 인수 사례다. 별도 held-out 심사 입력 전체와 공격·baseline·효과 평가를 통과시킨 것은 아니다. 업무 수정 최대2회의 소진 경계는 코드 검사이며 native 사례에서 실제 관측한 수정은1회다.

## Windows 명령 실행 제한

같은 질문의 workspace-write 실행 ID `01a12254-d8cd-7cf2-aa61-7abfada93661`은 명령 실행기 준비 단계에서 `helper_unknown_error: setup refresh had errors`로 실패했다. 명령 exit -1, 업무 코드가 실행되지 않아 통과로 기록하지 않았다. 실제 taskkill /PID77040 /T /F 결과로 종료했고 부모 exit1, 142.06초다. 실행 폴더를 `.harness/failed-product-workspace`에 보존했다. 전체 접근 모드 성공을 workspace-write 지원 성공으로 바꾸지 않는다. 실행자의 권한 선택은 필요하며 설치 도구가 이를 자동 변경하지 않는다.

## 사용량

이 CLI 버전의 turn.completed usage는 같은 native 세션의 누적 합계다. resume 뒤 값을 새로운 호출 합계로 그대로 더하지 않는다. 실제 rollout token_count.info.total_token_usage와 일치하는 것을 확인했다. 첫 실행값과 다음 실행값의 차이를 후속 입력의 관측량으로 등록한다. 전체 backend 모델 호출별 청구 기록으로 설명하지 않는다. cached_input은 input의 부분이며 합산하지 않는다. reasoning_output도 output에 포함된 관측값이다.

| 사례 | 입력 | 캐시 입력 | 출력 | 생각 출력 | 실측 비용 |
|---|---:|---:|---:|---:|---|
| 첫 업무 | 1,480,710 | 1,392,000 | 18,405 | 4,151 | 미측정 |
| 같은 대화 후속 입력(누적값의 차이) | 667,568 | 649,088 | 7,266 | 2,263 | 미측정 |
| 자료 부족 보류 | 700,960 | 627,712 | 9,058 | 2,536 | 미측정 |
| 미확인 모델 확인 요청 | 240,482 | 218,368 | 1,773 | 523 | 미측정 |
| workspace-write 실패 | 미측정 | 미측정 | 미측정 | 미측정 | 미측정 |

첫 입력값과 후속 입력의 누적 차이를 실제 업무 usage에 별도 등록하고 다시 export했다. 두 기록 합계는 native 세션 최신 누적 입력2,148,278/캐시2,041,088/출력25,671/생각6,414와 일치한다. 모델이 usage를 추정한 것은 아니다. 미확인 모델 실행은 PlanningTurn을 만들지 않으므로 CLI 사용량을 native 인수 관측 파일에 별도 보존한다. 업무 DB의 turn 사용량만을 전체 인수 사용량이라고 부르지 않는다. 성공 CLI 실행의 중복 없는 합계는 입력3,089,720/캐시2,887,168/출력36,502/생각9,473이다. 실패 실행의 미측정을0으로 채우거나 보유 크레딧/30만원에서 차감액을 추정하지 않는다. 첫 입력의 합계가 큰 점은 S05에서 불필요 조사·계약/원문 재로딩·호출수와 baseline을 비교할 개선 대상이다. 지금 토큰 절감을 입증했다고 주장하지 않는다.

## 코드 검사와 독립 리뷰

상품기획 공통 도구 검사75개가 exit0이다. 설치·이동 후 wrapper·hash drift, UUID/요청 재개·추가 질문·이전 조건/이력, 복수 버전 선택, failed candidate 최초0/수정1/2와 한도, 대형 검토 응답·이력 export, 미측정 runtime 상속 금지를 포함한다. 합성 경계 검사는 실제 고객 불편의 근거가 아니다.

독립 읽기 전용 리뷰 `/root/codex_product_design`의 지적을 반영했다. 119KiB 검토 중복 응답을 요약하고 전체 assessment는 DB/export에 유지했다. 큰 후속 요청 재전송66,686 bytes는 수정 뒤34,352 bytes로 확인됐다. 전이 전후 유효성·미관측 runtime·복수 문서 버전 선택을 확인했고 추가 실질 결함은 보고되지 않았다. native 실제 완료·usage와 업무 의미 품질은 이 코드 리뷰의 범위 밖이다.

## 남은 평가

Claude/Gemini 업무 설치·실행, 팀원 Claude 개발 인수, 심사 입력 전체·원문 공격·baseline·반복 실행·시간/공수/토큰 효과, S01d2 청소 불편·내부 치수, 외부 시각화, 새 OS/계정 제출 ZIP 재현은 완료하지 않았다. 이 검증은 특정 PC·실행기·설정의 업무 연결 인수다.

실행 JSONL/stdout/stderr/설치 지문/질문/usage delta는 `.harness/codex-product-acceptance/`에, 결과·자료 버전·SQLite/export는 별도 제품 폴더 runtime-data에 보존하며 Git에 올리지 않는다. 설치 후 최종 파일은 source manifest·product-install 지문과 대조한다.
