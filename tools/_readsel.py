import bpy,bmesh,sys,os
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
print("objects:", [(o.name, len(o.data.vertices)) for o in meshes])
ob=max(meshes,key=lambda o:len(o.data.vertices)); me=ob.data
print("active:", ob.name, "mode:", ob.mode)
# selection persists in mesh data even after leaving edit mode
sv=[v.index for v in me.vertices if v.select]
se=[e.index for e in me.edges if e.select]
sf=[p.index for p in me.polygons if p.select]
print(f"SELECTED  verts {len(sv)}  edges {len(se)}  faces {len(sf)}   (of {len(me.vertices)}/{len(me.edges)}/{len(me.polygons)})")
if sv:
    co=[me.vertices[i].co for i in sv]
    xs=[c.x for c in co]; ys=[c.y for c in co]; zs=[c.z for c in co]
    print(f"  bbox x[{min(xs):+.3f},{max(xs):+.3f}] y[{min(ys):+.3f},{max(ys):+.3f}] z[{min(zs):+.3f},{max(zs):+.3f}]")
    ctr=sum(co,Vector())/len(co)
    print(f"  centroid ({ctr.x:+.3f},{ctr.y:+.3f},{ctr.z:+.3f})")
    allz=[v.co.z for v in me.vertices]
    H=max(allz)-min(allz)
    print(f"  height fraction: {(ctr.z-min(allz))/H*100:.0f}% up the model")
