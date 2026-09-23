#!/usr/bin/env python3
"""Sanity-check a rendered PNG without looking at it.

Reports size, background uniformity, "ink" fraction (how much of the frame the
model covers) and prints a coarse ASCII preview so a text-only agent can verify
that a screenshot actually shows geometry.

Usage: png_check.py image.png [...] [--cols 78] [--rows 30] [--quiet]
                      [--components N]
Exit code 1 if an image is unreadable, blank, or clipped at the frame edge, or
if --components N is given and the image does not show exactly N separate
pieces of geometry.  A plate that should show four parts but resolves into two
silhouettes has hidden two of them behind the others.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

RAMP = " .:-=+*#%@"

INK_MIN = 0.02          # a frame with less ink than this shows (nearly) nothing
RANGE_MIN = 20          # a flat image has no shading to read the shape from
BORDER_MAX = 0.35       # touching the frame edge usually means --viewall clipped
BG_TOLERANCE = 12       # grey levels away from the background count as ink
REGION_TOLERANCE = 40   # stronger threshold for counting visible parts: it drops
                        # the anti-aliasing halo, which otherwise bridges two
                        # parts that do not touch
MIN_REGION = 0.003      # smaller regions than this fraction of the image are
                        # shading speckle, not a part


def regions(path, min_fraction=MIN_REGION):
    """Count the separate pieces of geometry in the image (4-connected ink)."""
    im = Image.open(path).convert("L")
    px = np.asarray(im, dtype=float)
    border = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    ink = np.abs(px - float(np.median(border))) > REGION_TOLERANCE
    h, w = ink.shape
    seen = np.zeros_like(ink)
    areas = []
    for start in zip(*np.where(ink & ~seen)):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        area = 0
        while stack:
            y, x = stack.pop()
            area += 1
            if y and ink[y - 1, x] and not seen[y - 1, x]:
                seen[y - 1, x] = True; stack.append((y - 1, x))
            if y + 1 < h and ink[y + 1, x] and not seen[y + 1, x]:
                seen[y + 1, x] = True; stack.append((y + 1, x))
            if x and ink[y, x - 1] and not seen[y, x - 1]:
                seen[y, x - 1] = True; stack.append((y, x - 1))
            if x + 1 < w and ink[y, x + 1] and not seen[y, x + 1]:
                seen[y, x + 1] = True; stack.append((y, x + 1))
        areas.append(area)
    return sorted([a for a in areas if a >= min_fraction * h * w], reverse=True)


def check(path, width, height, quiet, want_components=None):
    try:
        im = Image.open(path).convert("L")
    except (OSError, ValueError) as exc:
        print(f"== {path}  PROBLEMS: cannot read image: {exc}")
        return False
    px = np.asarray(im, dtype=float)
    small = np.asarray(im.resize((width, height)), dtype=float)
    # The background is the median of the frame edge, not of the whole frame: a
    # tightly cropped plate has more geometry than background, and there the
    # whole-frame median lands on a geometry shade (measured: 148 against a true
    # background of 248), which marks the background itself as ink.  The edge
    # ring is background by construction, as long as the model does not touch the
    # frame - and that case is a reported problem of its own.
    border = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    bg = float(np.median(border))
    mask = np.abs(small - bg) > BG_TOLERANCE
    ink = float(mask.mean())
    lo, hi = float(small.min()), float(small.max())
    edge = np.concatenate([mask[0], mask[-1], mask[:, 0], mask[:, -1]])
    parts = regions(path)
    problems = []
    if want_components is not None and len(parts) != want_components:
        problems.append(f"shows {len(parts)} separate piece(s) of geometry, expected {want_components}")
    if ink < INK_MIN:
        problems.append("nearly blank")
    if hi - lo < RANGE_MIN:
        problems.append("flat image")
    if edge.mean() > BORDER_MAX:
        problems.append("content spans the whole frame edge (model clipped?)")
    print(f"== {path}  {im.width}x{im.height}  {os.path.getsize(path)} bytes")
    print(f"   background={bg:.0f} range={lo:.0f}..{hi:.0f} ink_fraction={ink:.3f} "
          f"border_fill={edge.mean():.2f} regions={len(parts)}"
          + (f" (areas {', '.join(str(a) for a in parts[:6])})" if not quiet else "")
          + (f"  PROBLEMS: {', '.join(problems)}" if problems else "  ok"))
    if not quiet:
        for row in range(height):
            print("   " + "".join(
                RAMP[min(9, int((small[row, c] - lo) / (hi - lo + 1e-9) * 9.99))] if mask[row, c] else " "
                for c in range(width)
            ))
    return not problems


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--cols", type=int, default=78)
    ap.add_argument("--rows", type=int, default=30)
    ap.add_argument("--quiet", action="store_true", help="print the summary line only")
    ap.add_argument("--components", type=int, default=None,
                    help="fail unless the image shows exactly this many separate pieces of geometry")
    a = ap.parse_args()
    ok = all([check(p, a.cols, a.rows, a.quiet, a.components) for p in a.images])
    sys.exit(0 if ok else 1)
