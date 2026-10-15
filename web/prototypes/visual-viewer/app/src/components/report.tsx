// "보고서로 보기": 신진하's report page (vendor/jinha-report, put together in vite.config.ts) over the whole screen,
// fed with the export build_view.py put in view-data.js and the turn K shows, so both show the same result.
// It runs in a sandboxed iframe without same-origin rights: its own styles and scripts cannot touch K, and text from
// the export cannot reach K's page or files. Printing, the PDF and "보고서 파일 저장" work from the report's own buttons.
import { useEffect, useMemo } from 'react'
import { ArrowLeft } from 'lucide-react'
import template from 'virtual:jinha-report'
import type { ReportSource } from '../types'

const SLOT = '<script id="embedded-report" type="application/json">null</script>'
// The report's own rule for JSON inside a script tag (report-app.js safeJSON).
const safeJSON = (v: unknown) => JSON.stringify(v).replace(/[<>&\u2028\u2029]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'))
const attr = (s: string) => s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string))

export function reportHtml(r: ReportSource): string {
  const data = `<script id="embedded-report" type="application/json" data-turn-id="${attr(r.turn_id || '')}">${safeJSON(r.export)}</script>`
  return template.replace(SLOT, () => data)
}

export function ReportView({ source, close }: { source: ReportSource; close: () => void }) {
  const html = useMemo(() => reportHtml(source), [source])
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
        <span className="ml-auto hidden truncate text-zinc-500 md:inline">보고서 양식: 신진하 · 인쇄·PDF는 보고서 위쪽 버튼</span>
      </div>
      <iframe title="결과 보고서" srcDoc={html} className="min-h-0 w-full flex-1 border-0 bg-white"
        sandbox="allow-scripts allow-modals allow-downloads allow-popups allow-popups-to-escape-sandbox" />
    </div>
  )
}
