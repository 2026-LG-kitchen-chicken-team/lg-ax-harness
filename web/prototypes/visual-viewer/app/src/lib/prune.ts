// The viewer shows only what the planning work needs (AGENTS.md: question and conditions, evidence → pain → existing
// feature → proposal links, citations with locations, save status and rejections, unconfirmed items and limits, and
// the export file). Viewer how-tos, the Skill structure, operating notes, usage that was never measured and pages that
// repeat the story page are left out. build_view.py's data is unchanged (it still has everything).
import type { Block, Page, View } from '../types'

// Pages whose content the story page already shows; anything they hold that the story does not is moved first.
export const PRUNED_PAGES = new Set(['screening', 'compare', 'concepts'])
const startsWith = (b: Block, key: string, prefix: string) => typeof b[key] === 'string' && (b[key] as string).startsWith(prefix)
const has = (b: Block, key: string, part: string) => typeof b[key] === 'string' && (b[key] as string).includes(part)

function dropAfterHeading(blocks: Block[], heading: (b: Block) => boolean, until: (b: Block) => boolean): Block[] {
  const out: Block[] = []
  let skipping = false
  for (const b of blocks) {
    if (heading(b)) { skipping = true; continue }
    if (skipping && until(b)) skipping = false
    if (!skipping) out.push(b)
  }
  return out
}

const isHeading = (b: Block) => b.type === 'heading' || b.type === 'section'

function overview(blocks: Block[]): Block[] {
  let out = blocks.filter((b) => b.type !== 'lead')
  if (out[0]?.type === 'divider') out = out.slice(1)
  out = dropAfterHeading(out, (b) => isHeading(b) && startsWith(b, 'text', '판단 메모'), isHeading)
  out = dropAfterHeading(out, (b) => isHeading(b) && startsWith(b, 'text', '하네스 단계'), (b) => isHeading(b) || b.type === 'expander')
  return out.filter((b) => !(b.type === 'expander' && (startsWith(b, 'title', '이 화면 쓰는 법') || startsWith(b, 'title', '세션 정보'))))
}

function dashboard(blocks: Block[], moved: Block[]): Block[] {
  let out = blocks.filter((b) => !(b.type === 'callout' && has(b, 'text', '의견 묶음 차트')))
  out = out.filter((b) => !(b.type === 'expander' && startsWith(b, 'title', '의견 묶음 차트를 그리려면')))
  out = out.filter((b) => !(b.type === 'chips' && startsWith(b, 'source', 'evidence_refs의 origin')))
  out = dropAfterHeading(out, (b) => b.type === 'section' && startsWith(b, 'text', '불편·기능·제안과 근거'), (b) => isHeading(b) || b.type === 'divider')
  // The claim-by-claim review table (from the 기능 대조 page) goes right under the review judgement charts.
  const at = out.findIndex((b) => b.type === 'callout' && startsWith(b, 'text', '위 판단은'))
  if (moved.length) out.splice(at >= 0 ? at + 1 : out.length, 0, ...moved)
  // Every registered source (web result): the counts stay in view; the list, mostly sources the result does not cite,
  // folds under "원문 N건 보기".
  const all = out.findIndex((b) => b.type === 'section' && startsWith(b, 'text', '등록 원문 전체'))
  const table = all >= 0 ? out.findIndex((b, i) => i > all && b.type === 'table') : -1
  if (table >= 0 && !out.slice(all + 1, table).some(isHeading)) {
    out[table] = { type: 'expander', title: `원문 ${(out[table].rows || []).length}건 보기`, blocks: [out[table]] }
  }
  return out
}

function history(blocks: Block[]): Block[] {
  // Usage notes and charts go; the per-question evidence chart stays only when the session has two or more questions
  // (with one question it is a single dot that repeats the table's 근거 column).
  const chart = blocks.find((b) => b.type === 'line')
  const keepChart = Array.isArray(chart?.x) && chart.x.length >= 2
  let out = dropAfterHeading(blocks, (b) => b.type === 'section' && startsWith(b, 'text', '관측 사용량'), (b) => b.type === 'section')
  if (!keepChart) out = dropAfterHeading(out, (b) => b.type === 'section' && startsWith(b, 'text', 'turn별 등록 근거'), (b) => b.type === 'section')
  return out.filter((b) => !(b.type === 'callout' && (has(b, 'text', '사용량') || has(b, 'text', 'invocations'))))
}

function exportPage(blocks: Block[]): Block[] {
  return dropAfterHeading(blocks, (b) => b.type === 'section' && startsWith(b, 'text', '관측 사용량'), isHeading)
}

// The 기능 대조 page is not shown, so the story's link chart gets its 기존 기능 column (현재 불편 → 기존 기능 → 남은 불편
// → 제안). The review record links pains to remaining pains (feature_matches) and remaining pains to proposals
// (concept_links) by id; it has no pain-to-feature id, so no line is drawn to or from a feature and the note says so.
function withFeatureColumn(blocks: Block[]): Block[] {
  const check = blocks.find((b) => b.type === 'story' && b.key === 'check')
  const features: Block[] = (check?.blocks || []).find((x: Block) => x.type === 'claims')?.items || []
  if (!features.length) return blocks
  return blocks.map((b) => (b.type !== 'story' || b.key !== 'flow' ? b : {
    ...b,
    blocks: (b.blocks || []).map((f: Block) => (f.type !== 'flow' || (f.columns || []).some((c: Block) => c.key === 'feature') ? f : {
      ...f,
      columns: [f.columns[0], { key: 'feature', title: '기존 기능', tone: 'blue' }, ...f.columns.slice(1)],
      nodes: [...(f.nodes || []), ...features.map((it) => ({ id: it.id, column: 'feature', tone: 'blue', text: it.text, summary: it.summary }))],
      note: `${f.note || ''} 기존 기능 칸은 같은 모델에서 대조한 기능입니다. 불편·기능 사이의 연결은 검토 기록에 ID로 적혀 있지 않아 선을 그리지 않습니다.`.trim(),
    })),
  }))
}

function story(blocks: Block[], moved: Block[]): Block[] {
  return withFeatureColumn(blocks).map((b) => {
    if (b.type !== 'story' || b.key !== 'trust') return b
    const inner = (b.blocks || [])
      .filter((x: Block) => !(x.type === 'chips' && startsWith(x, 'title', '판단 메모')))
      .map((x: Block) => (x.type === 'tiles' ? { ...x, items: (x.items || []).filter((t: Block) => !startsWith(t, 'label', '사용량')) } : x))
    // Assumptions and review notes (from the 후기 선별 page) are unconfirmed items; they sit with the limits.
    const callout = inner.findIndex((x: Block) => x.type === 'callout')
    inner.splice(callout >= 0 ? callout : inner.length, 0, ...moved)
    return { ...b, blocks: inner }
  })
}

export function pruneForPlanning(view: View | null): View | null {
  if (!view || !view.pages.some((p) => p.id === 'story')) return view // request-only views keep their own pages
  const page = (id: string) => view.pages.find((p) => p.id === id)
  const toStory = (page('screening')?.blocks || []).filter((b) => b.type === 'expander'
    && (startsWith(b, 'title', '결과 가정') || startsWith(b, 'title', '검토 메모')))
  const toDashboard = (page('compare')?.blocks || []).filter((b) => b.type === 'expander' && startsWith(b, 'title', '주장별 검토 기록'))
  const pages: Page[] = view.pages
    .filter((p) => !PRUNED_PAGES.has(p.id))
    .map((p) => {
      if (p.id === 'story') return { ...p, blocks: story(p.blocks, toStory) }
      if (p.id === 'overview') return { ...p, blocks: overview(p.blocks) }
      if (p.id === 'dashboard') return { ...p, blocks: dashboard(p.blocks, toDashboard) }
      if (p.id === 'history') return { ...p, blocks: history(p.blocks) }
      if (p.id === 'export') return { ...p, blocks: exportPage(p.blocks) }
      return p
    })
  // Captions carry the page number ("06 · 제안: …"); keep them in step with the shorter list.
  const renumbered = pages.map((p, i) => {
    const title = p.caption?.title
    if (!title || !/^\d+\s*·/.test(title)) return p
    return { ...p, caption: { ...p.caption!, title: title.replace(/^\d+/, String(i + 1).padStart(2, '0')) } }
  })
  return { ...view, pages: renumbered, focus: view.focus && PRUNED_PAGES.has(view.focus) ? 'story' : view.focus }
}

// Removed pages open the story page, where their content now is.
export function prunedTarget(id: string | null): string | null {
  return id && PRUNED_PAGES.has(id) ? 'story' : id
}
