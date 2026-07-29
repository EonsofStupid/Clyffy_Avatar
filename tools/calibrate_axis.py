"""Render an angle sweep so a human can pick the forward axis ONCE per character.

    blender --background --python tools/calibrate_axis.py -- <mesh> <out_dir> [step_deg]

Writes ang_000.png … and a contact sheet. Look at it, pick the head-on view, and record
that number in the character's pack manifest as `forward_axis_deg`. Every downstream tool
reads it from there.

⚠️ CORRECTED 2026-07-25. This docstring used to claim the solvers below "all failed"
against a ground truth of 225 deg. THE 225 WAS WRONG, so the error figures were wrong,
and the conclusion ("calibrate, don't infer") was the wrong lesson drawn from it. That
mistaken note is why the correct measurement was distrusted for a whole session.

What actually happened:
  * max-radial-from-head-centroid   -> 284.6 deg   genuinely wrong (found a cheek)
  * bilateral-symmetry-plane        -> 170.5 deg   ROUGHLY RIGHT, and dismissed. It was
                                      run on the whole BODY; restricted to the head and
                                      allowed to fit the plane's offset it gives 233.75,
                                      matching the image-mirror scan to 1.4 deg.
  * narrow-band snout search        -> 305.0 deg   genuinely wrong (contrast only 1.95)

The true axis is 235.1 deg (world). A render sweep viewed as a downscaled contact sheet
read as 225 — the mirror-difference curve is smooth and shallow near its minimum, so a
10 deg error is invisible to the eye. Eyeballing a sweep is NOT a measurement.

USE THIS TOOL FOR A SANITY CHECK, NOT FOR THE NUMBER. To measure:
    tools/head_axis.py     3D bilateral symmetry of the HEAD, angle + plane offset
    tools/_mirrorscore.py  renders head-on and scores each image against its own mirror
Both are objective and they agree. And always record WHICH SPACE the angle is in — the
deeper bug was a world-space angle applied to local coordinates.
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
MESH = os.path.abspath(argv[0])
OUT  = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(os.path.dirname(MESH), "axis_cal")
STEP = float(argv[2]) if len(argv) > 2 else 45.0
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
if MESH.lower().endswith(".fbx"): bpy.ops.import_scene.fbx(filepath=MESH)
else:                             bpy.ops.import_scene.gltf(filepath=MESH)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))

mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for c in ob.bound_box:
    w = ob.matrix_world @ Vector(c)
    mn = Vector((min(mn[i], w[i]) for i in range(3)))
    mx = Vector((max(mx[i], w[i]) for i in range(3)))
dims = mx - mn; H = dims.z; ctr = (mn + mx) / 2

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 420; sc.render.resolution_y = 520

cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"

# frame the head — that is where "which way is forward" is legible
hc = Vector((ctr.x, ctr.y, mn.z + H*0.85)); R = H*0.6
cd.ortho_scale = H*0.36

angles = [a for a in range(0, 360, int(STEP))]
for a_deg in angles:
    a = math.radians(a_deg)
    # canonical convention — must match every other tool in this repo
    cam.location = (hc.x + math.sin(a)*R, hc.y - math.cos(a)*R, hc.z)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = os.path.join(OUT, f"ang_{a_deg:03d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {a_deg:3d} deg")

print(f"\nSweep written to {OUT}")
print("Pick the head-on view and record it as forward_axis_deg in the pack manifest.")
