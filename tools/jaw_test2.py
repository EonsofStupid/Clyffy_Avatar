import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
bpy.context.view_layer.objects.active=ob

# strip strays
bm=bmesh.new(); bm.from_mesh(ob.data)
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
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in set(i for c in comps[1:] for i in c)], context='VERTS')
bm.to_mesh(ob.data); bm.free()

me=ob.data; co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z> zmin+H*0.70]
cx=sum(c.x for c in head)/len(head); cy=sum(c.y for c in head)/len(head)
axis=Vector((cx,cy))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fd=(Vector((tip.x,tip.y))-axis).normalized()
fwd=Vector((fd.x,fd.y,0.0)); lateral=Vector((-fwd.y,fwd.x,0.0))
muzzle_len=(Vector((tip.x,tip.y))-axis).length
mouth_z=tip.z
hinge=Vector((axis.x,axis.y,mouth_z))+fwd*(muzzle_len*0.15)

JAW_DEPTH = H*0.085          # how far below the mouth line the jaw extends
BLEND_UP  = H*0.012          # soft band above the mouth line

def weight(c):
    # hard gate: must be in the jaw band, NOT the torso
    dz = mouth_z - c.z
    if dz < -BLEND_UP or dz > JAW_DEPTH: return 0.0
    rel = c - hinge
    f = rel.dot(fwd)
    if f <= 0.0: return 0.0
    wf = min(1.0, f/(muzzle_len*0.85))              # 0 at hinge -> 1 at muzzle tip
    # vertical: full through the band, feather at both edges
    if dz < 0:      wv = 1.0 - (-dz/BLEND_UP)
    elif dz > JAW_DEPTH*0.75: wv = 1.0 - (dz-JAW_DEPTH*0.75)/(JAW_DEPTH*0.25)
    else:           wv = 1.0
    w=max(0.0,min(1.0,wf*wv))
    return w*w*(3-2*w)

ws=[weight(c) for c in co]
n=sum(1 for w in ws if w>0.01)
print(f"muzzle_len {muzzle_len:.3f} mouth_z {mouth_z:.3f} JAW_DEPTH {JAW_DEPTH:.3f}")
print(f"jaw-weighted verts: {n} / {len(co)} ({100*n/len(co):.1f}%)")

# weight visualisation as vertex colour
vc=me.color_attributes.new(name="jawW", type='FLOAT_COLOR', domain='POINT')
for i,w in enumerate(ws): vc.data[i].color=(w,0.12,1.0-w,1.0)

ob.shape_key_add(name="Basis",from_mix=False)
sk=ob.shape_key_add(name="jaw_open",from_mix=False)
ANGLE=math.radians(30)
for i,c in enumerate(co):
    if ws[i]<=0.0: continue
    sk.data[i].co = hinge + (Matrix.Rotation(ANGLE*ws[i],4,lateral) @ (c-hinge))
mx=max((sk.data[i].co-co[i]).length for i in range(len(co)))
print(f"max displacement {mx:.4f} (model height {H:.3f}) = {100*mx/H:.1f}% of height")

sc=bpy.context.scene
sc.render.engine="BLENDER_WORKBENCH"
sc.render.resolution_x=620; sc.render.resolution_y=620
sc.world=bpy.data.worlds.new("W")
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam; cd.type="ORTHO"
hc=Vector((axis.x,axis.y,mouth_z+H*0.02)); r=H*0.16; cd.ortho_scale=r*2.9
sw=Matrix.Rotation(math.radians(30),3,Vector((0,0,1)))@fwd
cam.location=hc+sw*r*8
cam.rotation_euler=(math.radians(90),0,math.atan2(sw.y,sw.x)+math.radians(90))

sh=sc.display.shading
# 1) weight map
sh.light='FLAT'; sh.color_type='VERTEX'
sk.value=0.0
sc.render.filepath=os.path.join(OUT,"w_weights.png"); bpy.ops.render.render(write_still=True)
# 2) textured sweep
sh.light='STUDIO'; sh.color_type='TEXTURE'
for amt in (0.0,0.4,0.7,1.0):
    sk.value=amt
    sc.render.filepath=os.path.join(OUT,f"o_{int(amt*100):03d}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"clyffy_jaw2.blend"))
print("done")
