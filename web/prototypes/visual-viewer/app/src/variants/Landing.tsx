// H: bright service landing page look (reference: a fintech landing template the user picked). A soft gradient hero
// card with a drawn illustration, pastel number cards, a light-blue card carousel, a STEP list next to a review panel,
// and a grey notice box for the limits. Like B–G it only re-arranges the story page blocks; chains use only recorded
// links. No images or assets from the reference are used; the illustration is drawn with shapes and icons.
import { useRef, useState, type ReactNode } from 'react'
import {
  ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight, CircleCheck, FileText, Lightbulb, MessageSquareWarning, Quote, Rocket,
  Search, Sparkles, TriangleAlert, type LucideIcon,
} from 'lucide-react'
import { Badge, Badges } from '../components/ui'
import { Blocks } from '../components/blocks'
import { ModeSwitch, type Mode } from '../components/mode'
import { chainsOf, inner, notesOf, type Story } from '../lib/story'
import { cn, fmt, Md, safeHref, tone } from '../lib/utils'
import type { Block, View } from '../types'

const BLUE = 'text-[#1f5bff]'
const PASTEL: Record<string, string> = { blue: 'bg-[#eaf1ff]', red: 'bg-[#fff0f1]', orange: 'bg-[#fff6e3]', purple: 'bg-[#f1ecff]', green: 'bg-[#e7f8f3]', gray: 'bg-zinc-100' }
const ICON: Record<string, LucideIcon> = { blue: FileText, red: MessageSquareWarning, orange: TriangleAlert, purple: Lightbulb, green: CircleCheck, gray: Sparkles }
const INK: Record<string, string> = { blue: 'text-blue-600', red: 'text-rose-600', orange: 'text-amber-600', purple: 'text-violet-600', green: 'text-emerald-600', gray: 'text-zinc-500' }
const pad = (n: number) => String(n).padStart(2, '0')

export default function Landing({ view, story, mode, setMode, copy }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void; copy: (s: string) => void }) {
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
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  return (
    <div className="min-h-dvh bg-white text-zinc-900">
      <ModeSwitch mode={mode} setMode={setMode} className="fixed right-4 top-4 z-50" />
      <header className="mx-auto flex max-w-7xl items-baseline gap-3 px-6 py-5">
        <span className={cn('text-xl font-extrabold tracking-tight', BLUE)}>LG AX</span>
        <span className="text-sm text-zinc-500">상품기획 결과</span>
      </header>

      {/* hero card */}
      <section className="mx-auto max-w-7xl px-6">
        <div className="grid items-center gap-10 overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#eceeff] via-[#f0f1ff] to-[#e4efff] px-8 py-14 sm:px-14 lg:grid-cols-[1.25fr_1fr] lg:py-16">
          <div>
            <div className="text-sm text-zinc-500">{hero.eyebrow}</div>
            <h1 className="mt-4 text-balance text-4xl font-extrabold leading-[1.2] tracking-tight sm:text-5xl">{hero.title}</h1>
            <Badges items={hero.chips} className="mt-6" />
            <button type="button" onClick={() => jump('h-stats')} className="mt-8 rounded-md bg-zinc-900 px-5 py-3 text-sm font-semibold text-white hover:bg-zinc-700">결과 보기</button>
          </div>
          <HeroArt />
        </div>
      </section>

      {story.status.length > 0 && (
        <section className="mx-auto mt-10 flex max-w-5xl flex-col gap-3 px-6"><Blocks blocks={story.status} copy={copy} /></section>
      )}

      {/* stat cards */}
      <section id="h-stats" className="mx-auto max-w-6xl scroll-mt-4 px-6 py-24">
        {hero.subtitle && <h2 className="mx-auto max-w-3xl text-balance text-center text-2xl font-bold leading-snug tracking-tight sm:text-3xl"><Md text={hero.subtitle} /></h2>}
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(hero.stats || []).map((st: Block, i: number) => {
            const t = tone(st.tone)
            const Icon = ICON[t]
            return (
              <div key={i} className={cn('relative flex min-h-[13rem] flex-col rounded-2xl p-6', PASTEL[t])}>
                <div className="text-xs text-zinc-400">{pad(i + 1)}</div>
                <div className="mt-1 text-lg font-bold">{st.label}</div>
                <div className="mt-2 text-4xl font-extrabold tabular-nums">{fmt(st.value)}<span className="ml-1 text-base font-semibold text-zinc-500">{st.unit}</span></div>
                <span aria-hidden className="absolute bottom-5 right-5 grid size-14 place-items-center rounded-2xl bg-white/80 shadow-[0_12px_24px_-12px_rgba(0,0,0,0.25)]"><Icon className={cn('size-7', INK[t])} /></span>
              </div>
            )
          })}
        </div>
      </section>

      {/* pains band: card carousel */}
      <PainBand section={s.problem} pains={pains} />

      {/* process: STEP list next to the review panel */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="text-balance text-center text-2xl font-bold tracking-tight sm:text-3xl">{s.check?.title}</h2>
        <div className="mt-14 grid gap-12 lg:grid-cols-[1fr_1.1fr]">
          <ol className="flex flex-col gap-8 lg:border-r lg:border-zinc-200 lg:pr-10">
            <Step n={1} title={s.problem?.title} text={s.problem?.text} />
            <Step n={2} title={s.check?.title} text={s.check?.text}>
              {features.length > 0 && (
                <ul className="mt-3 flex flex-col gap-2">
                  {features.map((f, i) => <li key={i} className="flex gap-2 text-sm leading-relaxed text-zinc-600"><span className="shrink-0 font-mono font-semibold text-blue-600">{f.id}</span><span><Md text={f.text} /></span></li>)}
                </ul>
              )}
            </Step>
            <Step n={3} title={s.flow?.title} text={flow?.note} />
          </ol>
          <div className="self-start rounded-2xl bg-[#eef4ff] p-8">
            <div className="text-center text-lg font-bold">대조 판단 · 검토 기록</div>
            <div className="mt-6 flex flex-col gap-3">
              {matches.map((m, i) => (
                <div key={i} className="grid items-start gap-3 sm:grid-cols-[7.5rem_1fr]">
                  <div className="pt-2 font-mono text-sm font-semibold"><span className="text-rose-600">{m.from?.text}</span> → <span className="text-amber-700">{m.to?.text}</span></div>
                  <div className="rounded-lg bg-white px-4 py-3 text-sm leading-relaxed text-zinc-700 ring-1 ring-zinc-200">
                    <Badge chip={{ text: m.label, tone: m.tone }} className="mr-2" /><Md text={m.text} />
                  </div>
                </div>
              ))}
            </div>
            <Notes blocks={notesOf(s.check)} />
            <p className="mt-5 flex items-start gap-2 text-sm text-zinc-600"><CircleCheck className={cn('mt-0.5 size-4 shrink-0', BLUE)} aria-hidden />판단은 검토 기록에 모델이 쓴 그대로이며, 저장 도구는 형식만 검사했습니다.</p>
            <div className="mt-6 text-center"><button type="button" onClick={() => jump('h-flow')} className="rounded-md bg-[#1f5bff] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#1849d6]">연결 보기</button></div>
          </div>
        </div>
      </section>

      {/* flow: chains */}
      <section id="h-flow" className="scroll-mt-4 bg-[#f6f8ff] py-20">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-center text-2xl font-bold tracking-tight">{s.flow?.title}</h2>
          <div className="mt-10 flex flex-col gap-3">
            {chains.map(({ pain, steps }, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 rounded-xl bg-white px-5 py-4 shadow-[0_8px_24px_-18px_rgba(31,91,255,0.5)] ring-1 ring-blue-100">
                <Id id={pain.id} t="red" title={pain.text} />
                {steps.length === 0 && <span className="text-sm text-zinc-400">연결 기록 없음</span>}
                {steps.map((st, k) => (
                  <span key={k} className="flex flex-wrap items-center gap-2">
                    <ArrowRight className="size-4 text-zinc-300" aria-hidden /><Badge chip={{ text: st.via.label || '연결', tone: st.via.tone || 'gray' }} /><ArrowRight className="size-4 text-zinc-300" aria-hidden />
                    <Id id={st.remaining.id} t="orange" title={st.remaining.text} />
                    {st.concepts.map((c) => <span key={c.id} className="flex items-center gap-2"><ArrowRight className="size-4 text-zinc-300" aria-hidden /><Id id={c.id} t="purple" title={c.text} /></span>)}
                  </span>
                ))}
                <span className="ml-auto hidden max-w-sm truncate text-sm text-zinc-500 md:block"><Md text={pain.text} /></span>
              </div>
            ))}
            {orphanRemaining.map(({ remaining, concepts }, i) => (
              <div key={'r' + i} className="flex flex-wrap items-center gap-2 rounded-xl bg-white px-5 py-4 ring-1 ring-blue-100">
                <span className="text-sm text-zinc-400">현재 불편 연결 기록 없음</span><ArrowRight className="size-4 text-zinc-300" aria-hidden /><Id id={remaining.id} t="orange" title={remaining.text} />
                {concepts.map((c) => <span key={c.id} className="flex items-center gap-2"><ArrowRight className="size-4 text-zinc-300" aria-hidden /><Id id={c.id} t="purple" title={c.text} /></span>)}
              </div>
            ))}
            {orphanConcepts.length > 0 && <div className="flex flex-wrap items-center gap-2 rounded-xl bg-white px-5 py-4 text-sm text-zinc-500 ring-1 ring-blue-100">연결 기록 없는 제안 {orphanConcepts.map((c) => <Id key={c.id} id={c.id} t="purple" title={c.text} />)}</div>}
            <Notes blocks={notesOf(s.flow)} />
          </div>
        </div>
      </section>

      {/* solutions */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="text-balance text-center text-2xl font-bold tracking-tight sm:text-3xl">{s.solution?.title}</h2>
        {s.solution?.text && <p className="mt-3 text-center text-sm text-zinc-500"><Md text={s.solution.text} /></p>}
        <div className={cn('mt-12 grid gap-5', sols.length > 1 ? 'md:grid-cols-2 lg:grid-cols-3' : 'mx-auto max-w-2xl')}>
          {sols.map((c, i) => (
            <article key={i} className="flex flex-col rounded-2xl bg-white p-6 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.35)] ring-1 ring-zinc-200">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-zinc-900 px-2.5 py-1 text-xs font-semibold text-white">제안 {c.id}</span>
                <Badges items={[...(c.chips || []), ...(c.links || []).map((x: Block) => ({ text: '← ' + x.text, tone: 'orange' }))]} />
              </div>
              <p className="mt-4 text-[16px] font-semibold leading-relaxed"><Md text={c.text} /></p>
              {c.steps?.length > 0 && (
                <ol className="mt-4 flex flex-col gap-1.5">
                  {c.steps.map((x: string, k: number) => <li key={k} className="flex gap-2 text-sm leading-relaxed text-zinc-600"><span className={cn('shrink-0 text-xs font-bold leading-6', BLUE)}>STEP {pad(k + 1)}</span><span><Md text={x} /></span></li>)}
                </ol>
              )}
              {c.plan && (
                <dl className="mt-5 grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1.5 rounded-xl bg-[#f6f8ff] p-4 text-sm">
                  <dt className="text-zinc-500">검증</dt><dd><Badge chip={{ text: c.plan.status, tone: 'orange' }} /></dd>
                  {c.plan.rows.filter((r: Block) => r.k === '지표' || r.k === '성공 기준').map((r: Block, k: number) => (
                    <div key={k} className="contents"><dt className="text-zinc-500">{r.k}</dt><dd className="text-zinc-700"><Md text={r.v} /></dd></div>
                  ))}
                </dl>
              )}
            </article>
          ))}
        </div>
        <Notes blocks={notesOf(s.solution)} />
      </section>

      {/* limits as a notice box */}
      <section className="mx-auto max-w-6xl px-6 pb-16">
        <div className="grid gap-8 rounded-2xl bg-zinc-50 p-8 text-sm leading-relaxed text-zinc-600 md:grid-cols-2 sm:p-10">
          <div>
            <div className="font-semibold text-zinc-800">[{s.trust?.title || '믿을 수 있는 정도와 한계'}]</div>
            <ul className="mt-2 flex flex-col gap-1">
              {tiles.map((t, i) => (
                <li key={i}>• {t.label}: <b className={cn('font-semibold', INK[tone(t.tone)])}>{fmt(t.value)}{t.unit || ''}</b>{t.note ? ` (${t.note})` : ''}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="font-semibold text-zinc-800">[한계]</div>
            <p className="mt-2">검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정이며, 검토 기록은 모델이 쓰고 저장 도구는 형식만 검사했습니다.</p>
            {notes && <div className="mt-3 flex flex-wrap items-center gap-2">{notes.title}<Badges items={notes.items} /></div>}
          </div>
        </div>
      </section>

      <footer className="flex flex-col items-center gap-2 border-t border-zinc-100 px-6 py-10 text-center text-xs text-zinc-500">
        <span className={cn('text-base font-extrabold', BLUE)}>LG AX</span>
        <span>{view.context?.meta} · 화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다.</span>
      </footer>
    </div>
  )
}

const Id = ({ id, t, title }: { id: string; t: string; title?: string }) => (
  <span title={title} className={cn('rounded-full px-3 py-1 font-mono text-sm font-semibold', PASTEL[t], INK[t])}>{id}</span>
)

function Step({ n, title, text, children }: { n: number; title?: string; text?: string; children?: ReactNode }) {
  return (
    <li className="border-b border-zinc-200 pb-8 last:border-0 last:pb-0">
      <div className={cn('text-xs font-bold', BLUE)}>STEP {pad(n)}</div>
      {title && <div className="mt-1 text-lg font-bold">{title}</div>}
      {text && <p className="mt-2 text-sm leading-relaxed text-zinc-500"><Md text={text} /></p>}
      {children}
    </li>
  )
}

const NOTE: Record<string, string> = {
  info: 'bg-blue-50 text-blue-950 ring-blue-200', success: 'bg-emerald-50 text-emerald-950 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-950 ring-amber-200', error: 'bg-rose-50 text-rose-950 ring-rose-200',
}
// A section's own note ("결과에 제안이 없습니다" ...).
function Notes({ blocks }: { blocks: Block[] }) {
  if (!blocks.length) return null
  return <div className="mt-6 flex flex-col gap-2">{blocks.map((b, i) => <p key={i} role="note" className={cn('rounded-xl px-4 py-3 text-sm ring-1 ring-inset', NOTE[b.tone] || NOTE.info)}><Md text={b.text} /></p>)}</div>
}

// Pains in a light-blue band as a card carousel; the chosen card gets a blue frame and shows its first quote.
function PainBand({ section, pains }: { section?: Block; pains: Block[] }) {
  const [active, setActive] = useState(0)
  const track = useRef<HTMLDivElement>(null)
  const pick = (i: number) => {
    const n = Math.max(0, Math.min(pains.length - 1, i))
    setActive(n)
    track.current?.children[n]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }
  return (
    <section className="bg-[#eef4ff] py-24">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <h2 className="text-balance text-2xl font-bold tracking-tight sm:text-3xl">{section?.title}</h2>
        {section?.text && <p className="mt-3 text-sm text-zinc-500"><Md text={section.text} /></p>}
      </div>
      <div ref={track} className="mx-auto mt-12 flex max-w-7xl snap-x items-start gap-5 overflow-x-auto px-6 pb-4 pt-3 [scrollbar-width:none]">
        {pains.map((p, i) => {
          const on = i === active
          const q: Block | undefined = (p.quotes || [])[0]
          const h = safeHref(q?.href)
          return (
            <div key={i} className={cn('flex w-[18rem] shrink-0 snap-center flex-col rounded-2xl bg-white p-6', on ? 'ring-2 ring-[#1f5bff] shadow-[0_18px_40px_-20px_rgba(31,91,255,0.45)]' : 'ring-1 ring-zinc-200')}>
              <button type="button" onClick={() => pick(i)} aria-pressed={on} className="text-left">
                <span className="rounded-full bg-zinc-900 px-2.5 py-1 text-xs font-semibold text-white">{p.id}</span>
                <span className={cn('mt-4 block text-[16px] font-bold leading-snug', !on && 'line-clamp-4')}><Md text={p.text} /></span>
              </button>
              {on && q && (
                <figure className="mt-4 rounded-xl bg-[#f6f8ff] p-3 text-sm leading-relaxed text-zinc-700">
                  <blockquote className="flex gap-2"><Quote className="mt-0.5 size-3.5 shrink-0 text-zinc-300" aria-hidden /><span>{q.quote}</span></blockquote>
                  <figcaption className="mt-2 flex flex-wrap items-center gap-2 pl-5 text-xs text-zinc-500">
                    {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} />}{q.site}
                    {h && <a href={h} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-blue-700 hover:underline">원문<ArrowUpRight className="size-3" /></a>}
                  </figcaption>
                </figure>
              )}
              {!on && <button type="button" onClick={() => pick(i)} className="mt-5 inline-flex items-center gap-1 self-start text-sm font-medium text-zinc-700 hover:text-[#1f5bff]">원문 보기<ChevronRight className="size-4" aria-hidden /></button>}
            </div>
          )
        })}
      </div>
      {pains.length > 1 && (
        <div className="mx-auto mt-8 flex max-w-5xl items-center gap-6 px-6">
          <div className="h-0.5 flex-1 bg-zinc-200"><div className="h-full bg-[#1f5bff]" style={{ width: `${((active + 1) / pains.length) * 100}%` }} /></div>
          <span className="font-mono text-xs text-zinc-500">{pad(active + 1)} / {pad(pains.length)}</span>
          <button type="button" onClick={() => pick(active - 1)} aria-label="이전 불편" className="rounded p-1 hover:bg-white"><ChevronLeft className="size-4" /></button>
          <button type="button" onClick={() => pick(active + 1)} aria-label="다음 불편" className="rounded p-1 hover:bg-white"><ChevronRight className="size-4" /></button>
        </div>
      )}
      <div className="mx-auto max-w-5xl px-6"><Notes blocks={notesOf(section)} /></div>
    </section>
  )
}

// Drawn hero illustration (shapes and icons only).
function HeroArt() {
  return (
    <div aria-hidden className="relative mx-auto aspect-square w-full max-w-[24rem]">
      <div className="absolute inset-[9%] rounded-full bg-[#fbefc4]" />
      <Coin className="left-[0%] top-[8%] size-24" icon={Quote} />
      <Coin className="right-[0%] top-[20%] size-20" icon={Search} />
      <Coin className="bottom-[4%] right-[14%] size-24" icon={Lightbulb} />
      <div className="absolute left-1/2 top-1/2 grid size-44 -translate-x-1/2 -translate-y-1/2 -rotate-12 place-items-center rounded-[2.5rem] bg-gradient-to-br from-[#ff6d5e] to-[#d8312b] shadow-[inset_-14px_-18px_0_rgba(0,0,0,0.12),0_30px_60px_-20px_rgba(216,49,43,0.55)]">
        <Rocket className="size-20 text-white" />
      </div>
    </div>
  )
}
function Coin({ className, icon: Icon }: { className: string; icon: LucideIcon }) {
  return (
    <div className={cn('absolute grid place-items-center rounded-full bg-gradient-to-br from-[#ffc66d] to-[#ef8a22] shadow-[inset_-6px_-8px_0_rgba(0,0,0,0.12),0_16px_30px_-12px_rgba(239,138,34,0.6)]', className)}>
      <Icon className="size-1/2 text-white" />
    </div>
  )
}
