"""Cut the mouth open and build a shallow cavity. Non-destructive to the source FBX."""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
THRESH=0.09; DEPTH_F=0.055     # cavity depth as fraction of model height

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
bpy.context.view_layer.objects.active=ob

# ---- strip strays ----
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

# ---- frame ----
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head), sum(c.y for c in head)/len(head)))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fn=(Vector((tip.x,tip.y))-axis).normalized(); fwd=Vector((fn.x,fn.y,0))

# ---- mouth mask from texture ----
mat=me.materials[0]; img=None
for l in mat.node_tree.links:
    if l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE': img=l.from_node.image
W,Ht=img.size; px=list(img.pixels); uvl=me.uv_layers.active.data
mouth=set()
for p in me.polygons:
    c=p.center
    if c.z < tip.z-H*0.09 or c.z > tip.z+H*0.02: continue
    if (c-Vector((axis.x,axis.y,c.z))).dot(fwd) < H*0.03: continue
    us=[uvl[li].uv for li in p.loop_indices]
    u=sum(x.x for x in us)/len(us); v=sum(x.y for x in us)/len(us)
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    if 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2] < THRESH: mouth.add(p.index)
print(f"mouth candidate faces: {len(mouth)}")

# ---- keep only the largest edge-connected cluster (the lip line, not the tongue blob) ----
bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
mset=set(mouth); seen=set(); clusters=[]
for fi in mset:
    if fi in seen: continue
    st=[fi]; cl=[]; seen.add(fi)
    while st:
        cur=st.pop(); cl.append(cur)
        for e in bm.faces[cur].edges:
            for f2 in e.link_faces:
                if f2.index in mset and f2.index not in seen:
                    seen.add(f2.index); st.append(f2.index)
    clusters.append(cl)
clusters.sort(key=len,reverse=True)
for i,cl in enumerate(clusters[:4]):
    cs=[bm.faces[f].calc_center_median() for f in cl]
    lat=[(c-Vector((axis.x,axis.y,c.z))).cross(fwd).z for c in cs]
    print(f"  cluster {i}: {len(cl):3d} faces  lateral span {max(lat)-min(lat):.3f}  z {min(c.z for c in cs):+.3f}..{max(c.z for c in cs):+.3f}")
lip=clusters[0]
print(f"CUT cluster 0 -> {len(lip)} faces")

# ---- delete the lip faces => hole ----
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in lip], context='FACES_ONLY')
bm.edges.ensure_lookup_table()
boundary=[e for e in bm.edges if len(e.link_faces)==1]
print(f"boundary edges after cut: {len(boundary)}")

# ---- extrude the hole inward to form a cavity ----
inward = -fwd
rings=[(0.45,0.92),(0.75,0.72),(1.0,0.40)]   # (depth frac, scale)
cur_edges=boundary
hole_ctr=Vector((0,0,0))
vs=set(v for e in boundary for v in e.verts)
for v in vs: hole_ctr+=v.co
hole_ctr/=max(1,len(vs))
for dfrac,scale in rings:
    ret=bmesh.ops.extrude_edge_only(bm, edges=cur_edges)
    new_v=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMVert)]
    new_e=[g for g in ret['geom'] if isinstance(g,bmesh.types.BMEdge) and len(g.link_faces)==1]
    for v in new_v:
        d=v.co-hole_ctr
        v.co = hole_ctr + Vector((d.x*scale, d.y*scale, d.z*scale)) + inward*(H*DEPTH_F*dfrac)
    cur_edges=new_e
bmesh.ops.holes_fill(bm, edges=cur_edges)
bm.normal_update()
print(f"cavity built: {len(bm.faces)} faces total")

# ---- tag the interior faces so we can give them a dark material ----
interior=[f for f in bm.faces if (f.calc_center_median()-hole_ctr).dot(inward) > H*0.004]
print(f"interior faces tagged: {len(interior)}")
bm.to_mesh(me); bm.free()

dark=bpy.data.materials.new("clyffy_mouth_interior")
dark.use_nodes=True
bsdf=dark.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value=(0.075,0.028,0.032,1.0)
bsdf.inputs["Roughness"].default_value=0.62
me.materials.append(dark); dark_idx=len(me.materials)-1
hc=hole_ctr
for p in me.polygons:
    if (p.center-hc).dot(inward) > H*0.004 and (p.center-hc).length < H*0.10:
        p.material_index=dark_idx

# ---- jaw shape key (reusing the validated weighting) ----
co=[v.co.copy() for v in me.vertices]
mouth_z=tip.z; muzzle_len=(Vector((tip.x,tip.y))-axis).length
hinge=Vector((axis.x,axis.y,mouth_z))+fwd*(muzzle_len*0.15)
lateral=Vector((-fwd.y,fwd.x,0.0))
JAW_DEPTH=H*0.085; BLEND_UP=H*0.012
def weight(c):
    dz=mouth_z-c.z
    if dz<-BLEND_UP or dz>JAW_DEPTH: return 0.0
    f=(c-hinge).dot(fwd)
    if f<=0: return 0.0
    wf=min(1.0,f/(muzzle_len*0.85))
    if dz<0: wv=1.0-(-dz/BLEND_UP)
    elif dz>JAW_DEPTH*0.75: wv=1.0-(dz-JAW_DEPTH*0.75)/(JAW_DEPTH*0.25)
    else: wv=1.0
    w=max(0.0,min(1.0,wf*wv)); return w*w*(3-2*w)
ws=[weight(c) for c in co]
ob.shape_key_add(name="Basis",from_mix=False)
sk=ob.shape_key_add(name="jaw_open",from_mix=False)
ANG=math.radians(30)
for i,c in enumerate(co):
    if ws[i]<=0: continue
    sk.data[i].co=hinge+(Matrix.Rotation(ANG*ws[i],4,lateral)@(c-hinge))
print(f"jaw weighted {sum(1 for w in ws if w>0.01)} verts")

# ---- render ----
sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=680; sc.render.resolution_y=680
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z))-fwd*(H*0.030); R=H*0.30; cd.ortho_scale=H*0.26
a0=math.atan2(fwd.x,-fwd.y)
for off,tag in [(0,"front"),(math.radians(40),"q40")]:
    a=a0+off
    cam.location=(ctr.x+math.sin(a)*R, ctr.y-math.cos(a)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    for amt in (0.0,0.55,1.0):
        sk.value=amt
        sc.render.filepath=os.path.join(OUT,f"cut_{tag}_{int(amt*100):03d}.png")
        bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"clyffy_mouthcut.blend"))
print("DONE")
