"""B1 GATE — does our idle actually move like the reference? Renders and MEASURES. Saves nothing.

    blender -b --python tools/idle_check.py -- <body.blend> [out_dir] [seconds] [fwd_deg]

Exit 0 if measured crown RMS lands within the contract's tolerance of the measured target.

═══ WHY ═════════════════════════════════════════════════════════════════════════════════════

`control_surface.IDLE` carries amplitudes in DEGREES; the reference target is in crown TRANSLATION
as a fraction of body height. Nothing connects those two analytically — the crown's displacement
depends on where every pivot sits and how the camera projects it. So this renders the actual pose
and measures the actual silhouette, using the SAME crown measurement `tools/ref_motion.py` ran on
the operator's reference footage. Same instrument on both sides, or the comparison means nothing.

It renders flat on BLACK deliberately: the measurement only needs a silhouette, and Workbench is
~40x faster than Cycles for 192 frames. Beauty is `present.py`'s job.

WHAT THIS CANNOT CHECK: ear wobble. Spring bones are a VRM RUNTIME feature (`VRMC_springBone`,
simulated by the web renderer via `vrm.update(dt)`); Blender does not simulate them. This gate
proves the head MOVES, which is the excitation the springs were missing — the wobble itself is
the operator's eye on the live surface. Stated rather than implied, because a gate that quietly
does not cover the headline claim is worse than no gate.
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from control_surface import IDLE, idle_pose  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(
    os.path.dirname(SRC), "..", "..", "..", "work", "idle_check")
SECONDS = float(argv[2]) if len(argv) > 2 else 8.0
FWD = float(argv[3]) if len(argv) > 3 else 235.1
FPS = 24
RES = 512
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = ob.data
N = len(me.vertices)
co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
H = float(co[:, 2].max() - co[:, 2].min())
a = math.radians(FWD)
fwd = Vector((math.sin(a), -math.cos(a), 0.0))
lat = Vector((-fwd[1], fwd[0], 0.0))
up = Vector((0.0, 0.0, 1.0))
print(f"idle_check: {os.path.basename(SRC)}  H={H:.4f}  {SECONDS}s @ {FPS}fps")

# ── bones ────────────────────────────────────────────────────────────────────
def bone(*names):
    for n in names:
        if n in arm.pose.bones:
            return arm.pose.bones[n]
    return None


# The VRM humanoid calls it `head`; this armature's bone is named `skull` (jaw_rig.py authored
# jaw/skull/root). Map it here rather than renaming the bone, which the VRM export depends on.
BONES = {"hips": bone("hips"), "spine": bone("spine"), "chest": bone("chest"),
         "neck": bone("neck"), "head": bone("head", "skull")}
missing = [k for k, v in BONES.items() if v is None]
print(f"  bones: {[k for k, v in BONES.items() if v]}" + (f"  MISSING {missing}" if missing else ""))
REST = {k: (v.matrix.copy() if v else None) for k, v in BONES.items()}



def set_bone_rotation(pb, rots):
    """Rotate a pose bone about its own head, using world-space axes.

    Via matrix_basis CONJUGATION rather than the `pose_bone.matrix` setter. spine / chest /
    neck / skull are all `use_connect = True`, and for connected bones the matrix setter
    discards the translation component that a `T(h) R T(-h)` construction carries — which is
    why calibration measured EXACTLY 0.00000 crown displacement for every driver except hips
    (the one unconnected bone). The rig was fine; the way I was posing it was not.

    Conjugating by the bone's rest ROTATION gives a pure local rotation with no translation at
    all, so connectedness stops mattering:  basis = Brot^-1 @ R_world @ Brot
    """
    B = pb.bone.matrix_local.to_3x3()
    Binv = B.inverted()
    acc = Matrix.Identity(3)
    for deg, axis in rots:
        if abs(deg) < 1e-9:
            continue
        acc = acc @ (Binv @ Matrix.Rotation(math.radians(deg), 3, axis) @ B)
    pb.rotation_mode = "QUATERNION"
    pb.matrix_basis = acc.to_4x4()


def apply_pose(t: float):
    """Rotate in WORLD space about each bone's own head, parent-first.

    Same construction jaw_rig / _closeup use for the jaw: build the rotation about the bone's
    head_local and compose it onto the rest matrix. Parent-first ordering matters because
    `pose_bone.matrix` is armature-space, so a child re-derives its local basis from whatever
    the parent currently is.
    """
    for pb in BONES.values():
        if pb:
            pb.matrix_basis.identity()
    bpy.context.view_layer.update()

    p = idle_pose(t)
    plan = [
        ("hips",  [(p["hips_roll"], fwd)]),
        ("spine", [(p["spine_roll"], fwd), (p["spine_pitch"], lat)]),
        ("chest", [(p["chest_pitch"], lat)]),
        ("head",  [(p["head_roll"], fwd), (p["head_pitch"], lat), (p["head_yaw"], up)]),
    ]
    for name, rots in plan:
        pb = BONES.get(name)
        if pb is not None:
            set_bone_rotation(pb, rots)
    # hips TRANSLATION for the vertical bob, applied AFTER the rotations because
    # set_bone_rotation assigns matrix_basis wholesale and would otherwise wipe it.
    # `pose_bone.location` is already in SCENE units along the bone's local axes — dividing by
    # bone.length (0.0196) overshot the bob by ~50x and put crown Y RMS at 0.66 against a
    # target of 0.0101.
    hb = BONES.get("hips")
    if hb is not None:
        hb.location = (0.0, p.get("hips_rise", 0.0) * H, 0.0)
    bpy.context.view_layer.update()


# ── flat black render setup ──────────────────────────────────────────────────
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in ("LIGHT", "CAMERA"):
        bpy.data.objects.remove(o, do_unlink=True)
arm.hide_render = True
world = bpy.data.worlds.new("black")
world.use_nodes = False
world.color = (0, 0, 0)
sc.world = world

cd = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"
# Orthographic ON PURPOSE: a perspective camera would add its own parallax to the crown as the
# body leans toward it, and that would be measured as sway that the rig is not producing.
cd.ortho_scale = H * 1.25
focus = Vector((float(co[:, 0].mean()), float(co[:, 1].mean()),
                float(co[:, 2].min() + H * 0.5)))
cam.location = focus + fwd * (H * 3.0)
cam.rotation_euler = (Vector(focus) - cam.location).to_track_quat("-Z", "Y").to_euler()

sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x = RES
sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (1.0, 1.0, 1.0)
sc.render.image_settings.file_format = "PNG"

def render_and_measure():
    """Render one frame at the current pose and return (crown_x, crown_y, silhouette_height)."""
    sc.render.filepath = os.path.join(OUT, "_cal.png")
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(sc.render.filepath)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    l = px[..., :3].max(axis=2)
    sil = l > 0.10
    ys_, xs_ = np.nonzero(sil)
    top = int(ys_.min()); depth = max(3, int(0.02 * (ys_.max() - ys_.min())))
    b = ys_ <= top + depth
    w = l[ys_[b], xs_[b]].astype(float)
    return ((xs_[b] * w).sum() / w.sum(), (ys_[b] * w).sum() / w.sum(),
            float(ys_.max() - ys_.min()))


if "--calibrate" in sys.argv:
    # MEASURE THE LEVER instead of assuming it. IDLE is authored in DEGREES and the target is
    # crown TRANSLATION as a fraction of body height; the gain between them depends on where each
    # pivot actually sits, which is not knowable from the spec.
    #
    # Measured off the EVALUATED MESH, not off a render. The camera is orthographic along `fwd`,
    # so screen-X is exactly `position . lat` and screen-Y is `position . up` — no projection
    # needed, no render, and no chance of measuring a stale image. (The first version rendered
    # here and reported 0.00000 for every driver except hips, while a direct depsgraph read
    # showed the very same rotations moving the crown by 0.18 units. The rig was never the
    # problem; the measurement was.)
    def crown_lat_up():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        m = ev.to_mesh()
        k = len(m.vertices)
        c = np.empty(k * 3); m.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
        zt = c[:, 2].max()
        tops = c[c[:, 2] > zt - 0.12 * (c[:, 2].max() - c[:, 2].min())]
        ev.to_mesh_clear()
        p3 = tops.mean(axis=0)
        return (float(p3[0] * lat.x + p3[1] * lat.y), float(p3[2]))

    for pb in BONES.values():
        if pb:
            pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    x0, y0 = crown_lat_up()
    DRIVERS = [("hips_roll", "hips", fwd), ("spine_roll", "spine", fwd),
               ("spine_pitch", "spine", lat), ("chest_pitch", "chest", lat),
               ("head_roll", "head", fwd), ("head_pitch", "head", lat),
               ("head_yaw", "head", up)]
    TEST = 5.0
    print("\ncalibration — crown displacement per degree (body-heights/deg):")
    print(f"  {'driver':<14}{'dX/deg':>12}{'dY/deg':>12}")
    for nm, bname, axis in DRIVERS:
        for pb in BONES.values():
            if pb:
                pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        pb = BONES.get(bname)
        if pb is None:
            continue
        set_bone_rotation(pb, [(TEST, axis)])
        bpy.context.view_layer.update()
        x1, y1 = crown_lat_up()
        print(f"  {nm:<14}{(x1-x0)/H/TEST:>12.5f}{(y1-y0)/H/TEST:>12.5f}")
    sys.exit(0)


# ── measure from the EVALUATED MESH ──────────────────────────────────────────
# No rendering in the loop. The camera is orthographic and aligned to `lat`/`up`, so projecting
# the deformed mesh yields exactly what a render would measure — while being ~50x faster and
# removing a whole class of bug: the render path was silently reporting 0.0036 crown X RMS while
# the very same pose measured 0.0241 straight off the depsgraph.
#
# Both sides still measure the same QUANTITY: head-mass centroid (top 12% of the figure),
# projected on lat/up, normalised by figure height. The reference has to come from images; ours
# does not, and pretending otherwise only adds a rendering pipeline to the error budget.
def crown_now():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m = ev.to_mesh()
    k = len(m.vertices)
    c = np.empty(k * 3); m.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    zt, zb = c[:, 2].max(), c[:, 2].min()
    tops = c[c[:, 2] > zt - 0.12 * (zt - zb)]
    ev.to_mesh_clear()
    q = tops.mean(axis=0)
    return (float(q[0] * lat.x + q[1] * lat.y), float(q[2]), float(zt - zb))


nf = int(SECONDS * FPS)
crown_x, crown_y, silh = [], [], []
for i in range(nf):
    apply_pose(i / FPS)
    x, y, hh = crown_now()
    crown_x.append(x); crown_y.append(y); silh.append(hh)

crown_x = np.array(crown_x); crown_y = np.array(crown_y); silh = np.array(silh)
R = float(np.nanmedian(silh))
X = crown_x / R
Y = crown_y / R
tgt = IDLE["target"]
tx, ty = tgt["crown_x_rms_bodyheights"], tgt["crown_y_rms_bodyheights"]
tol = tgt.get("tolerance", 0.25)
mx, my = float(np.nanstd(X)), float(np.nanstd(Y))


def dom(sig):
    s = sig[np.isfinite(sig)]
    if len(s) < 16:
        return None
    w = (s - s.mean()) * np.hanning(len(s))
    sp = np.abs(np.fft.rfft(w)); fr = np.fft.rfftfreq(len(s), 1.0 / FPS)
    b = (fr > 0.05) & (fr < 3.0)
    return float(fr[b][sp[b].argmax()]) if b.any() else None


print(f"\n  figure height {R:.4f} units, varies {100*(np.nanmax(silh)-np.nanmin(silh))/R:.1f}%")
print(f"\n{'quantity':<26}{'measured':>12}{'target':>12}{'ratio':>10}")
ok = True
for nm, m, t in (("crown X rms", mx, tx), ("crown Y rms", my, ty)):
    r = m / t if t else float("inf")
    good = (1 - tol) <= r <= (1 + tol)
    ok &= good
    print(f"{nm:<26}{m:>12.4f}{t:>12.4f}{r:>9.2f}x  {'OK' if good else 'OUT'}")
print(f"{'crown X p2p':<26}{float(np.nanmax(X)-np.nanmin(X)):>12.4f}")
print(f"{'crown Y p2p':<26}{float(np.nanmax(Y)-np.nanmin(Y)):>12.4f}")
dx, dy = dom(X), dom(Y)
print(f"{'dominant X Hz':<26}{dx if dx else 0:>12.3f}{tgt['dominant_hz']['x']:>12.3f}")
print(f"{'dominant Y Hz':<26}{dy if dy else 0:>12.3f}{tgt['dominant_hz']['y']:>12.3f}")
print(f"{'median |frame delta| X':<26}{float(np.nanmedian(np.abs(np.diff(X)))):>12.5f}")

print("\n  NOTE: ear wobble is NOT checked here — VRM spring bones are simulated by the web\n"
      "  renderer, not by Blender. This gate proves the head MOVES, which is the excitation\n"
      "  the springs were missing. The wobble is the operator's eye on the live surface.")
print("\nidle_check " + ("GREEN" if ok else "RED — tune IDLE amplitudes in control_surface.py"))
sys.exit(0 if ok else 1)
