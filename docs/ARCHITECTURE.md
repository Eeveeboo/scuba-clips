# scuba-clips architecture

Refactor contract. Frozen interfaces — implement exactly these names/signatures.

## Hard rules

1. Everything under `lib/` contains **only** `module` and `function` definitions,
   with exactly one exception: `params.scad` additionally holds the plain constants
   `DEFAULT_FN` and `EPS`. No other file under `lib/` may carry a top-level
   assignment, and no file under `lib/` may contain top-level geometry. (OpenSCAD
   `use` imports modules and functions only: plain variables and `$fs`/`$fn`
   assignments in a `use`d file are silently dropped, so relying on them is a bug.
   Verified on 2026.09.12: `use` does not leak `$fs`/`$fn`/variables.)
2. No reliance on global special variables. Every public module takes
   `fn = DEFAULT_FN` and sets `$fn = fn;` as its first statement.
3. Public module names are lowercase `snake_case`. No `make_` prefix.
4. No layout/positioning inside geometry modules. Modules build geometry centred
   on the origin; callers apply `translate`/`rotate`. This replaces the old
   `origin = "center" | "bottom"` string switch.
5. String switches (`part = "main" | "cutter"`) are replaced by two modules:
   the part, and the keep-out / socket volume.
6. Named parameters for every literal that has meaning; keep the existing short
   parameter names (`d_hose`, `t_outer`, `w_gap`, `t_inner`, `h`) so reviews are
   cheap. `assert()` guards on dimensions and angle ranges.
7. No files with `.scad` entry points inside `lib/`. All renderable things live in
   `models/`.

## Constants and how `lib/` files get them

Default parameter expressions are evaluated in the **definition file's** scope, not
the caller's. So `use <params.scad>` does not make `DEFAULT_FN` visible to
`module foo(fn = DEFAULT_FN)`; it yields `WARNING: Ignoring unknown variable`
and silently falls back to OpenSCAD's default tessellation. Verified 2026.09.12:

```
use <params.scad>                     module m(fn = DEFAULT_FN) -> WARNING, fn = undef
include <params.scad> (in the lib)    module m(fn = DEFAULT_FN) -> fn = 100, no warning
```

Rules, therefore:

- **`lib/` file that needs a constant or helper function: `include <params.scad>`**
  (path is relative to the including file). `params.scad` holds assignments and
  `function`s only, so including it executes nothing but definitions.
- **Model: `use <../lib/params.scad>`.** `function`s cross a `use` boundary even
  though variables do not, so models call `webbing_hip_size()` etc. without pulling
  the constants into their own scope. Models must never `include` a `lib/` file.
- Several `lib/` files may each `include <params.scad>` in the same model: measured
  clean, no redefinition warning, and the constants do **not** leak into the
  model's scope.
- A `lib/` file that needs another `lib/` file's modules uses `use <other.scad>`
  for the modules and separately `include <params.scad>` for the constants it needs
  in its own default expressions. Do not `include` one lib from another.

## File map

| Path | Contents |
| --- | --- |
| `lib/params.scad` | `DEFAULT_FN`, `EPS`, `default_t_inner()`/`default_w_gap()`/`default_t_outer()`, hose/webbing dimension `function`s, derived-size helpers |
| `lib/shapes.scad` | `rounded_cube()`, `pie_wedge()`, `tapered_arm()` |
| `lib/c_clip.scad` | `c_clip()`, `c_clip_rounded()`, `dual_c_clip_rounded()`, `hose_clip()`, `hose_clip_socket()` |
| `lib/standoff.scad` | `standoff_clip()` |
| `lib/octi_clip.scad` | `octi_clip_part()`, `upper_octi_clip()`, `lower_octi_clip()` |
| `lib/webbing_clip.scad` | `webbing_clip()` |
| `models/*.scad` | one thin entry point per printable model, plus `all.scad` |
| `dev/print_tests.scad` | the fit-test matrix (was commented out at the bottom of the old file) |
| `tools/` | render + metrics + regression tooling, `tools/baseline/*.json` |
| `docs/images/` | screenshots referenced by `README.md` |

Old `scuba_hose_clip.scad` and `roundedcube.scad` are deleted (git history keeps them).

## Frozen signatures

`lib/params.scad`
```
DEFAULT_FN = 100;      // matches the old global $fn = 100 exactly
EPS = 0.01;

// Single source of truth for the clip wall defaults. The old file had these as
// file-level globals; they are functions so that `use` exports them.
function default_t_inner() = 2;
function default_w_gap()  = 2;
function default_t_outer() = 3;

function clip_total_diameter(d_hose, t_outer, w_gap, t_inner) =
    d_hose + t_inner / 2 + w_gap + t_outer;              // old `total_diameter`
function clip_base_diameter(d_hose, t_inner) = d_hose + t_inner / 2;   // old `base_diameter`

// Hose / webbing specs, one function each, replacing the old trailing globals.
function hose_inflator_tube_dia() = 27;
function hose_lpi_dia() = 12.5;           // old inflator_hose_d
function hose_hp_spg_dia() = 8;
function hose_reg_fitting_dia() = 18.5;   // old reg_fitting_d
function hose_mp_dia() = 12.5;            // old mp_reg_hose_d
function webbing_shoulder_size() = [50, 3];  // [width, thickness]
function webbing_hip_size() = [37.5, 5];
```

`lib/shapes.scad`
```
module rounded_cube(size = [1,1,1], radius = 0.5, center = false,
                    apply_to = "all", fn = DEFAULT_FN);
module pie_wedge(radius, angle, height, fn = DEFAULT_FN);
module tapered_arm(a_inner, r_inner, w_inner, a_outer, r_outer, w_outer, height, fn = DEFAULT_FN);
```
`rounded_cube` keeps upstream semantics (`apply_to` in `all|xmin|xmax|ymin|ymax|zmin|zmax|x|y|z`)
but must be hull-of-spheres/cylinders built directly instead of the 3-deep nested
loop with string comparisons. Drop the old file-wide `$fs = 0.01`
(it never applied through `use`, so dropping it is geometry-neutral).

**Keep the corner loops as three nested `for` statements.** This is not style. The
hull's triangulation depends on the *shape of the CSG child tree*, not on the
iteration order: manifold triangulates the same eight corners differently when they
are emitted by one multi-range `for (xi = ..., yi = ..., zi = ...)` than by three
nested `for` statements, even though the visited order is provably identical. The
nested form reproduces upstream's mesh exactly; the collapsed form does not, and the
difference propagates into every downstream union as run-to-run jitter in the
triangle count. That A/B was measured by `core`; the reproducible form is the one
committed. There is a comment in the code saying this for the same reason. Do not
"tidy" the three loops into one.

`pie_wedge` keeps the old behaviour exactly: solid wedge of `angle` degrees,
symmetric about +X, centred on Z, used to open the clip's C.

`lib/c_clip.scad`
```
module c_clip(id, od, angle, height, fn = DEFAULT_FN);                      // old make_c_sharp
module c_clip_rounded(id, od, angle, height, fn = DEFAULT_FN);              // old make_c_round
module dual_c_clip_rounded(id, od, angle_a, angle_b, height, fn = DEFAULT_FN); // old make_dual_c_round

module hose_clip(d_hose = 12, t_outer = 3, w_gap = 3, t_inner = 1.5,
                 a_inner_back = 60, a_outer_front = 90, a_offset = 15,
                 h = 10, fn = DEFAULT_FN);

module hose_clip_socket(d_hose = 12, t_outer = 3, w_gap = 3, t_inner = 1.5,
                        a_inner_back = 60, a_outer_front = 90, a_offset = 15,
                        h = 10, fn = DEFAULT_FN);
```
Positioning equivalences that must hold (this is how the old `origin`/`part`
switch is retired):
```
old make_scuba_clip(..., origin="center")            == hose_clip(...)
old make_scuba_clip(..., origin="bottom")            == translate([clip_total_diameter(...)/2, 0, 0]) hose_clip(...)
old make_scuba_clip(..., part="cutter", origin="X")  == same placement applied to hose_clip_socket(...)
```
`hose_clip_socket` is the reserved/keep-out volume (old `make_reserved_clip_space`):
full cylinder of `clip_total_diameter` plus the `a_outer_front` front wedge.
It deliberately keeps the full `hose_clip` parameter list even though it only reads
`d_hose`, `t_outer`, `w_gap`, `t_inner`, `a_outer_front` and `h`, so a call site can
emit a part and its matching negative from one argument list. This is the guard
against part and socket drifting apart. The ignored parameters must be documented
in the module as accepted-for-symmetry; do not "tidy" them away.

The inner relief cut inside the old `make_clip` (a `make_c_round` from `base_diameter`
to `base_diameter + w_gap` at `a_inner_front + a_offset`, height `h + 1`) must survive
as-is; give it a named inner module with a comment explaining intent.

**`hose_clip`'s own defaults are not the print-tuned defaults.** Its signature keeps
the original `make_scuba_clip` defaults (`t_outer = 3, w_gap = 3, t_inner = 1.5`),
which deliberately differ from `params.scad`'s `default_w_gap() = 2` and
`default_t_inner() = 2`. The old file had the same split: module defaults on
`make_scuba_clip`, different file-level globals that the models passed in. Do not
unify them. `models/*.scad` pass the print values explicitly, and the baseline
depends on the module defaults staying as they are.

`lib/standoff.scad`
```
module standoff_clip(h, tube_d, standoff_h, t_inner = default_t_inner(),
                     w_gap = default_w_gap(), t_outer = default_t_outer(),
                     fn = DEFAULT_FN);
```
The wall sizes are parameters rather than internal literals because the README
tells the user to tune the fit at the top of a model file, so a model that sets
`t_outer = 4` must be able to make the standoff clips inside it follow. A caller
that omits them gets the old file-level values, so existing call sites are
unaffected. `standoff_clip`'s own default placement of the part and its keep-out
volume must be written **once** and shared (one local module with `children()`),
never written out per-leaf: duplicated placement is the exact drift this refactor
exists to remove.

`lib/octi_clip.scad`
```
module octi_clip_part(h, tube_d, standoff_h, w_strap, t_strap, offset = 0, fn = DEFAULT_FN);
module upper_octi_clip(fn = DEFAULT_FN);
module lower_octi_clip(fn = DEFAULT_FN);
```
The old `alignment` parameter was a string or a number depending on the call site
(`alignment = "outer"` vs `alignment = -6`); both usages are really a numeric
x-offset, so `octi_clip_part` takes `offset` and all magic numbers in
`upper_octi_clip`/`lower_octi_clip` (22.5, 30, -22, 14.5, 29, -6, -31, 63, 51, ...)
become named locals with a one-line comment saying what they position.

**Sign of `offset` (frozen):** `offset` is a displacement in millimetres along +x,
so a positive value moves the clip in the +x direction. The old numeric `alignment`
was its negation, and old `alignment = "outer"` is `offset = 0`. Rationale: the old
form had a negative-looking value moving the part in +x, which is a trap for the
next reader; state the convention in the module's own comment as well, so the sign
never has to be inferred from a call site.

`lib/webbing_clip.scad`
```
module webbing_clip(wall_t, webbing_t, webbing_w, h, gap, tube_d = 12, fn = DEFAULT_FN);
```
The hardcoded `tube_d=12` moves to a default parameter. `webbing_clip` passes its
`wall_t` through to the standoff clips it contains as their `t_outer`, so the block
wall and the clips on it stay consistent when a model tunes the fit.

## Models

Each `models/*.scad` is thin: a header comment, `use <../lib/...>`, a
`MODEL_FN = 100;` variable (so `-D MODEL_FN=36` gives a draft render), the model's
own tuning variables, then one instantiation. `models/all.scad` keeps the old
print-plate layout (`translate([100,0,0])`, `translate([100,-50,0])`,
`translate([0,-50,0])`).

`models/all.scad` may `use` a sibling model file to reuse a multi-part assembly
rather than duplicating it, precisely because `use` does not execute the sibling's
top-level instantiation. This is the one sanctioned cross-`models/` import; it works
only under `use`, so do not switch such an import to `include` — that would emit the
sibling's model twice, in the wrong place.

## Regression contract

`tools/baseline/*.json` holds per-model metrics captured from commit `29a54aa`.
At `MODEL_FN = 100` every refactored model must match the baseline:
volume within 0.05% relative and bounding box within 0.01 mm, and render with
`Status: NoError` on the manifold backend. Do not "fix" a mismatch by editing the
baseline — fix the geometry.

Additionally, every model must render with `open_edges == 0` (see
`tools/stl_metrics.py`). The baseline satisfies this on all four models, and it is
the invariant that actually protects the user: a torn mesh slices badly, where a
triangle count off by four does not.

### Triangle counts: exact on the baseline toolchain, advisory otherwise

Triangle count is asserted **exactly** when the OpenSCAD build matches the one that
produced `tools/baseline/*.json` (recorded per baseline as `openscad_version`), and
with a 0.5% advisory band otherwise. The asymmetry is deliberate: within a pinned
toolchain the count is a deterministic function of the model, so exactness is a free
and sharp regression signal; across nightly versions manifold's triangulation may
legitimately change while the solid does not, so exactness there would fail
`make verify` on a non-bug and teach the user to ignore the check.

History, so this is not relitigated. The count used to jitter run to run on
byte-identical input (15040..15052), which made it worthless as an assertion and a
STL diff meaningless. The cause was bisected to `rounded_cube`: a collapsed
multi-range `for` builds a different child tree, and manifold then triangulates the
resulting coincident faces non-deterministically. Nesting the loops restored
determinism, and all four models now reproduce the baseline counts exactly on
repeated renders. If the count ever moves *within* a matching toolchain, treat it as
a real change to the CSG tree, not as noise.

Volume and bbox tolerances (0.05%, 0.01 mm) stay loose on purpose even though the
current models measure 0.00000%: they are the check that survives an OpenSCAD
upgrade and a legitimate `fn` change.

A dropped `fn` — the failure the count would otherwise catch — is caught far better
by volume (2.04% error) plus the explicit `Ignoring unknown variable "DEFAULT_FN"`
check in `tools/verify.sh`.

Do not "restore exactness" or widen the band without re-reading this section.
