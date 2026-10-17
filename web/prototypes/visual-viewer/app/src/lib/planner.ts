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
  const main: Block[] = story.blocks.filter(b => b.type !== 'story')
  if (flow) main.push({ ...flow, label: '문제와 기획', title: '어떤 문제를 어떻게 바꿀까요?', blocks: (flow.blocks || []).map((b: Block) => b.type === 'flow' ? { ...b, note: undefined } : b) })
  if (solution) main.push({ ...solution, label: '상품기획', title: '제안하는 기획', text: '각 제안의 적용 조건을 확인하고, 필요한 경우 상세 요구사항과 검증 계획을 펼쳐보세요.' })
  if (conditions.length) main.push({ type: 'story', key: 'conditions', label: '적용 조건', title: '기획에 반영한 전제', blocks: conditions.flatMap((b: Block) => b.blocks || []) })
  main.push({ type: 'callout', tone: 'info', text: '효과와 비용은 검증 전 기획안입니다. 다음 실행에 필요한 상세 요구사항·적용 순서·검증 계획은 각 제안에서 확인할 수 있습니다.' })
  const detail = sections.filter(b => b.key !== 'flow' && b.key !== 'solution' && b.key !== 'trust')
  const audit = trust ? [{ ...trust, blocks: (trust.blocks || []).filter((b: Block) => !conditions.includes(b)) }] : []
  const pages: Page[] = view.pages.map((p): Page => p.id === 'story'
    ? { ...p, title: '상품기획', nav: '상품기획', audience: 'planning', caption: { title: '핵심 문제와 제안', text: '기획을 먼저 읽고 필요한 근거만 찾아보세요.' }, blocks: main }
    : { ...p, audience: p.id === 'history' || p.id === 'export' ? 'diagnostic' : 'evidence' })
  if (detail.length) pages.push({ id: 'planning-detail', title: '문제·기능 상세 비교', nav: '상세 비교', audience: 'evidence', blocks: detail })
  if (audit.length) pages.push({ id: 'review-diagnostics', title: '검토·진단 기록', nav: '검토·진단 기록', audience: 'diagnostic', blocks: audit })
  return { ...view, pages }
}
