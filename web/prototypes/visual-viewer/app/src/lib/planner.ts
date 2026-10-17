// A display projection only. The saved export, report source, all source bodies and
// claim text stay intact. Page/block keys describe the schema, never a product or question.
import type { Block, Page, View } from '../types'

export function plannerFirst(view: View | null): View | null {
  if (!view) return view
  const story = view.pages.find(p => p.id === 'story')
  if (!story) return { ...view, pages: view.pages.map(p => ({ ...p, audience: 'planning' })) }
  const sections = story.blocks.filter(b => b.type === 'story')
  const flow = sections.find(b => b.key === 'flow')
  const solution = sections.find(b => b.key === 'solution')
  const trust = sections.find(b => b.key === 'trust')
  const conditions = (trust?.blocks || []).filter((b: Block) => b.type === 'expander' && String(b.title || '').startsWith('결과 가정'))
  const overview = view.pages.find(p => p.id === 'overview')
  const header = story.blocks.find(b => b.type === 'hero')
  // Keep business failures/stale warnings in place. Only the raw request cover and
  // its diagnostic chips/counts are replaced; the full request remains in overview.
  const main: Block[] = story.blocks.filter(b => b.type !== 'story' && b.type !== 'hero')
  if (header) main.unshift({ type: 'hero', planner: true,
    title: overview?.title || '상품기획안', scope: header.scope })
  if (solution) main.push({ ...solution, planner: true, label: '제안', title: '검토할 상품기획', text: undefined,
    blocks: (solution.blocks || []).map((b: Block) => b.type === 'solutions' ? { ...b, planner: true,
      items: (b.items || []).map((s: Block) => ({ ...s,
        background: (flow?.blocks || []).flatMap((f: Block) => f.type === 'flow' ? f.nodes || [] : [])
          .filter((n: Block) => n.column === 'remaining' && (s.links || []).some((l: Block) => l.text === n.id))
          .map((n: Block) => n.summary || n.text) })) } : b) })
  if (flow) main.push({ type: 'expander', title: '기획 배경 · 불편과 기존 기능 비교',
    blocks: (flow.blocks || []).map((b: Block) => b.type === 'flow' ? { ...b, note: undefined } : b) })
  if (conditions.length) main.push({ type: 'expander', title: '전체 기획의 조사 범위와 적용 조건', blocks: conditions.flatMap((b: Block) => b.blocks || []) })
  const detail = sections.filter(b => b.key !== 'flow' && b.key !== 'solution' && b.key !== 'trust')
  const audit = trust ? [{ ...trust, blocks: (trust.blocks || []).filter((b: Block) => !conditions.includes(b)) }] : []
  const pages: Page[] = view.pages.map((p): Page => p.id === 'story'
    ? { ...p, title: '상품기획', nav: '상품기획', audience: 'planning', caption: null, blocks: main }
    : { ...p, audience: p.id === 'history' || p.id === 'export' ? 'diagnostic' : 'evidence' })
  if (detail.length) pages.push({ id: 'planning-detail', title: '문제·기능 상세 비교', nav: '상세 비교', audience: 'evidence', blocks: detail })
  if (audit.length || view.context) pages.push({ id: 'review-diagnostics', title: '검토·진단 기록', nav: '검토·진단 기록', audience: 'diagnostic', blocks: [...audit,
    { type: 'chips', title: '저장 원본 상태', items: view.context?.status || [] },
    ...(view.context?.meta ? [{ type: 'callout', text: view.context.meta }] : [])] })
  // Developer metadata is preserved in the input/export and diagnostic page, not
  // repeated on every planner screen. Never mutate the saved source object.
  return { ...view, app: { ...view.app, subtitle: '고객 근거로 만드는 상품기획' },
    context: { status: (view.context?.status || []).slice(0, 1).map(({ text, tone }) => ({ text, tone })) }, pages }
}
