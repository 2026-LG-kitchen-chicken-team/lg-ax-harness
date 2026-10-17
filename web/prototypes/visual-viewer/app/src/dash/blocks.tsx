// Block renderers of K 업무형 (compact operations look). They take the blocks build_view.py writes and change only
// how they look. Layout only: no counting, ranking or judging here; block types not listed in SKIN fall through to the
// base renderers (components/blocks.tsx, components/story.tsx).
import { useState, type CSSProperties, type ReactNode } from 'react'
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronDown, Copy, ExternalLink, Info, OctagonAlert, Search } from 'lucide-react'
import { Badge, Badges } from '../components/ui'
import { Blocks, useTableRows } from '../components/blocks'
import { QuoteLine } from '../components/story'
import { useIdTip } from '../components/idtip'
import { HoverNote, SourceNote as SourceTip } from '../components/hovernote'
import { Lead } from '../components/lead'
import { barWidth, NoData, SkinBars, SkinDonut, SkinLine, useToneHex } from './charts'
import { type BlockRenderer, type Skin } from '../lib/skin'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, Chip } from '../types'

type P = { b: Block; copy: (s: string) => void }

// cn() keeps tailwind-merge's rule that a later font size drops an earlier line height; a few class lists below are
// split into cn() arguments on purpose, so the drawn line heights stay as they were.

// Surfaces and type. Colours that carry meaning (tones, warnings) keep their family.
export const LOOK = {
  gap: 'gap-3', card: 'rounded-lg border border-[#e6e6e6] bg-white', pad: 'p-4',
  title: 'text-[15px] font-semibold text-zinc-900',
  heading: 'mt-5 border-b border-[#e6e6e6] pb-2 text-[17px] font-semibold text-zinc-900',
  section: 'mt-2 text-[14px] font-semibold text-zinc-900',
  table: 'w-full text-[13px]',
  th: 'h-9 whitespace-nowrap bg-[#f3f3f3] px-3 text-left align-middle text-[12px] font-medium text-zinc-600 first:rounded-l-md last:rounded-r-md',
  td: 'border-b border-[#efefef] px-3 py-2.5 align-top text-zinc-800',
  input: 'h-8 rounded-md border border-[#e3e3e3] bg-white', badge: 'bg-[#e6f1e8] text-[#2f7d4f]',
  quote: 'text-[13.5px] leading-relaxed text-zinc-800',
}

// Where a number comes from stays one step away: a small "출처" mark that shows it on hover, focus or tap.
const Source = ({ text }: { text?: string }) => (text ? <div className="mt-1.5 flex justify-end"><SourceTip text={text} /></div> : null)

function Panel({ b, title, children, className }: { b: Block; title?: ReactNode; children: ReactNode; className?: string }) {
  const t = title ?? b.title
  return (
    <section className={cn('@container min-w-0', LOOK.card, LOOK.pad, className)}>
      {t && <div className={cn(LOOK.title, 'mb-4')}>{t}</div>}
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

// --- KPI rows ---------------------------------------------------------------------------------------------------
type Kpi = { label: string; value: number | string; unit?: string; tone?: string; note?: string; source?: string }
const kpiGrid = (n: number): { className: string; style: CSSProperties } => ({
  className: 'grid grid-cols-2 @max-3xl:[&>*:last-child:nth-child(odd)]:col-span-2 @3xl:[grid-template-columns:repeat(var(--n),minmax(0,1fr))]',
  style: { ['--n' as string]: Math.min(Math.max(n, 1), 6) },
})

function Kpis({ items, source }: { items: Kpi[]; source?: string }) {
  const hex = useToneHex()
  if (!items.length) return null
  const g = kpiGrid(items.length)
  return (
    <div className="@container min-w-0">
      <div className={cn(g.className, 'gap-3')} style={g.style}>
        {items.map((k, i) => (
          <div key={i} className={cn(LOOK.card, 'min-w-0 p-4')} title={k.source ? '출처: ' + k.source : undefined}>
            <div className="flex items-center gap-2 text-[13px] text-zinc-600"><span aria-hidden className="size-2 rounded-[2px]" style={{ background: hex[tone(k.tone)] }} />{k.label}</div>
            {/* lg-num: K motion 2, the stored number settles into place (no counting; index.css). */}
            <div className={cn('lg-num mt-3 font-medium leading-tight tracking-tight tabular-nums', vsize(k.value, k.unit, ['text-[30px]', 'text-xl', 'text-sm break-all']), tone(k.tone) === 'gray' ? 'text-zinc-500' : 'text-zinc-950')}
              style={{ ['--i' as string]: Math.min(i, 4) }}>
              {fmt(k.value)}{k.unit && <span className="ml-1 text-[13px] font-normal text-zinc-500">{k.unit}</span>}
            </div>
            {k.note && <div className="mt-1.5 text-[12px] leading-snug text-zinc-500">{k.note}</div>}
          </div>
        ))}
      </div>
      <Source text={source} />
    </div>
  )
}

// --- label/value strips (metrics) --------------------------------------------------------------------------------
function Metrics({ b }: P) {
  const items: Kpi[] = b.items || []
  return (
    <div className={cn(LOOK.card, '@container', 'px-4 py-3')}>
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

// --- charts -------------------------------------------------------------------------------------------------------
type Bar = { label: string; value: number; tone?: string; note?: string }

function HBars({ b }: P) {
  const items: Bar[] = b.items || []
  if (items.length > 6) return <BarTable b={b} />
  return <Panel b={b}>{items.length ? <BarRows b={b} items={items} /> : <NoData />}</Panel>
}

function BarRows({ b, items }: { b: Block; items: Bar[] }) {
  const hex = useToneHex()
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map((it, i) => (
        <li key={i} className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3.5rem] items-center gap-3 text-[13px]" title={it.note || undefined}>
          <span className="truncate text-zinc-600">{it.label}</span>
          <span className="h-1.5 rounded-full bg-[#f0f0f0]"><span className="block h-full rounded-full" style={{ width: barWidth(it.value, max), background: hex[tone(it.tone || b.tone || 'blue')] }} /></span>
          <span className="text-right font-semibold tabular-nums text-zinc-900">{fmt(it.value)}<span className="ml-0.5 text-[0.8em] font-medium text-muted-foreground">{b.unit || ''}</span></span>
        </li>
      ))}
    </ul>
  )
}

// Many bars (e.g. every item's linked evidence) read better as a table with a small bar per row.
function BarTable({ b }: { b: Block }) {
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
        <table className={LOOK.table}>
          <thead><tr><th className={cn(LOOK.th, 'w-14')}>No</th><th className={LOOK.th}>항목</th><th className={cn(LOOK.th, 'text-right')}>{head}</th><th className={cn(LOOK.th, 'hidden w-[32%] sm:table-cell')}><span className="sr-only">막대</span></th></tr></thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td className={cn(LOOK.td, 'whitespace-nowrap tabular-nums text-muted-foreground')}>{i + 1}</td>
                <td className={LOOK.td}>{label(it.label)}{it.note && <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{it.note}</div>}</td>
                <td className={cn(LOOK.td, 'whitespace-nowrap text-right font-semibold tabular-nums')}>{fmt(it.value)}<span className="ml-0.5 text-xs font-medium text-muted-foreground">{b.unit || ''}</span></td>
                <td className={cn(LOOK.td, 'hidden align-middle sm:table-cell')}>
                  <div className="h-2 rounded-full bg-muted">
                    <div className="h-full rounded-full" style={{ width: barWidth(it.value, max), background: hex[tone(it.tone || b.tone || 'blue')] }} />
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

const Donut = ({ b }: P) => <Panel b={b}><SkinDonut b={b} arc={20} /></Panel>
const Bars = ({ b }: P) => <Panel b={b}><SkinBars b={b} round={4} /></Panel>
const Line = ({ b }: P) => <Panel b={b}><SkinLine b={b} /></Panel>

// --- table --------------------------------------------------------------------------------------------------------
// What a cell shows, and its width/wrapping class. Short codes are drawn in the body font (no mono).
function cellBody(kind: string | undefined, v: unknown): ReactNode {
  if (v == null || v === '') return '–'
  if (kind === 'chips') return <Badges items={(Array.isArray(v) ? v : [v]) as Chip[]} />
  if (kind === 'pill') return <Badge chip={typeof v === 'string' ? { text: v } : (v as Chip)} />
  if (kind === 'link') {
    const o = v as { href?: string; text?: string } | string
    const h = safeHref(typeof o === 'string' ? o : o.href)
    const label = typeof o === 'string' ? '열기' : o.text || '열기'
    return h ? <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{label}<ExternalLink className="size-3" /></a> : '–'
  }
  return typeof v === 'number' ? fmt(v) : <Md text={String(v)} />
}
function cellClass(kind: string | undefined, v: unknown): string {
  if (v == null || v === '') return 'text-muted-foreground'
  if (kind === 'chips' || kind === 'pill') return ''
  if (kind === 'link') return 'whitespace-nowrap'
  return kind === 'mono' ? 'whitespace-nowrap tabular-nums' : kind === 'wide' ? 'min-w-64 max-w-md whitespace-pre-line' :
    kind === 'mid' ? 'min-w-40 max-w-64' : kind === 'num' ? 'whitespace-nowrap text-right tabular-nums' :
    String(v).length <= 12 ? 'whitespace-nowrap' : 'min-w-28'
}
function Cell({ kind, v, cls }: { kind?: string; v: unknown; cls: string }) {
  return <td className={cn(cls, cellClass(kind, v))}>{cellBody(kind, v)}</td>
}

// Columns a planner rarely reads first (long IDs, SHA-256, dates, disclosure and version codes) fold into each row's
// "상세". Short codes that name a row (T1, p1) and times stay. Nothing is removed: every value is one click away, and
// "모든 열" brings the full table back.
const SECONDARY_LABELS = new Set(['SHA-256', '게시·관측일', '구매·협찬·고지', '표현', '모델 범위', '기록 호출', '자료', '버전', 'result_key', '모델'])
const isSecondary = (c: Block, rows: Block[]) => SECONDARY_LABELS.has(c.label)
  || (c.kind === 'mono' && !/시각/.test(c.label) && rows.some((r) => String(r[c.key] ?? '').length > 4))

const FILTER = { wrap: 'inline-flex flex-wrap rounded-md bg-[#efefef] p-0.5', on: 'h-7 rounded bg-white px-2.5 text-[12px] font-medium text-zinc-900 shadow-xs', off: 'h-7 rounded px-2.5 text-[12px] text-zinc-600 hover:bg-white/70 hover:text-zinc-900' }

// The search box and filter sit above the table; the rows they leave are drawn below.
function TableBlock({ b }: P) {
  const { cols, shown, filters, q, setQ, f, setF } = useTableRows(b)
  const rows: Block[] = b.rows || []
  const [all, setAll] = useState(false)
  const [open, setOpen] = useState<Set<number>>(() => new Set())
  const folded = cols.filter((c) => isSecondary(c, rows))
  const fold = !all && folded.length > 0 && cols.length - folded.length >= 2
  const visible = fold ? cols.filter((c) => !folded.includes(c)) : cols
  const toggle = (k: number) => setOpen((s) => { const n = new Set(s); if (n.has(k)) n.delete(k); else n.add(k); return n })
  return (
    <Panel b={b}>
      {(b.search || b.filter) && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {b.search && (
            <label className="relative min-w-52 flex-1">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={b.search_placeholder || '검색'} aria-label="표 검색"
                className={cn(LOOK.input, 'w-full pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring/30')} />
            </label>
          )}
          {b.filter && (
            <div className={FILTER.wrap} role="group" aria-label="구분 거르기">
              {['', ...filters].map((v) => <button key={v || 'all'} type="button" onClick={() => setF(v)} aria-pressed={f === v} className={f === v ? FILTER.on : FILTER.off}>{v || '전체'}</button>)}
            </div>
          )}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className={LOOK.table}>
          <thead><tr>
            {visible.map((c) => <th key={c.key} className={cn(LOOK.th, c.kind === 'num' && 'text-right')}>{c.label}</th>)}
            {/* relative: the screen-reader label must stay inside the scroll box (an unanchored sr-only span widens the page). */}
            {fold && <th className={cn(LOOK.th, 'relative w-14')}><span className="sr-only">상세</span></th>}
          </tr></thead>
          <tbody className="[&>tr:hover>td]:bg-[#f7faf7]">
            {shown.map((r) => {
              const k = rows.indexOf(r)
              const on = fold && open.has(k)
              return [
                <tr key={k} className={on ? '[&>td]:border-b-0' : undefined}>
                  {visible.map((c) => <Cell key={c.key} kind={c.kind} v={r[c.key]} cls={LOOK.td} />)}
                  {fold && (
                    <td className={cn(LOOK.td, 'whitespace-nowrap text-right')}>
                      <button type="button" onClick={() => toggle(k)} aria-expanded={on} className="inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[12px] text-zinc-500 hover:bg-[#e6f1e8] hover:text-[#2f7d4f]">
                        상세<ChevronDown className={cn('size-3.5 transition-transform', on && 'rotate-180')} aria-hidden />
                      </button>
                    </td>
                  )}
                </tr>,
                on && (
                  <tr key={k + '-more'}>
                    <td colSpan={visible.length + 1} className="border-b border-[#efefef] bg-[#fafafa] px-3 py-2.5">
                      <dl className="lg-open grid gap-x-6 gap-y-1.5 text-[12.5px] sm:grid-cols-2">
                        {folded.map((c) => (
                          <div key={c.key} className="flex min-w-0 items-baseline gap-2">
                            <dt className="w-24 shrink-0 text-zinc-500">{c.label}</dt>
                            <dd className={cn('min-w-0 whitespace-pre-line text-zinc-800', c.kind === 'mono' && 'break-all font-mono text-[11.5px]')}>{cellBody(c.kind, r[c.key])}</dd>
                          </div>
                        ))}
                      </dl>
                    </td>
                  </tr>
                ),
              ]
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
        {b.count !== false && <span>{fmt(shown.length)}건</span>}
        {folded.length > 0 && cols.length - folded.length >= 2 && (
          <button type="button" onClick={() => setAll(!all)} aria-pressed={all} className="rounded px-1 text-zinc-500 underline-offset-2 hover:text-zinc-900 hover:underline">
            {all ? '주요 열만 보기' : `접힌 열 ${folded.length}개 모두 보기`}
          </button>
        )}
      </div>
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
  info: { bar: 'border-l-blue-500', ic: 'text-blue-600', icon: Info },
  success: { bar: 'border-l-emerald-500', ic: 'text-emerald-600', icon: CheckCircle2 },
  warning: { bar: 'border-l-amber-500', ic: 'text-amber-600', icon: AlertTriangle },
  error: { bar: 'border-l-rose-500', ic: 'text-rose-600', icon: OctagonAlert },
} as const

function Callout({ b }: P) {
  const n = NOTE[(b.tone as keyof typeof NOTE) in NOTE ? (b.tone as keyof typeof NOTE) : 'info']
  const Icon = n.icon
  // One hue: notes and successes take K's green; warnings and errors keep amber and rose.
  const calm = n === NOTE.info || n === NOTE.success
  return (
    <div role="note" className={cn('flex gap-2.5 rounded-md border border-l-[3px] border-[#e6e6e6] bg-white px-3 py-2.5 text-[13px] leading-relaxed text-zinc-800', calm ? 'border-l-[#5fae80]' : n.bar)}>
      <Icon className={cn('mt-0.5 size-4 shrink-0', calm ? 'text-[#2f8f57]' : n.ic)} aria-hidden /><div className="min-w-0"><Md text={b.text} /></div>
    </div>
  )
}

const Heading = ({ b }: P) => <h2 className={LOOK.heading}>{b.text}</h2>
const Section = ({ b }: P) => <h3 className={LOOK.section}>{b.text}</h3>

function Row({ b, copy }: P) {
  const cols: Block[] = b.cols || []
  return (
    <div className={cn('grid @3xl:[grid-template-columns:var(--cols)]', LOOK.gap)} style={{ ['--cols' as string]: cols.map((c) => `minmax(0,${c.span || 1}fr)`).join(' ') }}>
      {cols.map((c, i) => <div key={i} className={cn('flex min-w-0 flex-col', LOOK.gap)}><Blocks blocks={c.blocks || []} copy={copy} /></div>)}
    </div>
  )
}

function Quotes({ b }: P) {
  const hex = useToneHex()
  const title = b.title && <span className="flex items-center gap-2">{b.chip && <span aria-hidden className="size-2.5 rounded-full" style={{ background: hex[tone(b.chip.tone)] }} />}{b.title}</span>
  return (
    <Panel b={b} title={title || undefined}>
      <ul className="flex flex-col divide-y divide-[#eef0f4]">
        {(b.items || []).map((q: Block, i: number) => {
          const h = safeHref(q.href)
          return (
            <li key={i} className="flex gap-4 py-3 first:pt-0 last:pb-0">
              <figure className="min-w-0 flex-1">
                <blockquote className={LOOK.quote}><Clamp text={q.quote || ''} quote /></blockquote>
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

// Pain → feature → remaining → proposal columns as the builder grouped them, with the order drawn as a route above.
function Chain({ b }: P) {
  const cols: Block[] = b.columns || []
  return (
    <div className="@container min-w-0">
      {cols.length > 1 && (
        <div className={cn(LOOK.card, 'overflow-x-auto', 'mb-3 px-4 py-4')}>
          <ol className="relative flex min-w-max items-center justify-between gap-6 px-2" aria-label="대조 순서">
            <span aria-hidden className="absolute inset-x-6 top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-[#dfe9e1]" />
            {cols.map((c, i) => (
              <li key={i} className={cn('relative font-medium ring-4 ring-white', 'rounded-md px-2.5 py-1 text-[12px]',
                i === cols.length - 1 ? 'bg-[#2f8f57] text-white' : 'bg-[#f1f1f1] text-zinc-700')}>{c.title}</li>
            ))}
          </ol>
        </div>
      )}
      <div className={cn('grid @3xl:grid-cols-2 @6xl:grid-flow-col @6xl:auto-cols-fr @6xl:grid-cols-none', LOOK.gap)}>
        {cols.map((c, i) => (
          <div key={i} className="flex min-w-0 flex-col gap-3">
            <div className="flex items-center gap-2 text-[12px] font-semibold text-zinc-500">
              <span className={cn('grid size-6 place-items-center rounded-full text-[11px] font-semibold', LOOK.badge)}>{i + 1}</span>{c.title}
              {i < cols.length - 1 && <ArrowRight className="ml-auto hidden size-3.5 text-muted-foreground @6xl:block" aria-hidden />}
            </div>
            {(c.nodes || []).map((n: Block, k: number) => (
              <div key={k} className={cn(LOOK.card, 'flex flex-col gap-2', 'p-3 text-[13px]')}>
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
  const items: string[] = b.items || []
  return (
    <ol className="relative ml-1.5 flex flex-col gap-3 border-l-2 border-[#dfe9e1] py-1 pl-5 text-[13.5px] leading-relaxed">
      {items.map((x, i) => (
        <li key={i} className="relative"><span aria-hidden className="absolute -left-[27px] top-1.5 size-3 rounded-full border-2 border-white bg-[#2f8f57]" />
          <span className="mr-2 font-mono text-[11px] text-zinc-400">{String(i + 1).padStart(2, '0')}</span><Md text={x} /></li>
      ))}
    </ol>
  )
}

function Cards({ b }: P) {
  return (
    <div className="@container grid gap-3 @xl:grid-cols-2 @5xl:grid-cols-3">
      {(b.items || []).map((c: Block, i: number) => (
        <div key={i} className={cn(LOOK.card, 'p-3.5', 'flex min-w-0 gap-3')}>
          {b.numbered && <span className={cn('grid size-7 shrink-0 place-items-center rounded-full text-xs font-semibold', LOOK.badge)}>{i + 1}</span>}
          <div className="min-w-0">
            <div className="text-[14px] font-semibold">{c.title}</div>
            <p className={cn('mt-1.5 leading-relaxed text-muted-foreground', 'text-[13px]')}><Md text={c.text} /></p>
            <Badges items={c.chips} className="mt-2" />
          </div>
        </div>
      ))}
    </div>
  )
}

function Expander({ b, copy }: P) {
  return (
    <details className={cn('group', LOOK.card)} open={!!b.open}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg px-4 py-3 text-[14px] font-semibold hover:bg-[#f3f8f4] hover:text-[#2f7d4f] group-open:rounded-b-none [&::-webkit-details-marker]:hidden">
        <span>{b.title}</span>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className={cn('flex flex-col border-t', LOOK.gap, 'px-5 py-4')}><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </details>
  )
}

// Copy fields: the label above, the value in a field with its copy button inside. The path (where the file is) stays,
// its long hash shortened (복사 still copies all of it); file name, size, SHA-256 and versions fold under "파일 상세".
function Files({ b, copy }: P) {
  const h = safeHref(b.href)
  const items: Block[] = b.items || []
  const row = (f: Block, i: number, short = false) => (
    <div key={i} className="min-w-0">
      <div className="mb-1.5 text-[13px] text-muted-foreground">{f.label}</div>
      <div className="flex min-h-10 items-center gap-2 rounded-md border border-[#e6e6e6] bg-[#fafafa] py-1 pl-3 pr-1">
        <span className="min-w-0 flex-1 break-all font-mono text-xs" title={short ? String(f.value) : undefined}>{short ? shortHex(String(f.value)) : f.value}</span>
        {f.copy !== false && (
          <button type="button" onClick={() => copy(String(f.value))} className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md border bg-white px-2.5 text-xs font-medium hover:border-[#2f8f57]/40 hover:bg-[#f3f8f4] hover:text-[#2f7d4f]">
            <Copy className="size-3.5" aria-hidden />복사
          </button>
        )}
      </div>
    </div>
  )
  const main = items.filter((f) => f.label === '경로')
  const rest = main.length ? items.filter((f) => !main.includes(f)) : []
  return (
    <div className={cn(LOOK.card, LOOK.pad, 'flex flex-col', 'gap-3')}>
      {(rest.length ? main : items).map((f, i) => row(f, i, rest.length > 0))}
      {rest.length > 0 && (
        <details className="group/f">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-[12px] text-zinc-500 hover:text-zinc-900 [&::-webkit-details-marker]:hidden">
            파일 상세<span className="text-zinc-400">({rest.map((f) => f.label).join(' · ')})</span>
            <ChevronDown className="size-3.5 transition-transform group-open/f:rotate-180" aria-hidden />
          </summary>
          <div className="mt-3 flex flex-col gap-3">{rest.map((f, i) => row(f, i))}</div>
        </details>
      )}
      {h && <a className="inline-flex items-center gap-1 text-sm text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{b.href_label || '파일 열기'}<ExternalLink className="size-3.5" aria-hidden /></a>}
    </div>
  )
}
// "export-ce4bac11b8886e56…b281d6ca.json": a long hex run keeps its ends.
const shortHex = (s: string) => s.replace(/[0-9a-f]{20,}/g, (h) => `${h.slice(0, 8)}…${h.slice(-6)}`)

// Chips that are codes or times (versions, start time) fold into a "세부 N" mark that lists them on hover; a row of
// chips that are all codes (the model) stays as it is. Three or more passed checks ("✓ …") become one "✓ 통과 N개"
// chip that lists them on hover, so failures and scope stand out. The source note sits at the end.
function Chips({ b }: P) {
  const items: Chip[] = (b.items || []).map((c: Chip | string) => (typeof c === 'string' ? { text: c } : c))
  const main = items.filter((c) => !c.mono)
  const extra = main.length ? items.filter((c) => c.mono) : []
  const passed = main.filter((c) => c.text.startsWith('✓'))
  const fold = passed.length >= 3
  return (
    <div className="flex flex-col gap-1.5">
      {b.title && <div className="text-xs font-medium text-muted-foreground">{b.title}</div>}
      <div className="flex flex-wrap items-center gap-1.5">
        {fold && (
          <HoverNote note={<ul className="flex flex-col gap-0.5">{passed.map((c, i) => <li key={i}>{c.text}</li>)}</ul>}
            className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
            ✓ 통과 {passed.length}개<Info className="size-3 opacity-70" aria-hidden />
          </HoverNote>
        )}
        {(main.length ? main : items).filter((c) => !(fold && passed.includes(c))).map((c, i) => <Badge key={i} chip={{ ...c, mono: false }} />)}
        {extra.length > 0 && (
          <HoverNote note={<ul className="flex flex-col gap-0.5">{extra.map((c, i) => <li key={i}>{c.text}</li>)}</ul>}
            className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs text-zinc-500 ring-1 ring-inset ring-zinc-200 hover:text-zinc-900">
            <Info className="size-3" aria-hidden />세부 {extra.length}
          </HoverNote>
        )}
        {b.source && <SourceTip text={b.source} />}
      </div>
    </div>
  )
}

// --- story page ---------------------------------------------------------------------------------------------------
function Hero({ b }: P) {
  if (b.planner) return <header className="py-2">
    <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-[24px] font-semibold leading-snug tracking-tight">{b.title}</h1><Badges items={b.chips} /></div>
    {b.scope && <details className="mt-2 text-[12px] text-zinc-500">
      <summary className="cursor-pointer leading-relaxed">자료 범위 · {b.scope.models}개 모델 · 후기 {b.scope.reviews}건 · 제품자료 {b.scope.facts}건{b.scope.other > 0 && ` · 기타 ${b.scope.other}건`}{b.scope.as_of && ` · 관측 ${b.scope.as_of}`}</summary>
      <p className="mt-2 leading-relaxed">이번 결과에 전달된 등록 자료의 범위예요. 제안별 ‘근거 확인’은 그중 해당 제안이 인용한 자료를 보여줘요. 자료 건수는 고객 수나 시장 비율과 달라요. <a className="underline" href="#dashboard">자료 전체 보기</a></p>
    </details>}
  </header>
  return (
    <section className="@container flex min-w-0 flex-col gap-4">
      <div className={cn(LOOK.card, 'p-5')}>
        <div className="text-[13px] text-[#2f7d4f]">{b.eyebrow}</div>
        <h1 className={cn('mt-3 max-w-4xl text-balance font-bold leading-snug tracking-tight', 'text-[22px] font-semibold')}>{b.title}</h1>
        {b.subtitle && <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted-foreground"><Md text={b.subtitle} /></p>}
        <Badges items={b.chips} className="mt-5" />
      </div>
      {b.stats?.length > 0 && <Kpis items={b.stats} />}
    </section>
  )
}

// Story claims (현재 불편 · 기존 기능): one item takes the whole row with its quotes beside the text, and several items
// share the row (two, or three when wide).
function Claims({ b }: P) {
  const items: Block[] = b.items || []
  const t = tone(b.tone)
  const one = items.length === 1
  return (
    <div className="@container">
      <div className={cn('grid', LOOK.gap, !one && '@3xl:grid-cols-2', items.length >= 3 && '@7xl:grid-cols-3')}>
        {items.map((it, i) => {
          const quotes = (it.quotes || []).length > 0
          const head = (
            <>
              <div className="flex items-center gap-2">
                <Badge chip={{ text: it.id, tone: t }} />
                {b.kind_label && <span className="text-xs text-muted-foreground">{b.kind_label}</span>}
              </div>
              {/* The model's summary (or the first sentence) here; the ID chip above opens the whole text. */}
              <p className={cn('font-medium leading-relaxed', 'text-[14.5px]')}><Lead text={it.text} summary={it.summary} /></p>
            </>
          )
          const quoteList = quotes && <div className="flex min-w-0 flex-col gap-2">{it.quotes.map((q: Block, k: number) => <QuoteLine key={k} q={q} />)}</div>
          return one && quotes ? (
            <article key={i} className={cn(LOOK.card, LOOK.pad, 'grid min-w-0 gap-4 @3xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] @3xl:items-start @3xl:gap-8')}>
              <div className="flex min-w-0 flex-col gap-3">{head}<Badges items={it.chips} /></div>
              {quoteList}
            </article>
          ) : (
            <article key={i} className={cn(LOOK.card, LOOK.pad, 'flex min-w-0 flex-col gap-3')}>
              {head}{quoteList}<Badges items={it.chips} />
            </article>
          )
        })}
      </div>
    </div>
  )
}

const SECTION_NO: Record<string, number> = { problem: 1, check: 2, flow: 3, solution: 4, trust: 5 }

// Short report-style section titles (the user's choice). The count is the one in build_view.py's own title; when a
// title has no count the original title stays.
const REPORT_TITLES: Record<string, (n: string | null) => string | null> = {
  problem: (n) => (n ? `현재 불편 ${n}건 확인` : null),
  check: (n) => (n ? `기존 기능 ${n}건과 대조` : null),
  flow: () => '불편 → 기존 기능 → 남은 불편 → 제안',
  solution: (n) => (n ? `남은 불편 대응 제안 ${n}건` : null),
  trust: () => '근거 신뢰도와 한계',
}
function reportTitle(b: Block): string {
  const n = /(\d+)\s*(?:가지|개)/.exec(String(b.title || ''))?.[1] ?? null
  return REPORT_TITLES[b.key]?.(n) || b.title
}

function StorySection({ b, copy }: P) {
  if (b.planner) return <section aria-label={b.title} className="flex flex-col gap-4"><Blocks blocks={b.blocks || []} copy={copy} /></section>
  const no = b.planner ? undefined : SECTION_NO[b.key]
  const name = String(b.label || '').split('·').pop()?.trim()
  return (
    <section className="mt-4 flex flex-col gap-3">
      <div className="border-b border-[#e6e6e6] pb-2">
        <div className="text-[13px] font-medium text-[#2f7d4f]">{no ? `${no}. ` : ''}{name}</div>
        <h2 className="mt-1 text-balance text-[17px] font-semibold tracking-tight text-foreground">{b.planner ? b.title : reportTitle(b)}</h2>
        {b.text && <p className={cn('mt-1.5 max-w-3xl leading-relaxed text-muted-foreground', 'text-[13px]')}><Md text={b.text} /></p>}
      </div>
      <div className={cn('flex flex-col', LOOK.gap)}><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </section>
  )
}

const KpiBlock = ({ b }: P) => <Kpis items={b.items || []} source={b.source} />

const BLOCKS: Record<string, BlockRenderer> = {
  kpis: KpiBlock, metrics: Metrics, hbars: HBars, donut: Donut, bars: Bars, line: Line, table: TableBlock, callout: Callout,
  heading: Heading, section: Section, row: Row, quotes: Quotes, chain: Chain, steps: Steps, cards: Cards, features: Cards,
  expander: Expander, files: Files, hero: Hero, story: StorySection, tiles: KpiBlock, claims: Claims, chips: Chips,
}

// Chart colours: the green ramp carries the colour; warnings and failures keep a muted amber and rose.
export const SKIN: Skin = {
  id: 'ops',
  blocks: BLOCKS,
  hex: { blue: '#5fae80', green: '#2f8f57', red: '#c4615b', orange: '#cf9442', purple: '#1d5c39', gray: '#a3a3a3', k1: '#9ccfb0', k2: '#5fae80', k3: '#2f8f57', k4: '#1d5c39' },
}
