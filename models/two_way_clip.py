"""Two-way cord clip: keeps two hoses together and gives a cord a place to pass
through.

Each hose clip opens away from the other, so the pair sits 180 degrees apart.
Each clip sits on a standoff arm that flares to the centre, and the two arms
meet to form the hub with one taper from the larger hose to the smaller one. A
hole runs through that hub along the hose axis, so a cord or a zip tie can hold
the clip to a D-ring or a bolt snap. This part's tuning comes from
lib/config.py.

Render:
    uv run tools/render.py models/two_way_clip.py build
"""

from __future__ import annotations

from typing import Final

from lib.config import CONFIG, hose_clip_total_diameter
from lib.scad import OpenSCADObjectPlus, cylinder
from lib.standoff import hose_clip_on_standoff

EXPECTED_REGIONS: Final = 1


def two_way_clip() -> OpenSCADObjectPlus:
    """The part: two standoff hose clips with their openings turned away from
    each other, their flared arms tapered together at the hub, and the cord hole
    through it."""
    clip_config = CONFIG.two_way_clip
    library = CONFIG.library

    hose_1_diameter = clip_config.hose_1_diameter
    hose_2_diameter = clip_config.hose_2_diameter
    grip_length = clip_config.clip_grip_length
    clip_center_distance = clip_config.clip_center_distance
    cord_hole_diameter = clip_config.cord_hole_diameter
    backbone_wall_thickness = library.clip_backbone_wall_thickness

    if hose_1_diameter <= 0:
        raise ValueError("two_way_clip: hose_1_diameter must be positive")
    if hose_2_diameter <= 0:
        raise ValueError("two_way_clip: hose_2_diameter must be positive")
    if grip_length <= 0:
        raise ValueError("two_way_clip: clip_grip_length must be positive")
    if clip_center_distance <= 0:
        raise ValueError("two_way_clip: clip_center_distance must be positive")
    if cord_hole_diameter <= 0:
        raise ValueError("two_way_clip: cord_hole_diameter must be positive")

    clip_1_radius = hose_clip_total_diameter(hose_1_diameter) / 2
    clip_2_radius = hose_clip_total_diameter(hose_2_diameter) / 2
    # Each arm flares from its own clip to the hub. Both reach the same hub
    # width, halfway between the two clip widths, so the two tapers form one
    # straight taper from the larger clip to the smaller one.
    hub_width = clip_1_radius + clip_2_radius
    if cord_hole_diameter / 2 + backbone_wall_thickness > hub_width / 2:
        raise ValueError(
            "two_way_clip: the cord hole leaves too little wall in the hub"
        )
    if cord_hole_diameter / 2 + backbone_wall_thickness > grip_length / 2:
        raise ValueError(
            "two_way_clip: the cord hole leaves too little wall in the hub height"
        )

    # Each arm runs past the centre by the rounding radius, so its rounded base
    # edge is buried in the other arm. Without that overlap the two rounded base
    # edges meet at the centre and leave a groove, the divot seen from the side.
    overlap = library.standoff_rounding_radius

    def standoff_clip(hose_diameter: float) -> OpenSCADObjectPlus:
        """One standoff hose clip: its centre on the origin, its opening on +X
        and its arm flaring back along -X past the hub centre."""
        return hose_clip_on_standoff(
            height=grip_length,
            hose_diameter=hose_diameter,
            standoff_height=clip_center_distance + overlap,
            origin="center",
            base_diameter=hub_width,
            backbone_wall_thickness=backbone_wall_thickness,
            round_base=False,
        ).rotate(0, 0, -90)

    # The +X clip carries hose 1. The mirror turns the opening to -X and puts
    # the second clip on the -X side, so the pair is 180 degrees apart.
    clips = standoff_clip(hose_1_diameter).translate(clip_center_distance, 0, 0)
    clips += standoff_clip(hose_2_diameter).translate(
        clip_center_distance, 0, 0
    ).mirror(1, 0, 0)
    cord_hole = cylinder(h=grip_length + 1, d=cord_hole_diameter, center=True)

    return clips - cord_hole
