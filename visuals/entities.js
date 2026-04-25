/**
 * entities.js -- Fish meshes, obstacle boxes, hazard spheres.
 *
 * Uses object pooling: pre-allocate max expected meshes,
 * show/hide per frame instead of creating/destroying.
 */

import * as THREE from "three";

// ── Pool sizes ──
const MAX_FISH = 60;
const MAX_OBSTACLES = 30;
const MAX_HAZARDS = 40;

// ── Colors ──
const FISH_COLOR = 0x3a5068;
const FISH_TAIL_COLOR = 0x2e4458;
const OBSTACLE_COLOR = 0x1a3050;
const OBSTACLE_EDGE_COLOR = 0x2a5070;

const GLOW_INFECTED = 0xffaa00;
const GLOW_PARASITE = 0xcc44ff;
const GLOW_BOOSTING = 0x55ffcc;

const HAZARD_COLORS = {
  nh3: { color: 0x00ff64, opacity: 0.15 },
  disease: { color: 0xffb400, opacity: 0.15 },
  parasite: { color: 0xc850ff, opacity: 0.12 },
};

let fishPool = [];
let obstaclePool = [];
let hazardPool = [];
let glowPool = [];

/**
 * Initialize entity pools and add to scene.
 */
export function initEntities(sceneCtx, pond) {
  const { scene } = sceneCtx;

  // ── Fish pool ──
  // Each fish = group containing body (ellipsoid), tail, eye
  for (let i = 0; i < MAX_FISH; i++) {
    const group = new THREE.Group();
    group.visible = false;

    // Body (sphere scaled to ellipsoid)
    const bodyGeo = new THREE.SphereGeometry(1, 12, 8);
    const bodyMat = new THREE.MeshPhongMaterial({
      color: FISH_COLOR,
      shininess: 30,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.name = "fishBody";
    group.add(body);

    // Tail (cone)
    const tailGeo = new THREE.ConeGeometry(0.55, 1, 6);
    const tailMat = new THREE.MeshPhongMaterial({
      color: FISH_TAIL_COLOR,
      transparent: true,
      opacity: 0.8,
    });
    const tail = new THREE.Mesh(tailGeo, tailMat);
    tail.name = "fishTail";
    tail.rotation.z = Math.PI / 2; // point backward
    group.add(tail);

    // Eye (small white + black sphere)
    const eyeWhiteGeo = new THREE.SphereGeometry(0.15, 6, 6);
    const eyeWhiteMat = new THREE.MeshBasicMaterial({ color: 0xbbbbbb });
    const eyeWhite = new THREE.Mesh(eyeWhiteGeo, eyeWhiteMat);
    eyeWhite.name = "eyeWhite";
    group.add(eyeWhite);

    const eyePupilGeo = new THREE.SphereGeometry(0.08, 6, 6);
    const eyePupilMat = new THREE.MeshBasicMaterial({ color: 0x111111 });
    const eyePupil = new THREE.Mesh(eyePupilGeo, eyePupilMat);
    eyePupil.name = "eyePupil";
    group.add(eyePupil);

    // Store metadata
    group.userData = { fishId: -1, bodySize: 1 };

    scene.add(group);
    fishPool.push(group);
  }

  // ── Glow rings pool (3 per fish max: infected, parasite, boosting) ──
  for (let i = 0; i < MAX_FISH * 3; i++) {
    const ringGeo = new THREE.RingGeometry(1, 1.15, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.6,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.visible = false;
    scene.add(ring);
    glowPool.push(ring);
  }

  // ── Obstacle pool ──
  for (let i = 0; i < MAX_OBSTACLES; i++) {
    const boxGeo = new THREE.BoxGeometry(1, 1, 1);
    const boxMat = new THREE.MeshPhongMaterial({
      color: OBSTACLE_COLOR,
      transparent: true,
      opacity: 0.7,
    });
    const box = new THREE.Mesh(boxGeo, boxMat);
    box.visible = false;

    // Edge wireframe
    const edgeGeo = new THREE.EdgesGeometry(boxGeo);
    const edgeMat = new THREE.LineBasicMaterial({ color: OBSTACLE_EDGE_COLOR });
    const edges = new THREE.LineSegments(edgeGeo, edgeMat);
    box.add(edges);

    scene.add(box);
    obstaclePool.push(box);
  }

  // ── Hazard pool (transparent spheres) ──
  for (let i = 0; i < MAX_HAZARDS; i++) {
    const sphereGeo = new THREE.SphereGeometry(1, 16, 12);
    const sphereMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.15,
      depthWrite: false,
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.visible = false;

    // Wireframe ring for visibility
    const wireGeo = new THREE.EdgesGeometry(new THREE.SphereGeometry(1, 12, 8));
    const wireMat = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.3,
    });
    const wire = new THREE.LineSegments(wireGeo, wireMat);
    sphere.add(wire);

    scene.add(sphere);
    hazardPool.push(sphere);
  }

  return {
    fishPool,
    obstaclePool,
    hazardPool,
    glowPool,
  };
}

/**
 * Update all entities from a single frame of data.
 */
export function updateEntities(entitiesCtx, frame, sceneCtx) {
  const { fishPool, obstaclePool, hazardPool, glowPool } = entitiesCtx;
  const camera = sceneCtx.camera;

  // ── Update fish ──
  const fishData = frame.fish || [];
  for (let i = 0; i < fishPool.length; i++) {
    const group = fishPool[i];
    if (i < fishData.length && fishData[i].alive) {
      const fd = fishData[i];
      const bs = Math.max(1.5, fd.body_size * 0.35);
      group.visible = true;
      group.position.set(fd.x, fd.y, fd.z);
      group.userData.fishId = fd.id;
      group.userData.bodySize = bs;
      group.userData.fishData = fd;

      // Scale body
      const body = group.children[0];
      body.scale.set(bs, bs * 0.55, bs * 0.55);

      // Position tail
      const tail = group.children[1];
      tail.position.set(-bs - 0.5, 0, 0);
      tail.scale.set(bs * 0.4, bs * 0.5, bs * 0.4);

      // Position eyes
      const eyeWhite = group.children[2];
      eyeWhite.position.set(bs * 0.5, bs * 0.15, bs * 0.3);
      eyeWhite.scale.setScalar(bs * 0.8);

      const eyePupil = group.children[3];
      eyePupil.position.set(bs * 0.55, bs * 0.15, bs * 0.35);
      eyePupil.scale.setScalar(bs * 0.8);

      // Face direction of movement
      if (Math.abs(fd.vx) > 0.01 || Math.abs(fd.vy) > 0.01) {
        const angle = Math.atan2(fd.vy, fd.vx);
        group.rotation.z = angle;
      }
    } else {
      group.visible = false;
      group.userData.fishId = -1;
      group.userData.fishData = null;
    }
  }

  // ── Update glow rings ──
  let glowIdx = 0;
  for (let i = 0; i < fishData.length && i < fishPool.length; i++) {
    const fd = fishData[i];
    const group = fishPool[i];
    if (!fd.alive || !group.visible) continue;

    const bs = group.userData.bodySize;
    const glows = [];
    if (fd.is_infected) glows.push(GLOW_INFECTED);
    if (fd.has_parasite) glows.push(GLOW_PARASITE);
    if (fd.is_boosting) glows.push(GLOW_BOOSTING);

    for (let gi = 0; gi < glows.length; gi++) {
      if (glowIdx >= glowPool.length) break;
      const ring = glowPool[glowIdx++];
      ring.visible = true;
      const radius = bs + 1.5 + gi * 1.5;
      ring.scale.set(radius, radius, radius);
      ring.position.copy(group.position);
      ring.material.color.setHex(glows[gi]);
      ring.material.opacity = 0.5;
      // Billboard: face camera
      ring.lookAt(camera.position);
    }
  }
  // Hide unused glow rings
  for (let i = glowIdx; i < glowPool.length; i++) {
    glowPool[i].visible = false;
  }

  // ── Update obstacles ──
  const obsData = frame.obstacles || [];
  for (let i = 0; i < obstaclePool.length; i++) {
    const box = obstaclePool[i];
    if (i < obsData.length) {
      const od = obsData[i];
      box.visible = true;
      box.scale.set(od.w, od.h, od.d);
      box.position.set(od.x + od.w / 2, od.y + od.h / 2, od.z + od.d / 2);
    } else {
      box.visible = false;
    }
  }

  // ── Update hazards ──
  const hazData = frame.hazards || [];
  for (let i = 0; i < hazardPool.length; i++) {
    const sphere = hazardPool[i];
    if (i < hazData.length) {
      const hd = hazData[i];
      const hc = HAZARD_COLORS[hd.type] || HAZARD_COLORS.nh3;
      sphere.visible = true;
      sphere.scale.setScalar(hd.r);
      sphere.position.set(hd.x, hd.y, hd.z);
      sphere.material.color.setHex(hc.color);
      sphere.material.opacity = hc.opacity;
      // Update wireframe color
      const wire = sphere.children[0];
      if (wire) {
        wire.material.color.setHex(hc.color);
        wire.material.opacity = hc.opacity + 0.15;
      }
    } else {
      sphere.visible = false;
    }
  }
}

/**
 * Get the fish mesh pool (for raycasting in selection.js).
 */
export function getFishBodies() {
  const bodies = [];
  for (const group of fishPool) {
    if (group.visible && group.children[0]) {
      // Return the body mesh for raycasting
      bodies.push(group);
    }
  }
  return bodies;
}
