// E: warm paper "board" built with pieces adapted from Cult UI (MIT). Four lanes side by side
// (현재 불편 → 기존 기능 → 남은 불편 → 제안); cards open in place; hovering a card lights up the cards it is linked
// to in the review record. A dynamic island carries the status and opens into the limits.
// Like B–D it only re-arranges the story page blocks; links are only those the builder passed.
import { useMemo, useState, type ReactNode } from 'react'
import { ArrowUpRight, Quote } from 'lucide-react'
import { ModeSwitch, type Mode } from '../components/mode'
import { ExpandCard, Island, PaperGrain, TextureCard, TextureSeparator } from '../components/cult'
import { Blocks } from '../components/blocks'
import { inner, notesOf, type Story } from '../lib/story'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, View } from '../types'

type Lane = { key: string; title: string; hint: string; accent: string; dot: string; items: Block[]; notes: Block[] }
const CHIP: Record<string, string> = {
  red: 'bg-rose-100 text-rose-800', orange: 'bg-amber-100 text-amber-900', green: 'bg-emerald-100 text-emerald-800',
  blue: 'bg-sky-100 text-sky-800', purple: 'bg-violet-100 text-violet-800', gray: 'bg-stone-200 text-stone-700',
}
const NOTE: Record<string, string> = {
  info: 'bg-sky-50/90 text-sky-950 ring-sky-300/60', success: 'bg-emerald-50/90 text-emerald-950 ring-emerald-300/60',
  warning: 'bg-amber-50/90 text-amber-950 ring-amber-300/70', error: 'bg-rose-50/90 text-rose-950 ring-rose-300/70',
}
const Note = ({ b }: { b: Block }) => (
  <p role="note" className={cn('rounded-2xl px-4 py-3 text-sm leading-relaxed ring-1', NOTE[b.tone] || NOTE.info)}><Md text={b.text} /></p>
)
const Tag = ({ text, t, title }: { text: string; t?: string; title?: string }) => (
  <span title={title} className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold', CHIP[tone(t)])}>{text}</span>
)

export default function Board({ view, story, mode, setMode, copy }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void; copy: (s: string) => void }) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [hover, setHover] = useState<string | null>(null)
  const [islandOpen, setIslandOpen] = useState(false)
  const s = story.sections
  const hero: Block = story.hero || { type: 'hero' }
  const pains: Block[] = inner(s.problem, 'claims')?.items || []
  const features: Block[] = inner(s.check, 'claims')?.items || []
  const matches: Block[] = inner(s.check, 'matches')?.items || []
  const flow = inner(s.flow, 'flow')
  const remaining: Block[] = (flow?.nodes || []).filter((n: Block) => n.column === 'remaining')
  const sols: Block[] = inner(s.solution, 'solutions')?.items || []
  const tiles: Block[] = inner(s.trust, 'tiles')?.items || []
  const links: Block[] = useMemo(() => flow?.links || [], [flow])
  // Cards linked to the hovered card (both directions, one hop and the next hop along the chain).
  const lit = useMemo(() => {
    if (!hover) return null
    const set = new Set([hover])
    for (let k = 0; k < 2; k++) for (const l of links) { if (set.has(l.from)) set.add(l.to); if (set.has(l.to)) set.add(l.from) }
    return set
  }, [hover, links])

  if (!story.complete) {
    const page = view.pages.find((p) => p.id === 'story')
    return (
      <div className="min-h-dvh bg-background">
        <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />
        <main className="@container mx-auto flex max-w-3xl flex-col gap-5 px-4 py-16"><Blocks blocks={page?.blocks || []} copy={copy} /></main>
      </div>
    )
  }

  const lanes: Lane[] = [
    { key: 'pain', title: '현재 불편', hint: '근거에서 찾은 불편', accent: 'from-rose-200/70', dot: 'bg-rose-500', items: pains, notes: notesOf(s.problem) },
    { key: 'feature', title: '기존 기능', hint: '같은 모델에 이미 있는 것', accent: 'from-sky-200/70', dot: 'bg-sky-500', items: features, notes: notesOf(s.check) },
    { key: 'remaining', title: '남은 불편', hint: '기능이 있어도 남은 것', accent: 'from-amber-200/80', dot: 'bg-amber-500', items: remaining, notes: notesOf(s.flow) },
    { key: 'concept', title: '제안', hint: '남은 불편에 연결한 것', accent: 'from-violet-200/70', dot: 'bg-violet-500', items: sols, notes: notesOf(s.solution) },
  ]
  const out = (id: string) => links.filter((l) => l.from === id)
  const into = (id: string) => links.filter((l) => l.to === id)
  const judgments = (id: string) => matches.filter((m) => m.to?.text === id)
  const semantic = (hero.chips || []).find((c: Block) => /의미 검토/.test(c.text))
  const status = (hero.chips || [])[0]

  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-[#efe9df] text-stone-900">
      <PaperGrain className="fixed" />
      <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />

      <header className="relative mx-auto flex max-w-[1500px] flex-col items-center px-6 pt-8 text-center">
        <Island open={islandOpen} onToggle={() => setIslandOpen((o) => !o)}
          compact={(
            <div className="flex h-full items-center justify-between gap-3 px-5 text-[13px]">
              <span className="flex items-center gap-2"><span className="size-2 animate-pulse rounded-full bg-emerald-400" />{status?.text}</span>
              <span className="text-amber-300">{semantic?.text}</span>
            </div>
          )}
          large={(
            <div className="flex h-full flex-col justify-between p-6">
              <div className="flex items-center justify-between text-xs text-white/50"><span>믿을 수 있는 정도와 한계</span><span>닫기</span></div>
              <div className="grid grid-cols-3 gap-3">
                {tiles.slice(0, 6).map((t, i) => (
                  <div key={i}>
                    <div className="text-[11px] text-white/50">{t.label}</div>
                    <div className="text-2xl font-bold tracking-tight">{fmt(t.value)}<span className="ml-0.5 text-xs font-medium text-white/50">{t.unit}</span></div>
                  </div>
                ))}
              </div>
              <div className="text-[11px] text-white/45">검토 통과는 효과의 증명이 아닙니다. 효과·비용은 측정 전입니다.</div>
            </div>
          )} />
        <div className="mt-8 text-xs font-medium uppercase tracking-[0.25em] text-stone-500">{hero.eyebrow}</div>
        <h1 className="mt-4 max-w-5xl text-balance text-4xl font-extrabold leading-[1.15] tracking-tight text-stone-900 sm:text-[56px]">{hero.title}</h1>
        <div className="mt-6 flex flex-wrap justify-center gap-x-8 gap-y-2 text-sm text-stone-600">
          {(hero.stats || []).map((st: Block, i: number) => (
            <span key={i}><b className="mr-1 text-2xl font-extrabold tabular-nums text-stone-900">{fmt(st.value)}</b>{st.unit} {st.label}</span>
          ))}
        </div>
      </header>

      {/* the story page's warnings (held/invalid result, stopped requests) before the lanes */}
      {story.status.length > 0 && (
        <section className="relative mx-auto mt-10 flex max-w-[1500px] flex-col gap-3 px-6">
          {story.status.map((b, i) => b.type === 'callout' ? <Note key={i} b={b} /> : <Blocks key={i} blocks={[b]} copy={copy} />)}
        </section>
      )}

      <main className="relative mx-auto mt-12 grid max-w-[1500px] gap-5 px-6 pb-10 md:grid-cols-2 xl:grid-cols-4">
        {lanes.map((lane) => (
          <TextureCard key={lane.key} className="min-w-0">
            <div className={cn('rounded-t-[20px] bg-gradient-to-b to-transparent px-5 pb-3 pt-5', lane.accent)}>
              <div className="flex items-center gap-2">
                <span className={cn('size-2.5 rounded-full', lane.dot)} />
                <h2 className="text-lg font-bold tracking-tight">{lane.title}</h2>
                <span className="ml-auto rounded-full bg-white/80 px-2.5 py-0.5 text-sm font-bold tabular-nums ring-1 ring-stone-900/10">{lane.items.length}</span>
              </div>
              <div className="mt-1 text-xs text-stone-500">{lane.hint}</div>
            </div>
            <TextureSeparator />
            <div className="flex flex-col gap-3 p-3">
              {lane.notes.map((b, i) => <Note key={'n' + i} b={b} />)}
              {lane.items.map((it) => {
                const id = it.id as string
                const dim = lit && !lit.has(id)
                return (
                  <ExpandCard key={id} open={openId === id} onToggle={() => setOpenId(openId === id ? null : id)}
                    onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(null)}
                    className={cn('transition-[opacity,transform] duration-200', dim && 'opacity-35', lit?.has(id) && hover !== id && 'ring-2 ring-amber-400')}
                    head={(
                      <>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-mono text-xs font-bold text-stone-500">{id}</span>
                          {out(id).map((l, k) => <Tag key={'o' + k} text={`→ ${l.to}${l.label ? ' · ' + l.label : ''}`} t={l.tone} />)}
                          {lane.key === 'concept' && into(id).map((l, k) => <Tag key={'i' + k} text={`← ${l.from}`} t="orange" />)}
                          {lane.key === 'pain' && out(id).length === 0 && <Tag text="연결 기록 없음" t="gray" />}
                        </div>
                        <p className={cn('mt-2 text-[14px] leading-relaxed text-stone-800', openId !== id && 'line-clamp-3')}><Md text={it.text} /></p>
                      </>
                    )}>
                    <CardBody lane={lane.key} it={it} judgments={judgments(id)} />
                  </ExpandCard>
                )
              })}
              {!lane.items.length && <p className="px-2 py-6 text-center text-sm text-stone-400">항목 없음</p>}
            </div>
          </TextureCard>
        ))}
      </main>

      <footer className="relative mx-auto flex max-w-[1500px] flex-col gap-2 px-6 pb-14 text-xs text-stone-500">
        <p>카드에 마우스를 올리면 검토 기록에 적힌 연결만 밝아집니다. 누르면 그 자리에서 원문·판단·검증 계획이 펼쳐집니다. 위쪽 검은 바를 누르면 한계가 열립니다.</p>
        <p>{view.context?.meta} · 화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다. Components adapted from <a className="underline" href="https://www.cult-ui.com" target="_blank" rel="noopener noreferrer">Cult UI</a> (MIT).</p>
      </footer>
    </div>
  )
}

function CardBody({ lane, it, judgments }: { lane: string; it: Block; judgments: Block[] }): ReactNode {
  return (
    <div className="flex flex-col gap-3 border-t border-dashed border-stone-300 pt-3 text-[13px]">
      {(it.quotes || []).map((q: Block, k: number) => <QuoteLine key={k} q={q} />)}
      {lane === 'remaining' && judgments.map((m, k) => (
        <div key={k} className="rounded-xl bg-amber-50 p-3 ring-1 ring-amber-200">
          <div className="flex items-center gap-2 text-xs font-semibold"><span>{m.from?.text} → {m.to?.text}</span><Tag text={m.label} t={m.tone} /></div>
          <p className="mt-1.5 leading-relaxed text-stone-700"><Md text={m.text} /></p>
        </div>
      ))}
      {lane === 'remaining' && !judgments.length && <p className="text-stone-500">검토 기록에 이 남은 불편의 대조 판단이 없습니다.</p>}
      {lane === 'concept' && (
        <>
          <div className="flex flex-wrap gap-1.5">{(it.chips || []).map((c: Block, k: number) => <Tag key={k} text={c.text} t={c.tone} />)}</div>
          {it.steps?.length > 0 && (
            <ol className="flex flex-col gap-1">
              {it.steps.map((x: string, k: number) => <li key={k} className="flex gap-2 text-stone-700"><span className="font-mono text-stone-400">{k + 1}</span><span><Md text={x} /></span></li>)}
            </ol>
          )}
          {it.plan && (
            <dl className="grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1 rounded-xl bg-stone-100 p-3">
              <dt className="text-stone-500">검증</dt><dd><Tag text={it.plan.status} t="orange" /></dd>
              {it.plan.rows.filter((r: Block) => r.k === '지표' || r.k === '성공 기준').map((r: Block, k: number) => (
                <div key={k} className="contents"><dt className="text-stone-500">{r.k}</dt><dd className="text-stone-700"><Md text={r.v} /></dd></div>
              ))}
            </dl>
          )}
        </>
      )}
      {(it.chips || []).length > 0 && lane !== 'concept' && <div className="text-[11px] text-stone-500">{it.chips.map((c: Block) => c.text).join(' · ')}</div>}
    </div>
  )
}

function QuoteLine({ q }: { q: Block }) {
  const h = safeHref(q.href)
  return (
    <figure className="rounded-xl bg-stone-50 p-3 ring-1 ring-stone-200">
      <blockquote className="flex gap-2 leading-relaxed text-stone-700"><Quote className="mt-0.5 size-3.5 shrink-0 text-stone-300" aria-hidden /><span className="line-clamp-5">{q.quote}</span></blockquote>
      <figcaption className="mt-1.5 flex flex-wrap items-center gap-2 pl-5 text-[11px] text-stone-500">
        {q.type}{q.site && <span>· {q.site}</span>}
        {h && <a href={h} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-0.5 underline">원문<ArrowUpRight className="size-3" /></a>}
      </figcaption>
    </figure>
  )
}
