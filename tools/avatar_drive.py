"""Time-varying avatar drive — ARKit shapes + jaw bone + gaze.

    blender -b --python tools/avatar_drive.py -- \
        <body.blend> <out_dir> <fwd_deg> [--synth | audio.wav] [seconds]

Control-surface drive (contract v1). Replaces jaw-only flap (tools/jaw_drive.py) with:
  * jawOpen → jaw BONE (max 22°)
  * mouth ARKit keys from a simple viseme schedule (synth) or envelope (audio)
  * light gaze drift so the face is not a statue
  * rest_loop hold on the last frames (rest-state law)

Always writes:
  * drive_frames.jsonl  — one control-surface frame object per line (TTS / live sink)
  * drive_report.json
  * front/f_####.png (front_full/ with --full) + alpha_talk.mp4 when ffmpeg is available

NOT full phoneme lipsync — envelope + viseme rhythm. Phoneme tracks can feed the same
viseme_weights field later without schema change.
"""
import bpy, sys, os, math, subprocess, json, shutil
import numpy as np
from mathutils import Vector, Matrix

# import pure presets without running blender apply path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import VISEMES, PRESETS, ENVELOPE, GRAPHEME_VISEMES, text_to_visemes  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
# --full: frame the whole figure (legs + hooves) instead of the waist-up companion
# crop. Stripped before positional parsing so it can sit anywhere; note that the
# audio positional may itself be the literal "--synth", so only "--full" is removed.
FULL = "--full" in argv
argv = [x for x in argv if x != "--full"]
# --text "..." : derive visemes from the SPOKEN TEXT instead of energy buckets.
# Energy-only derivation exercised 5 of 15 pinned visemes (measured), so the mouth could
# only open and close — the "robotic" read. With the text we get lip closures, sibilants,
# rounding and spreading. Contract v1 anticipated this: the phoneme track plugs into the
# same viseme_weights field, no schema fork.
TEXT = None
if "--text" in argv:
    i = argv.index("--text")
    TEXT = argv[i + 1] if i + 1 < len(argv) else None
    del argv[i:i + 2]
RIG, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
SRC = argv[3] if len(argv) > 3 else "--synth"
SECS = float(argv[4]) if len(argv) > 4 else 4.0
# Envelope pipeline constants come from the CONTRACT (control_surface.ENVELOPE),
# not from literals here — the live renderer derives visemes from the same block.
FPS = ENVELOPE["fps"]
MAXDEG = ENVELOPE["jaw"]["max_deg"]
_SR = ENVELOPE["sample_rate"]
os.makedirs(OUT, exist_ok=True)
N_FR = int(SECS * FPS)
frame_log: list[dict] = []

# ── text-driven viseme timeline ──────────────────────────────────────────────
def viseme_spans_from_text(text, env, fps):
    """Lay the text's viseme sequence over the audio's VOICED runs.

    Not forced alignment — there is no phoniser here. It segments the envelope into voiced
    runs (the words), splits the text into words, matches them up, then distributes each
    word's visemes inside its run weighted by `GRAPHEME_VISEMES['durations']` so vowels hold
    and stops stay brief. Returns [(start_frame, end_frame, viseme)].

    When word and run counts disagree (the usual case — the envelope splits on breaths, not
    spaces) words are distributed proportionally rather than dropped, so the mouth keeps
    moving through the whole utterance instead of stopping when it runs out of runs.
    """
    sil_max = ENVELOPE["classes"][0]["max"]
    dur_w = GRAPHEME_VISEMES["durations"]
    n = len(env)

    runs = []
    f = 0
    while f < n:
        if env[f] >= sil_max:
            g = f
            while g < n and env[g] >= sil_max:
                g += 1
            if g - f >= 2:          # ignore single-frame blips
                runs.append((f, g))
            f = g
        else:
            f += 1
    if not runs:
        return []

    toks = text_to_visemes(text)
    words, cur = [], []
    for t in toks:
        if t == "sil":
            if cur:
                words.append(cur); cur = []
        else:
            cur.append(t)
    if cur:
        words.append(cur)
    if not words:
        return []

    # distribute words across runs proportionally to each run's length
    total_len = sum(b - a for a, b in runs)
    spans = []
    wi = 0
    for ri, (a, b) in enumerate(runs):
        share = (b - a) / max(total_len, 1)
        take = max(1, round(share * len(words))) if ri < len(runs) - 1 else max(1, len(words) - wi)
        chunk = [v for w in words[wi:wi + take] for v in w]
        wi += take
        if not chunk:
            continue
        weights = [dur_w.get(v, 1.0) for v in chunk]
        tot = sum(weights) or 1.0
        t = float(a)
        for v, w in zip(chunk, weights):
            span = (b - a) * (w / tot)
            s0, s1 = int(round(t)), int(round(t + span))
            if s1 > s0:
                spans.append((s0, min(s1, b), v))
            t += span
        if wi >= len(words):
            break
    return spans


def coarticulate(spans, n_frames, fps):
    """Per-frame viseme weights with attack/release ramps — mouths do not SNAP.

    Each span contributes a trapezoid; contributions MAX-merge (the contract's own layering
    verb). `carry` bleeds a neighbouring shape in, which is what coarticulation physically
    is: the lips are already moving toward the next sound before the current one ends.
    """
    ca = ENVELOPE["coartic"]
    atk = max(1, int(round(ca["attack_s"] * fps)))
    rel = max(1, int(round(ca["release_s"] * fps)))
    carry = float(ca["carry"])
    labels = ["sil"] * n_frames
    out = [dict() for _ in range(n_frames)]
    for (s0, s1, v) in spans:
        w = VISEMES.get(v, {})
        if not w:
            continue
        lo, hi = max(0, s0 - atk), min(n_frames, s1 + rel)
        for f in range(lo, hi):
            if f < s0:
                a = carry * (f - (s0 - atk)) / atk           # anticipatory
            elif f < s1:
                a = 1.0
            else:
                a = carry * (1.0 - (f - s1) / rel)           # carry-over
            if a <= 0.0:
                continue
            if s0 <= f < s1:
                labels[f] = v
            for k, val in w.items():
                out[f][k] = max(out[f].get(k, 0.0), val * a)
    return labels, out

# ── envelope ──────────────────────────────────────────────────────────────────
if SRC == "--synth":
    t = np.arange(N_FR) / FPS
    env = np.zeros(N_FR)
    # syllable bursts: (t0, dur, amp, viseme)
    syll = [
        (0.15, 0.18, 1.00, "aa"), (0.40, 0.14, 0.70, "E"),
        (0.60, 0.20, 0.95, "O"),  (0.90, 0.12, 0.50, "PP"),
        (1.15, 0.18, 0.88, "I"),  (1.42, 0.15, 0.65, "nn"),
        (1.68, 0.24, 1.00, "aa"), (2.05, 0.12, 0.45, "SS"),
        (2.28, 0.18, 0.85, "U"),  (2.55, 0.14, 0.60, "RR"),
        (2.80, 0.22, 0.92, "O"),  (3.15, 0.16, 0.70, "E"),
        (3.45, 0.20, 0.88, "aa"),
    ]
    viseme_track = ["sil"] * N_FR
    for t0, dur, amp, vis in syll:
        m = (t >= t0) & (t < t0 + dur)
        if not m.any():
            continue
        u = (t[m] - t0) / dur
        env[m] = np.maximum(env[m], amp * np.sin(np.pi * u) ** 0.7)
        for i in np.where(m)[0]:
            viseme_track[i] = vis
    label = "synthetic syllable rhythm + viseme schedule"
else:
    wav = os.path.join(OUT, "_audio.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.abspath(SRC),
         "-ac", "1", "-ar", str(_SR), "-f", "wav", wav],
        check=True,
    )
    import wave
    with wave.open(wav) as w:
        n = w.getnframes()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
    SECS = len(pcm) / float(_SR)
    N_FR = int(SECS * FPS)
    hop = max(1, len(pcm) // max(1, N_FR))
    env = np.array([
        np.sqrt((pcm[i * hop:(i + 1) * hop] ** 2).mean() + 1e-12)
        for i in range(N_FR)
    ])
    env = env / max(env.max(), 1e-9)
    env = env ** ENVELOPE["rms_gamma"]
    # energy → viseme class, from the shared contract table (first bucket wins)
    viseme_track = []
    for e in env:
        viseme_track.append(next(c["viseme"] for c in ENVELOPE["classes"] if e < c["max"]))
    label = os.path.basename(SRC)

k = np.array(ENVELOPE["smooth_kernel"])
env = np.convolve(np.pad(env, 1, mode="edge"), k, mode="same")[1:-1]
# hold rest on last 0.4s (rest-state law)
rest_n = min(N_FR, int(ENVELOPE["rest_hold_s"] * FPS))
print(f"drive: {label}  {SECS:.2f}s  {N_FR} frames @ {FPS}fps  "
      f"env [{env.min():.2f},{env.max():.2f}]  rest_hold {rest_n}f")

# Text-driven viseme track (preferred when the line is known). Falls back to the energy
# buckets when no --text is given, so existing callers behave exactly as before.
TXT_LABELS = TXT_WEIGHTS = None
if TEXT:
    _spans = viseme_spans_from_text(TEXT, env, FPS)
    if _spans:
        TXT_LABELS, TXT_WEIGHTS = coarticulate(_spans, N_FR, FPS)
        _used = sorted({v for _, _, v in _spans})
        print(f"  text lipsync: {len(_spans)} viseme spans, {len(_used)} distinct -> {' '.join(_used)}")
    else:
        print("  !! text lipsync: no voiced runs found; falling back to energy buckets")

# ── load rig ──────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath=RIG)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = ob.data
Nv = len(me.vertices)
co = np.empty((Nv, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0])
lat = np.array([-fwd[1], fwd[0], 0.0])
di = [i for i, m in enumerate(me.materials) if m and m.name.startswith("clyffy_mouth_interior")]
mouth = co.mean(0)
if di:
    cav = sorted({v for p in me.polygons if p.material_index == di[0] for v in p.vertices})
    if cav:
        mouth = co[cav].mean(0)

def bone(*names):
    for n in names:
        if n in arm.pose.bones:
            return arm.pose.bones[n]
    return None

jaw_b = bone("jaw")
eye_L = bone("eye_L", "leftEye")
eye_R = bone("eye_R", "rightEye")
kb = me.shape_keys.key_blocks if me.shape_keys else None
assert jaw_b is not None, "no jaw bone"
assert kb is not None, "no shape keys — use body blend with shapes"

# all ARKit keys we might touch
SHAPE_NAMES = [k.name for k in kb if k.name != "Basis"]
hv = Vector(jaw_b.bone.head_local)
lv = Vector(lat)

def zero_shapes():
    for n in SHAPE_NAMES:
        kb[n].value = 0.0

def set_jaw(amount: float):
    amount = float(max(0.0, min(1.0, amount)))
    ang = math.radians(MAXDEG) * amount
    R = (Matrix.Translation(hv)
         @ Matrix.Rotation(ang, 4, lv)
         @ Matrix.Translation(-hv))
    jaw_b.matrix = R @ jaw_b.bone.matrix_local

# ── keyframe ──────────────────────────────────────────────────────────────────
jaw_b.rotation_mode = "QUATERNION"
for eb in (eye_L, eye_R):
    if eb:
        eb.rotation_mode = "XYZ"

for f in range(N_FR):
    frame = f + 1
    zero_shapes()
    # rest hold at end
    if f >= N_FR - rest_n:
        set_jaw(0.0)
        for eb in (eye_L, eye_R):
            if eb:
                eb.rotation_euler = (0, 0, 0)
        state = {
            "frame": frame,
            "t": round((frame - 1) / FPS, 5),
            "rest_loop": True,
            "viseme": "sil",
            "env": 0.0,
            "viseme_weights": {},
            "gaze_target": {"yaw_deg": 0.0, "pitch_deg": 0.0},
            "goggle_state": "on-face",
        }
    else:
        e = float(env[f])
        if TXT_WEIGHTS is not None:
            vis = TXT_LABELS[f]
            weights = dict(TXT_WEIGHTS[f])
        else:
            vis = viseme_track[f]
            weights = dict(VISEMES.get(vis, {}))
        # scale viseme by envelope so quiet = closed
        _j = ENVELOPE["jaw"]
        jaw_amt = weights.pop("jawOpen", 0.0) * (_j["scale_base"] + _j["scale_env"] * e)
        # also lift jaw from raw envelope so silence stays shut
        jaw_amt = max(jaw_amt, _j["env_floor"] * e)
        applied = {}
        for name, val in weights.items():
            if name in kb:
                _w = ENVELOPE["weight_scale"]
                v = float(val) * (_w["base"] + _w["env"] * e)
                kb[name].value = v
                applied[name] = round(v, 4)
        applied["jawOpen"] = round(float(jaw_amt), 4)
        set_jaw(jaw_amt)
        # gentle gaze drift
        yaw = 8.0 * math.sin(2 * math.pi * f / (FPS * 2.5))
        pitch = 3.0 * math.sin(2 * math.pi * f / (FPS * 3.1) + 0.4)
        for eb in (eye_L, eye_R):
            if eb:
                eb.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
        state = {
            "frame": frame,
            "t": round((frame - 1) / FPS, 5),
            "rest_loop": False,
            "viseme": vis,
            "env": round(e, 4),
            "viseme_weights": applied,
            "gaze_target": {
                "yaw_deg": round(yaw, 3),
                "pitch_deg": round(pitch, 3),
            },
            "goggle_state": "on-face",
        }
    frame_log.append(state)

    # insert keys
    jaw_b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    jaw_b.keyframe_insert(data_path="location", frame=frame)
    for eb in (eye_L, eye_R):
        if eb:
            eb.keyframe_insert(data_path="rotation_euler", frame=frame)
    for n in SHAPE_NAMES:
        kb[n].keyframe_insert(data_path="value", frame=frame)
    if f % 24 == 0:
        print(f"  frame {frame}/{N_FR} vis={viseme_track[f]} env={env[f]:.2f}")

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N_FR
sc.render.fps = FPS
for o in list(bpy.data.objects):
    if o.type == "CAMERA":
        bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"
if sc.world is None:
    sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x = 720
sc.render.resolution_y = 900
cd = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam)
sc.camera = cam
cd.type = "ORTHO"
cd.clip_start = 0.01
cd.clip_end = H * 40
cd.ortho_scale = H * (1.12 if FULL else 0.70)
hc = co[co[:, 2] > 0.208].mean(0)
face_z = (float((co[:, 2].min() + co[:, 2].max()) * 0.5) if FULL
          else float(hc[2] - H * 0.04))
Rr = H * 4.5
# front only for alpha (faster); keep q38 optional
for off, tag in ((0.0, "front_full" if FULL else "front"),):
    ang = a + off
    cam.location = (hc[0] + math.sin(ang) * Rr, hc[1] - math.cos(ang) * Rr, face_z)
    cam.rotation_euler = (math.radians(90), 0, ang)
    d = os.path.join(OUT, tag)
    os.makedirs(d, exist_ok=True)
    sc.render.filepath = os.path.join(d, "f_")
    sc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(animation=True)
    print(f"  rendered {tag} ({N_FR} frames)")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_avatar_drive.blend"))

# control-surface timeline (contract v1)
jsonl_path = os.path.join(OUT, "drive_frames.jsonl")
with open(jsonl_path, "w") as f:
    for st in frame_log:
        f.write(json.dumps(st, separators=(",", ":")) + "\n")
print(f"wrote {jsonl_path} ({len(frame_log)} frames)")

# mp4 preview (mux source audio when not --synth)
mp4 = os.path.join(OUT, "alpha_talk.mp4")
ffmpeg = shutil.which("ffmpeg")
audio_src = None
if SRC != "--synth":
    cand = os.path.abspath(SRC)
    if os.path.isfile(cand):
        audio_src = cand
    # avatar_drive also writes _audio.wav when converting
    wav_conv = os.path.join(OUT, "_audio.wav")
    if os.path.isfile(wav_conv):
        audio_src = wav_conv

if ffmpeg:
    # frame dir follows the render tag, so --full muxes its own frames
    fdir = "front_full" if FULL else "front"
    front_dir = os.path.join(OUT, fdir)
    samples = sorted(os.listdir(front_dir)) if os.path.isdir(front_dir) else []
    if samples:
        # Blender writes f_0001.png (4-digit) starting at frame 1
        img_pat = os.path.join(front_dir, "f_%04d.png")
        if not os.path.isfile(os.path.join(front_dir, "f_0001.png")):
            img_pat = os.path.join(front_dir, "f_%d.png")
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", img_pat,
        ]
        if audio_src:
            cmd += ["-i", audio_src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-crf", "18", mp4]
        else:
            cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", mp4]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.isfile(mp4):
            print(f"wrote {mp4}" + (" (with audio)" if audio_src else " (video only)"))
        else:
            print(f"ffmpeg mp4 failed: {r.stderr[-400:] if r.stderr else r.stdout}")
    else:
        print(f"no {fdir} frames for mp4")
else:
    print("ffmpeg not found — skip alpha_talk.mp4")

meta = {
    "label": label,
    "seconds": SECS,
    "frames": N_FR,
    "fps": FPS,
    "max_jaw_deg": MAXDEG,
    "rest_hold_frames": rest_n,
    "visemes_used": sorted(set(viseme_track)),
    "contract": "control_surface v1",
    "drive_frames": "drive_frames.jsonl",
    "source": label,
    "audio_muxed": bool(audio_src),
}
with open(os.path.join(OUT, "drive_report.json"), "w") as f:
    json.dump(meta, f, indent=2)
print("ok")
