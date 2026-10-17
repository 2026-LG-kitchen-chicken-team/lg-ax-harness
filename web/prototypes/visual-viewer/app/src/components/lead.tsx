// K: an item's card shows the model's summary of it (insights `summaries`, marked "요약") or, without one, the first
// sentence the model wrote, whole (marked "첫 문장" when more follows). Its ID chip opens the whole
// saved text (components/idtip.tsx). An explicit inline disclosure keeps long text readable while scrolling or
// zoomed, without relying on the hover card. The screen never writes a summary of its own.
import { useId, useState } from 'react'
import { Md } from '../lib/utils'

export function firstSentence(text: string): string {
  const whole = String(text || '').trim()
  return /^(.+?[.!?])(?=\s|$)/s.exec(whole)?.[1] ?? whole
}

export function Lead({ text, summary, quiet = false }: { text: string; summary?: string | null; quiet?: boolean }) {
  const fullId = useId()
  const [expanded, setExpanded] = useState(false)
  const whole = String(text || '').trim()
  const lead = summary ? summary.trim() : firstSentence(whole)
  if (!summary && lead === whole) return <Md text={text} />
  return (
    <span className="lg-lead" data-expanded={expanded}>
      <span aria-hidden className="lg-lead-preview print:hidden">
        <Md text={lead} />
        {!quiet && <span className="ml-1.5 whitespace-nowrap align-[1px] text-[11px] font-normal text-zinc-400"
          title={summary ? '모델이 쓴 요약입니다. 전문은 전체 보기 또는 ID 칩에서 확인할 수 있습니다.' : '저장된 원문의 첫 문장입니다. 전문은 전체 보기 또는 ID 칩에서 확인할 수 있습니다.'}>
          {summary ? '요약' : '첫 문장'}
        </span>}
      </span>
      <button type="button" aria-expanded={expanded} aria-controls={fullId} onClick={() => setExpanded((value) => !value)}
        className="no-print ml-2 rounded text-[12px] font-medium text-[#2f7d4f] underline decoration-dotted underline-offset-2 hover:decoration-solid focus-visible:outline-2 focus-visible:outline-offset-2">
        {expanded ? '접기' : quiet ? '제안 설명 더 보기' : '전체 보기'}
      </button>
      <span id={fullId} className="mt-2 whitespace-pre-wrap break-words print:hidden" style={{ display: expanded ? 'block' : 'none' }}>
        <Md text={text} />
      </span>
      <span className={expanded ? 'hidden print:inline' : 'sr-only print:not-sr-only'}><Md text={text} /></span>
    </span>
  )
}
