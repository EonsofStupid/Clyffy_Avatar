"""Grow a real MANDIBLE under the mouth, so the jaw has something to carry when it drops.

    blender -b --python tools/chin_mass.py -- <open.blend> <out_dir> <fwd_deg> \
            [depth] [u_lo] [u_hi] [u_max] [fill] [hinge_back] [hinge_up]

WHY THIS STAGE EXISTS (measured 2026-07-28, operator call to build mass rather than cap
travel). The mouth was opening ~60% further than the character's anatomy could absorb:

    chin depth, lip line -> chin underside    ~5.0 %H
    jaw drop at the shipped 22 deg             7.41 %H
    aperture at 22 deg                         7.69 %H

The lower lip finished ~2.5%H BELOW where the chin bottom started, so at full open there
was no chin left under the mouth — the aperture ate it, which is what read as "a hole
punched in a rigid muzzle". No weight map can fix that: `m2_ceiling.py` applied the map an
ideal hand-painting would give (3263 rigid verts, 3x what the solve reaches) and the chin
still landed inside the shirt collar. The travel was simply larger than the anatomy.

M1 blamed the CAVITY and that was wrong — its "5.2%H depth" was the bag's HEIGHT. Measured
along fwd the cavity is 15.96%H deep with 10.85%H of palate above it. There was nothing to
deepen. What is genuinely missing is mass BELOW the cavity floor: 2.44%H median.

WHERE THE MASS GOES. The midline profile has an empty notch under the chin — the surface
steps back 6.6%H in one 1%H height step at z 0.177 (the chin's underside), and the chest
does not come forward again until ~20%H below the lip. So the mandible can be grown down
and back into space that is already empty, without touching the chest or the collar.

HOW. A smooth displacement field — NO new geometry. Vertex count and indices are preserved
exactly, which matters because `body_rig.py` transfers face weights from the rig BY VERTEX
INDEX and asserts equal counts; a stage that added verts here would break every downstream
consumer. Growth is measured from the JAWLINE PLANE (through the hinge and the lip line,
the same plane `jaw_rig.py` splits weights on), so the mandible grows perpendicular to the
jaw rather than along world -Z, and the lip line itself never moves (the bump is 0 there).

The mouth interior is EXCLUDED, so the cavity keeps its shape and the mandible thickens
underneath it — which is the "no mandible volume" defect, fixed at the source.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
# Peak growth, in units of body height. 0.045 takes the chin from ~5.0%H deep to ~9.5%H,
# which clears the 7.41%H drop at 22 deg with ~2%H of chin still showing under the lip.
DEPTH = float(argv[3]) if len(argv) > 3 else 0.045
# The bump profile in u (= distance BELOW the jawline plane), in units of H:
#   0..U_DEAD  flat zero — the lip slit itself
#   U_DEAD..U_LO ramp in
#   U_LO..U_HI hold      — full growth across the chin block
#   U_HI..U_MAX ramp out — back to the untouched throat
# U_DEAD IS NOT OPTIONAL. The lip slit is 0.0077 tall and its edges are ~0.0008 long, so a
# ramp that starts at u=0 puts a 0.004H displacement gradient across an 0.0008 edge —
# measured 4.67x stretch with 213 edges over 2x. Holding the field at zero until BELOW the
# slit drops that to a manageable number without changing the mandible at all.
U_DEAD = float(argv[4]) if len(argv) > 4 else 0.014
U_LO  = float(argv[5]) if len(argv) > 5 else 0.040
U_HI  = float(argv[6]) if len(argv) > 6 else 0.055
U_MAX = float(argv[7]) if len(argv) > 7 else 0.135
# Forward fill, so the new underside stays convex instead of becoming a knife edge.
# Keep this SMALL: it is what turns a jaw into a jowl. 0.010 visibly thickened the whole
# lower face and swallowed the neck.
FILL  = float(argv[8]) if len(argv) > 8 else 0.004
# WHERE ALONG THE JAW the mass sits, as distance forward of the hinge, in units of H.
# A flat mask thickens the jaw uniformly from the hinge to the chin, which merges the rear
# of the jaw into the neck and reads as jowly — that, not the depth itself, is what made a
# 0.050 growth look heavy. Ramping the mass in toward the chin keeps the jaw line and the
# neck while still buying depth where the aperture needs it.
A_LO  = float(argv[9])  if len(argv) > 9  else 0.020
A_HI  = float(argv[10]) if len(argv) > 10 else 0.140
# Lateral taper, so the chin deepens without ballooning the sides of the face. The mouth
# half-span is ~0.072H, so full growth to 0.070H and out by 0.140H keeps it under the mouth.
L_IN  = float(argv[11]) if len(argv) > 11 else 0.070
L_OUT = float(argv[12]) if len(argv) > 12 else 0.140
HINGE_BACK = float(argv[13]) if len(argv) > 13 else 0.75
HINGE_UP   = float(argv[14]) if len(argv) > 14 else 0.30
# Diffusion passes that carry the field smoothly into the protected set. See the block at the
# field construction — without this the protection boundary is a step, and a step in a
# displacement field folds the surface. Index 15: HINGE_UP already owns 14.
SMOOTH = int(argv[15]) if len(argv) > 15 else 14
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6, \
    "input is not canonical -- run tools/canonicalize.py first"

N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat

# ── the jawline plane, built EXACTLY as jaw_rig.py builds it ────────────────────────
di = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
assert di, "no clyffy_mouth_interior material -- run tools/mouth_open.py first"
cav_set, surf_set = set(), set()
for p in me.polygons:
    (cav_set if p.material_index == di[0] else surf_set).update(p.vertices)
rim = np.array(sorted(cav_set & surf_set))
cav = np.array(sorted(cav_set))
mouth = co[cav].mean(axis=0)
head_m = co[:, 2] > mouth[2]
hc = co[head_m].mean(axis=0)
band = head_m & (np.abs(co[:, 2] - mouth[2]) < H * 0.05)
f_front, f_back = fp[band].max(), fp[band].min()
lat0 = float(hc @ lat)
hinge = fwd * (f_front - (f_front - f_back) * HINGE_BACK) + lat * lat0
hinge[2] = mouth[2] + (zmax - mouth[2]) * HINGE_UP

rel = co - hinge
along = rel @ fwd
lipv = co[rim].mean(axis=0) - hinge
slope = float(lipv[2] / (lipv @ fwd))
sd = (rel[:, 2] - slope * along) / math.sqrt(1.0 + slope * slope)
u = -sd / H                                     # distance BELOW the jawline, in units of H
# the plane's own down-normal, so growth is perpendicular to the jaw, not to world Z
dn = np.array([slope * fwd[0], slope * fwd[1], -1.0]) / math.sqrt(1.0 + slope * slope)

print(f"canonical mesh: {N} verts   H={H:.4f}")
print(f"hinge ({hinge @ fwd:+.4f} fwd, {hinge[2]:+.4f} z)   jawline slope {slope:+.4f} "
      f"({math.degrees(math.atan(-slope)):.1f} deg below horizontal)")
print(f"lip line z {mouth[2]:+.4f}   down-normal ({dn[0]:+.3f},{dn[1]:+.3f},{dn[2]:+.3f})")

# ── the field ──────────────────────────────────────────────────────────────────────
def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

# bump in u: dead zone, ramp in, hold, ramp out. Zero across the lip slit and zero again
# in the throat, so neither the lip seal nor the neck is disturbed.
def bump_of(x):
    return np.where(x < U_DEAD, 0.0,
           np.where(x < U_LO, smoothstep((x - U_DEAD) / max(U_LO - U_DEAD, 1e-9)),
           np.where(x < U_HI, 1.0,
                    1.0 - smoothstep((x - U_HI) / max(U_MAX - U_HI, 1e-9)))))
bump = np.where(u > 0.0, bump_of(u), 0.0)

# forward of the hinge, so the mandible tapers to nothing AT the hinge like a real jaw,
# and deepens toward the chin rather than thickening the whole jaw uniformly
mask_f = smoothstep((along / H - A_LO) / max(A_HI - A_LO, 1e-9))
# lateral taper — keep the growth under the mouth instead of inflating the cheeks
mask_l = 1.0 - smoothstep((np.abs(lp - lat0) / H - L_IN) / max(L_OUT - L_IN, 1e-9))
# never touch the mouth interior: the cavity keeps its shape and the mandible thickens
# UNDER it, which is exactly the missing volume
protect = np.zeros(N, bool); protect[cav] = True
protect[rim] = True          # the lip line is the one thing that must not move at all

# ── THE SHIRT IS TEXTURE ON THE SAME SURFACE — protect it by SAMPLING, not by guessing ──
# There is no separate garment mesh: the navy t-shirt is painted on the one continuous
# body surface. Displacing geometry under it drags the collar with it. Sampled from the
# base-colour image, the collar on the midline front sits at z +0.150 — only 7.7%H below
# the lip line. That is the entire budget for chin AND neck, and it is why growth alone
# cannot buy back the 7.41%H the jaw drops at 22 deg.
img = None
collar_z = None   # set when the garment texture is sampled; used by the budget report below
for m in me.materials:
    if not m or not m.use_nodes: continue
    for nd in m.node_tree.nodes:
        if nd.type == 'TEX_IMAGE' and nd.image:
            img = nd.image; break
    if img: break
if img is not None:
    IW, IH = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(IH, IW, 4)
    uvl = me.uv_layers.active
    uv = np.zeros((N, 2)); seen = np.zeros(N, bool)
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            if not seen[vi]:
                uv[vi] = uvl.data[li].uv; seen[vi] = True
    xi = np.clip((uv[:, 0] % 1.0 * (IW - 1)).astype(int), 0, IW - 1)
    yi = np.clip((uv[:, 1] % 1.0 * (IH - 1)).astype(int), 0, IH - 1)
    c = px[yi, xi, :3]
    navy = (c[:, 2] > c[:, 0] * 1.25) & (c[:, 2] > c[:, 1] * 1.15) & (c[:, 2] < 0.45) & seen
    protect |= navy
    # The COLLAR is the first band that turns navy scanning DOWN from the lip — NOT the
    # highest navy vertex. The lanyard is blue too and runs up to the shoulders, so a max()
    # reports z +0.3527, above the mouth, which is nonsense.
    strip = (np.abs(lp - lat0) < H * 0.03) & (fp > 0) & seen
    collar_z = None
    zc = mouth[2]
    while zc > mouth[2] - H * 0.25:
        m = strip & (np.abs(co[:, 2] - zc) < H * 0.006)
        if m.sum() >= 4 and navy[m].mean() > 0.5:
            collar_z = zc; break
        zc -= H * 0.010
    print(f"  protected garment ({img.name}): {int(navy.sum())} navy verts"
          + (f", midline collar at z {collar_z:+.4f} = {100*(mouth[2]-collar_z)/H:.2f}%H "
             f"below the lip line — the HARD CEILING on chin depth" if collar_z else ""))
else:
    print("  !! no image texture found — the garment could NOT be protected")
for gname in ("eye_L", "eye_R", "teeth_upper", "teeth_lower", "tongue"):
    g = ob.vertex_groups.get(gname)
    if g:
        idx = [v.index for v in me.vertices for x in v.groups if x.group == g.index and x.weight > 0.5]
        protect[idx] = True
        print(f"  protected {gname}: {len(idx)} verts")

amp = bump * mask_f * mask_l
amp[protect] = 0.0

# ── DIFFUSE THE FIELD INTO THE PROTECTED SET ────────────────────────────────────────
# `amp[protect] = 0.0` on its own is a STEP: a vertex at full displacement sits directly
# beside one pinned at zero, and a step in a displacement field is a FOLD in the surface.
# That single line produced both of the defects the operator pointed at on 2026-08-04 —
#   * the two cone-like extensions at the lower-lateral corners of the chin, where the
#     navy-garment protection cuts the field off while `bump` is still 1.0, and
#   * the jagged shards along the lip line, where the `rim` protection does the same.
# Confirmed by stage: the chin is clean after mouth_open and both appear at chin_mass.
#
# The masks themselves are all smoothsteps, so the field was never the problem — the hard
# boundary condition was. Jacobi diffusion with the protected set held at zero (a Dirichlet
# condition) keeps every protected vertex EXACTLY untouched, which is the whole point of
# protecting it, while the surrounding field decays into it over several edge lengths
# instead of falling off a cliff. Same remedy as the Laplacian pass that fixed the
# festooned lip bands.
if SMOOTH > 0:
    ei = np.empty(len(me.edges) * 2, dtype=np.int32)
    me.edges.foreach_get("vertices", ei)
    ea, eb = ei[0::2], ei[1::2]
    deg = np.zeros(N)
    np.add.at(deg, ea, 1.0)
    np.add.at(deg, eb, 1.0)
    deg = np.maximum(deg, 1.0)
    before_max = float(amp.max())
    for _ in range(SMOOTH):
        acc = np.zeros(N)
        np.add.at(acc, ea, amp[eb])
        np.add.at(acc, eb, amp[ea])
        amp = 0.5 * amp + 0.5 * (acc / deg)
        amp[protect] = 0.0          # protected verts stay EXACTLY zero, every pass
    print(f"  field diffused {SMOOTH} passes into the protected set: "
          f"peak amp {before_max:.3f} -> {amp.max():.3f}, "
          f"{int((amp > 0.01).sum())} verts carry displacement")
    assert not np.any(amp[protect] > 1e-9), "diffusion leaked into a protected vertex"

# MONOTONICITY. The field compresses the throat as the chin grows into it. If the ramp-out
# is steeper than the growth, the surface folds through itself. u' = u + DEPTH*bump(u), so
# the map is injective iff 1 + DEPTH*d(bump)/du > 0 everywhere. Checked, not assumed.
uu = np.linspace(0.0, U_MAX * 1.2, 4000)
duu = np.gradient(uu + DEPTH * bump_of(uu), uu)
assert duu.min() > 0.05, (
    f"the u-map folds (min du'/du = {duu.min():.3f}): the ramp-out from U_HI={U_HI} to "
    f"U_MAX={U_MAX} is too steep for DEPTH={DEPTH}. Widen U_MAX or reduce DEPTH.")
print(f"u-map monotone: min du'/du = {duu.min():.3f} (>0 required, folds below 0)")

disp = (dn[None, :] * (DEPTH * H * amp)[:, None]
        + fwd[None, :] * (FILL * H * amp)[:, None])
moved = int((np.linalg.norm(disp, axis=1) > 1e-9).sum())
new = co + disp
print(f"field: DEPTH {DEPTH:.3f}H  u[{U_DEAD:.3f},{U_LO:.3f},{U_HI:.3f},{U_MAX:.3f}]H  "
      f"FILL {FILL:.3f}H  along[{A_LO:.3f},{A_HI:.3f}]H  lat[{L_IN:.3f},{L_OUT:.3f}]H")
print(f"  {moved} verts moved, max {np.linalg.norm(disp, axis=1).max()/H*100:.2f}%H, "
      f"mean {np.linalg.norm(disp[np.linalg.norm(disp,axis=1)>1e-9], axis=1).mean()/H*100:.2f}%H")

# ── edge stretch: a growth field that tears is not an improvement ───────────────────
pairs = set()
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k + 1) % len(vs)]
        pairs.add((i, j) if i < j else (j, i))
E = np.array(sorted(pairs), dtype=np.int64)
l0 = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1)
l1 = np.linalg.norm(new[E[:, 0]] - new[E[:, 1]], axis=1)
ok = l0 > 1e-9
ratio = np.ones(len(E)); ratio[ok] = l1[ok] / l0[ok]
print(f"edge stretch: max {ratio.max():.2f}x  min {ratio.min():.2f}x  "
      f">2x {int((ratio > 2).sum())}  <0.5x {int((ratio < 0.5).sum())}")

me.vertices.foreach_set("co", new.ravel()); me.update()

# ── did it actually buy chin depth? measure the midline silhouette before/after ─────
body = np.array(sorted(surf_set - cav_set), dtype=int)
mid = body[np.abs(lp[body] - lat0) < H * 0.012]
def chin_depth(C):
    """Depth of chin that still PROJECTS — the part a viewer reads as chin.

    Walking down the midline, the frontmost surface recedes gently across the chin and then
    tucks back under. Two earlier definitions both failed:
      * lowest midline vertex — measures the THROAT, reports ~12%H whatever the chin does;
      * biggest single backward step — the step MOVES as the notch fills, so it reported
        3.50 → 2.50%H for a chin that had visibly grown.
    Instead: how far below the lip line the silhouette still sits within THRESH of the
    chin's most forward point. That is monotone in the thing being built.
    """
    THRESH = H * 0.030
    f = C @ fwd
    zs, fs = [], []
    z = mouth[2] - H * 0.005
    while z > mouth[2] - H * 0.20:
        m = mid[np.abs(C[mid, 2] - z) < H * 0.006]
        if len(m) >= 2:
            zs.append(z); fs.append(f[m].max())
        z -= H * 0.010
    zs, fs = np.array(zs), np.array(fs)
    if len(zs) < 3:
        return float("nan"), float("nan")
    front = fs.max()
    keep = np.where(fs >= front - THRESH)[0]
    last = keep.max()
    return zs[last], fs[last]
for tag, C in (("before", co), ("after ", new)):
    zc, fc = chin_depth(C)
    print(f"chin {tag}: front silhouette holds to z {zc:+.4f} (fwd {fc:+.4f}) "
          f"= {100*(mouth[2]-zc)/H:5.2f}%H below the lip line")

# THE NUMBER THE COLLAR CONSTRAINT ACTUALLY USES: how far down the mandible this stage built
# reaches. Two silhouette-based definitions were tried first and BOTH were flat across every
# DEPTH setting (one measured the throat, the other keyed off the lip). The extent of the
# grown mass is monotone in DEPTH by construction, which is what a control knob needs.
core = np.where(amp > 0.5)[0]
if len(core):
    D = (mouth[2] - new[core, 2].min()) / H * 100
    print(f"MANDIBLE EXTENT: {len(core)} verts at amp>0.5 reach z {new[core,2].min():+.4f} "
          f"= {D:.2f}%H below the lip line")
    if collar_z is not None:
        budget = 100*(mouth[2] - collar_z)/H
        print(f"COLLAR BUDGET {budget:.2f}%H  ->  max jaw drop before the chin enters the "
              f"shirt = {budget - D:.2f}%H")
    print(f"  (jaw drop is 7.41%H at 22 deg, so ~{7.41/22:.3f}%H per degree)")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_chin.blend"))

# ── renders on jaw_rig.py's cameras, so every existing r_*.png compares directly ────
sc = bpy.context.scene
for o in [x for x in bpy.data.objects if x.type == 'CAMERA']:
    bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 640
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H * 30; cd.ortho_scale = H * 0.34
R2 = H * 5
for off, tag in ((0.0, "front"), (math.radians(50), "q50"), (math.radians(90), "side")):
    ac = a + off
    cam.location = (mouth[0] + math.sin(ac) * R2, mouth[1] - math.cos(ac) * R2, mouth[2])
    cam.rotation_euler = (math.radians(90), 0, ac)
    sc.render.filepath = os.path.join(OUT, f"chin_{tag}.png")
    bpy.ops.render.render(write_still=True)
print("ok")
