"""Find a character's forward axis by SNOUT SEARCH.

For every candidate horizontal direction, measure how far the head protrudes along it
*within a narrow lateral band*. A muzzle is narrow and protrudes far; ears and horns are
wide, so the band excludes them. The direction maximising narrow-band protrusion is
forward. Geometric, no assumption of symmetry, generalises across characters.

    blender --background --python tools/find_axis.py -- <mesh> [expected_deg]
"""
import bpy, sys, os, math
import numpy as np

argv = sys.argv[sys.argv.index("--")+1:]
MESH = os.path.abspath(argv[0]); EXPECT = float(argv[1]) if len(argv) > 1 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
if MESH.lower().endswith(".fbx"): bpy.ops.import_scene.fbx(filepath=MESH)
else:                             bpy.ops.import_scene.gltf(filepath=MESH)
ob = max([o for o in bpy.data.objects if o.type=="MESH"], key=lambda o: len(o.data.vertices))
V = np.array([[v.co.x,v.co.y,v.co.z] for v in ob.data.vertices])
zmin,zmax = V[:,2].min(), V[:,2].max(); H = zmax-zmin
head = V[V[:,2] > zmin + H*0.62]                    # upper head only
ctr  = head.mean(axis=0)
P    = head - ctr
print(f"mesh {len(V)} verts  height {H:.4f}   head band {len(head)} verts")

BAND = H*0.045                                      # snout half-width
prof = []
for deg in np.arange(0,360,1.0):
    a = math.radians(deg)
    f = np.array([math.sin(a), -math.cos(a), 0.0])  # turnaround convention
    l = np.array([f[1], -f[0], 0.0])
    fe = P @ f; la = np.abs(P @ l)
    sel = fe[la < BAND]
    prof.append((deg, sel.max() if len(sel) else -1e9))
prof = np.array(prof)
best = prof[prof[:,1].argmax()]
ang  = float(best[0])

order = prof[prof[:,1].argsort()[::-1]]
print("top candidate directions (deg, narrow-band protrusion):")
for d,v in order[:5]: print(f"   {d:6.1f}   {v:.4f}")
lo = prof[:,1].min(); hi = prof[:,1].max()
print(f"contrast: max {hi:.4f} vs min {lo:.4f}  ->  ratio {hi/max(lo,1e-6):.2f}")

print(f"\nFORWARD AXIS = {ang:.1f} deg")
print(f"  camera: loc = ctr + (sin a, -cos a)*R ; rot = (90deg, 0, a)   a = {ang:.1f}")
if EXPECT is not None:
    err = abs((ang-EXPECT+180)%360-180)
    print(f"  expected {EXPECT:.1f} -> ERROR {err:.1f} deg  [{'PASS' if err<12 else 'FAIL'}]")
