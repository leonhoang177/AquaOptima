/**
 * objects.js -- Food, probiotic, O2, fecal, dead fish, pollutant, plant meshes.
 * Colors: Food=orange, O2=white (40% brighter), Pollutant=darker blue.
 */

import * as THREE from "three";

const MAX_FOOD = 600,
  MAX_PROBIOTIC = 100,
  MAX_OXYGEN = 300,
  MAX_FECAL = 500;
const MAX_DEAD_FISH = 100,
  MAX_POLLUTANT = 500,
  MAX_PLANT = 200;

let pools = {};

function _pool(scene, n, fn) {
  const a = [];
  for (let i = 0; i < n; i++) {
    const m = fn();
    m.visible = false;
    scene.add(m);
    a.push(m);
  }
  return a;
}

export function initObjects(sceneCtx, pond) {
  const { scene } = sceneCtx;

  // Food: orange
  pools.food = _pool(
    scene,
    MAX_FOOD,
    () =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.8, 8, 6),
        new THREE.MeshPhongMaterial({
          color: 0xff8833,
          emissive: 0xcc6611,
          emissiveIntensity: 0.2,
        }),
      ),
  );

  pools.probiotic = _pool(scene, MAX_PROBIOTIC, () => {
    const g = new THREE.Group();
    g.add(
      new THREE.Mesh(
        new THREE.SphereGeometry(0.8, 8, 6),
        new THREE.MeshPhongMaterial({
          color: 0x55ffcc,
          emissive: 0x22aa88,
          emissiveIntensity: 0.2,
        }),
      ),
    );
    const cm = new THREE.MeshBasicMaterial({ color: 0xffffff });
    g.add(new THREE.Mesh(new THREE.BoxGeometry(1, 0.15, 0.15), cm));
    g.add(new THREE.Mesh(new THREE.BoxGeometry(0.15, 1, 0.15), cm));
    return g;
  });

  // Oxygen: bright white (40% brighter)
  pools.oxygen = _pool(
    scene,
    MAX_OXYGEN,
    () =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.5, 8, 6),
        new THREE.MeshPhongMaterial({
          color: 0xffffff,
          transparent: true,
          opacity: 0.75,
          emissive: 0xffffff,
          emissiveIntensity: 0.35,
        }),
      ),
  );

  pools.fecal = _pool(
    scene,
    MAX_FECAL,
    () =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.6, 6, 5),
        new THREE.MeshPhongMaterial({ color: 0x8b6914, shininess: 5 }),
      ),
  );

  pools.dead_fish = _pool(scene, MAX_DEAD_FISH, () => {
    const g = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.SphereGeometry(1, 8, 6),
      new THREE.MeshPhongMaterial({
        color: 0xcc2222,
        emissive: 0x881111,
        emissiveIntensity: 0.2,
      }),
    );
    body.scale.set(1.5, 0.6, 0.6);
    g.add(body);
    const tail = new THREE.Mesh(
      new THREE.ConeGeometry(0.4, 0.8, 5),
      new THREE.MeshPhongMaterial({ color: 0xaa1111 }),
    );
    tail.rotation.z = Math.PI / 2;
    tail.position.set(-1.8, 0, 0);
    g.add(tail);
    const xm = new THREE.MeshBasicMaterial({ color: 0xff8888 });
    const x1 = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.08), xm);
    x1.position.set(0.6, 0.2, 0.35);
    x1.rotation.z = Math.PI / 4;
    g.add(x1);
    const x2 = x1.clone();
    x2.rotation.z = -Math.PI / 4;
    g.add(x2);
    g.rotation.z = 0.4;
    g.rotation.x = 0.2;
    return g;
  });

  // Pollutant: darker blue
  pools.pollutant = _pool(
    scene,
    MAX_POLLUTANT,
    () =>
      new THREE.Mesh(
        new THREE.OctahedronGeometry(1, 0),
        new THREE.MeshPhongMaterial({
          color: 0x4477aa,
          transparent: true,
          opacity: 0.7,
          emissive: 0x334466,
          emissiveIntensity: 0.1,
        }),
      ),
  );

  const plantColors = [0x1a6633, 0x228844, 0x2a7744, 0x1a5533];
  pools.plant = _pool(scene, MAX_PLANT, () => {
    const g = new THREE.Group();
    const color = plantColors[Math.floor(Math.random() * plantColors.length)];
    const mat = new THREE.MeshPhongMaterial({
      color,
      transparent: true,
      opacity: 0.65,
      side: THREE.DoubleSide,
      emissive: color,
      emissiveIntensity: 0.08,
    });
    const h = 3 + Math.random() * 6;
    const blade = new THREE.Mesh(
      new THREE.PlaneGeometry(0.4 + Math.random() * 0.4, h),
      mat,
    );
    blade.rotation.y = Math.random() * Math.PI;
    blade.rotation.z = (Math.random() - 0.5) * 0.3;
    g.add(blade);
    if (Math.random() > 0.4) {
      const b2 = blade.clone();
      b2.material = mat.clone();
      b2.position.x += (Math.random() - 0.5) * 1.2;
      b2.rotation.y = Math.random() * Math.PI;
      g.add(b2);
    }
    return g;
  });

  return { pools };
}

function _sortSinkingFirst(arr) {
  arr.sort((a, b) => a.z - b.z);
}

export function updateObjects(objectsCtx, frame) {
  const objData = frame.objects || [];
  const byType = {
    food: [],
    probiotic: [],
    oxygen: [],
    fecal: [],
    dead_fish: [],
    pollutant: [],
    plant: [],
  };
  for (const obj of objData) {
    if (byType[obj.type]) byType[obj.type].push(obj);
  }

  _sortSinkingFirst(byType.food);
  _sortSinkingFirst(byType.probiotic);
  _sortSinkingFirst(byType.fecal);
  _sortSinkingFirst(byType.dead_fish);
  _sortSinkingFirst(byType.pollutant);

  _upd(pools.food, byType.food, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.6 + d.value * 0.1);
  });
  _upd(pools.probiotic, byType.probiotic, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.6 + d.value * 0.08);
  });
  _upd(pools.oxygen, byType.oxygen, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.5);
  });
  _upd(pools.fecal, byType.fecal, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.5 + d.value * 0.12);
  });
  _upd(pools.dead_fish, byType.dead_fish, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.8 + d.value * 0.1);
  });
  _upd(pools.pollutant, byType.pollutant, (m, d) => {
    m.position.set(d.x, d.y, d.z);
    m.scale.setScalar(0.6 + d.value * 0.15);
    m.rotation.y += 0.05;
    m.rotation.x += 0.03;
  });
  _upd(pools.plant, byType.plant, (m, d) => {
    m.position.set(d.x, d.y, d.z);
  });
}

function _upd(pool, data, fn) {
  for (let i = 0; i < pool.length; i++) {
    if (i < data.length) {
      pool[i].visible = true;
      fn(pool[i], data[i]);
    } else pool[i].visible = false;
  }
}
