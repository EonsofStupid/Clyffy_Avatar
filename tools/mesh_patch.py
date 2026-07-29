"""Close the inherited hole in the base mesh. Runs LAST — adds faces, never vertices.

    blender -b --python tools/mesh_patch.py -- <body.blend> <out_dir> [fwd_deg]

The Tripo base mesh ships with 19 boundary edges forming ONE hole 0.13%H across at mid-torso
(50.7%H from the top, verts 85 / 817-822 / 45985-45991) and 1 non-manifold edge beside it.
Verified identical before and after every stage this pack adds, so it is inherited, not ours
— but "inherited" is a reason to scope it, not a reason to leave it unclassified.

WHY IT RUNS LAST AND WHY IT ONLY ADDS FACES. Fixing it at `canonicalize` would be tidier in
principle and would mean re-running all twelve stages; more importantly, anything that changes
VERTEX COUNT invalidates the whole chain — `body_rig` transfers face weights BY INDEX and
asserts equal counts. Filling a boundary loop with a triangle fan over its OWN vertices adds
faces only, so vertex count, indices, weights and all 47 shape keys are untouched. Same play
`hoof.py` uses.

Impact, stated honestly: invisible at any demo framing. It matters when the VRM is handed to
someone else, where a non-watertight mesh is a real defect.
"""
import bpy, bmesh, sys, os, math
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2]) if len(argv) > 2 else 235.1
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N0 = len(me.vertices)
F0 = len(me.polygons)
co = np.empty((N0, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())

bm = bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

def survey(tag):
    nm = [e for e in bm.edges if not e.is_manifold and not e.is_boundary]
    bd = [e for e in bm.edges if e.is_boundary]
    print(f"  {tag:<8} verts {len(bm.verts)} faces {len(bm.faces)} "
          f"non-manifold {len(nm)} boundary {len(bd)}")
    return nm, bd

print("hygiene:")
nm0, bd0 = survey("before")

# ── group the boundary edges into loops ──────────────────────────────────────
loops = []
if bd0:
    adj = {}
    for e in bd0:
        i, j = e.verts[0], e.verts[1]
        adj.setdefault(i, set()).add(j); adj.setdefault(j, set()).add(i)
    seen = set()
    for s in list(adj):
        if s in seen: continue
        stack, comp = [s], []
        while stack:
            v = stack.pop()
            if v in seen: continue
            seen.add(v); comp.append(v)
            stack.extend(adj[v] - seen)
        loops.append(comp)

for k, comp in enumerate(loops):
    P = np.array([[v.co.x, v.co.y, v.co.z] for v in comp])
    span = float(np.linalg.norm(P.max(axis=0) - P.min(axis=0)))
    print(f"  hole {k}: {len(comp)} verts, span {span:.5f} ({100*span/H:.3f}%H), "
          f"z {P[:, 2].mean():+.4f}")

# ── STEP 1: remove the SLIVER that makes the edge non-manifold ───────────────
# Diagnosed rather than assumed. The single non-manifold edge (v818-v85) carries THREE faces,
# and one of them is a triangle of area 7.0e-08 — about 1% of a typical face here — bridging
# an otherwise open chain. A sliver stitched across a hole is the defect; the hole itself is
# just its symptom, which is why filling first only ever got 19 boundary edges down to 5.
areas = np.array([f.calc_area() for f in bm.faces])
med = float(np.median(areas[areas > 0])) if len(areas) else 1.0
SLIVER = 0.05 * med
killed = []
for e in [e for e in bm.edges if not e.is_manifold and not e.is_boundary]:
    slivers = sorted((f for f in e.link_faces), key=lambda f: f.calc_area())
    if slivers and slivers[0].calc_area() < SLIVER:
        killed.append((slivers[0].index, slivers[0].calc_area()))
        bmesh.ops.delete(bm, geom=[slivers[0]], context="FACES_ONLY")
if killed:
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    for idx, ar in killed:
        print(f"  removed sliver face {idx} (area {ar:.3e}, median face {med:.3e})")
    survey("mid")

# ── STEP 2: fill what is now a clean boundary ───────────────────────────────
# bmesh's own hole fill is the right tool: it triangulates the loop in place and takes its
# winding from the surrounding faces, which a hand-rolled fan does not.
filled = 0
for attempt in range(4):
    edges = [e for e in bm.edges if e.is_boundary]
    if not edges:
        break
    try:
        res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        made = len(res.get("faces", []))
        print(f"  holes_fill pass {attempt + 1}: {made} face(s) from {len(edges)} boundary edge(s)")
        filled += made
        if made == 0:
            break
        bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    except Exception as e:
        print(f"  holes_fill failed: {e}")
        break

# ── STEP 3: sweep WIRE edges ────────────────────────────────────────────────
# Deleting the sliver leaves its edges behind wherever they were not shared. A wire edge
# (0 link faces) reports as "non-manifold" and is pure debris — it is not a topology fault,
# but leaving it means the hygiene line never reads clean and the next person cannot tell the
# difference between debris and a real defect.
wires = [e for e in bm.edges if len(e.link_faces) == 0]
if wires:
    print(f"  removing {len(wires)} wire edge(s): "
          + ", ".join(f"v{e.verts[0].index}-v{e.verts[1].index}" for e in wires[:5]))
    bmesh.ops.delete(bm, geom=wires, context="EDGES")
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

if filled or killed or wires:
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
nm1, bd1 = survey("after")
bm.verts.index_update(); bm.faces.index_update()
bm.to_mesh(me); bm.free(); me.update()

N1 = len(me.vertices)
assert N1 == N0, f"VERTEX COUNT CHANGED {N0} -> {N1} — this invalidates body_rig's index transfer"
print(f"  vertex count preserved: {N0} (faces {F0} -> {len(me.polygons)})")
if me.shape_keys:
    print(f"  shape keys intact: {len(me.shape_keys.key_blocks)}")

if len(bd1) == 0 and len(nm1) == 0:
    print("mesh_patch GREEN — watertight, no non-manifold edges")
else:
    print(f"mesh_patch PARTIAL — boundary {len(bd1)}, non-manifold {len(nm1)} remain")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, os.path.basename(SRC)))
print(f"saved {os.path.basename(SRC)}")
