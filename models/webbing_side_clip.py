"""Webbing side clip: slides onto 37.5 x 5 mm hip webbing and holds one 12 mm
hose on each side. The webbing and the hose sizes come from
constants/hardware.py; everything below is this part's own tuning.

Draft render:
    uv run tools/render.py models/webbing_side_clip.py build/draft --draft
"""

from __future__ import annotations

from typing import Final

from solid2 import OpenSCADObjectPlus, cube, difference, translate, union

from constants.hardware import hose_side_clip_dia, webbing_hip_size
from lib.shapes import rounded_cube
from lib.standoff import hose_clip_on_standoff

MODEL_FN: int = 100
EXPECTED_REGIONS: Final = 1

wall_t: Final = 3  # wall thickness of the block and of the hose clips
block_h: Final = 20  # height of the webbing block
gap: Final = 0.5  # clearance, so the webbing slides in
tube_d: Final = hose_side_clip_dia  # hose held by the two standoff clips
clip_h: Final = 10  # height (clip axis) of both hose clips

hip: Final = webbing_hip_size  # [width, thickness] of the hip webbing
webbing_w: Final = hip[0]  # width along the webbing
webbing_t: Final = hip[1]  # thickness across the webbing

tt: Final = wall_t * 2 + webbing_t  # block thickness across the webbing
tw: Final = wall_t * 2 + webbing_w  # block width along the webbing
standoff_span: Final = tt  # distance from the webbing to the standoff end


def webbing_side_clip(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    """The part: a rounded block with the webbing passage and the clearance slot
    cut through it, and one hose standoff clip on each side of the webbing."""
    if wall_t <= 0:
        raise ValueError("webbing_side_clip: wall_t must be positive")
    if webbing_t <= 0:
        raise ValueError("webbing_side_clip: webbing_t must be positive")
    if webbing_w <= 0:
        raise ValueError("webbing_side_clip: webbing_w must be positive")
    if block_h <= 0:
        raise ValueError("webbing_side_clip: block_h must be positive")
    if gap < 0:
        raise ValueError("webbing_side_clip: gap must not be negative")

    body = union()(
        [
            # Rounded block that carries the webbing.
            rounded_cube(
                size=[tw, tt, block_h],
                center=True,
                radius=wall_t / 2,
                apply_to="all",
                fn=fn,
            ),
            # One standoff clip on each side, on the block's lower face: they
            # span -block_h / 2 .. -block_h / 2 + clip_h, so they are not
            # centred in Z. The clip wall follows the block wall, so a tuned
            # wall_t tunes both.
            translate([tw / 2, tt / 2, -block_h / 2 + clip_h / 2])(
                hose_clip_on_standoff(
                    h=clip_h,
                    tube_d=tube_d,
                    standoff_h=standoff_span,
                    t_outer=wall_t,
                    fn=fn,
                )
            ),
            translate([tw / -2, tt / 2, -block_h / 2 + clip_h / 2])(
                hose_clip_on_standoff(
                    h=clip_h,
                    tube_d=tube_d,
                    standoff_h=standoff_span,
                    t_outer=wall_t,
                    fn=fn,
                )
            ),
        ]
    )

    cuts = union()(
        [
            # Webbing passage through the block.
            cube(size=[webbing_w, webbing_t, block_h + 1], center=True),
            # Clearance slot, so the webbing slides in from one end.
            translate([tw / -2, 0, 0])(cube(size=[tw, gap, block_h + 1], center=True)),
        ]
    )

    return difference()([body, cuts])
