// K: an item's card shows the model's summary of it (insights `summaries`, marked "요약") or, without one, the first
// sentence the model wrote (cut at a word near `max` characters, "…" when there is more). Its ID chip opens the whole
// saved text (components/idtip.tsx). The screen never writes a summary of its own. Screen readers and print get the
// whole text.
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
  const whole = String(text || '').trim()
  const lead = summary ? summary.trim() : leadOf(text, max)
  if (!summary && lead === whole) return <Md text={text} />
  return (
    <>
      <span aria-hidden className="print:hidden">
        <Md text={lead} />
        {summary
          ? <span className="ml-1.5 whitespace-nowrap align-[1px] text-[11px] font-normal text-zinc-400" title="모델이 쓴 요약입니다. 저장된 원문 전체는 ID 칩에 마우스를 올리면 보입니다.">요약</span>
          : <span className="text-muted-foreground"> …</span>}
      </span>
      <span className="sr-only print:not-sr-only"><Md text={text} /></span>
    </>
  )
}
