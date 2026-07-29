"""Cut the mouth open along the OPERATOR-SELECTED seam and build a shallow cavity.

Consumes the CANONICAL mesh (tools/canonicalize.py): transforms frozen, operator
selections baked as vertex groups. Two fixes over the first version:

  * SEAM COMES FROM THE `op_lip_seam` VERTEX GROUP, not from `select` flags. The old
    version deleted with context='FACES_ONLY' purely to keep vertex indices stable for
    the raw-index selection files, which left 67 WIRE EDGES and 20 loose verts inside
    the new cavity. Groups travel with the geometry, so the delete can be clean.

  * THE EXTRUDE DIRECTION IS NOW IN THE RIGHT SPACE. `inward = -fwd` was built from
    forward_axis_deg, a WORLD value, and applied to LOCAL coords on an object carrying
    a +69.17 deg Z rotation -- so the cavity was pushed ~59 deg off, into the cheek
    rather than back into the head. The canonical mesh has identity transform.

    blender -b --python tools/mouth_open.py -- <canon.blend> <out_dir> <fwd_deg> [depth]
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
BL, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
# Depth must EXCEED the widest aperture the jaw will reach, or the jaw swings past the
# back wall and you see through the cavity. At 22 deg the aperture is ~0.077 of height.
DEPTH = float(argv[3]) if len(argv) > 3 else 0.12
# Cavity ring profile "depthfrac:scale,...". Scaling rings toward the hole centroid
# collapses a thin lip slit onto itself -- the 4-linked-face edges at the mouth corners
# (the documented "white spike artifacts"). Taper gently, push inward instead.
# Ring profile "depthfrac:lateral_scale:half_height".
# The first version scaled each ring UNIFORMLY toward the hole centroid, producing a flat
# tapering SLOT -- 0.1846 deep, 0.1445 wide, and only 0.0077 TALL. No room for teeth
# (~0.008), let alone a tongue. A real mouth bag EXPANDS vertically as it goes back,
# behind the lips, so the pocket has volume while the lip line stays shut at rest.
PROFILE = argv[4] if len(argv) > 4 else "0.30:0.98:0.015,0.70:0.92:0.033,1.00:0.60:0.026"
# The seam is picked per-FACE, so the cut boundary is a staircase of quad edges rather
# than a smooth lip curve. Invisible closed, clearly visible once the jaw opens. Relax
# the rim loop tangentially before building the cavity so the bag inherits a clean edge.
# Plain Laplacian smoothing SHRINKS a closed loop, which pulls the lip back and exposes
# the cavity at the corners IN THE REST POSE -- verified: bright specks at both corners
# at 3 and 6 iterations. Taubin (lambda/mu) alternates a positive and a slightly larger
# negative step, removing the high-frequency zigzag with no net shrinkage.
# VERDICT: 0. Measured at 3 and 6 plain-Laplacian passes and 6 and 15 Taubin passes.
# Taubin does fix the shrinkage (-0.63% vs -4.6%), but EVERY setting puts bright specks
# along the lip line in the REST pose, because the slit is only 0.0077 tall and even a
# 0.0032 vertex move is ~40% of it. The rest pose is the state the avatar sits in; a
# staircase visible at 4x zoom on a fully-open mouth is the lesser defect. Left at 0 on
# purpose -- the knob stays so the trade-off can be re-tested if the lip gets denser.
RIM_RELAX = int(argv[5]) if len(argv) > 5 else 0
RIM_LAM   = float(argv[6]) if len(argv) > 6 else 0.50
RIM_MU    = float(argv[7]) if len(argv) > 7 else -0.53
RINGS = [tuple(float(x) for x in seg.split(":")) for seg in PROFILE.split(",")]
print(f"cavity ring profile: {RINGS}")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
mw = ob.matrix_world
assert max(abs(x) for x in mw.to_euler()) < 1e-6, \
    "input is not canonical (object still carries a rotation) -- run tools/canonicalize.py first"

gi = {g.name: g.index for g in ob.vertex_groups}
assert "op_lip_seam" in gi, f"no op_lip_seam group; found {list(gi)}"
seam_v = set(v.index for v in me.vertices
             for g in v.groups if g.group == gi["op_lip_seam"] and g.weight > 0.5)
seam = [p.index for p in me.polygons if all(vi in seam_v for vi in p.vertices)]
print(f"seam from group: {len(seam_v)} verts -> {len(seam)} faces")

co = [v.co for v in me.vertices]; zs = [c.z for c in co]
H = max(zs) - min(zs)
a = math.radians(FWD)
fwd = Vector((math.sin(a), -math.cos(a), 0)).normalized()
inward = -fwd
print(f"forward {FWD:.1f} deg -> fwd ({fwd.x:+.3f},{fwd.y:+.3f})  cavity pushed along ({inward.x:+.3f},{inward.y:+.3f})")

bm = bmesh.new(); bm.from_mesh(me)
bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()

def hygiene(tag):
    nm = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    bd = sum(1 for e in bm.edges if e.is_boundary)
    wr = sum(1 for e in bm.edges if e.is_wire)
    lo = sum(1 for v in bm.verts if not v.link_edges)
    print(f"  {tag:20s} verts {len(bm.verts)} faces {len(bm.faces)} | "
          f"non-manifold {nm} boundary {bd} wire {wr} loose {lo}")

hygiene("before cut")
# PRE-EXISTING boundaries must not be extruded -- the canonical mesh still carries a
# 19-edge branching defect in the torso (documented in canonicalize.py). Extruding it
# is the documented BUILD_LOG bug that produced a protruding wedge.
# TAG the edges: a delete RENUMBERS edges, so a set of pre-delete indices is worthless.
# (The original version got away with indices only because FACES_ONLY never removed any.)
# ALL custom layers are created HERE, before anything holds an element reference.
# Creating a bmesh layer invalidates existing BMVert/BMEdge/BMFace references, so a layer
# created mid-stream silently voids every element captured before it.
pretag = bm.edges.layers.int.new("pre_boundary")
nmtag  = bm.edges.layers.int.new("pre_nonmanifold")
srclay = bm.verts.layers.int.new("cav_src")
depthlay = bm.verts.layers.float.new("cav_depth")   # 0 at the lip rim -> 1 at the back cap
npre = 0
for e in bm.edges:
    if e.is_boundary: e[pretag] = 1; npre += 1
    if not e.is_manifold and not e.is_boundary: e[nmtag] = 1
for v in bm.verts: v[srclay] = -1; v[depthlay] = 0.0
print(f"  pre-existing boundary edges (tagged, excluded from the extrude): {npre}")

# RESOLVE PINCH POINTS before cutting. The operator's seam is one face wide in places,
# so the hole's boundary can be a figure-eight -- 60 verts of degree 2 and one of degree
# 4. The 3-ring extrude folds through that pinch and welds walls together, which is what
# produced the 4-linked-face edges and the white spikes at the mouth corners.
# Grow the deleted region around any pinch vertex until the boundary is a simple cycle.
bm.verts.ensure_lookup_table()
seam_set = set(seam)
for it in range(8):
    degv = {}
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2 and sum(1 for f in lf if f.index in seam_set) == 1:
            for v in e.verts: degv[v.index] = degv.get(v.index, 0) + 1
    pinch = [v for v, d in degv.items() if d != 2]
    if not pinch:
        print(f"  seam boundary is a simple cycle ({len(degv)} verts) after {it} growth pass(es)")
        break
    add = {f.index for vi in pinch for f in bm.verts[vi].link_faces if f.index not in seam_set}
    seam_set |= add
    print(f"  pinch pass {it+1}: {len(pinch)} pinch vert(s) degree!=2, grew seam by {len(add)} face(s)")
else:
    print("  !! pinch points did NOT resolve in 8 passes -- cavity may self-intersect")
print(f"  cutting {len(seam_set)} faces (operator seam {len(seam)} + {len(seam_set)-len(seam)} to unpinch)")

# context='FACES' removes the faces AND the edges/verts left orphaned by them.
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(seam_set)], context='FACES')
bm.edges.ensure_lookup_table(); bm.verts.ensure_lookup_table(); bm.verts.index_update()
nverts_after_delete = len(bm.verts)
hygiene("after delete")

bound = [e for e in bm.edges if e.is_boundary and e[pretag] == 0]
vs = set(v for e in bound for v in e.verts)
hole = sum((v.co for v in vs), Vector())/max(1, len(vs))
print(f"  mouth boundary {len(bound)} edges   hole centre ({hole.x:+.4f},{hole.y:+.4f},{hole.z:+.4f})")

if RIM_RELAX > 0:
    radj = {}
    for e in bound:
        for v in e.verts: radj.setdefault(v, []).append(e)
    if all(len(x) == 2 for x in radj.values()):
        before = {v: v.co.copy() for v in radj}
        def taubin_step(factor):
            upd = {}
            for v, es in radj.items():
                nb = [e.other_vert(v) for e in es]
                upd[v] = v.co + (((nb[0].co + nb[1].co)/2.0) - v.co) * factor
            for v, c in upd.items(): v.co = c
        for _ in range(RIM_RELAX):
            taubin_step(RIM_LAM)
            taubin_step(RIM_MU)
        moved = max((v.co - before[v]).length for v in radj)
        span_b = max((before[v] - hole).length for v in radj)
        span_a = max((v.co - hole).length for v in radj)
        print(f"  rim relax (Taubin l={RIM_LAM} m={RIM_MU}): {RIM_RELAX} passes over {len(radj)} verts, "
              f"max move {moved:.5f} ({100*moved/H:.2f}% of height), "
              f"hole radius {span_b:.4f} -> {span_a:.4f} "
              f"({100*(span_a-span_b)/span_b:+.2f}% -- shrink must be ~0)")
    else:
        print(f"  !! rim is not a simple cycle -- skipping relax")

interior = []
newverts = []
lineage = {}      # cavity vert -> the LIP RIM vert it descends from
cur = bound
# Each ring is placed ABSOLUTELY from its rim ancestor, not relative to the previous ring.
# Relative placement compounds: ring 2 starts at ring 1's already-scaled z, so dividing by
# the rim half-height again over-scales it, and the inward depth double-counts too.
rim_pos = {}
for e in bound:
    for v in e.verts: rim_pos[v.index] = v.co.copy()
anc_pos = {}          # new vert -> its RIM ancestor's original position (propagated, not looked up)
rim_half_z = max(abs((c - hole).z) for c in rim_pos.values()) or 1e-6
latv, zv, fwdv = Vector((-fwd.y, fwd.x, 0.0)), Vector((0, 0, 1)), fwd
print(f"  rim half-height {rim_half_z:.5f} -> bag half-heights {[r[2] for r in RINGS]}")
for ring_i, (dfrac, lat_scale, half_h) in enumerate(RINGS):
    ret = bmesh.ops.extrude_edge_only(bm, edges=cur)
    nv = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMVert)]
    ne = [g for g in ret['geom'] if isinstance(g, bmesh.types.BMEdge) and len(g.link_faces) == 1]
    # Record which rim vert each new vert descends from. The mouth bag must be skinned
    # from the lip it hangs off: the lower wall follows the jaw, the upper wall stays.
    # Weighting bag verts by nearest-surface-vertex instead tears the bag in half,
    # because its two walls sit ~0.008 apart and neighbours snap to opposite lips.
    nvset = set(nv)
    for v in nv:
        for e in v.link_edges:
            o = e.other_vert(v)
            if o not in nvset:
                # ring 1: o is a rim vert (index valid). ring 2+: o already carries its
                # rim ancestor in the layer. Never depends on a new vert's own index.
                v[srclay] = o[srclay] if o[srclay] >= 0 else o.index
                v[depthlay] = float(ring_i + 1)/len(RINGS)
                # carry the ancestor POSITION too. Looking it up by index and falling back
                # to v.co on a miss silently compounds each ring off the previous one --
                # measured bag height 0.306 instead of 0.052.
                anc_pos[v] = anc_pos.get(o, o.co.copy())
                lineage[v] = True
                break
    interior += [g for g in ret['geom'] if isinstance(g, bmesh.types.BMFace)]
    newverts += nv
    missing = sum(1 for v in nv if v not in anc_pos)
    if missing: print(f"  !! ring {ring_i+1}: {missing} verts with no rim ancestor")
    for v in nv:
        d = anc_pos[v] - hole if v in anc_pos else v.co - hole   # from the RIM
        # anisotropic: keep the fwd spread, taper laterally, EXPAND vertically to half_h
        dl = d.dot(latv); dz = d.z; df = d.dot(fwdv)
        v.co = (hole + latv*(dl*lat_scale) + fwdv*df
                + zv*(dz/rim_half_z*half_h) + inward*(H*DEPTH*dfrac))
    cur = ne
fill = bmesh.ops.holes_fill(bm, edges=cur)
interior += fill.get('faces', [])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.normal_update()

wire = [e for e in bm.edges if e.is_wire]
if wire: bmesh.ops.delete(bm, geom=wire, context='EDGES')
loose = [v for v in bm.verts if not v.link_edges]
if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')
if wire or loose: print(f"  swept {len(wire)} wire edges, {len(loose)} loose verts")
hygiene("after cavity")
bad = [e for e in bm.edges if not e.is_manifold and not e.is_boundary and e[nmtag] == 0]
for e in bad:
    c = (e.verts[0].co + e.verts[1].co)/2
    print(f"  !! non-manifold edge introduced by the cavity at ({c.x:+.4f},{c.y:+.4f},{c.z:+.4f}) "
          f"link_faces {len(e.link_faces)}")

# Extrusion copies vertex data, so the new cavity verts inherited op_lip_seam /
# op_jaw_region membership. Those groups record what the OPERATOR picked -- generated
# geometry must not silently join them.
dl = bm.verts.layers.deform.verify()
opg = [gi[n] for n in ("op_jaw_region", "op_lip_seam")]
stripped = 0
for v in newverts:
    if not v.is_valid: continue
    for g in opg:
        if g in v[dl]: del v[dl][g]; stripped += 1
print(f"  stripped {stripped} inherited operator-group weights from new cavity verts")

nlin = sum(1 for v in bm.verts if v[srclay] >= 0)
assert len(bm.verts) >= nverts_after_delete, "verts were removed after lineage was recorded"
if len(bm.verts) != nverts_after_delete + len(newverts):
    print(f"  !! vert count moved unexpectedly -- cav_src rim indices may be stale")
ncap = sum(1 for v in bm.verts if v[depthlay] > 0.99)
print(f"  cavity lineage: {nlin} bag verts carry 'cav_src' -> their lip rim vert index")
print(f"  cavity depth   : 'cav_depth' 0=lip rim .. 1=back cap ({ncap} verts on the cap)")

bm.faces.index_update()
idx = set(f.index for f in interior if f.is_valid)
print(f"  cavity faces: {len(idx)}")
bm.to_mesh(me); bm.free(); me.update()

dark = bpy.data.materials.new("clyffy_mouth_interior"); dark.use_nodes = True
b = dark.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.065, 0.022, 0.026, 1.0)
b.inputs["Roughness"].default_value = 0.62
# Workbench/solid shading reads diffuse_color (viewport display), NOT the Principled
# base colour. Without this the cavity renders default light grey -- which is what the
# "white spike artifacts at the mouth corners" in BUILD_LOG actually were.
dark.diffuse_color = (0.065, 0.022, 0.026, 1.0)
dark.roughness = 0.62
me.materials.append(dark); di = len(me.materials)-1
for i in idx:
    if i < len(me.polygons): me.polygons[i].material_index = di

cav = [v for p in me.polygons if p.material_index == di for v in p.vertices]
cz = [me.vertices[v].co.z for v in set(cav)]
print(f"  cavity verts {len(set(cav))}  z[{min(cz):+.4f},{max(cz):+.4f}]  centre z {sum(cz)/len(cz):+.4f}")
print(f"  BAG HEIGHT {max(cz)-min(cz):.4f} (was 0.0077 as a flat slot; needs > ~0.04 for teeth+tongue)")
for g in ob.vertex_groups:
    n = sum(1 for v in me.vertices for x in v.groups if x.group == g.index and x.weight > 0.5)
    print(f"  group {g.name} survived the cut: {n} verts")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_open.blend"))

sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 620
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = H*0.30
R = H*5
for off, tag in [(0, "front"), (math.radians(45), "q45"), (math.radians(80), "side")]:
    ang = a + off
    cam.location = (hole.x + math.sin(ang)*R, hole.y - math.cos(ang)*R, hole.z)
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"cut_{tag}.png")
    bpy.ops.render.render(write_still=True)
print("ok")
