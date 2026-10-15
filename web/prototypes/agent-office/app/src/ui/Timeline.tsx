// Bottom bar: play / pause, speed, and a strip with every recorded call by lane (main, roles, Skills, web, DB).
import { memo, useCallback, useMemo, useRef } from 'react'
import { ROLE_IDS, SKILL_IDS } from '../lib/catalog'
import { clock, mmss, secs } from '../lib/labels'
import type { SessionModel } from '../lib/model'
import type { Mode } from '../types'
import { colorOf } from '../scene/ctx'

const LANES = [
  { id: 'main', ko: '메인' },
  { id: 'roles', ko: '연구 역할' },
  { id: 'skills', ko: 'Skill' },
  { id: 'web', ko: '웹' },
  { id: 'tools', ko: '셸·파일' },
  { id: 'db', ko: 'DB·질문' },
]

function laneOf(target: string, actor: string, kind: string): string {
  if (kind === 'delegate' || kind === 'handback' || ROLE_IDS.includes(actor)) return 'roles'
  if (SKILL_IDS.includes(target)) return 'skills'
  if (target === 'web') return 'web'
  if (target === 'console' || target === 'shelf') return 'tools'
  return 'main'
}

const Strip = memo(function Strip({ model, end }: { model: SessionModel; end: number }) {
  const span = Math.max(1, end - model.start)
  const x = (t: number) => ((t - model.start) / span) * 1000
  const laneY = (id: string) => LANES.findIndex((l) => l.id === id) * 10 + 1
  return (
    <svg viewBox="0 0 1000 60" preserveAspectRatio="none" className="absolute inset-0 h-full w-full">
      {LANES.map((l, i) => (
        <rect key={l.id} x={0} y={i * 10} width={1000} height={10} fill={i % 2 ? 'rgba(255,255,255,0.025)' : 'transparent'} />
      ))}
      {model.turns.map((tn, i) => (
        <rect key={`turn-${i}`} x={x(tn.start)} y={laneY('main')} width={Math.max(0.6, x(tn.end ?? end) - x(tn.start))} height={8} fill="rgba(56,225,255,0.12)" />
      ))}
      {model.presences.map((p) => (
        <rect key={p.agentId} x={x(p.start)} y={laneY('roles')} width={Math.max(0.8, x(p.end ?? end) - x(p.start))} height={8} fill={colorOf(p.actor)} opacity={0.28} />
      ))}
      {model.spans.map((s) => {
        const lane = laneOf(s.target, s.actor, s.kind)
        const color = s.status === 'fail' || s.detail.accepted === false ? '#ff4d6d' : lane === 'roles' && ROLE_IDS.includes(s.actor) ? colorOf(s.actor) : s.target === 'desk' || s.target === 'main' ? '#38e1ff' : colorOf(s.target)
        return <rect key={s.key} x={x(s.start)} y={laneY(lane) + 1} width={Math.max(0.7, x(s.end ?? end) - x(s.start))} height={6} fill={color} opacity={0.9} />
      })}
      {model.points.map((p) => {
        const color = p.basis === 'db_recorded' ? '#e7c27d' : p.kind === 'request' ? '#b9c8ff' : p.kind === 'turn_end' ? '#38e1ff' : '#8892b8'
        const lane = p.basis === 'db_recorded' || p.kind === 'request' ? 'db' : p.kind === 'role' ? 'roles' : 'main'
        return <rect key={p.key} x={x(p.t) - 0.4} y={laneY(lane)} width={0.8} height={8} fill={color} />
      })}
    </svg>
  )
})

export function Timeline({ model, mode, t, playing, speed, onSeek, onPlay, onSpeed, onLive, skipQuiet, onSkipQuiet, skipped }: {
  model: SessionModel
  mode: Mode
  t: number
  playing: boolean
  speed: number
  onSeek: (t: number) => void
  onPlay: (v: boolean) => void
  onSpeed: (v: number) => void
  onLive?: () => void
  skipQuiet: boolean
  onSkipQuiet: (v: boolean) => void
  skipped: number | null
}) {
  const track = useRef<HTMLDivElement>(null)
  // Live: the strip grows with the clock (rounded to whole seconds so it redraws at most once a second).
  const end = mode === 'live' ? Math.max(model.end, Math.ceil(t / 1000) * 1000) : model.end
  const span = Math.max(1, end - model.start)
  const frac = Math.min(1, Math.max(0, (t - model.start) / span))
  const seekAt = useCallback((clientX: number) => {
    const el = track.current
    if (!el) return
    const r = el.getBoundingClientRect()
    onSeek(model.start + Math.min(1, Math.max(0, (clientX - r.left) / r.width)) * span)
  }, [model.start, span, onSeek])
  const drag = useRef(false)
  const speeds = useMemo(() => [1, 4, 8, 16, 32, 64], [])
  return (
    <div className="panel pointer-events-auto flex flex-col gap-2 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        {mode !== 'live' ? (
          <button className="btn btn-primary w-[74px]" onClick={() => onPlay(!playing)}>{playing ? '일시정지' : '재생'}</button>
        ) : (
          <span className="chip chip-live"><span className="live-dot" />실시간</span>
        )}
        <button className="btn" onClick={() => onSeek(model.start)} title="처음으로">처음</button>
        {mode !== 'live' && (
          <div className="flex items-center gap-1" role="group" aria-label="재생 속도">
            {speeds.map((s) => (
              <button key={s} className={`btn btn-sm ${speed === s ? 'btn-on' : ''}`} onClick={() => onSpeed(s)}>{s}x</button>
            ))}
          </div>
        )}
        {mode !== 'live' && (
          <label className="flex cursor-pointer items-center gap-1.5 text-[11.5px] text-[var(--dim)]">
            <input type="checkbox" checked={skipQuiet} onChange={(e) => onSkipQuiet(e.target.checked)} className="accent-[#38e1ff]" />
            빈 시간 건너뛰기
          </label>
        )}
        {skipped != null && <span className="chip chip-skip">빈 시간 {secs(skipped)} 건너뜀</span>}
        <div className="ml-auto flex items-center gap-3 font-mono text-[12px] text-[var(--dim)]">
          <span className="text-[var(--fg)]">{clock(t)}</span>
          <span>{mmss(t - model.start)} / {mmss(span)}</span>
          {onLive && <button className="btn btn-sm" onClick={onLive}>실시간 보기</button>}
        </div>
      </div>
      <div className="flex gap-2">
        <div className="hidden w-[64px] shrink-0 flex-col justify-between py-[1px] text-[10px] leading-[10px] text-[var(--dim)] sm:flex">
          {LANES.map((l) => <span key={l.id} className="h-[10px] truncate">{l.ko}</span>)}
        </div>
        <div
          ref={track}
          className="relative h-[60px] flex-1 cursor-pointer overflow-hidden rounded-md border border-[var(--line)] bg-[rgba(4,8,20,0.6)]"
          onPointerDown={(e) => {
            drag.current = true
            ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
            seekAt(e.clientX)
          }}
          onPointerMove={(e) => drag.current && seekAt(e.clientX)}
          onPointerUp={() => (drag.current = false)}
        >
          <Strip model={model} end={end} />
          <div className="playhead" style={{ left: `${frac * 100}%` }} />
        </div>
      </div>
    </div>
  )
}
