// The slide (B) and poster (C) layouts only re-arrange the "story" page that build_view.py wrote.
// They never count, rank or link anything themselves.
import type { Block, View } from '../types'

export interface Story {
  hero?: Block
  status: Block[] // everything on the story page besides hero and sections: warnings, stopped-request tables, notes
  sections: Record<string, Block> // problem, check, flow, solution, trust
  complete: boolean // a saved result exists (all sections present)
}

export function storyOf(view: View | null): Story | null {
  const page = view?.pages.find((p) => p.id === 'story')
  if (!page) return null
  const sections: Record<string, Block> = {}
  for (const b of page.blocks) if (b.type === 'story') sections[b.key || b.label] = b
  return {
    hero: page.blocks.find((b) => b.type === 'hero'),
    status: page.blocks.filter((b) => b.type !== 'hero' && b.type !== 'story'),
    sections,
    complete: ['problem', 'check', 'flow', 'solution', 'trust'].every((k) => k in sections),
  }
}

export const inner = (section: Block | undefined, type: string): Block | undefined =>
  (section?.blocks || []).find((b: Block) => b.type === type)

// Notes the builder put inside a section ("결과에 현재 불편이 없습니다", "검토 기록에 기존 기능 대조 판단이 없습니다" ...).
// The trust section's note is the closing statement that every view already prints, so it is left out.
export const notesOf = (section: Block | undefined): Block[] =>
  section?.key === 'trust' ? [] : (section?.blocks || []).filter((b: Block) => b.type === 'callout')

// Pain → remaining pain → proposal chains from the recorded links only (feature_matches, concept_links). Remaining
// pains no pain link reaches, and proposals no link reaches, are returned separately so a view can say so.
export function chainsOf(flow: Block | undefined) {
  const nodes: Block[] = flow?.nodes || []
  const links: Block[] = flow?.links || []
  const node = (id: string) => nodes.find((n) => n.id === id) || { type: 'node', id, text: '' }
  const col = (c: string) => nodes.filter((n) => n.column === c)
  const conceptsOf = (rid: string) => links.filter((l) => l.from === rid).map((l) => node(l.to))
  const pains = col('pain')
  const fromPain = new Set(links.filter((l) => pains.some((p) => p.id === l.from)).map((l) => l.to))
  const reached = new Set(links.map((l) => l.to))
  return {
    chains: pains.map((p) => ({ pain: p, steps: links.filter((l) => l.from === p.id).map((l) => ({ via: l, remaining: node(l.to), concepts: conceptsOf(l.to) })) })),
    orphanRemaining: col('remaining').filter((r) => !fromPain.has(r.id)).map((r) => ({ remaining: r, concepts: conceptsOf(r.id) })),
    orphanConcepts: col('concept').filter((c) => !reached.has(c.id)),
  }
}

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = []
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size))
  return out
}
