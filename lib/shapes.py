"""Reusable solid shapes for the clip library. No builder here positions
anything: each builds centred on the origin and the caller applies
translate/rotate.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from lib.config import CONFIG
from lib.scad import (
    OpenSCADObjectPlus,
    cylinder,
    hull,
    linear_extrude,
    polygon,
    rotate_extrude,
    sphere,
    square,
    union,
)


def rounded_cube(
    size: float | Sequence[float],
    radius: float = 0.5,
    center: bool = False,
    apply_to: str = "all",
) -> OpenSCADObjectPlus:
    """Solid box with selected edges rounded; upstream `roundedcube` semantics.

    `apply_to` picks the rounded edges: "all", a face ("xmin" .. "zmax"), or an
    axis ("x"/"y"/"z") for the four edges parallel to that axis. The body is the
    hull of one sphere per selected corner and one cylinder per remaining
    corner, so the selected edges are the only rounded ones.

    The upstream file-wide `$fs = 0.01` never reached callers, so it stays gone.
    """
    size_vector = [size, size, size] if isinstance(size, (int, float)) else list(size)
    if len(size_vector) != 3:
        raise ValueError("rounded_cube: size must be a number or a 3-element vector")
    if radius < 0:
        raise ValueError("rounded_cube: radius must not be negative")
    if not (
        2 * radius <= size_vector[0]
        and 2 * radius <= size_vector[1]
        and 2 * radius <= size_vector[2]
    ):
        raise ValueError("rounded_cube: radius must not exceed half of any size axis")
    # A typo here would silently round the wrong edges, so check the name.
    if apply_to not in (
        "all",
        "xmin",
        "xmax",
        "ymin",
        "ymax",
        "zmin",
        "zmax",
        "x",
        "y",
        "z",
    ):
        raise ValueError(
            "rounded_cube: apply_to must be all, xmin, xmax, ymin, ymax, "
            "zmin, zmax, x, y, or z"
        )

    # Corner centres: radius in from each face. Side 0 is the low end of an
    # axis, side 1 the high end. A corner on the face that `apply_to` names gets
    # a sphere, so the edges of that face round; every other corner gets a
    # cylinder along the edge it belongs to.
    low_corner = [radius, radius, radius]
    high_corner = [size - radius for size in size_vector]
    corner_diameter = 2 * radius
    faces = (("xmin", "xmax"), ("ymin", "ymax"), ("zmin", "zmax"))
    # Rotation that puts a cylinder's axis on the axis `apply_to` names.
    axis_rotation = (
        [0, 90, 0]
        if apply_to in ("xmin", "xmax", "x")
        else [90, 90, 0]
        if apply_to in ("ymin", "ymax", "y")
        else [0, 0, 0]
    )

    # Keep the three nested loops, in x, y, z order: the corner order sets the
    # hull. Each loop level is one union, as the SCAD `for` groups are, because
    # the hull triangulates differently for a flat list of eight children.
    x_groups: list[OpenSCADObjectPlus] = []
    for x_index in (0, 1):
        y_groups: list[OpenSCADObjectPlus] = []
        for y_index in (0, 1):
            z_solids: list[OpenSCADObjectPlus] = []
            for z_index in (0, 1):
                corner_position = [
                    low_corner[0] if x_index == 0 else high_corner[0],
                    low_corner[1] if y_index == 0 else high_corner[1],
                    low_corner[2] if z_index == 0 else high_corner[2],
                ]
                on_rounded_face = (
                    apply_to == "all"
                    or apply_to == faces[0][x_index]
                    or apply_to == faces[1][y_index]
                    or apply_to == faces[2][z_index]
                )
                if on_rounded_face:
                    z_solids.append(sphere(r=radius).translate(corner_position))
                else:
                    z_solids.append(
                        cylinder(
                            h=corner_diameter,
                            r=radius,
                            center=True,
                        )
                        .rotate(axis_rotation)
                        .translate(corner_position)
                    )
            y_groups.append(union()(z_solids))
        x_groups.append(union()(y_groups))

    centre_offset = (
        [-size_vector[0] / 2, -size_vector[1] / 2, -size_vector[2] / 2]
        if center
        else [0, 0, 0]
    )
    return hull()(union()(x_groups)).translate(centre_offset)


def pie_wedge(
    radius: float,
    wedge_angle: float,
    height: float,
) -> OpenSCADObjectPlus:
    """Solid wedge of `wedge_angle` degrees, symmetric about +X, centred on Z;
    the clip uses it to open a C."""
    if radius <= 0:
        raise ValueError("pie_wedge: radius must be positive")
    if not (wedge_angle > 0 and wedge_angle <= 360):
        raise ValueError("pie_wedge: wedge_angle must be in (0, 360]")
    if height <= 0:
        raise ValueError("pie_wedge: height must be positive")

    return (
        rotate_extrude(angle=wedge_angle)(square([radius, height]))
        .rotate(0, 0, wedge_angle / -2)
        .translate(0, 0, height / -2)
    )


def tapered_arm(
    inner_angle: float,
    inner_radius: float,
    inner_width: float,
    outer_angle: float,
    outer_radius: float,
    outer_width: float,
    height: float,
) -> OpenSCADObjectPlus:
    """Straight arm of `height` from a point on the `inner_radius` circle at
    angle `inner_angle` to a point on the `outer_radius` circle at angle
    `outer_angle`; the end sections `inner_width` and `outer_width` make the arm
    taper."""
    if height <= 0:
        raise ValueError("tapered_arm: height must be positive")

    inner_point = [
        inner_radius * math.cos(math.radians(inner_angle)),
        inner_radius * math.sin(math.radians(inner_angle)),
    ]
    outer_point = [
        outer_radius * math.cos(math.radians(outer_angle)),
        outer_radius * math.sin(math.radians(outer_angle)),
    ]
    delta_x = outer_point[0] - inner_point[0]
    delta_y = outer_point[1] - inner_point[1]
    # OpenSCAD's `norm` is sqrt(x*x + y*y), so do not use math.hypot.
    arm_length = math.sqrt(delta_x * delta_x + delta_y * delta_y)
    if not arm_length > CONFIG.library.dimensional_resolution:
        raise ValueError("tapered_arm: inner and outer points must be distinct")
    # Unit perpendicular to the arm.
    perpendicular = [-delta_y / arm_length, delta_x / arm_length]

    points = [
        (
            inner_point[0] + perpendicular[0] * (inner_width),
            inner_point[1] + perpendicular[1] * (inner_width),
        ),
        (
            inner_point[0] + perpendicular[0] * (-inner_width / 4),
            inner_point[1] + perpendicular[1] * (-inner_width / 4),
        ),
        (
            outer_point[0] + perpendicular[0] * (-outer_width / 4),
            outer_point[1] + perpendicular[1] * (-outer_width / 4),
        ),
        (
            outer_point[0] + perpendicular[0] * (outer_width / 4),
            outer_point[1] + perpendicular[1] * (outer_width / 4),
        ),
    ]
    return linear_extrude(height=height, center=True)(polygon(points=points))
