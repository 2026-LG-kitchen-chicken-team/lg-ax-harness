// Charts. Horizontal bars are a plain "bar list" (readable labels, exact values); donut, grouped bars and lines use Unovis.
import {
  VisAxis, VisBulletLegend, VisDonut, VisDonutSelectors, VisGroupedBar, VisGroupedBarSelectors, VisLine, VisArea,
  VisScatter, VisScatterSelectors, VisSingleContainer, VisTooltip, VisXYContainer,
} from '@unovis/react'
import { cn, esc, fmt, tone, TONE_DOT, TONE_HEX } from '../lib/utils'
import type { Block } from '../types'

type Item = { label: string; value: number; tone?: string; note?: string }

export function BarList({ b }: { b: Block }) {
  const items: Item[] = b.items || []
  if (!items.length) return <Empty />
  const max = Math.max(1, ...items.map((i) => i.value || 0))
  return (
    <ul className="flex flex-col gap-2">
      {items.map((it, i) => (
        <li key={i} className="grid grid-cols-[minmax(0,11rem)_minmax(0,1fr)_auto] items-center gap-3 text-sm" title={it.note || undefined}>
          <span className="truncate text-muted-foreground">{it.label}</span>
          <span className="relative h-6 rounded-md bg-muted/70">
            <span
              className={cn('absolute inset-y-0 left-0 rounded-md opacity-90', TONE_DOT[tone(it.tone || b.tone || 'blue')])}
              style={{ width: `${Math.max(it.value > 0 ? 2 : 0, (it.value / max) * 100)}%` }}
            />
          </span>
          <span className="min-w-10 text-right font-semibold tabular-nums">{fmt(it.value)}{b.unit || ''}</span>
        </li>
      ))}
    </ul>
  )
}

function Empty() {
  return <p className="py-6 text-center text-sm text-muted-foreground">표시할 값이 없습니다.</p>
}

export function DonutChart({ b }: { b: Block }) {
  const items: Item[] = (b.items || []).filter((i: Item) => i.value > 0)
  const total = items.reduce((a, i) => a + i.value, 0)
  if (!total) return <Empty />
  return (
    <div className="flex flex-col items-center gap-4">
      <VisSingleContainer data={items} height={240}>
        <VisDonut<Item>
          value={(d) => d.value}
          color={(d) => TONE_HEX[tone(d.tone || 'blue')]}
          arcWidth={34}
          padAngle={0.02}
          cornerRadius={4}
          centralLabel={fmt(total)}
          centralSubLabel={b.center_label || '합계'}
        />
        <VisTooltip triggers={{ [VisDonutSelectors.segment]: (d: { data: Item }) => `${esc(d.data.label)}: ${fmt(d.data.value)}${esc(b.unit)}${d.data.note ? '<br>' + esc(d.data.note) : ''}` }} />
      </VisSingleContainer>
      <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {items.map((it, i) => (
          <li key={i} className="flex items-center gap-1.5">
            <span className={cn('size-2.5 rounded-sm', TONE_DOT[tone(it.tone || 'blue')])} />
            {it.label} <b className="text-foreground tabular-nums">{fmt(it.value)}{b.unit || ''}</b>
          </li>
        ))}
      </ul>
    </div>
  )
}

type Series = { name: string; tone?: string; values: number[]; area?: boolean; point_tones?: string[]; point_notes?: string[] }

export function GroupedBarChart({ b }: { b: Block }) {
  const cats: string[] = b.categories || []
  const series: Series[] = b.series || []
  if (!cats.length || !series.length) return <Empty />
  const data = cats.map((c, i) => ({ c, i, v: series.map((s) => s.values[i] || 0) }))
  type D = (typeof data)[number]
  return (
    <div className="flex flex-col gap-3">
      <VisBulletLegend items={series.map((s) => ({ name: s.name, color: TONE_HEX[tone(s.tone || 'blue')] }))} />
      <VisXYContainer<D> data={data} height={260} yDomain={[0, Math.max(1, ...data.flatMap((d) => d.v))]}>
        <VisGroupedBar<D>
          x={(d) => d.i}
          y={series.map((_, k) => (d: D) => d.v[k])}
          color={(_: D, k: number) => TONE_HEX[tone(series[k]?.tone || 'blue')]}
          roundedCorners={4}
          groupPadding={0.25}
          barPadding={0.1}
        />
        <VisAxis type="x" tickFormat={(i: number | Date) => cats[Number(i)] ?? ''} numTicks={cats.length} gridLine={false} />
        <VisAxis type="y" tickFormat={(v: number | Date) => (Number.isInteger(Number(v)) ? fmt(Number(v)) : '')} />
        <VisTooltip triggers={{ [VisGroupedBarSelectors.bar]: (d: D) => `${esc(d.c)}<br>` + series.map((s, k) => `${esc(s.name)}: ${fmt(d.v[k])}${esc(b.unit)}`).join('<br>') }} />
      </VisXYContainer>
    </div>
  )
}

export function LineChart({ b }: { b: Block }) {
  const xs: string[] = b.x || []
  const series: Series[] = b.series || []
  if (!xs.length || !series.length) return <Empty />
  const data = xs.map((x, i) => ({ x: String(x).replace('\n', ' · '), i, v: series.map((s) => s.values[i] || 0) }))
  type D = (typeof data)[number]
  const first = series[0]
  return (
    <div className="flex flex-col gap-3">
      {series.length > 1 && <VisBulletLegend items={series.map((s) => ({ name: s.name, color: TONE_HEX[tone(s.tone || 'blue')] }))} />}
      <VisXYContainer<D> data={data} height={b.height || 260} yDomain={[0, Math.max(1, ...data.flatMap((d) => d.v))]} xDomain={xs.length === 1 ? [-1, 1] : undefined}>
        {series.map((s, k) => s.area && (
          <VisArea<D> key={'a' + k} x={(d) => d.i} y={(d) => d.v[k]} color={TONE_HEX[tone(s.tone || 'blue')]} opacity={0.12} />
        ))}
        {series.map((s, k) => (
          <VisLine<D> key={'l' + k} x={(d) => d.i} y={(d) => d.v[k]} color={TONE_HEX[tone(s.tone || 'blue')]} lineWidth={2.5} />
        ))}
        <VisScatter<D>
          x={(d) => d.i}
          y={(d) => d.v[0]}
          size={10}
          color={(d) => TONE_HEX[tone(first.point_tones?.[d.i] || first.tone || 'blue')]}
          strokeColor="#fff"
          strokeWidth={2}
        />
        <VisAxis type="x" tickFormat={(i: number | Date) => data[Number(i)]?.x ?? ''} numTicks={Math.min(xs.length, 8)} gridLine={false} />
        <VisAxis type="y" tickFormat={(v: number | Date) => (Number.isInteger(Number(v)) ? fmt(Number(v)) : '')} />
        <VisTooltip triggers={{ [VisScatterSelectors.point]: (d: D) => `${esc(d.x)}<br>${esc(first.name)}: ${fmt(d.v[0])}${esc(b.unit)}${first.point_notes?.[d.i] ? '<br>' + esc(first.point_notes[d.i]) : ''}` }} />
      </VisXYContainer>
    </div>
  )
}
