import bpy, numpy as np, math

path = "mesh/canon/clyffy_v2_parts.blend"
bpy.ops.wm.open_mainfile(filepath=path)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
FWD = 235.1
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])

di = [i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")][0]
cav, surf = set(), set()
for p in me.polygons:
    (cav if p.material_index == di else surf).update(p.vertices)
rim = np.array(sorted(cav & surf))
print("rim", len(rim), "cav", len(cav), "H", H)

ef = {}
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k + 1) % len(vs)]
        ef.setdefault((min(i, j), max(i, j)), []).append(p.material_index == di)
rimset = set(int(x) for x in rim)
adj = {}
for (i, j), mats in ef.items():
    if i in rimset and j in rimset and any(mats) and not all(mats):
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
start = int(rim[0])
cyc = [start]
prev, cur = None, start
while True:
    nxt = [n for n in adj[cur] if n != prev]
    prev, cur = cur, nxt[0]
    if cur == start:
        break
    cyc.append(cur)
cyc = np.array(cyc)
L = len(cyc)
hc = co[co[:, 2] > 0.208].mean(0)
lat0 = float(hc @ lat)
clat = co[cyc] @ lat - lat0
ci = sorted([int(np.argmin(clat)), int(np.argmax(clat))])
chainA = np.zeros(L, bool)
chainA[ci[0] : ci[1] + 1] = True
if co[cyc[chainA], 2].mean() > co[cyc[~chainA], 2].mean():
    chainA = ~chainA
lower, upper = cyc[chainA], cyc[~chainA]
print(f"lower {len(lower)} upper {len(upper)}")

gaps = []
for i in upper:
    d = np.linalg.norm(co[lower] - co[i], axis=1)
    j = int(np.argmin(d))
    gaps.append((float(d[j]), int(i), int(lower[j])))
gaps.sort()
gs = np.array([g[0] for g in gaps])
print(f"nearest upper→lower gap: min {gs.min():.5f} med {np.median(gs):.5f} "
      f"max {gs.max():.5f}  ({100*gs.min()/H:.3f}%H min, {100*np.median(gs)/H:.3f}%H med)")
print(f"upper z mean {co[upper,2].mean():+.4f} lower z mean {co[lower,2].mean():+.4f} "
      f"dz {co[upper,2].mean()-co[lower,2].mean():.5f}")

# pair midpoints: direction upper→lower
pairs = gaps  # already nearest
move_up = []
move_lo = []
for dist, ui, li in pairs:
    if dist < 1e-9:
        continue
    # close half the gap on each side along the connecting vector
    mid = 0.5 * (co[ui] + co[li])
    move_up.append((ui, mid - co[ui]))
    move_lo.append((li, mid - co[li]))
# average gap vector length if we seal completely
print(f"full seal would move each side by ~{gs.mean()/2:.5f}")

gi = {g.name: g.index for g in ob.vertex_groups}

def grp(n):
    if n not in gi:
        return np.array([], int)
    idx = gi[n]
    return np.array([v.index for v in me.vertices
                     for g in v.groups if g.group == idx and g.weight > 0.5])

for n in ("teeth_upper", "teeth_lower", "tongue"):
    g = grp(n)
    if len(g) == 0:
        continue
    print(f"{n}: n={len(g)} z[{co[g,2].min():+.3f},{co[g,2].max():+.3f}] "
          f"fwd[{(co[g]@fwd).min():+.3f},{(co[g]@fwd).max():+.3f}]")
print(f"rim fwd mean {(co[rim]@fwd).mean():+.4f}")
tu, tl = grp("teeth_upper"), grp("teeth_lower")
print(f"teeth_u fwd mean {(co[tu]@fwd).mean():+.4f}  behind rim by "
      f"{(co[rim]@fwd).mean()-(co[tu]@fwd).mean():+.4f}")
print(f"teeth_l fwd mean {(co[tl]@fwd).mean():+.4f}  behind rim by "
      f"{(co[rim]@fwd).mean()-(co[tl]@fwd).mean():+.4f}")

# How much of the gap is z vs forward?
vecs = co[np.array([g[2] for g in gaps])] - co[np.array([g[1] for g in gaps])]
print(f"gap vector mean (x,y,z) {vecs.mean(0)}")
print(f"gap |dz| mean {np.abs(vecs[:,2]).mean():.5f}  |dfwd| mean {np.abs(vecs@fwd).mean():.5f}")
