"""How much room is there inside the cavity, and where exactly?"""
import bpy, sys, os, math
import numpy as np
argv=sys.argv[sys.argv.index("--")+1:]
SRC,FWD=os.path.abspath(argv[0]),float(argv[1])
bpy.ops.wm.open_mainfile(filepath=SRC)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
N=len(me.vertices); co=np.empty((N,3)); me.vertices.foreach_get("co",co.ravel())
zmin,zmax=co[:,2].min(),co[:,2].max(); H=zmax-zmin
a=math.radians(FWD); fwd=np.array([math.sin(a),-math.cos(a),0.0]); lat=np.array([-fwd[1],fwd[0],0.0])
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cavf=[p for p in me.polygons if p.material_index==di]
cav=sorted({v for p in cavf for v in p.vertices})
surf={v for p in me.polygons if p.material_index!=di for v in p.vertices}
rim=np.array(sorted(set(cav)&surf)); inner=np.array(sorted(set(cav)-surf))
C=co[cav].mean(axis=0)
hc=co[co[:,2]>0.208].mean(axis=0); lat0=float(hc@lat)
print(f"cavity: {len(cavf)} faces, {len(cav)} verts   rim {len(rim)}  interior {len(inner)}")
print(f"cavity centre ({C[0]:+.4f},{C[1]:+.4f},{C[2]:+.4f})")
for nm,ix in (("rim",rim),("interior",inner)):
    P=co[ix]
    print(f"  {nm:9s} fwd [{(P@fwd).min():+.4f},{(P@fwd).max():+.4f}]  "
          f"lat [{(P@lat).min()-lat0:+.4f},{(P@lat).max()-lat0:+.4f}]  z [{P[:,2].min():+.4f},{P[:,2].max():+.4f}]")
print(f"\ncavity DEPTH along fwd: {(co[rim]@fwd).max()-(co[inner]@fwd).min():.4f}")
print(f"cavity WIDTH across lat: {(co[rim]@lat).max()-(co[rim]@lat).min():.4f}")
print(f"lip slit height at rest: {co[rim][:,2].max()-co[rim][:,2].min():.4f}")
print(f"aperture at 22 deg (from manifest): 0.0549")
gi={g.name:g.index for g in ob.vertex_groups}
print(f"\nvertex groups present: {list(gi)}")
# connected components
import bmesh
bm=bmesh.new(); bm.from_mesh(me)
seen=set(); comps=[]
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; c=0
    while st:
        x=st.pop()
        if x.index in seen: continue
        seen.add(x.index); c+=1
        for e in x.link_edges: st.append(e.other_vert(x))
    comps.append(c)
comps.sort(reverse=True)
print(f"components: {comps[:6]}")
bm.free()
