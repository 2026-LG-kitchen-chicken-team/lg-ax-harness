// "한눈에 보기" story blocks (Magic UI-style landing sections). build_view.py decides every item, count and link;
// this file only lays them out. Connector lines in the flow are drawn only for links the builder passes.
import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ArrowRight, ExternalLink, FileText, Quote } from 'lucide-react'
import { Badge, Badges, Card } from './ui'
import { StatValue } from './magic'
import { Blocks } from './blocks'
import { HoverNote, SourceNote } from './hovernote'
import { Lead } from './lead'
import { useIdTip } from './idtip'
import { useSkin } from '../lib/skin'
import { cn, Md, safeHref, tone, TONE_DOT, TONE_HEX, TONE_SOFT, TONE_TEXT } from '../lib/utils'
import type { Block } from '../types'

type P = { b: Block; copy: (s: string) => void }

// Report cover: the question as written, what was saved, and the four counts. Plain type, no decoration.
function Hero({ b }: P) {
  return (
    <section className="rounded-2xl border bg-card px-6 py-8 sm:px-10 sm:py-10">
      <div className="text-[13px] text-muted-foreground">{b.eyebrow}</div>
      <h1 className="mt-3 max-w-4xl text-balance text-[28px] font-bold leading-snug tracking-tight sm:text-[36px]">{b.title}</h1>
      {b.subtitle && <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted-foreground"><Md text={b.subtitle} /></p>}
      <Badges items={b.chips} className="mt-5" />
      {b.stats?.length > 0 && (
        <dl className="mt-8 grid grid-cols-2 border-t pt-6 sm:grid-flow-col sm:auto-cols-fr sm:grid-cols-none sm:divide-x">
          {b.stats.map((s: Block, i: number) => (
            <div key={i} className="py-2 sm:px-6 sm:py-0 sm:first:pl-0">
              <dt className="text-[13px] text-muted-foreground">{s.label}</dt>
              <dd className="mt-1 text-[32px] font-bold leading-none tracking-tight">
                <StatValue value={s.value} />{s.unit && <span className="ml-1 text-base font-medium text-muted-foreground">{s.unit}</span>}
              </dd>
              {s.note && <div className="mt-1 text-xs text-muted-foreground">{s.note}</div>}
            </div>
          ))}
        </dl>
      )}
    </section>
  )
}

// Section order for the "1. 현재 불편" style numbering; the builder's label is "Problem · 현재 불편".
const SECTION_NO: Record<string, number> = { problem: 1, check: 2, flow: 3, solution: 4, trust: 5 }

function StorySection({ b, copy }: P) {
  const no = SECTION_NO[b.key]
  const name = String(b.label || '').split('·').pop()?.trim()
  return (
    <section className="mt-10 flex flex-col gap-5 border-t pt-8 sm:mt-12">
      <div>
        <div className="text-sm font-semibold text-muted-foreground">{no ? `${no}. ` : ''}{name}</div>
        <h2 className="mt-1.5 text-balance text-2xl font-bold tracking-tight sm:text-[28px]">{b.title}</h2>
        {b.text && <p className="mt-2 max-w-3xl text-[15px] leading-relaxed text-muted-foreground"><Md text={b.text} /></p>}
      </div>
      <div className="flex flex-col gap-4"><Blocks blocks={b.blocks || []} copy={copy} /></div>
    </section>
  )
}

export function QuoteLine({ q }: { q: Block }) {
  const h = safeHref(q.href)
  // K: the source ID is a reference code; it shows on the 원문 link's hover (or its own mark when there is no link).
  const ops = useSkin()?.id === 'ops'
  return (
    <figure className="rounded-lg bg-muted/60 px-3 py-2.5">
      <blockquote className="flex gap-2 text-[13px] leading-relaxed">
        <Quote className="mt-0.5 size-3.5 shrink-0 text-zinc-400" aria-hidden />
        <span className="line-clamp-4">{q.quote}</span>
      </blockquote>
      <figcaption className="mt-1.5 flex flex-wrap items-center gap-1.5 pl-5 text-[11px] text-muted-foreground">
        {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} />}
        {q.site && <span>{q.site}</span>}
        {h && <a href={h} target="_blank" rel="noopener noreferrer" title={ops && q.source_id ? q.source_id : undefined} className="inline-flex items-center gap-0.5 text-blue-700 hover:underline">원문<ExternalLink className="size-3" /></a>}
        {q.source_id && (ops ? !h && <HoverNote note={q.source_id} className="text-zinc-400 hover:text-zinc-700">ID</HoverNote> : <span className="font-mono">{q.source_id}</span>)}
      </figcaption>
    </figure>
  )
}

function Claims({ b }: P) {
  const t = tone(b.tone)
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {(b.items || []).map((it: Block, i: number) => (
        <Card key={i} className="flex flex-col gap-3 p-5">
          <div className="flex items-center gap-2">
            <Badge chip={{ text: it.id, tone: t }} />
            {b.kind_label && <span className="text-xs text-muted-foreground">{b.kind_label}</span>}
          </div>
          <p className="text-[15px] font-medium leading-relaxed"><Md text={it.text} /></p>
          {it.quotes?.length > 0 && <div className="flex flex-col gap-2">{it.quotes.map((q: Block, k: number) => <QuoteLine key={k} q={q} />)}</div>}
          <Badges items={it.chips} />
        </Card>
      ))}
    </div>
  )
}

function Matches({ b }: P) {
  const ops = useSkin()?.id === 'ops'
  return (
    <Card className="divide-y">
      {(b.items || []).map((m: Block, i: number) => (
        <div key={i} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:gap-4">
          <div className="flex shrink-0 items-center gap-2">
            <Badge chip={m.from} />
            <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
            <Badge chip={m.to} />
            <Badge chip={{ text: m.label, tone: m.tone }} className="font-semibold" />
          </div>
          {m.text && <p className="text-sm leading-relaxed text-muted-foreground"><Md text={m.text} /></p>}
        </div>
      ))}
      {b.source && (ops ? <div className="flex justify-end px-3 py-1.5"><SourceNote text={b.source} /></div>
        : <p className="px-4 py-2 text-[11px] text-muted-foreground">출처: {b.source}</p>)}
    </Card>
  )
}

// Columns of cards with connector curves between recorded links. The links are also printed inside each card,
// so the meaning does not depend on the drawing (narrow screens hide the curves).
export function Flow({ b, large }: P & { large?: boolean }) {
  // K: each node shows the model's summary (or the first sentence); its ID chip opens the whole text.
  const ops = useSkin()?.id === 'ops'
  const cols: Block[] = b.columns || []
  const nodes: Block[] = b.nodes || []
  const links: Block[] = useMemo(() => b.links || [], [b.links])
  const box = useRef<HTMLDivElement>(null)
  const refs = useRef(new Map<string, HTMLDivElement>())
  const [paths, setPaths] = useState<{ d: string; color: string }[]>([])
  const measure = useCallback(() => {
    const root = box.current
    if (!root) return
    const rb = root.getBoundingClientRect()
    // Inside a scaled slide or poster the measured boxes are scaled; the SVG draws in unscaled CSS pixels.
    const k = root.offsetWidth ? rb.width / root.offsetWidth : 1
    const out: { d: string; color: string }[] = []
    for (const l of links) {
      const a = refs.current.get(l.from)?.getBoundingClientRect()
      const z = refs.current.get(l.to)?.getBoundingClientRect()
      if (!a || !z || z.left <= a.right) continue // stacked layout: no curves
      const x1 = (a.right - rb.left) / k, y1 = (a.top + a.height / 2 - rb.top) / k
      const x2 = (z.left - rb.left) / k, y2 = (z.top + z.height / 2 - rb.top) / k
      const mx = (x1 + x2) / 2
      out.push({ d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, color: TONE_HEX[tone(l.tone || 'gray')] })
    }
    setPaths(out)
  }, [links])
  useLayoutEffect(() => {
    measure()
    const ro = new ResizeObserver(() => measure())
    if (box.current) ro.observe(box.current)
    return () => ro.disconnect()
  }, [measure])
  const outgoing = (id: string) => links.filter((l) => l.from === id)
  return (
    <div>
      <div ref={box} className={cn('relative grid gap-4', large ? 'grid-flow-col auto-cols-fr gap-24' : '@4xl:grid-flow-col @4xl:auto-cols-fr @4xl:gap-14')}>
        <svg className={cn('pointer-events-none absolute inset-0 h-full w-full overflow-visible', large ? 'block' : 'hidden @4xl:block')} aria-hidden>
          {paths.map((p, i) => <path key={i} d={p.d} fill="none" stroke={p.color} strokeOpacity={0.55} strokeWidth={2} />)}
        </svg>
        {cols.map((c) => (
          <div key={c.key} className="relative flex min-w-0 flex-col gap-3">
            <div className={cn('flex items-center gap-2 font-semibold text-muted-foreground', large ? 'text-xl' : 'text-xs')}>
              <span className={cn('rounded-full', large ? 'size-3' : 'size-2', TONE_DOT[tone(c.tone)])} />{c.title}
            </div>
            {nodes.filter((n) => n.column === c.key).map((n) => (
              <div key={n.id} ref={(el) => { if (el) refs.current.set(n.id, el); else refs.current.delete(n.id) }}
                className={cn('relative rounded-xl border bg-card p-3 shadow-xs ring-1 ring-inset ring-transparent')}>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge chip={{ text: n.id, tone: n.tone }} />
                  {outgoing(n.id).map((l, k) => <Badge key={k} chip={{ text: `→ ${l.to}${l.label ? ' · ' + l.label : ''}`, tone: l.tone || 'gray' }} />)}
                </div>
                {n.text && <p className={cn('mt-2 leading-relaxed', large ? 'line-clamp-3 text-xl' : 'line-clamp-4 text-[13px]')}>{ops ? <Lead text={n.text} summary={n.summary} max={60} /> : <Md text={n.text} />}</p>}
              </div>
            ))}
            {!nodes.some((n) => n.column === c.key) && <p className="text-xs text-muted-foreground">항목 없음</p>}
          </div>
        ))}
      </div>
      {b.note && <p className="mt-3 text-xs text-muted-foreground"><Md text={b.note} /></p>}
    </div>
  )
}

// K: a proposal's evidence is shown as "근거 원문 N건"; the IDs and their quotes open on hover.
function SourcesNote({ items }: { items: Block[] }) {
  const tip = useIdTip()
  const ids = items.map((c) => (typeof c === 'string' ? c : c.text))
  return (
    <HoverNote className="inline-flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-900"
      note={<ul className="flex flex-col gap-1.5">{ids.map((id) => <li key={id}><span className="font-mono text-[11px] text-zinc-400">{id}</span>{tip?.lookup(id) && <div className="line-clamp-3">{tip.lookup(id)!.text}</div>}</li>)}</ul>}>
      <FileText className="size-3.5" aria-hidden />근거 원문 {ids.length}건
    </HoverNote>
  )
}

function Solutions({ b }: P) {
  const ops = useSkin()?.id === 'ops'
  return (
    <div className="flex flex-col gap-4">
      {(b.items || []).map((s: Block, i: number) => (
        <Card key={i} className="overflow-hidden">
          <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <div className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-bold">제안 {s.n}</span>
                <Badge chip={{ text: s.id, tone: ops ? 'k4' : 'purple' }} />
                <Badges items={s.chips} />
              </div>
              <p className="text-[15px] leading-relaxed">{ops ? <Lead text={s.text} summary={s.summary} max={120} /> : <Md text={s.text} />}</p>
              {s.links?.length > 0 && <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">연결된 남은 불편 <Badges items={s.links} /></div>}
              {s.requirements?.length > 0 && <MiniList title="요구사항" items={s.requirements} />}
            </div>
            <div className="flex min-w-0 flex-col gap-3">
              {s.steps?.length > 0 ? (
                <div>
                  <div className="mb-2 text-xs font-semibold text-muted-foreground">구현 단계</div>
                  <ol className="flex flex-col gap-2">
                    {s.steps.map((x: string, k: number) => (
                      <li key={k} className="flex gap-2.5 text-[13px] leading-relaxed">
                        <span className="grid size-5 shrink-0 place-items-center rounded-full bg-violet-100 text-[11px] font-semibold text-violet-700">{k + 1}</span>
                        <span><Md text={x} /></span>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : <p className="text-xs text-muted-foreground">구현 단계: <b>미작성</b></p>}
              {s.plan ? (
                <div className="rounded-lg border bg-muted/40 p-3">
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold">검증 계획 <Badge chip={{ text: s.plan.status, tone: 'orange' }} /></div>
                  <dl className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-[13px]">
                    {s.plan.rows.map((r: Block, k: number) => <Row key={k} k={r.k} v={r.v} />)}
                  </dl>
                </div>
              ) : <p className="text-xs text-muted-foreground">검증 계획: <b>미작성</b></p>}
            </div>
          </div>
          {s.sources?.length > 0 && <div className="border-t bg-muted/30 px-6 py-2.5">{ops ? <SourcesNote items={s.sources} /> : <Badges items={s.sources} />}</div>}
        </Card>
      ))}
    </div>
  )
}

const Row = ({ k, v }: { k: string; v: string }) => (<><dt className="text-muted-foreground">{k}</dt><dd className="min-w-0"><Md text={v} /></dd></>)

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-semibold text-muted-foreground">{title}</div>
      <ul className="flex list-disc flex-col gap-1 pl-4 text-[13px] leading-relaxed marker:text-zinc-300">{items.map((x, i) => <li key={i}><Md text={x} /></li>)}</ul>
    </div>
  )
}

function Tiles({ b }: P) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {(b.items || []).map((t: Block, i: number) => (
        <Card key={i} className={cn('flex flex-col gap-1 p-4', t.tone && t.tone !== 'gray' && 'ring-1 ring-inset', t.tone && TONE_SOFT[tone(t.tone)].split(' ').filter((c) => c.startsWith('ring-')).join(' '))}>
          <div className="text-xs font-medium text-muted-foreground">{t.label}</div>
          <div className={cn('text-2xl font-bold tracking-tight', t.tone ? TONE_TEXT[tone(t.tone)] : '')}>
            <StatValue value={t.value} />{t.unit && <span className="ml-0.5 text-sm font-medium text-muted-foreground">{t.unit}</span>}
          </div>
          {t.note && <div className="text-[11px] leading-snug text-muted-foreground">{t.note}</div>}
        </Card>
      ))}
    </div>
  )
}

export const STORY_BLOCKS: Record<string, (p: P) => ReactNode> = {
  hero: Hero, story: StorySection, claims: Claims, matches: Matches, flow: Flow, solutions: Solutions, tiles: Tiles,
}
