import type { ReportSource, View } from '../types'

const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
const text = (v: unknown) => v === undefined || typeof v === 'string'

// Guard navigation and common block collection shapes, not the meaning of saved work.
function renderShape(v: unknown, depth = 0): boolean {
  if (depth > 64) return false
  if (Array.isArray(v)) return v.every(item => renderShape(item, depth + 1))
  if (!object(v)) return true
  for (const key of ['blocks', 'items', 'columns', 'cols', 'rows', 'nodes', 'links', 'quotes']) {
    if (v[key] !== undefined && !Array.isArray(v[key])) return false
    if (Array.isArray(v[key]) && !v[key].every(item => item != null)) return false
  }
  if (Array.isArray(v.blocks) && !v.blocks.every(b => object(b) && typeof b.type === 'string')) return false
  // Table cells may be named `type` and contain a chip object. Only entries in
  // an actual blocks collection use a required string discriminator (checked above).
  // The planning transform inserts a feature after columns[0]. Missing/empty columns would
  // otherwise replace a good view before prune/recolor throws. Check shape, not source meaning.
  if (v.type === 'flow') {
    if (!Array.isArray(v.columns) || !v.columns.length || !v.columns.every(c => object(c)
      && typeof c.key === 'string' && !!c.key && text(c.title))) return false
    for (const key of ['nodes', 'links']) if (Array.isArray(v[key]) && !v[key].every(object)) return false
  }
  if (v.type === 'claims' && Array.isArray(v.items) && !v.items.every(object)) return false
  return Object.values(v).every(item => renderShape(item, depth + 1))
}

export function isLgaxView(v: unknown): v is View {
  if (!object(v) || v.kind !== 'lgax-view' || !text(v.generated_at) || !Array.isArray(v.pages) || !v.pages.length) return false
  const ids = new Set<string>()
  for (const p of v.pages) {
    if (!object(p) || typeof p.id !== 'string' || !p.id || ids.has(p.id) || typeof p.title !== 'string'
      || !text(p.nav) || !Array.isArray(p.blocks) || !p.blocks.every(b => object(b) && typeof b.type === 'string' && renderShape(b))) return false
    ids.add(p.id)
    if (p.caption != null && (!object(p.caption) || !text(p.caption.title) || !text(p.caption.text) || !text(p.caption.meta))) return false
  }
  if (v.focus != null && (typeof v.focus !== 'string' || !ids.has(v.focus))) return false
  if (v.app !== undefined && (!object(v.app) || !text(v.app.title) || !text(v.app.subtitle))) return false
  if (v.context !== undefined) {
    if (!object(v.context) || !text(v.context.meta) || !text(v.context.loaded)) return false
    if (v.context.file !== undefined && (!object(v.context.file) || typeof v.context.file.name !== 'string')) return false
    if (v.context.status !== undefined && (!Array.isArray(v.context.status) || !v.context.status.every(s => object(s) && typeof s.text === 'string'))) return false
    if (v.context.footer !== undefined && (!Array.isArray(v.context.footer) || !v.context.footer.every(s => typeof s === 'string'))) return false
  }
  return true
}

// Every payload value, including source bodies, participates; no timestamp/length surrogate.
export const viewIdentity = (v: View): string => JSON.stringify(v)
export function fragmentId(hash: string): string {
  try { return decodeURIComponent(hash.replace(/^#/, '')) } catch { return '' }
}
export function pageTarget(view: View | null, id: string | null, preferred: string | null): string | null {
  if (preferred && view?.pages.some(page => page.id === preferred)) return preferred
  if (id && view?.pages.some(page => page.id === id)) return id
  return view?.pages[0]?.id ?? null
}

export function reportSnapshot(view: View): { identity: string; sourceIdentity: string; source: ReportSource } | null {
  const r = view.report
  if (!r || typeof r.turn_id !== 'string' || !r.turn_id || !object(r.export) || !Array.isArray(r.export.turns) || r.export.turns.length !== 1) return null
  const turn = r.export.turns[0]
  if (!object(turn) || !object(turn.state) || turn.state.turn_id !== r.turn_id) return null
  const sourceIdentity = JSON.stringify(r)
  return { identity: viewIdentity(view), sourceIdentity, source: JSON.parse(sourceIdentity) as ReportSource }
}

export type LoadPhase = 'waiting' | 'loading' | 'ready' | 'error'
export type ViewState = { view: View | null; identity: string; phase: LoadPhase; busy: boolean; lastReadAt: number | null }
export type Transport = (done: (value: unknown) => void, fail: () => void) => () => void
export function initialViewState(value: unknown): ViewState {
  const view = isLgaxView(value) ? value : null
  return { view, identity: view ? viewIdentity(view) : '', phase: view ? 'ready' : 'waiting', busy: false, lastReadAt: null }
}

// Generation checks cover callbacks after cancellation/disposal. Reads never overlap.
export function createViewLoader(options: {
  initial: ViewState; transport: Transport; update: (state: ViewState) => void
  changed?: (manual: boolean, changed: boolean) => void
  schedule: (callback: () => void, ms: number) => unknown; clear: (id: unknown) => void; timeoutMs?: number
}) {
  let state = options.initial
  let generation = 0
  let stopped = false
  let cancel: (() => void) | null = null
  let timer: unknown
  const publish = (next: ViewState) => { state = next; options.update(state) }
  const invalidate = () => { generation++; options.clear(timer); cancel?.(); cancel = null }
  return {
    load(manual = false) {
      if (stopped || state.busy) return false
      const id = ++generation
      publish({ ...state, busy: true, phase: manual || !state.view ? 'loading' : state.phase })
      const finish = (value: unknown, failed: boolean) => {
        if (stopped || id !== generation || !state.busy) return
        invalidate()
        if (failed || (value != null && !isLgaxView(value))) { publish({ ...state, busy: false, phase: 'error' }); return }
        if (value == null) { publish({ ...state, busy: false, phase: state.view ? 'error' : 'waiting' }); return }
        const view = value as View
        const identity = viewIdentity(view)
        const changed = identity !== state.identity
        publish({ view: changed ? view : state.view, identity, phase: 'ready', busy: false, lastReadAt: Date.now() })
        options.changed?.(manual, changed)
      }
      timer = options.schedule(() => finish(null, true), options.timeoutMs ?? 8000)
      try {
        const cleanup = options.transport(value => finish(value, false), () => finish(null, true))
        if (id === generation && state.busy) cancel = cleanup
        else cleanup()
      } catch { finish(null, true) }
      return true
    },
    replace(value: View) {
      if (stopped) return
      invalidate()
      publish({ view: value, identity: viewIdentity(value), phase: 'ready', busy: false, lastReadAt: Date.now() })
    },
    dispose() { stopped = true; invalidate() },
  }
}
