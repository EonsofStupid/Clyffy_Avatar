import bpy, math, numpy as np, os

OUT = "mesh/canon/shapes/mouthdiag"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath="mesh/canon/body/clyffy_v2_body.blend")
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
for m in bpy.data.materials:
    if m and ("teeth" in m.name or "tongue" in m.name):
        m.diffuse_color = (0.05, 0.02, 0.02, 1.0)
        print("dimmed", m.name)
me = ob.data
co = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(235.1)
hc = co[co[:, 2] > 0.208].mean(0)
mz = 0.225
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
cd.ortho_scale = 0.28
cd.clip_start = 0.01
cd.clip_end = H * 30
Rr = H * 5
cam.location = (hc[0] + math.sin(a) * Rr, hc[1] - math.cos(a) * Rr, mz)
cam.rotation_euler = (math.radians(90), 0, a)
if ob.data.shape_keys:
    for k in ob.data.shape_keys.key_blocks:
        k.value = 0.0
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for pb in arm.pose.bones:
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0, 0, 0)
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
sc.render.filepath = f"{OUT}/rest_teeth_dimmed.png"
bpy.ops.render.render(write_still=True)
print("ok")
