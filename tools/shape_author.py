"""ARKit-52 blendshape authoring, driven by the facial region atlas.

    blender -b --python tools/shape_author.py -- <atlas.blend> <out_dir> <fwd_deg> [names...]

Every shape is a parameterised deformation over NAMED, WEIGHTED regions (tools/face_atlas.py).
No shape re-derives geometry: that is where this build has been bitten repeatedly.

House rules, each learned the hard way:
  * Interior geometry (mouth bag, teeth, tongue) and the rigid eyeballs are NEVER moved by
    a skin shape -- they are driven by bones.
  * A lid must SLIDE OVER the eyeball at radius >= 1.06r, not collapse toward its centre,
    or the eye pokes through the closed lid.
  * jawOpen is bone-backed and is deliberately NOT authored here.

Full head (ARKit-52 authored set = 43; jawOpen + 8 eyeLook* are bone-driven):
  A  eyeBlink L/R
  B  eyeSquint/Wide L/R · browDown L/R · browInnerUp · browOuterUp L/R
  C  jaw F/L/R (not Open) · full mouth set (23)
  D  cheekPuff · cheekSquint L/R · noseSneer L/R · tongueOut
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
WANT = argv[3:] if len(argv) > 3 else None
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
up = np.array([0.0, 0.0, 1.0])
hc = co[co[:, 2] > 0.208].mean(axis=0)
lat0 = float(hc @ lat)

gi = {g.name: g.index for g in ob.vertex_groups}
def W(name):
    """region weights as a dense array"""
    w = np.zeros(N)
    if name not in gi: return w
    idx = gi[name]
    for v in me.vertices:
        for g in v.groups:
            if g.group == idx: w[v.index] = g.weight
    return w
def IDX(name): return np.where(W(name) > 0.5)[0]

EYE = {"L": (np.array(ob["eye_L_center"]), float(ob["eye_L_radius"]), IDX("eye_L")),
       "R": (np.array(ob["eye_R_center"]), float(ob["eye_R_radius"]), IDX("eye_R"))}
EYEBALL = set(EYE["L"][2].tolist()) | set(EYE["R"][2].tolist())
TEETH_U = set(IDX("teeth_upper").tolist())
TEETH_L = set(IDX("teeth_lower").tolist())
TONGUE  = set(IDX("tongue").tolist())
di = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
CAVITY = {v for p in me.polygons if p.material_index == di for v in p.vertices}
SURF = {v for p in me.polygons if p.material_index != di for v in p.vertices}
# ── THE LIP RIM IS NOT INTERIOR (operator ruling 2026-07-28) ──────────────────
# The rim is the 62-vert boundary where the cavity meets the skin — it is the LIP EDGE, and
# it was being protected along with the bag. Consequence, measured: not one of the 43 shape
# keys moved a single rim vertex, so no blendshape could change the mouth aperture at all.
# Every mouth morph moved the skin AROUND the lips while the lip edge stayed welded shut,
# which made the aperture 100% jaw-driven — and the jaw is capped at 13° by the shirt collar.
#
# That cap is also what pinned the chin: with gape coming only from jaw rotation, chin depth
# traded against gape one-for-one (d < 9.0%H − D) and the chin was stuck at the 4.5%H optimum
# of min(D, 9−D). Freeing the rim breaks that trade — the lips can open the mouth while the
# jaw barely moves, so the chin can finally be modelled for how it should LOOK.
#
# The BAG stays protected, and must: its verts are skinned from their rim ancestor via
# `cav_src`, and moving them independently tears the bag in half (the failure jaw_rig.py
# documents at 27x edge stretch). Instead the bag FOLLOWS the rim by that same lineage —
# see `propagate_bag` below.
RIM = CAVITY & SURF
BAG = CAVITY - RIM
RIGID = EYEBALL | TEETH_U | TEETH_L | TONGUE | BAG
rigid_mask = np.zeros(N, bool); rigid_mask[np.array(sorted(RIGID), dtype=int)] = True
print(f"protected from skin shapes: {int(rigid_mask.sum())} verts "
      f"(eyeballs, mouth BAG, teeth, tongue); the {len(RIM)}-vert LIP RIM is now free")

# Lineage written by tools/mouth_open.py: every bag vert records the rim vert it was
# extruded from, and how deep it sits (0 = lip rim, 1 = back cap).
_src = np.full(N, -1, np.int64); _dep = np.zeros(N)
if "cav_src" in me.attributes and "cav_depth" in me.attributes:
    _src = np.array([d.value for d in me.attributes["cav_src"].data], dtype=np.int64)
    _dep = np.array([d.value for d in me.attributes["cav_depth"].data], dtype=np.float64)
    print(f"cavity lineage: {int((_src >= 0).sum())} bag verts carry cav_src")
else:
    print("!! no cav_src/cav_depth — the bag CANNOT follow the lips and will tear if the "
          "rim moves. Re-run tools/mouth_open.py.")
_BAGI = np.where(_src >= 0)[0]

def propagate_bag(d):
    """Carry a rim displacement back into the mouth bag along its extrusion lineage.

    Full follow at the rim, decaying to zero at the back cap — so the bag stretches with the
    lips instead of tearing off them, and the cap stays put inside the skull. This is the
    displacement form of the weighting law jaw_rig.py already uses on the same lineage.
    """
    if not len(_BAGI):
        return d
    t = np.clip(_dep[_BAGI], 0.0, 1.0)
    d[_BAGI] = d[_src[_BAGI]] * (1.0 - t)[:, None]
    return d

REG = {k: W(k) for k in ("lip_upper","lip_lower","lip_corner_L","lip_corner_R",
                         "eyelid_upper_L","eyelid_lower_L","eyelid_upper_R","eyelid_lower_R",
                         "brow_L","brow_R","cheek_L","cheek_R","nose",
                         "op_jaw_region")}
for k, v in REG.items():
    if v.max() <= 0: print(f"  !! region {k} is EMPTY")

# ── shared helpers ────────────────────────────────────────────────────────────

def eye_out(tag):
    c, _, _ = EYE[tag]
    v = c - np.array([hc[0], hc[1], c[2]])
    return v / max(np.linalg.norm(v), 1e-9)

def lid_rotate(tag, which, amount, hold_front=True):
    """amount >0 closes toward midline; amount <0 opens. hold_front keeps r>=1.06r on close."""
    c, r, _ = EYE[tag]
    w = REG[f"eyelid_{which}_{tag}"]
    d = np.zeros((N, 3))
    u = eye_out(tag)
    for i in np.where((w > 0.01) & ~rigid_mask)[0]:
        rel = co[i] - c
        rad = float(np.linalg.norm(rel))
        if rad < 1e-9: continue
        al, be, ga = float(rel @ u), float(rel @ lat), float(rel @ up)
        th = -math.atan2(ga, al) * amount * float(w[i])
        ca_, sa = math.cos(th), math.sin(th)
        na, ng = al*ca_ - ga*sa, al*sa + ga*ca_
        nr = u*na + lat*be + up*ng
        n_ = np.linalg.norm(nr)
        if n_ > 1e-9:
            nr = nr / n_ * (max(rad, r*1.06) if hold_front else rad)
        d[i] = (c + nr) - co[i]
    return d

# ── ANTI-FOLD RELAXATION (2026-07-29) ────────────────────────────────────────
# MEASURED DEFECT. Rendering the open mouth at demo framing showed jagged black notches torn
# along the upper lip. Measuring the SKIN (not the cavity) found the cause: face normals
# INVERTING — the surface folding through itself. Each shape ALONE at 1.0:
#
#     mouthUpperUpRight 22 · lipTuckLower 23 · mouthPucker 21 · mouthUpperUpLeft 17
#     mouthFunnel 15 · mouthShrugUpper 14 · mouthSmileRight 13 ...
#
# It is NOT stacking — individual shapes fold on their own. When lip amplitude was doubled
# (0.012 -> 0.024) after the rim was unfrozen, the check made was CAVITY edge stretch (1.18x,
# well inside the rig's 3.85x) and nobody looked at skin normals. Same family of blind spot
# as the other four: the check looked where it was cheap to look.
#
# THE FIX IS NOT LOWER AMPLITUDE. The aperture was expensive — the jaw gave up three degrees
# to buy chin depth and the lips pay it back. A fold is a HIGH-FREQUENCY feature of the
# displacement field: neighbouring vertices moving in ways that cross. Smoothing the FIELD
# removes exactly that and leaves the low-frequency motion — the expression itself — intact.
# Peak magnitude is restored afterwards so the amplitude is not quietly given back.
_NI, _NJ = [], []
for _p in me.polygons:
    _vs = list(_p.vertices)
    for _k in range(len(_vs)):
        _i, _j = _vs[_k], _vs[(_k + 1) % len(_vs)]
        _NI += [_i, _j]; _NJ += [_j, _i]
_NI = np.asarray(_NI, dtype=np.int64); _NJ = np.asarray(_NJ, dtype=np.int64)
_DEG = np.bincount(_NI, minlength=N).astype(float); _DEG[_DEG == 0] = 1.0

def _nbr_avg(d):
    out = np.empty((N, 3))
    for c in range(3):
        out[:, c] = np.bincount(_NI, weights=d[_NJ, c], minlength=N)
    return out / _DEG[:, None]

_TRI = np.array([tuple(p.vertices)[:3] for p in me.polygons], dtype=np.int64)

def face_flips(d):
    """Count faces whose normal INVERTS under d — i.e. the surface folding through itself.

    The first triangle of each polygon is used as the proxy, consistently on both sides, so a
    non-planar quad cannot register as a flip by itself.
    """
    a, b, c = _TRI[:, 0], _TRI[:, 1], _TRI[:, 2]
    n0 = np.cross(co[b] - co[a], co[c] - co[a])
    P = co + d
    n1 = np.cross(P[b] - P[a], P[c] - P[a])
    return int((np.einsum('ij,ij->i', n0, n1) < 0).sum())

def relax(d, iters=6, lam=0.5, allow=None):
    """One smoothing pass over the mesh graph.

    ⚠️ NO PEAK RESTORATION. The first version rescaled the field back up to its original peak
    to "not give the amplitude back", and that MADE THINGS WORSE — `mouthSmileRight` went from
    13 flips to 25, because scaling the whole field uniformly pushes mid-field vertices past
    where they started and folds the surface somewhere else. Amplitude is recovered by
    authoring, not by rescaling a smoothed field.
    """
    mag = np.linalg.norm(d, axis=1)
    moving = mag > 1e-12
    if not moving.any():
        return d
    free = moving if allow is None else (moving & allow)
    out = d.copy()
    for _ in range(iters):
        a = _nbr_avg(out)
        out[free] += lam * (a[free] - out[free])
    return out

AMP_FLOOR = 0.85    # never trade more than 15% of a shape's travel to unfold it

# ⚠️ DEAD END — TRIED, MEASURED, REJECTED (2026-07-29). `unfold` is kept because the reasoning
# is worth having, but it is NOT called: the loop above only MEASURES folds now.
#
# What happened. Unbounded relaxation drives every fold to zero, and the cost is the shape:
# eyeBlinkLeft 43->0 flips while keeping 33% of its travel (6.41%H -> 2.12%H), which leaves
# the eye visibly open on a blink. With an 85% amplitude floor the big shapes simply refuse to
# unfold at all (they keep 100% amplitude AND 100% of their flips) and only the small lip
# rolls clear. Rendered before/after at demo framing, the "after" was NOT better — the
# aperture read smaller and the upper lip edge no less ragged.
#
# The deeper reason it cannot work: MOST FLIPS ARE NOT DEFECTS. A closing eyelid folds because
# that is what an eyelid does. The genuinely bad one — the jagged notch torn along the upper
# lip in open-mouth poses — is a TOPOLOGY limit, not a parameter one: there are not enough
# edge loops across the lip to absorb a 2.4%H lift without the surface crossing itself. The
# real fix is a retopology pass adding loops at the lip and the eyelid, which changes vertex
# count and therefore rebuilds the entire chain. That is a scoped job, not a tuning knob, and
# pretending a smoother solves it would be exactly the kind of minimal-fix-to-green this
# project forbids.

def unfold(d, allow=None, rounds=10, floor=AMP_FLOOR):
    """Relax until the surface stops folding, OR until the amplitude floor is reached.

    ⚠️ NOT EVERY FLIP IS A DEFECT, and the floor is what encodes that. A closing EYELID
    genuinely folds — that is what an eyelid does — and an unbounded version of this loop
    "fixed" 43 flips on `eyeBlinkLeft` by keeping 33% of its travel, which would leave the eye
    visibly open on a blink. Measured on the shipped build, most flips are benign lid-rolls
    and lip-rolls; the one that is NOT is the jagged notch torn along the upper lip in open-
    mouth poses. So: take the cheap unfolds, refuse the expensive ones, and SAY which is which
    instead of quietly gutting a shape to make a number go to zero.

    Returns (d, flips_before, flips_after, rounds_used, amplitude_retained).
    """
    f0 = face_flips(d)
    if f0 == 0:
        return d, f0, 0, 0, 1.0
    a0 = float(np.linalg.norm(d, axis=1).max())
    if a0 <= 1e-12:
        return d, f0, f0, 0, 1.0
    out, best = d, d
    for r in range(1, rounds + 1):
        cand = relax(out, allow=allow)
        amp = float(np.linalg.norm(cand, axis=1).max()) / a0
        if amp < floor:
            return best, f0, face_flips(best), r - 1, \
                   float(np.linalg.norm(best, axis=1).max()) / a0
        out = best = cand
        if face_flips(out) == 0:
            return out, f0, 0, r, amp
    return out, f0, face_flips(out), rounds, \
           float(np.linalg.norm(out, axis=1).max()) / a0

def wshift(w, du=0.0, df=0.0, dl=0.0):
    """Translate by a dense weight field along up / forward / lateral."""
    d = np.zeros((N, 3))
    vec = up*du + fwd*df + lat*dl
    m = (w > 0.01) & ~rigid_mask
    if m.any():
        d[m] = w[m, np.newaxis] * vec
    return d

def region_shift(name, du=0.0, df=0.0, dl=0.0):
    return wshift(REG[name], du=du, df=df, dl=dl)

def brow_move(tag, amp, focus="all"):
    c, r, _ = EYE[tag]
    w = REG[f"brow_{tag}"]
    eye_lat = float(c @ lat)
    side_outer = -1.0 if tag == "L" else 1.0
    ou = eye_out(tag)
    d = np.zeros((N, 3))
    for i in np.where((w > 0.01) & ~rigid_mask)[0]:
        t = ((float(co[i] @ lat) - eye_lat) * side_outer) / max(r * 1.8, 1e-9)
        if focus == "inner":
            sw = math.exp(-((t + 0.35)**2) / (2 * 0.38**2))
        elif focus == "outer":
            sw = math.exp(-((t - 0.40)**2) / (2 * 0.42**2))
        else:
            sw = 1.0
        mag = amp * H * float(w[i]) * sw
        d[i] = up * mag + ou * abs(mag) * (0.18 if mag > 0 else -0.08)
    return d

def lips_w():
    return np.maximum.reduce([REG["lip_upper"], REG["lip_lower"],
                              REG["lip_corner_L"], REG["lip_corner_R"]])

def mouth_center():
    w = lips_w()
    return (co * w[:, None]).sum(axis=0) / max(float(w.sum()), 1e-9)

def side_gate(tag, softness=0.028):
    """Soft half-face mask. tag 'L'/'R' — 1 on that side of the midplane, 0 on the other."""
    s = -1.0 if tag == "L" else 1.0
    t = (co @ lat - lat0) * s
    return np.clip(t / softness + 0.5, 0.0, 1.0)

def side_out(tag):
    """Lateral component pointing outward on that side of the face."""
    return (-1.0 if tag == "L" else 1.0)

def pucker_field(amp_in, amp_fwd, amp_vert=0.0):
    """Pull lips toward the mouth centre (amp_in), along forward (amp_fwd).
    amp_vert >0 separates upper/lower (funnel); <0 pinches them (press/close assist)."""
    w = lips_w()
    mc = mouth_center()
    d = np.zeros((N, 3))
    for i in np.where((w > 0.01) & ~rigid_mask)[0]:
        rel = co[i] - mc
        lat_c = float(rel @ lat)
        up_c = float(rel @ up)
        toward = -lat * lat_c - up * up_c * 0.35
        tn = float(np.linalg.norm(toward))
        if tn > 1e-9: toward = toward / tn
        vsep = up * amp_vert * (1.0 if up_c >= 0 else -1.0)
        d[i] = (toward * amp_in + fwd * amp_fwd + vsep) * float(w[i])
    return d

def expand_falloff(seed_w, reach, z_max=None):
    """Smoothstep falloff from a seed weight field. Hard binary regions tear at their
    edge (same lesson as the 1.0-next-to-0.0 lip rim) — jaw shapes MUST use this."""
    seeds = co[seed_w > 0.5]
    if len(seeds) == 0:
        seeds = co[seed_w > 0.05]
    if len(seeds) == 0:
        return np.zeros(N)
    dmin = np.full(N, 1e9)
    # chunked min-distance so we don't blow memory on 47k × seed
    step = 64
    for s0 in range(0, len(seeds), step):
        S = seeds[s0:s0+step]
        # (N, k, 3) → (N, k) norms → min
        diff = co[:, None, :] - S[None, :, :]
        dmin = np.minimum(dmin, np.linalg.norm(diff, axis=2).min(axis=1))
    t = np.clip(1.0 - dmin / max(reach, 1e-9), 0.0, 1.0)
    w = t * t * (3.0 - 2.0 * t)
    w[rigid_mask] = 0.0
    if z_max is not None:
        w[co[:, 2] > z_max] = 0.0
    return w

# ── Shape library ─────────────────────────────────────────────────────────────
SHAPES = {}

# ── A — eye blink ─────────────────────────────────────────────────────────────
SHAPES["eyeBlinkLeft"]  = lambda: lid_rotate("L", "upper", 1.0) + lid_rotate("L", "lower", 0.55)
SHAPES["eyeBlinkRight"] = lambda: lid_rotate("R", "upper", 1.0) + lid_rotate("R", "lower", 0.55)

# ── B — eye + brow ────────────────────────────────────────────────────────────
SHAPES["eyeSquintLeft"] = lambda: (
    lid_rotate("L", "upper", 0.20) + lid_rotate("L", "lower", 0.52)
    + region_shift("cheek_L", du=0.014*H, df=0.004*H)
)
SHAPES["eyeSquintRight"] = lambda: (
    lid_rotate("R", "upper", 0.20) + lid_rotate("R", "lower", 0.52)
    + region_shift("cheek_R", du=0.014*H, df=0.004*H)
)
SHAPES["eyeWideLeft"] = lambda: (
    lid_rotate("L", "upper", -0.48, hold_front=False)
    + lid_rotate("L", "lower", -0.34, hold_front=False)
)
SHAPES["eyeWideRight"] = lambda: (
    lid_rotate("R", "upper", -0.48, hold_front=False)
    + lid_rotate("R", "lower", -0.34, hold_front=False)
)
SHAPES["browDownLeft"]      = lambda: brow_move("L", amp=-0.026, focus="all")
SHAPES["browDownRight"]     = lambda: brow_move("R", amp=-0.026, focus="all")
SHAPES["browOuterUpLeft"]   = lambda: brow_move("L", amp=+0.030, focus="outer")
SHAPES["browOuterUpRight"]  = lambda: brow_move("R", amp=+0.030, focus="outer")
SHAPES["browInnerUp"]       = lambda: (
    brow_move("L", amp=+0.028, focus="inner") + brow_move("R", amp=+0.028, focus="inner")
)

# ── C — jaw (jawOpen is bone-backed — not authored) ───────────────────────────
# First pass translated the binary op_jaw_region and tore the lip rim open onto
# the cavity. Expand the seed into a SMOOTH falloff over the lower face so the
# chin moves as a soft unit — same rule as atlas weights (never binary).
_mc = mouth_center()
_mc_z = float(_mc[2])
_JAW_W = expand_falloff(
    np.maximum(REG["op_jaw_region"], REG["lip_lower"]),
    reach=H * 0.065,
    z_max=_mc_z + H * 0.035,   # stop below the nose / eyes
)
# Lower bag / floor of the cavity rides the jaw; upper bag stays with the skull.
LOWER_CAV = {i for i in BAG if co[i, 2] < _mc_z + 0.006}
UPPER_CAV = BAG - LOWER_CAV
JAW_RIDE = TEETH_L | TONGUE | LOWER_CAV
# The rim is deliberately absent here too: jaw* shapes may move the lip edge like any other
# mouth shape, and the bag is then carried by lineage rather than by this rigid ride.
always_mask = np.zeros(N, bool)
always_mask[np.array(sorted(EYEBALL | TEETH_U | UPPER_CAV), dtype=int)] = True
print(f"jaw falloff: {(_JAW_W > 0.05).sum()} verts peak={_JAW_W.max():.2f}  "
      f"jaw-ride interior {len(JAW_RIDE)} (lower teeth+tongue+lower bag)")

def _jaw(df=0.0, dl=0.0, du=0.0):
    """Soft lower-face translate + rigid ride for jaw-anchored interior."""
    d = wshift(_JAW_W, du=du, df=df, dl=dl)
    ride = up*du + fwd*df + lat*dl
    for i in JAW_RIDE:
        d[i] = ride
    return d

SHAPES["jawForward"] = lambda: _jaw(df=0.014*H, du=-0.003*H)
SHAPES["jawLeft"]    = lambda: _jaw(dl=-0.014*H)
SHAPES["jawRight"]   = lambda: _jaw(dl=+0.014*H)
JAW_SHAPES = {"jawForward", "jawLeft", "jawRight"}

# ── C — mouth ─────────────────────────────────────────────────────────────────
# Amplitudes kept modest: opening the lip slit past ~1%H reveals the cavity and
# the (protected, unmoved) teeth as white spikes. Smiles/corners are safer than
# vertical separation.
def _smile(tag):
    o = side_out(tag)
    return (
        region_shift(f"lip_corner_{tag}", du=0.022*H, dl=o*0.014*H, df=0.003*H)
        + wshift(REG["lip_upper"] * side_gate(tag), du=0.006*H, dl=o*0.003*H)
        + wshift(REG["lip_lower"] * side_gate(tag), du=0.005*H, dl=o*0.003*H)
        + region_shift(f"cheek_{tag}", du=0.008*H, df=0.002*H)
    )

def _frown(tag):
    o = side_out(tag)
    return (
        region_shift(f"lip_corner_{tag}", du=-0.014*H, dl=o*0.005*H, df=-0.001*H)
        + wshift(REG["lip_lower"] * side_gate(tag), du=-0.004*H)
    )

def _stretch(tag):
    o = side_out(tag)
    # corner-led, not a whole-lip yank — whole-lip lateral tore the commissure
    return (
        region_shift(f"lip_corner_{tag}", dl=o*0.016*H, du=-0.001*H)
        + wshift(REG["lip_upper"] * side_gate(tag, softness=0.035), dl=o*0.005*H)
        + wshift(REG["lip_lower"] * side_gate(tag, softness=0.035), dl=o*0.005*H)
    )

def _dimple(tag):
    o = side_out(tag)
    return (
        region_shift(f"cheek_{tag}", df=-0.008*H, dl=o*0.006*H, du=0.004*H)
        + region_shift(f"lip_corner_{tag}", dl=o*0.005*H, du=0.003*H, df=-0.002*H)
    )

# ── LIP OPENING AMPLITUDE ────────────────────────────────────────────────────
# These two carry the mouth aperture that the jaw no longer can — the jaw is capped at 10°
# by the shirt collar (see ENVELOPE["jaw"] in control_surface.py), so how far the lips part
# is set HERE, not by the rig.
#
# They were 0.012H / 0.010H, chosen while the lip rim was still WELDED, when no amount of
# amplitude could move the lip edge at all and the numbers only had to look sane. With the
# rim freed they became the real ceiling: full-strength mouthUpperUp* + mouthLowerDown*
# yielded only 1.18%H of aperture, ~55% of nominal after the region taper.
# Raising them is the cheapest aperture in the build — no collar cost, no jaw rotation.
LIP_UP_AMP   = 0.024      # was 0.012
LIP_DOWN_AMP = 0.020      # was 0.010
LIP_CORNER_UP, LIP_CORNER_DOWN = 0.009, 0.008    # were 0.005 / 0.004
# 2x, not 3x. Measured: 2x gives 2.35%H of lip-driven aperture at 1.18x max cavity edge
# stretch; 3x gives 3.52%H at 1.27x — numerically still safe, and the numbers are why it is
# worth saying that the RENDER rejected it. At 3x the upper lip lifts far enough to drag the
# muzzle pad with it and the whole face distorts. The mesh limit and the character limit are
# not the same limit, and here the character's is tighter.

def _upper_up(tag):
    o = side_out(tag)
    return (
        wshift(REG["lip_upper"] * side_gate(tag), du=LIP_UP_AMP*H, df=0.003*H)
        + region_shift(f"lip_corner_{tag}", du=LIP_CORNER_UP*H, dl=o*0.002*H)
    )

def _lower_down(tag):
    o = side_out(tag)
    return (
        wshift(REG["lip_lower"] * side_gate(tag), du=-LIP_DOWN_AMP*H, df=0.001*H)
        + region_shift(f"lip_corner_{tag}", du=-LIP_CORNER_DOWN*H, dl=o*0.002*H)
    )

def _press(tag):
    """Lips pressed on one side — toward each other + slight back."""
    g = side_gate(tag)
    return (
        wshift(REG["lip_upper"] * g, du=-0.006*H, df=-0.005*H)
        + wshift(REG["lip_lower"] * g, du=+0.006*H, df=-0.005*H)
        + region_shift(f"lip_corner_{tag}", df=-0.004*H)
    )

SHAPES["mouthSmileLeft"]      = lambda: _smile("L")
SHAPES["mouthSmileRight"]     = lambda: _smile("R")
SHAPES["mouthFrownLeft"]      = lambda: _frown("L")
SHAPES["mouthFrownRight"]     = lambda: _frown("R")
SHAPES["mouthStretchLeft"]    = lambda: _stretch("L")
SHAPES["mouthStretchRight"]   = lambda: _stretch("R")
SHAPES["mouthDimpleLeft"]     = lambda: _dimple("L")
SHAPES["mouthDimpleRight"]    = lambda: _dimple("R")
SHAPES["mouthUpperUpLeft"]    = lambda: _upper_up("L")
SHAPES["mouthUpperUpRight"]   = lambda: _upper_up("R")
SHAPES["mouthLowerDownLeft"]  = lambda: _lower_down("L")
SHAPES["mouthLowerDownRight"] = lambda: _lower_down("R")
SHAPES["mouthPressLeft"]      = lambda: _press("L")
SHAPES["mouthPressRight"]     = lambda: _press("R")

# pucker: pinch + forward; keep slit closed (amp_vert negative)
SHAPES["mouthPucker"] = lambda: pucker_field(amp_in=0.012*H, amp_fwd=0.014*H, amp_vert=-0.005*H)
# funnel: forward "oo" — modest open, not a full gape onto the teeth
SHAPES["mouthFunnel"] = lambda: (
    pucker_field(amp_in=-0.004*H, amp_fwd=0.016*H, amp_vert=0.006*H)
    + region_shift("lip_corner_L", dl=-0.004*H, df=0.006*H)
    + region_shift("lip_corner_R", dl=+0.004*H, df=0.006*H)
)
SHAPES["mouthRollUpper"] = lambda: (
    region_shift("lip_upper", df=-0.010*H, du=-0.003*H)
    + wshift(REG["lip_corner_L"], df=-0.005*H) + wshift(REG["lip_corner_R"], df=-0.005*H)
)
SHAPES["mouthRollLower"] = lambda: (
    region_shift("lip_lower", df=-0.010*H, du=+0.003*H)
    + wshift(REG["lip_corner_L"], df=-0.005*H) + wshift(REG["lip_corner_R"], df=-0.005*H)
)
SHAPES["mouthShrugUpper"] = lambda: (
    region_shift("lip_upper", du=0.012*H, df=0.005*H)
    + wshift(REG["nose"] * 0.20, du=0.003*H)
)
SHAPES["mouthShrugLower"] = lambda: (
    region_shift("lip_lower", du=0.010*H, df=0.003*H)
)
SHAPES["mouthClose"] = lambda: (
    region_shift("lip_upper", du=-0.008*H, df=-0.002*H)
    + region_shift("lip_lower", du=+0.008*H, df=-0.002*H)
    + region_shift("lip_corner_L", df=-0.001*H)
    + region_shift("lip_corner_R", df=-0.001*H)
)
# lateral mouth shift — expand slightly so cheeks ride along without a hard edge
_MOUTH_LAT = expand_falloff(lips_w(), reach=H*0.040, z_max=float(_mc[2])+H*0.050)
SHAPES["mouthLeft"] = lambda: (
    wshift(_MOUTH_LAT, dl=-0.014*H)
    + region_shift("cheek_L", dl=-0.005*H) + region_shift("cheek_R", dl=-0.003*H)
)
SHAPES["mouthRight"] = lambda: (
    wshift(_MOUTH_LAT, dl=+0.014*H)
    + region_shift("cheek_R", dl=+0.005*H) + region_shift("cheek_L", dl=+0.003*H)
)

# ── D — cheek / nose / tongue (completes the authored head) ───────────────────
def _cheek_puff(tag=None):
    """Inflate the cheek(s) outward. tag=None → both."""
    tags = ("L", "R") if tag is None else (tag,)
    d = np.zeros((N, 3))
    for t in tags:
        o = side_out(t)
        d = d + region_shift(f"cheek_{t}", df=0.022*H, dl=o*0.010*H, du=0.003*H)
    return d

def _cheek_squint(tag):
    """Raise the cheek toward the eye — the lower-face half of a smile-squint."""
    o = side_out(tag)
    return (
        region_shift(f"cheek_{tag}", du=0.014*H, df=0.004*H, dl=o*0.003*H)
        + lid_rotate(tag, "lower", 0.28)
        + region_shift(f"lip_corner_{tag}", du=0.004*H, dl=o*0.002*H)
    )

def _nose_sneer(tag):
    """Lift one side of the nose + a little of the upper lip under it."""
    o = side_out(tag)
    g = side_gate(tag, softness=0.030)
    return (
        wshift(REG["nose"] * g, du=0.012*H, df=0.004*H, dl=o*0.003*H)
        + wshift(REG["lip_upper"] * g, du=0.006*H, dl=o*0.002*H)
        + wshift(REG[f"cheek_{tag}"] * 0.35, du=0.005*H)
    )

# How far past the lip plane the tip finishes, once the measured gap is paid for.
TONGUE_PROTRUDE = 0.032      # of H, beyond the lip rim front
TONGUE_ROOT_HOLD = 0.12      # travel retained at the root (0 = pinned, 1 = rigid slab)
TONGUE_NARROW = 0.22         # lateral pinch at full extension — an extended tongue narrows

def _tongue_out():
    """Extend the tongue out through the lip slit. Allowed to move tongue verts (normally
    protected) — that is the whole point of this shape.

    THE PREVIOUS VERSION COULD NOT WORK, and the reason is worth keeping: it translated the
    whole tongue RIGIDLY by a hard-coded 0.048H, a number reasoned from the teeth INSET
    (0.030) rather than from where the tongue actually was. Measured on the delivered body
    blend, the tip sat 9.31%H behind the lip rim, so 4.80%H of travel finished 5.29%H SHORT
    and `tongueOut` only ever showed a red patch through the slit. It was answering a
    question nobody had asked.

    Two changes. First the travel is MEASURED here, every build, from the actual gap between
    the tip and the lip rim — so it cannot silently go stale when the mouth changes. Second
    it is a DEFORMATION, not a slab: travel ramps from the root (which stays anchored in the
    floor of the mouth, as a real tongue root does) to the tip. A rigid slide would drag the
    root out of the bag floor and leave a hole behind it.
    """
    d = np.zeros((N, 3))
    if TONGUE:
        ti = np.array(sorted(TONGUE), dtype=int)
        tf = co[ti] @ fwd
        f0, f1 = float(tf.min()), float(tf.max())
        # s = 0 at the root, 1 at the tip
        s = (tf - f0) / max(f1 - f0, 1e-9)
        ramp = TONGUE_ROOT_HOLD + (1.0 - TONGUE_ROOT_HOLD) * s**1.3

        # THE TRAVEL, measured — not a constant.
        rim_i = np.array(sorted(RIM), dtype=int)
        lip_front = float((co[rim_i] @ fwd).max())
        gap = lip_front - f1
        travel = gap + TONGUE_PROTRUDE * H

        # ... and the height, so the tip emerges through the SLIT rather than through the
        # chin: aim the tip at the vertical centre of the lip rim.
        z_slit = float(co[rim_i, 2].mean())
        z_tip = float(co[ti][np.argmax(tf), 2])
        lift = z_slit - z_tip

        c_lat = float((co[ti] @ lat).mean())
        for k, i in enumerate(ti):
            r = float(ramp[k])
            dl = float(co[i] @ lat) - c_lat
            d[i] = (fwd * (travel * r)
                    + up * (lift * r)
                    + lat * (-dl * TONGUE_NARROW * r))
        print(f"  tongueOut: gap {gap:+.4f} ({100*gap/H:.2f}%H) + protrude "
              f"{TONGUE_PROTRUDE*H:.4f} -> travel {travel:.4f} ({100*travel/H:.2f}%H), "
              f"lift {lift:+.4f}, root holds {TONGUE_ROOT_HOLD:.2f}")

    # Open the slit so the tongue is visible (not ghosting through sealed lips). Widened
    # after the render: the tip was measurably past the lip plane and still barely read from
    # the FRONT, because it was emerging through a slit that had hardly moved. Cheaper in
    # stretch than pushing the tongue further, and it is what a mouth actually does.
    d = d + region_shift("lip_lower", du=-0.020*H, df=0.008*H)
    d = d + region_shift("lip_upper", du=+0.011*H, df=0.004*H)
    d = d + region_shift("lip_corner_L", du=0.0, df=0.003*H)
    d = d + region_shift("lip_corner_R", du=0.0, df=0.003*H)
    return d

# ── TONGUE ARTICULATION + LIP TUCK — extension beyond ARKit-52 (2026-07-29) ──
# WHY THESE EXIST, measured. tools/viseme_distinct.py compared all 105 pinned viseme pairs
# for the first time and found the consonants collapsing onto silence:
#
#     DD/kk 0.17%H · CH/RR 0.23%H · SS/nn 0.25%H · sil/FF 0.25%H
#
# "f/v" was literally the same shape as saying nothing. Every collapsed pair is a
# TONGUE-POSITION or lip-to-teeth distinction — and the tongue had exactly ONE morph
# (`tongueOut`), which can only slide it forward. The vowels were fine because the jaw and
# the lips carry them; the consonants had nothing carrying them at all.
#
# ARKit-52 ships `tongueOut` and no other tongue control, so these four are a documented
# EXTENSION. They are ADDITIVE: the 43 ARKit keys are untouched, the drive contract's 38
# required morphs all still exist, and a consumer that only knows ARKit ignores these and
# gets exactly what it got before.
#
# EVERY MAGNITUDE IS DERIVED FROM MEASURED HEADROOM, not asserted. This cavity is shallow at
# the front (the bag converges on the lip slit), so a hard-coded lift that looked right at
# the root would drive the tip straight through the palate. Each vertex moves a fraction of
# ITS OWN distance to the local ceiling.

def _tongue_geom():
    """Tongue vertices with s = 0 at the root, 1 at the tip."""
    ti = np.array(sorted(TONGUE), dtype=int)
    tf = co[ti] @ fwd
    f0, f1 = float(tf.min()), float(tf.max())
    return ti, (tf - f0) / max(f1 - f0, 1e-9)

def _cavity_ceiling(fvals):
    """Local cavity ceiling at each fore-aft position, ducking under the upper teeth.

    Same windowed sampling mouth_parts.py uses to fit the tongue in the first place — the
    bag is only 186 verts, so a fixed bin returns empty slices on the sparse parts.
    """
    cavl = np.array(sorted(CAVITY), dtype=int)
    cf = co[cavl] @ fwd; cz = co[cavl, 2]
    tu = np.array(sorted(TEETH_U), dtype=int)
    uf = co[tu] @ fwd if len(tu) else np.array([])
    uz = co[tu, 2] if len(tu) else np.array([])
    lo, hi = float(cf.min()), float(cf.max())
    win = (hi - lo) * 0.15
    out = np.empty(len(fvals))
    for k, f in enumerate(fvals):
        m = np.abs(cf - f) <= win
        if int(m.sum()) < 4:
            idx = np.argsort(np.abs(cf - f))[:8]
            m = np.zeros(len(cf), bool); m[idx] = True
        c = float(cz[m].max())
        if len(uf):
            n = np.abs(uf - f) <= 0.010
            if int(n.sum()):
                c = min(c, float(uz[n].min()))
        out[k] = c
    return out

TONGUE_ART_CLEAR = 0.0020   # stand-off held from the local ceiling at full strength

def _tongue_raise(ramp_fn, fill, label):
    """Raise part of the tongue toward the roof of the mouth by a fraction of ITS headroom."""
    d = np.zeros((N, 3))
    if not TONGUE:
        return d
    ti, s = _tongue_geom()
    ceil = _cavity_ceiling(co[ti] @ fwd)
    head = np.maximum(ceil - TONGUE_ART_CLEAR - co[ti, 2], 0.0)
    r = ramp_fn(s)
    for k, i in enumerate(ti):
        d[i] = up * (fill * float(head[k]) * float(r[k]))
    mv = float(np.abs(d[ti]).max())
    print(f"  {label}: headroom max {head.max():.4f} ({100*head.max()/H:.2f}%H), "
          f"peak lift {mv:.4f} ({100*mv/H:.2f}%H)")
    return d

def _tongue_up():
    """Tip to the alveolar ridge — the /d/ /t/ /n/ /l/ /s/ position."""
    return _tongue_raise(lambda s: np.clip((s - 0.30) / 0.70, 0.0, 1.0) ** 1.4, 0.85, "tongueUp")

def _tongue_back():
    """Back of the tongue humps to the soft palate — the /k/ /g/ velar position.

    This one has the most room to work in (the bag is deepest at the back), which is exactly
    why DD vs kk was the tightest collapsed pair: nothing was using it.
    """
    return _tongue_raise(lambda s: np.clip((0.55 - s) / 0.55, 0.0, 1.0) ** 1.2, 0.80, "tongueBack")

def _tongue_curl():
    """Blade raised behind the tip — the postalveolar /sh/ /ch/ /r/ position."""
    return _tongue_raise(lambda s: np.exp(-((s - 0.58) / 0.24) ** 2), 0.75, "tongueCurl")

def _lip_tuck_lower():
    """Lower lip rolls UP and BACK against the upper teeth — the /f/ /v/ position.

    FF had been carried by `mouthRollLower` alone, which is a symmetric roll of both lips and
    measured 0.25%H from silence — indistinguishable. Labiodental needs the lower lip to go
    somewhere specific (behind the upper teeth) while the upper lip lifts clear of them.
    """
    return (region_shift("lip_lower", du=+0.016*H, df=-0.011*H)
            + region_shift("lip_corner_L", du=+0.004*H, df=-0.003*H)
            + region_shift("lip_corner_R", du=+0.004*H, df=-0.003*H)
            + region_shift("lip_upper", du=+0.007*H, df=+0.002*H))

SHAPES["tongueUp"]      = lambda: _tongue_up()
SHAPES["tongueBack"]    = lambda: _tongue_back()
SHAPES["tongueCurl"]    = lambda: _tongue_curl()
SHAPES["lipTuckLower"]  = lambda: _lip_tuck_lower()

SHAPES["cheekPuff"]        = lambda: _cheek_puff(None)
SHAPES["cheekSquintLeft"]  = lambda: _cheek_squint("L")
SHAPES["cheekSquintRight"] = lambda: _cheek_squint("R")
SHAPES["noseSneerLeft"]    = lambda: _nose_sneer("L")
SHAPES["noseSneerRight"]   = lambda: _nose_sneer("R")
SHAPES["tongueOut"]        = lambda: _tongue_out()

# tongueOut may move the tongue; jaw* may move jaw-anchored interior.
# The three articulation shapes move the tongue too, so they need the same exception —
# lipTuckLower does NOT, it only touches lip skin, which is already free.
TONGUE_SHAPES = {"tongueOut", "tongueUp", "tongueBack", "tongueCurl"}

# Combo renders for the full-head sheet
COMBOS = {
    "BOTH_blink":     ["eyeBlinkLeft", "eyeBlinkRight"],
    "BOTH_squint":    ["eyeSquintLeft", "eyeSquintRight"],
    "BOTH_wide":      ["eyeWideLeft", "eyeWideRight"],
    "BOTH_browDown":  ["browDownLeft", "browDownRight"],
    "BOTH_browOuter": ["browOuterUpLeft", "browOuterUpRight"],
    "BOTH_smile":     ["mouthSmileLeft", "mouthSmileRight"],
    "BOTH_frown":     ["mouthFrownLeft", "mouthFrownRight"],
    "BOTH_stretch":   ["mouthStretchLeft", "mouthStretchRight"],
    "BOTH_dimple":    ["mouthDimpleLeft", "mouthDimpleRight"],
    "BOTH_upperUp":   ["mouthUpperUpLeft", "mouthUpperUpRight"],
    "BOTH_lowerDown": ["mouthLowerDownLeft", "mouthLowerDownRight"],
    "BOTH_press":     ["mouthPressLeft", "mouthPressRight"],
    "BOTH_cheekSquint": ["cheekSquintLeft", "cheekSquintRight"],
    "BOTH_noseSneer":   ["noseSneerLeft", "noseSneerRight"],
}

names = [n for n in (WANT or list(SHAPES)) if n in SHAPES]
missing = [n for n in (WANT or []) if n not in SHAPES]
if missing:
    print(f"!! unknown shape names ignored: {missing}")
print(f"authoring {len(names)} shape(s): {names}")
if me.shape_keys is None:
    ob.shape_key_add(name="Basis", from_mix=False)
else:
    ob.shape_key_clear()
    ob.shape_key_add(name="Basis", from_mix=False)

report = []
for n in names:
    d = SHAPES[n]()
    # ANTI-FOLD PASS. Skin shapes only: jaw* and tongue* carry deliberate RIGID rides
    # (the whole lower arch, the whole tongue) and smoothing those would soften a motion
    # that is supposed to be rigid. Everything else is surface deformation, where a fold is
    # always a defect.
    # FOLD IS MEASURED AND REPORTED, NOT "FIXED". See the note on `unfold` — smoothing the
    # displacement field was tried, measured, and rejected on the render.
    fold_note = ""
    if n not in JAW_SHAPES and n not in TONGUE_SHAPES:
        _f = face_flips(d)
        if _f:
            fold_note = f"  [folds {_f}]"
    # Per-shape protect exceptions (match the bone-anchored interior membership):
    #   jaw*      → may move teeth_lower + tongue + lower bag
    #   tongueOut → may move tongue
    #   else      → full rigid_mask
    if n in JAW_SHAPES:
        d[always_mask] = 0.0
        leak_mask = always_mask
    elif n in TONGUE_SHAPES:
        # protect everything rigid EXCEPT the tongue itself
        tongue_mask = np.zeros(N, bool)
        if TONGUE:
            tongue_mask[np.array(sorted(TONGUE), dtype=int)] = True
        leak = rigid_mask & ~tongue_mask
        d[leak] = 0.0
        leak_mask = leak
    else:
        d[rigid_mask] = 0.0
        leak_mask = rigid_mask
    # The bag is zeroed by every mask above, then RE-DERIVED from wherever the lip rim
    # ended up. It must run after masking, and it is the only thing permitted to write into
    # bag verts — that is what keeps the bag welded to the lips instead of tearing off them.
    d = propagate_bag(d)
    leak_mask = leak_mask & ~np.isin(np.arange(N), _BAGI)
    sk = ob.shape_key_add(name=n, from_mix=False)
    tgt = co + d
    for i in np.where(np.linalg.norm(d, axis=1) > 1e-9)[0]:
        sk.data[int(i)].co = Vector(tgt[i])
    moved = int((np.linalg.norm(d, axis=1) > 1e-6).sum())
    mx = float(np.linalg.norm(d, axis=1).max())
    rigid_moved = int((np.linalg.norm(d[leak_mask], axis=1) > 1e-9).sum())
    report.append((n, moved, mx, rigid_moved))
    print(f"  {n:22s} moved {moved:5d} verts, max {mx:.4f} ({100*mx/H:.2f}% of height), "
          f"protected verts moved {rigid_moved} {'OK' if rigid_moved == 0 else '** LEAK **'}"
          f"{fold_note}")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_shapes.blend"))

# ── Renders — face frame centred between eyes and mouth ───────────────────────
sc = bpy.context.scene
for o in [x for x in bpy.data.objects if x.type == 'ARMATURE']: o.hide_render = True
for o in [x for x in bpy.data.objects if x.type == 'CAMERA']: bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 700
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = 0.32
eyez = float((EYE["L"][0][2] + EYE["R"][0][2])/2)
mz = float(mouth_center()[2])
facez = 0.55*eyez + 0.45*mz
Rr = H*5
cam.location = (hc[0]+math.sin(a)*Rr, hc[1]-math.cos(a)*Rr, facez)
cam.rotation_euler = (math.radians(90), 0, a)
kb = me.shape_keys.key_blocks

def zero():
    for k in kb: k.value = 0.0

def render_pose(path, active):
    zero()
    for n in active:
        if n in kb: kb[n].value = 1.0
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

zero()
sc.render.filepath = os.path.join(OUT, "s_REST.png"); bpy.ops.render.render(write_still=True)
for n in names:
    render_pose(os.path.join(OUT, f"s_{n}.png"), [n])
for cname, members in COMBOS.items():
    if all(m in names for m in members):
        render_pose(os.path.join(OUT, f"s_{cname}.png"), members)

print("ok")
print("REPORT")
leaks = 0
for n, moved, mx, rigid_moved in report:
    leaks += rigid_moved
    print(f"  {n:22s}  verts={moved:5d}  max={mx:.4f} ({100*mx/H:.2f}%H)  protected={rigid_moved}")
print(f"TOTAL shapes {len(report)}  protected_leaks {leaks}")
