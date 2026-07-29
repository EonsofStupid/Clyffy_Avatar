"""Facial region atlas — the shared foundation for every ARKit-52 blendshape.

    blender -b --python tools/face_atlas.py -- <parts.blend> <out_dir> <fwd_deg>

Each of the 43 authored shapes deforms a NAMED region. Detecting regions once and storing
them as WEIGHTED vertex groups means no shape re-derives geometry -- which is where this
build has been bitten repeatedly (world-vs-local space, sphere fit over the wrong support
set, lip classified by z instead of by chain).

Weights are smooth falloffs, never binary: a binary region tears at its edge exactly like
the 1.0-next-to-0.0 rim did.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6, "input not canonical"
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat
NECK = 0.208
head_m = co[:, 2] > NECK
hc = co[head_m].mean(axis=0); lat0 = float(hc @ lat)

gi = {g.name: g.index for g in ob.vertex_groups}
def grp(n):
    return np.array(sorted(v.index for v in me.vertices
                           for g in v.groups if g.group == gi[n] and g.weight > 0.5)) if n in gi else np.array([], int)

eyeL_c = np.array(ob["eye_L_center"]); eyeR_c = np.array(ob["eye_R_center"])
eyeL_r = float(ob["eye_L_radius"]);    eyeR_r = float(ob["eye_R_radius"])
EL, ER = grp("eye_L"), grp("eye_R")
eyeset = set(EL.tolist()) | set(ER.tolist())
di = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cav = {v for p in me.polygons if p.material_index == di for v in p.vertices}
surf = {v for p in me.polygons if p.material_index != di for v in p.vertices}
rim = np.array(sorted(cav & surf))
mouth_c = co[sorted(cav)].mean(axis=0)
partset = set()
for n in ("teeth_upper", "teeth_lower", "tongue"): partset |= set(grp(n).tolist())
# ⚠️ THE RIM IS NOT INTERIOR (2026-07-28). It is the LIP EDGE — the boundary where the
# cavity meets the skin — and excluding it here gave all 62 rim verts ZERO weight in
# lip_upper / lip_lower / lip_corner_*. Combined with shape_author's protect mask (which
# also froze it), the lip edge could not be moved by ANY of the 43 shapes: mouth morphs
# deformed the skin around the lips while the lip line itself stayed welded shut, so the
# mouth aperture was 100% jaw-driven. Two independent freezes, one symptom.
interior = (set(cav) - set(rim.tolist())) | partset   # bag/teeth/tongue only
print(f"eyes L{len(EL)}/R{len(ER)}  rim {len(rim)} (INCLUDED in the skin — it is the lip "
      f"edge)  interior+parts excluded {len(interior)}")

# ---- lip chains, by loop position (never by z -- that flips where the rim zigzags) ----
ef = {}
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k+1) % len(vs)]
        ef.setdefault((min(i, j), max(i, j)), []).append(p.material_index == di)
rimset = set(int(x) for x in rim); adjr = {}
for (i, j), mats in ef.items():
    if i in rimset and j in rimset and any(mats) and not all(mats):
        adjr.setdefault(i, []).append(j); adjr.setdefault(j, []).append(i)
start = int(rim[0]); cyc = [start]; prev, cur = None, start
while True:
    nxt = [n for n in adjr[cur] if n != prev]
    prev, cur = cur, nxt[0]
    if cur == start: break
    cyc.append(cur)
cyc = np.array(cyc); L = len(cyc)
clat = co[cyc] @ lat - lat0
ci = sorted([int(np.argmin(clat)), int(np.argmax(clat))])
chainA = np.zeros(L, bool); chainA[ci[0]:ci[1]+1] = True
if co[cyc[chainA], 2].mean() > co[cyc[~chainA], 2].mean(): chainA = ~chainA
lower_seed, upper_seed = cyc[chainA], cyc[~chainA]
cornerA, cornerB = int(cyc[ci[0]]), int(cyc[ci[1]])
print(f"lip chains: lower {len(lower_seed)}, upper {len(upper_seed)}, commissures {cornerA}/{cornerB}")

def falloff(seed_pts, reach, exclude=frozenset(), restrict=None):
    """weight = smoothstep(1 - d/reach) from the nearest seed point"""
    if len(seed_pts) == 0: return np.zeros(N)
    S = np.asarray(seed_pts, dtype=float).reshape(-1, 3)
    w = np.zeros(N)
    d = np.full(N, 1e9)
    for s in S:
        d = np.minimum(d, np.linalg.norm(co - s, axis=1))
    t = np.clip(1.0 - d/reach, 0.0, 1.0)
    w = t*t*(3 - 2*t)
    if restrict is not None: w[~restrict] = 0.0
    if exclude:
        w[np.array(sorted(exclude), dtype=int)] = 0.0
    return w

skin = head_m.copy()
skin[np.array(sorted(interior), dtype=int)] = False
skin_idx = np.where(skin)[0]

def snap(p):
    """Move a seed onto the SURFACE. A seed left inside the head is far from every vert:
    the nose seed produced 0 verts and the cheek seed peaked at 0.40 instead of 1.0."""
    k = int(np.argmin(np.linalg.norm(co[skin_idx] - np.asarray(p, float), axis=1)))
    return co[skin_idx[k]]

# ── LIP REGIONS MUST BE GEODESIC, NOT EUCLIDEAN ──────────────────────────────
# The two lip chains sit 0.0077 apart in space while the falloff reach is 0.030H, so a
# straight-line falloff from the upper chain covers the LOWER chain at ~1.0 as well.
# Measured after the rim was un-excluded: lip_upper and lip_lower BOTH had mean weight
# ~0.99 over all 62 rim verts. A "raise the upper lip" shape then raised both lips equally
# and the aperture did not change — full-strength mouthUpperUp* + mouthLowerDown* opened
# the mouth by 0.042%H against the jaw's 3.5%H.
#
# Distance ALONG THE SURFACE separates them, because the mouth is genuinely cut: to get
# from the upper lip to the lower one you must travel the long way around a commissure.
# This is the same reason jaw_rig.py solves its weights by diffusion over mesh edges rather
# than by proximity in space.
import heapq
_adj: dict[int, list[tuple[int, float]]] = {}
for p in me.polygons:
    if p.material_index == di:      # never path THROUGH the mouth bag
        continue
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = int(vs[k]), int(vs[(k + 1) % len(vs)])
        w_ = float(np.linalg.norm(co[i] - co[j]))
        _adj.setdefault(i, []).append((j, w_))
        _adj.setdefault(j, []).append((i, w_))

def geo_falloff(seed_ids, reach, exclude=frozenset(), restrict=None):
    """Multi-source Dijkstra over mesh edges → smoothstep falloff by SURFACE distance."""
    dist = np.full(N, np.inf)
    pq = []
    for s in np.asarray(seed_ids, dtype=int).tolist():
        dist[s] = 0.0
        heapq.heappush(pq, (0.0, s))
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist[u] or d > reach:
            continue
        for v, wv in _adj.get(u, ()):
            nd = d + wv
            if nd < dist[v] and nd <= reach:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    t = np.clip(1.0 - dist / reach, 0.0, 1.0)
    w = t * t * (3 - 2 * t)
    if restrict is not None: w[~restrict] = 0.0
    if exclude: w[np.array(sorted(exclude), dtype=int)] = 0.0
    return w

# ── THE OPERATOR'S SELECTION IS THE DOMAIN (ruling 2026-07-28) ───────────────
# The lip regions were bounded by a blind H*0.030 radius. The operator hand-picked the mouth
# faces precisely so the lips would be mapped from intent rather than from a magic number,
# and measurement backs that: the derived regions sat almost entirely INSIDE the selection
# (251 of 258 verts), while the selection covered 118 verts they never reached — nearly all
# of them BELOW the lip (down to 7.56%H vs the radius' 1.79%H) and further back.
#
# Dropping the lower lip really does pull the chin, so that reach is anatomically right; and
# bounding by the selection means a lip shape can never bleed into cheek or nose no matter
# how large the reach gets. Reach is now generous and the SELECTION does the limiting.
#
# `op_jaw_region` is not over-selected — it is a JAW map, and that is exactly how the rest of
# the pipeline consumes it (jaw_rig's rigid core, shape_author's jaw falloff). `op_lip_seam`
# is the lip line proper, and the rim chains seeding these falloffs descend from it.
LIP_DOMAIN = skin.copy()
_opreg = grp("op_jaw_region")
if len(_opreg):
    _sel = np.zeros(N, bool); _sel[_opreg] = True
    LIP_DOMAIN &= _sel
    print(f"lip domain = operator op_jaw_region ({int(_sel.sum())} verts) ∩ skin "
          f"-> {int(LIP_DOMAIN.sum())} verts")
else:
    print("!! no op_jaw_region — falling back to the radius-bounded skin domain")

REGIONS = {}
REGIONS["lip_upper"]  = geo_falloff(upper_seed, H*0.090, exclude=interior, restrict=LIP_DOMAIN)
REGIONS["lip_lower"]  = geo_falloff(lower_seed, H*0.090, exclude=interior, restrict=LIP_DOMAIN)
REGIONS["lip_corner_L"] = geo_falloff([cornerA], H*0.090, exclude=interior, restrict=LIP_DOMAIN)
REGIONS["lip_corner_R"] = geo_falloff([cornerB], H*0.090, exclude=interior, restrict=LIP_DOMAIN)
print(f"lip cross-talk, geodesic only: lip_upper on the LOWER chain "
      f"{REGIONS['lip_upper'][lower_seed].mean():.3f}, lip_lower on the UPPER chain "
      f"{REGIONS['lip_lower'][upper_seed].mean():.3f}")

# ── UPPER AND LOWER MUST COMPETE, NOT OVERLAP ────────────────────────────────
# Geodesic distance separates the chains, but only while the reach is short. Widening it to
# cover the operator's selection lets weight travel the short way AROUND a commissure and
# back onto the opposite lip: cross-talk went 0.159 -> 0.454 when reach went 0.030 -> 0.090H.
# A vertex is then claimed by both lips at once and "raise the upper lip" raises the lower
# one with it, which is the defect this whole change exists to remove.
# Resolve it as a PARTITION: each lip keeps the share of a vertex it is closer to. Vertices
# on a chain go entirely to that chain; vertices equidistant around a corner split evenly,
# which is what the commissure should do.
_u, _l = REGIONS["lip_upper"].copy(), REGIONS["lip_lower"].copy()
_tot = _u + _l + 1e-9
REGIONS["lip_upper"] = _u * (_u / _tot)
REGIONS["lip_lower"] = _l * (_l / _tot)
_xl = float(REGIONS["lip_upper"][lower_seed].mean())
_xu = float(REGIONS["lip_lower"][upper_seed].mean())
print(f"lip cross-talk after the partition: lip_upper on the LOWER chain {_xl:.3f}, "
      f"lip_lower on the UPPER chain {_xu:.3f}  (Euclidean gave ~0.99 both ways)")
assert _xl < 0.25 and _xu < 0.25, (
    f"lip regions still overlap ({_xl:.3f}/{_xu:.3f}) — a shape that moves one lip will move "
    f"the other and the mouth aperture will not respond")

for tag, c, r, ev in (("L", eyeL_c, eyeL_r, EL), ("R", eyeR_c, eyeR_r, ER)):
    outv = c - np.array([hc[0], hc[1], c[2]]); outv = outv/np.linalg.norm(outv)
    d = np.linalg.norm(co - c, axis=1)
    near = (d < r*1.9) & skin
    elev = (co - c)[:, 2]
    up_m  = near & (elev >  r*0.10)
    low_m = near & (elev < -r*0.10)
    REGIONS[f"eyelid_upper_{tag}"] = np.where(up_m,  np.clip(1.0 - (d - r)/(r*0.9), 0, 1), 0.0)
    REGIONS[f"eyelid_lower_{tag}"] = np.where(low_m, np.clip(1.0 - (d - r)/(r*0.9), 0, 1), 0.0)
    brow_c = snap(c + np.array([0, 0, r*1.9]) + outv*r*0.6)
    REGIONS[f"brow_{tag}"]  = falloff([brow_c], r*1.7, restrict=skin)
    cheek_c = snap(c + np.array([0, 0, -r*2.2]) + outv*r*0.9)
    REGIONS[f"cheek_{tag}"] = falloff([cheek_c], r*2.2, restrict=skin)

# The nose is the muzzle's most PROTRUDING point between the lip line and the eyes --
# a measured landmark, not an offset from a centroid that lands inside the head.
band = skin & (co[:, 2] > mouth_c[2] + H*0.020) & (co[:, 2] < min(eyeL_c[2], eyeR_c[2]) - H*0.020)
nose_c = co[int(np.where(band)[0][int(np.argmax(fp[band]))])] if band.any() else mouth_c
REGIONS["nose"] = falloff([nose_c], H*0.055, restrict=skin)
print(f"nose seed ({nose_c[0]:+.4f},{nose_c[1]:+.4f},{nose_c[2]:+.4f})  "
      f"from {int(band.sum())} muzzle-band verts")

print("\nregion            verts>0.05   peak   centroid-lateral   symmetry-partner")
for name in sorted(REGIONS):
    w = REGIONS[name]
    nz = np.where(w > 0.05)[0]
    clatm = float((co[nz] @ lat).mean() - lat0) if len(nz) else 0.0
    print(f"  {name:18s} {len(nz):6d}   {w.max():.2f}   {clatm:+.4f}")
    g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    for i in nz: g.add([int(i)], float(w[i]), 'REPLACE')

# SYMMETRY, measured SPATIALLY not by vert count. The eyeball domes are themselves 585 vs
# 397 verts, so this mesh's density is genuinely asymmetric and a count ratio will always
# look skewed even when the regions are correctly placed. Mirror the L centroid across the
# midplane and compare where it lands, and compare total weight.
print("\nsymmetry (spatial — mirror L across the midline, compare to R):")
for base in ("eyelid_upper", "eyelid_lower", "brow", "cheek", "lip_corner"):
    a_, b_ = REGIONS.get(f"{base}_L"), REGIONS.get(f"{base}_R")
    if a_ is None or b_ is None: continue
    ca_ = (co*a_[:, None]).sum(axis=0)/max(a_.sum(), 1e-9)
    cb_ = (co*b_[:, None]).sum(axis=0)/max(b_.sum(), 1e-9)
    mir = ca_ - lat*2.0*(float(ca_ @ lat) - lat0)          # mirror across the midplane
    dist = float(np.linalg.norm(mir - cb_))
    wr = max(a_.sum(), b_.sum())/max(1e-9, min(a_.sum(), b_.sum()))
    flag = "OK" if dist < H*0.035 else "** OFF **"
    print(f"  {base:14s} mirrored-centroid offset {dist:.4f} ({100*dist/H:.2f}% of height) "
          f"weight ratio {wr:.2f}:1  {flag}")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_atlas.blend"))
print("saved clyffy_v2_atlas.blend")

# ---- verification maps ----
ca = me.color_attributes.get("atlas") or me.color_attributes.new(name="atlas", type='FLOAT_COLOR', domain='POINT')
PALETTE = {"lip_upper":(0.95,0.25,0.2),"lip_lower":(0.2,0.55,0.95),"lip_corner_L":(1,0.85,0.1),
           "lip_corner_R":(0.1,0.9,0.5),"eyelid_upper_L":(0.95,0.4,0.1),"eyelid_lower_L":(0.4,0.2,0.9),
           "eyelid_upper_R":(0.95,0.4,0.1),"eyelid_lower_R":(0.4,0.2,0.9),"brow_L":(0.9,0.1,0.6),
           "brow_R":(0.9,0.1,0.6),"cheek_L":(0.1,0.8,0.8),"cheek_R":(0.1,0.8,0.8),"nose":(0.6,0.9,0.2)}
cols = np.tile(np.array([0.5,0.5,0.52,1.0]), (N,1))
best = np.zeros(N)
for name, w in REGIONS.items():
    c = np.array(list(PALETTE.get(name,(1,1,1))) + [1.0])
    take = w > best
    cols[take] = c*np.clip(w[take],0,1)[:,None] + np.array([0.5,0.5,0.52,1.0])*(1-np.clip(w[take],0,1))[:,None]
    best = np.maximum(best, w)
ca.data.foreach_set("color", cols.ravel()); me.color_attributes.active_color = ca
sc = bpy.context.scene
for o in [x for x in bpy.data.objects if x.type=='ARMATURE']: o.hide_render=True
for o in [x for x in bpy.data.objects if x.type=='CAMERA']: bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=sc.render.resolution_y=760
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=0.34
Rr=H*5; ctr=(eyeL_c+eyeR_c)/2; ctr[2]=(ctr[2]+mouth_c[2])/2
for off,tag in ((0,"atlas_front"),(math.radians(35),"atlas_q35")):
    ang=a+off
    cam.location=(hc[0]+math.sin(ang)*Rr, hc[1]-math.cos(ang)*Rr, ctr[2])
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
