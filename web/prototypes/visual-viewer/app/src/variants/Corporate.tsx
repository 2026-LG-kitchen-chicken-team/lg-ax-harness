// G: Korean corporate-site look (reference: a tech company site the user picked). A dark navy hero with a drawn
// network globe, then white sections with red eyebrows, rounded card carousels, a red band, a tinted panel and a
// dark closing banner. Like B–F it only re-arranges the story page blocks; chains use only recorded links.
// No images or assets from the reference are used; the globe is drawn here.
import { useId, useRef, useState, type ReactNode } from 'react'
import { ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight, Ellipsis, MessageSquareWarning } from 'lucide-react'
import { Badge, Badges } from '../components/ui'
import { Blocks } from '../components/blocks'
import { ModeSwitch, type Mode } from '../components/mode'
import { chainsOf, inner, notesOf, type Story } from '../lib/story'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, View } from '../types'

const RED = 'text-[#e8463d]'
const NODE: Record<string, string> = {
  red: 'bg-rose-50 text-rose-700 ring-rose-200', orange: 'bg-amber-50 text-amber-800 ring-amber-200',
  purple: 'bg-violet-50 text-violet-700 ring-violet-200', blue: 'bg-blue-50 text-blue-700 ring-blue-200', gray: 'bg-zinc-100 text-zinc-600 ring-zinc-200',
}
const ON_DARK: Record<string, string> = {
  red: 'text-rose-300', orange: 'text-amber-300', green: 'text-emerald-300', blue: 'text-sky-300', purple: 'text-violet-300', gray: 'text-zinc-300',
}
const pad = (n: number) => String(n).padStart(2, '0')
const Node = ({ id, t, title }: { id: string; t: string; title?: string }) => (
  <span title={title} className={cn('inline-flex items-center rounded-full px-3 py-1 font-mono text-sm font-semibold ring-1 ring-inset', NODE[t])}>{id}</span>
)

export default function Corporate({ view, story, mode, setMode, copy }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void; copy: (s: string) => void }) {
  if (!story.complete) {
    const page = view.pages.find((p) => p.id === 'story')
    return (
      <div className="min-h-dvh bg-background">
        <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />
        <main className="@container mx-auto flex max-w-3xl flex-col gap-5 px-4 py-16"><Blocks blocks={page?.blocks || []} copy={copy} /></main>
      </div>
    )
  }
  const s = story.sections
  const hero: Block = story.hero || { type: 'hero' }
  const pains: Block[] = inner(s.problem, 'claims')?.items || []
  const features: Block[] = inner(s.check, 'claims')?.items || []
  const matches: Block[] = inner(s.check, 'matches')?.items || []
  const flow = inner(s.flow, 'flow')
  const { chains, orphanRemaining, orphanConcepts } = chainsOf(flow)
  const sols: Block[] = inner(s.solution, 'solutions')?.items || []
  const tiles: Block[] = inner(s.trust, 'tiles')?.items || []
  const notes = inner(s.trust, 'chips')
  const nav = [['g-problem', '현재 불편'], ['g-check', '기존 기능 대조'], ['g-flow', '연결'], ['g-solution', '제안'], ['g-limits', '한계']]
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <div className="min-h-dvh bg-white text-zinc-900">
      <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />

      {/* hero */}
      <section className="relative isolate overflow-hidden bg-[#07112a] text-white">
        <NetworkGlobe />
        <header className="relative mx-auto flex max-w-7xl items-center gap-10 px-6 py-6 lg:px-10">
          <span className="text-lg font-extrabold tracking-tight">LG AX</span>
          <nav className="hidden items-center gap-8 text-sm text-white/75 lg:flex">
            {nav.map(([id, label]) => <button key={id} type="button" onClick={() => jump(id)} className="hover:text-white">{label}</button>)}
          </nav>
        </header>
        <div className="relative mx-auto flex min-h-[78vh] max-w-7xl flex-col justify-center px-6 pb-20 pt-10 lg:px-10">
          <div className={cn('text-sm font-semibold', 'text-[#ff6a60]')}>Question</div>
          <div className="mt-2 text-sm text-white/60">{hero.eyebrow}</div>
          <h1 className="mt-6 max-w-4xl text-balance text-4xl font-bold leading-[1.18] tracking-tight sm:text-6xl">{hero.title}</h1>
          {hero.subtitle && <p className="mt-6 max-w-2xl text-[17px] leading-relaxed text-white/70"><Md text={hero.subtitle} /></p>}
          <Badges items={hero.chips} className="mt-7" />
          <button type="button" onClick={() => jump('g-problem')} aria-label="현재 불편으로 이동"
            className="mt-10 grid size-12 place-items-center rounded-full ring-1 ring-white/60 hover:bg-white/10"><Ellipsis className="size-5" /></button>
          <dl className="mt-16 grid max-w-3xl grid-cols-2 gap-y-6 sm:grid-cols-4 sm:divide-x sm:divide-white/15">
            {(hero.stats || []).map((st: Block, i: number) => (
              <div key={i} className="sm:px-6 sm:first:pl-0">
                <dt className="text-xs text-white/55">{st.label}</dt>
                <dd className="mt-1 text-4xl font-bold tabular-nums">{fmt(st.value)}<span className="ml-1 text-base font-medium text-white/55">{st.unit}</span></dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {story.status.length > 0 && (
        <section className="mx-auto mt-14 flex max-w-5xl flex-col gap-3 px-6"><Blocks blocks={story.status} copy={copy} /></section>
      )}

      {/* problem: text on the left, pain cards on the right */}
      <ProblemSection section={s.problem} pains={pains} copy={copy} />

      {/* red band: quick links to the parts of the result */}
      <section className="bg-[#e8463d] text-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-10 lg:flex-row lg:items-center lg:px-10">
          <div>
            <div className="text-2xl font-bold tracking-tight">결과를 빠르게 살펴보세요</div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-white/80">{(hero.chips || []).map((c: Block, i: number) => <span key={i}>{c.text}</span>)}</div>
          </div>
          <nav className="flex flex-wrap gap-1 rounded-full bg-white p-1.5 text-sm text-zinc-700 lg:ml-auto" aria-label="결과 바로가기">
            {nav.map(([id, label]) => <button key={id} type="button" onClick={() => jump(id)} className="rounded-full px-4 py-2 hover:bg-rose-50 hover:text-[#e8463d]">{label}</button>)}
          </nav>
        </div>
      </section>

      {/* check: tinted section, white panel with features and judgments */}
      <section id="g-check" className="scroll-mt-4 bg-[#fdf5f4] py-24">
        <Heading eyebrow="Check" title={s.check?.title} text={s.check?.text} center />
        <div className="mx-auto mt-12 max-w-7xl px-6 lg:px-10">
          <div className="grid overflow-hidden rounded-[2rem] bg-white shadow-[0_30px_60px_-40px_rgba(0,0,0,0.3)] lg:grid-cols-[1fr_26rem]">
            <div className="p-8">
              <div className="mb-5 flex items-center gap-2 text-lg font-bold">기존 기능 <span className="rounded-full bg-zinc-100 px-2 text-sm">{features.length}</span></div>
              <div className="grid gap-4 sm:grid-cols-2">
                {features.map((f, i) => (
                  <div key={i} className="rounded-2xl p-5 shadow-[0_12px_30px_-20px_rgba(0,0,0,0.35)] ring-1 ring-zinc-100">
                    <div className="font-mono text-sm font-semibold text-blue-600">{f.id}</div>
                    <p className="mt-2 text-[15px] leading-relaxed text-zinc-700"><Md text={f.text} /></p>
                    <SourceLink q={(f.quotes || [])[0]} />
                  </div>
                ))}
              </div>
            </div>
            <div className="border-t border-zinc-100 bg-zinc-50/60 p-8 lg:border-l lg:border-t-0">
              <div className="text-lg font-bold">대조 판단 · 검토 기록</div>
              <ul className="mt-3 divide-y divide-zinc-200">
                {matches.map((m, i) => (
                  <li key={i} className="py-4">
                    <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
                      <span className="text-rose-600">{m.from?.text}</span><ArrowRight className="size-3.5 text-zinc-400" aria-hidden /><span className="text-amber-700">{m.to?.text}</span>
                      <Badge chip={{ text: m.label, tone: m.tone }} />
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-zinc-600"><Md text={m.text} /></p>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-zinc-500">판단은 검토 기록에 모델이 쓴 그대로이며, 저장 도구는 형식만 검사했습니다.</p>
            </div>
          </div>
          <Notes blocks={notesOf(s.check)} />
        </div>
      </section>

      {/* flow: text on the left, chains on the right */}
      <section id="g-flow" className="scroll-mt-4 py-24">
        <div className="mx-auto grid max-w-7xl gap-12 px-6 lg:grid-cols-[22rem_1fr] lg:px-10">
          <Heading eyebrow="Flow" title={s.flow?.title} text={flow?.note} />
          <div className="flex flex-col gap-3">
            {chains.map(({ pain, steps }, i) => (
              <div key={i} className="rounded-2xl p-5 ring-1 ring-zinc-200">
                <div className="flex flex-wrap items-center gap-2">
                  <Node id={pain.id} t="red" title={pain.text} />
                  {steps.length === 0 && <span className="text-sm text-zinc-400">연결 기록 없음</span>}
                  {steps.map((st, k) => (
                    <span key={k} className="flex flex-wrap items-center gap-2">
                      <span className="h-px w-5 bg-zinc-300" aria-hidden /><Badge chip={{ text: st.via.label || '연결', tone: st.via.tone || 'gray' }} /><ArrowRight className="size-4 text-zinc-400" aria-hidden />
                      <Node id={st.remaining.id} t="orange" title={st.remaining.text} />
                      {st.concepts.map((c) => <span key={c.id} className="flex items-center gap-2"><ArrowRight className="size-4 text-zinc-400" aria-hidden /><Node id={c.id} t="purple" title={c.text} /></span>)}
                    </span>
                  ))}
                </div>
                <p className="mt-2 line-clamp-2 text-sm text-zinc-500"><Md text={pain.text} /></p>
              </div>
            ))}
            {orphanRemaining.map(({ remaining, concepts }, i) => (
              <div key={'r' + i} className="flex flex-wrap items-center gap-2 rounded-2xl p-5 ring-1 ring-zinc-200">
                <span className="text-sm text-zinc-400">현재 불편 연결 기록 없음</span><ArrowRight className="size-4 text-zinc-400" aria-hidden />
                <Node id={remaining.id} t="orange" title={remaining.text} />
                {concepts.map((c) => <span key={c.id} className="flex items-center gap-2"><ArrowRight className="size-4 text-zinc-400" aria-hidden /><Node id={c.id} t="purple" title={c.text} /></span>)}
              </div>
            ))}
            {orphanConcepts.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 rounded-2xl p-5 text-sm text-zinc-500 ring-1 ring-zinc-200">
                연결 기록 없는 제안 {orphanConcepts.map((c) => <Node key={c.id} id={c.id} t="purple" title={c.text} />)}
              </div>
            )}
            <Notes blocks={notesOf(s.flow)} />
          </div>
        </div>
      </section>

      {/* solution: numbered cards */}
      <section id="g-solution" className="scroll-mt-4 bg-zinc-50 py-24">
        <Heading eyebrow="Solution" title={s.solution?.title} text={s.solution?.text} center />
        <div className={cn('mx-auto mt-12 grid gap-6 px-6 lg:px-10', sols.length > 1 ? 'max-w-7xl md:grid-cols-2 xl:grid-cols-3' : 'max-w-3xl')}>
          {sols.map((c, i) => (
            <article key={i} className="flex flex-col rounded-[1.75rem] bg-white p-8 shadow-[0_24px_50px_-36px_rgba(0,0,0,0.35)] ring-1 ring-zinc-100">
              <div className="flex items-start justify-between gap-4">
                <span className={cn('text-5xl font-extrabold leading-none tabular-nums', RED)}>{pad(i + 1)}</span>
                <span className="font-mono text-sm font-semibold text-violet-600">{c.id}</span>
              </div>
              <Badges items={[...(c.chips || []), ...(c.links || []).map((x: Block) => ({ text: '← ' + x.text, tone: 'orange' }))]} className="mt-5" />
              <p className="mt-4 text-[17px] font-semibold leading-relaxed"><Md text={c.text} /></p>
              {c.steps?.length > 0 && (
                <ol className="mt-5 flex flex-col gap-2 border-t border-zinc-100 pt-5">
                  {c.steps.map((x: string, k: number) => (
                    <li key={k} className="flex gap-3 text-sm leading-relaxed text-zinc-700"><span className={cn('shrink-0 font-semibold tabular-nums', RED)}>{pad(k + 1)}</span><span><Md text={x} /></span></li>
                  ))}
                </ol>
              )}
              {c.plan && (
                <dl className="mt-5 grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-2 rounded-2xl bg-[#fdf5f4] p-4 text-sm">
                  <dt className="text-zinc-500">검증</dt><dd><Badge chip={{ text: c.plan.status, tone: 'orange' }} /></dd>
                  {c.plan.rows.filter((r: Block) => r.k === '지표' || r.k === '성공 기준').map((r: Block, k: number) => (
                    <div key={k} className="contents"><dt className="text-zinc-500">{r.k}</dt><dd className="text-zinc-700"><Md text={r.v} /></dd></div>
                  ))}
                </dl>
              )}
            </article>
          ))}
        </div>
        <div className="mx-auto max-w-7xl px-6 lg:px-10"><Notes blocks={notesOf(s.solution)} /></div>
      </section>

      {/* limits: dark closing banner */}
      <section id="g-limits" className="relative isolate scroll-mt-4 overflow-hidden bg-[#0a1533] text-white">
        <NetworkGlobe dim />
        <div className="relative mx-auto max-w-7xl px-6 py-24 lg:px-10">
          <div className="text-sm font-semibold text-[#ff6a60]">Limits</div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{s.trust?.title}</h2>
          <p className="mt-4 max-w-3xl text-lg leading-relaxed text-white/80">검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정이며, 검토 기록은 모델이 쓰고 저장 도구는 형식만 검사했습니다.</p>
          <div className="mt-12 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {tiles.map((t, i) => (
              <div key={i} className="border-t border-white/15 pt-4">
                <div className="text-xs text-white/55">{t.label}</div>
                <div className={cn('mt-1 text-4xl font-bold tracking-tight', ON_DARK[tone(t.tone)])}>{fmt(t.value)}{t.unit && <span className="ml-1 text-base font-medium text-white/55">{t.unit}</span>}</div>
                {t.note && <div className="mt-1 text-sm text-white/55">{t.note}</div>}
              </div>
            ))}
          </div>
          {notes && <div className="mt-10 flex flex-wrap items-center gap-2 text-sm text-white/70">{notes.title}<Badges items={notes.items} /></div>}
        </div>
      </section>

      <footer className="mx-auto flex max-w-7xl flex-col gap-1 px-6 py-10 text-xs text-zinc-500 lg:px-10">
        <span className="text-sm font-bold text-zinc-800">LG AX 상품기획</span>
        <span>{view.context?.meta} · 화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다.</span>
      </footer>
    </div>
  )
}

function Heading({ eyebrow, title, text, center }: { eyebrow: string; title?: string; text?: string; center?: boolean }) {
  return (
    <div className={cn(center && 'mx-auto max-w-3xl px-6 text-center')}>
      <div className={cn('text-sm font-semibold', RED)}>{eyebrow}</div>
      {title && <h2 className="mt-3 text-balance text-3xl font-bold leading-snug tracking-tight sm:text-4xl">{title}</h2>}
      {text && <p className="mt-4 text-[15px] leading-relaxed text-zinc-500"><Md text={text} /></p>}
    </div>
  )
}

const NOTE: Record<string, string> = {
  info: 'bg-blue-50 text-blue-950 ring-blue-200', success: 'bg-emerald-50 text-emerald-950 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-950 ring-amber-200', error: 'bg-rose-50 text-rose-950 ring-rose-200',
}
// A section's own note ("결과에 제안이 없습니다" ...).
function Notes({ blocks }: { blocks: Block[] }) {
  if (!blocks.length) return null
  return <div className="mt-6 flex flex-col gap-2">{blocks.map((b, i) => <p key={i} role="note" className={cn('rounded-2xl px-5 py-3 text-sm ring-1 ring-inset', NOTE[b.tone] || NOTE.info)}><Md text={b.text} /></p>)}</div>
}

function SourceLink({ q }: { q?: Block }) {
  const h = safeHref(q?.href)
  if (!q) return null
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
      {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} />}{q.site}
      {h && <a href={h} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-blue-700 hover:underline">원문<ArrowUpRight className="size-3" /></a>}
    </div>
  )
}

// Pains as a card carousel; the chosen card turns red and shows its first quote. Every card stays readable.
function ProblemSection({ section, pains, copy }: { section?: Block; pains: Block[]; copy: (s: string) => void }) {
  const [active, setActive] = useState(0)
  const track = useRef<HTMLDivElement>(null)
  const pick = (i: number) => {
    const n = Math.max(0, Math.min(pains.length - 1, i))
    setActive(n)
    track.current?.children[n]?.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' })
  }
  const q: Block | undefined = (pains[active]?.quotes || [])[0]
  return (
    <section id="g-problem" className="relative scroll-mt-4 overflow-hidden py-24">
      <div aria-hidden className="pointer-events-none absolute -bottom-6 left-6 select-none text-[9rem] font-black leading-none text-transparent [-webkit-text-stroke:1.5px_rgb(0_0_0/0.07)] lg:text-[12rem]">PROBLEM</div>
      <div aria-hidden className="absolute bottom-16 right-0 top-16 hidden w-[40%] rounded-l-[3rem] bg-zinc-100/80 lg:block" />
      <div className="relative mx-auto grid max-w-7xl gap-12 px-6 lg:grid-cols-[22rem_1fr] lg:px-10">
        <div>
          <Heading eyebrow="Problem" title={section?.title} text={section?.text} />
          {pains.length > 1 && (
            <div className="mt-8 flex gap-2">
              <button type="button" onClick={() => pick(active - 1)} aria-label="이전 불편" className="grid size-11 place-items-center rounded-full ring-1 ring-zinc-300 hover:bg-zinc-50"><ChevronLeft className="size-5" /></button>
              <button type="button" onClick={() => pick(active + 1)} aria-label="다음 불편" className="grid size-11 place-items-center rounded-full ring-1 ring-zinc-300 hover:bg-zinc-50"><ChevronRight className="size-5" /></button>
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div ref={track} className="flex snap-x gap-5 overflow-x-auto pb-6 pt-2 [scrollbar-width:thin]">
            {pains.map((p, i) => {
              const on = i === active
              const pq: Block | undefined = (p.quotes || [])[0]
              return (
                <button key={i} type="button" onClick={() => pick(i)} aria-pressed={on}
                  className={cn('flex w-[18rem] shrink-0 snap-start flex-col rounded-[1.75rem] p-7 text-left sm:w-[20rem]',
                    on ? 'bg-[#e8463d] text-white shadow-[0_24px_48px_-20px_rgba(232,70,61,0.55)]' : 'bg-white shadow-[0_18px_40px_-26px_rgba(0,0,0,0.3)] ring-1 ring-zinc-100')}>
                  <span className={cn('grid size-14 place-items-center rounded-full', on ? 'bg-white/20' : 'bg-rose-50')}><MessageSquareWarning className={cn('size-6', on ? 'text-white' : 'text-rose-500')} aria-hidden /></span>
                  <span className={cn('mt-8 font-mono text-sm font-semibold', on ? 'text-white/80' : 'text-rose-600')}>{p.id} · 현재 불편</span>
                  <span className={cn('mt-2 text-lg font-bold leading-snug', !on && 'line-clamp-4')}><Md text={p.text} /></span>
                  {on && pq && <span className="mt-5 border-l-2 border-white/50 pl-3 text-sm leading-relaxed text-white/90">“{pq.quote}”</span>}
                  {on && pq && <span className="mt-2 text-xs text-white/75">{[pq.type, pq.site].filter(Boolean).join(' · ')}</span>}
                </button>
              )
            })}
          </div>
          {q && safeHref(q.href) && (
            <a href={safeHref(q.href)!} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-medium text-[#e8463d] hover:underline">
              {pains[active]?.id} 원문 페이지<ArrowUpRight className="size-3.5" />
            </a>
          )}
          <Notes blocks={notesOf(section)} />
          {!pains.length && !notesOf(section).length && <Blocks blocks={section?.blocks || []} copy={copy} />}
        </div>
      </div>
    </section>
  )
}

// Decorative globe with network arcs, drawn in SVG (deterministic, no images).
function NetworkGlobe({ dim }: { dim?: boolean }): ReactNode {
  const u = useId().replace(/:/g, '')
  const cx = 1180, cy = 760, r = 560
  const pts = Array.from({ length: 26 }, (_, i) => {
    const a = (i * 137.5 * Math.PI) / 180, d = r * (0.25 + ((i * 53) % 70) / 100)
    return [cx + Math.cos(a) * d * 0.95, cy - Math.abs(Math.sin(a)) * d * 0.9] as const
  })
  return (
    <svg aria-hidden className={cn('pointer-events-none absolute inset-0 -z-10 h-full w-full', dim && 'opacity-60')} viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
      <defs>
        <radialGradient id={u + "a"} cx="74%" cy="88%" r="60%"><stop offset="0" stopColor="#2563eb" stopOpacity="0.55" /><stop offset="1" stopColor="#07112a" stopOpacity="0" /></radialGradient>
        <radialGradient id={u + "b"} cx="18%" cy="10%" r="40%"><stop offset="0" stopColor="#0ea5e9" stopOpacity="0.18" /><stop offset="1" stopColor="#07112a" stopOpacity="0" /></radialGradient>
        <pattern id={u + "c"} width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.1" fill="#ffffff" fillOpacity="0.09" /></pattern>
      </defs>
      <rect width="1600" height="900" fill={`url(#${u}a)`} />
      <rect width="1600" height="900" fill={`url(#${u}b)`} />
      <rect width="760" height="900" fill={`url(#${u}c)`} />
      <g fill="none" stroke="#93c5fd" strokeOpacity="0.16">
        <circle cx={cx} cy={cy} r={r} />
        {[0.2, 0.45, 0.7, 0.9].map((k) => <ellipse key={'la' + k} cx={cx} cy={cy} rx={r} ry={r * k} />)}
        {[0.2, 0.45, 0.7].map((k) => <ellipse key={'lo' + k} cx={cx} cy={cy} rx={r * k} ry={r} />)}
      </g>
      <g fill="none" stroke="#38bdf8" strokeOpacity="0.45" strokeWidth="1.2">
        {pts.slice(1).map(([x, y], i) => { const [px, py] = pts[(i * 7) % pts.length]; return <path key={i} d={`M${px},${py} Q${(px + x) / 2},${Math.min(py, y) - 90} ${x},${y}`} /> })}
      </g>
      {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i % 5 === 0 ? 4 : 2.2} fill="#7dd3fc" fillOpacity={i % 5 === 0 ? 0.95 : 0.7} />)}
    </svg>
  )
}
