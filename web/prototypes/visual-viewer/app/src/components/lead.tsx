// K: an item's card shows the model's summary of it (insights `summaries`, marked "요약") or, without one, the first
// sentence the model wrote (cut at a word near `max` characters, "…" when there is more). Its ID chip opens the whole
// saved text (components/idtip.tsx). An explicit inline disclosure keeps long text readable while scrolling or
// zoomed, without relying on the hover card. The screen never writes a summary of its own.
import { useId, useState } from 'react'
import { Md } from '../lib/utils'

export function leadOf(text: string, max: number): string {
  const whole = String(text || '').trim()
  const first = /^(.+?[.!?])(?=\s|$)/s.exec(whole)?.[1] ?? whole
  if (first.length <= max) return first
  const cut = first.slice(0, max)
  const space = cut.lastIndexOf(' ')
  return (space > max * 0.6 ? cut.slice(0, space) : cut).replace(/[\s,·(]+$/, '')
}

export function Lead({ text, summary, max = 90 }: { text: string; summary?: string | null; max?: number }) {
  const fullId = useId()
  const [expanded, setExpanded] = useState(false)
  const whole = String(text || '').trim()
  const lead = summary ? summary.trim() : leadOf(text, max)
  if (!summary && lead === whole) return <Md text={text} />
  return (
    <span className="lg-lead" data-expanded={expanded}>
      <span aria-hidden className="lg-lead-preview print:hidden">
        <Md text={lead} />
        {summary
          ? <span className="ml-1.5 whitespace-nowrap align-[1px] text-[11px] font-normal text-zinc-400" title="모델이 쓴 요약입니다. 전문은 전체 보기 또는 ID 칩에서 확인할 수 있습니다.">요약</span>
          : <span className="text-muted-foreground"> …</span>}
      </span>
      <button type="button" aria-expanded={expanded} aria-controls={fullId} onClick={() => setExpanded((value) => !value)}
        className="no-print ml-2 rounded text-[12px] font-medium text-[#2f7d4f] underline decoration-dotted underline-offset-2 hover:decoration-solid focus-visible:outline-2 focus-visible:outline-offset-2">
        {expanded ? '접기' : '전체 보기'}
      </button>
      <span id={fullId} className="mt-2 whitespace-pre-wrap break-words print:hidden" style={{ display: expanded ? 'block' : 'none' }}>
        <Md text={text} />
      </span>
      <span className={expanded ? 'hidden print:inline' : 'sr-only print:not-sr-only'}><Md text={text} /></span>
    </span>
  )
}
