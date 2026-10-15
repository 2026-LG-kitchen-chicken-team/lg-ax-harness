// K 업무형's own renderers for some block types (components/blocks.tsx asks this context first) and its chart colours.
// The shared renderers also read it to draw K's way (report voice, summaries, source marks).
import { createContext, useContext, type ReactNode } from 'react'
import type { Block, Tone } from '../types'

export type SkinId = 'ops'
export type BlockRenderer = (p: { b: Block; copy: (s: string) => void }) => ReactNode
export interface Skin {
  id: SkinId
  blocks: Partial<Record<string, BlockRenderer>>
  hex: Record<Tone, string>
}
export const SkinContext = createContext<Skin | null>(null)
export const useSkin = () => useContext(SkinContext)
