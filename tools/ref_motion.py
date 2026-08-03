#!/usr/bin/env python3
"""B0 — measure MOTION signatures off the operator's reference videos. Read-only, no authoring.

    python3 tools/ref_motion.py [--dir <uploads>] [--out work/ref_motion]

═══ WHY THIS EXISTS ═════════════════════════════════════════════════════════════════════════

The operator supplied FOUR VIDEOS as the reference for "finesse on the lips and mouth". I
reduced them to four still frames and spent a build cycle measuring pixel colour. Motion was
the entire point of them being videos, and a still cannot show any of it.

This is POAM A10 beat B0, and its rule is: **no authoring at all.** It produces the numbers that
every later beat is scored against. Nothing in this file changes the avatar.

What later beats need from it:
  B1 (head + body)   -> head translation amplitude and frequency; how the head accents speech
  B2 (ears / settle) -> ear displacement lag behind the head, and settle time
  B3 (weight dynamics)-> how fast the mouth actually opens and closes; how long shapes HOLD
  B4 (snout as mass) -> pad height / area / nostril-area variation, already partly measured

═══ HOW IT MEASURES ═════════════════════════════════════════════════════════════════════════

The muzzle pad is the tracking landmark. It is the one feature that is distinctive by HUE rather
than by luminance, so it survives the heavy grading in these clips (one is a blue night scene
where white fur reads as (113,160,217)).

SCALE RULER: the pad's WIDTH. Measured at 3.8% variation across 1.6 s of heavy mouth motion
while its HEIGHT varied 17.7% — the snout squashes vertically and holds its width. That makes
width a stable per-frame ruler, so every distance here is reported in pad-widths and transfers
to our mesh regardless of shot scale.

Three clips are multi-shot (workshop wides with many characters, then a face). Measuring across
a cut would blend two different scenes into one meaningless curve, so shots are segmented FIRST
on frame-to-frame difference, and only shots with a single dominant pink blob are analysed.

No scipy or OpenCV on this box, so connected components are replaced by coarse-grid MODE
SEEKING: bin the pink pixels into cells, take the densest cell, keep only pixels within a window
of it. That rejects the other characters in the wide shots without a labeller, and a frame whose
pink is too scattered to have a clear mode is reported as untracked rather than guessed at.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = Path("/home/hades/.claude/uploads/8df66586-8d55-4c23-989d-ddf0a788f68c")
OUT = ROOT / "work/ref_motion"

# ── THE SHOT MANIFEST — chosen BY LOOKING, not by a detector ─────────────────────────────────
# Five successive auto-detectors failed here, each differently: an uncapped search window
# swallowed the frame; capping it starved exactly the best frames (a big clear face exceeds the
# cap, so "confidence" read LOWEST when tracking was BEST); the hue rule inverted under the blue
# grade; and ROI seeding drifted. Meanwhile the FIRST measurement in this project — a fixed crop
# on a locked-off shot — produced clean, stable numbers on the first try.
#
# So the shots, their frame ranges and their crops are declared here, picked off a gridded
# overlay of each clip and checked by eye. That is what an artist actually does: look at the
# footage, choose the take, set the frame. It is reproducible, auditable, and it cannot silently
# latch onto a warm prop across the room.
#
# crop is (x0, y0, x1, y1) in the clip's OWN pixels. frames is [start, end).
SHOTS = [
    # ── THE PRIMARY REFERENCE (operator-supplied 2026-07-31) ────────────────────────────────
    # ONE character, isolated on PURE BLACK, ears visible throughout, 8 s of continuous
    # performance. The operator supplied it precisely because the earlier clips kept letting me
    # grab the wrong character or the wrong scene — and it removes that failure mode outright:
    # with a black background the silhouette IS the character, so there is nothing to mistake it
    # for. Five auto-detectors and four "improvements" were spent fighting cluttered footage
    # that this clip simply does not have.
    dict(clip="6f675283", name="isolated_performance", frames=(0, 192), crop=None,
         method="silhouette",
         use="B1 head sway + B2 ear lag — one character on black, 8 s continuous take"),

    # ── muzzle deformation (validated: ruler stable to 3.1%) ────────────────────────────────
    dict(clip="48a464a0", name="muzzle_closeup", frames=(206, 246), crop=(520, 470, 1330, 900),
         method="crop",
         use="pad deformation — the snout filling frame, heavy mouth motion"),
]

W_PROC = 960                      # processing width; pad height stays ~60 px, plenty
SHOT_THRESH = 12.0                # mean abs RGB diff that counts as a cut
MIN_SHOT = 8                      # frames


def frames(path: Path, width: int):
    """Decode to raw RGB via ffmpeg. Avoids writing thousands of PNGs."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", str(path)],
        capture_output=True, text=True).stdout
    st = json.loads(probe)["streams"][0]
    w0, h0 = int(st["width"]), int(st["height"])
    num, den = st["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    h = int(round(h0 * width / w0 / 2)) * 2
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={width}:{h}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    n = width * h * 3
    while True:
        buf = p.stdout.read(n)
        if len(buf) < n:
            break
        yield np.frombuffer(buf, dtype=np.uint8).reshape(h, width, 3).astype(np.float32)
    p.stdout.close(); p.wait()
    return fps


def pink_mask(a: np.ndarray) -> np.ndarray:
    """The muzzle — WHITE-BALANCED first, then judged by hue.

    A fixed `R > B` rule does not survive these grades and silently fails on the most important
    clip: in the blue night closeup the muzzle measures sRGB (120,101,137), where R is LESS than
    B. The mask rejected the actual muzzle and latched onto stray warm pixels, giving 5% fill
    and 0.20 confidence on a frame that is nothing but muzzle.

    So: estimate the frame's own white point from its bright pixels, divide it out (von Kries —
    the same correction this project already needed for albedo), and only then ask which pixels
    are warmer than neutral. Clyffy's fur is canonically white, so the bright end of a frame
    containing him is a sound white reference.
    """
    lum = a.max(axis=2)
    bright = lum > np.percentile(lum, 88)
    if bright.sum() < 64:
        wp = np.array([1.0, 1.0, 1.0], np.float32)
    else:
        wp = a[bright].mean(axis=0)
        wp = np.maximum(wp / max(wp.mean(), 1e-6), 0.35)     # normalise, guard a dead channel
    b = a / wp                                               # white-balanced
    mx = b.max(axis=2); mn = b.min(axis=2)
    sat = np.where(mx > 1, (mx - mn) / np.maximum(mx, 1), 0)
    warm = b[..., 0] - 0.5 * (b[..., 1] + b[..., 2])         # red against the other two
    return (sat > 0.10) & (warm > 0.06 * np.maximum(mx, 1)) & (lum > 40)


def mode_window(mask: np.ndarray, cell: int = 24):
    """Densest region of a mask, without a connected-component labeller.

    Bins into `cell`-sized squares, takes the peak, then keeps mask pixels inside a window
    grown around it. Returns (kept_mask, confidence) where confidence is the fraction of all
    mask pixels that fell inside the window — low confidence means the pink is scattered
    across several characters and this frame should not be trusted.
    """
    ys, xs = np.nonzero(mask)
    if len(ys) < 120:
        return None, 0.0
    H, W = mask.shape
    gh, gw = (H + cell - 1) // cell, (W + cell - 1) // cell
    hist = np.zeros((gh, gw), dtype=np.int32)
    np.add.at(hist, (ys // cell, xs // cell), 1)
    py, px = np.unravel_index(int(hist.argmax()), hist.shape)
    cy, cx = (py + 0.5) * cell, (px + 0.5) * cell
    # Window sized from the blob's spread about the mode — but CAPPED.
    # Uncapped, a workshop wide shot full of warm props grows the window until it swallows the
    # frame, and the old confidence metric ("what fraction of pink is inside the window") then
    # reads ~1.0 because everything is inside it. Verified by looking at the debug overlays:
    # five of six shots were whole-frame boxes reported as 100% tracked. A head cannot be most
    # of the frame, so the radius is bounded by a plausible head size.
    d = np.hypot(ys - cy, xs - cx)
    r = min(max(np.percentile(d, 70), cell * 1.5), 0.16 * W)
    keep = d <= r * 1.6
    conf = float(keep.sum()) / float(len(ys))
    out = np.zeros_like(mask)
    out[ys[keep], xs[keep]] = True
    return out, conf


REJECT = {}


def _rej(why):
    REJECT[why] = REJECT.get(why, 0) + 1
    return None


def measure_silhouette(a: np.ndarray):
    """Head reference from the SILHOUETTE, for clips shot on black.

    Nothing to segment: the background is pure black (measured 5th-percentile luminance 0.0), so
    everything lit is the character. The CROWN — the topmost few rows of the silhouette — is a
    rigid point on the skull that needs no anatomy detection at all, and it tracks head bob and
    sway directly. Scale ruler is the silhouette's own height, which held to 6.9% across the
    whole 8 s take.

    This replaces five failed attempts at detecting a face in cluttered footage. The right fix
    was better FOOTAGE, not a better detector.
    """
    sil = a.max(axis=2) > 28
    ys, xs = np.nonzero(sil)
    if len(ys) < 500:
        return _rej("no_silhouette")
    top = int(ys.min())
    # HEAD-MASS centroid, not the topmost rows. The top few rows are HORN TIPS, and rolling the
    # head raises one horn while lowering the other, so a tip-row centroid partly cancels instead
    # of sliding — it under-reports lateral motion by ~6x. Averaging over the top 12% of the
    # figure takes the head as a mass and slides smoothly. Applied identically here and in
    # tools/idle_check.py; the two measurements are only comparable if the definition matches.
    band = ys <= top + 0.12 * (ys.max() - ys.min())
    if band.sum() < 40:
        return _rej("crown_thin")
    silh = float(ys.max() - ys.min())
    crown_x = float(xs[band].mean())
    rec = dict(cx=crown_x, cy=float(top), w=float(xs.max() - xs.min()), h=silh,
               area=float(len(ys)), nostril=0.0, aperture=0.0, conf=1.0)
    eb = ear_band(a, crown_x, top, silh)
    if eb:
        rec.update(eb)
    return rec


def measure_roi(a: np.ndarray, roi):
    """Muzzle metrics inside a tight, hand-chosen crop. Deliberately the SIMPLEST thing.

    This is a REVERSION, and the reversion is the point. The first measurement in this project
    used a tight crop, a plain absolute pink rule and a raw min/max bounding box, and it hit
    3.8% ruler stability on the first try. I then "improved" it four times — coarse-grid mode
    seeking, robust percentile bounds, a white-balanced hue test, ROI mean-shift — and every
    single addition made the numbers WORSE (stability went 3.8% -> 30% -> 67%).

    The additions were all solving a problem the crop already solved: rejecting everything that
    is not the muzzle. Given a crop that contains the muzzle and little else, the naive mask is
    correct and the clever ones introduce their own failure modes. Complexity was the bug.
    """
    y0, y1, x0, x1 = roi
    sub = a[y0:y1, x0:x1]
    if sub.size < 3000:
        return _rej("roi_tiny")
    mx = sub.max(axis=2); mn = sub.min(axis=2)
    sat = np.where(mx > 1, (mx - mn) / np.maximum(mx, 1), 0)
    m = (sat > 0.13) & (sub[..., 0] > sub[..., 2] + 10) & (mx > 60)
    if m.sum() < 200:
        return _rej("no_pink_in_roi")
    ys, xs = np.nonzero(m)
    bx0, bx1 = float(xs.min()), float(xs.max())
    by0, by1 = float(ys.min()), float(ys.max())
    w, h = bx1 - bx0, by1 - by0
    if w < 10 or h < 6:
        return _rej("bbox_tiny")

    lum = mx
    box = lum[int(by0):int(by1) + 1, int(bx0):int(bx1) + 1]
    if box.size < 100:
        return _rej("subbox_tiny")
    up = box[: max(1, box.shape[0] // 2)]
    nos = float((up < np.percentile(box, 20)).sum())
    lo0 = int(by0 + 0.55 * h); lo1 = min(sub.shape[0], int(by1 + 0.55 * h))
    lo = lum[lo0:lo1, int(bx0):int(bx1) + 1]
    ap = float((lo < np.percentile(box, 22)).sum()) if lo.size > 50 else 0.0
    return dict(cx=float(xs.mean()) + x0, cy=float(ys.mean()) + y0,
                w=w, h=h, area=float(len(ys)), nostril=nos, aperture=ap,
                conf=float(len(ys) / max(w * h, 1.0)))


def seed_roi(a: np.ndarray):
    """Find the muzzle once, to start a shot. Same mode-seek, used ONCE not per frame."""
    m, conf = mode_window(pink_mask(a))
    if m is None or conf < 0.20:
        return None
    ys, xs = np.nonzero(m)
    if len(ys) < 200:
        return None
    cx, cy = xs.mean(), ys.mean()
    x0, x1 = np.percentile(xs, [2, 98]); y0, y1 = np.percentile(ys, [2, 98])
    w, h = x1 - x0, y1 - y0
    if w < 20 or h < 12 or not (0.30 <= h / w <= 1.6):
        return None
    H, W, _ = a.shape
    if not (0.05 * W <= w <= 0.55 * W):
        return None
    mgx, mgy = 0.45 * w, 0.55 * h
    return (int(max(0, cy - h / 2 - mgy)), int(min(H, cy + h / 2 + mgy)),
            int(max(0, cx - w / 2 - mgx)), int(min(W, cx + w / 2 + mgx)))


def step_roi(rec, shape, w, h):
    """Re-centre the ROI on the last good measurement."""
    H, W = shape
    mgx, mgy = 0.45 * w, 0.55 * h
    return (int(max(0, rec["cy"] - h / 2 - mgy)), int(min(H, rec["cy"] + h / 2 + mgy)),
            int(max(0, rec["cx"] - w / 2 - mgx)), int(min(W, rec["cx"] + w / 2 + mgx)))


def _measure_unused(a: np.ndarray):
    """Per-frame muzzle metrics, or None if the frame cannot be tracked honestly.

    Every rejection is COUNTED by reason. Thresholds here were guessed twice and were wrong
    twice — first too loose (whole-frame boxes reported as tracked), then too tight (nothing
    passed at all). Counting the reasons turns threshold-setting into a measurement instead of
    another guess.
    """
    m, conf = mode_window(pink_mask(a))
    if m is None:
        return _rej("no_pink")
    if conf < 0.45:
        return _rej("low_conf")
    ys, xs = np.nonzero(m)
    if len(ys) < 150:
        return _rej("too_few_px")
    # robust bbox — percentiles, so a few stray pixels cannot set the extent
    x0, x1 = np.percentile(xs, [1, 99])
    y0, y1 = np.percentile(ys, [1, 99])
    w, h = float(x1 - x0), float(y1 - y0)
    if w < 12 or h < 8:
        return _rej("bbox_tiny")

    # ── IS THIS ACTUALLY A MUZZLE? ───────────────────────────────────────────
    # FILL is the discriminator the first version lacked. A muzzle pad is a dense solid region
    # of its own bounding box; warm clutter scattered across a room fills only a few percent of
    # the box that encloses it. This is what separates "tracked the face" from "drew a rectangle
    # round the whole scene", and without it five of six shots passed while measuring nothing.
    H, W = a.shape[0], a.shape[1]
    fill = len(ys) / max(w * h, 1.0)
    if fill < 0.42:
        return _rej(f"low_fill(<0.42)")
    if not (0.02 * W <= w <= 0.45 * W):
        return _rej("width_out_of_range")
    if not (0.35 <= h / w <= 1.30):        # the pad is wider than tall, never a tall streak
        return _rej("aspect_out_of_range")

    mx = a.max(axis=2)
    box = (slice(int(y0), int(y1) + 1), slice(int(x0), int(x1) + 1))
    sub = mx[box]
    if sub.size < 100:
        return _rej("subbox_tiny")
    # nostrils: dark holes in the UPPER half of the pad
    up = sub[: max(1, sub.shape[0] // 2)]
    nos = float((up < np.percentile(sub, 20)).sum())
    # mouth aperture: dark region in the LOWER third and just under the pad
    lo0 = int(y0 + 0.55 * h); lo1 = min(a.shape[0], int(y1 + 0.55 * h))
    lo = mx[lo0:lo1, int(x0):int(x1) + 1]
    ap = float((lo < np.percentile(sub, 22)).sum()) if lo.size > 50 else 0.0

    return dict(cx=float(xs.mean()), cy=float(ys.mean()),
                w=w, h=h, area=float(len(ys)), nostril=nos, aperture=ap, conf=conf)


def ear_band(a: np.ndarray, crown_x: float, top: int, silh: float):
    """Ear reach left/right of the skull, from the silhouette outline.

    The band is 8-20% of the figure's height below the crown, which sits across the horns and
    upper ears in every frame of the isolated clip and is above where the arms normally reach.
    Returns raw pixels; the caller normalises by the height ruler and rejects arm intrusion.

    ⚠️ WHAT THIS SIGNAL IS AND IS NOT. It measures how far the head's outline reaches sideways,
    which responds to ear swing AND to head rotation/perspective. It is therefore sound for
    AMPLITUDE (how far the ears travel relative to the skull) and NOT sound for isolating spring
    LAG, because a head turning in place changes the reach with no ear dynamics at all. Measured
    lag came out at 0 frames for both ears, which is the signature of a pose-dominated signal
    rather than evidence that the ears do not trail.
    """
    y0 = int(top + 0.08 * silh); y1 = int(top + 0.20 * silh)
    if y1 - y0 < 4 or y1 > a.shape[0]:
        return None
    band = a[y0:y1].max(axis=2) > 28
    by, bx = np.nonzero(band)
    if len(bx) < 20:
        return None
    return dict(ear_l=float(crown_x - bx.min()), ear_r=float(bx.max() - crown_x),
                ear_span=float(bx.max() - bx.min()))


def segment_shots(means: np.ndarray, hists: np.ndarray) -> list[tuple[int, int]]:
    """Cuts from BOTH mean luminance and colour-histogram distance.

    A fixed mean-difference threshold was not enough: the first pass found 2 shots in a clip
    that visibly has three scenes, so a workshop wide and a face closeup were averaged into one
    curve. Two scenes can share a mean while having completely different histograms, so the
    histogram distance catches the cuts the mean misses, and both thresholds are RELATIVE to
    the clip's own statistics rather than absolute.
    """
    dm = np.abs(np.diff(means))
    dh = np.abs(np.diff(hists, axis=0)).sum(axis=1) / 2.0     # total-variation distance
    m_thr = max(SHOT_THRESH, float(np.median(dm) + 6 * (np.percentile(dm, 75) - np.median(dm) + 1e-6)))
    h_thr = max(0.22, float(np.median(dh) + 6 * (np.percentile(dh, 75) - np.median(dh) + 1e-9)))
    cut_at = np.nonzero((dm > m_thr) | (dh > h_thr))[0]
    cuts = [0] + [int(i) + 1 for i in cut_at] + [len(means)]
    out = []
    for i in range(len(cuts) - 1):
        if cuts[i + 1] - cuts[i] >= MIN_SHOT:
            out.append((cuts[i], cuts[i + 1]))
    return out


def hist_of(a: np.ndarray) -> np.ndarray:
    """Coarse normalised RGB histogram — the shot-change signal the mean cannot see."""
    q = (a.reshape(-1, 3) // 64).astype(np.int32)          # 4 bins per channel
    idx = q[:, 0] * 16 + q[:, 1] * 4 + q[:, 2]
    h = np.bincount(idx, minlength=64).astype(np.float64)
    return h / max(h.sum(), 1.0)


def dominant_freq(sig: np.ndarray, fps: float):
    """Dominant oscillation of a centred signal — the idle sway rate."""
    if len(sig) < 16:
        return None, None
    x = sig - sig.mean()
    x = x * np.hanning(len(x))
    sp = np.abs(np.fft.rfft(x))
    fr = np.fft.rfftfreq(len(x), 1.0 / fps)
    lo = (fr > 0.08) & (fr < 4.0)                 # plausible body/head motion band
    if not lo.any():
        return None, None
    k = int(np.nonzero(lo)[0][sp[lo].argmax()])
    return float(fr[k]), float(sp[k] / max(sp[lo].sum(), 1e-9))


def rise_fall(sig: np.ndarray, fps: float):
    """10->90% rise and 90->10% fall times of the biggest excursion, in ms.

    This is the number B3 needs: how fast the mouth ACTUALLY opens. A weight that steps to
    target in one frame is the robotic tell; the reference will have a real duration.
    """
    if len(sig) < 8:
        return None
    s = sig.astype(float)
    rng = s.max() - s.min()
    if rng < 1e-6:
        return None
    lo, hi = s.min() + 0.1 * rng, s.min() + 0.9 * rng
    rises, falls = [], []
    state, start = None, None
    for i, v in enumerate(s):
        if state is None:
            state = "lo" if v <= lo else ("hi" if v >= hi else None)
            start = i
        elif state == "lo" and v >= hi:
            rises.append((i - start) / fps * 1000); state, start = "hi", i
        elif state == "hi" and v <= lo:
            falls.append((i - start) / fps * 1000); state, start = "lo", i
        elif (state == "lo" and v <= lo) or (state == "hi" and v >= hi):
            start = i
    return dict(rise_ms=float(np.median(rises)) if rises else None,
                fall_ms=float(np.median(falls)) if falls else None,
                n_rise=len(rises), n_fall=len(falls))


def hold_stats(sig: np.ndarray, fps: float):
    """How long the signal sits still — the HOLD durations a performance needs."""
    if len(sig) < 8:
        return None
    v = np.abs(np.diff(sig.astype(float)))
    q = np.percentile(v, 35)
    runs, cur = [], 0
    for x in v:
        if x <= q:
            cur += 1
        elif cur:
            runs.append(cur); cur = 0
    if cur:
        runs.append(cur)
    if not runs:
        return None
    r = np.array(runs) / fps * 1000
    return dict(median_ms=float(np.median(r)), p90_ms=float(np.percentile(r, 90)),
                max_ms=float(r.max()), n=len(r))


def var_pct(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    return float(100.0 * (x.max() - x.min()) / max(x.mean(), 1e-9))


def plot(curves: dict, path: Path, title: str):
    """PIL line plots — no matplotlib on this box."""
    keys = [k for k in ("pad_h", "pad_w", "area", "nostril", "aperture", "cx", "cy")
            if k in curves and len(curves[k]) > 4]
    if not keys:
        return
    W, RH, PAD = 900, 78, 34
    im = Image.new("RGB", (W, PAD + RH * len(keys) + 14), (16, 17, 20))
    d = ImageDraw.Draw(im)
    d.text((8, 8), title, fill=(255, 255, 255))
    for r, k in enumerate(keys):
        y0 = PAD + r * RH
        s = np.asarray(curves[k], float)
        ok = np.isfinite(s)
        if ok.sum() < 4:
            continue
        lo, hi = np.nanmin(s[ok]), np.nanmax(s[ok])
        rng = max(hi - lo, 1e-9)
        d.text((6, y0 + 2), f"{k}  {lo:.1f}..{hi:.1f}  (var {var_pct(s[ok]):.1f}%)",
               fill=(150, 230, 255))
        pts = []
        for i, v in enumerate(s):
            if not np.isfinite(v):
                pts = []
                continue
            x = 90 + i * (W - 100) / max(len(s) - 1, 1)
            y = y0 + RH - 8 - (v - lo) / rng * (RH - 26)
            pts.append((x, y))
            if len(pts) > 1:
                d.line(pts[-2:], fill=(255, 200, 120), width=1)
        d.line([(90, y0 + RH - 6), (W - 8, y0 + RH - 6)], fill=(60, 62, 70))
    im.save(path)


def main() -> int:
    DEBUG = "--debug" in sys.argv
    src = Path(sys.argv[sys.argv.index("--dir") + 1]) if "--dir" in sys.argv else UPLOADS
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else OUT
    out.mkdir(parents=True, exist_ok=True)
    print(f"ref_motion: {len(SHOTS)} declared shot(s) from {src}\n")

    report = {"source": str(src), "shots": {}}
    for spec in SHOTS:
        vids = list(src.glob(spec["clip"] + "*.mp4"))
        if not vids:
            print(f"── {spec['name']}: clip {spec['clip']} NOT FOUND")
            continue
        v = vids[0]
        f0, f1 = spec["frames"]
        method = spec.get("method", "crop")

        # decode only the declared range, cropped, at native resolution
        probe = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=r_frame_rate", "-of", "json", str(v)],
            capture_output=True, text=True).stdout)["streams"][0]
        num, den = probe["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        if spec.get("crop"):
            x0, y0, x1, y1 = spec["crop"]
            cw, ch = x1 - x0, y1 - y0
            vf = f"select='between(n,{f0},{f1 - 1})',crop={cw}:{ch}:{x0}:{y0}"
        else:
            cw, ch = 640, 360
            vf = f"select='between(n,{f0},{f1 - 1})',scale={cw}:{ch}"
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(v), "-vf", vf,
             "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True)
        n = cw * ch * 3
        nf = len(proc.stdout) // n
        buf = [np.frombuffer(proc.stdout[i * n:(i + 1) * n], dtype=np.uint8)
               .reshape(ch, cw, 3).astype(np.float32) for i in range(nf)]
        if nf < 8:
            print(f"── {spec['name']}: only {nf} frames decoded — SKIPPED")
            continue

        REJECT.clear()
        full = (0, ch, 0, cw)
        recs = ([measure_silhouette(a) for a in buf] if method == "silhouette"
                else [measure_roi(a, full) for a in buf])
        tracked = [r for r in recs if r]
        frac = len(tracked) / nf
        print(f"── {spec['name']:<16} {nf:3d} frames @ {fps:.0f}fps  crop {cw}x{ch}  "
              f"tracked {100*frac:.0f}%")
        if frac < 0.6:
            top = sorted(REJECT.items(), key=lambda kv: -kv[1])[:3]
            print(f"     UNUSABLE — {', '.join(f'{k}={v}' for k, v in top)}")
            continue

        def col(k):
            return np.array([r[k] if r else np.nan for r in recs], float)

        pad_w, pad_h = col("w"), col("h")
        # silhouette clips: the ruler is the figure's HEIGHT (pad width is the ear span there,
        # which moves with the performance and would be a moving ruler)
        ruler = float(np.nanmedian(pad_h if method == "silhouette" else pad_w))
        cx, cy = col("cx") / ruler, col("cy") / ruler
        area, nos, ap = col("area"), col("nostril"), col("aperture")

        rulcol = pad_h if method == "silhouette" else pad_w
        w_var = var_pct(rulcol[np.isfinite(rulcol)])
        ears = [r if (r and "ear_l" in r) else None for r in recs]
        n_ear = sum(1 for e in ears if e)

        fx, _ = dominant_freq(cx[np.isfinite(cx)], fps)
        fy, _ = dominant_freq(cy[np.isfinite(cy)], fps)
        sh = {
            "clip": spec["clip"], "use": spec["use"], "frames": nf,
            "duration_s": round(nf / fps, 2), "tracked_pct": round(100 * frac, 1),
            "crop": list(spec["crop"]) if spec.get("crop") else None,
            "method": method, "frame_range": list(spec["frames"]),
            "pad_width_px_median": round(ruler, 1),
            "ruler_stability_pct": round(w_var, 1),
            "variation_pct": {
                "pad_height": round(var_pct(pad_h[np.isfinite(pad_h)]), 1),
                "pad_width": round(w_var, 1),
                "pad_area": round(var_pct(area[np.isfinite(area)]), 1),
                "nostril_area": round(var_pct(nos[np.isfinite(nos)]), 1),
            },
            "head_translation_padwidths": {
                "x_p2p": round(float(np.nanmax(cx) - np.nanmin(cx)), 3),
                "y_p2p": round(float(np.nanmax(cy) - np.nanmin(cy)), 3),
                "x_dominant_hz": round(fx, 3) if fx else None,
                "y_dominant_hz": round(fy, 3) if fy else None,
            },
            "aperture": {"rise_fall": rise_fall(ap[np.isfinite(ap)], fps),
                         "hold": hold_stats(ap[np.isfinite(ap)], fps)},
            "pad_height_dynamics": {"rise_fall": rise_fall(pad_h[np.isfinite(pad_h)], fps),
                                    "hold": hold_stats(pad_h[np.isfinite(pad_h)], fps)},
            "ear_frames": n_ear,
        }
        if n_ear >= 12:
            el = np.array([e["ear_l"] if e else np.nan for e in ears], float)
            er = np.array([e["ear_r"] if e else np.nan for e in ears], float)
            sp = np.array([e["ear_span"] if e else np.nan for e in ears], float)
            # ARMS: when raised they exceed the ears laterally and would read as ear motion.
            arm = sp > np.nanmedian(sp) * 1.45
            el[arm] = np.nan; er[arm] = np.nan
            sh["ear_arm_rejected"] = int(arm.sum())
            sh["ear_amplitude_bodyheights"] = {
                "left_rms": round(float(np.nanstd(el / ruler)), 4),
                "right_rms": round(float(np.nanstd(er / ruler)), 4),
                "left_p2p": round(float(np.nanmax(el / ruler) - np.nanmin(el / ruler)), 4),
                "right_p2p": round(float(np.nanmax(er / ruler) - np.nanmin(er / ruler)), 4),
            }
            sh["ear_extent_padwidths"] = {
                "left_p2p": round(float(np.nanmax(el) - np.nanmin(el)), 3),
                "right_p2p": round(float(np.nanmax(er) - np.nanmin(er)), 3),
            }
            hv = np.abs(np.gradient(np.nan_to_num(cx, nan=float(np.nanmean(cx)))))
            ev = np.abs(np.gradient(np.nan_to_num(el, nan=float(np.nanmean(el)))))
            if np.std(hv) > 1e-9 and np.std(ev) > 1e-9:
                hv = (hv - hv.mean()) / hv.std(); ev = (ev - ev.mean()) / ev.std()
                cc = [(float(np.mean(hv[:len(hv) - L] * ev[L:])), L)
                      for L in range(0, min(12, nf // 3))]
                best = max(cc, key=lambda t: t[0])
                sh["ear_lag"] = {"frames": best[1], "ms": round(best[1] / fps * 1000, 1),
                                 "corr": round(best[0], 3)}
        report["shots"][spec["name"]] = sh

        vp = sh["variation_pct"]
        print(f"     ruler {ruler:.0f}px stable to {w_var:.1f}%  |  pad h {vp['pad_height']}%  "
              f"area {vp['pad_area']}%  nostril {vp['nostril_area']}%"
              + (f"  |  EARS {n_ear}f lag {sh.get('ear_lag',{}).get('ms','?')}ms"
                 if n_ear >= 12 else ""))
        plot({"pad_h": pad_h, "pad_w": pad_w, "area": area, "nostril": nos,
              "aperture": ap, "cx": cx, "cy": cy},
             out / f"{spec['name']}.png", f"{spec['name']}  {sh['duration_s']}s")
        if DEBUG:
            step = max(1, nf // 12)
            tiles = []
            for i in range(0, nf, step):
                if not recs[i]:
                    continue
                r = recs[i]
                im = Image.fromarray(buf[i].astype(np.uint8)).copy()
                dd = ImageDraw.Draw(im)
                dd.rectangle([r["cx"] - r["w"] / 2, r["cy"] - r["h"] / 2,
                              r["cx"] + r["w"] / 2, r["cy"] + r["h"] / 2],
                             outline=(0, 255, 0), width=3)
                dd.text((6, 6), f"f{f0+i} fill{r['conf']:.2f}", fill=(0, 255, 0))
                tiles.append(im.resize((240, int(240 * im.height / im.width))))
            if tiles:
                tw, th = tiles[0].size
                C = 6; R = (len(tiles) + C - 1) // C
                sheet = Image.new("RGB", (C * tw, R * th), (16, 17, 20))
                for j, t in enumerate(tiles):
                    sheet.paste(t, ((j % C) * tw, (j // C) * th))
                sheet.save(out / f"_track_{spec['name']}.png")
        del buf

    def jsonable(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(f"not JSON serialisable: {type(o).__name__}")

    (out / "ref_motion.json").write_text(json.dumps(report, indent=2, default=jsonable))
    print(f"\nwrote {out/'ref_motion.json'}  ({len(report['shots'])} usable shot(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
