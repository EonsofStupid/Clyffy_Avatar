"""Author the face MATERIALS: one continuous muzzle pad, SSS, roughness. Adds NO geometry.

    blender -b --python tools/materials.py -- <body.blend> <out_dir> [fwd_deg]

Runs AFTER mesh_patch (which adds faces, so anything keyed to face indices would be invalidated
by it) and BEFORE vrm_export.

═══ WHY THIS STAGE EXISTS ═══════════════════════════════════════════════════════════════════

Two measured CANON violations in the delivered build, neither of which any gate was asking about:

  1. `CANON.md` §1: "Subsurface scattering fur/feathers/skin — NO exceptions".
     Measured by tools/_matstate.py: SSS weight = 0.0 on all five materials. Pure plastic.

  2. `CANON.md`: "Broad pink muzzle."
     Measured by tools/_lipbands.py: the baked Tripo atlas paints the WHOLE muzzle near-white —
     6.9 out of 441 between the lip and the surrounding pad. There is no pink on the face at all,
     so a material pass has to carry COLOUR, not just surface response.

`present.py` has a `polish_materials()` that sets SSS at RENDER time, in RAM, and never saves, so
the hero PNGs showed subsurface the delivered VRM did not have. That is why (1) went unnoticed for
a week while the pictures looked fine. It now stands down when the mesh carries authored materials.

═══ THE REFERENCE — AND THE ONE I GOT WRONG ═════════════════════════════════════════════════

PRIMARY:     canon/reference/  — see canon/reference/SPEC.md (flat-lit, true 90° profile)
ARCHIVED:    canon/_archive/  — every earlier set; do not measure albedo from those

The first version of this stage used frames pulled from the operator's reference VIDEOS instead
(canon/mouth_ref/v1_*.png, v2_*.png). Both are badly graded for colour — one is a blue night scene
where white fur measures (113,160,217) — and worse, the samples I took off them landed on SHADED
muzzle, which I then used as the albedo of the whole pad. The arithmetic was careful and the input
was wrong:

    canon base sheet, lit pad    Y/Yfur 0.80-0.89   chroma 1.31 : 0.92 : 0.83
    canon anchor, lit pad        Y/Yfur 0.63-0.70   chroma 1.41-1.50 : 0.88 : 0.74
    what the video frames gave   Y/Yfur 0.496       chroma 1.76 : 0.81 : 0.66
    canon anchor, SHADED under   Y/Yfur 0.373       chroma 1.76 : 0.81 : 0.62   <- the match

40% too dark and 35% too saturated: an orange rubber pad instead of a soft pink muzzle. Use a
NEUTRALLY LIT reference for albedo. Graded frames are for structure and mood, never for colour.

═══ NO LIP BANDS ════════════════════════════════════════════════════════════════════════════

The mouth is a SLIT IN THE PAD. The lips are the pad continuing; the dark lip line is geometry
and occlusion, not paint. An earlier version painted three concentric bands (salmon inner rim ->
cream outer band -> fur), which is HUMAN vermilion-border anatomy and is on neither canon source.
Operator, on seeing it: "stop trying to human mouth this."

That structure was never measured. I wrote it as prose into canon/mouth_ref/README.md off a
low-resolution plate, then measured colour rigorously in service of it — precise execution of an
invented spec. Measuring hard does not make the target right.

═══ HOW ═════════════════════════════════════════════════════════════════════════════════════

Colour rides a per-vertex ATTRIBUTE, not a material split: a material holds a CONSTANT, so N
materials mean N-1 hard seams, and `CANON.md` bans ink outlines and flat/cel looks. The tint is a
RATIO relative to fur (fur stays exactly 1.0), so the atlas keeps all its own variation — pores,
shading, the Holstein black patches — and only the hue and level shift where the pad is.

The genuine material splits that already exist (cavity / teeth / tongue / hoof) are kept, because
those are real discontinuities rather than a gradient. For those, only HUE is rotated onto the
measurement and the tuned LUMINANCE is preserved: their in-frame brightness is occlusion, not
albedo, and darkening the albedo too would double-count.

Trade-off stated plainly: the float attribute driving roughness and SSS does NOT survive glTF
export, so the web renderer gets colour (COLOR_0 does export, via tools/vrm_color0_fix.py) but not
the surface response. Cycles/EEVEE gets everything.
"""
import bpy, sys, os, math, heapq
from collections import defaultdict
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2]) if len(argv) > 2 else 235.1
os.makedirs(OUT, exist_ok=True)

# ── measured targets ────────────────────────────────────────────────────────────────────────
# chroma = (R,G,B) normalised to unit luminance, MEASURED by tools/_refcolor.py.
# ylev    = albedo luminance as a fraction of the fur's.
#           "meas" = the frame's own Y ratio, trusted (adjacent + similarly lit + cross-frame).
#           "ladder" = set here from physical albedo, because the frame's Y is occlusion, not
#                      albedo. Stated so it is arguable rather than hidden.
TARGETS = {
    #                chroma                 ylev    basis
    "fur":       ((1.00, 1.00, 1.00),       1.000,  "it IS the white point"),
    # 2026-08-03: RE-MEASURED off canon/reference/detail_muzzle_profile.png by tools/_padcolor.py.
    # This was the last colour in the file still sourced from an ARCHIVED reference while the patch
    # browning beside it had already been re-measured against canon/reference — and it rendered the
    # pad visibly too pale next to the authoritative sheet. Median of 4 windows, ratio to adjacent
    # lit fur in linear light, sample boxes verified on a marks overlay first.
    #     was ((1.31, 0.92, 0.83), 0.850, "archived base_sheet lit pad, 3 samples")
    # One CLOSED-LOOP correction on top of the measurement: rendering the 1.44/0.743 target under
    # FLAT light (tools/pad_shot.py --flat) and measuring it back with the same estimator gave
    # pad/fur Y 1.11x too bright and red chroma 0.91x under-saturated, because SSS and the view
    # transform sit between the target and the pixel. Corrected by those factors and re-verified.
    "muzzle":    ((1.58, 0.88, 0.86),       0.669,  "canon/reference detail_muzzle_profile, 4 windows, render-corrected"),
}
# ── HOLSTEIN PATCHES: grey -> warm brown ────────────────────────────────────────────────────
# Measured as a ratio of the dark patch to the white fur (see canon/reference/SPEC.md), so the
# comparison survives the reference's lighting:
#     reference   patch/fur Y 0.036   chroma 1.47 : 0.86 : 1.00   (warm = brown)
#     ours        patch/fur Y 0.126   chroma 0.99 : 1.00 : 0.99   (dead neutral = grey)
# Ours is 3.5x too LIGHT with zero warmth. Operator 2026-08-01: get the face aligned to the
# reference, "color first then muzzle".
#
# The mask is DARK AND NOT BLUE. Dark alone would also catch the navy DevPULSE shirt, which is
# painted into the same atlas — measured: patches sRGB (98,99,98) at saturation 0.06, shirt
# (92,104,120) at 0.41. Excluding blue-dominant pixels separates them cleanly without needing a
# vertex group. Feathering on the atlas's own luminance means the patch EDGES stay exactly where
# the texture painted them, soft and organic, instead of being re-drawn by a threshold.
PATCH_CHROMA = (1.47, 0.86, 1.00)
PATCH_YLEV   = 0.036          # patch luminance as a fraction of the white fur's
PATCH_LUM_LO = 0.16           # atlas luminance at/below which a vertex is fully patch
PATCH_LUM_HI = 0.30           # at/above which it is fur and untouched
PATCH_BLUE_MAX = 0.015        # linear (B - R); above this it is the shirt, not fur

# Separate materials (constants, not the gradient).
TONGUE_CHROMA, TONGUE_Y = (2.03, 0.73, 0.60), 0.450   # ladder; chroma measured (lit edge)
TEETH_CHROMA,  TEETH_Y  = (1.09, 0.99, 0.85), 0.850   # ladder: enamel is bright
CAVITY_CHROMA, CAVITY_Y = (2.30, 0.60, 0.55), 0.060   # reads pure black in-frame via occlusion

# ── reference proportions (source now canon/reference/, see SPEC.md) ────────────────────────
# Landmark RATIOS off a gridded overlay of the FRONT view, so they transfer to our mesh
# regardless of scale or crop.
#
# The LATERAL anchor is EYE SEPARATION, not face width. Face width is ambiguous on this
# character — the ears read as part of the silhouette, and the mesh measurement I had been
# using (lateral extent above the lip line) includes them, so "56% of face width" meant two
# different things in the art and in the mesh. Eye separation is unambiguous in both: the art
# shows it plainly and the mesh publishes eye_L_center / eye_R_center as exact values.
REF_EYE_Y, REF_MUZTOP_Y, REF_MOUTH_Y, REF_PADBOT_Y = 5.75, 6.25, 8.65, 8.90
REF_EYE_X0, REF_EYE_X1 = 4.35, 5.75        # eye centre to eye centre
REF_MUZ_X0, REF_MUZ_X1 = 3.45, 6.70        # muzzle pad, left to right

# Surface response. Roughness: the reference settles that the tongue is MATTE with an SSS glow
# and the lip edge is wet. SSS radius is in scene units; the character is H=0.978 tall, so a
# 4 mm red mean-free-path is SSS_SCALE=0.004 against radius (1.0, 0.35, 0.22).
ROUGH_FUR, ROUGH_MUZZLE = 0.55, 0.42
SSS_FUR, SSS_FLESH = 0.15, 0.45
SSS_RADIUS = (1.0, 0.35, 0.22)
SSS_SCALE_SKIN, SSS_SCALE_TONGUE = 0.004, 0.006


def smooth01(t):
    """Smoothstep. Used everywhere a region ends, so no band has a hard edge."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb_to_linear(c):
    c = np.clip(np.asarray(c, float) / 255.0, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0


def lum(c):
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


# ── ROLLBACK, TAKEN FIRST ───────────────────────────────────────────────────────────────────
# Copied off disk BEFORE the file is opened. The previous version saved this at the END of the
# stage, which meant the "rollback" contained the fully MODIFIED state — it would have restored
# nothing. Caught when a re-run failed with "Base Color driven by VECT_MATH" reading its own
# output back out of the backup.
if os.path.abspath(OUT) == os.path.dirname(SRC):
    _pre = SRC + ".pre-mat"
    if not os.path.exists(_pre):
        import shutil
        shutil.copy2(SRC, _pre)
        print(f"  rollback saved BEFORE any edit: {os.path.basename(_pre)}")

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N = len(me.vertices)
F = len(me.polygons)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
co0 = co.copy()
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
zc = co[:, 2]
lp = co @ lat
print(f"materials: {os.path.basename(SRC)}  verts {N}  faces {F}  H={H:.4f}")

SK0 = len(me.shape_keys.key_blocks) if me.shape_keys else 0
VG0 = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index)
       for g in ob.vertex_groups}

# ── the lip rim: a MATERIAL boundary, as lip_seal.py:50-55 defines it ───────────────────────
mi = np.empty(F, dtype=np.int32); me.polygons.foreach_get("material_index", mi)
SKIN = int(np.bincount(mi).argmax())
names = [m.name if m else "" for m in me.materials]
DARK = next(i for i, nm in enumerate(names) if nm.startswith("clyffy_mouth_interior"))
TEETH = next((i for i, nm in enumerate(names) if nm.startswith("clyffy_teeth")), None)
TONGUE = next((i for i, nm in enumerate(names) if nm.startswith("clyffy_tongue")), None)

cav, oth = set(), set()
for i, p in enumerate(me.polygons):
    (cav if mi[i] == DARK else oth).update(int(v) for v in p.vertices)
rim = sorted(cav & oth)
surf = set()
for i in np.nonzero(mi == SKIN)[0]:
    surf.update(int(v) for v in me.polygons[int(i)].vertices)
print(f"  rim {len(rim)}  skin verts {len(surf)}")
assert rim, "empty lip rim"

# ── geodesic distance from the rim, over SKIN only ─────────────────────────────────────────
# Geodesic, never Euclidean: through the closed lip slit the upper and lower lips are ~0 apart
# in space but far apart across the surface, and a Euclidean band bleeds one into the other.
adj = defaultdict(list)
ev = np.empty(len(me.edges) * 2, dtype=np.int32)
me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
for i, j in ev:
    i, j = int(i), int(j)
    if i in surf and j in surf:
        w = float(np.linalg.norm(co[i] - co[j]))
        adj[i].append((j, w)); adj[j].append((i, w))
d = np.full(N, np.inf)
pq = []
for r in rim:
    if r in surf:
        d[r] = 0.0
        heapq.heappush(pq, (0.0, r))
while pq:
    dv, u = heapq.heappop(pq)
    if dv > d[u] + 1e-12:
        continue
    for v, w in adj[u]:
        nd = dv + w
        if nd < d[v]:
            d[v] = nd
            heapq.heappush(pq, (nd, v))
print(f"  geodesic reached {int(np.isfinite(d).sum())} verts")

# ── smooth the distance field, or the bands FESTOON ────────────────────────────────────────
# First render showed a chain of pale scalloped lobes along the lip — which I nearly blamed on
# the scalloped teeth showing through. It was not the teeth. The lobes are PALE, so they are the
# cream band itself, and the cause is resolution: the skin edge at the lip is ~0.0038-0.008 while
# the inner band is 0.0045 wide, so the band is about ONE EDGE across. An iso-distance contour
# that narrow can only be resolved to the nearest vertex, so its boundary festoons along the
# topology instead of running parallel to the lip.
#
# Laplacian-smoothing the scalar field fixes it at the right level: the iso-contours become
# smooth curves, and the bands blur — which canon wants anyway ("a soft dark crease, never a
# hard drawn line"). Passes ~ (edges to blur across)^2, so 8 covers a bit under 3 edges.
# The rim is pinned at 0 as a boundary condition so the field stays anchored to the lip.
FIELD_SMOOTH_PASSES = 8
EI, EJ = [], []
for i, j in ev:
    i, j = int(i), int(j)
    if i in surf and j in surf:
        EI.append(i); EJ.append(j)
EI = np.asarray(EI); EJ = np.asarray(EJ)
rim_idx = np.asarray([r for r in rim if r in surf])
finite = np.isfinite(d)
skin_edge = float(np.median(np.linalg.norm(co[EI] - co[EJ], axis=1)))

dd = np.where(finite, d, 0.0)
for _ in range(FIELD_SMOOTH_PASSES):
    s = np.zeros(N); c = np.zeros(N)
    np.add.at(s, EI, dd[EJ]); np.add.at(c, EI, 1.0)
    np.add.at(s, EJ, dd[EI]); np.add.at(c, EJ, 1.0)
    avg = np.where(c > 0, s / np.maximum(c, 1.0), dd)
    dd = 0.4 * dd + 0.6 * avg
    dd[rim_idx] = 0.0
d = np.where(finite, dd, np.inf)
print(f"  field smoothed {FIELD_SMOOTH_PASSES}x (skin edge at the lip {skin_edge:.5f} = "
      f"{100*skin_edge/H:.3f}%H)")

# ── landmarks -> region geometry, via the reference's own proportions ───────────────────────
z_eye = 0.5 * (float(ob["eye_L_center"][2]) + float(ob["eye_R_center"][2]))
z_rim = float(zc[rim].mean())
lat0 = float(lp[zc > z_rim].mean())
head = zc > z_rim - 0.10 * H
head_w = float(np.ptp(lp[head]))
span = z_eye - z_rim                                   # eye -> mouth, our mesh
per_dec = span / (REF_MOUTH_Y - REF_EYE_Y)             # one reference decile, in our units

z_muz_top = z_eye - (REF_MUZTOP_Y - REF_EYE_Y) * per_dec
z_muz_bot = z_rim - (REF_PADBOT_Y - REF_MOUTH_Y) * per_dec

# Lateral: scale the pad off the mesh's OWN eye separation, which is exact.
eyeL = np.asarray(ob["eye_L_center"], dtype=float)
eyeR = np.asarray(ob["eye_R_center"], dtype=float)
eye_sep = abs(float((eyeL - eyeR) @ lat))
muz_halfw = 0.5 * (REF_MUZ_X1 - REF_MUZ_X0) / (REF_EYE_X1 - REF_EYE_X0) * eye_sep
print(f"  z_eye {z_eye:.4f}  z_rim {z_rim:.4f}  span {span:.4f}  per_decile {per_dec:.5f}")
print(f"  eye separation {eye_sep:.4f} (the lateral anchor)")
print(f"  muzzle pad: z {z_muz_bot:.4f}..{z_muz_top:.4f}  half-width {muz_halfw:.4f} "
      f"(mouth half-width {0.5*np.ptp(lp[rim]):.4f})")

# Geodesic cap so the pad cannot creep around the skull. SELF-CALIBRATED: measure how far it
# actually is across the surface to the pad's own top edge, then allow a quarter more.
near_top = (np.abs(zc - z_muz_top) < 0.10 * span) & (np.abs(lp - lat0) < 0.5 * muz_halfw) & np.isfinite(d)
D_CAP = float(np.median(d[near_top])) * 1.25 if near_top.sum() >= 8 else 1.6 * (z_muz_top - z_rim)
print(f"  geodesic cap {D_CAP:.4f} (from {int(near_top.sum())} verts at the pad's top edge)")

# ── region weights, every edge feathered ───────────────────────────────────────────────────
Fz = 0.16 * (z_muz_top - z_rim)
Fl = 0.18 * muz_halfw
g_top = 1.0 - smooth01((zc - (z_muz_top - Fz)) / (2 * Fz))
g_lat = 1.0 - smooth01((np.abs(lp - lat0) - (muz_halfw - Fl)) / (2 * Fl))

# BELOW the mouth the pad ends by GEODESIC distance, not by height. A z-threshold cuts a
# straight horizontal line across a curved lip, which is exactly what the first render showed
# along the bottom of the pad; measuring outward from the lip instead lets the boundary follow
# the lip's own curve, the way the reference does. Above the mouth z is right — the pad's top
# edge really is a roughly level line across the bridge.
D_LOW = (REF_PADBOT_Y - REF_MOUTH_Y) * per_dec
g_bot = np.where(zc < z_rim,
                 1.0 - smooth01((d - (D_LOW - 0.4 * D_LOW)) / (0.8 * D_LOW)),
                 1.0)
g_bot[~np.isfinite(d) & (zc < z_rim)] = 0.0
print(f"  pad lower edge: geodesic {D_LOW:.5f} below the lip ({D_LOW/skin_edge:.2f} edges), "
      f"following the lip curve rather than a z-cut")
g_geo = 1.0 - smooth01((d - D_CAP) / (0.25 * D_CAP))
g_geo[~np.isfinite(d)] = 0.0
m_muz = g_top * g_bot * g_lat * g_geo

# ── NO LIP BANDS. The mouth is a SLIT IN THE PAD. ──────────────────────────────────────────
# The previous version painted three concentric bands around the mouth — a salmon inner rim and
# a cream outer band feathering into fur. That structure is HUMAN lip anatomy (a vermilion
# border) and it is not on this character. Operator, on seeing the render: "stop trying to human
# mouth this".
#
# It never came from a measurement. I wrote it into canon/mouth_ref/README.md as prose off a
# low-resolution 4-panel plate, before the good frames existed, and then measured colour
# rigorously in service of it — a precise execution of a structure I had invented. Both canon
# sources show the same thing instead: one continuous muzzle pad with the mouth cut into it, and
# the lips are simply the pad continuing. The dark lip line is geometry and occlusion, not paint.
#
# So there is exactly one region here: pad or fur.


def target_linear(key):
    ch, y, _ = TARGETS[key]
    ch = np.asarray(ch, float)
    return ch / max(lum(ch), 1e-9) * y * FUR_LIN


# The fur's own linear albedo, straight from the atlas: every target is expressed relative to
# it, so the ladder is anchored to what this build actually has rather than to a guess.
matskin = me.materials[SKIN]
bsdf = next(n for n in matskin.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
base_sock = bsdf.inputs["Base Color"]
assert base_sock.is_linked, "skin Base Color is not textured — this stage assumes the atlas"
# Walk UPSTREAM to the image. On a re-run this stage's own `atlas x tint` VectorMath node sits
# between the texture and Base Color, and asserting on the immediate node made the stage fail
# against any blend it had already processed — a stage that cannot run twice is not a stage.
def _find_image(sock, depth=0):
    if depth > 6 or not sock.is_linked:
        return None
    nd = sock.links[0].from_node
    if nd.type == "TEX_IMAGE":
        return nd
    for i in nd.inputs:
        r = _find_image(i, depth + 1)
        if r is not None:
            return r
    return None


tex_node = _find_image(base_sock)
assert tex_node is not None, "could not reach a TEX_IMAGE upstream of Base Color"
img = tex_node.image
W, Hp = img.size
px = np.asarray(img.pixels[:], dtype=np.float32).reshape(Hp, W, 4)

# per-vertex UV (mean of its loops) -> the atlas colour that vertex actually carries
cv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", cv)
uvs = np.empty(len(me.loops) * 2); me.uv_layers.active.data.foreach_get("uv", uvs)
uvs = uvs.reshape(-1, 2)
usum = np.zeros((N, 2)); ucnt = np.zeros(N)
np.add.at(usum, cv, uvs); np.add.at(ucnt, cv, 1.0)
ok = ucnt > 0
uv = np.zeros((N, 2)); uv[ok] = usum[ok] / ucnt[ok, None]
ix = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1).astype(int)
iy = np.clip((uv[:, 1] % 1.0) * (Hp - 1), 0, Hp - 1).astype(int)
atlas = px[iy, ix, :3].astype(float)                      # already linear

fur_mask = np.isfinite(d) & (m_muz < 0.02) & (d > 4.0 * skin_edge)
FUR_LIN = atlas[fur_mask].mean(axis=0) if fur_mask.sum() > 200 else np.array([0.367, 0.372, 0.388])
print(f"  fur albedo from the atlas ({int(fur_mask.sum())} verts): "
      f"linear ({FUR_LIN[0]:.3f},{FUR_LIN[1]:.3f},{FUR_LIN[2]:.3f})")

c_fur = target_linear("fur")

c_muz = target_linear("muzzle")

print("  targets (sRGB):")
for k, c in (("fur", c_fur), ("muzzle", c_muz)):
    s = linear_to_srgb(c)
    print(f"    {k:<10} ({s[0]:5.1f},{s[1]:5.1f},{s[2]:5.1f})   [{TARGETS[k][2]}]")

# ── the tint is RELATIVE TO FUR, not an absolute per-vertex correction ─────────────────────
# First attempt divided the atlas out per vertex (tint = target/atlas) so each vertex landed
# exactly on the measured colour. That is wrong, and its own diagnostic said so: it clamped on
# 29448 verts, 61% of the mesh. Forcing every vertex to an absolute target FLATTENS the atlas —
# it would have pulled the Holstein BLACK PATCHES up toward mean fur and crushed the bright fur
# down to it, destroying all the painted variation. (The clamp happened to rescue the black
# patches, since they want a multiplier of ~17; nothing was rescuing the highlights.)
#
# The right shape is a RATIO between regions. Each region gets one constant multiplier relative
# to the fur, and the tint lerps from 1.0 (fur: atlas completely untouched) toward that constant
# by the region weight. The atlas keeps every bit of its own variation — pores, shading, patches
# — everywhere, and only the hue and level SHIFT where the reference says they should.
def rel_to_fur(c, label):
    """Region colour as a multiplier on the fur, renormalised into COLOR_0's [0,1]."""
    r = c / np.maximum(c_fur, 1e-9)
    mx = float(r.max())
    if mx > 1.0:
        # glTF COLOR_0 cannot carry a multiplier above 1. Scaling the whole triple keeps the
        # measured HUE exactly and pays for it in level, which is the cheaper error: a band
        # that is a few percent dark still reads correct, a hue-clipped one does not.
        r = r / mx
        print(f"    {label}: renormalised by 1/{mx:.3f} to fit COLOR_0 (hue preserved)")
    return r


rel_fur = np.ones(3)
rel_muz = rel_to_fur(c_muz, "muzzle")

tint = rel_fur[None, :] * (1 - m_muz)[:, None] + rel_muz[None, :] * m_muz[:, None]
tint[~np.isfinite(d)] = 1.0
tint = np.clip(tint, 0.0, 1.0)
# ── patch tint, composed on top of the muzzle tint ──────────────────────────────────────────
# ONE canonical pair of masks, defined here and used for derivation, correction AND reporting.
# Two earlier attempts derived the multiplier from one vertex set and verified against another,
# so the correction pushed the wrong way (patch/fur Y went 0.016 -> 0.008 while chasing 0.036).
# That is the same mismatched-definition bug that cost the motion work a day: if two sides of a
# comparison do not use identical masks, they are not measuring the same thing.
atlas_lum = 0.2126 * atlas[:, 0] + 0.7152 * atlas[:, 1] + 0.0722 * atlas[:, 2]
not_blue = (atlas[:, 2] - atlas[:, 0]) < PATCH_BLUE_MAX

# The MUZZLE is excluded outright. The atlas paints pores and shading inside the pad, some of
# them below the dark threshold, and browning those turned the pink pad blotchy — dark spots
# scattered across the muzzle in the first render. The pad already has its own tint; a vertex
# cannot belong to both regions.
in_muzzle = m_muz > 0.05
PATCH_MASK = (atlas_lum < PATCH_LUM_LO) & not_blue & ~in_muzzle   # canonical: dark fur
FUR_MASK = (atlas_lum > 0.45) & ~in_muzzle                        # canonical: white fur
if int(PATCH_MASK.sum()) < 200 or int(FUR_MASK.sum()) < 200:
    raise RuntimeError(f"patch/fur masks too small ({int(PATCH_MASK.sum())}/"
                       f"{int(FUR_MASK.sum())}) — has the atlas changed?")

# Feather on the atlas's own luminance so the patch EDGES stay where the texture painted them.
w_patch = 1.0 - smooth01((atlas_lum - PATCH_LUM_LO) / max(PATCH_LUM_HI - PATCH_LUM_LO, 1e-9))
w_patch = np.where(not_blue & ~in_muzzle, w_patch, 0.0)

tint0 = tint.copy()
pch = np.asarray(PATCH_CHROMA, float)
pch = pch / max(lum(pch), 1e-9)


def _apply(rel):
    return np.clip(tint0 * ((1.0 - w_patch)[:, None] + rel[None, :] * w_patch[:, None]), 0.0, 1.0)


def _ratio(rel):
    """Achieved patch and fur ALBEDO. Names deliberately suffixed: plain `F` is the face count
    from the top of this file, and shadowing it made the geometry gate compare a colour array
    against an integer (`faces [0.78 0.75 0.74] -> 48077`). The gate caught it, which is what it
    is for, but the collision should not have been there."""
    alb = atlas * _apply(rel)
    return np.median(alb[PATCH_MASK], axis=0), np.median(alb[FUR_MASK], axis=0)


# Closed loop on the CANONICAL masks: measure the achieved albedo, correct, repeat.
rel_patch = np.ones(3)
for _pass in range(6):
    P_alb, F_alb = _ratio(rel_patch)
    want = pch * PATCH_YLEV * lum(F_alb)
    err = want / np.maximum(P_alb, 1e-6)
    if np.all(np.abs(err - 1.0) < 0.02):
        break
    rel_patch = np.clip(rel_patch * err, 1e-4, 1.0)
tint = _apply(rel_patch)

P_alb, F_alb = _ratio(rel_patch)
got_y = lum(P_alb) / max(lum(F_alb), 1e-9)
got_ch = (P_alb / np.maximum(F_alb, 1e-6)) / max(got_y, 1e-9)
ps = linear_to_srgb(np.median(atlas[PATCH_MASK], axis=0))
qs = linear_to_srgb(P_alb)
print(f"  patches: {int(PATCH_MASK.sum())} verts, {int((w_patch>0.02).sum())} touched "
      f"(feathered on the atlas's own edges)")
print(f"    albedo sRGB ({ps[0]:5.1f},{ps[1]:5.1f},{ps[2]:5.1f}) -> "
      f"({qs[0]:5.1f},{qs[1]:5.1f},{qs[2]:5.1f})   x({rel_patch[0]:.3f},{rel_patch[1]:.3f},{rel_patch[2]:.3f})")
print(f"    patch/fur  Y {got_y:.3f} (target {PATCH_YLEV})   "
      f"chroma ({got_ch[0]:.2f},{got_ch[1]:.2f},{got_ch[2]:.2f}) (target "
      f"{PATCH_CHROMA[0]:.2f},{PATCH_CHROMA[1]:.2f},{PATCH_CHROMA[2]:.2f})")
print(f"    shirt protected: {int(((~not_blue) & (atlas_lum < PATCH_LUM_LO)).sum())} "
      f"blue-dominant  |  muzzle protected: {int((in_muzzle & (atlas_lum < PATCH_LUM_LO)).sum())} "
      f"dark pad pixels")

print(f"  tint: fur stays 1.000, muzzle pad x({rel_muz[0]:.3f},{rel_muz[1]:.3f},{rel_muz[2]:.3f})")
print(f"    verts actually tinted (any channel < 0.99): "
      f"{int((tint < 0.99).any(axis=1).sum())} of {N}")

# ── the two float masks that drive surface response (Blender-only, not exported) ────────────
# One mask: the pad. The old `skin_wet` zone put a gloss ring at the lip, which was the
# specular half of the same human-lip mistake. Deleted with the bands rather than kept
# "just in case" — an unused attribute is indistinguishable from unfinished work.
w_flesh = m_muz.copy()


def put_color(name, arr):
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    at = me.color_attributes.new(name=name, type="FLOAT_COLOR", domain="POINT")
    buf = np.concatenate([arr, np.ones((N, 1))], axis=1).ravel()
    at.data.foreach_set("color", buf)
    return at


def put_float(name, arr):
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    at = me.attributes.new(name=name, type="FLOAT", domain="POINT")
    at.data.foreach_set("value", np.ascontiguousarray(arr, dtype=np.float32))
    return at


put_color("muzzle_tint", tint)
put_float("skin_flesh", w_flesh)
me.color_attributes.active_color = me.color_attributes["muzzle_tint"]
me.color_attributes.render_color_index = me.color_attributes.find("muzzle_tint")
print(f"  attributes: muzzle_tint (FLOAT_COLOR) + skin_flesh (FLOAT)")
print(f"    pad (flesh>0.5) on {int((w_flesh>0.5).sum())} verts")

# ── wire the node graph ────────────────────────────────────────────────────────────────────
nt = matskin.node_tree


def mix(data_type):
    """ShaderNodeMix, addressing sockets by ENABLED order rather than by name.

    Blender's Mix node carries a full set of A/B sockets for every data type and disables the
    ones that do not apply, so `inputs['A']` is ambiguous while the enabled order (Factor, A, B)
    is stable. Asserted rather than assumed.
    """
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = data_type
    ins = [s for s in n.inputs if s.enabled]
    assert len(ins) == 3, f"Mix({data_type}) exposed {len(ins)} enabled inputs, expected 3"
    outs = [s for s in n.outputs if s.enabled]
    return n, ins[0], ins[1], ins[2], outs[0]


for stale in [n for n in nt.nodes if n.label.startswith("clyffy_mat:")]:
    nt.nodes.remove(stale)

x0, y0 = tex_node.location.x, tex_node.location.y

n_tint = nt.nodes.new("ShaderNodeVertexColor")
n_tint.layer_name = "muzzle_tint"
n_tint.label = "clyffy_mat: tint"
n_tint.location = (x0, y0 + 320)

n_mul = nt.nodes.new("ShaderNodeVectorMath")
n_mul.operation = "MULTIPLY"
n_mul.label = "clyffy_mat: atlas x tint"
n_mul.location = (x0 + 260, y0 + 180)
nt.links.new(tex_node.outputs["Color"], n_mul.inputs[0])
nt.links.new(n_tint.outputs["Color"], n_mul.inputs[1])
nt.links.new(n_mul.outputs["Vector"], base_sock)

# roughness: keep the atlas map, then pull it toward the wet value at the lip
n_flesh = nt.nodes.new("ShaderNodeAttribute")
n_flesh.attribute_name = "skin_flesh"
n_flesh.label = "clyffy_mat: flesh"
n_flesh.location = (x0, y0 - 520)

rough_sock = bsdf.inputs["Roughness"]
rough_src = rough_sock.links[0].from_socket if rough_sock.is_linked else None

n_rmuz, f_r, a_r, b_r, o_r = mix("FLOAT")
n_rmuz.label = "clyffy_mat: rough pad"
n_rmuz.location = (x0 + 260, y0 - 380)
nt.links.new(n_flesh.outputs["Fac"], f_r)
if rough_src:
    nt.links.new(rough_src, a_r)
else:
    a_r.default_value = ROUGH_FUR
b_r.default_value = ROUGH_MUZZLE

nt.links.new(o_r, rough_sock)

# SSS weight rides the same flesh mask: fur gets some, the pad and lips get more
n_sss, f_s, a_s, b_s, o_s = mix("FLOAT")
n_sss.label = "clyffy_mat: sss"
n_sss.location = (x0 + 260, y0 - 560)
nt.links.new(n_flesh.outputs["Fac"], f_s)
a_s.default_value = SSS_FUR
b_s.default_value = SSS_FLESH
sss_sock = bsdf.inputs.get("Subsurface Weight") or bsdf.inputs.get("Subsurface")
assert sss_sock is not None, "no Subsurface Weight socket on this Principled BSDF"
nt.links.new(o_s, sss_sock)


def setv(b, key, val, *alts):
    s = b.inputs.get(key)
    for alt in alts:
        if s is None:
            s = b.inputs.get(alt)
    if s is None or s.is_linked:
        return False
    s.default_value = val
    return True


setv(bsdf, "Subsurface Radius", SSS_RADIUS)
setv(bsdf, "Subsurface Scale", SSS_SCALE_SKIN)
setv(bsdf, "Sheen Weight", 0.18, "Sheen")
setv(bsdf, "Sheen Roughness", 0.40)
print(f"  skin material '{matskin.name}': tint x atlas, roughness fur {ROUGH_FUR} -> pad "
      f"{ROUGH_MUZZLE}, SSS {SSS_FUR} -> {SSS_FLESH} @ scale {SSS_SCALE_SKIN}")


# ── the genuine material splits: correct HUE to the measurement, KEEP the tuned level ───────
# These three sit inside the mouth, where the reference frame's luminance is dominated by
# occlusion rather than by albedo — so the frame tells me their HUE reliably and their LEVEL not
# at all. Re-anchoring level to the atlas fur (0.355 linear) made enamel mid-grey sRGB (155,150,
# 143), which inside an unlit cavity would have made the teeth disappear: darkening the albedo
# AND letting occlusion darken it again double-counts, the same double-counting that collapsed
# the tongue blade earlier in this build.
#
# So: rotate each constant's chroma onto the measured ratio and PRESERVE its existing luminance,
# which was tuned against renders. Only what was actually measured gets changed.
def const_mat(slot, chroma, rough, sss, scale, label, ylev=None, **extra):
    if slot is None:
        print(f"  ! no slot for {label} — skipped")
        return
    m = me.materials[slot]
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b is None:
        print(f"  ! {m.name} has no Principled BSDF — skipped")
        return
    ch = np.asarray(chroma, float)
    ch = ch / max(lum(ch), 1e-9)                       # unit-luminance hue
    sock = b.inputs.get("Base Color")
    was = np.asarray(sock.default_value[:3], float) if sock and not sock.is_linked else None
    if ylev is not None:
        Y, how = ylev * lum(FUR_LIN), f"SET from ylev={ylev}"
    elif was is not None and lum(was) > 1e-6:
        Y, how = lum(was), "KEPT from the tuned value"
    else:
        Y, how = 0.30 * lum(FUR_LIN), "defaulted (nothing to keep)"
    c = ch * Y
    if was is not None:
        sw = linear_to_srgb(was)
        print(f"    {label}: level {how} -> Y={Y:.4f} (was Y={lum(was):.4f}, sRGB "
              f"{sw[0]:.0f},{sw[1]:.0f},{sw[2]:.0f}), hue rotated to the measurement")
    setv(b, "Base Color", (float(c[0]), float(c[1]), float(c[2]), 1.0))
    setv(b, "Roughness", rough)
    setv(b, "Subsurface Weight", sss, "Subsurface")
    setv(b, "Subsurface Radius", SSS_RADIUS)
    setv(b, "Subsurface Scale", scale)
    for k, v in extra.items():
        setv(b, k.replace("_", " "), v)
    m.diffuse_color = (float(c[0]), float(c[1]), float(c[2]), 1.0)   # Workbench reads this
    m.roughness = rough
    s = linear_to_srgb(c)
    print(f"  {m.name:<24} sRGB ({s[0]:5.1f},{s[1]:5.1f},{s[2]:5.1f})  rough {rough}  SSS {sss}")


# Tongue: MATTE with an SSS glow, which the reference settles explicitly — not glossy.
const_mat(TONGUE, TONGUE_CHROMA, 0.62, 0.55, SSS_SCALE_TONGUE, "tongue")
# Teeth: one continuous cream. Measured upper canine (176,158,130) vs dental pad (170,151,125)
# — the same colour, which is why the reference reads as a single pad rather than as teeth.
const_mat(TEETH, TEETH_CHROMA, 0.25, 0.12, 0.002, "teeth",
          Coat_Weight=0.18, Coat_Roughness=0.14)
# Cavity: measures (1,0,0) in the reference — pure black. Kept as a dark red ALBEDO rather than
# literal black, because black albedo would stay black if a fill light ever reaches it; it reads
# near-black through occlusion, which is what the frame is actually showing. This is the one
# interior level I DO move: the reference is unambiguous that it reads black, and ours was
# sRGB (74,45,48), light enough to read as a visible red hole.
const_mat(DARK, CAVITY_CHROMA, 0.68, 0.0, 0.002, "cavity",
          ylev=CAVITY_Y, Specular_IOR_Level=0.18)

# ── GATE: this stage must not have touched geometry ─────────────────────────────────────────
co2 = np.empty((N, 3)); me.vertices.foreach_get("co", co2.ravel())
moved = float(np.abs(co2 - co0).max())
SK1 = len(me.shape_keys.key_blocks) if me.shape_keys else 0
VG1 = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index)
       for g in ob.vertex_groups}
print("\ngate:")
print(f"  verts {N} -> {len(me.vertices)}   faces {F} -> {len(me.polygons)}")
print(f"  max vertex movement {moved:.3e}   shape keys {SK0} -> {SK1}")
bad = [k for k in VG0 if VG0[k] != VG1.get(k)]
print(f"  vertex groups {len(VG0)} -> {len(VG1)}, membership changed on {len(bad)}: {bad[:5]}")
assert len(me.vertices) == N and len(me.polygons) == F, "geometry changed — materials must not"
assert moved == 0.0, f"vertices moved by {moved}"
assert SK1 == SK0, "shape key count changed"
assert not bad, f"vertex group membership changed: {bad}"
print("  OK — colour and surface response only, geometry byte-identical")

# ── stage report, same convention as body_rig / spring_bones / vrm_export ───────────────────
# Its EXISTENCE is what tells tools/renderer_check.py that a delivered VRM is now required to
# carry a real COLOR_0. Without that signal the gate cannot tell "the tint is missing" from
# "this build predates the tint", and a gate that cannot tell those apart is not a gate.
report = {
    "verts": N, "faces": F, "H": H,
    "tinted_verts": int((tint < 0.99).any(axis=1).sum()),
    "flesh_verts": int((w_flesh > 0.5).sum()),
    "attributes": ["muzzle_tint", "skin_flesh"],
    "requires_color0": True,
    "muzzle": {"z_lo": z_muz_bot, "z_hi": z_muz_top, "half_width": muz_halfw,
               "geodesic_cap": D_CAP},
    "skin_edge": skin_edge,
    "pad_lower_geodesic": D_LOW,
    "targets_srgb": {k: [round(float(x), 1) for x in linear_to_srgb(v)]
                     for k, v in (("fur", c_fur), ("muzzle", c_muz))},
    "tint_multipliers": {"muzzle": [round(float(x), 4) for x in rel_muz],
                         "patch": [round(float(x), 4) for x in rel_patch]},
    "patch": {"chroma": list(PATCH_CHROMA), "ylev": PATCH_YLEV,
              "achieved_ylev": round(float(got_y), 4),
              "achieved_chroma": [round(float(x), 3) for x in got_ch],
              "verts": int(PATCH_MASK.sum()), "touched": int((w_patch > 0.02).sum()),
              "reference": "canon/reference/ (see SPEC.md)"},
    "sss": {"fur": SSS_FUR, "flesh": SSS_FLESH, "radius": list(SSS_RADIUS),
            "scale": SSS_SCALE_SKIN},
    "roughness": {"fur": ROUGH_FUR, "muzzle": ROUGH_MUZZLE},
    "reference": "canon/reference/ (see SPEC.md)",
}
import json as _json
with open(os.path.join(os.path.dirname(SRC), "materials_report.json"), "w") as fh:
    _json.dump(report, fh, indent=2)
print(f"  report: {os.path.join(os.path.dirname(SRC), 'materials_report.json')}")

dst = os.path.join(OUT, os.path.basename(SRC))
bpy.ops.wm.save_as_mainfile(filepath=dst)
print(f"wrote {dst}")
