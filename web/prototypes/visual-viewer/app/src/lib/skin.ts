// The dashboard views I–M draw A's pages and blocks in another look. Inside one of them this context carries the
// view's own renderers for some block types (components/blocks.tsx asks it first) and its chart colours. Outside
// (A and every other view) it is null and nothing changes.
import { createContext, useContext, type ReactNode } from 'react'
import type { Block, Tone } from '../types'

export type SkinId = 'navy' | 'mono' | 'ops' | 'analytics' | 'monoops'
export type BlockRenderer = (p: { b: Block; copy: (s: string) => void }) => ReactNode
export interface Skin {
  id: SkinId
  blocks: Partial<Record<string, BlockRenderer>>
  hex: Record<Tone, string>
  // J and M (black and white) colour chart series by order in greys; the tone is kept for status dots only.
  series?: string[]
}
export const SkinContext = createContext<Skin | null>(null)
export const useSkin = () => useContext(SkinContext)
