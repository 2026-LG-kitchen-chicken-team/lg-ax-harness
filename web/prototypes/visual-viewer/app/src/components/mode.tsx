// View mode switch for comparing layouts on the same data: A app, B slides, C one-page poster, D exhibition, E board,
// F = A's sidebar with every page in D's layout, G corporate site, H service landing page.
import { useCallback, useLayoutEffect, useState, type ReactNode } from 'react'
import { Building2, GalleryVerticalEnd, Kanban, LayoutDashboard, LayoutGrid, PanelLeft, Presentation, Rocket } from 'lucide-react'
import { cn } from '../lib/utils'

export type Mode = 'app' | 'slides' | 'poster' | 'editorial' | 'board' | 'exhibit' | 'corporate' | 'landing'
const MODES: { id: Mode; label: string; icon: typeof LayoutGrid }[] = [
  { id: 'app', label: 'A 앱', icon: LayoutDashboard },
  { id: 'slides', label: 'B 슬라이드', icon: Presentation },
  { id: 'poster', label: 'C 한 장', icon: LayoutGrid },
  { id: 'editorial', label: 'D 전시', icon: GalleryVerticalEnd },
  { id: 'board', label: 'E 보드', icon: Kanban },
  { id: 'exhibit', label: 'F 앱+전시', icon: PanelLeft },
  { id: 'corporate', label: 'G 기업', icon: Building2 },
  { id: 'landing', label: 'H 랜딩', icon: Rocket },
]
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

// Names show from xl (from 2xl with `compact`, for A's crowded header); narrower screens show the letters only.
export function ModeSwitch({ mode, setMode, dark, compact, className }: { mode: Mode; setMode: (m: Mode) => void; dark?: boolean; compact?: boolean; className?: string }) {
  return (
    <div role="radiogroup" aria-label="보기 방식" className={cn('no-print inline-flex items-center gap-0.5 rounded-lg p-0.5 text-xs',
      dark ? 'bg-white/10 text-zinc-200 ring-1 ring-white/15 backdrop-blur' : 'bg-zinc-100 text-zinc-600', className)}>
      {MODES.map(({ id, label, icon: Icon }) => (
        <button key={id} type="button" role="radio" aria-checked={mode === id} onClick={() => setMode(id)} title={label} aria-label={label}
          className={cn('inline-flex h-7 items-center gap-1.5 rounded-md px-2 font-medium',
            mode === id ? (dark ? 'bg-white text-zinc-900' : 'bg-white text-zinc-900 shadow-xs') : (dark ? 'hover:bg-white/10' : 'hover:text-zinc-900'))}>
          <Icon className="size-3.5" aria-hidden />{label.split(' ')[0]}
          <span className={compact ? 'hidden 2xl:inline' : 'hidden xl:inline'}>{label.split(' ').slice(1).join(' ')}</span>
        </button>
      ))}
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
