// B: 16:9 presentation built on reveal.js (arrow keys, F fullscreen, O/Esc slide overview, ?print-pdf for PDF).
// One message per slide, laid out from the story page blocks only.
import { useEffect, useRef, type ReactNode } from 'react'
import Reveal from 'reveal.js'
import type { RevealApi } from 'reveal.js'
import 'reveal.js/reveal.css'
import { ExternalLink, Printer, Quote } from 'lucide-react'
import { Alert, Badge, Badges } from '../components/ui'
import { DotPattern, StatValue } from '../components/magic'
import { Flow } from '../components/story'
import { ModeSwitch, type Mode } from '../components/mode'
import { chunk, inner, type Story } from '../lib/story'
import { cn, Md, safeHref, tone, TONE_DOT, TONE_HEX, TONE_TEXT } from '../lib/utils'
import type { Block, View } from '../types'

const printing = new URLSearchParams(location.search).has('print-pdf')

export default function Slides({ view, story, mode, setMode }: { view: View; story: Story; mode: Mode; setMode: (m: Mode) => void }) {
  const root = useRef<HTMLDivElement>(null)
  const deck = useRef<RevealApi | null>(null)
  useEffect(() => {
    if (printing) {
      // PDF: every slide as its own 1920x1080 page, then the browser's print dialog (save as PDF there).
      const style = document.createElement('style')
      style.textContent = '@page { size: 1920px 1080px; margin: 0; } html, body { margin: 0; background: #fff; }'
      document.head.appendChild(style)
      const t = window.setTimeout(() => window.print(), 900)
      return () => { window.clearTimeout(t); style.remove() }
    }
    const d = new Reveal(root.current!, {
      width: 1920, height: 1080, margin: 0.03, minScale: 0.1, maxScale: 2,
      hash: false, respondToHashChanges: false, history: false, embedded: false,
      controls: true, controlsTutorial: false, progress: true, slideNumber: 'c/t', center: false,
      transition: 'slide', backgroundTransition: 'fade',
    })
    let alive = true
    d.initialize().then(() => {
      if (!alive) return
      deck.current = d
      // ?slide=N opens the deck at slide N (1-based), e.g. to resume a presentation.
      const n = Number(new URLSearchParams(location.search).get('slide'))
      if (n > 1) d.slide(n - 1)
    })
    return () => { alive = false; try { d.destroy() } catch { /* already gone */ } deck.current = null }
  }, [])
  useEffect(() => { const d = deck.current; if (d) { d.sync(); d.layout() } }, [view])

  const s = story.sections
  const hero: Block = story.hero || { type: 'hero' }
  const pains = inner(s.problem, 'claims')?.items || []
  const features: Block[] = inner(s.check, 'claims')?.items || []
  const matches: Block[] = inner(s.check, 'matches')?.items || []
  const flow = inner(s.flow, 'flow')
  const sols = inner(s.solution, 'solutions')?.items || []
  const tiles = inner(s.trust, 'tiles')?.items || []
  const notes = inner(s.trust, 'chips')
  const meta = view.context?.meta || ''

  const slides: ReactNode[] = []
  slides.push(
    <Slide key="title" bare>
      <div className="relative flex h-full flex-col items-center justify-center overflow-hidden bg-gradient-to-b from-zinc-50 to-white px-32 text-center">
        <DotPattern className="[mask-image:radial-gradient(60%_60%_at_50%_30%,black,transparent)]" />
        <div className="relative inline-flex items-center gap-3 rounded-full border bg-white px-6 py-2 text-2xl text-muted-foreground shadow-xs">
          <span className="size-3 rounded-full bg-emerald-500" />{hero.eyebrow}
        </div>
        <h1 className="relative mt-12 text-balance bg-gradient-to-br from-zinc-950 via-zinc-800 to-zinc-500 bg-clip-text text-[88px] font-bold leading-[1.15] tracking-tight text-transparent">{hero.title}</h1>
        {hero.subtitle && <p className="relative mt-8 max-w-[1300px] text-balance text-3xl leading-relaxed text-muted-foreground"><Md text={hero.subtitle} /></p>}
        <Badges items={hero.chips} className="relative mt-8 justify-center [&>span]:px-4 [&>span]:py-1.5 [&>span]:text-xl" />
        {hero.stats?.length > 0 && (
          <div className="relative mt-14 grid w-full max-w-[1400px] grid-flow-col auto-cols-fr gap-px overflow-hidden rounded-2xl border bg-border">
            {hero.stats.map((st: Block, i: number) => (
              <div key={i} className="bg-white px-6 py-8">
                <div className="flex items-center justify-center gap-2 text-2xl text-muted-foreground"><span className={cn('size-3 rounded-full', TONE_DOT[tone(st.tone)])} />{st.label}</div>
                <div className="mt-2 text-7xl font-bold tracking-tight"><StatValue value={st.value} /><span className="ml-1 text-3xl font-medium text-muted-foreground">{st.unit}</span></div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Slide>,
  )
  if (story.status.length) {
    slides.push(
      <Slide key="status" label="먼저 볼 상태" tone="orange" title="이 결과를 볼 때 알아야 할 것">
        <div className="flex flex-col gap-5 text-2xl [&_div[role=note]]:text-2xl [&_div[role=note]]:leading-relaxed">
          {story.status.map((b, i) => <Alert key={i} tone={b.tone}><Md text={b.text} /></Alert>)}
        </div>
      </Slide>,
    )
  }
  if (!story.complete) {
    slides.push(
      <Slide key="empty" label="결과 없음" tone="gray" title="승인된 결과가 없어 이야기 슬라이드를 만들지 않았습니다">
        <p className="text-3xl leading-relaxed text-muted-foreground">위 상태와 이유는 A 앱 보기의 요청·개요 화면에서 자세히 볼 수 있습니다.</p>
      </Slide>,
    )
  }
  pains.forEach((p: Block, i: number) => slides.push(
    <Slide key={'p' + i} label={`Problem · 현재 불편 ${i + 1}/${pains.length}`} tone="red" title={null}>
      <div className="grid h-full grid-cols-[1.1fr_1fr] gap-16">
        <div className="flex flex-col justify-center gap-8">
          <Badge chip={{ text: p.id, tone: 'red' }} className="self-start px-4 py-1.5 text-2xl" />
          <p className="line-clamp-6 text-balance text-5xl font-semibold leading-[1.35] tracking-tight"><Md text={p.text} /></p>
          <Badges items={p.chips} className="[&>span]:text-lg" />
        </div>
        <div className="flex flex-col justify-center gap-6">
          {(p.quotes || []).map((q: Block, k: number) => <BigQuote key={k} q={q} />)}
          {!(p.quotes || []).length && <p className="text-2xl text-muted-foreground">연결된 원문이 없습니다.</p>}
        </div>
      </div>
    </Slide>,
  ))
  chunk(features, 4).forEach((group, gi, all) => slides.push(
    <Slide key={'f' + gi} label={`Check · 기존 기능${all.length > 1 ? ` ${gi + 1}/${all.length}` : ''}`} tone="blue" title={s.check?.title}>
      <div className="grid grid-cols-2 gap-6">
        {group.map((f: Block, k: number) => (
          <div key={k} className="relative overflow-hidden rounded-2xl border bg-white p-7">
            <span className="absolute inset-x-0 top-0 h-1.5" style={{ background: TONE_HEX.blue }} />
            <Badge chip={{ text: f.id, tone: 'blue' }} className="px-3 text-lg" />
            <p className="mt-4 line-clamp-4 text-[26px] leading-relaxed"><Md text={f.text} /></p>
          </div>
        ))}
      </div>
    </Slide>,
  ))
  chunk(matches, 4).forEach((group, gi, all) => slides.push(
    <Slide key={'m' + gi} label={`Check · 대조 판단${all.length > 1 ? ` ${gi + 1}/${all.length}` : ''}`} tone="blue" title="기능이 있다고 불편이 해소된 것은 아닙니다">
      <div className="flex flex-col divide-y rounded-2xl border bg-white">
        {group.map((m: Block, k: number) => (
          <div key={k} className="grid grid-cols-[auto_1fr] items-start gap-8 p-7">
            <div className="flex items-center gap-3 text-2xl">
              <Badge chip={m.from} className="px-3 text-xl" /><span className="text-muted-foreground">→</span><Badge chip={m.to} className="px-3 text-xl" />
              <Badge chip={{ text: m.label, tone: m.tone }} className="px-3 text-xl font-semibold" />
            </div>
            <p className="line-clamp-3 text-2xl leading-relaxed text-muted-foreground"><Md text={m.text} /></p>
          </div>
        ))}
      </div>
      <p className="mt-6 text-xl text-muted-foreground">판단은 검토 기록에 모델이 쓴 그대로이며, 저장 도구는 형식만 검사했습니다.</p>
    </Slide>,
  ))
  if (flow) slides.push(
    <Slide key="flow" label="Flow · 연결" tone="orange" title={s.flow?.title}>
      <Flow b={flow} copy={() => {}} large />
    </Slide>,
  )
  sols.forEach((c: Block, i: number) => slides.push(
    <Slide key={'c' + i} label={`Solution · 제안 ${i + 1}/${sols.length}`} tone="purple" title={null}>
      <div className="grid h-full grid-cols-[1.15fr_1fr] gap-14">
        <div className="flex flex-col justify-center gap-7">
          <div className="flex flex-wrap items-center gap-3">
            <Badge chip={{ text: c.id, tone: 'purple' }} className="px-4 py-1.5 text-2xl" />
            <Badges items={c.chips} className="[&>span]:px-3 [&>span]:text-lg" />
          </div>
          <p className="line-clamp-6 text-[40px] font-semibold leading-[1.4] tracking-tight"><Md text={c.text} /></p>
          {c.links?.length > 0 && <div className="flex items-center gap-3 text-xl text-muted-foreground">연결된 남은 불편 <Badges items={c.links} className="[&>span]:text-lg" /></div>}
          {c.requirements?.length > 0 && <p className="text-xl text-muted-foreground">요구사항 {c.requirements.length}개 · 전체는 A 앱 보기의 제안 화면</p>}
        </div>
        <div className="flex flex-col justify-center gap-6">
          {c.steps?.length > 0 && (
            <ol className="flex flex-col gap-3">
              {c.steps.slice(0, 6).map((x: string, k: number) => (
                <li key={k} className="flex gap-4 text-[22px] leading-snug">
                  <span className="grid size-9 shrink-0 place-items-center rounded-full bg-violet-100 text-lg font-semibold text-violet-700">{k + 1}</span>
                  <span className="line-clamp-2"><Md text={x} /></span>
                </li>
              ))}
            </ol>
          )}
          {c.plan && (
            <div className="rounded-2xl border bg-zinc-50 p-6">
              <div className="flex items-center gap-3 text-xl font-semibold">검증 계획 <Badge chip={{ text: c.plan.status, tone: 'orange' }} className="text-lg" /></div>
              <dl className="mt-3 grid grid-cols-[6rem_1fr] gap-x-4 gap-y-2 text-xl">
                {c.plan.rows.filter((r: Block) => r.k === '지표' || r.k === '성공 기준').map((r: Block, k: number) => (
                  <div key={k} className="contents"><dt className="text-muted-foreground">{r.k}</dt><dd className="line-clamp-3"><Md text={r.v} /></dd></div>
                ))}
              </dl>
            </div>
          )}
        </div>
      </div>
    </Slide>,
  ))
  if (s.trust) slides.push(
    <Slide key="trust" label="Trust · 한계" tone="gray" title={s.trust.title}>
      <div className="grid grid-cols-3 gap-6">
        {tiles.map((t: Block, i: number) => (
          <div key={i} className="rounded-2xl border bg-white p-7">
            <div className="text-xl text-muted-foreground">{t.label}</div>
            <div className={cn('mt-2 text-6xl font-bold tracking-tight', TONE_TEXT[tone(t.tone)])}><StatValue value={t.value} />{t.unit && <span className="ml-1 text-3xl font-medium text-muted-foreground">{t.unit}</span>}</div>
            {t.note && <div className="mt-2 line-clamp-2 text-lg text-muted-foreground">{t.note}</div>}
          </div>
        ))}
      </div>
      {notes && <div className="mt-8 flex items-center gap-4 text-xl text-muted-foreground">{notes.title}<Badges items={notes.items} className="[&>span]:text-lg" /></div>}
      <div className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 px-7 py-5 text-2xl leading-relaxed text-amber-950">
        검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정입니다.
      </div>
    </Slide>,
  )
  slides.push(
    <Slide key="end" bare>
      <div className="flex h-full flex-col items-center justify-center gap-6 bg-zinc-950 px-32 text-center text-white">
        <div className="text-2xl text-zinc-400">{meta}</div>
        <div className="text-balance text-6xl font-bold tracking-tight">근거·원문·업무 기록은 A 앱 보기의 세부 화면에서</div>
        <div className="text-2xl text-zinc-400">화면은 저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다.</div>
      </div>
    </Slide>,
  )

  if (printing) {
    return <div className="lgax-print">{slides.map((sl, i) => <div key={i} className="lgax-print-page">{sl}</div>)}</div>
  }
  return (
    <>
      <div className="fixed right-4 top-4 z-50 flex items-center gap-2 no-print">
        <ModeSwitch mode={mode} setMode={setMode} />
        <a href={'?print-pdf&mode=slides'} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-zinc-100 px-2.5 text-xs font-medium text-zinc-700 hover:bg-zinc-200" title="모든 슬라이드를 인쇄 화면으로 펼칩니다. 인쇄 창에서 PDF로 저장하세요.">
          <Printer className="size-3.5" />PDF
        </a>
      </div>
      <div className="reveal lgax-slides" ref={root}>
        <div className="slides">{slides}</div>
      </div>
    </>
  )
}

function Slide({ label, tone: t, title, children, bare }: { label?: string; tone?: string; title?: string | null; children?: ReactNode; bare?: boolean }) {
  if (bare) return <section className="!h-full !p-0 text-left">{children}</section>
  return (
    <section className="!h-full text-left">
      <div className="flex h-full flex-col px-24 pb-20 pt-20">
        {label && <div className={cn('text-xl font-semibold uppercase tracking-[0.2em]', TONE_TEXT[tone(t)])}>{label}</div>}
        {title && <h2 className="mt-4 text-balance text-6xl font-bold leading-tight tracking-tight">{title}</h2>}
        <div className={cn('min-h-0 flex-1', title ? 'mt-12' : 'mt-6')}>{children}</div>
      </div>
    </section>
  )
}

function BigQuote({ q }: { q: Block }) {
  const h = safeHref(q.href)
  return (
    <figure className="rounded-2xl bg-zinc-50 p-7 ring-1 ring-inset ring-zinc-200">
      <blockquote className="flex gap-4 text-[26px] leading-relaxed">
        <Quote className="mt-1 size-7 shrink-0 text-zinc-300" aria-hidden />
        <span className="line-clamp-5">{q.quote}</span>
      </blockquote>
      <figcaption className="mt-4 flex flex-wrap items-center gap-3 pl-11 text-lg text-muted-foreground">
        {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} className="text-base" />}
        {q.site && <span>{q.site}</span>}
        {h && <a href={h} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue-700">원문<ExternalLink className="size-4" /></a>}
      </figcaption>
    </figure>
  )
}
