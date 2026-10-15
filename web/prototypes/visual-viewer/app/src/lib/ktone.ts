// The viewer (K 업무형) uses one hue, its own green. The four kinds of items step from light to dark in the order of the work
// (현재 불편 k1 → 기존 기능 k2 → 남은 불편 k3 → 제안 k4), wherever they appear: IDs, link-chart columns, counts and
// bars. Colours that only decorate (blue, purple, green) join the same family; red and orange stay for failures and
// warnings (index.css tones them down). Only tones change; build_view.py's data is untouched.
import type { Block, Tone, View } from '../types'

const KINDS: [string, Tone][] = [['현재 불편', 'k1'], ['기존 기능', 'k2'], ['남은 불편', 'k3'], ['제안', 'k4']]
const kindOf = (s: unknown): Tone | null => KINDS.find(([k]) => String(s ?? '').trim().startsWith(k))?.[1] ?? null
const SECTIONS: Record<string, Tone> = { problem: 'k1', check: 'k2', flow: 'k3', solution: 'k4' }
const DECOR: Record<string, Tone> = { blue: 'k2', green: 'k3', purple: 'k4' }
const HUES = new Set(['blue', 'green', 'red', 'orange', 'purple'])

// p1 → k1, f1 → k2 … from the story page, where every item is listed under its kind.
function kindsById(view: View): Map<string, Tone> {
  const ids = new Map<string, Tone>()
  const walk = (blocks: Block[]) => {
    for (const b of blocks) {
      const kind = b.type === 'claims' ? kindOf(b.kind_label) : null
      if (kind) for (const it of b.items || []) ids.set(it.id, kind)
      if (b.type === 'flow') {
        const cols = new Map<string, Tone | null>((b.columns || []).map((c: Block) => [c.key, kindOf(c.title)]))
        for (const n of b.nodes || []) { const t = cols.get(n.column); if (t) ids.set(n.id, t) }
      }
      if (b.type === 'solutions') for (const s of b.items || []) ids.set(s.id, 'k4')
      if (b.blocks) walk(b.blocks)
    }
  }
  walk(view.pages.find((p) => p.id === 'story')?.blocks || [])
  return ids
}

export function recolorView(view: View | null): View | null {
  if (!view) return view
  const ids = kindsById(view)
  // A chip or item names its kind by an ID ("p1", "→ r1 · 일부 해소", "p1 현재 불편") or by the kind's own words.
  const kindOfItem = (o: Block): Tone | null => {
    const words = String(o.text ?? o.label ?? '').replace(/^→\s*/, '')
    return ids.get(words.split(/[\s·]/)[0]) ?? kindOf(words)
  }
  const pick = (o: Block): string => {
    if (!HUES.has(o.tone)) return o.tone
    return kindOfItem(o) ?? DECOR[o.tone] ?? o.tone
  }
  const walk = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(walk)
    if (!x || typeof x !== 'object') return x
    const o = { ...(x as Block) }
    if (o.type === 'flow') {
      o.columns = (o.columns || []).map((c: Block) => ({ ...c, tone: kindOf(c.title) ?? c.tone }))
      o.nodes = (o.nodes || []).map((n: Block) => ({ ...n, tone: ids.get(n.id) ?? n.tone }))
      o.links = (o.links || []).map((l: Block) => ({ ...l, tone: ids.get(l.to) ?? DECOR[l.tone] ?? l.tone }))
    } else if (o.type === 'story') {
      o.tone = SECTIONS[o.key] ?? o.tone
    } else if (o.type === 'claims') {
      o.tone = kindOf(o.kind_label) ?? o.tone
    } else if (typeof o.tone === 'string') {
      o.tone = pick(o)
    }
    if (Array.isArray(o.point_tones)) o.point_tones = o.point_tones.map((t: string) => DECOR[t] ?? t)
    if (typeof o.type_tone === 'string') o.type_tone = DECOR[o.type_tone] ?? o.type_tone // a quote's 후기 / 제품 사실 label
    for (const [k, v] of Object.entries(o)) if (v && typeof v === 'object') o[k] = walk(v)
    return o
  }
  return walk(view) as View
}
