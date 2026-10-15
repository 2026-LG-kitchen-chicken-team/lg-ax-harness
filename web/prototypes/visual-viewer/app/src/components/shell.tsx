// Pieces of the page shell (dash/DashApp.tsx): page icons, the page intro read from the caption, scroll-to-block, the
// Ctrl+K hotkey, larger text, back-to-top, the live dot and the empty state.
import { useEffect, useState } from 'react'
import {
  ArrowUp, BarChart3, Copy, FileText, Filter, GitCompareArrows, History, Home, Lightbulb, Package, Presentation,
} from 'lucide-react'
import { cn, Md } from '../lib/utils'
import { useVoice } from '../lib/voice'
import type { LiveState } from '../lib/useView'
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
  inline ? '저장된 실행 결과 · 단일 보고서' : live === 'on' ? '저장된 실행 결과 · 자동 갱신' : live === 'off' ? '데이터 파일 없음' : '저장된 실행 결과'

export function LiveDot({ live, inline, wide = '2xl' }: { live: LiveState; inline: boolean; wide?: '2xl' | 'never' }) {
  const text = liveText(live, inline)
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted-foreground sm:inline-flex" title={text}>
      <span className={cn('size-2 rounded-full', live === 'on' ? 'bg-emerald-500' : live === 'off' ? 'bg-rose-500' : 'bg-zinc-300')} />
      {wide === '2xl' && <span className="hidden 2xl:inline">{text}</span>}
    </span>
  )
}

// The hook that draws the view is read only from the folder a Claude Code/Codex session was started in (claude/ or
// codex/ of the judge ZIP), so the help names that folder and the by-hand refresh run from it.
const REFRESH = 'uv run python web/prototypes/visual-viewer/viewer.py open .'

export function Empty({ copy }: { copy?: (s: string) => void }) {
  const voice = useVoice()
  return (
    <div className="mx-auto mt-16 w-full max-w-xl">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">시각자료를 기다리는 중</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {voice('결과를 저장하면 훅이 이 폴더에 view-data.js를 만들고 화면이 자동으로 그려집니다. 이미 만든 view JSON이 있으면 왼쪽에서 여세요.')}
        </p>
      </div>
      <section className="mt-6 rounded-lg border border-[#e6e6e6] bg-white p-4 text-sm leading-relaxed text-zinc-700">
        <h2 className="text-[13px] font-semibold text-zinc-900">{voice('결과를 저장했는데 계속 비어 있으면')}</h2>
        <ol className="mt-2 list-decimal space-y-2 pl-5 marker:font-mono marker:text-xs marker:text-zinc-400">
          <li><Md text={voice('Claude Code·Codex 세션을 제품 폴더에서 시작했는지 확인하세요. 심사용 ZIP이면 최상위 폴더가 아니라 `claude/` 또는 `codex/` 폴더입니다. 화면을 그리는 훅은 세션을 시작한 폴더에서만 읽히고, 세션 중간에 cd로 옮겨도 읽히지 않습니다. 그 폴더에서 새 세션을 여세요.')} /></li>
          <li>{voice('바로 보려면 그 폴더에서 터미널을 열고 아래 명령을 실행하세요. 저장된 최신 결과로 화면을 다시 만듭니다.')}</li>
        </ol>
        <div className="mt-3 flex min-h-10 items-center gap-2 rounded-xl bg-zinc-950 py-1 pl-4 pr-1">
          {/* Wraps instead of scrolling on narrow screens: the trailing "." (this folder) must stay visible. */}
          <code className="min-w-0 flex-1 py-2 font-mono text-xs leading-relaxed text-zinc-100 [overflow-wrap:anywhere]">{REFRESH}</code>
          {copy && (
            <button type="button" onClick={() => copy(REFRESH)} title="명령 복사"
              className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-zinc-300 hover:bg-white/10 hover:text-white">
              <Copy className="size-3.5" aria-hidden />복사
            </button>
          )}
        </div>
      </section>
    </div>
  )
}
