// The editor's page logic: build the form from the schema, keep the URL in
// step with the form, and turn the server's SCAD into an STL.
//
// The form has no hard-coded field, section, or default: everything comes from
// `GET /api/schema`. The URL is the only state, and it uses the same keys as
// the SCAD request, so a copied URL reproduces the same clip.
//
// One render runs at a time. A change during a render marks the input as newer
// and starts one more render when the current one ends, so the newest input
// always wins and two WASM calls never run together.

import { scadToStl } from "./openscad.js";
import { createPreview } from "./preview.js";

const API = "/api";
const DEBOUNCE_MS = 400;
const form = document.getElementById("form");
const sections = document.getElementById("sections");
const statusLine = document.getElementById("status");
const dimensions = document.getElementById("dimensions");
const downloadStl = document.getElementById("download-stl");
const downloadScad = document.getElementById("download-scad");
const preview = createPreview(document.getElementById("preview"));

let downloadUrls = [];
let changeVersion = 0;
let rendering = false;
let debounceTimer = null;

function setStatus(message, isError) {
  statusLine.textContent = message;
  statusLine.classList.toggle("error", isError);
}

async function loadSchema() {
  const response = await fetch(`${API}/schema`);
  if (!response.ok) {
    throw new Error(`The schema request failed with status ${response.status}.`);
  }
  return response.json();
}

function fieldInput(field) {
  const input = document.createElement("input");
  input.name = field.key;
  input.dataset.type = field.type;
  if (field.type === "float_list") {
    input.type = "text";
    input.value = field.default.map((value) => String(value)).join(", ");
  } else if (field.type === "bool") {
    // A checkbox carries its state in `checked`, not `value`, so the boolean
    // needs its own branches in fieldInput, applyUrl and collectParams.
    input.type = "checkbox";
    input.checked = field.default;
  } else {
    input.type = "number";
    input.step = field.type === "int" ? "1" : "any";
    input.value = String(field.default);
  }
  return input;
}

function renderField(field) {
  const label = document.createElement("label");
  const caption = document.createElement("span");
  caption.textContent = field.label;
  label.append(caption);
  const input = fieldInput(field);
  input.id = field.key;
  label.append(input);
  if (field.comment) {
    const help = document.createElement("small");
    help.textContent = field.comment;
    label.append(help);
  }
  return label;
}

function renderForm(schema) {
  const modelSelect = document.getElementById("model");
  for (const model of schema.models) {
    const option = document.createElement("option");
    option.value = model.name;
    option.textContent = model.label;
    modelSelect.append(option);
  }
  for (const section of schema.sections) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = section.label;
    details.append(summary);
    for (const field of section.fields) {
      details.append(renderField(field));
    }
    sections.append(details);
  }
}

function applyUrl() {
  const params = new URLSearchParams(window.location.search);
  const model = params.get("model");
  if (model && form.elements.model.querySelector(`option[value="${model}"]`)) {
    form.elements.model.value = model;
  }
  for (const [key, value] of params) {
    if (key === "model") {
      continue;
    }
    const input = form.elements[key];
    if (input) {
      if (input.dataset.type === "bool") {
        input.checked = value === "true";
      } else {
        input.value = value;
      }
    }
  }
}

function collectParams() {
  const params = new URLSearchParams();
  params.set("model", form.elements.model.value);
  for (const input of form.querySelectorAll("[data-type]")) {
    if (input.dataset.type === "bool") {
      params.set(input.name, input.checked ? "true" : "false");
    } else {
      params.set(input.name, input.value);
    }
  }
  return params;
}

function updateUrl(params) {
  history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
}

function clearDownloads() {
  for (const url of downloadUrls) {
    URL.revokeObjectURL(url);
  }
  downloadUrls = [];
  downloadStl.hidden = true;
  downloadScad.hidden = true;
}

// The SCAD text already came with the render, so the second link needs no
// extra request. The user must not keep the old clip while the URL holds a
// bad value, so a failed render clears both links.
function showDownloads(stl, scadText) {
  clearDownloads();
  const stlUrl = URL.createObjectURL(new Blob([stl], { type: "model/stl" }));
  const scadUrl = URL.createObjectURL(new Blob([scadText], { type: "text/plain" }));
  downloadUrls = [stlUrl, scadUrl];
  downloadStl.href = stlUrl;
  downloadScad.href = scadUrl;
  downloadStl.hidden = false;
  downloadScad.hidden = false;
}

function formatSize(size) {
  return `${size.x.toFixed(1)} x ${size.y.toFixed(1)} x ${size.z.toFixed(1)} mm`;
}

async function runRender() {
  rendering = true;
  const version = changeVersion;
  const params = collectParams();
  const modelName = params.get("model");
  clearDownloads();
  setStatus("Rendering…", false);
  try {
    const response = await fetch(`${API}/scad?${params.toString()}`);
    const scadText = await response.text();
    if (!response.ok) {
      throw new Error(scadText.trim() || `The SCAD request failed with status ${response.status}.`);
    }
    const stl = await scadToStl(scadText);
    if (version !== changeVersion) {
      return;
    }
    const buffer = stl.buffer.slice(stl.byteOffset, stl.byteOffset + stl.byteLength);
    const size = preview.show(buffer, modelName);
    dimensions.textContent = formatSize(size);
    showDownloads(stl, scadText);
    setStatus("The clip is ready.", false);
  } catch (error) {
    if (version !== changeVersion) {
      return;
    }
    dimensions.textContent = "";
    setStatus(error.message, true);
  } finally {
    rendering = false;
    if (version !== changeVersion) {
      runRender();
    }
  }
}

function scheduleRender() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    debounceTimer = null;
    if (!rendering) {
      runRender();
    }
  }, DEBOUNCE_MS);
}

function onFormInput() {
  changeVersion += 1;
  updateUrl(collectParams());
  setStatus("Rendering…", false);
  scheduleRender();
}

async function main() {
  try {
    const schema = await loadSchema();
    renderForm(schema);
    applyUrl();
    form.addEventListener("input", onFormInput);
    form.addEventListener("submit", (event) => event.preventDefault());
    onFormInput();
  } catch (error) {
    setStatus(error.message, true);
  }
}

main();
