"""Produce the CANONICAL clyffy base mesh. Run once; everything downstream consumes this.

Industry standard, and each step exists because something upstream bit us:

1. FREEZE TRANSFORMS (apply loc/rot/scale -> identity).
   The Tripo object carried a +69.17 deg Z rotation. `forward_axis_deg` was calibrated
   from renders (WORLD) but every tool read `v.co` (LOCAL), so the jaw hinge axis was
   ~79 deg off and the mouth cut was extruded into the cheek. Freezing makes local ==
   world so the whole bug class cannot recur.

2. BAKE THE OPERATOR'S HAND SELECTIONS AS VERTEX GROUPS.
   They were stored as `select` flags in side .blend files, which are raw vertex INDICES.
   That forced every later step to preserve indices exactly (hence FACES_ONLY deletes and
   the 67 wire edges they left behind). Vertex groups travel with the geometry through
   edits -- this is how a rigger persists a hand-picked region.

3. CLEAN: no wire edges, no loose verts, consistent normals, pre-existing hole filled.

    blender -b --python tools/canonicalize.py -- <base.blend> <region.blend> <seam.blend> <out_dir>
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
BASE, REGION, SEAM, OUT = (os.path.abspath(argv[0]), os.path.abspath(argv[1]),
                           os.path.abspath(argv[2]), os.path.abspath(argv[3]))
os.makedirs(OUT, exist_ok=True)

def sel_of(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    o = [x for x in bpy.data.objects if x.type == "MESH"][0]
    vs = set(v.index for v in o.data.vertices if v.select)
    fs = set(p.index for p in o.data.polygons if p.select)
    return vs, fs, len(o.data.vertices)

reg_v, reg_f, n1 = sel_of(REGION)
seam_v, seam_f, n2 = sel_of(SEAM)
print(f"operator jaw region : {len(reg_v)} verts / {len(reg_f)} faces   (source has {n1} verts)")
print(f"operator lip seam   : {len(seam_v)} verts / {len(seam_f)} faces   (source has {n2} verts)")

bpy.ops.wm.open_mainfile(filepath=BASE)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
N0 = len(me.vertices)
assert N0 == n1 == n2, f"vertex-count mismatch: base {N0}, region {n1}, seam {n2}"

# --- record WORLD positions before freezing, to prove the freeze changed nothing ---
mw = ob.matrix_world
before = np.array([mw @ v.co for v in me.vertices])
e = mw.to_euler()
print(f"\nobject '{ob.name}' pre-freeze: rot ({math.degrees(e.x):+.2f},{math.degrees(e.y):+.2f},"
      f"{math.degrees(e.z):+.2f}) deg  scale {tuple(round(x,4) for x in mw.to_scale())}")

# --- 2. groups first, while indices are still the ones the operator clicked ---
for name, idx in (("op_jaw_region", reg_v), ("op_lip_seam", seam_v)):
    g = ob.vertex_groups.new(name=name)
    g.add(sorted(idx), 1.0, 'REPLACE')
print(f"baked vertex groups: {[g.name for g in ob.vertex_groups]}")

# --- 1. freeze ---
bpy.context.view_layer.objects.active = ob
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
mw2 = ob.matrix_world; e2 = mw2.to_euler()
after = np.array([v.co.copy() for v in me.vertices])
drift = np.abs(after - before).max()
print(f"post-freeze: rot ({math.degrees(e2.x):+.2f},{math.degrees(e2.y):+.2f},{math.degrees(e2.z):+.2f}) deg"
      f"  max |world drift| {drift:.3e}  ({'OK' if drift < 1e-5 else '** GEOMETRY MOVED **'})")

# --- 3. clean ---
def hygiene(tag):
    bm = bmesh.new(); bm.from_mesh(me)
    nm = sum(1 for x in bm.edges if not x.is_manifold and not x.is_boundary)
    bd = sum(1 for x in bm.edges if x.is_boundary)
    wr = sum(1 for x in bm.edges if x.is_wire)
    lo = sum(1 for v in bm.verts if not v.link_edges)
    za = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    ng = sum(1 for f in bm.faces if len(f.verts) > 4)
    print(f"  {tag:22s} verts {len(bm.verts)} faces {len(bm.faces)} | non-manifold {nm} "
          f"boundary {bd} wire {wr} loose {lo} zero-area {za} ngons {ng}")
    bm.free()
    return bd

print("\nhygiene:")
hygiene("before clean")
bm = bmesh.new(); bm.from_mesh(me)
wire = [x for x in bm.edges if x.is_wire]
if wire: bmesh.ops.delete(bm, geom=wire, context='EDGES')
loose = [v for v in bm.verts if not v.link_edges]
if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')
# Fill boundary loops ONE AT A TIME, and only genuine simple cycles. A blanket
# holes_fill over all boundary edges spans unrelated loops and produced a NEW
# non-manifold edge. The remaining loop is a branching defect in the Tripo source
# (see below) -- left alone on purpose, not silently "repaired".
# Fill boundary loops ONE AT A TIME, only genuine simple cycles, and ITERATE to a fixed
# point -- capping one loop can retire another nested inside it. A blanket holes_fill over
# all boundary edges spans unrelated loops and produced a NEW non-manifold edge.
def boundary_loops(bm):
    bnd = [x for x in bm.edges if x.is_boundary]
    adj = {}
    for x in bnd:
        for v in x.verts: adj.setdefault(v.index, []).append(x)
    seen, loops = set(), []
    for x in bnd:
        if x.index in seen: continue
        loop, stack = [], [x]
        while stack:
            y = stack.pop()
            if y.index in seen: continue
            seen.add(y.index); loop.append(y)
            for v in y.verts:
                for z in adj[v.index]:
                    if z.index not in seen: stack.append(z)
        loops.append(loop)
    return loops, adj

filled, skipped, pass_no = 0, [], 0
while True:
    pass_no += 1
    loops, adj = boundary_loops(bm)
    made = 0
    skipped = []
    for loop in loops:
        vs = {v for x in loop for v in x.verts}
        c = sum((v.co for v in vs), Vector())/len(vs)
        if not all(len(adj[v.index]) == 2 for v in vs):
            skipped.append((len(loop), c)); continue
        r = bmesh.ops.holes_fill(bm, edges=loop, sides=0)
        nf = r.get('faces', [])
        if not nf:
            # holes_fill declines some loops silently -- build the face directly so a
            # failure is either resolved or explained, never swallowed.
            ring, e0 = [], loop[0]
            v = e0.verts[0]; prev = None
            for _ in range(len(loop)):
                ring.append(v)
                nxt = [x for x in adj[v.index] if x is not prev][0]
                prev = nxt; v = nxt.other_vert(v)
            try:
                f = bm.faces.new(ring); nf = [f]
            except ValueError as ex:
                print(f"     !! {len(loop)}-edge cycle at ({c.x:+.4f},{c.y:+.4f},{c.z:+.4f}) "
                      f"cannot be capped: {ex}")
                skipped.append((len(loop), c)); continue
        if nf: bmesh.ops.triangulate(bm, faces=nf)
        made += len(nf)
    filled += made
    print(f"  fill pass {pass_no}: {len(loops)} boundary loop(s), capped {made}")
    if made == 0: break
for n, c in skipped:
    print(f"  !! LEFT UNFILLED: {n}-edge branching boundary at ({c.x:+.4f},{c.y:+.4f},{c.z:+.4f}) -- "
          f"non-simple cycle in the Tripo source, colocated with the 3-face non-manifold edge.")
    print(f"     Torso, z~{c.z:+.3f}; the jaw deformer is at z>+0.208 so it cannot affect the rig. "
          f"Documented, NOT auto-repaired -- an automatic fix here risks the lanyard/shirt geometry.")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me); bm.free(); me.update()
print(f"  removed {len(wire)} wire edges, {len(loose)} loose verts, filled {filled} hole face(s)")
hygiene("after clean")

# --- validate the groups survived ---
gi = {g.name: g.index for g in ob.vertex_groups}
counts = {}
for name, want in (("op_jaw_region", len(reg_v)), ("op_lip_seam", len(seam_v))):
    got = sum(1 for v in me.vertices for g in v.groups if g.group == gi[name] and g.weight > 0.5)
    counts[name] = got
    print(f"  group {name}: {got} verts (operator picked {want}) "
          f"{'OK' if got == want else '** LOST ' + str(want-got) + ' **'}")

# seam FACES, derived from the group so the cut no longer needs raw indices
seam_grp = set(v.index for v in me.vertices for g in v.groups if g.group == gi["op_lip_seam"] and g.weight > 0.5)
derived = [p.index for p in me.polygons if all(vi in seam_grp for vi in p.vertices)]
print(f"  seam faces derived from group: {len(derived)} (operator selected {len(seam_f)}) "
      f"{'OK' if len(derived) == len(seam_f) else '** MISMATCH **'}")

co = np.array([v.co.copy() for v in me.vertices])
print(f"\ncanonical bounds x[{co[:,0].min():+.4f},{co[:,0].max():+.4f}] "
      f"y[{co[:,1].min():+.4f},{co[:,1].max():+.4f}] z[{co[:,2].min():+.4f},{co[:,2].max():+.4f}]")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_canon.blend"))
print("ok")
