import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head), sum(c.y for c in head)/len(head)))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fwdn=(Vector((tip.x,tip.y))-axis).normalized(); fwd=Vector((fwdn.x,fwdn.y,0))

# --- pick the base-colour image (largest, index 0 of the material's TEX_IMAGE nodes) ---
img=None
mat=me.materials[0]
for n in mat.node_tree.nodes:
    if n.type=='TEX_IMAGE' and n.image:
        # base colour feeds Principled Base Color
        for l in mat.node_tree.links:
            if l.from_node is n and l.to_socket.name=='Base Color': img=n.image
if img is None:
    img=max([n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image], key=lambda i:i.size[0])
W,Ht=img.size
px=list(img.pixels)   # RGBA float
print(f"base colour image: {img.name} {W}x{Ht}")

uvl=me.uv_layers.active.data
def sample(u,v):
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return px[i],px[i+1],px[i+2]

# --- classify faces: dark (mouth line / inner) within the muzzle region ---
mouth=set(); lum_all=[]
for p in me.polygons:
    c=p.center
    if c.z < tip.z-H*0.10 or c.z > tip.z+H*0.06: continue
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd) < H*0.03: continue
    us=[uvl[li].uv for li in p.loop_indices]
    u=sum(x.x for x in us)/len(us); v=sum(x.y for x in us)/len(us)
    r,g,b=sample(u,v); lum=0.2126*r+0.7152*g+0.0722*b
    lum_all.append((lum,p.index))
    if lum < 0.055: mouth.add(p.index)
lum_all.sort()
print(f"faces in muzzle band: {len(lum_all)}  darkest lum {lum_all[0][0]:.4f}  median {lum_all[len(lum_all)//2][0]:.4f}")
print(f"mouth faces (lum<0.055): {len(mouth)}")
if mouth:
    ctrs=[me.polygons[i].center for i in mouth]
    lat=[(c-Vector((axis.x,axis.y,c.z))).cross(fwd).z for c in ctrs]
    print(f"  lateral span {max(lat)-min(lat):.3f}   z {min(c.z for c in ctrs):+.3f}..{max(c.z for c in ctrs):+.3f}  (tip z {tip.z:+.3f})")

vc=me.color_attributes.new(name="mask",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.80,0.80,0.82,1)
for pi in mouth:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1.0,0.12,0.05,1)

sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=680; sc.render.resolution_y=680
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z-H*0.012))
r=H*0.085; cd.ortho_scale=r*2.4
for deg,tag in [(0,"front"),(45,"q45")]:
    d=Matrix.Rotation(math.radians(deg),3,Vector((0,0,1)))@fwd
    cam.location=ctr+d*r*8; cam.rotation_euler=(math.radians(90),0,math.atan2(d.y,d.x)+math.radians(90))
    sc.render.filepath=os.path.join(OUT,f"mask_{tag}.png"); bpy.ops.render.render(write_still=True)
print("done")
