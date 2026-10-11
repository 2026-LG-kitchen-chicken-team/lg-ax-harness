# 제품 v0.7.0 시험판 배포 검증

2026-10-12. [제품 시험판](https://github.com/2026-LG-kitchen-chicken-team/lg-ax-harness/releases/tag/product-v0.7.0)을 실제 게시하고 원격 태그·새 다운로드·체크섬·GitHub asset digest·ZIP/태그 바이트를 대조했다. [검증 JSON](product-v0.7.0.json).

| 항목 | 실제 확인 |
|---|---|
| 소스 provenance | `33001576987dfc212b09f75d016f2cd65d00ff08` |
| 제품 전용 commit | `5aa651c14f6282ec463a63ccf0fae8416ffb0060`·부모 없는 snapshot |
| 제품 tree | `b6fd93e920d9cc6c5b341dd3454b1d6b0ebf2b00` |
| ZIP | lg-ax-harness-product-v0.7.0.zip·69파일·143,193bytes |
| SHA-256 | `89eba6307a7411aefceb79868f161bcab369eeecfca29ecdf3079a751cecfae5` |
| manifest | 자기 파일 제외68개 전부 SHA 일치 |
| 원격/다운로드 | 원격 tag=제품 commit, 다운로드 SHA/체크섬/GitHub digest 일치,69파일 각각 tag와 byte 일치 |

제품만 포함한다. 업무 Agent v7.4·6Skill·공통 Tool·설치/실행 안내·빈 기본 catalog·LICENSE/NOTICE가 있으며 개발 역할/Skill·평가 질문·로그/DB·인증·개인 설정·환경은 포함하지 않는다. 새 폴더 locked 설치·doctor·Claude 사본 재설치는 exit0이며 모델 업무 검증과 구분한다. 별도 개발용 하네스와 실제 검증 보고서는 소스 레포 main에서 관리한다.

동일 제품45파일 지문은 `73ec3fc2ac5931ed70bba7785dc31ef52c24493c32b8128b16060326793697e9`다. [품질 계약](../evaluation/quality-regression-20261012.md)에 따른 **Codex10건8통과/2실패·Claude3건2통과/1실패·R06미실행1건**과 [원본 대조/실제 시간·사용량·제한](quality-regression-20261012.md)을 공개했다. 현재 원본을 과거 검증본의 전면 통과로 표시하지 않는다. 보류 진단 통과는 상품기획 완성이나 실물 효과가 아니다.

제품189·평가128·eval28개 코드 검사 exit0. fresh task-bound 최종 검사 `f6b50612cdb548b1b2dfea620a019fa2`는 동결 원본/실제 저장 지문·보고서/사용량/프로브·ZIP69파일·경계9검사·자산·Claude 사본·발표 초안 정적 검사·diff 검사 exit0이며 독립 reviewer와 개발 장부 complete가 통과했다. 실제 AI 전면 품질 인증은 아니다. 당시 receipt·원본 로그는 Git 제외하며 내부 SHA 대조 근거다.

미해결: Codex 조사 보류 답변의 최종 inline pointer 전달 오류, 신규 냉장고 조사1건420초 timeout, Claude의 후기 주변 문맥/검증 지표·일부 저장 요약 귀속 모호성. Codex를 제출 기준으로 유지하고 Claude는 제한 검증/후순위다. 실패 원본과 부분 사용량을 보존하며 backend 중단·전체 청구·비용·일반/사람 절감률·공식 가산점은 주장하지 않는다. [토큰 가산점 구현·실제 사건](token-bonus-20261012.md).

이번3항목의 구현·제한 회귀·토큰 근거 정리는 종료했다. 발표자료의 최신 수치 반영·별도 관찰 화면/영상·실측 리허설·웹팀 원본 연결·운영진 최종 규격/재현/접수는 별도다. 이 시험판은 최종 제출 접수 또는 모든 심사 항목 충족을 뜻하지 않는다.
