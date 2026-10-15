// Renders the block list that build_view.py writes for each page. Layout only: no counting or judging here.
// K's own renderers (dash/blocks.tsx) come first, then the story blocks (story.tsx), then the plain text pieces below.
import { useMemo, useState, type ReactNode } from 'react'
import { STORY_BLOCKS } from './story'
import { useSkin } from '../lib/skin'
import { Md } from '../lib/utils'
import type { Block } from '../types'

export function Blocks({ blocks, copy }: { blocks: Block[]; copy: (s: string) => void }) {
  return <>{blocks.map((b, i) => <BlockView key={i} b={b} copy={copy} />)}</>
}

export function BlockView({ b, copy }: { b: Block; copy: (s: string) => void }): ReactNode {
  const Own = useSkin()?.blocks[b.type]
  if (Own) return <Own b={b} copy={copy} />
  const Story = STORY_BLOCKS[b.type]
  if (Story) return <Story b={b} copy={copy} />
  switch (b.type) {
    case 'lead': return <p className="max-w-3xl text-[17px] leading-relaxed text-zinc-600"><Md text={b.text} /></p>
    case 'text': return <p className="max-w-3xl text-[15px] leading-7"><Md text={b.text} /></p>
    case 'divider': return <hr className="my-2 border-border" />
    case 'list':
      return (
        <div>
          {b.title && <div className="mb-2 text-sm font-semibold">{b.title}</div>}
          <ul className="flex list-disc flex-col gap-2 pl-5 text-[15px] leading-relaxed marker:text-muted-foreground">
            {(b.items || []).map((x: string, i: number) => <li key={i}><Md text={x} /></li>)}
          </ul>
        </div>
      )
    case 'code': return <pre className="overflow-x-auto rounded-xl bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-100">{b.text}</pre>
    default: return null
  }
}

// Search box and filter chips of a table block. Filters only hide rows; nothing is re-counted.
export function useTableRows(b: Block) {
  const cols: Block[] = b.columns || []
  const rows: Block[] = b.rows || []
  const [q, setQ] = useState('')
  const [f, setF] = useState('')
  const text = (r: Block) => cols.map((c) => { const v = r[c.key]; return typeof v === 'object' && v ? JSON.stringify(v) : String(v ?? '') }).join(' ').toLowerCase()
  const fval = (r: Block) => { const v = b.filter ? r[b.filter] : ''; return typeof v === 'object' && v ? v.text : v }
  const filters: string[] = useMemo(() => (b.filter ? Array.from(new Set(rows.map(fval).filter(Boolean))) : []), [rows, b.filter]) // eslint-disable-line react-hooks/exhaustive-deps
  const shown = rows.filter((r) => (!q || text(r).includes(q.toLowerCase())) && (!f || fval(r) === f))
  return { cols, shown, filters, q, setQ, f, setF }
}
