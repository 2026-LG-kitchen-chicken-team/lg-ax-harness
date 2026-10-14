// shadcn/ui-style primitives, written in-tree (no CLI, no Radix): Card, Badge, Button, Alert, Table.
import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps, ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, OctagonAlert } from 'lucide-react'
import { cn, tone, TONE_SOFT } from '../../lib/utils'
import { useIdTip } from '../idtip'
import type { Chip } from '../../types'

export function Card({ className, ...props }: ComponentProps<'div'>) {
  return <div data-card className={cn('rounded-xl border bg-card text-card-foreground shadow-xs', className)} {...props} />
}
export function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-1 px-5 pt-5', className)} {...props} />
}
export function CardTitle({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('text-[15px] font-semibold leading-snug tracking-tight', className)} {...props} />
}
export function CardDescription({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('text-xs leading-relaxed text-muted-foreground', className)} {...props} />
}
export function CardContent({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('px-5 pb-5 pt-3', className)} {...props} />
}

const badgeVariants = cva(
  'inline-flex max-w-full items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap',
  { variants: { mono: { true: 'font-mono text-[11px] whitespace-normal break-all', false: '' } }, defaultVariants: { mono: false } },
)
// In A an ID chip (P1, R1, a source ID …) shows what it stands for on hover or focus (components/idtip.tsx).
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

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 cursor-pointer',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        outline: 'border bg-background hover:bg-accent',
        ghost: 'hover:bg-accent',
      },
      size: { default: 'h-9 px-4', sm: 'h-8 px-3 text-xs', icon: 'size-8' },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)
export function Button({ className, variant, size, ...props }: ComponentProps<'button'> & VariantProps<typeof buttonVariants>) {
  return <button type="button" className={cn(buttonVariants({ variant, size }), className)} {...props} />
}

const ALERT = {
  info: { cls: 'border-blue-200 bg-blue-50/60 text-blue-950', icon: Info, ic: 'text-blue-600' },
  success: { cls: 'border-emerald-200 bg-emerald-50/60 text-emerald-950', icon: CheckCircle2, ic: 'text-emerald-600' },
  warning: { cls: 'border-amber-200 bg-amber-50/70 text-amber-950', icon: AlertTriangle, ic: 'text-amber-600' },
  error: { cls: 'border-rose-200 bg-rose-50/70 text-rose-950', icon: OctagonAlert, ic: 'text-rose-600' },
} as const
export function Alert({ tone: t, children }: { tone?: string; children: ReactNode }) {
  const a = ALERT[(t as keyof typeof ALERT) in ALERT ? (t as keyof typeof ALERT) : 'info']
  const Icon = a.icon
  return (
    <div role="note" className={cn('flex gap-3 rounded-xl border px-4 py-3.5 text-[15px] leading-relaxed', a.cls)}>
      <Icon className={cn('mt-0.5 size-4 shrink-0', a.ic)} aria-hidden />
      <div className="min-w-0">{children}</div>
    </div>
  )
}

export function Table({ className, ...props }: ComponentProps<'table'>) {
  return (
    <div className="relative w-full overflow-x-auto">
      <table className={cn('w-full caption-bottom text-sm', className)} {...props} />
    </div>
  )
}
export const THead = (p: ComponentProps<'thead'>) => <thead {...p} className={cn('[&_tr]:border-b', p.className)} />
export const TBody = (p: ComponentProps<'tbody'>) => <tbody {...p} className={cn('[&_tr:last-child]:border-0', p.className)} />
export const TR = (p: ComponentProps<'tr'>) => <tr {...p} className={cn('border-b transition-colors hover:bg-muted/40', p.className)} />
export const TH = (p: ComponentProps<'th'>) => (
  <th {...p} className={cn('h-11 whitespace-nowrap px-3 text-left align-middle text-[13px] font-semibold text-muted-foreground', p.className)} />
)
export const TD = (p: ComponentProps<'td'>) => <td {...p} className={cn('px-3 py-3 align-top leading-relaxed', p.className)} />
