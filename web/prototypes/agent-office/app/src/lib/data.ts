// Loading the observer's records: live.js next to the page (re-read every second), or an events.jsonl / live.js file
// the user opens. Nothing is sent anywhere; the page only reads.
import { useEffect, useState } from 'react'
import type { LiveFile, OfficeEvent, ResultView } from '../types'

const POLL_MS = 1000

function readGlobal(): LiveFile | null {
  const v = window.LGAX_OFFICE_LIVE
  return v && v.kind === 'lgax-agent-office-live' && Array.isArray(v.events) ? v : null
}

// Re-adding the script tag (with a cache-busting query) re-reads live.js on file:// and http:// alike.
export function useLiveFile(enabled: boolean): { live: LiveFile | null; checkedAt: number | null } {
  const [live, setLive] = useState<LiveFile | null>(() => readGlobal())
  const [checkedAt, setCheckedAt] = useState<number | null>(() => (readGlobal() ? Date.now() : null))
  useEffect(() => {
    if (!enabled) return
    let stopped = false
    let tag: HTMLScriptElement | null = null
    const tick = () => {
      if (stopped) return
      tag?.remove()
      tag = document.createElement('script')
      tag.src = `live.js?ts=${Date.now()}`
      tag.charset = 'utf-8'
      tag.onload = () => {
        const v = readGlobal()
        setCheckedAt(Date.now())
        if (v) setLive((old) => (old && old.written_at === v.written_at && old.events.length === v.events.length ? old : v))
      }
      tag.onerror = () => setCheckedAt(Date.now())
      document.head.appendChild(tag)
    }
    const id = window.setInterval(tick, POLL_MS)
    return () => {
      stopped = true
      window.clearInterval(id)
      tag?.remove()
    }
  }, [enabled])
  return { live, checkedAt }
}

export const RESULT_VIEW_URL = '../visual-viewer/index.html'

// The result viewer writes runtime-data/visual-viewer/view-data.js (window.LGAX_VIEW) beside this folder. Re-read
// every few seconds; null when it is not there (viewer not installed or no export yet).
export function useResultView(): ResultView | null {
  const [view, setView] = useState<ResultView | null>(null)
  useEffect(() => {
    let stopped = false
    let tag: HTMLScriptElement | null = null
    const tick = () => {
      if (stopped) return
      tag?.remove()
      tag = document.createElement('script')
      tag.src = `../visual-viewer/view-data.js?ts=${Date.now()}`
      tag.charset = 'utf-8'
      tag.onload = () => {
        const v = window.LGAX_VIEW
        window.LGAX_VIEW = undefined // keep only the few fields below, not the whole result
        const next = v && v.kind === 'lgax-view' ? { kind: v.kind, generated_at: v.generated_at, context: { file: v.context?.file, status: v.context?.status } } : null
        setView((old) => (old?.generated_at === next?.generated_at && old?.context?.file?.name === next?.context?.file?.name ? old : next))
      }
      tag.onerror = () => setView(null)
      document.head.appendChild(tag)
    }
    tick()
    const id = window.setInterval(tick, 4000)
    return () => {
      stopped = true
      window.clearInterval(id)
      tag?.remove()
    }
  }, [])
  return view
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
