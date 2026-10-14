// Floor, the web street outside, and the workflow clock around the main desk.
import { useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree, type ThreeEvent } from '@react-three/fiber'
import { Grid, Html, Line, OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import * as THREE from 'three'
import { FLOOR, NODE } from '../lib/catalog'
import { PACKET_REAL_MS, STREET_Z, nodeVec, useScene } from './ctx'

function radialTexture(inner: string, outer: string): THREE.Texture {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const g = c.getContext('2d') as CanvasRenderingContext2D
  const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128)
  grd.addColorStop(0, inner)
  grd.addColorStop(1, outer)
  g.fillStyle = grd
  g.fillRect(0, 0, 256, 256)
  return new THREE.CanvasTexture(c)
}

export function Floor() {
  const w = FLOOR.maxX - FLOOR.minX
  const d = FLOOR.maxZ - FLOOR.minZ
  const cx = (FLOOR.maxX + FLOOR.minX) / 2
  const cz = (FLOOR.maxZ + FLOOR.minZ) / 2
  const halo = useMemo(() => radialTexture('rgba(40,90,190,0.55)', 'rgba(4,6,13,0)'), [])
  const edge = useMemo(() => new THREE.MeshBasicMaterial({ color: new THREE.Color('#2b6cff').multiplyScalar(1.6), toneMapped: false }), [])
  // Guide lines on the floor: the order the Skills describe (not a record of what happened).
  const guide: [number, number][] = [[0, 0.5], [6.2, -4.6], [11.2, -4.6], [16.2, -4.6], [16.2, 1.6], [11.2, 1.6], [6.2, 1.6], [6.2, 7.4]]
  return (
    <group>
      <mesh position={[cx, -0.9, cz - 2]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[150, 150]} />
        <meshBasicMaterial map={halo} transparent depthWrite={false} />
      </mesh>
      <mesh position={[cx, -0.35, cz]} receiveShadow>
        <boxGeometry args={[w, 0.7, d]} />
        <meshStandardMaterial color="#070c1b" roughness={0.6} metalness={0.5} />
      </mesh>
      <Grid position={[cx, 0.006, cz]} args={[w, d]} cellSize={1} cellThickness={0.55} cellColor="#13224a" sectionSize={4} sectionThickness={1.1} sectionColor="#1d3f8c" fadeDistance={400} fadeStrength={0} infiniteGrid={false} />
      {[
        [cx, FLOOR.minZ, w, 0.08],
        [cx, FLOOR.maxZ, w, 0.08],
        [FLOOR.minX, cz, 0.08, d],
        [FLOOR.maxX, cz, 0.08, d],
      ].map(([x, z, a, b], i) => (
        <mesh key={i} position={[x, 0.02, z]} material={edge}><boxGeometry args={[a, 0.06, b]} /></mesh>
      ))}
      <Line points={guide.map(([x, z]) => [x, 0.03, z] as [number, number, number])} color="#3a5bbd" lineWidth={1.4} dashed dashSize={0.3} gapSize={0.4} transparent opacity={0.55} />
    </group>
  )
}

function windowsTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas')
  c.width = 64
  c.height = 128
  const g = c.getContext('2d') as CanvasRenderingContext2D
  g.fillStyle = '#000'
  g.fillRect(0, 0, 64, 128)
  for (let y = 4; y < 128; y += 10) {
    for (let x = 4; x < 64; x += 12) {
      const v = (x * 13 + y * 7) % 11
      g.fillStyle = v < 6 ? '#fff' : v < 8 ? '#777' : '#111'
      g.fillRect(x, y, 7, 5)
    }
  }
  const tex = new THREE.CanvasTexture(c)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  return tex
}

const SPECIAL_LABEL: Record<string, string> = { search: '웹 검색', browser: '브라우저', web: '웹 (주소 없음)' }

function Building({ host, first, visits, source, lift = 0 }: { host: string; first: number; visits: number; source: string; lift?: number }) {
  const { snapRef, speedRef, hostPos, onSelect, overlay } = useScene()
  const group = useRef<THREE.Group>(null)
  const beacon = useRef<THREE.MeshBasicMaterial>(null)
  const p = useMemo(() => hostPos(host), [host, hostPos])
  const special = host in SPECIAL_LABEL
  const h = special ? 3.4 : Math.min(6, 2.2 + visits * 0.6)
  const color = special ? (host === 'search' ? '#5ad1ff' : '#ff7ad9') : source === 'worklog' ? '#e7c27d' : NODE.web.color
  const mat = useMemo(() => {
    const tex = windowsTexture()
    tex.repeat.set(1, h / 3)
    return new THREE.MeshStandardMaterial({ color: '#0d1430', emissive: color, emissiveMap: tex, emissiveIntensity: 0.6, roughness: 0.4, metalness: 0.6 })
  }, [color, h])
  const labelEl = useRef<HTMLDivElement>(null)
  useFrame((s) => {
    const snap = snapRef.current
    const g = group.current
    if (!g) return
    const appear = Math.min(1, Math.max(0, (snap.t - first) / (PACKET_REAL_MS * Math.max(1, speedRef.current))))
    g.visible = snap.t >= first
    g.scale.set(1, 0.02 + appear * 0.98, 1)
    const active = snap.activeHosts.has(host)
    const pulse = 0.5 + 0.5 * Math.sin(s.clock.elapsedTime * 8)
    mat.emissiveIntensity = active ? 1.6 + pulse * 1.4 : 0.55
    if (beacon.current) beacon.current.color.set(color).multiplyScalar(active ? 3 + pulse * 3 : 1.2)
    if (labelEl.current) {
      labelEl.current.style.display = g.visible ? '' : 'none'
      labelEl.current.dataset.active = active ? '1' : '0'
    }
  })
  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    onSelect('web')
  }
  return (
    <group position={[p.x, 0, p.z]} onClick={click}>
      <group ref={group}>
        <mesh position={[0, h / 2, 0]} material={mat}><boxGeometry args={[2.3, h, 2.3]} /></mesh>
        <mesh position={[0, h + 0.15, 0]}><boxGeometry args={[1.6, 0.3, 1.6]} /><meshStandardMaterial color="#141d3d" /></mesh>
        <mesh position={[0, h + 0.55, 0]}><sphereGeometry args={[0.16, 12, 12]} /><meshBasicMaterial ref={beacon} toneMapped={false} /></mesh>
      </group>
      <Html portal={overlay} position={[0, h + 1.1 + lift, 0]} center zIndexRange={[15, 0]} style={{ pointerEvents: 'none' }}>
        <div ref={labelEl} className="host-label" style={{ ['--c' as string]: color }}>
          {SPECIAL_LABEL[host] ?? host}
          {source === 'worklog' && <span className="host-src" title="하네스 작업 일지(DB)에 적힌 사이트">일지</span>}
        </div>
      </Html>
    </group>
  )
}

export function WebStreet() {
  const { model, overlay } = useScene()
  const special = useMemo(() => {
    const out: { host: string; first: number; visits: number }[] = []
    for (const h of ['search', 'browser', 'web']) {
      const spans = model.spans.filter((s) => s.target === 'web' && s.host === h)
      if (spans.length) out.push({ host: h, first: spans[0].start, visits: spans.length })
    }
    return out
  }, [model])
  const visits = useMemo(() => {
    const m = new Map<string, number>()
    for (const s of model.spans) if (s.target === 'web' && s.host) m.set(s.host, (m.get(s.host) ?? 0) + 1)
    for (const p of model.points) if (typeof p.wf?.host === 'string') m.set(p.wf.host, (m.get(p.wf.host) ?? 0) + 1)
    return m
  }, [model])
  const lane = useMemo(() => new THREE.MeshBasicMaterial({ color: new THREE.Color('#ff9f43').multiplyScalar(1.3), toneMapped: false }), [])
  return (
    <group>
      <mesh position={[3, -0.32, STREET_Z - 1.6]}>
        <boxGeometry args={[38, 0.6, 9.5]} />
        <meshStandardMaterial color="#05070f" roughness={0.9} />
      </mesh>
      {Array.from({ length: 16 }, (_, i) => (
        <mesh key={i} position={[-15 + i * 2.4, 0.0, STREET_Z + 2.1]} material={lane}><boxGeometry args={[1.2, 0.02, 0.08]} /></mesh>
      ))}
      <mesh position={[3, 0.5, -11.3]}>
        <boxGeometry args={[37, 1.0, 0.08]} />
        <meshStandardMaterial color="#ff9f43" transparent opacity={0.07} depthWrite={false} />
      </mesh>
      <mesh position={[3, 1.0, -11.3]} material={lane}><boxGeometry args={[37, 0.03, 0.05]} /></mesh>
      <Html portal={overlay} position={[-17.5, 0.4, STREET_Z + 2.3]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
        <div className="street-sign">바깥 웹 · 실제로 연 사이트만 건물이 됩니다</div>
      </Html>
      {special.map((b) => <Building key={b.host} host={b.host} first={b.first} visits={b.visits} source="tool" />)}
      {model.hosts.map((h, i) => <Building key={h.host} host={h.host} first={h.first} visits={visits.get(h.host) ?? 1} source={h.source} lift={i % 2 ? 1.3 : 0} />)}
    </group>
  )
}

// Workflow clock (from the harness DB): elapsed share of the budget, with the 420 s research and 90 s final marks.
const RING_R = 2.78
function markAt(leftMs: number, budgetMs: number): [number, number, number] {
  const a = ((budgetMs - leftMs) / budgetMs) * Math.PI * 2 - Math.PI / 2
  return [Math.cos(a) * RING_R, 0.35, Math.sin(a) * RING_R]
}

export function ClockRing() {
  const { snapRef } = useScene()
  const SEG = 96
  const R = RING_R
  const group = useRef<THREE.Group>(null)
  const mesh = useRef<THREE.InstancedMesh>(null)
  const marks = useRef<THREE.Group>(null)
  const c = nodeVec('main')
  const colors = useMemo(() => ({ on: new THREE.Color('#38e1ff'), warn: new THREE.Color('#ffb547'), end: new THREE.Color('#ff4d6d'), off: new THREE.Color('#14203f') }), [])
  useEffect(() => {
    const m = mesh.current
    if (!m) return
    const o = new THREE.Object3D()
    for (let i = 0; i < SEG; i++) {
      const a = (i / SEG) * Math.PI * 2 - Math.PI / 2
      o.position.set(Math.cos(a) * R, 0, Math.sin(a) * R)
      o.rotation.set(0, -a, 0)
      o.updateMatrix()
      m.setMatrixAt(i, o.matrix)
      m.setColorAt(i, colors.off)
    }
    m.instanceMatrix.needsUpdate = true
  }, [colors])
  useFrame(() => {
    const wf = snapRef.current.workflow
    if (group.current) group.current.visible = !!wf
    if (!wf || !mesh.current) return
    const budget = wf.budget
    const frac = budget ? Math.min(1, wf.elapsed / budget) : 0
    const col = new THREE.Color()
    for (let i = 0; i < SEG; i++) {
      const a = i / SEG
      if (budget && a < frac) {
        const leftAt = budget - a * budget
        col.copy(leftAt <= 90_000 ? colors.end : leftAt <= 420_000 ? colors.warn : colors.on).multiplyScalar(2.4)
      } else col.copy(colors.off)
      mesh.current.setColorAt(i, col)
    }
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true
    if (marks.current) {
      marks.current.visible = !!budget
      if (budget) {
        marks.current.children[0].position.set(...markAt(420_000, budget))
        marks.current.children[1].position.set(...markAt(90_000, budget))
      }
    }
  })
  const budget = 1_800_000
  return (
    <group position={[c.x, 0.26, c.z]}>
      <group ref={group} visible={false}>
        <instancedMesh ref={mesh} args={[undefined, undefined, SEG]}>
          <boxGeometry args={[0.07, 0.05, 0.16]} />
          <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
        <group ref={marks}>
          <mesh position={markAt(420_000, budget)}><boxGeometry args={[0.06, 0.7, 0.06]} /><meshBasicMaterial color={new THREE.Color('#ffb547').multiplyScalar(2)} toneMapped={false} /></mesh>
          <mesh position={markAt(90_000, budget)}><boxGeometry args={[0.06, 0.7, 0.06]} /><meshBasicMaterial color={new THREE.Color('#ff4d6d').multiplyScalar(2)} toneMapped={false} /></mesh>
        </group>
      </group>
    </group>
  )
}

export const CENTER = new THREE.Vector3(-0.6, 0, -6.6)
export const CAMERA_OFFSET = new THREE.Vector3(26, 27, 24)

export function Rig({ selected }: { selected: string | null }) {
  const { camera, size } = useThree()
  const controls = useRef<OrbitControlsImpl>(null)
  const goal = useRef(CENTER.clone())
  const until = useRef(0)
  const fit = useRef(20)
  const intro = useRef<number | null>(null)
  useEffect(() => {
    const cam = camera as THREE.OrthographicCamera
    // Phones get a closer view of the middle of the floor (drag to look around, pinch to zoom).
    fit.current = size.width < 640 ? Math.max(9, Math.min(size.width / 28, size.height / 38)) : Math.max(6, Math.min(size.width / 48, size.height / 35))
    if (intro.current == null) {
      intro.current = performance.now()
      cam.zoom = fit.current * 0.55
    } else cam.zoom = fit.current
    cam.updateProjectionMatrix()
  }, [camera, size.width, size.height])
  useEffect(() => {
    goal.current = selected === 'web' ? new THREE.Vector3(3, 0, -12) : selected ? nodeVec(selected) : CENTER.clone()
    until.current = performance.now() + 1400
  }, [selected])
  useFrame(() => {
    const c = controls.current
    // Opening move: swing in from the side and zoom to fit (2 s, only once).
    if (c && intro.current != null && performance.now() - intro.current < 2200) {
      const k = Math.min(1, (performance.now() - intro.current) / 2000)
      const e = 1 - Math.pow(1 - k, 3)
      const cam = camera as THREE.OrthographicCamera
      cam.zoom = fit.current * (0.55 + 0.45 * e)
      cam.updateProjectionMatrix()
      const angle = (1 - e) * 0.7
      const off = CAMERA_OFFSET.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle)
      camera.position.copy(c.target).add(off)
      c.update()
    }
    if (!c || performance.now() > until.current) return
    const delta = goal.current.clone().sub(c.target).multiplyScalar(0.08)
    c.target.add(delta)
    camera.position.add(delta)
    c.update()
  })
  return (
    <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.08} minZoom={5} maxZoom={90} minPolarAngle={0.3} maxPolarAngle={1.25} target={[CENTER.x, CENTER.y, CENTER.z]} />
  )
}
