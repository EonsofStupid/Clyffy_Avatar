"""Seal the rest lip slit so teeth stay hidden when the jaw is closed.

    blender -b --python tools/lip_seal.py -- <in.blend> <out.blend> <fwd_deg> [amount]

The mouth cut leaves a real gap between the upper and lower rim chains
(median ~0.0065 on this mesh). At rest that gap is a viewing tunnel into the
cavity — teeth sit ~0.025 behind the rim but still read through the slit.
This tool closes the gap by moving each rim chain toward its partner, with a
soft falloff into the surrounding skin so the seal does not crease.

amount (default 0.90): fraction of the half-gap closed. 1.0 is fully midplane;
slightly under 1 leaves a hairline so topology never z-fights.

Does NOT touch: teeth, tongue, eyeballs, or deep cavity verts (only the rim
and a tight skin falloff). Jaw-open is unaffected in spirit — the rest pose
simply starts closed; the jaw bone still rotates the lower chain open.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
FWD = float(argv[2])
amount = float(argv[3]) if len(argv) > 3 else 0.85
# Optional 5th arg: forward bulk as fraction of H (thickens the seal pad so the
# crease does not read as a hard white specular line under studio light).
fwd_bulk_frac = float(argv[4]) if len(argv) > 4 else 0.0025
SOFT_REACH_FRAC = 0.018   # × body height — skin falloff around the rim

os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
ob = max([o for o in bpy.data.objects if o.type == "MESH"],
         key=lambda o: len(o.data.vertices))
me = ob.data
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6, "input not canonical"
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
co0 = co.copy()
zmin, zmax = float(co[:, 2].min()), float(co[:, 2].max())
H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
hc = co[co[:, 2] > 0.208].mean(0)
lat0 = float(hc @ lat)

di = [i for i, m in enumerate(me.materials)
      if m and m.name.startswith("clyffy_mouth_interior")][0]
cav, surf = set(), set()
for p in me.polygons:
    (cav if p.material_index == di else surf).update(p.vertices)
rim = np.array(sorted(cav & surf), dtype=int)
print(f"rim {len(rim)}  cavity {len(cav)}  amount {amount}")

# ── rim cycle → upper / lower chains (chain membership, never z) ─────────────
ef = {}
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k + 1) % len(vs)]
        ef.setdefault((min(i, j), max(i, j)), []).append(p.material_index == di)
rimset = set(int(x) for x in rim)
adj = {}
for (i, j), mats in ef.items():
    if i in rimset and j in rimset and any(mats) and not all(mats):
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
start = int(rim[0])
cyc = [start]
prev, cur = None, start
while True:
    nxt = [n for n in adj[cur] if n != prev]
    if not nxt:
        raise RuntimeError("rim cycle broken")
    prev, cur = cur, nxt[0]
    if cur == start:
        break
    cyc.append(cur)
cyc = np.array(cyc, dtype=int)
L = len(cyc)
clat = co[cyc] @ lat - lat0
ci = sorted([int(np.argmin(clat)), int(np.argmax(clat))])
chainA = np.zeros(L, bool)
chainA[ci[0] : ci[1] + 1] = True
if co[cyc[chainA], 2].mean() > co[cyc[~chainA], 2].mean():
    chainA = ~chainA
lower = cyc[chainA]
upper = cyc[~chainA]
print(f"chains lower {len(lower)} upper {len(upper)}  commissures {cyc[ci[0]]}/{cyc[ci[1]]}")

# ── pair each upper vert to nearest lower; close toward midpoint ─────────────
delta = np.zeros((N, 3))
gaps = []
# lower may be claimed by several uppers — accumulate and average
lo_acc = {int(i): [] for i in lower}
for ui in upper:
    ui = int(ui)
    d = np.linalg.norm(co[lower] - co[ui], axis=1)
    k = int(np.argmin(d))
    li = int(lower[k])
    gap = float(d[k])
    gaps.append(gap)
    mid = 0.5 * (co[ui] + co[li])
    delta[ui] = amount * (mid - co[ui])
    lo_acc[li].append(amount * (mid - co[li]))
for li, vecs in lo_acc.items():
    if not vecs:
        continue
    delta[li] = np.mean(vecs, axis=0)
gaps = np.array(gaps)
print(f"pre-seal gap min/med/max {gaps.min():.5f}/{np.median(gaps):.5f}/{gaps.max():.5f}  "
      f"({100*np.median(gaps)/H:.3f}%H med)")

# Forward bulk: push the sealed pad toward the camera so the crease is a thick
# flesh lip, not a knife-edge that blows out white under studio lighting.
# First-pass seal at amount=0.9 closed the gap but left a bright specular line
# that survived even with teeth materials dimmed — that was the crease, not teeth.
bulk = fwd * (H * fwd_bulk_frac)
for i in list(upper) + list(lower):
    delta[int(i)] = delta[int(i)] + bulk
print(f"forward bulk {H*fwd_bulk_frac:.5f} ({100*fwd_bulk_frac:.2f}%H) amount={amount}")

# ── soft falloff into surrounding SKIN (not deep cavity, not parts) ──────────
gi = {g.name: g.index for g in ob.vertex_groups}

def grp(n, thr=0.5):
    if n not in gi:
        return set()
    idx = gi[n]
    return {v.index for v in me.vertices
            for g in v.groups if g.group == idx and g.weight > thr}

protected = set()
for n in ("teeth_upper", "teeth_lower", "tongue", "eye_L", "eye_R"):
    protected |= grp(n)
# deep cavity (cavity but not rim) stays — only rim + skin falloff move
deep_cav = cav - set(int(x) for x in rim)
protected |= deep_cav

rim_list = [int(x) for x in rim]
rim_co = co[rim]
reach = H * SOFT_REACH_FRAC
skin = np.array(sorted(surf - protected - set(rim_list)), dtype=int)
# nearest rim vert for each skin vert
# chunked for memory
nn = np.empty(len(skin), dtype=int)
dmin = np.full(len(skin), 1e9)
step = 32
for s0 in range(0, len(rim_co), step):
    S = rim_co[s0:s0 + step]
    diff = co[skin, None, :] - S[None, :, :]
    d = np.linalg.norm(diff, axis=2)  # (nskin, k)
    local_min = d.min(axis=1)
    local_arg = d.argmin(axis=1) + s0
    closer = local_min < dmin
    dmin[closer] = local_min[closer]
    nn[closer] = local_arg[closer]

soft_n = 0
for si, v in enumerate(skin):
    if dmin[si] >= reach:
        continue
    t = 1.0 - dmin[si] / reach
    w = t * t * (3 - 2 * t)
    # inherit the rim vert's delta
    ridx = rim_list[int(nn[si])]
    delta[v] = w * delta[ridx]
    soft_n += 1
print(f"soft falloff: {soft_n} skin verts within {reach:.4f}")

# never move protected with the lip delta
if protected:
    delta[np.array(sorted(protected), dtype=int)] = 0.0

# Inset teeth slightly deeper so a residual hairline never frames them.
# Teeth already sit ~0.025 behind the rim; another 0.008 is a safe margin.
teeth_inset = fwd * (-H * 0.008)
for n in ("teeth_upper", "teeth_lower"):
    for i in grp(n):
        delta[int(i)] = teeth_inset
print(f"teeth inset {H*0.008:.5f} along -fwd")

# apply
new = co + delta
me.vertices.foreach_set("co", new.ravel())
me.update()

# ── verify ───────────────────────────────────────────────────────────────────
co2 = np.empty((N, 3)); me.vertices.foreach_get("co", co2.ravel())
gaps2 = []
for ui in upper:
    ui = int(ui)
    d = np.linalg.norm(co2[lower] - co2[ui], axis=1)
    gaps2.append(float(d.min()))
gaps2 = np.array(gaps2)
moved = np.linalg.norm(delta, axis=1)
print(f"post-seal gap min/med/max {gaps2.min():.5f}/{np.median(gaps2):.5f}/{gaps2.max():.5f}  "
      f"({100*np.median(gaps2)/H:.3f}%H med)")
print(f"moved verts {(moved > 1e-7).sum()}  max disp {moved.max():.5f} ({100*moved.max()/H:.3f}%H)")
print(f"gap reduction med {100*(1 - np.median(gaps2)/max(np.median(gaps), 1e-12)):.1f}%")

# shape keys: if present, Basis must track the sealed rest, and every shape key
# target must receive the SAME delta so relative shapes are preserved.
if me.shape_keys is not None:
    kb = me.shape_keys.key_blocks
    print(f"propagating seal delta into {len(kb)} shape keys")
    for sk in kb:
        for i in np.where(moved > 1e-9)[0]:
            sk.data[int(i)].co = Vector(np.array(sk.data[int(i)].co) + delta[i])
    # mesh co already sealed; Basis should match mesh
    if "Basis" in kb:
        for i in range(N):
            kb["Basis"].data[i].co = Vector(new[i])

# ── CONTAINMENT GATE (authoritative) ─────────────────────────────────────────
# This is the stage that owns "nothing may be visible at rest", so this is where it gets
# MEASURED. mouth_parts.py declared it a hard criterion but only ever checked it by eye, and
# it had been failing — tooth slivers were poking through both commissures in every hero
# render since the parts were added.
#
# Cast a fan of rays outward from each interior vertex. A vertex properly inside the closed
# head hits skin in every outward direction: the mouth bag is an INDENTATION, not a hole, so
# a ray leaving it still crosses the front wall. A ray that escapes means a clear line to the
# outside — that vertex is visible.
from mathutils.bvhtree import BVHTree

gi_all = {g.name: g.index for g in ob.vertex_groups}
def _members(name):
    if name not in gi_all: return []
    return [v.index for v in me.vertices
            for g in v.groups if g.group == gi_all[name] and g.weight > 0.5]
parts = {n: _members(n) for n in ("teeth_lower", "teeth_upper", "tongue")}
part_vs = set().union(*[set(v) for v in parts.values()]) if parts else set()
if part_vs:
    skin_polys = [tuple(p.vertices) for p in me.polygons if not (set(p.vertices) & part_vs)]
    bvh = BVHTree.FromPolygons([Vector(c) for c in co2], skin_polys,
                               all_triangles=False, epsilon=0.0)
    fanv = []
    for yaw in (-40, -20, 0, 20, 40):
        for pitch in (-30, 0, 30):
            d = (Vector(fwd)*math.cos(math.radians(yaw))
                 + Vector(lat)*math.sin(math.radians(yaw)))
            d = d*math.cos(math.radians(pitch)) + Vector((0, 0, 1))*math.sin(math.radians(pitch))
            fanv.append(d.normalized())
    leaked = 0
    for name, ids in parts.items():
        if not ids: continue
        vis = [i for i in ids
               if any(bvh.ray_cast(Vector(co2[i]) + d*(H*1e-4), d, H*0.6)[0] is None
                      for d in fanv)]
        leaked += len(vis)
        print(f"containment {name:<13} {len(vis):>3} of {len(ids)} verts visible at rest"
              + ("   ** LEAK **" if vis else ""))
    if leaked:
        print(f"!! CONTAINMENT FAILING: {leaked} interior vertices are visible in the sealed "
              f"rest pose. Raise `amount`, or raise mouth_parts INSET so the arches sit "
              f"further back.")
    else:
        print("containment GREEN: no tooth or tongue vertex has a clear line out at rest")

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"saved {OUT}")
print("ok")
