"""Upper octopus retaining clip: hose standoff clips on a strap block that grips
the shoulder webbing. It holds the 18.5 mm regulator fitting and one 12.5 mm MP
hose; the shoulder webbing size comes from constants/hardware.py.

Draft render:
    uv run tools/render.py models/upper_octi_retaining_clip.py build/draft --draft
"""

from __future__ import annotations

from typing import Final

from solid2 import (
    OpenSCADObjectPlus,
    cube,
    difference,
    linear_extrude,
    mirror,
    polygon,
    rotate,
    translate,
    union,
)

from constants.hardware import hose_mp_dia, hose_reg_fitting_dia, webbing_shoulder_size
from lib.params import default_t_outer
from lib.shapes import rounded_cube
from lib.standoff import hose_clip_on_standoff

MODEL_FN: int = 100
EXPECTED_REGIONS: Final = 1

# The strap block that carries the webbing: the webbing plus one wall on each
# side, at the standoff wall thickness.
strap: Final = webbing_shoulder_size  # [width, thickness] of the shoulder webbing
w_strap: Final = strap[0]  # width along the webbing
t_strap: Final = strap[1]  # thickness across the webbing
t_outer: Final = default_t_outer()  # standoff wall thickness; the block's side wall
tt: Final = t_strap + t_outer * 2  # strap block thickness
tw: Final = w_strap + t_outer * 2  # strap block width

strap_block_h: Final = 50  # height of the webbing strap block
webbing_slot_h: Final = 63  # vertical slot the webbing passes through

clip_bottom_z: Final = -31  # z of the lower face of both octi clips
reg_clip_h: Final = 15  # height of the regulator-fitting clip
reg_clip_standoff: Final = 18  # regulator-fitting clip distance from the webbing
hose_clip_h: Final = 10  # height of the MP-hose clip
hose_clip_standoff: Final = 0  # MP-hose clip rests on the webbing

# Flared slit, so the webbing can be pushed in from the side.
slit_inner_half: Final = t_strap * 1.25  # slit half width at the webbing
slit_outer_half: Final = t_strap * 8  # slit half width at the flared ends
slit_flare_start: Final = 5  # z where the slit starts to flare
slit_angle: Final = -25  # tilt of the slit cutter
slit_thickness: Final = t_outer + 1  # Y thickness of the slit cutter
slit_y_offset: Final = t_strap + 0.5  # lift, so the slit cuts the near wall
slit_length: Final = 100  # Z length of the slit cutter

# The regulator-fitting clip sits on one side only; the MP-hose clip is
# mirrored, and both standoffs shift 6 mm in +X (the old alignment = -6).
#
# `offset` is a displacement in millimetres along +X, applied to the standoff
# that otherwise hangs off the strap block's left edge at x = -tw / 2.
# offset = 0 is the old alignment = "outer"; the old alignment = -6 is
# offset = +6.
offset: Final = 6


def strap_block_hose_clip(
    h: float, tube_d: float, standoff_h: float, fn: int = MODEL_FN
) -> OpenSCADObjectPlus:
    """One standoff hose clip on a strap block. The webbing passage is cut by
    the caller, so this builder is the part only."""
    if h <= 0:
        raise ValueError("strap_block_hose_clip: h must be positive")
    if tube_d <= 0:
        raise ValueError("strap_block_hose_clip: tube_d must be positive")
    if standoff_h < 0:
        raise ValueError("strap_block_hose_clip: standoff_h must not be negative")
    if w_strap <= 0:
        raise ValueError("strap_block_hose_clip: w_strap must be positive")
    if t_strap <= 0:
        raise ValueError("strap_block_hose_clip: t_strap must be positive")

    return union()(
        [
            translate([tw / -2 + offset, standoff_h, 0])(
                hose_clip_on_standoff(
                    h=h, tube_d=tube_d, standoff_h=standoff_h + tt, fn=fn
                )
            ),
            # The strap block itself; the webbing opening is cut by the caller.
            translate([0, tt / -2, 0])(
                rounded_cube(
                    size=[tw, tt, h],
                    center=True,
                    radius=t_outer / 2,
                    apply_to="all",
                    fn=fn,
                )
            ),
        ]
    )


def _flared_webbing_slit(
    length: float,
    inner_half_width: float,
    outer_half_width: float,
    flare_start: float,
    thickness: float,
    angle: float,
    y_offset: float,
    fn: int = MODEL_FN,
) -> OpenSCADObjectPlus:
    """Flared slit cutter in the XZ plane (X = slit width, Z = slit length): a
    slot `inner_half_width` wide where the webbing rests, flaring to
    `outer_half_width` at both ends so the webbing can be pushed through.
    `flare_start` is where the flare begins; `thickness`, `angle` and `y_offset`
    shape it for the caller."""
    pts = [
        (-outer_half_width, -length / 2),  # bottom-left flare
        (inner_half_width, -length / 2),  # bottom-right inner edge
        (inner_half_width, -flare_start),
        (inner_half_width, flare_start),
        (outer_half_width, length / 2),  # top-right flare
        (-inner_half_width, length / 2),  # top-left inner edge
        (-inner_half_width, flare_start),
        (-inner_half_width, -flare_start),
    ]

    return translate([0, y_offset, 0])(
        rotate([0, angle, 0])(
            rotate([90, 0, 0])(
                linear_extrude(height=thickness, center=True)(polygon(points=pts))
            )
        )
    )


def upper_octi_retaining_clip(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    """The shoulder part: the regulator-fitting clip, its mirrored MP-hose clip,
    and the strap block, with the webbing passage cut through."""
    return difference()(
        [
            union()(
                [
                    translate([0, 0, clip_bottom_z + reg_clip_h / 2])(
                        strap_block_hose_clip(
                            h=reg_clip_h,
                            tube_d=hose_reg_fitting_dia,
                            standoff_h=reg_clip_standoff,
                            fn=fn,
                        )
                    ),
                    mirror((1, 0, 0))(
                        translate([0, 0, clip_bottom_z + hose_clip_h / 2])(
                            strap_block_hose_clip(
                                h=hose_clip_h,
                                tube_d=hose_mp_dia,
                                standoff_h=hose_clip_standoff,
                                fn=fn,
                            )
                        )
                    ),
                    translate([0, tt / -2, 0])(
                        rounded_cube(
                            size=[tw, tt, strap_block_h],
                            center=True,
                            radius=t_outer / 2,
                            apply_to="all",
                            fn=fn,
                        )
                    ),
                ]
            ),
            # The subtraction group: the webbing passage and the flared slit,
            # placed through one translate.
            union()(
                [
                    translate([0, tt / -2, 0])(
                        union()(
                            [
                                # Webbing passage through the whole strap block.
                                cube([w_strap, t_strap, webbing_slot_h], center=True),
                                # Flared slit, so the webbing can be pushed in
                                # from the side.
                                _flared_webbing_slit(
                                    length=slit_length,
                                    inner_half_width=slit_inner_half,
                                    outer_half_width=slit_outer_half,
                                    flare_start=slit_flare_start,
                                    thickness=slit_thickness,
                                    angle=slit_angle,
                                    y_offset=slit_y_offset,
                                    fn=fn,
                                ),
                            ]
                        )
                    ),
                ]
            ),
        ]
    )
