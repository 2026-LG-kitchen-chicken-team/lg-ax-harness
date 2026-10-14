import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Captions, CaptionsOff, ChevronLeft, ChevronRight, FileJson, FileText, Menu, RefreshCw, Search, X } from 'lucide-react'
import { Badge, Button } from './components/ui'
import { BlockView } from './components/blocks'
import { ExhibitPage } from './components/exhibit'
import { IdTipProvider } from './components/idtip'
import { SearchDialog, type Hit } from './components/search'
import { ModeSwitch, useMode } from './components/mode'
import { BackToTop, Empty, ICONS, introOf, LiveDot, noEmoji, scrollToBlock, SearchHotkey, STORY_IDS, TextScale } from './components/shell'
import DashApp, { isSkin } from './dash/DashApp'
import { storyOf } from './lib/story'
import Slides from './variants/Slides'
import Poster from './variants/Poster'
import Editorial from './variants/Editorial'
import Board from './variants/Board'
import Corporate from './variants/Corporate'
import Landing from './variants/Landing'
import { cn, Md } from './lib/utils'
import { useView } from './lib/useView'
import { MERGED_EVIDENCE_SKINS, mergedTarget, mergeEvidencePages } from './lib/merge'
import type { Page, View } from './types'

const LG_RED = 'text-[#d0111b]'

const hashId = () => decodeURIComponent(location.hash.replace(/^#/, ''))
const read = (k: string) => { try { return localStorage.getItem(k) } catch { return null } }
const write = (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* storage unavailable */ } }

export default function App() {
  const [toasts, setToasts] = useState<{ id: number; msg: string }[]>([])
  const toast = useCallback((msg: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, msg }])
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2400)
  }, [])
  const { view, live, reload, openFile, inline } = useView(toast)
  const [current, setCurrent] = useState<string | null>(null)
  const [navOpen, setNavOpen] = useState(false)
  // The page explanation now sits under each title; the floating presentation caption is opt-in.
  const [capHidden, setCapHidden] = useState(() => read('lgax-cap-hidden') !== '0')
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

  const [mode, setMode] = useMode()
  // J, K and M draw the evidence dashboard and the evidence text as one page (lib/merge.ts); the data keeps both.
  const merged = MERGED_EVIDENCE_SKINS.has(mode)
  const shownView = useMemo(() => (merged ? mergeEvidencePages(view) : view), [merged, view])
  const page = view?.pages.find((p) => p.id === current) || null
  const shownPage = shownView?.pages.find((p) => p.id === (merged ? mergedTarget(current) : current)) || null
  useEffect(() => {
    if (!page || !view) return
    try { if (hashId() !== page.id) history.replaceState(null, '', '#' + encodeURIComponent(page.id)) } catch { /* previews may block */ }
    document.title = (shownPage || page).title + ' · ' + (view.app?.title || 'LG AX 상품기획')
  }, [page, shownPage, view])

  const go = (id: string) => {
    try { history.pushState(null, '', '#' + encodeURIComponent(id)) } catch { /* ignore */ }
    setCurrent(id)
    setNavOpen(false)
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
  const toggleCaption = () => setCapHidden((h) => { write('lgax-cap-hidden', h ? '0' : '1'); return !h })
  const toggleBig = () => setBig((b) => { write('lgax-text-big', b ? '0' : '1'); return !b })

  const story = storyOf(view)
  const toastsEl = (
    <div className="no-print pointer-events-none fixed right-4 top-20 z-[70] flex flex-col items-end gap-2">
      {toasts.map((t) => <div key={t.id} role="status" className="rounded-full bg-zinc-900 px-4 py-2 text-sm text-white shadow-lg">{t.msg}</div>)}
    </div>
  )
  // B–E, G and H re-arrange the story page; without one (request-only exports, insights-only views) they fall back to A.
  if (view && story && mode === 'slides') return <>{<Slides view={view} story={story} mode={mode} setMode={setMode} />}{toastsEl}</>
  if (view && story && mode === 'board') return <>{<Board view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'editorial') return <>{<Editorial view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'poster') return <>{<Poster view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'corporate') return <>{<Corporate view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'landing') return <>{<Landing view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  // I–M keep A's menu, pages and blocks and change only the look (dash/DashApp.tsx). They need no story page.
  if (isSkin(mode)) {
    return (
      <IdTipProvider view={view}>
        <DashApp skin={mode} view={shownView} page={shownPage}
          go={(id) => go(merged ? mergedTarget(id) || id : id)} pick={pick} copy={copy} live={live} reload={reload}
          openFile={openFile} inline={inline} mode={mode} setMode={setMode} big={big} toggleBig={toggleBig}
          searchOpen={searchOpen} openSearch={openSearch} closeSearch={() => setSearchOpen(false)} />
        {toastsEl}
      </IdTipProvider>
    )
  }

  const caption = page?.caption && !capHidden ? page.caption : null
  // F keeps A's sidebar and header and draws each page in D's exhibition layout (components/exhibit.tsx).
  const exhibit = mode === 'exhibit'
  return (
    <IdTipProvider view={view}>
      <div className={cn('min-h-dvh bg-background', !exhibit && 'theme-lg')}>
        {!exhibit && <><TextScale big={big} /><SearchHotkey open={openSearch} /></>}
        <Sidebar view={view} current={current} go={go} open={navOpen} close={() => setNavOpen(false)} reload={reload} openFile={openFile} inline={inline} />
        <div className="lg:pl-72">
          <header className="no-print sticky top-0 z-20 flex h-16 items-center gap-2 border-b bg-white/90 px-4 backdrop-blur sm:gap-3 sm:px-6">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setNavOpen(true)} aria-label="단계 메뉴 열기"><Menu className="size-5" /></Button>
            <nav className="flex min-w-0 items-center gap-2 text-sm" aria-label="현재 위치">
              <span className="hidden text-muted-foreground sm:inline">{view?.app?.title || 'LG AX 상품기획'}</span>
              <ChevronRight className="hidden size-3.5 text-zinc-300 sm:block" aria-hidden />
              <span className="truncate text-[15px] font-bold">{page?.nav || page?.title || '시각자료'}</span>
            </nav>
            <div className="ml-auto flex items-center gap-2">
              {!exhibit && view && (
                <button type="button" onClick={openSearch} aria-label="전체 검색 (Ctrl+K)" title="전체 검색 (Ctrl+K)"
                  className="inline-flex h-9 items-center gap-2 rounded-full bg-zinc-100 px-3 text-sm text-zinc-500 hover:bg-zinc-200/70">
                  <Search className="size-4" aria-hidden /><span className="hidden xl:inline">검색</span>
                  <kbd className="hidden rounded border bg-white px-1 font-sans text-[10px] text-zinc-400 xl:inline">Ctrl K</kbd>
                </button>
              )}
              {(story || exhibit) && <ModeSwitch mode={mode} setMode={setMode} compact />}
              <LiveDot live={live} inline={inline} />
              {!exhibit && (
                <button type="button" onClick={toggleBig} aria-pressed={big} title={big ? '글자 보통으로' : '글자 크게'}
                  className={cn('h-9 rounded-full px-3 text-sm font-semibold ring-1 ring-inset', big ? 'bg-zinc-900 text-white ring-zinc-900' : 'ring-border hover:bg-zinc-50')}>
                  가<span className="text-[11px]">{big ? '−' : '+'}</span>
                </button>
              )}
              {page?.caption && (
                <Button variant="outline" size="sm" onClick={toggleCaption} aria-pressed={!capHidden} className="rounded-full">
                  {capHidden ? <Captions className="size-3.5" /> : <CaptionsOff className="size-3.5" />}<span className="hidden sm:inline">{capHidden ? '발표 자막' : '자막 끄기'}</span>
                </Button>
              )}
            </div>
          </header>
          {exhibit ? (
            <main className={cn('@container print-full', caption ? 'pb-40' : 'pb-16')}>
              {view && page ? <ExhibitPage view={view} page={page} story={story} copy={copy} go={go} /> : <div className="px-4 py-8"><Empty /></div>}
            </main>
          ) : (
            <main className={cn('mx-auto grid max-w-[88rem] gap-8 px-4 py-8 sm:px-8 2xl:grid-cols-[minmax(0,1fr)_15rem] print-full', caption ? 'pb-40' : 'pb-16')}>
              <div className="@container flex min-w-0 flex-col gap-5">
                {view && page ? <PageView page={page} pages={view.pages} copy={copy} go={go} /> : <Empty />}
              </div>
              {page && <PageToc page={page} />}
            </main>
          )}
        </div>
        {caption && view && (
          <div role="status" aria-live="polite" className="no-print fixed inset-x-4 bottom-4 z-30 mx-auto max-w-4xl rounded-2xl bg-zinc-950/90 px-5 py-3.5 text-zinc-100 shadow-2xl ring-1 ring-white/10 backdrop-blur lg:left-[calc(18rem+1rem)]">
            <div className="text-[11px] text-zinc-400">{caption.meta || view.context?.meta}</div>
            <div className="mt-0.5 text-balance text-base font-semibold text-white sm:text-lg">{caption.title}</div>
            {caption.text && <p className="mt-0.5 text-sm text-zinc-300">{caption.text}</p>}
            <button type="button" onClick={toggleCaption} aria-label="자막 닫기" className="absolute right-3 top-3 rounded p-1 text-zinc-400 hover:text-white"><X className="size-4" /></button>
          </div>
        )}
        {!exhibit && <BackToTop raised={!!caption} />}
        <SearchDialog view={view} open={searchOpen} close={() => setSearchOpen(false)} pick={pick} />
        {toastsEl}
      </div>
    </IdTipProvider>
  )
}

function PageView({ page, pages, copy, go }: { page: Page; pages: Page[]; copy: (s: string) => void; go: (id: string) => void }) {
  const story = STORY_IDS.has(page.id)
  const intro = introOf(page.caption)
  const i = pages.findIndex((p) => p.id === page.id)
  const prev = pages[i - 1]
  const next = pages[i + 1]
  return (
    <>
      {!story && (
        <header className="mb-3">
          {intro.step && <div className={cn('text-sm font-bold', LG_RED)}>{intro.step}</div>}
          <h1 className="mt-1 text-balance text-[28px] font-bold leading-tight tracking-tight sm:text-[34px]">{page.title}</h1>
          {intro.title && <p className="mt-3 max-w-3xl text-[17px] font-semibold leading-snug text-zinc-800">{intro.title}</p>}
          {intro.text && <p className="mt-1.5 max-w-3xl text-[15px] leading-relaxed text-muted-foreground">{intro.text}</p>}
        </header>
      )}
      {page.blocks.map((b, k) => <div key={k} data-block={k} className="flex min-w-0 scroll-mt-24 flex-col"><BlockView b={b} copy={copy} /></div>)}
      <nav className="no-print mt-10 grid gap-3 sm:grid-cols-2" aria-label="화면 이동">
        {prev ? (
          <button type="button" onClick={() => go(prev.id)} className="flex items-center gap-4 rounded-2xl bg-white p-5 text-left ring-1 ring-border hover:ring-zinc-300">
            <ChevronLeft className="size-5 shrink-0 text-zinc-400" aria-hidden />
            <span className="min-w-0"><span className="block text-xs text-muted-foreground">이전 화면</span><span className="block truncate text-[15px] font-bold">{prev.nav || prev.title}</span></span>
          </button>
        ) : <span className="hidden sm:block" />}
        {next && (
          <button type="button" onClick={() => go(next.id)} className="flex items-center justify-end gap-4 rounded-2xl bg-white p-5 text-right ring-1 ring-border hover:ring-zinc-300">
            <span className="min-w-0"><span className="block text-xs text-muted-foreground">다음 화면</span><span className="block truncate text-[15px] font-bold">{next.nav || next.title}</span></span>
            <ChevronRight className="size-5 shrink-0 text-zinc-400" aria-hidden />
          </button>
        )}
      </nav>
    </>
  )
}

// "이 화면 목차": the page's headings and section labels, with the one being read marked.
function PageToc({ page }: { page: Page }) {
  const items = page.blocks.map((b, i) => ({ b, i })).filter(({ b }) => (b.type === 'heading' || b.type === 'section') && b.text)
  const [active, setActive] = useState(-1)
  useEffect(() => {
    const on = () => {
      let a = -1
      for (const { i } of items) { const el = document.querySelector(`[data-block="${i}"]`); if (el && el.getBoundingClientRect().top < 160) a = i }
      setActive(a)
    }
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [page]) // eslint-disable-line react-hooks/exhaustive-deps
  if (items.length < 2) return null
  return (
    <aside className="no-print hidden 2xl:block">
      <nav className="sticky top-24 rounded-2xl bg-white p-4 ring-1 ring-border" aria-label="이 화면 목차">
        <div className="px-2 pb-2 text-xs font-semibold text-muted-foreground">이 화면 목차</div>
        <ul className="flex flex-col gap-0.5">
          {items.map(({ b, i }) => (
            <li key={i}>
              <button type="button" onClick={() => scrollToBlock(i)} aria-current={active === i ? 'location' : undefined}
                className={cn('w-full rounded-lg px-2 py-1.5 text-left leading-snug', b.type === 'section' ? 'pl-4 text-[13px]' : 'text-sm font-semibold',
                  active === i ? 'bg-[#fdeeee] text-[#d0111b]' : 'text-zinc-600 hover:bg-zinc-50')}>
                {b.text}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}

function Sidebar({ view, current, go, open, close, reload, openFile, inline }: {
  view: View | null; current: string | null; go: (id: string) => void; open: boolean; close: () => void
  reload: () => void; openFile: (f: File) => void; inline: boolean
}) {
  const [over, setOver] = useState(false)
  const ctx = view?.context || {}
  const pages = view?.pages || []
  const groups = [
    { title: '발표', items: pages.filter((p) => STORY_IDS.has(p.id)) },
    { title: '세부 화면', items: pages.filter((p) => !STORY_IDS.has(p.id)) },
  ].filter((g) => g.items.length)
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={close} aria-hidden />}
      <aside className={cn('no-print fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r bg-sidebar transition-transform lg:translate-x-0',
        open ? 'translate-x-0 shadow-2xl' : '-translate-x-full')} aria-label="단계와 세션 자료">
        <div className="flex h-16 items-center gap-3 border-b px-5">
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#ea1917] text-[13px] font-extrabold tracking-tight text-white">LG</span>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-[15px] font-bold">{view?.app?.title || 'LG AX 상품기획'}</div>
            <div className="truncate text-xs text-muted-foreground">{view?.app?.subtitle || '하네스 시각자료 뷰어'}</div>
          </div>
          <Button variant="ghost" size="icon" className="ml-auto lg:hidden" onClick={close} aria-label="메뉴 닫기"><X className="size-4" /></Button>
        </div>
        <nav className="flex-1 overflow-y-auto px-4 py-5" aria-label="단계">
          {groups.map((g) => (
            <div key={g.title} className="mb-5">
              <div className="px-3 pb-2 text-xs font-semibold text-zinc-400">{g.title}</div>
              <ul className="flex flex-col gap-1">
                {g.items.map((p) => {
                  const Icon = ICONS[p.id]
                  const active = p.id === current
                  const n = pages.indexOf(p) + 1
                  return (
                    <li key={p.id}>
                      <button type="button" onClick={() => go(p.id)} aria-current={active ? 'page' : undefined}
                        className={cn('flex h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-[15px]',
                          active ? 'bg-[#fdeeee] font-bold text-[#d0111b]' : 'text-zinc-700 hover:bg-zinc-100')}>
                        {Icon ? <Icon className="size-[18px] shrink-0" aria-hidden /> : <FileText className="size-[18px] shrink-0" aria-hidden />}
                        <span className="truncate">{p.nav || p.title}</span>
                        <span className={cn('ml-auto font-mono text-[11px]', active ? 'text-[#d0111b]/60' : 'text-zinc-300')}>{String(n).padStart(2, '0')}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
          <div className="mt-2 rounded-2xl bg-[#f4f5f7] p-4">
            <div className="text-xs font-semibold text-muted-foreground">마지막 저장</div>
            <div className="mt-2.5 flex flex-wrap gap-1.5">{(ctx.status || [{ text: '데이터 없음' }]).map((s, i) => <Badge key={i} chip={s} />)}</div>
            {ctx.file && (
              <div className="mt-3 flex items-start gap-2 text-xs">
                <FileJson className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0"><div className="break-all font-medium">{ctx.file.name}</div><div className="text-muted-foreground">{ctx.file.size}{ctx.loaded ? ' · ' + ctx.loaded : ''}</div></div>
              </div>
            )}
            <Button variant="outline" size="sm" className="mt-3 h-9 w-full rounded-full bg-white" onClick={reload}><RefreshCw className="size-3.5" />다시 불러오기</Button>
          </div>
          {!inline && (
            <label onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) openFile(f) }}
              className={cn('mt-3 flex cursor-pointer flex-col gap-0.5 rounded-2xl border border-dashed p-4 text-xs text-muted-foreground transition-colors', over && 'border-zinc-900 bg-white')}>
              <span className="font-semibold text-foreground">화면 파일 열기</span>
              <span>view JSON을 고르거나 여기로 끌어 놓기</span>
              <input type="file" accept=".json,application/json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) openFile(f) }} />
            </label>
          )}
        </nav>
        <div className="border-t px-5 py-3 text-[11px] leading-relaxed text-muted-foreground">
          {(ctx.footer || []).map((f, i) => <div key={i} className="truncate"><Md text={noEmoji(f)} /></div>)}
        </div>
      </aside>
    </>
  )
}
