#!/usr/bin/env python3
"""Head proportions from a SILHOUETTE. One function, applied to reference and render alike.

    python3 tools/head_metrics.py <image> [<image> ...]

═══ WHY THIS EXISTS ═════════════════════════════════════════════════════════════════════════

Three separate attempts to compare our head to the operator's reference produced numbers that
contradicted what both of us could plainly see, and every time the cause was the same: I measured
the MESH one way and the PHOTO another. "Head height" ran to just below the mouth on our mesh and
to well below the chin on the reference, so the ratios were never comparable. The last version
reported our head as already too WIDE while the silhouettes plainly showed it too LONG.

So nothing here touches a mesh. Both sides are rendered or captured as images and measured by
this one function, which means the definitions cannot drift apart.

ANCHORS, chosen because they are unambiguous in a photograph AND in a render:
  * EAR LINE   — the row where the head silhouette is widest. Needs no anatomy knowledge.
  * EAR WIDTH  — the width at that row. Every distance below is expressed in these units, so
                 scale, crop and camera distance all cancel.
  * CROWN      — the highest row still at least 55% of ear width. Excludes the horns, which
                 taper to points and would otherwise set the top.
  * CHIN       — the narrowest row below the ear line, before the shoulders or coat flare out.

Reported: crown-above-ear and chin-below-ear, both in EAR WIDTHS. Two pure shape numbers with no
"head height" anywhere, which is precisely the quantity that could never be pinned down.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def silhouette(path: Path, thresh: int = 26) -> np.ndarray:
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    return a.max(axis=2) > thresh


def head_metrics(sil: np.ndarray, label: str = "") -> dict | None:
    ys, xs = np.nonzero(sil)
    if len(ys) < 500:
        return None
    top, bot = int(ys.min()), int(ys.max())

    def width(r: int) -> int:
        row = np.nonzero(sil[r])[0]
        return int(row.max() - row.min()) if len(row) > 1 else 0

    # THE EAR LINE IS THE FIRST LOCAL MAXIMUM SCANNING DOWN, not the global maximum.
    # Taking the widest row outright picked the LAB COAT SHOULDERS on the reference (they are
    # wider than the head and sit inside any fixed search window), which then put the "crown"
    # 0.76 ear-widths up and a "chin" 96% as wide as the ears. Scanning for the first peak finds
    # the ears on a head-only render and on a full figure alike, with no framing assumption.
    rows = [(r, width(r)) for r in range(top, bot)]
    rows = [(r, w) for r, w in rows if w > 0]
    if len(rows) < 40:
        return None
    ry = np.array([r for r, _ in rows])
    rw = np.array([w for _, w in rows], dtype=float)
    k = max(3, int(0.02 * len(rw)) | 1)
    sm = np.convolve(rw, np.ones(k) / k, mode="same")

    ear_i = None
    span = max(4, int(0.03 * len(sm)))
    for i in range(span, len(sm) - span):
        seg = sm[i - span:i + span + 1]
        if sm[i] >= seg.max() - 1e-9 and sm[i] > 0.25 * sm.max():
            # require a real dip after it, or it is just the shoulders ramping up
            after = sm[i:min(len(sm), i + 6 * span)]
            if after.min() < 0.88 * sm[i]:
                ear_i = i
                break
    if ear_i is None:
        ear_i = int(np.argmax(sm))
    ear_y, ear_w = int(ry[ear_i]), int(round(sm[ear_i]))
    if ear_w < 20:
        return None

    above = [(int(ry[i]), sm[i]) for i in range(ear_i)]
    crown_y = min((r for r, w in above if w > 0.55 * ear_w), default=ear_y)

    # chin = the narrowest row below the ears, searched only until the silhouette starts
    # widening again into shoulders or coat
    below = [(int(ry[i]), sm[i]) for i in range(ear_i + max(2, int(0.05 * ear_w)), len(sm))]
    chin_y, chin_w = (ear_y, float(ear_w))
    for r, w in below:
        if w < chin_w:
            chin_y, chin_w = r, w
        elif w > chin_w * 1.20:
            break

    return {
        "ear_y": ear_y, "ear_w": ear_w, "crown_y": crown_y, "chin_y": chin_y,
        "crown_above_ear": (ear_y - crown_y) / ear_w,
        "chin_below_ear": (chin_y - ear_y) / ear_w,
        "chin_w_over_ear_w": chin_w / ear_w,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    print(f"{'image':<34}{'ear width':>10}{'crown above':>13}{'chin below':>12}{'chin/ear w':>12}")
    out = []
    for p in sys.argv[1:]:
        m = head_metrics(silhouette(Path(p)), p)
        if not m:
            print(f"{Path(p).name:<34}   (no usable silhouette)")
            continue
        print(f"{Path(p).name:<34}{m['ear_w']:>10}{m['crown_above_ear']:>13.3f}"
              f"{m['chin_below_ear']:>12.3f}{m['chin_w_over_ear_w']:>12.3f}")
        out.append((Path(p).name, m))
    if len(out) >= 2:
        (n0, a), (n1, b) = out[0], out[1]
        print(f"\n  {n1} vs {n0}:")
        print(f"    crown above ear  {b['crown_above_ear']/max(a['crown_above_ear'],1e-9):.2f}x")
        print(f"    chin below ear   {b['chin_below_ear']/max(a['chin_below_ear'],1e-9):.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
