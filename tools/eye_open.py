"""Separate the eyeball domes from the skin along the socket rim.

Blink and gaze are the SAME job (BUILD_LOG 2026-07-26): while the mesh is welded, the skin
cannot slide over the eye because it is attached to it. Cut the dome free and the eyeball
becomes rigid (rotates for gaze) while the skin ring closes over it (blink).

Stage 1 of this tool VALIDATES that each socket rim is a closed simple cycle before any
cut happens -- the mouth cut taught us that a figure-eight boundary folds the extrude.

    blender -b --python tools/eye_open.py -- <open.blend> <out_dir> <fwd_deg> [--cut]
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
DO_CUT = "--cut" in argv
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6, "input not canonical"
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
NECK = 0.208
hc = co[co[:, 2] > NECK].mean(axis=0); lat0 = float(hc @ lat)
fp = co @ fwd

bm = bmesh.new(); bm.from_mesh(me)
# ALL layers up front: creating a bmesh layer invalidates existing element references.
domelay = bm.faces.layers.int.new("dome_tag")
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

# ---- socket rims as creases, merged (see tools/eye_probe.py) ----
band_lo, band_hi = NECK + (zmax-NECK)*0.35, NECK + (zmax-NECK)*0.90
crease = []
for e in bm.edges:
    if len(e.link_faces) != 2: continue
    v0, v1 = e.verts[0].index, e.verts[1].index
    zm = (co[v0, 2] + co[v1, 2])/2
    if not (band_lo < zm < band_hi): continue
    if (fp[v0] + fp[v1])/2 < float(hc @ fwd): continue
    n0, n1 = e.link_faces[0].normal, e.link_faces[1].normal
    if n0.length <= 0 or n1.length <= 0: continue
    if math.degrees(n0.angle(n1)) > 28.0: crease.append(e)
print(f"crease edges in the upper-front face: {len(crease)}")

adj = {}
for e in crease:
    v0, v1 = e.verts[0].index, e.verts[1].index
    adj.setdefault(v0, set()).add(v1); adj.setdefault(v1, set()).add(v0)
seen, groups = set(), []
for v in adj:
    if v in seen: continue
    stack, comp = [v], []
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); comp.append(x)
        stack.extend(adj[x])
    groups.append(comp)
merged = []
for g in sorted(groups, key=len, reverse=True):
    if len(g) < 4: continue
    c = co[np.array(g)].mean(axis=0)
    for m in merged:
        if np.linalg.norm(c - co[np.array(m)].mean(axis=0)) < 0.045: m.extend(g); break
    else: merged.append(list(g))
merged.sort(key=len, reverse=True)
rims = []
for m in merged[:4]:
    c = co[np.array(m)].mean(axis=0)
    off = float(c @ lat) - lat0
    if abs(off) > 0.015 and len(m) > 20: rims.append((np.array(sorted(set(m))), off, c))
rims.sort(key=lambda r: r[1])
print(f"socket rims found: {len(rims)}  lateral offsets {[round(r[1],4) for r in rims]}")
assert len(rims) == 2, f"expected 2 eye rims, got {len(rims)}"

# The crease gives a BAND of verts, not an edge loop (degrees 1/2/3, 58 edges for 51
# verts). Splitting along that produces a mess. Instead define the dome as a FACE REGION
# and take its boundary, which is a clean loop by construction -- the same pattern that
# made the mouth cut work.
bm.faces.ensure_lookup_table()
head_n = int((co[:, 2] > NECK).sum())

# The crease band is NOT continuous at 28 deg -- a flood fill seeded inside it escapes
# over the whole mesh (measured: 400% of the head). So the dome is defined DIRECTLY from
# the sphere fit instead, which is independent of crease continuity and which we already
# know is accurate (residual 4-7% of radius, tools/eye_probe.py).
def fit_dome(rimset, c0):
    outv = c0 - np.array([hc[0], hc[1], c0[2]])
    outv = outv/max(np.linalg.norm(outv), 1e-9)
    rad  = np.linalg.norm(co[rimset] - c0, axis=1).max()
    d    = np.linalg.norm(co - c0, axis=1)
    proj = (co - c0) @ outv
    near = np.where((d < rad*1.05) & (proj > -rad*0.15))[0]
    A = np.c_[2*co[near], np.ones(len(near))]
    b = (co[near]**2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    ctr = sol[:3]; r = math.sqrt(max(sol[3] + (ctr**2).sum(), 1e-12))
    resid = np.abs(np.linalg.norm(co[near] - ctr, axis=1) - r)
    return ctr, r, outv, rad, resid.mean()

results = []
for rimset, off, c0 in rims:
    tag = "LEFT " if off < 0 else "RIGHT"
    ctr, r, outv, rad, resid = fit_dome(rimset, c0)
    # cap half-angle implied by the rim: sin(theta) = rim_radius / sphere_radius
    sin_t = min(0.999, rad/max(r, 1e-9))
    cos_t = math.sqrt(max(0.0, 1.0 - sin_t*sin_t))
    dv = ((np.linalg.norm(co - ctr, axis=1) < r*1.20) &
          (((co - ctr) @ outv) > r*max(cos_t*0.90, 0.35)))
    dset = set(int(i) for i in np.where(dv)[0])
    dome_faces = set(f.index for f in bm.faces if all(v.index in dset for v in f.verts))
    fverts = set()
    for fi in dome_faces: fverts.update(v.index for v in bm.faces[fi].verts)
    print(f"  {tag} sphere r={r:.4f} resid {resid:.5f} | rim radius {rad:.4f} -> cap "
          f"half-angle {math.degrees(math.asin(sin_t)):.1f} deg")
    print(f"     dome region: {len(dome_faces)} faces / {len(fverts)} verts "
          f"({100*len(fverts)/head_n:.1f}% of the head)")
    if not dome_faces or len(fverts) > head_n*0.25:
        print("     ** dome region is empty or leaked -- not cutting **"); sys.exit(1)

    # boundary of the face region, with the mouth's pinch fix applied
    for it in range(8):
        deg = {}
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) == 2 and (lf[0].index in dome_faces) != (lf[1].index in dome_faces):
                for v in e.verts: deg[v.index] = deg.get(v.index, 0) + 1
        pinch = [v for v, dg in deg.items() if dg != 2]
        if not pinch:
            print(f"     boundary closed after {it} growth pass(es)"); break
        add = {f.index for vi in pinch for f in bm.verts[vi].link_faces
               if f.index not in dome_faces and all(
                   (v.index in dset) or (v.index in deg) for v in f.verts)}
        if not add:
            print(f"     ** {len(pinch)} pinch vert(s) and no face to grow into **"); break
        dome_faces |= add
        print(f"     pinch pass {it+1}: {len(pinch)} pinch vert(s), grew by {len(add)} face(s)")
    bedges = [e for e in bm.edges
              if len(e.link_faces) == 2 and
                 (e.link_faces[0].index in dome_faces) != (e.link_faces[1].index in dome_faces)]
    deg = {}
    for e in bedges:
        for v in e.verts: deg[v.index] = deg.get(v.index, 0) + 1
    from collections import Counter
    closed = set(deg.values()) == {2}
    print(f"     boundary: {len(bedges)} edges over {len(deg)} verts, "
          f"degrees {dict(Counter(deg.values()))} -> "
          f"{'CLOSED SIMPLE CYCLE' if closed else '** PINCHED **'}")
    results.append((tag, dome_faces, bedges, deg, closed, ctr, r, outv))

# LOOK before cutting. Paint the dome face regions and the boundary loops so the
# selection can be checked by eye -- the cap half-angles differ (56.7 vs 74.4 deg), so
# the right region reaches further around its sphere and may be taking skin with it.
ca = me.color_attributes.get("eyeregion") or me.color_attributes.new(name="eyeregion", type='FLOAT_COLOR', domain='POINT')
cols = np.tile(np.array([0.58, 0.58, 0.60, 1.0]), (N, 1))
for (tag, dome_faces, bedges, deg, closed, ctr, r, outv), col in zip(results, ([0.95,0.25,0.15,1],[0.15,0.5,0.95,1])):
    dv = set()
    for fi in dome_faces: dv.update(v.index for v in bm.faces[fi].verts)
    cols[sorted(dv)] = col
    cols[sorted(deg.keys())] = [1.0, 0.95, 0.2, 1.0]      # boundary loop in yellow
ca.data.foreach_set("color", cols.ravel())
me.color_attributes.active_color = ca
me.update()   # NOT bm.to_mesh -- the bmesh is unmodified and would wipe this attribute

sc = bpy.context.scene
for o in [x for x in bpy.data.objects if x.type == 'ARMATURE']: o.hide_render = True
for o in [x for x in bpy.data.objects if x.type == 'CAMERA']: bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'VERTEX'
sc.render.resolution_x = sc.render.resolution_y = 850
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30
eyez = float(np.mean([r[5][2] for r in results]))
Rr = H*5
for off, tag2, scl in ((0.0, "region_front", 0.24), (math.radians(32), "region_q32", 0.24)):
    ang = a + off; cd.ortho_scale = scl
    cam.location = (hc[0]+math.sin(ang)*Rr, hc[1]-math.cos(ang)*Rr, eyez)
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"{tag2}.png")
    bpy.ops.render.render(write_still=True)
print(f"region maps written to {OUT}")

if not all(r[4] for r in results):
    print("\n!! at least one boundary is pinched -- grow the region around the pinch "
          "verts first (same fix as the mouth seam). NOT cutting.")
    sys.exit(0)
print("\nboth dome boundaries are closed simple cycles -- safe to split")
if not DO_CUT:
    print("(validation only; pass --cut to perform the separation)")
    sys.exit(0)

# ================= THE SEPARATION =================
print("\n--- separating ---")
for k, (tag, dome_faces, bedges, deg, closed, ctr, r, outv) in enumerate(results):
    for fi in dome_faces: bm.faces[fi][domelay] = k + 1

allb = []
for _, _, bedges, _, _, _, _, _ in results: allb.extend(bedges)
allb = list({e.index: e for e in allb}.values())
bmesh.ops.split_edges(bm, edges=allb)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
print(f"split along {len(allb)} rim edges -> verts {len(bm.verts)} faces {len(bm.faces)}")

def close_shell(edges, ctr, r, outv, rings, tagname):
    """Extrude a boundary loop backward along -outv and cap it. Same pattern as the
    mouth cavity, which is proven on this mesh."""
    cur, made = edges, []
    for depth, scale in rings:
        ret = bmesh.ops.extrude_edge_only(bm, edges=cur)
        nv = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
        ne = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMEdge) and len(g.link_faces) == 1]
        made += [g for g in ret['geom'] if isinstance(g, bmesh.types.BMFace)]
        cv = Vector(ctr)
        for v in nv:
            radial = v.co - cv
            along = radial.dot(Vector(outv))
            perp = radial - Vector(outv)*along
            v.co = cv + perp*scale + Vector(outv)*(along - r*depth)
        cur = ne
    f = bmesh.ops.holes_fill(bm, edges=cur)
    made += f.get('faces', [])
    print(f"  {tagname}: closed with {len(made)} faces")
    return made

eye_face_sets, socket_faces = [], []
for k, (tag, dome_faces, bedges, deg, closed, ctr, r, outv) in enumerate(results):
    dome_b, skin_b = [], []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 1: continue
        if lf[0][domelay] == k + 1: dome_b.append(e)
        elif lf[0][domelay] == 0:
            c = (e.verts[0].co + e.verts[1].co)/2
            if (np.array(c) - ctr) @ outv > 0 and np.linalg.norm(np.array(c) - ctr) < r*1.6:
                skin_b.append(e)
    print(f"{tag}: dome boundary {len(dome_b)} edges, skin socket boundary {len(skin_b)} edges")
    eye_face_sets.append(close_shell(dome_b, ctr, r, outv, [(0.35, 0.86), (0.75, 0.55), (1.15, 0.18)], f"{tag} eyeball"))
    socket_faces.append(close_shell(skin_b, ctr, r, outv, [(0.55, 1.00), (1.05, 0.90), (1.55, 0.35)], f"{tag} socket"))

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# who is who, now that geometry moved
comp_of = {}
seen = set(); comps = []
for v in bm.verts:
    if v.index in seen: continue
    stack, comp = [v], []
    while stack:
        x = stack.pop()
        if x.index in seen: continue
        seen.add(x.index); comp.append(x.index)
        for e in x.link_edges: stack.append(e.other_vert(x))
    comps.append(sorted(comp))
comps.sort(key=len, reverse=True)
print(f"\nconnected components after separation: {len(comps)}  sizes {[len(c) for c in comps[:6]]}")

nm = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
bd = sum(1 for e in bm.edges if e.is_boundary)
wr = sum(1 for e in bm.edges if e.is_wire)
lo = sum(1 for v in bm.verts if not v.link_edges)
print(f"hygiene: verts {len(bm.verts)} faces {len(bm.faces)} | non-manifold {nm} boundary {bd} wire {wr} loose {lo}")

# eyeball vertex sets = the components that are NOT the body
body = set(comps[0])
eyeverts = [c for c in comps[1:] if len(c) > 50]
print(f"eyeball components: {[len(c) for c in eyeverts]}")
bm.to_mesh(me); me.update()

if len(eyeverts) == 2:
    centres = [results[0][5], results[1][5]]
    # match component -> eye by proximity to the fitted sphere centre
    co2 = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", co2.ravel())
    for comp in eyeverts:
        cmid = co2[np.array(comp)].mean(axis=0)
        k = int(np.argmin([np.linalg.norm(cmid - c) for c in centres]))
        name = "eye_L" if results[k][0].strip() == "LEFT" else "eye_R"
        g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        g.add(comp, 1.0, 'REPLACE')
        ob[f"{name}_center"] = [float(x) for x in results[k][5]]
        ob[f"{name}_radius"] = float(results[k][6])
        print(f"  vertex group {name}: {len(comp)} verts, centre "
              f"{tuple(round(float(x),4) for x in results[k][5])} r={results[k][6]:.4f}")
else:
    print("!! expected 2 eyeball components -- vertex groups NOT written")

for g in ob.vertex_groups:
    n = sum(1 for v in me.vertices for x in v.groups if x.group == g.index and x.weight > 0.5)
    print(f"  group {g.name}: {n} verts")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_eyes.blend"))
print("saved clyffy_v2_eyes.blend")
