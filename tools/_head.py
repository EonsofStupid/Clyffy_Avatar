import bpy,sys,os,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
MESH,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=MESH)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
for c in ob.bound_box:
    w=ob.matrix_world@Vector(c)
    mn=Vector((min(mn[i],w[i]) for i in range(3))); mx=Vector((max(mx[i],w[i]) for i in range(3)))
dims=mx-mn
head_z = mn.z + dims.z*0.84          # head centre
ctr=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,head_z))
r=dims.z*0.22
sc=bpy.context.scene
sc.render.resolution_x=700; sc.render.resolution_y=700
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.ortho_scale=r*2.6
sc.world=bpy.data.worlds.new("W")
def shot(name, ang, mode):
    sc.render.engine="BLENDER_WORKBENCH"
    sh=sc.display.shading
    if mode=="tex": sh.light='STUDIO'; sh.color_type='TEXTURE'; sh.show_xray=False; sc.display.shading.wireframe_color_type='OBJECT'
    else:           sh.light='FLAT';   sh.color_type='SINGLE'; sh.single_color=(0.8,0.8,0.82)
    sh.show_object_outline=False
    ob.show_wire = (mode=="wire"); ob.show_all_edges=(mode=="wire")
    a=math.radians(ang)
    cam.location=(ctr.x+math.sin(a)*r*6, ctr.y-math.cos(a)*r*6, ctr.z)
    cam.rotation_euler=(math.radians(90),0,a)
    sc.render.filepath=os.path.join(OUT,name); bpy.ops.render.render(write_still=True)
shot("head_front_tex.png",225,"tex")
shot("head_front_wire.png",225,"wire")
shot("head_side_wire.png",315,"wire")
