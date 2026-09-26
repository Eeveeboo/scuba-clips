// A minimal STL viewer: one mesh, one orbit control, a reference grid, an
// axis indicator, and a light.
//
// The camera keeps its place across re-renders of the same clip, so a value
// change does not move the view. It frames the model again only when the clip
// itself changes, because a different clip has a different size. The camera
// lives in memory; it never goes to the URL, localStorage, or a cookie.
//
// A ResizeObserver follows the container, so the canvas matches the panel
// after the page hides, shows, or changes size.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const MINOR_COLOR = 0x3a4048;
const MAJOR_COLOR = 0x6b7787;
const MIN_SPAN = 50;
const MAX_SPAN = 400;

export function createPreview(container) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x20242b);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.domElement.style.display = "block";
  container.append(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const light = new THREE.DirectionalLight(0xffffff, 1.4);
  light.position.set(60, 90, 120);
  scene.add(light);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const loader = new STLLoader();
  let mesh = null;
  let reference = null;
  let lastModel = null;

  function resize() {
    const width = container.clientWidth || 1;
    const height = container.clientHeight || 1;
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  resize();
  new ResizeObserver(resize).observe(container);

  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });

  function clearReference() {
    if (!reference) {
      return;
    }
    scene.remove(reference);
    reference.traverse((child) => {
      if (child.geometry) {
        child.geometry.dispose();
      }
      if (child.material) {
        child.material.dispose();
      }
    });
    reference = null;
  }

  // One grid at 10 mm lines over one at 1 mm lines, an axis indicator, and the
  // whole group lifted to the bottom of the model. The span comes from the
  // model size and stays bounded, so the line count cannot run away.
  function addReference(span, floorY) {
    clearReference();
    reference = new THREE.Group();
    const minor = new THREE.GridHelper(span, span, MINOR_COLOR, MINOR_COLOR);
    const major = new THREE.GridHelper(span, span / 10, MAJOR_COLOR, MAJOR_COLOR);
    major.position.y = 0.05;
    reference.add(minor);
    reference.add(major);
    reference.add(new THREE.AxesHelper(span / 2));
    reference.position.y = floorY;
    scene.add(reference);
  }

  function show(buffer, modelName) {
    const geometry = loader.parse(buffer);
    geometry.computeVertexNormals();
    geometry.center();
    geometry.computeBoundingBox();
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

    const box = geometry.boundingBox;
    const size = new THREE.Vector3();
    box.getSize(size);

    const maxDimension = Math.max(size.x, size.y, size.z);
    const span = Math.min(
      MAX_SPAN,
      Math.max(MIN_SPAN, Math.ceil(maxDimension / 10) * 10)
    );
    addReference(span, box.min.y);

    if (modelName !== lastModel) {
      lastModel = modelName;
      const radius = geometry.boundingSphere ? geometry.boundingSphere.radius : 50;
      const distance = Math.max(radius, 1);
      camera.position.set(distance * 1.6, distance * 1.4, distance * 1.6);
      camera.near = distance / 100;
      camera.far = distance * 100;
      camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
      controls.update();
    }
    return size;
  }

  return { show, resize };
}
