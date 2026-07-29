import bpy, os, sys
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(argv[0]))
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
me=ob.data
print("shape keys:", [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else None)
basis=me.shape_keys.key_blocks["Basis"]; jaw=me.shape_keys.key_blocks["jaw_open"]
print("jaw.value =", jaw.value, "| mute =", jaw.mute,
      "| slider", jaw.slider_min, jaw.slider_max)
print("key_blocks owner use_relative =", me.shape_keys.use_relative)
print("jaw.relative_key =", jaw.relative_key.name)
d=[(jaw.data[i].co - basis.data[i].co).length for i in range(len(me.vertices))]
mx=max(d); n=sum(1 for x in d if x>1e-6)
print(f"STORED DELTA: max {mx:.5f}  moved verts {n} / {len(d)}")
# now evaluate with value=1 and measure the ACTUAL evaluated mesh
jaw.value=1.0
dg=bpy.context.evaluated_depsgraph_get()
ev=ob.evaluated_get(dg).to_mesh()
d2=[(ev.vertices[i].co - basis.data[i].co).length for i in range(len(me.vertices))]
print(f"EVALUATED @1.0: max {max(d2):.5f}  moved {sum(1 for x in d2 if x>1e-6)}")
