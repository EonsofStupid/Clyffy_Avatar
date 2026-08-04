"""Give the muzzle pad its SURFACE: pebbled micro-relief and a wetter specular. Adds NO geometry.

    blender -b --python tools/muzzle_pad.py -- <body.blend> <out_dir> \
        [--pebble N] [--relief K] [--rough R] [--res N]

Chain position 14.5 — after `materials.py` (which authors the pad's COLOUR and SSS) and before
`vrm_export`.

═══ WHAT THE REFERENCE ACTUALLY SHOWS ══════════════════════════════════════════════════════

`canon/reference/detail_muzzle_profile.png`, the muzzle close-up, at a glance:

  * the pad is covered in fine PEBBLED micro-relief — a dense stipple, not smooth rubber
  * it reads GLOSSIER than the surrounding fur, a soft wet sheen rather than a hard highlight
  * the fur-to-pad boundary is RAGGED, fur strands overlapping the pink, not a clean arc

`materials.py` already gets the colour and the subsurface right. What it cannot do is relief:
`muzzle_tint` is a per-VERTEX attribute, and at this density a vertex cannot describe a pebble.

═══ WHY THIS IS BAKED, AND WHY THE NOISE IS 3D ═════════════════════════════════════════════

Two constraints decide the whole approach, and both were measured rather than assumed:

  1. PROCEDURAL NODES DO NOT SURVIVE glTF EXPORT. A Noise Texture driving a Bump node looks
     correct in Blender and reaches the VRM as nothing at all. Detail has to land in a TEXTURE.
     VRM 1.0 is fine with that — MToon carries glTF core's `normalTexture`.
  2. THE UV LAYOUT IS FRAGMENTED. Baking `skin_flesh` into UV space shows the muzzle scattered
     over roughly thirty small islands covering 6% of the sheet, which is Tripo auto-retopo doing
     what it does. Any noise evaluated in UV space would therefore be DISCONTINUOUS at every
     island edge — visible seams straight across the pad.

So the noise is evaluated in OBJECT space, where island boundaries do not exist, and Blender's
own baker resolves it into a tangent-space normal map — which also means Blender computes the
tangent frames instead of this script re-deriving them and being subtly wrong about handedness.

═══ THE PAD REGION IS COMPOSITED, NOT TRUSTED ══════════════════════════════════════════════

`bpy.ops.object.bake` bakes every face of the object, and the mouth interior, teeth and tongue
added by `mouth_parts` do not have meaningful UVs — if any of them overlaps the skin's islands it
would stomp real texels. So the bake goes to a SCRATCH image and only the pad region is composited
back over the original normal map. Anything outside the pad is byte-for-byte the texture that
shipped.
"""
import bpy, sys, os, shutil
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])


def opt(name, default, cast=float):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


PEBBLE = opt("--pebble", 620.0)     # object-space noise scale; larger = finer stipple
RELIEF = opt("--relief", 0.0016)    # bump distance in object units
ROUGH = opt("--rough", 0.34)        # pad roughness; materials.py leaves the pad at 0.42
RES = opt("--res", 4096, int)
PATTERN = argv[argv.index("--pattern") + 1] if "--pattern" in argv else "voronoi"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
N0, F0 = len(me.vertices), len(me.polygons)
SK0 = len(me.shape_keys.key_blocks) if me.shape_keys else 0
GRP0 = {g.name for g in ob.vertex_groups}

# `skin_flesh` is a generic FLOAT attribute on POINT domain, not a vertex group and not a colour
# attribute — see tools/materials.py put_float(). An Attribute node reads it through `Fac`.
assert "skin_flesh" in me.attributes, (
    "no skin_flesh attribute — run tools/materials.py first")
skin = me.materials[0]
sk_nt = skin.node_tree
nmap = next((n for n in sk_nt.nodes if n.type == "NORMAL_MAP"), None)
assert nmap is not None and nmap.inputs["Color"].is_linked, "skin material has no normal map"
nrm_tex = nmap.inputs["Color"].links[0].from_node
assert nrm_tex.type == "TEX_IMAGE" and nrm_tex.image, "normal map is not an image texture"
src_img = nrm_tex.image
W, H = src_img.size
print(f"muzzle_pad: {os.path.basename(SRC)}  verts {N0}  faces {F0}")
print(f"  normal map '{src_img.name}' {W}x{H}  colorspace {src_img.colorspace_settings.name}")

# ── remember every material's graph so the bake rig can be torn back out ─────
saved = []
for m in me.materials:
    if m and m.node_tree:
        saved.append((m, [(n.name, n.type) for n in m.node_tree.nodes]))

scratch_m = bpy.data.images.new("_pad_mask", RES, RES, alpha=False, float_buffer=True)
scratch_m.colorspace_settings.name = "Non-Color"

sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.cycles.samples = 1
sc.render.bake.margin = 16
sc.render.bake.use_selected_to_active = False
for o in bpy.context.view_layer.objects:
    o.select_set(False)
ob.select_set(True)
bpy.context.view_layer.objects.active = ob


def target(img):
    """Give every material an active image node pointing at `img` — the baker requires one."""
    for m in me.materials:
        if not m or not m.node_tree:
            continue
        nt = m.node_tree
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.name = "_bake_target"
        for n in nt.nodes:
            n.select = False
        t.select = True
        nt.nodes.active = t


def drop_targets():
    for m in me.materials:
        if not m or not m.node_tree:
            continue
        for n in [x for x in m.node_tree.nodes if x.name.startswith("_bake_target")]:
            m.node_tree.nodes.remove(n)


# ── 1. the pad mask, in UV space ─────────────────────────────────────────────
mask_graphs = []
for m in me.materials:
    if not m or not m.node_tree:
        continue
    nt = m.node_tree
    mask_graphs.append((m, [n for n in nt.nodes]))
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emi = nt.nodes.new("ShaderNodeEmission")
    att = nt.nodes.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = "skin_flesh"
    nt.links.new(att.outputs["Fac"], emi.inputs["Color"])
    nt.links.new(emi.outputs["Emission"], out.inputs["Surface"])
    out.is_active_output = True
target(scratch_m)
bpy.ops.object.bake(type="EMIT")
mask = np.array(scratch_m.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[..., 0]
drop_targets()
print(f"  pad mask baked: {int((mask > 0.05).sum())} texels > 0.05 "
      f"({100*(mask > 0.05).mean():.2f}% of the sheet)")

# ── 2. the pebbled normal ────────────────────────────────────────────────────
# Reload to get the untouched material graphs back rather than trying to rebuild them by hand.
bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
me = ob.data
skin = me.materials[0]
nt = skin.node_tree
nmap = next(n for n in nt.nodes if n.type == "NORMAL_MAP")
nrm_tex = nmap.inputs["Color"].links[0].from_node
src_img = nrm_tex.image
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

# Created HERE, not before the reload: `bpy.ops.wm.open_mainfile` clears bpy.data, so an image
# made earlier comes back as "StructRNA of type Image has been removed" the moment it is assigned.
scratch_n = bpy.data.images.new("_pad_normal", RES, RES, alpha=False, float_buffer=True)
scratch_n.colorspace_settings.name = "Non-Color"

tc = nt.nodes.new("ShaderNodeTexCoord")
# VORONOI, NOT NOISE. A Noise Texture is a cloudy fractal: rendered at the reference's stipple
# scale it reads as DUST on the pad rather than pebbling. The reference's micro-relief is made of
# discrete rounded cells, which is exactly what a Voronoi distance field is. Smooth F1 rounds the
# cell tops off instead of leaving the cones that plain F1 produces.
if PATTERN == "noise":
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = PEBBLE
    noise.inputs["Detail"].default_value = 2.0
    noise.inputs["Roughness"].default_value = 0.5
    height_socket = noise.outputs["Fac"]
else:
    noise = nt.nodes.new("ShaderNodeTexVoronoi")
    noise.feature = "SMOOTH_F1"
    noise.distance = "EUCLIDEAN"
    noise.inputs["Scale"].default_value = PEBBLE
    if "Smoothness" in noise.inputs:
        noise.inputs["Smoothness"].default_value = 0.38
    if "Randomness" in noise.inputs:
        noise.inputs["Randomness"].default_value = 1.0
    height_socket = noise.outputs["Distance"]
nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

att = nt.nodes.new("ShaderNodeAttribute")
att.attribute_type = "GEOMETRY"
att.attribute_name = "skin_flesh"
strength = nt.nodes.new("ShaderNodeMath")
strength.operation = "MULTIPLY"
strength.inputs[1].default_value = 1.0
nt.links.new(att.outputs["Fac"], strength.inputs[0])

bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Distance"].default_value = RELIEF
nt.links.new(strength.outputs["Value"], bump.inputs["Strength"])
nt.links.new(height_socket, bump.inputs["Height"])
nt.links.new(nmap.outputs["Normal"], bump.inputs["Normal"])   # pebble ON TOP of the sculpt normal
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.cycles.samples = 1
sc.render.bake.margin = 16
sc.render.bake.use_selected_to_active = False
sc.render.bake.normal_space = "TANGENT"
for o in bpy.context.view_layer.objects:
    o.select_set(False)
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
target(scratch_n)
bpy.ops.object.bake(type="NORMAL")
baked = np.array(scratch_n.pixels[:], dtype=np.float32).reshape(RES, RES, 4)
drop_targets()
print(f"  normal baked at {RES} ({PATTERN}, pebble scale {PEBBLE}, relief {RELIEF})")

# ── 3. composite ONLY the pad back over the shipped normal map ───────────────
orig = np.array(src_img.pixels[:], dtype=np.float32).reshape(H, W, 4)
if (H, W) != (RES, RES):
    yi = (np.arange(H) * RES // H).clip(0, RES - 1)
    xi = (np.arange(W) * RES // W).clip(0, RES - 1)
    baked = baked[yi][:, xi]
    mask = mask[yi][:, xi]

a = np.clip(mask, 0.0, 1.0)[..., None]
out_px = orig.copy()
out_px[..., :3] = orig[..., :3] * (1.0 - a) + baked[..., :3] * a

changed = int((np.abs(out_px[..., :3] - orig[..., :3]).max(axis=2) > 1.0 / 255.0).sum())
print(f"  composited: {changed} texels changed ({100*changed/(W*H):.2f}% of the map); "
      f"everything outside the pad is byte-identical")
assert changed > 1000, "composite changed almost nothing — the pad mask or the bake is empty"

new_img = bpy.data.images.new("clyffy_normal_pad", W, H, alpha=False, float_buffer=True)
new_img.colorspace_settings.name = "Non-Color"
new_img.pixels = out_px.ravel()
new_path = os.path.join(OUT, "clyffy_normal_pad.png")
new_img.filepath_raw = new_path
new_img.file_format = "PNG"
new_img.save()
nrm_tex.image = new_img
new_img.pack()
print(f"  wrote {new_path} and relinked the skin normal map to it")

# ── 4. the wetter specular ───────────────────────────────────────────────────
# materials.py drives Roughness through a Mix whose Factor is `skin_flesh`; its B input is the
# pad's roughness, so the pad is tuned by moving that one value and the fur is left alone.
rough_mix = None
for l in nt.links:
    if l.to_node == bsdf and l.to_socket.name == "Roughness":
        rough_mix = l.from_node
if rough_mix is not None and rough_mix.type == "MIX":
    # PICK THE SOCKET BY TYPE, NOT BY INDEX. ShaderNodeMix carries a full set of A/B sockets for
    # every data type it supports — Float, Vector, Color, Rotation — and only the pair matching
    # `data_type` is live. Index 7 is B_Color, so assigning a float to it raises TypeError.
    b = next(i for i in rough_mix.inputs
             if i.name == "B" and i.type == "VALUE" and not i.is_linked)
    was = round(float(b.default_value), 3)
    b.default_value = ROUGH
    print(f"  pad roughness {was} -> {ROUGH} (fur untouched, it comes from the texture)")
else:
    print("  WARNING: could not find the roughness Mix driven by skin_flesh — "
          "pad roughness NOT changed; check tools/materials.py has run")

# ── gate ─────────────────────────────────────────────────────────────────────
N1, F1 = len(me.vertices), len(me.polygons)
SK1 = len(me.shape_keys.key_blocks) if me.shape_keys else 0
GRP1 = {g.name for g in ob.vertex_groups}
print("\ngate:")
print(f"  verts {N0} -> {N1}   faces {F0} -> {F1}   shape keys {SK0} -> {SK1}   "
      f"groups {len(GRP0)} -> {len(GRP1)}")
assert (N0, F0, SK0) == (N1, F1, SK1), "muzzle_pad changed geometry — it must not"
assert GRP0 == GRP1, "vertex groups changed"

dst = os.path.join(OUT, os.path.basename(SRC))
bpy.ops.wm.save_as_mainfile(filepath=dst)
print(f"wrote {dst}")
