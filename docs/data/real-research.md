# 실제 근거 확대와 확인 한계

2026-10-10. 이전 LG 작업물 없이 공개 원문을 새로 조회했다. 업무 snapshot은 data/business/lg-research-v3, 재생성은 scripts/create-real-research.py다. 원문 snapshot 재현용 상수이며 스크래퍼가 아니다. 실제3모델·후기6발췌·공식 사실19개를 저장했다. 검토용 합성 자료는 업무 근거로 사용하지 않는다.

| 모델 | 실제 관측 불편/의견 | 정확한 제품 기능·구조 |
|---|---|---|
| S836GBB122 | 기존3개 긍정·편의/기대 의견. 현재 수납·청소 불편은 확보 못함 | 무빙도어 제빙기 탈부착, 야채실, 상부 조명 추가 확인 |
| B502S33 | 공식페이지 샤인 옵션 표시 후기에서 냉동실 수납 아쉬움과2인 사용 수용을 함께 확인. 다른 후기의 긍정 의견도 보존 | 외형780×1800×730mm,507L(냉장376·냉동131),유리선반·야채실·트위스트 제빙기 |
| T876MQQ012 | 모델명을 명시한 직접 발행 후기의 현재 적재 상태에서 중·하단 그림자 체감 | 4도어 상냉장/하냉동,870L(503·367),외형914×1787×918mm,상부 조명·접이선반1단·유리선반4·야채실2 |

주 출처: [S836GBB122](https://www.lge.co.kr/product/refrigerators/s836gbb122?modelId=MD10559848&pdpType=PURCHASE), [B502S33](https://www.lge.co.kr/product/refrigerators/b502s33?modelId=MD09091859&pdpType=PURCHASE), [T876MQQ012](https://www.lge.co.kr/product/refrigerators/t876mqq012?modelId=MD10681860&pdpType=PURCHASE), [T876MQQ012 직접 발행 후기](https://min-inter.co.kr/wiki/lg-dios-t876mqq012-refrigerator-purchase/). AI 리뷰 요약은 고객 원문으로 적재하지 않았다. 후기 전체 복제 없이 작은 발췌와 사실 요약을 사용한다.

공식페이지의 표시 후기와 실제 개별 구매/제조 버전 검증은 다르다. 구매 인증·협찬·정확한 후기 ID와 게시일은 확인된 항목 외에는 null이다. 블로그의 explicit_model_verified는 글에 정확한 모델명이 있음만 뜻하고 영수증·협찬 부재를 증명하지 않는다. 한 사례를 전체 사용자 불편율·제품 결함으로 일반화하지 않는다.

## 공식 설명서 대조

조사 Agent가 T876MQQ012 PDP 고객지원의 실제 브라우저 DOM에서 지원 코드 GC-B31FFX9Q.AQQGKRB, 게시일2025-09-22와 [LG 공식 PDF](https://gscs-b2c.lge.com/open/downloadFile?fileId=LuQhmLf8ZMxg8pHShCqA)를 확인했다. 부모의 web fetch는 timeout이었고, HTTPS 파일 다운로드는 성공했다. 36쪽 설명서 MFL71401547 Rev.03_091025를 읽고17·19쪽을 Poppler로 렌더링해 도해·주의문을 직접 확인했다.

16~19쪽의 서랍/접이식 선반/선반 높이 홈/바구니/내부 청소 절차를 대조해3개의 사실 요약을 등록했다. 적용 모델 한정 기능·부품 형태 주의를 보존하고, 노크온 같은 미적용 기능은 해당 모델에 옮기지 않았다. 내부 선반 수치·조절 간격·최소 분리 개방각은 확인 못했다. 공통 스펙 snapshot 범위에 연결된 문서 묶음으로 다루며 실제 설명서 번호/개정은 각 source.location에 남긴다.

PDF 전체와 렌더 이미지는 runtime-data에만 보관하며 Git 제외다. source.sha256는 적재한 발췌/사실 요약의 지문이며 전체 웹페이지·PDF 원본 지문과 다르다.

## 제외와 남은 범위

타이밍 B502S33 제목의 리뷰 미러에는 화이트/B502W33 옵션이 섞여 있었다. 그곳의90도 선반 분리·청소 불편을 B502S33 근거로 넣지 않았다. 쿠팡 링크에서 원래 해당 후기까지 확인하지 못했다. S836GBB122 전체 리뷰 목록도 브라우저 클릭만으로 표시를 확인하지 못했다. 조회 실패·미확인은 성공으로 바꾸지 않는다.

실제 수납/찾기 불편을 사용하는 소규모 업무 범위는 확보했다. **현재 모델의 청소 불편 원문·내부 mm/선반 간격·시장성·개선 시간/공수/토큰 절감은 여전히 미확인/미측정**이다. 따라서 S01d 전체를 완료로 표시하지 않는다. 외형 치수만으로 배치가 가능한 하드웨어 설계를 확정하지 않는다.

확인한 원본 PDF SHA256: `daf2eedaa91956b0e1e88b2ce70377f710e508600fcc6080bf3e88d6d641ed6d`. 표지·17·19쪽을 시각 확인했다.

독립 사용 점검에서 글의 제휴 수수료 고지를 확인해 v3의 commercial_disclosure로 보존했다. 제품 제공·협찬 여부는 null로 구분한다. v2는 초기 관측 이력으로 보존하며 덮어쓰지 않는다.

## B502S33 공식 청소 절차 추가 — 2026-10-11 KST

부모가 실제 Chrome의 B502S33 정확 PDP 고객지원에서 바로보기 링크를 읽고 [HTML 설명서 내부 청소](https://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html#topic_31)를 확인했다. DOM href는 `http://gscs-manual.lge.com/CNZ/MFL69140202/ko-kr/main.html`이며 원문 그대로 보존했다. 설명서는 HTTPS로 관측했으며, 코드가 동일 host·경로만 연결하고 수집·TLS 기준을 완화하지 않는지 회귀·독립 리뷰했다. 문서 버전은 MFL69140202/18이다. PDP의2024-10-04/2024-07-15는 표시 등록일이고 문서 발행일·제조 버전으로 확정하지 않는다.

실제 원문은 식품을 꺼낸 뒤 구성품을 분리하고, 선반·문 바구니·고무 패킹을 물 묻힌 부드러운 수건으로 닦고, 물기를 완전히 제거하도록 안내한다. `capture_web_page`2회→`import_web_evidence`1회로 Git 제외 `runtime-data/catalogs/lg-browser-b502-clean-20261010-v1`에 source `OBS-B502S33-MANUAL-CLEAN-20261010`1개를 추가했다. 원본 v3는 변경하지 않았다. 연결 snapshot `738263a3efcebc1017f95faf1ef0619e053423ed184ed67afba15d2ab9a8b358`, 설명서 snapshot `f0f45540b2844a5b15713694db0a7a26ba8ed55d824615fec042cbf995aca220`을 보존했다.

공용 문서의 model_matching은 product_page_association이다. 코드 import는 structural_valid=true/semantic_status=unverified/acceptance_ready=false다. 이는 **부모 브라우저 관측·일반 코드 등록**이며 출품 AI가 조사 Skill을 선택해 처리한 native 실행과는 별도다. source의 청소 절차가 실제 청소 불편·내부 usable mm·선반 간격·청소 시간 절감·고객 모집단을 입증하지 않는다. 이번 추가에서 그런 새 근거는0개이며 S01d2의 충분성은 미완료다.
