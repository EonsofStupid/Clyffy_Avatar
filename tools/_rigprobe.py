"""Measure the cut mesh so armature bones are PLACED, not guessed."""
import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
CUT,REGION,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2])

bpy.ops.wm.open_mainfile(filepath=REGION)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
src=[o for o in bpy.data.objects if o.type=="MESH"][0]
REG=set(v.index for v in src.data.vertices if v.select)

bpy.ops.wm.open_mainfile(filepath=CUT)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
print(f"verts {len(co)}   z[{zmin:+.4f},{zmax:+.4f}]  H={H:.4f}")
print(f"WORLD space. object matrix_world translation {tuple(round(x,4) for x in ob.matrix_world.translation)}  scale {tuple(round(x,4) for x in ob.matrix_world.to_scale())}")

a=math.radians(FWD)
fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
lateral=Vector((-fwd.y,fwd.x,0.0))
print(f"fwd ({fwd.x:+.3f},{fwd.y:+.3f})  lateral ({lateral.x:+.3f},{lateral.y:+.3f})")

# cavity = the mouth we cut
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
cav=set()
if di:
    for p in me.polygons:
        if p.material_index==di[0]:
            for vi in p.vertices: cav.add(vi)
print(f"cavity verts {len(cav)}  materials {[m.name for m in me.materials]}")
def stats(name,idx):
    if not idx: print(f"{name}: EMPTY"); return
    c=[co[i] for i in idx]
    ctr=sum(c,Vector())/len(c)
    print(f"{name}: n={len(c)} centroid({ctr.x:+.4f},{ctr.y:+.4f},{ctr.z:+.4f}) "
          f"z[{min(x.z for x in c):+.4f},{max(x.z for x in c):+.4f}] "
          f"lat_span {max((x-ctr).dot(lateral) for x in c)-min((x-ctr).dot(lateral) for x in c):+.4f} "
          f"fwd_span {max((x-ctr).dot(fwd) for x in c)-min((x-ctr).dot(fwd) for x in c):+.4f}")
    return ctr
mouth=stats("cavity",cav)
reg=stats("operator region",REG)

# horizontal cross-section width by z — the NECK is the narrowest slice above the mouth
print("\n z-slice profile (width across lateral, depth along fwd, count):")
NB=28
for b in range(NB):
    lo=zmin+H*b/NB; hi=zmin+H*(b+1)/NB
    s=[c for c in co if lo<=c.z<hi]
    if not s: print(f"  z {lo:+.3f}..{hi:+.3f}  ---"); continue
    ls=[c.dot(lateral) for c in s]; fs=[c.dot(fwd) for c in s]
    mark=""
    if mouth and lo<=mouth.z<hi: mark="  <== MOUTH"
    print(f"  z {lo:+.3f}..{hi:+.3f}  lat {max(ls)-min(ls):.4f}  fwd {max(fs)-min(fs):.4f}  n={len(s)}{mark}")
