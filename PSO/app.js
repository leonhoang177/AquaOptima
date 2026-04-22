// AquaOptima PSO Visualizer
// Expects simulation_data.json produced by: python -m PSO.main

const SPECIES_COLORS = ['#38bdf8', '#fb923c', '#4ade80'];
const FISH_SIZE = 7;
const FPS = 30;
const FRAME_MS = 1000 / FPS;

let data = null;
let frameIdx = 0;
let lastTime = 0;

async function init() {
  const panel = document.getElementById('panel');

  try {
    const resp = await fetch('simulation_data.json');
    if (!resp.ok) throw new Error(`HTTP ${resp.status} — file not found`);
    data = await resp.json();
  } catch (e) {
    panel.innerHTML = `
      <h2 style="color:#f87171">No simulation data</h2>
      <p class="error-msg">
        Could not load <code>simulation_data.json</code>.<br><br>
        Run the optimizer first:<br>
        <code>python -m PSO.main</code><br><br>
        Then serve this directory:<br>
        <code>python -m http.server 8000</code><br>
        and open <code>http://localhost:8000</code>.
      </p>`;
    return;
  }

  populateStaticInfo(data.metadata);
  requestAnimationFrame(animate);
}

function populateStaticInfo(meta) {
  const p = meta.optimal_env_params;
  document.getElementById('e-food').textContent = p.food_density.toFixed(3);
  document.getElementById('e-temp').textContent = p.temperature.toFixed(1) + ' °C';
  document.getElementById('e-o2').textContent   = p.oxygen_level.toFixed(2) + ' mg/L';
  document.getElementById('e-ph').textContent   = p.ph_level.toFixed(2);

  document.getElementById('t-pop').textContent = meta.target_population;
  document.getElementById('f-pop').textContent = meta.final_population;
  document.getElementById('t-div').textContent = meta.target_diversity.toFixed(3);
  document.getElementById('f-div').textContent = meta.final_diversity.toFixed(3);
}

function animate(ts) {
  if (!lastTime) lastTime = ts;
  const delta = ts - lastTime;

  if (delta >= FRAME_MS) {
    lastTime = ts - (delta % FRAME_MS);
    renderFrame(data.frames[frameIdx]);
    frameIdx = (frameIdx + 1) % data.frames.length;
  }

  requestAnimationFrame(animate);
}

function renderFrame(frame) {
  const canvas = document.getElementById('tank');
  const ctx = canvas.getContext('2d');
  const meta = data.metadata;

  // Background
  ctx.fillStyle = '#0b1929';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Subtle grid
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 1;
  for (let gx = 0; gx <= canvas.width; gx += 80) {
    ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke();
  }
  for (let gy = 0; gy <= canvas.height; gy += 80) {
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke();
  }

  // Food sources — glowing green circles
  for (const food of frame.food) {
    const r = 8 + food.amount * 14;
    const alpha = 0.25 + food.amount * 0.5;

    // Outer glow
    const grad = ctx.createRadialGradient(food.x, food.y, 0, food.x, food.y, r * 1.8);
    grad.addColorStop(0, `rgba(34,197,94,${alpha})`);
    grad.addColorStop(1, 'rgba(34,197,94,0)');
    ctx.beginPath();
    ctx.arc(food.x, food.y, r * 1.8, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Core
    ctx.beginPath();
    ctx.arc(food.x, food.y, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(34,197,94,${alpha + 0.15})`;
    ctx.fill();
    ctx.strokeStyle = `rgba(134,239,172,0.6)`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // School group-best markers (faint crosshair)
  for (const school of frame.schools) {
    const sx = school.gbest_x, sy = school.gbest_y;
    ctx.strokeStyle = 'rgba(255,255,255,0.18)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(sx - 9, sy); ctx.lineTo(sx + 9, sy);
    ctx.moveTo(sx, sy - 9); ctx.lineTo(sx, sy + 9);
    ctx.stroke();
    // Tiny circle
    ctx.beginPath();
    ctx.arc(sx, sy, 3, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.25)';
    ctx.stroke();
  }

  // Fish
  for (const fish of frame.fish) {
    drawFish(ctx, fish.x, fish.y, fish.angle, fish.species_id);
  }

  // Season boundary flash overlay
  const isLastStep = frame.timestep === meta.timesteps_per_season - 1;
  if (isLastStep) {
    ctx.fillStyle = 'rgba(15,185,177,0.06)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  // Update live stats
  document.getElementById('s-season').textContent =
    `${(frame.season ?? 0) + 1} / ${meta.num_seasons}`;
  document.getElementById('s-step').textContent =
    `${frame.timestep + 1} / ${meta.timesteps_per_season}`;
  document.getElementById('s-schools').textContent = frame.schools.length;
  document.getElementById('s-fish').textContent    = frame.fish.length;

  document.getElementById('season-label').textContent =
    `Season ${(frame.season ?? 0) + 1}  ·  Step ${frame.timestep + 1}`;

  const totalFrames = data.frames.length;
  document.getElementById('progress-fill').style.width =
    `${(frameIdx / totalFrames) * 100}%`;
}

function drawFish(ctx, x, y, angle, speciesId) {
  const color = SPECIES_COLORS[speciesId % SPECIES_COLORS.length];

  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);

  // Body — elongated teardrop pointing right (+x = forward)
  ctx.beginPath();
  ctx.moveTo(FISH_SIZE, 0);
  ctx.lineTo(-FISH_SIZE * 0.6, -FISH_SIZE * 0.55);
  ctx.lineTo(-FISH_SIZE * 0.35, 0);
  ctx.lineTo(-FISH_SIZE * 0.6,  FISH_SIZE * 0.55);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();

  // Tail fin
  ctx.beginPath();
  ctx.moveTo(-FISH_SIZE * 0.35, 0);
  ctx.lineTo(-FISH_SIZE * 0.9, -FISH_SIZE * 0.4);
  ctx.lineTo(-FISH_SIZE * 0.9,  FISH_SIZE * 0.4);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.55;
  ctx.fill();
  ctx.globalAlpha = 1.0;

  // Eye
  ctx.beginPath();
  ctx.arc(FISH_SIZE * 0.35, -FISH_SIZE * 0.18, 1.6, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(FISH_SIZE * 0.38, -FISH_SIZE * 0.18, 0.7, 0, Math.PI * 2);
  ctx.fillStyle = '#111';
  ctx.fill();

  ctx.restore();
}

init();
