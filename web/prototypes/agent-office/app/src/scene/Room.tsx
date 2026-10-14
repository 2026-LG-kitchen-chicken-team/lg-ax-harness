import { useMemo, useRef, type ReactNode } from 'react'
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { Html, RoundedBox, Sparkles } from '@react-three/drei'
import * as THREE from 'three'
import type { OfficeNode } from '../lib/catalog'
import { secs } from '../lib/labels'
import type { Status } from '../lib/state'
import { BAD, OK, PACKET_REAL_MS, useScene } from './ctx'
import { extraText } from './extra'

let gradient: THREE.Texture | null = null
// Vertical fade used by the light columns over busy rooms.
export function gradientTexture(): THREE.Texture {
  if (gradient) return gradient
  const c = document.createElement('canvas')
  c.width = 4
  c.height = 128
  const g = c.getContext('2d') as CanvasRenderingContext2D
  const grd = g.createLinearGradient(0, 0, 0, 128)
  grd.addColorStop(0, 'rgba(255,255,255,0)')
  grd.addColorStop(0.55, 'rgba(255,255,255,0.28)')
  grd.addColorStop(1, 'rgba(255,255,255,0.95)')
  g.fillStyle = grd
  g.fillRect(0, 0, 4, 128)
  gradient = new THREE.CanvasTexture(c)
  return gradient
}

const BAD_C = new THREE.Color(BAD)
const OK_C = new THREE.Color(OK)
const FLOOR_Y = 0.22

export function statusText(status: Status | undefined, activity: string | null, since: number | null, t: number): string {
  if (status === 'off') return '이번 기록에선 호출 안 됨'
  if (status === 'active') return `${activity ?? '작업 중'}${since != null ? ` · ${secs(t - since)}째` : ''}`
  if (activity) return status === 'idle' ? `최근: ${activity}` : activity
  return '대기'
}

// Neon frame around a room floor: four thin bars whose brightness carries the room's state (bloom picks it up).
function Frame({ w, d, material }: { w: number; d: number; material: THREE.Material }) {
  const t = 0.07
  const y = FLOOR_Y + 0.02
  return (
    <group>
      <mesh position={[0, y, -d / 2]} material={material}><boxGeometry args={[w, 0.05, t]} /></mesh>
      <mesh position={[0, y, d / 2]} material={material}><boxGeometry args={[w, 0.05, t]} /></mesh>
      <mesh position={[-w / 2, y, 0]} material={material}><boxGeometry args={[t, 0.05, d]} /></mesh>
      <mesh position={[w / 2, y, 0]} material={material}><boxGeometry args={[t, 0.05, d]} /></mesh>
    </group>
  )
}

export function Room({ node, children, label = true, walls = true }: { node: OfficeNode; children?: ReactNode; label?: boolean; walls?: boolean }) {
  const { snapRef, selected, onSelect, speedRef, overlay } = useScene()
  const [w, d] = node.size
  const color = useMemo(() => new THREE.Color(node.color), [node.color])
  const frameMat = useMemo(() => new THREE.MeshBasicMaterial({ color: node.color, toneMapped: false }), [node.color])
  const rimMat = useMemo(() => new THREE.MeshBasicMaterial({ color: node.color, toneMapped: false, transparent: true, opacity: 0.9 }), [node.color])
  const glassMat = useMemo(() => new THREE.MeshStandardMaterial({ color: node.color, transparent: true, opacity: 0.08, roughness: 0.1, metalness: 0.2, depthWrite: false, side: THREE.DoubleSide }), [node.color])
  const floorMat = useRef<THREE.MeshStandardMaterial>(null)
  const column = useRef<THREE.Mesh>(null)
  const columnMat = useMemo(() => new THREE.MeshBasicMaterial({ color: node.color, map: gradientTexture(), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }), [node.color])
  const sparkles = useRef<THREE.Group>(null)
  const statusEl = useRef<HTMLDivElement>(null)
  const codeEl = useRef<HTMLDivElement>(null)
  const extraEl = useRef<HTMLDivElement>(null)
  const lastExtra = useRef('')
  const wave = useRef<THREE.Mesh>(null)
  const waveMat = useMemo(() => new THREE.MeshBasicMaterial({ color: node.color, transparent: true, opacity: 0, toneMapped: false, depthWrite: false, side: THREE.DoubleSide }), [node.color])
  const boxEl = useRef<HTMLDivElement>(null)
  const hover = useRef(false)
  const last = useRef('')

  useFrame((state) => {
    const snap = snapRef.current
    const st = snap.nodes[node.id]
    const time = state.clock.elapsedTime
    const status = st?.status
    const pulse = 0.5 + 0.5 * Math.sin(time * 7)
    const isSel = selected === node.id
    let k = status === 'active' ? 2.4 + pulse * 1.8 : status === 'fail' ? 1.6 + pulse * 1.2 : status === 'done' ? 1.8 : status === 'off' ? 0.18 : 0.55
    if (isSel) k += 0.9
    if (hover.current) k += 0.5
    const base = status === 'fail' ? BAD_C : status === 'done' && node.kind !== 'role' ? OK_C : color
    frameMat.color.copy(base).multiplyScalar(k)
    rimMat.color.copy(base).multiplyScalar(Math.max(0.35, k * 0.7))
    glassMat.opacity = status === 'off' ? 0.03 : status === 'active' ? 0.16 : 0.08
    if (floorMat.current) {
      floorMat.current.emissive.copy(base)
      floorMat.current.emissiveIntensity = status === 'active' ? 0.22 + pulse * 0.12 : status === 'fail' ? 0.2 : status === 'done' ? 0.12 : 0.03
    }
    const lit = status === 'active' || status === 'fail'
    if (column.current) {
      const target = lit ? (status === 'fail' ? 0.35 : 0.5 + pulse * 0.25) : 0
      columnMat.opacity += (target - columnMat.opacity) * 0.15
      columnMat.color.copy(base)
      column.current.visible = columnMat.opacity > 0.01
      column.current.rotation.y = time * 0.6
    }
    if (sparkles.current) sparkles.current.visible = status === 'active'
    // Shock ring when something arrives in this room.
    if (wave.current) {
      const age = st?.lastStart != null ? (snap.t - st.lastStart) / (PACKET_REAL_MS * 0.9 * Math.max(1, speedRef.current)) : 9
      const on = age >= 0 && age < 1
      wave.current.visible = on
      if (on) {
        const sc = 0.25 + age * 1.1
        wave.current.scale.set(sc, sc, sc)
        waveMat.opacity = (1 - age) * 0.95
        waveMat.color.copy(base).multiplyScalar(3)
      }
    }
    const loud = status === 'active' || status === 'done' || status === 'fail' || node.kind === 'main'
    const text = loud ? statusText(status, st?.activity ?? null, st?.since ?? null, snap.t) : ''
    if (text !== last.current && statusEl.current) {
      statusEl.current.textContent = text
      statusEl.current.style.display = text ? '' : 'none'
      last.current = text
    }
    if (codeEl.current) codeEl.current.style.display = node.kind === 'main' || isSel || hover.current ? '' : 'none'
    // Count rooms already say the numbers in their status line right after a save; the extra line is for later.
    const extra = loud && st?.activity?.startsWith('저장된 후보') ? '' : extraText(node.id, snap) ?? ''
    if (extra !== lastExtra.current && extraEl.current) {
      extraEl.current.textContent = extra
      extraEl.current.style.display = extra ? '' : 'none'
      lastExtra.current = extra
    }
    if (boxEl.current) {
      const s = status ?? 'idle'
      if (boxEl.current.dataset.status !== s) boxEl.current.dataset.status = s
      const sel = isSel ? '1' : '0'
      if (boxEl.current.dataset.selected !== sel) boxEl.current.dataset.selected = sel
    }
  })

  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    onSelect(node.id)
  }
  const over = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    hover.current = true
    document.body.style.cursor = 'pointer'
  }
  const out = () => {
    hover.current = false
    document.body.style.cursor = ''
  }
  const r = Math.min(w, d) * 0.42

  return (
    <group position={[node.pos[0], 0, node.pos[1]]} onClick={click} onPointerOver={over} onPointerOut={out}>
      <RoundedBox args={[w, 0.2, d]} radius={0.08} smoothness={3} position={[0, 0.1, 0]} receiveShadow>
        <meshStandardMaterial ref={floorMat} color="#0b1224" roughness={0.55} metalness={0.35} emissive={node.color} emissiveIntensity={0.03} />
      </RoundedBox>
      <Frame w={w} d={d} material={frameMat} />
      {walls && (
        <group>
          <mesh position={[0, FLOOR_Y + 0.6, -d / 2 + 0.03]} material={glassMat}><boxGeometry args={[w, 1.2, 0.04]} /></mesh>
          <mesh position={[-w / 2 + 0.03, FLOOR_Y + 0.6, 0]} material={glassMat}><boxGeometry args={[0.04, 1.2, d]} /></mesh>
          <mesh position={[0, FLOOR_Y + 1.2, -d / 2 + 0.03]} material={rimMat}><boxGeometry args={[w, 0.035, 0.05]} /></mesh>
          <mesh position={[-w / 2 + 0.03, FLOOR_Y + 1.2, 0]} material={rimMat}><boxGeometry args={[0.05, 0.035, d]} /></mesh>
        </group>
      )}
      <mesh ref={column} position={[0, FLOOR_Y + 3.2, 0]} material={columnMat} visible={false}>
        <cylinderGeometry args={[r, r * 1.05, 6.4, 32, 1, true]} />
      </mesh>
      <group ref={sparkles} visible={false}>
        <Sparkles count={26} scale={[w * 0.8, 2.6, d * 0.8]} position={[0, FLOOR_Y + 1.4, 0]} size={3.2} speed={0.9} color={node.color} />
      </group>
      <mesh ref={wave} position={[0, FLOOR_Y + 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]} material={waveMat} visible={false}>
        <ringGeometry args={[Math.min(w, d) * 0.46, Math.min(w, d) * 0.5, 64]} />
      </mesh>
      <group position={[0, FLOOR_Y, 0]}>{children}</group>
      {label && (
        <Html portal={overlay} position={[node.kind === 'main' ? -w / 2 + 1.2 : 0, FLOOR_Y + 0.05, d / 2 + 0.05]} zIndexRange={[20, 0]} style={{ pointerEvents: 'none', transform: 'translate(-50%, 4px)' }}>
          <div ref={boxEl} className="room-label" data-kind={node.kind} style={{ ['--c' as string]: node.color }} onClick={() => onSelect(node.id)}>
            <div className="room-name">{node.ko}</div>
            <div ref={codeEl} className="room-code" style={{ display: 'none' }}>{node.code}</div>
            <div ref={statusEl} className="room-status" style={{ display: 'none' }} />
            <div ref={extraEl} className="room-extra" style={{ display: 'none' }} />
          </div>
        </Html>
      )}
    </group>
  )
}

// A screen or panel that glows with the room color while the room works.
export function useGlow(nodeId: string, color: string, idle = 0.35, busy = 2.6) {
  const { snapRef } = useScene()
  const mat = useMemo(() => new THREE.MeshBasicMaterial({ color, toneMapped: false }), [color])
  const base = useMemo(() => new THREE.Color(color), [color])
  useFrame((state) => {
    const st = snapRef.current.nodes[nodeId]?.status
    const pulse = 0.5 + 0.5 * Math.sin(state.clock.elapsedTime * 9)
    const k = st === 'active' ? busy * (0.75 + pulse * 0.35) : st === 'done' ? idle * 2.2 : st === 'fail' ? idle * 2 : st === 'off' ? idle * 0.3 : idle
    mat.color.copy(st === 'fail' ? BAD_C : base).multiplyScalar(k)
  })
  return mat
}

export function useActive(nodeId: string): () => boolean {
  const { snapRef } = useScene()
  return () => snapRef.current.nodes[nodeId]?.status === 'active'
}
