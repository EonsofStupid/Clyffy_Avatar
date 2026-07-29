import bpy,sys,os,math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
a=math.radians(FWD); fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
lateral=Vector((-fwd.y,fwd.x,0.0))
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head),sum(c.y for c in head)/len(head)))
# the cavity interior tells us exactly where the mouth is
dark=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
di=dark[0] if dark else -1
mouthv=set()
for p in me.polygons:
    if p.material_index==di:
        for vi in p.vertices: mouthv.add(vi)
mc=sum((me.vertices[i].co for i in mouthv),Vector())/max(1,len(mouthv))
print(f"cavity verts {len(mouthv)}  mouth centre ({mc.x:+.3f},{mc.y:+.3f},{mc.z:+.3f})")
mouth_z=mc.z
muzzle=(Vector((mc.x,mc.y))-axis).length
hinge=Vector((axis.x,axis.y,mouth_z))+fwd*(muzzle*0.10)
JD=H*0.075; BU=H*0.010
def wt(c):
    dz=mouth_z-c.z
    if dz<-BU or dz>JD: return 0.0
    f=(c-hinge).dot(fwd)
    if f<=0: return 0.0
    wf=min(1.0,f/(muzzle*0.90))
    wv=1.0-(-dz/BU) if dz<0 else (1.0-(dz-JD*0.7)/(JD*0.3) if dz>JD*0.7 else 1.0)
    w=max(0.0,min(1.0,wf*wv)); return w*w*(3-2*w)
ws=[wt(c) for c in co]
n=sum(1 for w in ws if w>0.01)
print(f"jaw-weighted {n} / {len(co)} ({100*n/len(co):.1f}%)")
ob.shape_key_add(name="Basis",from_mix=False)
sk=ob.shape_key_add(name="jaw_open",from_mix=False)
ANG=math.radians(26)
for i,c in enumerate(co):
    if ws[i]>0: sk.data[i].co=hinge+(Matrix.Rotation(ANG*ws[i],4,lateral)@(c-hinge))
mx=max((sk.data[i].co-co[i]).length for i in range(len(co)))
print(f"max displacement {mx:.4f} = {100*mx/H:.1f}% of height")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"clyffy_v2_jaw.blend"))
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=600; sc.render.resolution_y=600
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=H*0.30
R=H*5
for off,tag in [(0,"front"),(math.radians(45),"q45")]:
    ang=a+off
    cam.location=(mc.x+math.sin(ang)*R, mc.y-math.cos(ang)*R, mc.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    for amt in (0.0,0.5,1.0):
        sk.value=amt
        sc.render.filepath=os.path.join(OUT,f"j_{tag}_{int(amt*100):03d}.png"); bpy.ops.render.render(write_still=True)
print("ok")
