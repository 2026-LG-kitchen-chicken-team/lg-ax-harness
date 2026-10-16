import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { NODE } from './lib/catalog'
import { RESULT_VIEW_URL, useLiveFile, useResultView, parseRecordFile } from './lib/data'
import { observationMode, observationNotice } from './lib/readController'
import { demoLive } from './lib/demo'
import { dayClock, mmss, secs, STATUS_KO } from './lib/labels'
import { buildSession, parseTime, quietUntil, sessionsOf } from './lib/model'
import { snapshot } from './lib/state'
import { Office } from './scene/Office'
import { Inspector } from './ui/Inspector'
import { Feed, NowPanel } from './ui/NowPanel'
import { Timeline } from './ui/Timeline'
import { SceneBoundary } from './ui/SceneBoundary'
import type { DbSnapshot, Mode, OfficeEvent } from './types'

interface Source {
  name: string
  events: OfficeEvent[]
  db: DbSnapshot | null
}

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

export function App() {
  const observation = useLiveFile(true)
  const live = observation.value
  const resultRead = useResultView()
  const resultView = resultRead.value
  const [mode, setMode] = useState<Mode>(() => observationMode(HASH.get('mode')))
  const [file, setFile] = useState<Source | null>(null)
  const [fileNote, setFileNote] = useState<string | null>(null)
  const fileSequence = useRef(0)
  const [sceneUnavailable, setSceneUnavailable] = useState(false)
  const onSceneUnavailable = useCallback(() => setSceneUnavailable(true), [])
  const demo = useMemo(() => demoLive(), [])
  const source: Source = useMemo(() => {
    if (mode === 'demo') return { name: '데모', events: demo.events, db: demo.db ?? null }
    if (mode === 'replay' && file) return file
    return { name: '실제 관찰 기록', events: live?.events ?? [], db: live?.db ?? null }
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
  const observationRef = useRef(observation)
  const [tick, setTick] = useState(timeRef.current)
  useEffect(() => { speedRef.current = mode === 'live' ? 1 : speed }, [speed, mode])
  useEffect(() => { playingRef.current = playing }, [playing])
  useEffect(() => { skipRef.current = skipQuiet }, [skipQuiet])
  useEffect(() => { modelRef.current = model }, [model])
  useEffect(() => { modeRef.current = mode }, [mode])
  useEffect(() => { observationRef.current = observation }, [observation])

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
      if (modeRef.current === 'live') {
        const read = observationRef.current
        // A broken display connection is not evidence that AI work stopped or kept running.
        timeRef.current = read.error && read.lastSuccessAt ? read.lastSuccessAt : Date.now()
      }
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
    fileSequence.current += 1
    setFile(null)
    setFileNote(null)
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

  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; fileSequence.current += 1 }
  }, [])
  const openFile = async (f: File) => {
    const request = ++fileSequence.current
    try {
      const parsed = parseRecordFile(await f.text())
      if (!mounted.current || request !== fileSequence.current) return
      if (!parsed.events.length) { setFileNote('이 파일에는 읽을 수 있는 실행 기록이 없습니다. 다른 기록 파일을 선택해 주세요.'); return }
      setFile({ name: f.name, events: parsed.events, db: parsed.live?.db ?? null })
      setFileNote(`저장된 사건 ${parsed.events.length}개를 재생합니다.${parsed.skipped ? ` 읽을 수 없는 항목 ${parsed.skipped}개는 제외했습니다.` : ''}`)
      setPick(null)
      setMode('replay')
    } catch {
      if (mounted.current && request === fileSequence.current) setFileNote('기록 파일을 열지 못했습니다. 파일을 다시 선택해 주세요. 기존 기록은 유지됩니다.')
    }
  }

  const liveLast = live ? lastEventAt(live.events) : null
  const hasLive = !!live?.events.length
  const db = model.dbMatched ? model.db : null
  const turnStatus = db?.turn?.status ?? null
  const empty = !source.events.length
  const staleObservation = mode === 'live' && !!observation.error

  return (
    <div className="app-bg relative h-dvh w-full overflow-hidden">
      <div className="absolute inset-0">
        <SceneBoundary onUnavailable={onSceneUnavailable}><Office model={model} timeRef={timeRef} speedRef={speedRef} selected={selected} onSelect={onSelect} onUnavailable={onSceneUnavailable} /></SceneBoundary>
      </div>

      <div className="pointer-events-none absolute inset-0 flex flex-col gap-2 p-2 sm:p-3">
        <header className="panel pointer-events-auto flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2">
          <div className="mr-1 flex min-w-0 flex-col">
            <h1 className="brand">LG AX 기획 사무실</h1>
            <span className="text-[10.5px] text-[var(--dim)]">메인 Agent 1 · 선택 연구 역할 3 · 업무 Skill 6</span>
          </div>
          <div className="seg" role="tablist" aria-label="보기 방식">
            <button role="tab" aria-selected={mode === 'live'} className={mode === 'live' ? 'on' : ''} onClick={goLive}>실시간</button>
            <button role="tab" aria-selected={mode === 'replay'} className={mode === 'replay' ? 'on' : ''} disabled={!hasLive && !file} onClick={() => setMode('replay')}>기록 재생</button>
            <button role="tab" aria-selected={mode === 'demo'} className={mode === 'demo' ? 'on' : ''} onClick={() => { fileSequence.current += 1; setFileNote(null); setMode('demo') }}>데모</button>
          </div>
          {mode !== 'demo' && sessions.length > 0 && (
            <select className="select" value={sessionId ?? ''} onChange={(e) => { setPick(e.target.value); if (mode === 'live') setMode('replay') }} aria-label="세션 고르기">
              {sessions.map((s, i) => (
                <option key={s.id} value={s.id}>
                  {`${i + 1}. ${s.src === 'codex' ? 'Codex' : 'Claude'} · ${dayClock(s.start)} · ${mmss(s.end - s.start)} · 사건 ${s.count}${s.requests ? ` · 질문 ${s.requests}` : ''}${s.roles.length ? ` · 연구 역할 ${s.roles.length}` : ''}`}
                </option>
              ))}
            </select>
          )}
          <label className="btn cursor-pointer">
            기록 파일 열기
            <input type="file" accept=".jsonl,.json,.js,.txt" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void openFile(f); e.target.value = '' }} />
          </label>
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            {resultView && mode !== 'demo' && (
              <a className="btn btn-result" href={RESULT_VIEW_URL} target="_blank" rel="noopener">{resultRead.error ? '마지막 결과 열기' : '결과 화면 열기'}</a>
            )}
            {turnStatus && <span className={`chip ${turnStatus === 'completed' ? 'chip-ok' : 'chip-warn'}`}>업무 {STATUS_KO[turnStatus] ?? '상태 확인 필요'}</span>}
            {db?.turn && <span className="chip">수정 {db.turn.revision_count ?? '미측정'}/2</span>}
            {snap.workflow && <span className="chip">업무 시계 {mmss(snap.workflow.elapsed)}{snap.workflow.budget ? ` / ${mmss(snap.workflow.budget)}` : ''}</span>}
            {mode === 'live' && <span className={`chip ${staleObservation ? 'chip-warn' : 'chip-live'}`}><span className="live-dot" />{liveLast ? `마지막 실제 사건 ${secs(Date.now() - liveLast)} 전` : '실제 사건 대기'}</span>}
            {mode === 'live' && observation.lastSuccessAt && <span className="chip">화면 읽기 성공 {secs(Date.now() - observation.lastSuccessAt)} 전</span>}
            {mode !== 'live' && file && <span className="chip" title={fileNote ?? ''}>{file.name}</span>}
            {mode !== 'live' && !file && mode === 'replay' && <span className="chip hidden sm:inline-flex">저장된 실제 사건 {source.events.length}개</span>}
          </div>
        </header>

        {mode === 'live' && (
          <div className={`panel pointer-events-auto flex flex-wrap items-center gap-2 px-3 py-2 text-[12px] ${staleObservation ? 'tone-warn' : ''}`} role="status" aria-live="polite">
            <span className="flex-1">{observationNotice(observation, hasLive)}</span>
            <button className="btn btn-sm" disabled={observation.status === 'reading'} onClick={() => observation.retry()}>{observation.status === 'reading' ? '확인 중' : '기록 다시 확인'}</button>
          </div>
        )}
        {mode !== 'demo' && resultRead.error && (
          <div className="panel pointer-events-auto px-3 py-2 text-[12px] tone-warn" role="status">
            {resultView ? '결과 화면 갱신을 확인하지 못해 마지막 결과 링크를 유지합니다. AI 업무의 성공·실패와는 별개입니다.' : '아직 저장된 결과를 확인하지 못했습니다. AI 대화의 저장·최종 응답을 확인해 주세요. 결과가 준비되면 자동으로 표시합니다.'}
            <button className="btn btn-sm ml-2" disabled={resultRead.status === 'reading'} onClick={() => resultRead.retry()}>결과 다시 확인</button>
          </div>
        )}
        {sceneUnavailable && <div className="panel pointer-events-auto px-3 py-2 text-[12px]" role="status">입체 화면 대신 진행 목록과 실행 기록으로 작업을 확인할 수 있습니다.</div>}

        {mode === 'demo' && (
          <div className="demo-banner pointer-events-auto">
            <b>데모 화면</b> · 가상 기록으로 움직임만 보여 줍니다. 실제 하네스가 한 일이 아닙니다 (사이트 이름도 *.example).
            <button className="btn btn-sm ml-2" onClick={goLive}>실제 기록 보기</button>
          </div>
        )}
        {fileNote && <div className="note pointer-events-auto" role="status">{fileNote}</div>}

        <div className="flex min-h-0 flex-1 gap-2">
          <div className={`${sceneUnavailable ? selected ? 'hidden w-[300px] sm:flex' : 'flex min-w-0 w-full sm:w-[300px]' : 'hidden w-[300px] lg:flex'} shrink-0 flex-col gap-2`}>
            <div className="min-h-0 flex-1"><NowPanel snap={snap} selected={selected} onSelect={onSelect} stale={staleObservation} /></div>
            <Feed snap={snap} onSelect={onSelect} />
          </div>
          <div className="min-w-0 flex-1" />
          {selected ? (
            <div className="flex w-full max-w-[380px] shrink-0 sm:w-[380px]">
              <Inspector id={selected} model={model} snap={snap} resultView={mode === 'demo' ? null : resultView} stale={staleObservation} onClose={() => setSelected(null)} />
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
            <b>{mode === 'replay' ? '재생할 실제 기록을 기다립니다.' : '실제 실행 기록을 기다립니다.'}</b>
            <span>선택한 Codex 또는 Claude Code 대화에서 질문을 입력해 주세요. 실시간 보기에서는 기록이 도착하면 자동으로 표시합니다. 계속 표시되지 않으면 사용설명서의 관찰 재연결 안내를 확인해 주세요.</span>
            <div><button className="btn" onClick={() => { fileSequence.current += 1; setFileNote(null); setMode('demo') }}>데모 보기</button></div>
          </div>
        ) : (
          <Timeline model={model} mode={mode} t={tick} playing={playing} speed={speed} onSeek={seek} onPlay={setPlaying} onSpeed={setSpeed} onLive={hasLive && mode !== 'live' ? goLive : undefined}
            skipQuiet={skipQuiet} onSkipQuiet={setSkipQuiet} skipped={skipped && performance.now() - skipped.at < 2500 ? skipped.ms : null} />
        )}
      </div>
    </div>
  )
}
