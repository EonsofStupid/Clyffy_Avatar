import bpy,sys,os,math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
a=math.radians(FWD)
fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
lateral=Vector((-fwd.y,fwd.x,0.0))
print(f"fwd     ({fwd.x:+.3f},{fwd.y:+.3f})")
print(f"lateral ({lateral.x:+.3f},{lateral.y:+.3f})   dot={fwd.dot(lateral):+.4f}")

sk=me.shape_keys.key_blocks.get("jaw_open") if me.shape_keys else None
if sk:
    basis=me.shape_keys.key_blocks["Basis"]
    d=[(sk.data[i].co-basis.data[i].co) for i in range(len(co))]
    moved=[i for i,x in enumerate(d) if x.length>1e-6]
    print(f"moved verts: {len(moved)}")
    # SYMMETRY TEST: split moved verts by lateral side, compare counts and mean drop
    head=[c for c in co if c.z>zmin+H*0.70]
    axis=Vector((sum(c.x for c in head)/len(head),sum(c.y for c in head)/len(head)))
    L=[i for i in moved if (co[i]-Vector((axis.x,axis.y,co[i].z))).dot(lateral)>0]
    R=[i for i in moved if (co[i]-Vector((axis.x,axis.y,co[i].z))).dot(lateral)<0]
    print(f"  lateral+ side: {len(L)} verts, mean |delta| {sum(d[i].length for i in L)/max(1,len(L)):.4f}")
    print(f"  lateral- side: {len(R)} verts, mean |delta| {sum(d[i].length for i in R)/max(1,len(R)):.4f}")
    dz=[d[i].z for i in moved]
    print(f"  delta-z: min {min(dz):+.4f}  max {max(dz):+.4f}  mean {sum(dz)/len(dz):+.4f}")
    # colour by displacement magnitude
    mx=max(x.length for x in d)
    vc=me.color_attributes.get("w") or me.color_attributes.new(name="w",type='FLOAT_COLOR',domain='POINT')
    for i in range(len(co)):
        t=d[i].length/mx if mx>0 else 0
        vc.data[i].color=(t,0.12,1.0-t,1)
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=560; sc.render.resolution_y=560
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=H*0.42
mc=Vector((0,0,0))
if sk:
    mv=[i for i in range(len(co)) if (sk.data[i].co-me.shape_keys.key_blocks["Basis"].data[i].co).length>1e-6]
    mc=sum((co[i] for i in mv),Vector())/max(1,len(mv))
R2=H*5
for off,tag in [(0,"front"),(math.radians(50),"q50")]:
    ang=a+off
    cam.location=(mc.x+math.sin(ang)*R2, mc.y-math.cos(ang)*R2, mc.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"w_{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
