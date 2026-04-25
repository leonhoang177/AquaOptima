/**
 * effects.js -- Glow rings (handled in entities.js) and cannibal kill animations.
 *
 * Kill effects: expanding red ring + skull sprite that fades out.
 */

import * as THREE from "three";

// ── Config ──
const MAX_KILL_EFFECTS = 20;
const KILL_DURATION_FRAMES = 25;
const KILL_MAX_RADIUS = 8;
const KILL_COLOR = 0xff2222;

let killEffects = [];
let killPool = [];
let prevFishIds = new Set();

/**
 * Initialize kill effect pool.
 */
export function initEffects(sceneCtx, pond) {
  const { scene } = sceneCtx;

  for (let i = 0; i < MAX_KILL_EFFECTS; i++) {
    const group = new THREE.Group();
    group.visible = false;

    // Expanding ring
    const ringGeo = new THREE.RingGeometry(1, 1.3, 24);
    const ringMat = new THREE.MeshBasicMaterial({
      color: KILL_COLOR,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.name = "killRing";
    group.add(ring);

    // Inner flash
    const flashGeo = new THREE.CircleGeometry(1, 16);
    const flashMat = new THREE.MeshBasicMaterial({
      color: 0xff5050,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const flash = new THREE.Mesh(flashGeo, flashMat);
    flash.name = "killFlash";
    group.add(flash);

    // Skull text sprite
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    ctx.font = "48px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#ff3333";
    ctx.fillText("\u2620", 32, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({
      map: tex,
      transparent: true,
      opacity: 1,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.name = "killSkull";
    sprite.scale.set(3, 3, 1);
    group.add(sprite);

    scene.add(group);
    killPool.push(group);
  }

  return { killPool, killEffects };
}

/**
 * Detect kills from frame data and spawn effects.
 */
export function detectKills(effectsCtx, frame, prevFrame) {
  // From cannibal_events in frame data
  if (frame.cannibal_events) {
    for (const ev of frame.cannibal_events) {
      _spawnKill(effectsCtx, ev.x, ev.y, ev.z);
    }
  }

  // Detect disappearances (fish alive last frame, gone this frame)
  if (prevFrame) {
    const curIds = new Set(frame.fish.filter((f) => f.alive).map((f) => f.id));
    for (const pf of prevFrame.fish) {
      if (!pf.alive) continue;
      if (curIds.has(pf.id)) continue;

      // Check if near a current living fish (cannibal proxy)
      let nearFish = false;
      for (const cf of frame.fish) {
        if (!cf.alive) continue;
        const dx = cf.x - pf.x;
        const dy = cf.y - pf.y;
        const dz = cf.z - pf.z;
        if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 15) {
          nearFish = true;
          break;
        }
      }

      // Only show kill effect if near another fish and not already from cannibal_events
      if (nearFish) {
        const alreadyLogged = frame.cannibal_events?.some(
          (e) =>
            Math.abs(e.x - pf.x) < 2 &&
            Math.abs(e.y - pf.y) < 2 &&
            Math.abs(e.z - pf.z) < 2,
        );
        if (!alreadyLogged) {
          _spawnKill(effectsCtx, pf.x, pf.y, pf.z);
        }
      }
    }
  }
}

/**
 * Spawn a kill effect at position.
 */
function _spawnKill(effectsCtx, x, y, z) {
  effectsCtx.killEffects.push({
    x,
    y,
    z,
    age: 0,
    maxAge: KILL_DURATION_FRAMES,
  });
}

/**
 * Update all active kill effects (animate and expire).
 */
export function updateEffects(effectsCtx, sceneCtx) {
  const { killEffects, killPool } = effectsCtx;
  const camera = sceneCtx.camera;

  // Hide all first
  for (const group of killPool) {
    group.visible = false;
  }

  // Advance and render active effects
  const kept = [];
  let poolIdx = 0;

  for (const eff of killEffects) {
    eff.age++;
    if (eff.age >= eff.maxAge) continue;
    if (poolIdx >= killPool.length) {
      kept.push(eff);
      continue;
    }

    const p = eff.age / eff.maxAge; // 0 → 1
    const alpha = 1 - p;
    const group = killPool[poolIdx++];
    group.visible = true;
    group.position.set(eff.x, eff.y, eff.z);

    // Ring: expand and fade
    const ring = group.children[0];
    const radius = 2 + p * KILL_MAX_RADIUS;
    ring.scale.set(radius, radius, radius);
    ring.material.opacity = alpha * 0.7;
    ring.lookAt(camera.position);

    // Flash: shrink and fade quickly
    const flash = group.children[1];
    if (p < 0.25) {
      flash.visible = true;
      const flashAlpha = ((0.25 - p) / 0.25) * 0.35;
      flash.scale.setScalar(radius * 0.5);
      flash.material.opacity = flashAlpha;
      flash.lookAt(camera.position);
    } else {
      flash.visible = false;
    }

    // Skull: rise and fade
    const skull = group.children[2];
    if (alpha > 0.15) {
      skull.visible = true;
      skull.position.set(0, 0, -(radius + 1));
      const skullScale = 2 + p * 1.5;
      skull.scale.set(skullScale, skullScale, 1);
      skull.material.opacity = alpha;
    } else {
      skull.visible = false;
    }

    kept.push(eff);
  }

  effectsCtx.killEffects = kept;
}
