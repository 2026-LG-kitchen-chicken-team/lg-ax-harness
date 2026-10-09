# 신규 자료·공통 도구 검증

2026-10-10 Windows, Python 3.12.14. 사용자 요청의 신규 데이터·입출력 기준 및 공통 도구를 작성했다. [컨설팅](../consultation/2026-10-10.md)·[공통 계약](../contracts/common-tools.md)·[작업 상태](../plans/development-harness.md)를 따른다.

## 구현 범위

- 새 실제 자료: LG S836GBB122 공식 스펙 요약4개·표시 후기 발췌3개. 출처 URL·관측일·모델 연결·표현 형태·원문 위치·발췌 지문 보존. 개별 후기 모델 구매·작성일·협찬은 미확인.
- 신규 합성 시험: 모델3개·정확한 버전 범위4개·설명서 항목12개·리뷰40개. 업무·출품 시연 근거로 사용하지 않음.
- 공통 모델 선택·필터 조회·자료 적재 무결성·근거·결과 구조·조건 검사, SQLite 요청/후보/이력·실패 포함 수정 상한·트랜잭션·조회 캐시·무효화·관측 사용량·등록된 retry 장부.
- 개발 입력2개, 합성 예외 평가18개, 실제 자료 평가3개 작성. 실제 업무 AI·평가 runner는 미실행/미구현.

## 검사와 독립 검토

실제 실행 장부: `common-tools-20261010-001`. 부모가 코드·자료를 단독 작성했고 실제 네이티브 `/root/native_runtime_decision_review`를 읽기 전용 리뷰로 배정했다. 장부가 Agent나 Tool을 실행한 것은 아니다.

| 실제 검사 | 결과 | 로컬 receipt |
|---|---|---|
| `python -m unittest discover -s tests/product-tools -v` | 43개 통과, exit0 | `.harness/checks/a1c6b098675b40258baa389e0fbbee53/receipt.json` |
| 개발 helper 회귀 suite | 22개 통과, exit0 | `.harness/checks/3d76e4551301447791ad8f4d4377b6d1/receipt.json` |
| 개발 doctor | exit0, errors=[] | `.harness/checks/87616bfff862469ebe63250215e6e122/receipt.json` |
| 실제 자료 doctor | exit0, 실제1모델/3후기/4사양·business | `.harness/checks/c7d779f417344df4bb83f015c0886532/receipt.json` |
| 모델 선택→내부 입력 | exit0, 상세 불편 입력 없이 생성 | `.harness/checks/5dd2760ded704ebebdabb0d8fbaafd86/receipt.json` |
| 실제 후기 조회 | exit0, 정확한 범위·원문·origin·지문 | `.harness/checks/5e004b5e58e246e5a7272e839bdeca94/receipt.json` |
| git diff --check | exit0 | `.harness/checks/ea412317ba884909a6a61f14777dd121/receipt.json` |

위 검사는 최신 코드·자료·계약 입력 지문과 reviewer task/attempt에 연결했다. 첫 구현의 실제41검사도 exit0였고 날짜·미관측 모델 재사용 경계 검사를 더해 현재43개다. 문서 상대 링크도 실제로 확인했다.

사전 독립 검토에서 발견한 실패 후보의 무제한 수정, 상충 기능의 첫 항목 판정, 결과 재사용 지문 누락을 수정하고 회귀 사례를 포함했다. 최종 독립 reviewer가 모든 bound receipt의 입력·로그 SHA256/binding 및 코드·계약·자료·보고 범위를 대조했고 실질 발견 없음으로 반환했다. 실제 final 응답을 관측한 뒤 idle로 기록했다. `complete --run common-tools-20261010-001`은 exit0, errors=[]였다. 이것은 로컬 구현·검사·독립 리뷰의 완료이며 아래 업무·자료 충분성의 남은 범위를 없애지 않는다.

## 한계

현재 실제 후기들은 긍정적 편의·사용 기대 위주다. 현재 제품의 청소·수납 불편이 충분히 관측되지 않아 자료 확대와 부족 근거 처리의 실제 업무 인수가 남았다. 내부 치수·선반 간격·분리/조절·제조 가능성은 미확인이다.

원문 위치·SHA·인용문 검사는 주장 의미의 통과가 아니다. semantic_status=unverified/acceptance_ready=false를 유지한다. 등록된 retry/사용량은 호출자 보고이며 실제 네이티브 Tool/모델 호출의 자동 수집·강제 통제·취소를 증명하지 않는다. user_submitted는 진술이고 인증 경계가 아니다.

실제 Codex/Claude/Gemini 업무 연결·업무 Skill·불편 추출/제안·독립 의미 검토·LLM token 절감·시간/공수 절감·원격 CI·시연·제출 완료는 모두 이번 로컬 도구 검사 범위 밖이다. 기존 LG 작업물은 사용하지 않았고 별도 유료 모델 API를 호출하지 않았다. 전체 개발 모델 사용량은 미측정으로 남긴다.
