"""Presentable beauty renders — not Workbench diagnostics.

    blender -b --python tools/present.py -- \
        <body.blend> <out_dir> <fwd_deg> [state.json|preset|rest]...

Canon look (CANON.md):
  Pixar CGI × Arcane painterly grading
  SSS on skin/fur · deep teal shadows · amber rim · steel-blue fill
  DPN dark studio · waist-up companion framing · NO cel / NO outlines

Uses Cycles on GPU when available. Applies control_surface state if given a
JSON path or a named preset (rest/happy/surprised/talk_aa/…).
"""
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector, Matrix, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
RIG = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
FWD = float(argv[2])
# --full: whole-body framing (legs + hooves in shot). Default stays waist-up —
# that is the companion crop, and the face must stay large enough to review
# visemes and expressions on. Both framings coexist; see clyffy.pack.toml [rig.scope].
FULL = "--full" in argv[3:]
STATES = [s for s in argv[3:] if not s.startswith("--")] or \
         ["rest", "happy", "surprised", "talk_aa"]
PFX = "full_" if FULL else "hero_"
os.makedirs(OUT, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import PRESETS, VISEMES, ENVELOPE  # noqa: E402

# ── load ──────────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"],
         key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
hc = co[co[:, 2] > 0.208].mean(0)
# waist-up focus: mid chest / face — or body centre when framing the whole figure
if FULL:
    zmid = float((co[:, 2].min() + co[:, 2].max()) * 0.5)
    focus = np.array([hc[0], hc[1], zmid])
else:
    focus = np.array([hc[0], hc[1], float(hc[2] - H * 0.06)])

# hide armature from render
arm.hide_render = True
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)

# ── material polish ───────────────────────────────────────────────────────────
def polish_materials():
    for m in me.materials:
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        name = m.name.lower()
        # Blender 4.0 Principled: Subsurface Weight / Radius / Scale
        def set_in(sock, val):
            if sock is None:
                return
            if hasattr(sock, "default_value"):
                try:
                    sock.default_value = val
                except Exception:
                    pass

        if "teeth" in name:
            set_in(bsdf.inputs.get("Roughness"), 0.22)
            set_in(bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular"), 0.55)
            set_in(bsdf.inputs.get("Coat Weight"), 0.15)
            set_in(bsdf.inputs.get("Coat Roughness"), 0.12)
            # warm ivory
            set_in(bsdf.inputs.get("Base Color"), (0.95, 0.93, 0.88, 1.0))
        elif "tongue" in name:
            set_in(bsdf.inputs.get("Roughness"), 0.45)
            set_in(bsdf.inputs.get("Subsurface Weight") or bsdf.inputs.get("Subsurface"), 0.35)
            rad = bsdf.inputs.get("Subsurface Radius")
            if rad is not None:
                set_in(rad, (1.0, 0.2, 0.1))
        elif "mouth_interior" in name or "interior" in name:
            set_in(bsdf.inputs.get("Roughness"), 0.55)
            set_in(bsdf.inputs.get("Base Color"), (0.04, 0.012, 0.015, 1.0))
            set_in(bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular"), 0.15)
        else:
            # main body — SSS for fur/skin read, keep texture base color linked
            sss = bsdf.inputs.get("Subsurface Weight") or bsdf.inputs.get("Subsurface")
            set_in(sss, 0.12)
            rad = bsdf.inputs.get("Subsurface Radius")
            if rad is not None:
                set_in(rad, (1.0, 0.35, 0.2))
            set_in(bsdf.inputs.get("Roughness"), 0.48)
            # mild sheen for fur (Blender 4: Sheen Weight)
            set_in(bsdf.inputs.get("Sheen Weight") or bsdf.inputs.get("Sheen"), 0.18)
            set_in(bsdf.inputs.get("Sheen Roughness"), 0.4)

polish_materials()
print("materials polished (SSS / teeth / cavity)")

# ── world + lights (canon palette) ────────────────────────────────────────────
sc = bpy.context.scene
# dark studio world
world = bpy.data.worlds.new("DPN_Studio")
sc.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
w_out = wn.new("ShaderNodeOutputWorld")
w_bg = wn.new("ShaderNodeBackground")
# near-black with cold teal bias
w_bg.inputs["Color"].default_value = (0.012, 0.018, 0.022, 1.0)
w_bg.inputs["Strength"].default_value = 0.35
wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

def add_area(name, loc, rot, size, color, energy, shape="AREA"):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    sc.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    return obj

# camera basis for light placement (in front of face)
Rcam = H * 3.2
cam_pos = Vector((focus[0] + math.sin(a) * Rcam,
                  focus[1] - math.cos(a) * Rcam,
                  focus[2] + H * 0.08))
face = Vector(focus)

# ── light-rig scale (F1) ─────────────────────────────────────────────────────
# The rig below was tuned against the WAIST-UP crop, where the lit subject spans
# roughly half the figure. Framed full-body the same rig falls off badly down the
# legs: the key sits at focus.z + 0.40H with the hooves ~0.5H below focus, and the
# teal bounce that should lift them runs at 6.0 against the key's 28.0.
# Fix is to scale the rig to the framing, not to re-anchor it (it already tracks
# `focus`). Push the lights out by LR so the near/far falloff across the body
# flattens, grow the sources by LR so they stay soft, and compensate the inverse
# square with LR². Teal gets an extra push because it is the light nearest the legs.
LR = 1.60 if FULL else 1.00     # rig radius / source size scale
EN = LR * LR                    # inverse-square compensation
TEAL_BOOST = 2.5 if FULL else 1.0
RIM_Z   = 0.12 if FULL else 0.30   # drop the rim so it reaches the hooves
RIM_SZ  = 1.30 if FULL else 0.70

# Energies tuned for EEVEE area lights + Filmic (first pass blew out pure white).
# Key — soft warm front-left
key = add_area("L_Key",
               (face.x + lat[0] * H * 0.55 * LR + math.sin(a) * H * 1.6 * LR,
                face.y + lat[1] * H * 0.55 * LR - math.cos(a) * H * 1.6 * LR,
                face.z + H * 0.40 * LR),
               (math.radians(60), 0, a + math.radians(25)),
               H * 1.4 * LR, (1.0, 0.97, 0.92), 28.0 * EN)
# Fill — cold steel-blue monitor fill (canon)
fill = add_area("L_Fill",
                (face.x - lat[0] * H * 0.85 * LR + math.sin(a) * H * 1.3 * LR,
                 face.y - lat[1] * H * 0.85 * LR - math.cos(a) * H * 1.3 * LR,
                 face.z + H * 0.08 * LR),
                (math.radians(75), 0, a - math.radians(40)),
                H * 1.8 * LR, (0.50, 0.68, 0.95), 10.0 * EN)
# Rim — electric amber behind (canon) — keep thin, not a flood
rim = add_area("L_Rim",
               (face.x - math.sin(a) * H * 1.5 * LR + lat[0] * H * 0.25 * LR,
                face.y + math.cos(a) * H * 1.5 * LR + lat[1] * H * 0.25 * LR,
                face.z + H * RIM_Z * LR),
               (math.radians(100), 0, a + math.radians(180)),
               H * RIM_SZ * LR, (1.0, 0.55, 0.18), 40.0 * EN)
# Teal bounce from below (deep teal shadow pools) — the leg lifter at full-body
teal = add_area("L_Teal",
                (face.x + lat[0] * H * 0.25 * LR + math.sin(a) * H * 0.7 * LR,
                 face.y + lat[1] * H * 0.25 * LR - math.cos(a) * H * 0.7 * LR,
                 face.z - H * 0.40 * LR),
                (math.radians(30), 0, a),
                H * 2.0 * LR, (0.12, 0.45, 0.48), 6.0 * EN * TEAL_BOOST)

# Aim areas toward face
for light in (key, fill, rim, teal):
    direction = face - light.location
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

print("lights: key / steel fill / amber rim / teal bounce")

# ── camera ────────────────────────────────────────────────────────────────────
cd = bpy.data.cameras.new("BeautyCam")
cam = bpy.data.objects.new("BeautyCam", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.type = "PERSP"
cd.lens = 85
cd.clip_start = 0.01
cd.clip_end = H * 40
# slight three-quarter for life
ang = a + math.radians(12)
# 85mm on a 36mm sensor gives a 23.9° vertical FOV (tan(half) = 0.2118), so covering
# ~1.12H needs 1.12H / (2 * 0.2118) = 2.64H. 2.80H leaves headroom above the horns
# and clearance under the hooves.
dist = H * 2.80 if FULL else H * 1.55
cam.location = (focus[0] + math.sin(ang) * dist,
                focus[1] - math.cos(ang) * dist,
                focus[2] + H * 0.02)
# look at focus
direction = Vector(focus) - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

# ── Beauty engine: Cycles CUDA on GB10 (Blender ≥5.2), else EEVEE ─────────────
def _enable_cycles_cuda():
    """Prefer Cycles GPU. Returns True if a CUDA device was armed."""
    try:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "GPU"
        sc.cycles.samples = 128
        prefs = bpy.context.preferences.addons["cycles"].preferences
        # Prefer OptiX device type when present (GB10 build has it); else CUDA
        for dtype in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = dtype
                break
            except Exception:
                continue
        prefs.get_devices()
        n_gpu = 0
        for d in prefs.devices:
            use = d.type in ("CUDA", "OPTIX")
            d.use = use
            if use:
                n_gpu += 1
                print(f"Cycles device: {d.name} ({d.type})")
        # Denoise: OptiX GPU denoise if possible; OIDN often missing on this aarch64 build
        sc.cycles.use_denoising = False
        if hasattr(sc.cycles, "denoiser") and n_gpu:
            for dn in ("OPTIX", "OPENIMAGEDENOISE"):
                try:
                    sc.cycles.denoiser = dn
                    sc.cycles.use_denoising = True
                    print(f"Cycles denoiser: {dn}")
                    break
                except Exception:
                    continue
        return n_gpu > 0
    except Exception as e:
        print(f"Cycles CUDA setup failed: {e}")
        return False

def _enable_eevee():
    sc.render.engine = "BLENDER_EEVEE"
    ee = sc.eevee
    # 4.x / 5.x API drift — set what exists
    for k, v in (
        ("taa_render_samples", 128),
        ("use_gtao", True),
        ("gtao_distance", 0.3),
        ("gtao_factor", 1.0),
        ("use_bloom", True),
        ("bloom_threshold", 1.15),
        ("bloom_intensity", 0.015),
        ("bloom_radius", 4.0),
        ("use_ssr", True),
        ("use_ssr_refraction", False),
        ("ssr_quality", 0.75),
        ("use_soft_shadows", True),
        ("use_volumetric_lights", False),
    ):
        if hasattr(ee, k):
            try:
                setattr(ee, k, v)
            except Exception:
                pass
    for k, v in (("shadow_cube_size", "2048"), ("shadow_cascade_size", "2048")):
        if hasattr(ee, k):
            try:
                setattr(ee, k, v)
            except Exception:
                pass
    print("EEVEE 128 TAA + GTAO + SSR + soft bloom + Filmic")

if _enable_cycles_cuda():
    print("Cycles CUDA 128 samples + denoising + Filmic")
else:
    print("Falling back to EEVEE (no Cycles CUDA device)")
    _enable_eevee()

sc.view_settings.view_transform = "Filmic"
sc.view_settings.look = "Medium Contrast"
sc.view_settings.exposure = -0.35
sc.view_settings.gamma = 1.0
sc.render.resolution_x = 1080
sc.render.resolution_y = 1350  # 4:5 waist-up companion
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.film_transparent = False
# mild color management grade toward Arcane-ish contrast

# ── pose helpers ──────────────────────────────────────────────────────────────
def bone(*names):
    for n in names:
        if n in arm.pose.bones:
            return arm.pose.bones[n]
    return None

jaw_b = bone("jaw")
eye_L = bone("eye_L", "leftEye")
eye_R = bone("eye_R", "rightEye")
kb = me.shape_keys.key_blocks if me.shape_keys else None
lat_v = Vector(lat)
fwd_v = Vector(fwd)

def zero_all():
    if kb:
        for k in kb:
            if k.name != "Basis":
                k.value = 0.0
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def set_shape(name, value):
    if kb and name in kb and name != "Basis":
        kb[name].value = float(max(0.0, min(1.0, value)))

def set_jaw(amount):
    if jaw_b is None:
        return
    amount = float(max(0.0, min(1.0, amount)))
    hinge = Vector(jaw_b.bone.head_local)
    # Contract, not a literal — the heroes were posed at 22 deg against a 10 deg envelope.
    ang = math.radians(ENVELOPE["jaw"]["max_deg"]) * amount
    R = (Matrix.Translation(hinge)
         @ Matrix.Rotation(ang, 4, lat_v)
         @ Matrix.Translation(-hinge))
    jaw_b.matrix = R @ jaw_b.bone.matrix_local

def set_gaze(yaw_deg, pitch_deg):
    for eb in (eye_L, eye_R):
        if eb is None:
            continue
        eb.rotation_mode = "XYZ"
        eb.rotation_euler = (math.radians(pitch_deg), 0.0, math.radians(yaw_deg))

def apply_state(state: dict):
    zero_all()
    if state.get("rest_loop"):
        return
    weights = {}
    expr = state.get("expression_state")
    if isinstance(expr, str):
        weights.update(PRESETS.get(expr, {}))
    elif isinstance(expr, dict):
        weights.update({k: float(v) for k, v in expr.items()})
    vis = state.get("viseme_weights") or {}
    if isinstance(vis, str):
        vis = VISEMES.get(vis, {})
    for k, v in vis.items():
        weights[k] = max(weights.get(k, 0.0), float(v))
    jaw_amt = 0.0
    for name, val in weights.items():
        if name == "jawOpen":
            jaw_amt = max(jaw_amt, float(val))
        else:
            set_shape(name, float(val))
    if jaw_amt > 0:
        set_jaw(jaw_amt)
    gaze = state.get("gaze_target") or {}
    if "yaw_deg" in gaze or "pitch_deg" in gaze:
        set_gaze(float(gaze.get("yaw_deg", 0)), float(gaze.get("pitch_deg", 0)))
    bpy.context.view_layer.update()

# named shortcuts
NAMED = {
    "rest": {"rest_loop": True},
    "happy": {
        "expression_state": "happy",
        "gaze_target": {"yaw_deg": -8.0, "pitch_deg": 2.0},
    },
    "surprised": {
        "expression_state": "surprised",
        "gaze_target": {"yaw_deg": 0.0, "pitch_deg": 6.0},
    },
    "talk_aa": {
        "viseme_weights": VISEMES["aa"],
        "gaze_target": {"yaw_deg": 4.0, "pitch_deg": -1.0},
    },
    "talk_O": {
        "viseme_weights": VISEMES["O"],
        "gaze_target": {"yaw_deg": -3.0, "pitch_deg": 1.0},
    },
    "angry": {
        "expression_state": "angry",
        "gaze_target": {"yaw_deg": 10.0, "pitch_deg": -4.0},
    },
    "thinking": {
        "expression_state": "thinking",
        "gaze_target": {"yaw_deg": 14.0, "pitch_deg": 5.0},
    },
}

def resolve(spec: str) -> tuple[str, dict]:
    if spec.endswith(".json") and os.path.isfile(spec):
        with open(spec) as f:
            return Path_stem(spec), json.load(f)
    if os.path.isfile(spec):
        with open(spec) as f:
            return Path_stem(spec), json.load(f)
    if spec in NAMED:
        return spec, NAMED[spec]
    # try control dir
    cand = os.path.join(os.path.dirname(OUT), "control", f"state_{spec}.json")
    if os.path.isfile(cand):
        with open(cand) as f:
            return spec, json.load(f)
    print(f"!! unknown state {spec}, using rest")
    return "rest", NAMED["rest"]

def Path_stem(p):
    return os.path.splitext(os.path.basename(p))[0].replace("state_", "")

# ── render each state ─────────────────────────────────────────────────────────
for spec in STATES:
    tag, state = resolve(spec)
    print(f"rendering beauty: {tag}")
    apply_state(state)
    sc.render.filepath = os.path.join(OUT, f"{PFX}{tag}.png")
    bpy.ops.render.render(write_still=True)
    print(f"  → {PFX}{tag}.png")

# contact sheet
try:
    from PIL import Image, ImageDraw, ImageFont
    tags = [resolve(s)[0] for s in STATES]
    paths = [os.path.join(OUT, f"{PFX}{t}.png") for t in tags]
    paths = [p for p in paths if os.path.isfile(p)]
    if paths:
        ims = [Image.open(p).convert("RGB") for p in paths]
        # resize to common height
        h = 640
        ims = [im.resize((int(im.size[0] * h / im.size[1]), h)) for im in ims]
        w = max(im.size[0] for im in ims)
        pad, lh = 10, 32
        cols = min(4, len(ims))
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + lh + pad) + pad), (18, 22, 26))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except Exception:
            font = ImageFont.load_default()
        for i, (im, tag) in enumerate(zip(ims, tags)):
            r, c = divmod(i, cols)
            x = pad + c * (w + pad)
            y = pad + r * (h + lh + pad)
            sheet.paste(im, (x, y))
            draw.text((x + 8, y + h + 6), tag, fill=(210, 220, 230), font=font)
        sheet_path = os.path.join(OUT, "_fullsheet.jpg" if FULL else "_herosheet.jpg")
        sheet.save(sheet_path, quality=92)
        print(f"wrote {sheet_path}")
except Exception as e:
    print(f"sheet skipped: {e}")

print("ok")
