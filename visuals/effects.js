/**
 * effects.js -- Death and cannibal kill animations.
 * Dead fish: red ring + skull
 * Cannibal: yellow ring + jaw
 * Effects freeze when simulation is paused.
 */

import * as THREE from "three";

const MAX_EFFECTS = 30;
const KILL_DURATION_FRAMES = 20;
const KILL_MAX_RADIUS = 8;

// Cannibal: bright yellow
const CANNIBAL_COLOR = 0xffdd00;
const CANNIBAL_FLASH = 0xffee44;

// Death: red
const DEATH_COLOR = 0xff2222;
const DEATH_FLASH = 0xff5050;

let cannibalEffects = [];
let deathEffects = [];
let cannibalPool = [];
let deathPool = [];

function _createEffectPool(
  scene,
  count,
  ringColor,
  flashColor,
  iconText,
  iconColor,
) {
  const pool = [];
  for (let i = 0; i < count; i++) {
    const group = new THREE.Group();
    group.visible = false;

    const ringGeo = new THREE.RingGeometry(1, 1.3, 24);
    const ringMat = new THREE.MeshBasicMaterial({
      color: ringColor,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    group.add(new THREE.Mesh(ringGeo, ringMat));

    const flashGeo = new THREE.CircleGeometry(1, 16);
    const flashMat = new THREE.MeshBasicMaterial({
      color: flashColor,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    group.add(new THREE.Mesh(flashGeo, flashMat));

    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.font = "44px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = iconColor;
    ctx.fillText(iconText, 32, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        opacity: 1,
        depthWrite: false,
      }),
    );
    sprite.scale.set(3, 3, 1);
    group.add(sprite);

    scene.add(group);
    pool.push(group);
  }
  return pool;
}

export function initEffects(sceneCtx, pond) {
  const { scene } = sceneCtx;

  cannibalPool = _createEffectPool(
    scene,
    MAX_EFFECTS,
    CANNIBAL_COLOR,
    CANNIBAL_FLASH,
    "\uD83E\uDDB7",
    "#ffdd00",
  );
  deathPool = _createEffectPool(
    scene,
    MAX_EFFECTS,
    DEATH_COLOR,
    DEATH_FLASH,
    "\u2620",
    "#ff3333",
  );

  return { cannibalPool, deathPool, cannibalEffects, deathEffects };
}

export function detectKills(effectsCtx, frame, prevFrame) {
  // Cannibal events from simulation
  if (frame.cannibal_events) {
    for (const ev of frame.cannibal_events) {
      effectsCtx.cannibalEffects.push({
        x: ev.x,
        y: ev.y,
        z: ev.z,
        age: 0,
        maxAge: KILL_DURATION_FRAMES,
      });
    }
  }

  // Detect deaths (fish disappeared but NOT from cannibalism)
  if (prevFrame) {
    const curIds = new Set(frame.fish.filter((f) => f.alive).map((f) => f.id));
    const cannibalPreyIds = new Set();
    if (frame.cannibal_events) {
      for (const ev of frame.cannibal_events) {
        cannibalPreyIds.add(ev.prey);
      }
    }

    for (const pf of prevFrame.fish) {
      if (!pf.alive) continue;
      if (curIds.has(pf.id)) continue;
      // This fish disappeared
      if (cannibalPreyIds.has(pf.id)) continue; // Already handled as cannibal
      // This is a natural death
      effectsCtx.deathEffects.push({
        x: pf.x,
        y: pf.y,
        z: pf.z,
        age: 0,
        maxAge: KILL_DURATION_FRAMES,
      });
    }
  }
}

function _updatePool(effects, pool, camera, advancing) {
  for (const group of pool) group.visible = false;

  const kept = [];
  let poolIdx = 0;

  for (const eff of effects) {
    if (advancing) eff.age++;
    if (eff.age >= eff.maxAge) continue;
    if (poolIdx >= pool.length) {
      kept.push(eff);
      continue;
    }

    const p = eff.age / eff.maxAge;
    const alpha = 1 - p;
    const group = pool[poolIdx++];
    group.visible = true;
    group.position.set(eff.x, eff.y, eff.z);

    const ring = group.children[0];
    const radius = 2 + p * KILL_MAX_RADIUS;
    ring.scale.set(radius, radius, radius);
    ring.material.opacity = alpha * 0.8;
    ring.lookAt(camera.position);

    const flash = group.children[1];
    if (p < 0.25) {
      flash.visible = true;
      flash.scale.setScalar(radius * 0.5);
      flash.material.opacity = ((0.25 - p) / 0.25) * 0.4;
      flash.lookAt(camera.position);
    } else flash.visible = false;

    const icon = group.children[2];
    if (alpha > 0.15) {
      icon.visible = true;
      icon.position.set(0, 0, -(radius + 1));
      const s = 2 + p * 1.5;
      icon.scale.set(s, s, 1);
      icon.material.opacity = alpha;
    } else icon.visible = false;

    kept.push(eff);
  }

  return kept;
}

export function updateEffects(effectsCtx, sceneCtx, advancing) {
  const camera = sceneCtx.camera;
  effectsCtx.cannibalEffects = _updatePool(
    effectsCtx.cannibalEffects,
    effectsCtx.cannibalPool,
    camera,
    advancing,
  );
  effectsCtx.deathEffects = _updatePool(
    effectsCtx.deathEffects,
    effectsCtx.deathPool,
    camera,
    advancing,
  );
}

export function clearEffects(effectsCtx) {
  effectsCtx.cannibalEffects = [];
  effectsCtx.deathEffects = [];
}
