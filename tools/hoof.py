"""Give the hands their CLOVEN HOOF — the dark distal cap canon shows on a white forearm.

    blender -b --python tools/hoof.py -- <body.blend> <out_dir> <fwd_deg> [frac]

WHY. `clyffy.pack.toml [layers].base_body` lists "cloven-hooves" and the base sheet shows a
white furred forearm ending in TWO dark rounded toes. The mesh already has the right toe
COUNT — two soft lobes — but is white fur all the way to the tip, so the hoof reads as a
mitten. The body is a single texture, so the hoof needs its own material on the distal
faces: the same play `mouth_parts.py` uses for teeth and tongue.

⚠️ The toe count was nearly got wrong. A first read of the base sheet said THREE toes — that
came from a crop window (`crop=280:300:180:430`) that straddled two panels of the turnaround,
stitching one pose's hand beside another's. Panels are 1668/5 = 333.6 px wide; crop INSIDE
one. Cloven means split in two, and both the front and 3/4 panels agree on two.

OPERATOR SELECTION WINS. If the mesh carries an `op_hoof` vertex group, that IS the hoof and
this tool only assigns the material to it. The derivation below is the fallback so the pass
is not blocked waiting on hand-work — it is a guess at a styling line, and the operator's
pick beats it.

NO GEOMETRY CHANGE. Material assignment only, so this is safe to run after body_rig: vertex
count, indices, weights and the 43 shape keys are all untouched.
"""
import bpy, sys, os, math
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
# Distal fraction of the hand blob that reads as hoof, measured along the forearm axis.
# Canon runs the dark quite short — the toes and little more.
FRAC = float(argv[3]) if len(argv) > 3 else 0.38
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])

gi = {g.name: g.index for g in ob.vertex_groups}
def group_verts(name, thr=0.5):
    if name not in gi: return np.array([], dtype=int)
    return np.array(sorted(v.index for v in me.vertices
                           for g in v.groups if g.group == gi[name] and g.weight > thr), dtype=int)

hoof = np.zeros(N, bool)
op = group_verts("op_hoof")
if len(op):
    hoof[op] = True
    print(f"using the OPERATOR's op_hoof selection: {len(op)} verts")
else:
    print("no op_hoof group — deriving the hoof line from the hand bones (fallback)")
    for side in ("L", "R"):
        hb = arm.data.bones.get(f"hand_{side}")
        lb = arm.data.bones.get(f"lower_arm_{side}")
        if hb is None or lb is None:
            print(f"  !! missing hand_{side}/lower_arm_{side} bone"); continue
        wrist = np.array(hb.head_local)
        axis = np.array(hb.tail_local) - np.array(lb.head_local)
        n = np.linalg.norm(axis)
        if n < 1e-9:
            print(f"  !! degenerate arm axis on {side}"); continue
        axis = axis / n
        # the hand blob: verts the hand bone actually influences, so the region follows the
        # rig rather than a hand-tuned radius
        w = np.zeros(N)
        if f"hand_{side}" in gi:
            for v in me.vertices:
                for g in v.groups:
                    if g.group == gi[f"hand_{side}"]: w[v.index] = g.weight
        blob = np.where(w > 0.01)[0]
        if len(blob) < 10:
            print(f"  !! hand_{side} influences only {len(blob)} verts"); continue
        p = (co[blob] - wrist) @ axis
        cut = p.max() - (p.max() - p.min()) * FRAC
        sel = blob[p > cut]
        hoof[sel] = True
        print(f"  hand_{side}: {len(blob)} verts in the blob, hoof = distal {FRAC:.0%} "
              f"({len(sel)} verts) beyond {100*(p.max()-cut)/H:.2f}%H from the tip")

nsel = int(hoof.sum())
assert nsel, "no hoof verts selected — nothing to assign"
# a FACE is hoof only if all of its verts are, so the boundary lands on an edge loop
faces = [p.index for p in me.polygons if all(hoof[v] for v in p.vertices)]
print(f"hoof: {nsel} verts -> {len(faces)} faces")

mat = bpy.data.materials.new("clyffy_hoof")
mat.use_nodes = True
b = mat.node_tree.nodes["Principled BSDF"]
# canon: dark warm grey, slightly glossy keratin — NOT black, or it reads as a hole
b.inputs["Base Color"].default_value = (0.075, 0.070, 0.072, 1.0)
b.inputs["Roughness"].default_value = 0.38
# Workbench/solid reads diffuse_color, NOT the Principled input — the mouth cavity shipped
# light grey for exactly this reason
mat.diffuse_color = (0.075, 0.070, 0.072, 1.0)
mat.roughness = 0.38
me.materials.append(mat)
idx = len(me.materials) - 1
for f in faces:
    me.polygons[f].material_index = idx
g = ob.vertex_groups.get("hoof") or ob.vertex_groups.new(name="hoof")
g.add([int(i) for i in np.where(hoof)[0]], 1.0, 'REPLACE')
print(f"assigned material '{mat.name}' (slot {idx}) and vertex group 'hoof'")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_body.blend"))

# ── renders ──────────────────────────────────────────────────────────────────
sc = bpy.context.scene
arm.hide_render = True
for o in [x for x in bpy.data.objects if x.type == 'CAMERA']:
    bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 720
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.001; cd.clip_end = H * 30
R2 = H * 5
for side in ("L", "R"):
    hb = arm.data.bones.get(f"hand_{side}")
    if hb is None: continue
    c = (np.array(hb.head_local) + np.array(hb.tail_local)) * 0.5
    cd.ortho_scale = H * 0.16
    for off, tag in ((0.0, "front"), (math.radians(60), "q60")):
        ac = a + off
        cam.location = (c[0] + math.sin(ac) * R2, c[1] - math.cos(ac) * R2, c[2])
        cam.rotation_euler = (math.radians(90), 0, ac)
        sc.render.filepath = os.path.join(OUT, f"hoof{side}_{tag}.png")
        bpy.ops.render.render(write_still=True)
print("ok")
