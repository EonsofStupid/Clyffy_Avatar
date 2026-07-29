"""Classify the high-stretch edges precisely: what connects these two verts?"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
RIG,FWD,ANGDEG=os.path.abspath(argv[0]),float(argv[1]),float(argv[2])
bpy.ops.wm.open_mainfile(filepath=RIG)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
arm=[o for o in bpy.data.objects if o.type=="ARMATURE"][0]
me=ob.data; N=len(me.vertices)
co=np.empty((N,3)); me.vertices.foreach_get("co",co.ravel())
a=math.radians(FWD); fwd=np.array([math.sin(a),-math.cos(a),0.0]); lat=np.array([-fwd[1],fwd[0],0.0])
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cavf={p.index for p in me.polygons if p.material_index==di}
cav={v for p in me.polygons if p.material_index==di for v in p.vertices}
surf={v for p in me.polygons if p.material_index!=di for v in p.vertices}
rim=cav&surf
src=np.array([d.value for d in me.attributes["cav_src"].data],dtype=np.int64)
gj=ob.vertex_groups["jaw"].index
w=np.zeros(N)
for v in me.vertices:
    for g in v.groups:
        if g.group==gj: w[v.index]=g.weight
# edge -> incident face materials
ef={}
for p in me.polygons:
    vs=list(p.vertices)
    for k in range(len(vs)):
        i,j=vs[k],vs[(k+1)%len(vs)]
        ef.setdefault((min(i,j),max(i,j)),[]).append('cav' if p.material_index==di else 'surf')
jb=arm.pose.bones["jaw"]; hv=Vector(jb.bone.head_local); lv=Vector(lat)
R=Matrix.Translation(hv)@Matrix.Rotation(math.radians(ANGDEG),4,lv)@Matrix.Translation(-hv)
jb.matrix=R@jb.bone.matrix_local; bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get(); obe=ob.evaluated_get(dg); ev=obe.to_mesh()
d=np.empty((N,3)); ev.vertices.foreach_get("co",d.ravel()); obe.to_mesh_clear()
E=np.array([[e.vertices[0],e.vertices[1]] for e in me.edges],dtype=np.int64)
L0=np.linalg.norm(co[E[:,0]]-co[E[:,1]],axis=1); L1=np.linalg.norm(d[E[:,0]]-d[E[:,1]],axis=1)
ratio=np.where(L0>1e-9,L1/np.maximum(L0,1e-12),1.0)
ctr=float(co[co[:,2]>0.2257].mean(axis=0)@lat)
print(f"{'ratio':>7} {'rest':>8} {'w0':>5} {'w1':>5} {'dw':>5}  {'faces':>12}  v0/v1 kind          lat0     lat1     z")
for k in np.argsort(-ratio)[:20]:
    i,j=int(E[k,0]),int(E[k,1])
    key=(min(i,j),max(i,j)); mats=ef.get(key,[])
    def kind(x): return ("BAGIN" if src[x]>=0 else ("RIM" if x in rim else "SKIN"))
    print(f"{ratio[k]:7.2f} {L0[k]:8.5f} {w[i]:5.2f} {w[j]:5.2f} {abs(w[i]-w[j]):5.2f}  {'+'.join(sorted(set(mats))):>12}  "
          f"{kind(i):5}/{kind(j):5}  {co[i]@lat-ctr:+.4f} {co[j]@lat-ctr:+.4f}  {(co[i,2]+co[j,2])/2:+.4f}")
big=[k for k in range(len(E)) if abs(w[E[k,0]]-w[E[k,1]])>0.5]
print(f"\nedges with |w0-w1| > 0.5 : {len(big)}   (these are what tears)")
from collections import Counter
c=Counter()
for k in big:
    i,j=int(E[k,0]),int(E[k,1])
    def kind(x): return ("BAGIN" if src[x]>=0 else ("RIM" if x in rim else "SKIN"))
    c["/".join(sorted([kind(i),kind(j)]))]+=1
for k,v in c.most_common(): print(f"   {k:14s} {v}")
