// The object in each room. Each one moves only while its room is busy, so motion always means recorded activity.
import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { NODE } from '../lib/catalog'
import { BAD, GOLD, OK, PACKET_REAL_MS, useScene } from './ctx'
import { useActive, useGlow } from './Room'

const METAL = new THREE.MeshStandardMaterial({ color: '#34477f', roughness: 0.32, metalness: 0.75 })
const SHELL = new THREE.MeshStandardMaterial({ color: '#e4ebff', roughness: 0.25, metalness: 0.3 })
const DARK = new THREE.MeshStandardMaterial({ color: '#141d42', roughness: 0.45, metalness: 0.5 })

function useEase() {
  const v = useRef(0)
  return (target: number, rate = 0.08) => {
    v.current += (target - v.current) * rate
    return v.current
  }
}

export function RetrievalProp() {
  const id = 'evidence-retrieval'
  const glow = useGlow(id, NODE[id].color)
  const busy = useActive(id)
  const cards = useRef<THREE.Group>(null)
  const ease = useEase()
  useFrame((s, dt) => {
    const a = ease(busy() ? 1 : 0)
    const g = cards.current
    if (!g) return
    g.rotation.y += dt * (0.3 + a * 2.4)
    g.children.forEach((c, i) => {
      c.position.y = 1.0 + i * (0.12 + a * 0.22) + Math.sin(s.clock.elapsedTime * 3 + i) * 0.03 * a
      c.rotation.y = i * a * 0.35
    })
  })
  return (
    <group>
      <mesh position={[-1.1, 0.7, -0.9]} material={METAL}><boxGeometry args={[1.2, 1.4, 0.8]} /></mesh>
      {[0.35, 0.75, 1.15].map((y) => (
        <mesh key={y} position={[-1.1, y, -0.49]} material={glow}><boxGeometry args={[0.9, 0.06, 0.02]} /></mesh>
      ))}
      <mesh position={[0.5, 0.35, 0.2]} material={DARK}><cylinderGeometry args={[0.55, 0.65, 0.7, 24]} /></mesh>
      <mesh position={[0.5, 0.72, 0.2]} material={glow}><torusGeometry args={[0.5, 0.03, 8, 40]} /></mesh>
      <group ref={cards} position={[0.5, 0, 0.2]}>
        {[0, 1, 2, 3, 4].map((i) => (
          <mesh key={i} material={i % 2 ? glow : SHELL}><boxGeometry args={[0.9, 0.04, 0.62]} /></mesh>
        ))}
      </group>
    </group>
  )
}

export function RadarProp() {
  const id = 'web-evidence-collection'
  const glow = useGlow(id, NODE[id].color)
  const busy = useActive(id)
  const dish = useRef<THREE.Group>(null)
  const ease = useEase()
  useFrame((_, dt) => {
    const a = ease(busy() ? 1 : 0)
    if (dish.current) dish.current.rotation.y += dt * (0.25 + a * 3.5)
  })
  return (
    <group position={[0.2, 0, 0]}>
      <mesh position={[0, 0.25, 0]} material={METAL}><cylinderGeometry args={[0.7, 0.85, 0.5, 24]} /></mesh>
      <mesh position={[0, 0.9, 0]} material={SHELL}><cylinderGeometry args={[0.09, 0.12, 0.9, 12]} /></mesh>
      <group ref={dish} position={[0, 1.4, 0]}>
        <mesh rotation={[-0.9, 0, 0]} material={SHELL}>
          <sphereGeometry args={[0.95, 32, 12, 0, Math.PI * 2, 0, 0.9]} />
        </mesh>
        <mesh rotation={[-0.9, 0, 0]} position={[0, 0.02, 0]} material={glow}><torusGeometry args={[0.74, 0.03, 8, 48]} /></mesh>
        <mesh position={[0, 0.25, 0.35]} rotation={[-0.9, 0, 0]} material={glow}><cylinderGeometry args={[0.02, 0.02, 0.9, 6]} /></mesh>
        <mesh position={[0, 0.55, 0.72]} material={glow}><sphereGeometry args={[0.08, 12, 12]} /></mesh>
      </group>
    </group>
  )
}

export function SortProp() {
  const id = 'needs-structuring'
  const glow = useGlow(id, NODE[id].color)
  const busy = useActive(id)
  const grid = useRef<THREE.Group>(null)
  const ease = useEase()
  useFrame((s) => {
    const a = ease(busy() ? 1 : 0)
    grid.current?.children.forEach((c, i) => {
      const t = s.clock.elapsedTime * 4 + i * 0.7
      c.position.y = 0.95 + Math.max(0, Math.sin(t)) * 0.45 * a
      c.rotation.y = a * t * 0.3
    })
  })
  return (
    <group>
      <mesh position={[0, 0.4, 0]} material={METAL}><boxGeometry args={[2.0, 0.8, 1.6]} /></mesh>
      <mesh position={[0, 0.81, 0]} material={DARK}><boxGeometry args={[1.9, 0.02, 1.5]} /></mesh>
      <group ref={grid}>
        {Array.from({ length: 9 }, (_, i) => (
          <mesh key={i} position={[-0.55 + (i % 3) * 0.55, 0.95, -0.45 + Math.floor(i / 3) * 0.45]} material={i % 3 === 1 ? SHELL : glow}>
            <boxGeometry args={[0.3, 0.3, 0.3]} />
          </mesh>
        ))}
      </group>
    </group>
  )
}

export function ScaleProp() {
  const id = 'feature-comparison'
  const glow = useGlow(id, NODE[id].color)
  const busy = useActive(id)
  const beam = useRef<THREE.Group>(null)
  const ease = useEase()
  useFrame((s) => {
    const a = ease(busy() ? 1 : 0)
    if (beam.current) beam.current.rotation.z = Math.sin(s.clock.elapsedTime * 2.2) * 0.32 * a + 0.04
  })
  const pan = (x: number) => (
    <group position={[x, 0, 0]}>
      <mesh position={[0, -0.45, 0]} material={glow}><cylinderGeometry args={[0.01, 0.01, 0.9, 4]} /></mesh>
      <mesh position={[0, -0.9, 0]} material={SHELL}><cylinderGeometry args={[0.42, 0.3, 0.1, 24]} /></mesh>
    </group>
  )
  return (
    <group>
      <mesh position={[0, 0.12, 0]} material={METAL}><cylinderGeometry args={[0.6, 0.7, 0.24, 24]} /></mesh>
      <mesh position={[0, 1.0, 0]} material={SHELL}><cylinderGeometry args={[0.07, 0.09, 1.8, 12]} /></mesh>
      <group ref={beam} position={[0, 1.95, 0]}>
        <mesh material={glow}><boxGeometry args={[2.3, 0.07, 0.1]} /></mesh>
        {pan(-1.1)}
        {pan(1.1)}
      </group>
      <mesh position={[0, 2.0, 0]} material={glow}><sphereGeometry args={[0.1, 12, 12]} /></mesh>
    </group>
  )
}

export function BulbProp() {
  const id = 'concept-writing'
  const glow = useGlow(id, NODE[id].color, 0.4, 3.4)
  const busy = useActive(id)
  const ring = useRef<THREE.Group>(null)
  const ease = useEase()
  useFrame((s, dt) => {
    const a = ease(busy() ? 1 : 0)
    if (ring.current) {
      ring.current.rotation.y += dt * (0.4 + a * 2.5)
      ring.current.rotation.x = 0.6 + Math.sin(s.clock.elapsedTime) * 0.2
      ring.current.scale.setScalar(0.8 + a * 0.4)
    }
  })
  return (
    <group>
      <mesh position={[0, 0.3, 0]} material={METAL}><cylinderGeometry args={[0.5, 0.6, 0.6, 24]} /></mesh>
      <mesh position={[0, 0.75, 0]} material={SHELL}><cylinderGeometry args={[0.24, 0.28, 0.3, 16]} /></mesh>
      <mesh position={[0, 1.3, 0]} material={glow}><sphereGeometry args={[0.5, 32, 32]} /></mesh>
      <group ref={ring} position={[0, 1.3, 0]}>
        <mesh material={glow}><torusGeometry args={[0.85, 0.025, 8, 64]} /></mesh>
        <mesh position={[0.85, 0, 0]} material={glow}><sphereGeometry args={[0.07, 10, 10]} /></mesh>
      </group>
    </group>
  )
}

// Three slots: the first saved candidate and up to two revisions (the harness limit).
export function StampProp() {
  const id = 'review-and-revise'
  const { snapRef } = useScene()
  const glow = useGlow(id, NODE[id].color)
  const busy = useActive(id)
  const hammer = useRef<THREE.Group>(null)
  const slots = useMemo(() => [0, 1, 2].map(() => new THREE.MeshBasicMaterial({ color: '#223', toneMapped: false })), [])
  const ok = useMemo(() => new THREE.Color(OK), [])
  const bad = useMemo(() => new THREE.Color(BAD), [])
  const unknown = useMemo(() => new THREE.Color(GOLD), [])
  const dim = useMemo(() => new THREE.Color('#1c2547'), [])
  const ease = useEase()
  useFrame((s) => {
    const a = ease(busy() ? 1 : 0)
    if (hammer.current) hammer.current.position.y = 1.55 - Math.max(0, Math.sin(s.clock.elapsedTime * 7)) * 0.45 * a
    const saves = snapRef.current.saves
    slots.forEach((m, i) => {
      const sv = saves[i]
      if (!sv) m.color.copy(dim)
      else m.color.copy(sv.accepted === true ? ok : sv.accepted === false ? bad : unknown).multiplyScalar(2.2)
    })
  })
  return (
    <group>
      <mesh position={[0, 0.35, -0.2]} material={METAL}><boxGeometry args={[2.4, 0.7, 1.1]} /></mesh>
      {slots.map((m, i) => (
        <mesh key={i} position={[-0.75 + i * 0.75, 0.72, -0.2]} material={m}><boxGeometry args={[0.55, 0.05, 0.75]} /></mesh>
      ))}
      <mesh position={[1.35, 1.2, -0.6]} material={SHELL}><boxGeometry args={[0.2, 2.0, 0.2]} /></mesh>
      <group ref={hammer} position={[0.6, 1.55, -0.2]}>
        <mesh position={[0.4, 0.35, 0]} material={SHELL}><boxGeometry args={[0.9, 0.12, 0.16]} /></mesh>
        <mesh material={glow}><boxGeometry args={[0.5, 0.35, 0.5]} /></mesh>
      </group>
    </group>
  )
}

export function ConsoleProp() {
  const id = 'console'
  const glow = useGlow(id, NODE[id].color, 0.35, 2.2)
  const lines = useRef<THREE.Group>(null)
  const busy = useActive(id)
  useFrame((s) => {
    const on = busy()
    lines.current?.children.forEach((c, i) => {
      const t = (s.clock.elapsedTime * (on ? 2.2 : 0.2) + i * 0.18) % 1
      c.position.y = 0.85 + t * 0.9
      c.scale.x = 0.3 + ((i * 37) % 10) / 14
    })
  })
  return (
    <group>
      <mesh position={[0, 0.4, 0]} material={METAL}><boxGeometry args={[2.2, 0.8, 1.0]} /></mesh>
      <mesh position={[0, 0.83, 0.15]} rotation={[-0.25, 0, 0]} material={DARK}><boxGeometry args={[1.5, 0.05, 0.5]} /></mesh>
      <mesh position={[0, 1.35, -0.35]} material={DARK}><boxGeometry args={[1.9, 1.1, 0.06]} /></mesh>
      <group ref={lines} position={[-0.2, 0, -0.31]}>
        {[0, 1, 2, 3, 4].map((i) => (
          <mesh key={i} material={glow}><boxGeometry args={[1.2, 0.05, 0.01]} /></mesh>
        ))}
      </group>
    </group>
  )
}

export function ShelfProp() {
  const id = 'shelf'
  const glow = useGlow(id, NODE[id].color, 0.3, 2.4)
  const books = useMemo(() => {
    const out: { x: number; y: number; h: number; c: number }[] = []
    for (let row = 0; row < 3; row++) for (let i = 0; i < 9; i++) out.push({ x: -1.6 + i * 0.36 + (row % 2) * 0.05, y: 0.35 + row * 0.62, h: 0.32 + ((i * 7 + row * 3) % 5) * 0.04, c: (i + row) % 3 })
    return out
  }, [])
  return (
    <group position={[0, 0, -0.7]}>
      <mesh position={[0, 1.0, -0.25]} material={METAL}><boxGeometry args={[3.6, 2.0, 0.1]} /></mesh>
      {[0.15, 0.77, 1.39, 2.0].map((y) => (
        <mesh key={y} position={[0, y, 0]} material={METAL}><boxGeometry args={[3.6, 0.06, 0.5]} /></mesh>
      ))}
      {books.map((b, i) => (
        <mesh key={i} position={[b.x, b.y + b.h / 2 - 0.15, 0]} material={b.c === 0 ? glow : b.c === 1 ? SHELL : DARK}>
          <boxGeometry args={[0.26, b.h, 0.36]} />
        </mesh>
      ))}
    </group>
  )
}

export function VaultProp() {
  const id = 'vault'
  const glow = useGlow(id, NODE[id].color, 0.45, 2.4)
  const ring = useRef<THREE.Mesh>(null)
  useFrame((_, dt) => {
    if (ring.current) ring.current.rotation.z += dt * 0.8
  })
  return (
    <group position={[0, 0, -0.1]}>
      {[0, 1, 2].map((i) => (
        <group key={i} position={[0, 0.35 + i * 0.55, 0]}>
          <mesh material={SHELL}><cylinderGeometry args={[0.85, 0.85, 0.42, 32]} /></mesh>
          <mesh position={[0, 0.22, 0]} material={glow}><torusGeometry args={[0.85, 0.03, 8, 48]} /></mesh>
        </group>
      ))}
      <mesh ref={ring} position={[0, 1.0, 0]} rotation={[Math.PI / 2.4, 0, 0]} material={glow}><torusGeometry args={[1.35, 0.02, 6, 64]} /></mesh>
    </group>
  )
}

export function ReceptionProp() {
  const id = 'reception'
  const glow = useGlow(id, NODE[id].color, 0.4, 2.6)
  const env = useRef<THREE.Group>(null)
  const busy = useActive(id)
  const ease = useEase()
  useFrame((s) => {
    const a = ease(busy() ? 1 : 0, 0.05)
    if (env.current) {
      env.current.position.y = 1.2 + a * 0.8 + Math.sin(s.clock.elapsedTime * 2) * 0.06
      env.current.rotation.y = s.clock.elapsedTime * (0.3 + a)
      env.current.scale.setScalar(0.6 + a * 0.5)
    }
  })
  return (
    <group>
      <mesh position={[0, 0.45, 0.4]} material={METAL}><boxGeometry args={[3.0, 0.9, 0.7]} /></mesh>
      <mesh position={[0, 0.92, 0.4]} material={glow}><boxGeometry args={[3.0, 0.04, 0.72]} /></mesh>
      <group ref={env} position={[0, 1.2, -0.4]}>
        <mesh material={SHELL}><boxGeometry args={[0.9, 0.06, 0.6]} /></mesh>
        <mesh position={[0, 0.04, 0]} rotation={[0, Math.PI / 4, 0]} material={glow}><boxGeometry args={[0.45, 0.02, 0.45]} /></mesh>
      </group>
    </group>
  )
}

// Conveyor with one crate per save response, green when accepted and red when rejected.
export function ShippingProp() {
  const { snapRef, speedRef } = useScene()
  const crates = useRef<THREE.Group>(null)
  const mats = useMemo(() => Array.from({ length: 6 }, () => new THREE.MeshBasicMaterial({ color: OK, toneMapped: false })), [])
  const ok = useMemo(() => new THREE.Color(OK), [])
  const bad = useMemo(() => new THREE.Color(BAD), [])
  const unknown = useMemo(() => new THREE.Color(GOLD), [])
  const belt = useGlow('shipping', NODE.shipping.color, 0.25, 1.6)
  useFrame(() => {
    const snap = snapRef.current
    const saves = snap.saves.slice(-6)
    crates.current?.children.forEach((c, i) => {
      const sv = saves[i]
      c.visible = !!sv
      if (!sv) return
      const age = (snap.t - sv.t) / (PACKET_REAL_MS * 1.5 * Math.max(1, speedRef.current))
      const slide = Math.min(1, Math.max(0, age))
      const x = -5.6 + i * 1.9
      c.position.set(x - (1 - slide) * 3, 0.95 + (1 - slide) * 0.8, 0)
      mats[i].color.copy(sv.accepted === true ? ok : sv.accepted === false ? bad : unknown).multiplyScalar(1.6 + (1 - slide) * 2)
    })
  })
  return (
    <group>
      <mesh position={[0, 0.35, 0]} material={METAL}><boxGeometry args={[13.2, 0.5, 1.3]} /></mesh>
      <mesh position={[0, 0.62, 0.66]} material={belt}><boxGeometry args={[13.2, 0.04, 0.04]} /></mesh>
      <mesh position={[0, 0.62, -0.66]} material={belt}><boxGeometry args={[13.2, 0.04, 0.04]} /></mesh>
      <group ref={crates}>
        {mats.map((m, i) => (
          <group key={i} visible={false}>
            <mesh material={SHELL}><boxGeometry args={[0.9, 0.62, 0.9]} /></mesh>
            <mesh position={[0, 0.32, 0]} material={m}><boxGeometry args={[0.92, 0.06, 0.92]} /></mesh>
            <mesh position={[0, 0, 0.46]} material={m}><boxGeometry args={[0.5, 0.12, 0.02]} /></mesh>
          </group>
        ))}
      </group>
    </group>
  )
}

export function MainDesk() {
  const glow = useGlow('main', NODE.main.color, 0.5, 2.4)
  const ring = useRef<THREE.Group>(null)
  const { snapRef } = useScene()
  useFrame((_, dt) => {
    const mode = snapRef.current.main.mode
    if (ring.current) ring.current.rotation.y += dt * (mode === 'working' ? 2.2 : mode === 'thinking' ? 0.9 : 0.15)
  })
  return (
    <group>
      <mesh position={[0, 0.05, 0]} material={DARK}><cylinderGeometry args={[2.4, 2.5, 0.1, 64]} /></mesh>
      <mesh position={[0, 0.11, 0]} rotation={[-Math.PI / 2, 0, 0]} material={glow}><ringGeometry args={[2.3, 2.38, 64]} /></mesh>
      <group ref={ring} position={[0, 0.14, 0]}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <mesh key={i} rotation={[-Math.PI / 2, 0, (i * Math.PI) / 3]} material={glow}>
            <ringGeometry args={[1.7, 1.78, 24, 1, 0, Math.PI / 5]} />
          </mesh>
        ))}
      </group>
      <mesh position={[0, 0.55, -1.25]} rotation={[0, 0, 0]} material={METAL}>
        <torusGeometry args={[1.45, 0.22, 10, 40, Math.PI]} />
      </mesh>
      {[-0.95, 0, 0.95].map((a, i) => (
        <group key={i} position={[Math.sin(a) * 1.9, 1.75, -Math.cos(a) * 1.9 + 0.1]} rotation={[0, -a, 0]}>
          <mesh material={DARK}><boxGeometry args={[1.3, 0.8, 0.04]} /></mesh>
          <mesh position={[0, 0, 0.03]} material={glow}><planeGeometry args={[1.18, 0.68]} /></mesh>
        </group>
      ))}
    </group>
  )
}

export function RoleDesk({ id }: { id: string }) {
  const glow = useGlow(id, NODE[id].color, 0.25, 2.4)
  return (
    <group>
      <mesh position={[0, 0.42, -1.05]} material={METAL}><boxGeometry args={[2.6, 0.84, 0.9]} /></mesh>
      <mesh position={[0, 1.35, -1.3]} material={DARK}><boxGeometry args={[1.6, 0.9, 0.05]} /></mesh>
      <mesh position={[0, 1.35, -1.27]} material={glow}><planeGeometry args={[1.46, 0.76]} /></mesh>
      <mesh position={[0, 0.03, 0.3]} rotation={[-Math.PI / 2, 0, 0]} material={glow}><ringGeometry args={[0.7, 0.76, 48]} /></mesh>
    </group>
  )
}
