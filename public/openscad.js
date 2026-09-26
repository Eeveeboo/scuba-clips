// Run the vendored OpenSCAD WASM on one SCAD source and return the STL bytes.
//
// The wrapper caches the compiled module, so a second call reuses it. Each call
// still builds a fresh instance with its own in-memory filesystem.

import createOpenSCAD from "./vendor/openscad/openscad.js";

export async function scadToStl(scadText) {
  const log = [];
  const instance = await createOpenSCAD({
    noInitialRun: true,
    print: (text) => log.push(text),
    printErr: (text) => log.push(text),
  });
  instance.FS.writeFile("/in.scad", scadText);
  const exit = instance.callMain([
    "/in.scad",
    "--backend",
    "Manifold",
    "--render=true",
    "--export-format",
    "binstl",
    "-o",
    "/out.stl",
  ]);
  const output = log.join("\n");
  if (exit !== 0) {
    throw new Error(`OpenSCAD exited with status ${exit}. ${output}`);
  }
  if (!/Status:\s+NoError/.test(output)) {
    throw new Error(`OpenSCAD did not report Status: NoError. ${output}`);
  }
  return instance.FS.readFile("/out.stl");
}
