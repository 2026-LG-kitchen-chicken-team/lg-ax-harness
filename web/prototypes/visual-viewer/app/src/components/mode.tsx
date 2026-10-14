// View mode switch for comparing layouts on the same data: A app, B slides, C one-page poster, D exhibition, E board,
// F = A's sidebar with every page in D's layout, G corporate site, H service landing page, and the dashboard views
// I navy, J mono, K operations, L analytics (A's menu and pages in the look of four dashboard references) and M, J's
// look with K's compact layout.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import {
  Building2, ChartLine, Check, ChevronDown, Contrast, GalleryVerticalEnd, Kanban, LayoutDashboard, LayoutGrid, LayoutList,
  LayoutPanelLeft, PanelLeft, Presentation, Rocket, Rows3,
} from 'lucide-react'
import { cn } from '../lib/utils'

export type Mode = 'app' | 'slides' | 'poster' | 'editorial' | 'board' | 'exhibit' | 'corporate' | 'landing'
  | 'navy' | 'mono' | 'ops' | 'analytics' | 'monoops'
const MODES: { id: Mode; label: string; icon: typeof LayoutGrid }[] = [
  { id: 'app', label: 'A 앱', icon: LayoutDashboard },
  { id: 'slides', label: 'B 슬라이드', icon: Presentation },
  { id: 'poster', label: 'C 한 장', icon: LayoutGrid },
  { id: 'editorial', label: 'D 전시', icon: GalleryVerticalEnd },
  { id: 'board', label: 'E 보드', icon: Kanban },
  { id: 'exhibit', label: 'F 앱+전시', icon: PanelLeft },
  { id: 'corporate', label: 'G 기업', icon: Building2 },
  { id: 'landing', label: 'H 랜딩', icon: Rocket },
  { id: 'navy', label: 'I 네이비', icon: LayoutPanelLeft },
  { id: 'mono', label: 'J 모노', icon: Contrast },
  { id: 'ops', label: 'K 업무형', icon: Rows3 },
  { id: 'analytics', label: 'L 분석형', icon: ChartLine },
  { id: 'monoops', label: 'M 모노+업무', icon: LayoutList },
]
const GROUPS = [{ title: '보기 A–H', from: 0, to: 8 }, { title: '대시보드 I–M (A와 같은 화면, 다른 모양)', from: 8, to: 13 }]
const isMode = (m: unknown): m is Mode => MODES.some((x) => x.id === m)

export function useMode(): [Mode, (m: Mode) => void] {
  const [mode, set] = useState<Mode>(() => {
    const q = new URLSearchParams(location.search).get('mode')
    if (isMode(q)) return q
    // A shared single-file report can name its view (build_view.py --mode), so B/C files open as B/C for everyone.
    if (isMode(window.LGAX_DEFAULT_MODE)) return window.LGAX_DEFAULT_MODE
    try { const s = localStorage.getItem('lgax-view-mode'); if (isMode(s)) return s } catch { /* storage unavailable */ }
    return 'app'
  })
  const setMode = useCallback((m: Mode) => {
    set(m)
    try { localStorage.setItem('lgax-view-mode', m) } catch { /* storage unavailable */ }
  }, [])
  return [mode, setMode]
}

// One small button that opens the list of all thirteen views, so the switch fits a 1366px header and a phone.
// The view's name shows from sm (from xl with `compact`, for crowded headers); narrower screens show the letter only.
export function ModeSwitch({ mode, setMode, dark, compact, className }: { mode: Mode; setMode: (m: Mode) => void; dark?: boolean; compact?: boolean; className?: string }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const btn = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLDivElement>(null)
  const cur = MODES.find((m) => m.id === mode) || MODES[0]
  const Icon = cur.icon
  useEffect(() => {
    if (!open) return
    const out = (e: PointerEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('pointerdown', out)
    return () => document.removeEventListener('pointerdown', out)
  }, [open])
  useLayoutEffect(() => { if (open) list.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus() }, [open])
  const close = () => { setOpen(false); btn.current?.focus() }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') { e.preventDefault(); close(); return }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const items = Array.from(list.current?.querySelectorAll<HTMLButtonElement>('[role="radio"]') || [])
    const at = items.indexOf(document.activeElement as HTMLButtonElement)
    items[(at + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length]?.focus()
  }
  return (
    <div ref={box} className={cn('no-print relative inline-flex text-xs', className)}>
      <button ref={btn} type="button" onClick={() => setOpen((o) => !o)} aria-haspopup="true" aria-expanded={open} title={`보기 방식: ${cur.label} (바꾸기)`}
        aria-label={`보기 방식: ${cur.label}. 눌러서 바꾸기`}
        className={cn('inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 font-medium',
          dark ? 'bg-white/10 text-zinc-100 ring-1 ring-white/15 backdrop-blur hover:bg-white/15' : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200/80')}>
        <Icon className="size-3.5" aria-hidden />{cur.label.split(' ')[0]}
        <span className={compact ? 'hidden xl:inline' : 'hidden sm:inline'}>{cur.label.split(' ').slice(1).join(' ')}</span>
        <ChevronDown className={cn('size-3.5 opacity-60 transition-transform', open && 'rotate-180')} aria-hidden />
      </button>
      {open && (
        <div ref={list} role="radiogroup" aria-label="보기 방식" onKeyDown={onKey}
          className="absolute right-0 top-full z-[60] mt-1.5 max-h-[calc(100dvh-5rem)] w-64 overflow-y-auto rounded-xl bg-white p-1.5 text-left text-zinc-700 shadow-xl ring-1 ring-black/10">
          {GROUPS.map((g) => (
            <Group key={g.title} title={g.title}>
              {MODES.slice(g.from, g.to).map(({ id, label, icon: I }) => (
                <button key={id} type="button" role="radio" aria-checked={mode === id} onClick={() => { setMode(id); close() }}
                  className={cn('flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-[13px] outline-none hover:bg-zinc-100 focus-visible:bg-zinc-100',
                    mode === id && 'font-semibold text-zinc-950')}>
                  <span className="grid size-6 shrink-0 place-items-center rounded-md bg-zinc-100 font-mono text-[11px] font-semibold text-zinc-600">{label.split(' ')[0]}</span>
                  <I className="size-3.5 shrink-0 text-zinc-400" aria-hidden />
                  <span className="min-w-0 flex-1 truncate">{label.split(' ').slice(1).join(' ')}</span>
                  {mode === id && <Check className="size-4 shrink-0" aria-hidden />}
                </button>
              ))}
            </Group>
          ))}
        </div>
      )}
    </div>
  )
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="[&+&]:mt-1 [&+&]:border-t [&+&]:pt-1">
      <div className="px-2.5 pb-1 pt-1.5 text-[11px] text-zinc-400">{title}</div>
      {children}
    </div>
  )
}

// A fixed 1920x1080 canvas scaled to fit the window (letterboxed), so the poster always reads as one screen.
export function Stage({ children, className }: { children: ReactNode; className?: string }) {
  const [scale, setScale] = useState(1)
  useLayoutEffect(() => {
    const fit = () => setScale(Math.min(window.innerWidth / 1920, window.innerHeight / 1080))
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [])
  return (
    <div className="fixed inset-0 overflow-hidden bg-zinc-200/70">
      {/* Centre by the viewport, not by the unscaled 1920px box (grid centring shifted it right/down on smaller screens). */}
      <div className={cn('absolute left-1/2 top-1/2 overflow-hidden bg-white shadow-2xl', className)}
        style={{ width: 1920, height: 1080, transform: `translate(-50%, -50%) scale(${scale})`, transformOrigin: 'center' }}>
        {children}
      </div>
    </div>
  )
}
