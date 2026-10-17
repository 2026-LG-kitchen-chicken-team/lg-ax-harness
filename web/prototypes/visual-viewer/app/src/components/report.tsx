// "보고서로 보기": 신진하's report page (vendor/jinha-report, put together in vite.config.ts) over the whole screen,
// fed with the export build_view.py put in view-data.js and the turn K shows, so both show the same result.
// It runs in a sandboxed iframe without same-origin rights: its own styles and scripts cannot touch K, and text from
// the export cannot reach K's page or files. Printing, the PDF and "보고서 파일 저장" work from the report's own buttons.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import template from 'virtual:jinha-report'
import type { ReportSource } from '../types'

const SLOT = '<script id="embedded-report" type="application/json">null</script>'
// The report's own rule for JSON inside a script tag (report-app.js safeJSON).
const safeJSON = (v: unknown) => JSON.stringify(v).replace(/[<>&\u2028\u2029]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'))
const attr = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string))

export function reportHtml(r: ReportSource, instance = ''): string {
  // With build_view.py's charts the report gets its combined input {export, report_plan}; the plan is tied to the same turn.
  const payload = r.plan ? { export: r.export, report_plan: r.plan, report_plan_turn_id: r.turn_id || undefined } : r.export
  const data = `<script id="embedded-report" type="application/json" data-turn-id="${attr(r.turn_id || '')}" data-report-instance="${attr(instance)}">${safeJSON(payload)}</script>`
  return template.replace(SLOT, () => data)
}

export function ReportView({ source, close, outdated = false, latest }: {
  source: ReportSource; close: () => void; outdated?: boolean; latest?: () => void
}) {
  const [frame, setFrame] = useState<'loading' | 'ready' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  const iframe = useRef<HTMLIFrameElement | null>(null)
  const instance = useMemo(() => typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : Date.now() + '-' + Math.random(), [source, attempt])
  const activeInstance = useRef(instance); activeInstance.current = instance
  const html = useMemo(() => reportHtml(source, instance), [source, instance])
  useLayoutEffect(() => {
    activeInstance.current = instance
    setFrame('loading')
    const timer = window.setTimeout(() => { if (activeInstance.current === instance) setFrame(value => value === 'loading' ? 'error' : value) }, 10000)
    const onMessage = (event: MessageEvent) => {
      const data = event.data
      if (activeInstance.current !== instance || !iframe.current || event.source !== iframe.current.contentWindow || !data || typeof data !== 'object'
        || data.turn_id !== source.turn_id || data.instance !== instance) return
      if (data.type === 'lgax-report-ready') { window.clearTimeout(timer); setFrame('ready') }
      // The vendor also reports save/selection errors after rendering. Its notice handles those;
      // keep the already displayed report and do not describe an operation failure as a failed initial render.
      else if (data.type === 'lgax-report-error') { window.clearTimeout(timer); setFrame(value => value === 'ready' ? value : 'error') }
    }
    window.addEventListener('message', onMessage)
    return () => { activeInstance.current = ''; window.clearTimeout(timer); window.removeEventListener('message', onMessage) }
  }, [source.turn_id, instance])
  useEffect(() => {
    const was = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', onKey)
    return () => { document.body.style.overflow = was; window.removeEventListener('keydown', onKey) }
  }, [close])
  return (
    <div className="no-print fixed inset-0 z-[90] flex flex-col bg-white" role="dialog" aria-modal="true" aria-label="보고서로 보기">
      <div className="flex h-11 shrink-0 items-center gap-3 border-b border-[#e6e6e6] bg-[#fafafa] px-3 text-[13px] sm:px-4">
        <button type="button" onClick={close} autoFocus
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[#e3e3e3] bg-white px-2.5 font-medium text-zinc-700 hover:border-[#2f8f57]/40 hover:bg-[#f3f8f4] hover:text-[#2f7d4f]">
          <ArrowLeft className="size-4" aria-hidden />업무 화면으로
        </button>
        <span className="truncate font-medium text-[#2f8f57]">보고서로 보기</span>
      </div>
      {outdated && <div role="status" className="flex flex-wrap items-center gap-3 border-b border-[#e3e3e3] bg-[#f3f8f4] px-4 py-3 text-sm">
        <span>새 기획이 저장됐어요. 지금 보고 있는 보고서는 이전 저장 결과예요.</span>
        <button type="button" onClick={latest || close} className="font-medium text-[#2f7d4f] underline">{latest ? '최신 보고서 보기' : '업무 화면에서 새 결과 보기'}</button>
      </div>}
      {frame !== 'ready' && <div role="status" className="flex flex-wrap items-center gap-3 border-b border-[#e3e3e3] px-4 py-3 text-sm text-zinc-600">
        <span>{frame === 'loading' ? '보고서를 준비하고 있어요. 잠시만 기다려 주세요.' : '보고서를 표시하지 못했어요. 다시 열거나 업무 화면에서 결과를 확인해 주세요.'}</span>
        {frame === 'error' && <button type="button" onClick={() => setAttempt(value => value + 1)} className="font-medium text-[#2f7d4f] underline">보고서 다시 열기</button>}
      </div>}
      <iframe ref={iframe} key={instance} title="결과 보고서" srcDoc={html}
        onError={() => { if (activeInstance.current === instance) setFrame('error') }}
        aria-busy={frame === 'loading'} className="min-h-0 w-full flex-1 border-0 bg-white"
        sandbox="allow-scripts allow-modals allow-downloads allow-popups allow-popups-to-escape-sandbox" />
    </div>
  )
}
