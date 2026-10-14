// Block renderers of the dashboard views I (navy), J (mono), K (operations), L (analytics) and M (mono look with K's
// compact layout). They take the same
// blocks build_view.py writes for A and change only how they look. Layout only: no counting, ranking or judging here;
// block types not listed in SKINS fall through to A's renderers (components/blocks.tsx, components/story.tsx).
import { useState, type CSSProperties, type ReactNode } from 'react'
import {
  AlertTriangle, ArrowRight, CheckCircle2, ChevronDown, Copy, ExternalLink, FileText, Gauge, Globe, Hash, Info, Lightbulb,
  ListChecks, MessageSquareWarning, OctagonAlert, Quote, Search, ShieldCheck,
} from 'lucide-react'
import { Badge, Badges } from '../components/ui'
import { Blocks, useTableRows } from '../components/blocks'
import { QuoteLine } from '../components/story'
import { useIdTip } from '../components/idtip'
import { barWidth, NoData, SegmentBar, SkinBars, SkinDonut, SkinLine, useToneHex } from './charts'
import { useSkin, type BlockRenderer, type Skin, type SkinId } from '../lib/skin'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, Chip } from '../types'

type P = { b: Block; copy: (s: string) => void }

// Per-view surfaces and type. Colours that carry meaning (tones, warnings) stay the same family in every view.
interface Look {
  gap: string; card: string; pad: string; title: string; heading: string; section: string
  table: string; th: string; td: string; input: string; num: string; badge: string; quote: string
}
const LOOK: Record<SkinId, Look> = {
  navy: {
    gap: 'gap-5', card: 'rounded-[10px] bg-white ring-1 ring-[#eceef3] shadow-[0_1px_2px_rgb(29_33_49/0.04)]', pad: 'p-5 sm:p-6',
    title: 'text-[15px] font-semibold text-[#5d6378]',
    heading: 'mt-6 text-[19px] font-bold tracking-tight text-[#1d2131]',
    section: 'mt-3 text-[13px] font-semibold tracking-wide text-[#8a90a2]',
    table: 'w-full text-[14px]',
    th: 'h-10 whitespace-nowrap border-b border-[#eceef3] px-3 text-left align-middle text-[12px] font-medium text-[#8a90a2] first:pl-0',
    td: 'border-b border-[#f1f2f6] px-3 py-3.5 align-top text-[#2b3040] first:pl-0',
    input: 'h-10 rounded-lg border border-[#e3e6ee] bg-white', num: 'text-[#1d2131]', badge: 'bg-[#eef0fd] text-[#4f5bd5]',
    quote: 'text-[14.5px] leading-relaxed text-[#2b3040]',
  },
  mono: {
    gap: 'gap-5', card: 'rounded-[28px] bg-white', pad: 'p-6 sm:p-8',
    title: 'text-[22px] font-semibold tracking-tight text-zinc-950',
    heading: 'mt-8 text-[30px] font-semibold tracking-tight text-zinc-950',
    section: 'mt-4 text-[24px] font-semibold tracking-tight text-zinc-950',
    table: 'w-full border-separate border-spacing-y-2 text-[15px]',
    th: 'whitespace-nowrap px-4 pb-1 text-left align-middle text-[14px] font-normal text-zinc-500',
    td: 'bg-[#f5f5f5] px-4 py-4 align-top text-zinc-900 first:rounded-l-[18px] last:rounded-r-[18px]',
    input: 'h-11 rounded-full border border-zinc-300 bg-white', num: 'text-zinc-950', badge: 'bg-zinc-950 text-white',
    quote: 'text-[16px] leading-relaxed text-zinc-900',
  },
  ops: {
    gap: 'gap-3', card: 'rounded-lg border border-[#e6e6e6] bg-white', pad: 'p-4',
    title: 'text-[15px] font-semibold text-zinc-900',
    heading: 'mt-5 border-b border-[#e6e6e6] pb-2 text-[17px] font-semibold text-zinc-900',
    section: 'mt-2 text-[14px] font-semibold text-zinc-900',
    table: 'w-full text-[13px]',
    th: 'h-9 whitespace-nowrap bg-[#f3f3f3] px-3 text-left align-middle text-[12px] font-medium text-zinc-600 first:rounded-l-md last:rounded-r-md',
    td: 'border-b border-[#efefef] px-3 py-2.5 align-top text-zinc-800',
    input: 'h-8 rounded-md border border-[#e3e3e3] bg-white', num: 'text-zinc-950', badge: 'bg-[#e6f1e8] text-[#2f7d4f]',
    quote: 'text-[13.5px] leading-relaxed text-zinc-800',
  },
  analytics: {
    gap: 'gap-5', card: 'rounded-xl border border-[#ececee] bg-white shadow-[0_1px_2px_rgb(0_0_0/0.03)]', pad: 'p-5',
    title: 'text-[14px] font-semibold text-zinc-800',
    heading: 'mt-6 text-xl font-semibold tracking-tight text-zinc-900',
    section: 'mt-3 text-[15px] font-semibold text-zinc-900',
    table: 'w-full text-[14px]',
    th: 'h-10 whitespace-nowrap border-b border-[#ececee] px-3 text-left align-middle text-[13px] font-medium text-zinc-500 first:pl-0',
    td: 'border-b border-[#f3f3f4] px-3 py-3 align-top text-zinc-800 first:pl-0',
    input: 'h-9 rounded-lg border border-[#e4e4e7] bg-white', num: 'text-zinc-900', badge: 'bg-orange-50 text-orange-600',
    quote: 'text-[14px] leading-relaxed text-zinc-800',
  },
  monoops: {
    gap: 'gap-4', card: 'rounded-[22px] bg-white', pad: 'p-5',
    title: 'text-[17px] font-semibold tracking-tight text-zinc-950',
    heading: 'mt-6 text-[22px] font-semibold tracking-tight text-zinc-950',
    section: 'mt-2 text-[18px] font-semibold tracking-tight text-zinc-950',
    table: 'w-full border-separate border-spacing-y-1.5 text-[13.5px]',
    th: 'whitespace-nowrap px-3 pb-0.5 text-left align-middle text-[12px] font-normal text-zinc-500',
    td: 'bg-[#f5f5f5] px-3 py-2.5 align-top text-zinc-900 first:rounded-l-[14px] last:rounded-r-[14px]',
    input: 'h-9 rounded-full border border-zinc-300 bg-white', num: 'text-zinc-950', badge: 'bg-zinc-950 text-white',
    quote: 'text-[14px] leading-relaxed text-zinc-900',
  },
}
// J and M share the black-and-white look; K and M share the compact layout.
const isMono = (id: SkinId) => id === 'mono' || id === 'monoops'
const isDense = (id: SkinId) => id === 'ops' || id === 'monoops'
export const lookOf = (id: SkinId) => LOOK[id]
const useId = (): SkinId => useSkin()?.id || 'navy'
const useLook = () => LOOK[useId()]

export const Source = ({ text }: { text?: string }) => (text ? <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">출처: {text}</p> : null)

function Panel({ b, title, children, className }: { b: Block; title?: ReactNode; children: ReactNode; className?: string }) {
  const L = useLook()
  const t = title ?? b.title
  return (
    <section className={cn('@container min-w-0', L.card, L.pad, className)}>
      {t && <div className={cn(L.title, 'mb-4')}>{t}</div>}
      {children}
      <Source text={b.source} />
    </section>
  )
}

// Numbers in tabular figures; long words ("미측정", "의미 검토 전") get a smaller size and are never cut.
const vsize = (v: unknown, unit: unknown, s: [string, string, string]) => {
  const n = String(v ?? '').length + String(unit ?? '').length
  return n <= 6 ? s[0] : n <= 12 ? s[1] : s[2]
}
// A decorative icon from the label's words; the label itself says what the number is.
const ICON: [RegExp, typeof Hash][] = [
  [/불편/, MessageSquareWarning], [/기능/, ListChecks], [/제안/, Lightbulb], [/발췌|후기|원문/, Quote], [/사이트|출처/, Globe],
  [/사용량|토큰|비용|호출/, Gauge], [/의미|검토|뒷받침/, ShieldCheck], [/근거|자료/, FileText],
]
const iconOf = (label: string) => ICON.find(([re]) => re.test(label))?.[1] || Hash

// --- KPI rows ---------------------------------------------------------------------------------------------------
type Kpi = { label: string; value: number | string; unit?: string; tone?: string; note?: string; source?: string }
const kpiGrid = (n: number): { className: string; style: CSSProperties } => ({
  className: 'grid grid-cols-2 @max-3xl:[&>*:last-child:nth-child(odd)]:col-span-2 @3xl:[grid-template-columns:repeat(var(--n),minmax(0,1fr))]',
  style: { ['--n' as string]: Math.min(Math.max(n, 1), 6) },
})

export function Kpis({ items, source }: { items: Kpi[]; source?: string }) {
  const id = useId()
  if (!items.length) return null
  const K = { navy: NavyKpis, mono: MonoKpis, ops: OpsKpis, analytics: StripKpis, monoops: CompactMonoKpis }[id]
  return <div className="@container min-w-0"><K items={items} /><Source text={source} /></div>
}

function NavyKpis({ items }: { items: Kpi[] }) {
  const hex = useToneHex()
  const g = kpiGrid(items.length)
  return (
    <div className={cn(g.className, 'gap-4')} style={g.style}>
      {items.map((k, i) => {
        const t = tone(k.tone)
        const Icon = iconOf(k.label)
        return (
          <div key={i} className={cn(LOOK.navy.card, 'min-w-0 p-5')} title={k.source ? '출처: ' + k.source : undefined}>
            <div className="flex items-start gap-3">
              <span aria-hidden className="w-[3px] self-stretch rounded-full" style={{ background: hex[t] }} />
              <div className="min-w-0 flex-1">
                <div className="text-[14px] text-[#8a90a2]">{k.label}</div>
                <div className={cn('mt-1.5 font-semibold leading-tight tracking-tight tabular-nums', vsize(k.value, k.unit, ['text-[28px]', 'text-xl', 'text-base break-all']), t === 'gray' ? 'text-[#7c8296]' : 'text-[#1d2131]')}>
                  {fmt(k.value)}{k.unit && <span className="ml-1 text-sm font-medium text-[#8a90a2]">{k.unit}</span>}
                </div>
              </div>
              <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-lg" style={{ background: hex[t] + '17', color: hex[t] }}><Icon className="size-[18px]" /></span>
            </div>
            {k.note && <div className="mt-3 pl-[15px] text-[12.5px] leading-snug text-[#8a90a2]">{k.note}</div>}
          </div>
        )
      })}
    </div>
  )
}

// Tall rounded tiles with a round icon on top; the first one's icon is filled black (the lead count). M uses a shorter tile.
function MonoKpis({ items, compact }: { items: Kpi[]; compact?: boolean }) {
  const g = kpiGrid(items.length)
  return (
    <div className={cn(g.className, compact ? 'gap-3' : 'gap-4')} style={g.style}>
      {items.map((k, i) => {
        const Icon = iconOf(k.label)
        return (
          <div key={i} className={cn('flex min-w-0 flex-col items-center bg-white px-4 text-center', compact ? 'min-h-[9rem] rounded-[22px] pb-4 pt-4 @3xl:min-h-[10rem]' : 'min-h-[11rem] rounded-[28px] pb-6 pt-6 @3xl:min-h-[13rem]')} title={k.source ? '출처: ' + k.source : undefined}>
            <span aria-hidden className={cn('grid shrink-0 place-items-center rounded-full', compact ? 'size-10' : 'size-14', i === 0 ? 'bg-zinc-950 text-white' : 'bg-white text-zinc-900 shadow-[0_4px_14px_rgb(0_0_0/0.08)]')}><Icon className={compact ? 'size-4' : 'size-5'} /></span>
            <div className={cn('font-semibold leading-tight tracking-tight tabular-nums', compact ? 'mt-3' : 'mt-5', vsize(k.value, k.unit, compact ? ['text-[26px]', 'text-lg', 'text-sm break-all'] : ['text-[30px]', 'text-xl', 'text-base break-all']), tone(k.tone) === 'gray' ? 'text-zinc-500' : 'text-zinc-950')}>
              {fmt(k.value)}{k.unit && <span className={cn('ml-0.5 font-medium text-zinc-500', compact ? 'text-sm' : 'text-base')}>{k.unit}</span>}
            </div>
            <div className={cn('mt-1 leading-snug text-zinc-600', compact ? 'text-[13.5px]' : 'text-[15px]')}>{k.label}</div>
            {k.note && <div className={cn('leading-snug text-zinc-400', compact ? 'mt-1 text-[11.5px]' : 'mt-1.5 text-xs')}>{k.note}</div>}
          </div>
        )
      })}
    </div>
  )
}
const CompactMonoKpis = ({ items }: { items: Kpi[] }) => <MonoKpis items={items} compact />

function OpsKpis({ items }: { items: Kpi[] }) {
  const hex = useToneHex()
  const g = kpiGrid(items.length)
  return (
    <div className={cn(g.className, 'gap-3')} style={g.style}>
      {items.map((k, i) => (
        <div key={i} className={cn(LOOK.ops.card, 'min-w-0 p-4')} title={k.source ? '출처: ' + k.source : undefined}>
          <div className="flex items-center gap-2 text-[13px] text-zinc-600"><span aria-hidden className="size-2 rounded-[2px]" style={{ background: hex[tone(k.tone)] }} />{k.label}</div>
          <div className={cn('mt-3 font-medium leading-tight tracking-tight tabular-nums', vsize(k.value, k.unit, ['text-[30px]', 'text-xl', 'text-sm break-all']), tone(k.tone) === 'gray' ? 'text-zinc-500' : 'text-zinc-950')}>
            {fmt(k.value)}{k.unit && <span className="ml-1 text-[13px] font-normal text-zinc-500">{k.unit}</span>}
          </div>
          {k.note && <div className="mt-1.5 text-[12px] leading-snug text-zinc-500">{k.note}</div>}
        </div>
      ))}
    </div>
  )
}

// One bordered strip split into cells (L). The grid trick keeps inner rules only, for any number of cells.
function StripKpis({ items }: { items: Kpi[] }) {
  const hex = useToneHex()
  const g = kpiGrid(items.length)
  return (
    <div className="overflow-hidden rounded-xl border border-[#ececee] bg-white">
      <div className={cn(g.className, '-mb-px -mr-px')} style={g.style}>
        {items.map((k, i) => (
          <div key={i} className="min-w-0 border-b border-r border-[#ececee] p-5" title={k.source ? '출처: ' + k.source : undefined}>
            <div className="flex items-center gap-2 text-[14px] text-zinc-500"><span aria-hidden className="size-2 rounded-full" style={{ background: hex[tone(k.tone)] }} />{k.label}</div>
            <div className={cn('mt-2 font-semibold leading-tight tracking-tight tabular-nums', vsize(k.value, k.unit, ['text-[30px]', 'text-xl', 'text-base break-all']), tone(k.tone) === 'gray' ? 'text-zinc-500' : 'text-zinc-900')}>
              {fmt(k.value)}{k.unit && <span className="ml-1 text-sm font-medium text-zinc-500">{k.unit}</span>}
            </div>
            {k.note && <div className="mt-2 text-[13px] leading-snug text-zinc-500">{k.note}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

// --- label/value strips (metrics) --------------------------------------------------------------------------------
function Metrics({ b }: P) {
  const id = useId()
  const items: Kpi[] = b.items || []
  if (isDense(id)) {
    return (
      <div className={cn(LOOK[id].card, '@container', id === 'ops' ? 'px-4 py-3' : 'px-5 py-3.5')}>
        <dl className="grid gap-x-8 gap-y-1.5 @xl:grid-cols-2 @4xl:grid-cols-3">
          {items.map((m, i) => (
            <div key={i} className="flex min-w-0 items-baseline gap-2 text-[13px]">
              <dt className="w-28 shrink-0 text-zinc-500">{m.label}</dt><span aria-hidden className="text-zinc-400">:</span>
              <dd className="min-w-0 break-all font-semibold text-zinc-900">{fmt(m.value)}{m.unit && <span className="ml-0.5 font-normal text-zinc-500">{m.unit}</span>}
                {m.note && <span className="ml-2 font-normal text-zinc-500">{m.note}</span>}</dd>
            </div>
          ))}
        </dl>
      </div>
    )
  }
  const cell = (m: Kpi, i: number, cls: string) => (
    <div key={i} className={cn('min-w-0', cls)}>
      <dt className={cn('text-[13px]', id === 'mono' ? 'text-zinc-500' : 'text-muted-foreground')}>{m.label}</dt>
      <dd className={cn('mt-1 font-semibold tracking-tight tabular-nums', vsize(m.value, m.unit, ['text-2xl', 'text-lg', 'text-sm break-all']), tone(m.tone) === 'gray' ? 'text-zinc-500' : 'text-foreground')}>
        {fmt(m.value)}{m.unit && <span className="ml-0.5 text-sm font-medium text-muted-foreground">{m.unit}</span>}
      </dd>
      {m.note && <div className="mt-1 text-xs text-muted-foreground">{m.note}</div>}
    </div>
  )
  if (id === 'mono') return <dl className="@container grid grid-cols-2 gap-3 @2xl:grid-cols-3 @5xl:grid-cols-6">{items.map((m, i) => cell(m, i, 'rounded-[22px] bg-white p-5'))}</dl>
  return (
    <div className={cn('@container overflow-hidden', id === 'navy' ? LOOK.navy.card : 'rounded-xl border border-[#ececee] bg-white')}>
      <dl className="-mb-px -mr-px grid grid-cols-2 @2xl:grid-cols-3 @5xl:grid-cols-6">{items.map((m, i) => cell(m, i, 'border-b border-r border-[#eceef3] p-4'))}</dl>
    </div>
  )
}

// --- charts -------------------------------------------------------------------------------------------------------
type Bar = { label: string; value: number; tone?: string; note?: string }

function HBars({ b }: P) {
  const id = useId()
  const items: Bar[] = b.items || []
  if (items.length > 6) return <BarTable b={b} />
  return <Panel b={b}>{items.length ? <BarRows b={b} items={items} id={id} /> : <NoData />}</Panel>
}

function BarRows({ b, items, id }: { b: Block; items: Bar[]; id: SkinId }) {
  const hex = useToneHex()
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  const fill = (it: Bar) => (isMono(id) ? (tone(it.tone || b.tone) === 'gray' ? '#a3a3a3' : '#111111') : hex[tone(it.tone || b.tone || 'blue')])
  const val = (it: Bar) => <>{fmt(it.value)}<span className="ml-0.5 text-[0.8em] font-medium text-muted-foreground">{b.unit || ''}</span></>
  if (isDense(id)) {
    return (
      <ul className={cn('flex flex-col', id === 'ops' ? 'gap-2.5' : 'gap-3')}>
        {items.map((it, i) => (
          <li key={i} className={cn('grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3.5rem] items-center gap-3', id === 'ops' ? 'text-[13px]' : 'text-[13.5px]')} title={it.note || undefined}>
            <span className="truncate text-zinc-600">{it.label}</span>
            <span className={cn('rounded-full', id === 'ops' ? 'h-1.5 bg-[#f0f0f0]' : 'h-2.5 bg-[#efefef]')}><span className="block h-full rounded-full" style={{ width: barWidth(it.value, max), background: fill(it) }} /></span>
            <span className="text-right font-semibold tabular-nums text-zinc-900">{val(it)}</span>
          </li>
        ))}
      </ul>
    )
  }
  if (id === 'analytics') {
    return (
      <ul className="flex flex-col gap-3">
        {items.map((it, i) => (
          <li key={i} title={it.note || undefined}>
            <div className="text-[13px] text-zinc-500">{it.label}</div>
            <div className="mt-1 flex items-center gap-3">
              <span className="h-7 flex-1"><span className="block h-full rounded-md" style={{ width: barWidth(it.value, max), background: fill(it) }} /></span>
              <span className="w-14 shrink-0 text-right text-[15px] font-semibold tabular-nums text-zinc-900">{val(it)}</span>
            </div>
          </li>
        ))}
      </ul>
    )
  }
  const mono = id === 'mono'
  return (
    <ul className={cn('flex flex-col', mono ? 'gap-5' : 'gap-4')}>
      {items.map((it, i) => (
        <li key={i} title={it.note || undefined}>
          <div className="flex items-baseline justify-between gap-3">
            <span className={cn('min-w-0 truncate', mono ? 'text-[15px] text-zinc-700' : 'text-[13.5px] text-[#6b7186]')}>{it.label}</span>
            <span className={cn('shrink-0 font-semibold tabular-nums', mono ? 'text-[17px] text-zinc-950' : 'text-[15px] text-[#1d2131]')}>{val(it)}</span>
          </div>
          <div className={cn('mt-2 rounded-full', mono ? 'h-3 bg-[#efefef]' : 'h-2 bg-[#eef0f6]')}>
            <div className="h-full rounded-full" style={{ width: barWidth(it.value, max), background: fill(it) }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

// Many bars (e.g. every item's linked evidence) read better as a table with a small bar per row.
function BarTable({ b }: { b: Block }) {
  const id = useId()
  const L = LOOK[id]
  const hex = useToneHex()
  const tip = useIdTip()
  const items: Bar[] = b.items || []
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  const head = ({ 건: '건수', 개: '개수', 회: '횟수' } as Record<string, string>)[b.unit || ''] || '값'
  // "P1 현재 불편": a known ID at the start becomes a chip with its hover card; anything else stays text.
  const label = (s: string) => {
    const [first, ...rest] = String(s).split(' ')
    return tip?.lookup(first) ? <span className="inline-flex flex-wrap items-center gap-2"><Badge chip={{ text: first }} />{rest.join(' ')}</span> : s
  }
  return (
    <Panel b={b}>
      <div className="overflow-x-auto">
        <table className={L.table}>
          <thead><tr><th className={cn(L.th, 'w-14')}>No</th><th className={L.th}>항목</th><th className={cn(L.th, 'text-right')}>{head}</th><th className={cn(L.th, 'hidden w-[32%] sm:table-cell')}><span className="sr-only">막대</span></th></tr></thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td className={cn(L.td, 'whitespace-nowrap tabular-nums text-muted-foreground')}>{i + 1}</td>
                <td className={L.td}>{label(it.label)}{it.note && <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{it.note}</div>}</td>
                <td className={cn(L.td, 'whitespace-nowrap text-right font-semibold tabular-nums')}>{fmt(it.value)}<span className="ml-0.5 text-xs font-medium text-muted-foreground">{b.unit || ''}</span></td>
                <td className={cn(L.td, 'hidden align-middle sm:table-cell')}>
                  <div className={cn('h-2 rounded-full', isMono(id) ? 'bg-white' : 'bg-muted')}>
                    <div className="h-full rounded-full" style={{ width: barWidth(it.value, max), background: isMono(id) ? '#111111' : hex[tone(it.tone || b.tone || 'blue')] }} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function Donut({ b }: P) {
  const id = useId()
  return <Panel b={b}>{id === 'analytics' ? <SegmentBar b={b} /> : <SkinDonut b={b} arc={isDense(id) ? 20 : id === 'mono' ? 24 : 30} />}</Panel>
}
const Bars = ({ b }: P) => { const id = useId(); return <Panel b={b}><SkinBars b={b} round={isMono(id) ? 8 : 4} thin={isMono(id)} /></Panel> }
const Line = ({ b }: P) => { const id = useId(); return <Panel b={b}><SkinLine b={b} area={id === 'navy' || id === 'analytics'} /></Panel> }

// --- table --------------------------------------------------------------------------------------------------------
function Cell({ kind, v, cls }: { kind?: string; v: unknown; cls: string }) {
  if (v == null || v === '') return <td className={cn(cls, 'text-muted-foreground')}>–</td>
  if (kind === 'chips') return <td className={cls}><Badges items={(Array.isArray(v) ? v : [v]) as Chip[]} /></td>
  if (kind === 'pill') return <td className={cls}><Badge chip={typeof v === 'string' ? { text: v } : (v as Chip)} /></td>
  if (kind === 'link') {
    const o = v as { href?: string; text?: string } | string
    const h = safeHref(typeof o === 'string' ? o : o.href)
    const label = typeof o === 'string' ? '열기' : o.text || '열기'
    return <td className={cn(cls, 'whitespace-nowrap')}>{h ? <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{label}<ExternalLink className="size-3" /></a> : '–'}</td>
  }
  const k = kind === 'mono' ? 'whitespace-nowrap font-mono text-xs' : kind === 'wide' ? 'min-w-64 max-w-md whitespace-pre-line' :
    kind === 'mid' ? 'min-w-40 max-w-64' : kind === 'num' ? 'whitespace-nowrap text-right tabular-nums' :
    String(v).length <= 12 ? 'whitespace-nowrap' : 'min-w-28'
  return <td className={cn(cls, k)}>{typeof v === 'number' ? fmt(v) : <Md text={String(v)} />}</td>
}

const FILTER: Record<SkinId, { wrap: string; on: string; off: string }> = {
  navy: { wrap: 'flex flex-wrap gap-1.5', on: 'h-8 rounded-full bg-[#4f5bd5] px-3 text-[12.5px] font-medium text-white', off: 'h-8 rounded-full px-3 text-[12.5px] text-[#5d6378] ring-1 ring-inset ring-[#e3e6ee] hover:bg-[#f5f6fa]' },
  mono: { wrap: 'flex flex-wrap gap-2', on: 'h-10 rounded-full bg-zinc-950 px-4 text-[13px] font-medium text-white', off: 'h-10 rounded-full border border-zinc-300 px-4 text-[13px] text-zinc-700 hover:bg-zinc-50' },
  ops: { wrap: 'inline-flex flex-wrap rounded-md bg-[#efefef] p-0.5', on: 'h-7 rounded bg-white px-2.5 text-[12px] font-medium text-zinc-900 shadow-xs', off: 'h-7 rounded px-2.5 text-[12px] text-zinc-600 hover:text-zinc-900' },
  monoops: { wrap: 'flex flex-wrap gap-1.5', on: 'h-8 rounded-full bg-zinc-950 px-3 text-[12.5px] font-medium text-white', off: 'h-8 rounded-full border border-zinc-300 px-3 text-[12.5px] text-zinc-700 hover:bg-zinc-50' },
  analytics: { wrap: 'inline-flex flex-wrap rounded-lg bg-[#f4f4f5] p-1', on: 'h-7 rounded-md bg-white px-2.5 text-[13px] font-medium text-zinc-900 shadow-xs ring-1 ring-black/5', off: 'h-7 rounded-md px-2.5 text-[13px] text-zinc-600 hover:text-zinc-900' },
}

function TableBlock({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  const F = FILTER[id]
  const { cols, shown, filters, q, setQ, f, setF } = useTableRows(b)
  const tools = (b.search || b.filter) && (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      {b.search && (
        <label className="relative min-w-52 flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={b.search_placeholder || '검색'} aria-label="표 검색"
            className={cn(L.input, 'w-full pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring/30')} />
        </label>
      )}
      {b.filter && (
        <div className={F.wrap} role="group" aria-label="구분 거르기">
          {['', ...filters].map((v) => <button key={v || 'all'} type="button" onClick={() => setF(v)} aria-pressed={f === v} className={f === v ? F.on : F.off}>{v || '전체'}</button>)}
        </div>
      )}
    </div>
  )
  return (
    <Panel b={b}>
      {tools}
      <div className="overflow-x-auto">
        <table className={L.table}>
          <thead><tr>{cols.map((c) => <th key={c.key} className={cn(L.th, c.kind === 'num' && 'text-right')}>{c.label}</th>)}</tr></thead>
          <tbody className={id === 'navy' || id === 'analytics' ? '[&_tr:hover]:bg-muted/50' : undefined}>
            {shown.map((r, i) => <tr key={i}>{cols.map((c) => <Cell key={c.key} kind={c.kind} v={r[c.key]} cls={L.td} />)}</tr>)}
          </tbody>
        </table>
      </div>
      {b.count !== false && <p className="mt-2 text-xs text-muted-foreground">{fmt(shown.length)}건</p>}
    </Panel>
  )
}

// --- text pieces --------------------------------------------------------------------------------------------------
function Clamp({ text, lines = 3, quote }: { text: string; lines?: 3 | 5; quote?: boolean }) {
  const [open, setOpen] = useState(false)
  const long = text.length > lines * 50
  return (
    <div>
      <p className={cn('whitespace-pre-line', !open && long && (lines === 3 ? 'line-clamp-3' : 'line-clamp-5'))}>{quote ? <>“{text}”</> : <Md text={text} />}</p>
      {long && <button type="button" onClick={() => setOpen(!open)} className="mt-1 text-xs font-medium text-blue-700 hover:underline">{open ? '접기' : '더 보기'}</button>}
    </div>
  )
}

const NOTE = {
  info: { soft: 'bg-blue-50/70 ring-blue-200/70 text-blue-950', bar: 'border-l-blue-500', ic: 'text-blue-600', chip: 'bg-blue-50 text-blue-600', icon: Info },
  success: { soft: 'bg-emerald-50/70 ring-emerald-200/70 text-emerald-950', bar: 'border-l-emerald-500', ic: 'text-emerald-600', chip: 'bg-emerald-50 text-emerald-600', icon: CheckCircle2 },
  warning: { soft: 'bg-amber-50/80 ring-amber-200/80 text-amber-950', bar: 'border-l-amber-500', ic: 'text-amber-600', chip: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
  error: { soft: 'bg-rose-50/80 ring-rose-200/80 text-rose-950', bar: 'border-l-rose-500', ic: 'text-rose-600', chip: 'bg-rose-100 text-rose-700', icon: OctagonAlert },
} as const

function Callout({ b }: P) {
  const id = useId()
  const n = NOTE[(b.tone as keyof typeof NOTE) in NOTE ? (b.tone as keyof typeof NOTE) : 'info']
  const Icon = n.icon
  const navyInfo = id === 'navy' && n === NOTE.info
  if (isMono(id)) {
    const small = id === 'monoops'
    return (
      // Warnings and errors keep a light tint even in the black-and-white views, so they are never read as plain notes.
      <div role="note" className={cn('flex items-start leading-relaxed text-zinc-900', small ? 'gap-3 rounded-[18px] px-4 py-3 text-[14px]' : 'gap-4 rounded-[22px] px-5 py-4 text-[15px]',
        n === NOTE.warning ? 'bg-amber-50 ring-1 ring-inset ring-amber-200/80' : n === NOTE.error ? 'bg-rose-50 ring-1 ring-inset ring-rose-200/80' : 'bg-white')}>
        <span className={cn('grid shrink-0 place-items-center rounded-full', small ? 'size-8' : 'size-9', n.chip)}><Icon className="size-4" aria-hidden /></span>
        <div className="min-w-0 self-center">{<Md text={b.text} />}</div>
      </div>
    )
  }
  if (id === 'ops') {
    return (
      <div role="note" className={cn('flex gap-2.5 rounded-md border border-l-[3px] border-[#e6e6e6] bg-white px-3 py-2.5 text-[13px] leading-relaxed text-zinc-800', n.bar)}>
        <Icon className={cn('mt-0.5 size-4 shrink-0', n.ic)} aria-hidden /><div className="min-w-0"><Md text={b.text} /></div>
      </div>
    )
  }
  return (
    <div role="note" className={cn('flex gap-3 px-4 py-3.5 leading-relaxed ring-1 ring-inset', id === 'navy' ? 'rounded-[10px] text-[14.5px]' : 'rounded-xl text-[14px]',
      navyInfo ? 'bg-[#eef0fd]/80 text-[#262b4a] ring-[#dfe2fb]' : n.soft)}>
      <Icon className={cn('mt-0.5 size-4 shrink-0', navyInfo ? 'text-[#4f5bd5]' : n.ic)} aria-hidden /><div className="min-w-0"><Md text={b.text} /></div>
    </div>
  )
}

function Heading({ b }: P) { return <h2 className={useLook().heading}>{b.text}</h2> }
function Section({ b }: P) { return <h3 className={useLook().section}>{b.text}</h3> }

function Row({ b, copy }: P) {
  const L = useLook()
  const cols: Block[] = b.cols || []
  return (
    <div className={cn('grid @3xl:[grid-template-columns:var(--cols)]', L.gap)} style={{ ['--cols' as string]: cols.map((c) => `minmax(0,${c.span || 1}fr)`).join(' ') }}>
      {cols.map((c, i) => <div key={i} className={cn('flex min-w-0 flex-col', L.gap)}><Blocks blocks={c.blocks || []} copy={copy} /></div>)}
    </div>
  )
}

function Quotes({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  const hex = useToneHex()
  const title = b.title && <span className="flex items-center gap-2">{b.chip && <span aria-hidden className="size-2.5 rounded-full" style={{ background: hex[tone(b.chip.tone)] }} />}{b.title}</span>
  return (
    <Panel b={b} title={title || undefined}>
      <ul className={cn('flex flex-col', id === 'mono' ? 'gap-3' : id === 'monoops' ? 'gap-2' : 'divide-y divide-[#eef0f4]')}>
        {(b.items || []).map((q: Block, i: number) => {
          const h = safeHref(q.href)
          return (
            <li key={i} className={cn('flex', id === 'mono' ? 'gap-4 rounded-[20px] bg-[#f6f6f6] p-4' : id === 'monoops' ? 'gap-3 rounded-[16px] bg-[#f6f6f6] p-3' : id === 'ops' ? 'gap-4 py-3 first:pt-0 last:pb-0' : 'gap-4 py-4 first:pt-0 last:pb-0')}>
              {isMono(id) && <span aria-hidden className={cn('grid shrink-0 place-items-center rounded-full bg-white shadow-[0_4px_14px_rgb(0_0_0/0.06)]', id === 'mono' ? 'size-11' : 'size-9')}><Quote className="size-4" /></span>}
              <figure className="min-w-0 flex-1">
                <blockquote className={L.quote}><Clamp text={q.quote || ''} quote /></blockquote>
                <figcaption className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  <Badges items={q.chips} />{q.meta && <span>{q.meta}</span>}
                  {h && <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">원문 페이지<ExternalLink className="size-3" /></a>}
                </figcaption>
              </figure>
            </li>
          )
        })}
      </ul>
    </Panel>
  )
}

// Pain → feature → remaining → proposal columns as the builder grouped them. K, J and M also draw them as a route.
function Chain({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  const cols: Block[] = b.columns || []
  return (
    <div className="@container min-w-0">
      {(isDense(id) || id === 'mono') && cols.length > 1 && (
        <div className={cn(L.card, 'overflow-x-auto', id === 'ops' ? 'mb-3 px-4 py-4' : id === 'mono' ? 'mb-5 px-6 py-5' : 'mb-4 px-5 py-4')}>
          <ol className="relative flex min-w-max items-center justify-between gap-6 px-2" aria-label="대조 순서">
            <span aria-hidden className={cn('absolute inset-x-6 top-1/2 h-0.5 -translate-y-1/2 rounded-full', id === 'ops' ? 'bg-[#dfe9e1]' : 'bg-[#e2e2e2]')} />
            {cols.map((c, i) => (
              <li key={i} className={cn('relative font-medium ring-4 ring-white', id === 'ops' ? 'rounded-md px-2.5 py-1 text-[12px]' : 'rounded-full px-3.5 py-1.5 text-[13px]',
                i === cols.length - 1 ? (id === 'ops' ? 'bg-[#2f8f57] text-white' : 'bg-zinc-950 text-white') : 'bg-[#f1f1f1] text-zinc-700')}>{c.title}</li>
            ))}
          </ol>
        </div>
      )}
      <div className={cn('grid @3xl:grid-cols-2 @6xl:grid-flow-col @6xl:auto-cols-fr @6xl:grid-cols-none', L.gap)}>
        {cols.map((c, i) => (
          <div key={i} className="flex min-w-0 flex-col gap-3">
            <div className={cn('flex items-center gap-2', id === 'mono' ? 'px-2 text-[17px] font-semibold text-zinc-950' : id === 'monoops' ? 'px-1 text-[14px] font-semibold text-zinc-900' : id === 'ops' ? 'text-[12px] font-semibold text-zinc-500' : 'text-[13px] font-semibold text-muted-foreground')}>
              <span className={cn('grid size-6 place-items-center rounded-full text-[11px] font-semibold', L.badge)}>{i + 1}</span>{c.title}
              {i < cols.length - 1 && <ArrowRight className="ml-auto hidden size-3.5 text-muted-foreground @6xl:block" aria-hidden />}
            </div>
            {(c.nodes || []).map((n: Block, k: number) => (
              <div key={k} className={cn(L.card, 'flex flex-col gap-2', id === 'ops' ? 'p-3 text-[13px]' : id === 'mono' ? 'p-5 text-[15px]' : id === 'monoops' ? 'p-4 text-[13.5px]' : 'p-4 text-[14px]')}>
                {n.id && <Badge chip={{ text: n.id + (n.title ? ' · ' + n.title : ''), tone: n.tone }} className="self-start" />}
                {n.text && <div className="leading-relaxed"><Clamp text={n.text} lines={5} /></div>}
                <Badges items={n.tags} />
              </div>
            ))}
            {!(c.nodes || []).length && <p className="text-xs text-muted-foreground">항목 없음</p>}
          </div>
        ))}
      </div>
      <Source text={b.source} />
    </div>
  )
}

function Steps({ b }: P) {
  const id = useId()
  const items: string[] = b.items || []
  if (isDense(id)) {
    return (
      <ol className={cn('relative ml-1.5 flex flex-col gap-3 border-l-2 py-1 pl-5 text-[13.5px] leading-relaxed', id === 'ops' ? 'border-[#dfe9e1]' : 'border-[#e2e2e2]')}>
        {items.map((x, i) => (
          <li key={i} className="relative"><span aria-hidden className={cn('absolute -left-[27px] top-1.5 size-3 rounded-full border-2 border-white', id === 'ops' ? 'bg-[#2f8f57]' : 'bg-zinc-950')} />
            <span className="mr-2 font-mono text-[11px] text-zinc-400">{String(i + 1).padStart(2, '0')}</span><Md text={x} /></li>
        ))}
      </ol>
    )
  }
  return (
    <ol className="flex flex-col gap-2.5">
      {items.map((x, i) => (
        <li key={i} className={cn('flex gap-3 leading-relaxed', id === 'mono' ? 'text-[15px]' : 'text-[14.5px]')}>
          <span className={cn('grid size-6 shrink-0 place-items-center rounded-full text-[11px] font-semibold', LOOK[id].badge)}>{i + 1}</span><span className="min-w-0"><Md text={x} /></span>
        </li>
      ))}
    </ol>
  )
}

function Cards({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  const feat = b.type === 'features'
  return (
    <div className={cn('@container grid gap-3 @xl:grid-cols-2 @5xl:grid-cols-3', id === 'mono' && 'gap-4')}>
      {(b.items || []).map((c: Block, i: number) => (
        <div key={i} className={cn(L.card, id === 'ops' ? 'p-3.5' : id === 'mono' ? 'p-6' : id === 'monoops' ? 'p-4' : 'p-5', 'flex min-w-0 gap-3')}>
          {b.numbered && <span className={cn('grid size-7 shrink-0 place-items-center rounded-full text-xs font-semibold', L.badge)}>{i + 1}</span>}
          <div className="min-w-0">
            <div className={cn('font-semibold', id === 'mono' ? 'text-[17px]' : isDense(id) ? 'text-[14px]' : 'text-[15px]')}>{c.title}</div>
            <p className={cn('mt-1.5 leading-relaxed text-muted-foreground', isDense(id) ? 'text-[13px]' : feat ? 'text-sm' : 'text-[14.5px]')}><Md text={c.text} /></p>
            <Badges items={c.chips} className="mt-2" />
          </div>
        </div>
      ))}
    </div>
  )
}

function Expander({ b, copy }: P) {
  const id = useId()
  const L = LOOK[id]
  return (
    <details className={cn('group', L.card)} open={!!b.open}>
      <summary className={cn('flex cursor-pointer list-none items-center justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden',
        id === 'ops' ? 'px-4 py-3 text-[14px]' : id === 'mono' ? 'px-7 py-5 text-[17px]' : id === 'monoops' ? 'px-5 py-3.5 text-[15px]' : 'px-5 py-4 text-[15px]')}>
        <span>{b.title}</span>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className={cn('flex flex-col border-t', L.gap, isDense(id) ? 'px-5 py-4' : id === 'mono' ? 'px-7 py-6' : 'px-5 py-5')}><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </details>
  )
}

// Copy fields: the label above, the value in a field with its copy button inside.
function Files({ b, copy }: P) {
  const id = useId()
  const L = LOOK[id]
  const h = safeHref(b.href)
  const field = isMono(id) ? 'rounded-full bg-[#f4f4f4] pl-5 pr-1.5' : id === 'ops' ? 'rounded-md border border-[#e6e6e6] bg-[#fafafa] pl-3 pr-1' : 'rounded-lg border bg-muted/50 pl-3 pr-1.5'
  return (
    <div className={cn(L.card, L.pad, 'flex flex-col', isDense(id) ? 'gap-3' : 'gap-4')}>
      {(b.items || []).map((f: Block, i: number) => (
        <div key={i} className="min-w-0">
          <div className="mb-1.5 text-[13px] text-muted-foreground">{f.label}</div>
          <div className={cn('flex min-h-10 items-center gap-2 py-1', field)}>
            <span className="min-w-0 flex-1 break-all font-mono text-xs">{f.value}</span>
            {f.copy !== false && (
              <button type="button" onClick={() => copy(String(f.value))} className={cn('inline-flex h-8 shrink-0 items-center gap-1.5 border bg-white px-2.5 text-xs font-medium hover:bg-accent', isMono(id) ? 'rounded-full' : 'rounded-md')}>
                <Copy className="size-3.5" aria-hidden />복사
              </button>
            )}
          </div>
        </div>
      ))}
      {h && <a className="inline-flex items-center gap-1 text-sm text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{b.href_label || '파일 열기'}<ExternalLink className="size-3.5" aria-hidden /></a>}
    </div>
  )
}

// --- story page ---------------------------------------------------------------------------------------------------
function Hero({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  return (
    <section className="@container flex min-w-0 flex-col gap-4">
      <div className={cn(L.card, id === 'mono' ? 'p-7 sm:p-10' : isDense(id) ? 'p-5' : 'p-6 sm:p-8')}>
        <div className={cn('text-[13px]', id === 'navy' ? 'font-semibold text-[#4f5bd5]' : id === 'analytics' ? 'font-medium text-orange-600' : id === 'ops' ? 'text-[#2f7d4f]' : 'text-zinc-500')}>{b.eyebrow}</div>
        <h1 className={cn('mt-3 max-w-4xl text-balance font-bold leading-snug tracking-tight',
          id === 'mono' ? 'text-[30px] font-semibold sm:text-[40px]' : id === 'ops' ? 'text-[22px] font-semibold' : id === 'monoops' ? 'text-[24px] font-semibold sm:text-[28px]' : 'text-[26px] sm:text-[30px]')}>{b.title}</h1>
        {b.subtitle && <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted-foreground"><Md text={b.subtitle} /></p>}
        <Badges items={b.chips} className="mt-5" />
      </div>
      {b.stats?.length > 0 && <Kpis items={b.stats} />}
    </section>
  )
}

// Story claims (현재 불편 · 기존 기능): A puts them in two columns, so a single item left half the row empty. Here one
// item takes the whole row with its quotes beside the text, and several items share the row (two, or three when wide).
// Same items, text, quotes and chips as A; only the arrangement differs.
function Claims({ b }: P) {
  const id = useId()
  const L = LOOK[id]
  const items: Block[] = b.items || []
  const t = tone(b.tone)
  const one = items.length === 1
  const size = id === 'mono' ? 'text-[17px]' : id === 'ops' ? 'text-[14.5px]' : 'text-[15px]'
  return (
    <div className="@container">
      <div className={cn('grid', L.gap, !one && '@3xl:grid-cols-2', items.length >= 3 && '@7xl:grid-cols-3')}>
        {items.map((it, i) => {
          const quotes = (it.quotes || []).length > 0
          const head = (
            <>
              <div className="flex items-center gap-2">
                <Badge chip={{ text: it.id, tone: t }} />
                {b.kind_label && <span className="text-xs text-muted-foreground">{b.kind_label}</span>}
              </div>
              <p className={cn('font-medium leading-relaxed', size)}><Md text={it.text} /></p>
            </>
          )
          const quoteList = quotes && <div className="flex min-w-0 flex-col gap-2">{it.quotes.map((q: Block, k: number) => <QuoteLine key={k} q={q} />)}</div>
          return one && quotes ? (
            <article key={i} className={cn(L.card, L.pad, 'grid min-w-0 gap-4 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] @3xl:items-start @3xl:gap-8')}>
              <div className="flex min-w-0 flex-col gap-3">{head}<Badges items={it.chips} /></div>
              {quoteList}
            </article>
          ) : (
            <article key={i} className={cn(L.card, L.pad, 'flex min-w-0 flex-col gap-3')}>
              {head}{quoteList}<Badges items={it.chips} />
            </article>
          )
        })}
      </div>
    </div>
  )
}

const SECTION_NO: Record<string, number> = { problem: 1, check: 2, flow: 3, solution: 4, trust: 5 }

// K only (the user's choice): short report-style section titles. The count is the one in build_view.py's own title;
// when a title has no count the original title stays.
const REPORT_TITLES: Record<string, (n: string | null) => string | null> = {
  problem: (n) => (n ? `현재 불편 ${n}건 확인` : null),
  check: (n) => (n ? `기존 기능 ${n}건과 대조` : null),
  flow: () => '불편 → 남은 불편 → 제안',
  solution: (n) => (n ? `남은 불편 대응 제안 ${n}건` : null),
  trust: () => '근거 신뢰도와 한계',
}
function reportTitle(b: Block): string {
  const n = /(\d+)\s*(?:가지|개)/.exec(String(b.title || ''))?.[1] ?? null
  return REPORT_TITLES[b.key]?.(n) || b.title
}

function StorySection({ b, copy }: P) {
  const id = useId()
  const L = LOOK[id]
  const no = SECTION_NO[b.key]
  const name = String(b.label || '').split('·').pop()?.trim()
  const label = { navy: 'font-semibold text-[#4f5bd5]', mono: 'text-zinc-500', ops: 'font-medium text-[#2f7d4f]', analytics: 'font-medium text-orange-600', monoops: 'text-zinc-500' }[id]
  const title = { navy: 'text-[22px] font-bold', mono: 'text-[30px] font-semibold', ops: 'text-[17px] font-semibold', analytics: 'text-[20px] font-semibold', monoops: 'text-[22px] font-semibold' }[id]
  return (
    <section className={cn('flex flex-col', id === 'ops' ? 'mt-4 gap-3' : id === 'monoops' ? 'mt-6 gap-4' : 'mt-8 gap-4', id === 'mono' ? 'gap-5' : '')}>
      <div className={id === 'ops' ? 'border-b border-[#e6e6e6] pb-2' : ''}>
        <div className={cn('text-[13px]', label)}>{no ? `${no}. ` : ''}{name}</div>
        <h2 className={cn('mt-1 text-balance tracking-tight text-foreground', title)}>{id === 'ops' ? reportTitle(b) : b.title}</h2>
        {b.text && <p className={cn('mt-1.5 max-w-3xl leading-relaxed text-muted-foreground', id === 'ops' ? 'text-[13px]' : 'text-[15px]')}><Md text={b.text} /></p>}
      </div>
      <div className={cn('flex flex-col', L.gap)}><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </section>
  )
}

const Tiles = ({ b }: P) => <Kpis items={b.items || []} source={b.source} />
const KpiBlock = ({ b }: P) => <Kpis items={b.items || []} source={b.source} />

const COMMON: Record<string, BlockRenderer> = {
  kpis: KpiBlock, metrics: Metrics, hbars: HBars, donut: Donut, bars: Bars, line: Line, table: TableBlock, callout: Callout,
  heading: Heading, section: Section, row: Row, quotes: Quotes, chain: Chain, steps: Steps, cards: Cards, features: Cards,
  expander: Expander, files: Files, hero: Hero, story: StorySection, tiles: Tiles, claims: Claims,
}

// Chart colours per view. Tones keep their meaning (red = pain, green = supported, orange = uncertain …).
const HEXES: Record<SkinId, Skin['hex']> = {
  navy: { blue: '#4f5bd5', green: '#1f9d6b', red: '#e5484d', orange: '#f5a524', purple: '#7c5cff', gray: '#b4b9c6' },
  mono: { blue: '#2563eb', green: '#16a34a', red: '#e11d48', orange: '#f59e0b', purple: '#7c3aed', gray: '#a3a3a3' },
  ops: { blue: '#2f80ed', green: '#2f9e5b', red: '#e5484d', orange: '#f2994a', purple: '#8b5cf6', gray: '#a3a3a3' },
  analytics: { blue: '#7170f5', green: '#3ccf6e', red: '#ef5350', orange: '#f7931e', purple: '#a78bfa', gray: '#b8b8c0' },
  monoops: { blue: '#2563eb', green: '#16a34a', red: '#e11d48', orange: '#f59e0b', purple: '#7c3aed', gray: '#a3a3a3' },
}
const GREYS = ['#111111', '#c9c9c9', '#6b6b6b', '#e4e4e4', '#3f3f46', '#a3a3a3']

export const SKINS: Record<SkinId, Skin> = {
  navy: { id: 'navy', blocks: COMMON, hex: HEXES.navy },
  mono: { id: 'mono', blocks: COMMON, hex: HEXES.mono, series: GREYS },
  ops: { id: 'ops', blocks: COMMON, hex: HEXES.ops },
  analytics: { id: 'analytics', blocks: COMMON, hex: HEXES.analytics },
  monoops: { id: 'monoops', blocks: COMMON, hex: HEXES.monoops, series: GREYS },
}

