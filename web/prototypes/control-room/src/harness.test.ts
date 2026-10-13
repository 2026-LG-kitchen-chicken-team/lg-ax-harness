import assert from "node:assert/strict";
import test from "node:test";
import { nodes } from "./catalog";
import { createDemoTrace, parseHarnessTrace } from "./harness";

// Schema fixture follows conversation.py export_session, workflow.py events,
// state.py get_turn and evidence_coverage.py history. It is not a business run.
const exportFixture = () => ({
  session_id: "schema-fixture",
  requests: [
    {
      input: {
        session_id: "schema-fixture",
        request_key: "request-1",
        question: "정확 모델 상품기획",
      },
      turn_id: "turn-1",
      request_version: 1,
      events: [],
      workflow: { started_at: "2026-10-13T02:00:00+00:00" },
      workflow_events: [
        {
          observed_at: "2026-10-13T02:00:30+00:00",
          research_id: "research-1",
          event_key: "stop",
          kind: "research_stop",
          data: {
            code: "sources_exhausted",
            basis: "이번 조사 범위 기록",
            remaining_scope: [],
          },
        },
        {
          observed_at: "2026-10-13T02:00:05+00:00",
          research_id: "research-1",
          event_key: "plan",
          kind: "research_plan",
          data: {
            product_name: "정확 모델",
            coverage: [
              "positive",
              "negative",
              "long_term",
              "conditions",
              "counterexamples",
            ],
            source_plan: ["official", "reviews"],
          },
        },
        {
          observed_at: "2026-10-13T02:00:20+00:00",
          research_id: "research-1",
          event_key: "scan",
          kind: "source_scan",
          data: {
            source_url: "https://example.com/schema-fixture",
            page_label: "후기 원문",
            status: "observed",
            reviews: [],
            snapshot_ids: ["snapshot-1"],
            reason: "부모의 원문 관측 신고",
            source_type: "review_list",
          },
        },
      ],
    },
  ],
  turns: [
    {
      state: {
        session_id: "schema-fixture",
        turn_id: "turn-1",
        status: "held",
        valid: true,
        result_version: 1,
        result_history: [
          {
            result_key: "candidate-1",
            result_version: 1,
            created_at: "2026-10-13T02:00:50+00:00",
            validation: { contract_valid: true },
          },
        ],
      },
      candidates: [
        {
          result_key: "candidate-1",
          result_version: 1,
          result: { status: "held", evidence_refs: [] },
          validation: { contract_valid: true },
        },
      ],
      invocations: [
        {
          turn_id: "turn-1",
          invocation_id: "invocation-1",
          tool_name: "capture_web_page",
          request_hash: "0".repeat(64),
          attempts: 1,
          status: "succeeded",
          retryable: 0,
        },
      ],
      evidence_coverage_history: {
        deliveries: [
          {
            turn_id: "turn-1",
            binding: "binding-1",
            source_id: "source-1",
            observed_at: "2026-10-13T02:00:35+00:00",
          },
        ],
        review_reports: [
          {
            turn_id: "turn-1",
            binding: "binding-1",
            review_key: "review-1",
            observed_at: "2026-10-13T02:00:40+00:00",
            payload: {
              records: [
                {
                  source_id: "source-1",
                  disposition: "reviewed",
                  reason: "부모 직접독해",
                },
              ],
            },
          },
        ],
      },
      usage: [],
    },
  ],
  usage_summary: {
    recorded_calls: 0,
    status: "unknown",
    totals: { input_tokens: null, output_tokens: null },
    unknown_counts: { input_tokens: 0, output_tokens: 0 },
  },
  semantic_status: "unverified",
  acceptance_ready: false,
});

test("demo inventory and choreography use actual product-v0.10.0 roles and skills", () => {
  const trace = createDemoTrace();
  assert.equal(nodes.filter((node) => node.kind === "core").length, 1);
  assert.equal(nodes.filter((node) => node.kind === "agent").length, 3);
  assert.equal(nodes.filter((node) => node.kind === "skill").length, 6);
  assert.equal(trace.mode, "demo");
  assert.equal(trace.sessionId, null);
  assert.equal(trace.duration, 84);
  assert.match(trace.warnings.join(" "), /합성/);
  const ids = new Set(nodes.map((node) => node.id));
  assert.ok(
    trace.events.every(
      (event) => ids.has(event.source) && ids.has(event.target),
    ),
  );
  assert.ok(
    trace.events.every(
      (event, index) => index === 0 || event.at >= trace.events[index - 1].at,
    ),
  );
  assert.equal(
    trace.events.filter((event) => event.kind === "delegate").length,
    3,
  );
  assert.ok(
    trace.events.some(
      (event) => event.kind === "gate" && event.status === "held",
    ),
  );
  assert.equal(trace.events.at(-1)?.status, "done");
});

test("actual v0.10.0 export shape preserves observed ordering, held save and unknown usage", () => {
  const trace = parseHarnessTrace(exportFixture());
  assert.equal(trace.mode, "recorded");
  assert.equal(trace.sessionId, "schema-fixture");
  assert.equal(trace.duration, 50);
  assert.deepEqual(
    trace.events
      .filter((event) => event.kind === "journal")
      .map((event) => event.at),
    [5, 20, 30],
  );
  assert.equal(
    trace.events.find((event) => event.label.includes("후보 v1"))?.status,
    "held",
  );
  assert.equal(trace.metrics.evidence, 1);
  assert.equal(trace.metrics.tokens, null);
});

test("role installations, reviewer packets and source scans cannot create native delegation", () => {
  const fixture = exportFixture();
  const trace = parseHarnessTrace({
    ...fixture,
    optional_agents: [
      "product_official_researcher",
      "product_review_researcher",
      "product_evidence_reviewer",
    ],
    native_installation_verified: true,
    reviewer_packet: {
      native_id: "unverified-id",
      role: "product_evidence_reviewer",
    },
  });
  assert.ok(
    trace.events.every(
      (event) => event.source === "main" && event.target === "main",
    ),
  );
  assert.ok(
    trace.events.every(
      (event) => event.kind !== "delegate" && event.kind !== "reply",
    ),
  );
  const invocation = trace.events.find((event) =>
    event.label.includes("capture_web_page"),
  );
  assert.equal(invocation?.at, 0);
  assert.equal(invocation?.kind, "metadata");
  assert.equal(invocation?.status, "idle");
  assert.match(invocation?.detail ?? "", /web-evidence-collection/);
  assert.match(trace.warnings.join(" "), /시각이 없는/);
});

test("unknown event kinds and ambiguous tools retain metadata without fictitious skills", () => {
  const fixture = exportFixture();
  const trace = parseHarnessTrace({
    ...fixture,
    requests: [
      {
        ...fixture.requests[0],
        workflow_events: [
          {
            kind: "native_agent_started",
            data: { role: "product_review_researcher" },
            observed_at: "2026-10-13T02:00:10Z",
          },
        ],
      },
    ],
    turns: [
      {
        ...fixture.turns[0],
        invocations: [
          { tool_name: "select_evidence", status: "succeeded" },
          { tool_name: "__proto__", status: "succeeded" },
        ],
      },
    ],
  });
  assert.ok(
    trace.events.every(
      (event) => event.source === "main" && event.target === "main",
    ),
  );
  assert.equal(
    trace.events.find((event) => event.label.includes("native_agent_started"))
      ?.status,
    "idle",
  );
  assert.equal(
    trace.events.find((event) => event.label.includes("native_agent_started"))
      ?.kind,
    "metadata",
  );
  assert.match(
    trace.events.find((event) => event.label.includes("select_evidence"))
      ?.detail ?? "",
    /소속 불명확/,
  );
  assert.match(
    trace.events.find((event) => event.label.includes("__proto__"))?.detail ??
      "",
    /소속 불명확/,
  );
});

test("tokens remain unknown for partial measurements and record complete input plus output only", () => {
  const fixture = exportFixture();
  const totals = {
    input_tokens: 100,
    output_tokens: 20,
    cache_tokens: 80,
    reasoning_tokens: 10,
  };
  assert.equal(
    parseHarnessTrace({
      ...fixture,
      usage_summary: {
        recorded_calls: 2,
        totals,
        unknown_counts: { input_tokens: 1, output_tokens: 0 },
      },
    }).metrics.tokens,
    null,
  );
  const known = parseHarnessTrace({
    ...fixture,
    usage_summary: {
      recorded_calls: 1,
      totals,
      unknown_counts: { input_tokens: 0, output_tokens: 0 },
    },
  });
  assert.equal(known.metrics.tokens, 120);
  assert.match(known.warnings.join(" "), /기록된 호출/);
});

test("rejects export receipts and preserves a session without timed events", () => {
  assert.throws(
    () =>
      parseHarnessTrace({
        path: "runtime-data/exports/export-sha.json",
        sha256: "a".repeat(64),
      }),
    /receipt/,
  );
  assert.throws(
    () => parseHarnessTrace({ session_id: "empty", requests: [], turns: [] }),
    /기록이 없습니다/,
  );
  const trace = parseHarnessTrace({
    session_id: "request-only",
    requests: [{ input: { question: "조사 보류" } }],
    turns: [],
  });
  assert.equal(trace.events.length, 1);
  assert.equal(trace.events[0].kind, "metadata");
  assert.equal(trace.duration, 1);
  assert.equal(trace.metrics.evidence, null);
  assert.equal(trace.metrics.tokens, null);
});

test("does not assume a timezone for malformed or unzoned timestamp fields", () => {
  const trace = parseHarnessTrace({
    session_id: "no-zone",
    requests: [
      {
        workflow_events: [
          {
            kind: "checkpoint",
            observed_at: "2026-10-13T10:00:00",
            data: { remaining_tasks: [] },
          },
        ],
      },
    ],
    turns: [],
  });
  assert.equal(trace.events[0].kind, "metadata");
  assert.equal(trace.events[0].at, 0);
  assert.match(trace.warnings.join(" "), /시각이 없는/);
});

test("normalized UI demo export roundtrips while preserving mode and unmeasured usage", () => {
  const original = createDemoTrace();
  const imported = parseHarnessTrace(JSON.parse(JSON.stringify(original)));
  assert.deepEqual(imported, original);
  assert.equal(imported.mode, "demo");
  assert.equal(imported.sessionId, null);
  assert.deepEqual(imported.metrics, { evidence: null, tokens: null });
});

test("normalized recorded trace preserves core records without inventing native calls", () => {
  const original = parseHarnessTrace(exportFixture());
  const imported = parseHarnessTrace(JSON.parse(JSON.stringify(original)));
  assert.deepEqual(imported, original);
  assert.ok(
    imported.events.every(
      (event) => event.source === "main" && event.target === "main",
    ),
  );
  const first = original.events[0];
  assert.throws(
    () =>
      parseHarnessTrace({
        ...original,
        events: [{ ...first, target: "product_official_researcher" }],
      }),
    /메인 기록 범위/,
  );
  assert.throws(
    () =>
      parseHarnessTrace({
        ...original,
        events: [{ ...first, kind: "delegate" }],
      }),
    /메인 기록 범위/,
  );
  assert.throws(
    () => parseHarnessTrace({ ...original, sessionId: "<invented-session>" }),
    /sessionId/,
  );
});

test("normalized traces reject invalid ids, states, times, metrics and non-JSON raw data", () => {
  const original = createDemoTrace();
  const first = original.events[0];
  const invalidEvents = [
    { ...first, id: "<script>" },
    { ...first, source: "invented-agent" },
    { ...first, target: "__proto__" },
    { ...first, status: "completed" },
    { ...first, at: Number.NaN },
    { ...first, at: -1 },
    { ...first, at: original.duration + 1 },
    { ...first, kind: "invented-native-event" },
    { ...first, raw: { native_id: undefined } },
  ];
  for (const event of invalidEvents)
    assert.throws(
      () => parseHarnessTrace({ ...original, events: [event] }),
      /trace 형식/,
    );
  assert.throws(
    () => parseHarnessTrace({ ...original, duration: Infinity }),
    /duration/,
  );
  assert.throws(
    () => parseHarnessTrace({ ...original, duration: 365 * 86400 + 1 }),
    /duration/,
  );
  assert.throws(
    () => parseHarnessTrace({ ...original, events: [first, first] }),
    /event.id/,
  );
  assert.throws(
    () =>
      parseHarnessTrace({ ...original, events: [original.events[1], first] }),
    /event.at/,
  );
  assert.throws(
    () =>
      parseHarnessTrace({
        ...original,
        metrics: { evidence: null, tokens: 100 },
      }),
    /합성 demo/,
  );
  assert.throws(
    () => parseHarnessTrace({ ...original, warnings: [null] }),
    /warnings/,
  );
  assert.throws(() => parseHarnessTrace({ ...original, mode: "live" }), /mode/);
  assert.throws(
    () =>
      parseHarnessTrace({
        ...original,
        events: Array.from({ length: 25_001 }, () => first),
      }),
    /events/,
  );
});

test("synthetic export-format fixtures are visibly distinguished from real executions", () => {
  const fixture = exportFixture();
  for (const flag of [{ synthetic: true }, { schema_fixture: true }]) {
    const trace = parseHarnessTrace({ ...fixture, ...flag });
    assert.match(trace.title, /^\[형식 검증용 합성\]/);
    assert.match(trace.warnings.join(" "), /실제 업무 실행 기록이 아닙니다/);
    assert.equal(
      trace.events.filter((event) => event.kind === "delegate").length,
      0,
    );
  }
  const prefixed = parseHarnessTrace({
    ...fixture,
    synthetic: true,
    requests: [
      {
        ...fixture.requests[0],
        input: {
          ...fixture.requests[0].input,
          question: "[형식 검증용 합성] 냉장고 조사 기록",
        },
      },
    ],
  });
  assert.equal(prefixed.title, "[형식 검증용 합성] 냉장고 조사 기록");
  assert.match(
    parseHarnessTrace(JSON.parse(JSON.stringify(prefixed))).warnings.join(" "),
    /형식 검증용 합성 fixture/,
  );
});
