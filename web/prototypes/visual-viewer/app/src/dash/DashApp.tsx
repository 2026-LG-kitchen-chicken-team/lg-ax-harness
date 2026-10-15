// Dashboard views I–M: A's menu, nine pages, search, ID cards, page intro and prev/next, drawn in the look of four
// dashboard references (I navy sidebar, J monochrome rounded, K compact operations, L analytics with a right column)
// and M, which puts K's compact layout and page information into J's black-and-white look.
// Only build_view.py's data is shown: nothing from the references' sample content (names, deltas, offers) is copied.
import { useEffect, useLayoutEffect, useState, type ReactNode } from 'react'
import { ChevronLeft, ChevronRight, FileJson, FileText, FolderOpen, Info, Menu, RefreshCw, Search, X } from 'lucide-react'
import { Badge } from '../components/ui'
import { BlockView } from '../components/blocks'
import { HoverNote } from '../components/hovernote'
import { SearchDialog, type Hit } from '../components/search'
import { ModeSwitch, type Mode } from '../components/mode'
import { BackToTop, Empty, ICONS, introOf, LiveDot, noEmoji, scrollToBlock, SearchHotkey, STORY_IDS, TextScale } from '../components/shell'
import { lookOf, SKINS } from './blocks'
import { SkinContext, type SkinId } from '../lib/skin'
import { cn, Md } from '../lib/utils'
import type { LiveState } from '../lib/useView'
import type { Block, Page, View } from '../types'
import lgLogo from '../assets/lg-logo.png'

const IDS: SkinId[] = ['navy', 'mono', 'ops', 'analytics', 'monoops']
export const isSkin = (m: string): m is SkinId => (IDS as string[]).includes(m)

type Props = {
  skin: SkinId; view: View | null; page: Page | null; go: (id: string) => void; pick: (h: Hit) => void; copy: (s: string) => void
  live: LiveState; reload: () => void; openFile: (f: File) => void; inline: boolean
  mode: Mode; setMode: (m: Mode) => void; big: boolean; toggleBig: () => void
  searchOpen: boolean; openSearch: () => void; closeSearch: () => void
}

// Sidebar, menu items and the saved-status card per view.
const SIDE: Record<SkinId, { aside: string; offset: string; group: string; list: string; item: string; on: string; off: string; num?: string; numOn?: string; card: string; button: string; foot: string }> = {
  navy: {
    aside: 'w-64 bg-[#1d2131] text-[#c3c7d4]', offset: 'lg:pl-64',
    group: 'px-6 pb-2 text-[11px] font-semibold tracking-[0.16em] text-[#6e7488]', list: 'flex flex-col',
    item: 'flex h-11 w-full items-center gap-3 px-6 text-left text-[14.5px]',
    on: 'bg-white/[0.09] font-semibold text-white shadow-[inset_3px_0_0_#8a93f2]', off: 'text-[#c3c7d4] hover:bg-white/5 hover:text-white',
    num: 'ml-auto font-mono text-[11px] text-white/30',
    card: 'mx-4 rounded-xl bg-white/[0.06] p-4 text-[#c3c7d4]', button: 'mt-3 h-9 w-full rounded-lg bg-white/10 text-xs font-medium text-white hover:bg-white/15',
    foot: 'border-t border-white/10 px-6 py-3 text-[11px] leading-relaxed text-[#8a90a2]',
  },
  mono: {
    aside: 'w-68 bg-white text-zinc-900', offset: 'lg:pl-68',
    group: 'px-5 pb-2 text-xs text-zinc-400', list: 'flex flex-col gap-1',
    item: 'flex h-12 w-full items-center gap-3 rounded-full pl-1.5 pr-5 text-left text-[15px]',
    on: 'bg-zinc-950 font-medium text-white', off: 'text-zinc-700 hover:bg-zinc-100',
    card: 'mx-5 rounded-[24px] bg-[#f4f4f4] p-5 text-zinc-700', button: 'mt-3 h-10 w-full rounded-full bg-zinc-950 text-xs font-medium text-white hover:bg-zinc-800',
    foot: 'px-8 py-4 text-[11px] leading-relaxed text-zinc-400',
  },
  ops: {
    aside: 'w-60 border-r border-[#e6e6e6] bg-[#f5f5f5] text-zinc-800', offset: 'lg:pl-60',
    group: 'px-2.5 pb-1 text-[11px] font-medium text-zinc-400', list: 'flex flex-col gap-0.5',
    item: 'flex h-8 w-full items-center gap-2.5 rounded-md px-2.5 text-left text-[13px]',
    on: 'bg-[#e2ece0] font-medium text-[#1f3a24]', off: 'text-zinc-700 hover:bg-black/[0.06] hover:text-zinc-950',
    num: 'ml-auto font-mono text-[10px] text-zinc-400',
    card: 'mx-3 rounded-lg border border-[#e3e3e3] bg-white p-3 text-zinc-700', button: 'mt-2.5 h-8 w-full rounded-md border border-[#e3e3e3] text-xs font-medium hover:border-[#2f8f57]/40 hover:bg-[#f3f8f4] hover:text-[#2f7d4f]',
    foot: 'border-t border-[#e6e6e6] px-4 py-3 text-[11px] leading-relaxed text-zinc-500',
  },
  analytics: {
    aside: 'w-60 border-r border-[#ececee] bg-white text-zinc-800', offset: 'lg:pl-60',
    group: 'px-3 pb-1.5 text-[11px] font-medium text-zinc-400', list: 'flex flex-col gap-0.5',
    item: 'flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-left text-[14px]',
    on: 'bg-orange-50 font-medium text-orange-600', off: 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900',
    card: 'mx-3 rounded-xl border border-[#ececee] p-4 text-zinc-700', button: 'mt-3 h-9 w-full rounded-lg bg-zinc-900 text-[13px] font-medium text-white hover:bg-zinc-800',
    foot: 'border-t border-[#ececee] px-4 py-3 text-[11px] leading-relaxed text-zinc-500',
  },
  monoops: {
    aside: 'w-64 bg-white text-zinc-900', offset: 'lg:pl-64',
    group: 'px-4 pb-1.5 text-[11px] text-zinc-400', list: 'flex flex-col gap-0.5',
    item: 'flex h-10 w-full items-center gap-2.5 rounded-full pl-1 pr-4 text-left text-[14px]',
    on: 'bg-zinc-950 font-medium text-white', off: 'text-zinc-700 hover:bg-zinc-100',
    num: 'ml-auto font-mono text-[10px] text-zinc-400', numOn: 'text-white/50',
    card: 'mx-4 rounded-[20px] bg-[#f4f4f4] p-4 text-zinc-700', button: 'mt-3 h-9 w-full rounded-full bg-zinc-950 text-xs font-medium text-white hover:bg-zinc-800',
    foot: 'px-6 py-3 text-[11px] leading-relaxed text-zinc-400',
  },
}

// When build_view.py made this view's data (not when the result was saved).
const builtAt = (view: View | null) => (view?.generated_at ? view.generated_at.slice(0, 16).replace('T', ' ') : '')
// J, K and M open the search with "/" as well as Ctrl+K.
const SLASH = new Set<SkinId>(['mono', 'ops', 'monoops'])

export default function DashApp(p: Props) {
  const { skin, view, page } = p
  const [navOpen, setNavOpen] = useState(false)
  const go = (id: string) => { p.go(id); setNavOpen(false) }
  const S = SIDE[skin]
  const pages = view?.pages || []
  const i = page ? pages.findIndex((x) => x.id === page.id) : -1
  const next = i >= 0 ? pages[i + 1] : undefined
  const pick = (h: Hit) => { setNavOpen(false); p.pick(h) }
  const tools = <Tools {...p} />
  return (
    <SkinContext.Provider value={SKINS[skin]}>
      <div className={cn('min-h-dvh bg-background text-foreground', 'skin-' + skin)}>
        <TextScale big={p.big} /><SearchHotkey open={p.openSearch} slash={SLASH.has(skin)} />
        <Sidebar {...p} go={go} open={navOpen} close={() => setNavOpen(false)} />
        <div className={S.offset}>
          <TopBar {...p} tools={tools} openNav={() => setNavOpen(true)} />
          <div className={skin === 'analytics' ? 'xl:grid xl:grid-cols-[minmax(0,1fr)_19rem]' : ''}>
            <main className={cn('@container flex min-w-0 flex-col print-full', {
              navy: 'mx-auto max-w-[96rem] gap-5 px-4 py-6 sm:px-7', mono: 'mx-auto max-w-[96rem] gap-6 px-4 pb-12 pt-4 sm:px-8',
              ops: 'gap-3 px-4 py-4 sm:px-6', analytics: 'gap-5 px-4 pb-10 sm:px-6', monoops: 'gap-4 px-4 pb-10 pt-4 sm:px-6',
            }[skin])}>
              {view && page ? <Body {...p} go={go} /> : <Empty />}
            </main>
            {skin === 'analytics' && view && page && <Rail {...p} view={view} next={next} go={go} />}
          </div>
        </div>
        <BackToTop />
        <SearchDialog view={view} open={p.searchOpen} close={p.closeSearch} pick={pick} quiet={skin === 'ops'} />
      </div>
    </SkinContext.Provider>
  )
}

// Search, view switch, larger text and the live dot, styled per view.
function Tools({ skin, view, openSearch, mode, setMode, big, toggleBig, live, inline }: Props) {
  const search = {
    navy: <button type="button" onClick={openSearch} aria-label="전체 검색 (Ctrl+K)" title="전체 검색 (Ctrl+K)"
      className="flex h-10 items-center gap-2 rounded-lg border border-[#e3e6ee] px-3 text-[13px] text-[#9aa0b2] hover:border-[#cfd3e6] sm:w-60">
      <Search className="size-4" aria-hidden /><span className="hidden sm:inline">ID·인용·판단 검색</span><kbd className="ml-auto hidden rounded border border-[#e3e6ee] px-1 font-sans text-[10px] sm:inline">Ctrl K</kbd></button>,
    mono: <button type="button" onClick={openSearch} aria-label="전체 검색 (/ 또는 Ctrl+K)" title="전체 검색 (/ 또는 Ctrl+K)"
      className="flex h-11 items-center gap-2 rounded-full bg-white px-4 text-sm text-zinc-600 hover:text-zinc-950">
      <Search className="size-4" aria-hidden /><span className="hidden sm:inline">검색</span><kbd className="hidden rounded-full bg-zinc-100 px-2 font-sans text-[11px] text-zinc-500 md:inline">/</kbd></button>,
    ops: <button type="button" onClick={openSearch} aria-label="전체 검색 (/ 또는 Ctrl+K)" title="전체 검색 (/ 또는 Ctrl+K)"
      className="grid size-8 place-items-center rounded-md border border-[#e3e3e3] bg-white text-zinc-600 lg:hidden"><Search className="size-4" aria-hidden /></button>,
    analytics: <button type="button" onClick={openSearch} aria-label="전체 검색 (Ctrl+K)" title="전체 검색 (Ctrl+K)"
      className="flex h-9 items-center gap-2 rounded-lg bg-zinc-900 px-3 text-[13px] font-medium text-white hover:bg-zinc-800">
      <Search className="size-4" aria-hidden /><span className="hidden sm:inline">검색</span><kbd className="hidden rounded bg-white/15 px-1 font-sans text-[10px] md:inline">Ctrl K</kbd></button>,
    monoops: <button type="button" onClick={openSearch} aria-label="전체 검색 (/ 또는 Ctrl+K)" title="전체 검색 (/ 또는 Ctrl+K)"
      className="grid size-9 place-items-center rounded-full bg-white text-zinc-600 lg:hidden"><Search className="size-4" aria-hidden /></button>,
  }[skin]
  const bigCls = {
    navy: 'h-9 rounded-lg px-2.5 ring-1 ring-inset ring-[#e3e6ee]', mono: 'h-11 rounded-full bg-white px-4', ops: 'h-8 rounded-md border border-[#e3e3e3] bg-white px-2.5 hover:bg-zinc-100',
    analytics: 'h-9 rounded-lg px-2.5 ring-1 ring-inset ring-[#e4e4e7]', monoops: 'h-9 rounded-full bg-white px-3',
  }[skin]
  return (
    <div className="flex items-center gap-2">
      {view && search}
      <ModeSwitch mode={mode} setMode={setMode} compact={skin !== 'mono'}
        className={skin === 'mono' ? '[&>button]:h-11 [&>button]:rounded-full [&>button]:bg-white [&>button]:px-4' : skin === 'monoops' ? '[&>button]:h-9 [&>button]:rounded-full [&>button]:bg-white' : undefined} />
      <button type="button" onClick={toggleBig} aria-pressed={big} title={big ? '글자 보통으로' : '글자 크게'}
        className={cn('text-sm font-semibold', bigCls, big && (skin === 'navy' ? 'bg-[#4f5bd5] text-white ring-[#4f5bd5]' : skin === 'analytics' ? 'bg-orange-500 text-white ring-orange-500' : 'bg-zinc-900 text-white'))}>
        가<span className="text-[11px]">{big ? '−' : '+'}</span>
      </button>
      <LiveDot live={live} inline={inline} wide="never" />
    </div>
  )
}

function TopBar({ skin, view, page, tools, openNav }: Props & { tools: ReactNode; openNav: () => void }) {
  const menu = (cls: string) => (
    <button type="button" onClick={openNav} aria-label="단계 메뉴 열기" className={cn('grid shrink-0 place-items-center lg:hidden', cls)}><Menu className="size-5" /></button>
  )
  const title = page?.nav || page?.title || '시각자료'
  if (skin === 'navy') {
    return (
      <header className="no-print sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-[#eceef3] bg-white px-4 sm:px-7">
        {menu('size-9 rounded-lg hover:bg-[#f5f6fa]')}
        <div className="min-w-0 flex-1 truncate text-[19px] font-bold tracking-tight text-[#1d2131]">{page?.title || '시각자료'}</div>
        {tools}
      </header>
    )
  }
  const at = builtAt(view)
  if (skin === 'mono') {
    return (
      <header className="no-print flex items-center gap-2 px-4 pt-5 sm:px-8">
        {menu('size-11 rounded-full bg-white')}
        {at && <span className="hidden text-[13px] text-zinc-500 md:inline" title="build_view.py가 이 화면 자료를 만든 시각">화면 생성: {at}</span>}
        <div className="ml-auto">{tools}</div>
      </header>
    )
  }
  if (skin === 'monoops') {
    return (
      <header className="no-print sticky top-0 z-20 flex h-14 items-center gap-2 bg-[#ececec]/90 px-4 text-[13px] backdrop-blur sm:px-6">
        {menu('size-9 rounded-full bg-white')}
        <nav className="flex min-w-0 items-center gap-1.5" aria-label="현재 위치">
          <span className="hidden truncate text-zinc-500 sm:inline">{view?.app?.title || 'LG AX 상품기획'}</span>
          <span className="hidden text-zinc-400 sm:inline">/</span>
          <span className="truncate font-semibold text-zinc-950">{title}</span>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {at && <span className="hidden text-zinc-500 xl:inline" title="build_view.py가 이 화면 자료를 만든 시각">화면 생성: {at}</span>}
          {tools}
        </div>
      </header>
    )
  }
  if (skin === 'ops') {
    return (
      <header className="no-print sticky top-0 z-20 flex h-12 items-center gap-2 border-b border-[#ececec] bg-[#fafafa]/95 px-4 text-[13px] backdrop-blur sm:px-6">
        {menu('size-8 rounded-md hover:bg-black/5')}
        <nav className="flex min-w-0 items-center gap-1.5" aria-label="현재 위치">
          <span className="hidden truncate text-zinc-500 sm:inline">{view?.app?.title || 'LG AX 상품기획'}</span>
          <span className="hidden text-zinc-300 sm:inline">/</span>
          <span className="truncate font-medium text-[#2f8f57]">{title}</span>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {at && <span className="hidden text-zinc-500 xl:inline" title="build_view.py가 이 화면 자료를 만든 시각">화면 생성: {at}</span>}
          {tools}
        </div>
      </header>
    )
  }
  return (
    <header className="no-print sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-[#ececee] bg-white px-4 sm:px-6">
      {menu('size-9 rounded-lg hover:bg-zinc-100')}
      <div className="min-w-0 flex-1 truncate text-[16px] font-semibold text-zinc-900">{page?.title || '시각자료'}</div>
      {tools}
    </header>
  )
}

// LG mark (the file the user supplied; white made transparent). On the dark navy sidebar it sits on a white tile.
function LgMark({ className }: { className?: string }) {
  return <img src={lgLogo} alt="LG" className={cn('shrink-0 object-contain', className)} draggable={false} />
}

function Brand({ skin, view, close }: { skin: SkinId; view: View | null; close: () => void }) {
  const title = view?.app?.title || 'LG AX 상품기획'
  const sub = view?.app?.subtitle || '하네스 시각자료 뷰어'
  const x = <button type="button" onClick={close} aria-label="메뉴 닫기" className="ml-auto grid size-8 shrink-0 place-items-center rounded-md lg:hidden"><X className="size-4" /></button>
  if (skin === 'navy') {
    return (
      <div className="flex items-start gap-2 border-b border-white/10 px-6 pb-5 pt-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 text-[16px] font-extrabold tracking-wide text-white"><span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white"><LgMark className="size-6" /></span><span className="truncate">{title}</span></div>
          <div className="mt-1 truncate text-xs text-[#8a90a2]">{sub}</div>
        </div>{x}
      </div>
    )
  }
  if (skin === 'mono') {
    return (
      <div className="flex items-center gap-3 px-7 pb-7 pt-9">
        <LgMark className="size-11" />
        <div className="min-w-0"><div className="text-[21px] font-bold leading-tight tracking-tight">{title}</div><div className="mt-1 text-[13px] text-zinc-500">{sub}</div></div>{x}
      </div>
    )
  }
  if (skin === 'monoops') {
    return (
      <div className="flex items-center gap-2.5 px-6 pb-4 pt-6">
        <LgMark className="size-9" />
        <div className="min-w-0"><div className="text-[18px] font-bold leading-tight tracking-tight">{title}</div><div className="mt-0.5 text-[12px] text-zinc-500">{sub}</div></div>{x}
      </div>
    )
  }
  if (skin === 'ops') {
    return (
      <div className="flex items-center gap-2 p-3">
        <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg border border-[#e3e3e3] bg-white p-2">
          <LgMark className="size-8" />
          <div className="min-w-0 leading-tight"><div className="truncate text-[11px] text-zinc-500">{sub}</div><div className="truncate text-[13px] font-semibold">{title}</div></div>
        </div>{x}
      </div>
    )
  }
  return (
    <div className="flex h-14 items-center gap-2.5 border-b border-[#ececee] px-4">
      <LgMark className="size-7" />
      <div className="min-w-0 truncate text-[15px] font-semibold">{title}</div>{x}
    </div>
  )
}

function Sidebar({ skin, view, page, go, open, close, reload, openFile, inline, openSearch }: Props & { open: boolean; close: () => void }) {
  const S = SIDE[skin]
  const pages = view?.pages || []
  const groups = [
    { title: '발표', items: pages.filter((x) => STORY_IDS.has(x.id)) },
    { title: '세부 화면', items: pages.filter((x) => !STORY_IDS.has(x.id)) },
  ].filter((g) => g.items.length)
  const ctx = view?.context || {}
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={close} aria-hidden />}
      <aside className={cn('no-print fixed inset-y-0 left-0 z-40 flex flex-col transition-transform lg:translate-x-0', S.aside, open ? 'translate-x-0 shadow-2xl' : '-translate-x-full')}
        aria-label="단계와 세션 자료">
        <Brand skin={skin} view={view} close={close} />
        {(skin === 'ops' || skin === 'monoops') && view && (
          <button type="button" onClick={openSearch} className={skin === 'ops'
            ? 'mx-3 flex h-9 items-center gap-2 rounded-lg border border-[#e3e3e3] bg-white px-2.5 text-[13px] text-zinc-500 hover:text-zinc-800'
            : 'mx-4 flex h-10 items-center gap-2 rounded-full bg-[#f4f4f4] px-3.5 text-[13px] text-zinc-500 hover:text-zinc-900'}>
            <Search className="size-4" aria-hidden />빠른 검색<kbd className={cn('ml-auto px-1.5 font-sans text-[11px] text-zinc-500', skin === 'ops' ? 'rounded border border-[#e3e3e3]' : 'rounded-full bg-white')}>/</kbd>
          </button>
        )}
        {/* The saved-status card scrolls with the menu, so every page stays reachable on a 768px-high screen. */}
        <div className={cn('flex min-h-0 flex-1 flex-col overflow-y-auto', skin === 'navy' ? 'py-5' : skin === 'mono' ? 'pb-5' : 'py-4')}>
        <nav className={skin === 'mono' ? 'px-5' : skin === 'navy' ? '' : skin === 'monoops' ? 'px-4' : 'px-3'} aria-label="단계">
          {groups.map((g) => (
            <div key={g.title} className={skin === 'analytics' ? 'mb-3 border-b border-[#f0f0f2] pb-3 last:border-0' : 'mb-5'}>
              <div className={S.group}>{g.title}</div>
              <ul className={S.list}>
                {g.items.map((x) => {
                  const Icon = ICONS[x.id] || FileText
                  const active = x.id === page?.id
                  return (
                    <li key={x.id}>
                      <button type="button" onClick={() => go(x.id)} aria-current={active ? 'page' : undefined} className={cn(S.item, active ? S.on : S.off)}>
                        {skin === 'mono' || skin === 'monoops'
                          ? <span className={cn('grid shrink-0 place-items-center rounded-full', skin === 'mono' ? 'size-9' : 'size-8', active ? 'bg-white text-zinc-950' : 'bg-[#f2f2f2] text-zinc-700')}><Icon className={skin === 'mono' ? 'size-[18px]' : 'size-4'} aria-hidden /></span>
                          : <Icon className={cn('shrink-0', skin === 'ops' ? 'size-4' : 'size-[18px]')} aria-hidden />}
                        <span className="truncate">{x.nav || x.title}</span>
                        {S.num && <span className={cn(S.num, active && S.numOn)}>{String(pages.indexOf(x) + 1).padStart(2, '0')}</span>}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>
        {/* L shows the saved status in its right column from xl; below that it stays here. */}
        <SaveCard skin={skin} view={view} reload={reload} openFile={openFile} inline={inline} className={cn(S.card, 'mt-auto', skin === 'analytics' && 'xl:hidden')} />
        </div>
        {skin === 'ops' ? (
          (ctx.footer || []).length > 0 && (
            <div className={S.foot}>
              {/* K: the session ID and usage note are reference lines; they open on hover instead of sitting in the menu. */}
              <HoverNote note={<ul className="flex flex-col gap-1">{(ctx.footer || []).map((f, k) => <li key={k} className="break-all"><Md text={noEmoji(f)} /></li>)}</ul>}
                className="inline-flex items-center gap-1 rounded text-zinc-500 hover:text-zinc-800">
                <Info className="size-3.5" aria-hidden />세션 정보
              </HoverNote>
            </div>
          )
        ) : (
          <div className={cn(S.foot, skin === 'mono' && 'text-center')}>{(ctx.footer || []).map((f, k) => <div key={k} className="truncate"><Md text={noEmoji(f)} /></div>)}</div>
        )}
      </aside>
    </>
  )
}

// "마지막 저장": the export's status chips (의미 검토 전 · 인수 전 included), the file, reload and open-file.
function SaveCard({ skin, view, reload, openFile, inline, className, plain }: {
  skin: SkinId; view: View | null; reload: () => void; openFile: (f: File) => void; inline: boolean; className?: string; plain?: boolean
}) {
  const S = SIDE[skin]
  const ctx = view?.context || {}
  return (
    <div className={className}>
      {!plain && <div className={cn('text-xs font-semibold', skin === 'analytics' ? 'text-[14px] text-zinc-900' : 'opacity-80')}>마지막 저장</div>}
      <div className={cn('flex flex-wrap gap-1.5', !plain && 'mt-2.5')}>{(ctx.status || [{ text: '데이터 없음' }]).map((s, k) => <Badge key={k} chip={s} />)}</div>
      {ctx.file && (
        <div className="mt-3 flex items-start gap-2 text-xs">
          <FileJson className="mt-0.5 size-3.5 shrink-0 opacity-60" aria-hidden />
          <div className="min-w-0">
            {/* K names what the file is; its name (a long hash) opens on hover. */}
            {skin === 'ops'
              ? <HoverNote note={ctx.file.name} className="text-left font-medium underline decoration-zinc-300 decoration-dotted underline-offset-[3px]">저장된 결과 파일</HoverNote>
              : <div className="break-all font-medium">{ctx.file.name}</div>}
            <div className="opacity-70">{ctx.file.size}{ctx.loaded ? ' · ' + ctx.loaded : ''}</div>
          </div>
        </div>
      )}
      <button type="button" onClick={reload} className={cn('inline-flex items-center justify-center gap-1.5', S.button)}><RefreshCw className="size-3.5" aria-hidden />다시 불러오기</button>
      {!inline && (
        <label className="mt-2 flex cursor-pointer items-center justify-center gap-1.5 text-xs underline-offset-2 opacity-80 hover:underline">
          <FolderOpen className="size-3.5" aria-hidden />화면 파일(view JSON) 열기
          <input type="file" accept=".json,application/json" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) openFile(f) }} />
        </label>
      )}
    </div>
  )
}

// K motion 1 (index.css "K motion"): blocks below the first screen wait lowered and transparent, then rise in once
// when they come into view. Marked before the first paint, and only when the motion will run: readers who prefer
// reduced motion, browsers without IntersectionObserver and blocks already on the first screen are never hidden.
function useReveal(on: boolean, pageId: string | undefined) {
  useLayoutEffect(() => {
    if (!on || !pageId || typeof IntersectionObserver === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
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
  }, [on, pageId])
}

function Body({ skin, view, page, copy, go }: Props) {
  useReveal(skin === 'ops', page?.id)
  if (!view || !page) return null
  const pages = view.pages
  const i = pages.findIndex((x) => x.id === page.id)
  const story = STORY_IDS.has(page.id)
  const intro = introOf(page.caption)
  return (
    <>
      {(skin === 'navy' || skin === 'analytics') && <h1 className="hidden text-2xl font-bold print:block">{page.title}</h1>}
      {skin === 'analytics' && <SectionTabs page={page} />}
      {!story && <Head skin={skin} view={view} page={page} n={i + 1} total={pages.length} intro={intro} />}
      <PageBlocks skin={skin} blocks={page.blocks} copy={copy} />
      <PrevNext skin={skin} prev={pages[i - 1]} next={pages[i + 1]} go={go} />
    </>
  )
}

type Intro = ReturnType<typeof introOf>

// "이름 : 값" lines about the saved result (K's head card; J and M too): scope, file, what was loaded, status chips.
function InfoStrip({ skin, view, className }: { skin: SkinId; view: View; className?: string }) {
  const ctx = view.context || {}
  const file = skin === 'ops' ? '' : ctx.file ? `${ctx.file.name}${ctx.file.size ? ' · ' + ctx.file.size : ''}` : ''
  const pairs: [string, string][] = [['범위', ctx.meta || ''], ['파일', file], ['불러온 자료', ctx.loaded || '']]
  const dt = cn('shrink-0 text-zinc-500', skin === 'mono' ? 'w-20' : 'w-16')
  return (
    <dl className={cn('grid min-w-0 gap-x-6 gap-y-1 @2xl:grid-cols-2', skin === 'mono' ? 'text-[13.5px]' : skin === 'monoops' ? 'text-[12.5px]' : 'text-[12px]', className)}>
      {pairs.filter(([, v]) => v).map(([k, v]) => (
        <div key={k} className="flex min-w-0 items-baseline gap-2"><dt className={dt}>{k}</dt><span aria-hidden className="text-zinc-400">:</span><dd className="min-w-0 break-all font-medium text-zinc-900">{v}</dd></div>
      ))}
      <div className="flex min-w-0 items-center gap-2"><dt className={dt}>상태</dt><span aria-hidden className="text-zinc-400">:</span>
        <dd className="flex min-w-0 flex-wrap gap-1">{(ctx.status || [{ text: '데이터 없음' }]).map((s, k) => <Badge key={k} chip={s} />)}</dd></div>
    </dl>
  )
}
function Head({ skin, view, page, n, total, intro }: { skin: SkinId; view: View; page: Page; n: number; total: number; intro: Intro }) {
  const lines = (title: string, text: string) => (
    <>
      {intro.title && <p className={cn('max-w-3xl leading-snug', title)}>{intro.title}</p>}
      {intro.text && <p className={cn('mt-1 max-w-3xl leading-relaxed', text)}>{intro.text}</p>}
    </>
  )
  if (skin === 'navy') {
    return (
      <header className="pb-1">
        {intro.step && <div className="text-[13px] font-semibold text-[#4f5bd5]">{intro.step}</div>}
        <div className="mt-1">{lines('text-[16px] font-semibold text-[#1d2131]', 'text-[14px] text-[#6b7186]')}</div>
      </header>
    )
  }
  if (skin === 'mono') {
    return (
      <header className="flex flex-col gap-4 pb-1 pt-2">
        <div>
          <div className="flex items-center gap-2 text-[13px] text-zinc-500">
            {intro.step}<span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium tabular-nums text-zinc-600" title="화면 순서">{n} / {total}</span>
          </div>
          <h1 className="mt-1 text-balance text-[34px] font-semibold leading-tight tracking-tight text-zinc-950 sm:text-[40px]">{page.title}</h1>
          <div className="mt-3">{lines('text-[17px] text-zinc-800', 'text-[15px] text-zinc-500')}</div>
        </div>
        <InfoStrip skin={skin} view={view} className="rounded-[24px] bg-white px-6 py-4" />
      </header>
    )
  }
  if (skin === 'monoops') {
    const Icon = ICONS[page.id] || FileText
    return (
      <header className="flex flex-col gap-2">
        <div className="@container flex flex-col gap-4 rounded-[22px] bg-white p-5 @4xl:flex-row @4xl:items-center">
          <div className="flex min-w-0 items-center gap-3.5 @4xl:w-[22rem] @4xl:shrink-0">
            <span className="grid size-12 shrink-0 place-items-center rounded-full bg-zinc-950 text-white"><Icon className="size-5" aria-hidden /></span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-[22px] font-semibold tracking-tight text-zinc-950">{page.title}</h1>
                <span className="shrink-0 rounded-full bg-[#f1f1f1] px-2 py-0.5 text-[11px] font-medium tabular-nums text-zinc-600" title="화면 순서">{n} / {total}</span>
              </div>
              {intro.step && <div className="mt-0.5 text-[12px] text-zinc-500">{intro.step}</div>}
            </div>
          </div>
          <InfoStrip skin={skin} view={view} className="flex-1 rounded-[16px] bg-[#f5f5f5] px-4 py-2.5" />
        </div>
        {(intro.title || intro.text) && <div className="px-1 text-[13.5px]">{lines('font-medium text-zinc-900', 'text-zinc-500')}</div>}
      </header>
    )
  }
  if (skin === 'ops') {
    const Icon = ICONS[page.id] || FileText
    return (
      <header className="flex flex-col gap-2">
        <div className={cn(lookOf('ops').card, '@container flex flex-col gap-4 p-4 @4xl:flex-row @4xl:items-center')}>
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
          <InfoStrip skin={skin} view={view} className="flex-1 rounded-md border border-[#e6e6e6] px-3 py-2" />
        </div>
        {(intro.title || intro.text) && <div className="px-0.5 text-[13px]">{lines('font-medium text-zinc-800', 'text-zinc-500')}</div>}
      </header>
    )
  }
  return (
    <header>
      {intro.step && <div className="text-[13px] font-medium text-orange-600">{intro.step}</div>}
      <div className="mt-1">{lines('text-[16px] font-semibold text-zinc-900', 'text-[14px] text-zinc-500')}</div>
    </header>
  )
}

// Each top-level block keeps its data-block index (search results and section tabs scroll to it). In J a "핵심 지표"
// heading directly before the KPI tiles sits on their left, as in the reference's "Quick Stats" row.
function PageBlocks({ skin, blocks, copy }: { skin: SkinId; blocks: Block[]; copy: (s: string) => void }) {
  const out: ReactNode[] = []
  const wrap = (b: Block, k: number) => <div key={k} data-block={k} className="flex min-w-0 scroll-mt-28 flex-col"><BlockView b={b} copy={copy} /></div>
  for (let k = 0; k < blocks.length; k++) {
    const b = blocks[k]
    if ((skin === 'mono' || skin === 'monoops') && b.type === 'section' && blocks[k + 1]?.type === 'kpis') {
      out.push(
        <div key={'pair' + k} className={cn('grid gap-4 @5xl:items-center', skin === 'mono' ? '@5xl:grid-cols-[11rem_minmax(0,1fr)]' : '@5xl:grid-cols-[9rem_minmax(0,1fr)]')}>
          <div data-block={k} className="scroll-mt-28 [&>h3]:mt-0"><BlockView b={b} copy={copy} /></div>
          {wrap(blocks[k + 1], k + 1)}
        </div>,
      )
      k++
      continue
    }
    out.push(wrap(b, k))
  }
  return <>{out}</>
}

function PrevNext({ skin, prev, next, go }: { skin: SkinId; prev?: Page; next?: Page; go: (id: string) => void }) {
  const box = {
    navy: 'rounded-[10px] bg-white p-5 ring-1 ring-[#eceef3] hover:ring-[#cfd3e6]', mono: 'rounded-full bg-white py-3 pl-3 pr-6 hover:bg-zinc-50',
    ops: 'lg-lift rounded-lg border border-[#e6e6e6] bg-white px-4 py-3 hover:border-[#2f8f57]/45 hover:bg-[#fbfdfb]', analytics: 'rounded-xl border border-[#ececee] bg-white p-4 hover:border-zinc-300',
    monoops: 'rounded-full bg-white py-2.5 pl-2.5 pr-5 hover:bg-zinc-50',
  }[skin]
  const icon = skin === 'mono' ? 'grid size-11 shrink-0 place-items-center rounded-full bg-zinc-950 text-white'
    : skin === 'monoops' ? 'grid size-9 shrink-0 place-items-center rounded-full bg-zinc-950 text-white' : 'shrink-0 text-muted-foreground'
  const name = cn('block truncate font-semibold', skin === 'ops' ? 'text-[13px]' : skin === 'monoops' ? 'text-[14px]' : 'text-[15px]')
  return (
    <nav className={cn('no-print grid gap-3 sm:grid-cols-2', skin === 'ops' || skin === 'monoops' ? 'mt-6' : 'mt-10')} aria-label="화면 이동">
      {prev ? (
        <button type="button" onClick={() => go(prev.id)} className={cn('flex items-center gap-4 text-left', box)}>
          <span className={icon}><ChevronLeft className="lg-nudge lg-nudge-prev size-5" aria-hidden /></span>
          <span className="min-w-0"><span className="block text-xs text-muted-foreground">이전 화면</span><span className={name}>{prev.nav || prev.title}</span></span>
        </button>
      ) : <span className="hidden sm:block" />}
      {next && (
        <button type="button" onClick={() => go(next.id)} className={cn('flex items-center justify-end gap-4 text-right', box, skin === 'mono' && 'pl-6 pr-3', skin === 'monoops' && 'pl-5 pr-2.5')}>
          <span className="min-w-0"><span className="block text-xs text-muted-foreground">다음 화면</span><span className={name}>{next.nav || next.title}</span></span>
          <span className={icon}><ChevronRight className="lg-nudge lg-nudge-next size-5" aria-hidden /></span>
        </button>
      )}
    </nav>
  )
}

// L: the page's own sections (headings, section labels, story chapters) as tabs that scroll to them.
const STORY_NO: Record<string, number> = { problem: 1, check: 2, flow: 3, solution: 4, trust: 5 }
function SectionTabs({ page }: { page: Page }) {
  const items = page.blocks.map((b, i) => ({ b, i })).filter(({ b }) => ((b.type === 'heading' || b.type === 'section') && b.text) || (b.type === 'story' && b.label))
  const label = (b: Block) => (b.type === 'story' ? `${STORY_NO[b.key] ? STORY_NO[b.key] + '. ' : ''}${String(b.label).split('·').pop()?.trim()}` : b.text)
  const [active, setActive] = useState(-1)
  useEffect(() => {
    const on = () => {
      let a = -1
      for (const { i } of items) { const el = document.querySelector(`[data-block="${i}"]`); if (el && el.getBoundingClientRect().top < 170) a = i }
      setActive(a)
    }
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [page]) // eslint-disable-line react-hooks/exhaustive-deps
  if (items.length < 2) return <div className="h-1" aria-hidden />
  return (
    <nav className="no-print sticky top-14 z-10 -mx-4 bg-white/95 px-4 pb-2 pt-4 backdrop-blur sm:-mx-6 sm:px-6" aria-label="이 화면 구성">
      <div className="flex max-w-full gap-1 overflow-x-auto rounded-lg bg-[#f4f4f5] p-1 sm:inline-flex">
        {items.map(({ b, i }) => (
          <button key={i} type="button" onClick={() => scrollToBlock(i)} aria-current={active === i ? 'location' : undefined}
            className={cn('h-7 shrink-0 whitespace-nowrap rounded-md px-3 text-[13px]', active === i ? 'bg-white font-medium text-zinc-900 shadow-xs ring-1 ring-black/5' : 'text-zinc-600 hover:text-zinc-900')}>
            {label(b)}
          </button>
        ))}
      </div>
    </nav>
  )
}

// L's right column, only with data that exists: the saved status, the session lines and the next page's intro.
function Rail({ view, next, go, skin, reload, openFile, inline }: Props & { view: View; next?: Page; go: (id: string) => void }) {
  const ctx = view.context || {}
  const intro = introOf(next?.caption)
  const card = 'rounded-xl border border-[#ececee] bg-white p-4'
  return (
    <aside className="no-print hidden border-l border-[#ececee] xl:block" aria-label="저장 상태와 다음 화면">
      <div className="sticky top-14 flex max-h-[calc(100dvh-3.5rem)] flex-col gap-5 overflow-y-auto p-5">
        <section>
          <h2 className="mb-2.5 text-[15px] font-semibold text-zinc-900">마지막 저장</h2>
          <SaveCard skin={skin} view={view} reload={reload} openFile={openFile} inline={inline} className={cn(card, 'text-zinc-700')} plain />
        </section>
        {(ctx.footer || []).length > 0 && (
          <section>
            <h2 className="mb-2.5 text-[15px] font-semibold text-zinc-900">세션</h2>
            <ul className={cn(card, 'flex flex-col divide-y divide-[#f0f0f2] py-1 text-[13px] text-zinc-700')}>
              {(ctx.footer || []).map((f, k) => <li key={k} className="break-all py-2.5"><Md text={noEmoji(f)} /></li>)}
            </ul>
          </section>
        )}
        {next && (
          <section>
            <h2 className="mb-2.5 text-[15px] font-semibold text-zinc-900">다음 화면</h2>
            <div className={card}>
              <div className="text-[14px] font-semibold text-zinc-900">{next.nav || next.title}</div>
              {intro.title && <p className="mt-1 text-[13px] leading-relaxed text-zinc-500">{intro.title}</p>}
              <button type="button" onClick={() => go(next.id)} className="mt-3 inline-flex h-9 w-full items-center justify-center gap-1 rounded-lg border border-[#e4e4e7] text-[13px] font-medium hover:bg-zinc-50">
                열기<ChevronRight className="size-4" aria-hidden />
              </button>
            </div>
          </section>
        )}
      </div>
    </aside>
  )
}
