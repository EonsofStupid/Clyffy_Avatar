#!/usr/bin/env python3
"""Read TARGET COLOURS off the operator's reference frames, normalized to a white point.

    python3 tools/_refcolor.py [--marks OUT.png]

WHY NORMALIZED AND NOT SAMPLED DIRECTLY. The reference frames are dim, blue-graded night
shots: the muzzle pad that LOOKS salmon-pink measures sRGB (120,101,137) — blue-dominant
mauve. Both PIL and an independent ffmpeg decode agree on that value, so it is the file's
truth, and my visual impression of "pink" was my own eye white-balancing the frame. Worse,
the image display path auto-levels each image it renders, so a crop of that mauve region is
displayed as bright pink. I cannot colour-match by looking; I have to measure.

The fix is to work in RATIOS to a known white. Clyffy's fur is canonically WHITE, so the lit
fur IS the frame's white point. muzzle/fur is invariant to exposure and to a grey-world grade
to first order, which makes it transferable to OUR render's grading. Multiply the ratio by the
fur colour our atlas actually has and you get the muzzle colour our build should carry.

Everything is done in LINEAR light, because ratios of sRGB-encoded values are meaningless.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "canon/mouth_ref"

# What OUR mesh's fur measures in the baked atlas, from tools/_lipbands.py (linear).
OUR_FUR_LINEAR = np.array([0.367, 0.372, 0.388])


def to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(c, dtype=float) / 255.0, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(c, dtype=float), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


# Sample points as (decile_x, decile_y) read off a gridded overlay of each frame.
# r is the half-window in full-res pixels; medians, so a stray specular pixel cannot move it.
FRAMES = {
    "v1_48a464a0_t4.png": {
        "_white": [("fur bridge", 4.75, 3.30, 18),
                   ("fur muzzle-top", 4.40, 4.05, 14),
                   ("fur chin", 4.55, 9.10, 14)],
        "regions": [
            ("muzzle pad lit",      4.60, 5.60, 20),
            ("muzzle pad mid",      4.60, 6.40, 20),
            ("muzzle pad lower",    4.45, 7.10, 16),
            ("muzzle pad edge R",   5.60, 6.10, 12),
            ("nostril interior L",  3.85, 6.00, 8),
            ("nostril interior R",  5.55, 5.95, 8),
            ("lip roll lower",      4.60, 8.35, 10),
            ("lip crease",          4.75, 7.85, 6),
            ("teeth",               4.55, 8.05, 6),
            ("black patch",         3.50, 2.00, 16),
        ],
    },
    # Second pass on this frame. The first put "fur" on the pink muzzle (5.00,3.60) and on the
    # black background (3.30,5.20), giving an orange "white point" of (221,152,125) — garbage.
    # Verified against the marks overlay this time.
    "v2_7dca9cea_t4.png": {
        "_white": [("fur forehead blaze", 5.00, 2.25, 9),
                   ("fur cheek L", 3.92, 4.80, 9),
                   ("fur chin", 4.70, 8.75, 9)],
        "regions": [
            ("cavity deep",      5.00, 6.20, 10),
            ("tongue centre",    5.00, 7.10, 14),
            ("tongue edge",      4.55, 7.25, 8),
            ("upper dental pad", 5.00, 5.60, 8),
            ("upper canine L",   4.55, 5.62, 5),
            ("lower arch",       5.00, 7.62, 7),
            ("inner lip rim",    5.00, 5.30, 5),
            ("lower lip roll",   5.00, 8.10, 8),
            ("muzzle pad lit",   5.00, 3.90, 14),
        ],
    },
}


def main() -> int:
    marks = None
    if "--marks" in sys.argv:
        marks = Path(sys.argv[sys.argv.index("--marks") + 1])

    for fname, spec in FRAMES.items():
        p = REF / fname
        if not p.is_file():
            print(f"MISSING {p}")
            continue
        im = Image.open(p).convert("RGB")
        a = np.asarray(im).astype(float)
        Hp, Wp, _ = a.shape
        print(f"\n=== {fname}  {Wp}x{Hp} ===")

        draw_im = im.copy()
        dr = ImageDraw.Draw(draw_im)

        def sample(dx, dy, r):
            x = int(dx / 10.0 * Wp)
            y = int(dy / 10.0 * Hp)
            win = a[max(0, y - r):y + r, max(0, x - r):x + r].reshape(-1, 3)
            dr.rectangle([x - r, y - r, x + r, y + r], outline=(0, 255, 0), width=3)
            return np.median(win, axis=0), (x, y)

        # ── white point: the BRIGHTEST fur patch, in linear luminance ────────
        wl = []
        for nm, dx, dy, r in spec["_white"]:
            m, xy = sample(dx, dy, r)
            lin = to_linear(m)
            Y = float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])
            print(f"  white cand {nm:<16} at {xy} sRGB=({m[0]:5.1f},{m[1]:5.1f},{m[2]:5.1f}) Y={Y:.4f}")
            wl.append((Y, lin, nm))
        wl.sort(key=lambda t: -t[0])
        wY, wlin, wnm = wl[0]
        print(f"  -> WHITE POINT = '{wnm}' linear=({wlin[0]:.4f},{wlin[1]:.4f},{wlin[2]:.4f})")

        def lum(c):
            return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])

        our_Y = lum(OUR_FUR_LINEAR)
        print(f"  {'region':<19} {'ref sRGB':>17} {'Y/Yfur':>7} {'chroma R:G:B':>17} "
              f"{'-> OUR sRGB target':>20}")
        for nm, dx, dy, r in spec["regions"]:
            m, xy = sample(dx, dy, r)
            lin = to_linear(m)
            ratio = lin / np.maximum(wlin, 1e-6)      # von Kries: albedo estimate
            yr = lum(ratio)                            # luminance relative to the fur
            # Split the reference's authority: it specifies HUE reliably, but LEVEL is
            # contaminated by how the surface happens to face the key. Report both so a
            # pad that comes out brighter than white fur is visible as the error it is.
            chroma = ratio / max(yr, 1e-6)
            ours = to_srgb(np.clip(chroma * yr * OUR_FUR_LINEAR / max(our_Y, 1e-6) * our_Y, 0, 1))
            print(f"  {nm:<19} ({m[0]:5.1f},{m[1]:5.1f},{m[2]:5.1f}) {yr:7.3f} "
                  f"({chroma[0]:5.2f},{chroma[1]:5.2f},{chroma[2]:5.2f}) "
                  f"({ours[0]:5.1f},{ours[1]:5.1f},{ours[2]:5.1f})")

        if marks:
            out = marks.with_name(marks.stem + "_" + fname.split("_")[0] + marks.suffix)
            sc = max(1, Wp // 700)
            draw_im.resize((Wp // sc, Hp // sc)).save(out)
            print(f"  marks -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
