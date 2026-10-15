// K: an item's card shows the model's summary of it (insights `summaries`, marked "요약") or, without one, the first
// sentence the model wrote, whole (marked "첫 문장" when more follows). Nothing is cut mid-sentence and no card ends in
// "…" (user request 2026-10-15). Its ID chip opens the whole saved text (components/idtip.tsx). The screen never writes
// a summary of its own. Screen readers and print get the whole text.
import { Md } from '../lib/utils'

export function firstSentence(text: string): string {
  const whole = String(text || '').trim()
  return /^(.+?[.!?])(?=\s|$)/s.exec(whole)?.[1] ?? whole
}

export function Lead({ text, summary }: { text: string; summary?: string | null }) {
  const whole = String(text || '').trim()
  const lead = summary ? summary.trim() : firstSentence(whole)
  if (!summary && lead === whole) return <Md text={text} />
  return (
    <>
      <span aria-hidden className="print:hidden">
        <Md text={lead} />
        <span className="ml-1.5 whitespace-nowrap align-[1px] text-[11px] font-normal text-zinc-400"
          title={summary ? '모델이 쓴 요약입니다. 저장된 원문 전체는 ID 칩에 마우스를 올리면 보입니다.' : '저장된 원문의 첫 문장입니다. 전체는 ID 칩에 마우스를 올리면 보입니다.'}>
          {summary ? '요약' : '첫 문장'}
        </span>
      </span>
      <span className="sr-only print:not-sr-only"><Md text={text} /></span>
    </>
  )
}
