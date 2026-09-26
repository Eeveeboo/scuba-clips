"""Print plate: the four parts in one render, in the old plate layout. It
holds no sizes: each part reads its own tuning from lib/config.py.

`import`, never a build at import time: the models expose builder functions, so
this module can import the four parts and call each one once.

Render:
    uv run tools/render.py models/all.py build
"""

from __future__ import annotations

from typing import Final

from lib.scad import OpenSCADObjectPlus
from models.inflator_spg_combo_clip import inflator_spg_combo_clip
from models.lower_octi_retaining_clip import lower_octi_retaining_clip
from models.upper_inflator_retaining_clip import upper_inflator_retaining_clip
from models.upper_octi_retaining_clip import upper_octi_retaining_clip

EXPECTED_REGIONS: Final = 4


def all() -> OpenSCADObjectPlus:
    """The print plate: all four parts, placed in the old layout."""

    scene = inflator_spg_combo_clip()
    scene += upper_octi_retaining_clip().translate(100, 0, 0)
    scene += lower_octi_retaining_clip().translate(0, -100, 0)
    scene += upper_inflator_retaining_clip().translate(100, -100, 0)
    return scene
