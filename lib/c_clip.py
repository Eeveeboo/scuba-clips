"""C-shaped hose clips: the sharp and rounded rings, the two-opening ring, and
the assembled `hose_clip`.

Structure of `hose_clip`, from the inside out: the flexible `_flex_tongue`,
the `_gap_ring` in the radial gap, the `_tongue_flex_relief` that frees the
tongue, the stiff `_outer_backbone`, and the `_tongue_link_arms`, which join
the tongue tips to the backbone.

Every builder here builds centred on the origin. The caller translates.
"""

from __future__ import annotations

from solid2 import (
    OpenSCADObjectPlus,
    cylinder,
    difference,
    mirror,
    rotate,
    translate,
    union,
)

from lib.params import DEFAULT_FN, hose_clip_base_dia, hose_clip_total_dia
from lib.shapes import pie_wedge, tapered_arm


def _rounded_lip(
    angle: float, radius: float, diameter: float, height: float, fn: int = DEFAULT_FN
) -> OpenSCADObjectPlus:
    """One rounded lip at the end of a C opening: `angle` is the half opening,
    `radius` the lip centreline, `diameter` the head (halved again here, so the
    lip is half as thick as the ring wall)."""
    return rotate([0, 0, angle])(
        translate([radius, 0, 0])(
            cylinder(d=diameter / 2, h=height, center=True, _fn=fn)
        )
    )


def c_ring_sharp(
    id: float, od: float, angle: float, height: float, fn: int = DEFAULT_FN
) -> OpenSCADObjectPlus:
    """Ring with one angular opening and sharp lips; the C-clip primitive."""
    if not (id > 0 and od > id):
        raise ValueError("c_ring_sharp: need 0 < id < od")
    if not (angle > 0 and angle < 360):
        raise ValueError("c_ring_sharp: angle must be in (0, 360)")
    if height <= 0:
        raise ValueError("c_ring_sharp: height must be positive")

    ring = difference()(
        [
            cylinder(d=od, h=height, center=True, _fn=fn),
            cylinder(d=id, h=height + 1, center=True, _fn=fn),
        ]
    )
    return difference()([ring, pie_wedge(od, angle, height + 1, fn=fn)])


def c_ring_rounded(
    id: float, od: float, angle: float, height: float, fn: int = DEFAULT_FN
) -> OpenSCADObjectPlus:
    """`c_ring_sharp` with both lips rounded."""
    return union()(
        [
            c_ring_sharp(id=id, od=od, angle=angle, height=height, fn=fn),
            _rounded_lip(angle / 2, (id + od) / 4, od - id, height, fn=fn),
            _rounded_lip(-angle / 2, (id + od) / 4, od - id, height, fn=fn),
        ]
    )


def c_ring_rounded_two_openings(
    id: float,
    od: float,
    angle_a: float,
    angle_b: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Ring with two openings and four rounded lips: `angle_a` at the front (+X)
    and `angle_b` at the back (-X)."""
    if not (id > 0 and od > id):
        raise ValueError("c_ring_rounded_two_openings: need 0 < id < od")
    if not (angle_a > 0 and angle_a < 360):
        raise ValueError("c_ring_rounded_two_openings: angle_a must be in (0, 360)")
    if not (angle_b > 0 and angle_b < 360):
        raise ValueError("c_ring_rounded_two_openings: angle_b must be in (0, 360)")
    if height <= 0:
        raise ValueError("c_ring_rounded_two_openings: height must be positive")

    ring = difference()(
        [
            cylinder(d=od, h=height, center=True, _fn=fn),
            cylinder(d=id, h=height + 1, center=True, _fn=fn),
        ]
    )
    ring = difference()(
        [
            ring,
            pie_wedge(od, angle_a, height + 1, fn=fn),
            rotate([0, 0, 180])(pie_wedge(od, angle_b, height + 1, fn=fn)),
        ]
    )

    return union()(
        [
            ring,
            _rounded_lip(angle_a / 2, (id + od) / 4, od - id, height, fn=fn),
            _rounded_lip(-angle_a / 2, (id + od) / 4, od - id, height, fn=fn),
            rotate([0, 0, 180])(
                union()(
                    [
                        _rounded_lip(
                            angle_b / 2, (id + od) / 4, od - id, height, fn=fn
                        ),
                        _rounded_lip(
                            -angle_b / 2, (id + od) / 4, od - id, height, fn=fn
                        ),
                    ]
                )
            ),
        ]
    )


# --- The parts of `hose_clip` ---


def _flex_tongue(
    base_diameter: float,
    t_inner: float,
    a_inner_front: float,
    a_inner_back: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Flexible tongue: the inner C, `base_diameter - t_inner` .. `base_diameter`."""
    return c_ring_rounded_two_openings(
        id=base_diameter - t_inner,
        od=base_diameter,
        angle_a=a_inner_front,
        angle_b=a_inner_back,
        height=height,
        fn=fn,
    )


def _gap_ring(
    base_diameter: float,
    w_gap: float,
    a_inner_front: float,
    a_inner_back: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """The ring in the radial gap, from `base_diameter` to
    `base_diameter + w_gap`. `_tongue_flex_relief` thins it, so it does not
    bridge tongue and backbone."""
    return c_ring_rounded_two_openings(
        id=base_diameter,
        od=base_diameter + w_gap,
        angle_a=a_inner_front,
        angle_b=a_inner_back,
        height=height,
        fn=fn,
    )


def _outer_backbone(
    base_diameter: float,
    t_outer: float,
    w_gap: float,
    a_outer_front: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Stiff backbone: one rounded C from `base_diameter + w_gap` outward."""
    return c_ring_rounded(
        id=base_diameter + w_gap,
        od=base_diameter + w_gap + t_outer,
        angle=a_outer_front,
        height=height,
        fn=fn,
    )


def _tongue_link_arms(
    base_diameter: float,
    t_inner: float,
    t_outer: float,
    w_gap: float,
    a_inner_front: float,
    a_outer_front: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Two mirror-symmetric arms that join the tongue tips to the backbone."""
    r_tongue = (base_diameter - t_inner / 2) / 2  # mid-wall of the tongue
    r_backbone = (base_diameter + w_gap + t_outer / 2) / 2  # mid-wall of the backbone

    return union()(
        [
            tapered_arm(
                a_inner=a_inner_front / 2,
                r_inner=r_tongue,
                w_inner=t_inner,
                a_outer=a_outer_front / 2,
                r_outer=r_backbone,
                w_outer=t_outer,
                height=height,
                fn=fn,
            ),
            mirror((0, 1, 0))(
                tapered_arm(
                    a_inner=a_inner_front / 2,
                    r_inner=r_tongue,
                    w_inner=t_inner,
                    a_outer=a_outer_front / 2,
                    r_outer=r_backbone,
                    w_outer=t_outer,
                    height=height,
                    fn=fn,
                )
            ),
        ]
    )


def _tongue_flex_relief(
    base_diameter: float,
    w_gap: float,
    a_inner_front: float,
    a_offset: float,
    height: float,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Relief cut: a rounded C over `base_diameter` .. `base_diameter + w_gap` at
    the front arc `a_inner_front + a_offset`, one unit taller than the part. It
    is wider than the tongue opening, so only the arms hold the tongue: it can
    flex."""
    return c_ring_rounded(
        id=base_diameter,
        od=base_diameter + w_gap,
        angle=a_inner_front + a_offset,
        height=height + 1,
        fn=fn,
    )


def hose_clip(
    d_hose: float = 12,
    t_outer: float = 3,
    w_gap: float = 3,
    t_inner: float = 1.5,
    a_inner_back: float = 60,
    a_outer_front: float = 90,
    a_offset: float = 15,
    h: float = 10,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """One hose clip, centred on the origin. `a_inner_back` is the tongue opening
    at the back (-X), `a_outer_front` the backbone opening at the front (+X), and
    `a_offset` the extra front opening of the tongue and of the relief cut.

    The defaults here differ from the ones in params.py on purpose: this fit is
    hand-tuned, so do not unify them."""
    if not (d_hose > 0 and t_outer > 0 and w_gap > 0 and t_inner > 0 and h > 0):
        raise ValueError(
            "hose_clip: d_hose, t_outer, w_gap, t_inner and h must be positive"
        )
    if not (a_outer_front > 0 and a_outer_front < 360):
        raise ValueError("hose_clip: a_outer_front must be in (0, 360)")
    if not (a_inner_back > 0 and a_inner_back < 360):
        raise ValueError("hose_clip: a_inner_back must be in (0, 360)")
    if a_offset < 0:
        raise ValueError("hose_clip: a_offset must not be negative")
    if not (a_outer_front + a_offset + a_inner_back < 360):
        raise ValueError("hose_clip: the front and back openings must leave material")

    base_diameter = hose_clip_base_dia(d_hose, t_inner)
    a_inner_front = a_outer_front + a_offset

    body = union()(
        [
            _flex_tongue(
                base_diameter=base_diameter,
                t_inner=t_inner,
                a_inner_front=a_inner_front,
                a_inner_back=a_inner_back,
                height=h,
                fn=fn,
            ),
            _gap_ring(
                base_diameter=base_diameter,
                w_gap=w_gap,
                a_inner_front=a_inner_front,
                a_inner_back=a_inner_back,
                height=h,
                fn=fn,
            ),
            _outer_backbone(
                base_diameter=base_diameter,
                t_outer=t_outer,
                w_gap=w_gap,
                a_outer_front=a_outer_front,
                height=h,
                fn=fn,
            ),
            _tongue_link_arms(
                base_diameter=base_diameter,
                t_inner=t_inner,
                t_outer=t_outer,
                w_gap=w_gap,
                a_inner_front=a_inner_front,
                a_outer_front=a_outer_front,
                height=h,
                fn=fn,
            ),
        ]
    )
    return difference()(
        [
            body,
            _tongue_flex_relief(
                base_diameter=base_diameter,
                w_gap=w_gap,
                a_inner_front=a_inner_front,
                a_offset=a_offset,
                height=h,
                fn=fn,
            ),
        ]
    )


def hose_clip_keepout(
    d_hose: float = 12,
    t_outer: float = 3,
    w_gap: float = 3,
    t_inner: float = 1.5,
    a_inner_back: float = 60,
    a_outer_front: float = 90,
    a_offset: float = 15,
    h: float = 10,
    fn: int = DEFAULT_FN,
) -> OpenSCADObjectPlus:
    """Keep-out volume for one hose clip: the full envelope cylinder plus a front
    wedge of `a_outer_front` degrees.

    `a_inner_back` and `a_offset` are unused: they are accepted for symmetry with
    `hose_clip`, so a caller passes one argument list to a part and to its
    keep-out volume. Do not remove them; they do not change this volume."""
    if not (d_hose > 0 and t_outer > 0 and w_gap > 0 and t_inner > 0 and h > 0):
        raise ValueError(
            "hose_clip_keepout: d_hose, t_outer, w_gap, t_inner and h must be positive"
        )
    if not (a_outer_front > 0 and a_outer_front < 360):
        raise ValueError("hose_clip_keepout: a_outer_front must be in (0, 360)")

    total_diameter = hose_clip_total_dia(d_hose, t_outer, w_gap, t_inner)

    return union()(
        [
            cylinder(h=h + 1, r=total_diameter / 2, center=True, _fn=fn),
            pie_wedge(total_diameter, a_outer_front, h + 1, fn=fn),
        ]
    )
