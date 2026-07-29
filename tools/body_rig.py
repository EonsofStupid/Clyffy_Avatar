"""VRM-humanoid body rig for Clyffy — waist-up presenter, legs authored but never framed.

    blender -b --python tools/body_rig.py -- <shapes.blend> <jaw_rig.blend> <out_dir> <fwd_deg>

Why this is not Blender bone-heat:
  ARMATURE_AUTO returns zero weights on this Tripo mesh (see jaw_rig.py, _heatdiag.py).
  Body weights are distance-to-bone-segment falloffs, renormalised. Jaw/skull/root weights
  are TRANSFERRED from the proven jaw_rig by vertex index (topology is identical).

Scope (clyffy.pack.toml [rig.scope]):
  * waist-up presenter — arms, hands, eyes/face
  * legs authored for VRM humanoid compliance, never framed
  * fingers: single hand bone for now (topology is welded; per-finger later)
  * ears + tail as non-humanoid extras (spring-bone candidates)
"""
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--")+1:]
SRC, JAW_RIG, OUT, FWD = (os.path.abspath(argv[0]), os.path.abspath(argv[1]),
                          os.path.abspath(argv[2]), float(argv[3]))
os.makedirs(OUT, exist_ok=True)

# ── load shapes (keeps shape keys) ────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH" and o.name.find("001") < 0][0]
# drop stray empty meshes from prior renders
for o in list(bpy.data.objects):
    if o.type == "MESH" and o != ob:
        bpy.data.objects.remove(o, do_unlink=True)
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT", "ARMATURE"):
        bpy.data.objects.remove(o, do_unlink=True)
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6
zmin, zmax = float(co[:, 2].min()), float(co[:, 2].max()); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); fwd /= np.linalg.norm(fwd)
lat = np.array([-fwd[1], fwd[0], 0.0])
fp, lp = co @ fwd, co @ lat
hc = co[co[:, 2] > 0.208].mean(axis=0); lat0 = float(hc @ lat)
mid = np.array([hc[0], hc[1], 0.0])
print(f"shapes mesh: {N} verts  H={H:.4f}  shape_keys="
      f"{len(me.shape_keys.key_blocks) if me.shape_keys else 0}")

# ── SIDE CONVENTION (L1 fix, 2026-07-27) ─────────────────────────────────────
# `lat = [-fwd[1], fwd[0], 0]` is fwd rotated +90° about Z, which IS the character's
# LEFT (face north, west is your left). This file previously used side = -1 for "L"
# — the comment even said "-1 left (neg lat)" — so every bone named _L was authored on
# the character's RIGHT. Verified on the shipped VRM: leftUpperLeg x=-0.062 vs
# rightUpperLeg x=+0.075 while the model faces +Z, i.e. 4/5 humanoid pairs mirrored.
#
# Why it matters: VRM humanoid names are SEMANTIC. Any consumer that mirrors or
# retargets an animation (three-vrm, Unity, Unreal) trusts leftUpperLeg to be the
# left leg. It also silently inverts any forward vector built from L/R bones — which
# is exactly what reported a false "spec-compliant" and cost an export cycle.
#
# Fixed by swapping the LABELS, not the geometry: the mesh was always correct.
SIDE_L, SIDE_R = +1, -1

# The upstream eye custom-props carry the same mirrored labelling (eye_open.py), so
# swap them here at the point of consumption rather than regenerating the whole face
# chain. eyeL below is the character's ACTUAL left eye.
eyeL = np.array(ob["eye_R_center"]); eyeR = np.array(ob["eye_L_center"])
eyeL_r = float(ob["eye_R_radius"]);  eyeR_r = float(ob["eye_L_radius"])

# ── transfer jaw/skull/root weights from proven jaw_rig ───────────────────────
# Topology is byte-identical (verified); pull the three groups by vertex index.
w_jaw = np.zeros(N); w_skull = np.zeros(N); w_root = np.zeros(N)
# stash current scene, open jaw rig in a throwaway way via bpy.data.libraries
with bpy.data.libraries.load(JAW_RIG, link=False) as (data_from, data_to):
    data_to.objects = [n for n in data_from.objects]
jmesh = None; jarm = None
for o in data_to.objects:
    if o is None: continue
    if o.type == "MESH" and jmesh is None and ".001" not in o.name:
        jmesh = o
    if o.type == "ARMATURE" and jarm is None:
        jarm = o
assert jmesh is not None and len(jmesh.data.vertices) == N, "jaw_rig mesh mismatch"
# get jaw hinge from jaw bone
assert jarm is not None
jb = jarm.data.bones.get("jaw")
hinge = np.array(jb.head_local) if jb else None
chin_pt = np.array(jb.tail_local) if jb else None
gi = {g.name: g.index for g in jmesh.vertex_groups}
def read_w(name, out):
    if name not in gi: return
    idx = gi[name]
    for v in jmesh.data.vertices:
        for g in v.groups:
            if g.group == idx: out[v.index] = g.weight
read_w("jaw", w_jaw); read_w("skull", w_skull); read_w("root", w_root)
print(f"transferred face weights: jaw {(w_jaw>0.01).sum()}  skull {(w_skull>0.01).sum()}  "
      f"root {(w_root>0.01).sum()}  hinge={hinge}")
# free the loaded library objects from the scene (they are orphaned data)
for o in list(data_to.objects):
    if o is not None:
        bpy.data.objects.remove(o, do_unlink=True)

# ── landmark detection ────────────────────────────────────────────────────────
def pct_z(p): return zmin + p * H

# hips: widest lateral band in lower torso
best_span, hips_z = -1, pct_z(0.35)
for z in np.linspace(pct_z(0.22), pct_z(0.42), 25):
    m = np.abs(co[:, 2] - z) < H*0.015
    if m.sum() < 80: continue
    span = float(lp[m].max() - lp[m].min())
    if span > best_span:
        best_span, hips_z = span, float(z)
hips_c = np.array([hc[0], hc[1], hips_z])

# chest / spine samples along the midplane
def spine_point(z):
    """Centre of the body at height z — by EXTENT, not by vertex mean.

    ⚠️ THIS USED `co[m].mean(axis=0)` AND THAT IS DENSITY-BIASED. A mean over vertices is not
    a geometric centre: it is pulled toward wherever the mesh happens to be finest. Adding
    ~940 loops in the lip skin (tools/densify.py) moved the neck sample from
    (-0.0623, 0.0353) to (-0.1034, 0.0641) — because the lip sits 0.045H from the neck slab
    and fell inside it — which dragged the SKULL bone with it and exported the character
    facing -179.79 deg off +Z. Every other check stayed green: the VRM still had 22 humanoid
    bones, 47 morphs and 3 spring chains, and only `vrm_check`'s facing test caught it.
    The midpoint of the slab's fore-aft EXTENT is density-independent, which is the property
    this needs — a rig must not move because a distant part of the mesh got finer.
    """
    m = (np.abs(co[:, 2] - z) < H*0.02) & (np.abs(lp - lat0) < H*0.06)
    if m.sum() < 10:
        m = np.abs(co[:, 2] - z) < H*0.02
    slab = co[m]
    f = slab @ fwd
    p = lat * lat0 + fwd * float(0.5 * (f.min() + f.max()))
    p = np.asarray(p, dtype=float)
    p[2] = z
    return p

spine_z = hips_z + H*0.10
chest_z = hips_z + H*0.22
neck_z  = float((eyeL[2] + eyeR[2]) / 2) - H*0.08
head_z  = float((eyeL[2] + eyeR[2]) / 2) - H*0.02
top_z   = zmax - H*0.02

spine_c = spine_point(spine_z)
chest_c = spine_point(chest_z)
neck_c  = spine_point(neck_z)
head_c  = spine_point(head_z)
top_c   = spine_point(top_z)

# shoulders: extreme lateral at chest height, slightly forward of spine
def shoulder(side):
    # side: +1 = character's LEFT (+lat), -1 = RIGHT. See SIDE_L/SIDE_R above.
    m = (co[:, 2] > chest_z - H*0.04) & (co[:, 2] < chest_z + H*0.08)
    if side < 0:
        i = np.where(m)[0][np.argmin(lp[m])]
    else:
        i = np.where(m)[0][np.argmax(lp[m])]
    # pull shoulder joint inward from the surface extreme
    p = co[i].copy()
    p = p - lat * side * H * 0.04   # inset toward body
    p[2] = chest_z + H*0.02
    return p

sh_L = shoulder(SIDE_L); sh_R = shoulder(SIDE_R)

# hand tips: extreme lateral low mid-body (arms hang at sides)
def hand_tip(side):
    m = (co[:, 2] > pct_z(0.35)) & (co[:, 2] < pct_z(0.58))
    if side < 0:
        i = np.where(m)[0][np.argmin(lp[m])]
    else:
        i = np.where(m)[0][np.argmax(lp[m])]
    return co[i].copy()

hand_L = hand_tip(SIDE_L); hand_R = hand_tip(SIDE_R)

def arm_chain(sh, hand):
    """elbow at 55% of shoulder→hand, wrist at 88%."""
    v = hand - sh
    elbow = sh + v * 0.52
    wrist = sh + v * 0.88
    return elbow, wrist, hand

elb_L, wr_L, hd_L = arm_chain(sh_L, hand_L)
elb_R, wr_R, hd_R = arm_chain(sh_R, hand_R)

# legs: from hips down to feet (stub for VRM; never framed)
def leg_chain(side):
    # hip joint: lateral offset from hips_c
    hip = hips_c + lat * side * H * 0.07
    hip[2] = hips_z
    # foot: lowest verts on that side
    m = (co[:, 2] < pct_z(0.12)) & ((lp - lat0) * side > 0)
    if m.sum() < 20:
        m = co[:, 2] < pct_z(0.12)
    foot = co[m].mean(axis=0)
    foot = foot - lat * (float(foot @ lat) - (lat0 + side * H * 0.05))
    foot[2] = zmin + H * 0.02
    knee = hip + (foot - hip) * 0.50
    ankle = hip + (foot - hip) * 0.90
    return hip, knee, ankle, foot

hip_L, knee_L, ank_L, foot_L = leg_chain(SIDE_L)
hip_R, knee_R, ank_R, foot_R = leg_chain(SIDE_R)

# ears: free edge = most lateral head vert; attachment = inset toward skull.
# Chain must span SURFACE mesh or tip bones get zero weights (fabricated tips
# past the mesh leave mid/tip empty — measured on the first spring pass).
def ear(side):
    m = co[:, 2] > eyeL[2] - H*0.02
    if side < 0:
        i = int(np.where(m)[0][np.argmin(lp[m])])
    else:
        i = int(np.where(m)[0][np.argmax(lp[m])])
    tip = co[i].copy()                                   # free edge on the mesh
    # attachment: step toward head centre + slightly down toward the temple
    toward = np.array([hc[0], hc[1], tip[2]]) - tip
    toward = toward / max(np.linalg.norm(toward), 1e-9)
    base = tip + toward * (H * 0.045) + np.array([0.0, 0.0, -H*0.01])
    # snap base onto the nearest skin vert so the root sits on geometry
    k = int(np.argmin(np.linalg.norm(co - base, axis=1)))
    base = co[k].copy()
    return base, tip

earL_b, earL_t = ear(SIDE_L); earR_b, earR_t = ear(SIDE_R)

# tail: free end = rearmost lower-mid body; attachment steps toward hips
m_tail = (co[:, 2] > pct_z(0.28)) & (co[:, 2] < pct_z(0.55))
i_tip = int(np.where(m_tail)[0][np.argmin(fp[m_tail])])
tail_tip = co[i_tip].copy()
tail_tip = tail_tip - lat * (float(tail_tip @ lat) - lat0)   # stay near midplane
toward_hips = hips_c - tail_tip
toward_hips = toward_hips / max(np.linalg.norm(toward_hips), 1e-9)
tail_base = tail_tip + toward_hips * (H * 0.10)
k = int(np.argmin(np.linalg.norm(co - tail_base, axis=1)))
tail_base = co[k].copy()

print("landmarks:")
for name, p in [("hips", hips_c), ("spine", spine_c), ("chest", chest_c), ("neck", neck_c),
                ("sh_L", sh_L), ("sh_R", sh_R), ("hand_L", hd_L), ("hand_R", hd_R),
                ("hip_L", hip_L), ("foot_L", foot_L)]:
    print(f"  {name:8s} ({p[0]:+.3f},{p[1]:+.3f},{p[2]:+.3f})")

# ── build armature (VRM-ish names) ────────────────────────────────────────────
ad = bpy.data.armatures.new("clyffy_rig")
arm = bpy.data.objects.new("clyffy_rig", ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones

def bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head = Vector(head); b.tail = Vector(tail)
    if parent is not None:
        b.parent = parent
        b.use_connect = connect
    # avoid zero-length
    if (b.tail - b.head).length < 1e-5:
        b.tail = b.head + Vector((0, 0, H*0.02))
    return b

# spine chain
hips   = bone("hips",   hips_c + np.array([0,0,-H*0.02]), hips_c)
spine  = bone("spine",  hips_c, spine_c, hips, True)
chest  = bone("chest",  spine_c, chest_c, spine, True)
neck   = bone("neck",   chest_c, neck_c, chest, True)
# skull = head bone (VRM "head"); keep name "skull" for jaw-weight compatibility
skull  = bone("skull",  neck_c, top_c, neck, True)
# jaw under skull (transferred weights)
if hinge is not None and chin_pt is not None:
    jaw = bone("jaw", hinge, chin_pt, skull, False)
    jaw.align_roll(Vector(np.cross(lat, chin_pt - hinge)))
else:
    jaw = bone("jaw", head_c + np.array([0,0,-H*0.04]), head_c + np.array([0,0,-H*0.08]), skull, False)

# eyes (lookAt targets — rigid weights applied later)
eye_L = bone("eye_L", eyeL, eyeL + fwd*max(eyeL_r*1.5, H*0.02), skull, False)
eye_R = bone("eye_R", eyeR, eyeR + fwd*max(eyeR_r*1.5, H*0.02), skull, False)

# shoulders / arms
def side_arm(tag, sh, elb, wr, hand, parent_bone):
    # VRM uses left/right with capitalisation; use lowercase_L style for groups
    s = bone(f"shoulder_{tag}", chest_c + (sh-chest_c)*0.35, sh, parent_bone, False)
    u = bone(f"upper_arm_{tag}", sh, elb, s, True)
    l = bone(f"lower_arm_{tag}", elb, wr, u, True)
    h = bone(f"hand_{tag}", wr, hand, l, True)
    return s, u, l, h

shb_L, ua_L, la_L, h_L = side_arm("L", sh_L, elb_L, wr_L, hd_L, chest)
shb_R, ua_R, la_R, h_R = side_arm("R", sh_R, elb_R, wr_R, hd_R, chest)

# legs (VRM required; never framed)
def side_leg(tag, hip, knee, ank, foot, parent_bone):
    u = bone(f"upper_leg_{tag}", hip, knee, parent_bone, False)
    l = bone(f"lower_leg_{tag}", knee, ank, u, True)
    f = bone(f"foot_{tag}", ank, foot, l, True)
    return u, l, f

ul_L, ll_L, f_L = side_leg("L", hip_L, knee_L, ank_L, foot_L, hips)
ul_R, ll_R, f_R = side_leg("R", hip_R, knee_R, ank_R, foot_R, hips)

# non-humanoid extras — multi-segment chains for VRM spring bones.
# A single bone cannot carry a spring joint chain; VRM springs need a parent→child
# sequence of joints. Three segments each: root / mid / tip.
def make_chain(prefix, base, tip, parent_bone, n=3):
    """Build n connected bones from base→tip. Returns list of (name, head, tail)."""
    base = np.asarray(base, float); tip = np.asarray(tip, float)
    segs = []
    prev = parent_bone
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        h = base + (tip - base) * t0
        t = base + (tip - base) * t1
        name = prefix if i == 0 else f"{prefix}_{i+1}"
        b = bone(name, h, t, prev, connect=(i > 0))
        segs.append((name, h.copy(), t.copy()))
        prev = b
    return segs

ear_L_chain = make_chain("ear_L", earL_b, earL_t, skull, n=3)
ear_R_chain = make_chain("ear_R", earR_b, earR_t, skull, n=3)
# Tail needs more length resolution — 4 segments for a cow tail.
tail_chain  = make_chain("tail",  tail_base, tail_tip, hips, n=4)
SPRING_CHAINS = {
    "ear_L": [s[0] for s in ear_L_chain],
    "ear_R": [s[0] for s in ear_R_chain],
    "tail":  [s[0] for s in tail_chain],
}
print(f"spring chains: {SPRING_CHAINS}")

bpy.ops.object.mode_set(mode='OBJECT')
bone_names = [b.name for b in ad.bones]
print(f"bones ({len(bone_names)}): {bone_names}")

# ── body weights: distance-to-segment, then composite with face weights ───────
def seg_dist(P, A, B):
    """Distance from points P (N,3) to segment AB."""
    AB = B - A
    L2 = float(AB @ AB)
    if L2 < 1e-12:
        return np.linalg.norm(P - A, axis=1)
    t = np.clip(((P - A) @ AB) / L2, 0.0, 1.0)
    proj = A + t[:, None] * AB
    return np.linalg.norm(P - proj, axis=1)

# body influence bones (not jaw/skull — those come from transfer)
BODY = {
    "hips":        (hips_c + np.array([0,0,-H*0.02]), hips_c,              H*0.12),
    "spine":       (hips_c, spine_c,                                       H*0.10),
    "chest":       (spine_c, chest_c,                                      H*0.11),
    "neck":        (chest_c, neck_c,                                       H*0.06),
    "shoulder_L":  (chest_c + (sh_L-chest_c)*0.35, sh_L,                   H*0.07),
    "shoulder_R":  (chest_c + (sh_R-chest_c)*0.35, sh_R,                   H*0.07),
    "upper_arm_L": (sh_L, elb_L,                                           H*0.055),
    "upper_arm_R": (sh_R, elb_R,                                           H*0.055),
    "lower_arm_L": (elb_L, wr_L,                                           H*0.050),
    "lower_arm_R": (elb_R, wr_R,                                           H*0.050),
    "hand_L":      (wr_L, hd_L,                                            H*0.055),
    "hand_R":      (wr_R, hd_R,                                            H*0.055),
    "upper_leg_L": (hip_L, knee_L,                                         H*0.08),
    "upper_leg_R": (hip_R, knee_R,                                         H*0.08),
    "lower_leg_L": (knee_L, ank_L,                                         H*0.07),
    "lower_leg_R": (knee_R, ank_R,                                         H*0.07),
    "foot_L":      (ank_L, foot_L,                                         H*0.06),
    "foot_R":      (ank_R, foot_R,                                         H*0.06),
}

# raw weights
W = {}
for name, (A, B, reach) in BODY.items():
    d = seg_dist(co, np.asarray(A, float), np.asarray(B, float))
    t = np.clip(1.0 - d / reach, 0.0, 1.0)
    W[name] = t * t * (3 - 2 * t)

# Spring-chain weights: envelope by distance to the chain polyline, then
# partition ALONG the chain with overlapping Gaussians in the base→tip
# parameter. Nearest-segment alone left tip bones empty (mesh rarely reaches
# the free end of a short ear); the u-parameter forces tip ownership of the
# outer third even when geometry is sparse there.
def chain_weights(segs, reach):
    """segs: list of (name, head, tail). Returns dict name→weight array."""
    n = len(segs)
    names = [s[0] for s in segs]
    base = np.asarray(segs[0][1], float)
    tip  = np.asarray(segs[-1][2], float)
    axis = tip - base
    L2 = float(axis @ axis)
    dmin = np.full(N, 1e9)
    for _, h, t in segs:
        dmin = np.minimum(dmin, seg_dist(co, np.asarray(h, float), np.asarray(t, float)))
    env = np.clip(1.0 - dmin / max(reach, 1e-9), 0.0, 1.0)
    env = env * env * (3 - 2 * env)
    if L2 < 1e-12:
        u = np.zeros(N)
    else:
        u = np.clip(((co - base) @ axis) / L2, 0.0, 1.0)
    # Gaussian membership; width covers ~1.4 segment lengths so neighbours overlap
    sigma = max(0.55 / n, 0.12)
    stack = np.zeros((N, n))
    for i in range(n):
        c = (i + 0.5) / n
        stack[:, i] = np.exp(-0.5 * ((u - c) / sigma) ** 2)
    s = stack.sum(axis=1, keepdims=True)
    s[s < 1e-9] = 1.0
    stack = stack / s * env[:, None]
    return {names[i]: stack[:, i] for i in range(n)}

for name, segs, reach in (
    ("ear_L", ear_L_chain, H*0.055),
    ("ear_R", ear_R_chain, H*0.055),
    ("tail",  tail_chain,  H*0.085),
):
    cw = chain_weights(segs, reach)
    for k, v in cw.items():
        W[k] = v
        print(f"  chain weight {k}: {(v>0.05).sum()} verts peak={v.max():.2f}")

# eyes: rigid on their groups
gi_src = {g.name: g.index for g in ob.vertex_groups}
def grp(name):
    if name not in gi_src: return np.array([], int)
    idx = gi_src[name]
    return np.array(sorted(v.index for v in me.vertices
                           for g in v.groups if g.group == idx and g.weight > 0.5))
EL, ER = grp("eye_L"), grp("eye_R")
W["eye_L"] = np.zeros(N); W["eye_R"] = np.zeros(N)
if len(EL): W["eye_L"][EL] = 1.0
if len(ER): W["eye_R"][ER] = 1.0

# Face lock: the transferred jaw/skull weights already know the head. Above the
# neck, ZERO every body bone (including neck) so a spine bend cannot shear the
# skull — hierarchical rotation of the skull bone handles head motion rigidly.
head_hard = np.clip((co[:, 2] - (neck_z - H*0.02)) / (H*0.05), 0, 1)
head_hard = head_hard * head_hard * (3 - 2 * head_hard)
# Face + ear-chain bones ride the skull hierarchy; do not zero them in the head.
FACE = {"skull", "jaw", "eye_L", "eye_R"} | set(SPRING_CHAINS["ear_L"]) | set(SPRING_CHAINS["ear_R"])
for name in list(W.keys()):
    if name not in FACE:
        W[name] = W[name] * (1.0 - head_hard)

# inject transferred face weights (overwrite any body bleed in the head)
W["jaw"] = w_jaw
W["skull"] = w_skull
# root from jaw_rig was body remainder under the head — fold into hips/spine,
# but only below the neck so we don't re-contaminate the face.
#
# ⚠️ F2 (2026-07-27): "body remainder under the head" includes the LEGS. Folding it
# into hips at 0.85 everywhere below the neck handed hips a blanket claim over the
# whole leg chain; after normalisation hips outvoted every leg bone, measured as
# hips max 0.850 / 32856 verts vs upper_leg_L 0.315, lower_leg_L 0.481, foot_L 0.389.
# The legs were bound but not poseable — rotating a leg bone only partly moved the
# limb. Gate the fold off below the hip joint with the same smoothstep idiom used
# for head_hard above. hips keeps its OWN Gaussian segment weight (SEG["hips"]), so
# the hip region stays bound; only the blanket remainder is withdrawn from the legs.
leg_soft = np.clip((hips_z - co[:, 2]) / (H * 0.06), 0, 1)
leg_soft = leg_soft * leg_soft * (3 - 2 * leg_soft)
# ⚠️ SAME DEFECT ON THE ARMS (2026-07-28). F2 gated the fold off the legs by HEIGHT, which
# the arms escape entirely: they hang beside the torso and share its z range, so the blanket
# remainder still outvoted every arm bone. Measured on the shipped rig: hand_L max 0.436,
# hand_R 0.443, and NOT ONE vertex majority-owned by either hand bone — the hands were bound
# but unposeable, exactly as the legs were before F2.
# Height cannot separate an arm from the ribs, so gate by DISTANCE TO THE ARM CHAIN instead,
# using the same segments and radii the arm bones are built from.
arm_soft = np.zeros(N)
for _nm in ("shoulder_L", "shoulder_R", "upper_arm_L", "upper_arm_R",
            "lower_arm_L", "lower_arm_R", "hand_L", "hand_R"):
    _A, _B, _R = BODY[_nm]
    _t = np.clip(1.0 - seg_dist(co, _A, _B) / (_R * 1.6), 0.0, 1.0)
    arm_soft = np.maximum(arm_soft, _t * _t * (3 - 2 * _t))
print(f"arm gate: {int((arm_soft > 0.5).sum())} verts withdraw the blanket root fold "
      f"(max {arm_soft.max():.3f})")
root_fold = w_root * (1.0 - head_hard) * (1.0 - leg_soft) * (1.0 - arm_soft)
W["hips"] = np.maximum(W.get("hips", np.zeros(N)), root_fold * 0.85)
W["spine"] = np.maximum(W.get("spine", np.zeros(N)), root_fold * 0.15)
# where the transfer says skull/jaw, kill body competition before normalise —
# but leave ear-chain weights alone (they sit on the head surface and must not
# be swallowed by the skull transfer).
face_dom = np.clip(w_jaw + w_skull, 0, 1)
EAR = set(SPRING_CHAINS["ear_L"]) | set(SPRING_CHAINS["ear_R"])
for name in list(W.keys()):
    if name not in FACE and name not in EAR:
        W[name] = W[name] * (1.0 - face_dom)
# skull should not own verts the ear chain already claims
ear_dom = np.zeros(N)
for en in EAR:
    if en in W: ear_dom = np.maximum(ear_dom, W[en])
if "skull" in W:
    W["skull"] = W["skull"] * (1.0 - np.clip(ear_dom, 0, 1))

# teeth/tongue: jaw-anchored already in w_jaw; upper teeth on skull
for gname, bname in (("teeth_lower", "jaw"), ("tongue", "jaw"),
                     ("teeth_upper", "skull")):
    g = grp(gname)
    if len(g) == 0: continue
    for k in W: W[k][g] = 0.0
    W[bname][g] = 1.0

# eyes rigid
for tag, g in (("eye_L", EL), ("eye_R", ER)):
    if len(g) == 0: continue
    for k in W: W[k][g] = 0.0
    W[tag][g] = 1.0

# normalise: partition of unity, max 4 influences
names = list(W.keys())
M = np.stack([W[n] for n in names], axis=1)  # (N, B)
# zero tiny
M[M < 0.02] = 0.0
# keep top-4 per vertex
for i in range(N):
    row = M[i]
    if (row > 0).sum() <= 4: continue
    thr = np.partition(row, -4)[-4]
    row[row < thr] = 0.0
    M[i] = row
s = M.sum(axis=1, keepdims=True)
s[s < 1e-9] = 1.0
M = M / s
# any leftover zeros (isolated verts) → hips
orphan = M.sum(axis=1) < 0.5
if orphan.any():
    hi = names.index("hips")
    M[orphan, :] = 0.0
    M[orphan, hi] = 1.0
print(f"weight matrix: {M.shape[1]} bones, orphans snapped to hips: {int(orphan.sum())}")

# clear old armature groups if any, write new
for n in ("jaw", "skull", "root"):
    g = ob.vertex_groups.get(n)
    if g: ob.vertex_groups.remove(g)
for n in names:
    g = ob.vertex_groups.get(n)
    if g: ob.vertex_groups.remove(g)
    g = ob.vertex_groups.new(name=n)
    col = M[:, names.index(n)]
    for i in np.where(col > 1e-4)[0]:
        g.add([int(i)], float(col[i]), 'REPLACE')

mod = ob.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
# shape keys + armature: keep armature above shape keys is Blender default order issue —
# with shape keys present, armature modifier deforms the shaped mesh. Good.
ob.parent = arm

# validation
tot = M.sum(axis=1); infl = (M > 1e-4).sum(axis=1)
print(f"skin validation: Σw min {tot.min():.6f} max {tot.max():.6f} "
      f"|1-Σ|max {np.abs(tot-1).max():.2e}  influences/vert max {infl.max()} "
      f"({'OK' if infl.max() <= 4 else '** >4 **'})")

# ── pose tests ────────────────────────────────────────────────────────────────
def eval_co():
    dg = bpy.context.evaluated_depsgraph_get()
    obe = ob.evaluated_get(dg); ev = obe.to_mesh()
    v = np.empty((N, 3)); ev.vertices.foreach_get("co", v.ravel()); obe.to_mesh_clear()
    return v

def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()

def rotate_bone(name, axis, deg):
    pb = arm.pose.bones[name]
    pb.rotation_mode = 'XYZ'
    # axis in bone local: approximate with euler
    e = list(pb.rotation_euler)
    ax = {"x": 0, "y": 1, "z": 2}[axis]
    e[ax] = math.radians(deg)
    pb.rotation_euler = e
    bpy.context.view_layer.update()

reset_pose()
base = eval_co()
report = {"bones": bone_names, "n_verts": N, "shape_keys":
          [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
          "tests": []}

# arm raise L
rotate_bone("upper_arm_L", "x", -55)
d = eval_co(); disp = np.linalg.norm(d - base, axis=1)
report["tests"].append({"pose": "upper_arm_L raise -55x",
                        "moved": int((disp > 1e-4).sum()),
                        "max": float(disp.max()),
                        "max_pctH": float(100*disp.max()/H)})
print(f"test arm_L raise: moved {(disp>1e-4).sum()} max {disp.max():.4f} ({100*disp.max()/H:.1f}%H)")
reset_pose()

# arm raise R
rotate_bone("upper_arm_R", "x", -55)
d = eval_co(); disp = np.linalg.norm(d - base, axis=1)
report["tests"].append({"pose": "upper_arm_R raise -55x",
                        "moved": int((disp > 1e-4).sum()),
                        "max": float(disp.max()),
                        "max_pctH": float(100*disp.max()/H)})
print(f"test arm_R raise: moved {(disp>1e-4).sum()} max {disp.max():.4f} ({100*disp.max()/H:.1f}%H)")
reset_pose()

# spine bend (modest — hierarchical, head should ride without shearing)
rotate_bone("spine", "x", 8)
rotate_bone("chest", "x", 6)
d = eval_co(); disp = np.linalg.norm(d - base, axis=1)
# head shear check: skull-weighted verts should move nearly rigidly (low variance of disp)
sk = w_skull > 0.5
head_disp = disp[sk] if sk.any() else disp[:1]
report["tests"].append({"pose": "spine+chest bend",
                        "moved": int((disp > 1e-4).sum()),
                        "max": float(disp.max()),
                        "max_pctH": float(100*disp.max()/H),
                        "skull_disp_std": float(head_disp.std()) if sk.any() else None,
                        "skull_disp_mean": float(head_disp.mean()) if sk.any() else None})
print(f"test spine bend: moved {(disp>1e-4).sum()} max {disp.max():.4f} ({100*disp.max()/H:.1f}%H)  "
      f"skull disp mean/std {head_disp.mean():.4f}/{head_disp.std():.4f}")
reset_pose()

# jaw still works
if "jaw" in arm.pose.bones and hinge is not None:
    pb = arm.pose.bones["jaw"]
    hv, lv = Vector(hinge), Vector(lat)
    R = Matrix.Translation(hv) @ Matrix.Rotation(math.radians(22), 4, lv) @ Matrix.Translation(-hv)
    pb.matrix = R @ pb.bone.matrix_local
    bpy.context.view_layer.update()
    d = eval_co(); disp = np.linalg.norm(d - base, axis=1)
    report["tests"].append({"pose": "jaw 22deg",
                            "moved": int((disp > 1e-4).sum()),
                            "max": float(disp.max()),
                            "max_pctH": float(100*disp.max()/H)})
    print(f"test jaw 22deg: moved {(disp>1e-4).sum()} max {disp.max():.4f} ({100*disp.max()/H:.1f}%H)")
    reset_pose()

# eye look
if "eye_L" in arm.pose.bones:
    rotate_bone("eye_L", "z", 16)
    rotate_bone("eye_R", "z", 16)
    d = eval_co(); disp = np.linalg.norm(d - base, axis=1)
    report["tests"].append({"pose": "eyes look +16z",
                            "moved": int((disp > 1e-4).sum()),
                            "max": float(disp.max()),
                            "max_pctH": float(100*disp.max()/H)})
    print(f"test eyes: moved {(disp>1e-4).sum()} max {disp.max():.4f} ({100*disp.max()/H:.1f}%H)")
    reset_pose()

# Record spring chains for tools/spring_bones.py / vrm_export.py
report["spring_chains"] = SPRING_CHAINS
arm["spring_chains"] = json.dumps(SPRING_CHAINS)  # custom prop on the armature object

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_body.blend"))
with open(os.path.join(OUT, "body_rig_report.json"), "w") as f:
    json.dump(report, f, indent=2)

# ── renders ───────────────────────────────────────────────────────────────────
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"
sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 720; sc.render.resolution_y = 900
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*40; cd.ortho_scale = H*1.15
ctr = np.array([hc[0], hc[1], (zmin+zmax)/2]); Rr = H*4.5

def shoot(tag, pose_fn=None):
    reset_pose()
    if pose_fn: pose_fn()
    ang = a
    cam.location = (ctr[0]+math.sin(ang)*Rr, ctr[1]-math.cos(ang)*Rr, ctr[2])
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"body_{tag}.png")
    bpy.ops.render.render(write_still=True)

shoot("REST")
shoot("armL", lambda: rotate_bone("upper_arm_L", "x", -55))
shoot("armR", lambda: rotate_bone("upper_arm_R", "x", -55))
shoot("arms", lambda: (rotate_bone("upper_arm_L", "x", -50), rotate_bone("upper_arm_R", "x", -50)))
shoot("spine", lambda: (rotate_bone("spine", "x", 12), rotate_bone("chest", "x", 10)))
# three-quarter waist-up
cd.ortho_scale = H*0.70
ctr_wu = np.array([hc[0], hc[1], hips_z + H*0.25])
def shoot_wu(tag, pose_fn=None):
    reset_pose()
    if pose_fn: pose_fn()
    ang = a + math.radians(25)
    cam.location = (ctr_wu[0]+math.sin(ang)*Rr, ctr_wu[1]-math.cos(ang)*Rr, ctr_wu[2])
    cam.rotation_euler = (math.radians(90), 0, ang)
    sc.render.filepath = os.path.join(OUT, f"body_wu_{tag}.png")
    bpy.ops.render.render(write_still=True)
shoot_wu("REST")
shoot_wu("arms", lambda: (rotate_bone("upper_arm_L", "x", -50), rotate_bone("upper_arm_R", "x", -50)))
reset_pose()
print("ok")
