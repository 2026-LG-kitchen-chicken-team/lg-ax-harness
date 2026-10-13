# 상위 모델을 포함한 J2 비교 마감

이 비교 단계는 종료했다. 세 제품군 공통 모델/추론 권장 기준은 미충족이며 이전 H/I 점수를 현재 J2로 합산하지 않는다. [실측 JSON](recommendation-J-progress-20261013.json)·[고정 비교 계획](../evaluation/recommendation-J-20261013.md)을 따른다.

J2 소스 `d88262b0381b42b6a6925adee72af7b0d4c098effab56a3be5f02e4e699f811e`. 실제 입력 26/32·이전45 보존·누적71·자동 재전송0. 현재 native 결과 26·독립 의미 검토 23건이다. 업무 동시1 순차 실행으로 자료 폭을 유지한다.

| 조합/사례 | 실제 최종 전달 기준(초) | 적용 품질 점수 | 핵심 Moderate | 상태 |
|---|---:|---:|---:|---|
| J_C61M_MW_s1 gpt-6.1-sol / medium | 608.828 | 13/14 | 1 | 의미 gate 미충족 |
| J_AM_MW_s1 gpt-6-astra / medium | 579.813 | 13/14 | 1 | 의미 gate 미충족 |
| J_LH_MW_s1 gpt-6-luna / high | 296.985 | 12/14 | 1 | 의미 gate 미충족 |
| J_C61H_MW_s1 gpt-6.1-sol / high | 693.422 | 13/14 | 1 | 의미 gate 미충족 |
| J_C56M_MW_s1 gpt-5.6-sol / medium | 736.859 | 12/14 | 2 | 의미 gate 미충족 |
| J_AL_MW_s1 gpt-6-astra / low | 521.768 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_OPM_MW_s1 ['claude-opus-5-5'] / 중간(GUI;backend unknown) | 389.697 | 12/14 | 2 | 의미 gate 미충족 |
| J_C60M_MW_s1 gpt-6-sol / medium | 354.165 | 13/14 | 1 | 의미 gate 미충족 |
| J_OPH_MW_s1 ['claude-opus-5-5'] / 높음(GUI;backend unknown) | 435.583 | 12/14 | 2 | 의미 gate 미충족 |
| J_C61L_MW_s1 gpt-6.1-sol / low | 332.557 | 13/14 | 1 | 의미 gate 미충족 |
| J_FM_MW_s1 ['claude-fable-5-1'] / 중간(GUI;backend unknown) | 631.076 | 11/14 | 4 | 의미 gate 미충족 |
| J_AL_FR_c1 gpt-6-astra / low | 446.384 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_SM_MW_s1 ['claude-sonnet-5-5'] / 중간(GUI;backend unknown) | 251.475 | 10/14 | 3 | 의미 gate 미충족; 표준 종료 미충족 |
| J_AL_DW_c1 gpt-6-astra / low | 564.185 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_SH_MW_s1 ['claude-sonnet-5-5'] / 높음(GUI;backend unknown) | 565.533 | 13/14 | 1 | 의미 gate 미충족 |
| J_AL_MW_c2 gpt-6-astra / low | 517.234 | 13/14 | 1 | 의미 gate 미충족 |
| J_AL_FR_c2 gpt-6-astra / low | 402.265 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_AMBIGUOUS_FR gpt-6-astra / low | 238.579 | 10/10 (보류/미해결) | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_CANCEL_MW_p2 gpt-6-astra / low | 85.219 | 미판정 | 미판정 | 일반 품질 점수 적용 안 함 |
| J_ROLE_A_MW gpt-6.1-sol / medium | 30.594 | 미판정 | 미판정 | 일반 품질 점수 적용 안 함; 업무 실행 불가 |
| J_ROLE_B_MW gpt-6.1-sol / medium | 38.781 | 미판정 | 미판정 | 일반 품질 점수 적용 안 함; 업무 실행 불가 |
| J_FOLLOWUP_MW gpt-6-astra / low | 73.015 | 12/12 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_ROLE_YA_MW gpt-6.1-sol / medium | 585.343 | 13/14 | 1 | 의미 gate 미충족 |
| J_ROLE_YB_MW gpt-6.1-sol / medium | 457.531 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_RETAINED_MW_p2 gpt-6-astra / low | 812.406 | 14/14 | 0 | 해당 사례 의미 통과·공통 권장 미충족 |
| J_LIVE_MW gpt-6-astra / low | 1311.218 | 13/14 | 1 | 의미 gate 미충족 |

시간은 Codex에서 process/collector 종료, Claude GUI에서 실제 main user→assistant end_turn이다. GUI process exit는 미관측이며 두 끝점 차이를 유지한다. 각1회 결과로 effort 인과 효과·최적값·통계적 우위를 확정하지 않는다. Sonnet 중간은 workflow0·finish0·export1을 최종에 명시했으며 요청한 표준 종료를 수행한 시간과 동등 비교하지 않는다. 실제 runtime-data 기준 링크2는 존재하며 UI 클릭은 미실행이다.

범위는 냉장고28(후기22+사실6), 전자레인지48(후기40+사실8), 식기세척기36(후기30+사실6)이고 전체 catalog112를 보존했다. 전체 등록본문 전달과 고객/시장 대표성은 별개다. 기본 배포 catalog는empty다.

현재 여러 모델에서 원문 미명시 속성을 직접 사실로 강화하거나 비교/사용시점·기능존재와 실제 해소를 섞는 문제가 남았다. 모델을 높이거나 빠른 실패를 선택하는 것으로 품질을 통과시키지 않는다. 원문·저장·최종 의미와 종료 export를 독립 대조했다. 선택 검토자 실제 이점은 미입증이다.

현재 코드393·평가144·자산 exit0, 독립 코드 인수와 실제 사례별 종료 export/finish 정합을 확인한 범위는 JSON에 적었다. Luna 최종 `/C:/` 링크의 literal 경로 오류·UI 클릭 not_run을 보존한다. 코드/구조 통과는 의미 품질·HTML 화면·영상/발표 완성이 아니다.

보존 원문 재등록은 별도 superseded9c 소스에서115/115·전달115·caller-reviewed0으로 완료했다. 이후 J2의 별도 보존 자료 분석은 후기110+사실5 전체115 전달·현재 저장/웹/finish/종료export를 수행했고 812.406초·독립14/14였다. 후기110은 페이지107과 같은 블로그3발췌를 포함하며 독립 고객110명이 아니다. 새 live 조사·고정112 모델속도·시장대표성·실물효과로 합산하지 않는다.

발표+녹화 영상+전환은600초, 실제 업무 수행시간과 편집 길이를 구분한다. [녹화 시연 계획](../plans/recorded-demo-600-20261013.md)은 제작 계획이며 실제 영상/삽입/리허설/접수는 미완료다.

## 최종 추가 조사·역할 판정

이번 단계는26/32입력·누적71·자동재발송0으로 종료했고 남은6은 미사용이다. 전 제품군 공통 권장 gate는 미충족이다. 정상 품질 검토, 자료 부족 처리, 취소와 실행 환경 거절을 단일 성공률로 합산하지 않는다.

새 live39건의 catalog→DB→웹→최종export/current v1·본문SHA39/39는 일치했다. source53·보호84·기본empty3도 실제 SHA가 같다. 새 자료를 등록하는 시험의 `data_files_unchanged=None`은 해당 고정자료 비교의 적용 한계이며 코드·기본catalog 변조가 아니다. 실제15후기 관측단위19발췌+공식사실20/18,572자를 확보했다. LG 표시996건·GS 표시11명 전체 확보나 시장 대표성은 아니다. native웹 호출17개·보존blob15개 중13개 전체bytes가 실제 출력과 일치했고 나머지2개는 로그 잘림으로 전체bytes 인증이 제한된다. source_literal27개 SHA/위치/본문/원URL/시각은 모두 대조했다.

workflow1243.396초, 최종전달1310.359초, process종료1311.218초를 구분한다. live독립13/14의 핵심 누락은 기획 검증 계획의 전체 사전배정 시도 분모와 실패·중단·미확인 처리다. 별도P2는 실패4건의 잘못된 HTTP 보조 링크 귀속이며 실제 실패 literal은 정확히 보존됐다. HTTP오류 반환21개는 실패 사이트21곳이나 완전 복구를 뜻하지 않는다.

선택 검토자는 actual spawn/interrupt 확인·반환0·미완료다. 부모 A13/B14·585.343/457.531초의 단일 비교와 자식 없이 바뀐 판단만으로 검토 이점·시간/토큰 절감을 주장하지 않는다. parent 입력 관측은 B가 더 크고 자식/전체backend 사용량은unknown이다. 후속은 원상태52파일을 유지한 설명 처리, 취소는 코드로 만든 대기 turn의 저장 차단 범위이며 실제 진행 중 backend 취소 인증은 아니다.
