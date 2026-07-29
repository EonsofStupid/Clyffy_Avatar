"""Are the eyes/hands GEOMETRY or paint? Solid shading strips the texture and shows form."""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
SRC,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2])
os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
N=len(me.vertices); co=np.empty((N,3)); me.vertices.foreach_get("co",co.ravel())
zmin,zmax=co[:,2].min(),co[:,2].max(); H=zmax-zmin
a=math.radians(FWD); fwd=np.array([math.sin(a),-math.cos(a),0.0]); lat=np.array([-fwd[1],fwd[0],0.0])
head=co[co[:,2]>0.208]; hc=head.mean(axis=0)
print(f"head verts {len(head)}  z[{head[:,2].min():+.4f},{head[:,2].max():+.4f}]")
# vertical density profile of the head -- eyes should sit as a band above the muzzle
for b in range(10):
    lo=0.208+(zmax-0.208)*b/10; hi=0.208+(zmax-0.208)*(b+1)/10
    m=(co[:,2]>=lo)&(co[:,2]<hi)
    print(f"  z {lo:+.4f}..{hi:+.4f}  verts {int(m.sum()):5d}")
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in ('CAMERA','ARMATURE'):
        if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
        else: o.hide_render=True
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='SINGLE'
sc.display.shading.single_color=(0.75,0.75,0.78)
sc.display.shading.show_cavity=True
sc.render.resolution_x=sc.render.resolution_y=800
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30
R=H*5
eye_z=0.208+(zmax-0.208)*0.62
for off,tag,sc_ in ((0,"face_front",0.30),(math.radians(35),"face_q35",0.30),(0,"eye_zoom",0.14)):
    ang=a+off; cd.ortho_scale=sc_
    ctr=Vector((hc[0],hc[1],eye_z if tag=="eye_zoom" else (zmax+0.208)/2))
    cam.location=(ctr.x+math.sin(ang)*R, ctr.y-math.cos(ang)*R, ctr.z)
    cam.rotation_euler=(math.radians(90),0,ang)
    sc.render.filepath=os.path.join(OUT,f"{tag}.png"); bpy.ops.render.render(write_still=True)
print("ok")
