"""Render a TRUE 90 degree side view of the head, framed on the head alone.

    blender -b --python tools/profile_shot.py -- <mesh.blend> <out.png> [fwd]

The camera angle is DERIVED from the canonical forward, not eyeballed. With the turnaround
convention `cam.location = ctr + (sin a, -cos a, 0) * R`, `rotation_euler = (90, 0, a)`, the
camera looks along `(-sin a, cos a, 0)` and its right vector is `(cos a, sin a, 0)`. Setting
`a = FWD - 90` makes the view direction the lateral axis and the image-right axis the character's
FORWARD — so the snout lands at HIGH x and the back of the skull at LOW x, and no view is ever
"nearly side on".

Silhouette work only: BLENDER_WORKBENCH with a flat single-colour shading and a white world, so
the mesh reads as one solid mass against a bright field and segmentation never has to separate
white fur from white background by value.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2]) if len(argv) > 2 and not argv[2].startswith("--") else 235.1
# How far below the lip seam to keep, as a fraction of figure height. 0.090 is the collar and is
# right for snout work; chin and neck work needs more of the throat than that. Defined HERE, with
# the other args, because the framing code below consumes it long before the render settings.
CUT = float(argv[argv.index("--cut") + 1]) if "--cut" in argv else 0.090
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
for o in list(bpy.data.objects):
    if o.type == "MESH" and o is not ob:
        bpy.data.objects.remove(o, do_unlink=True)

# REST POSE. From body_rig onward the mesh is parented to `clyffy_rig`, and the render shows the
# ARMATURE-DEFORMED result while the framing is computed from the undeformed vertex data. The
# head came out turned roughly 30 degrees and the "true profile" measured 0.123 against 0.455 —
# a rig pose masquerading as a geometry regression. Object transforms are identity on every
# blend in the chain, so this was the only thing that could rotate it.
for arm in bpy.data.objects:
    if arm.type == "ARMATURE":
        arm.data.pose_position = "REST"

# ZERO EVERY SHAPE KEY. From shape_author onward the blends are SAVED with all 48 key blocks at
# value 1.0 — every ARKit blendshape stacked at full strength, jawForward and mouthDimple
# included. The render shows the EVALUATED mesh, so the muzzle measured 0.454 -> 0.270 across
# that stage and looked like the reshape had been destroyed. It had not; the rest pose was simply
# never being displayed. The shipped canon body carries the same state, so this is pre-existing.
_sk = 0
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            if kb.value:
                kb.value = 0.0
                _sk += 1
        o.show_only_shape_key = False
if _sk:
    print(f"  zeroed {_sk} non-zero shape keys so the REST shape is what gets measured")

N = len(ob.data.vertices)
co = np.empty((N, 3)); ob.data.vertices.foreach_get("co", co.ravel())
M = np.array(ob.matrix_world)
co = co @ M[:3, :3].T + M[:3, 3]
z = co[:, 2]

# ── FACING IS MEASURED FROM THE MESH, NOT ASSUMED ────────────────────────────
# FWD=235.1 describes the CANONICAL head blends. `body_rig` reorients the character in the VERTEX
# DATA for VRM export, so from that stage on the constant is simply wrong — object transforms are
# identity and the armature was forced to rest, yet the body still rendered as a 3/4 view and
# measured 0.127 against a reference of 0.455. A rotated camera reads as a destroyed muzzle.
#
# `op_lip_seam` sits on the FRONT of the face by definition and survives every stage of the
# chain, so the horizontal direction from the head's centroid to the lip seam IS the facing.
gi = {g.name: g.index for g in ob.vertex_groups}
if "op_lip_seam" in gi:
    want = gi["op_lip_seam"]
    idx = [v.index for v in ob.data.vertices
           for g in v.groups if g.group == want and g.weight > 0.5]
    lip_c = co[idx].mean(axis=0)
    head_c = co[z > lip_c[2]].mean(axis=0)
    d = lip_c[:2] - head_c[:2]
    n = float(np.hypot(*d))
    if n > 1e-6:
        FWD = math.degrees(math.atan2(d[0] / n, -d[1] / n)) % 360.0
        print(f"  facing MEASURED from op_lip_seam: {FWD:.1f} deg (canonical head blends are 235.1)")
    else:
        print("  WARNING: lip seam sits on the head centroid — falling back to FWD constant")
else:
    print(f"  WARNING: no op_lip_seam group — assuming FWD={FWD}, which is only correct "
          f"before body_rig")

a_f = math.radians(FWD)
lat = np.array([math.cos(a_f - math.pi / 2), math.sin(a_f - math.pi / 2), 0.0])

# Frame on the HEAD: the top slab of the figure. Generous enough to include the throat, tight
# enough that the chest never enters frame — the chest was previously the frontmost silhouette
# pixel and it set the "snout" reading.
#
# The frame is sized from the head's own FORWARD EXTENT, not from figure height. A head that is
# deeper than it is tall gets clipped otherwise: Blender's `ortho_scale` spans the LARGER render
# axis, so at 1100x1400 the horizontal field was only 0.323 against a head 0.344 deep and the
# snout — the one feature being measured — fell outside the frame.
fwdv = np.array([math.sin(a_f), -math.cos(a_f), 0.0])
H = float(z.max() - z.min())
z_hi = float(z.max())

# THE CUT IS ANATOMICAL, NOT A FRACTION OF FIGURE HEIGHT. `z_hi - 0.30*H` cuts a different part
# of the animal on every mesh: the neck-compression stage moves the head down, so the same
# formula gave 0.1957 on the canon body and 0.1706 on the reshaped one, and the two "head-only"
# silhouettes were not the same anatomy. That is the same mismatched-extent error that has now
# cost this project six separate measurements. `op_lip_seam` is an operator vertex group carried
# through every stage of the chain, so the collar is 9%H below it on any of them — the same
# constant head_proportion uses for the collar.
gi_ls = {g.name: g.index for g in ob.vertex_groups}
if "op_lip_seam" in gi_ls:
    want_ls = gi_ls["op_lip_seam"]
    zs = [co[v.index, 2] for v in ob.data.vertices
          for g in v.groups if g.group == want_ls and g.weight > 0.5]
    z_lo = float(np.mean(zs)) - CUT * H
    print(f"  cut anchored to op_lip_seam ({len(zs)} verts): lip z={np.mean(zs):.4f} "
          f"-> z_lo={z_lo:.4f}  (cut {CUT:.3f}H below the lip)")
else:
    z_lo = z_hi - 0.30 * H
    print(f"  WARNING: no op_lip_seam group — falling back to z_hi-0.30H = {z_lo:.4f}; "
          f"this is NOT comparable across meshes whose head sits at a different height")
head = z >= z_lo
fh = co[head] @ fwdv
f_mid = 0.5 * (float(fh.max()) + float(fh.min()))
depth = float(fh.max() - fh.min())
lat_mid = float(np.median(co[head] @ lat))
ctr = Vector((float(fwdv[0] * f_mid + lat[0] * lat_mid),
              float(fwdv[1] * f_mid + lat[1] * lat_mid),
              0.5 * (z_hi + z_lo)))
R = float(H)
FIELD = 1.20 * max(depth, z_hi - z_lo)

# CUT THE BODY AWAY BEFORE RENDERING. Framing alone is not enough: on a full-body blend the
# shoulders stay in frame, and every landmark in head_metrics is derived from the silhouette's
# WIDTH PROFILE — the shoulders are wider than the head, so they become `wmax`, the crown drops
# to the wrong row and every ratio built on it is wrong. Deleting below the collar means the only
# thing that can be measured is the head. This edits the in-memory copy only; nothing is saved.
import bmesh
bm = bmesh.new()
bm.from_mesh(ob.data)
bm.verts.ensure_lookup_table()
Mw = ob.matrix_world
doomed = [v for v in bm.verts if (Mw @ v.co).z < z_lo]
bmesh.ops.delete(bm, geom=doomed, context="VERTS")
bm.to_mesh(ob.data)
bm.free()
ob.data.update()
print(f"  head-only: dropped {len(doomed)} verts below z={z_lo:.4f}")

SHADED = "--shaded" in argv     # for LOOKING at; the silhouette pass is what gets measured

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
if SHADED:
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"
    sh.show_specular_highlight = True
else:
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (0.05, 0.05, 0.05)
    sh.show_specular_highlight = False
sc.render.film_transparent = False
w = bpy.data.worlds.new("W")
w.color = (1.0, 1.0, 1.0)
sc.world = w
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = 1300
sc.render.resolution_y = 1300
sc.render.image_settings.file_format = "PNG"

cd = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.type = "ORTHO"
cd.ortho_scale = FIELD
ang = math.radians(FWD - 90.0)
cam.location = (ctr.x + math.sin(ang) * R * 4, ctr.y - math.cos(ang) * R * 4, ctr.z)
cam.rotation_euler = (math.radians(90), 0, ang)

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print(f"profile_shot: {os.path.basename(SRC)} -> {OUT}")
print(f"  frame z {z_lo:.4f}..{z_hi:.4f}   ortho {cd.ortho_scale:.4f}   cam angle {FWD-90:.1f} deg")
print(f"  image-right axis is the character's FORWARD: snout at HIGH x")
