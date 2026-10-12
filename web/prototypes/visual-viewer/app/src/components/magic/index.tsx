// Magic UI-style effects (NumberTicker, RiseIn, DotPattern), written in-tree on top of `motion`.
import { useEffect, useId, useRef, type ReactNode } from 'react'
import { animate, useInView, useReducedMotion } from 'motion/react'
import { cn, fmt } from '../../lib/utils'

// Counts up to a stored count. Only for counts that exist in the result; never for estimates.
export function NumberTicker({ value, className }: { value: number | string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const reduce = useReducedMotion()
  const numeric = typeof value === 'number' && Number.isFinite(value)
  useEffect(() => {
    const el = ref.current
    if (!el || !numeric) return
    if (reduce || !inView) { el.textContent = fmt(value); return }
    const controls = animate(0, value as number, {
      duration: Math.min(1.2, 0.4 + (value as number) * 0.05),
      ease: 'easeOut',
      onUpdate: (v) => { el.textContent = fmt(Math.round(v)) },
    })
    return () => controls.stop()
  }, [value, numeric, inView, reduce])
  return <span ref={ref} className={cn('tabular-nums', className)}>{fmt(value)}</span>
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
