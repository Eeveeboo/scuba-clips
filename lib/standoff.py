"""Standoff clip: one hose clip plus a block that reaches out to the webbing or
strap it is mounted against. Shared by the octi clips and the webbing side
clip.
"""

from __future__ import annotations

from math import sqrt

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.config import CONFIG, hose_clip_total_diameter
from lib.scad import (
    OpenSCADObjectPlus,
    cube,
    cylinder,
    linear_extrude,
    polygon,
)


def _at_clip_position(
    clip_diameter: float, child: OpenSCADObjectPlus
) -> OpenSCADObjectPlus:
    """Place a clip, or the keep-out volume that shapes it, at the clip's own
    position, so the part and the cut can never drift apart."""
    return child.translate(clip_diameter / 2, 0, 0).rotate(0, 0, 90)


def _flared_arm(
    clip_diameter: float,
    standoff_height: float,
    base_diameter: float,
    height: float,
) -> OpenSCADObjectPlus:
    """Arm that widens from the clip's diameter out to `base_diameter` at the
    mounting face.

    Each side edge is the line from the mounting-face corner that is tangent to
    the clip circle, so the arm and the clip share a tangent and leave no step.
    """
    clip_radius = clip_diameter / 2
    clip_centre_y = clip_radius
    base_face_y = clip_centre_y - standoff_height
    # Tangent from the base corner to the clip circle (centre
    # (0, clip_centre_y), radius clip_radius): the near-side touch point is at
    # `tangent_length` along the corner direction plus `tangent_offset`
    # perpendicular to it.
    corner_x = base_diameter / 2
    corner_y = base_face_y - clip_centre_y
    corner_distance = sqrt(corner_x * corner_x + corner_y * corner_y)
    unit_x = corner_x / corner_distance
    unit_y = corner_y / corner_distance
    tangent_length = clip_radius * clip_radius / corner_distance
    tangent_offset = (
        clip_radius
        * sqrt(corner_distance * corner_distance - clip_radius * clip_radius)
        / corner_distance
    )
    tangent_a_x = tangent_length * unit_x - tangent_offset * unit_y
    tangent_a_y = clip_centre_y + tangent_length * unit_y + tangent_offset * unit_x
    tangent_b_x = tangent_length * unit_x + tangent_offset * unit_y
    tangent_b_y = clip_centre_y + tangent_length * unit_y - tangent_offset * unit_x
    # The touch point on the +X side, which the trapezoid mirrors to -X.
    tangent_x, tangent_y = (
        (tangent_a_x, tangent_a_y)
        if tangent_a_x >= tangent_b_x
        else (tangent_b_x, tangent_b_y)
    )
    points = [
        (-base_diameter / 2, base_face_y),
        (base_diameter / 2, base_face_y),
        (tangent_x, tangent_y),
        (-tangent_x, tangent_y),
    ]
    return linear_extrude(height=height, center=True)(polygon(points=points))


def hose_clip_on_standoff(
    height: float,
    hose_diameter: float,
    standoff_height: float,
    origin: str = "base",
    base_diameter: float | None = None,
    tongue_wall_thickness: float = CONFIG.library.clip_tongue_wall_thickness,
    radial_gap: float = CONFIG.library.clip_radial_gap,
    backbone_wall_thickness: float = CONFIG.library.clip_backbone_wall_thickness,
    round_base: bool = True,
) -> OpenSCADObjectPlus:
    """`standoff_height` is the reach from the clip to the mounting face. The
    clip walls default to the library's fit values and accept named overrides.

    `origin` picks what sits on the origin, with the arm along -Y:
    `"base"` puts the standoff's clip-side base there (the caller positions the
    mounting face), and `"center"` puts the hose clip's centre there.

    `base_diameter` widens the arm into a flare: the arm is `clip_diameter` wide
    at the clip and `base_diameter` wide at the mounting face. `None` (or
    `clip_diameter`) is the straight arm."""
    if height <= 0:
        raise ValueError("hose_clip_on_standoff: height must be positive")
    if hose_diameter <= 0:
        raise ValueError("hose_clip_on_standoff: hose_diameter must be positive")
    if standoff_height < 0:
        raise ValueError("hose_clip_on_standoff: standoff_height must not be negative")
    if origin not in ("base", "center"):
        raise ValueError("hose_clip_on_standoff: origin must be 'base' or 'center'")
    if base_diameter is not None and base_diameter <= 0:
        raise ValueError("hose_clip_on_standoff: base_diameter must be positive")

    # Outside diameter of the hose clip; also the width of the standoff arm.
    clip_diameter = hose_clip_total_diameter(
        hose_diameter, backbone_wall_thickness, radial_gap, tongue_wall_thickness
    )
    clip_radius = clip_diameter / 2

    clip = _at_clip_position(
        clip_diameter,
        hose_clip(
            hose_diameter=hose_diameter,
            backbone_wall_thickness=backbone_wall_thickness,
            radial_gap=radial_gap,
            tongue_wall_thickness=tongue_wall_thickness,
            height=height,
        ),
    )

    # The standoff: a round boss at the far end, and an arm back to the clip. The
    # arm is straight at the clip's own width, or flared to `base_diameter` at
    # the mounting face.
    boss = cylinder(h=height, r=clip_radius, center=False).translate(
        0, -standoff_height + clip_radius, height / -2
    )
    if base_diameter is None or base_diameter == clip_diameter:
        arm = cube([clip_diameter, standoff_height, height], center=True).translate(
            0, clip_radius - standoff_height / 2, 0
        )
    else:
        arm = _flared_arm(
            clip_diameter=clip_diameter,
            standoff_height=standoff_height,
            base_diameter=base_diameter,
            height=height,
        )
    standoff = (boss + arm if round_base else arm) - _at_clip_position(
        clip_diameter,
        hose_clip_keepout(
            hose_diameter=hose_diameter,
            backbone_wall_thickness=backbone_wall_thickness,
            radial_gap=radial_gap,
            tongue_wall_thickness=tongue_wall_thickness,
            height=height,
        ),
    )

    part = clip + standoff
    if origin == "center":
        return part.translate(0, clip_diameter / -2, 0)
    return part
