"""Measure the HEAD's bilateral symmetry plane, then render head-on candidates.

The manifest's forward_axis_deg=225 puts the cut mouth cavity at lateral -0.133 of a
0.168 half-width -- i.e. on the SIDE of the head. This re-measures properly:
mirror the head across a candidate plane and score by mean nearest-neighbour distance,
optimising BOTH the angle and the plane's lateral offset.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, kdtree

argv = sys.argv[sys.argv.index("--")+1:]
CUT, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=CUT)
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]; me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
mw = ob.matrix_world
R3 = np.array(mw.to_3x3()); T3 = np.array(mw.translation)
co = co @ R3.T + T3          # WORLD space -- the object carries a +69.17 deg Z rotation
print(f"object '{ob.name}' rot_z {np.degrees(np.arctan2(R3[1,0], R3[0,0])):+.2f} deg -> working in WORLD space")
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
NECK = 0.1590
head = co[co[:, 2] > NECK]
hc = head.mean(axis=0)
print(f"head verts {len(head)}  centroid ({hc[0]:+.4f},{hc[1]:+.4f},{hc[2]:+.4f})")

kd = kdtree.KDTree(len(head))
for i, c in enumerate(head): kd.insert(Vector(c), i)
kd.balance()
S = head[::max(1, len(head)//2500)]        # deterministic stride sample
print(f"symmetry scoring on {len(S)} sampled head verts")

def score(angle_deg, off):
    a = math.radians(angle_deg)
    f = np.array([math.sin(a), -math.cos(a), 0.0])
    l = np.array([-f[1], f[0], 0.0])
    d = S @ l - off
    M = S - 2.0*np.outer(d, l)
    tot = 0.0
    for p in M:
        _, _, dist = kd.find(Vector(p)); tot += dist
    return tot/len(M)

base_off = float(hc @ np.array([1.0, 0.0, 0.0]))
best = None
for ad in range(0, 180, 3):
    a = math.radians(ad); l = np.array([math.cos(a), math.sin(a), 0.0])
    off = float(head[:, :2] @ l[:2] .T.mean()) if False else float((head[:, :2] @ l[:2]).mean())
    s = score(ad, off)
    if best is None or s < best[0]: best = (s, ad, off)
print(f"coarse best: {best[1]:.0f} deg  err {best[0]:.5f} ({100*best[0]/H:.2f}% of height)")

fine = None
for ad10 in range(int((best[1]-4)*4), int((best[1]+4)*4)+1):
    ad = ad10/4.0
    a = math.radians(ad); l = np.array([math.cos(a), math.sin(a), 0.0])
    c0 = float((head[:, :2] @ l[:2]).mean())
    for k in range(-6, 7):
        off = c0 + k*H*0.004
        s = score(ad, off)
        if fine is None or s < fine[0]: fine = (s, ad, off)
print(f"FINE best: {fine[1]:.2f} deg (mirror plane), err {fine[0]:.5f} = {100*fine[0]/H:.2f}% of height")
print("  (this is the mirror-plane angle; forward is perpendicular, 180-ambiguous)")
for cand in (fine[1], (fine[1]+180) % 360):
    a = math.radians(cand); f = np.array([math.sin(a), -math.cos(a), 0.0])
    print(f"  candidate forward {cand:6.2f} deg -> head protrusion {float((head @ f).max() - (hc @ f)):+.4f}")
print(f"\nfor reference, err at manifest 225 deg: {score(225.0, float((head[:, :2] @ np.array([math.cos(math.radians(225)), math.sin(math.radians(225))])).mean())):.5f}")

# ---- render head-on candidates, full size, no contact-sheet downscaling ----
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 512
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = (zmax-NECK)*1.15
R = H*5
CANDS = [140, 150, 155, 160, 165, 170, 180, 195, 210, 225]
hz = (zmax + NECK)/2
for ang in CANDS:
    a = math.radians(ang)
    cam.location = (hc[0] + math.sin(a)*R, hc[1] - math.cos(a)*R, hz)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = os.path.join(OUT, f"head_{ang:03d}.png")
    bpy.ops.render.render(write_still=True)
print("ok")
