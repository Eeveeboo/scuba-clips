"""Lower octopus retaining clip: slides onto the hip webbing and holds one hose
on each side. The webbing and the hose sizes, and this part's tuning, come from
lib/config.py.

Render:
    uv run tools/render.py models/lower_octi_retaining_clip.py build
"""

from __future__ import annotations

from typing import Final

from lib.config import CONFIG
from lib.scad import OpenSCADObjectPlus, cube
from lib.shapes import rounded_cube
from lib.standoff import hose_clip_on_standoff
from lib.webbing import flared_webbing_slit

EXPECTED_REGIONS: Final = 1


def lower_octi_retaining_clip() -> OpenSCADObjectPlus:
    """The part: a rounded block with the webbing passage and the clearance slot
    cut through it, and one hose standoff clip on each side of the webbing."""
    clip_config = CONFIG.lower_octi_retaining_clip
    hardware = CONFIG.hardware

    # The block wall and the hose-clip wall are the same thickness, so one tuned
    # value tunes both.
    wall_thickness = CONFIG.library.webbing_wall_thickness
    block_height = clip_config.block_height
    webbing_clearance = clip_config.webbing_clearance
    clip_grip_length = clip_config.clip_grip_length
    hose_diameter = hardware.side_clip_hose_diameter
    webbing_width, webbing_thickness = hardware.webbing_hip_size

    # Derived sizes, so the block and the standoff cannot disagree.
    block_thickness = wall_thickness * 2 + webbing_thickness
    block_width = wall_thickness * 2 + webbing_width
    standoff_height = block_thickness

    if wall_thickness <= 0:
        raise ValueError("lower_octi_retaining_clip: wall_thickness must be positive")
    if webbing_thickness <= 0:
        raise ValueError(
            "lower_octi_retaining_clip: webbing_thickness must be positive"
        )
    if webbing_width <= 0:
        raise ValueError("lower_octi_retaining_clip: webbing_width must be positive")
    if block_height <= 0:
        raise ValueError("lower_octi_retaining_clip: block_height must be positive")
    if webbing_clearance < 0:
        raise ValueError(
            "lower_octi_retaining_clip: webbing_clearance must not be negative"
        )

    # Rounded block that carries the webbing.
    body = rounded_cube(
        size=[block_width, block_thickness, block_height],
        center=True,
        radius=wall_thickness,
        apply_to="all",
    )

    def standoff_clip(x: float) -> OpenSCADObjectPlus:
        """One standoff hose clip on the block's lower face at X = `x`. The clips
        span -block_height / 2 .. -block_height / 2 + clip_grip_length, so they
        are not centred in Z."""
        return hose_clip_on_standoff(
            height=clip_grip_length,
            hose_diameter=hose_diameter,
            standoff_height=standoff_height,
            backbone_wall_thickness=wall_thickness,
        ).translate(
            x,
            block_thickness / 2,
            -block_height / 2 + clip_grip_length / 2,
        )

    # One standoff clip on each side of the webbing.
    body += standoff_clip(block_width / 2)
    body += standoff_clip(block_width / -2)

    # The webbing passage through the block, plus a clearance slot at one end of
    # the block, so the webbing slides in.
    cuts = cube(
        size=[webbing_width, webbing_thickness, block_height + 1], center=True
    )

    if CONFIG.library.tpu_mode:
        cuts += flared_webbing_slit(
            webbing_width=webbing_width,
            webbing_thickness=webbing_thickness - 1,
            strap_block_height=block_height,
            slit_tightness=webbing_thickness,
            slit_flare_start=0.1,
            wall_thickness=wall_thickness,
        ).mirror(0, 1, 0)
    else:
        cuts += cube(
            size=[block_width, webbing_clearance, block_height + 1], center=True
        ).translate(block_width / -2, 0, 0)

    return body - cuts
