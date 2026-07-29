"""Render pinned Oculus-style VISEMES as a contact sheet (G4).

    blender -b --python tools/viseme_sheet.py -- \
        <body.blend> <out_dir> <fwd_deg>

Writes viseme_<label>.png and _visemesheet.jpg under out_dir.
Uses Workbench for speed — validation, not beauty.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import VISEMES, ENVELOPE  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
RIG = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2])
os.makedirs(OUT, exist_ok=True)
# READ THE CONTRACT, never a literal. This file said 22.0 while the published envelope said
# 10.0, so the G4 viseme sheet — the artifact the character is JUDGED from — had been drawing
# every viseme at 2.2x the jaw angle the rig is actually driven at. A gate artifact that
# flatters the rig is worse than no gate artifact.
MAXDEG = float(ENVELOPE["jaw"]["max_deg"])

bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"],
         key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = ob.data
kb = me.shape_keys.key_blocks if me.shape_keys else None
assert kb is not None
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
hc = co[co[:, 2] > 0.208].mean(0)

jaw_b = arm.pose.bones.get("jaw")
assert jaw_b is not None
hv = Vector(jaw_b.bone.head_local)
lv = Vector(lat)

def zero():
    for k in kb:
        if k.name != "Basis":
            k.value = 0.0
    jaw_b.rotation_mode = "QUATERNION"
    jaw_b.matrix = jaw_b.bone.matrix_local.copy()

def set_jaw(amount: float):
    amount = float(max(0.0, min(1.0, amount)))
    ang = math.radians(MAXDEG) * amount
    R = (Matrix.Translation(hv)
         @ Matrix.Rotation(ang, 4, lv)
         @ Matrix.Translation(-hv))
    jaw_b.matrix = R @ jaw_b.bone.matrix_local

def apply_viseme(label: str):
    zero()
    w = dict(VISEMES.get(label, {}))
    jaw = w.pop("jawOpen", 0.0)
    for name, val in w.items():
        if name in kb:
            kb[name].value = float(val)
    set_jaw(jaw)
    bpy.context.view_layer.update()

# camera / workbench
sc = bpy.context.scene
arm.hide_render = True
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"
if sc.world is None:
    sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x = 512
sc.render.resolution_y = 640
sc.render.image_settings.file_format = "PNG"
cd = bpy.data.cameras.new("VCam")
cam = bpy.data.objects.new("VCam", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.type = "ORTHO"
cd.ortho_scale = H * 0.55
cd.clip_start = 0.01
cd.clip_end = H * 40
face_z = float(hc[2] - H * 0.02)
Rr = H * 4.0
cam.location = (hc[0] + math.sin(a) * Rr, hc[1] - math.cos(a) * Rr, face_z)
cam.rotation_euler = (math.radians(90), 0, a)

paths = []
for label in VISEMES.keys():
    apply_viseme(label)
    path = os.path.join(OUT, f"viseme_{label}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    paths.append(path)
    print(f"  viseme {label} → {path}")

# contact sheet
try:
    from PIL import Image, ImageDraw, ImageFont
    imgs = [Image.open(p).convert("RGB") for p in paths]
    cols = 5
    rows = (len(imgs) + cols - 1) // cols
    w, h = imgs[0].size
    pad = 8
    label_h = 28
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad,
                              rows * (h + label_h) + (rows + 1) * pad), (20, 22, 28))
    draw = ImageDraw.Draw(sheet)
    labels = list(VISEMES.keys())
    for i, im in enumerate(imgs):
        r, c = divmod(i, cols)
        x = pad + c * (w + pad)
        y = pad + r * (h + label_h + pad)
        sheet.paste(im, (x, y))
        draw.text((x + 4, y + h + 4), labels[i], fill=(220, 220, 220))
    out_sheet = os.path.join(OUT, "_visemesheet.jpg")
    sheet.save(out_sheet, quality=90)
    print(f"wrote {out_sheet}")
except Exception as e:
    print(f"sheet skipped: {e}")

print("ok")
