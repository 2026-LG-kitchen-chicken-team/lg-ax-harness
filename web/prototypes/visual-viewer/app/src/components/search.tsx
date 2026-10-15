// Search across every page the builder wrote (text, quotes, table cells, IDs), opened with Ctrl+K or the header button.
// Picking a result opens that page and scrolls to the block. Nothing is fetched or recomputed.
import { useEffect, useMemo, useRef, useState } from 'react'
import { CornerDownLeft, Search } from 'lucide-react'
import { cn } from '../lib/utils'
import { useVoice } from '../lib/voice'
import type { Block, Page, View } from '../types'

export type Hit = { page: Page; block: number; expander: boolean; label: string; texts: string[]; text: string }
const SKIP = new Set(['type', 'tone', 'kind', 'href', 'icon', 'key', 'column', 'mono', 'tip', 'span', 'unit', 'open', 'count', 'search',
  'filter', 'numbered', 'chip', 'type_tone', 'title_icon', 'search_placeholder', 'source', 'href_label', 'copy'])

function strings(v: unknown, out: Set<string>) {
  if (typeof v === 'string') { const s = v.replace(/[`*]/g, '').trim(); if (s) out.add(s.slice(0, 600)) }
  else if (Array.isArray(v)) v.forEach((x) => strings(x, out))
  else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) if (!SKIP.has(k)) strings(x, out)
}

// One entry per top-level block, labelled by its own title so short matches (an ID) still say where they are.
const LABEL: Record<string, string> = { table: '표', quotes: '인용', chain: '대조 열', kpis: '지표', metrics: '지표', chips: '태그', callout: '안내', list: '목록', files: '파일' }
export function buildIndex(view: View | null): Hit[] {
  const out: Hit[] = []
  let heading = ''
  for (const page of view?.pages || []) {
    heading = ''
    page.blocks.forEach((b: Block, i: number) => {
      if (b.type === 'heading' || b.type === 'section') heading = String(b.text || '')
      const set = new Set<string>()
      strings(b, set)
      const own = b.title || b.label || (b.type === 'heading' || b.type === 'section' ? '' : heading) || LABEL[b.type] || ''
      out.push({ page, block: i, expander: b.type === 'expander', label: String(own).replace(/[`*]/g, ''), texts: [...set], text: '' })
    })
  }
  return out
}

function Snippet({ text, q }: { text: string; q: string }) {
  const at = text.toLowerCase().indexOf(q.toLowerCase())
  if (at < 0) return <>{text.slice(0, 120)}</>
  const from = Math.max(0, at - 40)
  return <>{from > 0 && '…'}{text.slice(from, at)}<mark className="rounded bg-[#ffe1e0] px-0.5 text-inherit">{text.slice(at, at + q.length)}</mark>{text.slice(at + q.length, at + q.length + 90)}{at + q.length + 90 < text.length && '…'}</>
}

// No help text while the box is empty (user request 2026-10-15): the result area stays closed until something is typed.
export function SearchDialog({ view, open, close, pick }: { view: View | null; open: boolean; close: () => void; pick: (h: Hit) => void }) {
  const index = useMemo(() => buildIndex(view), [view])
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { if (open) { setSel(0); window.setTimeout(() => input.current?.focus(), 0) } }, [open])
  const hits = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return []
    const out: Hit[] = []
    for (const h of index) {
      const found = h.texts.filter((t) => t.toLowerCase().includes(s))
      if (found.length) out.push({ ...h, text: found.sort((a, b) => b.length - a.length)[0] })
    }
    return out.slice(0, 60)
  }, [index, q])
  if (!open) return null
  const voice = useVoice()
  const choose = (h?: Hit) => { if (h) { pick(h); close() } }
  return (
    <div className="no-print fixed inset-0 z-[75] bg-black/40 px-4 pt-[10vh]" onClick={close} role="dialog" aria-modal="true" aria-label="전체 검색">
      <div className="mx-auto w-full max-w-2xl overflow-hidden rounded-3xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <label className="flex items-center gap-3 border-b px-5">
          <Search className="size-5 shrink-0 text-zinc-400" aria-hidden />
          <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setSel(0) }} placeholder="ID·인용·판단 검색 (예: P1, 불확실, 알림)"
            aria-label="전체 검색" className="h-14 w-full bg-transparent text-base outline-none placeholder:text-zinc-400"
            onKeyDown={(e) => {
              if (e.key === 'Escape') close()
              else if (e.key === 'ArrowDown') { e.preventDefault(); setSel((n) => Math.min(hits.length - 1, n + 1)) }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setSel((n) => Math.max(0, n - 1)) }
              else if (e.key === 'Enter') choose(hits[sel])
            }} />
          <kbd className="hidden shrink-0 whitespace-nowrap rounded-md border px-1.5 py-0.5 font-sans text-[11px] text-zinc-500 sm:block">Esc</kbd>
        </label>
        {q.trim() && <ul className="max-h-[60vh] overflow-y-auto p-2" role="listbox" aria-label="검색 결과">
          {!hits.length && <li className="px-4 py-8 text-center text-sm text-zinc-500">{voice('찾는 내용이 없습니다.')}</li>}
          {hits.map((h, i) => (
            <li key={i} role="option" aria-selected={i === sel}>
              <button type="button" onClick={() => choose(h)} onMouseEnter={() => setSel(i)}
                className={cn('flex w-full items-start gap-3 rounded-2xl px-4 py-3 text-left', i === sel ? 'bg-zinc-100' : '')}>
                <span className="mt-0.5 shrink-0 rounded-full bg-zinc-900 px-2 py-0.5 text-[11px] font-semibold text-white">{h.page.nav || h.page.title}</span>
                <span className="min-w-0 flex-1 text-sm leading-relaxed text-zinc-700">
                  {h.label && h.label !== h.text && <span className="mr-2 font-semibold text-zinc-900">{h.label}</span>}<Snippet text={h.text} q={q.trim()} />
                </span>
                {i === sel && <CornerDownLeft className="mt-1 size-4 shrink-0 text-zinc-400" aria-hidden />}
              </button>
            </li>
          ))}
        </ul>}
        <div className="flex gap-4 border-t px-5 py-2.5 text-[11px] text-zinc-500"><span>↑↓ 이동</span><span>Enter 열기</span><span>Esc 닫기</span>{hits.length > 0 && <span className="ml-auto">{hits.length === 60 ? '앞의 60곳만 표시' : `${hits.length}곳`}</span>}</div>
      </div>
    </div>
  )
}
