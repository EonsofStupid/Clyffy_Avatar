import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
angles=[float(a) for a in argv[2:]]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=max([o for o in bpy.data.objects if o.type=="MESH"],key=lambda o:len(o.data.vertices))
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for c in ob.bound_box:
    w=ob.matrix_world@Vector(c)
    mn=Vector((min(mn[i],w[i]) for i in range(3))); mx=Vector((max(mx[i],w[i]) for i in range(3)))
dims=mx-mn; H=dims.z; ctr=(mn+mx)/2
sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=460; sc.render.resolution_y=560
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
hc=Vector((ctr.x,ctr.y,mn.z+H*0.85)); R=H*0.6; cd.ortho_scale=H*0.36
for a_deg in angles:
    a=math.radians(a_deg)
    cam.location=(hc.x+math.sin(a)*R, hc.y-math.cos(a)*R, hc.z)
    cam.rotation_euler=(math.radians(90),0,a)
    sc.render.filepath=os.path.join(OUT,f"ang_{int(a_deg):03d}.png"); bpy.ops.render.render(write_still=True)
print("ok")
