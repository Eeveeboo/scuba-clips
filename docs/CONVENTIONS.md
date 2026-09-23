# scuba-clips conventions

How the library is built; the rules that hold geometry still.

## Hard rules

1. Three places hold code, and each has one job. `constants/hardware.py` holds
   the kit: the hose diameters and the webbing sizes, as plain assignments, for
   the user to edit. `lib/` holds reusable builders. `models/` holds one part per
   file: the part's builder, its tuning variables, and its plate expectation. No
   `lib/` builder and no constants assignment runs geometry at import time.
2. No global tessellation variable. Every builder takes `fn: int` and passes
   `_fn=fn` to every primitive that tessellates: `cylinder`, `sphere`, `circle`,
   `rotate_extrude`, and `text`. `cube`, `square`, `polygon`, and
   `linear_extrude` take no `_fn`. A `lib/` builder defaults to
   `fn: int = DEFAULT_FN`; a model builder defaults to `fn: int = MODEL_FN`. A
   model has no `DEFAULT_FN`. Never call `set_global_fn`.
3. Public builders are lowercase `snake_case`, with no `make_` prefix, and build
   centred on the origin; the caller positions them.
4. A part and its keep-out volume are two builders that take one argument list,
   so the pair cannot drift apart. `hose_clip` and `hose_clip_keepout` are the
   example.
5. Keep the short parameter names (`d_hose`, `t_outer`, `w_gap`, `t_inner`,
   `h`). Keep the guard on every builder, as a `raise ValueError`, not an
   `assert`: `python -O` removes an `assert` statement, and the guard must
   survive. A one-line comment above each builder says what it builds. A model's
   tuning variables carry a one-line comment too.
6. A model builder takes `fn: int = MODEL_FN` and nothing else. It reads its own
   file-level variables, so the part's numbers sit at the top of its file; a
   `lib/` builder keeps taking its dimensions as parameters.
7. A model's plate expectation is `EXPECTED_REGIONS: Final = N`:
   `models/all.py` says 3 and each single part says 1. It is the number of
   separate silhouettes the plate must show. A mismatch is a warning, not a
   failure: a camera that merges two parts into one blob is worth saying out
   loud, but it is a judgement call, unlike a blank or edge-clipped plate, which
   still fails.

## Imports

- A `lib/` builder imports the primitives it uses from `solid2`, and the
  formulas it needs from `lib.params`. Annotate each builder with
  `OpenSCADObjectPlus`, which `solid2` exports.
- A model imports its part's builders from `lib/`, and reads the kit from
  `constants/hardware.py`.
- Importing a model builds nothing. That is why each model's entry point is a
  builder function, and why `models/all.py` can import the three parts.
- `constants/hardware.py` holds plain assignments only: no builders, no
  formulas, no geometry.
- The type checker is `ty`; the linter and the formatter are `ruff`. Run
  `make typecheck` and `make lint` with every proof.

## File map

`constants/hardware.py`: the kit — `hose_*_dia` and `webbing_*_size`, plain
assignments.
`lib/params.py`: library defaults — `DEFAULT_FN`, `EPS`, `default_t_inner()`,
`default_w_gap()`, `default_t_outer()`, `hose_clip_total_dia()`,
`hose_clip_base_dia()`. `lib/shapes.py`: `rounded_cube`, `pie_wedge`,
`tapered_arm`. `lib/c_clip.py`: `c_ring_sharp`, `c_ring_rounded`,
`c_ring_rounded_two_openings`, `hose_clip`, `hose_clip_keepout`.
`lib/standoff.py`: `hose_clip_on_standoff`.
`models/inflator_spg_combo_clip.py`: `inflator_spg_combo_clip`.
`models/upper_octi_retaining_clip.py`: `strap_block_hose_clip`,
`_flared_webbing_slit`, `upper_octi_retaining_clip`.
`models/webbing_side_clip.py`: `webbing_side_clip`.
`models/all.py`: the print plate, all three parts.
`dev/print_tests.py`: fit coupons. `tools/`: the build and regression harness,
`tools/baseline/`.

## Traps

- **Give `hull()` exactly one child, and one union per loop level.**
  `rounded_cube` nests one `union()` per loop level (`xi`, then `yi`, then
  `zi`), and `hull()` gets that single outer union. The flat form moves the
  triangle count: eight children give 10510 triangles, the nested union gives
  10532, and the source gives 10532. A group built from a loop is an explicit
  union.
- **Keep a nested difference nested.** `difference()(difference()(od, id),
  wedge)` keeps the tree the source had. Writing `od - id - wedge` flattens the
  tree, and the flat form moved `c_ring_sharp`'s triangle count. Use explicit
  `difference()` where the source nests one.
- **An explicit union node can move a draft count.** `solidpython2` writes an
  explicit `union()` where the old source inlined a multi-statement group. At
  draft `fn=36` the combo clip can differ by a few triangles (measured 3312
  against 3322, same volume, 0 open edges); every committed `fn=100` mesh and
  image is exact.
- **`rounded_cube` keeps three nested loops.** A collapsed multi-range loop
  builds a different child tree, so the mesh and the triangle count change. Keep
  the order x, y, z, and keep the `if` that picks a sphere or a cylinder.
- **`rounded_cube` keeps `apply_to`.** Keep the seven face names and the three
  axis names, and keep the guard.
- **`hose_clip`'s defaults differ from `params.py`'s fit defaults:**
  `t_outer = 3`, `w_gap = 3`, `t_inner = 1.5` against `default_w_gap() = 2` and
  `default_t_inner() = 2`. Models pass the print values in; do not unify.
- **`hose_clip_keepout` keeps its unused parameters.** A part and its keep-out
  volume take one argument list, so the pair cannot drift apart.
- **`offset` is a displacement in millimetres along +x.** The old
  `alignment = "outer"` is `offset = 0`. It is a tuning variable in
  `models/upper_octi_retaining_clip.py`, and its sign comment stays with it.
- **`models/all.py` imports the parts.** Importing a model builds nothing. The
  entry point is a builder function, so an import cannot run a part twice.
- **`_fn` is not universal.** `cylinder`, `sphere`, `circle`, `rotate_extrude`,
  and `text` take it. `cube`, `square`, `polygon`, and `linear_extrude` do not;
  `cube(_fn=100)` raises `TypeError` at run time.
- **`_fn` is an `int`, never `None`.** A builder that declares `fn: int | None`
  and forwards it fails the type check. Keep `fn: int` everywhere.
- **Five calls are unchecked.** The convenience wrappers `cube`, `square`,
  `translate`, `rotate`, and `mirror` are declared `*args, **kwargs`, so ty
  cannot see their keywords. A mistake there reaches Python and raises
  `TypeError` in the generator; the render gate still catches it, because the
  generator stops before OpenSCAD starts.
- **Number format.** `solidpython2` writes `[1.0, 2.5]` where the old source had
  `[1, 2.5]`, and `1e-05` where it had `0.00001`. OpenSCAD reads both. Do not
  "tidy" a value.
- **`norm`.** Use `math.sqrt(dx*dx + dy*dy)`, not `math.hypot`, so the last bit
  matches.
- **`text()` in the coupons** needs `font="Liberation Sans"`, `halign="right"`,
  and `valign="center"`, as before, and it takes `_fn=fn`.
- **The `fn` canary.** A dropped `fn` shows up as a moved triangle count.

## Verification contract

`make check-baseline` renders all four models at `MODEL_FN = 100` and compares
the three parts against `tools/baseline/*.json` (captured from commit `29a54aa`).
The plate `models/all.py` has no baseline: check-baseline renders it and checks
its mesh and its screenshot.

- volume within 0.05% relative, bounding box within 0.01 mm, and
  `open_edges == 0` (a torn mesh slices badly, so that check protects the user);
- triangle count exact when the running OpenSCAD is the build that made the
  baseline, inside a 0.5% band otherwise. On the pinned toolchain the count is a
  deterministic function of the model, so a moved count means the CSG tree
  changed — a regression, not noise. The pinned build is OpenSCAD 2026.09.12;
- volume and bbox stay loose on purpose, to survive an OpenSCAD upgrade and a
  legitimate `fn` change. A dropped `fn` shows up as a moved triangle count;
- the plate's region count is compared against the model's own
  `EXPECTED_REGIONS` (`--components N` overrides it for a one-off look). A
  mismatch only warns: how a camera splits a part into silhouettes is a
  judgement call, while a blank or edge-clipped plate fails the build.
