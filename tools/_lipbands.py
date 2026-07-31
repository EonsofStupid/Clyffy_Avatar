#!/usr/bin/env python3
"""MEASURE the lip region: geodesic bands off the rim + what the TEXTURE already paints.

    blender -b <body.blend> --python tools/_lipbands.py -- [FWD]

Read-only. A7 step 0b.

WHY THIS BEFORE AUTHORING ANYTHING. `_matstate.py` shows Base Color on the 97.6% material is
a LINKED TEXTURE, not a constant. The reference calls for three concentric lip bands (salmon
inner rim -> cream outer band -> fur). If the baked Tripo atlas already paints that gradient,
then splitting materials to add colour would be re-authoring what exists, and the real deficit
is only SSS + roughness. If the atlas is flat across the whole muzzle, the split has to carry
colour too. Those are different jobs and I am not guessing which one this is.

Bands are GEODESIC (Dijkstra along mesh edges) from the lip rim, never Euclidean: the upper
and lower lips are ~0 apart in space through the closed slit but far apart across the surface,
and a Euclidean band would bleed one into the other.
"""
from __future__ import annotations

import sys
import heapq
import math
from collections import defaultdict

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FWD_DEG = float(argv[0]) if argv else 235.1
a = math.radians(FWD_DEG)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])

ob = max((o for o in bpy.data.objects if o.type == "MESH"),
         key=lambda o: len(o.data.polygons))
me = ob.data
n = len(me.vertices)
co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
H = float(co[:, 2].max() - co[:, 2].min())
print(f"object {ob.name}  verts {n}  faces {len(me.polygons)}  H={H:.4f}")

# ── the lip rim, exactly as lip_seal.py:50-55 derives it ─────────────────────
# NOT from the cav_src attribute. cav_src is EXTRUSION LINEAGE (which surface vert each
# cavity vert descends from) and marks only the 186 interior verts, none of which sit on
# the skin — intersecting it with the skin gives the empty set, which is how I got this
# wrong on the first run. The rim is a MATERIAL BOUNDARY: verts that belong to an interior
# face AND to some non-interior face.
mi = np.empty(len(me.polygons), dtype=np.int32)
me.polygons.foreach_get("material_index", mi)
SKIN_SLOT = int(np.bincount(mi).argmax())          # the 97.6% material
DARK = [i for i, m in enumerate(me.materials)
        if m and m.name.startswith("clyffy_mouth_interior")][0]

cav: set[int] = set()
other: set[int] = set()
for i, p in enumerate(me.polygons):
    (cav if mi[i] == DARK else other).update(int(v) for v in p.vertices)
rim = sorted(cav & other)

skin_faces = np.nonzero(mi == SKIN_SLOT)[0]
surf: set[int] = set()
for f in skin_faces:
    surf.update(int(v) for v in me.polygons[int(f)].vertices)

print(f"cav {len(cav)}  skin-surface {len(surf)}  RIM {len(rim)} "
      f"(rim on skin: {len(set(rim) & surf)})")
if not rim:
    raise RuntimeError("empty rim")

# ── geodesic distance from the rim, over SKIN faces only ─────────────────────
adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
ev = np.empty(len(me.edges) * 2, dtype=np.int32)
me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
for i, j in ev:
    i, j = int(i), int(j)
    if i in surf and j in surf:
        w = float(np.linalg.norm(co[i] - co[j]))
        adj[i].append((j, w)); adj[j].append((i, w))

INF = float("inf")
dist = np.full(n, INF)
pq: list[tuple[float, int]] = []
for r in rim:
    dist[r] = 0.0
    heapq.heappush(pq, (0.0, r))
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u] + 1e-12:
        continue
    for v, w in adj[u]:
        nd = d + w
        if nd < dist[v]:
            dist[v] = nd
            heapq.heappush(pq, (nd, v))
reached = int(np.isfinite(dist).sum())
print(f"geodesic reached {reached} of {len(surf)} skin verts")

# ── sample the base-colour texture at each vertex ────────────────────────────
mat = me.materials[SKIN_SLOT]
bsdf = next(x for x in mat.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
img = None
for key in ("Base Color", "Roughness"):
    s = bsdf.inputs.get(key)
    if s is not None and s.is_linked:
        nd = s.links[0].from_node
        if nd.type == "TEX_IMAGE":
            print(f"{key} <- image {nd.image.name} {tuple(nd.image.size)}")
            if key == "Base Color":
                img = nd.image
if img is None:
    raise RuntimeError("Base Color is not an image texture after all")

W, Hp = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(Hp, W, 4)

uvl = me.uv_layers.active.data
uv_sum = np.zeros((n, 2)); uv_cnt = np.zeros(n)
cv = np.empty(len(me.loops), dtype=np.int32)
me.loops.foreach_get("vertex_index", cv)
uvs = np.empty(len(me.loops) * 2); uvl.foreach_get("uv", uvs); uvs = uvs.reshape(-1, 2)
np.add.at(uv_sum, cv, uvs)
np.add.at(uv_cnt, cv, 1.0)
ok = uv_cnt > 0
uv = np.zeros((n, 2)); uv[ok] = uv_sum[ok] / uv_cnt[ok, None]

ix = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1).astype(int)
iy = np.clip((uv[:, 1] % 1.0) * (Hp - 1), 0, Hp - 1).astype(int)
rgb = px[iy, ix, :3]                      # linear, as stored


def srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def report(mask, label):
    k = int(mask.sum())
    if k == 0:
        print(f"  {label:<26} (empty)")
        return
    m = rgb[mask].mean(axis=0)
    s = srgb(m) * 255.0
    sd = rgb[mask].std(axis=0).mean()
    print(f"  {label:<26} n={k:<6} sRGB=({s[0]:5.1f},{s[1]:5.1f},{s[2]:5.1f})  "
          f"linear=({m[0]:.3f},{m[1]:.3f},{m[2]:.3f})  sd={sd:.4f}")


print("\nTEXTURE COLOUR BY GEODESIC BAND OFF THE LIP RIM (%H of body height):")
edges = [0.0, 0.005, 0.010, 0.020, 0.035, 0.055, 0.080]
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (dist >= lo * H) & (dist < hi * H)
    report(m, f"{lo*100:.1f}-{hi*100:.1f}%H")
report((dist >= edges[-1] * H) & np.isfinite(dist), f">{edges[-1]*100:.1f}%H (fur)")

print("\nTEXTURE COLOUR BY VERTEX GROUP:")
gi = {g.name: g.index for g in ob.vertex_groups}
for gname in ("lip_upper", "lip_lower", "lip_corner_L", "lip_corner_R", "nose",
              "cheek_L", "jaw", "skull"):
    if gname not in gi:
        continue
    want = gi[gname]
    mask = np.zeros(n, bool)
    for v in me.vertices:
        for g in v.groups:
            if g.group == want and g.weight > 0.5:
                mask[v.index] = True
    report(mask, gname)

# Is there ANY colour structure to find? If the muzzle is flat, a split must carry colour.
inner = (dist > 0) & (dist < 0.010 * H)
outer = (dist >= 0.020 * H) & (dist < 0.055 * H)
if inner.sum() and outer.sum():
    d = srgb(rgb[inner].mean(axis=0)) * 255 - srgb(rgb[outer].mean(axis=0)) * 255
    print(f"\ninner-lip minus outer-band, sRGB delta = "
          f"({d[0]:+.1f},{d[1]:+.1f},{d[2]:+.1f})  |delta|={np.linalg.norm(d):.1f}/441")
    print("  |delta| < 12 => the atlas is effectively FLAT here; a material split must "
          "carry colour, not just SSS.")

print("\nBAND SIZE IF SPLIT (faces, all-verts-in-band rule):")
fv = [list(p.vertices) for p in me.polygons]
for lo, hi, name in ((0.0, 0.010, "inner lip rim"),
                     (0.010, 0.030, "outer lip band"),
                     (0.030, 0.080, "muzzle pad")):
    c = sum(1 for i, vs in enumerate(fv)
            if mi[i] == SKIN_SLOT and vs
            and all(lo * H <= dist[v] < hi * H for v in vs))
    print(f"  {name:<18} {c} faces")
