// Magic UI-style pieces (StatValue, RiseIn, DotPattern), written in-tree.
import { useId, type ReactNode } from 'react'
import { cn, fmt } from '../../lib/utils'

// A stored count, shown as is. No count-up effect: a paused animation would leave a wrong number on screen.
export function StatValue({ value, className }: { value: number | string; className?: string }) {
  return <span className={cn('tabular-nums', className)}>{fmt(value)}</span>
}

// Entrance rise-in on first render (CSS only). It never hides content: no opacity or blur change, no scroll trigger.
export function RiseIn({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  // Only animate when the page is actually on screen; a hidden or background tab just shows the content.
  const play = typeof document !== 'undefined' && document.visibilityState === 'visible'
  return <div className={cn(play && 'animate-rise-in', className)} style={play ? { animationDelay: `${delay}s` } : undefined}>{children}</div>
}

export function DotPattern({ className }: { className?: string }) {
  const id = useId()
  return (
    <svg aria-hidden className={cn('pointer-events-none absolute inset-0 h-full w-full fill-zinc-300/70', className)}>
      <defs>
        <pattern id={id} width="18" height="18" patternUnits="userSpaceOnUse">
          <circle cx="1.5" cy="1.5" r="1.2" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  )
}
