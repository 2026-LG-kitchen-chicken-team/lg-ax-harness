// "한눈에 보기" story blocks that K draws with these renderers: matches, the connection flow and the proposals (its own
// renderers in dash/blocks.tsx draw the cover, sections and claims). build_view.py decides every item, count and link;
// this file only lays them out. Connector lines in the flow are drawn only for links the builder passes.
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ArrowRight, Copy, ExternalLink, FileText, Quote } from 'lucide-react'
import { Badge, Badges, Card } from './ui'
import { HoverNote, SourceNote } from './hovernote'
import { Lead } from './lead'
import { useIdTip } from './idtip'
import { cn, Md, safeHref, tone, TONE_DOT, TONE_HEX } from '../lib/utils'
import type { Block } from '../types'

type P = { b: Block; copy: (s: string) => void }

export function QuoteLine({ q }: { q: Block }) {
  const h = safeHref(q.href)
  // The source ID is a reference code; it shows on the 원문 link's hover (or its own mark when there is no link).
  return (
    <figure className="rounded-lg bg-muted/60 px-3 py-2.5">
      <blockquote className="flex gap-2 text-[13px] leading-relaxed">
        <Quote className="mt-0.5 size-3.5 shrink-0 text-zinc-400" aria-hidden />
        <span className="line-clamp-4">{q.quote}</span>
      </blockquote>
      <figcaption className="mt-1.5 flex flex-wrap items-center gap-1.5 pl-5 text-[11px] text-muted-foreground">
        {q.type && <Badge chip={{ text: q.type, tone: q.type_tone || 'gray' }} />}
        {q.site && <span>{q.site}</span>}
        {h && <a href={h} target="_blank" rel="noopener noreferrer" title={q.source_id || undefined} className="inline-flex items-center gap-0.5 text-blue-700 hover:underline">원문<ExternalLink className="size-3" /></a>}
        {q.source_id && !h && <HoverNote note={q.source_id} className="text-zinc-400 hover:text-zinc-700">ID</HoverNote>}
      </figcaption>
    </figure>
  )
}

function Matches({ b }: P) {
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
      {b.source && <div className="flex justify-end px-3 py-1.5"><SourceNote text={b.source} /></div>}
    </Card>
  )
}

// Columns of cards with connector curves between recorded links. The links are also printed inside each card,
// so the meaning does not depend on the drawing (narrow screens hide the curves).
function Flow({ b }: P) {
  // Each node shows the model's summary (or the first sentence); its ID chip opens the whole text.
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
    // If the box is ever drawn scaled, the measured boxes are scaled; the SVG draws in unscaled CSS pixels.
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
      <div ref={box} className={cn('relative grid gap-4', '@4xl:grid-flow-col @4xl:auto-cols-fr @4xl:gap-14')}>
        <svg className={cn('pointer-events-none absolute inset-0 h-full w-full overflow-visible', 'hidden @4xl:block')} aria-hidden>
          {paths.map((p, i) => <path key={i} d={p.d} fill="none" stroke={p.color} strokeOpacity={0.55} strokeWidth={2} />)}
        </svg>
        {cols.map((c) => (
          <div key={c.key} className="relative flex min-w-0 flex-col gap-3">
            <div className={cn('flex items-center gap-2 font-semibold text-muted-foreground', 'text-xs')}>
              <span className={cn('rounded-full', 'size-2', TONE_DOT[tone(c.tone)])} />{c.title}
            </div>
            {nodes.filter((n) => n.column === c.key).map((n) => (
              <div key={n.id} ref={(el) => { if (el) refs.current.set(n.id, el); else refs.current.delete(n.id) }}
                className={cn('relative rounded-xl border bg-card p-3 shadow-xs ring-1 ring-inset ring-transparent')}>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge chip={{ text: n.id, tone: n.tone }} />
                  {outgoing(n.id).map((l, k) => <Badge key={k} chip={{ text: `→ ${l.to}${l.label ? ' · ' + l.label : ''}`, tone: l.tone || 'gray' }} />)}
                </div>
                {n.text && <p className={cn('mt-2 leading-relaxed', 'text-[13px]')}><Lead text={n.text} summary={n.summary} /></p>}
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

// A proposal's evidence is shown as "근거 원문 N건"; the IDs and their quotes open on hover.
function SourcesNote({ items }: { items: Block[] }) {
  const tip = useIdTip()
  const ids = items.map((c) => (typeof c === 'string' ? c : c.text))
  return (
    <details className="group/evidence text-xs text-zinc-600">
      <summary className="inline-flex cursor-pointer items-center gap-1.5 rounded py-1 font-medium text-[#2f7d4f] focus-visible:outline-2">
        <FileText className="size-3.5" aria-hidden />근거 확인 ({ids.length}건)
      </summary>
      <ul className="mt-3 flex flex-col gap-2">{ids.map((id, i) => {
        const entry = tip?.lookup(id), href = safeHref(entry?.href)
        return <li key={id}><details className="rounded-lg border bg-white p-3">
          <summary className="cursor-pointer leading-relaxed text-zinc-700"><b>근거 {i + 1} · {entry?.kind || '자료'}</b>{entry?.location && <span className="ml-2 text-zinc-500">{entry.location}</span>}</summary>
          <p className="mt-3 whitespace-pre-line text-[13px] font-normal leading-relaxed">{entry?.text || '이 자료는 전체 근거 목록에서 확인할 수 있어요.'}</p>
          {href && <a href={href} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex items-center gap-1 font-medium text-[#2f7d4f] underline">{entry?.site || '원문 페이지'}<ExternalLink className="size-3" aria-hidden /></a>}
        </details></li>
      })}</ul>
      <a href="#dashboard" className="mt-3 inline-block font-medium underline underline-offset-2">조사 자료와 출처 전체 보기</a>
    </details>
  )
}

// One user action, with selectable text only when clipboard access is unavailable.
// Copying never starts a model or changes the saved planning result.
function CopyQuestion({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'copied' | 'fallback'>('idle')
  useEffect(() => {
    if (state !== 'copied') return
    const timer = window.setTimeout(() => setState('idle'), 3500)
    return () => window.clearTimeout(timer)
  }, [state])
  const copyQuestion = async () => {
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
      await Promise.race([navigator.clipboard.writeText(text), new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error('clipboard timeout')), 1500)
      })])
      setState('copied')
    } catch { setState('fallback') }
    finally { clearTimeout(timer) }
  }
  return <div className="no-print text-[12px]">
    <button type="button" onClick={copyQuestion} className="inline-flex items-center gap-1.5 rounded-md border border-[#cbdcc8] bg-white px-3 py-2 font-medium text-[#2f7d4f] hover:bg-[#f3f8f1]"><Copy className="size-3.5" aria-hidden />수정 질문 복사</button>
    {state === 'copied' && <span role="status" className="ml-3 text-[#2f7d4f]">복사했습니다. 작업하던 AI 대화에 붙여넣으세요.</span>}
    {state === 'fallback' && <div className="mt-3"><p role="status">질문을 직접 선택해 작업하던 AI 대화에 붙여넣으세요.</p><textarea aria-label="이 제안의 후속 질문" translate="no" spellCheck={false} readOnly value={text} className="mt-2 min-h-28 w-full rounded border bg-white p-3 text-zinc-700" /></div>}
  </div>
}

function WorkDraft({ draft }: { draft: Block }) {
  if (!draft) return null
  if (typeof draft.title !== 'string' || !Array.isArray(draft.columns) || !draft.columns.length || draft.columns.some((c: unknown) => typeof c !== 'string')
    || !Array.isArray(draft.rows) || draft.rows.some((row: unknown) => !Array.isArray(row) || row.length !== draft.columns.length || row.some(cell => typeof cell !== 'string'))) {
    return <p role="status" className="text-[13px] text-zinc-600">업무 초안을 읽지 못했어요. 저장 결과를 다시 열어 주세요.</p>
  }
  return <section aria-label={draft.title} className="rounded-xl border border-[#cbdcc8] bg-[#f8fbf6] p-4">
    <h4 className="text-[15px] font-semibold text-[#244d30]">{draft.title}</h4>
    <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-[13px] leading-relaxed">
      <thead><tr className="border-b border-[#d8e5d5]">{draft.columns.map((c: string, i: number) => <th key={i} scope="col" className="px-3 py-2 align-top font-semibold">{c}</th>)}</tr></thead>
      <tbody>{draft.rows.map((row: string[], i: number) => <tr key={i} className="border-b border-[#e1eadf] last:border-0">{row.map((cell, j) => <td key={j} className="whitespace-pre-wrap px-3 py-3 align-top">{cell}</td>)}</tr>)}</tbody>
    </table></div>
  </section>
}

function Solutions({ b }: P) {
  const items: Block[] = b.items || []
  const heading = (s: Block, i: number) => s.title || `제안 ${String(s.n || i + 1).padStart(2, '0')}`
  const decision = b.planning_decision
  const comparison = (s: Block) => (decision?.comparisons || []).find((c: Block) => c.concept_id === s.id)
  const hasReasons = items.some(s => comparison(s)?.reason)
  const hasTradeoffs = items.some(s => comparison(s)?.tradeoff)
  return (
    <div className="flex flex-col gap-4">
      {b.planner && decision?.summary && <p className="rounded-lg bg-[#edf5e9] p-4 text-[15px] leading-relaxed text-[#244d30]"><Md text={decision.summary} /></p>}
      {b.planner && items.length === 1 && (hasReasons || hasTradeoffs) && <dl className="grid gap-2 rounded-lg border bg-white p-4 text-[13px] leading-relaxed">
        {hasReasons && <div><dt className="font-semibold">선택 이유</dt><dd><Md text={comparison(items[0])?.reason || ''} /></dd></div>}
        {hasTradeoffs && <div><dt className="font-semibold">고려할 점</dt><dd><Md text={comparison(items[0])?.tradeoff || ''} /></dd></div>}
      </dl>}
      {b.planner && items.length > 1 && <section aria-label="제안별 비교" className="rounded-lg border bg-white p-4">
        <h2 className="text-[15px] font-semibold text-zinc-700">제안별 비교</h2>
        <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[560px] text-left text-[13px] leading-relaxed">
          <thead><tr className="border-b text-zinc-500"><th className="w-1/4 px-2 py-2 font-medium">제안</th><th className="px-2 py-2 font-medium">핵심 내용</th>{hasReasons && <th className="px-2 py-2 font-medium">선택 이유</th>}{hasTradeoffs && <th className="px-2 py-2 font-medium">고려할 점</th>}</tr></thead>
          <tbody>{items.map((s, i) => <tr key={i} className="border-b last:border-0">
            <th className="px-2 py-3 align-top font-medium"><a className="text-[#2f7d4f] underline" href={`#planner-proposal-${i + 1}`}>{heading(s, i)}</a></th>
            <td className="px-2 py-3 align-top"><Md text={s.summary || s.text || ''} /></td>
            {hasReasons && <td className="px-2 py-3 align-top"><Md text={comparison(s)?.reason || ''} /></td>}
            {hasTradeoffs && <td className="px-2 py-3 align-top"><Md text={comparison(s)?.tradeoff || ''} /></td>}
          </tr>)}</tbody>
        </table></div>
      </section>}
      {items.map((s: Block, i: number) => (
        <Card key={i} className="scroll-mt-20 overflow-hidden" id={`planner-proposal-${i + 1}`}>
          <div className="flex flex-col gap-4 p-5">
            <div className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold tracking-wide text-[#2f7d4f]">제안 {String(s.n || i + 1).padStart(2, '0')}</span>
                {b.planner && decision?.selected_concept_ids?.includes(s.id) && <span className="rounded-full bg-[#e2efdb] px-2 py-1 text-xs font-semibold text-[#2f7d4f]">착수 제안</span>}
                {!b.planner && <><Badge chip={{ text: s.id, tone: 'k4' }} /><Badges items={s.chips} /></>}
                {b.planner && <Badges items={(s.chips || []).filter((c: Block) => c.text === '하드웨어 필요' || c.text === '내부 치수 필요')} />}
              </div>
              {(s.title || b.planner) && <h3 className="text-[19px] font-semibold leading-snug tracking-tight">{heading(s, i)}</h3>}
              {b.planner ? <>
                {!s.text && s.summary && <p className="text-[15px] leading-relaxed text-zinc-900"><Md text={s.summary} /></p>}
                <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-zinc-800"><Md text={s.text} /></div>
              </> : <p className="text-[15px] leading-relaxed text-zinc-900"><Lead text={s.text} summary={s.summary} /></p>}
              {!b.planner && s.links?.length > 0 && <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">연결된 남은 불편 <Badges items={s.links} /></div>}
              {s.background?.length > 0 && <div className="text-[13px] leading-relaxed text-zinc-600"><b className="text-zinc-800">기획 배경</b>{s.background.map((x: string, k: number) => <p key={k} className="mt-1"><Md text={x} /></p>)}</div>}
              {b.planner && s.work_draft && <WorkDraft draft={s.work_draft} />}
              {s.assumptions?.length > 0 && <MiniList title="추진 전에 확인할 조건" items={s.assumptions} />}
              {b.planner && s.requirements?.length > 0 && <MiniList title="기획 요구사항" items={s.requirements} />}
              {s.steps?.length > 0 && <div className="rounded-lg border border-[#dfe9dc] bg-[#f3f8f1] p-3 text-[13px]"><b className="text-[#2f7d4f]">다음 행동</b><p className="mt-1"><Md text={s.steps[0]} /></p></div>}
              {b.planner && s.follow_up && <CopyQuestion key={s.follow_up} text={s.follow_up} />}
            </div>
            {(s.steps?.length > 0 || s.plan || (!b.planner && s.requirements?.length > 0) || (b.planner && (s.chips || []).some((c: Block) => c.text.startsWith('기존 기능 중복')))) && <details className="planner-detail rounded-lg border bg-muted/20 p-3">
              <summary className="cursor-pointer text-[13px] font-medium">{b.planner ? '적용 순서 · 검증 방법' : '요구사항 · 적용 순서 · 검증 방법'}</summary>
              <div className="mt-3 flex min-w-0 flex-col gap-3">
              {b.planner && <Badges items={(s.chips || []).filter((c: Block) => c.text.startsWith('기존 기능 중복'))} />}
              {!b.planner && s.requirements?.length > 0 && <MiniList title="기획 요구사항" items={s.requirements} />}
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
              ) : null}
              {s.plan ? (
                <div className="rounded-lg border bg-muted/40 p-3">
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold">검증 계획 <Badge chip={{ text: s.plan.status, tone: 'orange' }} /></div>
                  <dl className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-[13px]">
                    {s.plan.rows.map((r: Block, k: number) => <Row key={k} k={r.k} v={r.v} />)}
                  </dl>
                </div>
              ) : null}
              </div>
            </details>}
          </div>
          {s.sources?.length > 0 && <div className="border-t bg-muted/30 px-6 py-2.5"><SourcesNote items={s.sources} /></div>}
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

export const STORY_BLOCKS: Record<string, (p: P) => ReactNode> = { matches: Matches, flow: Flow, solutions: Solutions }
