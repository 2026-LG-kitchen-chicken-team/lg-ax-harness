// Pieces of the page shell (dash/DashApp.tsx): page icons, the page intro read from the caption, scroll-to-block, the
// Ctrl+K hotkey, larger text, back-to-top, the live dot and the empty state.
import { useEffect, useState } from 'react'
import {
  ArrowUp, BarChart3, FileText, Filter, GitCompareArrows, History, Home, Lightbulb, LoaderCircle, Package, Presentation,
} from 'lucide-react'
import { cn } from '../lib/utils'
import type { LiveState } from '../lib/useView'
import type { LoadPhase } from '../lib/viewState'
import type { Caption } from '../types'

export const ICONS: Record<string, typeof Home> = {
  story: Presentation, overview: Home, dashboard: BarChart3, screening: Filter, compare: GitCompareArrows,
  concepts: Lightbulb, history: History, evidence: FileText, export: Package,
}
export const STORY_IDS = new Set(['story'])
// The builder decorates some strings with emoji ("🆔 Session: …"); the views show the words only.
export const noEmoji = (s: string) => s.replace(/[\p{Extended_Pictographic}️‍]/gu, '').trim()

// Scroll to a top-level block of the current page (search results, page contents) and let it glow once.
// Scrolling follows prefers-reduced-motion as well (index.css "K motion").
const scrollBehavior = (): ScrollBehavior => (window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth')

export function scrollToBlock(i: number, openDetails = false) {
  const el = document.querySelector<HTMLElement>(`[data-block="${i}"]`)
  if (!el) return
  if (openDetails) el.querySelectorAll('details').forEach((d) => { d.open = true })
  el.scrollIntoView({ behavior: scrollBehavior(), block: 'start' })
  el.classList.remove('lg-flash')
  void el.offsetWidth
  el.classList.add('lg-flash')
  window.setTimeout(() => el.classList.remove('lg-flash'), 1900)
}

// "03 · 근거: 결과에 쓴 근거 10건과 검토 판단을 셉니다" → step line + sentence. Anything else is shown as written.
export function introOf(c?: Caption | null): { step?: string; title?: string; text?: string } {
  if (!c) return {}
  const m = /^(\d+)\s*·\s*([^:]+):\s*(.+)$/.exec(c.title || '')
  return m ? { step: `STEP ${m[1]} · ${m[2].trim()}`, title: m[3], text: c.text } : { title: c.title, text: c.text }
}

// 글자 크게: every size is in rem, so the view scales from the root. Undone when the view is left.
export function TextScale({ big }: { big: boolean }) {
  useEffect(() => {
    document.documentElement.style.fontSize = big ? '112.5%' : ''
    return () => { document.documentElement.style.fontSize = '' }
  }, [big])
  return null
}

// Ctrl+K (and "/" when `slash` is set) opens the search; "/" is ignored while typing in a field.
export function SearchHotkey({ open, slash }: { open: () => void; slash?: boolean }) {
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open(); return }
      const t = e.target as HTMLElement | null
      const typing = !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))
      if (slash && e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); open() }
    }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [open, slash])
  return null
}

export function BackToTop({ raised, className }: { raised?: boolean; className?: string }) {
  const [on, setOn] = useState(false)
  useEffect(() => {
    const f = () => setOn(window.scrollY > 600)
    f()
    window.addEventListener('scroll', f, { passive: true })
    return () => window.removeEventListener('scroll', f)
  }, [])
  if (!on) return null
  return (
    <button type="button" onClick={() => window.scrollTo({ top: 0, behavior: scrollBehavior() })} aria-label="맨 위로"
      className={cn('no-print fixed right-6 z-30 grid size-11 place-items-center rounded-full bg-white shadow-lg ring-1 ring-zinc-200 hover:bg-zinc-50', raised ? 'bottom-32 lg:bottom-6' : 'bottom-6', className)}>
      <ArrowUp className="size-5" />
    </button>
  )
}

export const liveText = (live: LiveState, inline: boolean) =>
  inline ? '저장된 실행 결과 · 단일 보고서' : live === 'on' ? '최근 저장 결과 · 자동 갱신' : live === 'off' ? '화면 연결을 다시 확인해 주세요' : '저장된 결과 · 자동 갱신 대기'

export function LiveDot({ live, inline, wide = '2xl' }: { live: LiveState; inline: boolean; wide?: '2xl' | 'never' }) {
  const text = liveText(live, inline)
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:inline-flex" title={text}>
      <span className={cn('size-2 rounded-full', live === 'on' ? 'bg-emerald-500' : live === 'off' ? 'bg-rose-500' : 'bg-zinc-300')} />
      {wide === '2xl' && <span className="hidden 2xl:inline">{text}</span>}
    </span>
  )
}

// These states describe reading the saved screen, never an inferred AI work stage.
type ReadProps = { phase: LoadPhase; busy: boolean; reload: () => void }
export function ReadNotice({ phase, busy, reload }: ReadProps) {
  if (phase !== 'error' && phase !== 'loading') return null
  return <div role="status" className="no-print flex flex-wrap items-center gap-3 rounded-lg border border-[#e3e3e3] bg-white px-4 py-3 text-sm text-zinc-700">
    <span>{phase === 'error' ? '새 결과를 불러오지 못했어요. 최근에 확인한 저장 결과를 보여드리고 있어요.' : '최근 저장 결과를 보여드리며 화면 연결을 확인하고 있어요.'}</span>
    {phase === 'error' && <button type="button" disabled={busy} onClick={reload} className="font-medium text-[#2f7d4f] underline disabled:opacity-50">다시 불러오기</button>}
  </div>
}

export function Empty({ phase, busy, reload }: ReadProps) {
  const failed = phase === 'error'
  const loading = phase === 'loading'
  return <div className="mx-auto mt-12 w-full max-w-xl rounded-2xl border border-[#e3e8e3] bg-white px-6 py-10 text-center shadow-sm" role="status" aria-busy={loading}>
    <div className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-[#eef5eb] text-[#2f7d4f]">
      {loading ? <LoaderCircle className="size-6 motion-safe:animate-spin" aria-hidden /> : <FileText className="size-6" aria-hidden />}
    </div>
    <h1 className="text-2xl font-bold tracking-tight">{failed ? '화면 연결을 확인해 주세요' : loading ? '저장된 결과를 불러오고 있어요' : '첫 결과를 기다리고 있어요'}</h1>
    <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
      {failed ? '지금은 저장된 화면 자료를 읽지 못했어요. 잠시 후 다시 불러오거나 저장한 화면 자료를 직접 열어 주세요.'
        : loading ? '잠시만 기다려 주세요. 결과가 확인되면 이 화면에 표시해 드릴게요.'
          : '아직 표시할 저장 결과가 없어요. 업무 결과가 저장되면 자동으로 확인해요. 이미 저장했다면 다시 불러오기를 눌러 주세요.'}
    </p>
    {loading && <div aria-hidden className="mx-auto mt-6 flex max-w-sm flex-col gap-2 motion-safe:animate-pulse"><div className="h-3 w-3/4 rounded bg-zinc-100" /><div className="h-3 rounded bg-zinc-100" /><div className="h-3 w-5/6 rounded bg-zinc-100" /></div>}
    <button type="button" onClick={reload} disabled={busy} className="mt-5 rounded-md border border-[#e3e3e3] bg-white px-4 py-2 text-sm font-medium text-[#2f7d4f] disabled:opacity-50">{busy ? '화면 연결 확인 중' : '다시 불러오기'}</button>
  </div>
}
