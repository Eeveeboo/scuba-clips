# The hosted editor's server side

The editor lets a casual user set the clip values and download a printable STL
with no local install. The server is small and stateless: it reads the clip
schema and emits OpenSCAD source, and the browser turns that source into the STL
and the 3D preview.

## What lives where

- `lib/config.py` — `config_schema()` builds the field list by reflection from
  the config dataclasses, and `build_config()` validates one request mapping.
  There is no hand-written field list.
- `web/generator.py` — `render_scad()` sets the request config, drops the
  cached `lib.*` and `models.*` modules, imports the model again, and returns
  `solid2.scad_render(build())`. A module lock serialises generation.
- `web/service.py` — the schema and SCAD answers as `Response` values, plus the
  query parsing. It holds no socket code.
- `web/dev_server.py` — the local server. Run it with
  `uv run python -m web.dev_server`. It serves `/api/schema`, `/api/scad`, and
  the static files in `web/public/` when that folder exists.
- `api/schema.py`, `api/scad.py` — the Vercel Python entry points. Each holds
  only the HTTP plumbing and calls `web.service`.

## Updating the vendored OpenSCAD WASM

The client unit vendors the OpenSCAD WASM build under
`web/public/vendor/openscad/`. That folder comes from the npm package
`@lofcz/openscad-wasm`. To update it, install the new version and copy the
package's build output into `web/public/vendor/openscad/`, then check the
client's preview and STL generation against a known part.
