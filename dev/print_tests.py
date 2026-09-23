"""Fit-test matrix for the C-clip: print a grid of clips across hose diameters
and gap widths, each on a grip block with an engraved label, and test how they
feel on the hose.

This is a dev tool and it renders many clips at once, so `print_tests` takes an
`fn` and the caller can render a draft:

    uv run python -m dev.print_tests 36 > build/scad/print_tests.scad
"""

from __future__ import annotations

import sys
from typing import Final

from solid2 import (
    OpenSCADObjectPlus,
    cube,
    difference,
    linear_extrude,
    scad_render,
    text,
    translate,
    union,
)

from lib.c_clip import hose_clip, hose_clip_keepout
from lib.params import hose_clip_total_dia

MODEL_FN: Final = 100

# Matrix axes: every hose diameter against every gap width.
hose_diameters: Final = [18, 19, 20, 27]  # mm; the last is the BCD inflator tube
w_gap_values: Final = [2, 3]  # mm; relief gap between the C walls
t_inner: Final = 2  # mm; clip inner wall thickness
t_outer: Final = 3  # mm; clip outer wall thickness

# Grip block behind each clip (old literals: 25 x 12 x 10 at x = -9).
grip_x: Final = -9  # X centre of the block, so it sticks out as a grip
grip_len: Final = 25  # X length of the block
grip_h: Final = 12  # Y height of the block
grip_depth: Final = 10  # Z depth of the block, and the clip length

# Grid layout and label placement (old literals: 40, +-2.5, 4.5, size 5).
pitch: Final = 40  # mm between matrix cells
label_size: Final = 5  # mm
label_x: Final = 1  # X anchor of the right-aligned label
label_y: Final = 2.5  # Y offset of each of the two label lines
label_h: Final = 1  # extrusion height of the label
# How far the label starts inside the block, so the label and the block overlap
# instead of touching face to face.
label_sink: Final = 0.5


# One fit-test clip on its grip block, with the hose kept out of the block.
def fit_test_clip(
    d_hose: float,
    t_inner: float,
    w_gap: float,
    t_outer: float,
    fn: int = MODEL_FN,
) -> OpenSCADObjectPlus:
    d = hose_clip_total_dia(
        d_hose=d_hose, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer
    )

    # One placement for the clip and its keep-out volume, so the part and the
    # cut that shapes it cannot drift apart.
    placement = [d / 2, 0, 0]

    # The grip block, with the hose kept out of it.
    block = difference()(
        translate([grip_x, 0, 0])(cube([grip_len, grip_h, grip_depth], center=True)),
        translate(placement)(
            hose_clip_keepout(
                d_hose=d_hose,
                t_inner=t_inner,
                w_gap=w_gap,
                t_outer=t_outer,
                h=grip_depth,
                fn=fn,
            )
        ),
    )

    # The clip itself, centred on its own outside diameter.
    clip = translate(placement)(
        hose_clip(
            d_hose=d_hose,
            t_inner=t_inner,
            w_gap=w_gap,
            t_outer=t_outer,
            h=grip_depth,
            fn=fn,
        )
    )

    # A module body of two statements is an implicit union; keep it explicit.
    return union()(block, clip)


# Engraved label on the top face of the grip block. It starts inside the block
# so that the label and the block join by overlap.
def engraved_label(text_str: str, y: float, fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    return translate([label_x, y, grip_depth / 2 - label_sink])(
        linear_extrude(height=label_h)(
            text(
                text_str,
                size=label_size,
                font="Liberation Sans",
                halign="right",
                valign="center",
                _fn=fn,
            )
        )
    )


# The coupon grid: one clip per cell, plus its two engraved label lines.
def print_tests(fn: int = MODEL_FN) -> OpenSCADObjectPlus:
    cells: list[OpenSCADObjectPlus] = []
    for i, d_hose in enumerate(hose_diameters):
        for j, w_gap in enumerate(w_gap_values):
            children = [
                fit_test_clip(
                    d_hose=d_hose, t_inner=t_inner, w_gap=w_gap, t_outer=t_outer, fn=fn
                ),
                engraved_label(f"{d_hose}, {t_inner}", label_y, fn=fn),
                engraved_label(f"{w_gap}, {t_outer}", -label_y, fn=fn),
            ]
            cells.append(translate([j * pitch, i * pitch, 0])(union()(children)))
    return union()(cells)


if __name__ == "__main__":
    # A dev tool: `uv run python -m dev.print_tests [fn]` writes the source.
    fn = int(sys.argv[1]) if len(sys.argv) > 1 else MODEL_FN
    print(scad_render(print_tests(fn=fn)))
