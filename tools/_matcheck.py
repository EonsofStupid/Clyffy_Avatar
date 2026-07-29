import bpy, sys, os
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
faces=[p for p in me.polygons if p.material_index==di]
zs=[me.vertices[v].co.z for p in faces for v in p.vertices]
print(f"materials {[m.name for m in me.materials]}")
print(f"faces with clyffy_mouth_interior: {len(faces)}   z[{min(zs):+.4f},{max(zs):+.4f}]")
for m in me.materials:
    print(f"  {m.name}: diffuse_color {tuple(round(x,3) for x in m.diffuse_color)}")
# any face NOT dark that sits inside the mouth z-band and faces the wrong way?
import math
band=[p for p in me.polygons if p.material_index!=di and
      all(abs(me.vertices[v].co.z-0.2257)<0.05 for v in p.vertices)]
print(f"non-cavity faces within +-0.05 of the mouth z: {len(band)}")
