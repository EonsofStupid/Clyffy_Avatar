import bpy, bmesh, sys, os, math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
THRESH=float(argv[2]) if len(argv)>2 else 0.09
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head), sum(c.y for c in head)/len(head)))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fn=(Vector((tip.x,tip.y))-axis).normalized(); fwd=Vector((fn.x,fn.y,0))

mat=me.materials[0]; img=None
for l in mat.node_tree.links:
    if l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE': img=l.from_node.image
W,Ht=img.size; px=list(img.pixels); uvl=me.uv_layers.active.data
def lum_of(p):
    us=[uvl[li].uv for li in p.loop_indices]
    u=sum(x.x for x in us)/len(us); v=sum(x.y for x in us)/len(us)
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2]

mouth=set()
for p in me.polygons:
    c=p.center
    if c.z < tip.z-H*0.09 or c.z > tip.z+H*0.02: continue        # below the nose only
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd) < H*0.03: continue
    if lum_of(p) < THRESH: mouth.add(p.index)
ctrs=[me.polygons[i].center for i in mouth]
print(f"THRESH {THRESH}  mouth faces {len(mouth)}")
if ctrs:
    lat=[(c-Vector((axis.x,axis.y,c.z))).cross(fwd).z for c in ctrs]
    print(f"  lateral span {max(lat)-min(lat):.3f}  z {min(c.z for c in ctrs):+.3f}..{max(c.z for c in ctrs):+.3f}  tip z {tip.z:+.3f}")

vc=me.color_attributes.new(name="mask",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.82,0.82,0.84,1)
for pi in mouth:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1.0,0.10,0.04,1)

sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=700; sc.render.resolution_y=700
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z))-fwd*(H*0.030)
R=H*0.30; cd.ortho_scale=H*0.24
# SAME convention as the working turnaround: loc=(sin a, -cos a), rot=(90,0,a)
a0=math.atan2(fwd.x,-fwd.y)
for off,tag in [(0,"front"),(math.radians(42),"q42")]:
    a=a0+off
    cam.location=(ctr.x+math.sin(a)*R, ctr.y-math.cos(a)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    sc.render.filepath=os.path.join(OUT,f"m_{tag}.png"); bpy.ops.render.render(write_still=True)
print("done")
