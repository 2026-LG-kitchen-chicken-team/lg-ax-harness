// Passive file reads only. A failed read never clears the last valid observation or starts AI work.
import type { Mode } from '../types'

export type ReadError = 'unavailable' | 'invalid' | 'timeout'
export interface ReadSnapshot<T> {
  value: T | null
  status: 'waiting' | 'reading' | 'ready' | 'error'
  lastSuccessAt: number | null
  lastAttemptAt: number | null
  error: ReadError | null
}
export interface Loaded<T> { value: T; identity: string }
export type Transport<T> = (ok: (data: Loaded<T>) => void, fail: (error: ReadError) => void) => (() => void)
export interface Scheduler {
  now: () => number
  set: (callback: () => void, delay: number) => unknown
  clear: (timer: unknown) => void
}
export const browserScheduler: Scheduler = {
  now: () => Date.now(),
  set: (callback, delay) => setTimeout(callback, delay),
  clear: (timer) => clearTimeout(timer as ReturnType<typeof setTimeout>),
}
export function initialRead<T>(value: T | null = null, now = Date.now()): ReadSnapshot<T> {
  return { value, status: value ? 'ready' : 'waiting', lastSuccessAt: value ? now : null, lastAttemptAt: null, error: null }
}

export function createReadController<T>(options: {
  transport: Transport<T>; interval: number; timeout?: number; scheduler?: Scheduler
  initial?: ReadSnapshot<T>; identity?: string; onState: (state: ReadSnapshot<T>) => void
}) {
  const clock = options.scheduler ?? browserScheduler
  let state = options.initial ?? initialRead<T>()
  let identity = options.identity ?? null
  let stopped = true
  let next: unknown = null
  let active: { cancel: () => void; timer: unknown } | null = null
  const emit = (patch: Partial<ReadSnapshot<T>>) => {
    state = { ...state, ...patch }
    if (!stopped) options.onState(state)
  }
  const clearNext = () => { if (next != null) clock.clear(next); next = null }
  const refresh = (): boolean => {
    if (stopped || active) return false // manual refresh and polling share one in-flight read
    clearNext()
    const request = { cancel: () => {}, timer: null as unknown }
    active = request
    emit({ status: 'reading', lastAttemptAt: clock.now() })
    const finish = (data: Loaded<T> | null, error: ReadError | null) => {
      if (stopped || active !== request) return // timed-out, superseded or unmounted callbacks
      active = null
      if (request.timer != null) clock.clear(request.timer)
      request.cancel()
      if (data) {
        const value = data.identity === identity && state.value ? state.value : data.value
        identity = data.identity
        emit({ value, status: 'ready', lastSuccessAt: clock.now(), error: null })
      } else emit({ status: 'error', error: error ?? 'unavailable' })
      if (!stopped && !active) next = clock.set(refresh, options.interval)
    }
    request.timer = clock.set(() => finish(null, 'timeout'), options.timeout ?? 5000)
    try {
      const cancel = options.transport((data) => finish(data, null), (error) => finish(null, error))
      if (active === request) request.cancel = cancel
      else cancel() // synchronous transport completion also gets cleaned up
    } catch { finish(null, 'unavailable') }
    return true
  }
  return {
    start() { if (!stopped) return; stopped = false; refresh() },
    refresh,
    stop() {
      stopped = true; clearNext()
      const request = active; active = null
      if (request) { if (request.timer != null) clock.clear(request.timer); request.cancel() }
    },
    getState: () => state,
  }
}

export function observationMode(requested: string | null): Mode {
  return requested === 'demo' || requested === 'replay' ? requested : 'live'
}
export function observationNotice<T>(read: ReadSnapshot<T>, hasEvents: boolean): string {
  if (read.error) return read.value
    ? '관찰 화면 갱신이 지연돼 마지막으로 확인한 기록을 보여줍니다. AI 업무 실패를 뜻하지 않습니다. 자동으로 다시 확인합니다.'
    : '실행 기록을 아직 읽지 못했습니다. AI 대화에서 작업과 권한 요청을 확인해 주세요. 자동으로 다시 확인합니다.'
  if (!hasEvents) return '실제 실행 기록을 기다립니다. Codex 또는 Claude Code에서 질문하면 기록이 도착하는 대로 표시합니다.'
  return '실제 기록을 표시합니다. 화면을 읽은 시각과 AI에서 마지막 사건이 발생한 시각은 서로 다릅니다.'
}
