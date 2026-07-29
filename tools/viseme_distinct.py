"""Are the visemes actually DISTINGUISHABLE? Measured, not eyeballed.

    blender -b --python tools/viseme_distinct.py -- <body.blend> [fwd_deg]

The face is the product and talking is the demo, so the question that decides whether this
is a solid alpha is not "does each viseme render" — every sheet in the pack already shows
that — but "can a viewer TELL THEM APART". Nothing in the pack has ever asked that.

Method. Pose the rig into each pinned viseme through the SAME path the contract uses (jaw
bone from ENVELOPE, morphs by name), take the evaluated mouth-region vertices, and measure
the RMS displacement between every pair. Two visemes whose mouth geometry differs by less
than the rig's own noise floor are the same shape wearing two names, and no amount of
lipsync accuracy upstream will make them read.

Reported against %H so the numbers are comparable with every other measurement in the pack.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import VISEMES, ENVELOPE  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
RIG = os.path.abspath(argv[0])
FWD = float(argv[1]) if len(argv) > 1 else 235.1
MAXDEG = float(ENVELOPE["jaw"]["max_deg"])

bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
me = ob.data
kb = me.shape_keys.key_blocks if me.shape_keys else None
assert kb is not None, "no shape keys"
N = len(me.vertices)
base = np.empty((N, 3)); kb["Basis"].data.foreach_get("co", base.ravel())
H = float(base[:, 2].max() - base[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])
lv = Vector(lat)

# Mouth region: everything within a generous radius of the cavity centroid, plus the parts.
di = [i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")]
cav = sorted({v for p in me.polygons if p.material_index in di for v in p.vertices})
mouth = base[cav].mean(axis=0)
d = np.linalg.norm(base - mouth, axis=1)
REGION = np.where(d < H * 0.13)[0]
gi = {g.name: g.index for g in ob.vertex_groups}
for n in ("tongue", "teeth_upper", "teeth_lower"):
    if n in gi:
        k = gi[n]
        extra = [v.index for v in me.vertices
                 if any(g.group == k and g.weight > 0.5 for g in v.groups)]
        REGION = np.union1d(REGION, np.array(extra, dtype=int))
print(f"mesh {N} verts, H {H:.4f}, mouth region {len(REGION)} verts")

jaw_b = arm.pose.bones.get("jaw") if arm else None
hv = Vector(jaw_b.bone.head_local) if jaw_b else Vector((0, 0, 0))

def evaluate(mix):
    for k in kb:
        if k.name != "Basis": k.value = 0.0
    jaw = 0.0
    for n, v in mix.items():
        if n == "jawOpen":
            jaw = float(v); continue
        if n in kb and n != "Basis":
            kb[n].value = float(max(0.0, min(1.0, v)))
    if jaw_b:
        jaw_b.rotation_mode = "QUATERNION"
        jaw_b.matrix = jaw_b.bone.matrix_local.copy()
        if jaw > 0.0:
            ang = math.radians(MAXDEG) * max(0.0, min(1.0, jaw))
            R = (Matrix.Translation(hv) @ Matrix.Rotation(ang, 4, lv) @ Matrix.Translation(-hv))
            jaw_b.matrix = R @ jaw_b.bone.matrix_local
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    obe = ob.evaluated_get(dg); ev = obe.to_mesh()
    C = np.empty((N, 3)); ev.vertices.foreach_get("co", C.ravel()); obe.to_mesh_clear()
    return C[REGION]

names = list(VISEMES.keys())
P = {}
for n in names:
    P[n] = evaluate(dict(VISEMES[n]))

# travel from silence — how much each viseme actually moves the mouth at all
print("\nTRAVEL FROM sil (RMS over the mouth region)")
sil = P.get("sil", P[names[0]])
trav = {}
for n in names:
    r = float(np.sqrt(((P[n] - sil) ** 2).sum(axis=1).mean()))
    trav[n] = 100 * r / H
for n in sorted(names, key=lambda x: -trav[x]):
    bar = "#" * int(trav[n] * 12)
    print(f"  {n:<5} {trav[n]:5.2f}%H  {bar}")

# ── TWO METRICS, because RMS alone is not a fair judge ───────────────────────
# RMS over a FIXED region is dominated by how MANY vertices move, not by how distinctive the
# shape is. A jaw drop moves thousands of verts a little and scores high; a sibilant's spread
# lips move ~230 verts a lot and score low, even though a viewer reads the second one
# instantly. Measured: SS moves the mouth 0.28%H RMS while `mouthStretch` alone is a 2.10%H
# shape — the dilution is real and it is a property of the metric, not of the face.
#
# So report BOTH and judge on both:
#   RMS  — "how different does the whole mouth look" (global similarity)
#   P95  — 95th-percentile per-vertex displacement, "is there a distinct LOCAL feature"
# A pair that is close on BOTH is genuinely the same shape twice. A pair close on RMS but
# separated on P95 has a real local difference the RMS is averaging away.
print("\nPAIRWISE SEPARATION (RMS %H). Pairs under the threshold are the same shape twice.")
M = np.zeros((len(names), len(names)))
Q = np.zeros((len(names), len(names)))
for i, x in enumerate(names):
    for j, y in enumerate(names):
        if i < j:
            dv = np.linalg.norm(P[x] - P[y], axis=1)
            r = float(np.sqrt((dv ** 2).mean()))
            M[i, j] = M[j, i] = 100 * r / H
            Q[i, j] = Q[j, i] = 100 * float(np.percentile(dv, 95)) / H
hdr = "        " + "".join(f"{n:>6}" for n in names)
print(hdr)
for i, x in enumerate(names):
    row = "".join((f"{M[i,j]:6.2f}" if i != j else "     ·") for j in range(len(names)))
    print(f"  {x:<5} {row}")

THRESH = 0.25    # %H RMS — below this the whole-mouth difference is at shading-noise level
P95_THRESH = 0.60  # %H — below this there is no distinct local feature either
pairs = [(names[i], names[j], M[i, j], Q[i, j])
         for i in range(len(names)) for j in range(i + 1, len(names))]
pairs.sort(key=lambda t: t[2])
print(f"\nCLOSEST PAIRS (RMS threshold {THRESH:.2f}%H · P95 threshold {P95_THRESH:.2f}%H)")
bad = [p for p in pairs if p[2] < THRESH and p[3] < P95_THRESH]
soft = [p for p in pairs if p[2] < THRESH and p[3] >= P95_THRESH]
for x, y, v, q in pairs[:12]:
    if v < THRESH and q < P95_THRESH:
        flag = "  <-- INDISTINGUISHABLE (both metrics)"
    elif v < THRESH:
        flag = "  (close overall, but a real local difference)"
    else:
        flag = ""
    print(f"  {x:<5} vs {y:<5} RMS {v:5.2f}%H  P95 {q:5.2f}%H{flag}")
print(f"\n{len(bad)} of {len(pairs)} pairs fail BOTH metrics; {len(soft)} are RMS-close only")
print(f"RMS  median {np.median([p[2] for p in pairs]):.2f}%H  "
      f"min {min(p[2] for p in pairs):.2f}%H  max {max(p[2] for p in pairs):.2f}%H")
print(f"P95  median {np.median([p[3] for p in pairs]):.2f}%H  "
      f"min {min(p[3] for p in pairs):.2f}%H  max {max(p[3] for p in pairs):.2f}%H")
# ⚠️ NOT EVERY PAIR SHOULD SEPARATE. Lipreading groups phonemes into viseme CLASSES for a
# reason: /p,b,m/ look alike on a real face, so do /k,g,ng/. The Oculus 15-viseme set this
# pack pins already collapses those. The standard is "pairs a human distinguishes should
# separate", not "all 105 pairs separate" — chasing the latter would be fitting the metric.
dead = [n for n in names if trav[n] < 0.10 and n != "sil"]
if dead:
    print(f"!! visemes that barely move at all: {dead}")
print("ok")
