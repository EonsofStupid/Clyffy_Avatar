"""Reshape the head to canon proportions. DISPLACEMENT ONLY — vertex indices preserved.

    blender -b --python tools/head_proportion.py -- <canon.blend> <out_dir> [fwd] \
        [--neck K] [--squash K] [--widen K] [--measure]

Runs at chain position 1.5 — AFTER `canonicalize`, BEFORE `mouth_open`.

═══ WHY HERE AND NOT ON THE FINISHED BODY ═══════════════════════════════════════════════════

Operator, 2026-08-01: *"the head is long when it needs to be short"*, and earlier *"you have
never really captured his mouth"*. Measured against `canon/face_ref/FACE_REF_front.png`, our head
is ~44% too narrow for its height, and the excess sits below the mouth: the jaw/throat runs 28%
of head height under the lip where the reference runs ~14%. That also drags the mouth to 72% down
the head instead of ~87%, which is a large part of why the mouth never reads right — it is placed
wrong, not only shaped wrong.

This CANNOT be done on the delivered body. All 47 shape keys are DELTAS authored against the
current geometry; reshaping underneath them would leave every delta scaled wrong for its new
neighbourhood. `chin_mass.py` is a displacement stage at position 3 for exactly this reason. So
the proportion change goes in early and the twelve downstream stages re-run.

═══ HOW ════════════════════════════════════════════════════════════════════════════════════

A piecewise-linear Z REMAP, not a free-form sculpt:

    * band [z_bot, z_top] is compressed by `neck`
    * everything ABOVE the band translates down by exactly what the band lost
    * everything BELOW is untouched — the legs stay on the ground

Compressing a band without translating what sits above it would tear the mesh apart, so the
translation is not a nicety. Nothing is scaled about an arbitrary origin.

The head itself then gets an independent vertical `squash` and lateral `widen`, both applied
about the head's own centre with a smooth falloff into the neck so no crease appears at the
boundary.

DISPLACEMENT ONLY: vertex count, indices, face count and both operator vertex groups
(`op_jaw_region`, `op_lip_seam`) are asserted unchanged, so every downstream stage still finds
what it expects.
"""
import bpy, sys, os, math
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2]) if len(argv) > 2 and not argv[2].startswith("--") else 235.1


def opt(name, default):
    return float(argv[argv.index(name) + 1]) if name in argv else default


NECK = opt("--neck", 0.55)      # keep this fraction of the jaw->collar band
SQUASH = opt("--squash", 1.00)  # vertical scale of the head itself
WIDEN = opt("--widen", 1.00)    # lateral scale of the head itself
MEASURE_ONLY = "--measure" in argv
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N = len(me.vertices)
F = len(me.polygons)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
co0 = co.copy()
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
lp = co @ lat
z = co[:, 2]

GRP0 = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index)
        for g in ob.vertex_groups}
gi = {g.name: g.index for g in ob.vertex_groups}


def group_mask(name):
    m = np.zeros(N, bool)
    if name not in gi:
        return m
    want = gi[name]
    for v in me.vertices:
        for g in v.groups:
            if g.group == want and g.weight > 0.5:
                m[v.index] = True
                break
    return m


lip = group_mask("op_lip_seam")
assert lip.sum() > 20, "op_lip_seam missing — is this the canonicalised mesh?"
z_lip = float(z[lip].mean())
lat0 = float(np.median(lp[z > z_lip]))


def width_at(zz, half=0.008):
    m = np.abs(z - zz) < half
    return float(np.ptp(lp[m])) if m.sum() >= 8 else 0.0


# ── landmarks, from the mesh's own width profile ─────────────────────────────
# The head is the wide mass above the neck; the neck is the local MINIMUM of lateral width
# between the jaw and the shoulders. Found by scanning rather than assumed, because a hard-coded
# z would silently drift the moment the mesh changes.
# Scan ONLY the head — above the lip seam for the skull, and a narrow band below it for the
# neck. Scanning the whole figure put the "widest point" at the HIPS (z = -0.16, width 0.568)
# and produced a head 163% tall with the mouth above its own crown. The body is wider than the
# head; the search has to be told where the head is.
head_zs = np.linspace(z.max(), z_lip, 160)
prof = [(zz, width_at(zz)) for zz in head_zs]
prof = [(zz, w) for zz, w in prof if w > 0]
ear_z, ear_w = max(prof, key=lambda t: t[1])                       # widest = the ear line
above = [(zz, w) for zz, w in prof if zz > ear_z]
# HIGHEST z where the skull is still wide — not the lowest. Taking the min clipped the head
# at the ear line and threw away the entire forehead, reporting a head only 0.156 tall with the
# mouth 95% down it.
crown_z = max((zz for zz, w in above if w > 0.55 * ear_w), default=ear_z)

# neck = narrowest point in the band just below the lip, before the shoulders flare
neck_zs = np.linspace(z_lip + 0.01 * H, z_lip - 0.16 * H, 120)
nprof = [(zz, width_at(zz)) for zz in neck_zs]
nprof = [(zz, w) for zz, w in nprof if w > 0]
neck_z, neck_w = min(nprof, key=lambda t: t[1]) if nprof else (z_lip, 0.0)

print(f"head_proportion: {os.path.basename(SRC)}  verts {N}  H={H:.4f}")
print(f"  lip seam z      {z_lip:.4f}")
print(f"  ear line z      {ear_z:.4f}  width {ear_w:.4f}   <- widest point")
print(f"  neck z          {neck_z:.4f}  width {neck_w:.4f}   <- narrowest below the head")
print(f"  skull crown z   {crown_z:.4f}  (excludes horns)")
head_h = crown_z - neck_z
print(f"  HEAD HEIGHT     {head_h:.4f}   ear-to-ear {ear_w:.4f}   ASPECT {ear_w/max(head_h,1e-9):.2f}")
print(f"  mouth sits      {100*(crown_z - z_lip)/max(head_h,1e-9):.0f}% down the head")
print(f"  REFERENCE       aspect 1.48, mouth 87% down "
      f"(canon/face_ref/FACE_REF_front.png, read off a gridded overlay)")

if MEASURE_ONLY:
    print("\n--measure: nothing written")
    raise SystemExit(0)

# ── 1. neck band compression ─────────────────────────────────────────────────
# The band runs from the collar up to the jaw's narrowest point. Compressing it pulls the head
# DOWN onto the shoulders, which is what the reference shows: chin meets collar, no column.
COLLAR = z_lip - 0.090 * H          # pack SSOT: the shirt collar sits 9.00%H below the lip
z_top, z_bot = neck_z, COLLAR
band = max(z_top - z_bot, 1e-6)
lost = band * (1.0 - NECK)
newz = z.copy()
inband = (z >= z_bot) & (z < z_top)
newz[inband] = z_bot + (z[inband] - z_bot) * NECK
newz[z >= z_top] = z[z >= z_top] - lost
print(f"\n  neck band {z_bot:.4f}..{z_top:.4f} x{NECK}  -> removed {lost:.4f} "
      f"({100*lost/H:.2f}%H); everything above translates down by the same amount")

co[:, 2] = newz
z2 = co[:, 2]
crown2 = crown_z - lost
neck2 = z_bot + (neck_z - z_bot) * NECK
lip2 = z_lip - lost

# ── 2. head squash / widen, about the head's own centre ──────────────────────
# Weighted so the effect fades to nothing by the neck: a hard cut here would crease the throat.
if abs(SQUASH - 1.0) > 1e-6 or abs(WIDEN - 1.0) > 1e-6:
    t = np.clip((z2 - neck2) / max(crown2 - neck2, 1e-9), 0.0, 1.0)
    w = t * t * (3.0 - 2.0 * t)                       # smoothstep, 0 at the neck, 1 at the crown
    zc = 0.5 * (crown2 + neck2)
    co[:, 2] = zc + (z2 - zc) * (1.0 + (SQUASH - 1.0) * w)
    d = (lp - lat0) * ((WIDEN - 1.0) * w)
    co[:, 0] += lat[0] * d
    co[:, 1] += lat[1] * d
    print(f"  head squash x{SQUASH} / widen x{WIDEN}, smoothstepped from the neck to the crown")

me.vertices.foreach_set("co", co.ravel())
me.update()

# ── gate ─────────────────────────────────────────────────────────────────────
# RE-MEASURES the deformed mesh with the same landmark scan used before. The first version
# PREDICTED the result analytically and got it backwards — it reported the aspect rising
# 1.85 -> 1.98 -> 2.05 as the head was squashed shorter, because it recomputed the ear width at
# a z the ears had already moved away from. A gate that predicts instead of measuring is not a
# gate.
zf = co[:, 2]
lpf = co @ lat
lip_f = float(zf[lip].mean())


def width_at_f(zz, half=0.008):
    m = np.abs(zf - zz) < half
    return float(np.ptp(lpf[m])) if m.sum() >= 8 else 0.0


hz = np.linspace(zf.max(), lip_f, 160)
pf = [(zz, width_at_f(zz)) for zz in hz]
pf = [(zz, w) for zz, w in pf if w > 0]
ear_zf, ear_wf = max(pf, key=lambda t: t[1])
abv = [(zz, w) for zz, w in pf if zz > ear_zf]
crown_f = max((zz for zz, w in abv if w > 0.55 * ear_wf), default=ear_zf)
nz = np.linspace(lip_f + 0.01 * H, lip_f - 0.16 * H, 120)
nf = [(zz, width_at_f(zz)) for zz in nz]
nf = [(zz, w) for zz, w in nf if w > 0]
neck_f = min(nf, key=lambda t: t[1])[0] if nf else lip_f
head_hf = crown_f - neck_f

GRP1 = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index)
        for g in ob.vertex_groups}
print("\ngate:")
print(f"  verts {N} -> {len(me.vertices)}   faces {F} -> {len(me.polygons)}")
print(f"  groups {GRP0} -> {GRP1}")
assert len(me.vertices) == N and len(me.polygons) == F, "vertex/face count changed"
assert GRP0 == GRP1, "operator vertex groups changed"
moved = float(np.abs(co - co0).max())
print(f"  max displacement {moved:.4f} ({100*moved/H:.2f}%H)")
print(f"\n  MEASURED after:  crown {crown_f:.4f}  neck {neck_f:.4f}  height {head_hf:.4f}")
print(f"                   ear-to-ear {ear_wf:.4f}   ASPECT {ear_wf/max(head_hf,1e-9):.2f}"
      f"   (was {ear_w/max(head_h,1e-9):.2f}, reference 1.48)")
print(f"  mouth now        {100*(crown_f - lip_f)/max(head_hf,1e-9):.0f}% down the head "
      f"(was {100*(crown_z - z_lip)/max(head_h,1e-9):.0f}%, reference 87%)")

dst = os.path.join(OUT, "clyffy_v2_prop.blend")
bpy.ops.wm.save_as_mainfile(filepath=dst)
print(f"wrote {dst}")
