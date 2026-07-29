"""Locate the eyeball domes and their socket rims, and decide whether a lid can close.

Same play as the lip seam: the socket rim is a CREASE, so find it as high-dihedral edges
rather than guessing a z-band. Reports dome geometry (sphere fit), rim geometry, and how
much lid travel a blink would need.

    blender -b --python tools/eye_probe.py -- <mesh.blend> <out_dir> <fwd_deg>
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat
NECK = 0.208
head = co[:, 2] > NECK
hc = co[head].mean(axis=0); lat0 = float(hc @ lat)

bm = bmesh.new(); bm.from_mesh(me)
bm.edges.ensure_lookup_table(); bm.verts.ensure_lookup_table()

# --- creases in the upper face: the socket rim is a fold, like the lip line was ---
band_lo, band_hi = NECK + (zmax-NECK)*0.35, NECK + (zmax-NECK)*0.90
cand = []
for e in bm.edges:
    if len(e.link_faces) != 2: continue
    v0, v1 = e.verts[0].index, e.verts[1].index
    zmid = (co[v0, 2] + co[v1, 2])/2
    if not (band_lo < zmid < band_hi): continue
    if (fp[v0] + fp[v1])/2 < float(hc @ fwd): continue          # front of the head only
    n0, n1 = e.link_faces[0].normal, e.link_faces[1].normal
    ang = math.degrees(n0.angle(n1)) if n0.length > 0 and n1.length > 0 else 0.0
    if ang > 28.0: cand.append((e.index, v0, v1, ang))
print(f"crease candidates in the upper-front face band z[{band_lo:+.4f},{band_hi:+.4f}]: {len(cand)}")

# cluster crease verts into connected groups through the crease edges themselves
adj = {}
for _, v0, v1, _ in cand:
    adj.setdefault(v0, []).append(v1); adj.setdefault(v1, []).append(v0)
seen, groups = set(), []
for v in adj:
    if v in seen: continue
    stack, comp = [v], []
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); comp.append(x)
        stack.extend(adj[x])
    groups.append(comp)
groups.sort(key=len, reverse=True)
# MERGE clusters that belong to the same socket. A 28-deg threshold catches only the
# sharpest folds, so one rim arrives as several arcs (inner corner, outer corner, brow).
merged = []
for g in groups:
    if len(g) < 4: continue
    c = co[np.array(g)].mean(axis=0)
    for m in merged:
        if np.linalg.norm(c - co[np.array(m)].mean(axis=0)) < 0.045:
            m.extend(g); break
    else:
        merged.append(list(g))
merged.sort(key=len, reverse=True)
print(f"after proximity merge: {len(merged)} rims, sizes {[len(m) for m in merged[:6]]}")
groups = merged
print(f"crease clusters: {len(groups)}  sizes {[len(g) for g in groups[:8]]}")
for i, g in enumerate(groups[:6]):
    G = co[np.array(g)]
    c = G.mean(axis=0)
    print(f"  cluster {i}: {len(g)} verts  centre ({c[0]:+.4f},{c[1]:+.4f},{c[2]:+.4f})  "
          f"lateral {float(c @ lat)-lat0:+.4f}  z-extent {G[:,2].max()-G[:,2].min():.4f}  "
          f"radius {np.linalg.norm(G-c, axis=1).max():.4f}")

# --- the two eye rims: symmetric clusters at opposite lateral offsets ---
cands = [(np.array(g), float(co[np.array(g)].mean(axis=0) @ lat) - lat0) for g in groups[:8] if len(g) > 20]
left  = [c for c in cands if c[1] < -0.01]
right = [c for c in cands if c[1] >  0.01]
if not (left and right):
    print("!! could not identify two symmetric eye rims -- inspect the clusters above")
    sys.exit(0)
L = max(left,  key=lambda c: len(c[0])); R = max(right, key=lambda c: len(c[0]))
print(f"\nEYE RIMS: left {len(L[0])} verts @ lateral {L[1]:+.4f}   right {len(R[0])} verts @ lateral {R[1]:+.4f}")

# --- fit a sphere to each dome: verts inside the rim, ahead of the rim plane ---
def analyse(rimidx, tag):
    rim = co[rimidx]
    c0 = rim.mean(axis=0)
    rad = np.linalg.norm(rim - c0, axis=1).max()
    # Outward direction for this socket: from the head axis through the rim centre.
    outv = c0 - np.array([hc[0], hc[1], c0[2]])
    outv = outv/max(np.linalg.norm(outv), 1e-9)
    # The DOME is the cap inside the rim that protrudes past the rim plane. Fitting a
    # sphere to a ball around the rim instead drags in surrounding skull and reports a
    # false "not spherical".
    d = np.linalg.norm(co - c0, axis=1)
    proj = (co - c0) @ outv
    near = np.where((d < rad*1.05) & (proj > -rad*0.15))[0]
    if len(near) < 30:
        near = np.where(d < rad*1.05)[0]
    A = np.c_[2*co[near], np.ones(len(near))]
    b = (co[near]**2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    ctr = sol[:3]; r = math.sqrt(max(sol[3] + (ctr**2).sum(), 1e-12))
    resid = np.abs(np.linalg.norm(co[near] - ctr, axis=1) - r)
    print(f"\n{tag}:")
    print(f"  rim: {len(rimidx)} verts, radius {rad:.4f} ({100*rad/H:.2f}% of body height)")
    print(f"  sphere fit on {len(near)} verts: r={r:.4f}  residual mean {resid.mean():.5f} max {resid.max():.5f}")
    print(f"  {'-> a genuine spherical dome' if resid.mean() < r*0.12 else '-> NOT spherical; flat/irregular'}")
    print(f"  dome cap isolated: {len(near)} verts, protrusion span {proj[near].max()-proj[near].min():.4f}")
    # how far must a lid travel to cover it?
    print(f"  aperture (rim opening) {2*rad:.4f}; a full blink must travel ~{2*rad:.4f} = {100*2*rad/H:.2f}% of height")
    # is there lid geometry BETWEEN the rim and the dome? count verts in the shell
    d = np.linalg.norm(co - c0, axis=1)
    shell = np.where((d > rad*0.98) & (d < rad*1.45))[0]
    print(f"  verts in the surrounding shell (candidate lid band): {len(shell)}")
    return c0, rad, ctr, r

cL = analyse(L[0], "LEFT eye"); cR = analyse(R[0], "RIGHT eye")

# ---- CANDIDATE BLINK: squash the eye region vertically toward its own midline.
# With no separate lid geometry this is how a stylised character blinks -- the skin
# closes over the dome. Build it as a shape key and LOOK at it; that is decisive,
# where more geometric analysis is not.
kb = ob.shape_key_add(name="Basis", from_mix=False)
sk = ob.shape_key_add(name="blink_test", from_mix=False)
for (c0, rad, ctr, r) in (cL, cR):
    reach = rad*1.55
    d = np.linalg.norm(co - c0, axis=1)
    sel = np.where(d < reach)[0]
    for i in sel:
        t = 1.0 - (d[i]/reach)
        t = max(0.0, min(1.0, t)); t = t*t*(3-2*t)
        dz = (c0[2] - co[i, 2])*t*0.92          # collapse toward the eye's horizontal midline
        sk.data[int(i)].co = Vector((co[i,0], co[i,1], co[i,2] + dz))
nblink = sum(int((np.linalg.norm(co - c[0], axis=1) < c[1]*1.55).sum()) for c in (cL, cR))
print(f"\nblink_test shape key: {nblink} verts moved across both eyes")

# --- paint the finding so it can be checked by eye ---
ca = me.color_attributes.get("eyemap") or me.color_attributes.new(name="eyemap", type='FLOAT_COLOR', domain='POINT')
cols = np.tile(np.array([0.55, 0.55, 0.58, 1.0]), (N, 1))
for idx, col in ((L[0], [1.0, 0.15, 0.1, 1]), (R[0], [0.1, 0.5, 1.0, 1])):
    cols[idx] = col
ca.data.foreach_set("color", cols.ravel())
me.color_attributes.active_color = ca
bm.free()

sc = bpy.context.scene
for o in [x for x in bpy.data.objects if x.type == 'ARMATURE']: o.hide_render = True
for o in [x for x in bpy.data.objects if x.type == 'CAMERA']: bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'VERTEX'
sc.render.resolution_x = sc.render.resolution_y = 800
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = 0.22
eyez = (cL[0][2] + cR[0][2])/2
Rr = H*5
def shoot(tag, off, colour, scale):
    sc.display.shading.color_type = colour
    cd.ortho_scale = scale
    ang = a + off
    cam.location = (hc[0]+math.sin(ang)*Rr, hc[1]-math.cos(ang)*Rr, eyez)
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
shoot("rim_front", 0.0, 'VERTEX', 0.22)
sc.display.shading.light = 'STUDIO'
for amt, lbl in ((0.0, "000"), (0.5, "050"), (1.0, "100")):
    sk.value = amt
    shoot(f"blink_{lbl}", 0.0, 'TEXTURE', 0.22)
    shoot(f"blinkwide_{lbl}", 0.0, 'TEXTURE', 0.34)
sk.value = 0.0
print("\nok")
