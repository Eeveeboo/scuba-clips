#!/usr/bin/env python3
"""Trim a rendered PNG to the geometry it shows, with a margin. In place.

OpenSCAD's --viewall fits the bounding SPHERE of the model, so a wide flat part
gets a lot of background. Cropping to the ink bounding box (plus a margin) makes
the delivered plates read consistently tight without touching the camera.

The crop is idempotent: a second run finds the ink at the margin and keeps the
image as it is.

Usage: trim_png.py image.png [...] [--margin MARGIN] [--dry-run]
"""
import sys

import click
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


@click.command()
@click.argument("images", nargs=-1, required=True)
@click.option("--margin", type=int, default=40, show_default=True,
              help="Pixels of background kept on each side.")
@click.option("--dry-run", is_flag=True, help="Report the crop, keep the file.")
def main(images, margin, dry_run):
    """Trim each PNG to the geometry it shows, with a margin, in place.

    The crop is idempotent: a second run finds the ink at the margin and keeps
    the image as it is.
    """
    if margin < 0:
        raise click.UsageError("--margin must not be negative")
    ok = True
    for path in images:
        try:
            ok = trim(path, margin, dry_run) and ok
        except (OSError, ValueError) as exc:
            click.echo(f"trim_png.py: {path}: cannot read image: {exc}")
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
