"""Upper octopus retaining clip: hose standoff clips on a strap block that grips
the shoulder webbing. The hose and webbing sizes, and this part's tuning, come
from lib/config.py.

Render:
    uv run tools/render.py models/upper_octi_retaining_clip.py build
"""

from __future__ import annotations

from typing import Final

from lib.config import CONFIG
from lib.scad import OpenSCADObjectPlus, cube
from lib.shapes import rounded_cube
from lib.standoff import hose_clip_on_standoff
from lib.webbing import flared_webbing_slit

EXPECTED_REGIONS: Final = 1


def upper_octi_retaining_clip() -> OpenSCADObjectPlus:
    """The shoulder part: the regulator-fitting clip, its mirrored LP
    regulator-hose clip, and the strap block, with the webbing passage cut
    through."""
    clip_config = CONFIG.upper_octi_retaining_clip
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

    # Both clips hang from the bottom of the webbing passage, so the hoses stay
    # clear of the webbing. The passage sits half the cutter overshoot below the
    # block, so the clip and block faces are never coplanar.
    clip_bottom_z = -webbing_slot_height / 2

    def strap_block(height: float) -> OpenSCADObjectPlus:
        """The rounded strap block, `height` tall, centred on the origin and
        against the webbing."""
        return rounded_cube(
            size=[block_width, block_thickness, height],
            center=True,
            radius=wall_thickness,
            apply_to="all",
        ).translate(0, block_thickness / -2, 0)

    def strap_block_hose_clip(
        height: float, hose_diameter: float, standoff_height: float
    ) -> OpenSCADObjectPlus:
        """One standoff hose clip with the block stub it stands on. The webbing
        passage is cut by the caller, so this builder is the part only."""
        if height <= 0:
            raise ValueError("strap_block_hose_clip: height must be positive")
        if hose_diameter <= 0:
            raise ValueError("strap_block_hose_clip: hose_diameter must be positive")
        if standoff_height < 0:
            raise ValueError(
                "strap_block_hose_clip: standoff_height must not be negative"
            )

        return hose_clip_on_standoff(
            height=height,
            hose_diameter=hose_diameter,
            standoff_height=standoff_height + block_thickness,
        ).translate(
            block_width / -2 + clip_config.standoff_offset, standoff_height, 0
        ) + strap_block(height)

    # The regulator-fitting clip sits on one side only; the LP regulator-hose
    # clip is mirrored, and both standoffs shift by `standoff_offset` in +X.
    body = strap_block_hose_clip(
        height=hardware.regulator_fitting_length,
        hose_diameter=hardware.regulator_fitting_diameter,
        standoff_height=clip_config.regulator_clip_standoff,
    ).translate(0, 0, clip_bottom_z + hardware.regulator_fitting_length / 2)
    body += (
        strap_block_hose_clip(
            height=clip_config.hose_clip_grip_length,
            hose_diameter=hardware.regulator_hose_diameter,
            standoff_height=clip_config.hose_clip_standoff,
        )
        .translate(0, 0, clip_bottom_z + clip_config.hose_clip_grip_length / 2)
        .mirror(1, 0, 0)
    )
    # The full-height strap block that carries the webbing. Each clip stub above
    # is a block at the clip's own height; this one sets the part's height.
    body += strap_block(clip_config.strap_block_height)

    # The cut: the webbing passage and the flared slit, placed as one group so
    # one translate moves both.
    webbing_cut = cube(
        [webbing_width, webbing_thickness, webbing_slot_height], center=True
    ) + flared_webbing_slit(
        webbing_width=webbing_width,
        webbing_thickness=webbing_thickness,
        strap_block_height=clip_config.strap_block_height,
        slit_tightness=clip_config.slit_tightness,
        slit_flare_start=clip_config.slit_flare_start,
        wall_thickness=wall_thickness,
    ).mirror(0, 1, 0)

    return body - webbing_cut.translate(0, block_thickness / -2, 0)
