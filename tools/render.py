#!/usr/bin/env python3
"""render.py — the single render entry point for the scuba-clips build.

  tools/render.py <model.py> <outdir> [--stl|--png|--both|--scad] [--draft]
                  [--name NAME] [--camera X,Y,Z,RX,RY,RZ] [--components N]
                  [--log FILE] [--quiet]
  tools/render.py --check          # is the OpenSCAD binary usable?
  tools/render.py --print-version  # the version string, e.g. 2026.09.12

Imports models/<name>.py, calls its <name> builder with fn=36 (--draft) or
fn=100, and writes the generated source to build/scad/<name>.scad.  That file
is what OpenSCAD renders to <outdir>/<name>.stl and/or <outdir>/<name>.png,
where <name> defaults to the model file name without its extension.  --scad
writes the generated source only and starts no render.  A PNG is trimmed to
the geometry plus a 45 px margin, because --viewall fits the bounding sphere
and leaves a wide part floating in background.  The full OpenSCAD output goes
to build/logs/<name>.log (build/logs/<name>.draft.log in draft mode).

The plate's region count is checked against the model's own EXPECTED_REGIONS:
models/all.py says 3, each single part 1.  --components N overrides it.  A
mismatch is a WARNING, not a failure: a camera that merges two parts is worth
saying, but it is a judgement call.  The count used to be a hard-coded 3 here,
which meant a camera change could quietly stop showing a part while the render
still passed.

Exit status is not zero when the model raises while it is built, when OpenSCAD
is missing or too old, when the render reports WARNING or ERROR, when the
render summary does not say "Status: NoError", or when png_check.py rejects
the screenshot.

Manifold backend and --render=true are always used: the legacy CGAL backend
needs minutes for these models instead of about a second.
"""
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import png_check
import solid2
import stl_metrics
import trim_png

ROOT = Path(__file__).resolve().parent.parent

# The models are Python packages at the repo root.  tools/ is sys.path[0] when
# this file runs as a script, so put the repo root on sys.path before importing
# one.
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# The camera angle, chosen so that the part's own structure reads, and then
# trimmed to the margin below.  The ink fraction of the shipped plate is in
# brackets.  --camera overrides it.
#
# 65,0, 0 : three-quarter view from above, no spin.  The combo plate's two C clip
#           bores read as enclosed holes only at no spin (33 enclosed background
#           cells against 0 at 45/30), which is the feature that identifies that
#           part [0.51].
# 45,0, 0 : hero plate.  The print plate is L-shaped (three parts), and the
#           webbing clip sits 50 mm behind the combo clip while both are 50..60 mm
#           wide.  Measured: tilt 0..50 keeps three separate silhouettes, tilt 60
#           and above merges them into one blob.  45 keeps 5 degrees of margin
#           below the flip and still shows the parts in three-quarter view [0.09].
# 30,0,90 : the octi clip's bores run along Z, so a near-plan view looks down
#           them and shows them as holes; a three-quarter view hides them and
#           reads as the back of the part.  Enclosed bore pixels: 1856 at tilt 25,
#           818 at 35, 423 at 45, and 0 at the old 45/30/0 spin-0 view.  30 also
#           keeps enough tilt to show the strap block and both standoffs [0.15].
# 55,0,25 : OpenSCAD's own default view.  The webbing clip's two standoffs and
#           its slot stay visible against the background (fill 0.59); 60/0
#           flattens it (fill 0.92) [0.40].
CAMERA_DEFAULT = "0,0,0,45,0,180,0"

FN_FULL = 100
FN_DRAFT = 36
# 45 px keeps the ink clear of png_check's outermost downsample rows (650/30 = 22 px
# per row), so the border_fill test keeps reading 0.00.
MARGIN = 45
# png_check.py's own default frame for the ASCII preview and the edge test.
PNG_COLS = 78
PNG_ROWS = 30

USAGE = """usage: render.py <model.py> <outdir> [--stl|--png|--both|--scad]
                  [--draft] [--name NAME] [--camera X,Y,Z,RX,RY,RZ]
                  [--components N] [--log FILE] [--quiet]
       render.py --check

Writes <outdir>/<name>.stl and/or <name>.png from models/<name>.py.  <name>
defaults to the model file name without its extension.  Every render writes the
generated source to build/scad/<name>.scad; --scad stops after that write and
renders nothing.  The full OpenSCAD output goes to build/logs/<name>.log
(build/logs/<name>.draft.log in draft mode).  --draft renders at fn=36 instead
of 100.  --components N overrides the model's own EXPECTED_REGIONS, which the
plate's region count is checked against; a mismatch warns instead of failing.
Exit status is not zero when the model raises while it is built, when OpenSCAD
is missing or older than 2024, when the render reports WARNING or ERROR, when
the render summary does not say "Status: NoError", or when png_check.py rejects
the screenshot."""


def die(message):
    print(f"render.py: {message}", file=sys.stderr)
    raise SystemExit(2)


def log_dir():
    """Where the render logs go: $LOG_DIR, or build/logs."""
    return Path(os.environ["LOG_DIR"]) if os.environ.get("LOG_DIR") else ROOT / "build" / "logs"


def find_openscad():
    if os.environ.get("OPENSCAD"):
        return os.environ["OPENSCAD"]
    app = Path("/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    if os.access(app, os.X_OK):
        return str(app)
    return shutil.which("openscad")


def version_line(binary):
    """The first line of `<binary> --version`, with stderr folded in."""
    result = subprocess.run([binary, "--version"], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    lines = result.stdout.splitlines()
    return lines[0] if lines else ""


def check_binary():
    """Return the usable binary path, or stop with a reason."""
    binary = find_openscad()
    if not binary:
        die("no OpenSCAD binary found. Install OpenSCAD, or set OPENSCAD=/path/to/OpenSCAD.")
    if not os.access(binary, os.X_OK):
        die(f"OPENSCAD={binary} is not executable.")
    raw = version_line(binary)
    years = re.findall(r"(\d{4})\.\d{2}", raw)
    if not years:
        die(f"cannot read a version from '{binary} --version' (got: {raw}).")
    if int(years[-1]) < 2024:
        die(f"{binary} reports '{raw}'. This harness needs OpenSCAD 2024 or newer: "
            "the legacy CGAL backend takes minutes on these models, the manifold "
            "backend about a second. Install a current build, or set OPENSCAD= to a current one.")
    return binary


def openscad_version():
    """The version string, e.g. 2026.09.12, or "" when it cannot be read."""
    binary = check_binary()
    found = re.findall(r"\d{4}\.\d{2}(?:\.\d+)?", version_line(binary))
    return found[-1] if found else ""


def log_failure(message, log, quiet):
    print(f"render.py: {message}", file=sys.stderr)
    if quiet:
        hits = [(number, line) for number, line in
                enumerate(log.read_text(errors="replace").splitlines(), 1)
                if re.search(r"WARNING|ERROR", line)]
        for number, line in hits[:10]:
            print(f"{number}:{line}", file=sys.stderr)


def check_render_log(log, model, quiet):
    """A render is good only when OpenSCAD says so and nothing warned."""
    text = log.read_text(errors="replace")
    if re.search(r"WARNING|ERROR", text):
        log_failure(f"OpenSCAD reported warnings or errors while rendering {model} "
                    f"(log: {log})", log, quiet)
        return False
    if not re.search(r"Status:\s*NoError", text):
        log_failure(f"no 'Status: NoError' in the render summary for {model} — the top "
                    f"level object is not a manifold 3D object (log: {log})", log, quiet)
        return False
    return True


def model_scad(model, fn):
    """Build one Python model and write build/scad/<name>.scad.

    Returns the imported module and the generated file.  The import and the
    build run before OpenSCAD starts, so a broken model stops the render here
    with the real Python error.
    """
    name = Path(model).stem
    scad_path = ROOT / "build" / "scad" / f"{name}.scad"
    scad_path.parent.mkdir(parents=True, exist_ok=True)
    module = importlib.import_module(f"models.{name}")
    build = getattr(module, name)
    solid2.scad_render_to_file(build(fn=fn), str(scad_path))
    return module, scad_path


def run_openscad(binary, model, output, log, camera=None):
    """Render model to output, appending the OpenSCAD output to log.

    A camera adds the view flags a screenshot needs; an STL leaves it out.
    """
    command = [binary, "--backend=manifold", "--render=true"]
    if camera is not None:
        command += ["--autocenter", "--viewall", "--imgsize=900,650", "--projection=o",
                    "--colorscheme=Tomorrow", f"--camera={camera}"]
    command += ["-o", str(output), str(model)]
    with open(log, "ab") as fh:
        result = subprocess.run(command, stdout=fh, stderr=subprocess.STDOUT)
    return result.returncode


def render(model, outdir, kind="both", draft=False, name=None, camera=None,
           components=None, log=None, quiet=False):
    """Render one model.  Returns 0 when every requested artefact passed."""
    model = Path(model)
    outdir = Path(outdir)
    if not model.is_file():
        die(f"no such model file: {model}")
    if name is None:
        name = model.stem
    if camera is None:
        camera = CAMERA_DEFAULT
    fn = FN_DRAFT if draft else FN_FULL

    binary = check_binary()
    outdir.mkdir(parents=True, exist_ok=True)
    logs = log_dir()
    logs.mkdir(parents=True, exist_ok=True)
    if log is None:
        log = logs / (f"{name}.draft.log" if draft else f"{name}.log")
    log = Path(log)
    log.write_text("")
    print(f"render.py: {model} -> {outdir}/{name}.{{stl,png}} [{kind}] fn={fn} "
          f"camera={camera}", file=sys.stderr)

    # Build the Python model first: the generated source is the gate.  A model
    # that raises stops the render here, before OpenSCAD starts.
    try:
        module, scad = model_scad(model, fn)
    except Exception as exc:  # noqa: BLE001 - any model error must fail this render, not crash the tool
        print(f"render.py: cannot build {model}: {exc}", file=sys.stderr)
        return 1
    if kind == "scad":
        return 0

    # Render into build/tmp and publish with a rename: a reader never sees a
    # half-written STL or plate, and a plate appears only after it has passed
    # png_check.  Two people running `make verify` at the same time no longer trip
    # over each other's partial files; the pid keeps the staging paths apart.
    tmp_dir = ROOT / "build" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    stage_stl = tmp_dir / f"{name}.{os.getpid()}.stl"
    stage_png = tmp_dir / f"{name}.{os.getpid()}.png"

    failed = 0

    if kind in ("stl", "both"):
        status = run_openscad(binary, scad, stage_stl, log)
        if not quiet:
            sys.stderr.write(log.read_text(errors="replace"))
        if status != 0:
            log_failure(f"OpenSCAD exit status {status} while writing {outdir}/{name}.stl "
                        f"(log: {log})", log, quiet)
            failed = 1
        elif not check_render_log(log, model, quiet):
            failed = 1
        else:
            os.replace(stage_stl, outdir / f"{name}.stl")
            metrics = stl_metrics.metrics(str(outdir / f"{name}.stl"))
            # Flush: verify.py captures stdout and stderr into one file, and the
            # warning lines that go with this model must not drift past it.
            print(json.dumps(metrics, sort_keys=True), flush=True)
            if "error" in metrics:
                failed = 1

    if kind in ("png", "both"):
        log.write_text("")
        status = run_openscad(binary, scad, stage_png, log, camera=camera)
        if not quiet:
            sys.stderr.write(log.read_text(errors="replace"))
        if status != 0:
            log_failure(f"OpenSCAD exit status {status} while writing {outdir}/{name}.png "
                        f"(log: {log})", log, quiet)
            failed = 1
        elif not check_render_log(log, model, quiet):
            failed = 1
        else:
            # --viewall fits the model's bounding sphere, so a wide part leaves
            # most of the frame as background.  Trim to the ink with a margin that
            # stays clear of png_check's frame-edge test, then check the plate
            # before it ships.
            if not trim_png.trim(str(stage_png), MARGIN, dry_run=False):
                failed = 1
            # The model says how many silhouettes its plate must show; --components
            # overrides that for a one-off look.
            if components is not None:
                want = components
            else:
                want = getattr(module, "EXPECTED_REGIONS", None)
            if png_check.check(str(stage_png), PNG_COLS, PNG_ROWS, quiet, want):
                os.replace(stage_png, outdir / f"{name}.png")
            else:
                failed = 1

    return failed


def main(argv=None):
    args = list(sys.argv[1:]) if argv is None else list(argv)
    model = None
    outdir = None
    kind = "both"
    draft = False
    quiet = False
    name = None
    camera = None
    components = None
    log = None

    while args:
        arg = args.pop(0)
        if arg == "--check":
            binary = check_binary()
            print(f"render.py: OpenSCAD ok: {binary} ({version_line(binary)})")
            return 0
        if arg == "--print-version":
            print(openscad_version())
            return 0
        if arg in ("--stl", "--png", "--both", "--scad"):
            kind = arg[2:]
        elif arg == "--draft":
            draft = True
        elif arg == "--quiet":
            quiet = True
        elif arg in ("--name", "--camera", "--components", "--log"):
            if not args:
                die(f"{arg} needs a value")
            value = args.pop(0)
            if arg == "--name":
                name = value
            elif arg == "--camera":
                camera = value
            elif arg == "--log":
                log = value
            else:
                try:
                    components = int(value)
                except ValueError:
                    die(f"--components needs a whole number, got '{value}'")
        elif arg in ("-h", "--help"):
            print(USAGE)
            return 0
        elif arg.startswith("-"):
            die(f"unknown option '{arg}' (try --help)")
        elif model is None:
            model = arg
        elif outdir is None:
            outdir = arg
        else:
            die(f"unexpected argument '{arg}'")

    if model is None:
        die("no model given (try --help)")
    if outdir is None:
        die("no output directory given (try --help)")
    return render(model, outdir, kind=kind, draft=draft, name=name, camera=camera,
                  components=components, log=log, quiet=quiet)


if __name__ == "__main__":
    sys.exit(main())
