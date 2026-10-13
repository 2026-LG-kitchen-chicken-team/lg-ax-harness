// Magic UI-style pieces (StatValue, DotPattern), written in-tree.
import { useId } from 'react'
import { cn, fmt } from '../../lib/utils'

// A stored count, shown as is. No count-up effect: a paused animation would leave a wrong number on screen.
export function StatValue({ value, className }: { value: number | string; className?: string }) {
  return <span className={cn('tabular-nums', className)}>{fmt(value)}</span>
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
