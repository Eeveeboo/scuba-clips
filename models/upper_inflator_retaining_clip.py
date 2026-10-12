"""Upper inflator retaining clip: the inflator tube clip on a strap block that
grips the shoulder webbing. The hose and webbing sizes, and this part's tuning,
come from lib/config.py.

Render:
    uv run tools/render.py models/upper_inflator_retaining_clip.py build
"""

from __future__ import annotations

from typing import Final

from lib.config import CONFIG, hose_clip_total_diameter
from lib.scad import OpenSCADObjectPlus, cube
from lib.shapes import rounded_cube
from lib.standoff import hose_clip_on_standoff
from lib.webbing import flared_webbing_slit

EXPECTED_REGIONS: Final = 1


def upper_inflator_retaining_clip() -> OpenSCADObjectPlus:
    clip_config = CONFIG.upper_inflator_retaining_clip
    hardware = CONFIG.hardware
    wall_thickness = CONFIG.library.webbing_wall_thickness

    # The strap block carries the webbing plus one wall on each side.
    webbing_width, webbing_thickness = hardware.webbing_shoulder_size
    block_thickness = webbing_thickness + wall_thickness * 2
    block_width = webbing_width + wall_thickness * 2

    # The webbing slot is a cutter: it must pass both faces of the strap block,
    # or the boolean cut leaves a coplanar face. The 1 mm overshoot is the same
    # one the lower octopus retaining clip uses.
    webbing_slot_height = clip_config.strap_block_height + 1

    strap_block = rounded_cube(
        size=[block_width, block_thickness, clip_config.strap_block_height],
        center=True,
        radius=wall_thickness,
        apply_to="all",
    )
    # Cutout where the webbing needs to go
    strap_block -= cube(
        size=[webbing_width, webbing_thickness, webbing_slot_height], center=True
    )

    inflator_clip_total_diameter = hose_clip_total_diameter(
        hardware.inflator_tube_diameter
    )
    # The clip is centred on its standoff base, so the base lifts by half the
    # grip length to put the clip's bottom edge flush with the block's bottom
    # edge.
    clip_base_z = (clip_config.clip_grip_length - clip_config.strap_block_height) / 2
    inflator_clip = hose_clip_on_standoff(
        height=clip_config.clip_grip_length,
        hose_diameter=hardware.inflator_tube_diameter,
        standoff_height=inflator_clip_total_diameter / 2 + wall_thickness,
        round_base=False,
    ).translate(0, block_thickness / 2, clip_base_z)

    return (
        strap_block
        + inflator_clip
        - flared_webbing_slit(
            webbing_width=webbing_width,
            webbing_thickness=webbing_thickness,
            strap_block_height=clip_config.strap_block_height,
            slit_tightness=clip_config.slit_tightness,
            slit_flare_start=clip_config.slit_flare_start,
            wall_thickness=wall_thickness,
        ).mirror(0, 1, 0)
    )
