// D: dark editorial "exhibition" page built with interactions adapted from Skiper UI free components.
// Long scroll: scattered question that settles (skiper31) → text-roll index (skiper58) → pains as expanding strips
// (skiper52) → features and judgments → link chains → numbered proposals → limits, with a scroll ring (skiper89).
// Like B and C it only re-arranges the story page blocks; chains use only links the builder passed.
import { useRef, type ReactNode } from 'react'
import { useScroll } from 'motion/react'
import { ArrowUpRight, Quote } from 'lucide-react'
import { ModeSwitch, type Mode } from '../components/mode'
import { HoverExpand, ScatterText, ScrollRing, TextRoll } from '../components/skiper'
import { Blocks } from '../components/blocks'
import { inner, type Story } from '../lib/story'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, View } from '../types'

const INK: Record<string, string> = {
  red: 'text-rose-400', orange: 'text-amber-300', green: 'text-emerald-300', blue: 'text-sky-300', purple: 'text-violet-300', gray: 'text-zinc-400',
}
const PILL: Record<string, string> = {
  red: 'border-rose-400/40 text-rose-300', orange: 'border-amber-300/40 text-amber-200', green: 'border-emerald-300/40 text-emerald-200',
  blue: 'border-sky-300/40 text-sky-200', purple: 'border-violet-300/40 text-violet-200', gray: 'border-white/20 text-zinc-300',
}
const Pill = ({ text, t, title }: { text: string; t?: string; title?: string }) => (
  <span title={title} className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium', PILL[tone(t)])}>{text}</span>
)

export default function Editorial({ view, story, mode, setMode, copy }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void; copy: (s: string) => void }) {
  const cover = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: cover })
  const s = story.sections
  const hero: Block = story.hero || { type: 'hero' }
  const pains: Block[] = inner(s.problem, 'claims')?.items || []
  const features: Block[] = inner(s.check, 'claims')?.items || []
  const matches: Block[] = inner(s.check, 'matches')?.items || []
  const flow = inner(s.flow, 'flow')
  const sols: Block[] = inner(s.solution, 'solutions')?.items || []
  const tiles: Block[] = inner(s.trust, 'tiles')?.items || []
  const notes = inner(s.trust, 'chips')
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  const header = (
    <div className="no-print fixed inset-x-0 top-0 z-40 flex items-center justify-between px-6 py-4 mix-blend-normal">
      <div className="text-sm font-semibold tracking-tight text-white/80">LG AX · 상품기획 결과</div>
      <ModeSwitch mode={mode} setMode={setMode} dark />
    </div>
  )

  if (!story.complete) {
    const page = view.pages.find((p) => p.id === 'story')
    return (
      <div className="min-h-dvh bg-background">
        <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />
        <main className="@container mx-auto flex max-w-3xl flex-col gap-5 px-4 py-16"><Blocks blocks={page?.blocks || []} copy={copy} /></main>
      </div>
    )
  }

  // Chains pain → remaining → concept, from recorded links only.
  const links: Block[] = flow?.links || []
  const nodes: Block[] = flow?.nodes || []
  const textOf = (id: string) => nodes.find((n) => n.id === id)?.text || ''
  const chains = pains.map((p) => ({
    pain: p,
    steps: links.filter((l) => l.from === p.id).map((l) => ({ via: l, remaining: l.to, concepts: links.filter((k) => k.from === l.to).map((k) => k.to) })),
  }))
  const chapters = [
    { id: 'd-problem', word: 'PROBLEM', ko: '현재 불편', n: pains.length },
    { id: 'd-check', word: 'CHECK', ko: '기존 기능 대조', n: features.length },
    { id: 'd-flow', word: 'FLOW', ko: '불편 → 제안 연결', n: links.length },
    { id: 'd-solution', word: 'SOLUTION', ko: '제안', n: sols.length },
    { id: 'd-limits', word: 'LIMITS', ko: '한계', n: null as number | null },
  ]

  return (
    <div className="min-h-dvh bg-[#0b0b0c] text-zinc-100 [color-scheme:dark] selection:bg-amber-300 selection:text-black">
      {header}
      <ScrollRing />

      {/* cover: question settles as you scroll (skiper31) */}
      <section ref={cover} className="relative h-[200vh]">
        <div className="sticky top-0 flex h-dvh flex-col items-center justify-center overflow-hidden px-6 text-center">
          <div className="text-xs uppercase tracking-[0.3em] text-white/40">{hero.eyebrow}</div>
          <h1 className="mt-8 max-w-6xl text-balance text-5xl font-extrabold leading-[1.1] tracking-tight text-amber-300 sm:text-7xl">
            <ScatterText text={hero.title || ''} progress={scrollYProgress} />
          </h1>
          <div className="mt-10 flex flex-wrap justify-center gap-2">
            {(hero.chips || []).map((c: Block, i: number) => <Pill key={i} text={c.text} t={c.tone} title={c.tip} />)}
          </div>
          <dl className="mt-14 grid grid-cols-2 gap-x-14 gap-y-6 sm:grid-cols-4">
            {(hero.stats || []).map((st: Block, i: number) => (
              <div key={i}>
                <dt className="text-xs uppercase tracking-widest text-white/40">{st.label}</dt>
                <dd className="mt-1 font-mono text-5xl font-semibold tabular-nums">{fmt(st.value)}<span className="ml-1 text-base text-white/40">{st.unit}</span></dd>
              </div>
            ))}
          </dl>
          <div className="absolute bottom-10 text-[11px] uppercase tracking-[0.3em] text-white/30">스크롤</div>
        </div>
      </section>

      {/* index: text-roll chapters (skiper58) */}
      <section className="mx-auto max-w-6xl px-6 py-28">
        <div className="mb-8 text-xs uppercase tracking-[0.3em] text-white/40">Index</div>
        <ul className="flex flex-col">
          {chapters.map((c, i) => (
            <li key={c.id} className="border-t border-white/10 last:border-b">
              <button type="button" onClick={() => go(c.id)} className="group flex w-full items-baseline gap-6 py-5 text-left">
                <span className="w-12 font-mono text-sm text-white/30">[{i + 1}]</span>
                <TextRoll className="text-6xl font-extrabold uppercase tracking-[-0.03em] sm:text-8xl">{c.word}</TextRoll>
                <span className="ml-auto text-right text-sm text-white/50">{c.ko}{c.n != null ? <span className="ml-2 font-mono text-white/80">{c.n}</span> : null}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {/* problem: expanding strips (skiper52) */}
      <Chapter id="d-problem" no="01" word="Problem" title={s.problem?.title} text={s.problem?.text}>
        <HoverExpand items={pains} className="max-md:flex-col"
          strip={(p, active) => (
            <div className={cn('absolute inset-0 bg-gradient-to-b from-rose-500/25 via-zinc-900 to-zinc-950 ring-1 ring-inset ring-white/10', active && 'from-rose-500/40')}>
              {!active && <span className="absolute left-1/2 top-6 -translate-x-1/2 font-mono text-sm text-rose-300 [writing-mode:vertical-rl]">{p.id}</span>}
            </div>
          )}
          open={(p) => (
            <div className="max-w-xl">
              <div className="font-mono text-sm text-rose-300">{p.id} · 현재 불편</div>
              <p className="mt-3 line-clamp-5 text-2xl font-semibold leading-snug text-white"><Md text={p.text} /></p>
              {(p.quotes || [])[0] && <QuoteLine q={p.quotes[0]} />}
            </div>
          )} />
        <p className="mt-4 text-xs text-white/40">띠에 마우스를 올리거나 Tab으로 옮기면 펼쳐집니다. 인용은 저장된 원문 그대로입니다.</p>
      </Chapter>

      {/* check: features + judgments */}
      <Chapter id="d-check" no="02" word="Check" title={s.check?.title} text={s.check?.text}>
        <div className="grid gap-x-12 gap-y-8 md:grid-cols-2">
          {features.map((f, i) => (
            <div key={i} className="border-t border-white/15 pt-5">
              <div className="font-mono text-sm text-sky-300">{f.id}</div>
              <p className="mt-2 text-lg leading-relaxed text-white/85"><Md text={f.text} /></p>
            </div>
          ))}
        </div>
        {matches.length > 0 && (
          <div className="mt-16">
            <div className="mb-4 text-xs uppercase tracking-[0.3em] text-white/40">대조 판단 · 검토 기록</div>
            {matches.map((m, i) => (
              <div key={i} className="grid gap-4 border-t border-white/10 py-5 md:grid-cols-[16rem_1fr]">
                <div className="flex items-center gap-2 font-mono text-sm">
                  <span className="text-rose-300">{m.from?.text}</span><span className="text-white/30">→</span><span className="text-amber-200">{m.to?.text}</span>
                  <Pill text={m.label} t={m.tone} />
                </div>
                <p className="text-[15px] leading-relaxed text-white/60"><Md text={m.text} /></p>
              </div>
            ))}
          </div>
        )}
      </Chapter>

      {/* flow: link chains as typographic lines */}
      <Chapter id="d-flow" no="03" word="Flow" title={s.flow?.title} text="선은 검토 기록(feature_matches·concept_links)에 적힌 연결만 이었습니다. 연결이 적히지 않은 불편은 '연결 기록 없음'으로 둡니다.">
        <div className="flex flex-col">
          {chains.map(({ pain, steps }, i) => (
            <div key={i} className="grid gap-3 border-t border-white/10 py-6 md:grid-cols-[1fr_auto]">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 font-mono text-xl">
                <span className="text-rose-300">{pain.id}</span>
                {steps.length === 0 && <span className="text-sm text-white/30">— 연결 기록 없음</span>}
                {steps.map((st, k) => (
                  <span key={k} className="flex flex-wrap items-center gap-3">
                    <span className="text-white/25">──</span><span className={cn('text-sm', INK[tone(st.via.tone)])}>{st.via.label || '연결'}</span><span className="text-white/25">──▶</span>
                    <span className="text-amber-200" title={textOf(st.remaining)}>{st.remaining}</span>
                    {st.concepts.length > 0 && <><span className="text-white/25">──▶</span>{st.concepts.map((c) => <span key={c} className="text-violet-300" title={textOf(c)}>{c}</span>)}</>}
                  </span>
                ))}
              </div>
              <p className="line-clamp-2 max-w-xl text-sm leading-relaxed text-white/45 md:text-right"><Md text={pain.text} /></p>
            </div>
          ))}
        </div>
      </Chapter>

      {/* solution: numbered proposals */}
      <Chapter id="d-solution" no="04" word="Solution" title={s.solution?.title} text={s.solution?.text}>
        <div className="flex flex-col">
          {sols.map((c, i) => (
            <article key={i} className="grid gap-8 border-t border-white/15 py-12 lg:grid-cols-[8rem_1fr_1fr]">
              <div className="font-mono text-7xl font-light leading-none text-amber-300">{String(i + 1).padStart(2, '0')}</div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm text-violet-300">{c.id}</span>
                  {(c.chips || []).map((x: Block, k: number) => <Pill key={k} text={x.text} t={x.tone} />)}
                  {(c.links || []).map((x: Block, k: number) => <Pill key={'l' + k} text={'← ' + x.text} t="orange" />)}
                </div>
                <p className="mt-4 text-2xl font-semibold leading-snug text-white"><Md text={c.text} /></p>
              </div>
              <div className="flex flex-col gap-5 text-[15px]">
                {c.steps?.length > 0 && (
                  <ol className="flex flex-col gap-2">
                    {c.steps.map((x: string, k: number) => (
                      <li key={k} className="flex gap-3 text-white/75"><span className="font-mono text-white/30">{String(k + 1).padStart(2, '0')}</span><span><Md text={x} /></span></li>
                    ))}
                  </ol>
                )}
                {c.plan && (
                  <dl className="grid grid-cols-[5rem_1fr] gap-x-4 gap-y-2 border-t border-white/10 pt-4 text-sm">
                    <dt className="text-white/40">검증</dt><dd><Pill text={c.plan.status} t="orange" /></dd>
                    {c.plan.rows.filter((r: Block) => r.k === '지표' || r.k === '성공 기준').map((r: Block, k: number) => (
                      <div key={k} className="contents"><dt className="text-white/40">{r.k}</dt><dd className="text-white/70"><Md text={r.v} /></dd></div>
                    ))}
                  </dl>
                )}
              </div>
            </article>
          ))}
        </div>
      </Chapter>

      {/* limits: big statements */}
      <Chapter id="d-limits" no="05" word="Limits" title={s.trust?.title}>
        <div className="grid gap-x-12 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {tiles.map((t, i) => (
            <div key={i} className="border-t border-white/15 pt-5">
              <div className="text-xs uppercase tracking-widest text-white/40">{t.label}</div>
              <div className={cn('mt-2 text-6xl font-extrabold tracking-tight', INK[tone(t.tone)])}>{fmt(t.value)}{t.unit && <span className="ml-1 text-xl font-medium text-white/40">{t.unit}</span>}</div>
              {t.note && <div className="mt-2 text-sm text-white/45">{t.note}</div>}
            </div>
          ))}
        </div>
        {notes && <div className="mt-10 flex flex-wrap items-center gap-2 text-sm text-white/50">{notes.title}{(notes.items || []).map((x: Block, k: number) => <Pill key={k} text={x.text} t={x.tone} />)}</div>}
        <p className="mt-14 max-w-4xl text-balance text-3xl font-semibold leading-snug text-white">
          검토 통과는 효과의 증명이 아닙니다. <span className="text-white/50">효과·비용·시장성은 측정 전 미확정이며, 검토 기록은 모델이 쓰고 저장 도구는 형식만 검사했습니다.</span>
        </p>
      </Chapter>

      <footer className="mx-auto flex max-w-6xl flex-col gap-2 border-t border-white/10 px-6 py-10 text-xs text-white/35">
        <div>{view.context?.meta} · 화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다.</div>
        <div>
          Interactions adapted from <a className="underline decoration-white/30 hover:text-white/70" href="https://skiper-ui.com" target="_blank" rel="noopener noreferrer">Skiper UI</a> free
          components (skiper31, skiper52, skiper58, skiper89) by @gurvinder-singh02.
        </div>
      </footer>
    </div>
  )
}

function Chapter({ id, no, word, title, text, children }: { id: string; no: string; word: string; title?: string; text?: string; children: ReactNode }) {
  return (
    <section id={id} className="mx-auto max-w-6xl scroll-mt-16 px-6 py-24">
      <div className="flex items-baseline gap-4 text-xs uppercase tracking-[0.3em] text-white/40"><span className="font-mono">{no}</span>{word}</div>
      {title && <h2 className="mt-5 max-w-4xl text-balance text-4xl font-extrabold leading-tight tracking-tight sm:text-6xl">{title}</h2>}
      {text && <p className="mt-5 max-w-3xl text-[15px] leading-relaxed text-white/55"><Md text={text} /></p>}
      <div className="mt-14">{children}</div>
    </section>
  )
}

function QuoteLine({ q }: { q: Block }) {
  const h = safeHref(q.href)
  return (
    <figure className="mt-5 border-l-2 border-rose-400/60 pl-4">
      <blockquote className="flex gap-2 text-[15px] leading-relaxed text-white/75"><Quote className="mt-1 size-3.5 shrink-0 text-white/30" aria-hidden /><span className="line-clamp-4">{q.quote}</span></blockquote>
      <figcaption className="mt-2 flex flex-wrap items-center gap-2 text-xs text-white/40">
        {q.type && <span>{q.type}</span>}{q.site && <span>· {q.site}</span>}
        {h && <a href={h} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-0.5 text-white/60 underline decoration-white/20 hover:text-white">원문<ArrowUpRight className="size-3" /></a>}
      </figcaption>
    </figure>
  )
}
