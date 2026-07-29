import bpy

def jawinfo(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    j = arm.data.bones["jaw"]
    print("===", path)
    print("  head", tuple(round(x, 5) for x in j.head_local))
    print("  tail", tuple(round(x, 5) for x in j.tail_local))
    print("  len", round(j.length, 5), "parent", j.parent.name if j.parent else None)
    print("  matrix_local:")
    for row in j.matrix_local:
        print("   ", tuple(round(float(x), 5) for x in row))
    sk = arm.data.bones.get("skull") or arm.data.bones.get("head")
    if sk:
        print("  skull/head", sk.name, "head", tuple(round(x, 4) for x in sk.head_local),
              "tail", tuple(round(x, 4) for x in sk.tail_local))
        print("  children", [c.name for c in sk.children])
    # evaluate same rotation and compare a few lip verts
    import numpy as np, math
    from mathutils import Vector, Matrix
    ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
    co = np.empty((len(ob.data.vertices), 3)); ob.data.vertices.foreach_get("co", co.ravel())
    FWD = 235.1; a = math.radians(FWD)
    fwd = Vector((math.sin(a), -math.cos(a), 0))
    lat = Vector((-fwd.y, fwd.x, 0)).normalized()
    hinge = Vector(j.head_local)
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    def evald():
        dg = bpy.context.evaluated_depsgraph_get()
        obe = ob.evaluated_get(dg); ev = obe.to_mesh()
        v = np.empty((len(ev.vertices), 3)); ev.vertices.foreach_get("co", v.ravel()); obe.to_mesh_clear()
        return v
    base = evald()
    pb = arm.pose.bones["jaw"]
    R = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(22), 4, lat) @ Matrix.Translation(-hinge)
    pb.matrix = R @ pb.bone.matrix_local
    bpy.context.view_layer.update()
    opened = evald()
    disp = np.linalg.norm(opened - base, axis=1)
    print("  open max disp", float(disp.max()), "mean on moved", float(disp[disp > 1e-4].mean()))
    # z-drop of lower third of moved verts
    moved = disp > 0.01
    if moved.any():
        dz = opened[moved, 2] - base[moved, 2]
        print("  moved n", int(moved.sum()), "mean dz", float(dz.mean()), "min dz", float(dz.min()))

jawinfo("mesh/canon/clyffy_v2_rig.blend")
jawinfo("mesh/canon/body/clyffy_v2_body.blend")
