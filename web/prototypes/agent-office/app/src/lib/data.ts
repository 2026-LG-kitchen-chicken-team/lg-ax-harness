// Loading the observer's records: live.js next to the page (re-read every second), or an events.jsonl / live.js file
// the user opens. Nothing is sent anywhere; the page only reads.
import { useCallback, useEffect, useRef, useState } from 'react'
import type { LiveFile, OfficeEvent, ResultView } from '../types'
import { createReadController, initialRead, type Loaded, type ReadSnapshot, type Scheduler, type Transport } from './readController'

const POLL_MS = 1000

export function validLiveFile(v: unknown): LiveFile | null {
  const value = v as LiveFile
  return value && value.kind === 'lgax-agent-office-live' && Array.isArray(value.events) && value.events.every(isEvent) ? value : null
}

// Injected scheduling/transport is for no-browser tests; the default only reads the existing local file.
export function usePassiveRead<T>(enabled: boolean, seed: T | null, transport: Transport<T>, interval: number, scheduler?: Scheduler) {
  const [read, setRead] = useState<ReadSnapshot<T>>(() => initialRead(seed, scheduler?.now()))
  const current = useRef(read)
  current.current = read
  const control = useRef<ReturnType<typeof createReadController<T>> | null>(null)
  useEffect(() => {
    if (!enabled) return
    const controller = createReadController({ transport, interval, scheduler, initial: current.current, onState: setRead })
    control.current = controller
    controller.start()
    return () => { controller.stop(); if (control.current === controller) control.current = null }
  }, [enabled, transport, interval, scheduler])
  const retry = useCallback(() => control.current?.refresh(), [])
  return { ...read, retry }
}

export const RESULT_VIEW_URL = '../visual-viewer/index.html'

export function resultMetadata(raw: unknown): ResultView | null {
  const v = raw as { kind?: string; generated_at?: string; result_identity?: string; context?: ResultView['context']; pages?: unknown[] }
  if (!v || v.kind !== 'lgax-view' || !Array.isArray(v.pages) || !v.pages.length) return null
  const name = v.context?.file?.name
  const statuses = Array.isArray(v.context?.status) ? v.context.status.filter((s) => s && typeof s.text === 'string') : []
  return { kind: v.kind, generated_at: typeof v.generated_at === 'string' ? v.generated_at : undefined,
    result_identity: typeof v.result_identity === 'string' ? v.result_identity : undefined,
    context: { file: typeof name === 'string' ? { name } : undefined,
      status: statuses.map((s) => ({ text: s.text, tone: typeof s.tone === 'string' ? s.tone : undefined })) } }
}

export function loadedValue<T>(raw: unknown, validate: (raw: unknown) => T | null): Loaded<T> | null {
  const value = validate(raw)
  if (!value) return null
  const identity = JSON.stringify(raw)
  return identity ? { value, identity } : null
}

function scriptTransport<T>(url: string, read: () => unknown, reset: () => void, validate: (raw: unknown) => T | null): Transport<T> {
  return (ok, fail) => {
    let active = true
    const tag = document.createElement('script')
    tag.src = `${url}?ts=${Date.now()}`; tag.charset = 'utf-8'
    reset() // a load that did not assign data must not reuse an old global as a successful read
    tag.onload = () => {
      if (!active) return
      try {
        const raw = read(); reset()
        // Exact content, including result binding/version/status. No timestamp/length collisions.
        const value = loadedValue(raw, validate)
        if (!value) { fail('invalid'); return }
        ok(value)
      } catch { fail('invalid') }
    }
    tag.onerror = () => { if (active) fail('unavailable') }
    document.head.appendChild(tag)
    return () => { active = false; tag.onload = null; tag.onerror = null; tag.remove() }
  }
}
const liveTransport = scriptTransport('live.js', () => window.LGAX_OFFICE_LIVE, () => { window.LGAX_OFFICE_LIVE = undefined }, validLiveFile)
const resultTransport = scriptTransport('../visual-viewer/view-data.js', () => window.LGAX_VIEW, () => { window.LGAX_VIEW = undefined }, resultMetadata)
interface ReadEnvironment<T> { transport?: Transport<T>; scheduler?: Scheduler }
export function useLiveFile(enabled: boolean, environment?: ReadEnvironment<LiveFile>) {
  return usePassiveRead(enabled, validLiveFile(window.LGAX_OFFICE_LIVE), environment?.transport ?? liveTransport, POLL_MS, environment?.scheduler)
}
export function useResultView(environment?: ReadEnvironment<ResultView>) {
  return usePassiveRead(true, null, environment?.transport ?? resultTransport, 4000, environment?.scheduler)
}

function isEvent(v: unknown): v is OfficeEvent {
  const e = v as OfficeEvent
  return !!e && typeof e === 'object' && typeof e.ts === 'string' && typeof e.kind === 'string' && typeof e.hook === 'string'
}

// events.jsonl (one event per line) or live.js / snapshot-like JSON. Returns the events and, for live.js, its db.
export function parseRecordFile(text: string): { events: OfficeEvent[]; live: LiveFile | null; skipped: number } {
  const trimmed = text.replace(/^﻿/, '').trim()
  const braceAt = trimmed.indexOf('{')
  if (/^\/\*|^window\.|^\{\s*"kind"\s*:\s*"lgax-agent-office-live"/.test(trimmed) && braceAt >= 0) {
    try {
      const obj = JSON.parse(trimmed.slice(braceAt, trimmed.lastIndexOf('}') + 1)) as LiveFile
      if (obj.kind === 'lgax-agent-office-live' && Array.isArray(obj.events)) {
        const events = obj.events.filter(isEvent)
        return { events, live: obj, skipped: obj.events.length - events.length }
      }
    } catch {
      /* fall through to line parsing */
    }
  }
  const events: OfficeEvent[] = []
  let skipped = 0
  for (const line of trimmed.split(/\r?\n/)) {
    if (!line.trim()) continue
    try {
      const v = JSON.parse(line)
      if (isEvent(v)) events.push(v)
      else skipped += 1
    } catch {
      skipped += 1
    }
  }
  return { events, live: null, skipped }
}
