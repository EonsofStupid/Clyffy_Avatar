"""Procedural jaw-open shape key test — no mouth cavity cut.

Finds the muzzle, defines a jaw pivot, rotates the lower-muzzle verts about it with a
smooth falloff, stores the result as a shape key, and renders an open-amount sweep.
Answers ONE question: does a sealed-mouth jaw rotation read as talking?
"""
import bpy, bmesh, sys, os, math, json
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--")+1:]
MESH, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = ob

# ---- 1. delete stray fragments (keep only the largest connected component) ----
bm = bmesh.new(); bm.from_mesh(ob.data)
seen=set(); comps=[]
for v in bm.verts:
    if v.index in seen: continue
    stack=[v]; comp=[]; seen.add(v.index)
    while stack:
        cur=stack.pop(); comp.append(cur.index)
        for e in cur.link_edges:
            o=e.other_vert(cur)
            if o.index not in seen: seen.add(o.index); stack.append(o)
    comps.append(comp)
comps.sort(key=len, reverse=True)
strays = set(i for c in comps[1:] for i in c)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in strays], context='VERTS')
bm.to_mesh(ob.data); bm.free()
print(f"deleted {len(strays)} stray verts across {len(comps)-1} fragments; "
      f"{len(ob.data.vertices)} remain")

me = ob.data
co = [v.co.copy() for v in me.vertices]
zs = [c.z for c in co]
zmin, zmax = min(zs), max(zs)
H = zmax - zmin

# ---- 2. locate the muzzle: furthest-from-axis vertex in the head band ----
head_lo = zmin + H*0.70
head = [c for c in co if c.z > head_lo]
cx = sum(c.x for c in head)/len(head); cy = sum(c.y for c in head)/len(head)
axis = Vector((cx, cy))
tip = max(head, key=lambda c: (Vector((c.x, c.y)) - axis).length)
face_dir = (Vector((tip.x, tip.y)) - axis).normalized()
print(f"muzzle tip {tuple(round(v,3) for v in tip)}  facing {tuple(round(v,3) for v in face_dir)}")

# ---- 3. jaw pivot: behind the muzzle tip, at mouth height ----
fwd = Vector((face_dir.x, face_dir.y, 0.0))
lateral = Vector((-fwd.y, fwd.x, 0.0))            # rotation axis (ear-to-ear)
mouth_z = tip.z                                    # mouth sits at muzzle height
pivot = Vector((axis.x, axis.y, mouth_z)) + fwd * ( (Vector((tip.x,tip.y))-axis).length * 0.25 )
print(f"jaw pivot {tuple(round(v,3) for v in pivot)}")

# ---- 4. weight: forward of pivot AND below mouth line, smooth falloff ----
def weight(c):
    rel = c - pivot
    f = rel.dot(fwd)                               # forward extent
    if f <= 0.0: return 0.0
    below = (mouth_z + H*0.012) - c.z              # how far below the mouth line
    if below <= 0.0: return 0.0
    wf = min(1.0, f / (H*0.10))
    wb = min(1.0, below / (H*0.055))
    w = wf * wb
    return w*w*(3-2*w)                             # smoothstep

ws = [weight(c) for c in co]
n_aff = sum(1 for w in ws if w > 0.01)
print(f"jaw-weighted verts: {n_aff} / {len(co)} ({100*n_aff/len(co):.1f}%)")

# ---- 5. bake as shape key ----
ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="jaw_open", from_mix=False)
ANGLE = math.radians(28)
for i, c in enumerate(co):
    w = ws[i]
    if w <= 0.0: continue
    R = Matrix.Rotation(ANGLE*w, 4, lateral)
    sk.data[i].co = pivot + (R @ (c - pivot))
print(f"shape key 'jaw_open' baked at {math.degrees(ANGLE):.0f} deg max")

# ---- 6. render the sweep ----
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x = 620; sc.render.resolution_y = 620
sc.world = bpy.data.worlds.new("W")
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"

head_ctr = Vector((axis.x, axis.y, zmin + H*0.855))
r = H*0.20
cd.ortho_scale = r*2.7
# camera on the facing axis, swung 25 deg for a 3/4 read
sw = Matrix.Rotation(math.radians(25), 3, Vector((0,0,1))) @ fwd
cam.location = head_ctr + sw*r*7
cam.rotation_euler = (math.radians(90), 0, math.atan2(sw.y, sw.x) + math.radians(90))

for amt in (0.0, 0.35, 0.70, 1.0):
    sk.value = amt
    sc.render.filepath = os.path.join(OUT, f"jaw_{int(amt*100):03d}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_jawtest.blend"))
print("saved blend")
