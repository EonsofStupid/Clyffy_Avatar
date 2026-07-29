"""Isolate the bone-heat failure: mesh hygiene + which bones/meshes solve."""
import bpy, sys, os, math, bmesh
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
FWD=float(argv[0])

def load(path):
    if path.lower().endswith(".fbx"):
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=os.path.abspath(path))
    else:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    return [o for o in bpy.data.objects if o.type=="MESH"][0]

def hygiene(ob):
    bm=bmesh.new(); bm.from_mesh(ob.data)
    nonman=sum(1 for e in bm.edges if not e.is_manifold)
    bound=sum(1 for e in bm.edges if e.is_boundary)
    wire=sum(1 for e in bm.edges if e.is_wire)
    zero=sum(1 for f in bm.faces if f.calc_area()<1e-12)
    loose=sum(1 for v in bm.verts if not v.link_edges)
    # doubles
    seen={}; dup=0
    for v in bm.verts:
        k=(round(v.co.x,6),round(v.co.y,6),round(v.co.z,6))
        if k in seen: dup+=1
        seen[k]=1
    print(f"    edges {len(bm.edges)}  non-manifold {nonman}  boundary {bound}  wire {wire}  "
          f"zero-area faces {zero}  loose verts {loose}  coincident verts {dup}")
    bm.free()

def build(ob, bones, tag):
    zs=[v.co.z for v in ob.data.vertices]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
    a=math.radians(FWD)
    fwd=Vector((math.sin(a),-math.cos(a),0)).normalized(); lateral=Vector((-fwd.y,fwd.x,0.0))
    co=[v.co.copy() for v in ob.data.vertices]
    neck=zmin+0.6608*H
    head=[c for c in co if c.z>neck]; hc=sum(head,Vector())/len(head)
    mouth_z=zmin+0.6899*H
    band=[c for c in head if abs(c.z-mouth_z)<H*0.05]
    f_front=max(c.dot(fwd) for c in band); depth=f_front-min(c.dot(fwd) for c in band)
    lat0=hc.dot(lateral); head_h=zmax-neck
    hinge=fwd*(f_front-depth*0.75)+lateral*lat0+Vector((0,0,mouth_z+head_h*0.12))
    chin=Vector((hc.x,hc.y,mouth_z-head_h*0.085))
    ad=bpy.data.armatures.new("A"); arm=bpy.data.objects.new("A",ad)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT'); eb=ad.edit_bones
    made={}
    if "body" in bones:
        b=eb.new("body"); b.head=Vector((hc.x,hc.y,zmin)); b.tail=Vector((hc.x,hc.y,neck)); made["body"]=b
    if "skull" in bones:
        s=eb.new("skull"); s.head=Vector((hc.x,hc.y,neck)); s.tail=Vector((hc.x,hc.y,zmax-head_h*0.10))
        if "body" in made: s.parent=made["body"]; s.use_connect=True
        made["skull"]=s
    if "jaw" in bones:
        j=eb.new("jaw"); j.head=hinge; j.tail=chin
        if "skull" in made: j.parent=made["skull"]; j.use_connect=False
        made["jaw"]=j
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active=arm
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError as e:
        print(f"    {tag}: EXCEPTION {e}"); return
    res=[]
    for name in bones:
        g=ob.vertex_groups.get(name)
        if g is None: res.append(f"{name}=NOGROUP"); continue
        n=sum(1 for v in ob.data.vertices for gg in v.groups if gg.group==g.index and gg.weight>0.01)
        res.append(f"{name}={n}")
    print(f"    {tag}: {'  '.join(res)}")

for path,label in [("mesh/v2open/clyffy_v2_mouthopen.blend","CUT mesh (with cavity)"),
                   ("mesh/clyffy_base_neutral_v2.fbx","ORIGINAL uncut v2")]:
    print(f"\n=== {label} ===")
    ob=load(path); print(f"    verts {len(ob.data.vertices)}  faces {len(ob.data.polygons)}")
    hygiene(ob)
    for bones,tag in [(["body","skull","jaw"],"body+skull+jaw"),
                      (["body","skull"],"body+skull only"),
                      (["skull","jaw"],"skull+jaw only")]:
        ob2=load(path)
        build(ob2,bones,tag)
