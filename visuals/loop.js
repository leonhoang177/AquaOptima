/**
 * loop.js -- Main render/animation loop and frame advancement.
 */

import { detectKills, updateEffects } from "./effects.js";
import { updateEntities } from "./entities.js";
import { updateObjects } from "./objects.js";
import { updateSelection } from "./selection.js";
import { state, updateUI } from "./ui.js";

let sceneCtx = null;
let entitiesCtx = null;
let objectsCtx = null;
let effectsCtx = null;
let frames = [];
let totalFrames = 0;
let lastTime = 0;

/**
 * Start the render loop.
 */
export function startLoop(sc, ec, oc, efc, framesData, pond) {
  sceneCtx = sc;
  entitiesCtx = ec;
  objectsCtx = oc;
  effectsCtx = efc;
  frames = framesData;
  totalFrames = frames.length;

  requestAnimationFrame(tick);
}

/**
 * Main tick — called every animation frame by the browser.
 */
function tick(timestamp) {
  requestAnimationFrame(tick);

  if (!frames.length) return;

  // ── Frame rate control ──
  const interval = 1000 / state.fps;
  if (timestamp - lastTime < interval) {
    // Still render the scene (for smooth orbit controls) but don't advance frame
    _render();
    return;
  }
  lastTime = timestamp;

  // ── Advance frame ──
  if (state.playing) {
    state.currentFrame = Math.min(state.currentFrame + 1, totalFrames - 1);
  }

  const frame = frames[state.currentFrame];
  const prevFrame =
    state.currentFrame > 0 ? frames[state.currentFrame - 1] : null;

  // ── Update all modules ──
  updateEntities(entitiesCtx, frame, sceneCtx);
  updateObjects(objectsCtx, frame);
  detectKills(effectsCtx, frame, prevFrame);
  updateEffects(effectsCtx, sceneCtx);
  updateUI(frame, totalFrames);
  updateSelection(frame);

  // ── Render ──
  _render();
}

/**
 * Render the scene.
 */
function _render() {
  sceneCtx.controls.update();
  sceneCtx.renderer.render(sceneCtx.scene, sceneCtx.camera);
}
