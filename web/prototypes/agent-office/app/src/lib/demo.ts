// Demo record: made-up events in the observer's own format, so the office can be shown before any real run.
// Every value is invented (hosts are *.example). The page labels this mode as demo everywhere it is shown.
import type { DbSnapshot, LiveFile, OfficeEvent } from '../types'

const SESSION = 'demo-session'

export function demoLive(now = Date.now()): LiveFile {
  const base = now - 5_000
  const at = (s: number) => new Date(base + s * 1000).toISOString()
  const events: OfficeEvent[] = []
  let n = 0
  const push = (s: number, e: Partial<OfficeEvent>) => {
    n += 1
    events.push({
      v: 1, id: `demo-${n}`, ts: at(s), ts_basis: 'demo', src: 'demo', hook: 'PreToolUse', session: SESSION, prompt_id: 'demo-prompt',
      agent_id: null, actor: 'main', tool: null, call: null, kind: 'tool', node: 'main', op: null, ops: [], phase: 'point',
      basis: 'demo', detail: {}, ...e,
    })
  }
  // One tool call = PreToolUse + PostToolUse with the same call id.
  const call = (s: number, dur: number, e: Partial<OfficeEvent>, endDetail: Record<string, unknown> = {}, fail = false) => {
    const id = `demo-call-${n}`
    push(s, { ...e, call: id, hook: 'PreToolUse', phase: 'start', detail: { ...(e.detail ?? {}) } })
    push(s + dur, {
      ...e, call: id, hook: fail ? 'PostToolUseFailure' : 'PostToolUse', phase: fail ? 'fail' : 'end',
      detail: { ...(e.detail ?? {}), duration_ms: dur * 1000, ...endDetail },
    })
  }
  const op = (s: number, dur: number, node: string, name: string, end: Record<string, unknown> = {}) =>
    call(s, dur, { tool: 'Bash', kind: 'skill_op', node, op: name, ops: [name] }, end)
  const load = (s: number, node: string) => call(s, 0.1, { tool: 'Read', kind: 'skill_load', node })
  const role = (agent: string, actor: string) => ({ agent_id: agent, actor, node: actor })

  push(0, { hook: 'SessionStart', kind: 'session', phase: 'start', detail: { reason: 'startup' } })
  push(3, { hook: 'UserPromptSubmit', kind: 'request' })
  load(5, 'evidence-retrieval')
  op(6, 2, 'evidence-retrieval', 'doctor')
  op(9, 2.5, 'evidence-retrieval', 'open_request_bundle')
  op(12, 2, 'evidence-retrieval', 'open_product_workflow')
  call(14.5, 0.8, { tool: 'Bash', kind: 'shell', detail: { programs: ['ls'] } })
  op(15.5, 1.5, 'evidence-retrieval', 'evidence_inventory')
  load(18, 'web-evidence-collection')
  // Two research roles in parallel, launched in the background.
  call(20, 0.06, { tool: 'Agent', kind: 'delegate', node: 'product_official_researcher' }, { background: true, response_status: 'async_launched' })
  call(20.5, 0.06, { tool: 'Agent', kind: 'delegate', node: 'product_review_researcher' }, { background: true, response_status: 'async_launched' })
  push(21, { hook: 'SubagentStart', kind: 'subagent', phase: 'start', ...role('demo-a1', 'product_official_researcher') })
  push(21.3, { hook: 'SubagentStart', kind: 'subagent', phase: 'start', ...role('demo-a2', 'product_review_researcher') })
  call(23, 6, { tool: 'WebFetch', kind: 'web', ...role('demo-a1', 'product_official_researcher'), detail: { host: 'official.example' } })
  call(30, 0.3, { tool: 'Read', kind: 'file', ...role('demo-a1', 'product_official_researcher'), detail: { area: 'web_evidence' } })
  call(35, 7, { tool: 'WebFetch', kind: 'web', ...role('demo-a1', 'product_official_researcher'), detail: { host: 'manual.example' } })
  call(24, 7, { tool: 'WebSearch', kind: 'web', ...role('demo-a2', 'product_review_researcher') })
  call(33, 7, { tool: 'WebFetch', kind: 'web', ...role('demo-a2', 'product_review_researcher'), detail: { host: 'review-a.example' } })
  call(42, 6, { tool: 'WebFetch', kind: 'web', ...role('demo-a2', 'product_review_researcher'), detail: { host: 'community.example' } })
  call(50, 7, { tool: 'WebFetch', kind: 'web', ...role('demo-a2', 'product_review_researcher'), detail: { host: 'review-b.example' } })
  op(30, 1, 'evidence-retrieval', 'record_workflow_event')
  call(60, 0.1, { tool: 'SubagentHandback', kind: 'handback', ...role('demo-a1', 'product_official_researcher') })
  push(61, { hook: 'SubagentStop', kind: 'subagent', phase: 'end', ...role('demo-a1', 'product_official_researcher') })
  push(62, { hook: 'UserPromptSubmit', kind: 'handback_delivered', detail: { from_agent_id: 'demo-a1' } })
  op(63, 4, 'web-evidence-collection', 'import_web_evidence_bulk')
  call(75, 0.1, { tool: 'SubagentHandback', kind: 'handback', ...role('demo-a2', 'product_review_researcher') })
  push(76, { hook: 'SubagentStop', kind: 'subagent', phase: 'end', ...role('demo-a2', 'product_review_researcher') })
  push(77, { hook: 'UserPromptSubmit', kind: 'handback_delivered', detail: { from_agent_id: 'demo-a2' } })
  op(78, 4, 'web-evidence-collection', 'import_web_evidence_bulk')
  op(84, 4, 'evidence-retrieval', 'read_evidence_batch')
  op(90, 1, 'evidence-retrieval', 'evidence_coverage')
  op(92, 1, 'evidence-retrieval', 'record_workflow_event')
  load(94, 'needs-structuring')
  op(96, 1.2, 'needs-structuring', 'select_evidence')
  load(100, 'feature-comparison')
  op(101, 2, 'feature-comparison', 'retrieve_product_facts')
  load(106, 'concept-writing')
  op(110, 1, 'concept-writing', 'validate_constraints')
  load(112, 'review-and-revise')
  op(114, 2, 'review-and-revise', 'prepare_review_packet')
  // Independent reviewer: reads only.
  call(117, 0.06, { tool: 'Agent', kind: 'delegate', node: 'product_evidence_reviewer' }, { background: true, response_status: 'async_launched' })
  push(117.5, { hook: 'SubagentStart', kind: 'subagent', phase: 'start', ...role('demo-a3', 'product_evidence_reviewer') })
  call(119, 0.4, { tool: 'Read', kind: 'file', ...role('demo-a3', 'product_evidence_reviewer'), detail: { area: 'runtime' } })
  call(122, 1.2, { tool: 'Grep', kind: 'file', ...role('demo-a3', 'product_evidence_reviewer'), detail: { area: 'web_evidence' } })
  call(130, 0.6, { tool: 'Read', kind: 'file', ...role('demo-a3', 'product_evidence_reviewer'), detail: { area: 'web_evidence' } })
  call(150, 0.1, { tool: 'SubagentHandback', kind: 'handback', ...role('demo-a3', 'product_evidence_reviewer') })
  push(151, { hook: 'SubagentStop', kind: 'subagent', phase: 'end', ...role('demo-a3', 'product_evidence_reviewer') })
  push(152, { hook: 'UserPromptSubmit', kind: 'handback_delivered', detail: { from_agent_id: 'demo-a3' } })
  op(155, 3, 'review-and-revise', 'save_reviewed_result', { accepted: false, reason: '데모: 근거 연결 보완', turn_status: 'draft', result_version: 1, revision_count: 0 })
  op(160, 1.2, 'needs-structuring', 'validate_source_refs')
  op(165, 3, 'review-and-revise', 'save_reviewed_result', { accepted: true, turn_status: 'completed', result_version: 2, revision_count: 1 })
  op(170, 2, 'review-and-revise', 'export_session')
  push(176, { hook: 'Stop', kind: 'turn_end' })

  const db: DbSnapshot = {
    available: true, read_at: at(176),
    workflow: { research_id: 'demo', started_at: at(13), budget_seconds: 1800, research_stopped_at: at(92.5), finished_at: at(173) },
    workflow_events: [
      { kind: 'research_plan', observed_at: at(30.5), product: '데모 제품' },
      { kind: 'source_scan', observed_at: at(64), host: 'official.example', status: 'observed', sources: 2 },
      { kind: 'source_scan', observed_at: at(79), host: 'review-a.example', status: 'observed', reviews: 6 },
      { kind: 'source_scan', observed_at: at(80), host: 'community.example', status: 'observed', reviews: 3 },
      { kind: 'research_stop', observed_at: at(92.5) },
      { kind: 'finish', observed_at: at(173) },
    ],
    request: { question: '데모 질문: 정확 모델의 실제 후기에서 불편을 찾고 기존 기능과 비교한 개선안', turn_id: 'demo-turn', status: 'completed' },
    turn: { turn_id: 'demo-turn', status: 'completed', revision_count: 1, result_version: 2, valid: true, created_at: at(9) },
    results: 2,
    candidates: [
      { result_version: 1, created_at: at(157), status: 'draft', counts: { pains: 4, existing_features: 3, remaining_pains: 2, concepts: 2, evidence_refs: 9 }, contract_valid: true, structural_valid: true, acceptance_ready: false, semantic_status: null },
      { result_version: 2, created_at: at(167), status: 'completed', counts: { pains: 4, existing_features: 3, remaining_pains: 2, concepts: 2, evidence_refs: 11 }, contract_valid: true, structural_valid: true, acceptance_ready: true, semantic_status: null },
    ],
    evidence_delivered: 11, evidence_reviews: 1, cancelled: false,
  }
  return { kind: 'lgax-agent-office-live', version: 1, written_at: at(176), harness_version: 'demo', events, db }
}
