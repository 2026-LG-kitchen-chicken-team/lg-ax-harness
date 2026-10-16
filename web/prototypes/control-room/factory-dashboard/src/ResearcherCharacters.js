import * as THREE from 'three';
import { RESEARCHER_ROLES, researcherPose } from './researcher-motion.js';

const PLACEMENTS = {
  overview: [-2.90, .06, 1.40], retrieve: [-6.80, .42, 1.48],
  structure: [-3.90, .42, -3.42], compare: [3.18, .42, -2.57],
  concept: [5.80, .06, 5.10], validate: [-1.60, .06, 8.60],
};

// The original generated PNGs remain intact. UV regions select each figure;
// alpha bounds and the feet anchor keep the two work poses registered.
function atlasFrames(image, columns, rows) {
  const canvas = document.createElement('canvas');
  canvas.width = image.width; canvas.height = image.height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(image, 0, 0);
  const pixels = ctx.getImageData(0, 0, image.width, image.height).data;
  return Array.from({ length: columns * rows }, (_, index) => {
    const column = index % columns, row = Math.floor(index / columns);
    const x0 = Math.round(column * image.width / columns), x1 = Math.round((column + 1) * image.width / columns);
    const y0 = Math.round(row * image.height / rows), y1 = Math.round((row + 1) * image.height / rows);
    const xs = new Uint16Array(x1 - x0), ys = new Uint16Array(y1 - y0);
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      if (pixels[(y * image.width + x) * 4 + 3] > 220) { xs[x - x0]++; ys[y - y0]++; }
    }
    const occupiedX = Array.from(xs.keys()).filter(x => xs[x] > 6);
    const occupiedY = Array.from(ys.keys()).filter(y => ys[y] > 8);
    if (!occupiedX.length || !occupiedY.length) throw Error('연구원 이미지 영역을 찾지 못했습니다.');
    const left = x0 + Math.max(0, occupiedX[0] - 3), right = x0 + Math.min(xs.length, occupiedX.at(-1) + 4);
    const top = y0 + Math.max(0, occupiedY[0] - 3), bottom = y0 + Math.min(ys.length, occupiedY.at(-1) + 4);
    let footSum = 0, footCount = 0;
    for (let y = Math.round(bottom - (bottom - top) * .12); y < bottom; y++) for (let x = left; x < right; x++) {
      if (pixels[(y * image.width + x) * 4 + 3] > 220) { footSum += x; footCount++; }
    }
    const texture = new THREE.Texture(image);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.repeat.set((right - left) / image.width, (bottom - top) / image.height);
    texture.offset.set(left / image.width, 1 - bottom / image.height);
    texture.needsUpdate = true;
    return { texture, aspect: (right - left) / (bottom - top), anchor: ((footCount ? footSum / footCount : (left + right) / 2) - left) / (right - left) };
  });
}

export function createResearchers(scene, onLoadState) {
  let disposed = false, frames = null;
  const loader = new THREE.ImageLoader(), textures = [];
  const ringGeometry = new THREE.RingGeometry(.30, .35, 28);
  const people = RESEARCHER_ROLES.map(id => {
    const group = new THREE.Group(); group.userData.station = id;
    group.position.set(...PLACEMENTS[id]); scene.add(group);
    const material = new THREE.SpriteMaterial({ transparent: true, alphaTest: .55, depthWrite: false, toneMapped: false });
    const sprite = new THREE.Sprite(material); sprite.visible = false; group.add(sprite);
    const ringMaterial = new THREE.MeshBasicMaterial({ color: '#f69646', transparent: true, opacity: .65, depthWrite: false, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial); ring.rotation.x = -Math.PI / 2; ring.position.y = .018; ring.visible = false; group.add(ring);
    return { id, group, sprite, material, ring, ringMaterial, current: null };
  });
  Promise.all([
    loader.loadAsync('/characters/researcher-team-v1.png'),
    loader.loadAsync('/characters/researcher-work-v1.png'),
  ]).then(([idle, work]) => {
    if (disposed) return;
    frames = { idle: atlasFrames(idle, 3, 2), work: atlasFrames(work, 6, 2) };
    textures.push(...frames.idle.map(f => f.texture), ...frames.work.map(f => f.texture));
    onLoadState?.('ready');
  }).catch(() => { if (!disposed) onLoadState?.('error'); });
  return {
    update(options) {
      if (!frames || disposed) return;
      people.forEach((person, index) => {
        const pose = researcherPose(person.id, options);
        const frame = pose.working ? frames.work[index + pose.frame * 6] : frames.idle[index];
        if (person.current !== frame) {
          person.material.map = frame.texture; person.material.needsUpdate = true;
          person.sprite.scale.set(1.82 * frame.aspect, 1.82, 1);
          person.sprite.center.set(frame.anchor, 0); person.current = frame;
        }
        person.sprite.visible = true; person.ring.visible = pose.working;
        person.sprite.position.y = pose.working && !options.reducedMotion ? Math.sin(options.elapsed * 4.4) * .012 : 0;
      });
    },
    dispose() { disposed = true; people.forEach(p => { scene.remove(p.group); p.material.dispose(); p.ringMaterial.dispose(); }); ringGeometry.dispose(); textures.forEach(t => t.dispose()); },
  };
}
