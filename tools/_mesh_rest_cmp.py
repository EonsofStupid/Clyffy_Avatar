import bpy, numpy as np

def load(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
    co = np.empty((len(ob.data.vertices), 3)); ob.data.vertices.foreach_get("co", co.ravel())
    return co, ob.name

c_rig, n1 = load("mesh/canon/clyffy_v2_rig.blend")
c_shp, n2 = load("mesh/canon/shapes/clyffy_v2_shapes.blend")
c_bdy, n3 = load("mesh/canon/body/clyffy_v2_body.blend")
c_parts, n4 = load("mesh/canon/clyffy_v2_parts.blend")
print("N", len(c_rig), len(c_shp), len(c_bdy), len(c_parts))
for a, b, lab in [
    (c_rig, c_shp, "rig vs shapes"),
    (c_rig, c_bdy, "rig vs body"),
    (c_shp, c_bdy, "shapes vs body"),
    (c_parts, c_shp, "parts vs shapes"),
    (c_parts, c_rig, "parts vs rig"),
]:
    if len(a) != len(b):
        print(lab, "N mismatch"); continue
    d = np.linalg.norm(a - b, axis=1)
    print(f"{lab}: max {d.max():.6f} mean {d.mean():.6e} n>1e-5 {(d>1e-5).sum()} n>1e-3 {(d>1e-3).sum()}")
