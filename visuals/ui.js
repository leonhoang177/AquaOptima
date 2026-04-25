/**
 * ui.js -- Controls (play/pause/speed), stats bar, genotype bar.
 */

// ── State (exported for loop.js to read) ──
export const state = {
  playing: true,
  fps: 3,
  fpsIndex: 2,
  currentFrame: 0,
};

const FPS_STEPS = [1, 2, 3, 5, 10, 15, 30, 60, 120];

// ── DOM refs ──
let btnPlay, btnPause, btnRestart, btnSlower, btnFaster;
let speedDisplay, frameSlider, timeDisplay, progressBar;
let statsBar, genotypeBar, hudDiv;

/**
 * Initialize UI: wire up controls, populate genotype bar.
 */
export function initUI(data) {
  btnPlay = document.getElementById("btn-play");
  btnPause = document.getElementById("btn-pause");
  btnRestart = document.getElementById("btn-restart");
  btnSlower = document.getElementById("btn-slower");
  btnFaster = document.getElementById("btn-faster");
  speedDisplay = document.getElementById("speed-display");
  frameSlider = document.getElementById("frame-slider");
  timeDisplay = document.getElementById("time-display");
  progressBar = document.getElementById("progress-bar");
  statsBar = document.getElementById("stats-bar");
  genotypeBar = document.getElementById("genotype-bar");
  hudDiv = document.getElementById("hud");

  // Set slider max
  const maxFrame =
    data.frames && data.frames.length > 0 ? data.frames.length - 1 : 0;
  frameSlider.max = maxFrame;

  // ── Play / Pause / Restart ──
  btnPlay.addEventListener("click", () => {
    state.playing = true;
    btnPlay.classList.add("active");
    btnPause.classList.remove("active");
  });

  btnPause.addEventListener("click", () => {
    state.playing = false;
    btnPause.classList.add("active");
    btnPlay.classList.remove("active");
  });

  btnRestart.addEventListener("click", () => {
    state.currentFrame = 0;
    frameSlider.value = 0;
  });

  // ── Speed ──
  btnSlower.addEventListener("click", () => {
    state.fpsIndex = Math.max(0, state.fpsIndex - 1);
    state.fps = FPS_STEPS[state.fpsIndex];
    speedDisplay.textContent = state.fps + " fps";
  });

  btnFaster.addEventListener("click", () => {
    state.fpsIndex = Math.min(FPS_STEPS.length - 1, state.fpsIndex + 1);
    state.fps = FPS_STEPS[state.fpsIndex];
    speedDisplay.textContent = state.fps + " fps";
  });

  // ── Frame slider ──
  frameSlider.addEventListener("input", () => {
    state.currentFrame = parseInt(frameSlider.value);
  });

  // ── Progress bar click ──
  document
    .getElementById("progress-bar-container")
    .addEventListener("click", (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      state.currentFrame = Math.floor(pct * maxFrame);
      frameSlider.value = state.currentFrame;
    });

  // ── Populate genotype bar ──
  _populateGenotype(data);
}

/**
 * Update UI elements for the current frame.
 */
export function updateUI(frame, totalFrames) {
  // ── Time display ──
  const p2 = (n) => String(n).padStart(2, "0");
  const p4 = (n) => String(n).padStart(4, "0");
  timeDisplay.textContent = `Day ${p2(frame.day)} | Hour ${p2(frame.hour)} | Frame ${p4(state.currentFrame + 1)}/${p4(totalFrames)}`;

  // ── Slider + progress ──
  frameSlider.value = state.currentFrame;
  progressBar.style.width =
    (state.currentFrame / Math.max(1, totalFrames - 1)) * 100 + "%";

  // ── HUD ──
  hudDiv.textContent = `Alive: ${frame.alive_count} / ${frame.total_count}`;

  // ── Stats bar ──
  const alive = frame.fish.filter((f) => f.alive);
  const n = alive.length || 1;
  const total = frame.total_count;
  const sp = (alive.length / total) * 100;

  let sH = 0,
    sE = 0,
    sF = 0,
    sI = 0,
    sO = 0;
  let nInf = 0,
    nPar = 0,
    nBst = 0;
  for (const f of alive) {
    sH += f.hp;
    sE += f.energy;
    sF += f.fullness;
    sI += f.immunity;
    sO += f.oxygen;
    if (f.is_infected) nInf++;
    if (f.has_parasite) nPar++;
    if (f.is_boosting) nBst++;
  }

  const fm = (v) => (v / n).toFixed(1);

  statsBar.innerHTML = `
    <div class="stat-chip"><span class="stat-chip-label">Survival</span><span class="stat-chip-value">${sp.toFixed(1)}% (${alive.length}/${total})</span></div>
    <div class="stat-chip"><span class="stat-chip-label">HP</span><span class="stat-chip-value">${fm(sH)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Energy</span><span class="stat-chip-value">${fm(sE)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Fullness</span><span class="stat-chip-value">${fm(sF)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Immunity</span><span class="stat-chip-value">${fm(sI)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">O₂</span><span class="stat-chip-value">${fm(sO)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Infected</span><span class="stat-chip-value">${nInf}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Parasitized</span><span class="stat-chip-value">${nPar}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Boosting</span><span class="stat-chip-value">${nBst}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Objects</span><span class="stat-chip-value">${frame.objects.length}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Hazards</span><span class="stat-chip-value">${frame.hazards.length}</span></div>
  `;
}

/**
 * Populate the genotype bar (static, set once).
 */
function _populateGenotype(data) {
  if (!data || !data.genotype) return;
  const g = data.genotype;
  const L = (v) => ["Middle", "Corner", "Random"][v] || "?";

  genotypeBar.innerHTML = `
    <div class="geno-chip"><span class="geno-chip-label">Fitness:</span><span class="geno-chip-value">${data.fitness.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Survival:</span><span class="geno-chip-value">${(data.survival_rate * 100).toFixed(1)}%</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Cost:</span><span class="geno-chip-value">$${data.cost.toFixed(2)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Food:</span><span class="geno-chip-value">${g.food_quantity}× / ${g.food_interval}h @ ${L(g.food_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Prob:</span><span class="geno-chip-value">${g.probiotic_quantity}× / ${g.probiotic_interval}h @ ${L(g.probiotic_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">O₂:</span><span class="geno-chip-value">${g.oxygen_duration}h / ${g.oxygen_interval}h @ ${L(g.oxygen_location)}</span></div>
  `;
}
