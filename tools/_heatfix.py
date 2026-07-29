"""Can cleanup rescue bone heat? And is scipy available for a real diffusion solve?"""
import bpy, sys, os, math, bmesh
from mathutils import Vector
try:
    import scipy, numpy
    print(f"scipy {scipy.__version__}  numpy {numpy.__version__}  -> sparse solve available")
except Exception as e:
    print(f"scipy MISSING: {e}")
try:
    import numpy; print(f"numpy {numpy.__version__} present")
except Exception as e:
    print(f"numpy MISSING: {e}")

FWD=225.0
def load(p):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(p))
    if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    return [o for o in bpy.data.objects if o.type=="MESH"][0]

def clean(ob, fill_holes, tri):
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bm=bmesh.new(); bm.from_mesh(ob.data)
    # drop wire edges (no faces) — leftovers from the face delete
    wire=[e for e in bm.edges if e.is_wire]
    bmesh.ops.delete(bm, geom=wire, context='EDGES')
    if fill_holes:
        bnd=[e for e in bm.edges if e.is_boundary]
        if bnd: bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if tri: bmesh.ops.triangulate(bm, faces=bm.faces)
    nm=sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return nm

def heat(ob, tag):
    zs=[v.co.z for v in ob.data.vertices]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
    a=math.radians(FWD); fwd=Vector((math.sin(a),-math.cos(a),0)).normalized()
    lateral=Vector((-fwd.y,fwd.x,0.0))
    co=[v.co.copy() for v in ob.data.vertices]
    neck=zmin+0.6608*H; mouth_z=zmin+0.6899*H
    head=[c for c in co if c.z>neck]; hc=sum(head,Vector())/len(head)
    band=[c for c in head if abs(c.z-mouth_z)<H*0.05]
    f_front=max(c.dot(fwd) for c in band); depth=f_front-min(c.dot(fwd) for c in band)
    lat0=hc.dot(lateral); head_h=zmax-neck
    ad=bpy.data.armatures.new("A"); arm=bpy.data.objects.new("A",ad)
    bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT'); eb=ad.edit_bones
    b=eb.new("body"); b.head=Vector((hc.x,hc.y,zmin)); b.tail=Vector((hc.x,hc.y,neck))
    s=eb.new("skull"); s.head=Vector((hc.x,hc.y,neck)); s.tail=Vector((hc.x,hc.y,zmax-head_h*0.10))
    s.parent=b; s.use_connect=True
    j=eb.new("jaw"); j.head=fwd*(f_front-depth*0.75)+lateral*lat0+Vector((0,0,mouth_z+head_h*0.12))
    j.tail=Vector((hc.x,hc.y,mouth_z-head_h*0.085)); j.parent=s; j.use_connect=False
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active=arm
    try: bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except RuntimeError as e: print(f"  {tag}: EXCEPTION {e}"); return
    out=[]
    for n in ("body","skull","jaw"):
        g=ob.vertex_groups.get(n)
        c=0 if g is None else sum(1 for v in ob.data.vertices for gg in v.groups if gg.group==g.index and gg.weight>0.01)
        out.append(f"{n}={c}")
    print(f"  {tag}: {'  '.join(out)}")

CUT="mesh/v2open/clyffy_v2_mouthopen.blend"
for fill,tri,tag in [(False,False,"wire-removed only"),
                     (True,False,"wire-removed + holes filled"),
                     (True,True,"wire-removed + filled + triangulated")]:
    ob=load(CUT); nm=clean(ob,fill,tri)
    print(f"\n[{tag}] verts {len(ob.data.vertices)} faces {len(ob.data.polygons)} non-manifold-after {nm}")
    heat(ob,tag)
