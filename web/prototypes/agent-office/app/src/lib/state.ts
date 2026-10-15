// What every part of the office is doing at time t (replay position or now).
import { COUNT_ROOMS, NODES, ROLE_IDS } from './catalog'
import { labelOf, secs } from './labels'
import type { Point, SaveOutcome, SessionModel, Span } from './model'

export type Status = 'idle' | 'active' | 'done' | 'fail' | 'off'

export interface NodeState {
  id: string
  status: Status
  activity: string | null // what it is doing now, or last did
  since: number | null
  active: Span[]
  calls: number
  fails: number
  busyMs: number
  lastAt: number | null
  lastStart: number | null // newest thing that arrived here (call start, question, save, DB record)
}

export interface MainState {
  mode: 'working' | 'thinking' | 'idle'
  label: string
  since: number | null
}

export interface FeedItem {
  key: string
  t: number
  who: string
  label: string
  tone: 'start' | 'end' | 'fail' | 'point' | 'db'
  basis: string
  node: string
}

export interface Snapshot {
  t: number
  main: MainState
  nodes: Record<string, NodeState>
  active: Span[]
  presence: Record<string, { since: number; agentId: string } | null>
  saves: SaveOutcome[]
  hostsSeen: string[]
  activeHosts: Set<string>
  counts: { node: string; values: { ko: string; value: number | null }[]; t: number } []
  workflow: { elapsed: number; budget: number | null; left: number | null; researchStopped: boolean; finished: boolean } | null
  feed: FeedItem[]
}

const RECENT_MS = 8_000 // a room stays lit as "just finished" this long (in record time)

export function snapshot(m: SessionModel, t: number, feedLimit = 0): Snapshot {
  const nodes: Record<string, NodeState> = {}
  for (const n of NODES) nodes[n.id] = { id: n.id, status: 'idle', activity: null, since: null, active: [], calls: 0, fails: 0, busyMs: 0, lastAt: null, lastStart: null }
  const active: Span[] = []
  const touch = (id: string, s: Span, running: boolean) => {
    const st = nodes[id]
    if (!st) return
    st.calls += 1
    if (st.lastStart == null || s.start > st.lastStart) st.lastStart = s.start
    if (s.status === 'fail' && s.end != null && s.end <= t) st.fails += 1
    st.busyMs += Math.max(0, Math.min(t, s.end ?? t) - s.start)
    if (running) {
      st.active.push(s)
      if (st.status !== 'active') {
        st.status = 'active'
        st.since = s.start
      }
      st.activity = s.label
      st.lastAt = t
    } else if (st.status !== 'active') {
      const endT = s.end ?? s.start
      if (st.lastAt == null || endT >= st.lastAt) {
        st.lastAt = endT
        st.activity = s.endLabel ?? s.label
        st.status = t - endT < RECENT_MS ? (['fail', 'interrupted', 'unknown'].includes(s.status) || s.detail.accepted === false ? 'fail' : 'done') : 'idle'
      }
    }
  }
  for (const s of m.spans) {
    if (s.start > t) continue
    const running = s.end == null || s.end > t
    if (running) active.push(s)
    // The room the call goes to, and the role who made it.
    const place = s.target === 'desk' || s.target === 'main' ? null : s.target
    if (place) touch(place, s, running)
    if (ROLE_IDS.includes(s.actor)) touch(s.actor, s, running)
  }

  // Research roles: present from SubagentStart (or first own call) to SubagentStop.
  const presence: Snapshot['presence'] = {}
  for (const id of ROLE_IDS) presence[id] = null
  for (const p of m.presences) {
    if (p.start <= t && (p.end == null || p.end > t)) {
      presence[p.actor] = { since: p.start, agentId: p.agentId }
      const st = nodes[p.actor]
      if (st.status !== 'active') {
        st.status = 'active'
        st.since = p.start
        st.activity = st.activity ?? '생각 중 (도구 사용 없음)'
      }
      if (!st.active.length) st.activity = '생각 중 (도구 사용 없음)'
    } else if (p.end != null && p.end <= t && nodes[p.actor].status !== 'active') {
      const st = nodes[p.actor]
      st.status = t - p.end < RECENT_MS ? (p.outcome === 'cancelled' ? 'fail' : 'done') : 'idle'
      st.activity = p.outcome === 'cancelled' ? 'child 취소 관측 · 도구 종료 결과 미확인' : '일을 마치고 결과를 돌려줌'
      st.lastAt = p.end
    }
  }
  for (const id of ROLE_IDS) if (!m.presences.some((p) => p.actor === id) && nodes[id].calls === 0) nodes[id].status = 'off'

  // Main: a running call of its own, else thinking inside a turn, else waiting.
  const mainCalls = active.filter((s) => s.actor === 'main')
  const turn = [...m.turns].reverse().find((x) => x.start <= t)
  const inTurn = !!turn && (turn.end == null || turn.end > t)
  let main: MainState
  if (mainCalls.length) {
    const s = mainCalls[mainCalls.length - 1]
    main = { mode: 'working', label: s.label + (mainCalls.length > 1 ? ` 외 ${mainCalls.length - 1}건` : ''), since: s.start }
  } else if (inTurn) {
    const lastEnd = Math.max(turn!.start, ...m.spans.filter((s) => s.actor === 'main' && s.end != null && s.end <= t).map((s) => s.end as number))
    main = { mode: 'thinking', label: '생각 중 (도구 사용 없음)', since: lastEnd }
  } else {
    main = { mode: 'idle', label: turn?.outcome === 'cancelled' ? 'turn 취소 관측 · 다음 질문을 기다림' : m.turns.length ? '답변을 마치고 다음 질문을 기다림' : '질문을 기다림', since: turn?.end ?? null }
  }
  const mainNode = nodes.main
  mainNode.status = main.mode === 'idle' ? 'idle' : 'active'
  mainNode.activity = main.label
  mainNode.since = main.since
  mainNode.calls = m.spans.filter((s) => s.actor === 'main' && s.start <= t).length
  mainNode.fails = m.spans.filter((s) => s.actor === 'main' && s.status === 'fail' && s.end != null && s.end <= t).length
  mainNode.active = mainCalls

  // Reception: lit briefly when a question arrives.
  const lastReq = [...m.points].reverse().find((p) => p.kind === 'request' && p.t <= t)
  if (lastReq) {
    nodes.reception.calls = m.points.filter((p) => p.kind === 'request' && p.t <= t).length
    nodes.reception.lastAt = lastReq.t
    nodes.reception.lastStart = lastReq.t
    nodes.reception.activity = '질문 접수'
    nodes.reception.status = t - lastReq.t < RECENT_MS ? 'active' : 'idle'
  }

  const saves = m.saves.filter((s) => s.t <= t)
  if (saves.length) {
    const last = saves[saves.length - 1]
    const ship = nodes.shipping
    ship.calls = saves.length
    ship.lastAt = last.t
    ship.lastStart = last.t
    ship.activity = last.accepted == null ? '저장 응답 확인 못 함' : last.accepted ? `승인 · ${last.turnStatus ?? ''}`.trim() : `거절 · ${last.reason ?? last.turnStatus ?? ''}`.trim()
    ship.status = t - last.t < RECENT_MS ? (last.accepted === false ? 'fail' : 'done') : 'idle'
    ship.fails = saves.filter((s) => s.accepted === false).length
  }

  // Database: the workflow clock and the counts in each saved candidate (rooms that make almost no tool calls).
  let workflow: Snapshot['workflow'] = null
  if (m.workflow && m.workflow.start <= t) {
    const stopAt = m.workflow.finish ?? Infinity
    const elapsed = Math.min(t, stopAt) - m.workflow.start
    workflow = {
      elapsed,
      budget: m.workflow.budgetMs,
      left: m.workflow.budgetMs != null ? m.workflow.budgetMs - elapsed : null,
      researchStopped: m.workflow.researchStop != null && m.workflow.researchStop <= t,
      finished: m.workflow.finish != null && m.workflow.finish <= t,
    }
    const vault = nodes.vault
    const wfPoints = m.points.filter((p) => p.kind === 'wf' && p.t <= t)
    vault.calls = wfPoints.length
    const lastWf = wfPoints[wfPoints.length - 1]
    if (lastWf) {
      vault.lastAt = lastWf.t
      vault.lastStart = lastWf.t
      vault.activity = pointLabel(lastWf)
      vault.status = t - lastWf.t < RECENT_MS ? 'done' : 'idle'
    }
  }
  const counts: Snapshot['counts'] = []
  const cand = [...m.candidates].reverse().find((c) => c.t <= t)
  if (cand) {
    for (const room of COUNT_ROOMS) {
      const values = room.keys.map((k) => ({ ko: k.ko, value: cand.counts?.[k.key] ?? null }))
      counts.push({ node: room.node, values, t: cand.t })
      const st = nodes[room.node]
      if (st.lastStart == null || cand.t > st.lastStart) st.lastStart = cand.t
      if (st.status !== 'active') {
        st.activity = `저장된 후보 v${cand.result_version ?? '?'}: ` + values.map((v) => `${v.ko} ${v.value ?? '미측정'}`).join(' · ')
        st.lastAt = cand.t
        st.status = t - cand.t < RECENT_MS ? 'done' : st.status === 'fail' ? 'fail' : 'idle'
      }
    }
  }

  const hostsSeen = m.hosts.filter((h) => h.first <= t).map((h) => h.host)
  const activeHosts = new Set(active.filter((s) => s.target === 'web' && s.host).map((s) => s.host as string))
  if (active.some((s) => s.target === 'web')) {
    nodes.web.status = 'active'
    nodes.web.activity = active.filter((s) => s.target === 'web').map((s) => s.label).join(' · ')
  }

  return { t, main, nodes, active, presence, saves, hostsSeen, activeHosts, counts, workflow, feed: feedLimit ? feedAt(m, t, feedLimit) : [] }
}

function who(actor: string): string {
  if (actor === 'main') return '메인'
  if (actor === 'other_subagent') return '보조'
  return { product_official_researcher: '공식조사', product_review_researcher: '후기조사', product_evidence_reviewer: '근거검토' }[actor] ?? actor
}

export function feedAt(m: SessionModel, t: number, limit: number): FeedItem[] {
  const items: FeedItem[] = []
  for (const s of m.spans) {
    if (s.start <= t) items.push({ key: `${s.key}:s`, t: s.start, who: who(s.actor), label: s.label, tone: 'start', basis: s.basis, node: nodeOf(s) })
    if (s.end != null && s.end <= t && s.status !== 'running') {
      items.push({
        key: `${s.key}:e`, t: s.end, who: who(s.actor), label: `${s.endLabel ?? s.label} · ${secs(s.durationMs)}`,
        tone: ['fail', 'interrupted', 'unknown'].includes(s.status) || s.detail.accepted === false ? 'fail' : 'end', basis: s.basis, node: nodeOf(s),
      })
    }
  }
  for (const p of m.points) {
    if (p.t > t) continue
    items.push({ key: p.key, t: p.t, who: p.basis === 'db_recorded' ? 'DB' : who(p.ev?.actor ?? 'main'), label: pointLabel(p), tone: p.basis === 'db_recorded' ? 'db' : 'point', basis: p.basis, node: p.node })
  }
  items.sort((a, b) => b.t - a.t)
  return items.slice(0, limit)
}

export function nodeOf(s: Span): string {
  if (s.target === 'desk' || s.target === 'main') return s.actor === 'other_subagent' ? 'main' : s.actor
  return s.target
}

export function pointLabel(p: Point): string {
  if (p.wf) {
    const w = p.wf
    const name = ({ research_plan: '조사 계획', source_scan: '자료 훑기', research_stop: '조사 멈춤', analysis_scope: '분석 범위', checkpoint: '중간 점검', finish: '업무 끝' } as Record<string, string>)[w.kind] ?? w.kind
    const bits = [w.host, typeof w.reviews === 'number' ? `후기 ${w.reviews}건` : null, w.code, typeof w.sources === 'number' ? `자료 ${w.sources}건` : null, w.page]
      .filter((x) => typeof x === 'string' && x) as string[]
    return `작업 일지 · ${name}${bits.length ? ' · ' + bits.join(' · ') : ''}`
  }
  if (p.cand) {
    const c = p.cand.counts ?? {}
    const v = (x: number | null | undefined) => (x == null ? '미측정' : String(x))
    return `후보 v${p.cand.result_version ?? '?'} 기록 · 불편 ${v(c.pains)} · 기존 기능 ${v(c.existing_features)} · 남은 불편 ${v(c.remaining_pains)} · 콘셉트 ${v(c.concepts)}`
  }
  return p.label || (p.ev ? labelOf(p.ev) : p.kind)
}
