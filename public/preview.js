// A minimal STL viewer: one mesh, one orbit control, one light.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

export function createPreview(container) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x20242b);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  container.append(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const light = new THREE.DirectionalLight(0xffffff, 1.4);
  light.position.set(60, 90, 120);
  scene.add(light);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const loader = new STLLoader();
  let mesh = null;

  function resize() {
    const width = container.clientWidth || 1;
    const height = container.clientHeight || 1;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  function show(buffer) {
    const geometry = loader.parse(buffer);
    geometry.computeVertexNormals();
    geometry.center();
    geometry.computeBoundingSphere();

    if (mesh) {
      scene.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
    const material = new THREE.MeshStandardMaterial({
      color: 0x6fb7d8,
      metalness: 0.1,
      roughness: 0.6,
    });
    mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    const radius = geometry.boundingSphere ? geometry.boundingSphere.radius : 50;
    const distance = Math.max(radius, 1);
    camera.position.set(distance * 1.6, distance * 1.4, distance * 1.6);
    camera.near = distance / 100;
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();
  }

  return { show };
}
