"""Diagnose rest vs open mouth across shapes / jaw_rig / body blends."""
import bpy, os, math, numpy as np
from mathutils import Vector, Matrix

OUT = os.path.abspath("mesh/canon/shapes/mouthdiag")
os.makedirs(OUT, exist_ok=True)
FWD = 235.1


def mouth_cam(ob, scale=0.28):
    me = ob.data
    co = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", co.ravel())
    H = float(co[:, 2].max() - co[:, 2].min())
    a = math.radians(FWD)
    hc = co[co[:, 2] > 0.208].mean(0)
    gi = {g.name: g.index for g in ob.vertex_groups}
    mz = None
    for nm in ("lip_upper", "lip_lower", "op_lip_seam"):
        if nm not in gi:
            continue
        idx = gi[nm]
        ids = [v.index for v in me.vertices for g in v.groups if g.group == idx and g.weight > 0.3]
        if ids:
            mz = float(co[ids, 2].mean())
            break
    if mz is None:
        mz = float(hc[2] - 0.1)
    for o in list(bpy.data.objects):
        if o.type == "CAMERA":
            bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = sc.render.resolution_y = 720
    cd = bpy.data.cameras.new("C")
    cam = bpy.data.objects.new("C", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cd.type = "ORTHO"
    cd.clip_start = 0.01
    cd.clip_end = H * 30
    cd.ortho_scale = scale
    Rr = H * 5
    cam.location = (hc[0] + math.sin(a) * Rr, hc[1] - math.cos(a) * Rr, mz)
    cam.rotation_euler = (math.radians(90), 0, a)
    return sc, H, a


def eval_co(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    obe = ob.evaluated_get(dg)
    ev = obe.to_mesh()
    eco = np.empty((len(ev.vertices), 3))
    ev.vertices.foreach_get("co", eco.ravel())
    obe.to_mesh_clear()
    return eco


def lip_aperture(ob):
    me = ob.data
    co = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", co.ravel())
    eco = eval_co(ob)
    gi = {g.name: g.index for g in ob.vertex_groups}

    def idxs(nm, thr=0.3):
        if nm not in gi:
            return np.array([], int)
        id_ = gi[nm]
        return np.array([v.index for v in me.vertices
                         for g in v.groups if g.group == id_ and g.weight > thr])

    up, lo = idxs("lip_upper"), idxs("lip_lower")
    if len(up) == 0 or len(lo) == 0:
        return {"aperture": None, "max_disp": float(np.linalg.norm(eco - co, axis=1).max())}
    return {
        "aperture": float(eco[up, 2].mean() - eco[lo, 2].mean()),
        "up_z": float(eco[up, 2].mean()),
        "lo_z": float(eco[lo, 2].mean()),
        "max_disp": float(np.linalg.norm(eco - co, axis=1).max()),
    }


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def open_jaw(arm, deg, a):
    jb = arm.data.bones["jaw"]
    hinge = Vector(jb.head_local)
    fwd = Vector((math.sin(a), -math.cos(a), 0))
    lat = Vector((-fwd.y, fwd.x, 0)).normalized()
    pb = arm.pose.bones["jaw"]
    R = (Matrix.Translation(hinge)
         @ Matrix.Rotation(math.radians(deg), 4, lat)
         @ Matrix.Translation(-hinge))
    pb.matrix = R @ pb.bone.matrix_local
    bpy.context.view_layer.update()


# ── 1 shapes ─────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath="mesh/canon/shapes/clyffy_v2_shapes.blend")
ob = next(o for o in bpy.data.objects if o.type == "MESH" and ".001" not in o.name)
sc, H, a = mouth_cam(ob)
kb = ob.data.shape_keys.key_blocks if ob.data.shape_keys else []
for k in kb:
    k.value = 0.0
print("shapes REST", lip_aperture(ob))
sc.render.filepath = f"{OUT}/cmp_shapes_REST.png"; bpy.ops.render.render(write_still=True)
if "mouthFunnel" in kb:
    kb["mouthFunnel"].value = 1.0
    print("shapes funnel", lip_aperture(ob))
    sc.render.filepath = f"{OUT}/cmp_shapes_funnel.png"; bpy.ops.render.render(write_still=True)
    kb["mouthFunnel"].value = 0.0

# ── 2 jaw_rig ────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath="mesh/canon/clyffy_v2_rig.blend")
ob = next(o for o in bpy.data.objects if o.type == "MESH" and ".001" not in o.name)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc, H, a = mouth_cam(ob)
reset_pose(arm)
print("jawrig REST", lip_aperture(ob))
sc.render.filepath = f"{OUT}/cmp_jawrig_REST.png"; bpy.ops.render.render(write_still=True)
for sign, tag in ((+1, "p"), (-1, "m")):
    reset_pose(arm)
    open_jaw(arm, 22 * sign, a)
    print(f"jawrig OPEN22{tag}", lip_aperture(ob))
    sc.render.filepath = f"{OUT}/cmp_jawrig_OPEN22{tag}.png"; bpy.ops.render.render(write_still=True)

# ── 3 body ───────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath="mesh/canon/body/clyffy_v2_body.blend")
ob = next(o for o in bpy.data.objects
          if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc, H, a = mouth_cam(ob, scale=0.30)
if ob.data.shape_keys:
    for k in ob.data.shape_keys.key_blocks:
        k.value = 0.0
reset_pose(arm)
print("body REST", lip_aperture(ob))
print("body has jaw bone", "jaw" in arm.data.bones)
print("body jaw vgroup", "jaw" in [g.name for g in ob.vertex_groups])
# jaw weight mass
if "jaw" in {g.name for g in ob.vertex_groups}:
    gi = {g.name: g.index for g in ob.vertex_groups}["jaw"]
    wsum = 0.0; n = 0
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.01:
                wsum += g.weight; n += 1
    print(f"body jaw weights: {n} verts sum={wsum:.1f}")
sc.render.filepath = f"{OUT}/cmp_body_REST.png"; bpy.ops.render.render(write_still=True)
if "jaw" in arm.pose.bones:
    for sign, tag in ((+1, "p"), (-1, "m")):
        reset_pose(arm)
        open_jaw(arm, 22 * sign, a)
        print(f"body OPEN22{tag}", lip_aperture(ob))
        sc.render.filepath = f"{OUT}/cmp_body_OPEN22{tag}.png"; bpy.ops.render.render(write_still=True)
print("ok")
