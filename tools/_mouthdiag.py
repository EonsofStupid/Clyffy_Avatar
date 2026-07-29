import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
me=ob.data
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
cx=sum(c.x for c in head)/len(head); cy=sum(c.y for c in head)/len(head)
axis=Vector((cx,cy))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fd=(Vector((tip.x,tip.y))-axis).normalized(); fwd=Vector((fd.x,fd.y,0))
print(f"muzzle tip {tuple(round(v,3) for v in tip)}")

# curvature probe: for verts near the muzzle front, report sharp dihedral angles
bm=bmesh.new(); bm.from_mesh(me); bm.edges.ensure_lookup_table()
sharp=[]
for e in bm.edges:
    if len(e.link_faces)!=2: continue
    mid=(e.verts[0].co+e.verts[1].co)/2
    if mid.z < tip.z-H*0.09 or mid.z > tip.z+H*0.05: continue
    if (mid-Vector((axis.x,axis.y,mid.z))).dot(fwd) < 0: continue
    a=e.calc_face_angle(0.0)
    if a > math.radians(38): sharp.append((math.degrees(a), mid.copy()))
sharp.sort(reverse=True)
print(f"sharp edges (>38 deg) in mouth band: {len(sharp)}")
for a,m in sharp[:6]: print(f"   {a:5.1f} deg at {tuple(round(v,3) for v in m)}")
bm.free()

sc=bpy.context.scene
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.render.resolution_x=640; sc.render.resolution_y=640
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam; cd.type="ORTHO"
ctr=Vector((tip.x,tip.y,tip.z))*0.5 + Vector((axis.x,axis.y,tip.z))*0.5
r=H*0.11; cd.ortho_scale=r*2.6
def shot(name, deg, mode):
    sh=sc.display.shading
    if mode=="tex": sh.light='STUDIO'; sh.color_type='TEXTURE'
    else:           sh.light='STUDIO'; sh.color_type='SINGLE'; sh.single_color=(0.72,0.72,0.75); sh.studio_light='basic.sl'
    a=math.radians(deg)
    d=Matrix.Rotation(a,3,Vector((0,0,1)))@fwd
    cam.location=ctr+d*r*7; cam.rotation_euler=(math.radians(90),0,math.atan2(d.y,d.x)+math.radians(90))
    sc.render.filepath=os.path.join(OUT,name); bpy.ops.render.render(write_still=True)
for deg,tag in [(0,"front"),(35,"q35"),(70,"side")]:
    shot(f"m_{tag}_tex.png",deg,"tex")
    shot(f"m_{tag}_solid.png",deg,"solid")
print("done")
