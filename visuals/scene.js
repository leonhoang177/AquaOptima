/**
 * scene.js -- Three.js scene: renderer, camera, controls, lights, pond, dense plants.
 * 95% of grass perfectly upright, 4% slight lean, 1% strong lean.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

export function initScene(container, pond) {
  const { width: W, height: H, depth: D } = pond;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x1a3050, 1);
  _resize(renderer, container);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x1a3050, 0.0015);

  const aspect = container.clientWidth / container.clientHeight;
  const camera = new THREE.PerspectiveCamera(50, aspect, 1, 1000);

  camera.up.set(0, 0, -1);
  camera.position.set(W * 0.5, -H * 1.5, D * 0.5);
  camera.lookAt(W * 0.5, H * 0.5, D * 0.5);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(W * 0.5, H * 0.5, D * 0.5);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 20;
  controls.maxDistance = 600;
  controls.minPolarAngle = 0;
  controls.maxPolarAngle = Math.PI;
  controls.minAzimuthAngle = -Infinity;
  controls.maxAzimuthAngle = Infinity;
  controls.update();

  scene.add(new THREE.AmbientLight(0x6688bb, 1.0));
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
  dirLight.position.set(W * 0.5, -H, D * 0.3);
  scene.add(dirLight);
  const fillLight = new THREE.DirectionalLight(0x88aacc, 0.5);
  fillLight.position.set(W * 0.5, H * 2, D * 0.5);
  scene.add(fillLight);
  const bottomLight = new THREE.DirectionalLight(0x887766, 0.3);
  bottomLight.position.set(W * 0.5, H * 0.5, D * 2);
  scene.add(bottomLight);

  const pondLine = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(W, H, D)),
    new THREE.LineBasicMaterial({ color: 0x3a7ab0 }),
  );
  pondLine.position.set(W / 2, H / 2, D / 2);
  scene.add(pondLine);

  const surfMat = new THREE.MeshBasicMaterial({
    color: 0x4a8acc,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide,
  });
  const surf = new THREE.Mesh(new THREE.PlaneGeometry(W, H), surfMat);
  surf.position.set(W / 2, H / 2, 0);
  scene.add(surf);

  const floorMat = new THREE.MeshBasicMaterial({
    color: 0x3a3028,
    transparent: true,
    opacity: 0.4,
    side: THREE.DoubleSide,
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, H), floorMat);
  floor.position.set(W / 2, H / 2, D);
  scene.add(floor);

  const gridGroup = new THREE.Group();
  const gridMat = new THREE.LineBasicMaterial({
    color: 0x4a3a2a,
    transparent: true,
    opacity: 0.12,
  });
  for (let x = 0; x <= W; x += 25) {
    gridGroup.add(
      new THREE.LineSegments(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x, 0, D),
          new THREE.Vector3(x, H, D),
        ]),
        gridMat,
      ),
    );
  }
  for (let y = 0; y <= H; y += 25) {
    gridGroup.add(
      new THREE.LineSegments(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, y, D),
          new THREE.Vector3(W, y, D),
        ]),
        gridMat,
      ),
    );
  }
  scene.add(gridGroup);

  _createPlants(scene, W, H, D);

  window.addEventListener("resize", () => {
    _resize(renderer, container);
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
  });

  return { renderer, scene, camera, controls, pond };
}

export function getRenderer(ctx) {
  return ctx.renderer;
}

function _resize(renderer, container) {
  const w = container.clientWidth;
  const h = container.clientHeight || window.innerHeight - container.offsetTop;
  renderer.setSize(w, h);
}

function _grassLean() {
  // 95% perfectly upright, 4% slight lean, 1% strong lean
  const r = Math.random();
  if (r < 0.01) return (Math.random() - 0.5) * 1.0;
  if (r < 0.05) return (Math.random() - 0.5) * 0.3;
  return 0;
}

function _createPlants(scene, W, H, D) {
  const group = new THREE.Group();
  const grassColors = [0x1a6633, 0x228844, 0x2a7744, 0x1a5533, 0x1e7040];
  const kelpColors = [0x0f4422, 0x1a5530, 0x0d3318, 0x145528];

  const spacing = 5;
  for (let gx = 3; gx < W - 3; gx += spacing) {
    for (let gy = 2; gy < H - 2; gy += spacing) {
      if (Math.random() > 0.9) continue;
      const px = gx + (Math.random() - 0.5) * spacing * 0.8;
      const py = gy + (Math.random() - 0.5) * spacing * 0.8;
      const height = 3 + Math.random() * 8;
      const width = 0.3 + Math.random() * 0.5;
      const color = grassColors[Math.floor(Math.random() * grassColors.length)];
      const mat = new THREE.MeshPhongMaterial({
        color,
        transparent: true,
        opacity: 0.6 + Math.random() * 0.15,
        side: THREE.DoubleSide,
        emissive: color,
        emissiveIntensity: 0.08,
      });
      const blade = new THREE.Mesh(new THREE.PlaneGeometry(width, height), mat);
      blade.position.set(px, py, D - height * 0.5);
      blade.rotation.x = Math.PI / 2;
      blade.rotation.z = Math.random() * Math.PI;
      blade.rotation.y = _grassLean();
      group.add(blade);

      if (Math.random() > 0.3) {
        const b2 = blade.clone();
        b2.material = mat.clone();
        b2.position.x += (Math.random() - 0.5) * 1.5;
        b2.position.y += (Math.random() - 0.5) * 1.2;
        const h2 = 2 + Math.random() * 6;
        b2.position.z = D - h2 * 0.5;
        b2.rotation.z = Math.random() * Math.PI;
        b2.rotation.y = _grassLean();
        group.add(b2);
      }
    }
  }

  // Kelp clusters
  for (let i = 0; i < 30; i++) {
    const cx = Math.random() * (W - 30) + 15;
    const cy = Math.random() * (H - 15) + 7;
    const count = 3 + Math.floor(Math.random() * 5);
    for (let j = 0; j < count; j++) {
      const kx = cx + (Math.random() - 0.5) * 6;
      const ky = cy + (Math.random() - 0.5) * 4;
      const kh = 2 + Math.random() * 5;
      const kw = 0.7 + Math.random() * 1.0;
      const kColor = kelpColors[Math.floor(Math.random() * kelpColors.length)];
      const kMat = new THREE.MeshPhongMaterial({
        color: kColor,
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
        emissive: kColor,
        emissiveIntensity: 0.05,
      });
      const kelp = new THREE.Mesh(new THREE.PlaneGeometry(kw, kh), kMat);
      kelp.position.set(kx, ky, D - kh * 0.5);
      kelp.rotation.x = Math.PI / 2;
      kelp.rotation.z = Math.random() * Math.PI;
      kelp.rotation.y = _grassLean();
      group.add(kelp);
    }
  }

  scene.add(group);
}
