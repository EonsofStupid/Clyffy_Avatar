import bpy, sys, os, math
import numpy as np
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
for path in argv:
    p=os.path.abspath(path)
    if p.lower().endswith(".fbx"):
        bpy.ops.wm.read_homefile(use_empty=True); bpy.ops.import_scene.fbx(filepath=p)
    else:
        bpy.ops.wm.open_mainfile(filepath=p)
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
    mw=ob.matrix_world
    e=mw.to_euler()
    print(f"\n=== {os.path.basename(p)} : object '{ob.name}' ===")
    print(f"  loc {tuple(round(x,4) for x in mw.translation)}  "
          f"rot_euler_deg ({math.degrees(e.x):+.2f}, {math.degrees(e.y):+.2f}, {math.degrees(e.z):+.2f})  "
          f"scale {tuple(round(x,4) for x in mw.to_scale())}")
    N=len(ob.data.vertices)
    L=np.empty((N,3)); ob.data.vertices.foreach_get("co", L.ravel())
    W=np.array([mw @ Vector(c) for c in L[::37]])
    Ls=L[::37]
    for tag,V in (("LOCAL v.co",Ls),("WORLD  mw@co",W)):
        zmin,zmax=V[:,2].min(),V[:,2].max()
        print(f"  {tag}: x[{V[:,0].min():+.4f},{V[:,0].max():+.4f}] "
              f"y[{V[:,1].min():+.4f},{V[:,1].max():+.4f}] z[{zmin:+.4f},{zmax:+.4f}]")
    # where does the mouth cavity sit in each space?
    me=ob.data
    di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
    if di:
        cav=sorted({vi for pp in me.polygons if pp.material_index==di[0] for vi in pp.vertices})
        lc=L[cav].mean(axis=0)
        wc=np.array(mw @ Vector(lc))
        hl=L[L[:,2]>0.159].mean(axis=0)
        hw=np.array(mw @ Vector(hl))
        for tag,m,h in (("LOCAL",lc,hl),("WORLD",wc,hw)):
            d=m-h; a=math.degrees(math.atan2(d[0], -d[1]))%360
            print(f"  {tag}: head centre->mouth offset ({d[0]:+.4f},{d[1]:+.4f}) => forward axis {a:.1f} deg")
