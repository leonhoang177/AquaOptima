/**
 * selection.js -- Raycaster click detection + selected fish detail panel.
 */

import * as THREE from "three";
import { getFishBodies } from "./entities.js";

let selectedFishId = null;
let sceneRef = null;
let containerRef = null;
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();

let panel, panelBody, panelTitle, panelClose;

const BAR_COLORS = {
  health: "#e06070",
  oxygen: "#88ccff",
  fullness: "#ffee55",
  immunity: "#55ffcc",
};

const STATUS_COLORS = {
  infected: "#ffaa00",
  parasitized: "#cc44ff",
};

export function initSelection(sceneCtx, container) {
  sceneRef = sceneCtx;
  containerRef = container;
  panel = document.getElementById("fish-panel");
  panelBody = document.getElementById("fish-panel-body");
  panelTitle = document.getElementById("fish-panel-title");
  panelClose = document.getElementById("fish-panel-close");

  container.addEventListener("click", _onClick);
  panelClose.addEventListener("click", (e) => {
    e.stopPropagation();
    _deselect();
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _deselect();
  });
}

export function getSelectedFishId() {
  return selectedFishId;
}

export function updateSelection(frame) {
  if (selectedFishId === null) return;
  const fd = frame.fish.find((f) => f.id === selectedFishId);
  if (!fd || !fd.alive) {
    _renderDeadPanel();
    return;
  }
  _renderPanel(fd);
}

function _onClick(e) {
  if (panel.contains(e.target)) return;
  const rect = containerRef.getBoundingClientRect();
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(mouse, sceneRef.camera);

  const fishGroups = getFishBodies();
  const bodyMeshes = [];
  const meshToGroup = new Map();
  for (const group of fishGroups) {
    const body = group.children[0];
    if (body) {
      bodyMeshes.push(body);
      meshToGroup.set(body, group);
    }
  }

  const intersects = raycaster.intersectObjects(bodyMeshes, false);
  if (intersects.length > 0) {
    const group = meshToGroup.get(intersects[0].object);
    if (group && group.userData.fishId >= 0) {
      selectedFishId = group.userData.fishId;
      panelTitle.textContent = `Fish #${selectedFishId}`;
      panel.classList.add("visible");
      return;
    }
  }
  _deselect();
}

function _deselect() {
  selectedFishId = null;
  panel.classList.remove("visible");
}

function _renderPanel(fd) {
  const bars = [
    { key: "health", label: "Health", cur: fd.health, max: fd.max_health },
    { key: "oxygen", label: "Oxygen", cur: fd.oxygen, max: fd.max_oxygen },
    {
      key: "fullness",
      label: "Fullness",
      cur: fd.fullness,
      max: fd.max_fullness,
    },
    {
      key: "immunity",
      label: "Immunity",
      cur: fd.immunity,
      max: fd.max_immunity,
    },
  ];

  let barsHTML = "";
  for (const b of bars) {
    const pct = Math.max(0, Math.min(100, (b.cur / b.max) * 100));
    barsHTML += `
      <div class="fp-bar-row">
        <div class="fp-bar-label-row">
          <span class="fp-bar-name">${b.label}</span>
          <span class="fp-bar-nums">${b.cur.toFixed(1)} / ${b.max.toFixed(1)}</span>
        </div>
        <div class="fp-bar-track">
          <div class="fp-bar-fill" style="width:${pct}%;background:${BAR_COLORS[b.key]}"></div>
        </div>
      </div>`;
  }

  const statuses = [
    {
      label: "Infected",
      active: fd.is_infected,
      color: STATUS_COLORS.infected,
    },
    {
      label: "Parasitized",
      active: fd.has_parasite,
      color: STATUS_COLORS.parasitized,
    },
  ];

  let statusHTML = "";
  for (const s of statuses) {
    const dotColor = s.active ? s.color : "#333";
    const textColor = s.active ? "#e0e8f0" : "#556677";
    statusHTML += `
      <div class="fp-row">
        <span class="fp-label">
          <span class="fp-status-dot" style="background:${dotColor};box-shadow:${s.active ? "0 0 4px " + s.color : "none"}"></span>
          ${s.label}
        </span>
        <span class="fp-value" style="color:${textColor}">${s.active ? "Yes" : "No"}</span>
      </div>`;
  }

  const effVel = Math.sqrt(fd.vx * fd.vx + fd.vy * fd.vy + fd.vz * fd.vz);

  panelBody.innerHTML = `
    <div class="fp-section">
      <div class="fp-section-title">Traits</div>
      <div class="fp-row"><span class="fp-label">Body Size</span><span class="fp-value">${fd.body_size}</span></div>
      <div class="fp-row"><span class="fp-label">Mouth Size</span><span class="fp-value">${fd.mouth_size}</span></div>
      <div class="fp-row"><span class="fp-label">Base Velocity</span><span class="fp-value">${fd.base_velocity}</span></div>
    </div>
    <div class="fp-section">
      <div class="fp-section-title">Vitals</div>
      ${barsHTML}
    </div>
    <div class="fp-section">
      <div class="fp-section-title">Status</div>
      ${statusHTML}
    </div>
    <div class="fp-section">
      <div class="fp-section-title">Dynamics</div>
      <div class="fp-row"><span class="fp-label">Eff. Speed</span><span class="fp-value">${effVel.toFixed(2)}</span></div>
    </div>
  `;
}

function _renderDeadPanel() {
  panelBody.innerHTML = `
    <div class="fp-dead-banner">☠ DEAD</div>
    <div class="fp-section" style="margin-top:8px;">
      <div class="fp-row"><span class="fp-label">This fish is no longer alive.</span></div>
      <div class="fp-row"><span class="fp-label" style="font-size:0.85em;color:#556677;">Click another fish or press Escape.</span></div>
    </div>
  `;
}
