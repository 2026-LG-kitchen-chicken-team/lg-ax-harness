// shadcn/ui-style primitives, written in-tree (no CLI, no Radix): Card and Badge.
import { cva } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn, tone, TONE_SOFT } from '../../lib/utils'
import { useIdTip } from '../idtip'
import type { Chip } from '../../types'

export function Card({ className, ...props }: ComponentProps<'div'>) {
  return <div data-card className={cn('rounded-xl border bg-card text-card-foreground shadow-xs', className)} {...props} />
}

const badgeVariants = cva(
  'inline-flex max-w-full items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap',
  { variants: { mono: { true: 'font-mono text-[11px] whitespace-normal break-all', false: '' } }, defaultVariants: { mono: false } },
)
// An ID chip (P1, R1, a source ID …) shows what it stands for on hover or focus (components/idtip.tsx).
export function Badge({ chip, className }: { chip: Chip | string; className?: string }) {
  const c = typeof chip === 'string' ? { text: chip } : chip
  const tip = useIdTip()
  const cls = cn(badgeVariants({ mono: !!c.mono }), TONE_SOFT[tone(c.tone)], className)
  const t = tone(c.tone)
  if (!tip?.lookup(c.text)) return <span data-badge data-tone={t} title={c.tip || undefined} className={cls}>{c.text}</span>
  return (
    <span data-badge data-tone={t} tabIndex={0} className={cn(cls, 'cursor-help underline decoration-dotted decoration-1 underline-offset-[3px] focus-visible:outline-2')}
      onMouseEnter={(e) => tip.show(c.text, e.currentTarget)} onMouseLeave={tip.hide} onFocus={(e) => tip.show(c.text, e.currentTarget)} onBlur={tip.hide}>
      {c.text}
    </span>
  )
}
export function Badges({ items, className }: { items?: (Chip | string)[]; className?: string }) {
  if (!items?.length) return null
  return <div className={cn('flex flex-wrap gap-1.5', className)}>{items.map((c, i) => <Badge key={i} chip={c} />)}</div>
}
