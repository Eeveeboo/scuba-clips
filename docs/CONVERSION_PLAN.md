# Convert scuba-clips to SolidPython

This document is the handoff plan for one job: replace the OpenSCAD sources
with Python, so that Python is the only thing we maintain. This is a refactor.
The geometry must not change.

Read `docs/CONVENTIONS.md` before you start. It holds the geometry rules that
stay in force.

## 1. Goal and rules

Goal: the same three parts and the same print plate, built from Python sources
through the `solidpython2` library.

Rules for this job:

- Do not change `tools/baseline/*.json`. A moved metric is a defect in the new
  Python code, not a baseline to update.
- Do not hand-edit `docs/images/*.png`. Render them.
- Do not commit, push, amend, or rewrite history.
- Change only the code this job needs. Keep the change small.
- When the work grows, stop and report. Do not extend the job without a message.
- Ask before you leave a requirement out.

## 2. Decisions already made

| Item | Decision |
| --- | --- |
| Library | `solidpython2` |
| Layout | Flat. Keep `constants/`, `lib/`, `models/`, `dev/` |
| Generated `.scad` | Build output only, in `build/scad/`. Not committed |
| Type checker | `ty`. Not mypy |
| Linter & Formatter | `ruff` |
| Type style | Plain Python, fully annotated. No raw SCAD identifiers |
| `fn` plumbing | A Python argument. No `-D MODEL_FN=` on the command line |
| A moved metric | Fix the generator |
| DX | `make watch`, auto discovery, `make save-baseline`, `make check-baseline` |
| Priority | Humans first, agents second. The human edit-and-look loop comes first |

## 3. Verified facts

These facts come from measurement. Reproduce them before you change code.

| Fact | Value | How to reproduce |
| --- | --- | --- |
| The harness passes now | All 4 models PASS. Triangle counts exact | `make verify IMG_DIR=build/verify-images` |
| Plate images | A fresh render is byte-identical to `docs/images/*.png` | `cmp docs/images/x.png build/verify-images/x.png` |
| OpenSCAD | 2026.09.12. This is the build that recorded the baselines | `OpenSCAD --version` |
| ty | 0.0.79. It resolves `from lib.shapes import box` from the project root, with no config | `uv run ty check` |
| solidpython2 packaging | Version 2.1.3 ships no `py.typed`, and no stub package exists on PyPI. ty reads the source annotations anyway | `ls .venv/lib/*/site-packages/solid2` |
| Explicit union | Same mesh as OpenSCAD's implicit union. 340 triangles and 1114.262 mm3 for both | See appendix A |
| Single-child union | Same mesh as a bare child. 12 triangles and 1000.0 mm3 for both | See appendix A |
| Operators | `a + b` writes `union`, `a - b` writes `difference`, and the order is kept | See appendix A |
| `$fn` | `cylinder(..., _fn=36)` writes `cylinder($fn = 36, ...)` | See appendix A |
| `_fn` support | `cylinder`, `sphere`, `circle`, `rotate_extrude`, and `text` take `_fn`. `cube`, `square`, `polygon`, and `linear_extrude` do not | `inspect.signature` |
| Child list | `hull()(children)` and `union()(children)` accept one Python list. Do not spread it | See appendix A |
| A group node in `hull()` | An eight-child `hull()` gives 10510 triangles. One union child gives 10532. The SCAD source gives 10532 | See appendix A |
| Nested difference | `a - b - c` and `difference()(a, b, c)` give the same mesh: 424 triangles and 704.193 mm3 | See appendix A |
| Rounded cube port | Matches the SCAD original on both branches: 10532 triangles with every corner rounded, 434 with only the z-axis corners rounded, the same volume, no open edges | See appendix A |
| ty and solidpython2 | ty reads solidpython2's own annotations and checks the call sites. `cylinder(h=1, r=0.5, _fn=100)` passes. `_fn=None` is refused: `_fn` is declared `int` | See appendix A |
| Unchecked calls | The convenience wrappers `cube`, `square`, `translate`, `rotate`, and `mirror` are declared `*args, **kwargs`, so ty does not check their keywords | See appendix A |

The union result is the important one. `solidpython2` always writes an explicit
`union()` where the SCAD source leans on an implicit union. That change is safe
for the mesh. You can therefore replace two statements in a module body with
`a + b`.

The `hull()` result is the second important one. It is a trap, not a gift.
Section 10 has the rule.

The `ty` result means no shim module is needed. Import the primitives from
`solid2` in each module that needs them, and annotate each builder with
`OpenSCADObjectPlus`.

## 4. Target tree

```
constants/
  __init__.py
  hardware.py        the kit: hose diameters and webbing sizes
lib/
  __init__.py
  params.py          DEFAULT_FN, EPS, the fit defaults, the envelope formulas
  shapes.py          rounded_cube, pie_wedge, tapered_arm
  c_clip.py          the C rings, hose_clip, hose_clip_keepout
  standoff.py        hose_clip_on_standoff
models/
  __init__.py
  all.py             the print plate
  inflator_spg_combo_clip.py
  upper_octi_retaining_clip.py
  webbing_side_clip.py
dev/
  __init__.py
  print_tests.py     the fit coupons
tools/
  render.py          render one model
  verify.py          save or check the baselines
  watch.py           new: re-render on a change
  baseline/          the frozen metrics. Do not edit
build/               gitignored output, including build/scad/ and build/watch/
```

Delete every `.scad` source at the end. `git log` keeps them.

## 5. Conventions for the Python sources

These replace the matching rules in `docs/CONVENTIONS.md`.

1. Three places hold code, and each has one job. `constants/hardware.py` holds
   the kit, as plain assignments, for the user to edit. `lib/` holds the
   reusable builders. `models/` holds one part per file. No `lib/` module and no
   constants module runs geometry when it is imported.
2. Every builder takes `fn: int` and passes `_fn=fn` to every primitive that
   tessellates: `cylinder`, `sphere`, `circle`, `rotate_extrude`, and `text`.
   `cube`, `square`, `polygon`, and `linear_extrude` take no `_fn`. The type is
   `int`, never `int | None`: solidpython2 declares `_fn: int`, and it refuses
   `None`. A `lib/` builder defaults to `DEFAULT_FN`. A model builder defaults
   to its own `MODEL_FN`. Never call `set_global_fn`.
3. The file name is the entry point. `models/webbing_side_clip.py` defines
   `webbing_side_clip(fn: int = MODEL_FN) -> OpenSCADObjectPlus`.
   `models/all.py` imports the three part builders and calls them with the same
   `fn`.
4. A model states its plate expectation as `EXPECTED_REGIONS: Final = 1`. This
   replaces the `// Config: {expected_regions: N}` comment. `models/all.py`
   states 3.
5. Keep the current names, the short parameter names, and the comment above each
   builder. The rename table in `docs/CONVENTIONS.md` stays correct.
6. Replace each `assert()` guard with a Python `raise ValueError`, not with
   `assert`. `python -O` removes an `assert` statement, and the guard must
   survive. The guard now runs before OpenSCAD starts.
7. Keep the arithmetic as it is, in the same order, and keep the parentheses.
   The tessellation depends on the exact floating-point values.
8. Import each primitive from `solid2` in the module that uses it. Annotate the
   object type as `OpenSCADObjectPlus`, which `solid2` exports. Then every
   builder has a real return type, and ty checks the keyword arguments.
   Appendix B holds the version that was run.
9. Give `hull()` exactly one child. Write `hull()(union()(children))`, not
   `hull()(children)`. The flat form moves the triangle count. Section 10 has
   the numbers and the reason.

## 6. Make targets

| Target | Job |
| --- | --- |
| `make watch` | The human loop. Watch `models/`, `lib/`, `constants/` |
| `make one MODEL=x` | One model, STL and PNG |
| `make all` | Every model, STL and PNG. `all` is `stl` + `png` |
| `make stl`, `make png` | Every model, one artefact kind |
| `make scad` | Write every generated `.scad` into `build/scad/` |
| `make typecheck` | `uv run ty check` |
| `make lint` | `uv run ruff check` |
| `make format` | `uv run ruff format` |
| `make preview` | Draft build at `fn=36` into `build/draft/` |
| `make save-baseline` | Render all and write `tools/baseline/*.json` |
| `make check-baseline` | Render all and compare against the baselines |
| `make clean` | Remove `build/` |
| `make help` | The target list |

`make verify` retires. `make check-baseline` is the same run under an honest
name. Reserve it for refactors. The everyday loop is `make watch`.

### `make watch`

- Discover the models from `models/*.py`.
- Render every model once at start, so a viewer has all the images.
- A change in `models/x.py` re-renders `x`, and only `x`.
- A change in `lib/*.py` or `constants/*.py` re-renders every model.
- Write PNG only, into `build/watch/`. Keep `docs/images/` for `make png`.
- Use a polling loop of `os.stat` mtimes. Add no dependency. Batch changes
  inside a debounce window. Render one model at a time.
- Keep the last good image: `tools/render.py` already stages and renames.

## 7. Harness changes

`tools/render.py`:

- Take `models/<name>.py` in place of `models/<name>.scad`.
- Import `models.<name>`, call `models.<name>.<name>(fn=fn)`, and write
  `build/scad/<name>.scad` with `solid2.scad_render_to_file`.
- Pass `fn` to the builder. Drop `-D MODEL_FN=`.
- Read `EXPECTED_REGIONS` from the imported module and pass it to
  `png_check.check`. Drop the `// Config:` comment reader.
- Keep the manifold flags, the log checks, the staging, the trim, and the
  `"Status: NoError"` check. They do not change.

`tools/verify.py`:

- Discover the models from `models/*.py`.
- Add `--save`, which writes the baseline JSON files instead of comparing.
  Keep every comparison tolerance and every check as it is.
- Delete the `DEFAULT_FN` canary check. `include` and `use` are gone, so the
  canary can never fire.

`tools/png_check.py`:

- Delete `model_config`, `components_from_model`, `CONFIG_RE`, `PAIR_RE`,
  `KNOWN_KEYS`, `_coerce`, and the `--components-from` option. The caller now
  passes the count.
- Keep `--components N` and every image check.

`pyproject.toml`:

```toml
dependencies = ["numpy>=1.26", "pillow>=10.3", "solidpython2>=2.1.3"]

[dependency-groups]
dev = ["ty>=0.0.79", "ruff>=0.16.8"]
```

`ruff` lints and formats the new Python sources. Run `make lint` with every
proof that runs `make typecheck`. Do not reformat the existing `tools/*.py`;
section 11 says why.

## 8. Steps and proofs

Do the steps in this order. Each step ends with a proof. Do not start the next
step until the proof passes.

### Step 1: dependencies and the type check

Add `solidpython2` and `ty`. Prove two things before you port anything.

Proof, first part: one module imports `cube`, `cylinder`, and
`OpenSCADObjectPlus` from `solid2`, builds a small solid, and writes it with
`scad_render`. `uv run ty check` finds no error, and the module prints OpenSCAD
source.

Proof, second part: prove that ty refuses a bad call. Put `_fn=None` on one
primitive in a scratch file, run `uv run ty check`, and confirm it reports
`invalid-argument-type`. Then delete the scratch file. This proves the check is
live before you rely on it.

### Step 2: the kit and the library defaults

Port `constants/hardware.scad` to `constants/hardware.py` and
`lib/params.scad` to `lib/params.py`.

Proof: `uv run ty check`.

### Step 3: the primitives

Port `lib/shapes.scad`, `lib/c_clip.scad`, and `lib/standoff.scad`.

Proof, first part: run the round trip on `rounded_cube` itself, with
`size=[10, 12, 14]`, `radius=1.5`, `center=true`, and `fn=100`. With
`apply_to="all"` expect 10532 triangles and 1614.41 mm3. With `apply_to="z"`
expect 434 triangles and 1652.895 mm3. Both must have zero open edges, and both
must match a render of the SCAD original. Do not go on until both match.

Proof, second part: build one part with `hose_clip` at the model's own numbers,
render it, and compare the metrics against a render of the SCAD `hose_clip` at
the same numbers. Expect the same volume, the same bounding box, the same
triangle count, and zero open edges.

### Step 4: the smallest part

Port `models/webbing_side_clip.scad` and move `tools/render.py` onto Python
models, so this step renders through the new path.

Proof: `make check-baseline` shows 9690.235 mm3, a 61.5 x 26.583 x 19.999 mm
box, 11448 triangles, and 0 open edges.

### Step 5: the two other parts

Port `models/upper_octi_retaining_clip.scad` and
`models/inflator_spg_combo_clip.scad`.

Proof: `make check-baseline` shows 28760.040 mm3 and 15046 triangles for the
octi clip, and 5242.845 mm3 and 7828 triangles for the combo clip.

### Step 6: the print plate

Port `models/all.scad` to `models/all.py`, and re-render the plates.

Proof: `cmp` reports that all four fresh images match `docs/images/*.png`. The
plate must show three regions.

### Step 7: watch and the new targets

Add `tools/watch.py`, add the new targets to the `Makefile`, and split the
baseline tool.

Proof: `make check-baseline`, `make typecheck`, and `make all` pass. In a
`make watch` run, one model change re-renders that model alone, and one `lib/`
change re-renders all models.

### Step 8: the coupons and the documents

Port `dev/print_tests.scad` to `dev/print_tests.py`. Rewrite `README.md` and
`docs/CONVENTIONS.md`. Delete every `.scad` source.

Proof: `make check-baseline` and `make all` pass on the clean tree, and
`grep -r --include=*.scad .` finds no source file outside `build/`.

## 9. Baseline values

`make check-baseline` compares against these numbers. `MODEL_FN = 100` for all
of them, and the toolchain is OpenSCAD 2026.09.12.

| Model | Volume mm3 | Bounding box mm | Triangles | Open edges |
| --- | --- | --- | --- | --- |
| `inflator_spg_combo_clip` | 5242.845 | [-11.887, -20.488, -5.0] to [36.39, 18.248, 5.0] | 7828 | 0 |
| `upper_octi_retaining_clip` | 28760.040 | [-34.25, -9.0, -31.0] to [31.25, 39.131, 24.999] | 15046 | 0 |
| `webbing_side_clip` | 9690.235 | [-30.75, -5.5, -10.0] to [30.75, 21.083, 9.999] | 11448 | 0 |

The plate `all` has no baseline. It renders, and it must show three regions.

Tolerances, unchanged: volume within 0.05% relative, bounding box within
0.01 mm, triangle count exact on the baseline toolchain, zero open edges.

## 10. Traps

Each line here cost time before. Keep them.

- **`hull()` takes one child in the source.** The SCAD `rounded_cube` writes
  `hull() for (xi) for (yi) for (zi) ...`. In OpenSCAD a module body of several
  statements is an implicit union, so `hull()` has one child, a union. A Python
  list makes it eight children. Measured on a `[10, 12, 14]` cube of radius 1.5
  at `fn=100`: eight children give 10510 triangles, one union child gives
  10532, and the SCAD source gives 10532. Write `hull()(union()(children))`.
  The same rule applies anywhere else you build a group from a loop.
- **`_fn` is not universal.** `cylinder`, `sphere`, `circle`, `rotate_extrude`,
  and `text` take it. `cube`, `square`, `polygon`, and `linear_extrude` do not.
  `cube(_fn=100)` raises `TypeError` at run time. `set_global_fn` writes a
  global `$fn` statement and breaks rule 2.
- **`_fn` is an `int`, never `None`.** solidpython2 declares `_fn: int = None`,
  and ty reads the `int` half. A builder that declares `fn: int | None` and
  forwards it fails the type check. Keep `fn: int` everywhere.
- **Five calls are unchecked.** The convenience wrappers `cube`, `square`,
  `translate`, `rotate`, and `mirror` are declared `*args, **kwargs`, so ty
  cannot see their keywords. A `cube(_fn=...)` mistake reaches Python and
  raises `TypeError` in the generator. The render gate still catches it, because
  the generator stops before OpenSCAD starts.
- **Number format.** `solidpython2` writes `[1.0, 2.5]` where SCAD had
  `[1, 2.5]`, and `1e-05` where SCAD had `0.00001`. OpenSCAD reads both. Do not
  "tidy" a value.
- **`norm`.** OpenSCAD's `norm` is `sqrt(x*x + y*y + z*z)`. Use
  `math.sqrt(dx*dx + dy*dy)`, not `math.hypot`, so the last bit matches.
- **`rounded_cube` corner order.** Keep the three nested loops, in the order
  x, y, z, and keep the `if` that picks a sphere or a cylinder. The SCAD
  multi-range `for` trap goes away in Python, but the corner order still sets
  the hull.
- **`rounded_cube` keeps `apply_to`.** Keep the seven face names and the three
  axis names, and keep the guard.
- **`hose_clip` defaults differ from `params.py`.** `t_outer = 3`,
  `w_gap = 3`, `t_inner = 1.5` against `default_w_gap() = 2` and
  `default_t_inner() = 2`. The models pass their own values in. Do not unify.
- **`hose_clip_keepout` keeps its unused parameters.** A part and its keep-out
  volume take one argument list, so the pair cannot drift apart.
- **`offset` is millimetres along +x.** `offset = 0` is the old
  `alignment = "outer"`. Keep the sign comment with the variable.
- **`models/all.py` imports the parts.** Importing a model module must not build
  anything. That is why the entry point is a function.
- **`text()` in the coupons** needs `font="Liberation Sans"`, `halign="right"`,
  and `valign="center"`, as now.
- **The `fn` canary.** `docs/CONVENTIONS.md` calls a dropped `fn` a 2.04% volume
  error. In Python a dropped `_fn` shows up as a moved triangle count instead.
- **The first line of a model file** is no longer a `// Config:` comment. It is
  a docstring. `png_check.py` no longer reads it.

## 11. Out of scope

- Do not annotate `tools/render.py`, `tools/verify.py`, `tools/png_check.py`,
  `tools/stl_metrics.py`, or `tools/trim_png.py`. They pass `ty` today. A
  separate job can annotate them.
- Do not change any camera, any tolerance, or any image check.
- Do not add a test framework.
- Do not change the parts. If a wall thickness looks wrong, report it.
- Do not run `ruff format` over `tools/`. This job is a port, not a reformat.
  Lint and format the files you write, and leave the rest as they are.

## 12. Open points

These defaults are in force unless the user says otherwise.

1. `make watch` writes to `build/watch/`, not to `docs/images/`.
2. `EXPECTED_REGIONS` replaces the `// Config:` comment.
3. A change in `constants/` re-renders all models, the same as `lib/`.
4. A change to a part does **not** refresh `all.png`, by the user's rule. Only a
   change to `all.py`, to `lib/`, or to `constants/` does.
5. `make verify` goes away.
6. ty checks the calls it can see. The five `*args, **kwargs` wrappers are not
   checked. A mistake there stops the generator with a Python `TypeError`, and
   `tools/render.py` reports it.

## 13. Definition of done

- Every `.scad` source is deleted. Python is the only source.
- `make check-baseline` passes with the numbers in section 9.
- `make all` passes, and all four plate images are byte-identical to the
  committed ones.
- `make typecheck` passes.
- `make lint` passes, and only the files this job writes are formatted.
- `make watch` re-renders one model on a model change and all models on a `lib/`
  change.
- The model list comes from `models/*.py` in every tool. No list is written by
  hand.
- `README.md` and `docs/CONVENTIONS.md` describe the Python sources, and the
  leftover OpenSCAD words are gone.

## Appendix A: commands

The sandbox cannot start OpenSCAD: the Qt build reports "Incompatible processor
... neon". The sandbox also blocks the `uv` cache. Run these commands with
escalation, or on the real machine.

```sh
make verify IMG_DIR=build/verify-images      # the green state, before any change
make check-baseline                         # the green state, after each step
uv run ty check
make all
make watch
```

The union measurement, which needs four small probe files:

```sh
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD --backend=manifold \
  --render=true -o /tmp/a.stl /tmp/a_implicit.scad
uv run tools/stl_metrics.py /tmp/a.stl /tmp/b_explicit.stl
```

`a_implicit.scad` holds a module with two statements in the body.
`b_explicit.scad` holds the same two statements inside `union()`. Both give 340
triangles and 1114.262 mm3. A bare `cube` and a `union()` around one `cube`
both give 12 triangles and 1000.0 mm3.

The library measurements:

```sh
uv run --with solidpython2 --no-project python -c '
from solid2 import *
print(scad_render(cube(1) + cylinder(r=0.5, h=1, center=True)))
print(scad_render(cylinder(d=10, h=5, center=True, _fn=36)))
print(scad_render(hull()([sphere(r=1), translate([3, 0, 0])(sphere(r=1))])))
'
```

The first call writes a `union()` of the two solids, and a chain such as
`a + b - c` writes a `difference()` that holds that `union()` in order. The
second call writes `cylinder($fn = 36, center = true, d = 10, h = 5)`.
The third call shows that `hull()` and `union()` take one list of children, so a
Python loop can build the list and no call site needs to spread one.

The `hull()` measurement, which is the trap of this job:

```sh
for f in rounded_scad p8_explicit p8_for_group q_union_group q_module_group; do
  OpenSCAD --backend=manifold --render=true -o /tmp/$f.stl /tmp/$f.scad
done
uv run tools/stl_metrics.py /tmp/rounded_scad.stl /tmp/p8_explicit.stl \
  /tmp/p8_for_group.stl /tmp/q_union_group.stl /tmp/q_module_group.stl
```

All five solids are a `[10, 12, 14]` box with radius 1.5 at `fn=100`, centred,
with every corner rounded. The results:

`rounded_scad.scad` is `include <shapes.scad>` plus one
`rounded_cube(size = [10, 12, 14], radius = 1.5, center = true, apply_to =
"all", fn = 100);`. `p8_explicit.scad` writes the eight `translate` calls out
by hand. `p8_for_group.scad` reaches them through a `for` loop.
`q_union_group.scad` wraps them in `union()`. `q_module_group.scad` wraps them
in a module call.

| File | Shape of the `hull()` input | Triangles | Volume mm3 |
| --- | --- | --- | --- |
| `rounded_scad` | the SCAD `rounded_cube` | 10532 | 1614.41 |
| `p8_explicit` | eight children, `$fn` as an argument | 10510 | 1614.41 |
| `p8_fn_statement` | eight children, `$fn` as a statement | 10510 | 1614.41 |
| `p8_for_group` | one `for` group | 10532 | 1614.41 |
| `q_union_group` | one `union()` | 10532 | 1614.41 |
| `q_module_group` | one module call | 10532 | 1614.41 |

The volume is identical in every row. Only the triangle count moves, and it
moves with the number of children `hull()` sees. `$fn` as an argument and `$fn`
as a statement give the same result.

The nested-difference measurement: a `difference()` whose first child is another
`difference()` gives 424 triangles and 704.193 mm3, the same as one `difference()`
with three children. Nesting differences is safe.

The rounded-cube round trip. The port in appendix B, driven from a probe model:

| Case | SCAD original | Python port |
| --- | --- | --- |
| `apply_to="all"` | 10532 triangles, 1614.41 mm3 | 10532 triangles, 1614.41 mm3 |
| `apply_to="z"` | 434 triangles, 1652.895 mm3 | 434 triangles, 1652.895 mm3 |

Both cases have zero open edges. The port needs `hull()(union()(children))`.
With `hull()(children)` it gives 10510 triangles, and the baseline check fails.

The type check ran in the probe project. `uv run ty check` reports no error on
the ported `rounded_cube` and on the model that calls it.

The same run found three facts about solidpython2:

- A call with a real value passes: `cylinder(h=1, r=0.5, center=True,
  _fn=100)`.
- `_fn=None` is refused with `invalid-argument-type`, because the parameter is
  declared `int`.
- `cube(size=1, _fn=36)` is not refused. `cube`, `square`, `translate`,
  `rotate`, and `mirror` are convenience wrappers declared `*args, **kwargs`.
  At run time that call raises `TypeError: cube.__init__() got an unexpected
  keyword argument '_fn'`.

An earlier attempt put a hand-written signature layer in front of solidpython2.
It produced 12 errors of its own, because hand-written `int | None` parameters
do not match solidpython2's `int` parameters. Do not build that layer.

## Appendix B: the shape of a ported module

This is the ported `rounded_cube`. It ran in the probe, it type-checked, and its
mesh matched the SCAD original on both branches. Use the same shape for the
rest of the port.

The block below was taken out of this document, kept in the probe project, and
run: `uv run ty check` passed, and the render gave 10532 triangles, 1614.41 mm3,
and no open edges, against the SCAD original's 10532 and 1614.41.

```python
from __future__ import annotations

from typing import Sequence

from solid2 import (
    OpenSCADObjectPlus,
    cylinder,
    hull,
    rotate,
    sphere,
    translate,
    union,
)

DEFAULT_FN: int = 100


def rounded_cube(
    size: float | Sequence[float],
    radius: float = 0.5,
    center: bool = False,
    apply_to: str = "all",
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Solid box with selected edges rounded; upstream `roundedcube` semantics."""
    s = [size, size, size] if isinstance(size, (int, float)) else list(size)
    lo = [radius, radius, radius]
    hi = [s[0] - radius, s[1] - radius, s[2] - radius]
    diameter = 2 * radius
    axis_rotate = (
        [0, 90, 0]
        if apply_to in ("xmin", "xmax", "x")
        else [90, 90, 0]
        if apply_to in ("ymin", "ymax", "y")
        else [0, 0, 0]
    )

    children: list[OpenSCADObjectPlus] = []
    for xi in (0, 1):
        for yi in (0, 1):
            for zi in (0, 1):
                point = _corner_point(lo, hi, xi, yi, zi)
                if _corner_is_rounded(xi, yi, zi, apply_to):
                    children.append(translate(point)(sphere(r=radius, _fn=fn)))
                else:
                    children.append(
                        translate(point)(
                            rotate(axis_rotate)(
                                cylinder(h=diameter, r=radius, center=True, _fn=fn)
                            )
                        )
                    )

    offset = [-s[0] / 2, -s[1] / 2, -s[2] / 2] if center else [0, 0, 0]
    return translate(offset)(hull()(union()(children)))
```

`_corner_point` and `_corner_is_rounded` are the same as the two SCAD
functions, with `assert` guards replaced by `raise ValueError`.

Four lines here are not free choices:

- `hull()(union()(children))`, not `hull()(children)`. Section 10 explains why.
- `_fn=fn` on the sphere and on the cylinder, and nothing on a cube.
- `fn: int`, never `int | None`.
- `OpenSCADObjectPlus` as the return type, imported from `solid2`.
