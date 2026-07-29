import bpy, numpy as np

bpy.ops.wm.open_mainfile(filepath="mesh/canon/body/clyffy_v2_body.blend")
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
co = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", co.ravel())
kb = me.shape_keys.key_blocks
basis = kb["Basis"]
bco = np.array([list(basis.data[i].co) for i in range(len(me.vertices))])
d = np.linalg.norm(co - bco, axis=1)
print("basis vs mesh max", float(d.max()), "mean", float(d.mean()), "n>1e-6", int((d > 1e-6).sum()))
# any non-zero shape key values?
for k in kb:
    if k.value != 0:
        print("NONZERO KEY", k.name, k.value)
print("all keys zero" if all(k.value == 0 for k in kb) else "some nonzero")
# mute shape keys and compare evaluated
for k in kb:
    k.mute = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
obe = ob.evaluated_get(dg); ev = obe.to_mesh()
eco = np.empty((len(ev.vertices), 3)); ev.vertices.foreach_get("co", eco.ravel()); obe.to_mesh_clear()
d2 = np.linalg.norm(eco - co, axis=1)
print("muted sk eval vs mesh max", float(d2.max()))
for k in kb:
    k.mute = False
