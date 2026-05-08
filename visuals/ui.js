/**
 * ui.js -- Controls, stats bar, genotype bar.
 * Default speed 7. Loop toggle. Play/Pause before Restart.
 * All metrics normalized 0.0000 - 1.0000.
 * Death reason tracking: suffocated, starved, weakened, sick, parasited, cannibalized.
 */

export const state = {
  playing: true,
  fps: 7,
  currentFrame: 0,
  loop: false,
};

const MIN_FPS = 1;
const MAX_FPS = 120;
const FPS_STEP = 1;
const JUMP_STEP = 5;

let btnPlayPause, btnRestart, btnLoop;
let btnSpeedDown, btnSpeedUp, speedDisplay;
let btnJumpBack, btnJumpFwd;
let timeDisplay, progressBar;
let statsBar, deathBar, genotypeBar, hudDiv;
let totalFramesCount = 0;
let jumpCooldown = false;

export function initUI(data) {
  btnPlayPause = document.getElementById("btn-playpause");
  btnRestart = document.getElementById("btn-restart");
  btnLoop = document.getElementById("btn-loop");
  btnSpeedDown = document.getElementById("btn-speed-down");
  btnSpeedUp = document.getElementById("btn-speed-up");
  speedDisplay = document.getElementById("speed-display");
  btnJumpBack = document.getElementById("btn-jump-back");
  btnJumpFwd = document.getElementById("btn-jump-fwd");
  timeDisplay = document.getElementById("time-display");
  progressBar = document.getElementById("progress-bar");
  statsBar = document.getElementById("stats-bar");
  deathBar = document.getElementById("death-bar");
  genotypeBar = document.getElementById("genotype-bar");
  hudDiv = document.getElementById("hud");

  totalFramesCount =
    data.frames && data.frames.length > 0 ? data.frames.length : 0;

  btnPlayPause.addEventListener("click", () => {
    state.playing = !state.playing;
    btnPlayPause.textContent = state.playing ? "Pause" : "Play";
    btnPlayPause.classList.toggle("active", state.playing);
  });

  btnRestart.addEventListener("click", () => {
    state.currentFrame = 0;
  });

  btnLoop.addEventListener("click", () => {
    state.loop = !state.loop;
    btnLoop.textContent = state.loop ? "Loop: On" : "Loop: Off";
    btnLoop.classList.toggle("active", state.loop);
  });

  // Speed controls
  btnSpeedDown.addEventListener("click", () => {
    state.fps = Math.max(MIN_FPS, state.fps - FPS_STEP);
    speedDisplay.textContent = state.fps;
  });
  btnSpeedUp.addEventListener("click", () => {
    state.fps = Math.min(MAX_FPS, state.fps + FPS_STEP);
    speedDisplay.textContent = state.fps;
  });

  // Jump controls (auto-pause, disable during load)
  btnJumpBack.addEventListener("click", () => {
    if (jumpCooldown) return;
    _pause();
    state.currentFrame = Math.max(0, state.currentFrame - JUMP_STEP);
    _startJumpCooldown();
  });
  btnJumpFwd.addEventListener("click", () => {
    if (jumpCooldown) return;
    _pause();
    state.currentFrame = Math.min(
      totalFramesCount - 1,
      state.currentFrame + JUMP_STEP,
    );
    _startJumpCooldown();
  });

  // Progress bar click
  document
    .getElementById("progress-bar-container")
    .addEventListener("click", (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      state.currentFrame = Math.max(
        0,
        Math.min(
          totalFramesCount - 1,
          Math.floor(pct * (totalFramesCount - 1)),
        ),
      );
    });

  speedDisplay.textContent = state.fps;
  _populateGenotype(data);
}

function _pause() {
  state.playing = false;
  btnPlayPause.textContent = "Play";
  btnPlayPause.classList.remove("active");
}

function _startJumpCooldown() {
  jumpCooldown = true;
  btnJumpBack.disabled = true;
  btnJumpFwd.disabled = true;
  btnJumpBack.style.opacity = "0.4";
  btnJumpFwd.style.opacity = "0.4";
  btnJumpBack.style.cursor = "not-allowed";
  btnJumpFwd.style.cursor = "not-allowed";
}

export function signalFrameReady() {
  if (!jumpCooldown) return;
  jumpCooldown = false;
  btnJumpBack.disabled = false;
  btnJumpFwd.disabled = false;
  btnJumpBack.style.opacity = "";
  btnJumpFwd.style.opacity = "";
  btnJumpBack.style.cursor = "";
  btnJumpFwd.style.cursor = "";
}

/**
 * Return a CSS color for survival rate percentage tiers.
 *   >= 80% → green
 *   >= 60% → yellow
 *   >= 40% → pink
 *   >= 20% → orange
 *   <  20% → red
 */
function _survivalColor(pct) {
  if (pct >= 80) return "#2ca02c"; // green
  if (pct >= 60) return "#e6d520"; // yellow
  if (pct >= 40) return "#e87da0"; // pink
  if (pct >= 20) return "#ff7f0e"; // orange
  return "#d62728"; // red
}

export function updateUI(frame, totalFrames, deathReasons) {
  deathReasons = deathReasons || {};
  const lost = deathReasons.deaths || 0;
  const suffocated = deathReasons.suffocated || 0;
  const starved = deathReasons.starved || 0;
  const weakened = deathReasons.weakened || 0;
  const sick = deathReasons.sick || 0;
  const parasited = deathReasons.parasited || 0;
  const cannibalized = deathReasons.cannibalized || 0;

  const p2 = (n) => String(n).padStart(2, "0");
  const p4 = (n) => String(n).padStart(4, "0");
  timeDisplay.textContent = `Day ${p2(frame.day)} | Hour ${p2(frame.hour)} | Frame ${p4(state.currentFrame + 1)}/${p4(totalFrames)}`;
  progressBar.style.width =
    (state.currentFrame / Math.max(1, totalFrames - 1)) * 100 + "%";
  hudDiv.textContent = `Alive: ${frame.alive_count} / ${frame.total_count}`;

  const alive = frame.fish.filter((f) => f.alive);
  const n = alive.length || 1;
  const total = frame.total_count;
  const srPct = (alive.length / total) * 100;
  const srColor = _survivalColor(srPct);
  let sH = 0,
    sF = 0,
    sI = 0,
    sO = 0,
    nInf = 0,
    nPar = 0;
  for (const f of alive) {
    sH += f.health;
    sF += f.fullness;
    sI += f.immunity;
    sO += f.oxygen;
    if (f.is_infected) nInf++;
    if (f.has_parasite) nPar++;
  }
  const fm = (v) => (v / n).toFixed(1);

  statsBar.innerHTML = `
    <div class="stat-chip"><span class="stat-chip-label">Survival Rate</span><span class="stat-chip-value" style="color:${srColor}">${srPct.toFixed(2)}% (${alive.length}/${total})</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Health</span><span class="stat-chip-value">${fm(sH)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Fullness</span><span class="stat-chip-value">${fm(sF)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Immunity</span><span class="stat-chip-value">${fm(sI)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">O₂</span><span class="stat-chip-value">${fm(sO)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Infected</span><span class="stat-chip-value">${nInf}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Parasitized</span><span class="stat-chip-value">${nPar}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Objects</span><span class="stat-chip-value">${frame.objects.length}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Hazards</span><span class="stat-chip-value">${frame.hazards.length}</span></div>
  `;

  deathBar.innerHTML = `
    <div class="stat-chip"><span class="stat-chip-label">Lost</span><span class="stat-chip-value">${lost}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Suffocated</span><span class="stat-chip-value">${suffocated}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Starved</span><span class="stat-chip-value">${starved}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Weakened</span><span class="stat-chip-value">${weakened}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Sick</span><span class="stat-chip-value">${sick}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Parasited</span><span class="stat-chip-value">${parasited}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Cannibalized</span><span class="stat-chip-value">${cannibalized}</span></div>
  `;
}

function _populateGenotype(data) {
  if (!data || !data.genotype) return;
  const g = data.genotype;
  const L = (v) =>
    [
      "Center",
      "Top-Left",
      "Top-Right",
      "Bot-Left",
      "Bot-Right",
      "Top-Center",
      "Bot-Center",
      "Left-Center",
      "Right-Center",
      "Random",
    ][v] || "?";
  const initialFishCount = data.initial_fish_count || "?";
  genotypeBar.innerHTML = `
    <div class="geno-chip"><span class="geno-chip-label">Fitness:</span><span class="geno-chip-value">${data.fitness.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Survival Rate:</span><span class="geno-chip-value">${data.survival_rate.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Saving Rate:</span><span class="geno-chip-value">${data.saving_rate.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Healthiness:</span><span class="geno-chip-value">${data.avg_healthiness.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Cost:</span><span class="geno-chip-value">$${data.cost.toFixed(2)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Initial Fish:</span><span class="geno-chip-value">${initialFishCount}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Food:</span><span class="geno-chip-value">${g.food_quantity}x / ${g.food_interval}h @ ${L(g.food_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Prob:</span><span class="geno-chip-value">${g.probiotic_quantity}x / ${g.probiotic_interval}h @ ${L(g.probiotic_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">O₂:</span><span class="geno-chip-value">${g.oxygen_duration}h / ${g.oxygen_interval}h @ ${L(g.oxygen_location)}</span></div>
  `;
}
