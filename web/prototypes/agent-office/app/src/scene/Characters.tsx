// The people in the office: the main planner and the three optional research roles (hover bots), plus a small
// drone for Claude Code's own helper subagents. A role bot is only solid while its subagent is recorded as present.
import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { NODE, ROLE_IDS } from '../lib/catalog'
import { PACKET_REAL_MS, actorVec, targetVec, useScene } from './ctx'
import { gradientTexture } from './Room'

function Bot({ color, crown = false, scale = 1 }: { color: string; crown?: boolean; scale?: number }) {
  const body = useMemo(() => new THREE.MeshStandardMaterial({ color: '#e6ecff', roughness: 0.3, metalness: 0.35, transparent: true }), [])
  const trim = useMemo(() => new THREE.MeshStandardMaterial({ color: '#28345f', roughness: 0.4, metalness: 0.6, transparent: true }), [])
  const light = useMemo(() => new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(2.6), toneMapped: false, transparent: true }), [color])
  return (
    <group scale={scale} userData={{ mats: [body, trim, light] }}>
      <mesh position={[0, 0.08, 0]} rotation={[-Math.PI / 2, 0, 0]} material={light}><ringGeometry args={[0.32, 0.42, 32]} /></mesh>
      <mesh position={[0, 0.78, 0]} material={body}><capsuleGeometry args={[0.32, 0.42, 6, 18]} /></mesh>
      <mesh position={[0, 0.8, 0.3]} material={trim}><boxGeometry args={[0.34, 0.24, 0.06]} /></mesh>
      <mesh position={[0, 0.83, 0.335]} material={light}><boxGeometry args={[0.2, 0.05, 0.02]} /></mesh>
      <mesh position={[0, 1.42, 0]} material={body}><sphereGeometry args={[0.32, 24, 24]} /></mesh>
      <mesh position={[0, 1.44, 0.2]} material={trim}><boxGeometry args={[0.46, 0.18, 0.2]} /></mesh>
      <mesh position={[0, 1.44, 0.305]} material={light}><boxGeometry args={[0.4, 0.07, 0.02]} /></mesh>
      <mesh position={[0, 1.8, 0]} material={trim}><cylinderGeometry args={[0.015, 0.015, 0.22, 6]} /></mesh>
      <mesh position={[0, 1.93, 0]} material={light}><sphereGeometry args={[0.06, 12, 12]} /></mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[s * 0.42, 0.85, 0.05]} rotation={[0.3, 0, s * 0.25]} material={body}>
          <capsuleGeometry args={[0.08, 0.32, 4, 10]} />
        </mesh>
      ))}
      {crown && (
        <mesh position={[0, 2.1, 0]} rotation={[Math.PI / 2, 0, 0]} material={light}><torusGeometry args={[0.28, 0.025, 8, 40]} /></mesh>
      )}
    </group>
  )
}

function setOpacity(group: THREE.Object3D | null, opacity: number) {
  const mats = (group?.children[0]?.userData?.mats ?? []) as THREE.Material[]
  for (const m of mats) m.opacity = opacity
}

function faceToward(group: THREE.Group, from: THREE.Vector3, to: THREE.Vector3 | null, rate = 0.12, rest = 0) {
  const want = to ? Math.atan2(to.x - from.x, to.z - from.z) : rest
  let diff = want - group.rotation.y
  diff = Math.atan2(Math.sin(diff), Math.cos(diff))
  group.rotation.y += diff * rate
}

export function MainBot() {
  const { snapRef, hostPos } = useScene()
  const group = useRef<THREE.Group>(null)
  const orbs = useRef<THREE.Group>(null)
  const home = useMemo(() => actorVec('main', 0.22).add(new THREE.Vector3(0, 0, 0.35)), [])
  useFrame((s) => {
    const g = group.current
    if (!g) return
    const snap = snapRef.current
    const time = s.clock.elapsedTime
    const working = snap.main.mode === 'working'
    g.position.set(home.x, home.y + Math.sin(time * (working ? 6 : 2)) * (working ? 0.06 : 0.04), home.z)
    const span = snap.active.filter((x) => x.actor === 'main').slice(-1)[0]
    faceToward(g, home, span ? targetVec(span, hostPos) : null, 0.1, 0)
    if (orbs.current) {
      orbs.current.visible = snap.main.mode === 'thinking'
      orbs.current.rotation.y = time * 2.4
      orbs.current.position.y = 2.45 + Math.sin(time * 3) * 0.05
    }
  })
  return (
    <group ref={group}>
      <Bot color={NODE.main.color} crown scale={1.15} />
      <group ref={orbs} visible={false}>
        {[0, 1, 2].map((i) => (
          <mesh key={i} position={[Math.cos((i * Math.PI * 2) / 3) * 0.45, 0, Math.sin((i * Math.PI * 2) / 3) * 0.45]}>
            <sphereGeometry args={[0.09, 12, 12]} />
            <meshBasicMaterial color={new THREE.Color(NODE.main.color).multiplyScalar(3)} toneMapped={false} />
          </mesh>
        ))}
      </group>
    </group>
  )
}

function RoleBot({ id }: { id: string }) {
  const { snapRef, hostPos, speedRef } = useScene()
  const group = useRef<THREE.Group>(null)
  const beam = useRef<THREE.Mesh>(null)
  const beamMat = useMemo(() => new THREE.MeshBasicMaterial({ color: new THREE.Color(NODE[id].color).multiplyScalar(2), map: gradientTexture(), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }), [id])
  const home = useMemo(() => actorVec(id, 0.22), [id])
  const shown = useRef(0)
  useFrame((s) => {
    const g = group.current
    if (!g) return
    const snap = snapRef.current
    const here = snap.presence[id]
    const want = here ? 1 : 0
    shown.current += (want - shown.current) * 0.08
    const k = shown.current
    // Arrival flash: a light column for the first moment after SubagentStart.
    const age = here ? (snap.t - here.since) / (PACKET_REAL_MS * 1.4 * Math.max(1, speedRef.current)) : 9
    beamMat.opacity = age < 1 ? (1 - age) * 0.9 : k * 0.12
    if (beam.current) beam.current.visible = beamMat.opacity > 0.01
    g.visible = k > 0.02 || snap.nodes[id]?.status !== 'off'
    setOpacity(g, 0.12 + k * 0.88)
    g.scale.setScalar(0.85 + k * 0.15)
    g.position.set(home.x, home.y + Math.sin(s.clock.elapsedTime * 3 + home.x) * 0.05 * k, home.z)
    const span = snap.active.filter((x) => x.actor === id).slice(-1)[0]
    faceToward(g, home, span ? targetVec(span, hostPos) : null, 0.1, Math.PI)
  })
  return (
    <group>
      <group ref={group}>
        <Bot color={NODE[id].color} />
      </group>
      <mesh ref={beam} position={[home.x, 3.2, home.z]} material={beamMat} visible={false}>
        <cylinderGeometry args={[0.7, 0.9, 6.4, 24, 1, true]} />
      </mesh>
    </group>
  )
}

// Claude Code's own helper subagents (not harness roles): a small drone near main, shown briefly when recorded.
function HelperDrone() {
  const { snapRef, model, speedRef } = useScene()
  const g = useRef<THREE.Group>(null)
  const helpers = useMemo(() => model.points.filter((p) => p.kind === 'helper').map((p) => p.t), [model])
  useFrame((s) => {
    if (!g.current) return
    const t = snapRef.current.t
    const win = PACKET_REAL_MS * 2.5 * Math.max(1, speedRef.current)
    const on = helpers.some((h) => h <= t && t - h < win)
    g.current.visible = on
    const a = s.clock.elapsedTime * 1.6
    const c = actorVec('main', 2.8)
    g.current.position.set(c.x + Math.cos(a) * 2.2, c.y + Math.sin(a * 2) * 0.2, c.z + Math.sin(a) * 2.2)
    g.current.rotation.y = a * 3
  })
  return (
    <group ref={g} visible={false}>
      <mesh><octahedronGeometry args={[0.22]} /><meshBasicMaterial color={new THREE.Color('#9fb4ff').multiplyScalar(2.4)} toneMapped={false} /></mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.34, 0.02, 6, 24]} /><meshBasicMaterial color="#9fb4ff" toneMapped={false} /></mesh>
    </group>
  )
}

export function Characters() {
  return (
    <group>
      <MainBot />
      {ROLE_IDS.map((id) => <RoleBot key={id} id={id} />)}
      <HelperDrone />
    </group>
  )
}
