"""Where is the skin tearing? Per-edge and per-face stretch on the posed rig.

Renders a stretch map and reports the worst offenders with their material, jaw weight
and position, so the corner artefact is identified rather than guessed at.

    blender -b --python tools/stretch_map.py -- <rig.blend> <out_dir> <fwd_deg> <angle>
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--")+1:]
RIG, OUT, FWD, ANGDEG = (os.path.abspath(argv[0]), os.path.abspath(argv[1]),
                         float(argv[2]), float(argv[3]))
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=RIG)
ob  = [o for o in bpy.data.objects if o.type == "MESH"][0]
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
me  = ob.data
N   = len(me.vertices)
co  = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin

a   = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
di  = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cavf = {p.index for p in me.polygons if p.material_index == di}
cav  = sorted({v for p in me.polygons if p.material_index == di for v in p.vertices})
mouth = co[cav].mean(axis=0)

gj = ob.vertex_groups["jaw"].index
w = np.zeros(N)
for v in me.vertices:
    for g in v.groups:
        if g.group == gj: w[v.index] = g.weight

jb = arm.pose.bones["jaw"]
hv = Vector(jb.bone.head_local); lv = Vector(lat)
R = Matrix.Translation(hv) @ Matrix.Rotation(math.radians(ANGDEG), 4, lv) @ Matrix.Translation(-hv)
jb.matrix = R @ jb.bone.matrix_local
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); obe = ob.evaluated_get(dg); ev = obe.to_mesh()
d = np.empty((N, 3)); ev.vertices.foreach_get("co", d.ravel()); obe.to_mesh_clear()

# ---- per-edge stretch ----
E = np.array([[e.vertices[0], e.vertices[1]] for e in me.edges], dtype=np.int64)
L0 = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1)
L1 = np.linalg.norm(d[E[:, 0]] - d[E[:, 1]], axis=1)
ok = L0 > 1e-9
ratio = np.ones(len(E)); ratio[ok] = L1[ok]/L0[ok]
print(f"edge stretch @ {ANGDEG:.0f} deg: max {ratio.max():.2f}x  "
      f"p99.9 {np.percentile(ratio,99.9):.2f}x  p99 {np.percentile(ratio,99):.2f}x  median {np.median(ratio):.3f}x")
for thr in (1.5, 2.0, 3.0, 5.0):
    print(f"  edges stretched >{thr:.1f}x : {int((ratio>thr).sum())}")

# per-vertex worst incident edge, for the colour map
vstretch = np.ones(N)
for k in range(len(E)):
    r = ratio[k]
    if r > vstretch[E[k,0]]: vstretch[E[k,0]] = r
    if r > vstretch[E[k,1]]: vstretch[E[k,1]] = r

cavset = set(cav)
srcattr = me.attributes.get("cav_src")
src = np.array([d.value for d in srcattr.data], dtype=np.int64) if srcattr else -np.ones(N, np.int64)
top = np.argsort(-ratio)[:15]
print("\nTOP 15 EDGES BY STRETCH:")
print(f"  {'ratio':>8} {'rest_len':>9} {'new_len':>9}  {'w0':>5} {'w1':>5}  {'v0':>7} {'v1':>7}  kind")
for k in top:
    i, j = int(E[k,0]), int(E[k,1])
    ki = "bag" if i in cavset else "skin"; kj = "bag" if j in cavset else "skin"
    di_, dj_ = ("cap/inner" if src[i] >= 0 else "rim/surf"), ("cap/inner" if src[j] >= 0 else "rim/surf")
    print(f"  {ratio[k]:8.2f} {L0[k]:9.5f} {L1[k]:9.5f}  {w[i]:5.2f} {w[j]:5.2f}  {i:7d} {j:7d}  "
          f"{ki}/{di_} - {kj}/{dj_}  z={(co[i,2]+co[j,2])/2:+.4f}")
nbag = sum(1 for k in np.where(ratio>3.0)[0] if int(E[k,0]) in cavset or int(E[k,1]) in cavset)
print(f"\n  of {int((ratio>3.0).sum())} edges >3x: {nbag} touch the mouth bag, {int((ratio>3.0).sum())-nbag} are pure skin")
worst = np.argsort(-ratio)[:400]
print("\nworst-stretched edges, grouped:")
buckets = {}
for k in worst:
    i, j = E[k]
    incav = (i in set(cav)) or (j in set(cav))
    key = ("cavity" if incav else "skin")
    buckets.setdefault(key, []).append(k)
for key, ks in buckets.items():
    ks = np.array(ks)
    mid = (co[E[ks,0]] + co[E[ks,1]])/2
    ww  = (w[E[ks,0]] + w[E[ks,1]])/2
    latoff = mid @ lat - float(co[co[:,2] > mouth[2]].mean(axis=0) @ lat)
    print(f"  {key:7s} n={len(ks)}  stretch {ratio[ks].min():.2f}-{ratio[ks].max():.2f}x  "
          f"z[{mid[:,2].min():+.4f},{mid[:,2].max():+.4f}]  |lateral offset| {np.abs(latoff).mean():.4f} "
          f"(head half-width ~0.168)  jaw weight {ww.min():.2f}-{ww.max():.2f} mean {ww.mean():.2f}")

# how far laterally does the cavity reach vs the lip rim?
surf = {v for p in me.polygons if p.index not in cavf for v in p.vertices}
rim  = np.array(sorted(set(cav) & surf))
inner= np.array(sorted(set(cav) - surf))
ctr_lat = float(co[co[:,2] > mouth[2]].mean(axis=0) @ lat)
print(f"\nlateral reach about the midline:")
for name, ix in (("lip rim", rim), ("cavity interior", inner)):
    o = co[ix] @ lat - ctr_lat
    print(f"  {name:16s} n={len(ix)}  lateral [{o.min():+.4f},{o.max():+.4f}]  span {o.max()-o.min():.4f}")
print(f"  {'stretched skin':16s}      lateral extremes of the >2x edges: "
      f"{np.abs((co[E[ratio>2.0][:,0]] @ lat) - ctr_lat).max() if (ratio>2.0).any() else 0:.4f}")

ca = me.color_attributes.get("stretch") or me.color_attributes.new(name="stretch", type='FLOAT_COLOR', domain='POINT')
t = np.clip((vstretch - 1.0)/1.5, 0, 1)
cols = np.zeros((N,4)); cols[:,0] = t; cols[:,1] = 0.35*(1-t); cols[:,2] = 1.0-t; cols[:,3] = 1
ca.data.foreach_set("color", cols.ravel())
me.color_attributes.active_color = ca

sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'VERTEX'
sc.render.resolution_x = sc.render.resolution_y = 700
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = H*0.26
R2 = H*5
for off, tag in ((0, "front"), (math.radians(50), "q50")):
    ang = a + off
    cam.location = (mouth[0]+math.sin(ang)*R2, mouth[1]-math.cos(ang)*R2, mouth[2])
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"stretch_{tag}.png")
    bpy.ops.render.render(write_still=True)
print("ok")
