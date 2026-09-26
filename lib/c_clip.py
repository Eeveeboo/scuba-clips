"""C-shaped hose clips: the sharp and rounded rings, the two-opening ring, and
the assembled `hose_clip`.

`hose_clip` is four parts, one inside the other: the flexible tongue (the inner
C), the ring in the radial gap, the stiff backbone, and the two arms that join
the tongue tips to the backbone. A relief cut then frees the tongue.

Every builder here builds centred on the origin. The caller translates.
"""

from __future__ import annotations

from lib.config import CONFIG, hose_clip_base_diameter, hose_clip_total_diameter
from lib.scad import (
    OpenSCADObjectPlus,
    cylinder,
)
from lib.shapes import pie_wedge, tapered_arm


def _rounded_lip(
    half_opening_angle: float,
    centreline_radius: float,
    head_diameter: float,
    height: float,
) -> OpenSCADObjectPlus:
    """One rounded lip at the end of a C opening: `half_opening_angle` is the
    half opening, `centreline_radius` the lip centreline, `head_diameter` the lip
    head diameter, halved here, so the lip is half as thick as the ring wall."""
    return (
        cylinder(d=head_diameter / 2, h=height, center=True)
        .translate(centreline_radius, 0, 0)
        .rotate(0, 0, half_opening_angle)
    )


def c_ring_sharp(
    inner_diameter: float,
    outer_diameter: float,
    opening_angle: float,
    height: float,
) -> OpenSCADObjectPlus:
    """Ring with one angular opening and sharp lips; the C-clip primitive."""
    if not (inner_diameter > 0 and outer_diameter > inner_diameter):
        raise ValueError("c_ring_sharp: need 0 < inner_diameter < outer_diameter")
    if not (opening_angle > 0 and opening_angle < 360):
        raise ValueError("c_ring_sharp: opening_angle must be in (0, 360)")
    if height <= 0:
        raise ValueError("c_ring_sharp: height must be positive")

    ring = cylinder(d=outer_diameter, h=height, center=True) - cylinder(
        d=inner_diameter, h=height + 1, center=True
    )
    return ring - pie_wedge(outer_diameter, opening_angle, height + 1)


def c_ring_rounded(
    inner_diameter: float,
    outer_diameter: float,
    opening_angle: float,
    height: float,
) -> OpenSCADObjectPlus:
    """`c_ring_sharp` with both lips rounded."""
    lip_radius = (inner_diameter + outer_diameter) / 4
    lip_diameter = outer_diameter - inner_diameter

    def lip(half_opening_angle: float) -> OpenSCADObjectPlus:
        """The rounded lip `half_opening_angle` off the +X axis."""
        return _rounded_lip(half_opening_angle, lip_radius, lip_diameter, height)

    return (
        c_ring_sharp(
            inner_diameter=inner_diameter,
            outer_diameter=outer_diameter,
            opening_angle=opening_angle,
            height=height,
        )
        + lip(opening_angle / 2)
        + lip(-opening_angle / 2)
    )


def c_ring_rounded_two_openings(
    inner_diameter: float,
    outer_diameter: float,
    front_opening_angle: float,
    back_opening_angle: float,
    height: float,
) -> OpenSCADObjectPlus:
    """Ring with two openings and four rounded lips: `front_opening_angle` at the
    front (+X) and `back_opening_angle` at the back (-X)."""
    if not (inner_diameter > 0 and outer_diameter > inner_diameter):
        raise ValueError(
            "c_ring_rounded_two_openings: need 0 < inner_diameter < outer_diameter"
        )
    if not (front_opening_angle > 0 and front_opening_angle < 360):
        raise ValueError(
            "c_ring_rounded_two_openings: front_opening_angle must be in (0, 360)"
        )
    if not (back_opening_angle > 0 and back_opening_angle < 360):
        raise ValueError(
            "c_ring_rounded_two_openings: back_opening_angle must be in (0, 360)"
        )
    if height <= 0:
        raise ValueError("c_ring_rounded_two_openings: height must be positive")

    ring = cylinder(d=outer_diameter, h=height, center=True)
    ring -= cylinder(d=inner_diameter, h=height + 1, center=True)
    ring -= pie_wedge(outer_diameter, front_opening_angle, height + 1)
    ring -= pie_wedge(outer_diameter, back_opening_angle, height + 1).rotate(0, 0, 180)

    lip_radius = (inner_diameter + outer_diameter) / 4
    lip_diameter = outer_diameter - inner_diameter

    def lip(half_opening_angle: float) -> OpenSCADObjectPlus:
        """The rounded lip `half_opening_angle` off the +X axis."""
        return _rounded_lip(half_opening_angle, lip_radius, lip_diameter, height)

    back_lips = (lip(back_opening_angle / 2) + lip(-back_opening_angle / 2)).rotate(
        0, 0, 180
    )
    front_lips = lip(front_opening_angle / 2) + lip(-front_opening_angle / 2)
    return ring + front_lips + back_lips


def hose_clip(
    hose_diameter: float = 12,
    backbone_wall_thickness: float = 3,
    radial_gap: float = 3,
    tongue_wall_thickness: float = 1.5,
    tongue_back_angle: float = CONFIG.hardware.tongue_back_angle,
    backbone_front_angle: float = CONFIG.hardware.backbone_front_angle,
    opening_angle_offset: float = CONFIG.hardware.opening_angle_offset,
    height: float = 10,
) -> OpenSCADObjectPlus:
    """One hose clip, centred on the origin. `tongue_back_angle` is the tongue
    opening at the back (-X), `backbone_front_angle` the backbone opening at the
    front (+X), and `opening_angle_offset` the extra front opening of the tongue
    and of the relief cut. The angle defaults come from the `[hardware]` config
    section."""
    if not (
        hose_diameter > 0
        and backbone_wall_thickness > 0
        and radial_gap > 0
        and tongue_wall_thickness > 0
        and height > 0
    ):
        raise ValueError(
            "hose_clip: hose_diameter, backbone_wall_thickness, radial_gap, "
            "tongue_wall_thickness and height must be positive"
        )
    if not (backbone_front_angle > 0 and backbone_front_angle < 360):
        raise ValueError("hose_clip: backbone_front_angle must be in (0, 360)")
    if not (tongue_back_angle > 0 and tongue_back_angle < 360):
        raise ValueError("hose_clip: tongue_back_angle must be in (0, 360)")
    if opening_angle_offset < 0:
        raise ValueError("hose_clip: opening_angle_offset must not be negative")
    if not (backbone_front_angle + opening_angle_offset + tongue_back_angle < 360):
        raise ValueError("hose_clip: the front and back openings must leave material")

    base_diameter = hose_clip_base_diameter(hose_diameter, tongue_wall_thickness)
    tongue_front_angle = backbone_front_angle + opening_angle_offset
    # Mid-wall radii of the tongue and the backbone: the two ends of each arm.
    tongue_mid_radius = (base_diameter - tongue_wall_thickness / 2) / 2
    backbone_mid_radius = (base_diameter + radial_gap + backbone_wall_thickness / 2) / 2

    # The four parts of the body, one inside the other.
    body = c_ring_rounded_two_openings(
        inner_diameter=base_diameter - tongue_wall_thickness,
        outer_diameter=base_diameter,
        front_opening_angle=tongue_front_angle,
        back_opening_angle=tongue_back_angle,
        height=height,
    )
    body += c_ring_rounded_two_openings(
        inner_diameter=base_diameter,
        outer_diameter=base_diameter + radial_gap,
        front_opening_angle=tongue_front_angle,
        back_opening_angle=tongue_back_angle,
        height=height,
    )
    body += c_ring_rounded(
        inner_diameter=base_diameter + radial_gap,
        outer_diameter=base_diameter + radial_gap + backbone_wall_thickness,
        opening_angle=backbone_front_angle,
        height=height,
    )
    arm = tapered_arm(
        inner_angle=tongue_front_angle / 2,
        inner_radius=tongue_mid_radius,
        inner_width=tongue_wall_thickness,
        outer_angle=backbone_front_angle / 2,
        outer_radius=backbone_mid_radius,
        outer_width=backbone_wall_thickness,
        height=height,
    )
    body += arm + arm.mirror(0, 1, 0)
    # Relief cut: a rounded C over the radial gap at the front arc, one unit
    # taller than the part. It is wider than the tongue opening, so only the
    # arms hold the tongue and the tongue can flex.
    return body - c_ring_rounded(
        inner_diameter=base_diameter,
        outer_diameter=base_diameter + radial_gap,
        opening_angle=tongue_front_angle + opening_angle_offset,
        height=height + 1,
    )


def hose_clip_keepout(
    hose_diameter: float = 12,
    backbone_wall_thickness: float = 3,
    radial_gap: float = 3,
    tongue_wall_thickness: float = 1.5,
    tongue_back_angle: float = CONFIG.hardware.tongue_back_angle,
    backbone_front_angle: float = CONFIG.hardware.backbone_front_angle,
    opening_angle_offset: float = CONFIG.hardware.opening_angle_offset,
    height: float = 10,
) -> OpenSCADObjectPlus:
    """Keep-out volume for one hose clip: the full envelope cylinder plus a front
    wedge of `backbone_front_angle` degrees.

    `tongue_back_angle` and `opening_angle_offset` are unused: they are accepted
    for symmetry with `hose_clip`, so a caller passes one argument list to a part
    and to its keep-out volume. Do not remove them; they do not change this
    volume."""
    if not (
        hose_diameter > 0
        and backbone_wall_thickness > 0
        and radial_gap > 0
        and tongue_wall_thickness > 0
        and height > 0
    ):
        raise ValueError(
            "hose_clip_keepout: hose_diameter, backbone_wall_thickness, radial_gap, "
            "tongue_wall_thickness and height must be positive"
        )
    if not (backbone_front_angle > 0 and backbone_front_angle < 360):
        raise ValueError("hose_clip_keepout: backbone_front_angle must be in (0, 360)")

    clip_total_diameter = hose_clip_total_diameter(
        hose_diameter, backbone_wall_thickness, radial_gap, tongue_wall_thickness
    )

    rough_keepout = cylinder(
        h=height + 1, r=clip_total_diameter / 2, center=True
    ) + pie_wedge(clip_total_diameter, backbone_front_angle, height + 1)

    return rough_keepout - hose_clip(
        hose_diameter=hose_diameter,
        backbone_wall_thickness=backbone_wall_thickness,
        radial_gap=radial_gap,
        tongue_wall_thickness=tongue_wall_thickness,
        tongue_back_angle=tongue_back_angle,
        backbone_front_angle=backbone_front_angle,
        opening_angle_offset=opening_angle_offset,
        height=height + 1,
    )
