// C: one 1920x1080 screen (bento grid) with a connection map in the middle. Click a card or a map node for details.
// Everything comes from the story page; map lines are only the links build_view.py passed (review record).
import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ExternalLink, Quote, X } from 'lucide-react'
import { Alert, Badge, Badges } from '../components/ui'
import { DotPattern, StatValue } from '../components/magic'
import { Blocks } from '../components/blocks'
import { ModeSwitch, Stage, type Mode } from '../components/mode'
import { inner, type Story } from '../lib/story'
import { cn, Md, safeHref, tone, TONE_DOT, TONE_HEX, TONE_SOFT, TONE_TEXT } from '../lib/utils'
import type { Block, View } from '../types'

type Detail = { kind: string; tone: string; item: Block }

export default function Poster({ view, story, mode, setMode, copy }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void; copy: (s: string) => void }) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [wide, setWide] = useState(() => window.innerWidth >= 900)
  useLayoutEffect(() => {
    const on = () => setWide(window.innerWidth >= 900)
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [])
  const s = story.sections
  const hero: Block = story.hero || { type: 'hero' }
  const pains: Block[] = inner(s.problem, 'claims')?.items || []
  const features: Block[] = inner(s.check, 'claims')?.items || []
  const flow = inner(s.flow, 'flow')
  const sols: Block[] = inner(s.solution, 'solutions')?.items || []
  const tiles: Block[] = inner(s.trust, 'tiles')?.items || []
  const notes = inner(s.trust, 'chips')
  const nodeText = useMemo(() => Object.fromEntries((flow?.nodes || []).map((n: Block) => [n.id, n])), [flow])

  const switcher = <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />
  if (!story.complete || !wide) {
    // No saved result, or a phone-sized screen: the poster cannot be one screen, so show the story stacked.
    const page = view.pages.find((p) => p.id === 'story')
    return (
      <div className="min-h-dvh bg-background">
        {switcher}
        <main className="@container mx-auto flex max-w-3xl flex-col gap-5 px-4 py-16">
          {wide ? null : <Alert tone="info">C안(한 장 요약)은 큰 화면용입니다. 좁은 화면에서는 같은 내용을 세로로 보여줍니다.</Alert>}
          <Blocks blocks={page?.blocks || []} copy={copy} />
        </main>
      </div>
    )
  }

  const open = (kind: string, t: string, item: Block) => setDetail({ kind, tone: t, item })
  const solById = Object.fromEntries(sols.map((c) => [c.id, c]))
  const painById = Object.fromEntries(pains.map((p) => [p.id, p]))
  return (
    <>
      {switcher}
      <Stage>
        <div className="grid h-full grid-cols-[560px_1fr_560px] grid-rows-[250px_1fr_210px] gap-5 p-9"
          style={{ gridTemplateAreas: '"hero hero stats" "pains map concepts" "trust trust limits"' }}>
          {/* hero */}
          <Cell area="hero" className="relative flex flex-col justify-center overflow-hidden bg-gradient-to-br from-zinc-50 to-white px-10">
            <DotPattern className="[mask-image:radial-gradient(70%_80%_at_0%_0%,black,transparent)]" />
            <div className="relative flex items-center gap-2 text-base text-muted-foreground"><span className="size-2 rounded-full bg-emerald-500" />{hero.eyebrow}</div>
            <h1 className="relative mt-3 line-clamp-2 text-balance text-[44px] font-bold leading-[1.2] tracking-tight">{hero.title}</h1>
            <Badges items={hero.chips} className="relative mt-4 [&>span]:text-sm" />
          </Cell>
          {/* stats */}
          <Cell area="stats" className="grid grid-cols-2 gap-px overflow-hidden bg-border p-0">
            {(hero.stats || []).map((st: Block, i: number) => (
              <div key={i} className="flex flex-col justify-center bg-white px-7">
                <div className="flex items-center gap-2 text-sm text-muted-foreground"><span className={cn('size-2 rounded-full', TONE_DOT[tone(st.tone)])} />{st.label}</div>
                <div className="mt-1 text-5xl font-bold tracking-tight"><StatValue value={st.value} /><span className="ml-1 text-xl font-medium text-muted-foreground">{st.unit}</span></div>
              </div>
            ))}
          </Cell>
          {/* pains */}
          <Cell area="pains" title="현재 불편" tone="red" count={pains.length}>
            <List items={pains} tone="red" max={5} onOpen={(p) => open('현재 불편', 'red', p)} meta={(p) => `원문 ${(p.quotes || []).length}건 보기`} />
          </Cell>
          {/* map */}
          <Cell area="map" title="불편 → 남은 불편 → 제안 연결" tone="orange" note="검토 기록에 적힌 연결만 그림">
            {flow && <MapView flow={flow} onOpen={(id, col) => {
              if (col === 'pain' && painById[id]) open('현재 불편', 'red', painById[id])
              else if (col === 'concept' && solById[id]) open('제안', 'purple', solById[id])
              else if (nodeText[id]) open('남은 불편', 'orange', nodeText[id])
            }} />}
          </Cell>
          {/* concepts */}
          <Cell area="concepts" title="제안" tone="purple" count={sols.length}>
            <List items={sols} tone="purple" max={4} onOpen={(c) => open('제안', 'purple', c)} meta={(c) => [c.plan ? `검증 계획 ${c.plan.status}` : '검증 계획 미작성', ...(c.chips || []).slice(0, 1).map((x: Block) => x.text)].join(' · ')} />
          </Cell>
          {/* trust */}
          <Cell area="trust" className="grid grid-flow-col auto-cols-fr gap-3 bg-transparent p-0 shadow-none ring-0">
            {tiles.map((t, i) => (
              <div key={i} className="flex flex-col justify-center rounded-2xl bg-white px-5 ring-1 ring-zinc-200">
                <div className="text-sm text-muted-foreground">{t.label}</div>
                <div className={cn('mt-1 text-4xl font-bold tracking-tight', TONE_TEXT[tone(t.tone)])}><StatValue value={t.value} />{t.unit && <span className="ml-0.5 text-lg font-medium text-muted-foreground">{t.unit}</span>}</div>
                {t.note && <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{t.note}</div>}
              </div>
            ))}
          </Cell>
          {/* limits */}
          <Cell area="limits" title="한계" tone="gray" className="bg-amber-50/60 ring-amber-200">
            <p className="text-[15px] leading-relaxed text-amber-950">검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정이며, 검토 기록은 모델이 쓰고 저장 도구는 형식만 검사했습니다.</p>
            {notes && <Badges items={notes.items} className="mt-3" />}
            {features.length > 0 && (
              <button type="button" onClick={() => open('기존 기능', 'blue', { type: 'claim', id: `기존 기능 ${features.length}개`, text: features.map((f) => `${f.id}: ${f.text}`).join('\n'), quotes: features.flatMap((f) => (f.quotes || []).slice(0, 1)) })}
                className="mt-3 text-sm font-medium text-blue-700 hover:underline">대조한 기존 기능 {features.length}개 보기</button>
            )}
          </Cell>
        </div>
      </Stage>
      {story.status.length > 0 && (
        <div className="no-print fixed bottom-4 left-4 z-40 max-w-xl">{story.status.slice(0, 1).map((b, i) => <Alert key={i} tone={b.tone}><Md text={b.text} /></Alert>)}</div>
      )}
      {detail && <DetailDialog d={detail} close={() => setDetail(null)} />}
    </>
  )
}

function Cell({ area, title, tone: t, count, note, className, children }: {
  area: string; title?: string; tone?: string; count?: number; note?: string; className?: string; children?: ReactNode
}) {
  return (
    <section style={{ gridArea: area }} className={cn('min-h-0 min-w-0 rounded-2xl bg-white p-6 shadow-xs ring-1 ring-zinc-200', className)}>
      {title && (
        <div className="mb-4 flex items-center gap-2">
          <span className={cn('size-2.5 rounded-full', TONE_DOT[tone(t)])} />
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          {count != null && <span className={cn('rounded-md px-1.5 text-sm font-semibold ring-1 ring-inset', TONE_SOFT[tone(t)])}>{count}</span>}
          {note && <span className="ml-auto text-xs text-muted-foreground">{note}</span>}
        </div>
      )}
      {children}
    </section>
  )
}

function List({ items, tone: t, max, onOpen, meta }: { items: Block[]; tone: string; max: number; onOpen: (b: Block) => void; meta: (b: Block) => string }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {items.slice(0, max).map((it, i) => (
        <li key={i}>
          <button type="button" onClick={() => onOpen(it)}
            className="group w-full rounded-xl p-3 text-left ring-1 ring-zinc-200 transition-shadow hover:shadow-md hover:ring-zinc-300">
            <div className="flex items-center gap-2"><Badge chip={{ text: it.id, tone: t }} /><span className="ml-auto text-xs text-muted-foreground group-hover:text-foreground">{meta(it)}</span></div>
            <p className="mt-1.5 line-clamp-2 text-[15px] leading-snug"><Md text={it.text} /></p>
          </button>
        </li>
      ))}
      {items.length > max && <li className="px-1 text-sm text-muted-foreground">외 {items.length - max}개 · A 앱 보기에서 전체 보기</li>}
    </ul>
  )
}

// Connection map: three fixed columns of nodes and animated beams for recorded links only.
function MapView({ flow, onOpen }: { flow: Block; onOpen: (id: string, column: string) => void }) {
  const cols: Block[] = flow.columns || []
  const nodes: Block[] = flow.nodes || []
  const links: Block[] = useMemo(() => flow.links || [], [flow.links])
  const box = useRef<HTMLDivElement>(null)
  const refs = useRef(new Map<string, HTMLButtonElement>())
  const [paths, setPaths] = useState<{ d: string; color: string; label: string; mx: number; my: number; from: string; to: string }[]>([])
  const [hover, setHover] = useState<string | null>(null)
  const measure = useCallback(() => {
    const root = box.current
    if (!root) return
    const rb = root.getBoundingClientRect()
    const k = root.offsetWidth ? rb.width / root.offsetWidth : 1
    setPaths(links.flatMap((l) => {
      const a = refs.current.get(l.from)?.getBoundingClientRect()
      const z = refs.current.get(l.to)?.getBoundingClientRect()
      if (!a || !z) return []
      const x1 = (a.right - rb.left) / k, y1 = (a.top + a.height / 2 - rb.top) / k
      const x2 = (z.left - rb.left) / k, y2 = (z.top + z.height / 2 - rb.top) / k
      const mx = (x1 + x2) / 2
      return [{ d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`, color: TONE_HEX[tone(l.tone || 'gray')], label: l.label || '', mx, my: (y1 + y2) / 2, from: l.from, to: l.to }]
    }))
  }, [links])
  useLayoutEffect(() => {
    measure()
    const ro = new ResizeObserver(() => measure())
    if (box.current) ro.observe(box.current)
    return () => ro.disconnect()
  }, [measure])
  const linked = (id: string) => links.some((l) => l.from === id || l.to === id)
  return (
    <div className="flex h-[calc(100%-2.75rem)] flex-col gap-3">
    <div className="grid grid-cols-3 gap-28">
      {cols.map((c) => <div key={c.key} className={cn('text-sm font-semibold', TONE_TEXT[tone(c.tone)])}>{c.title}</div>)}
    </div>
    <div ref={box} className="relative grid min-h-0 flex-1 grid-cols-3 gap-28">
      <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" aria-hidden>
        {paths.map((p, i) => (
          <g key={i} opacity={hover && p.from !== hover && p.to !== hover ? 0.2 : 1}>
            <path d={p.d} fill="none" stroke={p.color} strokeOpacity={0.45} strokeWidth={3} />
            <path d={p.d} fill="none" stroke={p.color} strokeWidth={3} strokeLinecap="round" className="lgax-beam" />
            {p.label && (
              <g transform={`translate(${p.mx},${p.my})`}>
                <rect x={-30} y={-12} width={60} height={24} rx={12} fill="#fff" stroke={p.color} strokeOpacity={0.5} />
                <text textAnchor="middle" dy={5} fontSize={13} fontWeight={600} fill={p.color}>{p.label}</text>
              </g>
            )}
          </g>
        ))}
      </svg>
      {cols.map((c) => (
        <div key={c.key} className="relative flex min-w-0 flex-col justify-center gap-3">
          {nodes.filter((n) => n.column === c.key).map((n) => (
            <button key={n.id} type="button" ref={(el) => { if (el) refs.current.set(n.id, el); else refs.current.delete(n.id) }}
              onClick={() => onOpen(n.id, c.key)} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
              className={cn('relative z-10 rounded-xl bg-white p-3 text-left shadow-xs ring-1 transition-shadow hover:shadow-md',
                linked(n.id) ? 'ring-zinc-300' : 'ring-zinc-200 opacity-75')}>
              <Badge chip={{ text: n.id, tone: n.tone }} />
              <p className="mt-1.5 line-clamp-2 text-[13px] leading-snug text-muted-foreground"><Md text={n.text} /></p>
            </button>
          ))}
        </div>
      ))}
    </div>
    </div>
  )
}

function DetailDialog({ d, close }: { d: Detail; close: () => void }) {
  const it = d.item
  return (
    <div className="no-print fixed inset-0 z-[60] grid place-items-center bg-black/40 p-6" onClick={close} role="dialog" aria-modal="true" aria-label={`${d.kind} ${it.id}`}>
      <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-7 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          <div>
            <div className={cn('text-xs font-semibold uppercase tracking-widest', TONE_TEXT[tone(d.tone)])}>{d.kind}</div>
            <div className="mt-1 flex flex-wrap items-center gap-2"><Badge chip={{ text: it.id, tone: d.tone }} /><Badges items={it.chips} /></div>
          </div>
          <button type="button" onClick={close} aria-label="닫기" className="ml-auto rounded-md p-1.5 text-muted-foreground hover:bg-zinc-100"><X className="size-5" /></button>
        </div>
        <p className="mt-4 whitespace-pre-line text-lg leading-relaxed"><Md text={it.text} /></p>
        {(it.quotes || []).length > 0 && (
          <div className="mt-5 flex flex-col gap-3">
            {it.quotes.map((q: Block, k: number) => {
              const h = safeHref(q.href)
              return (
                <figure key={k} className="rounded-xl bg-zinc-50 p-4 ring-1 ring-inset ring-zinc-200">
                  <blockquote className="flex gap-2 text-[15px] leading-relaxed"><Quote className="mt-0.5 size-4 shrink-0 text-zinc-300" aria-hidden />{q.quote}</blockquote>
                  <figcaption className="mt-2 flex flex-wrap items-center gap-2 pl-6 text-xs text-muted-foreground">
                    {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} />}{q.site}
                    {h && <a href={h} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-blue-700">원문<ExternalLink className="size-3" /></a>}
                    {q.source_id && <span className="font-mono">{q.source_id}</span>}
                  </figcaption>
                </figure>
              )
            })}
          </div>
        )}
        {it.steps?.length > 0 && (
          <div className="mt-5"><div className="mb-2 text-sm font-semibold text-muted-foreground">구현 단계</div>
            <ol className="flex list-decimal flex-col gap-1 pl-5 text-[15px]">{it.steps.map((x: string, k: number) => <li key={k}><Md text={x} /></li>)}</ol></div>
        )}
        {it.requirements?.length > 0 && (
          <div className="mt-5"><div className="mb-2 text-sm font-semibold text-muted-foreground">요구사항</div>
            <ul className="flex list-disc flex-col gap-1 pl-5 text-[15px]">{it.requirements.map((x: string, k: number) => <li key={k}><Md text={x} /></li>)}</ul></div>
        )}
        {it.plan && (
          <div className="mt-5 rounded-xl border bg-zinc-50 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">검증 계획 <Badge chip={{ text: it.plan.status, tone: 'orange' }} /></div>
            <dl className="grid grid-cols-[5rem_1fr] gap-x-3 gap-y-1.5 text-sm">{it.plan.rows.map((r: Block, k: number) => <div key={k} className="contents"><dt className="text-muted-foreground">{r.k}</dt><dd><Md text={r.v} /></dd></div>)}</dl>
          </div>
        )}
        {it.sources?.length > 0 && <Badges items={it.sources} className="mt-5" />}
      </div>
    </div>
  )
}
