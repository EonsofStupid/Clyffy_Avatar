"""Find the lip seam INSIDE the operator's hand-selected deformation region."""
import bpy,bmesh,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ms=[o for o in bpy.data.objects if o.type=="MESH"]; ob=ms[0]
for x in ms[1:]: bpy.data.objects.remove(x,do_unlink=True)
me=ob.data
SEL=set(v.index for v in me.vertices if v.select)
print(f"operator region: {len(SEL)} verts")
co=[v.co for v in me.vertices]; zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
a=math.radians(FWD); fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()

# --- 1. luminance INSIDE the region only ---
mat=me.materials[0]; img=None
for l in mat.node_tree.links:
    if l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE': img=l.from_node.image
W,Ht=img.size; px=list(img.pixels); uvl=me.uv_layers.active.data
def lum(u,v):
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2]
inreg=[p for p in me.polygons if all(vi in SEL for vi in p.vertices)]
print(f"faces fully inside region: {len(inreg)}")
vals=[]
for p in inreg:
    us=[uvl[li].uv for li in p.loop_indices]
    pts=list(us)+[sum(us,Vector((0,0)))/len(us)]
    for i in range(len(us)): pts.append((us[i]+us[(i+1)%len(us)])/2)
    vals.append((min(lum(q.x,q.y) for q in pts), p.index))
vals.sort()
print(f"luminance in-region: darkest {vals[0][0]:.4f}  median {vals[len(vals)//2][0]:.4f}  brightest {vals[-1][0]:.4f}")
# take the darkest decile as the seam
k=max(8,len(vals)//10)
seam=set(i for _,i in vals[:k])
print(f"seam candidate (darkest {k} faces): {len(seam)}")

# --- 2. sharpest creases inside the region, for cross-check ---
bm=bmesh.new(); bm.from_mesh(me); bm.edges.ensure_lookup_table()
sharp=[]
for e in bm.edges:
    if len(e.link_faces)!=2: continue
    if not all(v.index in SEL for v in e.verts): continue
    sharp.append((math.degrees(e.calc_face_angle(0.0)), e.index))
sharp.sort(reverse=True)
print(f"in-region edges: {len(sharp)}   sharpest {sharp[0][0]:.1f} deg   median {sharp[len(sharp)//2][0]:.1f} deg")
bm.free()

vc=me.color_attributes.get("lip") or me.color_attributes.new(name="lip",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.88,0.88,0.90,1)
for i in SEL: vc.data[i].color=(0.55,0.75,0.95,1)          # operator region = blue
for pi in seam:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1,0.05,0.02,1)   # seam = red

sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W3")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='VERTEX'
sc.render.resolution_x=600; sc.render.resolution_y=600
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30
ctr=sum((me.vertices[i].co for i in SEL),Vector())/len(SEL); R=H*5
for off,tag in [(0,"front"),(math.radians(55),"q55")]:
    ang=a+off; cd.ortho_scale=H*0.33
    cam.location=(ctr.x+math.sin(ang)*R, ctr.y-math.cos(ang)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"lip_{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
