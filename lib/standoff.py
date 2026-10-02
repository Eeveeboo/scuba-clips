"""Standoff clip: one hose clip plus a block that reaches out to the webbing or
strap it is mounted against. Shared by the octi clips and the webbing side
clip.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

from lib.c_clip2 import hose_clip, hose_clip_keepout
from lib.config import CONFIG, hose_clip_total_diameter
from lib.scad import (
    OpenSCADObjectPlus,
    cylinder,
    hull,
    linear_extrude,
    offset,
    polygon,
    rotate_extrude,
    sphere,
    square,
    union,
)


def _at_clip_position(
    clip_diameter: float, child: OpenSCADObjectPlus
) -> OpenSCADObjectPlus:
    """Place a clip, or the keep-out volume that shapes it, at the clip's own
    position, so the part and the cut can never drift apart."""
    return child.translate(clip_diameter / 2, 0, 0).rotate(0, 0, 90)


def _inset_convex_polygon(
    points: Sequence[tuple[float, float]], radius: float
) -> list[tuple[float, float]]:
    """The convex polygon `points`, shrunk `radius` inward on every edge. Each
    new vertex is where two adjacent inset edge lines meet."""
    count = len(points)
    inset: list[tuple[float, float]] = []
    for index in range(count):
        previous = points[index - 1]
        current = points[index]
        following = points[(index + 1) % count]
        # Inward unit normals of the two edges that meet at this vertex.
        normal_in = _edge_normal(previous, current)
        normal_out = _edge_normal(current, following)
        # The inset line through `previous`/`current` is the edge moved along
        # its inward normal; the inset line through `current`/`following` is
        # likewise. Their intersection is the inset vertex.
        offset_in = (
            previous[0] + normal_in[0] * radius,
            previous[1] + normal_in[1] * radius,
        )
        offset_out = (
            current[0] + normal_out[0] * radius,
            current[1] + normal_out[1] * radius,
        )
        dx_in = current[0] - previous[0]
        dy_in = current[1] - previous[1]
        dx_out = following[0] - current[0]
        dy_out = following[1] - current[1]
        denominator = dx_in * dy_out - dy_in * dx_out
        if abs(denominator) < CONFIG.library.dimensional_resolution:
            inset.append((current[0] + normal_in[0] * radius, current[1] + normal_in[1] * radius))
            continue
        t = (
            (offset_out[0] - offset_in[0]) * dy_out
            - (offset_out[1] - offset_in[1]) * dx_out
        ) / denominator
        inset.append((offset_in[0] + t * dx_in, offset_in[1] + t * dy_in))
    return inset


def _edge_normal(
    start: tuple[float, float], end: tuple[float, float]
) -> tuple[float, float]:
    """The unit normal of an edge, turned towards the polygon's inside. The
    polygons here wind counter-clockwise, so that is the left normal."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = sqrt(dx * dx + dy * dy)
    return (-dy / length, dx / length)


def _rounded_edges_prism(
    points: Sequence[tuple[float, float]],
    height: float,
    radius: float,
) -> OpenSCADObjectPlus:
    """Extrude a convex, counter-clockwise polygon to `height` with its top and
    bottom edges rounded by `radius`, so no rim is sharp.

    A straight band keeps the full footprint over the middle of the height. Each
    cap is the convex hull of one sphere per vertex of the footprint inset by
    `radius`, at the height where the fillet begins: the hull meets the band at
    the full footprint and sweeps a quarter circle to the inset face. A zero or
    negative radius leaves the rims sharp.
    """
    if radius <= 0:
        return linear_extrude(height=height, center=True)(polygon(points=points))
    middle = linear_extrude(height=height - 2 * radius, center=True)(
        polygon(points=points)
    )
    inset = _inset_convex_polygon(points, radius)
    cap_z = height / 2 - radius
    top_caps = [sphere(r=radius).translate(x, y, cap_z) for x, y in inset]
    bottom_caps = [sphere(r=radius).translate(x, y, -cap_z) for x, y in inset]
    upper = hull()(union()(top_caps))
    lower = hull()(union()(bottom_caps))
    return middle + lower + upper


def _rounded_edges_cylinder(
    radius_xy: float,
    height: float,
    radius: float,
) -> OpenSCADObjectPlus:
    """A cylinder of `radius_xy` and `height`, its top and bottom rims rounded
    by `radius`. The axial cross-section is a rectangle with its two outer
    corners rounded and its inner edge left straight on the axis, so the top and
    bottom faces stay flat and meet flush at the centre.

    Rounding the inner corners too would pull the faces down at the axis and
    leave a divot; the axis edge must stay sharp."""
    if radius <= 0:
        return cylinder(h=height, r=radius_xy, center=True)
    # The cross-section lives at x >= 0, so the sweep makes a solid cylinder
    # rather than an annulus. Rounding every corner would pull the faces down
    # near the axis and leave a divot, so square the inner corner back up: only
    # the outer corner (x = radius_xy) keeps the fillet.
    section = offset(r=radius)(offset(delta=-radius)(square([radius_xy, height])))
    section += square([radius, height])
    return rotate_extrude()(section.translate(0, height / -2, 0))


def _flared_arm(
    clip_diameter: float,
    standoff_height: float,
    base_diameter: float,
    height: float,
    radius: float,
) -> OpenSCADObjectPlus:
    """Arm that widens from the clip's diameter out to `base_diameter` at the
    mounting face, with its top and bottom edges rounded by `radius`.

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
    return _rounded_edges_prism(points, height, radius)


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
    rounding_radius: float = CONFIG.library.standoff_rounding_radius,
) -> OpenSCADObjectPlus:
    """`standoff_height` is the reach from the clip to the mounting face. The
    clip walls default to the library's fit values and accept named overrides.

    `origin` picks what sits on the origin, with the arm along -Y:
    `"base"` puts the standoff's clip-side base there (the caller positions the
    mounting face), and `"center"` puts the hose clip's centre there.

    `base_diameter` widens the arm into a flare: the arm is `clip_diameter` wide
    at the clip and `base_diameter` wide at the mounting face. `None` (or
    `clip_diameter`) is the straight arm.

    `rounding_radius` rounds the standoff's top and bottom edges, so the arm and
    the base have no sharp rim. Zero leaves them sharp. The radius defaults from
    `[library] standoff_rounding_radius`."""
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
    if rounding_radius < 0:
        raise ValueError(
            "hose_clip_on_standoff: rounding_radius must not be negative"
        )

    # Outside diameter of the hose clip; also the width of the standoff arm.
    clip_diameter = hose_clip_total_diameter(
        hose_diameter, backbone_wall_thickness, radial_gap, tongue_wall_thickness
    )
    clip_radius = clip_diameter / 2
    # The fillet on the arm's top and bottom cannot eat more than the arm's
    # width, or the two fillets meet and the rim has no straight band left.
    if rounding_radius >= clip_radius:
        raise ValueError(
            "hose_clip_on_standoff: rounding_radius must be smaller than the "
            "clip radius"
        )
    if rounding_radius >= height / 2:
        raise ValueError(
            "hose_clip_on_standoff: rounding_radius must be smaller than half "
            "the clip height"
        )

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
    # the mounting face. Both are extruded with rounded top and bottom edges.
    base_face_y = clip_radius - standoff_height
    if base_diameter is None or base_diameter == clip_diameter:
        arm = _rounded_edges_prism(
            points=[
                (-clip_radius, base_face_y),
                (clip_radius, base_face_y),
                (clip_radius, clip_radius),
                (-clip_radius, clip_radius),
            ],
            height=height,
            radius=rounding_radius,
        )
    else:
        arm = _flared_arm(
            clip_diameter=clip_diameter,
            standoff_height=standoff_height,
            base_diameter=base_diameter,
            height=height,
            radius=rounding_radius,
        )
    standoff = arm
    if round_base:
        standoff += _rounded_edges_cylinder(
            radius_xy=clip_radius,
            height=height,
            radius=rounding_radius,
        ).translate(0, base_face_y, 0)
    standoff -= _at_clip_position(
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
