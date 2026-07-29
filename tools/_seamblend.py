"""Save a .blend with the detected lip seam SELECTED, ready to orbit and judge."""
import bpy,bmesh,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
BL,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2])
bpy.ops.wm.open_mainfile(filepath=BL)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ms=[o for o in bpy.data.objects if o.type=="MESH"]; ob=ms[0]
for x in ms[1:]: bpy.data.objects.remove(x,do_unlink=True)   # drop the duplicate import
me=ob.data
SEL=set(v.index for v in me.vertices if v.select)
mat=me.materials[0]; img=None
for l in mat.node_tree.links:
    if l.to_socket.name=='Base Color' and l.from_node.type=='TEX_IMAGE': img=l.from_node.image
W,Ht=img.size; px=list(img.pixels); uvl=me.uv_layers.active.data
def lum(u,v):
    x=int(u%1.0*(W-1)); y=int(v%1.0*(Ht-1)); i=(y*W+x)*4
    return 0.2126*px[i]+0.7152*px[i+1]+0.0722*px[i+2]
vals=[]
for p in me.polygons:
    if not all(vi in SEL for vi in p.vertices): continue
    us=[uvl[li].uv for li in p.loop_indices]
    pts=list(us)+[sum(us,Vector((0,0)))/len(us)]
    for i in range(len(us)): pts.append((us[i]+us[(i+1)%len(us)])/2)
    vals.append((min(lum(q.x,q.y) for q in pts), p.index))
vals.sort()
k=max(8,len(vals)//10)
seam=set(i for _,i in vals[:k])

# clear everything, then select ONLY the seam
for v in me.vertices: v.select=False
for e in me.edges:    e.select=False
for p in me.polygons: p.select=False
for pi in seam:
    me.polygons[pi].select=True
    for vi in me.polygons[pi].vertices: me.vertices[vi].select=True
for e in me.edges:
    if all(me.vertices[v].select for v in e.vertices): e.select=True

# vertex colours too, so it reads in solid shading without entering edit mode
vc=me.color_attributes.get("seam") or me.color_attributes.new(name="seam",type='FLOAT_COLOR',domain='POINT')
for i in range(len(me.vertices)): vc.data[i].color=(0.85,0.85,0.87,1)
for i in SEL: vc.data[i].color=(0.55,0.75,0.95,1)
for pi in seam:
    for vi in me.polygons[pi].vertices: vc.data[vi].color=(1,0.05,0.02,1)

bpy.context.view_layer.objects.active=ob
ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_mode(type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"seam faces selected: {len(seam)}   saved {OUT}")
