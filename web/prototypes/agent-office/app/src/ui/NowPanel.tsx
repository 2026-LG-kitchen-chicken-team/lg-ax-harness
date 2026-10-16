// Left panel: one line per part of the harness saying what it is doing right now, then the latest records.
import { NODE, NODES } from '../lib/catalog'
import { clock } from '../lib/labels'
import type { Snapshot } from '../lib/state'
import { statusText } from '../scene/Room'

const GROUPS: { title: string; ids: string[] }[] = [
  { title: 'Agent · 선택 연구 역할', ids: ['main', 'product_official_researcher', 'product_review_researcher', 'product_evidence_reviewer'] },
  { title: '업무 Skill 6', ids: ['evidence-retrieval', 'web-evidence-collection', 'needs-structuring', 'feature-comparison', 'concept-writing', 'review-and-revise'] },
  { title: '시설', ids: NODES.filter((n) => n.kind === 'place').map((n) => n.id) },
]

export function NowPanel({ snap, selected, onSelect, stale = false }: { snap: Snapshot; selected: string | null; onSelect: (id: string) => void; stale?: boolean }) {
  const active = Object.values(snap.nodes).filter((n) => n.status === 'active').length
  return (
    <div className="panel pointer-events-auto flex max-h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-3 py-2">
        <h2 className="text-[13px] font-bold">{stale ? '마지막으로 확인한 일' : '지금 하는 일'}</h2>
        <span className="font-mono text-[11px] text-[var(--dim)]">{stale ? '갱신 확인 필요' : active ? `${active}곳 작업 관측` : '새 사건 대기'}</span>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto px-2 py-2">
        {GROUPS.map((g) => (
          <div key={g.title} className="flex flex-col gap-0.5">
            <div className="px-1 text-[10.5px] font-semibold text-[var(--dim)]">{g.title}</div>
            {g.ids.map((id) => {
              const st = snap.nodes[id]
              const node = NODE[id]
              return (
                <button key={id} className={`now-row ${selected === id ? 'is-sel' : ''}`} data-status={st?.status ?? 'idle'} style={{ ['--c' as string]: node.color }} onClick={() => onSelect(id)}>
                  <span className="now-dot" />
                  <span className="now-name">{node.ko}</span>
                  <span className="now-act">{statusText(st?.status, st?.activity ?? null, st?.since ?? null, snap.t)}</span>
                </button>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export function Feed({ snap, onSelect }: { snap: Snapshot; onSelect: (id: string) => void }) {
  const items = snap.feed.slice(0, 7)
  return (
    <div className="panel pointer-events-auto flex flex-col overflow-hidden">
      <div className="border-b border-[var(--line)] px-3 py-1.5 text-[12px] font-bold">방금 일어난 일</div>
      <ul className="flex flex-col px-2 py-1.5">
        {items.map((f) => (
          <li key={f.key}>
            <button className={`feed-row feed-btn tone-${f.tone}`} onClick={() => onSelect(f.node)}>
              <span className="font-mono text-[10.5px] text-[var(--dim)]">{clock(f.t)}</span>
              <span className="w-[42px] shrink-0 text-[10.5px] text-[var(--dim)]">{f.who}</span>
              <span className="flex-1 truncate text-left">{f.label}</span>
            </button>
          </li>
        ))}
        {!items.length && <li className="px-1 py-1 text-[12px] text-[var(--dim)]">아직 기록이 없습니다.</li>}
      </ul>
    </div>
  )
}
