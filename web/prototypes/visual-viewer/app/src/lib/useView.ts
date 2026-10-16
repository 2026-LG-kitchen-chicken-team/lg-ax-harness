import { useCallback, useEffect, useRef, useState } from 'react'
import { createViewLoader, initialViewState, isLgaxView, type Transport } from './viewState'

export { isLgaxView } from './viewState'
export type LiveState = 'on' | 'off' | 'idle'

// Capture only this script's assignment; a timed-out script cannot supply a later read's payload.
export const scriptTransport: Transport = (done, fail) => {
  const script = document.createElement('script')
  const previous = Object.getOwnPropertyDescriptor(window, 'LGAX_VIEW')
  let value: unknown
  let assigned = false
  Object.defineProperty(window, 'LGAX_VIEW', {
    configurable: true,
    get: () => previous?.value,
    set: next => { if (document.currentScript === script) { value = next; assigned = true } },
  })
  let active = true
  script.src = 'view-data.js?ts=' + Date.now()
  script.charset = 'utf-8'
  script.onload = () => { if (active) done(assigned ? value : undefined) }
  script.onerror = () => { if (active) fail() }
  const cleanup = () => {
    if (!active) return
    active = false
    script.onload = null; script.onerror = null; script.remove()
    if (previous) Object.defineProperty(window, 'LGAX_VIEW', previous)
    else delete window.LGAX_VIEW
  }
  try { document.head.appendChild(script) } catch { cleanup(); throw new Error('viewer read failed') }
  return cleanup
}

export function useView(onToast: (msg: string) => void) {
  const [state, setState] = useState(() => initialViewState(window.LGAX_VIEW))
  const [fromFile, setFromFile] = useState(false)
  const toastRef = useRef(onToast); toastRef.current = onToast
  const loader = useRef<ReturnType<typeof createViewLoader> | null>(null)
  const latest = useRef(state); latest.current = state
  const reader = useRef<FileReader | null>(null)
  const fileGeneration = useRef(0)
  const inline = !!window.LGAX_VIEW_INLINE
  const local = location.protocol === 'file:' || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)
  const canPoll = !inline && local && !fromFile

  useEffect(() => {
    const current = createViewLoader({
      initial: latest.current, transport: scriptTransport, update: setState,
      schedule: (f, ms) => window.setTimeout(f, ms), clear: id => window.clearTimeout(id as number),
      changed: (manual, changed) => {
        if (changed) toastRef.current('화면 자료를 갱신했어요.')
        else if (manual) toastRef.current('최근 저장된 결과예요. 바뀐 내용이 없습니다.')
      },
    })
    loader.current = current
    if (canPoll) current.load()
    const id = canPoll ? window.setInterval(() => current.load(), 2000) : undefined
    return () => { window.clearInterval(id); current.dispose(); loader.current = null }
  }, [canPoll])

  useEffect(() => () => { fileGeneration.current++; reader.current?.abort() }, [])
  const reload = useCallback(() => {
    if (inline) { toastRef.current('저장된 결과가 담긴 보고서예요. 새 결과는 업무 화면에서 확인하세요.'); return }
    fileGeneration.current++; reader.current?.abort()
    if (fromFile) setFromFile(false)
    else loader.current?.load(true)
  }, [inline, fromFile])
  const openFile = useCallback((file: File) => {
    const id = ++fileGeneration.current
    reader.current?.abort()
    const current = new FileReader(); reader.current = current
    const failed = () => {
      if (id === fileGeneration.current) toastRef.current('화면 자료를 열지 못했어요. 올바른 화면 파일을 다시 선택해 주세요. 기존 결과는 그대로 볼 수 있어요.')
    }
    current.onload = () => {
      if (id !== fileGeneration.current) return
      try {
        const value: unknown = JSON.parse(String(current.result))
        if (!isLgaxView(value)) { failed(); return }
        loader.current?.replace(value)
        setFromFile(true)
        toastRef.current('선택한 화면 자료를 열었어요. 자동 갱신을 다시 켜려면 다시 불러오기를 눌러 주세요.')
      } catch { failed() }
    }
    current.onerror = failed
    try { current.readAsText(file, 'utf-8') } catch { failed() }
  }, [])
  const live: LiveState = canPoll ? state.phase === 'error' ? 'off' : state.phase === 'ready' ? 'on' : 'idle' : 'idle'
  return { ...state, live, reload, openFile, inline, fromFile }
}
