# scuba-clips

Parametric scuba hose clips, built from Python with `solidpython2`: an
inflator/SPG combo clip, an upper octopus retaining clip for shoulder webbing,
and a webbing side clip with two standoffs.

![All three parts](docs/images/all.png)

| Combo | Upper octopus | Webbing side |
| --- | --- | --- |
| ![combo](docs/images/inflator_spg_combo_clip.png) | ![upper](docs/images/upper_octi_retaining_clip.png) | ![webbing](docs/images/webbing_side_clip.png) |

## Use the nightly build, with the manifold solver

Use a **nightly** OpenSCAD and always pass `--backend=manifold`. The 2021.01
release has no `--backend` option, so it cannot use manifold, and the legacy CGAL
solver is painfully slow: on the same part, manifold renders the upper clip in
**1.0 s** where CGAL takes **3 min 04 s**. `make` refuses pre-2024 builds.

## Build

The build is Python. `solidpython2` writes the OpenSCAD source, and OpenSCAD
renders it with the manifold solver. `uv` builds the environment from
`pyproject.toml` and `uv.lock`; a new machine needs `uv` and OpenSCAD only.

```sh
uv sync              # once: the build environment into .venv
make                 # list targets
make all             # STL + screenshot per model (stl + png)
make stl             # STLs only
make png             # screenshots only, into docs/images/
make scad            # generated OpenSCAD source into build/scad/
make watch           # re-render on a source change, into build/watch/
make one MODEL=x     # one model, STL and screenshot
make preview         # fast draft build at fn=36, into build/draft/
make typecheck       # uv run ty check
make lint            # uv run ruff check
make format          # uv run ruff format
make check-baseline  # compare volume, bbox and mesh against tools/baseline/
make save-baseline   # render all and write tools/baseline/
make clean
```

Render one model directly, or with another binary:

```sh
uv run tools/render.py models/upper_octi_retaining_clip.py build/stl
uv run tools/render.py models/upper_octi_retaining_clip.py build/stl --stl --draft
make OPENSCAD=/path/to/OpenSCAD stl
```

## Layout

`constants/hardware.py` your hoses and your webbing — the first thing to tune
· `models/` one part per file: its builder, its tuning variables, and its plate
expectation, `all.py` the full plate · `lib/` reusable geometry builders, rarely
edited · `dev/print_tests.py` fit coupons, print these first ·
`docs/CONVENTIONS.md` conventions · `tools/` the build and regression harness.

## How a model is built

Each `models/<name>.py` defines `<name>(fn: int = MODEL_FN)`. The builder takes
`fn` and passes it to every primitive that tessellates, so a draft render at
`fn=36` is fast and a full render uses `MODEL_FN = 100`. Each model states its
plate expectation as `EXPECTED_REGIONS`. Importing a model builds nothing; only
a call to the builder makes geometry.

## Tuning

First set your kit. `constants/hardware.py` holds each hose diameter as
`hose_*_dia` and each webbing size as `webbing_*_size` (`[width, thickness]`),
in plain assignments that every model reads.

Then tune a part in its own model file, in the variables at the top:

| Model | Knobs |
| --- | --- |
| `inflator_spg_combo_clip` | `t_inner`, `t_outer`, `w_gap`, `clip_h`, and the outer clips' placement (`hp_spg_*`, `lpi_*`) |
| `upper_octi_retaining_clip` | `clip_bottom_z`, `reg_clip_h`, `reg_clip_standoff`, `hose_clip_h`, `hose_clip_standoff`, `strap_block_h`, `webbing_slot_h`, the `slit_*` numbers, `offset` |
| `webbing_side_clip` | `wall_t`, `block_h`, `clip_h`, `gap`, `tube_d` |
| `all` | none — the print plate places the three parts, and each part reads its own knobs |

`lib/` holds the geometry builders and their fit defaults. Leave it alone
unless you are changing a builder itself. In `webbing_side_clip`, `wall_t`
drives the block wall and the walls of its `hose_clip_on_standoff` clips.
