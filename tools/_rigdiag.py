"""Why did bone heat fail? Test whether the bone endpoints are INSIDE the mesh volume."""
import bpy, sys, os, math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
CUT,FWD=os.path.abspath(argv[0]),float(argv[1])
bpy.ops.wm.open_mainfile(filepath=CUT)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
a=math.radians(FWD)
fwd=Vector((math.sin(a),-math.cos(a),0)).normalized(); lateral=Vector((-fwd.y,fwd.x,0.0))
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
cav=set()
for p in me.polygons:
    if di and p.material_index==di[0]:
        for vi in p.vertices: cav.add(vi)
mouth=sum((co[i] for i in cav),Vector())/len(cav)

def inside(p):
    """parity test: cast rays in 6 directions, majority-vote on odd hit counts"""
    votes=0
    for d in (Vector((1,0,0)),Vector((-1,0,0)),Vector((0,1,0)),Vector((0,-1,0)),Vector((0,0,1)),Vector((0,0,-1))):
        n=0; org=p.copy()
        for _ in range(32):
            hit,loc,nor,idx=ob.ray_cast(org,d,distance=H*4)
            if not hit: break
            n+=1; org=loc+d*1e-5
        votes+= (n%2)
    return votes, votes>=4

head=[c for c in co if c.z>0.159]
hc=sum(head,Vector())/len(head)
band=[c for c in head if abs(c.z-mouth.z)<H*0.05]
f_front=max(c.dot(fwd) for c in band); f_back=min(c.dot(fwd) for c in band)
depth=f_front-f_back; lat0=hc.dot(lateral); head_h=zmax-0.159
print(f"head centroid ({hc.x:+.4f},{hc.y:+.4f},{hc.z:+.4f})  lat0 {lat0:+.4f}")
print(f"mouth ({mouth.x:+.4f},{mouth.y:+.4f},{mouth.z:+.4f})  fwd pos {mouth.dot(fwd):+.4f}")
print(f"at mouth band: fwd front {f_front:+.4f} back {f_back:+.4f} depth {depth:.4f}")
print(f"lateral extent at mouth band: [{min(c.dot(lateral) for c in band):+.4f},{max(c.dot(lateral) for c in band):+.4f}]\n")

print("INSIDE TEST (votes/6, need >=4):")
for name,frac_back,up in [("hinge HINGE_BACK=0.75",0.75,0.12),("hinge 0.60",0.60,0.12),
                          ("hinge 0.45",0.45,0.12),("hinge 0.35",0.35,0.12),
                          ("hinge 0.45 up0.05",0.45,0.05),("hinge 0.45 up0.20",0.45,0.20)]:
    p=fwd*(f_front-depth*frac_back)+lateral*lat0+Vector((0,0,mouth.z+head_h*up))
    v,ins=inside(p)
    print(f"  {name:26s} ({p.x:+.4f},{p.y:+.4f},{p.z:+.4f})  votes {v}/6  {'INSIDE' if ins else '** OUTSIDE **'}")
for name,p in [("mouth centre",mouth),("head centroid",hc),("chin-ish",Vector((hc.x,hc.y,0.1975)))]:
    v,ins=inside(p)
    print(f"  {name:26s} ({p.x:+.4f},{p.y:+.4f},{p.z:+.4f})  votes {v}/6  {'INSIDE' if ins else '** OUTSIDE **'}")
