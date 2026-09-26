#!/usr/bin/env python3
"""render.py — the single render entry point for the scuba-clips build.

  tools/render.py <model.py> <outdir>
                  [--name NAME] [--camera X,Y,Z,RX,RY,RZ] [--components N]
                  [--log FILE] [--quiet]
  tools/render.py --check          # is the OpenSCAD binary usable?
  tools/render.py --print-version  # the version string, e.g. 2026.09.12

Imports models/<name>.py, or models/<dir>/<name>.py for a nested model such as
models/dev/print_tests.py, and calls that file's <name> builder.  The generated
source goes to <outdir>/<name>.scad.  That file is what OpenSCAD renders
to <outdir>/<name>.stl and <outdir>/<name>.png, where <name> defaults to the
model file name without its extension.  A PNG is trimmed to the geometry plus a
45 px margin, because --viewall fits the bounding sphere and leaves a wide part
floating in background.  The full OpenSCAD output goes to <outdir>/<name>.log.

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

import click
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

# 45 px keeps the ink clear of png_check's outermost downsample rows (650/30 = 22 px
# per row), so the border_fill test keeps reading 0.00.
MARGIN = 45
# png_check.py's own default frame for the ASCII preview and the edge test.
PNG_COLS = 78
PNG_ROWS = 30

def die(message):
    print(f"render.py: {message}", file=sys.stderr)
    raise SystemExit(2)


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


def forget_project_modules():
    """Drop the cached project modules, so the next import reads the source again.

    Python keeps every imported module in sys.modules, and a second import of
    the same name answers with that old object.  tools/watch.py renders in one
    process, so without this a source edit would rebuild the old geometry and
    publish the same image.  lib/ goes too: every model imports it, and a
    change there must reach the next render.
    """
    roots = {"models", "lib"}
    for key in [key for key in sys.modules if key.split(".")[0] in roots]:
        del sys.modules[key]


def find_models(models_dir):
    """The model names under models_dir, at any depth.

    models/dev/print_tests.py is model "dev/print_tests".  __init__.py holds a
    package, not a model.
    """
    models_dir = Path(models_dir)
    names = (path.relative_to(models_dir).with_suffix("").as_posix()
             for path in models_dir.rglob("*.py"))
    return sorted(name for name in names if Path(name).name != "__init__")


def module_name(model):
    """The import path of a model file: models/dev/x.py -> models.dev.x.

    A model file outside models/ keeps the flat answer, models.<stem>, which is
    what a scratch tree outside the repo gets.
    """
    path = Path(model).resolve()
    try:
        relative = path.relative_to(ROOT / "models")
    except ValueError:
        return f"models.{path.stem}"
    parts = ("models",) + relative.with_suffix("").parts
    return ".".join(parts)


def model_scad(model, scad_path):
    """Build one Python model and write its generated .scad to scad_path.

    Returns the imported module and the generated file.  The import and the
    build run before OpenSCAD starts, so a broken model stops the render here
    with the real Python error.
    """
    name = Path(model).stem
    forget_project_modules()
    scad_path.parent.mkdir(parents=True, exist_ok=True)
    module = importlib.import_module(module_name(model))
    build = getattr(module, name)
    solid2.scad_render_to_file(build(), str(scad_path))
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


def render(model, outdir, name=None, camera=None, components=None, log=None, quiet=False):
    """Render one model.  Returns 0 when every artefact passed."""
    model = Path(model)
    outdir = Path(outdir)
    if not model.is_file():
        die(f"no such model file: {model}")
    if name is None:
        name = model.stem
    if camera is None:
        camera = CAMERA_DEFAULT

    binary = check_binary()
    outdir.mkdir(parents=True, exist_ok=True)
    scad_path = outdir / f"{name}.scad"
    stl_path = outdir / f"{name}.stl"
    png_path = outdir / f"{name}.png"
    if log is None:
        log = outdir / f"{name}.log"
    log = Path(log)
    log.write_text("")
    print(f"render.py: {model} -> {outdir}/{name}.{{stl,png,scad}} "
          f"camera={camera}", file=sys.stderr)

    # Build the Python model first: the generated source is the gate.  A model
    # that raises stops the render here, before OpenSCAD starts.
    try:
        module, scad = model_scad(model, scad_path)
    except Exception as exc:  # noqa: BLE001 - any model error must fail this render, not crash the tool
        print(f"render.py: cannot build {model}: {exc}", file=sys.stderr)
        return 1

    # Render under a temporary name in outdir and publish with a rename: a reader
    # never sees a half-written STL or plate, and a plate appears only after it
    # has passed png_check.  Two people rendering at the same time do not trip
    # over each other's partial files; the pid keeps the staging paths apart.
    stage_stl = outdir / f"{name}.{os.getpid()}.tmp.stl"
    stage_png = outdir / f"{name}.{os.getpid()}.tmp.png"

    failed = 0

    status = run_openscad(binary, scad, stage_stl, log)
    if not quiet:
        sys.stderr.write(log.read_text(errors="replace"))
    if status != 0:
        log_failure(f"OpenSCAD exit status {status} while writing {stl_path} "
                    f"(log: {log})", log, quiet)
        failed = 1
    elif not check_render_log(log, model, quiet):
        failed = 1
    else:
        os.replace(stage_stl, stl_path)
        metrics = stl_metrics.metrics(str(stl_path))
        # Flush: verify.py captures stdout and stderr into one file, and the
        # warning lines that go with this model must not drift past it.
        print(json.dumps(metrics, sort_keys=True), flush=True)
        if "error" in metrics:
            failed = 1

    log.write_text("")
    status = run_openscad(binary, scad, stage_png, log, camera=camera)
    if not quiet:
        sys.stderr.write(log.read_text(errors="replace"))
    if status != 0:
        log_failure(f"OpenSCAD exit status {status} while writing {png_path} "
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
            os.replace(stage_png, png_path)
        else:
            failed = 1

    return failed


def show_check(ctx, _param, value):
    """The --check callback: report the OpenSCAD binary, then stop.

    Eager, so it runs before click demands a model and an output directory.
    """
    if not value or ctx.resilient_parsing:
        return
    binary = check_binary()
    click.echo(f"render.py: OpenSCAD ok: {binary} ({version_line(binary)})")
    ctx.exit(0)


def show_version(ctx, _param, value):
    """The --print-version callback: print the OpenSCAD version, then stop."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(openscad_version())
    ctx.exit(0)


@click.command()
@click.argument("model")
@click.argument("outdir")
@click.option("--name", metavar="NAME",
              help="Base name of the output files, default the model file name.")
@click.option("--camera", metavar="X,Y,Z,RX,RY,RZ",
              help="OpenSCAD camera for the screenshot.")
@click.option("--components", type=int, metavar="N",
              help="Expected plate regions; overrides the model's EXPECTED_REGIONS.")
@click.option("--log", metavar="FILE", help="Write the OpenSCAD output to FILE.")
@click.option("--quiet", is_flag=True, help="Do not echo the OpenSCAD output.")
@click.option("--check", is_flag=True, is_eager=True, expose_value=False,
              callback=show_check, help="Report the OpenSCAD binary and stop.")
@click.option("--print-version", is_flag=True, is_eager=True, expose_value=False,
              callback=show_version, help="Print the OpenSCAD version and stop.")
def main(model, outdir, name, camera, components, log, quiet):
    """Render models/<name>.py through OpenSCAD.

    Writes <outdir>/<name>.stl, <outdir>/<name>.png and the generated source
    <outdir>/<name>.scad.  The full OpenSCAD output goes to <outdir>/<name>.log.
    A mismatch against a model's own EXPECTED_REGIONS warns instead of failing.

    The exit status is not zero when the model raises while it is built, when
    OpenSCAD is missing or older than 2024, when the render reports WARNING or
    ERROR, when the render summary does not say "Status: NoError", or when
    png_check.py rejects the screenshot.
    """
    sys.exit(render(model, outdir, name=name, camera=camera,
                    components=components, log=log, quiet=quiet))


if __name__ == "__main__":
    main()
