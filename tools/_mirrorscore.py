"""Image-space symmetry: render head-on candidates, score each against its mirror."""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:]
CUT,OUT=os.path.abspath(argv[0]),os.path.abspath(argv[1]); os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=CUT)
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]
N=len(ob.data.vertices); co=np.empty((N,3)); ob.data.vertices.foreach_get("co",co.ravel())
mw=ob.matrix_world; R3=np.array(mw.to_3x3()); T3=np.array(mw.translation)
co=co@R3.T+T3
zmin,zmax=co[:,2].min(),co[:,2].max(); H=zmax-zmin
NECK=0.1590; head=co[co[:,2]>NECK]; hc=head.mean(axis=0)
sc=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type=='CAMERA': bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='FLAT'; sc.display.shading.color_type='SINGLE'
sc.display.shading.single_color=(1,1,1)
sc.render.resolution_x=sc.render.resolution_y=400
sc.render.film_transparent=True
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=(zmax-NECK)*1.15
Rr=H*5; hz=(zmax+NECK)/2
res=[]
for a10 in range(2310,2400,5):
    ang=a10/10.0; a=math.radians(ang)
    cam.location=(hc[0]+math.sin(a)*Rr, hc[1]-math.cos(a)*Rr, hz)
    cam.rotation_euler=(math.radians(90),0,a)
    fp=os.path.join(OUT,f"m_{int(ang*10):04d}.png"); sc.render.filepath=fp
    bpy.ops.render.render(write_still=True)
    im=bpy.data.images.load(fp)
    w,h=im.size
    px=np.array(im.pixels[:]).reshape(h,w,4)[:,:,3]   # alpha = silhouette
    bpy.data.images.remove(im)
    d=np.abs(px-px[:,::-1]).mean()
    res.append((d,ang))
    print(f"  {ang:6.1f} deg  mirror-diff {d:.5f}")
import numpy as _np
res.sort(key=lambda t: t[1])
A=_np.array([a for d,a in res]); D=_np.array([d for d,a in res])
k=int(D.argmin())
if 0<k<len(A)-1:
    y0,y1,y2=D[k-1],D[k],D[k+1]
    off=0.5*(y0-y2)/max(1e-12,(y0-2*y1+y2))
    peak=A[k]+off*(A[1]-A[0])
else: peak=A[k]
print(f"\nMOST SYMMETRIC SILHOUETTE: {A[k]:.1f} deg sampled, parabolic peak {peak:.2f} deg (diff {D[k]:.5f})")
