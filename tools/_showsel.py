import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode!='OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
ob=meshes[0]; me=ob.data
for extra in meshes[1:]: bpy.data.objects.remove(extra, do_unlink=True)
sel=[v.index for v in me.vertices if v.select]
vc=me.color_attributes.get("sel") or me.color_attributes.new(name="sel",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.85,0.85,0.87,1)
for i in sel: vc.data[i].color=(1,0.08,0.03,1)
print(f"marked {len(sel)} selected verts")
co=[v.co for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("WW")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=560; sc.render.resolution_y=620
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30
selco=[me.vertices[i].co for i in sel]
ctr=sum(selco,Vector())/len(selco)
a0=math.radians(FWD); R=H*5
for off,tag,scale in [(0,"face",H*0.34),(math.radians(55),"q55",H*0.34),(0,"wide",H*1.1)]:
    ang=a0+off
    c = ctr if scale<H*0.5 else Vector((0,0,zmin+H*0.5))
    cd.ortho_scale=scale
    cam.location=(c.x+math.sin(ang)*R, c.y-math.cos(ang)*R, c.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"sel_{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
