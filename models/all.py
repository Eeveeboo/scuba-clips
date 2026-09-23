"""Print plate: the three parts in one render, in the old plate layout. It
holds no sizes: each part reads its own tuning variables and the constants it
imports.

`import`, never a build at import time: the models expose builder functions, so
this module can import the three parts and call each one once.

Draft render:
    uv run tools/render.py models/all.py build/draft --draft
"""

from __future__ import annotations

from typing import Final

from solid2 import OpenSCADObjectPlus, translate, union

from models.inflator_spg_combo_clip import inflator_spg_combo_clip
from models.upper_octi_retaining_clip import upper_octi_retaining_clip
from models.webbing_side_clip import webbing_side_clip

MODEL_FN: int = 100
EXPECTED_REGIONS: Final = 3


def all(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    """The print plate: all three parts, placed in the old layout."""
    return union()(
        [
            inflator_spg_combo_clip(fn=fn),
            translate([100, -50, 0])(upper_octi_retaining_clip(fn=fn)),
            translate([0, -100, 0])(webbing_side_clip(fn=fn)),
        ]
    )
