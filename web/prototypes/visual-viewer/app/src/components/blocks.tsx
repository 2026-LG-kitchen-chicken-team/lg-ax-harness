// Renders the block list that build_view.py writes for each page. Layout only: no counting or judging here.
import { useMemo, useState, type ReactNode } from 'react'
import { ArrowRight, ChevronDown, Copy, ExternalLink, Search } from 'lucide-react'
import {
  Alert, Badge, Badges, Button, Card, CardContent, CardHeader, CardTitle, Table, TBody, TD, TH, THead, TR,
} from './ui'
import { BarList, DonutChart, GroupedBarChart, LineChart } from './charts'
import { StatValue } from './magic'
import { STORY_BLOCKS } from './story'
import { useSkin } from '../lib/skin'
import { cn, fmt, Md, safeHref, tone, TONE_DOT, TONE_TEXT } from '../lib/utils'
import type { Block, Chip } from '../types'

export function Blocks({ blocks, copy }: { blocks: Block[]; copy: (s: string) => void }) {
  return <>{blocks.map((b, i) => <BlockView key={i} b={b} copy={copy} />)}</>
}

export function Source({ text }: { text?: string }) {
  if (!text) return null
  return <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">출처: {text}</p>
}

function ChartCard({ b, children }: { b: Block; children: ReactNode }) {
  return (
    <Card className="min-w-0">
      {b.title && <CardHeader><CardTitle>{b.title}</CardTitle></CardHeader>}
      <CardContent className={b.title ? '' : 'pt-5'}>
        {children}
        <Source text={b.source} />
      </CardContent>
    </Card>
  )
}

export function BlockView({ b, copy }: { b: Block; copy: (s: string) => void }): ReactNode {
  // The dashboard views (I–L) draw some block types their own way; everything else falls through to A's renderers.
  const Own = useSkin()?.blocks[b.type]
  if (Own) return <Own b={b} copy={copy} />
  const Story = STORY_BLOCKS[b.type]
  if (Story) return <Story b={b} copy={copy} />
  switch (b.type) {
    case 'lead': return <p className="max-w-3xl text-[17px] leading-relaxed text-zinc-600"><Md text={b.text} /></p>
    case 'text': return <p className="max-w-3xl text-[15px] leading-7"><Md text={b.text} /></p>
    case 'divider': return <hr className="my-2 border-border" />
    case 'heading':
      return <h2 className="mt-8 flex items-center gap-3 text-[22px] font-bold tracking-tight"><span aria-hidden className="h-5 w-1 shrink-0 rounded-full bg-[#ea1917]" />{b.text}</h2>
    case 'section':
      return <h3 className="mt-6 flex items-center gap-2 text-base font-bold"><span aria-hidden className="size-1.5 shrink-0 rounded-full bg-[#ea1917]" />{b.text}</h3>
    case 'callout': return <Alert tone={b.tone}><Md text={b.text} /></Alert>
    case 'chips':
      return (
        <div className="flex flex-col gap-2">
          {b.title && <div className="text-xs font-medium text-muted-foreground">{b.title}</div>}
          <Badges items={b.items} />
          {b.source && <p className="text-[11px] text-muted-foreground">출처: {b.source}</p>}
        </div>
      )
    case 'kpis': return <Kpis b={b} />
    case 'metrics': return <Metrics b={b} />
    case 'hbars': return <ChartCard b={b}><BarList b={b} /></ChartCard>
    case 'donut': return <ChartCard b={b}><DonutChart b={b} /></ChartCard>
    case 'bars': return <ChartCard b={b}><GroupedBarChart b={b} /></ChartCard>
    case 'line': return <ChartCard b={b}><LineChart b={b} /></ChartCard>
    case 'row': {
      const cols: Block[] = b.cols || []
      return (
        <div className="grid gap-4 @3xl:[grid-template-columns:var(--cols)]" style={{ ['--cols' as string]: cols.map((c) => `minmax(0,${c.span || 1}fr)`).join(' ') }}>
          {cols.map((c, i) => <div key={i} className="flex min-w-0 flex-col gap-4"><Blocks blocks={c.blocks || []} copy={copy} /></div>)}
        </div>
      )
    }
    case 'table': return <DataTable b={b} />
    case 'quotes': return <Quotes b={b} />
    case 'chain': return <Chain b={b} />
    case 'cards':
      return (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(b.items || []).map((c: Block, i: number) => (
            <Card key={i} className="p-4">
              <div className="flex items-start gap-3">
                {b.numbered && <span className="grid size-6 shrink-0 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{i + 1}</span>}
                <div className="min-w-0">
                  <div className="text-sm font-semibold">{c.title}</div>
                  <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground"><Md text={c.text} /></p>
                  <Badges items={c.chips} className="mt-2" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )
    case 'list':
      return (
        <div>
          {b.title && <div className="mb-2 text-sm font-semibold">{b.title}</div>}
          <ul className="flex list-disc flex-col gap-2 pl-5 text-[15px] leading-relaxed marker:text-muted-foreground">
            {(b.items || []).map((x: string, i: number) => <li key={i}><Md text={x} /></li>)}
          </ul>
        </div>
      )
    case 'steps':
      return (
        <ol className="flex flex-col gap-2">
          {(b.items || []).map((x: string, i: number) => (
            <li key={i} className="flex gap-3 text-[15px] leading-relaxed">
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-muted text-[11px] font-semibold">{i + 1}</span>
              <span><Md text={x} /></span>
            </li>
          ))}
        </ol>
      )
    case 'features':
      return (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {(b.items || []).map((f: Block, i: number) => (
            <Card key={i} className="p-4">
              <div className="text-sm font-semibold">{f.title}</div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground"><Md text={f.text} /></p>
            </Card>
          ))}
        </div>
      )
    case 'expander': return <Expander b={b} copy={copy} />
    case 'code': return <pre className="overflow-x-auto rounded-xl bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-100">{b.text}</pre>
    case 'files': return <Files b={b} copy={copy} />
    default: return null
  }
}

function Kpis({ b }: { b: Block }) {
  const items: Block[] = b.items || []
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {items.map((k, i) => {
          const t = tone(k.tone)
          return (
            <Card key={i} className="relative overflow-hidden p-4" title={k.source ? '출처: ' + k.source : undefined}>
              <div className="flex items-center gap-2 text-[13px] font-medium text-muted-foreground">
                <span className={cn('size-2 rounded-full', TONE_DOT[t])} />{k.label}
              </div>
              <div className={cn('mt-2 text-4xl font-bold tracking-tight', t === 'gray' ? 'text-zinc-500' : 'text-foreground')}>
                <StatValue value={k.value} />
                {k.unit && <span className="ml-0.5 text-base font-medium text-muted-foreground">{k.unit}</span>}
              </div>
              {k.note && <div className="mt-1 text-xs text-muted-foreground">{k.note}</div>}
            </Card>
          )
        })}
      </div>
      <Source text={b.source} />
    </div>
  )
}

function Metrics({ b }: { b: Block }) {
  return (
    <Card className="grid grid-cols-2 divide-border md:grid-cols-3 xl:grid-cols-6 [&>*]:border-b md:[&>*]:border-r">
      {(b.items || []).map((m: Block, i: number) => {
        const long = String(m.value ?? '').length + String(m.unit ?? '').length > 9
        return (
          <div key={i} className="min-w-0 p-4">
            <div className="text-[13px] text-muted-foreground">{m.label}</div>
            <div className={cn('mt-1 font-semibold tracking-tight', long ? 'text-base' : 'text-2xl')}>
              {fmt(m.value)}{m.unit ? <span className="ml-0.5 text-sm font-medium text-muted-foreground">{m.unit}</span> : null}
            </div>
            {m.note && <div className="mt-1 text-xs text-muted-foreground">{m.note}</div>}
          </div>
        )
      })}
    </Card>
  )
}

function Cell({ kind, v }: { kind?: string; v: unknown }) {
  if (v == null || v === '') return <TD className="text-muted-foreground">–</TD>
  if (kind === 'chips') return <TD><Badges items={(Array.isArray(v) ? v : [v]) as Chip[]} /></TD>
  if (kind === 'pill') return <TD><Badge chip={typeof v === 'string' ? { text: v } : (v as Chip)} /></TD>
  if (kind === 'link') {
    const o = v as { href?: string; text?: string } | string
    const h = safeHref(typeof o === 'string' ? o : o.href)
    const label = typeof o === 'string' ? '열기' : o.text || '열기'
    return <TD className="whitespace-nowrap">{h ? <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{label}<ExternalLink className="size-3" /></a> : '–'}</TD>
  }
  const cls = kind === 'mono' ? 'font-mono text-xs whitespace-nowrap' : kind === 'wide' ? 'min-w-64 max-w-md whitespace-pre-line' :
    kind === 'mid' ? 'min-w-40 max-w-64' : kind === 'num' ? 'text-right tabular-nums whitespace-nowrap' :
    String(v).length <= 12 ? 'whitespace-nowrap' : 'min-w-28'
  return <TD className={cls}>{typeof v === 'number' ? fmt(v) : <Md text={String(v)} />}</TD>
}

// Search box and filter chips of a table block (shared by A and F). Filters only hide rows; nothing is re-counted.
export function useTableRows(b: Block) {
  const cols: Block[] = b.columns || []
  const rows: Block[] = b.rows || []
  const [q, setQ] = useState('')
  const [f, setF] = useState('')
  const text = (r: Block) => cols.map((c) => { const v = r[c.key]; return typeof v === 'object' && v ? JSON.stringify(v) : String(v ?? '') }).join(' ').toLowerCase()
  const fval = (r: Block) => { const v = b.filter ? r[b.filter] : ''; return typeof v === 'object' && v ? v.text : v }
  const filters: string[] = useMemo(() => (b.filter ? Array.from(new Set(rows.map(fval).filter(Boolean))) : []), [rows, b.filter]) // eslint-disable-line react-hooks/exhaustive-deps
  const shown = rows.filter((r) => (!q || text(r).includes(q.toLowerCase())) && (!f || fval(r) === f))
  return { cols, shown, filters, q, setQ, f, setF }
}

function DataTable({ b }: { b: Block }) {
  const { cols, shown, filters, q, setQ, f, setF } = useTableRows(b)
  return (
    <Card className="min-w-0">
      {(b.title || b.search || b.filter) && (
        <CardHeader className="gap-3">
          {b.title && <CardTitle>{b.title}</CardTitle>}
          {(b.search || b.filter) && (
            <div className="flex flex-wrap items-center gap-2">
              {b.search && (
                <label className="relative min-w-52 flex-1">
                  <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" aria-hidden />
                  <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={b.search_placeholder || '검색'} aria-label="표 검색"
                    className="h-9 w-full rounded-md border bg-background pl-8 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring/40" />
                </label>
              )}
              {b.filter && ['', ...filters].map((v) => (
                <button key={v || 'all'} type="button" onClick={() => setF(v)} aria-pressed={f === v}
                  className={cn('h-8 rounded-full border px-3 text-xs', f === v ? 'border-primary bg-primary text-primary-foreground' : 'bg-background hover:bg-accent')}>
                  {v || '전체'}
                </button>
              ))}
            </div>
          )}
        </CardHeader>
      )}
      <CardContent className={b.title || b.search || b.filter ? '' : 'pt-2'}>
        <Table>
          <THead><TR className="hover:bg-transparent">{cols.map((c) => <TH key={c.key}>{c.label}</TH>)}</TR></THead>
          <TBody className="[&_tr:nth-child(even)]:bg-zinc-50/70">{shown.map((r, i) => <TR key={i}>{cols.map((c) => <Cell key={c.key} kind={c.kind} v={r[c.key]} />)}</TR>)}</TBody>
        </Table>
        {b.count !== false && <p className="mt-2 text-xs text-muted-foreground">{fmt(shown.length)}건</p>}
        <Source text={b.source} />
      </CardContent>
    </Card>
  )
}

function Clamp({ text, lines = 3, quote }: { text: string; lines?: number; quote?: boolean }) {
  const [open, setOpen] = useState(false)
  const long = text.length > (lines * 50)
  return (
    <div>
      <p className={cn('whitespace-pre-line text-[15px] leading-relaxed', !open && long && (lines === 3 ? 'line-clamp-3' : 'line-clamp-5'))}>
        {quote ? <>“{text}”</> : <Md text={text} />}
      </p>
      {long && <button type="button" onClick={() => setOpen(!open)} className="mt-1 text-xs font-medium text-blue-700 hover:underline">{open ? '접기' : '더 보기'}</button>}
    </div>
  )
}

function Quotes({ b }: { b: Block }) {
  return (
    <Card>
      {b.title && <CardHeader><CardTitle className="flex items-center gap-2">{b.chip && <span className={cn('size-2.5 rounded-full', TONE_DOT[tone(b.chip.tone)])} />}{b.title}</CardTitle></CardHeader>}
      <CardContent className={cn('flex flex-col divide-y', b.title ? '' : 'pt-5')}>
        {(b.items || []).map((q: Block, i: number) => {
          const h = safeHref(q.href)
          return (
            <figure key={i} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0">
              <blockquote className="border-l-2 border-zinc-300 pl-3"><Clamp text={q.quote || ''} quote /></blockquote>
              <figcaption className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                <Badges items={q.chips} />
                {q.meta && <span>{q.meta}</span>}
                {h && <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">원문 페이지<ExternalLink className="size-3" /></a>}
              </figcaption>
            </figure>
          )
        })}
      </CardContent>
    </Card>
  )
}

function Chain({ b }: { b: Block }) {
  const cols: Block[] = b.columns || []
  return (
    <div>
      <div className="grid gap-3 @4xl:grid-flow-col @4xl:auto-cols-fr">
        {cols.map((c, i) => (
          <div key={i} className="relative flex min-w-0 flex-col gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              {c.title}
              {i < cols.length - 1 && <ArrowRight className="hidden size-3.5 @4xl:block" aria-hidden />}
            </div>
            {(c.nodes || []).map((n: Block, k: number) => (
              <Card key={k} className="flex flex-col gap-2 p-3">
                {n.id && <Badge chip={{ text: n.id + (n.title ? ' · ' + n.title : ''), tone: n.tone }} className="self-start" />}
                {n.text && <Clamp text={n.text} lines={5} />}
                <Badges items={n.tags} />
              </Card>
            ))}
            {!(c.nodes || []).length && <p className="text-xs text-muted-foreground">항목 없음</p>}
          </div>
        ))}
      </div>
      <Source text={b.source} />
    </div>
  )
}

function Expander({ b, copy }: { b: Block; copy: (s: string) => void }) {
  return (
    <details className="group rounded-xl border bg-card" open={!!b.open}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-[15px] font-semibold [&::-webkit-details-marker]:hidden">
        <span>{b.title}</span>
        <ChevronDown className="size-4 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden />
      </summary>
      <div className="flex flex-col gap-4 border-t px-5 py-5"><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </details>
  )
}

function Files({ b, copy }: { b: Block; copy: (s: string) => void }) {
  const h = safeHref(b.href)
  return (
    <div className="flex flex-col gap-2">
      <Card className="divide-y">
        {(b.items || []).map((f: Block, i: number) => (
          <div key={i} className="grid grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 max-sm:grid-cols-[minmax(0,1fr)_auto]">
            <span className="text-xs text-muted-foreground max-sm:col-span-2">{f.label}</span>
            <span className="break-all font-mono text-xs">{f.value}</span>
            {f.copy !== false ? <Button variant="outline" size="sm" onClick={() => copy(String(f.value))}><Copy className="size-3.5" />복사</Button> : <span />}
          </div>
        ))}
      </Card>
      {h && <a className={cn('inline-flex items-center gap-1 text-sm', TONE_TEXT.blue)} href={h} target="_blank" rel="noopener noreferrer">{b.href_label || '파일 열기'}</a>}
    </div>
  )
}
