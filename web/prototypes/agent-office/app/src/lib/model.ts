// Turns recorded hook events into what the office shows: tool calls as spans (start -> end), points in time,
// research-role presence, question turns, and the database timeline (workflow clock, work log, saved candidates).
// Nothing is inferred from call order or time overlap; a span is one tool_use_id seen by Pre/PostToolUse.
import type { Candidate, DbSnapshot, OfficeEvent, WorkflowEvent } from '../types'
import { ROLE_IDS, SAVE_OPS, SKILL_IDS } from './catalog'
import { isBrowserTool, labelOf } from './labels'

export interface Span {
  key: string
  actor: string
  agentId: string | null
  target: string // skill id, role id, 'console', 'shelf', 'web', 'desk'
  host: string | null // building in the web street ('search' / 'browser' for tools without a host)
  kind: string
  tool: string | null
  op: string | null
  node: string | null
  label: string
  endLabel: string | null
  start: number
  end: number | null
  status: 'running' | 'done' | 'fail'
  durationMs: number | null
  basis: string
  detail: Record<string, unknown>
  events: OfficeEvent[]
}

export interface Point {
  key: string
  t: number
  kind: string // request, turn_end, handback_delivered, notification, session_start, session_end, helper, wf, candidate
  node: string
  label: string
  basis: string
  ev?: OfficeEvent
  wf?: WorkflowEvent
  cand?: Candidate
}

export interface Presence {
  agentId: string
  actor: string
  start: number
  end: number | null
}

export interface Turn {
  start: number
  end: number | null
  kind: string // request, handback_delivered, notification
}

export interface SaveOutcome {
  span: Span
  t: number
  accepted: boolean | null
  reason: string | null
  turnStatus: string | null
  resultVersion: number | null
  revisionCount: number | null
}

export interface Workflow {
  start: number
  budgetMs: number | null
  researchStop: number | null
  finish: number | null
}

export interface SessionInfo {
  id: string
  start: number
  end: number
  count: number
  requests: number
  roles: string[]
}

export interface SessionModel {
  id: string
  start: number
  end: number
  live: boolean
  events: OfficeEvent[]
  spans: Span[]
  points: Point[]
  presences: Presence[]
  turns: Turn[]
  saves: SaveOutcome[]
  hosts: { host: string; first: number; source: 'tool' | 'worklog' }[]
  db: DbSnapshot | null
  dbMatched: boolean
  workflow: Workflow | null
  candidates: (Candidate & { t: number })[]
  busy: [number, number][] // merged spans of time when something was happening (tool calls, turns, roles, points)
}

export function parseTime(value: unknown): number | null {
  if (typeof value !== 'string' || !value) return null
  // Python writes microseconds (6 digits); keep milliseconds so every browser parses it the same way.
  const t = Date.parse(value.replace(/(\.\d{3})\d+/, '$1'))
  return Number.isFinite(t) ? t : null
}

export function sessionsOf(events: OfficeEvent[]): SessionInfo[] {
  const by = new Map<string, SessionInfo>()
  for (const e of events) {
    const id = e.session ?? 'unknown'
    const t = parseTime(e.ts)
    if (t == null) continue
    const s = by.get(id) ?? { id, start: t, end: t, count: 0, requests: 0, roles: [] }
    s.start = Math.min(s.start, t)
    s.end = Math.max(s.end, t)
    s.count += 1
    if (e.kind === 'request') s.requests += 1
    if (ROLE_IDS.includes(e.actor) && !s.roles.includes(e.actor)) s.roles.push(e.actor)
    by.set(id, s)
  }
  return [...by.values()].sort((a, b) => a.start - b.start)
}

function targetOf(e: OfficeEvent): { target: string; host: string | null } {
  const detail = e.detail ?? {}
  switch (e.kind) {
    case 'skill_op':
    case 'skill_load':
      return { target: SKILL_IDS.includes(e.node ?? '') ? (e.node as string) : 'desk', host: null }
    case 'delegate':
      return { target: e.node ?? 'desk', host: null }
    case 'handback':
      return { target: 'main', host: null }
    case 'web':
      return { target: 'web', host: typeof detail.host === 'string' ? detail.host : e.tool === 'WebSearch' ? 'search' : 'web' }
    case 'shell':
      return { target: 'console', host: null }
    case 'file':
      return { target: 'shelf', host: null }
    default:
      if (e.tool === 'SubagentHandback') return { target: 'main', host: null }
      if (isBrowserTool(e.tool)) return { target: 'web', host: 'browser' }
      if (['Read', 'Write', 'Edit', 'Grep', 'Glob', 'NotebookEdit'].includes(e.tool ?? '')) return { target: 'shelf', host: null }
      return { target: 'desk', host: null }
  }
}

const TOOL_HOOKS = new Set(['PreToolUse', 'PostToolUse', 'PostToolUseFailure'])

export function buildSession(all: OfficeEvent[], sessionId: string, db: DbSnapshot | null, live: boolean, latest: boolean): SessionModel {
  const events = all
    .filter((e) => (e.session ?? 'unknown') === sessionId && parseTime(e.ts) != null)
    .map((e, i) => ({ e, i, t: parseTime(e.ts) as number }))
    .sort((a, b) => a.t - b.t || a.i - b.i)
  const start = events.length ? events[0].t : Date.now()
  const end = events.length ? events[events.length - 1].t : start

  const spans: Span[] = []
  const byCall = new Map<string, Span>()
  const points: Point[] = []
  const presences = new Map<string, Presence>()
  const turns: Turn[] = []
  const hostFirst = new Map<string, { host: string; first: number; source: 'tool' | 'worklog' }>()

  for (const { e, t } of events) {
    const detail = e.detail ?? {}
    // Research-role presence: SubagentStart/Stop with the role's agent_id; their own tool calls also prove presence.
    if (e.agent_id && ROLE_IDS.includes(e.actor)) {
      const p = presences.get(e.agent_id) ?? { agentId: e.agent_id, actor: e.actor, start: t, end: null }
      p.start = Math.min(p.start, t)
      if (e.kind === 'subagent' && e.phase === 'end') p.end = t
      presences.set(e.agent_id, p)
    }
    if (TOOL_HOOKS.has(e.hook)) {
      const key = `${e.call ?? e.id}`
      let span = byCall.get(key)
      if (e.phase === 'start' || !span) {
        const dur = typeof detail.duration_ms === 'number' ? detail.duration_ms : null
        const { target, host } = targetOf(e)
        span = {
          key, actor: e.actor, agentId: e.agent_id, target, host, kind: e.kind, tool: e.tool, op: e.op, node: e.node,
          label: labelOf({ ...e, phase: 'start' }), endLabel: null,
          start: e.phase === 'start' ? t : dur != null ? t - dur : t, end: null, status: 'running', durationMs: null,
          basis: e.basis, detail: { ...detail }, events: [],
        }
        byCall.set(key, span)
        spans.push(span)
      }
      span.events.push(e)
      if (e.phase === 'end' || e.phase === 'fail') {
        span.end = t
        span.status = e.phase === 'fail' ? 'fail' : 'done'
        span.durationMs = typeof detail.duration_ms === 'number' ? detail.duration_ms : t - span.start
        span.endLabel = labelOf(e)
        Object.assign(span.detail, detail)
        if (!span.host && typeof detail.host === 'string') span.host = detail.host
      }
      if (span.kind === 'web' && span.host && !['search', 'web', 'browser'].includes(span.host) && !hostFirst.has(span.host)) {
        hostFirst.set(span.host, { host: span.host, first: span.start, source: 'tool' })
      }
      continue
    }
    const label = labelOf(e)
    if (e.kind === 'request' || e.kind === 'handback_delivered' || e.kind === 'notification') {
      turns.push({ start: t, end: null, kind: e.kind })
      points.push({ key: e.id, t, kind: e.kind, node: e.kind === 'request' ? 'reception' : 'main', label, basis: e.basis, ev: e })
    } else if (e.kind === 'turn_end') {
      const open = [...turns].reverse().find((x) => x.end == null)
      if (open) open.end = t
      for (const x of turns) if (x.end == null) x.end = t
      points.push({ key: e.id, t, kind: 'turn_end', node: 'main', label, basis: e.basis, ev: e })
    } else if (e.kind === 'session') {
      points.push({ key: e.id, t, kind: e.phase === 'start' ? 'session_start' : 'session_end', node: 'main', label, basis: e.basis, ev: e })
    } else if (e.kind === 'subagent') {
      points.push({ key: e.id, t, kind: e.node === 'other_subagent' ? 'helper' : 'role', node: e.node ?? 'main', label, basis: e.basis, ev: e })
    } else {
      points.push({ key: e.id, t, kind: e.kind, node: e.node ?? 'main', label, basis: e.basis, ev: e })
    }
  }
  // A call with no end: still running when live, otherwise it stopped being recorded at the session's last event.
  for (const s of spans) if (s.end == null && !live) s.end = Math.max(end, s.start)

  const saves: SaveOutcome[] = spans
    .filter((s) => s.kind === 'skill_op' && SAVE_OPS.has(s.op ?? '') && s.status !== 'running')
    .map((s) => ({
      span: s,
      t: s.end ?? s.start,
      accepted: typeof s.detail.accepted === 'boolean' ? s.detail.accepted : null,
      reason: typeof s.detail.reason === 'string' ? s.detail.reason : null,
      turnStatus: typeof s.detail.turn_status === 'string' ? s.detail.turn_status : null,
      resultVersion: typeof s.detail.result_version === 'number' ? s.detail.result_version : null,
      revisionCount: typeof s.detail.revision_count === 'number' ? s.detail.revision_count : null,
    }))

  // The database snapshot is the harness's latest state. Use it only when its own times fall inside this session.
  let workflow: Workflow | null = null
  let candidates: (Candidate & { t: number })[] = []
  let dbMatched = false
  if (db?.available) {
    const lo = start - 60_000
    const hi = (live && latest ? Date.now() : end) + 120_000
    const inside = (v: unknown) => {
      const t = parseTime(v)
      return t != null && t >= lo && t <= hi
    }
    dbMatched = inside(db.workflow?.started_at) || inside(db.turn?.created_at)
    if (dbMatched) {
      const ws = parseTime(db.workflow?.started_at)
      if (db.workflow && ws != null && inside(db.workflow.started_at)) {
        workflow = {
          start: ws,
          budgetMs: typeof db.workflow.budget_seconds === 'number' ? db.workflow.budget_seconds * 1000 : null,
          researchStop: parseTime(db.workflow.research_stopped_at),
          finish: parseTime(db.workflow.finished_at),
        }
        points.push({ key: 'wf-start', t: ws, kind: 'wf', node: 'vault', label: '업무 시계 시작 (DB)', basis: 'db_recorded' })
        for (const [i, w] of (db.workflow_events ?? []).entries()) {
          const t = parseTime(w.observed_at)
          if (t == null) continue
          points.push({ key: `wf-${i}`, t, kind: 'wf', node: w.kind === 'source_scan' ? 'web' : 'vault', label: '', basis: 'db_recorded', wf: w })
          if (w.kind === 'source_scan' && typeof w.host === 'string' && !hostFirst.has(w.host)) {
            hostFirst.set(w.host, { host: w.host, first: t, source: 'worklog' })
          }
        }
      }
      candidates = (db.candidates ?? [])
        .map((c) => ({ ...c, t: parseTime(c.created_at) ?? NaN }))
        .filter((c) => Number.isFinite(c.t) && c.t >= lo && c.t <= hi)
      for (const c of candidates) {
        points.push({ key: `cand-${c.result_version}`, t: c.t, kind: 'candidate', node: 'review-and-revise', label: `후보 v${c.result_version ?? '?'} 저장 기록 (DB)`, basis: 'db_recorded', cand: c })
      }
    }
  }
  points.sort((a, b) => a.t - b.t)

  const raw: [number, number][] = [
    ...spans.map((s) => [s.start, s.end ?? end] as [number, number]),
    ...turns.map((x) => [x.start, x.end ?? end] as [number, number]),
    ...[...presences.values()].map((p) => [p.start, p.end ?? end] as [number, number]),
    ...points.map((p) => [p.t, p.t + 3000] as [number, number]),
  ].sort((a, b) => a[0] - b[0])
  const busy: [number, number][] = []
  for (const [a, b] of raw) {
    const last = busy[busy.length - 1]
    if (last && a <= last[1]) last[1] = Math.max(last[1], b)
    else busy.push([a, b])
  }

  return {
    id: sessionId, start, end, live, events: events.map((x) => x.e), spans, points,
    presences: [...presences.values()], turns, saves,
    hosts: [...hostFirst.values()].sort((a, b) => a.first - b.first),
    db, dbMatched, workflow, candidates, busy,
  }
}

// When t falls in a quiet gap (nothing running, no open turn), the time the next activity starts; otherwise null.
export function quietUntil(m: SessionModel, t: number): number | null {
  for (const [a, b] of m.busy) {
    if (t < a) return a
    if (t <= b) return null
  }
  return null
}
