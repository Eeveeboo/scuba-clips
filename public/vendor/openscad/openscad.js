/// <reference types="./openscad.d.ts" />
let factory;
// Static specifier on purpose: bundlers (webpack/rspack/vite) resolve it
// into the module graph and code-split the glue. A computed
// `import(new URL(...))` is opaque to them and fails at runtime.
function loadFactory() {
    return import('./openscad.wasm.js').then((module) => module.default);
}
// Static `new URL(asset, import.meta.url)` so bundlers emit the wasm as an
// asset and swap in the emitted URL. In Node/Deno this is a file:// URL —
// pass `instantiateWasm` there, the browser fetches it natively.
const WASM_URL = new URL("./openscad.wasm", import.meta.url);
async function OpenSCAD(options) {
    if (!factory) {
        factory = loadFactory().catch((error) => {
            // Don't cache a rejected import, so a failed load can be retried.
            factory = undefined;
            throw error;
        });
    }
    const createModule = await factory;
    return await createModule({
        noInitialRun: true,
        locateFile: (path) => path.endsWith(".wasm") ? WASM_URL.href : new URL(`./${path}`, import.meta.url).href,
        ...options,
    });
}
let buildInfo;
function getBuildInfo() {
    if (!buildInfo) {
        buildInfo = readBuildInfo().catch((error) => {
            // Don't cache a failure, so it can be retried.
            buildInfo = undefined;
            throw error;
        });
    }
    return buildInfo;
}
async function readBuildInfo() {
    const lines = [];
    const instance = await OpenSCAD({
        noInitialRun: true,
        print: (text) => lines.push(text),
        printErr: () => { },
    });
    instance.callMain(["--info"]);
    return lines;
}

export { OpenSCAD as default, getBuildInfo };
