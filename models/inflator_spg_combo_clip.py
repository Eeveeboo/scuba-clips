"""Inflator + SPG combo clip: bundles the three left-side hoses of a rig.
Fits the 27 mm BCD inflator tube, the 12.5 mm LPI hose and the 8 mm HP/SPG
hose.

Draft render:
    uv run tools/render.py models/inflator_spg_combo_clip.py build/draft --draft
"""

from __future__ import annotations

from typing import Final

from solid2 import OpenSCADObjectPlus, cube, difference, rotate, translate, union

from constants.hardware import (
    hose_hp_spg_dia,
    hose_inflator_tube_dia,
    hose_lpi_dia,
)
from lib.c_clip import hose_clip, hose_clip_keepout
from lib.params import hose_clip_total_dia

MODEL_FN: int = 100
EXPECTED_REGIONS: Final = 1

# Clip walls and clip length (old file-level t_inner / t_outer / w_gap and the
# default clip height).
t_inner: Final = 2
t_outer: Final = 3
w_gap: Final = 2
clip_h: Final = 10

# Hoses this clip fits.
inflator_tube_d: Final = hose_inflator_tube_dia  # BCD inflator tube
lpi_hose_d: Final = hose_lpi_dia  # LPI hose, first stage to inflator
hp_spg_hose_d: Final = hose_hp_spg_dia  # HP hose, first stage to the SPG

# Position of the HP/SPG clip around the inflator clip.
hp_spg_angle: Final = 30  # degrees, from the inflator clip's axis
hp_spg_radius: Final = 22.5  # distance from the inflator clip's centre
hp_spg_block_x: Final = -14.5  # X centre of the block between the two clips
hp_spg_block_len: Final = 29  # X length of that block

# Position of the LPI clip around the inflator clip.
lpi_angle: Final = -22  # degrees, from the inflator clip's axis
lpi_radius: Final = 30  # distance from the inflator clip's centre
lpi_block_x: Final = -14.5  # X centre of the blocks between the two clips
lpi_block_len: Final = 29  # X length of those blocks
lpi_block_angle: Final = 12  # degrees, tilt of the block on each side

# Each hose position is written once, and both the clip and its keep-out volume
# go through it, so the part and the cut cannot drift apart.


def _at_inflator_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
    """Placement of the BCD inflator tube clip, opposite the other two."""
    return rotate([0, 0, 180])(child)


def _at_hp_spg_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
    """Placement of the HP/SPG hose clip."""
    return rotate([0, 0, hp_spg_angle])(translate([hp_spg_radius, 0, 0])(child))


def _at_lpi_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
    """Placement of the LPI hose clip."""
    return rotate([0, 0, lpi_angle])(translate([lpi_radius, 0, 0])(child))


def _hose_clips_and_blocks(
    blocks: bool = False, fn: int = MODEL_FN
) -> OpenSCADObjectPlus:
    """The three hose clips, with their connecting blocks when `blocks` is
    true."""
    # BCD inflator tube, clip opening away from the other two.
    inflator = _at_inflator_clip(
        hose_clip(
            d_hose=inflator_tube_d,
            t_inner=t_inner,
            w_gap=w_gap,
            t_outer=t_outer,
            h=clip_h,
            fn=fn,
        )
    )

    # HP/SPG hose, and the block between it and the inflator clip.
    hp_spg_children = [
        hose_clip(
            d_hose=hp_spg_hose_d,
            t_inner=t_inner,
            w_gap=w_gap,
            t_outer=t_outer,
            h=clip_h,
            fn=fn,
        )
    ]
    if blocks:
        hp_spg_children.append(
            translate([hp_spg_block_x, 0, 0])(
                cube(
                    [
                        hp_spg_block_len,
                        hose_clip_total_dia(
                            d_hose=hp_spg_hose_d,
                            t_outer=t_outer,
                            w_gap=w_gap,
                            t_inner=t_inner,
                        ),
                        clip_h,
                    ],
                    center=True,
                )
            )
        )
    hp_spg = _at_hp_spg_clip(union()(hp_spg_children))

    # LPI hose, with a block on each side.
    lpi_children = [
        hose_clip(
            d_hose=lpi_hose_d,
            t_inner=t_inner,
            w_gap=w_gap,
            t_outer=t_outer,
            h=clip_h,
            fn=fn,
        )
    ]
    if blocks:
        lpi_children.append(
            rotate([0, 0, -lpi_block_angle])(
                translate([lpi_block_x, 0, 0])(
                    cube(
                        [
                            lpi_block_len,
                            hose_clip_total_dia(
                                d_hose=lpi_hose_d,
                                t_outer=t_outer,
                                w_gap=w_gap,
                                t_inner=t_inner,
                            ),
                            clip_h,
                        ],
                        center=True,
                    )
                )
            )
        )
        lpi_children.append(
            rotate([0, 0, lpi_block_angle])(
                translate([lpi_block_x, 0, 0])(
                    cube(
                        [
                            lpi_block_len,
                            hose_clip_total_dia(
                                d_hose=lpi_hose_d,
                                t_outer=t_outer,
                                w_gap=w_gap,
                                t_inner=t_inner,
                            ),
                            clip_h,
                        ],
                        center=True,
                    )
                )
            )
        )
    lpi = _at_lpi_clip(union()(lpi_children))

    return union()([inflator, hp_spg, lpi])


def _hose_keepouts(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    """Keep-out volumes for the three hoses, through the same placements."""
    return union()(
        [
            _at_inflator_clip(
                hose_clip_keepout(
                    d_hose=inflator_tube_d,
                    t_inner=t_inner,
                    w_gap=w_gap,
                    t_outer=t_outer,
                    h=clip_h,
                    fn=fn,
                )
            ),
            _at_hp_spg_clip(
                hose_clip_keepout(
                    d_hose=hp_spg_hose_d,
                    t_inner=t_inner,
                    w_gap=w_gap,
                    t_outer=t_outer,
                    h=clip_h,
                    fn=fn,
                )
            ),
            _at_lpi_clip(
                hose_clip_keepout(
                    d_hose=lpi_hose_d,
                    t_inner=t_inner,
                    w_gap=w_gap,
                    t_outer=t_outer,
                    h=clip_h,
                    fn=fn,
                )
            ),
        ]
    )


def inflator_spg_combo_clip(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    """The whole combo: three hose clips plus their connecting blocks."""
    return union()(
        [
            _hose_clips_and_blocks(blocks=False, fn=fn),
            difference()(
                [
                    _hose_clips_and_blocks(blocks=True, fn=fn),
                    _hose_keepouts(fn=fn),
                ]
            ),
        ]
    )
