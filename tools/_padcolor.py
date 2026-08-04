#!/usr/bin/env python3
"""Measure the MUZZLE PAD albedo off `canon/reference/detail_muzzle_profile.png`.

    python3 tools/_padcolor.py [--marks OUT.png]

`tools/materials.py` still targets the pad at chroma (1.31, 0.92, 0.83) sourced from the
"archived base_sheet lit pad" — an ARCHIVED reference. The patch browning next to it in the same
file was correctly re-measured against `canon/reference/`, so the pad is the one colour in the
material still keyed to a superseded source, and against the authoritative sheet it renders too
pale. This measures it the same way the patch was measured.

RATIOS TO THE FUR, IN LINEAR LIGHT. Clyffy's fur is canonically white, so lit fur is the frame's
white point; pad/fur is invariant to exposure and to a grey-world grade to first order, which is
what makes it transferable onto our own render's grading. Absolute sRGB samples are not.

Windows are stated as fractions of the image and drawn to a marks file, because the previous
generation of this measurement put a "fur" sample on the pink muzzle and produced a white point
of (221,152,125) — an orange one — which then poisoned every colour derived from it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "canon/reference/detail_muzzle_profile.png"

# (name, x0, y0, x1, y1) as fractions of the image
FUR = [
    ("fur cheek",      0.16, 0.42, 0.25, 0.55),
    ("fur upper jaw",  0.28, 0.28, 0.35, 0.38),
    ("fur under lip",  0.30, 0.72, 0.38, 0.82),
]
PAD = [
    ("pad lit upper",  0.495, 0.20, 0.560, 0.29),   # clear of the nostril opening
    ("pad mid",        0.55, 0.40, 0.64, 0.50),
    ("pad lower",      0.52, 0.55, 0.60, 0.63),
    ("pad far side",   0.68, 0.35, 0.73, 0.45),
]


def to_linear(c):
    c = np.clip(np.asarray(c, dtype=float) / 255.0, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(c):
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def main() -> int:
    if not REF.is_file():
        print(f"MISSING {REF}")
        return 1
    im = Image.open(REF).convert("RGB")
    a = np.asarray(im).astype(float)
    H, W, _ = a.shape
    print(f"{REF.name}  {W}x{H}")

    draw = im.copy()
    d = ImageDraw.Draw(draw)

    def sample(box, colour):
        x0, y0, x1, y1 = box
        px = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)].reshape(-1, 3)
        d.rectangle([int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)], outline=colour, width=6)
        return np.median(px, axis=0)

    print(f"\n  {'region':<16}{'sRGB':>20}{'linear Y':>11}")
    furs = []
    for nm, *box in FUR:
        m = sample(box, (0, 220, 60))
        lin = to_linear(m)
        furs.append(lin)
        print(f"  {nm:<16}({m[0]:5.1f},{m[1]:5.1f},{m[2]:5.1f}){lum(lin):>11.4f}")
    fur_lin = np.median(np.array(furs), axis=0)
    print(f"  {'-> WHITE POINT':<16}{'':>20}{lum(fur_lin):>11.4f}   "
          f"linear ({fur_lin[0]:.4f},{fur_lin[1]:.4f},{fur_lin[2]:.4f})")

    pads = []
    print()
    for nm, *box in PAD:
        m = sample(box, (255, 0, 200))
        lin = to_linear(m)
        pads.append(lin)
        r = lin / np.maximum(fur_lin, 1e-6)
        print(f"  {nm:<16}({m[0]:5.1f},{m[1]:5.1f},{m[2]:5.1f}){lum(lin):>11.4f}"
              f"   pad/fur Y {lum(r):.3f}  chroma {r/max(lum(r),1e-6)}")
    pad_lin = np.median(np.array(pads), axis=0)
    ratio = pad_lin / np.maximum(fur_lin, 1e-6)
    ylev = lum(ratio)
    chroma = ratio / max(ylev, 1e-6)

    print(f"\n  MEASURED PAD (median of {len(PAD)} windows):")
    print(f"    ylev   {ylev:.3f}       <- pad luminance as a fraction of the fur's")
    print(f"    chroma ({chroma[0]:.2f}, {chroma[1]:.2f}, {chroma[2]:.2f})")
    print(f"\n  tools/materials.py currently has:")
    print(f"    \"muzzle\": ((1.31, 0.92, 0.83), 0.850, \"archived base_sheet lit pad, 3 samples\")")
    print(f"  measured against canon/reference:")
    print(f"    \"muzzle\": (({chroma[0]:.2f}, {chroma[1]:.2f}, {chroma[2]:.2f}), {ylev:.3f}, "
          f"\"canon/reference detail_muzzle_profile, {len(PAD)} windows\")")

    if "--marks" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--marks") + 1])
        sc = max(1, W // 1200)
        draw.resize((W // sc, H // sc)).save(out)
        print(f"\n  marks -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
