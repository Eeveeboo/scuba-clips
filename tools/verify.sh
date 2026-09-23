#!/usr/bin/env bash
#
# verify.sh — build every model at MODEL_FN=100 and compare it against the
# frozen baseline in tools/baseline/.
#
#   tools/verify.sh
#
# Prints a pass/fail table with the relative volume error and the bounding box
# delta, and exits non-zero on any of these failures:
#   * a model or a screenshot is missing,
#   * OpenSCAD reports WARNING or ERROR, or does not report "Status: NoError",
#   * the DEFAULT_FN canary appears: 'WARNING: Ignoring unknown variable "DEFAULT_FN"'
#     (a library default expression fell back to OpenSCAD's own tessellation),
#   * volume differs from the baseline by more than 0.05% relative,
#   * the bounding box differs from the baseline by more than 0.01 mm,
#   * the triangle count differs from the baseline.  Exact when the running
#     OpenSCAD is the build that made the baseline (tools/baseline/*.json records
#     it): inside one toolchain the count is a deterministic function of the
#     model.  Inside a 0.5% band, with a note, when the toolchain differs, since
#     manifold's triangulation can move between nightlies while the solid does
#     not.  A dropped $fn moves this model from 15046 to 1646 either way,
#   * the mesh has open edges (a torn surface; the STL would slice badly),
#   * a baseline exists with no matching model.
#
# The paths are overridable by environment, which the Makefile uses and which
# lets the harness be proven against a sandbox copy of the old geometry:
#   MODELS_DIR BASELINE_DIR STL_DIR IMG_DIR WORK
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MODELS_DIR=${MODELS_DIR:-$ROOT/models}
BASELINE_DIR=${BASELINE_DIR:-$ROOT/tools/baseline}
STL_DIR=${STL_DIR:-$ROOT/build/stl}
IMG_DIR=${IMG_DIR:-$ROOT/docs/images}
# Each run gets its own scratch directory: two runs of `make verify` at the same
# time (which happens on a team) otherwise interleave status.tsv and the metric
# files, and one run then reads the other's half-finished list of models.
WORK="${WORK:-$ROOT/build/verify}.$$"
LOG_DIR="$WORK/logs"
RENDER="$ROOT/tools/render.sh"
OSCAD_VERSION=$("$RENDER" --print-version)

mkdir -p "$WORK/metrics" "$LOG_DIR"
trap 'rm -rf "$WORK"' EXIT
export LOG_DIR
METRICS="$ROOT/tools/stl_metrics.py"
PNG_CHECK="$ROOT/tools/png_check.py"

mkdir -p "$STL_DIR" "$IMG_DIR"

models=()
for f in "$MODELS_DIR"/*.scad; do
  [ -e "$f" ] || continue
  models+=("$(basename "$f" .scad)")
done
if [ "${#models[@]}" -eq 0 ]; then
  echo "verify.sh: no models found in $MODELS_DIR" >&2
  exit 1
fi

printf 'verify.sh: %d models from %s\n' "${#models[@]}" "$MODELS_DIR"
: >"$WORK/status.tsv"

for m in "${models[@]}"; do
  stl_status=FAIL
  png_status=FAIL
  canary=ok

  if "$RENDER" "$MODELS_DIR/$m.scad" "$STL_DIR" --stl --quiet; then stl_status=ok; fi
  grep -q 'Ignoring unknown variable' "$LOG_DIR/$m.log" 2>/dev/null && canary=FAIL

  if [ -f "$STL_DIR/$m.stl" ]; then
    python3 "$METRICS" "$STL_DIR/$m.stl" >"$WORK/metrics/$m.json" || stl_status=FAIL
  else
    stl_status=FAIL
  fi

  if "$RENDER" "$MODELS_DIR/$m.scad" "$IMG_DIR" --png --quiet; then png_status=ok; fi
  grep -q 'Ignoring unknown variable' "$LOG_DIR/$m.log" 2>/dev/null && canary=FAIL

  printf '%s\t%s\t%s\t%s\n' "$m" "$stl_status" "$png_status" "$canary" >>"$WORK/status.tsv"
done

python3 - "$WORK" "$BASELINE_DIR" "$OSCAD_VERSION" <<'PY'
import json
import os
import sys

work, baseline_dir, oscad_version = sys.argv[1], sys.argv[2], sys.argv[3]
VOL_TOL_PCT = 0.05      # relative
BBOX_TOL_MM = 0.01
TRI_TOL_PCT = 0.5       # band for a toolchain other than the baseline's; a real
                        # tessellation regression moves the count by far more
                        # (a dropped $fn moves this model from 15046 to 1646)
FIELDS = ("bbox_min", "bbox_max")

status = {}
with open(os.path.join(work, "status.tsv")) as fh:
    for line in fh:
        name, stl, png, canary = line.split()
        status[name] = {"stl": stl, "png": png, "canary": canary}

baselines = {}
for fn in sorted(os.listdir(baseline_dir)):
    if fn.endswith(".json"):
        with open(os.path.join(baseline_dir, fn)) as fh:
            baselines[fn[: -len(".json")]] = json.load(fh)


def new_metrics(name):
    path = os.path.join(work, "metrics", name + ".json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def num(value):
    return float(value) if isinstance(value, (int, float)) else 0.0


def cell(value, width, places):
    return "-".rjust(width) if value is None else f"{value:>{width}.{places}f}"


rows = []
notes = []
other_toolchain = set()
for name in list(status) + [n for n in sorted(baselines) if n not in status]:
    base = baselines.get(name)
    new = new_metrics(name)
    st = status.get(name, {"stl": "MISSING", "png": "MISSING", "canary": "MISSING"})
    reasons = []

    if name not in status:
        reasons.append("model missing (baseline exists)")
    if st["stl"] != "ok":
        reasons.append("render failed (see build/logs/%s.log)" % name)
    if st["png"] != "ok":
        reasons.append("screenshot failed")
    if st["canary"] != "ok":
        reasons.append('DEFAULT_FN canary: WARNING: Ignoring unknown variable "DEFAULT_FN"')

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
        same_toolchain = bool(base_version) and base_version == oscad_version
        if not same_toolchain:
            other_toolchain.add(name)
        if t_base != t_new:
            tri_pct = abs(t_new - t_base) / t_base * 100.0 if t_base else 100.0
            if same_toolchain:
                reasons.append(f"triangles {t_new} against baseline {t_base}: this OpenSCAD "
                               f"({oscad_version}) produced the baseline, so the count is exact")
            elif tri_pct > TRI_TOL_PCT:
                reasons.append(f"triangles {t_new} against baseline {t_base} ({tri_pct:.2f}%)")
            else:
                notes.append(
                    f"{name}: toolchain differs from the baseline (this OpenSCAD "
                    f"{oscad_version or 'unknown'}, baseline {base_version or 'not recorded'}): "
                    f"triangles {t_new} against {t_base}, {tri_pct:.2f}% inside the {TRI_TOL_PCT}% band.")
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

print(f"OpenSCAD {oscad_version or 'unknown'}; baselines recorded under "
      f"{', '.join(sorted({b.get('openscad_version') or 'an unrecorded build' for b in baselines.values()}))}")
header = (f"{'model':26s} {'volume base':>11s} {'volume new':>11s} {'err %':>8s} "
          f"{'bbox mm':>8s} {'tris base':>9s} {'tris new':>9s} {'open':>4s} "
          f"{'stl':>4s} {'png':>4s} {'fn':>4s}  result")
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
          f"{st['stl']:>4s} {st['png']:>4s} {st['canary']:>4s}  "
          f"{'FAIL' if broken else 'PASS'}")

print()
for note in notes:
    print("note: " + note)
if notes:
    print()
if failures:
    print(f"verify.sh: {failures} of {len(rows)} models FAILED")
    for (name, _vb, _vn, _e, _b, _tb, _tn, _o, _st, reasons) in rows:
        if reasons and reasons != ["no baseline (not compared)"]:
            print(f"  {name}: " + "; ".join(reasons))
    sys.exit(1)

toolchain_note = ("triangles exact: the running OpenSCAD matches the baseline toolchain"
                  if not other_toolchain else
                  f"triangles exact where the toolchain matches, within {TRI_TOL_PCT}% elsewhere "
                  f"({len(other_toolchain)} model(s) under another toolchain)")
print(f"verify.sh: all {len(rows)} models PASS (volume within {VOL_TOL_PCT}%, "
      f"bbox within {BBOX_TOL_MM} mm, {toolchain_note}, no open edges)")
PY
result=$?

if [ "$result" -ne 0 ]; then
  while IFS=$'\t' read -r name stl png canary; do
    [ "$png" = "ok" ] || python3 "$PNG_CHECK" "$IMG_DIR/$name.png" || true
  done <"$WORK/status.tsv"
fi

exit "$result"
