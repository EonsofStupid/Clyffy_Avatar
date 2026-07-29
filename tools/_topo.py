import bpy,bmesh,sys,os
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.abspath(argv[0]))
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
me=ob.data
bm=bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

# --- connected components (loose parts) ---
seen=set(); comps=[]
for v in bm.verts:
    if v.index in seen: continue
    stack=[v]; comp=[]
    seen.add(v.index)
    while stack:
        cur=stack.pop(); comp.append(cur)
        for e in cur.link_edges:
            o=e.other_vert(cur)
            if o.index not in seen:
                seen.add(o.index); stack.append(o)
    comps.append(comp)
comps.sort(key=len, reverse=True)
print(f"LOOSE PARTS: {len(comps)}")
tot=len(bm.verts)
for i,c in enumerate(comps[:12]):
    zs=[v.co.z for v in c]; xs=[v.co.x for v in c]; ys=[v.co.y for v in c]
    print(f"  part {i:2d}: {len(c):6d} verts ({100*len(c)/tot:5.1f}%)  "
          f"z[{min(zs):+.3f},{max(zs):+.3f}] x[{min(xs):+.3f},{max(xs):+.3f}]")

# --- manifold / boundary check: open edges = holes (mouth cavity, eye sockets) ---
boundary=[e for e in bm.edges if len(e.link_faces)==1]
nonman=[e for e in bm.edges if len(e.link_faces)>2]
print(f"\nBOUNDARY (hole) EDGES: {len(boundary)}")
print(f"NON-MANIFOLD EDGES:    {len(nonman)}")
if boundary:
    zs=[v.co.z for e in boundary for v in e.verts]
    print(f"  boundary z-range: [{min(zs):+.3f},{max(zs):+.3f}]")
print(f"\nTOTAL verts {len(bm.verts)}  edges {len(bm.edges)}  faces {len(bm.faces)}")
print(f"materials on object: {[ms.material.name if ms.material else None for ms in ob.material_slots]}")
bm.free()
