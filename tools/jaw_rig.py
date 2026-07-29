"""Jaw rig for clyffy: armature + skin weights, on the CANONICAL mesh.

    blender -b --python tools/jaw_rig.py -- <open.blend> <out_dir> <fwd_deg> [angle] [back] [up]

WEIGHTS -- why they are solved here rather than by Blender.
Blender's `ARMATURE_AUTO` (bone heat) returns ZERO weights for every bone on this Tripo
mesh. Verified on the cut mesh, the original uncut FBX, with hole-filling and with
triangulation, and for every bone subset (tools/_heatdiag.py, tools/_heatfix.py). It
reports the failure as a Warning, not an exception, so it silently "succeeds".

Bone heat is harmonic diffusion over the mesh surface, so that is solved directly:

    Laplace(w) = 0 on free verts,  w = 1 on the jaw core,  w = 0 on the skull/body core

by conjugate gradient on the graph Laplacian. Diffusion travels along MESH EDGES, and
the mouth is genuinely cut, so weight cannot cross from the lower jaw to the upper lip --
it has to go the long way around the corners and decays doing it. The three earlier
solvers used distance/projection in space, where the upper lip sits 0.005 from the lower
lip and always got dragged along.

The jaw CORE is anchored rigid (w=1 over the whole lower-jaw block, not just a seed at
the lip) so the jaw ROTATES instead of stretching; the harmonic solve only shapes the
falloff band at the hinge and the jawline. That is what weight painting produces by hand.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector, Matrix, kdtree

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
ANGDEG     = float(argv[3]) if len(argv) > 3 else 22.0
HINGE_BACK = float(argv[4]) if len(argv) > 4 else 0.75
HINGE_UP   = float(argv[5]) if len(argv) > 5 else 0.30   # fraction of (top-of-head - mouth)
# Radius of the corner relief zone, ABSOLUTE units. Must stay small next to the mouth's
# half-span (~0.072) or it frees the upper lip and the aperture collapses.
CORNER_R   = float(argv[6]) if len(argv) > 6 else 0.020
SMOOTH     = int(argv[7]) if len(argv) > 7 else 0      # weight-relax iterations near the mouth
# How far BELOW the operator's jaw-region floor the hard w=0 anchor sits, in units of H.
# ⚠️ M1 (2026-07-28): this was hardwired to BAND (0.030H) via `floor_z = chin_bottom - H*FLOOR_DROP`,
# where chin_bottom is the min z of the operator's 390-vert hand-picked op_jaw_region. Every
# vertex below that line is HARD-ANCHORED TO ZERO, so the chin and jowl mass could never
# follow the jaw. Measured on the shipped rig: of 6443 exterior verts in the lower muzzle,
# only 34.5% moved at jawOpen=1.0 — the jaw drove a thin collar around the lip opening and
# the face around it stayed static. That is why an open mouth read as a hole punched in a
# rigid muzzle rather than a jaw dropping.
# Raising this extends how much of the lower muzzle the jaw owns. It is a JUDGMENT call, not
# a free win: too far and the throat/neck starts swinging when he talks, which reads worse
# than the original defect. Compare renders before changing the default.
FLOOR_DROP = float(argv[8]) if len(argv) > 8 else 0.030
# How far below chin_bottom the RIGID CORE (w=1) extends, in units of H.
# ⚠️ Measured 2026-07-28: lowering FLOOR_DROP alone does NOT fix the static muzzle. It moves
# the w=0 boundary further out, so the harmonic solve just spreads a LONGER, WEAKER gradient
# across the chin — verts>0.01 went 3673 -> 5818 while "fully rigid" stayed at 998 and the
# mean weight FELL 0.540 -> 0.441. The chin got more influence-of-a-kind, but weaker.
# The chin/jowl mass has to be ANCHORED to the jaw, not interpolated toward it. `along > BAND`
# already restricts the core to forward of the hinge, which is what keeps the throat out of
# it — the throat sits at and behind the hinge.
CORE_DROP  = float(argv[9]) if len(argv) > 9 else 0.0
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
mw = ob.matrix_world
assert max(abs(x) for x in mw.to_euler()) < 1e-6 and (np.abs(np.array(mw.to_scale())-1) < 1e-6).all(), \
    "input is not canonical -- run tools/canonicalize.py (local must equal world)"

N  = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin

gi = {g.name: g.index for g in ob.vertex_groups}
def group(name):
    return np.array(sorted(v.index for v in me.vertices
                           for g in v.groups if g.group == gi[name] and g.weight > 0.5))
REG  = group("op_jaw_region")
SEAM = group("op_lip_seam")
print(f"canonical mesh: {N} verts   operator groups: jaw region {len(REG)}, lip seam {len(SEAM)}")

a   = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat

di = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
assert di, "no clyffy_mouth_interior material -- run tools/mouth_open.py first"
cav_set, surf_set = set(), set()
for p in me.polygons:
    (cav_set if p.material_index == di[0] else surf_set).update(p.vertices)
rim = np.array(sorted(cav_set & surf_set))
cav = np.array(sorted(cav_set))
mouth = co[cav].mean(axis=0)
seam_lo, seam_hi = co[SEAM, 2].min(), co[SEAM, 2].max()
chin_bottom = float(co[REG, 2].min())
print(f"mouth centre z {mouth[2]:+.4f}   seam z [{seam_lo:+.4f},{seam_hi:+.4f}]   "
      f"chin bottom {chin_bottom:+.4f}   lip rim {len(rim)} verts")

head_m = co[:, 2] > mouth[2]
hc     = co[head_m].mean(axis=0)
band   = head_m & (np.abs(co[:, 2] - mouth[2]) < H*0.05)
f_front, f_back = fp[band].max(), fp[band].min()
depth   = f_front - f_back
lat0    = float(hc @ lat)
hinge_f = f_front - depth*HINGE_BACK
hinge_z = mouth[2] + (zmax - mouth[2])*HINGE_UP
hinge   = fwd*hinge_f + lat*lat0; hinge[2] = hinge_z
BAND    = H*0.030
floor_z = chin_bottom - H*FLOOR_DROP
print(f"face depth at mouth band {depth:.4f}   hinge ({hinge[0]:+.4f},{hinge[1]:+.4f},{hinge[2]:+.4f})   "
      f"jaw floor {floor_z:+.4f}   falloff band {BAND:.4f}")

# ---------------- anchors: a RIGID core bounded by the JAWLINE ----------------
# The jaw/skull boundary is NOT a horizontal cut above the lip. A horizontal cut leaves
# the mouth corner rigidly skull right where it has to give, so the skin there stretches
# into a thin web -- the light-grey slivers at the corners. A real jaw weight map follows
# the JAWLINE: a diagonal running from the mouth corner back and up toward the hinge.
# So the boundary is the plane through the hinge containing the lip line and the hinge
# axis, and "jaw" is everything below it.
rel   = co - hinge
along = rel @ fwd
hgt   = rel[:, 2]
lipv  = co[rim].mean(axis=0) - hinge
slope = float(lipv[2] / (lipv @ fwd))          # ray from the hinge down-forward to the lip
sd    = (hgt - slope*along) / math.sqrt(1.0 + slope*slope)   # signed distance below/above
print(f"jawline: slope {slope:+.4f} from hinge through the lip line "
      f"({math.degrees(math.atan(-slope)):.1f} deg below horizontal)")

anchor = np.zeros(N, bool); aval = np.zeros(N)
jaw_core = (sd < -BAND) & (along > BAND) & (co[:, 2] > chin_bottom - H*CORE_DROP)
jaw_core[REG[co[REG, 2] < seam_lo]] = True          # operator's own picks, below the lip
anchor[jaw_core] = True; aval[jaw_core] = 1.0
n_one = int(jaw_core.sum())

# LIP RIM: taper toward 0.5 at the mouth corner, measured ALONG THE RIM LOOP.
# The rim is a closed loop, so the lower lip (must move) and upper lip (must not) are
# ADJACENT at the commissure; hard-anchoring 1 and 0 there tears the edge between them.
# Lateral offset is a bad proxy for corner proximity on a curved mouth -- verts at the
# same lateral offset sit at very different places along the loop -- so walk the loop and
# taper by ARC DISTANCE from the corner.
rimset = set(rim.tolist())
ef = {}
for p_ in me.polygons:
    vs = list(p_.vertices)
    for k in range(len(vs)):
        i_, j_ = vs[k], vs[(k+1) % len(vs)]
        ef.setdefault((min(i_, j_), max(i_, j_)), []).append(p_.material_index == di[0])
rim_adj = {}
for (i_, j_), mats in ef.items():
    if i_ in rimset and j_ in rimset and any(mats) and not all(mats):
        rim_adj.setdefault(i_, []).append(j_); rim_adj.setdefault(j_, []).append(i_)
degs = {v: len(n) for v, n in rim_adj.items()}
assert degs and set(degs.values()) == {2}, f"lip rim is not a simple cycle: degrees {sorted(set(degs.values()))}"
start = rim[0]; cycle = [start]; prev = None; cur_v = start
while True:
    nxt = [n for n in rim_adj[cur_v] if n != prev]
    prev, cur_v = cur_v, nxt[0]
    if cur_v == start: break
    cycle.append(cur_v)
assert len(cycle) == len(rim), f"rim cycle walked {len(cycle)} of {len(rim)} verts"
cyc = np.array(cycle)
clat = co[cyc] @ lat - lat0
ci = [int(np.argmin(clat)), int(np.argmax(clat))]          # the two commissures
L = len(cyc)
steps = np.minimum(np.abs(np.arange(L)[:, None] - np.array(ci)[None, :]),
                   L - np.abs(np.arange(L)[:, None] - np.array(ci)[None, :])).min(axis=1)
RIM_WIN = max(3, L//8)
sfac = np.clip(steps/RIM_WIN, 0.0, 1.0)
sfac = sfac*sfac*(3 - 2*sfac)                              # smoothstep along the loop

# CLASSIFY BY CHAIN, NOT BY Z. The two commissures split the loop into an upper chain and
# a lower chain. Deciding "is this the lower lip?" per-vertex from its z instead flips
# sides wherever the rim zigzags -- and it does, because the lip line is not horizontal
# and the slit is only 0.0077 tall. That put w=1.00 next to w=0.00 on CYCLE-ADJACENT
# verts in the middle of the mouth and tore them 27x. Chain membership is monotonic
# along the loop by construction, so adjacent verts can never flip.
lo_i, hi_i = min(ci), max(ci)
chainA = np.zeros(L, bool); chainA[lo_i:hi_i+1] = True      # one side, commissure to commissure
if co[cyc[chainA], 2].mean() > co[cyc[~chainA], 2].mean():
    chainA = ~chainA                                        # chainA is the LOWER lip
rim_w = np.where(chainA, 0.5 + 0.5*sfac, 0.5 - 0.5*sfac)
anchor[cyc] = True; aval[cyc] = rim_w
zflip = int((chainA != (co[cyc, 2] < mouth[2])).sum())
print(f"lip rim: {L}-vert cycle, commissures at loop idx {ci}, taper window {RIM_WIN} steps")
print(f"  lower chain {int(chainA.sum())} verts (w {rim_w[chainA].min():.2f}-{rim_w[chainA].max():.2f}), "
      f"upper chain {int((~chainA).sum())} verts (w {rim_w[~chainA].min():.2f}-{rim_w[~chainA].max():.2f})")
print(f"  {zflip} verts where a z-based split would have disagreed with the chain "
      f"(each one was a 1.0-vs-0.0 tear)")

zero = (sd > BAND) | (co[:, 2] < floor_z) | (along < -BAND)
zero &= ~anchor
anchor[zero] = True; aval[zero] = 0.0

# CORNER RELIEF. The rim is one closed loop, so going around it you cross from lower lip
# (must move) to upper lip (must not) AT THE CORNER -- adjacent verts hard-anchored 1 and
# 0. That is a guaranteed tear: measured 11.9x edge stretch there. Free every anchor
# within CORNER_R of each corner and let the harmonic solve interpolate across it, which
# is what a rigger achieves by hand-smoothing weights at the commissure.
rim_lat = co[rim] @ lat - lat0
dcorner = np.minimum(np.linalg.norm(co - co[cyc[ci[0]]], axis=1),
                     np.linalg.norm(co - co[cyc[ci[1]]], axis=1))
is_rim = np.zeros(N, bool); is_rim[cyc] = True
relief = (dcorner < CORNER_R) & ~is_rim      # the RIM keeps its tapered boundary condition
freed = int((relief & anchor).sum())
anchor[relief] = False; aval[relief] = 0.0
print(f"corner relief: radius {CORNER_R:.4f} -> freed {freed} non-rim verts around the "
      f"commissures so the skin interpolates to the tapered rim")
print(f"anchors: jaw core w=1 {n_one} verts, skull/body core w=0 {int(zero.sum())} verts, "
      f"free (falloff) {N - int(anchor.sum())}")

# TEETH / TONGUE / EYES are separate connected components. A component with no anchor
# makes L_FF singular and the CG solve ill-posed, so every one of them is anchored
# explicitly and rigidly: lower teeth and tongue ride the JAW, upper teeth the SKULL.
for gname, val in (("teeth_lower", 1.0), ("tongue", 1.0), ("teeth_upper", 0.0),
                   ("eye_L", 0.0), ("eye_R", 0.0)):
    if gname in gi:
        gidx = group(gname)
        if len(gidx):
            anchor[gidx] = True; aval[gidx] = val
            print(f"  anchored {gname}: {len(gidx)} verts -> w={val}")

# ---------------- graph: outer surface only ----------------
pairs = []
for p in me.polygons:
    if p.material_index == di[0]: continue    # cavity faces bridge the open mouth in ~4 edges
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k+1) % len(vs)]
        pairs.append((i, j) if i < j else (j, i))
E = np.unique(np.array(pairs, dtype=np.int64), axis=0)
e0, e1 = E[:, 0], E[:, 1]
deg = np.bincount(e0, minlength=N) + np.bincount(e1, minlength=N)
free = (~anchor) & (deg > 0)
idx  = -np.ones(N, np.int64); idx[free] = np.arange(free.sum())
nf   = int(free.sum())
ff   = free[e0] & free[e1]
f0, f1 = idx[e0[ff]], idx[e1[ff]]
degf = deg[free].astype(float)
def matvec(x):
    return degf*x - (np.bincount(f0, weights=x[f1], minlength=nf)
                   + np.bincount(f1, weights=x[f0], minlength=nf))
fa = free[e0] & anchor[e1]; af = anchor[e0] & free[e1]
b = (np.bincount(idx[e0[fa]], weights=aval[e1[fa]], minlength=nf)
   + np.bincount(idx[e1[af]], weights=aval[e0[af]], minlength=nf))
x = np.zeros(nf); r = b - matvec(x); pv = r.copy(); rs = float(r @ r); r0 = math.sqrt(rs)
it = 0
for it in range(1, 20001):
    Ap = matvec(pv); al = rs/float(pv @ Ap)
    x += al*pv; r -= al*Ap
    rs2 = float(r @ r)
    if math.sqrt(rs2) < 1e-9*max(r0, 1e-12): break
    pv = r + (rs2/rs)*pv; rs = rs2
print(f"harmonic solve: {it} CG iters, residual {math.sqrt(rs2):.2e} (start {r0:.2e}), {nf} free verts")

w = aval.copy(); w[free] = np.clip(x, 0.0, 1.0); w[deg == 0] = 0.0

# The mouth bag is held out of the graph, so it is skinned from LINEAGE: every bag vert
# takes the weight of the lip rim vert it was extruded from (attribute `cav_src`, written
# by tools/mouth_open.py). The lower wall therefore follows the jaw and the upper wall
# stays, as one piece.
# Weighting the bag by NEAREST SURFACE VERTEX instead tore it in half: its two walls sit
# ~0.008 apart, so neighbouring bag verts snapped to opposite lips and ended up w=0.95 vs
# w=0.08 on the SAME EDGE -- measured 27x edge stretch, which is what the corner slivers
# actually were.
assert "cav_src" in me.attributes, "no cav_src attribute -- re-run tools/mouth_open.py"
src = np.array([d.value for d in me.attributes["cav_src"].data], dtype=np.int64)
inner = np.where(src >= 0)[0]
assert (src[inner] < N).all(), "cav_src holds out-of-range rim indices"
assert "cav_depth" in me.attributes, "no cav_depth attribute -- re-run tools/mouth_open.py"
dpt = np.array([d.value for d in me.attributes["cav_depth"].data], dtype=np.float64)
# The bag is a CLOSED TUBE: its back cap joins the upper wall to the lower wall, so a
# straight 1/0 split tears the cap (measured 60x across 0.0006-long edges). Blend each
# wall's inherited lip weight toward a common 0.5 with depth, so the cap is uniform and
# the shear is spread through the bag -- standard mouth-bag skinning.
t = np.clip(dpt[inner], 0.0, 1.0)
w[inner] = w[src[inner]]*(1.0 - t) + 0.5*t
print(f"mouth bag: {len(inner)} verts skinned from their lip-rim ancestor, blended toward "
      f"0.5 with depth (w range {w[inner].min():.3f}-{w[inner].max():.3f})")

# RELAX the weights near the mouth over the SAME surface graph used for the solve.
# The harmonic field is already smooth on the free set, but it meets the hard jaw-core
# anchors with a kink, and a kink across a short edge is stretch. This is the "smooth
# weights" pass a rigger finishes with. Confined to the mouth region so the body is
# untouched, and re-applied to the bag afterwards so lineage still holds.
if SMOOTH > 0:
    near = np.linalg.norm(co - mouth, axis=1) < H*0.18
    near &= (src < 0)                     # bag verts are re-derived from the rim below
    nb_sum = np.zeros(N); nb_cnt = np.zeros(N)
    for _ in range(SMOOTH):
        nb_sum[:] = 0.0; nb_cnt[:] = 0.0
        np.add.at(nb_sum, e0, w[e1]); np.add.at(nb_sum, e1, w[e0])
        np.add.at(nb_cnt, e0, 1.0);   np.add.at(nb_cnt, e1, 1.0)
        avg = np.divide(nb_sum, np.maximum(nb_cnt, 1e-9))
        w[near] = 0.5*w[near] + 0.5*avg[near]
    w[cyc] = rim_w                        # the rim taper is a boundary condition, keep it
    w[inner] = w[src[inner]]*(1.0 - np.clip(dpt[inner], 0, 1)) + 0.5*np.clip(dpt[inner], 0, 1)
    print(f"weight relax: {SMOOTH} iterations over {int(near.sum())} verts near the mouth")

nz = np.where(w > 0.01)[0]
rigid = int((w > 0.99).sum())
print(f"jaw weights: {len(nz)} verts >0.01, {rigid} fully rigid (w>0.99), mean {w[nz].mean():.3f}")
P = nz[(lp[nz]-lat0) > 0]; M = nz[(lp[nz]-lat0) < 0]
mp, mm = w[P].mean(), w[M].mean()
print(f"symmetry: +side {len(P)} (mean {mp:.3f})  -side {len(M)} (mean {mm:.3f})  "
      f"ratio {max(mp,mm)/max(1e-9,min(mp,mm)):.2f}:1")

# ---------------- armature ----------------
chin_v = REG[co[REG, 2] <= np.sort(co[REG, 2])[max(0, len(REG)//10)]]
chin   = co[chin_v].mean(axis=0)
chin   = chin + (np.array([hc[0], hc[1], chin[2]]) - chin)*0.35
head_base = mouth[2] - (mouth[2]-zmin)*0.10

ad  = bpy.data.armatures.new("clyffy_rig")
arm = bpy.data.objects.new("clyffy_rig", ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones
root  = eb.new("root");  root.head = (hc[0], hc[1], zmin); root.tail = (hc[0], hc[1], head_base)
skull = eb.new("skull"); skull.head = (hc[0], hc[1], head_base); skull.tail = (hc[0], hc[1], zmax - (zmax-head_base)*0.10)
skull.parent = root; skull.use_connect = True
jaw = eb.new("jaw"); jaw.head = tuple(hinge); jaw.tail = tuple(chin)
jaw.parent = skull; jaw.use_connect = False
jaw.align_roll(Vector(np.cross(lat, chin - hinge)))   # local X == the hinge axis
bpy.ops.object.mode_set(mode='OBJECT')
print(f"bones: root, skull, jaw  (jaw {np.linalg.norm(chin-hinge):.4f} long, "
      f"head->tail {tuple(round(float(v),4) for v in hinge)} -> {tuple(round(float(v),4) for v in chin)})")

gj = ob.vertex_groups.new(name="jaw")
gs = ob.vertex_groups.new(name="skull")
gb = ob.vertex_groups.new(name="root")
t = np.clip((co[:, 2] - (head_base - BAND))/(2*BAND), 0, 1)
sfrac = t*t*(3 - 2*t)
rest = 1.0 - w
for i in range(N):
    if w[i] > 1e-4:                     gj.add([i], float(w[i]), 'REPLACE')
    if rest[i]*sfrac[i] > 1e-4:         gs.add([i], float(rest[i]*sfrac[i]), 'REPLACE')
    if rest[i]*(1-sfrac[i]) > 1e-4:     gb.add([i], float(rest[i]*(1-sfrac[i])), 'REPLACE')
mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
ob.parent = arm

# ---- validate the skin: partition of unity, influence count ----
tot = np.zeros(N); infl = np.zeros(N, int)
gset = {gj.index, gs.index, gb.index}
for v in me.vertices:
    for g in v.groups:
        if g.group in gset: tot[v.index] += g.weight; infl[v.index] += 1
print(f"skin validation: weight sum min {tot.min():.6f} max {tot.max():.6f} "
      f"(|1-sum|max {np.abs(tot-1).max():.2e})   influences/vert max {infl.max()} "
      f"({'OK <=4' if infl.max() <= 4 else '** EXCEEDS 4 **'})")

ca = me.color_attributes.new(name="jawmap", type='FLOAT_COLOR', domain='POINT')
cols = np.zeros((N, 4)); cols[:, 0] = w; cols[:, 1] = 0.15+0.25*(1-w); cols[:, 2] = 1.0-w; cols[:, 3] = 1
ca.data.foreach_set("color", cols.ravel())
# ⚠️ 2026-07-28: WITHOUT THIS THE WEIGHT MAP RENDERS FLAT GREY. Workbench
# color_type='VERTEX' draws the ACTIVE colour attribute; creating one does not make it
# active, and the mesh already carries others. Every wmap_*.png produced before this date
# is blind — every weight judgment in M1 was made without ever seeing the map.
me.color_attributes.active_color = ca
me.color_attributes.render_color_index = list(me.color_attributes).index(ca)

# ---------------- pose + measure ----------------
pb = arm.pose.bones["jaw"]
hv, lv = Vector(hinge), Vector(lat)
def pose(angle):
    R = Matrix.Translation(hv) @ Matrix.Rotation(angle, 4, lv) @ Matrix.Translation(-hv)
    pb.matrix = R @ pb.bone.matrix_local
    bpy.context.view_layer.update()
def evald():
    dg = bpy.context.evaluated_depsgraph_get(); obe = ob.evaluated_get(dg); ev = obe.to_mesh()
    v = np.empty((N, 3)); ev.vertices.foreach_get("co", v.ravel()); obe.to_mesh_clear()
    return v
ANG = math.radians(ANGDEG)
# Split the rim by CHAIN, the same way the weights do. Splitting by z here disagreed
# with the chain on 23 of 62 verts, so the aperture was averaging upper and lower
# together and read far too small.
rim_lo = cyc[chainA]; rim_up = cyc[~chainA]
pose(0.0); base = evald()
pose(+ANG); up = evald()
sign = 1.0 if up[rim_lo, 2].mean() < base[rim_lo, 2].mean() else -1.0
pose(sign*ANG); d = evald()
disp = np.linalg.norm(d - co, axis=1)
closed = float(co[rim_up, 2].mean() - co[rim_lo, 2].mean())
opened = float(d[rim_up, 2].mean() - d[rim_lo, 2].mean())
print(f"pose @ {ANGDEG:.0f} deg (sign {sign:+.0f}): max displacement {disp.max():.4f} = {100*disp.max()/H:.1f}% of height")
print(f"  LOWER lip rim moves {disp[rim_lo].mean():.4f}   UPPER lip rim moves {disp[rim_up].mean():.6f} (must be ~0)")
print(f"  APERTURE {closed:.4f} -> {opened:.4f}  = {100*opened/H:.1f}% of body height")
pose(0.0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_rig.blend"))

# ---------------- renders ----------------
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'
sc.render.resolution_x = sc.render.resolution_y = 640
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = H*0.34
R2 = H*5
def shoot(tag, off, colour):
    sc.display.shading.color_type = colour
    ang = a + off
    cam.location = (mouth[0]+math.sin(ang)*R2, mouth[1]-math.cos(ang)*R2, mouth[2])
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
shoot("wmap_front", 0.0, 'VERTEX'); shoot("wmap_q50", math.radians(50), 'VERTEX')
for amt, lbl in ((0.0, "000"), (0.5, "050"), (1.0, "100")):
    pose(sign*ANG*amt)
    shoot(f"r_front_{lbl}", 0.0, 'TEXTURE'); shoot(f"r_q50_{lbl}", math.radians(50), 'TEXTURE')
pose(0.0)
print("ok")
