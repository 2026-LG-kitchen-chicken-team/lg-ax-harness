import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment, Lightformer, OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";
import { nodes, type HarnessNode } from "./catalog";
import type { TraceEvent } from "./harness";

type Props = {
  time: number;
  events: TraceEvent[];
  selected: string;
  onSelect: (id: string) => void;
  statuses: Record<string, string>;
  motion: boolean;
};

type ProjectedLabel = { id: string; x: number; y: number; visible: boolean };

const CORE_COLOR = "#ff496d";
const agentNodes = nodes.filter((node) => node.kind === "agent");
const skillNodes = nodes.filter((node) => node.kind === "skill");
const nodeById = new Map(nodes.map((node) => [node.id, node]));
const locations = new Map<string, THREE.Vector3>();
locations.set("main", new THREE.Vector3(0, 2.1, 0));
const agentPositions: [number, number, number][] = [
  [-4.7, 1.25, -3.4],
  [0, 1.25, -5.35],
  [4.7, 1.25, -3.4],
];
const skillPositions: [number, number, number][] = [
  [-6.1, 0.76, 0.75],
  [-4.8, 0.76, 3.55],
  [-1.85, 0.76, 5.5],
  [1.85, 0.76, 5.5],
  [4.8, 0.76, 3.55],
  [6.1, 0.76, 0.75],
];
agentNodes.forEach((node, index) =>
  locations.set(
    node.id,
    new THREE.Vector3(...agentPositions[index % agentPositions.length]),
  ),
);
skillNodes.forEach((node, index) =>
  locations.set(
    node.id,
    new THREE.Vector3(...skillPositions[index % skillPositions.length]),
  ),
);

const statusLabel: Record<string, string> = {
  idle: "STANDBY",
  unknown: "UNOBSERVED",
  active: "WORKING",
  done: "COMPLETE",
  held: "CHECKPOINT",
  error: "ATTENTION",
};

const viewTarget = new THREE.Vector3(0, 0.95, 0);
const viewDirection = new THREE.Vector3(0, 10.05, 17).normalize();

/** Reserve real screen pixels for labels, not just the mesh bounding box. */
function fittedDistance(width: number, height: number, fieldOfView = 42) {
  const aspect = Math.max(0.3, width / Math.max(height, 1));
  const availableHorizontal = Math.max(0.35, 1 - 128 / Math.max(width, 1));
  const tangent = Math.tan(THREE.MathUtils.degToRad(fieldOfView / 2));
  let distance = 20.25;
  nodes
    .filter((node) => node.kind !== "core")
    .forEach((node) => {
      const location = locations.get(node.id)!;
      const label = new THREE.Vector3(
        location.x,
        node.kind === "agent" ? 2.65 : -0.28,
        location.z + (node.kind === "skill" ? 0.78 : 0),
      );
      const relative = label.sub(viewTarget);
      distance = Math.max(
        distance,
        Math.abs(relative.x) / (tangent * aspect * availableHorizontal) +
          relative.dot(viewDirection),
      );
    });
  return distance * 1.03;
}

function ResponsiveCamera({ distance }: { distance: number }) {
  const camera = useThree((state) => state.camera);
  const controls = useThree((state) => state.controls);
  useEffect(() => {
    camera.position
      .copy(viewDirection)
      .multiplyScalar(distance)
      .add(viewTarget);
    camera.lookAt(viewTarget);
    camera.updateMatrixWorld();
    if (
      controls &&
      "update" in controls &&
      typeof controls.update === "function"
    )
      controls.update();
  }, [camera, controls, distance]);
  return null;
}

function ProjectLabels({
  onProject,
}: {
  onProject: (labels: ProjectedLabel[]) => void;
}) {
  const previous = useRef<ProjectedLabel[]>([]);
  const projected = useMemo(() => new THREE.Vector3(), []);
  useFrame(({ camera, size }) => {
    camera.updateMatrixWorld();
    const next = nodes.map((node) => {
      const location = locations.get(node.id)!;
      if (node.kind === "core") projected.set(0, 0.2, 1.95);
      else
        projected.set(
          location.x,
          node.kind === "agent" ? 2.65 : -0.28,
          location.z + (node.kind === "skill" ? 0.78 : 0),
        );
      projected.project(camera);
      return {
        id: node.id,
        x: ((projected.x + 1) * size.width) / 2,
        y: ((1 - projected.y) * size.height) / 2,
        visible:
          projected.z > -1 &&
          projected.z < 1 &&
          Math.abs(projected.x) < 1.2 &&
          Math.abs(projected.y) < 1.2,
      };
    });
    const changed = next.some((label, index) => {
      const last = previous.current[index];
      return (
        !last ||
        last.visible !== label.visible ||
        Math.abs(last.x - label.x) > 0.5 ||
        Math.abs(last.y - label.y) > 0.5
      );
    });
    if (changed) {
      previous.current = next;
      onProject(next);
    }
  });
  return null;
}

function emissiveColor(hex: string, strength: number) {
  return new THREE.Color(hex).multiplyScalar(strength);
}

function buildRoute(source: string, target: string) {
  const from = locations.get(source);
  const to = locations.get(target);
  if (!from || !to || source === target) return null;
  const difference = new THREE.Vector3().subVectors(to, from);
  const middle = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
  const lateral = new THREE.Vector3(-difference.z, 0, difference.x).normalize();
  middle.addScaledVector(lateral, 0.28);
  middle.y += source === "main" || target === "main" ? 0.45 : 1.4;
  return new THREE.QuadraticBezierCurve3(from, middle, to);
}

function HardwareRing({
  radius,
  y,
  color,
  bright = false,
  thickness = 0.018,
}: {
  radius: number;
  y: number;
  color: string;
  bright?: boolean;
  thickness?: number;
}) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, y, 0]}>
      <torusGeometry args={[radius, thickness, 8, 100]} />
      <meshBasicMaterial
        color={emissiveColor(color, bright ? 2.8 : 0.32)}
        toneMapped={false}
      />
    </mesh>
  );
}

function Floor() {
  const ticks = useMemo(
    () =>
      Array.from({ length: 80 }, (_, index) => {
        const angle = (index / 80) * Math.PI * 2;
        return {
          angle,
          position: [
            Math.sin(angle) * 8.13,
            -0.155,
            Math.cos(angle) * 8.13,
          ] as [number, number, number],
          major: index % 5 === 0,
        };
      }),
    [],
  );
  return (
    <group>
      <mesh position={[0, -0.54, 0]} receiveShadow>
        <cylinderGeometry args={[8.7, 8.9, 0.55, 96]} />
        <meshStandardMaterial
          color="#07111d"
          metalness={0.86}
          roughness={0.36}
        />
      </mesh>
      <mesh position={[0, -0.24, 0]} receiveShadow>
        <cylinderGeometry args={[8.63, 8.63, 0.035, 96]} />
        <meshStandardMaterial
          color="#0a1624"
          metalness={0.72}
          roughness={0.28}
        />
      </mesh>
      <HardwareRing radius={8.57} y={-0.205} color="#34667e" />
      <HardwareRing radius={8.32} y={-0.203} color="#263e50" />
      <HardwareRing radius={7.78} y={-0.2} color="#26455b" />
      <HardwareRing radius={6.6} y={-0.198} color="#1d3447" />
      <HardwareRing radius={3.5} y={-0.198} color="#26374c" />
      <HardwareRing radius={2.5} y={-0.195} color="#273c52" />
      {ticks.map((tick, index) => (
        <mesh
          key={index}
          position={tick.position}
          rotation={[0, tick.angle, 0]}
        >
          <boxGeometry
            args={[
              tick.major ? 0.028 : 0.013,
              0.012,
              tick.major ? 0.18 : 0.085,
            ]}
          />
          <meshBasicMaterial color={tick.major ? "#355a6b" : "#1c3546"} />
        </mesh>
      ))}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.84, 0]}
        receiveShadow
      >
        <planeGeometry args={[120, 120]} />
        <meshStandardMaterial
          color="#040811"
          metalness={0.28}
          roughness={0.8}
        />
      </mesh>
    </group>
  );
}

const haloVertex = `
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;
const haloFragment = `
  uniform vec3 tint;
  uniform float power;
  varying vec3 vNormal;
  varying vec3 vView;
  void main() {
    float fresnel = pow(1.0 - max(dot(normalize(vNormal), normalize(vView)), 0.0), 3.5);
    gl_FragColor = vec4(tint * (1.1 + power), fresnel * 0.46);
  }
`;

function Core({
  time,
  selected,
  onSelect,
  status,
  motion,
  events,
  bodyScale,
}: {
  time: number;
  selected: boolean;
  onSelect: Props["onSelect"];
  status: string;
  motion: boolean;
  events: TraceEvent[];
  bodyScale: number;
}) {
  const machinery = useRef<THREE.Group>(null);
  const inner = useRef<THREE.Group>(null);
  const halo = useRef<THREE.ShaderMaterial>(null);
  const elapsed = useRef(0);
  const pulse = events.some(
    (event) =>
      event.kind !== "metadata" &&
      (event.source === "main" || event.target === "main") &&
      time >= event.at &&
      time - event.at < 1.7,
  );
  const haloUniforms = useMemo(
    () => ({
      tint: { value: new THREE.Color(CORE_COLOR) },
      power: { value: 0 },
    }),
    [],
  );
  useFrame((_, delta) => {
    if (motion) elapsed.current += delta;
    if (machinery.current)
      machinery.current.rotation.y = elapsed.current * 0.085;
    if (inner.current) {
      inner.current.rotation.y = elapsed.current * -0.16;
      inner.current.rotation.z = Math.sin(elapsed.current * 0.16) * 0.1;
    }
    if (halo.current) halo.current.uniforms.power.value = pulse ? 1.5 : 0.25;
  });
  return (
    <group
      onClick={(event) => {
        event.stopPropagation();
        onSelect("main");
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
    >
      <mesh position={[0, 0.04, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[1.62, 1.85, 0.44, 64]} />
        <meshStandardMaterial
          color="#182335"
          metalness={0.9}
          roughness={0.27}
        />
      </mesh>
      <mesh position={[0, 0.34, 0]} castShadow>
        <cylinderGeometry args={[1.3, 1.58, 0.22, 64]} />
        <meshStandardMaterial
          color="#0b1423"
          metalness={0.94}
          roughness={0.19}
        />
      </mesh>
      <mesh position={[0, 0.51, 0]}>
        <cylinderGeometry args={[1.18, 1.18, 0.12, 64]} />
        <meshStandardMaterial
          color="#1c2838"
          metalness={0.9}
          roughness={0.24}
        />
      </mesh>
      <HardwareRing
        radius={1.62}
        y={0.2}
        color={CORE_COLOR}
        bright
        thickness={0.025}
      />
      <HardwareRing
        radius={1.29}
        y={0.445}
        color={CORE_COLOR}
        bright={selected || pulse}
        thickness={0.016}
      />
      <HardwareRing radius={1.01} y={0.58} color="#6e2a44" />
      <HardwareRing
        radius={2.0}
        y={-0.175}
        color={CORE_COLOR}
        bright={selected}
        thickness={0.012}
      />
      <group position={[0, 2.06, 0]} scale={bodyScale}>
        <mesh>
          <sphereGeometry args={[1.06, 64, 48]} />
          <meshPhysicalMaterial
            color="#131e32"
            metalness={0.2}
            roughness={0.1}
            transmission={0.62}
            thickness={0.9}
            ior={1.3}
            clearcoat={1}
            clearcoatRoughness={0.05}
            envMapIntensity={1.8}
          />
        </mesh>
        <mesh scale={1.012}>
          <sphereGeometry args={[1.06, 48, 32]} />
          <shaderMaterial
            ref={halo}
            vertexShader={haloVertex}
            fragmentShader={haloFragment}
            uniforms={haloUniforms}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            toneMapped={false}
          />
        </mesh>
        <group ref={inner}>
          <mesh>
            <icosahedronGeometry args={[0.61, 0]} />
            <meshStandardMaterial
              color="#653c56"
              metalness={0.9}
              roughness={0.17}
              emissive={CORE_COLOR}
              emissiveIntensity={pulse ? 0.4 : 0.08}
            />
          </mesh>
          <mesh scale={1.025}>
            <icosahedronGeometry args={[0.61, 0]} />
            <meshBasicMaterial
              color={emissiveColor(CORE_COLOR, pulse ? 2.3 : 1.3)}
              wireframe
              toneMapped={false}
            />
          </mesh>
        </group>
        <group ref={machinery}>
          {[
            [-0.25, 0.1, 0.52],
            [1.05, -0.35, -0.32],
            [0.48, 0.4, -0.96],
          ].map((rotation, index) => (
            <group key={index} rotation={rotation as [number, number, number]}>
              <mesh>
                <torusGeometry
                  args={[1.34 + index * 0.12, 0.026, 8, 100, Math.PI * 1.52]}
                />
                <meshStandardMaterial
                  color="#617083"
                  metalness={0.9}
                  roughness={0.21}
                />
              </mesh>
              <mesh rotation={[0, 0, Math.PI * 1.52]}>
                <torusGeometry
                  args={[1.34 + index * 0.12, 0.019, 8, 36, Math.PI * 0.32]}
                />
                <meshBasicMaterial
                  color={emissiveColor(
                    index === 1 ? "#a7d9ee" : CORE_COLOR,
                    2.4,
                  )}
                  toneMapped={false}
                />
              </mesh>
            </group>
          ))}
        </group>
        <pointLight
          color={CORE_COLOR}
          intensity={pulse ? 5 : 2.4}
          distance={6}
          decay={2}
        />
      </group>
    </group>
  );
}

function Station({
  node,
  index,
  selected,
  status,
  onSelect,
  motion,
  time,
  events,
}: {
  node: HarnessNode;
  index: number;
  selected: boolean;
  status: string;
  onSelect: Props["onSelect"];
  motion: boolean;
  time: number;
  events: TraceEvent[];
}) {
  const location = locations.get(node.id)!;
  const isAgent = node.kind === "agent";
  const color = status === "error" ? "#ff496d" : node.color;
  const active = status === "active";
  const recent = events.some(
    (event) =>
      event.kind !== "metadata" &&
      event.target === node.id &&
      time >= event.at &&
      time - event.at < 2.6,
  );
  const orb = useRef<THREE.Group>(null);
  const ring = useRef<THREE.Mesh>(null);
  const elapsed = useRef(index * 0.65);
  useFrame((_, delta) => {
    if (motion) elapsed.current += delta;
    if (orb.current) {
      orb.current.rotation.y = elapsed.current * (active ? 0.55 : 0.1);
      orb.current.position.y =
        (isAgent ? 1.28 : 0.8) + Math.sin(elapsed.current * 1.3) * 0.055;
    }
    if (ring.current) ring.current.rotation.z = elapsed.current * 0.18;
  });
  const width = isAgent ? 0.92 : 0.6;
  return (
    <group
      position={[location.x, 0, location.z]}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(node.id);
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "";
      }}
    >
      <mesh position={[0, 0, 0]} receiveShadow castShadow>
        <cylinderGeometry
          args={[width, width + 0.12, 0.38, isAgent ? 48 : 6]}
        />
        <meshStandardMaterial
          color="#142234"
          metalness={0.88}
          roughness={0.31}
        />
      </mesh>
      <mesh position={[0, 0.27, 0]} castShadow>
        <cylinderGeometry
          args={[width * 0.82, width, 0.16, isAgent ? 48 : 6]}
        />
        <meshStandardMaterial
          color="#24364a"
          metalness={0.82}
          roughness={0.22}
        />
      </mesh>
      <HardwareRing
        radius={width * 0.85}
        y={0.36}
        color={color}
        bright={active || recent || selected}
        thickness={isAgent ? 0.022 : 0.017}
      />
      <HardwareRing
        radius={width + 0.18}
        y={-0.173}
        color={color}
        bright={selected}
        thickness={0.01}
      />
      <group ref={orb} position={[0, isAgent ? 1.28 : 0.8, 0]}>
        <mesh castShadow>
          {isAgent ? (
            <octahedronGeometry args={[0.37, 0]} />
          ) : (
            <boxGeometry args={[0.3, 0.3, 0.3]} />
          )}
          <meshPhysicalMaterial
            color="#26364b"
            metalness={0.74}
            roughness={0.18}
            clearcoat={1}
            emissive={color}
            emissiveIntensity={active || recent ? 0.38 : 0.035}
          />
        </mesh>
        <mesh scale={1.012}>
          {isAgent ? (
            <octahedronGeometry args={[0.37, 0]} />
          ) : (
            <boxGeometry args={[0.3, 0.3, 0.3]} />
          )}
          <meshBasicMaterial
            wireframe
            color={emissiveColor(color, active || selected ? 2.4 : 0.75)}
            toneMapped={false}
          />
        </mesh>
        {isAgent && (
          <mesh ref={ring} rotation={[Math.PI / 2.8, 0, 0]}>
            <torusGeometry args={[0.6, 0.012, 6, 60, Math.PI * 1.6]} />
            <meshBasicMaterial
              color={emissiveColor(color, active ? 2 : 0.6)}
              toneMapped={false}
            />
          </mesh>
        )}
      </group>
      <mesh position={[0, isAgent ? 0.78 : 0.55, 0]}>
        <cylinderGeometry
          args={[0.09, width * 0.57, isAgent ? 0.83 : 0.38, 32, 1, true]}
        />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={active || recent ? 0.09 : 0.025}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
          toneMapped={false}
        />
      </mesh>
      {Array.from({ length: isAgent ? 6 : 3 }, (_, tick) => (
        <mesh
          key={tick}
          position={[(tick - (isAgent ? 2.5 : 1)) * 0.14, 0.21, width * 0.96]}
        >
          <boxGeometry args={[0.05, 0.027, 0.012]} />
          <meshBasicMaterial
            color={emissiveColor(color, active && tick <= 3 ? 2 : 0.3)}
            toneMapped={false}
          />
        </mesh>
      ))}
      <pointLight
        position={[0, 0.6, 0]}
        color={color}
        intensity={active || selected ? 1.9 : 0.35}
        distance={2.8}
      />
    </group>
  );
}

function Route({
  source,
  target,
  color,
  illuminated = false,
}: {
  source: string;
  target: string;
  color: string;
  illuminated?: boolean;
}) {
  const curve = useMemo(() => buildRoute(source, target), [source, target]);
  const geometry = useMemo(
    () =>
      curve
        ? new THREE.TubeGeometry(
            curve,
            64,
            illuminated ? 0.018 : 0.009,
            5,
            false,
          )
        : null,
    [curve, illuminated],
  );
  if (!geometry) return null;
  return (
    <mesh geometry={geometry}>
      <meshBasicMaterial
        color={emissiveColor(color, illuminated ? 0.7 : 0.2)}
        transparent
        opacity={illuminated ? 0.62 : 0.45}
        depthWrite={false}
        toneMapped={false}
      />
    </mesh>
  );
}

function Packet({ event, time }: { event: TraceEvent; time: number }) {
  const curve = useMemo(
    () => buildRoute(event.source, event.target),
    [event.source, event.target],
  );
  const age = time - event.at;
  const color =
    event.kind === "reply" || event.status === "done"
      ? "#a6f3db"
      : event.kind === "skill"
        ? "#f4c875"
        : event.source === "main"
          ? CORE_COLOR
          : nodeById.get(event.source)?.color || "#8de6ff";
  if (!curve || event.kind === "metadata" || age < 0 || age > 3.2) return null;
  const progress = Math.min(1, age / 2.8);
  return (
    <group>
      <Route
        source={event.source}
        target={event.target}
        color={color}
        illuminated
      />
      {Array.from({ length: 10 }, (_, index) => {
        const parameter = progress - index * 0.023;
        if (parameter < 0 || parameter > 1) return null;
        const point = curve.getPointAt(parameter);
        const size = index === 0 ? 0.083 : 0.054 * (1 - index / 11);
        return (
          <mesh key={index} position={point}>
            <sphereGeometry args={[size, 8, 6]} />
            <meshBasicMaterial
              color={emissiveColor(color, index === 0 ? 5 : 2.5)}
              transparent
              opacity={
                Math.max(0.08, 1 - index / 11) *
                (age > 2.8 ? Math.max(0, 1 - (age - 2.8) / 0.4) : 1)
              }
              toneMapped={false}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function Dust({ motion }: { motion: boolean }) {
  const group = useRef<THREE.Points>(null);
  const elapsed = useRef(0);
  const positions = useMemo(() => {
    const data = new Float32Array(110 * 3);
    for (let index = 0; index < 110; index++) {
      const angle = index * 2.39996;
      const radius = 2 + ((index * 37) % 73) / 10;
      data[index * 3] = Math.cos(angle) * radius;
      data[index * 3 + 1] = 1.4 + ((index * 19) % 51) / 12;
      data[index * 3 + 2] = Math.sin(angle) * radius;
    }
    return data;
  }, []);
  useFrame((_, delta) => {
    if (motion) elapsed.current += delta;
    if (group.current) group.current.rotation.y = elapsed.current * 0.008;
  });
  return (
    <points ref={group}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#7593af"
        size={0.021}
        transparent
        opacity={0.35}
        depthWrite={false}
        sizeAttenuation
      />
    </points>
  );
}

function Stage(
  props: Props & { onProject: (labels: ProjectedLabel[]) => void },
) {
  const { time, events, selected, onSelect, statuses, motion } = props;
  const size = useThree((state) => state.size);
  const distance = fittedDistance(size.width, size.height);
  const coreScale = Math.min(
    1.15,
    Math.max(1, 1.15 / (size.width / Math.max(size.height, 1))),
  );
  const recentEvents = events.filter(
    (event) =>
      event.kind !== "metadata" &&
      event.source !== event.target &&
      time >= event.at &&
      time - event.at <= 3.2,
  );
  return (
    <>
      <color attach="background" args={["#060a12"]} />
      <fog attach="fog" args={["#060a12", 22, 50]} />
      <ambientLight intensity={0.22} color="#9bb2cf" />
      <directionalLight
        position={[-6, 12, 7]}
        intensity={2.1}
        color="#c9dcfa"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        shadow-bias={-0.0005}
      />
      <directionalLight position={[8, 7, -8]} intensity={2.3} color="#6283b3" />
      <spotLight
        position={[-10, 5, -2]}
        color="#7de1ff"
        intensity={45}
        distance={25}
        angle={0.45}
        penumbra={1}
      />
      <spotLight
        position={[7, 5, 3]}
        color="#f3a0b5"
        intensity={28}
        distance={22}
        angle={0.5}
        penumbra={1}
      />
      <Environment resolution={128} frames={1}>
        <Lightformer
          intensity={3}
          color="#e2edff"
          scale={[12, 2, 1]}
          position={[0, 7, -7]}
          rotation={[Math.PI / 3, 0, 0]}
        />
        <Lightformer
          intensity={2}
          color="#9ad8ff"
          scale={[3, 8, 1]}
          position={[-8, 3, 0]}
          rotation={[0, Math.PI / 2, 0]}
        />
        <Lightformer
          intensity={1.6}
          color="#ffb5c9"
          scale={[3, 6, 1]}
          position={[8, 4, 2]}
          rotation={[0, -Math.PI / 2, 0]}
        />
      </Environment>
      <Floor />
      {nodes
        .filter((node) => node.kind !== "core")
        .map((node) => (
          <Route
            key={node.id}
            source="main"
            target={node.id}
            color={node.color}
          />
        ))}
      <Core
        time={time}
        events={events}
        selected={selected === "main"}
        onSelect={onSelect}
        status={statuses.main || "idle"}
        motion={motion}
        bodyScale={coreScale}
      />
      {agentNodes.map((node, index) => (
        <Station
          key={node.id}
          node={node}
          index={index}
          selected={selected === node.id}
          status={statuses[node.id] || "idle"}
          onSelect={onSelect}
          motion={motion}
          time={time}
          events={events}
        />
      ))}
      {skillNodes.map((node, index) => (
        <Station
          key={node.id}
          node={node}
          index={index}
          selected={selected === node.id}
          status={statuses[node.id] || "idle"}
          onSelect={onSelect}
          motion={motion}
          time={time}
          events={events}
        />
      ))}
      {recentEvents.map((event) => (
        <Packet key={event.id} event={event} time={time} />
      ))}
      <Dust motion={motion} />
      <OrbitControls
        makeDefault
        target={[0, 0.95, 0]}
        enablePan={false}
        enableDamping
        dampingFactor={0.08}
        minDistance={distance * 0.94}
        maxDistance={distance * 1.3}
        minPolarAngle={Math.PI / 5}
        maxPolarAngle={Math.PI / 2.6}
        minAzimuthAngle={-Math.PI / 4}
        maxAzimuthAngle={Math.PI / 4}
      />
      <ResponsiveCamera distance={distance} />
      <ProjectLabels onProject={props.onProject} />
      <EffectComposer multisampling={2}>
        <Bloom
          mipmapBlur
          luminanceThreshold={1}
          luminanceSmoothing={0.2}
          intensity={0.64}
          radius={0.63}
        />
        <Vignette eskil={false} offset={0.15} darkness={0.58} />
      </EffectComposer>
    </>
  );
}

export default function ControlScene(props: Props) {
  const [labels, setLabels] = useState<ProjectedLabel[]>([]);
  const onProject = useCallback(
    (next: ProjectedLabel[]) => setLabels(next),
    [],
  );
  return (
    <div
      className="control-scene"
      style={{ position: "relative", width: "100%", height: "100%" }}
    >
      <Canvas
        className="control-canvas"
        shadows
        dpr={[1, 1.6]}
        camera={{ position: [0, 11, 17], fov: 42, near: 0.1, far: 100 }}
        gl={{
          antialias: false,
          powerPreference: "high-performance",
          alpha: false,
        }}
      >
        <Stage {...props} onProject={onProject} />
      </Canvas>
      <div
        className="scene-label-overlay"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 3,
        }}
      >
        {labels.map((position) => {
          const node = nodeById.get(position.id)!;
          const status = props.statuses[node.id] || "idle";
          const core = node.kind === "core";
          const color =
            status === "error" ? CORE_COLOR : core ? CORE_COLOR : node.color;
          const skillIndex = skillNodes.findIndex(
            (skill) => skill.id === node.id,
          );
          return (
            <div
              key={node.id}
              className="scene-label-anchor"
              style={{
                position: "absolute",
                left: position.x,
                top: position.y,
                transform: "translate(-50%, -50%)",
                display: position.visible ? "block" : "none",
                pointerEvents: "none",
                zIndex: core ? 2 : 1,
              }}
            >
              <button
                className={`scene-label ${core ? "core-label" : ""} ${props.selected === node.id ? "selected" : ""}`}
                style={
                  {
                    "--node-color": color,
                    pointerEvents: "auto",
                  } as CSSProperties
                }
                onClick={() => props.onSelect(node.id)}
                aria-label={`${core ? "MAIN CORE" : node.label} 노드 선택`}
              >
                <span className="label-type">
                  {core
                    ? "ORCHESTRATOR"
                    : node.kind === "agent"
                      ? "RESEARCH AGENT"
                      : `SKILL ${String(skillIndex + 1).padStart(2, "0")}`}
                </span>
                <span className="label-name">
                  {core ? "MAIN CORE" : node.label}
                </span>
                <span className="label-state">
                  {statusLabel[status] || status.toUpperCase()}
                </span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
