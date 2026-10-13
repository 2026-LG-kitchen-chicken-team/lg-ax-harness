import { nodes } from "./catalog";

export interface TraceEvent {
  id: string;
  /** Seconds from first observed timestamp. Untimed metadata stays at zero. */
  at: number;
  kind: string;
  source: string;
  target: string;
  label: string;
  detail: string;
  status: "active" | "done" | "held" | "error" | "idle";
  raw?: unknown;
}

export interface HarnessTrace {
  mode: "demo" | "recorded";
  title: string;
  sessionId: string | null;
  duration: number;
  events: TraceEvent[];
  warnings: string[];
  metrics: { evidence: number | null; tokens: number | null };
}

/** Directed animation score. It is not a recorded business run. */
export function createDemoTrace(): HarnessTrace {
  const events: TraceEvent[] = [];
  const add = (
    at: number,
    kind: string,
    source: string,
    target: string,
    label: string,
    detail: string,
    status: TraceEvent["status"] = "active",
  ) => {
    events.push({
      id: `demo-${events.length + 1}`,
      at,
      kind,
      source,
      target,
      label,
      detail,
      status,
    });
  };
  add(
    0,
    "request",
    "main",
    "main",
    "새 상품기획 요청",
    "합성 시연: 정확 모델과 조사 범위를 고정합니다.",
  );
  add(
    3,
    "skill",
    "main",
    "evidence-retrieval",
    "조사 범위 고정",
    "open_product_workflow · 원질문, 전체 제품 범위, 최초 deadline",
  );
  add(
    7,
    "skill",
    "main",
    "evidence-retrieval",
    "조사 계획 준비",
    "실제 실행 시 제품전반·긍정·부정·장기사용·조건·반례를 조사합니다.",
    "done",
  );
  add(
    11,
    "delegate",
    "main",
    "product_official_researcher",
    "공식 자료 조사 위임",
    "합성 위임: 정확 모델·원문 범위·지문·deadline을 전달합니다.",
  );
  add(
    12.2,
    "delegate",
    "main",
    "product_review_researcher",
    "후기 분석 병렬 위임",
    "합성 위임: 같은 catalog에서 후기 맥락과 상충 의견을 독립 조사합니다.",
  );
  add(
    16,
    "skill",
    "main",
    "web-evidence-collection",
    "원문 확보",
    "부모가 관측 원문의 URL·모델 귀속·full/partial·보존 위치를 확인합니다.",
  );
  add(
    22,
    "collect",
    "main",
    "web-evidence-collection",
    "원문 지문 검증",
    "부모만 검증·등록합니다. 자식 source_id 신고는 delivery gate를 대신하지 않습니다.",
    "done",
  );
  add(
    25,
    "role_done",
    "main",
    "product_official_researcher",
    "공식 조사 반환 준비",
    "합성 반환: 공식 사실·사용 조건·미확인 범위를 구분합니다.",
    "done",
  );
  add(
    26,
    "reply",
    "product_official_researcher",
    "main",
    "공식 근거 수신",
    "합성 메시지: 원문 사실과 AI 해석을 분리하고 부모가 다시 대조합니다.",
  );
  add(
    29,
    "role_done",
    "main",
    "product_review_researcher",
    "후기 분석 반환 준비",
    "합성 반환: 긍정·불편·조건·반례·미검토 범위를 명시합니다.",
    "done",
  );
  add(
    30,
    "reply",
    "product_review_researcher",
    "main",
    "후기 맥락 수신",
    "합성 메시지: 부모가 원문을 직접 검증하고 분석 범위를 통합합니다.",
  );
  add(
    32,
    "skill",
    "main",
    "evidence-retrieval",
    "등록 원문 전량 전달",
    "read_evidence_batch · 기록된 원문 전달과 검토/제외 scope를 대조합니다.",
  );
  add(
    35,
    "skill",
    "main",
    "evidence-retrieval",
    "근거 coverage 대조",
    "원문 항목 수와 고객 수·자료 충분성을 구분합니다.",
    "done",
  );
  add(
    36,
    "skill",
    "main",
    "needs-structuring",
    "사용 맥락 구조화",
    "원문 근거에 연결한 불편, 조건, 상충 의견을 구조화합니다.",
  );
  add(
    40,
    "skill",
    "main",
    "needs-structuring",
    "Needs map 준비",
    "합성 시연: 같은 불편도 사용 조건에 따라 다른 해석을 남깁니다.",
    "done",
  );
  add(
    41,
    "skill",
    "main",
    "feature-comparison",
    "기존 기능과 대조",
    "정확 모델의 기존 기능과 남은 불편을 비교합니다.",
  );
  add(
    44,
    "skill",
    "main",
    "feature-comparison",
    "기능 중복 점검",
    "제조사 문구, AI 해석, 추가 기획 가설을 구분합니다.",
    "done",
  );
  add(
    45,
    "skill",
    "main",
    "concept-writing",
    "첫 콘셉트 작성",
    "원문·모델·제약에 연결한 최초 후보를 작성합니다.",
  );
  add(
    48,
    "skill",
    "main",
    "concept-writing",
    "후보 packet 준비",
    "합성 시연: 변경할 수 없는 후보·원문·지문을 검토자에게 전달할 준비를 합니다.",
    "done",
  );
  add(
    49,
    "delegate",
    "main",
    "product_evidence_reviewer",
    "독립 근거 검토",
    "합성 위임: 중요한 귀속·상충·기존 기능 중복을 독립 대조합니다.",
  );
  add(
    54,
    "role_done",
    "main",
    "product_evidence_reviewer",
    "검토 의견 반환 준비",
    "합성 검토: 과한 효과 단정과 조건 누락을 지적합니다.",
    "done",
  );
  add(
    55,
    "reply",
    "product_evidence_reviewer",
    "main",
    "수정 필요 의견 수신",
    "합성 메시지: 후기 조건을 넘어선 효과 주장은 현재 후보에서 수정해야 합니다.",
    "held",
  );
  add(
    57,
    "gate",
    "main",
    "review-and-revise",
    "DELIVERY GATE · HELD",
    "검토 지적을 반영하기 전에는 완료로 전달하지 않습니다.",
    "held",
  );
  add(
    60,
    "revision",
    "main",
    "review-and-revise",
    "동일 turn에서 수정",
    "합성 시연: 같은 요청·최초 deadline·원문 scope 안에서 revision 1을 작성합니다.",
  );
  add(
    65,
    "skill",
    "main",
    "concept-writing",
    "조건부 표현 반영",
    "확인되지 않은 효과 단정은 제거하고 기획 가설·검증 필요 조건을 명시합니다.",
  );
  add(
    68,
    "skill",
    "main",
    "concept-writing",
    "수정 콘셉트 반환",
    "합성 시연: 원문에 맞춰 한계를 보존한 후보를 메인으로 반환합니다.",
    "done",
  );
  add(
    71,
    "review",
    "main",
    "review-and-revise",
    "현재 버전 재검토",
    "원문 의미·모델·중복·제약과 전량 전달/검토 이력을 대조합니다.",
  );
  add(
    75,
    "save",
    "main",
    "review-and-revise",
    "검토한 후보 저장",
    "save_and_export · 저장된 현재 버전과 웹 전달 데이터의 지문을 맞춥니다.",
    "done",
  );
  add(
    78,
    "reply",
    "review-and-revise",
    "main",
    "저장 receipt 수신",
    "합성 receipt: 실제 시스템에서는 accepted·valid·현재 버전·web_ready를 확인합니다.",
  );
  add(
    82,
    "complete",
    "main",
    "main",
    "전달 데이터 준비",
    "합성 연출 완료. 실제 업무 성공·native 종료·HTML 검수는 이 시연으로 인증하지 않습니다.",
    "done",
  );
  return {
    mode: "demo",
    title: "상품기획 에이전트 · 시각 연출 데모",
    sessionId: null,
    duration: 84,
    events,
    warnings: [
      "합성 시나리오입니다. 84초는 화면 연출 길이이며 실제 업무 시간·성과·사용량이 아닙니다.",
    ],
    metrics: { evidence: null, tokens: null },
  };
}

type RecordValue = Record<string, unknown>;
const record = (value: unknown): RecordValue =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordValue)
    : {};
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);
const str = (value: unknown): string =>
  typeof value === "string" ? value : "";
const finite = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;
const summaryText = (value: unknown, max = 800): string => {
  if (typeof value === "string") return value.slice(0, max);
  try {
    return JSON.stringify(value)?.slice(0, max) || "";
  } catch {
    return "";
  }
};
const timestamp = (value: unknown): number | null => {
  if (
    typeof value !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
  )
    return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
};
const observedStatus = (value: unknown): TraceEvent["status"] => {
  if (["succeeded", "completed", "complete", "done"].includes(str(value)))
    return "done";
  if (
    ["held", "needs_revision", "needs_input", "research_required"].includes(
      str(value),
    )
  )
    return "held";
  if (["failed", "cancelled", "error"].includes(str(value))) return "error";
  if (["running", "researching", "active"].includes(str(value)))
    return "active";
  return "idle";
};

// Only unique operations from product-v0.10.0 skills/manifest.json are attributed.
// Shared operations (select_evidence, current_request, match_product_scope,
// retrieve_product_facts, validate_source_refs) cannot identify the calling skill.
const uniqueSkillOperations: Record<string, string> = {
  doctor: "evidence-retrieval",
  list_models: "evidence-retrieval",
  set_request_scope_policy: "evidence-retrieval",
  open_product_workflow: "evidence-retrieval",
  record_workflow_event: "evidence-retrieval",
  workflow_status: "evidence-retrieval",
  open_request: "evidence-retrieval",
  open_request_bundle: "evidence-retrieval",
  resolve_request: "evidence-retrieval",
  resolve_request_bundle: "evidence-retrieval",
  record_request_research: "evidence-retrieval",
  prepare_planning_input: "evidence-retrieval",
  retrieve_reviews: "evidence-retrieval",
  evidence_inventory: "evidence-retrieval",
  read_evidence_batch: "evidence-retrieval",
  record_evidence_review: "evidence-retrieval",
  evidence_coverage: "evidence-retrieval",
  fetch_web_page: "web-evidence-collection",
  capture_web_page: "web-evidence-collection",
  import_web_evidence: "web-evidence-collection",
  configure_web_research: "web-evidence-collection",
  import_web_evidence_bulk: "web-evidence-collection",
  validate_constraints: "concept-writing",
  validate_result_contract: "review-and-revise",
  review_product_result: "review-and-revise",
  start_turn: "review-and-revise",
  get_turn: "review-and-revise",
  save_result: "review-and-revise",
  save_reviewed_result: "review-and-revise",
  save_and_export: "review-and-revise",
  prepare_web_result: "review-and-revise",
  deliver_result: "review-and-revise",
  export_session: "review-and-revise",
  record_usage: "review-and-revise",
  cancel_turn: "review-and-revise",
  begin_invocation: "review-and-revise",
  finish_invocation: "review-and-revise",
  prepare_review_packet: "review-and-revise",
  verify_review_packet: "review-and-revise",
};

function requireTrace(condition: unknown, field: string): asserts condition {
  if (!condition)
    throw new Error(`관제실 trace 형식이 올바르지 않습니다: ${field}`);
}

const eventKinds = new Set([
  "request",
  "delegate",
  "reply",
  "skill",
  "collect",
  "role_done",
  "review",
  "gate",
  "revision",
  "save",
  "complete",
  "metadata",
  "journal",
  "evidence",
]);
const recordedKinds = new Set([
  "request",
  "journal",
  "evidence",
  "review",
  "save",
  "gate",
  "metadata",
]);
const eventStatuses = new Set<TraceEvent["status"]>([
  "active",
  "done",
  "held",
  "error",
  "idle",
]);
const boundedString = (
  value: unknown,
  max: number,
  allowEmpty = false,
): value is string =>
  typeof value === "string" &&
  value.length <= max &&
  (allowEmpty || value.trim().length > 0);

/** A normalized export must remain JSON data, including its optional raw records. */
function validateJsonData(input: unknown): void {
  const visiting = new Set<object>();
  let count = 0;
  const visit = (value: unknown, depth: number) => {
    count += 1;
    requireTrace(depth <= 64 && count <= 500_000, "raw 데이터 깊이·항목 한도");
    if (
      value === null ||
      typeof value === "boolean" ||
      typeof value === "string"
    )
      return;
    if (typeof value === "number") {
      requireTrace(Number.isFinite(value), "raw의 유한 숫자");
      return;
    }
    requireTrace(
      typeof value === "object" && value !== null,
      "raw JSON 데이터",
    );
    requireTrace(!visiting.has(value), "raw 순환 참조");
    requireTrace(
      Array.isArray(value) ||
        Object.getPrototypeOf(value) === Object.prototype ||
        Object.getPrototypeOf(value) === null,
      "raw JSON object",
    );
    visiting.add(value);
    for (const child of Array.isArray(value) ? value : Object.values(value))
      visit(child, depth + 1);
    visiting.delete(value);
  };
  visit(input, 0);
}

/** Accept the UI's exportTrace() output without upgrading demo evidence. */
function parseNormalizedTrace(root: RecordValue): HarnessTrace {
  requireTrace(root.mode === "demo" || root.mode === "recorded", "mode");
  requireTrace(boundedString(root.title, 1000), "title");
  const mode = root.mode;
  const title = root.title;
  const duration = root.duration;
  requireTrace(
    typeof duration === "number" &&
      Number.isFinite(duration) &&
      duration >= 1 &&
      duration <= 365 * 86400,
    "duration (1초~365일)",
  );
  requireTrace(
    mode === "demo"
      ? root.sessionId === null
      : boundedString(root.sessionId, 200) &&
          /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(root.sessionId),
    "sessionId",
  );
  const sessionId = root.sessionId as string | null;
  requireTrace(
    Array.isArray(root.events) &&
      root.events.length > 0 &&
      root.events.length <= 25_000,
    "events (1~25,000건)",
  );
  requireTrace(
    Array.isArray(root.warnings) &&
      root.warnings.length <= 100 &&
      root.warnings.every((value) => boundedString(value, 2000)),
    "warnings",
  );
  const warnings = [...root.warnings] as string[];
  const metrics = record(root.metrics);
  for (const key of ["evidence", "tokens"]) {
    const value = metrics[key];
    requireTrace(
      value === null ||
        (typeof value === "number" &&
          Number.isSafeInteger(value) &&
          value >= 0),
      `metrics.${key}`,
    );
    if (mode === "demo")
      requireTrace(value === null, `합성 demo의 metrics.${key}는 null`);
  }
  const ids = new Set<string>();
  const endpointIds = new Set(nodes.map((node) => node.id));
  let previousAt = -1;
  const events: TraceEvent[] = root.events.map((value: unknown) => {
    const event = record(value);
    requireTrace(
      boundedString(event.id, 200) &&
        /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(event.id) &&
        !ids.has(event.id),
      "중복 없는 event.id",
    );
    ids.add(event.id);
    requireTrace(
      typeof event.at === "number" &&
        Number.isFinite(event.at) &&
        event.at >= previousAt &&
        event.at >= 0 &&
        event.at <= duration,
      "순서가 유지된 event.at",
    );
    previousAt = event.at;
    requireTrace(
      typeof event.kind === "string" && eventKinds.has(event.kind),
      "event.kind",
    );
    requireTrace(
      typeof event.source === "string" && endpointIds.has(event.source),
      "event.source",
    );
    requireTrace(
      typeof event.target === "string" && endpointIds.has(event.target),
      "event.target",
    );
    requireTrace(boundedString(event.label, 1000), "event.label");
    requireTrace(boundedString(event.detail, 16000, true), "event.detail");
    requireTrace(
      typeof event.status === "string" &&
        eventStatuses.has(event.status as TraceEvent["status"]),
      "event.status",
    );
    if (mode === "recorded") {
      requireTrace(
        event.source === "main" &&
          event.target === "main" &&
          recordedKinds.has(event.kind),
        "v0.10.0 저장 trace의 메인 기록 범위",
      );
    }
    if (Object.hasOwn(event, "raw")) validateJsonData(event.raw);
    return {
      id: event.id,
      at: event.at,
      kind: event.kind,
      source: event.source,
      target: event.target,
      label: event.label,
      detail: event.detail,
      status: event.status as TraceEvent["status"],
      ...(Object.hasOwn(event, "raw") ? { raw: event.raw } : {}),
    };
  });
  // Validate the complete normalized body and bound serialized size before reuse.
  validateJsonData(root);
  requireTrace(
    new TextEncoder().encode(JSON.stringify(root)).byteLength <=
      25 * 1024 * 1024,
    "trace JSON 25MB 한도",
  );
  if (mode === "demo" && !warnings.some((value) => value.includes("합성")))
    warnings.push(
      "합성 시각 연출입니다. 실제 업무 실행·사용량·성과 기록이 아닙니다.",
    );
  if (
    mode === "recorded" &&
    !warnings.some((value) => value.includes("native 서브에이전트"))
  )
    warnings.push(
      "v0.10.0 저장 trace에는 native 서브에이전트 실행·메시지 장부가 없습니다.",
    );
  return {
    mode,
    title,
    sessionId,
    duration,
    events,
    warnings,
    metrics: {
      evidence: metrics.evidence as number | null,
      tokens: metrics.tokens as number | null,
    },
  };
}

/** Read a normalized UI trace or the export FILE body, never a path/SHA receipt. */
export function parseHarnessTrace(input: unknown): HarnessTrace {
  const root = record(input);
  if (
    Object.hasOwn(root, "mode") ||
    (Object.hasOwn(root, "duration") && Object.hasOwn(root, "events"))
  )
    return parseNormalizedTrace(root);
  const sessionId = str(root.session_id);
  if (
    !sessionId ||
    !Array.isArray(root.requests) ||
    !Array.isArray(root.turns)
  ) {
    throw new Error(
      "v0.10.0 export_session이 저장한 세션 JSON 파일을 선택하세요. path·sha256만 있는 receipt는 실행 기록이 아닙니다.",
    );
  }
  if (!root.requests.length && !root.turns.length)
    throw new Error("세션 JSON에 요청·turn 기록이 없습니다.");

  const warnings = new Set<string>([
    "저장 기록 재생입니다. v0.10.0 export에는 native 서브에이전트 실행·메시지 장부가 없어 역할 실행을 추정하지 않습니다.",
    "조사 journal·coverage·검토는 호출자 신고이며 원문 의미·자료 충분성·실제 native 종료의 자동 인증이 아닙니다.",
    "시간축은 시각이 있는 첫·마지막 관측 사건 사이의 구간이며 전체 업무·native 실행 시간을 뜻하지 않습니다.",
  ]);
  const isFixture = root.synthetic === true || root.schema_fixture === true;
  if (isFixture)
    warnings.add(
      "형식 검증용 합성 fixture입니다. export 필드 구조와 화면을 검사하기 위한 데이터이며 실제 업무 실행 기록이 아닙니다.",
    );
  type PendingEvent = Omit<TraceEvent, "at"> & {
    stamp: number | null;
    order: number;
  };
  const pending: PendingEvent[] = [];
  const add = (options: Omit<PendingEvent, "id" | "order">) => {
    pending.push({
      ...options,
      id: `recorded-${pending.length + 1}`,
      order: pending.length,
    });
  };
  const core = (
    stamp: number | null,
    kind: string,
    label: string,
    detail: string,
    status: TraceEvent["status"],
    raw: unknown,
  ) => {
    if (stamp === null)
      warnings.add(
        "시각이 없는 항목은 0초의 metadata로 보존합니다. 실행 순서·소요 시간·병렬 실행을 만들어내지 않습니다.",
      );
    add({
      stamp,
      kind: stamp === null ? "metadata" : kind,
      source: "main",
      target: "main",
      label,
      detail,
      status: stamp === null ? "idle" : status,
      raw,
    });
  };
  let question = "";
  for (const requestValue of root.requests) {
    const request = record(requestValue);
    const requestInput = record(request.input);
    const workflow = record(request.workflow);
    if (!question) question = str(requestInput.question);
    if (timestamp(workflow.started_at) !== null) {
      core(
        timestamp(workflow.started_at),
        "request",
        "업무 시계 시작 기록",
        `${str(requestInput.request_key)} · 최초 요청에 연결된 로컬 업무 시계`,
        "active",
        workflow,
      );
    }
    for (const eventValue of list(request.workflow_events)) {
      const event = record(eventValue);
      const data = record(event.data);
      const kind = str(event.kind) || "unknown";
      let label = `Journal · ${kind}`;
      let detail = summaryText(data);
      let status: TraceEvent["status"] = "idle";
      let displayKind = kind === "finish" ? "save" : "journal";
      switch (kind) {
        case "research_plan":
          label = "제품전반 조사 계획 신고";
          detail = `${str(data.product_name)} · coverage: ${summaryText(data.coverage)}`;
          status = "active";
          break;
        case "source_scan":
          label = "원문 조사 관측 신고";
          detail = `${str(data.page_label)} · ${str(data.status)} · ${str(data.reason)} · ${str(data.source_url)}`;
          status = data.status === "inaccessible" ? "held" : "active";
          break;
        case "research_stop":
          label = "원문 수집 마감 기록";
          detail = `${str(data.code)} · ${str(data.basis)} · 남은 범위: ${summaryText(data.remaining_scope)}`;
          status = [
            "access_failure",
            "insufficient_evidence",
            "whole_budget_expired",
          ].includes(str(data.code))
            ? "held"
            : "idle";
          break;
        case "analysis_scope":
          label = "분석 범위 신고";
          detail = `source_ids: ${summaryText(data.source_ids)} · ${str(data.scope)}`;
          status = "active";
          break;
        case "checkpoint":
          label = "업무 checkpoint";
          detail = `남은 작업: ${summaryText(data.remaining_tasks)}`;
          break;
        case "finish": {
          label = "전달 파일 finish 기록";
          const layout = record(data.layout_review);
          detail = `전달: ${summaryText(data.delivered_paths)} · layout 검수 신고: ${str(layout.status)} · ${str(layout.scope)}. 업무·native 성공과 구분합니다.`;
          status = layout.status === "failed" ? "error" : "done";
          break;
        }
        default:
          displayKind = "metadata";
          warnings.add(
            "지원하지 않는 journal 종류는 원본 metadata로 보존하며 에이전트·스킬 호출로 해석하지 않습니다.",
          );
      }
      core(
        timestamp(event.observed_at),
        displayKind,
        label,
        detail,
        status,
        event,
      );
    }
    // Request version journals have no observed_at in this release.
    for (const eventValue of list(request.events)) {
      const event = record(eventValue);
      const eventInput = record(event.input);
      core(
        null,
        "metadata",
        `요청 version ${summaryText(event.version, 30)} · ${str(event.kind) || "unknown"}`,
        `${str(eventInput.status)} · ${str(eventInput.reason)} · 시각 미기록`,
        observedStatus(eventInput.status),
        event,
      );
    }
    if (!request.turn_id && request.response) {
      const response = record(request.response);
      core(
        null,
        "metadata",
        "Turn 전 요청 상태",
        `${str(response.status)} · ${summaryText(response.reason)} · 완료된 기획으로 해석하지 않습니다.`,
        observedStatus(response.status),
        response,
      );
    }
  }

  const sourceIds = new Set<string>();
  let evidenceObserved = false;
  for (const turnValue of root.turns) {
    const turn = record(turnValue);
    const state = record(turn.state);
    const turnId = str(state.turn_id) || "turn 미기록";
    const coverage = record(turn.evidence_coverage_history);
    if (Array.isArray(coverage.deliveries)) evidenceObserved = true;
    for (const deliveryValue of list(coverage.deliveries)) {
      const delivery = record(deliveryValue);
      if (str(delivery.source_id)) sourceIds.add(str(delivery.source_id));
      core(
        timestamp(delivery.observed_at),
        "evidence",
        "등록 원문 전달 기록",
        `${turnId} · ${str(delivery.source_id)} · binding ${str(delivery.binding)}`,
        "active",
        delivery,
      );
    }
    for (const reportValue of list(coverage.review_reports)) {
      const report = record(reportValue);
      const records = list(record(report.payload).records);
      const reviewed = records.filter(
        (value) => record(value).disposition === "reviewed",
      ).length;
      const excluded = records.filter(
        (value) => record(value).disposition === "excluded",
      ).length;
      core(
        timestamp(report.observed_at),
        "review",
        "근거 검토·제외 신고",
        `${turnId} · reviewed ${reviewed} / excluded ${excluded} · 자식 실제 실행·독립 검토를 인증하지 않습니다.`,
        "idle",
        report,
      );
    }
    for (const invocationValue of list(turn.invocations)) {
      const invocation = record(invocationValue);
      const tool = str(invocation.tool_name) || "tool_name 미기록";
      const skill = Object.hasOwn(uniqueSkillOperations, tool)
        ? uniqueSkillOperations[tool]
        : null;
      core(
        null,
        "metadata",
        `호출 장부 · ${tool}`,
        `${turnId} · ${str(invocation.status)} · attempts ${summaryText(invocation.attempts, 20)} · ${skill ? `고유 operation 소속 ${skill}` : "스킬 소속 불명확"} · 호출자 신고 장부, 시각 미기록`,
        "idle",
        invocation,
      );
    }
    const candidates = list(turn.candidates).map(record);
    for (const historyValue of list(state.result_history)) {
      const history = record(historyValue);
      const candidate = candidates.find(
        (value) =>
          value.result_key === history.result_key &&
          value.result_version === history.result_version,
      );
      const validation = record(history.validation);
      const result = record(candidate?.result);
      const accepted = validation.contract_valid === true && !validation.error;
      const candidateStatus = accepted
        ? observedStatus(result.status)
        : validation.contract_valid === false
          ? "held"
          : "idle";
      core(
        timestamp(history.created_at),
        accepted ? "save" : "gate",
        `후보 v${summaryText(history.result_version, 20)} ${accepted ? "구조 승인·저장" : validation.contract_valid === false ? "거절·보존" : "판정 미확인"}`,
        `${turnId} · ${str(history.result_key)} · ${str(result.status)} · ${summaryText(validation.error)} · 의미 검증·현재 전달 준비와 구분합니다.`,
        candidateStatus,
        { history, candidate: candidate ?? null },
      );
    }
    const cancellation = record(state.cancellation);
    if (state.cancellation)
      core(
        timestamp(cancellation.recorded_at),
        "gate",
        "로컬 업무 쓰기 취소",
        `${str(cancellation.reason)} · native/backend 중단 관측과 구분합니다.`,
        "error",
        cancellation,
      );
    core(
      null,
      "metadata",
      "저장된 turn 현재 상태",
      `${turnId} · ${str(state.status)} · valid ${summaryText(state.valid, 20)} · result version ${summaryText(state.result_version, 20)}`,
      observedStatus(state.status),
      state,
    );
  }

  const summary = record(root.usage_summary);
  const totals = record(summary.totals);
  const unknownCounts = record(summary.unknown_counts);
  const inputTokens = finite(totals.input_tokens);
  const outputTokens = finite(totals.output_tokens);
  const tokens =
    finite(summary.recorded_calls) !== null &&
    Number(summary.recorded_calls) > 0 &&
    inputTokens !== null &&
    outputTokens !== null &&
    unknownCounts.input_tokens === 0 &&
    unknownCounts.output_tokens === 0
      ? finite(inputTokens + outputTokens)
      : null;
  warnings.add(
    tokens === null
      ? "토큰 사용량은 미측정 또는 일부 필드 미확인으로 unknown을 유지합니다."
      : "토큰은 기록된 호출의 input+output 합입니다. native 전체·부모/자식 포함 범위는 미확인입니다.",
  );

  if (!pending.length)
    core(
      null,
      "metadata",
      "세션 metadata",
      "실행 사건이 기록되지 않은 세션입니다.",
      "idle",
      root,
    );
  const stamps = pending
    .map((event) => event.stamp)
    .filter((value): value is number => value !== null);
  const first = stamps.length
    ? stamps.reduce((earliest, stamp) => Math.min(earliest, stamp), stamps[0])
    : 0;
  const events: TraceEvent[] = pending
    .map(({ stamp, order, ...event }) => ({
      ...event,
      at: stamp === null ? 0 : Math.max(0, (stamp - first) / 1000),
      order,
    }))
    .sort((a, b) => a.at - b.at || a.order - b.order)
    .map(({ order: _order, ...event }) => event);
  if (!stamps.length)
    warnings.add(
      "관측 시각이 없어 시간축을 재구성할 수 없습니다. 1초는 기록 화면을 유지하는 최소 길이입니다.",
    );
  else if ((events.at(-1)?.at ?? 0) === 0)
    warnings.add(
      "관측 시각이 한 지점에만 있어 실행 길이를 알 수 없습니다. 1초는 최소 재생 길이입니다.",
    );
  return {
    mode: "recorded",
    title: isFixture
      ? `[형식 검증용 합성] ${(question || "v0.10.0 export 형식 fixture").replace(/^\[형식 검증용 합성\]\s*/, "").slice(0, 100)}`
      : question
        ? question.slice(0, 100)
        : "v0.10.0 저장 세션 기록",
    sessionId,
    duration: Math.max(1, events.at(-1)?.at ?? 0),
    events,
    warnings: [...warnings],
    metrics: { evidence: evidenceObserved ? sourceIds.size : null, tokens },
  };
}
