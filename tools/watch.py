#!/usr/bin/env python3
"""watch.py — re-render a model when its source changes.

  tools/watch.py

Renders every model once at start, PNG only, into build/watch/, then polls the
mtimes of the model files and their inputs:

  * a change in models/x.py re-renders x, and only x,
  * a change in models/all.py re-renders every model: the plate holds the parts,
  * a change in lib/*.py or constants/*.py re-renders every model.

A part change does not refresh all.png.  Only all.py, lib/ and constants/ do.
Changes inside one debounce window are batched into one round, and one model
renders at a time.  tools/render.py stages and renames, so a render that fails
leaves the last good image in place.  No dependency is added: the mtimes come
from os.stat.  Run it until you interrupt it with Ctrl-C.

The model list comes from models/*.py.  The paths are overridable by
environment, as in the other tools: MODELS_DIR WATCH_DIR
"""

import os
import sys
import time
from pathlib import Path

import render

ROOT = Path(__file__).resolve().parent.parent

POLL_SECONDS = 0.5  # how often the mtimes are read
DEBOUNCE_SECONDS = 0.5  # a quiet window this long closes a batch of changes
PLATE = "all"  # models/all.py: the print plate, which holds every part

USAGE = """usage: watch.py

Renders every model under models/*.py, PNG only, into build/watch/ (WATCH_DIR),
then re-renders a model when its source changes and every model when lib/ or
constants/ changes.  Ctrl-C stops it."""


def path_from_env(name, default):
    """A path from the environment, defaulted and resolved against the repo root."""
    value = os.environ.get(name)
    if not value:
        return ROOT / default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def watch_paths(models_dir):
    """The model files, and the shared inputs whose change re-renders every model."""
    files = sorted(models_dir.glob("*.py"))
    model_files = [path for path in files if path.stem != "__init__"]
    shared = [path for path in files if path.stem == "__init__"]
    shared += sorted((ROOT / "lib").glob("*.py"))
    shared += sorted((ROOT / "constants").glob("*.py"))
    return model_files, shared


def snapshot(paths):
    """The mtime of each watched file in nanoseconds, or None when unreadable."""
    stamp = {}
    for path in paths:
        try:
            stamp[path] = path.stat().st_mtime_ns
        except OSError:
            stamp[path] = None
    return stamp


def changed(before, after):
    """The paths whose mtime moved between two snapshots; a new file counts."""
    names = set(before) | set(after)
    return {path for path in names if before.get(path) != after.get(path)}


def targets_for(bumped, model_files, shared):
    """The models one batch of changes re-renders, sorted, without duplicates."""
    names = sorted(path.stem for path in model_files)
    if bumped & set(shared):
        return names
    targets = []
    for path in sorted(bumped):
        if path.stem in names and path.stem not in targets:
            targets.append(path.stem)
    if PLATE in targets:
        return names
    return targets


def render_one(name, models_dir, out_dir):
    """Render one model to a PNG.  Returns True when the image was published."""
    model = models_dir / f"{name}.py"
    log = out_dir / "logs" / f"{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    status = render.render(model, out_dir, kind="png", quiet=True, log=log)
    if status == 0:
        print(f"watch.py: {name} -> {out_dir / f'{name}.png'}", flush=True)
        return True
    print(
        f"watch.py: {name} FAILED, the last good image stays (log: {log})", flush=True
    )
    return False


def wait_for_changes(models_dir, stamps):
    """Block until a watched file changes; debounce the batch.

    Returns the model files, the shared files, the new stamps and the paths that
    changed.  The stamps are taken when the batch is consumed, so a change that
    lands during a render shows up as a change again.
    """
    while True:
        time.sleep(POLL_SECONDS)
        model_files, shared = watch_paths(models_dir)
        now = snapshot(model_files + shared)
        bumped = changed(stamps, now)
        if not bumped:
            stamps = now
            continue
        last = time.monotonic()
        while time.monotonic() - last < DEBOUNCE_SECONDS:
            time.sleep(POLL_SECONDS)
            model_files, shared = watch_paths(models_dir)
            stamps = snapshot(model_files + shared)
            more = changed(now, stamps)
            if more:
                bumped |= more
                last = time.monotonic()
            now = stamps
        return model_files, shared, stamps, bumped


def main():
    for arg in sys.argv[1:]:
        if arg in ("-h", "--help"):
            print(USAGE)
            return 0
        print(f"watch.py: unknown option '{arg}' (try --help)", file=sys.stderr)
        return 2

    models_dir = path_from_env("MODELS_DIR", "models")
    out_dir = path_from_env("WATCH_DIR", "build/watch")
    if not models_dir.is_dir():
        print(f"watch.py: no models directory {models_dir}", file=sys.stderr)
        return 1
    model_files, shared = watch_paths(models_dir)
    names = sorted(path.stem for path in model_files)
    if not names:
        print(f"watch.py: no models found in {models_dir}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"watch.py: watching {len(names)} models in {models_dir} and "
        f"{len(shared)} shared files in lib/ and constants/",
        flush=True,
    )
    print(f"watch.py: PNGs go to {out_dir}", flush=True)

    # The stamps come first: a change made while the first round renders is then
    # visible to the loop below and gets a fresh render.
    stamps = snapshot(model_files + shared)
    for name in names:
        render_one(name, models_dir, out_dir)

    try:
        while True:
            model_files, shared, stamps, bumped = wait_for_changes(models_dir, stamps)
            print(
                f"watch.py: {len(bumped)} changed file(s): "
                f"{', '.join(sorted(str(path.relative_to(ROOT)) for path in bumped))}",
                flush=True,
            )
            targets = targets_for(bumped, model_files, shared)
            if not targets:
                print("watch.py: nothing to re-render", flush=True)
                continue
            print(f"watch.py: re-rendering {', '.join(targets)}", flush=True)
            for name in targets:
                render_one(name, models_dir, out_dir)
    except KeyboardInterrupt:
        print("watch.py: stopped", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
