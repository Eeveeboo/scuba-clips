#!/usr/bin/env python3
"""cli.py — the scuba-clips build harness.

  uv run cli make-all
  uv run cli watch
  uv run cli help

Every command reuses the code under tools/ and lib/.  make-all removes build/
and renders every model under models/ into build/, at any depth.  watch keeps
the incremental behaviour of tools/watch.py.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
# render.py imports its siblings as top-level modules, so tools/ must be on the
# path before it loads.  render.py puts the repo root on the path itself.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import render

# ruff checks every Python source the build writes, and the two tools that are
# already in the new layout.  The older tools/*.py keep their own layout: this
# is a port, not a reformat.
PY_PATHS = ("lib", "models", "tools/watch.py", "tools/cli.py")
BUILD_DIR = ROOT / "build"
MODELS_DIR = ROOT / "models"


def run_python(arguments):
    """Run a Python command in this environment, and exit with its status."""
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT, check=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


@click.group(no_args_is_help=True)
def main():
    """Build the scuba clips, and check the sources."""


@main.command(name="help")
@click.pass_context
def help_command(ctx):
    """Show this command list, the OpenSCAD binary, and the model list."""
    click.echo(ctx.parent.get_help())
    binary = render.find_openscad()
    names = render.find_models(MODELS_DIR)
    click.echo()
    click.echo(f"  OpenSCAD: {binary or 'not found'}")
    click.echo(f"  models:   {' '.join(names) if names else 'none in models/'}")


@main.command(name="make-all")
def make_all():
    """Remove build/ and render every model into build/."""
    render.check_binary()
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    names = render.find_models(MODELS_DIR)
    if not names:
        click.echo("cli: no models in models/ yet")
        return
    failed = []
    for name in names:
        model = MODELS_DIR / f"{name}.py"
        out_dir = BUILD_DIR / Path(name).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        if render.render(model, out_dir, name=Path(name).name, quiet=True) != 0:
            failed.append(name)
    if failed:
        raise click.ClickException(
            f"{len(failed)} of {len(names)} render(s) FAILED: {', '.join(failed)}"
        )


@main.command(name="watch")
def watch_command():
    """Re-render a model when its source changes."""
    render.check_binary()
    run_python([str(TOOLS_DIR / "watch.py")])


@main.command(name="clean")
def clean():
    """Remove build/."""
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


@main.command(name="lint")
def lint():
    """Ruff check the Python sources."""
    run_python(["-m", "ruff", "check", *PY_PATHS])


@main.command(name="typecheck")
def typecheck():
    """Run ty check."""
    run_python(["-m", "ty", "check"])


@main.command(name="format")
def format_sources():
    """Ruff format the Python sources."""
    run_python(["-m", "ruff", "format", *PY_PATHS])


@main.command(name="config-example")
def config_example():
    """Write config.example.toml from lib/config.py."""
    run_python(["-m", "lib.config", "--example"])


@main.command(name="check-config-example")
def check_config_example():
    """Fail when config.example.toml is stale."""
    run_python(["-m", "lib.config", "--check"])


@main.command(name="check-baseline")
def check_baseline():
    """Render all and compare against tools/baseline/."""
    render.check_binary()
    run_python([str(TOOLS_DIR / "verify.py")])


@main.command(name="save-baseline")
def save_baseline():
    """Render all and write tools/baseline/*.json."""
    render.check_binary()
    run_python([str(TOOLS_DIR / "verify.py"), "--save"])


if __name__ == "__main__":
    main()
