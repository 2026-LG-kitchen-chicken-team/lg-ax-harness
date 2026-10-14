import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { NODE } from './lib/catalog'
import { useLiveFile, parseRecordFile } from './lib/data'
import { demoLive } from './lib/demo'
import { dayClock, mmss, secs, STATUS_KO } from './lib/labels'
import { buildSession, parseTime, quietUntil, sessionsOf } from './lib/model'
import { snapshot } from './lib/state'
import { Office } from './scene/Office'
import { Inspector } from './ui/Inspector'
import { Feed, NowPanel } from './ui/NowPanel'
import { Timeline } from './ui/Timeline'
import type { DbSnapshot, Mode, OfficeEvent } from './types'

interface Source {
  name: string
  events: OfficeEvent[]
  db: DbSnapshot | null
}

const RECENT_LIVE_MS = 15 * 60_000

function lastEventAt(events: OfficeEvent[]): number | null {
  let best: number | null = null
  for (const e of events) {
    const t = parseTime(e.ts)
    if (t != null && (best == null || t > best)) best = t
  }
  return best
}

// Link to a moment: #mode=replay&s=2&t=95&sel=evidence-retrieval&play=0 (s is 1-based, t is seconds from the start).
const HASH = new URLSearchParams(window.location.hash.slice(1))

function initialMode(): Mode {
  const asked = HASH.get('mode')
  if (asked === 'demo' || ((asked === 'replay' || asked === 'live') && window.LGAX_OFFICE_LIVE?.events?.length)) return asked
  const live = window.LGAX_OFFICE_LIVE
  if (!live?.events?.length) return 'demo'
  const last = lastEventAt(live.events)
  return last != null && Date.now() - last < RECENT_LIVE_MS ? 'live' : 'replay'
}

export function App() {
  const { live, checkedAt } = useLiveFile(true)
  const [mode, setMode] = useState<Mode>(initialMode)
  const [file, setFile] = useState<Source | null>(null)
  const [fileNote, setFileNote] = useState<string | null>(null)
  const demo = useMemo(() => demoLive(), [])
  const source: Source = useMemo(() => {
    if (mode === 'demo') return { name: '데모', events: demo.events, db: demo.db ?? null }
    if (mode === 'replay' && file) return file
    return { name: 'live.js', events: live?.events ?? [], db: live?.db ?? null }
  }, [mode, demo, file, live])
  const sessions = useMemo(() => sessionsOf(source.events), [source.events])
  const latestId = sessions.length ? sessions[sessions.length - 1].id : null
  const [pick, setPick] = useState<string | null>(() => {
    const i = Number(HASH.get('s'))
    const list = sessionsOf(window.LGAX_OFFICE_LIVE?.events ?? [])
    return Number.isInteger(i) && i >= 1 && i <= list.length ? list[i - 1].id : null
  })
  const sessionId = mode === 'live' ? latestId : pick && sessions.some((s) => s.id === pick) ? pick : latestId
  const model = useMemo(
    () => buildSession(source.events, sessionId ?? '-', source.db, mode === 'live', sessionId === latestId),
    [source, sessionId, mode, latestId],
  )

  const timeRef = useRef(mode === 'live' ? Date.now() : model.start)
  const [speed, setSpeed] = useState(mode === 'demo' ? 4 : 8)
  const speedRef = useRef(speed)
  const [playing, setPlaying] = useState(true)
  const [skipQuiet, setSkipQuiet] = useState(true)
  const skipRef = useRef(skipQuiet)
  const [skipped, setSkipped] = useState<{ ms: number; at: number } | null>(null)
  const playingRef = useRef(playing)
  const modelRef = useRef(model)
  const modeRef = useRef(mode)
  const [tick, setTick] = useState(timeRef.current)
  useEffect(() => { speedRef.current = mode === 'live' ? 1 : speed }, [speed, mode])
  useEffect(() => { playingRef.current = playing }, [playing])
  useEffect(() => { skipRef.current = skipQuiet }, [skipQuiet])
  useEffect(() => { modelRef.current = model }, [model])
  useEffect(() => { modeRef.current = mode }, [mode])

  // A new session, file or mode starts from its beginning (or now, when live).
  const startKey = `${mode}|${sessionId}|${file?.name ?? ''}`
  const firstStart = useRef(true)
  useEffect(() => {
    const m = modelRef.current
    timeRef.current = modeRef.current === 'live' ? Date.now() : m.start
    let play = true
    if (firstStart.current) {
      firstStart.current = false
      const at = Number(HASH.get('t'))
      if (HASH.has('t') && Number.isFinite(at) && modeRef.current !== 'live') timeRef.current = Math.min(m.end, m.start + at * 1000)
      if (HASH.get('play') === '0') play = false
      const sp = Number(HASH.get('speed'))
      if ([1, 4, 8, 16, 32, 64].includes(sp)) setSpeed(sp)
    } else if (modeRef.current === 'demo') setSpeed(4)
    setTick(timeRef.current)
    setPlaying(play)
  }, [startKey])

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    let lastUi = 0
    let holdUntil = 0
    const step = (now: number) => {
      const dt = Math.min(250, now - last)
      last = now
      const m = modelRef.current
      if (modeRef.current === 'live') timeRef.current = Date.now()
      else if (playingRef.current) {
        timeRef.current += dt * speedRef.current
        // Quiet gaps longer than ~2 s on screen are jumped over (thinking inside a turn is not a gap).
        const next = skipRef.current ? quietUntil(m, timeRef.current) : null
        if (next != null && next - timeRef.current > 2000 * speedRef.current) {
          const lead = 600 * speedRef.current
          setSkipped({ ms: next - lead - timeRef.current, at: now })
          timeRef.current = next - lead
        }
        if (timeRef.current >= m.end) {
          timeRef.current = m.end
          if (modeRef.current === 'demo') {
            if (!holdUntil) holdUntil = now + 3000
            else if (now > holdUntil) {
              timeRef.current = m.start
              holdUntil = 0
            }
          } else {
            playingRef.current = false
            setPlaying(false)
          }
        }
      }
      if (now - lastUi > 125) {
        lastUi = now
        setTick(timeRef.current)
      }
      raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [])

  const snap = useMemo(() => snapshot(model, tick, 40), [model, tick])
  const [selected, setSelected] = useState<string | null>(() => (NODE[HASH.get('sel') ?? ''] ? HASH.get('sel') : null))
  const onSelect = useCallback((id: string | null) => setSelected(id), [])

  const seek = useCallback((t: number) => {
    if (modeRef.current === 'live') {
      setMode('replay')
      setPick(modelRef.current.id)
    }
    timeRef.current = t
    setTick(t)
  }, [])
  const goLive = useCallback(() => {
    setFile(null)
    setMode('live')
  }, [])

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (['SELECT', 'INPUT', 'BUTTON', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return
      if (e.code === 'Space' && modeRef.current !== 'live') {
        e.preventDefault()
        setPlaying((p) => !p)
      } else if (e.key === 'Escape') setSelected(null)
      else if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && modeRef.current !== 'live') {
        const m = modelRef.current
        const step = (e.key === 'ArrowRight' ? 1 : -1) * 5000 * Math.max(1, speedRef.current / 4)
        timeRef.current = Math.min(m.end, Math.max(m.start, timeRef.current + step))
        setTick(timeRef.current)
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])

  const openFile = async (f: File) => {
    const text = await f.text()
    const parsed = parseRecordFile(text)
    if (!parsed.events.length) {
      setFileNote(`${f.name}: 읽을 수 있는 관측 기록이 없습니다.`)
      return
    }
    setFile({ name: f.name, events: parsed.events, db: parsed.live?.db ?? null })
    setFileNote(`${f.name}: 사건 ${parsed.events.length}개${parsed.skipped ? ` (읽지 못한 줄 ${parsed.skipped}개)` : ''}${parsed.live ? '' : ' · DB 정보 없음'}`)
    setPick(null)
    setMode('replay')
  }

  const liveLast = live ? lastEventAt(live.events) : null
  const hasLive = !!live?.events.length
  const db = model.dbMatched ? model.db : null
  const turnStatus = db?.turn?.status ?? null
  const empty = !source.events.length

  return (
    <div className="app-bg relative h-dvh w-full overflow-hidden">
      <div className="absolute inset-0">
        <Office model={model} timeRef={timeRef} speedRef={speedRef} selected={selected} onSelect={onSelect} />
      </div>

      <div className="pointer-events-none absolute inset-0 flex flex-col gap-2 p-2 sm:p-3">
        <header className="panel pointer-events-auto flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2">
          <div className="mr-1 flex min-w-0 flex-col">
            <h1 className="brand">LG AX 기획 사무실</h1>
            <span className="text-[10.5px] text-[var(--dim)]">product v0.10.0 구조 · 메인 1 · 연구 역할 3 · 업무 Skill 6</span>
          </div>
          <div className="seg" role="tablist" aria-label="보기 방식">
            <button role="tab" aria-selected={mode === 'live'} className={mode === 'live' ? 'on' : ''} disabled={!hasLive} onClick={goLive} title={hasLive ? '' : 'live.js가 없습니다'}>실시간</button>
            <button role="tab" aria-selected={mode === 'replay'} className={mode === 'replay' ? 'on' : ''} disabled={!hasLive && !file} onClick={() => setMode('replay')}>기록 재생</button>
            <button role="tab" aria-selected={mode === 'demo'} className={mode === 'demo' ? 'on' : ''} onClick={() => setMode('demo')}>데모</button>
          </div>
          {mode !== 'demo' && sessions.length > 0 && (
            <select className="select" value={sessionId ?? ''} onChange={(e) => { setPick(e.target.value); if (mode === 'live') setMode('replay') }} aria-label="세션 고르기">
              {sessions.map((s, i) => (
                <option key={s.id} value={s.id}>
                  {`${i + 1}. ${dayClock(s.start)} · ${mmss(s.end - s.start)} · 사건 ${s.count}${s.requests ? ` · 질문 ${s.requests}` : ''}${s.roles.length ? ` · 연구 역할 ${s.roles.length}` : ''}`}
                </option>
              ))}
            </select>
          )}
          <label className="btn cursor-pointer">
            기록 파일 열기
            <input type="file" accept=".jsonl,.json,.js,.txt" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void openFile(f); e.target.value = '' }} />
          </label>
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            {turnStatus && <span className={`chip ${turnStatus === 'completed' ? 'chip-ok' : 'chip-warn'}`}>turn {STATUS_KO[turnStatus] ?? turnStatus}</span>}
            {db?.turn && <span className="chip">수정 {db.turn.revision_count ?? '미측정'}/2</span>}
            {snap.workflow && <span className="chip">업무 시계 {mmss(snap.workflow.elapsed)}{snap.workflow.budget ? ` / ${mmss(snap.workflow.budget)}` : ''}</span>}
            {mode === 'live' && <span className="chip chip-live"><span className="live-dot" />{liveLast ? `마지막 기록 ${secs(Date.now() - liveLast)} 전` : '기록 대기'}</span>}
            {mode !== 'live' && file && <span className="chip" title={fileNote ?? ''}>{file.name}</span>}
            {mode !== 'live' && !file && mode === 'replay' && <span className="chip hidden sm:inline-flex">live.js · 최근 {source.events.length}개 사건</span>}
          </div>
        </header>

        {mode === 'demo' && (
          <div className="demo-banner pointer-events-auto">
            <b>데모 화면</b> · 가상 기록으로 움직임만 보여 줍니다. 실제 하네스가 한 일이 아닙니다 (사이트 이름도 *.example).
            {hasLive && <button className="btn btn-sm ml-2" onClick={() => setMode(liveLast && Date.now() - liveLast < RECENT_LIVE_MS ? 'live' : 'replay')}>실제 기록 보기</button>}
          </div>
        )}
        {fileNote && mode === 'replay' && file && <div className="note pointer-events-auto">{fileNote}</div>}

        <div className="flex min-h-0 flex-1 gap-2">
          <div className="hidden w-[300px] shrink-0 flex-col gap-2 lg:flex">
            <div className="min-h-0 flex-1"><NowPanel snap={snap} selected={selected} onSelect={onSelect} /></div>
            <Feed snap={snap} onSelect={onSelect} />
          </div>
          <div className="min-w-0 flex-1" />
          {selected ? (
            <div className="flex w-full max-w-[380px] shrink-0 sm:w-[380px]">
              <Inspector id={selected} model={model} snap={snap} onClose={() => setSelected(null)} />
            </div>
          ) : (
            <div className="hidden w-[300px] shrink-0 flex-col justify-end gap-2 sm:flex">
              <div className="panel pointer-events-auto px-3 py-2.5 text-[11.5px] leading-relaxed">
                <div className="mb-1 text-[12px] font-bold">보는 법</div>
                <div>방이나 사람을 누르면 하는 일·지금 상태·기록이 나옵니다.</div>
                <div><span className="legend-dot" style={{ background: '#38e1ff' }} />빛 기둥: 지금 일하는 곳</div>
                <div><span className="legend-dot" style={{ background: '#ffb547' }} />빛 알갱이: 도구 호출 시작·끝 (빨강은 실패·거절)</div>
                <div><span className="legend-dot" style={{ background: '#c77dff' }} />점선: 아직 끝나지 않은 호출</div>
                <div><span className="legend-dot" style={{ background: '#e7c27d' }} />금색: 하네스 DB에 적힌 기록</div>
                <div className="mt-1 text-[var(--dim)]">흐린 연구실은 이 기록에서 부르지 않은 역할입니다. 바닥 점선은 Skill 설명 순서이고 실제 기록이 아닙니다.</div>
              </div>
            </div>
          )}
        </div>

        {empty ? (
          <div className="panel pointer-events-auto mx-auto flex max-w-[560px] flex-col gap-2 px-4 py-3 text-[12.5px] leading-relaxed">
            <b>아직 관측 기록이 없습니다.</b>
            <span>레포 폴더에서 <code>office.py install --claude &lt;하네스 폴더&gt;</code>로 관측 훅을 설치하고, 그 하네스 폴더에서 Claude Code로 질문하면 여기에 바로 나타납니다.{checkedAt ? '' : ' (live.js를 아직 찾지 못했습니다)'}</span>
            <div><button className="btn" onClick={() => setMode('demo')}>데모 보기</button></div>
          </div>
        ) : (
          <Timeline model={model} mode={mode} t={tick} playing={playing} speed={speed} onSeek={seek} onPlay={setPlaying} onSpeed={setSpeed} onLive={hasLive && mode !== 'live' ? goLive : undefined}
            skipQuiet={skipQuiet} onSkipQuiet={setSkipQuiet} skipped={skipped && performance.now() - skipped.at < 2500 ? skipped.ms : null} />
        )}
      </div>
    </div>
  )
}
