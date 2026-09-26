#!/usr/bin/env python3
"""verify.py — build every model and compare it against the frozen baseline in
tools/baseline/.

  tools/verify.py            # render all, compare against the baselines
  tools/verify.py --save     # render all, write tools/baseline/<name>.json

The models come from every .py under models/, at any depth: a dev model such
as models/dev/print_tests.py is model dev/print_tests.  Each model module states
its plate expectation as EXPECTED_REGIONS.

Prints a pass/fail table with the relative volume error and the bounding box
delta, and exits non-zero on any of these failures:
  * a model or a screenshot is missing,
  * OpenSCAD reports WARNING or ERROR, or does not report "Status: NoError",
  * volume differs from the baseline by more than 0.05% relative,
  * the bounding box differs from the baseline by more than 0.01 mm,
  * the triangle count differs from the baseline.  Exact when the running
    OpenSCAD is the build that made the baseline (tools/baseline/*.json records
    it): inside one toolchain the count is a deterministic function of the
    model.  Inside a 0.5% band, with a note, when the toolchain differs, since
    manifold's triangulation can move between nightlies while the solid does
    not.  A dropped tessellation argument moves the octi clip from 15046 to 1646 either
    way,
  * the mesh has open edges (a torn surface; the STL would slice badly),
  * a baseline exists with no matching model.

--save writes one JSON per model, in the shape of the frozen baselines.  It
writes no baseline for a model whose render failed, so a broken tree cannot
freeze one, and the run still reports the failure.

The paths are overridable by environment, which lets the harness be pointed at a
scratch copy:
  MODELS_DIR BASELINE_DIR OUT_DIR
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import click
import png_check
import render
import stl_metrics

ROOT = Path(__file__).resolve().parent.parent
# The models are a package under the repo root: models/<name>.py.  The tool runs
# from tools/, so the root goes on the path for `import models.<name>`.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.config import CONFIG

VOL_TOL_PCT = 0.05      # relative
BBOX_TOL_MM = 0.01
TRI_TOL_PCT = 0.5       # band for a toolchain other than the baseline's; a real
                        # tessellation regression moves the count by far more
                        # (a dropped tessellation argument moves this model from 15046 to 1646)
FIELDS = ("bbox_min", "bbox_max")
# The tessellation the frozen baselines were recorded at: the harness renders
# every model at the value in `[library] tessellation_resolution`.
MODEL_TESSELLATION = CONFIG.library.tessellation_resolution
# png_check.py's own default frame, used for the ASCII preview of a bad plate.
PNG_COLS = 78
PNG_ROWS = 30


def path_from_env(name, default):
    """A path from the environment, defaulted and resolved against the repo root."""
    value = os.environ.get(name)
    if not value:
        return ROOT / default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def source_commit():
    """The short HEAD hash a baseline is captured from, or 'unknown'."""
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def save_baselines(metrics, baseline_dir, status, out_dir):
    """Write one baseline JSON per model.  Returns the number of models that failed.

    A model whose render failed has no fresh metrics, so it gets no baseline: the
    file on disk stays as it was, and the run reports the failure.
    """
    baseline_dir.mkdir(parents=True, exist_ok=True)
    version = render.openscad_version()
    commit = source_commit()
    saved = 0
    failed = 0
    for name in sorted(metrics):
        if status[name]["stl"] != "ok" or "error" in metrics[name] or status[name]["png"] != "ok":
            print(f"verify.py: {name}: no baseline written, the render failed "
                  f"(see {out_dir}/{name}.log)", file=sys.stderr)
            failed += 1
            continue
        record = dict(metrics[name])
        record["file"] = f"{name}.stl"
        record.update({"tessellation": MODEL_TESSELLATION, "openscad_version": version, "source_commit": commit})
        path = baseline_dir / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"verify.py: saved {path}: {record['volume_mm3']} mm3, "
              f"{record['triangles']} triangles, {record['open_edges']} open edges")
        saved += 1
    print(f"verify.py: saved {saved} of {saved + failed} baselines to {baseline_dir}")
    return failed


def num(value):
    return float(value) if isinstance(value, (int, float)) else 0.0


def cell(value, width, places):
    return "-".rjust(width) if value is None else f"{value:>{width}.{places}f}"


def compare(status, metrics, baselines, version, out_dir):
    """Print the pass/fail table.  Returns the number of models that failed."""
    rows = []
    notes = []
    other_toolchain = set()
    for name in list(status) + [n for n in sorted(baselines) if n not in status]:
        base = baselines.get(name)
        new = metrics.get(name)
        st = status.get(name, {"stl": "MISSING", "png": "MISSING"})
        reasons = []

        if name not in status:
            reasons.append("model missing (baseline exists)")
        if st["stl"] != "ok":
            reasons.append(f"render failed (see {out_dir}/{name}.log)")
        if st["png"] != "ok":
            reasons.append("screenshot failed")

        v_base = v_new = e_pct = bbox_delta = t_base = t_new = o_new = None
        if base is not None and new is not None and "error" not in new:
            v_base = num(base.get("volume_mm3"))
            v_new = num(new.get("volume_mm3"))
            if v_base:
                e_pct = abs(v_new - v_base) / abs(v_base) * 100.0
                if e_pct > VOL_TOL_PCT:
                    reasons.append(f"volume error {e_pct:.4f}% > {VOL_TOL_PCT}%")
            bbox_delta = max(
                abs(num(new.get(f, [0, 0, 0])[i]) - num(base.get(f, [0, 0, 0])[i]))
                for f in FIELDS for i in range(3)
            )
            if bbox_delta > BBOX_TOL_MM:
                reasons.append(f"bbox delta {bbox_delta:.4f} mm > {BBOX_TOL_MM} mm")
            t_base = base.get("triangles")
            t_new = new.get("triangles")
            o_new = new.get("open_edges")
            if o_new != 0:
                reasons.append(f"{o_new} open edges: the mesh is torn and would slice badly")
            if base.get("open_edges") is not None and o_new != base["open_edges"]:
                reasons.append(f"open edges {o_new} against baseline {base['open_edges']}")
            base_version = base.get("openscad_version")
            same_toolchain = bool(base_version) and base_version == version
            if not same_toolchain:
                other_toolchain.add(name)
            if t_base != t_new:
                tri_pct = abs(t_new - t_base) / t_base * 100.0 if t_base else 100.0
                if same_toolchain:
                    reasons.append(f"triangles {t_new} against baseline {t_base}: this OpenSCAD "
                                   f"({version}) produced the baseline, so the count is exact")
                elif tri_pct > TRI_TOL_PCT:
                    reasons.append(f"triangles {t_new} against baseline {t_base} ({tri_pct:.2f}%)")
                else:
                    notes.append(
                        f"{name}: toolchain differs from the baseline (this OpenSCAD "
                        f"{version or 'unknown'}, baseline {base_version or 'not recorded'}): "
                        f"triangles {t_new} against {t_base}, {tri_pct:.2f}% inside the "
                        f"{TRI_TOL_PCT}% band.")
        elif new is not None and "open_edges" in new and new["open_edges"] != 0:
            o_new = new["open_edges"]
            reasons.append(f"{o_new} open edges: the mesh is torn and would slice badly")
        elif new is not None and "error" in new:
            reasons.append("metrics unreadable: " + str(new["error"]))
        elif base is not None:
            reasons.append("no metrics (no STL)")

        if base is None and not reasons:
            reasons = ["no baseline (not compared)"]
        rows.append((name, v_base, v_new, e_pct, bbox_delta, t_base, t_new, o_new, st, reasons))

    print(f"OpenSCAD {version or 'unknown'}; baselines recorded under "
          f"{', '.join(sorted({b.get('openscad_version') or 'an unrecorded build' for b in baselines.values()}))}")
    header = (f"{'model':26s} {'volume base':>11s} {'volume new':>11s} {'err %':>8s} "
              f"{'bbox mm':>8s} {'tris base':>9s} {'tris new':>9s} {'open':>4s} "
              f"{'stl':>4s} {'png':>4s}  result")
    print()
    print(header)
    print("-" * len(header))
    failures = 0
    for (name, v_base, v_new, e_pct, bbox_delta, t_base, t_new, o_new, st, reasons) in rows:
        broken = [r for r in reasons if r != "no baseline (not compared)"]
        failures += 1 if broken else 0
        print(f"{name:26s} {cell(v_base, 11, 3)} {cell(v_new, 11, 3)} "
              f"{cell(e_pct, 8, 4)} {cell(bbox_delta, 8, 4)} "
              f"{'-' if t_base is None else str(t_base):>9s} "
              f"{'-' if t_new is None else str(t_new):>9s} "
              f"{'-' if o_new is None else str(o_new):>4s} "
              f"{st['stl']:>4s} {st['png']:>4s}  "
              f"{'FAIL' if broken else 'PASS'}")

    print()
    for note in notes:
        print("note: " + note)
    if notes:
        print()
    if failures:
        print(f"verify.py: {failures} of {len(rows)} models FAILED")
        for (name, _v_base, _v_new, _e_pct, _bbox, _t_base, _t_new, _o, _st, reasons) in rows:
            if reasons and reasons != ["no baseline (not compared)"]:
                print(f"  {name}: " + "; ".join(reasons))
    else:
        toolchain_note = ("triangles exact: the running OpenSCAD matches the baseline toolchain"
                          if not other_toolchain else
                          f"triangles exact where the toolchain matches, within {TRI_TOL_PCT}% "
                          f"elsewhere ({len(other_toolchain)} model(s) under another toolchain)")
        print(f"verify.py: all {len(rows)} models PASS (volume within {VOL_TOL_PCT}%, "
              f"bbox within {BBOX_TOL_MM} mm, {toolchain_note}, no open edges)")
    return failures


def expected_regions(name):
    """The region count a model asks for, from its own EXPECTED_REGIONS.

    Returns None when the module cannot be imported or names no count, so the
    caller checks nothing: a wrong count would make the plate check fire on a
    good render.
    """
    try:
        module = importlib.import_module(f"models.{name.replace('/', '.')}")
    except ImportError as exc:
        print(f"verify.py: cannot import models.{name.replace('/', '.')}: {exc}")
        return None
    want = getattr(module, "EXPECTED_REGIONS", None)
    if isinstance(want, bool) or not isinstance(want, int):
        print(f"verify.py: models.{name} states no integer EXPECTED_REGIONS "
              f"(got {want!r}); not checking the plate")
        return None
    return want


def show_failed_screenshots(status, out_dir):
    """Re-check each failed plate with the ASCII preview, to say what went wrong."""
    for name, state in status.items():
        if state["png"] == "ok":
            continue
        want = expected_regions(name)
        png_check.check(str(out_dir / f"{name}.png"), PNG_COLS, PNG_ROWS, False, want)


@click.command()
@click.option("--save", is_flag=True,
              help="Render all and write the baselines instead of comparing.")
def main(save):
    """Render every model and compare it against the frozen baselines.

    The models come from every .py under models/, and each is rendered at the `[library]
    tessellation_resolution` from lib/config.py through tools/render.py.  --save
    writes tools/baseline/*.json in place of the comparison.  A missing model, a
    failed render, a moved metric, a torn mesh, and a baseline with no matching
    model all fail the run.
    """
    models_dir = path_from_env("MODELS_DIR", "models")
    baseline_dir = path_from_env("BASELINE_DIR", "tools/baseline")
    out_dir = path_from_env("OUT_DIR", "build")

    version = render.openscad_version()
    out_dir.mkdir(parents=True, exist_ok=True)

    models = render.find_models(models_dir)
    if not models:
        print(f"verify.py: no models found in {models_dir}", file=sys.stderr)
        sys.exit(1)
    print(f"verify.py: {len(models)} models from {models_dir}", flush=True)

    status = {}
    metrics = {}
    for name in models:
        model = models_dir / f"{name}.py"
        # A nested name keeps its directory: dev/print_tests writes build/dev/.
        model_out = out_dir / Path(name).parent
        stem = Path(name).name
        # render.py publishes an STL only after its own checks and a plate only
        # after png_check, so drop the old files first: what is on disk when the
        # render returns is exactly what passed.
        for suffix in (".stl", ".png"):
            (out_dir / f"{name}{suffix}").unlink(missing_ok=True)
        render.render(model, model_out, name=stem, quiet=True,
                      log=model_out / f"{stem}.log")

        stl_status = "ok" if (out_dir / f"{name}.stl").is_file() else "FAIL"
        png_status = "ok" if (out_dir / f"{name}.png").is_file() else "FAIL"

        if stl_status == "ok":
            metrics[name] = stl_metrics.metrics(str(out_dir / f"{name}.stl"))
            if "error" in metrics[name]:
                stl_status = "FAIL"

        status[name] = {"stl": stl_status, "png": png_status}

    if save:
        failures = save_baselines(metrics, baseline_dir, status, out_dir)
    else:
        baselines = {path.relative_to(baseline_dir).with_suffix("").as_posix(): json.loads(path.read_text())
                     for path in sorted(baseline_dir.rglob("*.json"))}
        failures = compare(status, metrics, baselines, version, out_dir)

    if failures:
        if not save:
            show_failed_screenshots(status, out_dir)
        sys.exit(1)


if __name__ == "__main__":
    main()
