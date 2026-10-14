// Moving light: a packet flies when a call starts (actor -> room) and when it ends (room -> actor, red on failure);
// a dashed beam joins the two while the call runs. Everything is computed from the record time, so scrubbing works.
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { QuadraticBezierLine } from '@react-three/drei'
import * as THREE from 'three'
import { COUNT_ROOMS, ROLE_IDS } from '../lib/catalog'
import type { SessionModel, Span } from '../lib/model'
import { BAD, GOLD, OK, PACKET_REAL_MS, actorVec, colorOf, nodeVec, targetVec, useScene } from './ctx'

interface Route {
  t: number
  from: THREE.Vector3
  to: THREE.Vector3
  mid: THREE.Vector3
  color: THREE.Color
  size: number
}

function route(t: number, from: THREE.Vector3, to: THREE.Vector3, color: string | THREE.Color, size = 1): Route {
  const mid = from.clone().lerp(to, 0.5)
  mid.y = Math.max(from.y, to.y) + 1.6 + from.distanceTo(to) * 0.14
  return { t, from, to, mid, color: new THREE.Color(color), size }
}

function lighter(hex: string): THREE.Color {
  return new THREE.Color(hex).lerp(new THREE.Color('#ffffff'), 0.35)
}

export function buildRoutes(model: SessionModel, hostPos: (h: string) => THREE.Vector3): Route[] {
  const out: Route[] = []
  for (const s of model.spans) {
    const to = targetVec(s, hostPos)
    if (!to) continue
    const from = actorVec(s.actor)
    const color = s.kind === 'handback' ? GOLD : s.target === 'web' ? colorOf('web') : colorOf(s.target)
    out.push(route(s.start, from, to, color, s.kind === 'delegate' || s.kind === 'handback' ? 1.5 : 1))
    if (s.kind === 'delegate' || s.kind === 'handback' || s.end == null || s.status === 'running') continue
    const failed = s.status === 'fail' || s.detail.accepted === false
    out.push(route(s.end, to.clone(), from.clone(), failed ? BAD : lighter(s.target === 'web' ? colorOf('web') : colorOf(s.target)), failed ? 1.3 : 0.8))
  }
  const main = actorVec('main')
  for (const p of model.points) {
    if (p.kind === 'request') out.push(route(p.t, nodeVec('reception', 1.6), main.clone(), '#b9c8ff', 1.6))
    if (p.cand) {
      for (const room of COUNT_ROOMS) out.push(route(p.t, nodeVec(room.node, 1.4), nodeVec('review-and-revise', 1.4), colorOf(room.node), 1.1))
      out.push(route(p.t, nodeVec('review-and-revise', 1.4), nodeVec('vault', 1.6), colorOf('vault'), 1.2))
    }
    if (p.wf) {
      const host = typeof p.wf.host === 'string' ? p.wf.host : null
      out.push(route(p.t, host ? hostPos(host).setY(3) : main.clone(), nodeVec('vault', 1.6), colorOf(host ? 'web' : 'vault'), 0.9))
    }
  }
  for (const sv of model.saves) {
    out.push(route(sv.t, nodeVec('review-and-revise', 1.4), nodeVec('shipping', 1.4), sv.accepted === true ? OK : sv.accepted === false ? BAD : GOLD, 1.5))
  }
  return out.sort((a, b) => a.t - b.t)
}

const MAX_PACKETS = 90
const TRAIL = 8
const tmp = new THREE.Object3D()
const pos = new THREE.Vector3()
const col = new THREE.Color()

function bezier(r: Route, q: number, into: THREE.Vector3) {
  const a = 1 - q
  into.set(
    a * a * r.from.x + 2 * a * q * r.mid.x + q * q * r.to.x,
    a * a * r.from.y + 2 * a * q * r.mid.y + q * q * r.to.y,
    a * a * r.from.z + 2 * a * q * r.mid.z + q * q * r.to.z,
  )
}

export function Packets() {
  const { model, snapRef, speedRef, hostPos } = useScene()
  const mesh = useRef<THREE.InstancedMesh>(null)
  const routes = useMemo(() => buildRoutes(model, hostPos), [model, hostPos])
  useLayoutEffect(() => {
    const m = mesh.current
    if (!m) return
    for (let i = 0; i < MAX_PACKETS * TRAIL; i++) m.setColorAt(i, col.set('#000000'))
    m.count = 0
  }, [])
  useFrame(() => {
    const m = mesh.current
    if (!m) return
    const t = snapRef.current.t
    const life = PACKET_REAL_MS * Math.max(1, speedRef.current)
    let lo = 0
    let hi = routes.length
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (routes[mid].t < t - life) lo = mid + 1
      else hi = mid
    }
    let n = 0
    let packets = 0
    for (let i = lo; i < routes.length && packets < MAX_PACKETS; i++) {
      const r = routes[i]
      if (r.t > t) break
      const p = (t - r.t) / life
      if (p < 0 || p >= 1) continue
      packets += 1
      const eased = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2
      for (let k = 0; k < TRAIL; k++) {
        const q = eased - k * 0.028
        if (q < 0) break
        bezier(r, q, pos)
        const fade = 1 - k / TRAIL
        tmp.position.copy(pos)
        tmp.scale.setScalar((k === 0 ? 0.2 : 0.14) * fade * r.size)
        tmp.updateMatrix()
        m.setMatrixAt(n, tmp.matrix)
        m.setColorAt(n, col.copy(r.color).multiplyScalar((k === 0 ? 4 : 2.4) * fade))
        n += 1
      }
    }
    m.count = n
    m.instanceMatrix.needsUpdate = true
    if (m.instanceColor) m.instanceColor.needsUpdate = true
  })
  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX_PACKETS * TRAIL]} frustumCulled={false}>
      <sphereGeometry args={[1, 12, 10]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  )
}

function Beam({ span }: { span: Span }) {
  const { hostPos } = useScene()
  const ref = useRef<any>(null)
  const { from, to, mid, color } = useMemo(() => {
    const to = targetVec(span, hostPos) ?? actorVec('main')
    const from = actorVec(span.actor)
    const mid = from.clone().lerp(to, 0.5)
    mid.y = Math.max(from.y, to.y) + 1.6 + from.distanceTo(to) * 0.14
    const base = span.kind === 'handback' ? GOLD : span.target === 'web' ? colorOf('web') : colorOf(span.target)
    return { from, to, mid, color: new THREE.Color(base).multiplyScalar(2.2) }
  }, [span, hostPos])
  useLayoutEffect(() => {
    const m = ref.current?.material
    if (m) m.toneMapped = false
  }, [])
  useFrame((_, dt) => {
    const m = ref.current?.material
    if (m) m.dashOffset -= dt * 2.2
  })
  return (
    <QuadraticBezierLine ref={ref} start={from} end={to} mid={mid} color={color} lineWidth={2.4} dashed dashSize={0.5} gapSize={0.35} transparent opacity={0.85} />
  )
}

export function Beams() {
  const { snapRef } = useScene()
  const [spans, setSpans] = useState<Span[]>([])
  const keys = useRef('')
  useFrame(() => {
    const act = snapRef.current.active.filter((s) => s.target !== 'desk' && s.kind !== 'delegate')
    const k = act.map((s) => s.key).join('|')
    if (k !== keys.current) {
      keys.current = k
      setSpans(act)
    }
  })
  return <group>{spans.map((s) => <Beam key={s.key} span={s} />)}</group>
}

// Research roles that are present but not using a tool: a soft link to main shows who they work for.
export function RoleLinks() {
  const { snapRef } = useScene()
  const [present, setPresent] = useState<string[]>([])
  const keys = useRef('')
  useFrame(() => {
    const p = ROLE_IDS.filter((id) => snapRef.current.presence[id])
    const k = p.join('|')
    if (k !== keys.current) {
      keys.current = k
      setPresent(p)
    }
  })
  return (
    <group>
      {present.map((id) => {
        const from = actorVec('main', 0.3)
        const to = actorVec(id, 0.3)
        const mid = from.clone().lerp(to, 0.5).setY(0.3)
        return <QuadraticBezierLine key={id} start={from} end={to} mid={mid} color={colorOf(id)} lineWidth={1.2} dashed dashSize={0.2} gapSize={0.3} transparent opacity={0.5} />
      })}
    </group>
  )
}
