"""Standoff clip: one hose clip plus a block that reaches out to the webbing or
strap it is mounted against. Shared by the octi clips and the webbing side
clip.
"""

from __future__ import annotations

from solid2 import (
    OpenSCADObjectPlus,
    cube,
    cylinder,
    difference,
    rotate,
    translate,
    union,
)

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.params import (
    DEFAULT_FN,
    default_t_inner,
    default_t_outer,
    default_w_gap,
    hose_clip_total_dia,
)


def _place_clip_and_keepout(d: float, child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
    """One placement for the clip and its keep-out volume, so the part and the
    cut that shapes it can never drift apart."""
    return rotate([0, 0, 90])(translate([d / 2, 0, 0])(child))


def hose_clip_on_standoff(
    h: float,
    tube_d: float,
    standoff_h: float,
    t_inner: float = default_t_inner(),
    w_gap: float = default_w_gap(),
    t_outer: float = default_t_outer(),
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """`standoff_h` is the reach from the clip to the mounting face. The clip
    walls default to the library's fit values and accept named overrides."""
    if h <= 0:
        raise ValueError("hose_clip_on_standoff: h must be positive")
    if tube_d <= 0:
        raise ValueError("hose_clip_on_standoff: tube_d must be positive")
    if standoff_h < 0:
        raise ValueError("hose_clip_on_standoff: standoff_h must not be negative")

    # Outside diameter of the hose clip; also the width of the standoff arm.
    d = hose_clip_total_dia(tube_d, t_outer, w_gap, t_inner)

    clip = _place_clip_and_keepout(
        d,
        hose_clip(
            d_hose=tube_d,
            t_outer=t_outer,
            w_gap=w_gap,
            t_inner=t_inner,
            h=h,
            fn=fn,
        ),
    )

    # Round boss at the far end of the standoff, and the flat arm from the clip
    # out to the boss.
    boss = translate([0, -standoff_h + d / 2, h / -2])(
        cylinder(h=h, r=d / 2, center=False, _fn=fn)
    )
    arm = translate([0, d / 2 - standoff_h / 2, 0])(
        cube([d, standoff_h, h], center=True)
    )
    standoff = difference()(
        [
            union()([boss, arm]),
            _place_clip_and_keepout(
                d,
                hose_clip_keepout(
                    d_hose=tube_d,
                    t_outer=t_outer,
                    w_gap=w_gap,
                    t_inner=t_inner,
                    h=h,
                    fn=fn,
                ),
            ),
        ]
    )

    return union()([clip, standoff])
