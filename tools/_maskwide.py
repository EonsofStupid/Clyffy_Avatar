import bpy,bmesh,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]); os.makedirs(OUT,exist_ok=True)
TH=float(argv[3]) if len(argv)>3 else 0.11
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=max([o for o in bpy.data.objects if o.type=="MESH"],key=lambda o:len(o.data.vertices)); me=ob.data
co=[v.co.copy() for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head),sum(c.y for c in head)/len(head)))
a=math.radians(FWD); fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
lateral=Vector((-fwd.y,fwd.x,0))
band=[c for c in head if abs((c-Vector((axis.x,axis.y,c.z))).dot(lateral))<H*0.05]
tip=max(band,key=lambda c:(c-Vector((axis.x,axis.y,c.z))).dot(fwd))
mat=me.materials[0]; img=None
for l in mat.node_tree.links:
    if l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE': img=l.from_node.image
W,Ht=img.size; px=list(img.pixels); uvl=me.uv_layers.active.data
def lum(u,v):
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2]
seed=set()
for p in me.polygons:
    c=p.center
    if c.z<tip.z-H*0.075 or c.z>tip.z+H*0.005: continue
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd)<H*0.03: continue
    us=[uvl[li].uv for li in p.loop_indices]
    pts=list(us)+[sum(us,Vector((0,0)))/len(us)]
    for i in range(len(us)): pts.append((us[i]+us[(i+1)%len(us)])/2)
    if any(lum(q.x,q.y)<TH for q in pts): seed.add(p.index)
vc=me.color_attributes.new(name="m",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.85,0.85,0.87,1)
for pi in seed:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1,0.08,0.03,1)
# mark the detected tip in BLUE so I can see if it is on the muzzle
best=min(range(len(me.vertices)), key=lambda i:(me.vertices[i].co-tip).length)
for vi in [best]: vc.data[vi].color=(0,0.3,1,1)
print(f"tip {tuple(round(v,3) for v in tip)}  seed {len(seed)}")
sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=520; sc.render.resolution_y=640
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*20
ctr=Vector((axis.x,axis.y,zmin+H*0.5)); R=H*4
cd.ortho_scale=H*1.15
for off,tag in [(0,"front"),(math.radians(90),"side")]:
    ang=a+off
    cam.location=(ctr.x+math.sin(ang)*R, ctr.y-math.cos(ang)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"wide_{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
