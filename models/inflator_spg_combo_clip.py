"""Inflator + SPG combo clip: bundles the three left-side hoses of a rig.
Fits the BCD inflator tube, the LPI hose and the HP/SPG hose. The hose sizes
and this part's tuning come from lib/config.py.

The three hose clips sit at the corners of the hose triangle. The config gives
the three centre distances that make that triangle; the model solves the angle
at the inflator clip with the law of cosines and splays the two satellite clips
symmetrically about the inflator clip's axis. No clip angle is configured.

Render:
    uv run tools/render.py models/inflator_spg_combo_clip.py build
"""

from __future__ import annotations

from math import acos, degrees, sqrt
from typing import Final

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.config import CONFIG, hose_clip_total_diameter
from lib.scad import OpenSCADObjectPlus
from lib.standoff import hose_clip_on_standoff

EXPECTED_REGIONS: Final = 1


def _spread_angle() -> float:
    """The angle at the inflator clip, from the triangle of centre distances.

    The HP/SPG clip and the LPI clip are `hp_spg_lpi_clip_distance` apart, so the
    law of cosines gives the angle between them at the inflator. The two
    satellite clips sit at plus and minus half of that angle, so the triangle
    is symmetric about the inflator clip's axis.
    """
    clip_config = CONFIG.inflator_spg_combo_clip
    hp_spg_clip_distance = clip_config.hp_spg_clip_distance
    lpi_clip_distance = clip_config.lpi_clip_distance
    hp_spg_lpi_clip_distance = clip_config.hp_spg_lpi_clip_distance
    if (
        hp_spg_clip_distance <= 0
        or lpi_clip_distance <= 0
        or hp_spg_lpi_clip_distance <= 0
    ):
        raise ValueError(
            "inflator_spg_combo_clip: the triangle distances must be positive"
        )
    if (
        hp_spg_lpi_clip_distance >= hp_spg_clip_distance + lpi_clip_distance
        or hp_spg_clip_distance >= lpi_clip_distance + hp_spg_lpi_clip_distance
        or lpi_clip_distance >= hp_spg_clip_distance + hp_spg_lpi_clip_distance
    ):
        raise ValueError(
            "inflator_spg_combo_clip: the triangle distances cannot close a triangle"
        )
    cosine = (
        hp_spg_clip_distance * hp_spg_clip_distance
        + lpi_clip_distance * lpi_clip_distance
        - hp_spg_lpi_clip_distance * hp_spg_lpi_clip_distance
    ) / (2 * hp_spg_clip_distance * lpi_clip_distance)
    return degrees(acos(max(-1.0, min(1.0, cosine))))


def inflator_spg_combo_clip() -> OpenSCADObjectPlus:
    """The whole combo: three hose clips plus their standoff arms.

    The inflator clip sits on the origin. The HP/SPG and LPI clips sit at their
    configured centre distances, splayed by plus and minus half of the triangle
    angle, and each carries a standoff arm whose base reaches the inflator clip.
    """
    clip_config = CONFIG.inflator_spg_combo_clip
    hardware = CONFIG.hardware
    library = CONFIG.library
    if not 0 <= clip_config.standoff_flare_percent <= 100:
        raise ValueError(
            "inflator_spg_combo_clip: standoff_flare_percent must be between 0 and 100"
        )
    grip_length = clip_config.clip_grip_length
    spread = _spread_angle()
    # The fit walls of every clip in this part.
    tongue_wall_thickness = library.clip_tongue_wall_thickness
    radial_gap = library.clip_radial_gap
    backbone_wall_thickness = library.clip_backbone_wall_thickness
    inflator_clip_diameter = hose_clip_total_diameter(
        hardware.inflator_tube_diameter,
        backbone_wall_thickness,
        radial_gap,
        tongue_wall_thickness,
    )

    def bare_clip(hose_diameter: float) -> OpenSCADObjectPlus:
        """One bare hose clip, at the fit walls above."""
        return hose_clip(
            hose_diameter=hose_diameter,
            tongue_wall_thickness=tongue_wall_thickness,
            radial_gap=radial_gap,
            backbone_wall_thickness=backbone_wall_thickness,
            height=grip_length,
        )

    def keepout(hose_diameter: float) -> OpenSCADObjectPlus:
        """Keep-out volume for one hose, at the fit walls above."""
        return hose_clip_keepout(
            hose_diameter=hose_diameter,
            tongue_wall_thickness=tongue_wall_thickness,
            radial_gap=radial_gap,
            backbone_wall_thickness=backbone_wall_thickness,
            height=grip_length,
        )

    def standoff_clip(hose_diameter: float, distance: float) -> OpenSCADObjectPlus:
        """One hose clip on a standoff arm that reaches the inflator clip centre.

        The arm runs along -X, back toward the inflator, and `origin="center"`
        puts the clip's centre on the placement point, so the caller places a
        triangle corner and the arm points home. `standoff_flare_percent` widens
        the arm toward the inflator; at 100 percent the base is the chord of the
        inflator clip circle on the base plane, so the arm lands on the large
        clip edge.
        """
        clip_diameter = hose_clip_total_diameter(
            hose_diameter, backbone_wall_thickness, radial_gap, tongue_wall_thickness
        )
        standoff_height = distance - clip_diameter / 2
        if standoff_height < 0:
            raise ValueError(
                "inflator_spg_combo_clip: a clip is closer to the inflator than "
                "its standoff can reach"
            )
        # The arm base sits one clip radius from the inflator centre, so at 100
        # percent its width is the chord where that plane cuts the inflator clip
        # circle. The arm edges then land exactly on the big clip, with no step.
        flare_base_width = sqrt(
            inflator_clip_diameter * inflator_clip_diameter
            - clip_diameter * clip_diameter
        )
        base_diameter = clip_diameter + (clip_config.standoff_flare_percent / 100) * (
            flare_base_width - clip_diameter
        )
        return hose_clip_on_standoff(
            height=grip_length,
            hose_diameter=hose_diameter,
            standoff_height=standoff_height,
            origin="center",
            base_diameter=base_diameter,
            tongue_wall_thickness=tongue_wall_thickness,
            radial_gap=radial_gap,
            backbone_wall_thickness=backbone_wall_thickness,
        ).rotate(0, 0, -90)

    # Placements. The inflator clip faces back, and each satellite clip sits
    # `distance` from the inflator clip centre, splayed half the triangle angle
    # to one side of the inflator clip's axis.
    def at_inflator_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
        """Placement of the BCD inflator tube clip, opposite the other two."""
        return child.rotate(0, 0, 180)

    def at_hp_spg_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
        """Placement of the HP/SPG hose clip, above the inflator clip's axis."""
        return child.translate(clip_config.hp_spg_clip_distance, 0, 0).rotate(
            0, 0, spread / 2
        )

    def at_lpi_clip(child: OpenSCADObjectPlus) -> OpenSCADObjectPlus:
        """Placement of the LPI hose clip, below the inflator clip's axis."""
        return child.translate(clip_config.lpi_clip_distance, 0, 0).rotate(
            0, 0, spread / -2
        )

    # The three clips in their three roles: bare, on the standoff arm, and as
    # the keep-out volume that trims that arm. The standoff clips minus the
    # keep-outs remove the clips themselves, which sit inside their own
    # envelopes, so the bare clips add them back.
    inflator_clip = at_inflator_clip(bare_clip(hardware.inflator_tube_diameter))

    clips_with_standoffs = (
        inflator_clip
        + at_hp_spg_clip(
            standoff_clip(hardware.spg_hose_diameter, clip_config.hp_spg_clip_distance)
        )
        + at_lpi_clip(
            standoff_clip(
                hardware.lp_inflator_hose_diameter,
                clip_config.lpi_clip_distance,
            )
        )
    )
    keepout_volumes = (
        at_inflator_clip(keepout(hardware.inflator_tube_diameter))
        + at_hp_spg_clip(keepout(hardware.spg_hose_diameter))
        + at_lpi_clip(keepout(hardware.lp_inflator_hose_diameter))
    )
    return clips_with_standoffs - keepout_volumes
