"""Jaw driven by the OPERATOR's hand-selected region, not a computed band."""
import bpy,sys,os,math,json
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
CUT,REGION,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),os.path.abspath(argv[2]),float(argv[3])
ANGDEG=float(argv[4]) if len(argv)>4 else 30.0
os.makedirs(OUT,exist_ok=True)

# 1. read the operator's jaw region from his ORIGINAL selection file
bpy.ops.wm.open_mainfile(filepath=REGION)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
src=[o for o in bpy.data.objects if o.type=="MESH"][0]
REG=set(v.index for v in src.data.vertices if v.select)
print(f"operator jaw region: {len(REG)} verts (from {os.path.basename(REGION)})")

# 2. open the cut mesh — FACES_ONLY delete preserves original vert indices
bpy.ops.wm.open_mainfile(filepath=CUT)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]; zs=[c.z for c in co]
zmin,zmax=min(zs),max(zs); H=zmax-zmin
print(f"cut mesh: {len(co)} verts (region indices valid: {max(REG) < len(co)})")

a=math.radians(FWD)
fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
lateral=Vector((-fwd.y,fwd.x,0.0))

# cavity verts (dark material) mark the mouth; include them so the interior moves too
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")]
cav=set()
if di:
    for p in me.polygons:
        if p.material_index==di[0]:
            for vi in p.vertices: cav.add(vi)
JAW = REG | cav
# SYMMETRISE: the hand-clicked region is lopsided; mirror it across the known midline
head=[c for c in co if c.z>zmin+H*0.70]
hc=Vector((sum(c.x for c in head)/len(head), sum(c.y for c in head)/len(head), 0))
def mirror(c):
    rel=Vector((c.x-hc.x, c.y-hc.y, 0.0))
    d=rel.dot(lateral)
    m=Vector((c.x,c.y,c.z)) - lateral*(2*d)
    return m
CELL=H*0.010
grid={}
for i,c in enumerate(co):
    grid.setdefault((round(c.x/CELL),round(c.y/CELL),round(c.z/CELL)), []).append(i)
added=0
for i in list(JAW):
    m=mirror(co[i])
    for dk in ((0,0,0),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
        key=(round(m.x/CELL)+dk[0], round(m.y/CELL)+dk[1], round(m.z/CELL)+dk[2])
        for j in grid.get(key,[]):
            if j not in JAW and (co[j]-m).length < CELL*1.5:
                JAW.add(j); added+=1
print(f"jaw set = operator region + cavity = {len(JAW)-added} -> symmetrised +{added} = {len(JAW)} verts")

# hinge: BEHIND the jaw set, at its top — the pivot the lower jaw swings from
jc=[co[i] for i in JAW]
top_z=max(c.z for c in jc)
back = min(jc, key=lambda c:(c-Vector((0,0,c.z))).dot(fwd))
hinge=Vector((sum(c.x for c in jc)/len(jc), sum(c.y for c in jc)/len(jc), top_z))
hinge -= fwd*( (max((c-hinge).dot(fwd) for c in jc)) * 0.15 )
print(f"hinge ({hinge.x:+.3f},{hinge.y:+.3f},{hinge.z:+.3f})  top_z {top_z:+.3f}")

# weight: 0 at the hinge, 1 at the far end — so it ROTATES rather than translating
fmax=max((c-hinge).dot(fwd) for c in jc) or 1.0
ws=[0.0]*len(co)
for i in JAW:
    f=(co[i]-hinge).dot(fwd)
    t=max(0.0,min(1.0,f/fmax))
    ws[i]=t*t*(3-2*t)
n=sum(1 for w in ws if w>0.01)
# symmetry check across the mid-plane
ctrx=sum(c.x for c in jc)/len(jc); ctry=sum(c.y for c in jc)/len(jc)
P=[i for i in JAW if (co[i]-Vector((ctrx,ctry,co[i].z))).dot(lateral)>0]
M=[i for i in JAW if (co[i]-Vector((ctrx,ctry,co[i].z))).dot(lateral)<0]
print(f"weighted {n}   symmetry: +side {len(P)} (mean w {sum(ws[i] for i in P)/max(1,len(P)):.3f})  "
      f"-side {len(M)} (mean w {sum(ws[i] for i in M)/max(1,len(M)):.3f})")

ob.shape_key_add(name="Basis",from_mix=False)
sk=ob.shape_key_add(name="jaw_open",from_mix=False)
ANG=math.radians(ANGDEG)
for i in range(len(co)):
    if ws[i]>0: sk.data[i].co=hinge+(Matrix.Rotation(ANG*ws[i],4,lateral)@(co[i]-hinge))
mx=max((sk.data[i].co-co[i]).length for i in range(len(co)))
print(f"max displacement {mx:.4f} = {100*mx/H:.1f}% of height  @ {ANGDEG:.0f} deg")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"clyffy_v2_jaw3.blend"))

sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=600; sc.render.resolution_y=600
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd); sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=H*0.32
mc=sum(jc,Vector())/len(jc); R2=H*5
for off,tag in [(0,"front"),(math.radians(50),"q50")]:
    ang=a+off
    cam.location=(mc.x+math.sin(ang)*R2, mc.y-math.cos(ang)*R2, mc.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    for amt in (0.0,0.5,1.0):
        sk.value=amt
        sc.render.filepath=os.path.join(OUT,f"j_{tag}_{int(amt*100):03d}.png"); bpy.ops.render.render(write_still=True)
print("ok")
