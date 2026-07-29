import bpy,sys,os,math
import numpy as np
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
sel=[v.co for v in me.vertices if v.select]
print(f"region verts: {len(sel)}")
P=np.array([[c.x,c.y] for c in sel]); P-=P.mean(axis=0)
u,s,vt=np.linalg.svd(P, full_matrices=False)
major=vt[0]; minor=vt[1]
print(f"principal spread: major {s[0]:.4f}  minor {s[1]:.4f}   ratio {s[0]/max(s[1],1e-9):.2f}")
print(f"major axis (=LATERAL, ear-to-ear): ({major[0]:+.3f},{major[1]:+.3f})")
# forward = perpendicular to lateral; disambiguate by which way the muzzle protrudes
allco=np.array([[v.co.x,v.co.y,v.co.z] for v in me.vertices])
zmin,zmax=allco[:,2].min(),allco[:,2].max(); H=zmax-zmin
head=allco[allco[:,2]>zmin+H*0.70]
hc=head[:,:2].mean(axis=0)
for sign in (1,-1):
    f=minor*sign
    ext=((head[:,:2]-hc)@f).max()
    print(f"  candidate fwd ({f[0]:+.3f},{f[1]:+.3f})  head protrusion {ext:+.4f}")
best=max((1,-1), key=lambda sg: ((head[:,:2]-hc)@(minor*sg)).max())
fwd=minor*best
ang=math.degrees(math.atan2(fwd[0],-fwd[1]))%360
print(f"\nMEASURED FORWARD AXIS = {ang:.1f} deg   (manifest says 225.0)")
print(f"  error vs manifest: {abs((ang-225+180)%360-180):.1f} deg")
