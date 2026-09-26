"""Generate OpenSCAD source for one clip, with no leftover state.

The web server is stateless and answers requests concurrently. Two pieces of
process state make that unsafe:

1. `lib.config.CONFIG` is one module global, and every model reads it.
2. Python caches the imported project modules in `sys.modules`.

One lock serialises generation. Each request sets the config, drops the cached
`lib.*` and `models.*` modules (except `lib.config`, which holds the new
config), and imports the model again. The lock is required: the spike showed
that without it concurrent requests with different values all returned the same
source, the last writer's.
"""

from __future__ import annotations

import importlib
import sys
import threading
from typing import Any

import solid2

from lib.config import build_config, set_config

_LOCK = threading.Lock()
_PROJECT_ROOTS = {"lib", "models"}
# lib.config itself stays: it holds the config the server just set.
_KEEP = {"lib.config"}


def _forget_project_modules() -> None:
    """Drop the cached project modules, so an import reads the source again."""
    stale = [
        key
        for key in sys.modules
        if key.split(".")[0] in _PROJECT_ROOTS and key not in _KEEP
    ]
    for key in stale:
        del sys.modules[key]


def render_scad(model_name: str, values: dict[str, Any]) -> str:
    """The OpenSCAD source for `model_name` with `values` applied.

    `values` is a nested `section -> field -> value` mapping. A key that is
    absent keeps its default. The result is a string: this function never writes
    a file and never calls OpenSCAD.
    """
    config = build_config(values)
    with _LOCK:
        set_config(config)
        _forget_project_modules()
        module = importlib.import_module(f"models.{model_name}")
        build = getattr(module, model_name)
        return solid2.scad_render(build())
