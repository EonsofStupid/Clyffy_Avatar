"""Render the tongue: in the mouth, and on its own.

    blender -b --python tools/tongue_sheet.py -- <body.blend> <out_dir> <fwd_deg> [tag]

Writes t_<pose>_<view>.png, t_iso_<view>.png and _tonguesheet.jpg under out_dir.

WHY THIS EXISTS. The tongue lives inside a closed head, so every other sheet in the pack
shows it either not at all (rest, correctly — containment is a gate) or as a dark smear
behind the teeth. The mouth closeups here are posed straight off the CONTRACT's own viseme
table, and the isolated pass hides the head entirely so the authored geometry can actually
be looked at. Workbench, not Cycles: this is validation, and flat shading reads shape better
than a beauty render of an unlit cavity.

The jaw angle comes from ENVELOPE["jaw"]["max_deg"], never a literal — see the note in
viseme_sheet.py about what happens when a validation render poses harder than the rig does.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import VISEMES, ENVELOPE  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
RIG = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2]) if len(argv) > 2 else 235.1
TAG = argv[3] if len(argv) > 3 else ""
os.makedirs(OUT, exist_ok=True)
MAXDEG = float(ENVELOPE["jaw"]["max_deg"])

bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
me = ob.data
kb = me.shape_keys.key_blocks if me.shape_keys else None
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
lv = Vector(lat)

gi = {g.name: g.index for g in ob.vertex_groups}
def IDX(n):
    if n not in gi: return np.array([], int)
    k = gi[n]
    return np.array([v.index for v in me.vertices
                     if any(g.group == k and g.weight > 0.5 for g in v.groups)], int)
TON, TU, TL = IDX("tongue"), IDX("teeth_upper"), IDX("teeth_lower")
PARTS = set(TON.tolist()) | set(TU.tolist()) | set(TL.tolist())
di = [i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")]
cav = sorted({v for p in me.polygons if p.material_index in di for v in p.vertices})
mouth = co[cav].mean(axis=0)
print(f"mesh {N} verts, H {H:.4f} | tongue {len(TON)} teeth {len(TU)}/{len(TL)}")

jaw_b = arm.pose.bones.get("jaw") if arm else None
hv = Vector(jaw_b.bone.head_local) if jaw_b else Vector((0, 0, 0))

def zero():
    if kb:
        for k in kb:
            if k.name != "Basis": k.value = 0.0
    if jaw_b:
        jaw_b.rotation_mode = "QUATERNION"
        jaw_b.matrix = jaw_b.bone.matrix_local.copy()
    bpy.context.view_layer.update()

def set_pose(mix):
    zero()
    jaw = float(mix.get("jawOpen", 0.0))
    if kb:
        for n, v in mix.items():
            if n == "jawOpen": continue
            if n in kb and n != "Basis":
                kb[n].value = float(max(0.0, min(1.0, v)))
    if jaw_b and jaw > 0.0:
        ang = math.radians(MAXDEG) * max(0.0, min(1.0, jaw))
        R = (Matrix.Translation(hv) @ Matrix.Rotation(ang, 4, lv) @ Matrix.Translation(-hv))
        jaw_b.matrix = R @ jaw_b.bone.matrix_local
    bpy.context.view_layer.update()

# ── scene ────────────────────────────────────────────────────────────────────
sc = bpy.context.scene
for c in [o for o in bpy.data.objects if o.type == "CAMERA"]:
    bpy.data.objects.remove(c, do_unlink=True)
if arm: arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"
sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x = sc.render.resolution_y = 720
sc.render.film_transparent = False
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.001; cd.clip_end = H * 40
Rr = H * 5

def shoot(path, yaw_off, target, scale, pitch=0.0):
    ang = a + yaw_off
    cd.ortho_scale = scale
    cam.location = (target[0] + math.sin(ang)*Rr*math.cos(pitch),
                    target[1] - math.cos(ang)*Rr*math.cos(pitch),
                    target[2] + Rr*math.sin(pitch))
    cam.rotation_euler = (math.radians(90) - pitch, 0, ang)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

# ── in-mouth poses, straight from the contract's viseme table ────────────────
POSES = [
    ("rest",      {}),
    ("aa",        dict(VISEMES.get("aa", {"jawOpen": 0.85}))),
    ("TH",        dict(VISEMES.get("TH", {"jawOpen": 0.22, "tongueOut": 0.3}))),
    ("tongueOut", {"tongueOut": 1.0}),
    ("jaw+tongue", {"jawOpen": 1.0, "tongueOut": 1.0}),
]
VIEWS = [("front", 0.0, 0.0), ("q40", math.radians(40), 0.0), ("low", 0.0, math.radians(-25))]
shots = []
for name, mix in POSES:
    set_pose(mix)
    for vname, yaw, pitch in VIEWS:
        p = os.path.join(OUT, f"t_{name}_{vname}.png")
        shoot(p, yaw, mouth, H * 0.115, pitch)
        shots.append((f"{name} / {vname}", p))
    print(f"  posed {name:<10} {mix}")

# ── isolated parts: the authored geometry with the head taken away ───────────
# Built from the EVALUATED mesh so shape keys and the armature are baked in — an isolated
# render of the rest coordinates would be a different object from the one on screen above.
def isolate(mix, tag):
    set_pose(mix)
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    obe = ob.evaluated_get(dg); ev = obe.to_mesh()
    C = np.empty((len(ev.vertices), 3)); ev.vertices.foreach_get("co", C.ravel())
    polys = [(tuple(p.vertices), p.material_index) for p in ev.polygons
             if set(p.vertices) <= PARTS]
    obe.to_mesh_clear()
    bm = bmesh.new()
    vmap = {}
    for vs, _mi in polys:
        for i in vs:
            if i not in vmap:
                vmap[i] = bm.verts.new((float(C[i][0]), float(C[i][1]), float(C[i][2])))
    bm.verts.index_update()
    fmap = []
    for vs, mi in polys:
        try:
            f = bm.faces.new(tuple(vmap[i] for i in vs)); fmap.append((f, mi))
        except ValueError:
            pass
    nm = bpy.data.meshes.new(f"iso_{tag}")
    bm.to_mesh(nm); bm.free()
    for m in me.materials:
        nm.materials.append(m)
    for k, (f, mi) in enumerate(fmap):
        if k < len(nm.polygons): nm.polygons[k].material_index = mi
    iso = bpy.data.objects.new(f"iso_{tag}", nm)
    sc.collection.objects.link(iso)
    ob.hide_render = True
    out = []
    for vname, yaw, pitch in (("side", math.radians(90), 0.0),
                              ("q40", math.radians(40), 0.0),
                              ("top", 0.0, math.radians(-80))):
        p = os.path.join(OUT, f"t_iso_{tag}_{vname}.png")
        shoot(p, yaw, mouth, H * 0.135, pitch)
        out.append((f"isolated {tag} / {vname}", p))
    ob.hide_render = False
    bpy.data.objects.remove(iso, do_unlink=True)
    print(f"  isolated {tag}: {len(polys)} part faces")
    return out

shots += isolate({}, "rest")
shots += isolate({"tongueOut": 1.0}, "out")

# ── contact sheet ────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw
    cols = 3
    ims = [(lbl, Image.open(p)) for lbl, p in shots if os.path.isfile(p)]
    if ims:
        w, h = ims[0][1].size
        rows = (len(ims) + cols - 1) // cols
        pad, band = 8, 26
        sheet = Image.new("RGB", (cols*w + (cols+1)*pad, rows*(h+band) + (rows+1)*pad),
                          (24, 24, 26))
        draw = ImageDraw.Draw(sheet)
        for k, (lbl, im) in enumerate(ims):
            r, c = divmod(k, cols)
            x = pad + c*(w + pad); y = pad + r*(h + band + pad)
            sheet.paste(im, (x, y))
            draw.text((x + 4, y + h + 5), lbl, fill=(235, 235, 235))
        name = f"_tonguesheet{('_' + TAG) if TAG else ''}.jpg"
        sheet.save(os.path.join(OUT, name), quality=92)
        print(f"wrote {os.path.join(OUT, name)} ({len(ims)} panels)")
except Exception as e:
    print(f"sheet skipped: {e}")
print("ok")
