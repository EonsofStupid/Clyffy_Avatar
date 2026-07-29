"""Is the mouth hole boundary a simple cycle? A pinch point folds the extrude."""
import bpy, bmesh, sys, os
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
gi={g.name:g.index for g in ob.vertex_groups}
seam_v=set(v.index for v in me.vertices for g in v.groups if g.group==gi["op_lip_seam"] and g.weight>0.5)
seam=[p.index for p in me.polygons if all(vi in seam_v for vi in p.vertices)]
bm=bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
tag=bm.edges.layers.int.new("t")
for e in bm.edges:
    if e.is_boundary: e[tag]=1
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in seam], context='FACES')
bm.edges.ensure_lookup_table()
bound=[e for e in bm.edges if e.is_boundary and e[tag]==0]
print(f"mouth boundary: {len(bound)} edges")
deg={}
for e in bound:
    for v in e.verts: deg[v.index]=deg.get(v.index,0)+1
from collections import Counter
print(f"  boundary vert degrees: {dict(Counter(deg.values()))}")
pinch=[v for v,d in deg.items() if d!=2]
print(f"  PINCH VERTS (degree != 2): {len(pinch)}")
for vi in pinch[:10]:
    c=bm.verts[vi].co if vi<len(bm.verts) else None
    print(f"    vert {vi} degree {deg[vi]}")
# also: does the deleted region touch itself?
print(f"  deleted {len(seam)} faces; seam group has {len(seam_v)} verts")
