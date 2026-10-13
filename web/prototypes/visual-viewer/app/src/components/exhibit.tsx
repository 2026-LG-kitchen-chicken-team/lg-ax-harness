// F: A's sidebar and colours with every page laid out like D's exhibition (big type, thin rules, mono numbers,
// chapter labels, text-roll links). Layout only: build_view.py decides every item, count, label and link. The story
// page reuses D's body (EditorialBody) in light colours; the other pages render the builder's block list here.
// Nothing is counted, ranked or linked in this file.
import { useState, type ReactNode } from 'react'
import { AlertTriangle, ArrowRight, ArrowUpRight, CheckCircle2, Copy, Info, OctagonAlert, Plus, Quote, Search } from 'lucide-react'
import { Badge, Badges, Button } from './ui'
import { DonutChart, GroupedBarChart, LineChart } from './charts'
import { ScrollRing, TextRoll } from './skiper'
import { useTableRows } from './blocks'
import { EditorialBody, LimitTiles, MatchRows, QuoteLine, SkiperCredit, SolutionList } from '../variants/Editorial'
import { ExThemeContext } from '../lib/exTheme'
import type { Story } from '../lib/story'
import { cn, fmt, Md, safeHref, tone, TONE_DOT, TONE_TEXT } from '../lib/utils'
import type { Block, Chip, Page, View } from '../types'

// English chapter words in D's manner; pages the builder does not know (AI insights pages) show only their number.
const WORDS: Record<string, string> = {
  story: 'Story', overview: 'Overview', dashboard: 'Dashboard', screening: 'Screening', compare: 'Check',
  concepts: 'Solution', history: 'History', evidence: 'Evidence', export: 'Export',
}
const pad = (n: number) => String(n).padStart(2, '0')

type CopyFn = (s: string) => void

export function ExhibitPage({ view, page, story, copy, go }: { view: View; page: Page; story: Story | null; copy: CopyFn; go: (id: string) => void }) {
  const i = view.pages.findIndex((p) => p.id === page.id)
  const next = view.pages[i + 1]
  const first = view.pages[0]
  const isStory = page.id === 'story'
  // The story page's status blocks (warnings, stopped requests) stay visible next to D's chapters.
  const notices = page.blocks.filter((b) => b.type !== 'hero' && b.type !== 'story')
  return (
    <ExThemeContext.Provider value="light">
      <div className="hidden lg:block"><ScrollRing /></div>
      {isStory && story?.complete ? (
        <EditorialBody story={story} embedded notices={notices.length ? <ExBlocks blocks={notices} copy={copy} /> : undefined}
          sectionNotes={(key) => <SectionNotes section={story.sections[key]} copy={copy} />} />
      ) : (
        <article className="@container mx-auto flex max-w-6xl flex-col gap-6 px-6 pt-16 sm:pt-20">
          {!isStory && <PageHead no={i + 1} total={view.pages.length} word={WORDS[page.id]} title={page.title} />}
          <ExBlocks blocks={page.blocks} copy={copy} />
        </article>
      )}
      {next ? <NextPage page={next} go={go} label="다음" /> : first && first.id !== page.id ? <NextPage page={first} go={go} label="처음" /> : null}
      <footer className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-10 text-xs text-zinc-400">
        <div>{view.context?.meta} · 화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다.</div>
        <div><SkiperCredit /></div>
      </footer>
    </ExThemeContext.Provider>
  )
}

// Notes the builder put inside a story section ("결과에 제안이 없습니다" ...). D's chapters show only the items, so F adds them.
// The trust section is left out: its one note is the closing statement D already prints in full.
function SectionNotes({ section, copy }: { section?: Block; copy: CopyFn }) {
  const notes = section?.key === 'trust' ? [] : (section?.blocks || []).filter((b: Block) => b.type === 'callout')
  return notes.length ? <div className="mt-10 flex flex-col gap-4"><ExBlocks blocks={notes} copy={copy} /></div> : null
}

function PageHead({ no, total, word, title }: { no: number; total: number; word?: string; title: string }) {
  return (
    <header className="pb-8">
      <div className="flex items-baseline gap-4 text-xs uppercase tracking-[0.3em] text-muted-foreground">
        <span className="font-mono"><span className="font-semibold text-zinc-950">{pad(no)}</span> / {pad(total)}</span>{word}
      </div>
      <h1 className="mt-5 max-w-4xl text-balance text-4xl font-extrabold leading-tight tracking-tight text-zinc-950 sm:text-6xl">{title}</h1>
    </header>
  )
}

// Big text-roll link to the next page (skiper58), like D's index.
function NextPage({ page, go, label }: { page: Page; go: (id: string) => void; label: string }) {
  return (
    <nav className="no-print mx-auto mt-24 max-w-6xl px-6" aria-label={label + ' 화면'}>
      <button type="button" onClick={() => go(page.id)} className="group flex w-full items-baseline gap-6 border-y py-8 text-left">
        <span className="w-12 shrink-0 font-mono text-sm text-zinc-400">{label}</span>
        <TextRoll className="min-w-0 text-5xl font-extrabold uppercase tracking-[-0.03em] text-zinc-950 sm:text-7xl">{WORDS[page.id] || page.nav || page.title}</TextRoll>
        <span className="ml-auto flex shrink-0 items-center gap-2 text-sm text-muted-foreground group-hover:text-zinc-950">{page.nav || page.title}<ArrowRight className="size-4" aria-hidden /></span>
      </button>
    </nav>
  )
}

export function ExBlocks({ blocks, copy }: { blocks: Block[]; copy: CopyFn }) {
  return <>{blocks.map((b, i) => <ExBlock key={i} b={b} copy={copy} />)}</>
}

function ExBlock({ b, copy }: { b: Block; copy: CopyFn }): ReactNode {
  switch (b.type) {
    case 'lead': return <p className="max-w-3xl text-lg leading-relaxed text-zinc-600 sm:text-xl"><Md text={b.text} /></p>
    case 'text': return <p className="max-w-3xl text-[15px] leading-relaxed text-zinc-700"><Md text={b.text} /></p>
    // Headings already carry a rule in this style, so a divider is only space.
    case 'divider': return <div aria-hidden className="h-2" />
    case 'heading': return <h2 className="mt-16 border-t border-zinc-900 pt-8 text-3xl font-extrabold tracking-tight text-zinc-950 sm:text-4xl [header+&]:mt-0">{b.text}</h2>
    case 'section':
      return <h3 className="mt-14 flex items-center gap-4 text-xs uppercase tracking-[0.18em] text-muted-foreground [header+&]:mt-0"><span aria-hidden className="h-px w-10 bg-zinc-900" />{b.text}</h3>
    case 'callout': return <Note tone={b.tone}><Md text={b.text} /></Note>
    case 'chips':
      return (
        <div className="flex flex-col gap-2.5">
          {b.title && <div className="text-xs tracking-widest text-muted-foreground">{b.title}</div>}
          <Badges items={b.items} />
          <Source text={b.source} />
        </div>
      )
    case 'kpis': return <Kpis b={b} />
    case 'metrics': return <Metrics b={b} />
    case 'hbars': return <Figure b={b}><BarRows b={b} /></Figure>
    case 'donut': return <Figure b={b}><DonutChart b={b} /></Figure>
    case 'bars': return <Figure b={b}><GroupedBarChart b={b} /></Figure>
    case 'line': return <Figure b={b}><LineChart b={b} /></Figure>
    case 'row': {
      const cols: Block[] = b.cols || []
      return (
        <div className="grid gap-x-12 gap-y-10 @3xl:[grid-template-columns:var(--cols)]" style={{ ['--cols' as string]: cols.map((c) => `minmax(0,${c.span || 1}fr)`).join(' ') }}>
          {cols.map((c, i) => <div key={i} className="flex min-w-0 flex-col gap-6"><ExBlocks blocks={c.blocks || []} copy={copy} /></div>)}
        </div>
      )
    }
    case 'table': return <Table b={b} />
    case 'quotes': return <Quotes b={b} />
    case 'chain': return <Chain b={b} />
    case 'cards':
      return (
        <div className="grid gap-x-10 gap-y-8 @2xl:grid-cols-2 @5xl:grid-cols-3">
          {(b.items || []).map((c: Block, i: number) => (
            <div key={i} className="flex gap-5 border-t pt-5">
              {b.numbered && <span className="font-mono text-4xl font-light leading-none text-zinc-950">{pad(i + 1)}</span>}
              <div className="min-w-0">
                <div className="text-lg font-semibold text-zinc-950">{c.title}</div>
                <p className="mt-1.5 text-[15px] leading-relaxed text-zinc-600"><Md text={c.text} /></p>
                <Badges items={c.chips} className="mt-3" />
              </div>
            </div>
          ))}
        </div>
      )
    case 'list':
      return (
        <div>
          {b.title && <div className="mb-3 text-lg font-semibold tracking-tight text-zinc-950">{b.title}</div>}
          <ul className="flex flex-col border-t">
            {(b.items || []).map((x: string, i: number) => (
              <li key={i} className="flex gap-4 border-b border-zinc-100 py-3 text-[15px] leading-relaxed text-zinc-700">
                <span aria-hidden className="mt-[0.8em] h-px w-3 shrink-0 bg-zinc-400" /><span className="min-w-0"><Md text={x} /></span>
              </li>
            ))}
          </ul>
        </div>
      )
    case 'steps':
      return (
        <ol className="flex flex-col border-b">
          {(b.items || []).map((x: string, i: number) => (
            <li key={i} className="flex gap-5 border-t py-3 text-[15px] leading-relaxed text-zinc-700">
              <span className="font-mono text-zinc-400">{pad(i + 1)}</span><span className="min-w-0"><Md text={x} /></span>
            </li>
          ))}
        </ol>
      )
    case 'features':
      return (
        <div className="grid gap-x-10 gap-y-8 @2xl:grid-cols-2 @5xl:grid-cols-3">
          {(b.items || []).map((f: Block, i: number) => (
            <div key={i} className="border-t pt-5">
              <div className="text-lg font-semibold text-zinc-950">{f.title}</div>
              <p className="mt-2 text-[15px] leading-relaxed text-zinc-600"><Md text={f.text} /></p>
            </div>
          ))}
        </div>
      )
    case 'expander': return <Expander b={b} copy={copy} />
    case 'code': return <pre className="overflow-x-auto rounded-xl bg-zinc-950 p-5 font-mono text-xs leading-relaxed text-zinc-100">{b.text}</pre>
    case 'files': return <Files b={b} copy={copy} />
    // Story blocks: the story page without a saved result, and AI insights pages that use them.
    case 'hero': return <Hero b={b} />
    case 'story': return <StorySection b={b} copy={copy} />
    case 'claims': return <Claims b={b} />
    case 'matches': return <div><MatchRows items={b.items || []} /><Source text={b.source} /></div>
    case 'flow': return <FlowColumns b={b} />
    case 'solutions': return <SolutionList items={b.items || []} />
    case 'tiles': return <LimitTiles items={b.items || []} />
    default: return null
  }
}

const Source = ({ text }: { text?: string }) => (text ? <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">출처: {text}</p> : null)

// A's alert colours in D's shape: a left bar instead of a box.
const NOTE = {
  info: { cls: 'border-blue-500 bg-blue-50/60 text-blue-950', ic: 'text-blue-600', icon: Info },
  success: { cls: 'border-emerald-500 bg-emerald-50/60 text-emerald-950', ic: 'text-emerald-600', icon: CheckCircle2 },
  warning: { cls: 'border-amber-500 bg-amber-50/70 text-amber-950', ic: 'text-amber-600', icon: AlertTriangle },
  error: { cls: 'border-rose-500 bg-rose-50/70 text-rose-950', ic: 'text-rose-600', icon: OctagonAlert },
} as const
function Note({ tone: t, children }: { tone?: string; children: ReactNode }) {
  const n = NOTE[(t as keyof typeof NOTE) in NOTE ? (t as keyof typeof NOTE) : 'info']
  const Icon = n.icon
  return (
    <div role="note" className={cn('flex max-w-4xl gap-4 border-l-2 py-4 pl-5 pr-6 text-[15px] leading-relaxed', n.cls)}>
      <Icon className={cn('mt-1 size-4 shrink-0', n.ic)} aria-hidden />
      <div className="min-w-0">{children}</div>
    </div>
  )
}

// Numbers in mono like D; words ("미측정", model names) in the text font. Long values get smaller, never cut.
const numeric = (v: unknown) => typeof v === 'number' || /^[\d.,/\s%-]+$/.test(String(v ?? ''))
function valueSize(v: unknown, unit: unknown, sizes: [string, string, string]) {
  const n = String(v ?? '').length + String(unit ?? '').length
  return n <= 5 ? sizes[0] : n <= 12 ? sizes[1] : sizes[2]
}

function Kpis({ b }: { b: Block }) {
  return (
    <div>
      <dl className="grid grid-cols-2 gap-x-10 gap-y-10 @2xl:grid-cols-3 @5xl:grid-cols-5">
        {(b.items || []).map((k: Block, i: number) => {
          const t = tone(k.tone)
          return (
            <div key={i} className="min-w-0 border-t pt-4" title={k.source ? '출처: ' + k.source : undefined}>
              <dt className="flex items-center gap-2 text-xs tracking-widest text-muted-foreground"><span className={cn('size-1.5 rounded-full', TONE_DOT[t])} />{k.label}</dt>
              <dd className={cn('mt-3 font-semibold leading-none tabular-nums', numeric(k.value) ? 'font-mono' : 'font-sans', valueSize(k.value, k.unit, ['text-6xl', 'text-3xl', 'text-lg break-all']), t === 'gray' ? 'text-zinc-400' : 'text-zinc-950')}>
                {fmt(k.value)}{k.unit && <span className="ml-1 font-sans text-base font-medium text-muted-foreground">{k.unit}</span>}
              </dd>
              {k.note && <div className="mt-3 text-sm text-muted-foreground">{k.note}</div>}
            </div>
          )
        })}
      </dl>
      <Source text={b.source} />
    </div>
  )
}

function Metrics({ b }: { b: Block }) {
  return (
    <dl className="grid grid-cols-2 gap-x-8 gap-y-8 @2xl:grid-cols-3 @5xl:grid-cols-6">
      {(b.items || []).map((m: Block, i: number) => (
        <div key={i} className="min-w-0 border-t pt-4">
          <dt className="text-xs tracking-widest text-muted-foreground">{m.label}</dt>
          <dd className={cn('mt-2 font-semibold leading-tight text-zinc-950', numeric(m.value) ? 'font-mono' : 'font-sans', valueSize(m.value, m.unit, ['text-4xl', 'text-2xl', 'text-sm break-all font-mono']))}>
            {fmt(m.value)}{m.unit ? <span className="ml-1 font-sans text-sm font-medium text-muted-foreground">{m.unit}</span> : null}
          </dd>
          {m.note && <div className="mt-2 text-xs text-muted-foreground">{m.note}</div>}
        </div>
      ))}
    </dl>
  )
}

function Figure({ b, children }: { b: Block; children: ReactNode }) {
  return (
    <figure className="min-w-0 border-t pt-5">
      {b.title && <figcaption className="text-lg font-semibold tracking-tight text-zinc-950">{b.title}</figcaption>}
      <div className={b.title ? 'mt-6' : ''}>{children}</div>
      <Source text={b.source} />
    </figure>
  )
}

// Horizontal bars as thin rules with the stored value in big mono type.
function BarRows({ b }: { b: Block }) {
  const items: Block[] = b.items || []
  if (!items.length) return <p className="py-6 text-sm text-muted-foreground">표시할 값이 없습니다.</p>
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  return (
    <ul className="flex flex-col gap-5">
      {items.map((it, i) => (
        <li key={i} title={it.note || undefined}>
          <div className="flex items-baseline justify-between gap-4">
            <span className="min-w-0 truncate text-sm text-zinc-600">{it.label}</span>
            <span className="shrink-0 font-mono text-2xl font-semibold tabular-nums text-zinc-950">{fmt(it.value)}<span className="ml-1 font-sans text-sm font-medium text-muted-foreground">{b.unit || ''}</span></span>
          </div>
          <div className="mt-2 h-1.5 rounded-full bg-zinc-100">
            <div className={cn('h-full rounded-full', TONE_DOT[tone(it.tone || b.tone || 'blue')])} style={{ width: `${Math.max(it.value > 0 ? 2 : 0, (it.value / max) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

function Cell({ kind, v }: { kind?: string; v: unknown }) {
  const td = 'px-3 py-3 align-top first:pl-0'
  if (v == null || v === '') return <td className={cn(td, 'text-zinc-400')}>–</td>
  if (kind === 'chips') return <td className={td}><Badges items={(Array.isArray(v) ? v : [v]) as Chip[]} /></td>
  if (kind === 'pill') return <td className={td}><Badge chip={typeof v === 'string' ? { text: v } : (v as Chip)} /></td>
  if (kind === 'link') {
    const o = v as { href?: string; text?: string } | string
    const h = safeHref(typeof o === 'string' ? o : o.href)
    const label = typeof o === 'string' ? '열기' : o.text || '열기'
    return <td className={cn(td, 'whitespace-nowrap')}>{h ? <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{label}<ArrowUpRight className="size-3" /></a> : '–'}</td>
  }
  const cls = kind === 'mono' ? 'whitespace-nowrap font-mono text-xs text-zinc-800' : kind === 'wide' ? 'min-w-64 max-w-md whitespace-pre-line text-zinc-800' :
    kind === 'mid' ? 'min-w-40 max-w-64 text-zinc-700' : kind === 'num' ? 'whitespace-nowrap text-right font-mono tabular-nums text-zinc-950' :
    String(v).length <= 12 ? 'whitespace-nowrap text-zinc-700' : 'min-w-28 text-zinc-700'
  return <td className={cn(td, cls)}>{typeof v === 'number' ? fmt(v) : <Md text={String(v)} />}</td>
}

function Table({ b }: { b: Block }) {
  const { cols, shown, filters, q, setQ, f, setF } = useTableRows(b)
  return (
    <div className="min-w-0">
      {(b.title || b.search || b.filter) && (
        <div className="mb-5 flex flex-col gap-4">
          {b.title && <div className="text-lg font-semibold tracking-tight text-zinc-950">{b.title}</div>}
          {(b.search || b.filter) && (
            <div className="flex flex-wrap items-center gap-2">
              {b.search && (
                <label className="relative mr-2 min-w-52 flex-1">
                  <Search className="absolute left-0 top-3 size-4 text-zinc-400" aria-hidden />
                  <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={b.search_placeholder || '검색'} aria-label="표 검색"
                    className="h-10 w-full border-b border-zinc-300 bg-transparent pl-7 text-[15px] outline-none placeholder:text-zinc-400 focus:border-zinc-900" />
                </label>
              )}
              {b.filter && ['', ...filters].map((v) => (
                <button key={v || 'all'} type="button" onClick={() => setF(v)} aria-pressed={f === v}
                  className={cn('h-8 rounded-full border px-3 text-xs', f === v ? 'border-zinc-900 bg-zinc-900 font-medium text-white' : 'text-zinc-600 hover:bg-zinc-50')}>
                  {v || '전체'}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="overflow-x-auto border-t border-zinc-900">
        <table className="w-full text-sm">
          <thead><tr className="border-b">{cols.map((c) => <th key={c.key} className="h-11 whitespace-nowrap px-3 text-left align-middle text-[11px] font-medium tracking-widest text-muted-foreground first:pl-0">{c.label}</th>)}</tr></thead>
          <tbody>{shown.map((r, i) => <tr key={i} className="border-b border-zinc-100 transition-colors hover:bg-zinc-50">{cols.map((c) => <Cell key={c.key} kind={c.kind} v={r[c.key]} />)}</tr>)}</tbody>
        </table>
      </div>
      {b.count !== false && <p className="mt-3 font-mono text-xs text-muted-foreground">{fmt(shown.length)}건</p>}
      <Source text={b.source} />
    </div>
  )
}

function Clamp({ text, lines = 3, quote }: { text: string; lines?: 3 | 5; quote?: boolean }) {
  const [open, setOpen] = useState(false)
  const long = text.length > lines * 50
  return (
    <div>
      <p className={cn('whitespace-pre-line', !open && long && (lines === 3 ? 'line-clamp-3' : 'line-clamp-5'))}>{quote ? <>“{text}”</> : <Md text={text} />}</p>
      {long && <button type="button" onClick={() => setOpen(!open)} className="mt-2 text-xs font-medium text-blue-700 hover:underline">{open ? '접기' : '더 보기'}</button>}
    </div>
  )
}

function Quotes({ b }: { b: Block }) {
  return (
    <div>
      {b.title && <div className="mb-3 flex items-center gap-2 text-lg font-semibold tracking-tight text-zinc-950">{b.chip && <span className={cn('size-2 rounded-full', TONE_DOT[tone(b.chip.tone)])} />}{b.title}</div>}
      <div className="flex flex-col">
        {(b.items || []).map((q: Block, i: number) => {
          const h = safeHref(q.href)
          return (
            <figure key={i} className="grid gap-x-6 gap-y-3 border-t py-7 md:grid-cols-[2rem_minmax(0,1fr)]">
              <Quote className="size-5 text-zinc-300" aria-hidden />
              <div className="min-w-0">
                <blockquote className="text-lg leading-relaxed text-zinc-800"><Clamp text={q.quote || ''} quote /></blockquote>
                <figcaption className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badges items={q.chips} />
                  {q.meta && <span>{q.meta}</span>}
                  {h && <a className="inline-flex items-center gap-1 text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">원문 페이지<ArrowUpRight className="size-3" /></a>}
                </figcaption>
              </div>
            </figure>
          )
        })}
      </div>
    </div>
  )
}

// Pain → feature → remaining → proposal columns, as the builder grouped them. No lines are drawn here.
function Chain({ b }: { b: Block }) {
  const cols: Block[] = b.columns || []
  return (
    <div>
      <div className="grid gap-x-8 gap-y-12 @3xl:grid-cols-2 @5xl:grid-flow-col @5xl:auto-cols-fr @5xl:grid-cols-none">
        {cols.map((c, i) => (
          <div key={i} className="flex min-w-0 flex-col">
            <div className="flex items-center gap-3 border-b border-zinc-900 pb-3 text-xs tracking-[0.12em] text-muted-foreground">
              <span className="font-mono font-semibold text-zinc-950">{pad(i + 1)}</span>{c.title}
              {i < cols.length - 1 && <ArrowRight className="ml-auto hidden size-4 text-zinc-300 @5xl:block" aria-hidden />}
            </div>
            {(c.nodes || []).map((n: Block, k: number) => (
              <div key={k} className="flex flex-col gap-3 border-b py-5">
                {n.id && <div className={cn('font-mono text-sm font-medium', TONE_TEXT[tone(n.tone)])}>{n.id}{n.title ? <span className="ml-2 font-sans text-zinc-800">{n.title}</span> : null}</div>}
                {n.text && <div className="text-[15px] leading-relaxed text-zinc-700"><Clamp text={n.text} lines={5} /></div>}
                <Badges items={n.tags} />
              </div>
            ))}
            {!(c.nodes || []).length && <p className="border-b py-5 text-sm text-zinc-400">항목 없음</p>}
          </div>
        ))}
      </div>
      <Source text={b.source} />
    </div>
  )
}

function Expander({ b, copy }: { b: Block; copy: CopyFn }) {
  return (
    <details className="group border-y [details+&]:-mt-6 [details+&]:border-t-0" open={!!b.open}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-lg font-semibold text-zinc-900 hover:text-zinc-600 [&::-webkit-details-marker]:hidden">
        <span>{b.title}</span>
        <Plus className="size-5 shrink-0 text-zinc-400 transition-transform group-open:rotate-45" aria-hidden />
      </summary>
      <div className="flex flex-col gap-6 pb-8 pt-2"><ExBlocks blocks={b.blocks || []} copy={copy} /></div>
    </details>
  )
}

function Files({ b, copy }: { b: Block; copy: CopyFn }) {
  const h = safeHref(b.href)
  return (
    <div className="flex flex-col gap-3">
      <div className="border-t">
        {(b.items || []).map((f: Block, i: number) => (
          <div key={i} className="grid grid-cols-[8rem_minmax(0,1fr)_auto] items-center gap-4 border-b border-zinc-100 py-3 max-sm:grid-cols-[minmax(0,1fr)_auto]">
            <span className="text-xs text-muted-foreground max-sm:col-span-2">{f.label}</span>
            <span className="break-all font-mono text-xs text-zinc-800">{f.value}</span>
            {f.copy !== false ? <Button variant="outline" size="sm" onClick={() => copy(String(f.value))}><Copy className="size-3.5" aria-hidden />복사</Button> : <span />}
          </div>
        ))}
      </div>
      {h && <a className="inline-flex items-center gap-1 text-sm text-blue-700 hover:underline" href={h} target="_blank" rel="noopener noreferrer">{b.href_label || '파일 열기'}<ArrowUpRight className="size-3.5" aria-hidden /></a>}
    </div>
  )
}

function Hero({ b }: { b: Block }) {
  return (
    <section className="flex flex-col items-start pb-6 pt-4">
      <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">{b.eyebrow}</div>
      <h1 className="mt-6 max-w-5xl text-balance text-5xl font-extrabold leading-[1.1] tracking-tight text-zinc-950 sm:text-7xl">{b.title}</h1>
      {b.subtitle && <p className="mt-6 max-w-3xl text-lg leading-relaxed text-zinc-600"><Md text={b.subtitle} /></p>}
      <Badges items={b.chips} className="mt-8" />
      {b.stats?.length > 0 && (
        <dl className="mt-12 grid grid-cols-2 gap-x-14 gap-y-6 sm:grid-cols-4">
          {b.stats.map((st: Block, i: number) => (
            <div key={i}>
              <dt className="text-xs uppercase tracking-widest text-muted-foreground">{st.label}</dt>
              <dd className="mt-1 font-mono text-5xl font-semibold tabular-nums text-zinc-950">{fmt(st.value)}<span className="ml-1 text-base text-muted-foreground">{st.unit}</span></dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

function StorySection({ b, copy }: { b: Block; copy: CopyFn }) {
  return (
    <section className="mt-16 flex flex-col gap-4">
      <div className={cn('text-xs uppercase tracking-[0.3em]', TONE_TEXT[tone(b.tone)])}>{b.label}</div>
      <h2 className="max-w-4xl text-balance text-4xl font-extrabold leading-tight tracking-tight text-zinc-950 sm:text-5xl">{b.title}</h2>
      {b.text && <p className="max-w-3xl text-[15px] leading-relaxed text-zinc-600"><Md text={b.text} /></p>}
      <div className="mt-8 flex flex-col gap-6"><ExBlocks blocks={b.blocks || []} copy={copy} /></div>
    </section>
  )
}

function Claims({ b }: { b: Block }) {
  const t = tone(b.tone)
  return (
    <div className="grid gap-x-12 gap-y-10 @3xl:grid-cols-2">
      {(b.items || []).map((it: Block, i: number) => (
        <div key={i} className="border-t pt-5">
          <div className="flex items-baseline gap-3 font-mono text-sm"><span className={TONE_TEXT[t]}>{it.id}</span>{b.kind_label && <span className="font-sans text-xs text-muted-foreground">{b.kind_label}</span>}</div>
          <p className="mt-2 text-lg leading-relaxed text-zinc-800"><Md text={it.text} /></p>
          {(it.quotes || []).map((q: Block, k: number) => <QuoteLine key={k} q={q} />)}
          <Badges items={it.chips} className="mt-4" />
        </div>
      ))}
    </div>
  )
}

// The builder's flow block as columns; each item lists its recorded outgoing links as text (no drawn lines).
function FlowColumns({ b }: { b: Block }) {
  const cols: Block[] = b.columns || []
  const nodes: Block[] = b.nodes || []
  const links: Block[] = b.links || []
  return (
    <div>
      <div className="grid gap-x-10 gap-y-10 @3xl:grid-flow-col @3xl:auto-cols-fr">
        {cols.map((c) => (
          <div key={c.key} className="flex min-w-0 flex-col">
            <div className={cn('border-b border-zinc-900 pb-3 text-xs tracking-[0.12em]', TONE_TEXT[tone(c.tone)])}>{c.title}</div>
            {nodes.filter((n) => n.column === c.key).map((n) => (
              <div key={n.id} className="border-b py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn('font-mono text-sm', TONE_TEXT[tone(n.tone)])}>{n.id}</span>
                  {links.filter((l) => l.from === n.id).map((l, k) => <Badge key={k} chip={{ text: `→ ${l.to}${l.label ? ' · ' + l.label : ''}`, tone: l.tone || 'gray' }} />)}
                </div>
                {n.text && <p className="mt-2 line-clamp-4 text-[15px] leading-relaxed text-zinc-700"><Md text={n.text} /></p>}
              </div>
            ))}
            {!nodes.some((n) => n.column === c.key) && <p className="border-b py-4 text-sm text-zinc-400">항목 없음</p>}
          </div>
        ))}
      </div>
      {b.note && <p className="mt-4 text-xs text-muted-foreground"><Md text={b.note} /></p>}
    </div>
  )
}
