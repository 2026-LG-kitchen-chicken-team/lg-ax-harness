import { useMemo, useRef, type MutableRefObject } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Environment, Lightformer } from '@react-three/drei'
import { Bloom, EffectComposer, Vignette } from '@react-three/postprocessing'
import { NODES, type OfficeNode } from '../lib/catalog'
import type { SessionModel } from '../lib/model'
import { snapshot, type Snapshot } from '../lib/state'
import { Characters } from './Characters'
import { SceneContext, makeHostPos, useScene } from './ctx'
import { Beams, Packets, RoleLinks } from './Flow'
import {
  BulbProp, ConsoleProp, MainDesk, RadarProp, ReceptionProp, RetrievalProp, RoleDesk, ScaleProp, ShelfProp, ShippingProp, SortProp, StampProp, VaultProp,
} from './Props'
import { Room } from './Room'
import { CAMERA_OFFSET, CENTER, ClockRing, Floor, Rig, WebStreet } from './World'

function Ticker() {
  const { model, timeRef, snapRef } = useScene()
  useFrame(() => {
    snapRef.current = snapshot(model, timeRef.current)
  }, -1)
  return null
}

function propFor(n: OfficeNode) {
  switch (n.id) {
    case 'main': return <MainDesk />
    case 'evidence-retrieval': return <RetrievalProp />
    case 'web-evidence-collection': return <RadarProp />
    case 'needs-structuring': return <SortProp />
    case 'feature-comparison': return <ScaleProp />
    case 'concept-writing': return <BulbProp />
    case 'review-and-revise': return <StampProp />
    case 'console': return <ConsoleProp />
    case 'shelf': return <ShelfProp />
    case 'vault': return <VaultProp />
    case 'reception': return <ReceptionProp />
    case 'shipping': return <ShippingProp />
    default: return n.kind === 'role' ? <RoleDesk id={n.id} /> : null
  }
}

export function Office({ model, timeRef, speedRef, selected, onSelect }: {
  model: SessionModel
  timeRef: MutableRefObject<number>
  speedRef: MutableRefObject<number>
  selected: string | null
  onSelect: (id: string | null) => void
}) {
  const snapRef = useRef<Snapshot>(snapshot(model, timeRef.current))
  const overlay = useRef<HTMLDivElement>(null)
  const hostPos = useMemo(() => makeHostPos(model), [model])
  const value = useMemo(
    () => ({ model, timeRef, speedRef, snapRef, selected, onSelect, hostPos, overlay: overlay as MutableRefObject<HTMLElement> }),
    [model, timeRef, speedRef, selected, onSelect, hostPos],
  )
  const cam = CENTER.clone().add(CAMERA_OFFSET)
  return (
    <div className="relative isolate h-full w-full">
    <Canvas
      orthographic
      dpr={[1, 2]}
      camera={{ position: [cam.x, cam.y, cam.z], zoom: 22, near: -200, far: 400 }}
      gl={{ antialias: false, powerPreference: 'high-performance' }}
      onPointerMissed={() => onSelect(null)}
    >
      <SceneContext.Provider value={value}>
        <color attach="background" args={['#03050b']} />
        <Ticker />
        <Environment resolution={256} frames={1}>
          <Lightformer form="rect" intensity={1.6} color="#9cc0ff" position={[0, 12, 0]} rotation-x={Math.PI / 2} scale={[40, 40, 1]} />
          <Lightformer form="rect" intensity={2.4} color="#38e1ff" position={[18, 4, 12]} scale={[14, 4, 1]} />
          <Lightformer form="ring" intensity={3} color="#ff7ad9" position={[-14, 6, -12]} scale={7} />
          <Lightformer form="rect" intensity={1.4} color="#ffb547" position={[4, 3, -20]} scale={[30, 3, 1]} />
        </Environment>
        <ambientLight intensity={0.5} />
        <hemisphereLight args={['#8fb3ff', '#0a0f1f', 0.55]} />
        <directionalLight position={[12, 24, 10]} intensity={1.1} color="#dfe8ff" />
        <directionalLight position={[-14, 10, -8]} intensity={0.35} color="#7c8cff" />
        <Floor />
        {NODES.filter((n) => n.id !== 'web').map((n) => (
          <Room key={n.id} node={n} walls={n.id !== 'shipping'}>{propFor(n)}</Room>
        ))}
        <Characters />
        <WebStreet />
        <ClockRing />
        <RoleLinks />
        <Beams />
        <Packets />
        <Rig selected={selected} />
        <EffectComposer multisampling={4}>
          <Bloom mipmapBlur intensity={1.25} luminanceThreshold={0.7} luminanceSmoothing={0.25} radius={0.72} />
          <Vignette offset={0.22} darkness={0.78} />
        </EffectComposer>
      </SceneContext.Provider>
    </Canvas>
    <div ref={overlay} className="pointer-events-none absolute inset-0 overflow-hidden" />
    </div>
  )
}
