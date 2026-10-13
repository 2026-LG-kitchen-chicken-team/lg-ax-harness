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

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = []
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size))
  return out
}
