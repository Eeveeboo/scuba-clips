"""Shared defaults and dimension formulas for the clip library.

Assignments and functions only: importing this module executes nothing but
definitions.

The hardware this kit fits (hose diameters, webbing sizes) is not here; it
lives in constants/hardware.py, which each model reads.
"""

from typing import Final

DEFAULT_FN: Final = 100  # the old global $fn = 100, so tessellation is unchanged
EPS: Final = 0.01

# Clip wall sizes: one source of truth for the old file-level globals t_inner,
# w_gap and t_outer, so a tuned model and a standoff clip cannot disagree.


def default_t_inner() -> float:
    return 2


def default_w_gap() -> float:
    return 2


def default_t_outer() -> float:
    return 3


# Hose clip envelope. `d_hose` is the hose diameter, `t_inner` the flexible
# tongue wall, `w_gap` the radial gap, `t_outer` the structural outer wall.
def hose_clip_total_dia(
    d_hose: float, t_outer: float, w_gap: float, t_inner: float
) -> float:
    return d_hose + t_inner / 2 + w_gap + t_outer  # old `total_diameter`


def hose_clip_base_dia(d_hose: float, t_inner: float) -> float:
    return d_hose + t_inner / 2  # old `base_diameter`
