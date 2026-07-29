"""Drive the jaw bone from an envelope and render a motion preview.

    blender -b --python tools/jaw_drive.py -- <rig.blend> <out_dir> <fwd_deg> [audio|--synth] [seconds]

With an audio file it decodes via ffmpeg and uses the RMS envelope. With --synth it uses
a deterministic syllable rhythm, so the rig can be eyeballed before a voice exists.
NOTE: this is JAW FLAP, not lipsync -- with no visemes every phoneme looks the same.
"""
import bpy, sys, os, math, subprocess
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--")+1:]
RIG, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
SRC   = argv[3] if len(argv) > 3 else "--synth"
SECS  = float(argv[4]) if len(argv) > 4 else 4.0
FPS   = 24
MAXDEG = 22.0
os.makedirs(OUT, exist_ok=True)
N_FR = int(SECS*FPS)

if SRC == "--synth":
    # deterministic syllable rhythm: bursts with attack/decay and breath gaps
    t = np.arange(N_FR)/FPS
    env = np.zeros(N_FR)
    syll = [(0.15,0.20,1.00),(0.42,0.14,0.72),(0.62,0.22,0.95),(0.95,0.13,0.55),
            (1.18,0.20,0.88),(1.45,0.16,0.70),(1.70,0.26,1.00),(2.10,0.12,0.48),
            (2.32,0.20,0.85),(2.60,0.15,0.62),(2.86,0.24,0.93),(3.25,0.18,0.75),
            (3.55,0.22,0.90)]
    for t0, dur, amp in syll:
        m = (t >= t0) & (t < t0+dur)
        if not m.any(): continue
        u = (t[m]-t0)/dur
        env[m] = np.maximum(env[m], amp*np.sin(np.pi*u)**0.7)
    label = "synthetic syllable rhythm (NOT a voice)"
else:
    wav = os.path.join(OUT, "_audio.wav")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",os.path.abspath(SRC),
                    "-ac","1","-ar","16000","-f","wav",wav], check=True)
    import wave
    with wave.open(wav) as w:
        n = w.getnframes(); pcm = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64)/32768.0
    SECS = len(pcm)/16000.0; N_FR = int(SECS*FPS)
    hop = max(1, len(pcm)//max(1, N_FR))
    env = np.array([np.sqrt((pcm[i*hop:(i+1)*hop]**2).mean() + 1e-12) for i in range(N_FR)])
    env = env/max(env.max(), 1e-9)
    env = env**0.6                       # perceptual-ish; keeps quiet speech visible
    label = os.path.basename(SRC)

# light smoothing so the jaw has mass instead of snapping
k = np.array([0.15, 0.7, 0.15])
env = np.convolve(np.pad(env, 1, mode='edge'), k, mode='same')[1:-1]
print(f"drive: {label}  {SECS:.2f}s  {N_FR} frames @ {FPS}fps  env min {env.min():.2f} max {env.max():.2f}")

bpy.ops.wm.open_mainfile(filepath=RIG)
ob  = [o for o in bpy.data.objects if o.type == "MESH"][0]
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
me  = ob.data
Nv  = len(me.vertices)
co  = np.empty((Nv, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a   = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
di  = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cav = sorted({v for p in me.polygons if p.material_index == di for v in p.vertices})
mouth = co[cav].mean(axis=0)

jb = arm.pose.bones["jaw"]; hv = Vector(jb.bone.head_local); lv = Vector(lat)
jb.rotation_mode = 'QUATERNION'
for f in range(N_FR):
    ang = math.radians(MAXDEG)*float(env[f])
    R = Matrix.Translation(hv) @ Matrix.Rotation(ang, 4, lv) @ Matrix.Translation(-hv)
    jb.matrix = R @ jb.bone.matrix_local
    bpy.context.view_layer.update()
    jb.keyframe_insert(data_path="rotation_quaternion", frame=f+1)
    jb.keyframe_insert(data_path="location", frame=f+1)

sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N_FR
sc.render.fps = FPS
for o in list(bpy.data.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
sc.render.engine = "BLENDER_WORKBENCH"; sc.world = bpy.data.worlds.new("W")
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 720
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.clip_start = 0.01; cd.clip_end = H*30; cd.ortho_scale = H*0.42
R2 = H*5
for off, tag in ((0.0, "front"), (math.radians(38), "q38")):
    ang = a + off
    cam.location = (mouth[0]+math.sin(ang)*R2, mouth[1]-math.cos(ang)*R2, mouth[2]+H*0.03)
    cam.rotation_euler = (math.radians(90), 0, ang)
    d = os.path.join(OUT, tag); os.makedirs(d, exist_ok=True)
    sc.render.filepath = os.path.join(d, "f_")
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)
    print(f"  rendered {tag}")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_talktest.blend"))
print("ok")
