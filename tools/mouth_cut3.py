"""Cut the mouth open on v2. Forward axis is SUPPLIED, never derived.

    blender --background --python tools/mouth_cut3.py -- <mesh> <out> <fwd_deg> [thresh]
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
FWD_DEG=float(argv[2]); THRESH=float(argv[3]) if len(argv)>3 else 0.11
DEPTH_F=0.050; DILATE=1

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=max([o for o in bpy.data.objects if o.type=="MESH"],key=lambda o:len(o.data.vertices))
bpy.context.view_layer.objects.active=ob; me=ob.data

co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head), sum(c.y for c in head)/len(head)))

# ---- FORWARD AXIS FROM THE MANIFEST (camera convention: loc = ctr + (sin a, -cos a)*R)
a=math.radians(FWD_DEG)
fwd=Vector((math.sin(a), -math.cos(a), 0.0)).normalized()
lateral=Vector((-fwd.y, fwd.x, 0.0))
print(f"forward axis SUPPLIED {FWD_DEG} deg -> ({fwd.x:+.3f},{fwd.y:+.3f})")

# muzzle tip measured ALONG the supplied axis, in a narrow lateral band
band=[c for c in head if abs((c-Vector((axis.x,axis.y,c.z))).dot(lateral)) < H*0.05]
tip=max(band, key=lambda c:(c-Vector((axis.x,axis.y,c.z))).dot(fwd))
print(f"muzzle tip {tuple(round(v,3) for v in tip)}  (from {len(band)} narrow-band verts)")

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
    if c.z < tip.z-H*0.075 or c.z > tip.z+H*0.005: continue
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd) < H*0.03: continue
    us=[uvl[li].uv for li in p.loop_indices]
    pts=list(us)+[sum(us,Vector((0,0)))/len(us)]
    for i in range(len(us)): pts.append((us[i]+us[(i+1)%len(us)])/2)
    if any(lum(q.x,q.y)<THRESH for q in pts): seed.add(p.index)
print(f"seed faces: {len(seed)}")

bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for _ in range(DILATE):
    add=set()
    for fi in seed:
        for e in bm.faces[fi].edges:
            for f2 in e.link_faces:
                c=f2.calc_center_median()
                if tip.z-H*0.075 <= c.z <= tip.z+H*0.005: add.add(f2.index)
    seed|=add
print(f"after dilate: {len(seed)}")

mset=set(seed); seen=set(); cl=[]
for fi in mset:
    if fi in seen: continue
    st=[fi]; c2=[]; seen.add(fi)
    while st:
        cur=st.pop(); c2.append(cur)
        for e in bm.faces[cur].edges:
            for f2 in e.link_faces:
                if f2.index in mset and f2.index not in seen: seen.add(f2.index); st.append(f2.index)
    cl.append(c2)
cl.sort(key=len,reverse=True)
def span(c):
    cs=[bm.faces[f].calc_center_median() for f in c]
    lat=[(x-Vector((axis.x,axis.y,x.z))).cross(fwd).z for x in cs]
    return max(lat)-min(lat)
for i,c in enumerate(cl[:3]): print(f"  cluster {i}: {len(c)} faces span {span(c):.3f}")
lip=cl[0]; print(f"CUT -> {len(lip)} faces, span {span(lip):.3f}")
bm.free()

# ---- render the MASK first so a bad selection is visible, not silent ----
vc=me.color_attributes.new(name="mask",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.82,0.82,0.84,1)
for pi in lip:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1.0,0.10,0.04,1)

sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.render.resolution_x=640; sc.render.resolution_y=640
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z))-fwd*(H*0.03); R=H*3.0; cd.ortho_scale=H*0.22
cd.clip_start=0.01; cd.clip_end=H*10
def shot(name, off, mode):
    sh=sc.display.shading
    if mode=="mask": sh.light='FLAT'; sh.color_type='VERTEX'
    else:            sh.light='STUDIO'; sh.color_type='TEXTURE'
    ang=math.radians(FWD_DEG)+off
    cam.location=(ctr.x+math.sin(ang)*R, ctr.y-math.cos(ang)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,name); bpy.ops.render.render(write_still=True)
shot("mask_front.png",0,"mask"); shot("mask_q40.png",math.radians(40),"mask")
print("mask rendered")
