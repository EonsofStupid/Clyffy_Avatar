import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BL)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
sk=me.shape_keys.key_blocks.get("jaw_open")
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head),sum(c.y for c in head)/len(head)))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fn=(Vector((tip.x,tip.y))-axis).normalized(); fwd=Vector((fn.x,fn.y,0))
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W2")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=560; sc.render.resolution_y=620
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((axis.x,axis.y,zmin+H*0.845)); R=H*0.5; cd.ortho_scale=H*0.40
a0=math.atan2(fwd.x,-fwd.y)
for off,tag in [(0,"front"),(math.radians(40),"q40")]:
    a=a0+off
    cam.location=(ctr.x+math.sin(a)*R,ctr.y-math.cos(a)*R,ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    for amt in (0.0,1.0):
        if sk: sk.value=amt
        sc.render.filepath=os.path.join(OUT,f"w_{tag}_{int(amt*100):03d}.png"); bpy.ops.render.render(write_still=True)
print("ok")
