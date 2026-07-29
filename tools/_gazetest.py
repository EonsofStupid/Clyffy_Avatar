"""Now that the domes are separate: does gaze rotate, and does a lid close over them?"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index("--")+1:]
SRC,OUT,FWD=os.path.abspath(argv[0]),os.path.abspath(argv[1]),float(argv[2])
os.makedirs(OUT,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
ob=[o for o in bpy.data.objects if o.type=="MESH"][0]; me=ob.data
N=len(me.vertices); co=np.empty((N,3)); me.vertices.foreach_get("co",co.ravel())
zmin,zmax=co[:,2].min(),co[:,2].max(); H=zmax-zmin
a=math.radians(FWD); fwd=np.array([math.sin(a),-math.cos(a),0.0]); lat=np.array([-fwd[1],fwd[0],0.0])
gi={g.name:g.index for g in ob.vertex_groups}
def grp(n): return np.array(sorted(v.index for v in me.vertices for g in v.groups if g.group==gi[n] and g.weight>0.5))
EL,ER=grp("eye_L"),grp("eye_R")
cL=np.array(ob["eye_L_center"]); cR=np.array(ob["eye_R_center"])
rL=float(ob["eye_L_radius"]);   rR=float(ob["eye_R_radius"])
eyeset=set(EL.tolist())|set(ER.tolist())
print(f"eye_L {len(EL)} verts r={rL:.4f}   eye_R {len(ER)} verts r={rR:.4f}")

base=co.copy()
def apply(coords):
    flat=coords.astype(np.float32).ravel()
    me.vertices.foreach_set("co", flat); me.update()

def gaze(yaw_deg, pitch_deg):
    out=base.copy()
    for idx,c in ((EL,cL),(ER,cR)):
        R=(Matrix.Rotation(math.radians(yaw_deg),3,Vector((0,0,1))) @
           Matrix.Rotation(math.radians(pitch_deg),3,Vector(lat)))
        M=np.array(R)
        out[idx]=(base[idx]-c) @ M.T + c
    return out

def blink(amt):
    """Close the SKIN over the now-rigid eyeball.

    The lid must SLIDE OVER the dome, not collapse through it. Pulling skin toward the
    eye centre's z-plane closes it BEHIND the eyeball -- whose apex protrudes a full
    radius in front of that plane -- so the eye pokes through. Instead: rotate each skin
    vert about the lateral axis, around the eye centre, until its elevation reaches the
    horizontal midline, holding its radius at >= r so it passes in front of the dome.
    """
    out=base.copy()
    up=np.array([0.0,0.0,1.0])
    for c,r,outv in ((cL,rL,None),(cR,rR,None)):
        oc = c-np.array([base[base[:,2]>0.208][:,0].mean(), base[base[:,2]>0.208][:,1].mean(), c[2]])
        u = oc/max(np.linalg.norm(oc),1e-9)            # outward (forward) for this socket
        reach=r*1.38   # tight: only the socket ring is a lid; beyond that is face
        d=np.linalg.norm(base-c,axis=1)
        sel=[i for i in np.where(d<reach)[0] if i not in eyeset]
        for i in sel:
            rel=base[i]-c
            rad=np.linalg.norm(rel)
            if rad<1e-9: continue
            alpha=float(rel@u); beta=float(rel@lat); gamma=float(rel@up)
            if abs(gamma)<1e-9 and alpha<=0: continue
            theta=-math.atan2(gamma,alpha)             # rotation that brings it to the midline
            w=1.0-max(0.0,(rad-r)/max(reach-r,1e-9)); w=max(0.0,min(1.0,w)); w=w*w*(3-2*w)
            th=theta*amt*w
            ca_,sa=math.cos(th),math.sin(th)
            na=alpha*ca_-gamma*sa; ng=alpha*sa+gamma*ca_
            newrel=u*na+lat*beta+up*ng
            nr=np.linalg.norm(newrel)
            if nr>1e-9:
                target=max(rad, r*1.06) if w>0.05 else rad
                newrel=newrel/nr*target
            out[i]=c+newrel
    return out

sc=bpy.context.scene
for o in [x for x in bpy.data.objects if x.type=='ARMATURE']: o.hide_render=True
for o in [x for x in bpy.data.objects if x.type=='CAMERA']: bpy.data.objects.remove(o,do_unlink=True)
sc.render.engine="BLENDER_WORKBENCH"; sc.world=bpy.data.worlds.new("W")
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=sc.render.resolution_y=700
cd=bpy.data.cameras.new("C"); cam=bpy.data.objects.new("C",cd)
sc.collection.objects.link(cam); sc.camera=cam
cd.type="ORTHO"; cd.clip_start=0.01; cd.clip_end=H*30; cd.ortho_scale=0.26
eyez=float((cL[2]+cR[2])/2); hc=base[base[:,2]>0.208].mean(axis=0); Rr=H*5
cam.location=(hc[0]+math.sin(a)*Rr, hc[1]-math.cos(a)*Rr, eyez)
cam.rotation_euler=(math.radians(90),0,a)
for tag,coords in (("rest",base),
                   ("gaze_left",gaze(-16,0)), ("gaze_right",gaze(16,0)),
                   ("gaze_up",gaze(0,-12)),   ("gaze_down",gaze(0,12)),
                   ("blink_50",blink(0.5)),   ("blink_100",blink(1.0))):
    apply(coords)
    sc.render.filepath=os.path.join(OUT,f"{tag}.png"); bpy.ops.render.render(write_still=True)
apply(base)
print("ok")
