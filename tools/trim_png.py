#!/usr/bin/env python3
"""Trim a rendered PNG to the geometry it shows, with a margin. In place.

OpenSCAD's --viewall fits the bounding SPHERE of the model, so a wide flat part
gets a lot of background. Cropping to the ink bounding box (plus a margin) makes
the delivered plates read consistently tight without touching the camera.

The crop is idempotent: a second run finds the ink at the margin and keeps the
image as it is.

Usage: trim_png.py image.png [...] [--margin 45] [--dry-run]
"""
import argparse
import sys

import numpy as np
from PIL import Image

BG_TOLERANCE = 12   # grey levels away from the background count as ink


def trim(path, margin, dry_run):
    im = Image.open(path)
    grey = np.asarray(im.convert("L"), dtype=float)
    bg = float(np.median(grey))
    mask = np.abs(grey - bg) > BG_TOLERANCE
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        print(f"trim_png.py: {path}: no geometry found, left as is")
        return True
    x0 = max(0, int(cols[0]) - margin)
    x1 = min(im.width, int(cols[-1]) + 1 + margin)
    y0 = max(0, int(rows[0]) - margin)
    y1 = min(im.height, int(rows[-1]) + 1 + margin)
    if (x0, y0, x1, y1) == (0, 0, im.width, im.height):
        print(f"trim_png.py: {path}: {im.width}x{im.height} already tight")
        return True
    out = im.crop((x0, y0, x1, y1))
    print(f"trim_png.py: {path}: {im.width}x{im.height} -> {out.width}x{out.height} "
          f"(ink {int(cols[-1]) - int(cols[0]) + 1}x{int(rows[-1]) - int(rows[0]) + 1}, margin {margin})")
    if not dry_run:
        out.save(path)
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--margin", type=int, default=40, help="pixels of background kept on each side")
    ap.add_argument("--dry-run", action="store_true", help="report the crop, keep the file")
    a = ap.parse_args()
    if a.margin < 0:
        ap.error("--margin must not be negative")
    ok = True
    for p in a.images:
        try:
            ok = trim(p, a.margin, a.dry_run) and ok
        except (OSError, ValueError) as exc:
            print(f"trim_png.py: {p}: cannot read image: {exc}")
            ok = False
    sys.exit(0 if ok else 1)
