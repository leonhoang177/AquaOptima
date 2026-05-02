/**
 * entities.js -- Fish, obstacles, hazards.
 * Fish color 40% brighter. Selected fish: neon green emissive.
 * Disease/parasite opacity reduced 30%.
 */

import * as THREE from "three";
import { getSelectedFishId } from "./selection.js";

const MAX_FISH = 60,
  MAX_OBSTACLES = 30,
  MAX_HAZARDS = 40;

const FISH_COLOR = 0xabd4f0;
const FISH_SELECTED_EMISSIVE = 0x33ff66;
const FISH_SELECTED_EMISSIVE_INTENSITY = 0.6;
const FISH_TAIL_COLOR = 0x96c2dd;
const OBSTACLE_COLOR = 0x5a3a28;
const OBSTACLE_EDGE_COLOR = 0x7a5a40;
const GLOW_INFECTED = 0xffaa00;
const GLOW_PARASITE = 0xcc44ff;

const HAZARD_COLORS = {
  nh3: { color: 0x00ff64, opacity: 0.12 },
  disease: { color: 0xffb400, opacity: 0.126 },
  parasite: { color: 0xc850ff, opacity: 0.105 },
};

let fishPool = [],
  obstaclePool = [],
  hazardSpherePool = [],
  hazardDiscPool = [],
  glowPool = [];
let selectionLight = null;

export function initEntities(sceneCtx, pond) {
  const { scene } = sceneCtx;

  selectionLight = new THREE.PointLight(0x33ff66, 0, 30);
  selectionLight.visible = false;
  scene.add(selectionLight);

  for (let i = 0; i < MAX_FISH; i++) {
    const g = new THREE.Group();
    g.visible = false;
    const bodyMat = new THREE.MeshPhongMaterial({
      color: FISH_COLOR,
      shininess: 50,
      emissive: 0x000000,
      emissiveIntensity: 0,
    });
    g.add(new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), bodyMat));
    const tailMat = new THREE.MeshPhongMaterial({
      color: FISH_TAIL_COLOR,
      transparent: true,
      opacity: 0.85,
    });
    const tail = new THREE.Mesh(new THREE.ConeGeometry(0.55, 1, 6), tailMat);
    tail.rotation.z = Math.PI / 2;
    g.add(tail);
    g.add(
      new THREE.Mesh(
        new THREE.SphereGeometry(0.15, 6, 6),
        new THREE.MeshBasicMaterial({ color: 0xeeeeee }),
      ),
    );
    g.add(
      new THREE.Mesh(
        new THREE.SphereGeometry(0.08, 6, 6),
        new THREE.MeshBasicMaterial({ color: 0x111111 }),
      ),
    );
    g.userData = { fishId: -1, bodySize: 1, fishData: null };
    scene.add(g);
    fishPool.push(g);
  }

  for (let i = 0; i < MAX_FISH * 2; i++) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(1, 1.1, 32),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    ring.visible = false;
    scene.add(ring);
    glowPool.push(ring);
  }

  for (let i = 0; i < MAX_OBSTACLES; i++) {
    const box = new THREE.Mesh(
      new THREE.BoxGeometry(1, 1, 1),
      new THREE.MeshPhongMaterial({
        color: OBSTACLE_COLOR,
        transparent: true,
        opacity: 0.75,
        shininess: 10,
      }),
    );
    box.visible = false;
    box.add(
      new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1)),
        new THREE.LineBasicMaterial({ color: OBSTACLE_EDGE_COLOR }),
      ),
    );
    scene.add(box);
    obstaclePool.push(box);
  }

  for (let i = 0; i < MAX_HAZARDS; i++) {
    const s = new THREE.Mesh(
      new THREE.SphereGeometry(1, 20, 14),
      new THREE.MeshPhongMaterial({
        color: 0x00ff64,
        transparent: true,
        opacity: 0.12,
        depthWrite: false,
        shininess: 80,
        emissive: 0x00ff64,
        emissiveIntensity: 0.05,
      }),
    );
    s.visible = false;
    scene.add(s);
    hazardSpherePool.push(s);
  }

  for (let i = 0; i < MAX_HAZARDS; i++) {
    const cyl = new THREE.Mesh(
      new THREE.CylinderGeometry(1, 1, 1, 24, 1, true),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.12,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    cyl.visible = false;
    const capMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const cap1 = new THREE.Mesh(new THREE.CircleGeometry(1, 24), capMat);
    cap1.rotation.x = Math.PI / 2;
    cap1.position.y = 0.5;
    cyl.add(cap1);
    const cap2 = cap1.clone();
    cap2.position.y = -0.5;
    cyl.add(cap2);
    scene.add(cyl);
    hazardDiscPool.push(cyl);
  }

  return {
    fishPool,
    obstaclePool,
    hazardSpherePool,
    hazardDiscPool,
    glowPool,
    selectionLight,
  };
}

export function updateEntities(entitiesCtx, frame, sceneCtx) {
  const {
    fishPool,
    obstaclePool,
    hazardSpherePool,
    hazardDiscPool,
    glowPool,
    selectionLight,
  } = entitiesCtx;
  const camera = sceneCtx.camera;
  const selectedId = getSelectedFishId();
  const FLOOR_HAZ_H = 12.0;

  const fishData = frame.fish || [];
  let selectedGroup = null;

  for (let i = 0; i < fishPool.length; i++) {
    const g = fishPool[i];
    if (i < fishData.length && fishData[i].alive) {
      const fd = fishData[i];
      const bs = Math.max(1.5, fd.body_size * 0.35);
      g.visible = true;
      g.position.set(fd.x, fd.y, fd.z);
      g.userData.fishId = fd.id;
      g.userData.bodySize = bs;
      g.userData.fishData = fd;

      const body = g.children[0];
      body.scale.set(bs, bs * 0.55, bs * 0.55);
      const isSel = fd.id === selectedId;
      body.material.color.setHex(FISH_COLOR);
      body.material.emissive.setHex(isSel ? FISH_SELECTED_EMISSIVE : 0x000000);
      body.material.emissiveIntensity = isSel
        ? FISH_SELECTED_EMISSIVE_INTENSITY
        : 0;
      if (isSel) selectedGroup = g;

      g.children[1].position.set(-bs - 0.5, 0, 0);
      g.children[1].scale.set(bs * 0.4, bs * 0.5, bs * 0.4);
      g.children[2].position.set(bs * 0.5, bs * 0.15, bs * 0.3);
      g.children[2].scale.setScalar(bs * 0.8);
      g.children[3].position.set(bs * 0.55, bs * 0.15, bs * 0.35);
      g.children[3].scale.setScalar(bs * 0.8);

      if (Math.abs(fd.vx) > 0.01 || Math.abs(fd.vy) > 0.01)
        g.rotation.z = Math.atan2(fd.vy, fd.vx);
    } else {
      g.visible = false;
      g.userData.fishId = -1;
      g.userData.fishData = null;
    }
  }

  if (selectedGroup) {
    selectionLight.visible = true;
    selectionLight.position.copy(selectedGroup.position);
    selectionLight.color.setHex(0x33ff66);
    selectionLight.intensity = 1.5;
  } else {
    selectionLight.visible = false;
  }

  let gi = 0;
  for (let i = 0; i < fishData.length && i < fishPool.length; i++) {
    const fd = fishData[i];
    const grp = fishPool[i];
    if (!fd.alive || !grp.visible) continue;
    const bs = grp.userData.bodySize;
    const rings = [];
    if (fd.is_infected) rings.push({ color: GLOW_INFECTED, radius: bs + 0.4 });
    if (fd.has_parasite) rings.push({ color: GLOW_PARASITE, radius: bs + 0.9 });
    for (const r of rings) {
      if (gi >= glowPool.length) break;
      const ring = glowPool[gi++];
      ring.visible = true;
      ring.scale.set(r.radius, r.radius, r.radius);
      ring.position.copy(grp.position);
      ring.material.color.setHex(r.color);
      ring.material.opacity = 0.6;
      ring.lookAt(camera.position);
    }
  }
  for (let i = gi; i < glowPool.length; i++) glowPool[i].visible = false;

  const obsData = frame.obstacles || [];
  for (let i = 0; i < obstaclePool.length; i++) {
    if (i < obsData.length) {
      const od = obsData[i];
      obstaclePool[i].visible = true;
      obstaclePool[i].scale.set(od.w, od.h, od.d);
      obstaclePool[i].position.set(
        od.x + od.w / 2,
        od.y + od.h / 2,
        od.z + od.d / 2,
      );
    } else obstaclePool[i].visible = false;
  }

  const hazData = frame.hazards || [];
  const sphHaz = [],
    flrHaz = [];
  for (const hd of hazData) {
    if (hd.is_floor) flrHaz.push(hd);
    else sphHaz.push(hd);
  }

  for (let i = 0; i < hazardSpherePool.length; i++) {
    const s = hazardSpherePool[i];
    if (i < sphHaz.length) {
      const hd = sphHaz[i];
      const hc = HAZARD_COLORS[hd.type] || HAZARD_COLORS.nh3;
      s.visible = true;
      s.scale.setScalar(hd.r);
      s.position.set(hd.x, hd.y, hd.z);
      s.material.color.setHex(hc.color);
      s.material.opacity = hc.opacity;
      s.material.emissive.setHex(hc.color);
      s.material.emissiveIntensity = 0.05;
    } else s.visible = false;
  }

  for (let i = 0; i < hazardDiscPool.length; i++) {
    const c = hazardDiscPool[i];
    if (i < flrHaz.length) {
      const hd = flrHaz[i];
      const hc = HAZARD_COLORS[hd.type] || HAZARD_COLORS.disease;
      c.visible = true;
      c.scale.set(hd.r, FLOOR_HAZ_H, hd.r);
      c.rotation.x = Math.PI / 2;
      c.position.set(hd.x, hd.y, hd.z - FLOOR_HAZ_H * 0.5);
      c.material.color.setHex(hc.color);
      c.material.opacity = hc.opacity;
      for (const ch of c.children) {
        ch.material.color.setHex(hc.color);
        ch.material.opacity = hc.opacity + 0.04;
      }
    } else c.visible = false;
  }
}

export function getFishBodies() {
  return fishPool.filter((g) => g.visible && g.children[0]);
}
