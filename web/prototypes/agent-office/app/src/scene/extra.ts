// One extra line under a room's name tag: real numbers that belong to that room (DB values are marked).
import { mmss } from '../lib/labels'
import type { Snapshot } from '../lib/state'

export function extraText(id: string, snap: Snapshot): string | null {
  if (id === 'main' && snap.workflow) {
    const w = snap.workflow
    return `업무 시계 ${mmss(w.elapsed)}${w.budget ? ` / ${mmss(w.budget)}` : ''}${w.finished ? ' · 끝' : w.researchStopped ? ' · 조사 멈춤' : ''}`
  }
  if ((id === 'review-and-revise' || id === 'shipping') && snap.saves.length) {
    const marks = snap.saves.map((s) => (s.accepted === true ? '승인' : s.accepted === false ? '거절' : '응답 미확인'))
    return id === 'shipping' ? `저장 ${snap.saves.length}건 · 마지막 ${marks[marks.length - 1]}` : `후보 저장 ${snap.saves.length}/3 · ${marks.join(' · ')}`
  }
  const c = snap.counts.find((x) => x.node === id)
  if (c) return c.values.map((v) => `${v.ko} ${v.value ?? '미측정'}`).join(' · ') + ' (DB)'
  if (id === 'vault' && snap.nodes.vault.calls) return `작업 일지 ${snap.nodes.vault.calls}건 (DB)`
  return null
}
