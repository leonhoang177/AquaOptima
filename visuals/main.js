/**
 * main.js -- Entry point: fetch data, initialize all modules, start loop.
 */

import { initEffects } from "./effects.js";
import { initEntities } from "./entities.js";
import { initLegend } from "./legend.js";
import { startLoop } from "./loop.js";
import { initObjects } from "./objects.js";
import { initScene } from "./scene.js";
import { initSelection } from "./selection.js";
import { initUI } from "./ui.js";

const loadingDiv = document.getElementById("loading");

async function main() {
  let data;
  try {
    const resp = await fetch("../logs/simulation_data.json");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    data = await resp.json();
  } catch (err) {
    loadingDiv.innerHTML = `
      <div style="color:#ff4c6a;">Could not load simulation_data.json<br>
      <span style="font-size:0.7em;color:#8899aa;">${err.message}</span></div>`;
    return;
  }

  const pond = {
    width: data.pond_width,
    height: data.pond_height,
    depth: data.pond_depth,
  };

  const frames = data.frames;
  if (!frames || frames.length === 0) {
    loadingDiv.innerHTML = `
      <div style="color:#ff4c6a;">No frames in simulation data.</div>`;
    return;
  }

  const container = document.getElementById("canvas-container");

  // Initialize all modules
  const sceneCtx = initScene(container, pond);
  const entitiesCtx = initEntities(sceneCtx, pond);
  const objectsCtx = initObjects(sceneCtx, pond);
  const effectsCtx = initEffects(sceneCtx, pond);
  initUI(data);
  initSelection(sceneCtx, container);
  initLegend();

  // Hide loading
  loadingDiv.classList.add("hidden");

  // Start the render/animation loop
  startLoop(sceneCtx, entitiesCtx, objectsCtx, effectsCtx, frames, pond);
}

main();
