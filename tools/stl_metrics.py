#!/usr/bin/env python3
"""Compute volume, bbox and edge-manifold stats for an STL file.

Usage: stl_metrics.py file.stl [...]
One JSON object per file on stdout.
"""
import json
import struct
import sys

import numpy as np


class StlError(Exception):
    """The file is not a readable STL."""


def read_stl(path):
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        raise StlError(f"cannot read {path}: {exc}") from exc
    if data[:5] == b"solid" and b"facet" in data[:2048]:
        tris, cur = [], []
        for line in data.decode("ascii", "replace").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                cur.append([float(x) for x in line.split()[1:4]])
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return np.array(tris, dtype=np.float64)
    if len(data) < 84:
        raise StlError(f"{path} is too short to be a binary STL ({len(data)} bytes)")
    n = struct.unpack("<I", data[80:84])[0]
    if len(data) < 84 + n * 50:
        raise StlError(
            f"{path} is truncated: header says {n} triangles, "
            f"the file holds {max(0, len(data) - 84) // 50}"
        )
    arr = np.frombuffer(data[84 : 84 + n * 50], dtype=np.uint8).reshape(n, 50)
    return arr[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def canonical_edges(tri):
    """Return sorted (M, 6) array of undirected vertex-pair coordinates."""
    e = np.round(tri[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2, 3), 5).reshape(-1, 6)
    a, b = e[:, :3], e[:, 3:]
    d = a - b
    swap = (d[:, 0] > 0) | ((d[:, 0] == 0) & ((d[:, 1] > 0) | ((d[:, 1] == 0) & (d[:, 2] > 0))))
    out = np.empty_like(e)
    out[swap] = np.hstack([b[swap], a[swap]])
    out[~swap] = e[~swap]
    return out


def metrics(path):
    try:
        t = read_stl(path)
    except StlError as exc:
        return {"file": path, "error": str(exc), "triangles": 0}
    if len(t) == 0:
        return {"file": path, "error": "no triangles", "triangles": 0}
    v0, v1, v2 = t[:, 0], t[:, 1], t[:, 2]
    vol = float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)
    pts = t.reshape(-1, 3)
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    _, counts = np.unique(canonical_edges(t), axis=0, return_counts=True)
    return {
        "file": path,
        "triangles": int(len(t)),
        "volume_mm3": round(vol, 3),
        "bbox_min": [round(float(x), 3) for x in lo],
        "bbox_max": [round(float(x), 3) for x in hi],
        "size": [round(float(x), 3) for x in (hi - lo)],
        "edges_not_used_twice": int((counts != 2).sum()),
        "open_edges": int((counts == 1).sum()),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: stl_metrics.py file.stl [...]", file=sys.stderr)
        sys.exit(2)
    status = 0
    for p in sys.argv[1:]:
        m = metrics(p)
        print(json.dumps(m, sort_keys=True))
        if "error" in m:
            status = 1
    sys.exit(status)
