import bpy, bmesh, sys, os
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
bm=bmesh.new(); bm.from_mesh(ob.data)
bnd=[e for e in bm.edges if e.is_boundary]
print(f"boundary edges: {len(bnd)}")
# walk loops
adj={}
for e in bnd:
    for v in e.verts: adj.setdefault(v.index,[]).append(e)
seen=set(); loops=[]
for e in bnd:
    if e.index in seen: continue
    loop=[]; stack=[e]
    while stack:
        x=stack.pop()
        if x.index in seen: continue
        seen.add(x.index); loop.append(x)
        for v in x.verts:
            for y in adj[v.index]:
                if y.index not in seen: stack.append(y)
    loops.append(loop)
print(f"boundary loops: {len(loops)}")
for i,l in enumerate(loops):
    vs={v for x in l for v in x.verts}
    c=sum((v.co for v in vs),Vector())/len(vs)
    degs=[len(adj[v.index]) for v in vs]
    print(f"  loop {i}: {len(l)} edges, {len(vs)} verts, centre ({c.x:+.4f},{c.y:+.4f},{c.z:+.4f}) "
          f"z[{min(v.co.z for v in vs):+.4f},{max(v.co.z for v in vs):+.4f}] vert-degree min {min(degs)} max {max(degs)} "
          f"{'SIMPLE CYCLE' if min(degs)==2 and max(degs)==2 else '** NOT A SIMPLE CYCLE **'}")
nm=[e for e in bm.edges if not e.is_manifold and not e.is_boundary]
print(f"non-manifold (non-boundary) edges: {len(nm)}")
for e in nm:
    c=(e.verts[0].co+e.verts[1].co)/2
    print(f"  at ({c.x:+.4f},{c.y:+.4f},{c.z:+.4f})  link_faces {len(e.link_faces)}")
