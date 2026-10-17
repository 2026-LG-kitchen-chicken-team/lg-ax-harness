// K 업무형, the viewer's one view: a compact operations dashboard with a light grey menu, the pages, search, ID cards,
// a page head card and prev/next. The other twelve views were removed at the user's request (2026-10-15).
// Only build_view.py's data is shown: nothing from the reference's sample content (names, deltas, offers) is copied.
import { useLayoutEffect, useState, type ReactNode } from 'react'
import { FileJson, FileText, FolderOpen, Info, Menu, NotebookText, RefreshCw, Search, X } from 'lucide-react'
import { Badge } from '../components/ui'
import { BlockView } from '../components/blocks'
import { HoverNote } from '../components/hovernote'
import { SearchDialog, type Hit } from '../components/search'
import { BackToTop, Empty, ICONS, introOf, noEmoji, ReadNotice, SearchHotkey, STORY_IDS, TextScale } from '../components/shell'
import { LOOK, SKIN } from './blocks'
import { SkinContext } from '../lib/skin'
import { cn, Md } from '../lib/utils'
import type { LiveState } from '../lib/useView'
import type { LoadPhase } from '../lib/viewState'
import type { Block, Page, View } from '../types'
import lgLogo from '../assets/lg-logo.png'

type Props = {
  view: View | null; page: Page | null; go: (id: string) => void; pick: (h: Hit) => void; copy: (s: string) => void
  live: LiveState; reload: () => void; openFile: (f: File) => void; inline: boolean
  phase: LoadPhase; busy: boolean; lastReadAt: number | null; fromFile: boolean
  big: boolean; toggleBig: () => void
  searchOpen: boolean; openSearch: () => void; closeSearch: () => void
  // Set when the data carries the export: opens "보고서로 보기" (components/report.tsx).
  openReport?: () => void
}

// Sidebar, menu items and the saved-status card.
const S = {
  aside: 'w-60 border-r border-[#e6e6e6] bg-[#f5f5f5] text-zinc-800', offset: 'lg:pl-60',
  group: 'px-2.5 pb-1 text-[11px] font-medium text-zinc-400', list: 'flex flex-col gap-0.5',
  item: 'flex h-8 w-full items-center gap-2.5 rounded-md px-2.5 text-left text-[13px]',
  on: 'bg-[#e2ece0] font-medium text-[#1f3a24]', off: 'text-zinc-700 hover:bg-black/[0.06] hover:text-zinc-950',
  num: 'ml-auto font-mono text-[10px] text-zinc-400',
  card: 'mx-3 rounded-lg border border-[#e3e3e3] bg-white p-3 text-zinc-700', button: 'mt-2.5 h-8 w-full rounded-md border border-[#e3e3e3] text-xs font-medium hover:border-[#2f8f57]/40 hover:bg-[#f3f8f4] hover:text-[#2f7d4f]',
  foot: 'border-t border-[#e6e6e6] px-4 py-3 text-[11px] leading-relaxed text-zinc-500',
}

export default function DashApp(p: Props) {
  const { view, page } = p
  const [navOpen, setNavOpen] = useState(false)
  const go = (id: string) => { p.go(id); setNavOpen(false) }
  const pick = (h: Hit) => { setNavOpen(false); p.pick(h) }
  const tools = <Tools {...p} />
  return (
    <SkinContext.Provider value={SKIN}>
      <div className="skin-ops min-h-dvh bg-background text-foreground">
        {/* "/" opens the search as well as Ctrl+K. */}
        <TextScale big={p.big} /><SearchHotkey open={p.openSearch} slash />
        <Sidebar {...p} go={go} open={navOpen} close={() => setNavOpen(false)} />
        <div className={S.offset}>
          <TopBar {...p} tools={tools} openNav={() => setNavOpen(true)} />
          <main className="@container mx-auto flex w-full max-w-[1280px] min-w-0 flex-col gap-4 px-4 py-5 print-full sm:px-8">
            {view && page ? <><ReadNotice phase={p.phase} busy={p.busy} reload={p.reload} /><Body {...p} go={go} /></>
              : <Empty phase={p.phase} busy={p.busy} reload={p.reload} />}
          </main>
        </div>
        <BackToTop />
        <SearchDialog view={view ? { ...view, pages: view.pages.filter(x => x.audience !== 'diagnostic' || page?.audience === 'diagnostic') } : null} open={p.searchOpen} close={p.closeSearch} pick={pick} />
      </div>
    </SkinContext.Provider>
  )
}

// 보고서로 보기, search (narrow screens; wider ones have it in the menu), larger text and the live dot.
function Tools({ view, openSearch, big, toggleBig, openReport }: Props) {
  return (
    <div className="flex items-center gap-2">
      {openReport && (
        <button type="button" onClick={openReport} title="이 기획안을 보고서로 보기"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[#e3e3e3] bg-white px-2.5 text-[13px] font-medium text-zinc-700 hover:border-[#2f8f57]/40 hover:bg-[#f3f8f4] hover:text-[#2f7d4f]">
          <NotebookText className="size-4" aria-hidden /><span className="hidden sm:inline">보고서로 보기</span><span className="sr-only sm:hidden">보고서로 보기</span>
        </button>
      )}
      {view && (
        <button type="button" onClick={openSearch} aria-label="전체 검색 (/ 또는 Ctrl+K)" title="전체 검색 (/ 또는 Ctrl+K)"
          className="grid size-8 place-items-center rounded-md border border-[#e3e3e3] bg-white text-zinc-600 lg:hidden"><Search className="size-4" aria-hidden /></button>
      )}
      <button type="button" onClick={toggleBig} aria-pressed={big} title={big ? '글자 보통으로' : '글자 크게'}
        className={cn('h-8 rounded-md border border-[#e3e3e3] bg-white px-2.5 text-sm font-semibold hover:bg-zinc-100', big && 'bg-zinc-900 text-white')}>
        가<span className="text-[11px]">{big ? '−' : '+'}</span>
      </button>
    </div>
  )
}

function TopBar({ view, page, tools, openNav }: Props & { tools: ReactNode; openNav: () => void }) {
  const title = page?.nav || page?.title || '시각자료'
  return (
    <header className="no-print sticky top-0 z-20 flex h-12 items-center gap-2 border-b border-[#ececec] bg-[#fafafa]/95 px-4 text-[13px] backdrop-blur sm:px-6">
      <button type="button" onClick={openNav} aria-label="단계 메뉴 열기" className="grid size-8 shrink-0 place-items-center rounded-md hover:bg-black/5 lg:hidden"><Menu className="size-5" /></button>
      <nav className="flex min-w-0 items-center gap-1.5" aria-label="현재 위치">
        <span className="hidden truncate text-zinc-500 sm:inline">{view?.app?.title || 'LG AX 상품기획'}</span>
        <span className="hidden text-zinc-300 sm:inline">/</span>
        <span className="truncate font-medium text-[#2f8f57]">{title}</span>
      </nav>
      <div className="ml-auto flex items-center gap-3">
        {tools}
      </div>
    </header>
  )
}

// LG mark (the file the user supplied; white made transparent).
function LgMark({ className }: { className?: string }) {
  return <img src={lgLogo} alt="LG" className={cn('shrink-0 object-contain', className)} draggable={false} />
}

function Brand({ view, close }: { view: View | null; close: () => void }) {
  const title = view?.app?.title || 'LG AX 상품기획'
  const sub = view?.app?.subtitle || '하네스 시각자료 뷰어'
  return (
    <div className="flex items-center gap-2 p-3">
      <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg border border-[#e3e3e3] bg-white p-2">
        <LgMark className="size-8" />
        <div className="min-w-0 leading-tight"><div className="truncate text-[11px] text-zinc-500">{sub}</div><div className="truncate text-[13px] font-semibold">{title}</div></div>
      </div>
      <button type="button" onClick={close} aria-label="메뉴 닫기" className="ml-auto grid size-8 shrink-0 place-items-center rounded-md lg:hidden"><X className="size-4" /></button>
    </div>
  )
}

function Sidebar({ view, page, go, open, close, reload, openFile, inline, openSearch, lastReadAt, fromFile, busy }: Props & { open: boolean; close: () => void }) {
  const pages = view?.pages || []
  const groups = [
    { title: '기획', items: pages.filter((x) => x.audience === 'planning' || (!x.audience && STORY_IDS.has(x.id))) },
    { title: '근거·부록', items: pages.filter((x) => x.audience === 'evidence' || (!x.audience && !STORY_IDS.has(x.id))) },
  ].filter((g) => g.items.length)
  const diagnostics = pages.filter(x => x.audience === 'diagnostic')
  const ctx = view?.context || {}
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={close} aria-hidden />}
      <aside className={cn('no-print fixed inset-y-0 left-0 z-40 flex flex-col transition-transform lg:translate-x-0', S.aside, open ? 'translate-x-0 shadow-2xl' : '-translate-x-full')}
        aria-label="단계와 세션 자료">
        <Brand view={view} close={close} />
        {view && (
          <button type="button" onClick={openSearch} className="mx-3 flex h-9 items-center gap-2 rounded-lg border border-[#e3e3e3] bg-white px-2.5 text-[13px] text-zinc-500 hover:text-zinc-800">
            <Search className="size-4" aria-hidden />빠른 검색<kbd className="ml-auto rounded border border-[#e3e3e3] px-1.5 font-sans text-[11px] text-zinc-500">/</kbd>
          </button>
        )}
        {/* The saved-status card scrolls with the menu, so every page stays reachable on a 768px-high screen. */}
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto py-4">
        <nav className="px-3" aria-label="단계">
          {groups.map((g) => (
            <div key={g.title} className="mb-5">
              <div className={S.group}>{g.title}</div>
              <ul className={S.list}>
                {g.items.map((x) => {
                  const Icon = ICONS[x.id] || FileText
                  const active = x.id === page?.id
                  return (
                    <li key={x.id}>
                      <button type="button" onClick={() => go(x.id)} aria-current={active ? 'page' : undefined} className={cn(S.item, active ? S.on : S.off)}>
                        <Icon className="size-4 shrink-0" aria-hidden />
                        <span className="truncate">{x.nav || x.title}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
          {diagnostics.length > 0 && <details className="mb-5" open={page?.audience === 'diagnostic' || undefined}>
            <summary className="cursor-pointer px-2.5 py-2 text-xs text-zinc-500">고급 · 실행 및 진단 기록</summary>
            <ul className={S.list}>{diagnostics.map(x => <li key={x.id}>
              <button type="button" onClick={() => go(x.id)} aria-current={x.id === page?.id ? 'page' : undefined}
                className={cn(S.item, x.id === page?.id ? S.on : S.off)}><FileText className="size-4 shrink-0" aria-hidden />{x.nav || x.title}</button>
            </li>)}</ul>
          </details>}
        </nav>
        <SaveCard view={view} reload={reload} openFile={openFile} inline={inline} lastReadAt={lastReadAt} fromFile={fromFile} busy={busy} className={cn(S.card, 'mt-auto')} />
        </div>
        {page?.audience === 'diagnostic' && (ctx.footer || []).length > 0 && (
          <div className={S.foot}>
            {/* The session ID and usage note are reference lines; they open on hover instead of sitting in the menu. */}
            <HoverNote note={<ul className="flex flex-col gap-1">{(ctx.footer || []).map((f, k) => <li key={k} className="break-all"><Md text={noEmoji(f)} /></li>)}</ul>}
              className="inline-flex items-center gap-1 rounded text-zinc-500 hover:text-zinc-800">
              <Info className="size-3.5" aria-hidden />세션 정보
            </HoverNote>
          </div>
        )}
      </aside>
    </>
  )
}

// "마지막 저장": the export's status chips (의미 검토 전 · 인수 전 included), the file, reload and open-file.
function SaveCard({ view, reload, openFile, inline, className, lastReadAt, fromFile, busy }: {
  view: View | null; reload: () => void; openFile: (f: File) => void; inline: boolean; className?: string
  lastReadAt: number | null; fromFile: boolean; busy: boolean
}) {
  const ctx = view?.context || {}
  return (
    <details className={className} open={!view || undefined}>
      <summary className="cursor-pointer text-xs font-medium text-zinc-500">저장 결과 관리</summary>
      <div className="mt-3">
      <div className="text-xs font-semibold opacity-80">{fromFile ? '직접 연 화면 자료' : '최근 저장 결과'}</div>
      {lastReadAt && <div className="mt-1 text-[11px] text-zinc-500">{fromFile ? '열어 본 시각' : '확인 시각'}: {new Date(lastReadAt).toLocaleTimeString('ko-KR')}</div>}
      {ctx.file && (
        <div className="mt-3 flex items-start gap-2 text-xs">
          <FileJson className="mt-0.5 size-3.5 shrink-0 opacity-60" aria-hidden />
          <div className="min-w-0">
            {/* Names what the file is; its name (a long hash) opens on hover. */}
            <HoverNote note={ctx.file.name} className="text-left font-medium underline decoration-zinc-300 decoration-dotted underline-offset-[3px]">저장된 결과 파일</HoverNote>
            <div className="opacity-70">{ctx.file.size}{ctx.loaded ? ' · ' + ctx.loaded : ''}</div>
          </div>
        </div>
      )}
      <button type="button" onClick={reload} disabled={busy} className={cn('inline-flex items-center justify-center gap-1.5 disabled:opacity-50', S.button)}><RefreshCw className="size-3.5" aria-hidden />{busy ? '화면 연결 확인 중' : '다시 불러오기'}</button>
      {!inline && (
        <label className="mt-2 flex cursor-pointer items-center justify-center gap-1.5 text-xs underline-offset-2 opacity-80 hover:underline">
          <FolderOpen className="size-3.5" aria-hidden />저장한 화면 자료 열기
          <input type="file" accept=".json,application/json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) openFile(f); e.target.value = '' }} />
        </label>
      )}
      </div>
    </details>
  )
}

// Motion 1 (index.css "K motion"): blocks below the first screen wait lowered and transparent, then rise in once
// when they come into view. Marked before the first paint, and only when the motion will run: readers who prefer
// reduced motion, browsers without IntersectionObserver and blocks already on the first screen are never hidden.
function useReveal(pageId: string | undefined) {
  useLayoutEffect(() => {
    if (!pageId || typeof IntersectionObserver === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    // A new page opens at the top (App scrolls there), so "below the first screen" is measured from the page's top.
    const els = [...document.querySelectorAll<HTMLElement>('main [data-block]')]
      .filter((el) => el.getBoundingClientRect().top + window.scrollY > window.innerHeight * 0.92)
    if (!els.length) return
    const pending = new Set(els)
    const show = (el: HTMLElement) => { el.dataset.reveal = 'in'; pending.delete(el); io.unobserve(el) }
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) show(e.target as HTMLElement)
    }, { rootMargin: '0px 0px -6% 0px' })
    // Blocks jumped past (End key, scrollbar drag, a search result further down) never intersect: show them as well.
    const passed = () => { for (const el of pending) if (el.getBoundingClientRect().bottom < 0) show(el) }
    els.forEach((el) => { el.dataset.reveal = 'wait'; io.observe(el) })
    window.addEventListener('scroll', passed, { passive: true })
    return () => {
      io.disconnect()
      window.removeEventListener('scroll', passed)
      els.forEach((el) => { delete el.dataset.reveal })
    }
  }, [pageId])
}

function Body({ view, page, copy }: Props) {
  useReveal(page?.id)
  if (!view || !page) return null
  const pages = view.pages
  const i = pages.findIndex((x) => x.id === page.id)
  return (
    <>
      {!STORY_IDS.has(page.id) && <Head view={view} page={page} n={i + 1} total={pages.length} intro={introOf(page.caption)} />}
      {/* Each top-level block keeps its data-block index (search results scroll to it). */}
      {page.blocks.map((b: Block, k: number) => <div key={k} data-block={k} className="flex min-w-0 scroll-mt-28 flex-col"><BlockView b={b} copy={copy} /></div>)}
    </>
  )
}

type Intro = ReturnType<typeof introOf>

// "이름 : 값" lines about the saved result in the head card: scope, what was loaded and the status chips.
function InfoStrip({ view, className }: { view: View; className?: string }) {
  const ctx = view.context || {}
  const pairs: [string, string][] = [['범위', ctx.meta || ''], ['불러온 자료', ctx.loaded || '']]
  const dt = 'w-16 shrink-0 text-zinc-500'
  return (
    <dl className={cn('grid min-w-0 gap-x-6 gap-y-1 text-[12px] @2xl:grid-cols-2', className)}>
      {pairs.filter(([, v]) => v).map(([k, v]) => (
        <div key={k} className="flex min-w-0 items-baseline gap-2"><dt className={dt}>{k}</dt><span aria-hidden className="text-zinc-400">:</span><dd className="min-w-0 break-all font-medium text-zinc-900">{v}</dd></div>
      ))}
      <div className="flex min-w-0 items-center gap-2"><dt className={dt}>상태</dt><span aria-hidden className="text-zinc-400">:</span>
        <dd className="flex min-w-0 flex-wrap gap-1">{(ctx.status || [{ text: '데이터 없음' }]).map((s, k) => <Badge key={k} chip={s} />)}</dd></div>
    </dl>
  )
}

function Head({ view, page, n, total, intro }: { view: View; page: Page; n: number; total: number; intro: Intro }) {
  const Icon = ICONS[page.id] || FileText
  return (
    <header className="flex flex-col gap-2">
      <div className={cn(LOOK.card, '@container flex flex-col gap-4 p-4 @4xl:flex-row @4xl:items-center')}>
        <div className="flex min-w-0 items-center gap-3.5 @4xl:w-[21rem] @4xl:shrink-0">
          <span className="grid size-12 shrink-0 place-items-center rounded-full bg-[#eef3ec] text-[#2f7d4f]"><Icon className="size-5" aria-hidden /></span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-[20px] font-semibold tracking-tight">{page.title}</h1>
              <span className="shrink-0 rounded-md bg-zinc-100 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-zinc-600" title="화면 순서">{n} / {total}</span>
            </div>
            {intro.step && <div className="mt-0.5 text-[12px] text-zinc-500">{intro.step}</div>}
          </div>
        </div>
        {page.audience === 'diagnostic' && <InfoStrip view={view} className="flex-1 rounded-md border border-[#e6e6e6] px-3 py-2" />}
      </div>
      {(intro.title || intro.text) && (
        <div className="px-0.5 text-[13px]">
          {intro.title && <p className="max-w-3xl font-medium leading-snug text-zinc-800">{intro.title}</p>}
          {intro.text && <p className="mt-1 max-w-3xl leading-relaxed text-zinc-500">{intro.text}</p>}
        </div>
      )}
    </header>
  )
}
