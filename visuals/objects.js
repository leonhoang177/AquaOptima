/**
 * objects.js -- Food, probiotic, O₂, fecal, dead fish, pollutant meshes.
 *
 * Uses object pooling per type.
 */

import * as THREE from "three";

// ── Pool sizes ──
const MAX_FOOD = 60;
const MAX_PROBIOTIC = 60;
const MAX_OXYGEN = 80;
const MAX_FECAL = 40;
const MAX_DEAD_FISH = 20;
const MAX_POLLUTANT = 30;

// ── Colors ──
const FOOD_COLOR = 0xffee55;
const FOOD_EDGE = 0xccaa22;
const PROBIOTIC_COLOR = 0x55ffcc;
const PROBIOTIC_EDGE = 0x22aa88;
const OXYGEN_COLOR = 0x88ccff;
const FECAL_COLOR = 0x8b6914;
const DEAD_FISH_COLOR = 0xcc2222;
const POLLUTANT_COLOR = 0xcc6600;

let pools = {};

/**
 * Create a pool of meshes for a given type.
 */
function _createPool(scene, count, createFn) {
  const arr = [];
  for (let i = 0; i < count; i++) {
    const mesh = createFn();
    mesh.visible = false;
    scene.add(mesh);
    arr.push(mesh);
  }
  return arr;
}

/**
 * Initialize all object pools.
 */
export function initObjects(sceneCtx, pond) {
  const { scene } = sceneCtx;

  // ── Food (small yellow spheres) ──
  pools.food = _createPool(scene, MAX_FOOD, () => {
    const geo = new THREE.SphereGeometry(0.8, 8, 6);
    const mat = new THREE.MeshPhongMaterial({
      color: FOOD_COLOR,
      emissive: FOOD_EDGE,
      emissiveIntensity: 0.2,
    });
    return new THREE.Mesh(geo, mat);
  });

  // ── Probiotic (small green spheres with cross) ──
  pools.probiotic = _createPool(scene, MAX_PROBIOTIC, () => {
    const group = new THREE.Group();

    const geo = new THREE.SphereGeometry(0.8, 8, 6);
    const mat = new THREE.MeshPhongMaterial({
      color: PROBIOTIC_COLOR,
      emissive: PROBIOTIC_EDGE,
      emissiveIntensity: 0.2,
    });
    group.add(new THREE.Mesh(geo, mat));

    // Cross (two thin boxes)
    const crossMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const h = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.15, 0.15), crossMat);
    group.add(h);
    const v = new THREE.Mesh(new THREE.BoxGeometry(0.15, 1.0, 0.15), crossMat);
    group.add(v);

    return group;
  });

  // ── Oxygen (small translucent blue spheres) ──
  pools.oxygen = _createPool(scene, MAX_OXYGEN, () => {
    const geo = new THREE.SphereGeometry(0.5, 8, 6);
    const mat = new THREE.MeshPhongMaterial({
      color: OXYGEN_COLOR,
      transparent: true,
      opacity: 0.45,
      emissive: OXYGEN_COLOR,
      emissiveIntensity: 0.15,
    });
    return new THREE.Mesh(geo, mat);
  });

  // ── Fecal (small brown spheres, scaled by value) ──
  pools.fecal = _createPool(scene, MAX_FECAL, () => {
    const geo = new THREE.SphereGeometry(0.6, 6, 5);
    const mat = new THREE.MeshPhongMaterial({
      color: FECAL_COLOR,
      shininess: 5,
    });
    return new THREE.Mesh(geo, mat);
  });

  // ── Dead fish (red elongated shape, rotated) ──
  pools.dead_fish = _createPool(scene, MAX_DEAD_FISH, () => {
    const group = new THREE.Group();

    // Body
    const bodyGeo = new THREE.SphereGeometry(1, 8, 6);
    const bodyMat = new THREE.MeshPhongMaterial({
      color: DEAD_FISH_COLOR,
      emissive: 0x881111,
      emissiveIntensity: 0.2,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.scale.set(1.5, 0.6, 0.6);
    group.add(body);

    // Tail
    const tailGeo = new THREE.ConeGeometry(0.4, 0.8, 5);
    const tailMat = new THREE.MeshPhongMaterial({ color: 0xaa1111 });
    const tail = new THREE.Mesh(tailGeo, tailMat);
    tail.rotation.z = Math.PI / 2;
    tail.position.set(-1.8, 0, 0);
    group.add(tail);

    // X eyes (two crossed lines)
    const xMat = new THREE.MeshBasicMaterial({ color: 0xff8888 });
    const x1 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.08), xMat);
    x1.position.set(0.6, 0.2, 0.35);
    x1.rotation.z = Math.PI / 4;
    group.add(x1);
    const x2 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.08), xMat);
    x2.position.set(0.6, 0.2, 0.35);
    x2.rotation.z = -Math.PI / 4;
    group.add(x2);

    // Tilt the whole dead fish
    group.rotation.z = 0.4;
    group.rotation.x = 0.2;

    return group;
  });

  // ── Pollutant (orange octahedron as warning shape) ──
  pools.pollutant = _createPool(scene, MAX_POLLUTANT, () => {
    const geo = new THREE.OctahedronGeometry(1, 0);
    const mat = new THREE.MeshPhongMaterial({
      color: POLLUTANT_COLOR,
      transparent: true,
      opacity: 0.7,
      emissive: POLLUTANT_COLOR,
      emissiveIntensity: 0.15,
    });
    return new THREE.Mesh(geo, mat);
  });

  return { pools };
}

/**
 * Update all object meshes from frame data.
 */
export function updateObjects(objectsCtx, frame) {
  const objData = frame.objects || [];

  // Sort objects by type for pool assignment
  const byType = {
    food: [],
    probiotic: [],
    oxygen: [],
    fecal: [],
    dead_fish: [],
    pollutant: [],
  };

  for (const obj of objData) {
    if (byType[obj.type]) {
      byType[obj.type].push(obj);
    }
  }

  // ── Update each pool ──
  _updatePool(pools.food, byType.food, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    const s = 0.6 + d.value * 0.1;
    mesh.scale.setScalar(s);
  });

  _updatePool(pools.probiotic, byType.probiotic, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    const s = 0.6 + d.value * 0.08;
    mesh.scale.setScalar(s);
  });

  _updatePool(pools.oxygen, byType.oxygen, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    mesh.scale.setScalar(0.5);
  });

  _updatePool(pools.fecal, byType.fecal, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    const s = 0.5 + d.value * 0.12;
    mesh.scale.setScalar(s);
  });

  _updatePool(pools.dead_fish, byType.dead_fish, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    const s = 0.8 + d.value * 0.1;
    mesh.scale.setScalar(s);
  });

  _updatePool(pools.pollutant, byType.pollutant, (mesh, d) => {
    mesh.position.set(d.x, d.y, d.z);
    const s = 0.6 + d.value * 0.15;
    mesh.scale.setScalar(s);
    // Slow rotation for visual interest
    mesh.rotation.y += 0.05;
    mesh.rotation.x += 0.03;
  });
}

/**
 * Generic pool updater: show first N, apply transform, hide rest.
 */
function _updatePool(pool, dataArr, applyFn) {
  for (let i = 0; i < pool.length; i++) {
    if (i < dataArr.length) {
      pool[i].visible = true;
      applyFn(pool[i], dataArr[i]);
    } else {
      pool[i].visible = false;
    }
  }
}
