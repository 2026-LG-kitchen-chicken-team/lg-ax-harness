// Vite plugin for vite.config.ts. Plain Node (like publish.mjs) so the app's type check needs no Node types.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { plannerReport } from './planner-report.mjs'

// "보고서로 보기": 신진하's report (../vendor/jinha-report, kept byte for byte; see SOURCE.md) as one HTML string. The
// stylesheets and scripts go inline (the viewer is one file), the host's Cloudflare snippet and the canonical link (an
// outside address) are dropped, and buttons that make no sense inside the viewer are hidden. Every step must match
// exactly once, so a new version of the report that changes these spots fails the build instead of shipping half-done.
/** @returns {import('vite').Plugin} */
export function jinhaReport() {
  const id = 'virtual:jinha-report'
  const dir = fileURLToPath(new URL('../vendor/jinha-report/', import.meta.url))
  return {
    name: 'jinha-report',
    resolveId: (source) => (source === id ? '\0' + id : undefined),
    load(resolved) {
      if (resolved !== '\0' + id) return
      const read = (name) => { this.addWatchFile(dir + name); return readFileSync(dir + name, 'utf8') }
      const once = (html, find, to, what) => {
        const n = typeof find === 'string' ? html.split(find).length - 1 : (html.match(new RegExp(find, 'g')) || []).length
        if (n !== 1) throw new Error(`jinha-report: ${what} found ${n} times (expected 1)`)
        return html.replace(find, () => to)
      }
      let code = { adapter: read('report-data-adapter.js'), app: read('report-app.js') }
      // The iframe load event only means the document loaded. Report actual
      // embedded-result rendering separately, without leaking internal errors.
      // Keep upstream vendor files byte-identical; fail closed on a changed hook.
      code.app = once(code.app, 'const notice=(message,error=false)=>{',
        `const reportState=type=>{if(window.parent!==window)window.parent.postMessage({type,turn_id:document.getElementById('embedded-report')?.getAttribute('data-turn-id')||null,instance:document.getElementById('embedded-report')?.getAttribute('data-report-instance')||null},'*');};
const notice=(message,error=false)=>{if(error){reportState('lgax-report-error');message='보고서를 표시하지 못했어요. 업무 화면에서 다시 열어주세요.';}`,
        'report status notice')
      code.app = once(code.app, 'restoreTraceSelection();',
        "restoreTraceSelection();reportState('lgax-report-ready');", 'embedded render completion')
      let css = read('styles.css') + '\n' + read('result-report.css')
      let html = read('index.html')
      this.addWatchFile(fileURLToPath(new URL('./planner-report.mjs', import.meta.url)))
      ;({ code, html, css } = plannerReport({ code, html, css, once }))
      for (const [name, text] of Object.entries({ ...code, css })) {
        if (/<\/(script|style)/i.test(text)) throw new Error(`jinha-report: ${name} contains a closing script/style tag`)
      }
      const hide = '#import-report,#copy-link,#show-sample,.connection-help{display:none!important}'
      html = once(html, /<link rel="canonical" href="[^"]*">/, '', 'canonical link')
      html = once(html, '<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="result-report.css">', `<style>\n${css}\n${hide}\n</style>`, 'stylesheets')
      html = once(html, '<script src="report-data-adapter.js"></script><script src="report-app.js"></script>', `<script>\n${code.adapter}\n</script><script>\n${code.app}\n</script>`, 'scripts')
      html = once(html, /<script>\(function\(\)\{function c\(\)\{[^]*?<\/script>/, '', 'Cloudflare snippet')
      once(html, '<script id="embedded-report" type="application/json">null</script>', '', 'data slot')
      // The report's own code keeps its site address for the hidden "페이지 링크 복사" button; nothing else may point out.
      if (/https?:\/\/(?!www\.w3\.org\/)/.test(html.replace(code.app, ''))) throw new Error('jinha-report: an outside address is left in the page')
      return `export default ${JSON.stringify(html)}`
    },
  }
}
