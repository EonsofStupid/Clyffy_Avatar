import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
THRESH=0.11; DEPTH_F=0.050; DILATE=1

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
bpy.context.view_layer.objects.active=ob
bm=bmesh.new(); bm.from_mesh(me)
seen=set(); comps=[]
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; c=[]; seen.add(v.index)
    while st:
        cur=st.pop(); c.append(cur.index)
        for e in cur.link_edges:
            o=e.other_vert(cur)
            if o.index not in seen: seen.add(o.index); st.append(o)
    comps.append(c)
comps.sort(key=len,reverse=True)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.verts[i] for i in set(i for c in comps[1:] for i in c)],context='VERTS')
bm.to_mesh(me); bm.free()

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
def lum_at(u,v):
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2]

# MULTI-SAMPLE: corners + centre + edge midpoints -> catches a line thinner than a face
seed=set()
for p in me.polygons:
    c=p.center
    if c.z < tip.z-H*0.075 or c.z > tip.z+H*0.005: continue
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd) < H*0.03: continue
    us=[uvl[li].uv for li in p.loop_indices]
    pts=list(us)+[sum(us,Vector((0,0)))/len(us)]
    for i in range(len(us)): pts.append((us[i]+us[(i+1)%len(us)])/2)
    if any(lum_at(u.x,u.y)<THRESH for u in pts): seed.add(p.index)
print(f"seed faces (multi-sample): {len(seed)}")

bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for _ in range(DILATE):
    add=set()
    for fi in seed:
        for e in bm.faces[fi].edges:
            for f2 in e.link_faces:
                c=f2.calc_center_median()
                if c.z < tip.z-H*0.075 or c.z > tip.z+H*0.005: continue
                add.add(f2.index)
    seed |= add
print(f"after dilate x{DILATE}: {len(seed)}")

mset=set(seed); seen=set(); clusters=[]
for fi in mset:
    if fi in seen: continue
    st=[fi]; cl=[]; seen.add(fi)
    while st:
        cur=st.pop(); cl.append(cur)
        for e in bm.faces[cur].edges:
            for f2 in e.link_faces:
                if f2.index in mset and f2.index not in seen: seen.add(f2.index); st.append(f2.index)
    clusters.append(cl)
clusters.sort(key=len,reverse=True)
def span(cl):
    cs=[bm.faces[f].calc_center_median() for f in cl]
    lat=[(c-Vector((axis.x,axis.y,c.z))).cross(fwd).z for c in cs]
    return max(lat)-min(lat)
for i,cl in enumerate(clusters[:3]): print(f"  cluster {i}: {len(cl)} faces span {span(cl):.3f}")
lip=clusters[0]
if span(lip) < 0.055:
    print(f"ABORT: widest cluster spans only {span(lip):.3f}, expected >0.055 — mask still fragmented")
    sys.exit(2)
print(f"CUT -> {len(lip)} faces, span {span(lip):.3f}")

bmesh.ops.delete(bm, geom=[bm.faces[i] for i in lip], context='FACES_ONLY')
bm.edges.ensure_lookup_table()
boundary=[e for e in bm.edges if len(e.link_faces)==1]
vs=set(v for e in boundary for v in e.verts)
hole_ctr=sum((v.co for v in vs), Vector())/max(1,len(vs))
print(f"boundary edges {len(boundary)}  hole centre {tuple(round(x,3) for x in hole_ctr)}")

interior_faces=[]
cur=boundary
for dfrac,scale in [(0.45,0.90),(0.78,0.66),(1.0,0.34)]:
    ret=bmesh.ops.extrude_edge_only(bm, edges=cur)
    nv=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMVert)]
    ne=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMEdge) and len(g.link_faces)==1]
    interior_faces += [g for g in ret['geom'] if isinstance(g,bmesh.types.BMFace)]
    for v in nv:
        d=v.co-hole_ctr
        v.co = hole_ctr + d*scale - fwd*(H*DEPTH_F*dfrac)
    cur=ne
fill=bmesh.ops.holes_fill(bm, edges=cur)
interior_faces += [g for g in fill.get('faces',[])]
bm.normal_update()
interior_idx=set(f.index for f in interior_faces if f.is_valid)
print(f"cavity faces (tracked exactly): {len(interior_idx)}")
bm.to_mesh(me); bm.free()

dark=bpy.data.materials.new("clyffy_mouth_interior"); dark.use_nodes=True
b=dark.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value=(0.070,0.026,0.030,1.0); b.inputs["Roughness"].default_value=0.6
me.materials.append(dark); di=len(me.materials)-1
for i in interior_idx:
    if i < len(me.polygons): me.polygons[i].material_index=di

co=[v.co.copy() for v in me.vertices]
mouth_z=tip.z; ml=(Vector((tip.x,tip.y))-axis).length
hinge=Vector((axis.x,axis.y,mouth_z))+fwd*(ml*0.15); lat=Vector((-fwd.y,fwd.x,0))
JD=H*0.085; BU=H*0.012
def wt(c):
    dz=mouth_z-c.z
    if dz<-BU or dz>JD: return 0.0
    f=(c-hinge).dot(fwd)
    if f<=0: return 0.0
    wf=min(1.0,f/(ml*0.85))
    wv=1.0-(-dz/BU) if dz<0 else (1.0-(dz-JD*0.75)/(JD*0.25) if dz>JD*0.75 else 1.0)
    w=max(0.0,min(1.0,wf*wv)); return w*w*(3-2*w)
ws=[wt(c) for c in co]
ob.shape_key_add(name="Basis",from_mix=False); sk=ob.shape_key_add(name="jaw_open",from_mix=False)
for i,c in enumerate(co):
    if ws[i]>0: sk.data[i].co=hinge+(Matrix.Rotation(math.radians(30)*ws[i],4,lat)@(c-hinge))

sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=680; sc.render.resolution_y=680
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((hole_ctr.x,hole_ctr.y,hole_ctr.z)); R=H*0.30; cd.ortho_scale=H*0.20
a0=math.atan2(fwd.x,-fwd.y)
for off,tag in [(0,"front"),(math.radians(38),"q38")]:
    a=a0+off
    cam.location=(ctr.x+math.sin(a)*R, ctr.y-math.cos(a)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    for amt in (0.0,0.55,1.0):
        sk.value=amt
        sc.render.filepath=os.path.join(OUT,f"c_{tag}_{int(amt*100):03d}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"clyffy_mouthcut2.blend"))
print("DONE")
