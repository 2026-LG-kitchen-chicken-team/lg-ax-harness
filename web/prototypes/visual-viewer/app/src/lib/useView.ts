import { useCallback, useEffect, useRef, useState } from 'react'
import type { View } from '../types'

// Live reload: when opened as a local file (or localhost), re-read view-data.js every 2 s.
// Refresh only reads the file the hook wrote; it never runs a model or a harness step.
const isLocal = typeof location !== 'undefined' &&
  (location.protocol === 'file:' || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname))

const signature = (v: View) => {
  try { return (v.generated_at || '') + ':' + JSON.stringify(v).length } catch { return String(Math.random()) }
}

export const isLgaxView = (v: unknown): v is View =>
  !!v && typeof v === 'object' && (v as View).kind === 'lgax-view' && Array.isArray((v as View).pages)

export type LiveState = 'on' | 'off' | 'idle'

export function useView(onToast: (msg: string) => void) {
  const [view, setView] = useState<View | null>(() => (isLgaxView(window.LGAX_VIEW) ? window.LGAX_VIEW! : null))
  const [live, setLive] = useState<LiveState>('idle')
  const [fromFile, setFromFile] = useState(false)
  const sig = useRef(view ? signature(view) : '')
  const toastRef = useRef(onToast)
  toastRef.current = onToast

  const poll = useCallback((manual: boolean) => {
    const s = document.createElement('script')
    s.src = 'view-data.js?ts=' + Date.now()
    s.charset = 'utf-8'
    s.onload = () => {
      s.remove()
      setLive('on')
      const v = window.LGAX_VIEW
      if (isLgaxView(v) && signature(v) !== sig.current) {
        sig.current = signature(v)
        setView(v)
        if (!manual) toastRef.current('새 시각자료를 반영했습니다')
      } else if (manual) {
        toastRef.current('바뀐 내용이 없습니다')
      }
    }
    s.onerror = () => { s.remove(); setLive('off'); if (manual) toastRef.current('view-data.js를 읽지 못했습니다') }
    document.head.appendChild(s)
  }, [])

  const canPoll = !window.LGAX_VIEW_INLINE && isLocal && !fromFile
  useEffect(() => {
    if (!canPoll) return
    setLive('on')
    const id = window.setInterval(() => poll(false), 2000)
    return () => window.clearInterval(id)
  }, [canPoll, poll])

  const reload = useCallback(() => {
    if (window.LGAX_VIEW_INLINE) { toastRef.current('이 파일은 데이터가 들어 있는 단일 보고서입니다'); return }
    setFromFile(false)
    poll(true)
  }, [poll])

  const openFile = useCallback((f: File) => {
    const r = new FileReader()
    r.onload = () => {
      try {
        const v = JSON.parse(String(r.result))
        if (isLgaxView(v)) {
          sig.current = signature(v)
          setView(v)
          setFromFile(true)
          setLive('idle')
          toastRef.current(f.name + ' 파일을 열었습니다 (자동 갱신 멈춤)')
        } else if (v && v.turns && v.requests) {
          toastRef.current('export 원본입니다. build_view.py로 화면 데이터로 바꾼 뒤 여세요.')
        } else {
          toastRef.current('lgax-view 형식의 JSON이 아닙니다.')
        }
      } catch (err) {
        toastRef.current('JSON을 읽지 못했습니다: ' + (err as Error).message)
      }
    }
    r.readAsText(f, 'utf-8')
  }, [])

  return { view, live: canPoll ? live : 'idle' as LiveState, reload, openFile, inline: !!window.LGAX_VIEW_INLINE }
}
