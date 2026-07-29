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
fwd=Vector(((Vector((tip.x,tip.y))-axis).normalized().x,(Vector((tip.x,tip.y))-axis).normalized().y,0))

bm=bmesh.new(); bm.from_mesh(me)
bm.edges.ensure_lookup_table(); bm.verts.ensure_lookup_table()
# candidate crease edges anywhere on the muzzle
cand=set()
for e in bm.edges:
    if len(e.link_faces)!=2: continue
    mid=(e.verts[0].co+e.verts[1].co)/2
    if mid.z < tip.z-H*0.11 or mid.z > tip.z+H*0.10: continue
    if (mid-Vector((axis.x,axis.y,mid.z))).dot(fwd) < H*0.02: continue
    if e.calc_face_angle(0.0) > math.radians(34): cand.add(e.index)
print(f"candidate crease edges: {len(cand)}")

# cluster into connected chains
seen=set(); chains=[]
for ei in cand:
    if ei in seen: continue
    stack=[ei]; ch=[]; seen.add(ei)
    while stack:
        cur=stack.pop(); ch.append(cur)
        for v in bm.edges[cur].verts:
            for e2 in v.link_edges:
                if e2.index in cand and e2.index not in seen:
                    seen.add(e2.index); stack.append(e2.index)
    chains.append(ch)
chains.sort(key=len,reverse=True)
print(f"chains: {len(chains)}")
cols=[(1,0.15,0.1),(0.1,0.9,0.3),(0.2,0.4,1.0),(1,0.85,0.1),(1,0.3,0.9),(0.1,0.9,0.9)]
vc=me.color_attributes.new(name="seam",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.80,0.80,0.82,1)
for ci,ch in enumerate(chains[:6]):
    vs=[v.co for ei in ch for v in bm.edges[ei].verts]
    zc=sum(v.z for v in vs)/len(vs)
    lat=[ (v - Vector((axis.x,axis.y,v.z))).cross(fwd).z for v in vs ]
    span=max(lat)-min(lat)
    fext=[ (v - Vector((axis.x,axis.y,v.z))).dot(fwd) for v in vs ]
    print(f"  chain {ci}: {len(ch):4d} edges  z~{zc:+.3f} (tip {tip.z:+.3f}, d={zc-tip.z:+.3f})  lateral span {span:.3f}  fwd {min(fext):+.3f}..{max(fext):+.3f}  COLOUR {['red','green','blue','yellow','magenta','cyan'][ci]}")
    for ei in ch:
        for v in bm.edges[ei].verts: vc.data[v.index].color=(*cols[ci],1)
bm.free()

sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=680; sc.render.resolution_y=680
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z))*0.55+Vector((axis.x,axis.y,tip.z))*0.45
r=H*0.115; cd.ortho_scale=r*2.7
for deg,tag in [(0,"front"),(40,"q40")]:
    d=Matrix.Rotation(math.radians(deg),3,Vector((0,0,1)))@fwd
    cam.location=ctr+d*r*7; cam.rotation_euler=(math.radians(90),0,math.atan2(d.y,d.x)+math.radians(90))
    sc.render.filepath=os.path.join(OUT,f"seam_{tag}.png"); bpy.ops.render.render(write_still=True)
