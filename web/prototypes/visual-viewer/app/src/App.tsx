import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { IdTipProvider } from './components/idtip'
import { type Hit } from './components/search'
import { scrollToBlock } from './components/shell'
import DashApp from './dash/DashApp'
import { useView } from './lib/useView'
import { mergedTarget, mergeEvidencePages } from './lib/merge'
import { reportVoice, voiceView } from './lib/voice'
import { prunedTarget, pruneForPlanning } from './lib/prune'
import { plainView } from './lib/plain'
import { recolorView } from './lib/ktone'

const hashId = () => decodeURIComponent(location.hash.replace(/^#/, ''))
const read = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const write = (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* storage unavailable */ } }

// The viewer has one view, K 업무형 (dash/DashApp.tsx). The other twelve were removed at the user's request (2026-10-15).
export default function App() {
  const [toasts, setToasts] = useState<{ id: number; msg: string }[]>([])
  const toast = useCallback((msg: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, msg }])
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2400)
  }, [])
  const { view, live, reload, openFile, inline } = useView(toast)
  const [current, setCurrent] = useState<string | null>(null)
  const [big, setBig] = useState(() => read('lgax-text-big') === '1')
  const [searchOpen, setSearchOpen] = useState(false)
  const openSearch = useCallback(() => setSearchOpen(true), [])
  const lastFocus = useRef<string | null>(null)

  // Page choice: keep the current page across refreshes; follow the builder's focus when it changes (new export).
  useEffect(() => {
    if (!view) return
    const has = (id?: string | null) => !!id && view.pages.some((p) => p.id === id)
    const focusChanged = !!view.focus && view.focus !== lastFocus.current
    const booting = lastFocus.current === null && current === null
    lastFocus.current = view.focus || ''
    let target = current
    if (booting) target = has(hashId()) ? hashId() : view.focus || view.pages[0].id
    else if (focusChanged) target = view.focus!
    if (!has(target)) target = view.pages[0].id
    if (target !== current) setCurrent(target)
  }, [view]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const on = () => { const id = hashId(); if (view?.pages.some((p) => p.id === id)) setCurrent(id) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [view])

  // The evidence dashboard and the evidence text are drawn as one page (lib/merge.ts); the view keeps only what the
  // planning work needs (lib/prune.ts), reads in report style (lib/voice.ts), leaves field names out of the visible text
  // (lib/plain.ts) and uses one hue (lib/ktone.ts). build_view.py's data itself is unchanged.
  const shownView = useMemo(() => recolorView(plainView(voiceView(pruneForPlanning(mergeEvidencePages(view))))), [view])
  const target = (id: string | null) => prunedTarget(mergedTarget(id))
  const page = view?.pages.find((p) => p.id === current) || null
  const shownPage = shownView?.pages.find((p) => p.id === target(current)) || null
  useEffect(() => {
    if (!page || !view) return
    try { if (hashId() !== page.id) history.replaceState(null, '', '#' + encodeURIComponent(page.id)) } catch { /* previews may block */ }
    document.title = (shownPage || page).title + ' · ' + (view.app?.title || 'LG AX 상품기획')
  }, [page, shownPage, view])

  const go = (id: string) => {
    try { history.pushState(null, '', '#' + encodeURIComponent(id)) } catch { /* ignore */ }
    setCurrent(id)
    window.scrollTo(0, 0)
  }
  const pick = (h: Hit) => {
    if (h.page.id !== current) go(h.page.id)
    window.setTimeout(() => scrollToBlock(h.block, h.expander), 80)
  }
  const copy = useCallback((text: string) => {
    const done = () => toast('복사했습니다')
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(done, () => toast('복사하지 못했습니다. 직접 선택해 복사하세요.'))
    else toast('복사하지 못했습니다. 직접 선택해 복사하세요.')
  }, [toast])
  const toggleBig = () => setBig((b) => { write('lgax-text-big', b ? '0' : '1'); return !b })

  return (
    <IdTipProvider view={view}>
      <DashApp view={shownView} page={shownPage}
        go={(id) => go(target(id) || id)} pick={pick} copy={copy} live={live} reload={reload}
        openFile={openFile} inline={inline} big={big} toggleBig={toggleBig}
        searchOpen={searchOpen} openSearch={openSearch} closeSearch={() => setSearchOpen(false)} />
      <div className="no-print pointer-events-none fixed right-4 top-20 z-[70] flex flex-col items-end gap-2">
        {toasts.map((t) => <div key={t.id} role="status" className="rounded-full bg-zinc-900 px-4 py-2 text-sm text-white shadow-lg">{reportVoice(t.msg)}</div>)}
      </div>
    </IdTipProvider>
  )
}
