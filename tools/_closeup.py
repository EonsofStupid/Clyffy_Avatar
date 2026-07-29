import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
RIG,OUT,FWD,ANG=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2]),float(argv[3])
os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=RIG)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
arm=[o for o in bpy.data.objects if o.type=="ARMATURE"][0]
me=ob.data; N=len(me.vertices)
co=np.empty((N,3)); me.vertices.foreach_get("co",co.ravel())
zmin,zmax=co[:,2].min(),co[:,2].max(); H=zmax-zmin
a=math.radians(FWD); fwd=np.array([math.sin(a),-math.cos(a),0.0]); lat=np.array([-fwd[1],fwd[0],0.0])
di=[i for i,m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cav=sorted({v for p in me.polygons if p.material_index==di for v in p.vertices})
mouth=co[cav].mean(axis=0)
jb=arm.pose.bones["jaw"]; hv=Vector(jb.bone.head_local); lv=Vector(lat)
R=Matrix.Translation(hv)@Matrix.Rotation(math.radians(ANG),4,lv)@Matrix.Translation(-hv)
jb.matrix=R@jb.bone.matrix_local; bpy.context.view_layer.update()
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
arm.hide_render=True
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=sc.render.resolution_y=900
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30
Rr=H*5
lat_ext=max(abs((co[cav]@lat).max()-(mouth@lat)), abs((co[cav]@lat).min()-(mouth@lat)))
for off,tag,scale in ((0,"corner",0.075),(math.radians(35),"corner35",0.075)):
    ang=a+off; cd.ortho_scale=scale
    tgt=mouth + lat*(lat_ext*0.85)          # aim at the mouth CORNER
    cam.location=(tgt[0]+math.sin(ang)*Rr, tgt[1]-math.cos(ang)*Rr, tgt[2])
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
