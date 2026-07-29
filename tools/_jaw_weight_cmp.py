import bpy, numpy as np

def load_w(path, gname):
    bpy.ops.wm.open_mainfile(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    ob = max(meshes, key=lambda o: len(o.data.vertices))
    N = len(ob.data.vertices)
    w = np.zeros(N)
    gi = {g.name: g.index for g in ob.vertex_groups}
    if gname not in gi:
        print(path, "NO", gname, "have", list(gi.keys())[:25])
        return None, None
    idx = gi[gname]
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == idx:
                w[v.index] = g.weight
    co = np.empty((N, 3)); ob.data.vertices.foreach_get("co", co.ravel())
    return w, co

w1, c1 = load_w("mesh/canon/clyffy_v2_rig.blend", "jaw")
w2, c2 = load_w("mesh/canon/body/clyffy_v2_body.blend", "jaw")
print("N", len(w1), len(w2), "coords match", np.allclose(c1, c2))
print("jaw_rig jaw: n>0.01", int((w1 > 0.01).sum()), "n>0.99", int((w1 > 0.99).sum()),
      "mean", float(w1[w1 > 0.01].mean()), "max", float(w1.max()))
print("body    jaw: n>0.01", int((w2 > 0.01).sum()), "n>0.99", int((w2 > 0.99).sum()),
      "mean", float(w2[w2 > 0.01].mean()), "max", float(w2.max()))
d = np.abs(w1 - w2)
print("abs diff mean", float(d.mean()), "max", float(d.max()),
      "n>0.05", int((d > 0.05).sum()), "n>0.2", int((d > 0.2).sum()))
core = w1 > 0.9
print("core w1>0.9: body mean", float(w2[core].mean()), "min", float(w2[core].min()),
      "n body<0.5", int((w2[core] < 0.5).sum()), "/", int(core.sum()))
band = (w1 > 0.05) & (w1 < 0.5)
print("falloff band n", int(band.sum()), "w1 mean", float(w1[band].mean()),
      "w2 mean", float(w2[band].mean()))

ws1, _ = load_w("mesh/canon/clyffy_v2_rig.blend", "skull")
ws2, _ = load_w("mesh/canon/body/clyffy_v2_body.blend", "skull")
print("skull rig n>0.01", int((ws1 > 0.01).sum()), "body", int((ws2 > 0.01).sum()))
print("skull abs diff max", float(np.abs(ws1 - ws2).max()), "mean", float(np.abs(ws1 - ws2).mean()))

# where body jaw is much weaker than source
hurt = (w1 - w2) > 0.3
print("jaw diluted >0.3: n", int(hurt.sum()), "mean w1", float(w1[hurt].mean()) if hurt.any() else 0,
      "mean w2", float(w2[hurt].mean()) if hurt.any() else 0)
# Σ of non-jaw non-skull on those verts from body groups
bpy.ops.wm.open_mainfile(filepath="mesh/canon/body/clyffy_v2_body.blend")
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
N = len(ob.data.vertices)
groups = {g.name: g.index for g in ob.vertex_groups}
face = {"jaw", "skull", "eye_L", "eye_R", "leftEye", "rightEye", "head"}
steal = np.zeros(N)
for name, idx in groups.items():
    if name in face or name.startswith("ear"):
        continue
    for v in ob.data.vertices:
        for g in v.groups:
            if g.group == idx:
                steal[v.index] += g.weight
print("on diluted verts, non-face weight mean", float(steal[hurt].mean()) if hurt.any() else 0)
print("on core, non-face weight mean", float(steal[core].mean()))
print("on core, jaw+skull sum mean", float((w2 + ws2)[core].mean()))
