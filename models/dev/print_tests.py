"""Fit-test matrix for the C-clip: print a grid of clips across hose diameters
and gap widths, each on a grip block with an engraved label, and test how they
feel on the hose.

This is a dev tool and it renders many clips at once: the detail comes from
`[library] tessellation_resolution` in config.toml, so a low value there
renders the matrix faster.

    uv run python -m models.dev.print_tests > build/print_tests.scad
"""

from __future__ import annotations

from typing import Final

import click

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.config import hose_clip_total_diameter
from lib.scad import (
    OpenSCADObjectPlus,
    cube,
    linear_extrude,
    scad_render,
    text,
    union,
)

# Matrix axes: every hose diameter against every gap width.
hose_diameters: Final = [18, 19, 20, 27]  # mm; the last is the BCD inflator tube
radial_gap_values: Final = [2, 3]  # mm; relief gap between the C walls
tongue_wall_thickness: Final = 2  # mm; clip inner wall thickness
backbone_wall_thickness: Final = 3  # mm; clip outer wall thickness

# Grip block behind each clip (old literals: 25 x 12 x 10 at x = -9).
grip_x: Final = -9  # X centre of the block, so it sticks out as a grip
grip_length: Final = 25  # X length of the block
grip_height: Final = 12  # Y height of the block
grip_depth: Final = 10  # Z depth of the block, and the clip length

# Grid layout and label placement (old literals: 40, +-2.5, 4.5, size 5).
pitch: Final = 40  # mm between matrix cells
label_size: Final = 5  # mm
label_x: Final = 1  # X anchor of the right-aligned label
label_y: Final = 2.5  # Y offset of each of the two label lines
label_height: Final = 1  # extrusion height of the label
# How far the label starts inside the block, so the label and the block overlap
# instead of touching face to face.
label_sink: Final = 0.5


def fit_test_clip(hose_diameter: float, radial_gap: float) -> OpenSCADObjectPlus:
    """One fit-test clip on its grip block, with the hose kept out of the block.

    The two wall thicknesses are fixed matrix settings, so they come from this
    module; only the two matrix axes are parameters.
    """
    clip_diameter = hose_clip_total_diameter(
        hose_diameter=hose_diameter,
        tongue_wall_thickness=tongue_wall_thickness,
        radial_gap=radial_gap,
        backbone_wall_thickness=backbone_wall_thickness,
    )

    # One placement for the clip and its keep-out volume, so the part and the
    # cut that shapes it cannot drift apart.
    placement = [clip_diameter / 2, 0, 0]

    # The grip block, with the hose kept out of it.
    block = cube([grip_length, grip_height, grip_depth], center=True).translate(
        grip_x, 0, 0
    ) - hose_clip_keepout(
        hose_diameter=hose_diameter,
        tongue_wall_thickness=tongue_wall_thickness,
        radial_gap=radial_gap,
        backbone_wall_thickness=backbone_wall_thickness,
        height=grip_depth,
    ).translate(placement)

    # The clip itself, centred on its own outside diameter.
    clip = hose_clip(
        hose_diameter=hose_diameter,
        tongue_wall_thickness=tongue_wall_thickness,
        radial_gap=radial_gap,
        backbone_wall_thickness=backbone_wall_thickness,
        height=grip_depth,
    ).translate(placement)

    # A module body of two statements is an implicit union; keep it explicit.
    return union()([block, clip])


def engraved_label(label_text: str, line_offset: float) -> OpenSCADObjectPlus:
    """Engraved label on the top face of the grip block. It starts inside the
    block, so the label and the block join by overlap."""
    return linear_extrude(height=label_height)(
        text(
            label_text,
            size=label_size,
            font="Liberation Sans",
            halign="right",
            valign="center",
        )
    ).translate(label_x, line_offset, grip_depth / 2 - label_sink)


def print_tests() -> OpenSCADObjectPlus:
    """The coupon grid: one clip per cell, plus its two engraved label lines."""
    cells: list[OpenSCADObjectPlus] = []
    for i, hose_diameter in enumerate(hose_diameters):
        for j, radial_gap in enumerate(radial_gap_values):
            cell = (
                fit_test_clip(hose_diameter=hose_diameter, radial_gap=radial_gap)
                + engraved_label(
                    f"{hose_diameter}, {tongue_wall_thickness}",
                    label_y,
                )
                + engraved_label(
                    f"{radial_gap}, {backbone_wall_thickness}",
                    -label_y,
                )
            )
            cells.append(cell.translate(j * pitch, i * pitch, 0))
    return union()(cells)


@click.command()
def main() -> None:
    """Write the fit-test plate source to stdout."""
    click.echo(scad_render(print_tests()))


if __name__ == "__main__":
    main()
