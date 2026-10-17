// Shape of window.LGAX_VIEW written by build_view.py. The viewer only renders; every count and label comes from there.

// k1–k4: K's one-hue ramp (lib/ktone.ts), light to dark along 현재 불편 → 기존 기능 → 남은 불편 → 제안.
export type Tone = 'blue' | 'green' | 'red' | 'orange' | 'purple' | 'gray' | 'k1' | 'k2' | 'k3' | 'k4'

export interface Chip {
  text: string
  tone?: Tone | string
  mono?: boolean
  tip?: string
}

export interface Caption {
  title?: string
  text?: string
  meta?: string
}

// Blocks are loosely typed on purpose: build_view.py (and model-written insights pages) own the shape.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Block = { type: string; [key: string]: any }

export interface Page {
  id: string
  audience?: 'planning' | 'evidence' | 'diagnostic'
  nav?: string
  icon?: string
  title: string
  title_icon?: string
  caption?: Caption | null
  blocks: Block[]
}

// The saved export and the turn the screen shows, for "보고서로 보기" (components/report.tsx). The report page reads
// the export itself; nothing in the viewer reads or changes it. plan: chart sections build_view.py counted, in the
// report's report_plan form (근거 구성, 제안과 근거 연결).
export interface ReportSource {
  export: unknown
  turn_id?: string | null
  plan?: unknown
}

export interface View {
  kind: 'lgax-view'
  schema: number
  generated_at?: string
  focus?: string | null
  app?: { title?: string; subtitle?: string; icon?: string }
  context?: {
    meta?: string
    file?: { name: string; size?: string }
    loaded?: string
    status?: Chip[]
    footer?: string[]
  }
  pages: Page[]
  warnings?: string[]
  report?: ReportSource
}

declare global {
  interface Window {
    LGAX_VIEW?: View
    LGAX_VIEW_INLINE?: boolean
  }
}
