from math import asin, degrees
from typing import Final

from lib.shapes import pie_wedge

EXPECTED_REGIONS: Final = 1

from lib.config import CONFIG
from lib.scad import OpenSCADObjectPlus, circle, cylinder, sphere, square


def _pill2d(h: float, t: float, eps: float = 0) -> OpenSCADObjectPlus:
    shape = square([t + eps, h - t], center=True)
    shape += circle(r=t/2).translate([0, (h - t) / 2])
    shape += circle(r=t/2).translate([0, (h - t) / -2])
    return shape


def _pill3d(h: float, t: float) -> OpenSCADObjectPlus:
    obj = cylinder(h=h - t, r=t / 2, center=True)
    obj += sphere(r=t/2).translate([0, 0, (h - t) / 2])
    obj += sphere(r=t/2).translate([0, 0, (h - t) / -2])
    return obj

def _inverse_capped_pill_arc(h: float, id: float, od: float, a: float, eps: float=0):
    t = (od - id) / 2
    obj = _pill2d(h, t, eps).translate([id / 2 + (t) / 2, 0, 0]).rotate_extrude(a)
    obj -= _pill3d(h, t).translate([id / 2 + t / 2, 0, 0])
    obj -= _pill3d(h, t).translate([id / 2 + t / 2, 0, 0]).rotate([0, 0, a])
    return obj.rotate(a / -2 + 180)

def _pill_arc(h: float, id: float, od: float, a: float):
    t = (od - id) / 2
    obj = _pill2d(h, t).translate([id / 2 + t / 2, 0, 0]).rotate_extrude(a)
    obj += _pill3d(h, t).translate([id / 2 + t / 2, 0, 0])
    obj += _pill3d(h, t).translate([id / 2 + t / 2, 0, 0]).rotate([0, 0, a])
    return obj.rotate(a / -2 + 180)


def __bridge_arm(
    h: float,
    tongue_id: float, tongue_od: float,
    backbone_id: float, backbone_od: float,
    a_tongue: float, a_backbone: float,
) -> OpenSCADObjectPlus:
    t_tongue = (tongue_od-tongue_id)/2
    tongue_slice = (
        _pill3d(h=h, t=t_tongue)
        .translate([tongue_id / 2 + t_tongue / 2, 0, 0])
        .rotate(a_tongue+180)
    )
    t_backbone = (backbone_od-backbone_id)/2
    backbone_slice = (
        _pill3d(h=h, t=t_backbone)
        .translate([backbone_id / 2 + t_backbone / 2, 0, 0])
        .rotate(a_backbone+180)
    )
    return (tongue_slice + backbone_slice).hull()

def _bridge_arm(
    h: float,
    tongue_id: float, tongue_od: float,
    backbone_id: float, backbone_od: float,
    a_tongue: float, a_backbone: float,
    arc: float,
) -> OpenSCADObjectPlus:
    return (
       __bridge_arm(h,tongue_id,tongue_od, backbone_id, backbone_od, a_tongue, a_backbone) +
       __bridge_arm(h,tongue_id,tongue_od, backbone_id, backbone_od, a_tongue-arc, a_backbone-arc)
    ).hull()

def hose_clip(
    hose_diameter: float = 12,
    backbone_wall_thickness: float = CONFIG.library.clip_backbone_wall_thickness,
    radial_gap: float = CONFIG.library.clip_radial_gap,
    tongue_wall_thickness: float = CONFIG.library.clip_tongue_wall_thickness,
    tongue_back_angle: float = CONFIG.hardware.tongue_back_angle,
    backbone_front_angle: float = CONFIG.hardware.backbone_front_angle,
    opening_angle_offset: float = CONFIG.hardware.opening_angle_offset,
    height: float = 10,
) -> OpenSCADObjectPlus:

    tongue_od = hose_diameter + tongue_wall_thickness*2
    backbone_id = tongue_od+radial_gap*2
    backbone_od = backbone_id + backbone_wall_thickness*2

    # The full-wall pill arc ends in a round "finger": the largest circle that
    # fits the wall, tangent to the hose and to the backbone's outer surface.
    # Its centre sits `finger_centre_radius` from the axis, so seen from the axis
    # the finger reaches `finger_half_angle` past the end of the straight arc and
    # into the opening. `backbone_front_angle` is the opening between the finger
    # tips, so shorten the arc by one finger half-angle at each end to put those
    # tips at the edge of the opening rather than the finger centres there.
    finger_radius = (backbone_od - hose_diameter) / 4
    finger_centre_radius = (hose_diameter / 2 + backbone_od / 2) / 2
    finger_half_angle = degrees(asin(finger_radius / finger_centre_radius))
    backbone_arc_a = 360 - backbone_front_angle - finger_half_angle * 2

    obj = _pill_arc(
        h=height,
        id=hose_diameter,
        od=backbone_od,
        a=backbone_arc_a,
    )

    if not CONFIG.library.tpu_mode:
        obj -= _pill_arc(
            h=height*2,
            id=tongue_od,
            od=backbone_id,
            a=backbone_arc_a - finger_half_angle*2
        )
        obj -= _inverse_capped_pill_arc(
            h=height*2,
            id=hose_diameter,
            od=tongue_od,
            a=tongue_back_angle,
            eps=radial_gap
        )

    return obj

def hose_clip_keepout(
    hose_diameter: float = 12,
    backbone_wall_thickness: float = CONFIG.library.clip_backbone_wall_thickness,
    radial_gap: float = CONFIG.library.clip_radial_gap,
    tongue_wall_thickness: float = CONFIG.library.clip_tongue_wall_thickness,
    tongue_back_angle: float = CONFIG.hardware.tongue_back_angle,
    backbone_front_angle: float = CONFIG.hardware.backbone_front_angle,
    opening_angle_offset: float = CONFIG.hardware.opening_angle_offset,
    height: float = 10,
) -> OpenSCADObjectPlus:
    clip_total_diameter = hose_diameter + tongue_wall_thickness*2 + radial_gap*2
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
        height=height,
    )
