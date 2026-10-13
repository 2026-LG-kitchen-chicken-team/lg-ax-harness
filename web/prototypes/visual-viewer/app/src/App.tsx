import { useCallback, useEffect, useRef, useState } from 'react'
import {
  BarChart3, Captions, CaptionsOff, FileJson, FileText, Filter, GitCompareArrows, History, Home, Lightbulb, Menu,
  Package, RefreshCw, Sparkles, X,
} from 'lucide-react'
import { Badge, Button } from './components/ui'
import { Blocks } from './components/blocks'
import { ExhibitPage } from './components/exhibit'
import { ModeSwitch, useMode } from './components/mode'
import { storyOf } from './lib/story'
import Slides from './variants/Slides'
import Poster from './variants/Poster'
import Editorial from './variants/Editorial'
import Board from './variants/Board'
import { cn, Md } from './lib/utils'
import { useView, type LiveState } from './lib/useView'
import type { Page, View } from './types'

const ICONS: Record<string, typeof Home> = {
  story: Sparkles, overview: Home, dashboard: BarChart3, screening: Filter, compare: GitCompareArrows,
  concepts: Lightbulb, history: History, evidence: FileText, export: Package,
}
const STORY_IDS = new Set(['story'])

const hashId = () => decodeURIComponent(location.hash.replace(/^#/, ''))

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
  const [capHidden, setCapHidden] = useState(() => { try { return localStorage.getItem('lgax-cap-hidden') === '1' } catch { return false } })
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

  const page = view?.pages.find((p) => p.id === current) || null
  useEffect(() => {
    if (!page || !view) return
    try { if (hashId() !== page.id) history.replaceState(null, '', '#' + encodeURIComponent(page.id)) } catch { /* previews may block */ }
    document.title = page.title + ' · ' + (view.app?.title || 'LG AX 상품기획')
  }, [page, view])

  const go = (id: string) => {
    try { history.pushState(null, '', '#' + encodeURIComponent(id)) } catch { /* ignore */ }
    setCurrent(id)
    setNavOpen(false)
    window.scrollTo(0, 0)
  }
  const copy = useCallback((text: string) => {
    const done = () => toast('복사했습니다')
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(done, () => toast('복사하지 못했습니다. 직접 선택해 복사하세요.'))
    else toast('복사하지 못했습니다. 직접 선택해 복사하세요.')
  }, [toast])
  const toggleCaption = () => {
    setCapHidden((h) => { try { localStorage.setItem('lgax-cap-hidden', h ? '0' : '1') } catch { /* storage unavailable */ } return !h })
  }

  const [mode, setMode] = useMode()
  const story = storyOf(view)
  const toastsEl = (
    <div className="no-print pointer-events-none fixed right-4 top-16 z-[70] flex flex-col items-end gap-2">
      {toasts.map((t) => <div key={t.id} role="status" className="rounded-lg bg-zinc-900 px-3.5 py-2 text-sm text-white shadow-lg">{t.msg}</div>)}
    </div>
  )
  // B and C re-arrange the story page; without one (request-only exports, insights-only views) they fall back to A.
  if (view && story && mode === 'slides') return <>{<Slides view={view} story={story} mode={mode} setMode={setMode} />}{toastsEl}</>
  if (view && story && mode === 'board') return <>{<Board view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'editorial') return <>{<Editorial view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>
  if (view && story && mode === 'poster') return <>{<Poster view={view} story={story} mode={mode} setMode={setMode} copy={copy} />}{toastsEl}</>

  const caption = page?.caption && !capHidden ? page.caption : null
  // F keeps A's sidebar, header and colours and draws each page in D's exhibition layout (components/exhibit.tsx).
  const exhibit = mode === 'exhibit'
  return (
    <div className="min-h-dvh bg-background">
      <Sidebar view={view} current={current} go={go} open={navOpen} close={() => setNavOpen(false)} reload={reload} openFile={openFile} inline={inline} />
      <div className="lg:pl-72">
        <header className="no-print sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-white/80 px-4 backdrop-blur sm:px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setNavOpen(true)} aria-label="단계 메뉴 열기"><Menu className="size-4" /></Button>
          <nav className="flex min-w-0 items-center gap-2 text-sm" aria-label="현재 위치">
            <span className="hidden text-muted-foreground sm:inline">{view?.app?.title || 'LG AX 상품기획'}</span>
            <span className="hidden text-muted-foreground sm:inline">/</span>
            <span className="truncate font-medium">{page?.nav || page?.title || '시각자료'}</span>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            {(story || exhibit) && <ModeSwitch mode={mode} setMode={setMode} className="hidden md:inline-flex" />}
            <LiveDot live={live} inline={inline} />
            {page?.caption && (
              <Button variant="outline" size="sm" onClick={toggleCaption} aria-pressed={!capHidden}>
                {capHidden ? <Captions className="size-3.5" /> : <CaptionsOff className="size-3.5" />}{capHidden ? '자막 보기' : '자막 끄기'}
              </Button>
            )}
          </div>
        </header>
        {exhibit ? (
          <main className={cn('@container print-full', caption ? 'pb-40' : 'pb-16')}>
            {view && page ? <ExhibitPage view={view} page={page} story={story} copy={copy} go={go} /> : <div className="px-4 py-8"><Empty /></div>}
          </main>
        ) : (
          <main className={cn('@container mx-auto flex max-w-6xl flex-col gap-5 px-4 py-8 sm:px-8 print-full', caption ? 'pb-40' : 'pb-16')}>
            {view && page ? <PageView page={page} copy={copy} /> : <Empty />}
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
      {toastsEl}
    </div>
  )
}

function PageView({ page, copy }: { page: Page; copy: (s: string) => void }) {
  const story = STORY_IDS.has(page.id)
  return (
    <>
      {!story && (
        <div className="mb-1 flex items-start gap-3">
          {page.title_icon && <span aria-hidden className="text-2xl leading-9">{page.title_icon}</span>}
          <h1 className="text-balance text-2xl font-bold leading-9 tracking-tight sm:text-3xl">{page.title}</h1>
        </div>
      )}
      <Blocks blocks={page.blocks} copy={copy} />
    </>
  )
}

function LiveDot({ live, inline }: { live: LiveState; inline: boolean }) {
  const text = inline ? '저장된 실행 결과 · 단일 보고서' : live === 'on' ? '저장된 실행 결과 · 자동 갱신' : live === 'off' ? '데이터 파일 없음' : '저장된 실행 결과'
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:inline-flex">
      <span className={cn('size-2 rounded-full', live === 'on' ? 'bg-emerald-500' : live === 'off' ? 'bg-rose-500' : 'bg-zinc-300')} />{text}
    </span>
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
        <div className="flex h-14 items-center gap-2.5 border-b px-4">
          <span className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-rose-500 to-fuchsia-600 text-sm font-bold text-white">LG</span>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-semibold">{view?.app?.title || 'LG AX 상품기획'}</div>
            <div className="truncate text-xs text-muted-foreground">{view?.app?.subtitle || '하네스 시각자료 뷰어'}</div>
          </div>
          <Button variant="ghost" size="icon" className="ml-auto lg:hidden" onClick={close} aria-label="메뉴 닫기"><X className="size-4" /></Button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="단계">
          {groups.map((g) => (
            <div key={g.title} className="mb-4">
              <div className="px-2 pb-1.5 text-[11px] font-medium text-muted-foreground">{g.title}</div>
              <ul className="flex flex-col gap-0.5">
                {g.items.map((p) => {
                  const Icon = ICONS[p.id]
                  const active = p.id === current
                  return (
                    <li key={p.id}>
                      <button type="button" onClick={() => go(p.id)} aria-current={active ? 'page' : undefined}
                        className={cn('flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm',
                          active ? 'bg-zinc-900 font-medium text-white' : 'text-zinc-700 hover:bg-zinc-200/60')}>
                        {Icon ? <Icon className="size-4 shrink-0" aria-hidden /> : <span aria-hidden className="w-4 text-center">{p.icon || '📄'}</span>}
                        <span className="truncate">{p.nav || p.title}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
          <div className="mt-2 rounded-xl border bg-white p-3">
            <div className="text-[11px] font-medium text-muted-foreground">마지막 저장</div>
            <div className="mt-2 flex flex-wrap gap-1.5">{(ctx.status || [{ text: '데이터 없음' }]).map((s, i) => <Badge key={i} chip={s} />)}</div>
            {ctx.file && (
              <div className="mt-3 flex items-start gap-2 text-xs">
                <FileJson className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0"><div className="break-all font-medium">{ctx.file.name}</div><div className="text-muted-foreground">{ctx.file.size}{ctx.loaded ? ' · ' + ctx.loaded : ''}</div></div>
              </div>
            )}
            <Button variant="outline" size="sm" className="mt-3 w-full" onClick={reload}><RefreshCw className="size-3.5" />다시 불러오기</Button>
          </div>
          {!inline && (
            <label onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) openFile(f) }}
              className={cn('mt-3 flex cursor-pointer flex-col gap-0.5 rounded-xl border border-dashed p-3 text-xs text-muted-foreground transition-colors', over && 'border-zinc-900 bg-white')}>
              <span className="font-medium text-foreground">화면 파일 열기</span>
              <span>view JSON을 고르거나 여기로 끌어 놓기</span>
              <input type="file" accept=".json,application/json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) openFile(f) }} />
            </label>
          )}
        </nav>
        <div className="border-t px-4 py-3 text-[11px] leading-relaxed text-muted-foreground">
          {(ctx.footer || []).map((f, i) => <div key={i} className="truncate"><Md text={f} /></div>)}
        </div>
      </aside>
    </>
  )
}

function Empty() {
  return (
    <div className="mx-auto mt-16 max-w-xl text-center">
      <div className="text-4xl" aria-hidden>⏳</div>
      <h1 className="mt-4 text-2xl font-bold tracking-tight">시각자료를 기다리는 중</h1>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        CLI가 이 폴더에 <b>view-data.js</b>를 만들면 화면이 자동으로 그려집니다. 이미 만든 view JSON이 있으면 왼쪽에서 여세요.
      </p>
      <pre className="mt-6 overflow-x-auto rounded-xl bg-zinc-950 p-4 text-left font-mono text-xs text-zinc-100">python build_view.py --export &lt;export 파일&gt; --open</pre>
    </div>
  )
}
