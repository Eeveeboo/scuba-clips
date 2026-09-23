#!/usr/bin/env bash
#
# render.sh — the single render entry point for the scuba-clips build.
#
#   tools/render.sh <model.scad> <outdir> [--stl|--png|--both] [--draft]
#                   [--name NAME] [--camera X,Y,Z,RX,RY,RZ] [--log FILE] [--quiet]
#   tools/render.sh --check          # is the OpenSCAD binary usable?
#   tools/render.sh --print-version  # the version string, e.g. 2026.09.12
#
# Writes <outdir>/<name>.stl and/or <outdir>/<name>.png, where <name> defaults
# to the model file name without its extension.  A PNG is trimmed to the
# geometry plus a 45 px margin, because --viewall fits the bounding sphere and
# leaves a wide part floating in background.  The full OpenSCAD output goes to
# build/logs/<name>.log (build/logs/<name>.draft.log in draft mode).
#
# Exit status is not zero when OpenSCAD is missing or too old, when the render
# reports WARNING or ERROR, when the render summary does not say
# "Status: NoError", or when png_check.py rejects the screenshot.
#
# Manifold backend and --render=true are always used: the legacy CGAL backend
# needs minutes for these models instead of about a second.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LOG_DIR=${LOG_DIR:-$ROOT/build/logs}
METRICS="$ROOT/tools/stl_metrics.py"
PNG_CHECK="$ROOT/tools/png_check.py"
TRIM_PNG="$ROOT/tools/trim_png.py"

# The camera angle per model, chosen so that the part's own structure reads, and
# then trimmed to the margin below.  The ink fraction of the shipped plate is in
# brackets.  --camera overrides the table.
#
# 65,0, 0 : three-quarter view from above, no spin.  The combo plate's two C clip
#           bores read as enclosed holes only at no spin (33 enclosed background
#           cells against 0 at 45/30), which is the feature that identifies that
#           part [0.51].
# 30,0, 0 : hero plate.  The print plate is a 2x2 layout, and two of the four
#           parts hide behind the others when the view tilts too far.  Measured
#           at azimuth 0: elevation 0..35 shows 4 separate silhouettes, 36 and
#           above shows 3 (65, the previous hero, shows 2).  30 keeps 6 degrees
#           of margin below the flip and still fills the plate [0.35].
# 60,0, 0 : the lower clip is two mirrored clips; from here the two read as
#           separate arms (silhouette fill 0.69) instead of the diagonal overlap
#           of 55/0/25 (fill 0.47) [0.41].
# 45,30,0 : the isometric of the contract.  The upper clip is near-cubic, and
#           65/0 flattens it into a block (silhouette fill 0.91 against 0.59
#           here) [0.40].
# 55,0,25 : OpenSCAD's own default view.  The webbing clip's two standoffs and
#           its slot stay visible against the background (fill 0.59); 60/0
#           flattens it (fill 0.92) [0.40].
CAMERA_DEFAULT="0,0,0,45,30,0,0"
camera_for() {
  case "$1" in
    inflator_spg_combo_clip)   echo "0,0,0,65,0,0,0" ;;
    lower_octi_retaining_clip) echo "0,0,0,60,0,0,0" ;;
    upper_octi_retaining_clip) echo "0,0,0,45,30,0,0" ;;
    webbing_side_clip)         echo "0,0,0,55,0,25,0" ;;
    all)                       echo "0,0,0,30,0,0,0" ;;
    *)                         echo "$CAMERA_DEFAULT" ;;
  esac
}

die() { printf 'render.sh: %s\n' "$1" >&2; exit 2; }

usage() {
  cat <<'EOF'
usage: render.sh <model.scad> <outdir> [--stl|--png|--both] [--draft]
                  [--name NAME] [--camera X,Y,Z,RX,RY,RZ] [--log FILE] [--quiet]
       render.sh --check

Writes <outdir>/<name>.stl and/or <outdir>/<name>.png.  <name> defaults to the
model file name without its extension.  The full OpenSCAD output goes to
build/logs/<name>.log (build/logs/<name>.draft.log in draft mode).  --draft
renders at MODEL_FN=36 instead of 100.  Exit status is not zero when OpenSCAD
is missing or older than 2024, when the render reports WARNING or ERROR, when
the render summary does not say "Status: NoError", or when png_check.py
rejects the screenshot.
EOF
}

find_openscad() {
  if [ -n "${OPENSCAD:-}" ]; then
    printf '%s\n' "$OPENSCAD"
  elif [ -x /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD ]; then
    printf '%s\n' /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
  elif command -v openscad >/dev/null 2>&1; then
    command -v openscad
  fi
}

# Print the usable binary path, or stop with a reason.
check_binary() {
  local bin raw year
  bin=$(find_openscad)
  [ -n "$bin" ] || die "no OpenSCAD binary found. Install OpenSCAD, or set OPENSCAD=/path/to/OpenSCAD."
  [ -x "$bin" ] || die "OPENSCAD=$bin is not executable."
  raw=$("$bin" --version 2>&1 | head -n 1)
  year=$(printf '%s\n' "$raw" | sed -nE 's/.*([0-9]{4})\.[0-9]{2}.*/\1/p')
  [ -n "$year" ] || die "cannot read a version from '$bin --version' (got: $raw)."
  if [ "$year" -lt 2024 ]; then
    die "$bin reports '$raw'. This harness needs OpenSCAD 2024 or newer: the legacy CGAL backend takes minutes on these models, the manifold backend about a second. Install a current build, or set OPENSCAD= to a current one."
  fi
  printf '%s\n' "$bin"
}

MODEL=""
OUTDIR=""
KIND="both"
DRAFT=0
NAME=""
CAMERA=""
COMPONENTS=""
LOG=""
QUIET=0

while [ $# -gt 0 ]; do
  case "$1" in
    --check) BIN=$(check_binary); echo "render.sh: OpenSCAD ok: $BIN ($("$BIN" --version 2>&1 | head -n1))"; exit 0 ;;
    --print-version) BIN=$(check_binary); "$BIN" --version 2>&1 | head -n 1 | sed -nE 's/.*([0-9]{4}\.[0-9]{2}(\.[0-9]+)?).*/\1/p'; exit 0 ;;
    --stl|--png|--both) KIND="${1#--}" ;;
    --draft) DRAFT=1 ;;
    --quiet) QUIET=1 ;;
    --name) shift; [ $# -gt 0 ] || die "--name needs a value"; NAME="$1" ;;
    --camera) shift; [ $# -gt 0 ] || die "--camera needs a value"; CAMERA="$1" ;;
    --components) shift; [ $# -gt 0 ] || die "--components needs a value"; COMPONENTS="$1" ;;
    --log) shift; [ $# -gt 0 ] || die "--log needs a value"; LOG="$1" ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option '$1' (try --help)" ;;
    *) if [ -z "$MODEL" ]; then MODEL="$1"
       elif [ -z "$OUTDIR" ]; then OUTDIR="$1"
       else die "unexpected argument '$1'"; fi ;;
  esac
  shift
done

[ -n "$MODEL" ] || die "no model given (try --help)"
[ -f "$MODEL" ] || die "no such model file: $MODEL"
[ -n "$OUTDIR" ] || die "no output directory given (try --help)"
[ -n "$NAME" ] || NAME=$(basename "$MODEL" .scad)
[ -n "$CAMERA" ] || CAMERA=$(camera_for "$NAME")
# The overview plate must show all four parts as separate silhouettes; a lower
# elevation stacks them into fewer blobs and hides parts behind each other.
[ -n "$COMPONENTS" ] || [ "$NAME" != "all" ] || COMPONENTS=4

FN=100
[ "$DRAFT" -eq 0 ] || FN=36
# 45 px keeps the ink clear of png_check's outermost downsample rows (650/30 = 22 px
# per row), so the border_fill test keeps reading 0.00.
MARGIN=45

BIN=$(check_binary)
mkdir -p "$OUTDIR" "$LOG_DIR"
[ -n "$LOG" ] || { if [ "$DRAFT" -eq 0 ]; then LOG="$LOG_DIR/$NAME.log"; else LOG="$LOG_DIR/$NAME.draft.log"; fi; }
: >"$LOG"
echo "render.sh: $MODEL -> $OUTDIR/$NAME.{stl,png} [$KIND] fn=$FN camera=$CAMERA" >&2

log_failure() {
  echo "render.sh: $1" >&2
  if [ "$QUIET" -eq 1 ]; then
    grep -nE 'WARNING|ERROR' "$LOG" | head -n 10 >&2 || true
  else
    echo "  full OpenSCAD output: $LOG" >&2
  fi
}

# A render is good only when OpenSCAD says so and nothing warned.
check_render_log() {
  if grep -qE 'WARNING|ERROR' "$LOG"; then
    log_failure "OpenSCAD reported warnings or errors while rendering $MODEL (log: $LOG)"
    return 1
  fi
  if ! grep -qE 'Status:[[:space:]]*NoError' "$LOG"; then
    log_failure "no 'Status: NoError' in the render summary for $MODEL — the top level object is not a manifold 3D object (log: $LOG)"
    return 1
  fi
  return 0
}

FAILED=0
STATUS=0

# Render into build/tmp and publish with a rename: a reader never sees a
# half-written STL or plate, and a plate appears only after it has passed
# png_check.  Two people running `make verify` at the same time no longer trip
# over each other's partial files; the pid keeps the staging paths apart.
TMP_DIR="$ROOT/build/tmp"
mkdir -p "$TMP_DIR"
STAGE_STL="$TMP_DIR/$NAME.$$.stl"
STAGE_PNG="$TMP_DIR/$NAME.$$.png"

if [ "$KIND" = "stl" ] || [ "$KIND" = "both" ]; then
  set +e
  "$BIN" --backend=manifold --render=true -D MODEL_FN="$FN" -o "$STAGE_STL" "$MODEL" >>"$LOG" 2>&1
  STATUS=$?
  set -e
  [ "$QUIET" -eq 1 ] || cat "$LOG" >&2
  if [ "$STATUS" -ne 0 ]; then
    log_failure "OpenSCAD exit status $STATUS while writing $OUTDIR/$NAME.stl (log: $LOG)"
    FAILED=1
  elif ! check_render_log; then
    FAILED=1
  else
    mv -f "$STAGE_STL" "$OUTDIR/$NAME.stl"
    python3 "$METRICS" "$OUTDIR/$NAME.stl" || FAILED=1
  fi
fi

if [ "$KIND" = "png" ] || [ "$KIND" = "both" ]; then
  : >"$LOG"
  set +e
  "$BIN" --backend=manifold --render=true -D MODEL_FN="$FN" \
    --autocenter --viewall --imgsize=900,650 --projection=o \
    --colorscheme=Tomorrow --camera="$CAMERA" \
    -o "$STAGE_PNG" "$MODEL" >>"$LOG" 2>&1
  STATUS=$?
  set -e
  [ "$QUIET" -eq 1 ] || cat "$LOG" >&2
  if [ "$STATUS" -ne 0 ]; then
    log_failure "OpenSCAD exit status $STATUS while writing $OUTDIR/$NAME.png (log: $LOG)"
    FAILED=1
  elif ! check_render_log; then
    FAILED=1
  else
    # --viewall fits the model's bounding sphere, so a wide part leaves most of
    # the frame as background.  Trim to the ink with a margin that stays clear
    # of png_check's frame-edge test, then check the plate before it ships.
    python3 "$TRIM_PNG" "$STAGE_PNG" --margin "$MARGIN" || FAILED=1
    CHECK_ARGS=(--quiet "$STAGE_PNG")
    [ "$QUIET" -eq 1 ] || CHECK_ARGS=("$STAGE_PNG")
    [ -z "$COMPONENTS" ] || CHECK_ARGS+=(--components "$COMPONENTS")
    if python3 "$PNG_CHECK" "${CHECK_ARGS[@]}"; then
      mv -f "$STAGE_PNG" "$OUTDIR/$NAME.png"
    else
      FAILED=1
    fi
  fi
fi

exit "$FAILED"
