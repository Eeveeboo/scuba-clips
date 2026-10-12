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

import math
from math import degrees
from typing import Final

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.c_clip2 import pill3d
from lib.config import CONFIG
from lib.scad import OpenSCADObjectPlus

EXPECTED_REGIONS: Final = 1


def two_way_clip() -> OpenSCADObjectPlus:
    """The part: two standoff hose clips with their openings turned away from
    each other, their flared arms tapered together at the hub, and the cord hole
    through it."""
    clip_config = CONFIG.two_way_clip

    hose_1_diameter = clip_config.hose_1_diameter
    hose_2_diameter = clip_config.hose_2_diameter
    clip_center_distance = clip_config.clip_center_distance
    h = clip_config.clip_grip_length
    t = CONFIG.library.clip_backbone_wall_thickness + CONFIG.library.clip_tongue_wall_thickness + CONFIG.library.clip_radial_gap

    clip1 = hose_clip(hose_diameter=hose_1_diameter, height=h).translate(clip_center_distance/2,0,0)
    clip2 = hose_clip(hose_diameter=hose_2_diameter, height=h).rotate(180).translate(clip_center_distance/-2,0,0)
    clip1neg = hose_clip_keepout(hose_diameter=hose_1_diameter, height=h).translate(clip_center_distance/2,0,0)
    clip2neg = hose_clip_keepout(hose_diameter=hose_2_diameter, height=h).rotate(180).translate(clip_center_distance/-2,0,0)

    r1 = hose_1_diameter/2
    r2 = hose_2_diameter/2
    a = pill3d(h,t).translate(r1+(t/2),0,0).rotate(degrees(math.asin((r1-r2)/clip_center_distance)) + 90).translate(clip_center_distance/2,0,0)
    b = a.mirror(0,1,0)
    c = pill3d(h,t).translate(r2+(t/2),0,0).rotate(degrees(math.asin((r1-r2)/clip_center_distance)) + 90).translate(clip_center_distance/-2,0,0)
    d = c.mirror(0,1,0)

    clips = clip1 + clip2
    if clip_config.lattice_only:
        bridge = (a+c).hull() + (b+d).hull();
    else:
        bridge = (a+b+c+d).hull() - clip1neg - clip2neg

    return clips + bridge
