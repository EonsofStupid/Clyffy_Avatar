"""Is any tooth in front of the lip seal line from the camera?"""
import bpy, numpy as np, math

bpy.ops.wm.open_mainfile(filepath="mesh/canon/clyffy_v2_parts.blend")
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
FWD = 235.1
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat
H = float(co[:, 2].max() - co[:, 2].min())

di = [i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")][0]
cav, surf = set(), set()
for p in me.polygons:
    (cav if p.material_index == di else surf).update(p.vertices)
rim = np.array(sorted(cav & surf), dtype=int)

gi = {g.name: g.index for g in ob.vertex_groups}

def grp(n):
    idx = gi[n]
    return np.array([v.index for v in me.vertices for g in v.groups if g.group == idx and g.weight > 0.5])

tu, tl = grp("teeth_upper"), grp("teeth_lower")
# For each tooth vert, is there a rim vert near the same lateral with lower fwd?
# tooth is "visible" if its fwd > nearby rim fwd (pokes past the seal)
def poke(g, name):
    n_poke = 0
    worst = 0.0
    for i in g:
        # rim verts within 0.02 lateral
        near = rim[np.abs(lp[rim] - lp[i]) < 0.02]
        if len(near) == 0:
            continue
        rim_fwd = fp[near].max()  # most forward lip at this lat
        poke_amt = fp[i] - rim_fwd
        if poke_amt > -0.002:  # within 2mm of rim front or past
            n_poke += 1
            worst = max(worst, poke_amt)
    print(f"{name}: verts near/past rim front: {n_poke}/{len(g)}  worst poke {worst:+.4f}")

poke(tu, "teeth_upper")
poke(tl, "teeth_lower")
print(f"rim fwd range [{fp[rim].min():+.3f},{fp[rim].max():+.3f}]")
print(f"teeth_u fwd range [{fp[tu].min():+.3f},{fp[tu].max():+.3f}]")
print(f"teeth_l fwd range [{fp[tl].min():+.3f},{fp[tl].max():+.3f}]")

# material colors
for m in me.materials:
    if m:
        print(f"mat {m.name}: diffuse={tuple(m.diffuse_color)}")
