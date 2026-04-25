/**
 * scene.js -- Three.js scene setup: renderer, camera, orbit controls, lights, pond box.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/**
 * Initialize the 3D scene.
 * @param {HTMLElement} container - The DOM element to attach the renderer to.
 * @param {{width:number, height:number, depth:number}} pond - Pond dimensions.
 * @returns {object} sceneCtx - Shared scene context.
 */
export function initScene(container, pond) {
  const { width: W, height: H, depth: D } = pond;

  // ── Renderer ──
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x0a1628, 1);
  renderer.shadowMap.enabled = false;
  _resize(renderer, container);
  container.appendChild(renderer.domElement);

  // ── Scene ──
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0a1628, 0.003);

  // ── Camera ──
  const aspect = container.clientWidth / container.clientHeight;
  const camera = new THREE.PerspectiveCamera(50, aspect, 1, 1000);
  // Position camera looking at pond from above-front
  camera.position.set(W * 0.5, -H * 0.8, D * 1.8);
  camera.lookAt(W * 0.5, H * 0.5, D * 0.5);

  // ── Orbit controls ──
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(W * 0.5, H * 0.5, D * 0.5);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 20;
  controls.maxDistance = 500;
  controls.update();

  // ── Lights ──
  const ambientLight = new THREE.AmbientLight(0x4466aa, 0.6);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(W * 0.3, -H * 0.5, D * 2);
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0x88aacc, 0.3);
  fillLight.position.set(W * 0.7, H * 1.5, D * 0.5);
  scene.add(fillLight);

  // ── Pond box (wireframe edges) ──
  const pondGeo = new THREE.BoxGeometry(W, H, D);
  const pondEdges = new THREE.EdgesGeometry(pondGeo);
  const pondLine = new THREE.LineSegments(
    pondEdges,
    new THREE.LineBasicMaterial({ color: 0x1e5080, linewidth: 1 }),
  );
  pondLine.position.set(W * 0.5, H * 0.5, D * 0.5);
  scene.add(pondLine);

  // ── Pond floor (subtle plane) ──
  const floorGeo = new THREE.PlaneGeometry(W, H);
  const floorMat = new THREE.MeshBasicMaterial({
    color: 0x071a2c,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
  });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.position.set(W * 0.5, H * 0.5, D);
  scene.add(floor);

  // ── Water surface (subtle plane at z=0) ──
  const surfaceGeo = new THREE.PlaneGeometry(W, H);
  const surfaceMat = new THREE.MeshBasicMaterial({
    color: 0x1a5588,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide,
  });
  const surface = new THREE.Mesh(surfaceGeo, surfaceMat);
  surface.position.set(W * 0.5, H * 0.5, 0);
  scene.add(surface);

  // ── Grid on floor ──
  const gridGroup = new THREE.Group();
  const gridMat = new THREE.LineBasicMaterial({
    color: 0x1e3a5f,
    transparent: true,
    opacity: 0.2,
  });
  const gridStep = 25;
  for (let x = 0; x <= W; x += gridStep) {
    const pts = [new THREE.Vector3(x, 0, D), new THREE.Vector3(x, H, D)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    gridGroup.add(new THREE.LineSegments(geo, gridMat));
  }
  for (let y = 0; y <= H; y += gridStep) {
    const pts = [new THREE.Vector3(0, y, D), new THREE.Vector3(W, y, D)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    gridGroup.add(new THREE.LineSegments(geo, gridMat));
  }
  scene.add(gridGroup);

  // ── Resize handler ──
  window.addEventListener("resize", () => {
    _resize(renderer, container);
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
  });

  return {
    renderer,
    scene,
    camera,
    controls,
    pond,
  };
}

/**
 * @returns {THREE.WebGLRenderer}
 */
export function getRenderer(sceneCtx) {
  return sceneCtx.renderer;
}

function _resize(renderer, container) {
  const w = container.clientWidth;
  const h = container.clientHeight || window.innerHeight - container.offsetTop;
  renderer.setSize(w, h);
}
