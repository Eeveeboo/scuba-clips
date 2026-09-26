// The editor's page logic: build the form from the schema, keep the URL in
// step with the form, and turn the server's SCAD into an STL.
//
// The form has no hard-coded field, section, or default: everything comes from
// `GET /api/schema`. The URL is the only state, and it uses the same keys as
// the SCAD request, so a copied URL reproduces the same clip.

import { scadToStl } from "./openscad.js";
import { createPreview } from "./preview.js";

const API = "/api";
const form = document.getElementById("form");
const sections = document.getElementById("sections");
const statusLine = document.getElementById("status");
const button = document.getElementById("generate");
const result = document.getElementById("result");
const download = document.getElementById("download");
const preview = createPreview(document.getElementById("preview"));

let downloadUrl = null;

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
    const fieldset = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = section.label;
    fieldset.append(legend);
    for (const field of section.fields) {
      fieldset.append(renderField(field));
    }
    sections.append(fieldset);
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
      input.value = value;
    }
  }
}

function collectParams() {
  const params = new URLSearchParams();
  params.set("model", form.elements.model.value);
  for (const input of form.querySelectorAll("[data-type]")) {
    params.set(input.name, input.value);
  }
  return params;
}

function updateUrl(params) {
  history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
}

function showDownload(stl) {
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
  }
  downloadUrl = URL.createObjectURL(new Blob([stl], { type: "model/stl" }));
  download.href = downloadUrl;
  result.hidden = false;
  preview.resize();
}

async function generate(event) {
  event.preventDefault();
  const params = collectParams();
  updateUrl(params);
  button.disabled = true;
  setStatus("Generating the clip…", false);
  try {
    const response = await fetch(`${API}/scad?${params.toString()}`);
    const scadText = await response.text();
    if (!response.ok) {
      throw new Error(scadText.trim() || `The SCAD request failed with status ${response.status}.`);
    }
    const stl = await scadToStl(scadText);
    const buffer = stl.buffer.slice(stl.byteOffset, stl.byteOffset + stl.byteLength);
    preview.show(buffer);
    showDownload(stl);
    setStatus("The clip is ready.", false);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function main() {
  try {
    const schema = await loadSchema();
    renderForm(schema);
    applyUrl();
    form.addEventListener("input", () => updateUrl(collectParams()));
    form.addEventListener("submit", generate);
  } catch (error) {
    setStatus(error.message, true);
  }
}

main();
