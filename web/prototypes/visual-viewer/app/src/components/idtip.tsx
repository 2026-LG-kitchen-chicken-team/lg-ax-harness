// Hover or focus an ID chip (P1, R1, C1, a source ID …) in A to see what it stands for. The index is read from the
// story page and the evidence table that build_view.py wrote; nothing else is looked up or inferred.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Block, View } from '../types'

type Entry = { kind: string; text: string }
// light: the chip sits in K, which shows a light card that eases in (index.css "lg-tip"); the other views keep the dark one.
type Tip = { id: string; entry: Entry; left: number; top?: number; bottom?: number; light: boolean }
type Api = { lookup: (id: string) => Entry | undefined; show: (id: string, el: HTMLElement) => void; hide: () => void }
const Ctx = createContext<Api | null>(null)
export const useIdTip = () => useContext(Ctx)

export function buildIdIndex(view: View | null): Map<string, Entry> {
  const map = new Map<string, Entry>()
  if (!view) return map
  const put = (id: unknown, kind: string, text: unknown) => {
    if (typeof id === 'string' && id && typeof text === 'string' && text && !map.has(id)) map.set(id, { kind, text })
  }
  const walk = (blocks: Block[]) => {
    for (const b of blocks) {
      if (b.type === 'claims') for (const it of b.items || []) put(it.id, b.kind_label || '항목', it.text)
      if (b.type === 'flow') for (const n of b.nodes || []) put(n.id, (b.columns || []).find((c: Block) => c.key === n.column)?.title || '항목', n.text)
      if (b.type === 'solutions') for (const s of b.items || []) put(s.id, '제안', s.text)
      if (b.blocks) walk(b.blocks)
    }
  }
  walk(view.pages.find((p) => p.id === 'story')?.blocks || [])
  for (const b of view.pages.find((p) => p.id === 'evidence')?.blocks || []) {
    if (b.type !== 'table' || !(b.columns || []).some((c: Block) => c.key === 'id')) continue
    for (const r of b.rows || []) put(r.id, '근거 원문', [r.quote, r.loc].filter((x) => typeof x === 'string' && x).join(' — '))
  }
  return map
}

export function IdTipProvider({ view, children }: { view: View | null; children: ReactNode }) {
  const index = useMemo(() => buildIdIndex(view), [view])
  const [tip, setTip] = useState<Tip | null>(null)
  const lookup = useCallback((id: string) => index.get(id), [index])
  const show = useCallback((id: string, el: HTMLElement) => {
    const entry = index.get(id)
    if (!entry) return
    const r = el.getBoundingClientRect()
    const left = Math.max(8, Math.min(r.left, window.innerWidth - (el.closest('.skin-ops') ? 424 : 368)))
    const light = !!el.closest('.skin-ops')
    // Open below the chip, or above it near the bottom of the window.
    setTip(r.bottom > window.innerHeight - 200 ? { id, entry, left, light, bottom: window.innerHeight - r.top + 8 } : { id, entry, left, light, top: r.bottom + 8 })
  }, [index])
  const hide = useCallback(() => setTip(null), [])
  useEffect(() => {
    if (!tip) return
    window.addEventListener('scroll', hide, { passive: true, capture: true })
    return () => window.removeEventListener('scroll', hide, { capture: true })
  }, [tip, hide])
  const api = useMemo(() => ({ lookup, show, hide }), [lookup, show, hide])
  return (
    <Ctx.Provider value={api}>
      {children}
      {tip?.light && (
        <div key={tip.id} role="tooltip" data-side={tip.top != null ? 'below' : 'above'}
          className="lg-tip no-print pointer-events-none fixed z-[80] w-max max-w-[min(26rem,calc(100vw-1rem))] rounded-xl border border-[#e3e8e3] bg-white px-4 py-3 text-[13.5px] leading-relaxed text-zinc-800 shadow-[0_14px_36px_-14px_rgb(0_0_0/0.3)]"
          style={{ left: tip.left, top: tip.top, bottom: tip.bottom }}>
          <div className="text-xs text-zinc-500"><span className="font-semibold text-[#2f7d4f]">{tip.id}</span> · {tip.entry.kind}</div>
          {/* K's cards show only the first sentence, so the card here gives the whole text. */}
          <p className="mt-1 whitespace-pre-line">{tip.entry.text}</p>
        </div>
      )}
      {tip && !tip.light && (
        <div role="tooltip" className="no-print pointer-events-none fixed z-[80] w-[22rem] max-w-[calc(100vw-1rem)] rounded-2xl bg-zinc-900 px-4 py-3 text-sm leading-relaxed text-white shadow-xl"
          style={{ left: tip.left, top: tip.top, bottom: tip.bottom }}>
          <div className="text-xs text-zinc-400"><span className="font-mono font-semibold text-white">{tip.id}</span> · {tip.entry.kind}</div>
          <p className="mt-1 line-clamp-6">{tip.entry.text}</p>
        </div>
      )}
    </Ctx.Provider>
  )
}
