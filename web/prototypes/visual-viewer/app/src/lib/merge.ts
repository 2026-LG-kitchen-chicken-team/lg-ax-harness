// The viewer shows the evidence dashboard and the registered evidence text as one page. The data from build_view.py is
// unchanged (it still has both pages); only what the screen draws is re-arranged.
import type { Page, View } from '../types'

export const MERGED_INTO = 'dashboard'
const MERGED_FROM = 'evidence'

// Page ids that no longer exist in the merged view, and the page that now holds them.
export function mergedTarget(id: string | null): string | null {
  return id === MERGED_FROM ? MERGED_INTO : id
}

export function mergeEvidencePages(view: View | null): View | null {
  if (!view) return view
  const dash = view.pages.find((p) => p.id === MERGED_INTO)
  const ev = view.pages.find((p) => p.id === MERGED_FROM)
  if (!dash || !ev) return view
  const fix = (b: Page['blocks'][number]) =>
    typeof b.text === 'string' && b.text.includes("'근거 원문' 화면에")
      ? { ...b, text: b.text.replace("'근거 원문' 화면에", "아래 '근거 원문'에") }
      : b
  const caption = dash.caption
    ? { ...dash.caption, text: [dash.caption.text, ev.caption?.text].filter(Boolean).join(' ') }
    : ev.caption
  const merged: Page = {
    ...dash,
    nav: '근거 대시보드·원문',
    title: '근거 대시보드와 원문',
    caption,
    blocks: [...dash.blocks.map(fix), { type: 'divider' }, { type: 'section', text: '근거 원문' }, ...ev.blocks],
  }
  const pages = view.pages.filter((p) => p.id !== MERGED_FROM).map((p) => (p.id === MERGED_INTO ? merged : p))
  // Captions carry the page number ("08 · 원문: …"); keep them in step with the shorter page list.
  const renumbered = pages.map((p, i) => {
    const title = p.caption?.title
    if (!title || !/^\d+\s*·/.test(title)) return p
    return { ...p, caption: { ...p.caption!, title: title.replace(/^\d+/, String(i + 1).padStart(2, '0')) } }
  })
  return { ...view, pages: renumbered, focus: view.focus === MERGED_FROM ? MERGED_INTO : view.focus }
}
