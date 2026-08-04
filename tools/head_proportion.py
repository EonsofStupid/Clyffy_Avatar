"""Reshape the head to canon proportions. DISPLACEMENT ONLY — vertex indices preserved.

    blender -b --python tools/head_proportion.py -- <canon.blend> <out_dir> [fwd] \
        [--neck K] [--squash K] [--widen K] [--measure]

Runs at chain position 1.5 — AFTER `canonicalize`, BEFORE `mouth_open`.

═══ WHY HERE AND NOT ON THE FINISHED BODY ═══════════════════════════════════════════════════

Operator, 2026-08-01: *"the head is long when it needs to be short"*, and earlier *"you have
never really captured his mouth"*. Measured against `canon/reference/`, our head
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
SNOUT = opt("--snout", 1.00)    # scale on the muzzle's FORWARD projection past the forehead
MUZZLE = opt("--muzzle", 1.00)  # VERTICAL fullness of the muzzle mass (profile-measured; not width)
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
      f"(canon/reference/, read off a gridded overlay — see SPEC.md)")

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

# ── 1b. SNOUT PROJECTION ─────────────────────────────────────────────────────
# Scales the forward EXCESS past the forehead plane, so the back of the head, the skull and the
# neck are untouched. >1 extends the muzzle, <1 retracts it: at full weight the vertex maps to
# `f_brow + (f - f_brow) * SNOUT`.
#
# MEASURED IN PROFILE, which is the only view that can see it — tools/profile_shot.py renders a
# true 90 degree side view and tools/head_metrics.snout_projection measures it and the reference
# panel through one function. Against `canon/reference/`:
#
#     snout past the brow / skull behind the brow     reference 0.455   ours 0.401   (0.88x)
#     muzzle depth / crown-to-snout-tip               reference 0.635   ours 0.547   (0.86x)
#
#     --snout 1.15 puts BOTH ratios on 1.00x.
#
# ⛔ CORRECTION. An earlier version of this comment claimed "reference 0.144, ours 0.347 -> ours
# protrudes ~2.4x too far" and the whole stage was built to RETRACT the muzzle. That was wrong,
# and it was wrong in the project's signature way: the old metric placed the brow row at a
# fraction of crown-to-CHIN, and on the reference sheet the chin was set by the LAB COAT. That
# dropped the brow row onto the muzzle itself, so `x_brow` came out nearly equal to `x_snout` and
# the reference's projection collapsed to a third of its real value. Our render has no coat, so
# the two sides were measuring different rows. Reproduced live: the same panel read 0.404, then
# 0.070, purely from where the chin landed. The metric now anchors on CROWN and SNOUT TIP only —
# two landmarks that are unambiguously head on both sides — and never looks below the muzzle.
#
# The front view was right the whole time: the muzzle needs to come FORWARD, not back.
if abs(SNOUT - 1.0) > 1e-6 or abs(MUZZLE - 1.0) > 1e-6:
    f = co @ fwd
    zc2 = co[:, 2]
    # forehead plane: how far forward the face reaches ABOVE the muzzle, near the brow
    # POST-compression landmarks (lip2 / crown2 / neck2). Using the pre-compression z_lip and
    # crown_z here put the muzzle weight band 0.0358 too high — the neck stage had already
    # shifted every vertex above it DOWN by exactly that much — so the pullback was landing on
    # the brow instead of the muzzle and the rendered silhouette barely moved while the mesh's
    # forward extent went 0.2011 -> 0.1430.
    brow = (zc2 > lip2 + 0.45 * (crown2 - lip2)) & (zc2 < crown2) & (np.abs(lp - lat0) < 0.25 * ear_w)
    f_brow = float(np.percentile(f[brow], 92)) if brow.sum() > 20 else float(np.percentile(f, 90))
    head_m = zc2 > (neck2 - 0.02 * H)
    depth_m = float(np.ptp(f[head_m]))
    proj = f - f_brow
    proj_max = float(proj[head_m].max())
    proj0 = proj_max / max(depth_m, 1e-9)

    # ── the Z BAND IS MEASURED FROM THE MESH, not placed by hand ─────────────
    # Two hand-placed bands failed before this. Both were written as a fraction of the lip->crown
    # span, and both were wrong in ways that a probe caught and the renders did not:
    #   * NO LOWER EDGE. `wz` was 1 for every vertex below its upper cutoff, which on the real
    #     mesh meant 39141 of 46001 vertices — 85% of the body, down to the hooves at z=-0.489.
    #     Only the `ahead` gate kept the chest from being dragged backwards. It worked by accident.
    #   * The 0.55 -> 0.85 widening was justified by a diagnosis that was never checked. At 0.55
    #     the snout tip's z term already evaluated to 1.013 -> clipped to 1.000; it was at FULL
    #     weight the whole time. Widening only added pullback to the FOREHEAD, which must not move.
    #
    # So the band is derived instead: for each horizontal slice of the head, how far does the face
    # reach past the brow plane? That profile IS the muzzle — it peaks at the snout and decays to
    # nothing at the forehead above and the throat below, so the band is bounded at both ends by
    # measurement rather than by a guessed constant.
    NB = 64
    zlo, zhi = float(zc2[head_m].min()), float(zc2[head_m].max())
    bi = np.clip(((zc2 - zlo) / max(zhi - zlo, 1e-9) * NB).astype(int), 0, NB - 1)
    pz = np.zeros(NB)
    for b in range(NB):
        m = head_m & (bi == b)
        if m.sum() >= 8:
            pz[b] = max(0.0, float(proj[m].max()))
    pz = np.convolve(pz, np.ones(5) / 5.0, mode="same")   # a stray vertex must not set the band
    pzn = pz / max(pz.max(), 1e-9)

    # SAMPLE THE PROFILE BY INTERPOLATION, NOT BY BIN INDEX. `pzn[bi]` is a nearest-bin lookup, so
    # the weight was piecewise-CONSTANT in z: 64 slabs about 0.0037 units thick, comparable to an
    # edge length, with a jump at every boundary. Those jumps are normal discontinuities — real
    # creases in the surface. At --muzzle 1.35 they multiplied the crease edges in the upper face
    # 99 -> 325 and fused the two eye-socket rims (25 and 21 verts) into a single 240-vertex band
    # across the midline, which is what made eye_open report "expected 2 eye rims, got 1".
    zb_c = zlo + (np.arange(NB) + 0.5) * (zhi - zlo) / NB
    pzv = np.interp(zc2, zb_c, pzn)
    BAND_LO, BAND_HI = 0.15, 0.45            # slices protruding <15% of peak are not the muzzle
    tz = np.clip((pzv - BAND_LO) / (BAND_HI - BAND_LO), 0.0, 1.0)
    wz = tz * tz * (3.0 - 2.0 * tz)
    wz[~head_m] = 0.0

    # ── `ahead` is a CLAMP, not a taper ──────────────────────────────────────
    # The displacement is already proportional to (f - f_brow), so it is zero at the brow plane on
    # its own; `ahead` only has to stop vertices BEHIND that plane from being pushed forward.
    # Scaling its ramp by 0.35 x HEAD DEPTH made it 0.1204 long against a snout that only projects
    # 0.0859 — the entire muzzle sat inside the fade, `w_sn` peaked at 0.714 with zero vertices
    # above 0.9, and the retraction floored at 71% no matter how far `--snout` was pushed. That was
    # the saturation. Scaled by the MEASURED projection it is a short ramp near the brow only.
    ta = np.clip(proj / max(0.15 * proj_max, 1e-9), 0.0, 1.0)
    ahead = ta * ta * (3.0 - 2.0 * ta)
    w_sn = wz * ahead
    d = proj * (1.0 - SNOUT) * w_sn
    co[:, 0] -= fwd[0] * d
    co[:, 1] -= fwd[1] * d

    zb = [zlo + (b + 0.5) * (zhi - zlo) / NB for b in range(NB)]
    on = [zb[b] for b in range(NB) if pzn[b] >= BAND_HI]
    print(f"\n  snout band MEASURED: full weight z {min(on):.4f}..{max(on):.4f} "
          f"({100*(max(on)-min(on))/H:.1f}%H), brow plane f={f_brow:.4f}, projection {proj_max:.4f}")
    print(f"    weighted verts: w_sn>0.9 {int((w_sn>0.9).sum())}  >0.5 {int((w_sn>0.5).sum())}  "
          f">0.01 {int((w_sn>0.01).sum())}   max w_sn {w_sn.max():.3f}")
    f2 = co @ fwd
    proj1 = (float(f2[head_m].max()) - f_brow) / max(float(np.ptp(f2[head_m])), 1e-9)
    # Mesh-level only, for tracking that the edit did something. NOT comparable to the reference:
    # it normalises by head depth, which this edit changes, so numerator and denominator move
    # together and the ratio under-reports. The comparable number comes from profile_shot.py +
    # head_metrics.snout_projection, which measure our render and the reference panel identically.
    print(f"  snout x{SNOUT}: mesh forward excess {proj0:.3f} -> {proj1:.3f} of head depth "
          f"(indicative only — compare via tools/snout_ladder.sh)")

    # ── 1c. MUZZLE FULLNESS ──────────────────────────────────────────────────
    # With the projection on target at --snout 1.15 the overlay still showed the reference
    # standing proud ABOVE the muzzle (a higher nose bridge) and BELOW it (a fuller lower lip).
    # Getting the tip to the right place did not make the mass the right thickness.
    #
    # Z ONLY, DELIBERATELY. A profile silhouette cannot see lateral width, and this stage does not
    # guess at quantities it has not measured. Muzzle width is a FRONT-view job and is left alone.
    if abs(MUZZLE - 1.0) > 1e-6:
        f3 = co @ fwd
        root = f_brow - 0.5 * proj_max          # fullness reaches back into the muzzle's root
        tf = np.clip((f3 - root) / max(0.5 * proj_max, 1e-9), 0.0, 1.0)
        wf = wz * (tf * tf * (3.0 - 2.0 * tf))
        tot = float(wf.sum())
        if tot > 1e-6:
            z_mz = float((co[:, 2] * wf).sum() / tot)     # the muzzle's own centre height
            co[:, 2] += (co[:, 2] - z_mz) * (MUZZLE - 1.0) * wf
            print(f"  muzzle x{MUZZLE} about z={z_mz:.4f} (Z only; lateral width is a front-view "
                  f"job and is untouched), {int((wf > 0.5).sum())} verts at >0.5 weight")

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
