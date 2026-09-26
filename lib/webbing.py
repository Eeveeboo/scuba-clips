"""Webbing cutters: the flared slit that lets the webbing into a retaining clip.
Shared by the upper octi and upper inflator clips.
"""

from __future__ import annotations

from math import atan, degrees

from lib.scad import OpenSCADObjectPlus, linear_extrude, polygon


def flared_webbing_slit(
    webbing_width: float,
    webbing_thickness: float,
    strap_block_height: float,
    slit_tightness: float,
    slit_flare_start: float,
    backbone_wall_thickness: float,
) -> OpenSCADObjectPlus:
    """Flared slit cutter in the XZ plane (X = slit width, Z = slit length),
    lifted to the webbing's near (+Y) face.

    The slot is `slit_tightness` wider than the webbing where the webbing rests,
    and it flares out to `webbing_width` at both ends so the webbing can be
    pushed in from the front. The slit runs `strap_block_height` twice over, so
    it cuts past both block faces, and that length also sets the flare slope:
    the flare reaches the webbing edge at `slit_length / 2`. The cutter tilts so
    the flare edge runs parallel to the webbing. Its Y thickness is
    `backbone_wall_thickness` plus a one-unit overshoot. The caller mirrors the
    cutter to cut the opposite face.
    """
    if webbing_width <= 0:
        raise ValueError("flared_webbing_slit: webbing_width must be positive")
    if webbing_thickness <= 0:
        raise ValueError("flared_webbing_slit: webbing_thickness must be positive")
    if strap_block_height <= 0:
        raise ValueError("flared_webbing_slit: strap_block_height must be positive")
    if slit_tightness < 0:
        raise ValueError("flared_webbing_slit: slit_tightness must not be negative")
    if backbone_wall_thickness <= 0:
        raise ValueError(
            "flared_webbing_slit: backbone_wall_thickness must be positive"
        )

    slit_length = strap_block_height * 2
    if not 0 < slit_flare_start < slit_length / 2:
        raise ValueError(
            "flared_webbing_slit: slit_flare_start must be between 0 and half "
            "the slit length"
        )

    inner_half_width = (webbing_thickness + slit_tightness) / 2
    outer_half_width = webbing_width / 2
    tilt_angle = -degrees(
        atan(
            (outer_half_width - inner_half_width) / (slit_length / 2 - slit_flare_start)
        )
    )
    thickness = backbone_wall_thickness + 1  # Y thickness of the cutter
    # Lift the cutter, so it meets the webbing at the webbing's near face.
    y_offset = (webbing_thickness + thickness) / 2

    points = [
        (-outer_half_width, -slit_length / 2),  # bottom-left flare
        (inner_half_width, -slit_length / 2),  # bottom-right inner edge
        (inner_half_width, -slit_flare_start),
        (inner_half_width, slit_flare_start),
        (outer_half_width, slit_length / 2),  # top-right flare
        (-inner_half_width, slit_length / 2),  # top-left inner edge
        (-inner_half_width, slit_flare_start),
        (-inner_half_width, -slit_flare_start),
    ]

    return (
        linear_extrude(height=thickness, center=True)(polygon(points=points))
        .rotate(90, 0, 0)
        .rotate(0, tilt_angle, 0)
        .translate(0, y_offset, 0)
    )
