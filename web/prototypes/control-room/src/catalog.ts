export interface HarnessNode {
  id: string;
  kind: "core" | "agent" | "skill";
  label: string;
  subtitle: string;
  color: string;
  description: string;
}

/** Exact product-v0.10.0 inventory, not evidence that any role was invoked. */
export const nodes: HarnessNode[] = [
  {
    id: "main",
    kind: "core",
    label: "MAIN",
    subtitle: "Product orchestrator",
    color: "#ff496d",
    description:
      "상품기획 메인. 원문 검증·등록, 조사 통합, 후보 검토와 저장을 담당합니다.",
  },
  {
    id: "product_official_researcher",
    kind: "agent",
    label: "OFFICIAL",
    subtitle: "Official researcher",
    color: "#61d5ff",
    description:
      "선택적 공식 자료 조사자. 모델 귀속, 사양·설명서, 사용 조건을 읽고 반환합니다.",
  },
  {
    id: "product_review_researcher",
    kind: "agent",
    label: "REVIEWS",
    subtitle: "Review researcher",
    color: "#a992ff",
    description:
      "선택적 후기 조사분석자. 긍정·불편·장기 사용·조건·반례를 원문에 연결합니다.",
  },
  {
    id: "product_evidence_reviewer",
    kind: "agent",
    label: "REVIEWER",
    subtitle: "Evidence reviewer",
    color: "#f5bf76",
    description:
      "선택적 독립 근거 검토자. 불변 후보 packet을 대조하고 메인에 검토 결과를 반환합니다.",
  },
  {
    id: "evidence-retrieval",
    kind: "skill",
    label: "RETRIEVE",
    subtitle: "Evidence retrieval",
    color: "#5ce1ca",
    description:
      "선택된 정확 모델의 등록 원문 조회, 전달·검토 이력과 coverage를 확인합니다.",
  },
  {
    id: "web-evidence-collection",
    kind: "skill",
    label: "COLLECT",
    subtitle: "Web evidence collection",
    color: "#5aaef7",
    description:
      "외부에서 실제 원문을 확보하고 부모가 검증한 원문을 등록합니다.",
  },
  {
    id: "needs-structuring",
    kind: "skill",
    label: "NEEDS",
    subtitle: "Needs structuring",
    color: "#a18bfa",
    description:
      "실제 후기의 불편·사용 맥락·상충 의견을 근거에 연결해 구조화합니다.",
  },
  {
    id: "feature-comparison",
    kind: "skill",
    label: "COMPARE",
    subtitle: "Feature comparison",
    color: "#ef9aca",
    description: "확인된 불편을 정확 모델의 기존 기능·사용 조건과 대조합니다.",
  },
  {
    id: "concept-writing",
    kind: "skill",
    label: "CONCEPT",
    subtitle: "Concept writing",
    color: "#f5c476",
    description:
      "근거와 기존 기능 대조를 바탕으로 제약을 지키는 상품기획 콘셉트를 작성합니다.",
  },
  {
    id: "review-and-revise",
    kind: "skill",
    label: "REVISE",
    subtitle: "Review and revise",
    color: "#f08081",
    description:
      "후보의 원문 의미·귀속·중복·제약을 검토하고 최초 생성·최대 2회 수정을 저장합니다.",
  },
];
