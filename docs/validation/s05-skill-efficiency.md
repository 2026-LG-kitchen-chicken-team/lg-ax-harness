# S05 Skill 중복 호출 정리와 제한된 실제 비교

2026-10-10. 개발용 하네스를 사용해 **출품** Agent·Skill 지침을 수정했다. 독립 모델 API·새 서브에이전트·UI를 추가하지 않았다. 원문·Tool 코드·자료·저장 계약과 최종 검사는 유지한다. 이 기록은 전체 S05·최종 제출·다른 실행 환경 인수를 완료시키지 않는다.

## 분석과 변경

기존 [J17](s05-hardening.md)의 정상 대조는 420.56초 timeout, 삽입 조건은 401.88초 성공이었다. 읽기 전용 evaluator가 완료 trace를 분석했다. 완료 명령은 각각 19/23개, 명령 stdout의 UTF-8 합계는 81,516/92,214 bytes였다. Skill/계약 읽기·조회·저장 응답의 반복을 확인했지만 이벤트별 시각이 없어 어느 Tool이 지연을 만들었는지 확정하지 못했다. 명령이 더 많았던 삽입 조건이 먼저 끝났으므로 출력량과 시간을 인과 관계로 단정하지 않는다. 기존 paired acceptance 실패를 보존한다.

- Agent `product-planning-v5.1`: 저장 자료로 충분하거나 외부 조회가 금지된 첫 요청은 `open_request_bundle`로 준비·시작·원문 조회를 합친다. 외부 조사 필요성을 먼저 판단해야 하면 turn 전에 필요한 범위만 조회한다.
- `evidence-retrieval`, `needs-structuring`, `feature-comparison`: 정확한 scope·버전·위치·지문·원문을 이미 받았으면 사용한다. 누락/잘림·새 사실·버전 변경·범위 모호성에는 필요한 조회를 수행한다. 긍정·상충 자료와 원문 의미 대조를 생략하지 않는다.
- `concept-writing`: 전체 업무의 최종 `save_reviewed_result`에 구조·출처·제약 검사를 연결한다. 단독 Skill·진단·최종 저장 없는 작업은 해당 검사를 실제 실행한다. 중간 후보를 검증 완료로 표시하지 않는다.
- 상세 계약은 불명확한 필드/의미나 오류 진단에 읽는다. 이미 읽은 계약을 습관적으로 검색·전체 읽기하지 않는다. 짧은 저장 양식과 최종 assessment·저장/export는 유지한다.

독립 source 리뷰에서 turn 시작 뒤 새 자료를 등록하면 원래 turn이 무효화돼 보류도 저장하지 못할 수 있다는 결함을 발견했다. 최종 v5.1은 기존 `--data`/자료 버전으로 `held`와 사유를 저장·export하고 실제 추가 입력을 기다린다. **그 입력이 도착한 뒤, 새 turn 시작 전에** 자료를 등록/반영한다. 오래된 turn·실패 이력·수정 한도를 초기화하지 않는다. Agent와 조회 Skill의 일치를 재검토했다. 이 외부 조사 분기는 이번 native 사례에서 실행하지 않았다.

## 실제 native 비교 범위

동일한 실제 입력 S05-R01(B502S33 수납 개선, 하드웨어 추가 금지, 개선안 2개 이내 요청)을 기존 v4와 수정 v5에 각각 1회 넣었다. 실제 제안은 각 1개였다. 기존 원본은 commit `73b1dbc0aed563dd269b87984eb6d64e3eb0b5e8`에서 동결했다. 서로 다른 새 설치·DB·세션에서 동일 데이터·동일 질문/중립 출력 계약을 사용했다. rubric·기대 답·개발 평가 코드는 제품 설치에 넣지 않았다. 외부 웹/API/다른 자료는 금지했고 실제 저장·export를 요구했다.

모델은 설정 상속으로 관측된 `gpt-6.1-sol`, reasoning `ultra`, Codex 0.162.0/Windows 전체 접근 모드였다. 두 조건은 병렬로 실행했고 환경 전역 설정·캐시는 초기화하지 않았다. native 입력 상한 2회, 조건별 420초, 자동 재실행 없음이었다. `--disable multi_agent`와 직접 수행 지시를 적용했으며 실제 위임 여부는 trace에서 따로 검토한다.

| 관측 항목 | 기존 v4 | 수정 v5 |
|---|---:|---:|
| CLI 종료 / 업무 상태 | exit 0 / completed | exit 0 / completed |
| 경과 시간 | 388.67초 | 322.31초 |
| 완료 명령 | 18 | 13 |
| 명령 stdout UTF-8 합계 | 64,795 bytes | 51,272 bytes |
| 세션 관측 입력 토큰 | 401,575 | 216,694 |
| 그중 cached input | 355,840 | 181,632 |
| input − cached input | 45,735 | 35,062 |
| 관측 출력 토큰 | 14,776 | 13,647 |
| 그중 reasoning output | 3,789 | 2,790 |
| 저장 후보 / 출력·저장 일치 | 1 / 일치 | 1 / 일치 |
| 결과가 실제 사용한 출처 | 4 | 6 |
| 구조·출처 위치/지문 검사 | 통과 | 통과 |
| 전체 backend 호출/청구·사람 공수 | 미측정 | 미측정 |

입력 관측은 이 1쌍에서 46.04%, input−cache는 23.34%, 시간은 17.07% 감소했다. stdout byte 합계는 전체 문맥 크기나 네트워크 전송량이 아니다. token-count 이벤트 12/7개는 backend 호출 수가 아니다. reasoning 토큰은 출력에 다시 더하지 않는다. 최종 usage_summary의 `unknown`을 세션 관측으로 덮어쓰지 않는다.

독립 원문 의미 검토는 아래에 기록한다. 구조 검사 도구의 `semantic_status=unverified`, `acceptance_ready=false`와 모델 자기보고 `supported`는 품질 합격 근거가 아니다. 한 알려진 질문의 1회 비교이고 일반 프롬프트 baseline·미사용 평가·반복 측정이 없으므로 비용 절감·일반적 속도/품질 우위·시간/공수 효과는 미입증이다.

명령 감소 5회는 계약 읽기/검색 3회와 선행 validation 2회가 없어졌다는 관측과 일치했다. 계약 stdout은 17,069→0 bytes지만 Skill stdout은 9,680→11,270 bytes, 저장 반환은 13,935→15,769 bytes로 늘었다. 단계별 시간은 없어 경과 시간 감소를 이 변경만의 효과로 확정하지 않는다. rollout에서 위임 호출은 확인되지 않았으나 옵션에 의한 권한 차단 증명은 아니다.

### 실행 원본과 최종 소스의 차이

native 수정 조건은 **v5 동결 원본**이다. 실행 중 독립 리뷰로 v5.1의 외부 조사/보류 가드를 보완했고, v5.1은 정적 리뷰·기존 코드 검사·ZIP 재현으로 검증했다. 이번 v5 결과를 v5.1 모든 분기의 native 통과로 표시하지 않는다. 추가 모델 입력은 실행하지 않았다.

- 데이터 지문: `625fb0712490a092e465cb26a53c05742d9dd3809f261c4db56a1fa3ed91c66b`.
- 논리 질문 지문: `64747578242585c18ab80dde248c548be773e66a0898dcc9b0faca46f8fde85d`.
- native v5 Agent SHA: `a9b6a7d6db17931feac98d4d537b99ae54b221e3cde5fd755b79b7fee8fa0046`.
- 최종 v5.1 Agent SHA: `2dd4c2984496e8d70777a956c4539cf4a45d0d646a7638bdd1fbf6364d5f2c34`.
- 최종 Skill manifest SHA: `344229877417b464f778586abc3a7dcaf2b4ad14e8d3f31d47f054cd8054a69d`.

원문 trace·질문 파일·final·DB·출력 전체는 Git 제외인 `.harness/s05-skill-efficiency-20261010` 및 새 Temp 설치에 보존했다. native 실행 receipt `5842556a52e74ceda32da0dd29e8962a`는 v5 입력의 당시 결과이며 v5.1의 fresh receipt로 재사용하지 않는다. 원본 해시·같은 설정/데이터/질문·실제 저장·추출 JSON·출처 구조를 재검사한 audit는 모델 호출 없이 수행했다.

## 실제 검사

아래 receipt는 `.harness/checks/ID/receipt.json`에 있으며 실제 명령·시각·exit code·입력·로그 지문을 담는다. 공개 저장소에 원문 실행 로그를 올리지 않는다.

| 실제 명령 | 결과 | receipt ID |
|---|---|---|
| `python -m unittest discover -s tests/product-tools -v` | 97개, exit 0 | `59b8d96f73d54de8bfa3a71a64061e21` |
| `python -m unittest discover -s tests/evaluation -v` | 29개, exit 0 | `9f987a94f0ed444295359bc2b4863c6c` |
| `python scripts/check-product-assets.py` | 최종 v5.1·manifest, exit 0 | `631256fbb5224b9b80af62dba4dd0246` |
| `python .harness/run-skill-efficiency.py` | 실제 2회·구조/저장 일치, exit 0; v5 | `5842556a52e74ceda32da0dd29e8962a` |
| `python .harness/audit-skill-efficiency.py` | 원본 hash·구조/저장 재대조, exit 0 | `e048edc9f15b42ceaa5887bbace7b2b3` |
| `python .harness/prepare-product-release.py` | 최종 v5.1 ZIP 70파일·새 폴더 8명령, exit 0 | `91b9a9fbcd4e4819ad57e911326153a4` |

audit의 첫 호출은 디렉터리를 `--input`에 넣어 실행 전 거부됐고 exit 1이었다. 개별 파일로 수정해 위 실제 검사를 수행했다. 실패를 제품 실행 성공에 합산하지 않는다.

최종 배포 감사의 첫 실행은 설치 `.gitignore`를 개발 레포의 같은 이름 파일과 비교해 exit 1이었다. 설치 manifest가 지정한 제품 템플릿 원본·변환 정보를 기준으로 비교하도록 감사 코드를 수정했다. 제품 파일 결함으로 판정하거나 기존 실패 영수증을 덮어쓰지 않았다.

ZIP은 `lg-ax-harness-product-v0.1.0.zip`, SHA-256 `b5534ab54ef5213cf9f9adeb3d05f2909910c31c1a83f572a88dac1bba4b24bc`다. manifest 목록·파일별 SHA·자료 디렉터리의 정확한 3파일을 대조했다. 개발 체계·평가·팀 기록·원문 로그·DB·인증·의존 환경을 제외했다. 새 추출 환경의 `uv sync --locked`/doctor, 그 ZIP에서 새 Claude·Gemini 사본 설치/sync/doctor 8명령 모두 exit 0이다. Claude/Gemini native 업무 인수는 미실행이다.

## 독립 검토와 릴리스 상태

출품 Agent/Skill source 리뷰의 자료 변경/보류 결함은 수정 후 재검토로 해소했다. 별도 읽기 전용 evaluator가 두 실제 답변을 정확한 모델의 저장 원문 6건과 대조했고 **중대 의미 결함을 발견하지 못했다**. 냉동실 협소 체감과 같은 후기의 2인 사용 수용을 함께 보존하고, 현재 긍정을 불편으로 바꾸거나 다른 수납부 기능을 냉동실 해결로 해석하지 않았다. 기록·입고·소진 안내는 제안이며 과잉 구매·누락·효과를 관측 사실로 단정하지 않았다. 새 부품·제빙기 탈착·내부 치수를 요구하지 않았다. 기존 동일 안내 존재 여부·시장 신규성은 미확인이다. 출처 4/6건의 위치·SHA·origin·quote와 저장/출력을 대조했다. `exclude_pains=[]`이므로 제외불편 해석은 이번 사례의 검증 범위가 아니다.

리뷰의 최초 JSON-only 결함 지적은 실제 prompt/helper 103행 대조 후 철회했다. 계약은 한국어 설명과 JSON 객체를 **포함**하는 형태를 허용한다. 검사는 전체 답변을 기계용 JSON으로 파싱한 것이 아니라 그 안의 `{result,assessment}`를 추출해 대조한 범위다. 계약 밖 요건을 추가하지 않는다. source/실제 의미 리뷰 모두 파일 수정·추가 native/API 입력 없이 수행했다.

현재는 발행 전 검증 원본이며 [릴리스 계약](../contracts/product-release.md)에 따라 제품 ZIP과 SHA 목록만 `product-v0.1.0` prerelease 후보로 준비했다. 실제 발행/다운로드 검증은 후속 기록에 연결한다. 발표·영상·최종 제출 완료를 표시하지 않는다.

다음 우선순위는 팀 개별 보고서 접수/환경별 실제 인수, v5.1 자료 부족/외부 조사 상태 연결의 native 검증, J17 정상 대조 timeout과 반환 원문 공격의 paired 재검증, 제한된 반복·미사용 평가다. 사람 공수·전체 청구·시장 신규성·청소 근거/내부 치수·발표/영상은 계속 미완료다.
