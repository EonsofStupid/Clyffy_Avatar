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
from PIL import Image, ImageDraw


def silhouette(path: Path, thresh: int = 26) -> np.ndarray:
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    return a.max(axis=2) > thresh


def silhouette_light_bg(path: Path, thresh: int = 22) -> np.ndarray:
    """Silhouette on a LIGHT-GREY field, by flood-filling the background from the border.

    Colour distance cannot do this: the reference sheets put WHITE FUR (225,220,217) on a grey
    field (208-223) that also carries a gradient, so a threshold either eats the fur or keeps the
    background. Measured, then verified by eye — the first attempt produced a fragmented mask and
    a snout-tip reading taken from a neighbouring panel bleeding into frame.

    The background is CONNECTED from every border pixel and the character is an island, so the
    fill separates them regardless of how close the two values are.
    """
    im = Image.open(path).convert("RGB")
    W, H = im.size
    work = im.copy()
    MARK = (255, 0, 255)
    for xy in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1),
               (W // 2, 0), (W // 2, H - 1), (0, H // 2), (W - 1, H // 2)]:
        try:
            ImageDraw.floodfill(work, xy, MARK, thresh=thresh)
        except Exception:
            pass
    a = np.asarray(work)
    return ~((a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255))


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep only the blob containing the mask's centroid — drops adjacent-panel bleed."""
    m = Image.fromarray((mask * 255).astype(np.uint8)).convert("RGB")
    ys, xs = np.nonzero(mask)
    seed = (int(np.median(xs)), int(np.median(ys)))
    if not mask[seed[1], seed[0]]:
        seed = (int(xs[len(xs) // 2]), int(ys[len(ys) // 2]))
    ImageDraw.floodfill(m, seed, (0, 255, 0), thresh=10)
    a = np.asarray(m)
    return (a[..., 0] == 0) & (a[..., 1] == 255) & (a[..., 2] == 0)


def fill_holes(mask: np.ndarray) -> np.ndarray:
    """Fill interior holes — the brown patches segment out and would notch the outline."""
    pad = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = mask
    m = Image.fromarray((~pad * 255).astype(np.uint8)).convert("RGB")
    ImageDraw.floodfill(m, (0, 0), (255, 0, 0), thresh=10)
    a = np.asarray(m)
    outside = (a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 0)
    return (~outside)[1:-1, 1:-1]


def clean_silhouette(path: Path, light_bg: bool, mirror: bool = False) -> np.ndarray:
    """The full pipeline both sides of a comparison must go through."""
    m = silhouette_light_bg(path) if light_bg else silhouette(path)
    m = fill_holes(largest_component(m))
    return m[:, ::-1] if mirror else m


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


# ═══════════════════════════════════════════════════════════════════════════════════════════
# PROFILE metrics — the measurement this project never had
# ═══════════════════════════════════════════════════════════════════════════════════════════
def profile_metrics(sil: np.ndarray) -> dict | None:
    """Head proportions from a TRUE SIDE silhouette.

    Anchored on HEAD DEPTH — snout tip to the back of the skull — because that is unambiguous
    in a photograph and in a render, needs no anatomy knowledge, and is the one dimension a
    front view physically cannot show. Every proportion failure in this build (snout
    projection, head length, lip curve, chin) is a profile problem that was being measured
    front-on.

    The character faces LEFT in our render and RIGHT in the reference sheet, so the caller
    mirrors one of them; this function assumes the snout is at LOW x.
    """
    ys, xs = np.nonzero(sil)
    if len(ys) < 500:
        return None
    x_snout, x_back = int(xs.min()), int(xs.max())
    depth = x_back - x_snout
    if depth < 40:
        return None

    def col_extent(c: int):
        r = np.nonzero(sil[:, c])[0]
        return (int(r.min()), int(r.max())) if len(r) > 1 else None

    def row_extent(r: int):
        c = np.nonzero(sil[r])[0]
        return (int(c.min()), int(c.max())) if len(c) > 1 else None

    # crown: highest row whose horizontal run is still a real slab of head, not a horn tip
    rows = [(r, (lambda e: e[1] - e[0] if e else 0)(row_extent(r)))
            for r in range(int(ys.min()), int(ys.max()))]
    rows = [(r, w) for r, w in rows if w > 0]
    wmax = max(w for _, w in rows)
    crown = min(r for r, w in rows if w > 0.45 * wmax)
    chin = max(r for r, w in rows if w > 0.18 * wmax)
    height = chin - crown

    # snout tip height, and how far the muzzle stands proud of the face above it
    tip_rows = np.nonzero(sil[:, x_snout:x_snout + max(3, depth // 60)].any(axis=1))[0]
    tip_y = int(tip_rows.mean()) if len(tip_rows) else crown

    return {
        "depth": depth, "height": height, "crown_y": crown, "chin_y": chin,
        "height_over_depth": height / depth,
        "snout_tip_y_frac": (tip_y - crown) / max(height, 1),
    }


def profile_main(paths, mirror_flags):
    print(f"{'image':<30}{'depth':>8}{'height':>8}{'H/D':>8}{'snout tip y':>13}")
    out = []
    for p, mir in zip(paths, mirror_flags):
        s = silhouette(Path(p))
        if mir:
            s = s[:, ::-1]
        m = profile_metrics(s)
        if not m:
            print(f"{Path(p).name:<30}  (no usable silhouette)")
            continue
        print(f"{Path(p).name:<30}{m['depth']:>8}{m['height']:>8}"
              f"{m['height_over_depth']:>8.3f}{m['snout_tip_y_frac']:>13.3f}")
        out.append(m)
    if len(out) == 2:
        a, b = out
        print(f"\n  ours vs reference:")
        print(f"    height/depth   {b['height_over_depth']/a['height_over_depth']:.2f}x"
              f"   (ref {a['height_over_depth']:.3f} -> ours {b['height_over_depth']:.3f})")
        print(f"    snout tip y    ref {a['snout_tip_y_frac']:.3f} -> ours {b['snout_tip_y_frac']:.3f}")
