"""Close-up of the muzzle pad under NEUTRAL studio light, framed by the pad itself.

    blender -b --python tools/pad_shot.py -- <body.blend> <out.png> [--samples N] [--yaw D]

Deliberately NOT the canon look. `tools/present.py` renders the DPN dark studio with teal shadows
and an amber rim, which is right for a hero image and useless for judging surface: a rim light
will invent relief that is not there. `canon/reference/detail_muzzle_profile.png` is flat even
studio light on a plain field, so this matches that — the same rule the albedo work already
follows, and for the same reason.

The camera is aimed at the centroid of the `skin_flesh` attribute, so it frames the pad on any
mesh without a hand-tuned position that would drift the moment proportions change.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])


def opt(name, default, cast=float):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


SAMPLES = opt("--samples", 96, int)
YAW = opt("--yaw", 34.0)          # degrees off pure profile, toward the front
ZOOM = opt("--zoom", 1.0)         # >1 pulls back; needed to get LIT fur into frame beside the pad
# FLAT: uniform world dome only, no key and no fill. Required for any pad/fur ALBEDO RATIO to mean
# anything. With a key light the pad faces it and the cheek does not, which measured the pad as
# 1.285x BRIGHTER than white fur — impossible for a pink pad, and purely an artefact of comparing
# two differently-lit surfaces. `canon/reference` is flat-lit for exactly this reason.
FLAT = "--flat" in argv
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
for arm in bpy.data.objects:
    if arm.type == "ARMATURE":
        arm.data.pose_position = "REST"
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            kb.value = 0.0

N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
M = np.array(ob.matrix_world)
co = co @ M[:3, :3].T + M[:3, 3]

assert "skin_flesh" in me.attributes, "no skin_flesh attribute — run tools/materials.py first"
w = np.zeros(N, dtype=np.float32)
me.attributes["skin_flesh"].data.foreach_get("value", w)
sel = w > 0.5
assert sel.sum() > 50, f"skin_flesh selects only {int(sel.sum())} verts"
# FRAME THE NOSE, NOT THE WHOLE MASK. `skin_flesh` spans nearly the full lower face — 2665 verts
# with a p90 radius of 0.197 on a head about 0.2 tall — because materials.py treats the entire
# muzzle as flesh, not just the rhinarium. Framing on its centroid gives a wide face shot in which
# no micro-relief is legible. So the shot centres on the FORWARD QUARTER of the pad, which is the
# nose and nostrils, and that is what the reference close-up shows.

# facing, measured from the lip seam (see tools/profile_shot.py for why this is not a constant)
gi = {g.name: g.index for g in ob.vertex_groups}
want = gi["op_lip_seam"]
idx = [v.index for v in me.vertices for g in v.groups if g.group == want and g.weight > 0.5]
lip_c = co[idx].mean(axis=0)
head_c = co[co[:, 2] > lip_c[2]].mean(axis=0)
d = lip_c[:2] - head_c[:2]
FWD = math.degrees(math.atan2(d[0] / np.hypot(*d), -d[1] / np.hypot(*d))) % 360.0
ang = math.radians(FWD - 90.0 + YAW)

fwd_v = np.array([math.sin(math.radians(FWD)), -math.cos(math.radians(FWD)), 0.0])
pf = co[sel] @ fwd_v
front = co[sel][pf >= np.percentile(pf, 75)]
ctr = Vector(front.mean(axis=0))
pad_r = float(np.percentile(np.linalg.norm(front - front.mean(axis=0), axis=1), 85))
print(f"pad: {int(sel.sum())} flesh verts; framing the forward quarter "
      f"({len(front)} verts) at centre {tuple(round(v,4) for v in ctr)}, radius {pad_r:.4f}")

sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
    bpy.context.preferences.addons["cycles"].preferences.get_devices()
except Exception:
    pass
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False        # OIDN CPU device is unavailable in this build
sc.render.resolution_x = 1400
sc.render.resolution_y = 1000
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "None"

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.62, 0.63, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 2.6 if FLAT else 1.0
sc.world = world

R = pad_r * 6.0
cam_d = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cam_d.type = "ORTHO"
cam_d.ortho_scale = pad_r * 4.2 * ZOOM
cam.location = (ctr.x + math.sin(ang) * R, ctr.y - math.cos(ang) * R, ctr.z + pad_r * 0.35)
look = ctr - Vector(cam.location)
cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()

# broad soft key from the upper front, plus a fill — enough to read relief, not enough to sculpt it
for name, offs, size, power in ([] if FLAT else
                                [("key", (0.9, -1.5, 1.5), 2.2, 260.0),
                                 ("fill", (-1.6, -0.9, 0.2), 3.0, 70.0)]):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size * pad_r * 10
    ld.energy = power * pad_r * 10
    lo = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(lo)
    lo.location = (ctr.x + offs[0] * R * 0.5, ctr.y + offs[1] * R * 0.5, ctr.z + offs[2] * R * 0.5)
    v = ctr - Vector(lo.location)
    lo.rotation_euler = v.to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print(f"pad_shot -> {OUT}  (facing {FWD:.1f} deg, yaw +{YAW}, ortho {cam_d.ortho_scale:.4f})")
