# The hosted editor's server side

The editor lets a casual user set the clip values and download a printable STL
with no local install. The server is small and stateless: it reads the clip
schema and emits OpenSCAD source, and the browser turns that source into the STL
and the 3D preview.

## What lives where

- `lib/config.py` — `config_schema()` builds the field list by reflection from
  the config dataclasses, and `build_config()` validates one request mapping.
  There is no hand-written field list.
- `api/support/generator.py` — `render_scad()` sets the request config, drops the
  cached `lib.*` and `models.*` modules, imports the model again, and returns
  `solid2.scad_render(build())`. A module lock serialises generation.
- `api/support/service.py` — the schema and SCAD answers as `Response` values,
  plus the query parsing. It holds no socket code.
- `main.py` — the single Flask entrypoint at the repository root. It holds only
  the HTTP plumbing and calls `api.support.service`. Run it locally with
  `uv run flask --app main run`. It serves `/api/schema`, `/api/scad`, and the
  static files in the repository's `public/`.
- `vercel.json` — the deploy config. It sets the "Flask" framework preset,
  excludes development folders and `public/` from the function bundle with
  `functions.excludeFiles`, and sets a long cache lifetime for `/vendor/*`.
  Vercel installs the dependencies from `pyproject.toml` and `uv.lock` with uv,
  so no `requirements.txt` is needed.

The helper modules must not define `app`, `application`, or `handler`: the root
`main.py` is the single entrypoint, and Vercel deploys it as the Flask app.

## Updating the vendored OpenSCAD WASM

The client vendors the OpenSCAD WASM build under `public/vendor/openscad/`.
That folder comes from the npm package `@lofcz/openscad-wasm`. To update it,
download the new version and copy its `openscad.js`, `openscad.wasm.js`, and
`openscad.wasm` into `public/vendor/openscad/`, then check the client's preview
and STL generation against a known part.
