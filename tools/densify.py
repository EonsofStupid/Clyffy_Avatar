"""Add edge loops in the lip skin so the shapes have mesh to deform WITH.

    blender -b --python tools/densify.py -- <eyes.blend> <out_dir> <fwd_deg> [cuts] [reach]

⚠️ RUNS AFTER `eye_open --cut`, NOT after `canonicalize`. Two hard constraints put it here,
both found by trying the obvious placement first:

  1. THE EYE CUT IS FRAGILE. Densifying before it destabilises the separation. Measured:
     baseline yields 3 connected components (body + 2 eyeballs); at reach 0.070 it yields
     5 — sizes [47348, 640, 425, 102, 42] — and at 0.060 still 4. `eye_open` requires
     EXACTLY 2 eyeball components and silently skips writing `eye_L_center` /
     `eye_L_radius` / `eye_R_center` / `eye_R_radius` when it does not get them, which then
     kills `face_atlas` four stages later with a bare KeyError. Reach 0.085 additionally
     pinched the left dome boundary (degree-4 vertex) and refused to cut at all.
  2. `cav_src` CANNOT BE INTERPOLATED. `mouth_open` writes it as an INT layer — each bag
     vertex records the lip-rim vertex it was extruded from — and `jaw_rig` skins the bag by
     that lineage. Subdividing a cavity edge would hand the new vertex a meaningless average
     of two ancestor INDICES. So this only ever touches SKIN.

Running here costs nothing: the fold this fixes happens in `shape_author`, six stages later.

WHY. The upper lip tears in open-mouth poses — face normals invert, the surface folds through
itself (26 flips on `happy`, 24 on `aa`). Smoothing the displacement field was tried and
rejected: it cannot fix a fold caused by there being too little mesh to fold WITH. The
measurement that settles it:

    lip-region median edge, canon (pre-cut) : 0.00373  = 0.73x the global median
    lip-region median edge, final body      : 0.00691  = 1.35x the global median

The lip starts FINER than the rest of the head and ends up 35% COARSER. `mouth_open` opens
the pocket by stretching the rings it already has rather than adding any, so by the time the
shapes ask the lip to move 2.4%H there is nothing left to absorb it. Adding loops here — up
front, before the pocket is opened — gives that stretch somewhere to go.

WHAT IT MUST NOT BREAK. The operator hand-selected `op_jaw_region` (390 verts) and
`op_lip_seam` (81) on this mesh, and the whole lip atlas is bounded by them — those
selections are not reproducible and must survive. bmesh interpolates the deform layer across
a subdivision, so weights carry; this script VERIFIES that rather than trusting it, and
refuses to save if a group loses members.
"""
import bpy, bmesh, sys, os, math
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
CUTS  = int(argv[3]) if len(argv) > 3 else 1      # loops inserted per edge
REACH = float(argv[4]) if len(argv) > 4 else 0.085  # of H, around the lip seam
# ⚠️ EYELID DENSIFICATION IS OFF BY DEFAULT — TRIED, MEASURED, REJECTED (2026-07-29).
# Pass a non-zero multiple to re-enable it; the shipped value is 0.0 for the reasons below.
# At 2.2x eyeball radius it adds +3087 verts (46838 -> 50865 with the lip) and buys NOTHING:
#
#   fold rate per moved vertex   eyeBlinkLeft  43/489  = 0.088  ->  177/1920 = 0.092  WORSE
#                                eyeSquintLeft 40/735  = 0.054  ->  137/2288 = 0.060  WORSE
#                                eyeWideLeft   34/489  = 0.070  ->  127/1920 = 0.066  ~same
#
# and the RENDER agrees — side by side at the same framing the denser lid is slightly worse,
# because the fold does not go away, it just resolves into finer and more visible creasing.
# The reason is the one already recorded in [shapes.surface_fold]: A CLOSING EYELID GENUINELY
# FOLDS. It is not a resolution deficit, so resolution does not fix it. The LIP is different —
# there the mesh was measurably stretched by mouth_open (1.35x the global median edge) and
# adding loops demonstrably helped. Do not assume the two cases are the same problem.
EYE_MULT = float(argv[5]) if len(argv) > 5 else 0.0   # eyelid band, as a multiple of eyeball radius
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
N0, F0 = len(me.vertices), len(me.polygons)
co = np.empty((N0, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])

gi = {g.name: g.index for g in ob.vertex_groups}
def members(name):
    if name not in gi: return set()
    k = gi[name]
    return {v.index for v in me.vertices if any(g.group == k for g in v.groups)}

BEFORE = {g.name: len(members(g.name)) for g in ob.vertex_groups}
print(f"{os.path.basename(SRC)}: {N0} verts, {F0} faces")
print("groups before:", {k: v for k, v in BEFORE.items() if v})

# ── seed the regions to densify ─────────────────────────────────────────────
# The LIP comes from the operator's own seam selection, not a guessed radius — the same rule
# face_atlas follows. Eyes come from the eyeball custom props the pipeline already stores.
lip_seed = members("op_lip_seam")
if not lip_seed:
    raise SystemExit("no op_lip_seam group — refusing to guess where the lip is")
lip_ctr = co[sorted(lip_seed)].mean(axis=0)
d_lip = np.linalg.norm(co - lip_ctr, axis=1)
sel = d_lip < H * REACH
n_lip = int(sel.sum())

# EYELID SKIN. Withheld on the first pass out of caution about the eye cut — unnecessary,
# because by this stage the cut has ALREADY HAPPENED and cannot be affected. Verified before
# extending the patch here: the eyes blend reports boundary 19, which is only the inherited
# torso hole, so the separation leaves BOTH pieces closed and there is no open socket for
# mesh_patch to wrongly fill later.
# The eyeball SHELLS are still excluded (below) — they are separate closed spheres and
# subdividing them would only cost vertices. This band is the lid skin around each socket,
# which is what folds when eyeBlink/eyeSquint/eyeWide drive it.
n_eye = 0
for tag in ("L", "R"):
    key = f"eye_{tag}_center"
    if key in ob.keys():
        c = np.array(ob[key]); r = float(ob.get(f"eye_{tag}_radius", H * 0.03))
        band = np.linalg.norm(co - c, axis=1) < r * EYE_MULT
        n_eye += int(band.sum())
        sel |= band
n_tot = int(sel.sum())
print(f"densify seeds: lip {n_lip} verts (reach {REACH:.3f}H around op_lip_seam) + "
      f"eyelids {n_eye} verts ({EYE_MULT:.1f}x eyeball radius) -> {n_tot} selected")

# ── EXCLUSIONS: the cavity, and the eyeballs ────────────────────────────────
# The cavity is off-limits because of `cav_src` (see the module docstring). The eyeballs are
# separate shells by this point and subdividing them would only cost verts.
di = {i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")}
cav_faces = {i for i, p in enumerate(me.polygons) if p.material_index in di}
cav_verts = {v for i in cav_faces for v in me.polygons[i].vertices}
eyeballs = set()
for tag in ("eye_L", "eye_R"):
    eyeballs |= members(tag)
if cav_verts:
    print(f"  excluding {len(cav_verts)} cavity verts (cav_src lineage is an INT layer)")
if eyeballs:
    print(f"  excluding {len(eyeballs)} eyeball verts")

bm = bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
selset = set(np.where(sel)[0].tolist()) - cav_verts - eyeballs
# Take whole FACES, then their edges — subdividing a loose edge set leaves n-gons behind.
# A face is only eligible if EVERY vertex is in the patch, which automatically keeps the
# subdivision off the lip rim itself (rim verts are cavity verts and therefore excluded).
faces = [f for f in bm.faces
         if f.index not in cav_faces and all(v.index in selset for v in f.verts)]
edges = list({e for f in faces for e in f.edges})
print(f"  patch: {len(faces)} faces, {len(edges)} edges, {CUTS} cut(s) each")

L0 = np.array([e.calc_length() for e in edges])
res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=CUTS, use_grid_fill=True)
bm.verts.index_update(); bm.faces.index_update()
bm.to_mesh(me); bm.free(); me.update()

N1, F1 = len(me.vertices), len(me.polygons)
co1 = np.empty((N1, 3)); me.vertices.foreach_get("co", co1.ravel())
pairs = set()
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k + 1) % len(vs)]
        pairs.add((min(i, j), max(i, j)))
E = np.array(sorted(pairs))
Lall = np.linalg.norm(co1[E[:, 0]] - co1[E[:, 1]], axis=1)
lc = np.linalg.norm(co1 - lip_ctr, axis=1)
near = (lc[E[:, 0]] < H * 0.10) | (lc[E[:, 1]] < H * 0.10)
print(f"  verts {N0} -> {N1} (+{N1-N0})   faces {F0} -> {F1} (+{F1-F0})")
print(f"  lip-region median edge {np.median(L0):.5f} -> {np.median(Lall[near]):.5f} "
      f"({100*np.median(Lall[near])/H:.2f}%H)  global median {np.median(Lall):.5f} "
      f"-> ratio {np.median(Lall[near])/np.median(Lall):.2f}x")

# ── the operator's selections MUST survive ──────────────────────────────────
AFTER = {g.name: len(members(g.name)) for g in ob.vertex_groups}
bad = [k for k in BEFORE if BEFORE[k] and AFTER.get(k, 0) < BEFORE[k]]
print("groups after:", {k: v for k, v in AFTER.items() if v})
if bad:
    raise SystemExit(f"!! REFUSING TO SAVE — vertex group(s) LOST members: "
                     + ", ".join(f"{k} {BEFORE[k]}->{AFTER[k]}" for k in bad))
for k in BEFORE:
    if BEFORE[k] and AFTER[k] > BEFORE[k]:
        print(f"  {k}: {BEFORE[k]} -> {AFTER[k]} (subdivision interpolated new members — expected)")

bm2 = bmesh.new(); bm2.from_mesh(me)
nmf = sum(1 for e in bm2.edges if not e.is_manifold and not e.is_boundary)
bdf = sum(1 for e in bm2.edges if e.is_boundary)
bm2.free()
print(f"hygiene: non-manifold {nmf} boundary {bdf}")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_eyes.blend"))
print("saved clyffy_v2_eyes.blend")
