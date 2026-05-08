/**
 * loop.js -- Main render/animation loop and frame advancement.
 * Supports loop mode (restart when finished).
 * Tracks death reasons: suffocated, starved, weakened, sick, parasited, cannibalized.
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

// Death reason counters
let deathReasons = _emptyReasons();

function _emptyReasons() {
  return {
    deaths: 0,
    suffocated: 0,
    starved: 0,
    weakened: 0,
    sick: 0,
    parasited: 0,
    cannibalized: 0,
  };
}

export function startLoop(sc, ec, oc, efc, framesData, pond) {
  sceneCtx = sc;
  entitiesCtx = ec;
  objectsCtx = oc;
  effectsCtx = efc;
  frames = framesData;
  totalFrames = frames.length;
  requestAnimationFrame(tick);
}

function _processFrameDeathEvents(frame) {
  // Process death_events (natural deaths)
  if (frame.death_events) {
    for (const ev of frame.death_events) {
      deathReasons.deaths++;
      const reasons = ev.reasons || [];
      for (const r of reasons) {
        if (deathReasons.hasOwnProperty(r)) {
          deathReasons[r]++;
        }
      }
    }
  }

  // Process cannibal_events (cannibalism deaths)
  if (frame.cannibal_events) {
    for (const ev of frame.cannibal_events) {
      deathReasons.deaths++;
      const reasons = ev.reasons || ["cannibalized"];
      for (const r of reasons) {
        if (deathReasons.hasOwnProperty(r)) {
          deathReasons[r]++;
        }
      }
    }
  }
}

function _countEventsUpTo(upTo) {
  const reasons = _emptyReasons();
  for (let i = 0; i <= upTo && i < frames.length; i++) {
    const f = frames[i];

    // Death events
    if (f.death_events) {
      for (const ev of f.death_events) {
        reasons.deaths++;
        const rs = ev.reasons || [];
        for (const r of rs) {
          if (reasons.hasOwnProperty(r)) {
            reasons[r]++;
          }
        }
      }
    }

    // Cannibal events
    if (f.cannibal_events) {
      for (const ev of f.cannibal_events) {
        reasons.deaths++;
        const rs = ev.reasons || ["cannibalized"];
        for (const r of rs) {
          if (reasons.hasOwnProperty(r)) {
            reasons[r]++;
          }
        }
      }
    }
  }
  return reasons;
}

function _resetCounters() {
  deathReasons = _emptyReasons();
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
    deathReasons = _countEventsUpTo(state.currentFrame);
  }

  // Manual frame stepping while paused (includes jump)
  if (!state.playing && state.currentFrame !== prevFrameIdx) {
    if (state.currentFrame > prevFrameIdx) {
      for (let i = prevFrameIdx + 1; i <= state.currentFrame; i++) {
        const f = frames[i];
        const prev = i > 0 ? frames[i - 1] : null;
        _processFrameDeathEvents(f);
        detectKills(effectsCtx, f, prev);
      }
      updateEffects(effectsCtx, sceneCtx, true);
    }
    prevFrameIdx = state.currentFrame;
    const frame = frames[state.currentFrame];
    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    updateUI(frame, totalFrames, deathReasons);
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

    _processFrameDeathEvents(frame);

    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    detectKills(effectsCtx, frame, prev);
    updateEffects(effectsCtx, sceneCtx, true);
    updateUI(frame, totalFrames, deathReasons);
    updateSelection(frame);
  } else {
    const frame = frames[state.currentFrame];
    updateEntities(entitiesCtx, frame, sceneCtx);
    updateObjects(objectsCtx, frame);
    updateEffects(effectsCtx, sceneCtx, false);
    updateUI(frame, totalFrames, deathReasons);
    updateSelection(frame);
  }

  _render();
  signalFrameReady();
}

function _render() {
  sceneCtx.controls.update();
  sceneCtx.renderer.render(sceneCtx.scene, sceneCtx.camera);
}
