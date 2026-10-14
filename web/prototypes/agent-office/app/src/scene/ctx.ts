import { createContext, useContext, type MutableRefObject } from 'react'
import * as THREE from 'three'
import { NODE, ROLE_IDS } from '../lib/catalog'
import type { SessionModel, Span } from '../lib/model'
import type { Snapshot } from '../lib/state'

export interface SceneValue {
  model: SessionModel
  timeRef: MutableRefObject<number>
  speedRef: MutableRefObject<number>
  snapRef: MutableRefObject<Snapshot>
  selected: string | null
  onSelect: (id: string | null) => void
  hostPos: (host: string) => THREE.Vector3
  // Fixed layer over the canvas for every drei <Html> label (its default target is not ready for the first label).
  overlay: MutableRefObject<HTMLElement>
}

export const SceneContext = createContext<SceneValue | null>(null)

export function useScene(): SceneValue {
  const v = useContext(SceneContext)
  if (!v) throw new Error('SceneContext missing')
  return v
}

export const STREET_Z = -14.2
const SPECIAL_X: Record<string, number> = { search: -13.2, browser: -9.6, web: -6.0 }

// Buildings in the web street: fixed spots for search / browser, then each observed host in order of first visit.
export function makeHostPos(model: SessionModel): (host: string) => THREE.Vector3 {
  const order = model.hosts.map((h) => h.host)
  return (host: string) => {
    if (host in SPECIAL_X) return new THREE.Vector3(SPECIAL_X[host], 0, STREET_Z)
    const i = Math.max(0, order.indexOf(host))
    const row = Math.floor(i / 7)
    return new THREE.Vector3(-2.2 + (i % 7) * 3.5 + row * 1.7, 0, STREET_Z - row * 3.6)
  }
}

export function nodeVec(id: string, y = 0): THREE.Vector3 {
  const n = NODE[id]
  return n ? new THREE.Vector3(n.pos[0], y, n.pos[1]) : new THREE.Vector3(0, y, 0)
}

// Where a character stands: main at its desk, roles in their pods, Claude Code helpers next to main.
export function actorVec(actor: string, y = 1.4): THREE.Vector3 {
  if (ROLE_IDS.includes(actor)) return nodeVec(actor, y).add(new THREE.Vector3(0, 0, 0.2))
  if (actor === 'other_subagent') return nodeVec('main', y + 1.2).add(new THREE.Vector3(1.6, 0, -1.4))
  return nodeVec('main', y)
}

export function targetVec(span: Span, hostPos: (h: string) => THREE.Vector3, y = 1.2): THREE.Vector3 | null {
  if (span.target === 'desk') return null
  if (span.target === 'web') return hostPos(span.host ?? 'web').setY(y + 2)
  if (span.target === 'main') return actorVec('main', y)
  if (ROLE_IDS.includes(span.target)) return actorVec(span.target, y)
  return nodeVec(span.target, y)
}

export function colorOf(id: string): string {
  return NODE[id]?.color ?? '#9fb4ff'
}

export const OK = '#7dff9b'
export const BAD = '#ff4d6d'
export const GOLD = '#ffd166'

// Packets should look the same speed on screen whatever the replay speed: their life is measured in record time.
export const PACKET_REAL_MS = 1500
