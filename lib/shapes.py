"""Reusable solid shapes for the clip library. No builder here positions
anything: each builds centred on the origin and the caller applies
translate/rotate.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from solid2 import (
    OpenSCADObjectPlus,
    cylinder,
    hull,
    linear_extrude,
    polygon,
    rotate,
    rotate_extrude,
    sphere,
    square,
    translate,
    union,
)

from lib.params import DEFAULT_FN, EPS


def rounded_cube(
    size: float | Sequence[float],
    radius: float = 0.5,
    center: bool = False,
    apply_to: str = "all",
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Solid box with selected edges rounded; upstream `roundedcube` semantics.

    `apply_to` picks the rounded edges: "all", a face ("xmin" .. "zmax"), or an
    axis ("x"/"y"/"z") for the four edges parallel to that axis. The body is the
    hull of one sphere per selected corner and one cylinder per remaining
    corner, so the selected edges are the only rounded ones.

    The upstream file-wide `$fs = 0.01` never reached callers, so it stays gone.
    """
    s = [size, size, size] if isinstance(size, (int, float)) else list(size)
    if len(s) != 3:
        raise ValueError("rounded_cube: size must be a number or a 3-element vector")
    if radius < 0:
        raise ValueError("rounded_cube: radius must not be negative")
    if not (2 * radius <= s[0] and 2 * radius <= s[1] and 2 * radius <= s[2]):
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

    # Corner centres: radius in from each face.
    lo = [radius, radius, radius]
    hi = [s[0] - radius, s[1] - radius, s[2] - radius]
    diameter = 2 * radius
    # Rotation that puts a cylinder's axis on the axis `apply_to` names.
    axis_rotate = (
        [0, 90, 0]
        if apply_to in ("xmin", "xmax", "x")
        else [90, 90, 0]
        if apply_to in ("ymin", "ymax", "y")
        else [0, 0, 0]
    )

    # Keep the three nested loops, in x, y, z order: the corner order sets the
    # hull. Each loop level is one union, as the SCAD `for` groups are, because
    # the hull triangulates differently for a flat list of eight children.
    xi_groups: list[OpenSCADObjectPlus] = []
    for xi in (0, 1):
        yi_groups: list[OpenSCADObjectPlus] = []
        for yi in (0, 1):
            zi_solids: list[OpenSCADObjectPlus] = []
            for zi in (0, 1):
                point = _corner_point(lo, hi, xi, yi, zi)
                if _corner_is_rounded(xi, yi, zi, apply_to):
                    zi_solids.append(translate(point)(sphere(r=radius, _fn=fn)))
                else:
                    zi_solids.append(
                        translate(point)(
                            rotate(axis_rotate)(
                                cylinder(h=diameter, r=radius, center=True, _fn=fn)
                            )
                        )
                    )
            yi_groups.append(union()(zi_solids))
        xi_groups.append(union()(yi_groups))

    offset = [-s[0] / 2, -s[1] / 2, -s[2] / 2] if center else [0, 0, 0]
    return translate(offset)(hull()(union()(xi_groups)))


def _corner_point(
    lo: Sequence[float], hi: Sequence[float], xi: int, yi: int, zi: int
) -> list[float]:
    """Corner position: side 0 is the low end of an axis, 1 the high end."""
    return [
        lo[0] if xi == 0 else hi[0],
        lo[1] if yi == 0 else hi[1],
        lo[2] if zi == 0 else hi[2],
    ]


def _corner_is_rounded(xi: int, yi: int, zi: int, apply_to: str) -> bool:
    """True when this corner sits on the face that `apply_to` names; those
    corners get a sphere, so the edges of that face are rounded. "all" rounds
    every one."""
    faces = (("xmin", "xmax"), ("ymin", "ymax"), ("zmin", "zmax"))
    return (
        apply_to == "all"
        or apply_to == faces[0][xi]
        or apply_to == faces[1][yi]
        or apply_to == faces[2][zi]
    )


def pie_wedge(
    radius: float, angle: float, height: float, fn: int = DEFAULT_FN
) -> OpenSCADObjectPlus:
    """Solid wedge of `angle` degrees, symmetric about +X, centred on Z; the
    clip uses it to open a C."""
    if radius <= 0:
        raise ValueError("pie_wedge: radius must be positive")
    if not (angle > 0 and angle <= 360):
        raise ValueError("pie_wedge: angle must be in (0, 360]")
    if height <= 0:
        raise ValueError("pie_wedge: height must be positive")

    return translate([0, 0, height / -2])(
        rotate([0, 0, angle / -2])(
            rotate_extrude(angle=angle, _fn=fn)(square([radius, height]))
        )
    )


def tapered_arm(
    a_inner: float,
    r_inner: float,
    w_inner: float,
    a_outer: float,
    r_outer: float,
    w_outer: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Straight arm of `height` from a point on the `r_inner` circle at angle
    `a_inner` to a point on the `r_outer` circle at angle `a_outer`; the end
    sections `w_inner` and `w_outer` make the arm taper."""
    if height <= 0:
        raise ValueError("tapered_arm: height must be positive")

    p1 = [
        r_inner * math.cos(math.radians(a_inner)),
        r_inner * math.sin(math.radians(a_inner)),
    ]
    p2 = [
        r_outer * math.cos(math.radians(a_outer)),
        r_outer * math.sin(math.radians(a_outer)),
    ]
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    # OpenSCAD's `norm` is sqrt(x*x + y*y), so do not use math.hypot.
    length = math.sqrt(dx * dx + dy * dy)
    if not length > EPS:
        raise ValueError("tapered_arm: inner and outer points must be distinct")
    n = [-dy / length, dx / length]  # unit perpendicular to the arm

    points = [
        (p1[0] + n[0] * (w_inner), p1[1] + n[1] * (w_inner)),
        (p1[0] + n[0] * (-w_inner / 4), p1[1] + n[1] * (-w_inner / 4)),
        (p2[0] + n[0] * (-w_outer / 4), p2[1] + n[1] * (-w_outer / 4)),
        (p2[0] + n[0] * (w_outer / 4), p2[1] + n[1] * (w_outer / 4)),
    ]
    return linear_extrude(height=height, center=True)(polygon(points=points))
