"""Prepare the body-rigged Clyffy blend for VRM and export a .vrm.

    blender -b --python tools/vrm_export.py -- <body.blend> <out.vrm>

Requires the VRM Add-on for Blender (saturday06) — installed under
~/.config/blender/5.2/scripts/addons/VRM_Addon_for_Blender-release (also linked from 4.0 install).

Steps:
  1. Rename bones (+ matching vertex groups) to VRM humanoid names
  2. Auto-assign humanoid bones
  3. Bind ARKit morphs to VRM1 expressions
  4. Configure bone-mode lookAt on the eye bones
  5. Author VRMC_springBone (ears L/R + tail) via tools/spring_bones.py
  6. Export .vrm
"""
import bpy, sys, os, math, addon_utils, json, importlib.util
from pathlib import Path

# load sibling tools/spring_bones.py regardless of cwd
_SPRING_PATH = Path(__file__).resolve().parent / "spring_bones.py"
_spec = importlib.util.spec_from_file_location("clyffy_spring_bones", _SPRING_PATH)
_spring_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_spring_mod)
author_spring_bones = _spring_mod.author_spring_bones

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
# Canonical forward (clyffy.pack.toml [calibration]). The mesh is authored facing
# FWD° in the Blender XY plane; VRM requires it face +Z. See the yaw fix below.
FWD = float(argv[2]) if len(argv) > 2 else 235.1
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)

# enable addon
mod = "VRM_Addon_for_Blender-release"
addon_utils.enable(mod, default_set=True, persistent=True)
print(f"enabled addon: {mod}")

bpy.ops.wm.open_mainfile(filepath=SRC)

# pick armature + mesh
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ob = next(o for o in bpy.data.objects if o.type == "MESH"
          and any(m.type == "ARMATURE" for m in o.modifiers))
print(f"armature={arm.name}  mesh={ob.name}  bones={len(arm.data.bones)}  "
      f"shape_keys={len(ob.data.shape_keys.key_blocks) if ob.data.shape_keys else 0}")

# ── FACE +Z (VRM 1.0 spec) ───────────────────────────────────────────────────
# ⚠️ FIXED 2026-07-27. Exports before this date were SPEC-VIOLATING: the model kept
# its Blender authoring yaw and faced +55.1° off +Z (= FWD 235.1° - 180°). Measured
# from the humanoid bones of the shipped file:
#     lateral(R->L) = [+0.572, 0, -0.820]   (spec: ~[+1, 0, 0])
#     forward       = [+0.814, +0.124, +0.568]   (spec: ~[0, 0, +1])
# Consequences seen downstream: the avatar renders in 3/4 view instead of front-on,
# and — the real bug — a consumer rotating the jaw about world X gets a pitch/yaw MIX,
# so the muzzle barely opens while the teeth swing sideways out through the lip.
# That is not a renderer bug to patch per-adapter; every consumer (three-vrm, Unity,
# Unreal) would inherit it. Fix at the source.
#
# Axis conversion: the mesh is authored facing [sin(FWD), -cos(FWD), 0] in Blender XY;
# yawing the rig by -FWD about Blender Z makes it face +Z after the addon's own
# orientation pass. VERIFY WITH tools/vrm_check.py, which measures facing from the EYE
# bones — NOT from leftUpperLeg/rightUpperLeg. Those are MIRRORED on this rig
# (body_rig.py treats -lat as "left" while +lat is the character's actual left), so any
# left/right-derived forward vector comes out backwards. That mistake cost a whole
# export cycle: it reported "spec-compliant" while the renderer showed the back of the head.
# The mesh is PARENTED to the armature, so rotating the armature carries everything, and
# the exporter bakes it into the root node TRS (no destructive transform-apply on a
# 44-shape-key mesh).
YAW = -FWD
arm.rotation_euler = (0.0, 0.0, math.radians(YAW))
print(f"VRM orientation: yawed rig by {YAW:.1f}° about Z so the model faces +Z (was {FWD - 180:.1f}° off)")

# ── rename bones to VRM humanoid names ────────────────────────────────────────
# Our body_rig names → VRM 1.0 humanoid names
RENAME = {
    "hips": "hips",
    "spine": "spine",
    "chest": "chest",
    "neck": "neck",
    "skull": "head",          # VRM expects "head"
    "jaw": "jaw",
    "eye_L": "leftEye",
    "eye_R": "rightEye",
    "shoulder_L": "leftShoulder",
    "upper_arm_L": "leftUpperArm",
    "lower_arm_L": "leftLowerArm",
    "hand_L": "leftHand",
    "shoulder_R": "rightShoulder",
    "upper_arm_R": "rightUpperArm",
    "lower_arm_R": "rightLowerArm",
    "hand_R": "rightHand",
    "upper_leg_L": "leftUpperLeg",
    "lower_leg_L": "leftLowerLeg",
    "foot_L": "leftFoot",
    "upper_leg_R": "rightUpperLeg",
    "lower_leg_R": "rightLowerLeg",
    "foot_R": "rightFoot",
    # non-humanoid extras keep their names
    "ear_L": "ear_L",
    "ear_R": "ear_R",
    "tail": "tail",
}

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
# rename carefully — two-pass to avoid collisions
tmp = {}
for old, new in RENAME.items():
    if old not in eb:
        print(f"  !! missing bone {old}")
        continue
    if old == new:
        continue
    t = f"__tmp_{old}"
    eb[old].name = t
    tmp[t] = new
for t, new in tmp.items():
    eb[t].name = new
bpy.ops.object.mode_set(mode="OBJECT")

# vertex groups must match bone names for the armature modifier
for g in list(ob.vertex_groups):
    if g.name in RENAME and RENAME[g.name] != g.name:
        g.name = RENAME[g.name]
# also fix any __tmp_ leftovers
for g in list(ob.vertex_groups):
    if g.name.startswith("__tmp_"):
        old = g.name[len("__tmp_"):]
        g.name = RENAME.get(old, old)

print("bones after rename:", [b.name for b in arm.data.bones])

# ── assign humanoid ───────────────────────────────────────────────────────────
# Ear/tail spring chains confuse the addon's structure-search auto-assign
# (it maps leftEye→ear_L, leftUpperLeg→tail, …). Force an explicit map and
# disable further automatic reassignment so export does not undo it.
import importlib
get_armature_extension = importlib.import_module(
    "VRM_Addon_for_Blender-release.editor.extension"
).get_armature_extension
HumanBoneName = importlib.import_module(
    "VRM_Addon_for_Blender-release.common.vrm1.human_bone"
).HumanBoneName

HUMANOID_MAP = {
    HumanBoneName.HIPS: "hips",
    HumanBoneName.SPINE: "spine",
    HumanBoneName.CHEST: "chest",
    HumanBoneName.NECK: "neck",
    HumanBoneName.HEAD: "head",
    HumanBoneName.JAW: "jaw",
    HumanBoneName.LEFT_EYE: "leftEye",
    HumanBoneName.RIGHT_EYE: "rightEye",
    HumanBoneName.LEFT_SHOULDER: "leftShoulder",
    HumanBoneName.LEFT_UPPER_ARM: "leftUpperArm",
    HumanBoneName.LEFT_LOWER_ARM: "leftLowerArm",
    HumanBoneName.LEFT_HAND: "leftHand",
    HumanBoneName.RIGHT_SHOULDER: "rightShoulder",
    HumanBoneName.RIGHT_UPPER_ARM: "rightUpperArm",
    HumanBoneName.RIGHT_LOWER_ARM: "rightLowerArm",
    HumanBoneName.RIGHT_HAND: "rightHand",
    HumanBoneName.LEFT_UPPER_LEG: "leftUpperLeg",
    HumanBoneName.LEFT_LOWER_LEG: "leftLowerLeg",
    HumanBoneName.LEFT_FOOT: "leftFoot",
    HumanBoneName.RIGHT_UPPER_LEG: "rightUpperLeg",
    HumanBoneName.RIGHT_LOWER_LEG: "rightLowerLeg",
    HumanBoneName.RIGHT_FOOT: "rightFoot",
}

def force_humanoid(arm_obj):
    ext = get_armature_extension(arm_obj.data)
    hb = ext.vrm1.humanoid.human_bones
    mapping = hb.human_bone_name_to_human_bone()
    # clear everything first (drops bad optional assignments like leftToes→tail_4)
    for human_bone in mapping.values():
        human_bone.node.bone_name = ""
    for enum_k, bname in HUMANOID_MAP.items():
        if enum_k in mapping and bname in arm_obj.data.bones:
            mapping[enum_k].node.bone_name = bname
    hb.initial_automatic_bone_assignment = False
    ok = hb.bones_are_correctly_assigned()
    print(f"humanoid forced map: correctly_assigned={ok}  "
          f"n={sum(1 for v in mapping.values() if v.node.bone_name)}")
    return ok

bpy.context.view_layer.objects.active = arm
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
force_humanoid(arm)

# lookAt bone mode
try:
    ext = get_armature_extension(arm.data)
    look = ext.vrm1.look_at
    look.type = "bone"
    if hasattr(look, "offset_from_head_bone"):
        look.offset_from_head_bone = (0.0, -0.06, 0.06)
    print(f"lookAt configured: {look.type}")
except Exception as e:
    print(f"lookAt config: {e}")

# ── ARKit expressions ─────────────────────────────────────────────────────────
try:
    bpy.ops.vrm.assign_vrm1_expressions_from_arkit(armature_object_name=arm.name)
    print("assigned VRM1 expressions from ARKit morphs")
except Exception as e:
    print(f"ARKit expression assign: {e}")
    # manual: bind each shape key name that matches an ARKit preset
    try:
        ext = get_armature_extension(arm.data)
        exprs = ext.vrm1.expressions
        sk_names = {k.name for k in ob.data.shape_keys.key_blocks} if ob.data.shape_keys else set()
        # preset list is on expressions.preset
        preset = exprs.preset
        for attr in dir(preset):
            if attr.startswith("_"): continue
            exp = getattr(preset, attr, None)
            if exp is None or not hasattr(exp, "morph_target_binds"):
                continue
            # common: attr name matches shape key (eyeBlinkLeft etc.)
            # convert snake to camel if needed
            candidates = [attr, attr[0].lower() + "".join(
                w.capitalize() if i else w for i, w in enumerate(attr.split("_"))
            ) if "_" in attr else attr]
            # also try direct ARKit names
            for c in list(candidates):
                if c in sk_names:
                    # add morph bind
                    bind = exp.morph_target_binds.add()
                    bind.node.mesh_object_name = ob.name
                    bind.index = c
                    bind.weight = 1.0
                    print(f"  bound expression {attr} → shape {c}")
                    break
    except Exception as e2:
        print(f"manual expression bind failed: {e2}")

# meta
try:
    ext = get_armature_extension(arm.data)
    meta = ext.vrm1.meta
    meta.vrm_name = "Clyffy"
    meta.version = "0.1.0"
    if hasattr(meta, "authors") and len(meta.authors) == 0:
        a = meta.authors.add(); a.value = "AngryVibes"
    elif hasattr(meta, "author"):
        meta.author = "AngryVibes"
    print("meta set: Clyffy")
except Exception as e:
    print(f"meta: {e}")

# ── spring bones (ears + tail) ────────────────────────────────────────────────
spring_report = {}
try:
    spring_report = author_spring_bones(arm)
    print(f"spring bones authored: {list(spring_report.get('chains', {}).keys())}")
    with open(os.path.join(os.path.dirname(OUT), "spring_bones_report.json"), "w") as f:
        json.dump(spring_report, f, indent=2)
except Exception as e:
    print(f"!! spring bones FAILED: {e}")
    import traceback; traceback.print_exc()

# re-force humanoid after spring authoring (structure search can re-taint candidates)
force_humanoid(arm)

# save prepared blend
prep = os.path.join(os.path.dirname(OUT), "clyffy_v2_vrm.blend")
bpy.ops.wm.save_as_mainfile(filepath=prep)
print(f"saved prepared blend: {prep}")

# ── export ────────────────────────────────────────────────────────────────────
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
ob.select_set(True)
# final force immediately before export
force_humanoid(arm)

result = {"ok": False}
try:
    ret = bpy.ops.export_scene.vrm(
        filepath=OUT,
        use_addon_preferences=False,
        export_invisibles=False,
        export_only_selections=False,
        export_all_influences=False,
        armature_object_name=arm.name,
        ignore_warning=True,
    )
    result["op"] = list(ret)
    result["ok"] = "FINISHED" in ret
    print(f"export_scene.vrm → {ret}")
except Exception as e:
    print(f"export_scene.vrm failed: {e}")
    import traceback; traceback.print_exc()
    # try the low-level path
    try:
        from VRM_Addon_for_Blender_release.exporter.export_scene import _export_vrm
        class FakeOp:
            export_invisibles = False
            export_only_selections = False
            export_all_influences = False
            export_lights = False
            export_gltf_animations = False
            export_try_sparse_sk = False
            enable_advanced_preferences = False
            errors = None
            ignore_warning = True
        ret = _export_vrm(Path(OUT), FakeOp(), bpy.context, armature_object_name=arm.name)
        result["op"] = list(ret) if ret else None
        result["ok"] = ret and "FINISHED" in ret
        print(f"_export_vrm → {ret}")
    except Exception as e2:
        print(f"_export_vrm failed: {e2}")
        import traceback; traceback.print_exc()

if os.path.isfile(OUT):
    result["size"] = os.path.getsize(OUT)
    print(f"VRM written: {OUT} ({result['size']} bytes)")
else:
    print(f"!! no file at {OUT}")

# report assigned humanoid bones + spring bones
report = {
    "export": result,
    "bones": [b.name for b in arm.data.bones],
    "humanoid": {},
    "spring_bones": spring_report,
}
try:
    ext = get_armature_extension(arm.data)
    hb = ext.vrm1.humanoid.human_bones
    mapping = hb.human_bone_name_to_human_bone()
    for k, human_bone in mapping.items():
        key = k.value if hasattr(k, "value") else str(k)
        bn = human_bone.node.bone_name
        if bn:
            report["humanoid"][key] = bn
    print("humanoid assignment:", json.dumps(report["humanoid"], indent=2))
    sb = ext.spring_bone1
    report["spring_bone_counts"] = {
        "springs": len(sb.springs),
        "colliders": len(sb.colliders),
        "collider_groups": len(sb.collider_groups),
        "joints": sum(len(s.joints) for s in sb.springs),
    }
    print("spring_bone_counts:", report["spring_bone_counts"])
except Exception as e:
    print(f"report humanoid/spring: {e}")

with open(os.path.join(os.path.dirname(OUT), "vrm_export_report.json"), "w") as f:
    json.dump(report, f, indent=2)
print("ok" if result.get("ok") or os.path.isfile(OUT) else "FAILED")
