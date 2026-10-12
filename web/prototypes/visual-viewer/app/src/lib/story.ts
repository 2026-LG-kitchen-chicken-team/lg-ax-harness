// The slide (B) and poster (C) layouts only re-arrange the "story" page that build_view.py wrote.
// They never count, rank or link anything themselves.
import type { Block, View } from '../types'

export interface Story {
  hero?: Block
  status: Block[] // status / warning callouts shown before the story
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
    status: page.blocks.filter((b) => b.type === 'callout'),
    sections,
    complete: ['problem', 'check', 'flow', 'solution', 'trust'].every((k) => k in sections),
  }
}

export const inner = (section: Block | undefined, type: string): Block | undefined =>
  (section?.blocks || []).find((b: Block) => b.type === type)

export function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = []
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size))
  return out
}
