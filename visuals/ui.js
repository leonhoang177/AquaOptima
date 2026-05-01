/**
 * ui.js -- Controls, stats bar, genotype bar.
 */

export const state = {
  playing: true,
  fps: 3,
  currentFrame: 0,
};

let btnPlayPause, btnRestart;
let btnBack5, btnBack3, btnBack1, btnFwd1, btnFwd3, btnFwd5;
let fpsInput, timeDisplay, progressBar;
let statsBar, genotypeBar, hudDiv;
let totalFramesCount = 0;

export function initUI(data) {
  btnPlayPause = document.getElementById("btn-playpause");
  btnRestart = document.getElementById("btn-restart");
  btnBack5 = document.getElementById("btn-back5");
  btnBack3 = document.getElementById("btn-back3");
  btnBack1 = document.getElementById("btn-back1");
  btnFwd1 = document.getElementById("btn-fwd1");
  btnFwd3 = document.getElementById("btn-fwd3");
  btnFwd5 = document.getElementById("btn-fwd5");
  fpsInput = document.getElementById("fps-input");
  timeDisplay = document.getElementById("time-display");
  progressBar = document.getElementById("progress-bar");
  statsBar = document.getElementById("stats-bar");
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

  btnBack5.addEventListener("click", () => {
    _step(-5);
  });
  btnBack3.addEventListener("click", () => {
    _step(-3);
  });
  btnBack1.addEventListener("click", () => {
    _step(-1);
  });
  btnFwd1.addEventListener("click", () => {
    _step(1);
  });
  btnFwd3.addEventListener("click", () => {
    _step(3);
  });
  btnFwd5.addEventListener("click", () => {
    _step(5);
  });

  fpsInput.addEventListener("change", () => {
    const v = parseInt(fpsInput.value);
    if (v >= 1 && v <= 120) state.fps = v;
    else fpsInput.value = state.fps;
  });

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

  _populateGenotype(data);
}

function _step(delta) {
  state.currentFrame = Math.max(
    0,
    Math.min(totalFramesCount - 1, state.currentFrame + delta),
  );
}

export function updateUI(frame, totalFrames, cannibalCount, deathCount) {
  cannibalCount = cannibalCount || 0;
  deathCount = deathCount || 0;
  const p2 = (n) => String(n).padStart(2, "0");
  const p4 = (n) => String(n).padStart(4, "0");
  timeDisplay.textContent = `Day ${p2(frame.day)} | Hour ${p2(frame.hour)} | Frame ${p4(state.currentFrame + 1)}/${p4(totalFrames)}`;
  progressBar.style.width =
    (state.currentFrame / Math.max(1, totalFrames - 1)) * 100 + "%";
  hudDiv.textContent = `Alive: ${frame.alive_count} / ${frame.total_count}`;

  const alive = frame.fish.filter((f) => f.alive);
  const n = alive.length || 1;
  const total = frame.total_count;
  const sp = (alive.length / total) * 100;
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
    <div class="stat-chip"><span class="stat-chip-label">Survival</span><span class="stat-chip-value">${sp.toFixed(1)}% (${alive.length}/${total})</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Health</span><span class="stat-chip-value">${fm(sH)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Fullness</span><span class="stat-chip-value">${fm(sF)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Immunity</span><span class="stat-chip-value">${fm(sI)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">O2</span><span class="stat-chip-value">${fm(sO)}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Infected</span><span class="stat-chip-value">${nInf}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Parasitized</span><span class="stat-chip-value">${nPar}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Deaths</span><span class="stat-chip-value">${deathCount}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Cannibalized</span><span class="stat-chip-value">${cannibalCount}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Objects</span><span class="stat-chip-value">${frame.objects.length}</span></div>
    <div class="stat-chip"><span class="stat-chip-label">Hazards</span><span class="stat-chip-value">${frame.hazards.length}</span></div>
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
  genotypeBar.innerHTML = `
    <div class="geno-chip"><span class="geno-chip-label">Fitness:</span><span class="geno-chip-value">${data.fitness.toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Yield:</span><span class="geno-chip-value">${(data.yield || 0).toFixed(4)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Survival:</span><span class="geno-chip-value">${(data.survival_rate * 100).toFixed(1)}%</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Cost:</span><span class="geno-chip-value">$${data.cost.toFixed(2)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Saving:</span><span class="geno-chip-value">$${(data.saving || 0).toFixed(2)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Fish:</span><span class="geno-chip-value">${g.fish_count}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Food:</span><span class="geno-chip-value">${g.food_quantity}x / ${g.food_interval}h @ ${L(g.food_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">Prob:</span><span class="geno-chip-value">${g.probiotic_quantity}x / ${g.probiotic_interval}h @ ${L(g.probiotic_location)}</span></div>
    <div class="geno-chip"><span class="geno-chip-label">O2:</span><span class="geno-chip-value">${g.oxygen_duration}h / ${g.oxygen_interval}h @ ${L(g.oxygen_location)}</span></div>
  `;
}
