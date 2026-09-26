#!/usr/bin/env python3
"""watch.py — re-render a model when its source changes.

  tools/watch.py

Renders every model once at start as an STL, a PNG and a .scad into build/
(WATCH_DIR), then polls the mtimes of the model files and their inputs:

  * a change in models/x.py re-renders x, and only x,
  * a change in models/all.py re-renders every model: the plate holds the parts,
  * a change in lib/*.py or config.toml re-renders every model.

Every .py under the models directory counts, at any depth: models/dev/x.py is
model dev/x and renders to build/dev/x.png.  The name is the path relative to
the models directory, so a nested model and a top-level one never collide.

A part change does not refresh all.png.  Only all.py, lib/ and config.toml do.
Changes inside one debounce window are batched into one round, and one model
renders at a time.  tools/render.py stages and renames, so a render that fails
leaves the last good files in place.  No dependency is added: the mtimes come
from os.stat.  Run it until you interrupt it with Ctrl-C.

A render that succeeds prints a green line.  A render that fails prints a bold
red line to stderr, and a red line counts the failures of the round.  The other
lines are cyan.  The colour is dropped when the output is not a terminal.

The model list comes from every models/**/*.py.  The paths are overridable by
environment, as in the other tools: MODELS_DIR WATCH_DIR
"""

import os
import sys
import time
from pathlib import Path

import click
import render

ROOT = Path(__file__).resolve().parent.parent

POLL_SECONDS = 0.5  # how often the mtimes are read
DEBOUNCE_SECONDS = 0.5  # a quiet window this long closes a batch of changes
PLATE = "all"  # models/all.py: the print plate, which holds every part


def path_from_env(name, default):
    """A path from the environment, defaulted and resolved against the repo root."""
    value = os.environ.get(name)
    if not value:
        return ROOT / default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def watch_paths(models_dir):
    """The model files, and the shared inputs whose change re-renders every model."""
    files = sorted(models_dir.rglob("*.py"))
    model_files = [path for path in files if path.name != "__init__.py"]
    shared = [path for path in files if path.name == "__init__.py"]
    shared += sorted((ROOT / "lib").glob("*.py"))
    shared.append(ROOT / "config.toml")
    return model_files, shared


def model_name(path, models_dir):
    """A model's name: its path under the models directory, as dev/print_tests."""
    return path.relative_to(models_dir).with_suffix("").as_posix()


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


def targets_for(bumped, model_files, shared, models_dir):
    """The models one batch of changes re-renders, sorted, without duplicates."""
    names = sorted(model_name(path, models_dir) for path in model_files)
    if bumped & set(shared):
        return names
    by_path = {path: model_name(path, models_dir) for path in model_files}
    targets = []
    for path in sorted(bumped):
        name = by_path.get(path)
        if name and name not in targets:
            targets.append(name)
    if PLATE in targets:
        return names
    return targets


def say(message, colour=None, err=False):
    """One prefixed line, written now, in the given colour.

    click.echo drops the colour when the stream is not a terminal.  The flush
    keeps a long render from holding the line back.
    """
    stream = sys.stderr if err else sys.stdout
    click.echo(
        click.style(f"watch.py: {message}", fg=colour, bold=colour == "red"),
        file=stream,
    )
    stream.flush()


def ok(message):
    """A line that reports a good result, in green."""
    say(message, colour="green")


def bad(message):
    """A line that reports a problem, in bold red on stderr, so it stands out."""
    say(message, colour="red", err=True)


def render_one(name, models_dir, out_dir):
    """Render one model to an STL, a PNG and a .scad.  Returns True on success.

    A nested name keeps its directory: dev/print_tests writes build/dev/.
    """
    model = models_dir / f"{name}.py"
    stem = Path(name).name
    outdir = out_dir / Path(name).parent
    log = outdir / f"{stem}.log"
    status = render.render(model, outdir, quiet=True, log=log)
    if status == 0:
        ok(f"{name} -> {outdir}/{stem}.{{stl,png,scad}}")
        return True
    bad(f"{name} FAILED, the last good files stay (log: {log})")
    return False


def render_all(names, models_dir, out_dir):
    """Render each name in turn, and count the failures in a red closing line."""
    failed = [name for name in names if not render_one(name, models_dir, out_dir)]
    if failed:
        bad(f"{len(failed)} of {len(names)} render(s) FAILED: {', '.join(failed)}")


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


@click.command()
def main():
    """Re-render a model when its source changes.

    Renders every model under models/ as an STL, a PNG and a .scad into build/
    (WATCH_DIR), a nested model as build/dev/x.png, then re-renders a model when
    its source changes and every model when lib/ or config.toml changes.  Ctrl-C
    stops it.
    """
    models_dir = path_from_env("MODELS_DIR", "models")
    out_dir = path_from_env("WATCH_DIR", "build")
    if not models_dir.is_dir():
        bad(f"no models directory {models_dir}")
        sys.exit(1)
    model_files, shared = watch_paths(models_dir)
    names = sorted(model_name(path, models_dir) for path in model_files)
    if not names:
        bad(f"no models found in {models_dir}")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    say(
        f"watching {len(names)} models in {models_dir} and "
        f"{len(shared)} shared files (__init__.py, lib/, config.toml)",
        colour="cyan",
    )
    say(f"PNGs go to {out_dir}", colour="cyan")

    # The stamps come first: a change made while the first round renders is then
    # visible to the loop below and gets a fresh render.
    stamps = snapshot(model_files + shared)
    render_all(names, models_dir, out_dir)

    try:
        while True:
            model_files, shared, stamps, bumped = wait_for_changes(models_dir, stamps)
            say(
                f"{len(bumped)} changed file(s): "
                f"{', '.join(sorted(str(path.relative_to(ROOT)) for path in bumped))}",
                colour="cyan",
            )
            targets = targets_for(bumped, model_files, shared, models_dir)
            if not targets:
                say("nothing to re-render", colour="cyan")
                continue
            say(f"re-rendering {', '.join(targets)}", colour="cyan")
            render_all(targets, models_dir, out_dir)
    except KeyboardInterrupt:
        say("stopped", colour="cyan")


if __name__ == "__main__":
    main()
