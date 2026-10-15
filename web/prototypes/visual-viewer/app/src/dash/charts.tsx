// K's charts: a donut with its total in the middle and the values beside it, grouped bars and lines in K's colours.
// Every value is the builder's; nothing is counted or smoothed into new numbers here. Charts are drawn at once (no
// grow-in): K's motion is limited to five kinds (index.css "K motion").
import {
  VisArea, VisAxis, VisDonut, VisDonutSelectors, VisGroupedBar, VisGroupedBarSelectors, VisLine, VisScatter,
  VisScatterSelectors, VisSingleContainer, VisTooltip, VisXYContainer,
} from '@unovis/react'
import { useSkin } from '../lib/skin'
import { useVoice } from '../lib/voice'
import { esc, fmt, tone } from '../lib/utils'
import type { Block } from '../types'

type Item = { label: string; value: number; tone?: string; note?: string }
type Series = { name: string; tone?: string; values: number[]; area?: boolean; point_tones?: string[]; point_notes?: string[] }

// Tone colour in K's palette.
function useColor() {
  const hex = useToneHex()
  return (t: string | undefined) => hex[tone(t || 'blue')]
}
const HEX = { blue: '#2563eb', green: '#16a34a', red: '#e11d48', orange: '#f59e0b', purple: '#7c3aed', gray: '#a1a1aa', k1: '#9ccfb0', k2: '#5fae80', k3: '#2f8f57', k4: '#1d5c39' }
export function useToneHex() {
  return useSkin()?.hex || HEX
}

export function NoData() {
  const voice = useVoice()
  return <p className="py-6 text-center text-sm text-muted-foreground">{voice('표시할 값이 없습니다.')}</p>
}

// Total in the middle, each part's label and stored value beside the ring.
export function SkinDonut({ b, arc = 28 }: { b: Block; arc?: number }) {
  const color = useColor()
  const items: Item[] = (b.items || []).filter((i: Item) => i.value > 0)
  const total = items.reduce((a, i) => a + i.value, 0)
  if (!total) return <NoData />
  return (
    <div className="flex flex-col items-center gap-6 @md:flex-row">
      <div className="w-full max-w-[13rem] shrink-0">
        <VisSingleContainer data={items} height={208} duration={0}>
          <VisDonut<Item> value={(d) => d.value} color={(d: Item) => color(d.tone)} arcWidth={arc} padAngle={0.015} cornerRadius={3}
            centralLabel={fmt(total)} centralSubLabel={b.center_label || '합계'} />
          <VisTooltip triggers={{ [VisDonutSelectors.segment]: (d: { data: Item }) => `${esc(d.data.label)}: ${fmt(d.data.value)}${esc(b.unit)}${d.data.note ? '<br>' + esc(d.data.note) : ''}` }} />
        </VisSingleContainer>
      </div>
      <ul className="grid w-full min-w-0 flex-1 gap-4 @md:w-auto">
        {items.map((it, i) => (
          <li key={i} title={it.note || undefined}>
            <div className="text-[13px] leading-snug text-muted-foreground">{it.label}</div>
            <div className="mt-1 flex items-center gap-2 text-xl font-semibold tabular-nums">
              <span className="size-2.5 shrink-0 rounded-full" style={{ background: color(it.tone) }} aria-hidden />{fmt(it.value)}<span className="text-sm font-medium text-muted-foreground">{b.unit || ''}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Legend({ series }: { series: Series[] }) {
  const color = useColor()
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {series.map((s, k) => <li key={k} className="flex items-center gap-1.5"><span className="size-2.5 rounded-full" style={{ background: color(s.tone) }} aria-hidden />{s.name}</li>)}
    </ul>
  )
}

export function SkinBars({ b, round = 4, thin }: { b: Block; round?: number; thin?: boolean }) {
  const color = useColor()
  const cats: string[] = b.categories || []
  const series: Series[] = b.series || []
  if (!cats.length || !series.length) return <NoData />
  const data = cats.map((c, i) => ({ c, i, v: series.map((s) => s.values[i] || 0) }))
  type D = (typeof data)[number]
  return (
    <div className="flex flex-col gap-3">
      <Legend series={series} />
      <VisXYContainer<D> data={data} height={260} duration={0} yDomain={[0, Math.max(1, ...data.flatMap((d) => d.v))]}>
        <VisGroupedBar<D> x={(d) => d.i} y={series.map((_, k) => (d: D) => d.v[k])} color={(_: D, k: number) => color(series[k]?.tone)}
          roundedCorners={round} groupPadding={thin ? 0.45 : 0.25} barPadding={thin ? 0.3 : 0.1} />
        <VisAxis type="x" tickFormat={(i: number | Date) => cats[Number(i)] ?? ''} numTicks={cats.length} gridLine={false} />
        <VisAxis type="y" tickFormat={(v: number | Date) => (Number.isInteger(Number(v)) ? fmt(Number(v)) : '')} />
        <VisTooltip triggers={{ [VisGroupedBarSelectors.bar]: (d: D) => `<b>${esc(d.c)}</b><br>` + series.map((s, k) => `${esc(s.name)}: ${fmt(d.v[k])}${esc(b.unit)}`).join('<br>') }} />
      </VisXYContainer>
    </div>
  )
}

// Lines with a soft area under a single series; points keep the builder's status colours (point_tones).
export function SkinLine({ b, area }: { b: Block; area?: boolean }) {
  const color = useColor()
  const hex = useToneHex()
  const xs: string[] = b.x || []
  const series: Series[] = b.series || []
  if (!xs.length || !series.length) return <NoData />
  const data = xs.map((x, i) => ({ x: String(x).replace('\n', ' · '), i, v: series.map((s) => s.values[i] || 0) }))
  type D = (typeof data)[number]
  const first = series[0]
  const tip = (d: D) => `<b>${esc(d.x)}</b>` + series.map((s, k) => `<br>${esc(s.name)}: ${fmt(d.v[k])}${esc(b.unit)}`).join('')
    + (first.point_notes?.[d.i] ? '<br>' + esc(first.point_notes[d.i]) : '')
  return (
    <div className="flex flex-col gap-3">
      {series.length > 1 && <Legend series={series} />}
      <VisXYContainer<D> data={data} height={b.height || 260} duration={0} yDomain={[0, Math.max(1, ...data.flatMap((d) => d.v))]} xDomain={xs.length === 1 ? [-1, 1] : undefined}>
        {series.map((s, k) => (s.area || (area && series.length === 1)) && (
          <VisArea<D> key={'a' + k} x={(d) => d.i} y={(d) => d.v[k]} color={color(s.tone)} opacity={0.12} />
        ))}
        {series.map((s, k) => <VisLine<D> key={'l' + k} x={(d) => d.i} y={(d) => d.v[k]} color={color(s.tone)} lineWidth={2.5} />)}
        <VisScatter<D> x={(d) => d.i} y={(d) => d.v[0]} size={11}
          color={(d) => (first.point_tones?.[d.i] ? hex[tone(first.point_tones[d.i])] : color(first.tone))} strokeColor="#fff" strokeWidth={2} />
        <VisAxis type="x" tickFormat={(i: number | Date) => data[Number(i)]?.x ?? ''} numTicks={Math.min(xs.length, 8)} gridLine={false} />
        <VisAxis type="y" tickFormat={(v: number | Date) => (Number.isInteger(Number(v)) ? fmt(Number(v)) : '')} />
        <VisTooltip triggers={{ [VisScatterSelectors.point]: tip }} />
      </VisXYContainer>
    </div>
  )
}

export const barWidth = (v: number, max: number) => `${Math.max(v > 0 ? 2 : 0, (v / Math.max(1, max)) * 100)}%`
