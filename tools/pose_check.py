"""POSED containment — does anything break the skin in the states the character is SEEN in?

    blender -b --python tools/pose_check.py -- <body.blend> [fwd_deg]

Exit 0 = clean. Exit 1 if any interior vertex is outside the exterior skin in any pose.

WHY THIS EXISTS. `lip_seal.py` has a containment gate and it is a good one, but it only ever
tests REST — the pose where the lips are shut and nothing can escape by construction. Every
gate in the pack was green while the beauty heroes showed a white tooth sliver breaking the
lip at the left commissure in `talk_aa` and another speck at the right corner in `happy`.
That is the third blind spot of the same shape found in two days: the gates tested what was
cheap to test, not the states the character is actually seen in.

THE TEST IS NOT VISIBILITY. Teeth and tongue SHOULD be visible through an open mouth — that
is the whole point of having them. The defect is a tooth showing through the CHEEK or LIP.

THE METHOD: CAP THE MOUTH, THEN ASK INSIDE-OR-OUT.
The reason an open mouth is hard to test is that the skin surface has a hole in it, so
"inside the head" stops being well defined. So close it: build a membrane across the lip rim
(a triangle fan from the rim's centroid) and add it to the exterior skin. The head is now a
closed volume whose interior INCLUDES the mouth cavity. Then a plain parity test answers the
real question exactly —

    inside  -> contained, whether or not a camera can see it through the opening
    outside -> it has come through the cheek, the lip, or out past the mouth entirely

Parity is voted over three ray directions, because the base mesh carries one 0.13%H hole and
one non-manifold edge (inherited from Tripo) that can flip a single ray.

⚠️ TWO EARLIER TESTS WERE WRONG. Kept here so neither is retried.
  1. SIGNED DISTANCE to the nearest exterior-skin point. Reports 109 failures, but with the
     mouth open a tongue sitting correctly in the aperture has its nearest point on the lip
     rim and scores "outside" by up to 5.6%H. Flagged the tongue at every open vowel.
  2. RAY FAN + APERTURE POLYGON — escape is legal only through the mouth opening. Right in
     principle, wrong in practice: the lip rim spans 5.85%H fore-aft and is strongly
     NON-PLANAR, so fitting a plane and projecting gives a self-intersecting polygon and the
     even-odd test is meaningless. Reported 1516 failures, almost all at the mouth CENTRE —
     the one place the test was supposed to permit.
Both failed the same way: they were clustered where the mouth OPENS, not where it breaks.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import VISEMES, PRESETS, ENVELOPE  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
RIG = os.path.abspath(argv[0])
FWD = float(argv[1]) if len(argv) > 1 else 235.1
# A vertex is only reported once it is clearly proud of the surface. Floating-point noise on
# a nearest-point query is ~1e-6; this is 0.02%H, comfortably above it and still far tighter
# than anything that shows in a render.
TOL = float(argv[2]) if len(argv) > 2 else 0.0002

bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
me = ob.data
kb = me.shape_keys.key_blocks if me.shape_keys else None
N = len(me.vertices)
base = np.empty((N, 3))
(kb["Basis"].data if kb else me.vertices).foreach_get("co", base.ravel())
H = float(base[:, 2].max() - base[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])
lv = Vector(lat)
MAXDEG = float(ENVELOPE["jaw"]["max_deg"])

gi = {g.name: g.index for g in ob.vertex_groups}
def IDX(n):
    if n not in gi: return np.array([], dtype=int)
    k = gi[n]
    return np.array([v.index for v in me.vertices
                     if any(g.group == k and g.weight > 0.5 for g in v.groups)], dtype=int)
PART = {n: IDX(n) for n in ("teeth_upper", "teeth_lower", "tongue")}
PARTSET = set()
for v in PART.values(): PARTSET |= set(v.tolist())

di = {i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")}
# Occluder = everything that is not a PART: exterior skin AND the mouth bag. The bag has to
# be in it — it is the back wall a contained tooth's rays run into.
skin_poly_ids = [i for i, p in enumerate(me.polygons) if not set(p.vertices) <= PARTSET]
cavset = {v for p in me.polygons if p.material_index in di for v in p.vertices}
surfset = {v for p in me.polygons if p.material_index not in di for v in p.vertices}
RIM = np.array(sorted(cavset & surfset), dtype=int)
lat0 = float(base[base[:, 2] > 0.208].mean(axis=0) @ lat)
rim_half = float(np.abs(base[RIM] @ lat - lat0).max())

# The lip rim, walked as a CYCLE. Never split or order it by z — a z-order disagrees with the
# real loop on ~25 of 62 verts (documented trap; it under-reports the aperture about tenfold).
_ef = {}
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k + 1) % len(vs)]
        _ef.setdefault((min(i, j), max(i, j)), []).append(p.material_index in di)
_rs = set(int(x) for x in RIM); _adj = {}
for (i, j), mm in _ef.items():
    if i in _rs and j in _rs and any(mm) and not all(mm):
        _adj.setdefault(i, []).append(j); _adj.setdefault(j, []).append(i)
_st = int(RIM[0]); RIM_CYC = [_st]; _prev, _cur = None, _st
while True:
    _nx = [n for n in _adj[_cur] if n != _prev]
    _prev, _cur = _cur, _nx[0]
    if _cur == _st: break
    RIM_CYC.append(_cur)
RIM_CYC = np.array(RIM_CYC, dtype=int)
print(f"mesh {N} verts, H {H:.4f} | parts "
      f"{'/'.join(str(len(v)) for v in PART.values())} | occluder polys {len(skin_poly_ids)}")
print(f"lip rim cycle {len(RIM_CYC)} verts — the aperture the mouth is allowed to show through")

jaw_b = arm.pose.bones.get("jaw") if arm else None
hv = Vector(jaw_b.bone.head_local) if jaw_b else Vector((0, 0, 0))

# Exterior skin only (no bag, no parts) — the cap supplies the rest of the closed surface.
EXT_POLYS_TEMPLATE = [tuple(me.polygons[i].vertices) for i in range(len(me.polygons))
                      if me.polygons[i].material_index not in di
                      and not set(me.polygons[i].vertices) <= PARTSET]
print(f"exterior skin polys {len(EXT_POLYS_TEMPLATE)} + {len(RIM_CYC)} cap triangles")

def pose(mix):
    if kb:
        for k in kb:
            if k.name != "Basis": k.value = 0.0
    jaw = 0.0
    for n, v in mix.items():
        if n == "jawOpen":
            jaw = float(v); continue
        if kb and n in kb and n != "Basis":
            kb[n].value = float(max(0.0, min(1.0, v)))
    if jaw_b:
        jaw_b.rotation_mode = "QUATERNION"
        jaw_b.matrix = jaw_b.bone.matrix_local.copy()
        if jaw > 0.0:
            ang = math.radians(MAXDEG) * max(0.0, min(1.0, jaw))
            R = (Matrix.Translation(hv) @ Matrix.Rotation(ang, 4, lv) @ Matrix.Translation(-hv))
            jaw_b.matrix = R @ jaw_b.bone.matrix_local
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    obe = ob.evaluated_get(dg); ev = obe.to_mesh()
    C = np.empty((len(ev.vertices), 3)); ev.vertices.foreach_get("co", C.ravel())
    polys = [tuple(ev.polygons[i].vertices) for i in skin_poly_ids]
    obe.to_mesh_clear()
    return C, polys

# Three probe directions for the parity vote. Deliberately oblique and mutually unlike, so a
# single bad crossing (the inherited pinhole, a coincident edge) cannot carry the verdict.
PARITY_DIRS = [Vector(v).normalized() for v in
               ((0.37, 0.71, 0.60), (-0.83, 0.21, -0.52), (0.19, -0.88, 0.44))]

def capped_occluder(C):
    """Exterior skin + a membrane across the lip rim, so the head is a CLOSED volume.

    Without the cap "inside the head" is undefined the moment the mouth opens, which is what
    sank both earlier tests. The bag is deliberately NOT included: with the cap on, the
    enclosed volume is the head INCLUDING its mouth cavity, which is exactly the region a
    tooth or the tongue is allowed to occupy.
    """
    verts = [Vector(c) for c in C]
    ctr = C[RIM_CYC].mean(axis=0)
    ci = len(verts)
    verts.append(Vector(ctr))
    polys = list(EXT_POLYS_TEMPLATE)
    L = len(RIM_CYC)
    for k in range(L):
        polys.append((int(RIM_CYC[k]), int(RIM_CYC[(k + 1) % L]), ci))
    return verts, polys

def inside(bvh, p):
    """Parity vote: is p inside the closed capped surface?"""
    votes = 0
    for d in PARITY_DIRS:
        n, o, guard = 0, Vector(p), 0
        while guard < 64:
            hit = bvh.ray_cast(o + d * (H * 1e-5), d, H * 4.0)
            if hit[0] is None:
                break
            n += 1
            o = hit[0]
            guard += 1
        votes += (n % 2)
    return votes >= 2

def check(tag, mix):
    C, _ = pose(mix)
    verts, polys = capped_occluder(C)
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    worst, per = [], {}
    for name, idx in PART.items():
        n_bad = 0
        for i in idx:
            if not inside(bvh, Vector(C[i])):
                n_bad += 1
                worst.append((name, int(i),
                              abs(float(C[i] @ lat) - lat0) / max(rim_half, 1e-9)))
        per[name] = n_bad
    total = sum(per.values())
    mark = "  ** THROUGH THE SKIN **" if total else ""
    print(f"  {tag:<16} through-skin: teeth_upper {per['teeth_upper']:>3}  "
          f"teeth_lower {per['teeth_lower']:>3}  tongue {per['tongue']:>3}{mark}")
    if worst:
        arcs = [w[2] for w in worst]
        print(f"       arch pos {min(arcs):.2f}–{max(arcs):.2f} median {float(np.median(arcs)):.2f}"
              f"  e.g. {worst[0][0]} v{worst[0][1]}")
    return total, worst

print("\nPOSED CONTAINMENT — interior geometry outside the exterior skin")
cases = [("rest", {})]
cases += [(f"viseme {n}", dict(VISEMES[n])) for n in VISEMES]
cases += [(f"preset {n}", dict(PRESETS[n])) for n in PRESETS]
cases += [(f"jawOpen {v:.2f}", {"jawOpen": v}) for v in (0.25, 0.5, 0.75, 1.0)]
# The corner is where it fails, so drive the corner shapes hard as their own cases.
cases += [("smile@1", {"mouthSmileLeft": 1.0, "mouthSmileRight": 1.0}),
          ("stretch@1", {"mouthStretchLeft": 1.0, "mouthStretchRight": 1.0}),
          ("aa+smile", dict(VISEMES["aa"], mouthSmileLeft=0.8, mouthSmileRight=0.8))]

grand = 0
all_worst = []
for tag, mix in cases:
    t, w = check(tag, mix)
    grand += t
    all_worst += w

print()
if grand == 0:
    print(f"pose_check GREEN — nothing breaks the skin in {len(cases)} posed states")
    sys.exit(0)
arcs = [w[2] for w in all_worst]
from collections import Counter
by_part = Counter(w[0] for w in all_worst)
print(f"pose_check RED — {grand} vertex-instances outside the capped head across {len(cases)} states")
print(f"  by part: {dict(by_part)}")
print(f"  arch positions {min(arcs):.2f}–{max(arcs):.2f}, median {float(np.median(arcs)):.2f} "
      f"(near 1.0 = the COMMISSURES)")
sys.exit(1)
