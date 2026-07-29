import bpy, sys, os, math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for ob in bpy.data.objects:
    if ob.type=="MESH":
        for c in ob.bound_box:
            w=ob.matrix_world@Vector(c)
            mn=Vector((min(mn[i],w[i]) for i in range(3))); mx=Vector((max(mx[i],w[i]) for i in range(3)))
ctr=(mn+mx)/2; dims=mx-mn; r=max(dims)
sc=bpy.context.scene
sc.render.engine="BLENDER_WORKBENCH"
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=640; sc.render.resolution_y=800
w=bpy.data.worlds.new("W"); sc.world=w
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.ortho_scale=r*1.15
for ang in range(0,360,45):
    a=math.radians(ang)
    cam.location=(ctr.x+math.sin(a)*r*3, ctr.y-math.cos(a)*r*3, ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    sc.render.filepath=os.path.join(OUT,f"a{ang:03d}.png")
    bpy.ops.render.render(write_still=True)
print("dims",[round(v,3) for v in dims])
