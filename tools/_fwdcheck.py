import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.abspath(argv[0]))
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
co=[v.co.copy() for v in me.vertices]
zs=[c.z for c in co]; zmin,zmax=min(zs),max(zs); H=zmax-zmin
head=[c for c in co if c.z>zmin+H*0.70]
axis=Vector((sum(c.x for c in head)/len(head),sum(c.y for c in head)/len(head)))
tip=max(head,key=lambda c:(Vector((c.x,c.y))-axis).length)
fn=(Vector((tip.x,tip.y))-axis).normalized()
print(f"head-band centroid  ({axis.x:+.4f},{axis.y:+.4f})")
print(f"'tip' by max-radial ({tip.x:+.4f},{tip.y:+.4f},{tip.z:+.4f})  dir ({fn.x:+.3f},{fn.y:+.3f})")
print(f"  -> turnaround angle of that dir: {math.degrees(math.atan2(fn.x,-fn.y))%360:.1f} deg")
print(f"  (empirically the TRUE front is 225 deg)")
true=math.radians(225)
tf=Vector((math.sin(true),-math.cos(true)))
print(f"true-front dir      ({tf.x:+.3f},{tf.y:+.3f})")
print(f"ANGULAR ERROR: {math.degrees(fn.angle(tf)):.1f} deg")
# what IS at the detected tip?
print(f"\n'tip' height in head band: {(tip.z-(zmin+H*0.70))/(H*0.30)*100:.0f}% up the head")
