/**
 * loop.js -- Main render/animation loop and frame advancement.
 * Supports loop mode (restart when finished).
 */

import { clearEffects, detectKills, updateEffects } from "./effects.js";
import { updateEntities } from "./entities.js";
import { updateObjects } from "./objects.js";
import { updateSelection } from "./selection.js";
import { signalFrameReady, state, updateUI } from "./ui.js";

let sceneCtx = null;
let entitiesCtx = null;
let objectsCtx = null;
let effectsCtx = null;
let frames = [];
let totalFrames = 0;
let lastTime = 0;
let prevFrameIdx = -1;
let cumulativeCannibalCount = 0;
let cumulativeDeathCount = 0;

export function startLoop(sc, ec, oc, efc, framesData, pond) {
  sceneCtx = sc;
  entitiesCtx = ec;
  objectsCtx = oc;
  effectsCtx = efc;
  frames = framesData;
  totalFrames = frames.length;
  requestAnimationFrame(tick);
}

function _countEvents(upTo) {
  let cannibals = 0,
    deaths = 0;
  let prevFishIds = null;
  for (let i = 0; i <= upTo && i < frames.length; i++) {
    const f = frames[i];
    if (f.cannibal_events) cannibals += f.cannibal_events.length;

    if (i > 0 && prevFishIds) {
      const curIds = new Set(
        f.fish.filter((fi) => fi.alive).map((fi) => fi.id),
      );
      const cannibalPreyIds = new Set();
      if (f.cannibal_events) {
        for (const ev of f.cannibal_events) cannibalPreyIds.add(ev.prey);
      }
      for (const pid of prevFishIds) {
        if (!curIds.has(pid) && !cannibalPreyIds.has(pid)) deaths++;
      }
    }
    prevFishIds = new Set(f.fish.filter((fi) => fi.alive).map((fi) => fi.id));
  }
  return { cannibals, deaths };
}

function _countFrameDeaths(frame, prevFrame) {
  if (!prevFrame) return 0;
  const curIds = new Set(frame.fish.filter((f) => f.alive).map((f) => f.id));
  const cannibalPreyIds = new Set();
  if (frame.cannibal_events) {
    for (const ev of frame.cannibal_events) cannibalPreyIds.add(ev.prey);
  }
  let deaths = 0;
  for (const pf of prevFrame.fish) {
    if (!pf.alive) continue;
    if (!curIds.has(pf.id) && !cannibalPreyIds.has(pf.id)) deaths++;
  }
  return deaths;
}

function _resetCounters() {
  cumulativeCannibalCount = 0;
  cumulativeDeathCount = 0;
  clearEffects(effectsCtx);
}

function tick(timestamp) {
  requestAnimationFrame(tick);
  if (!frames.length) return;

  const interval = 1000 / state.fps;
  if (timestamp - lastTime < interval) {
    _render();
    return;
  }
  lastTime = timestamp;

  // Detect rewind
  if (state.currentFrame < prevFrameIdx) {
    clearEffects(effectsCtx);
    const counts = _countEvents(state.currentFrame);
    cumulativeCannibalCount = counts.cannibals;
    cumulativeDeathCount = counts.deaths;
  }

  // Manual frame stepping while paused (includes jump)
  if (!state.playing && state.currentFrame !== prevFrameIdx) {
    if (state.currentFrame > prevFrameIdx) {
      for (let i = prevFrameIdx + 1; i <= state.currentFrame; i++) {
        const f = frames[i];
        const prev = i > 0 ? frames[i - 1] : null;
        if (f.cannibal_events)
          cumulativeCannibalCount += f.cannibal_events.length;
        cumulativeDeathCount += _countFrameDeaths(f, prev);
        detectKills(effectsCtx, f, prev);
      }
      updateEffects(effectsCtx, sceneCtx, true);
    }
    prevFrameIdx = state.currentFrame;
    const frame = frames[state.currentFrame];
    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    updateUI(frame, totalFrames, cumulativeCannibalCount, cumulativeDeathCount);
    updateSelection(frame);
    _render();
    signalFrameReady();
    return;
  }

  if (state.playing) {
    prevFrameIdx = state.currentFrame;

    // Loop: restart when reaching the end
    if (state.currentFrame >= totalFrames - 1) {
      if (state.loop) {
        state.currentFrame = 0;
        prevFrameIdx = -1;
        _resetCounters();
      } else {
        state.currentFrame = totalFrames - 1;
      }
    } else {
      state.currentFrame = state.currentFrame + 1;
    }

    const frame = frames[state.currentFrame];
    const prev = state.currentFrame > 0 ? frames[state.currentFrame - 1] : null;

    if (frame.cannibal_events) {
      cumulativeCannibalCount += frame.cannibal_events.length;
    }
    cumulativeDeathCount += _countFrameDeaths(frame, prev);

    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    detectKills(effectsCtx, frame, prev);
    updateEffects(effectsCtx, sceneCtx, true);
    updateUI(frame, totalFrames, cumulativeCannibalCount, cumulativeDeathCount);
    updateSelection(frame);
  } else {
    const frame = frames[state.currentFrame];
    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    updateEffects(effectsCtx, sceneCtx, false);
    updateUI(frame, totalFrames, cumulativeCannibalCount, cumulativeDeathCount);
    updateSelection(frame);
  }

  _render();
  signalFrameReady();
}

function _render() {
  sceneCtx.controls.update();
  sceneCtx.renderer.render(sceneCtx.scene, sceneCtx.camera);
}
