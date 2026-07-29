"""Author VRM 1.0 spring bones (VRMC_springBone) on a Clyffy armature.

    Called from tools/vrm_export.py after humanoid rename, or standalone:

    blender -b --python tools/spring_bones.py -- <vrm_prepared.blend> <out.blend>

Chains expected (from body_rig.py custom prop `spring_chains` or defaults):
  ear_L → [ear_L, ear_L_2, ear_L_3]
  ear_R → [ear_R, ear_R_2, ear_R_3]
  tail  → [tail,  tail_2,  tail_3, tail_4]

Design (methodical, not freestyle):
  * Multi-segment chains already exist on the armature (body_rig builds them).
  * Each chain becomes ONE spring with one joint per bone, root→tip.
  * Parameters ease toward the tip (softer, larger hit radius) — standard
    spring-bone practice so the free end leads and the root stays planted.
  * Head sphere colliders keep ears out of the skull; a hip collider keeps
    the tail from folding into the pelvis.
  * Gravity is world-down in Blender (+Z up → gravity_dir (0,0,-1)).

Requires VRM Add-on for Blender (saturday06).
"""
from __future__ import annotations

import json
import math
from typing import Iterable, Sequence

# Joint params: (stiffness, drag_force, gravity_power, hit_radius)
# Tuned for a stylised cow at ~1 unit tall. Stiffness drops, radius grows tipward.
EAR_PROFILE = [
    # root (attachment)          mid                         tip
    (1.8, 0.55, 0.05, 0.012),
    (1.1, 0.45, 0.10, 0.014),
    (0.55, 0.35, 0.15, 0.016),
]
TAIL_PROFILE = [
    (1.4, 0.50, 0.20, 0.018),
    (0.90, 0.42, 0.35, 0.022),
    (0.50, 0.35, 0.50, 0.026),
    (0.25, 0.28, 0.65, 0.030),
]
GRAVITY_DIR = (0.0, 0.0, -1.0)  # Blender world: −Z is down


def _import_vrm():
    import addon_utils, importlib
    addon_utils.enable("VRM_Addon_for_Blender-release", default_set=True, persistent=True)
    ext = importlib.import_module("VRM_Addon_for_Blender-release.editor.extension")
    return ext.get_armature_extension


def _resolve_chains(arm, bones) -> dict[str, list[str]]:
    """Prefer armature custom prop written by body_rig; else discover by name."""
    raw = arm.get("spring_chains")
    if raw:
        try:
            chains = json.loads(raw) if isinstance(raw, str) else dict(raw)
            # keep only bones that still exist (rename may have happened)
            out = {}
            for k, names in chains.items():
                present = [n for n in names if n in bones]
                if present:
                    out[k] = present
            if out:
                return out
        except Exception as e:
            print(f"  spring_chains prop unreadable ({e}); discovering")

    # Discovery fallback: ear_L, ear_L_2, … / tail, tail_2, …
    out: dict[str, list[str]] = {}
    for prefix in ("ear_L", "ear_R", "tail"):
        names = [prefix] if prefix in bones else []
        i = 2
        while f"{prefix}_{i}" in bones:
            names.append(f"{prefix}_{i}")
            i += 1
        if names:
            out[prefix] = names
    return out


def _profile_for(chain_key: str, n: int):
    base = EAR_PROFILE if chain_key.startswith("ear") else TAIL_PROFILE
    if n == len(base):
        return base
    # resample: pick evenly from the base profile
    if n <= 0:
        return []
    out = []
    for i in range(n):
        t = 0.0 if n == 1 else i / (n - 1)
        j = min(int(round(t * (len(base) - 1))), len(base) - 1)
        out.append(base[j])
    return out


def _clear_springs(spring_bone) -> None:
    """Idempotent: wipe previous springs/colliders so re-runs don't stack."""
    while len(spring_bone.springs):
        spring_bone.springs.remove(0)
    while len(spring_bone.collider_groups):
        spring_bone.collider_groups.remove(0)
    # colliders own bpy empties — remove objects then entries
    import bpy
    for col in list(spring_bone.colliders):
        obj = getattr(col, "bpy_object", None)
        if obj is not None:
            for ch in list(obj.children):
                bpy.data.objects.remove(ch, do_unlink=True)
            bpy.data.objects.remove(obj, do_unlink=True)
    while len(spring_bone.colliders):
        spring_bone.colliders.remove(0)


def _add_sphere_collider(context, arm, spring_bone, bone_name: str,
                        radius: float, offset=(0.0, 0.0, 0.0),
                        name: str = ""):
    col = spring_bone.add_collider(context, arm)
    col.shape.sphere.radius = float(radius)
    col.shape.sphere.offset = tuple(float(x) for x in offset)
    col.node.bone_name = bone_name
    # reset_bpy_object parents the empty to the bone
    try:
        col.reset_bpy_object(context, arm)
    except Exception as e:
        print(f"  collider reset_bpy_object({bone_name}): {e}")
    if name and col.bpy_object is not None:
        col.bpy_object.name = name
    return col


def author_spring_bones(arm, *, chains: dict[str, list[str]] | None = None) -> dict:
    """Author springs + colliders on `arm`. Returns a report dict."""
    import bpy
    get_armature_extension = _import_vrm()
    context = bpy.context
    bones = {b.name: b for b in arm.data.bones}
    if chains is None:
        chains = _resolve_chains(arm, bones)
    if not chains:
        raise RuntimeError("no spring chains found on armature")

    ext = get_armature_extension(arm.data)
    sb = ext.spring_bone1
    _clear_springs(sb)

    report = {"chains": {}, "colliders": [], "springs": []}

    # ── colliders ────────────────────────────────────────────────────────────
    # Head sphere: keeps ear springs from clipping through the skull.
    # Offset slightly forward of the head bone so it sits in the cranium bulk.
    head_bone = "head" if "head" in bones else ("skull" if "skull" in bones else None)
    hips_bone = "hips" if "hips" in bones else None
    H = 1.0
    if head_bone:
        hb = bones[head_bone]
        H = max(hb.length * 5.0, 0.5)  # rough body-scale proxy
    colliders = {}
    if head_bone:
        # two head colliders: cranium + muzzle-ish so ears don't swing through face
        colliders["head"] = _add_sphere_collider(
            context, arm, sb, head_bone,
            radius=0.07 * (H if H < 2 else 1.0),
            offset=(0.0, -0.02, 0.02),
            name="col_head",
        )
        colliders["muzzle"] = _add_sphere_collider(
            context, arm, sb, head_bone,
            radius=0.05,
            offset=(0.0, -0.08, -0.02),
            name="col_muzzle",
        )
        report["colliders"].append({"name": "head", "bone": head_bone, "r": 0.07})
        report["colliders"].append({"name": "muzzle", "bone": head_bone, "r": 0.05})
    if hips_bone:
        colliders["hips"] = _add_sphere_collider(
            context, arm, sb, hips_bone,
            radius=0.09,
            offset=(0.0, 0.0, 0.04),
            name="col_hips",
        )
        report["colliders"].append({"name": "hips", "bone": hips_bone, "r": 0.09})

    # collider groups (referenced by springs)
    def group(name: str, cols: Iterable):
        g = sb.add_collider_group()
        g.vrm_name = name
        for c in cols:
            ref = g.add_collider()
            ref.collider_uuid = c.uuid
        return g

    g_head = group("head", [c for k, c in colliders.items() if k in ("head", "muzzle")]) if colliders else None
    g_body = group("body", [c for k, c in colliders.items() if k == "hips"]) if "hips" in colliders else None

    # ── springs ──────────────────────────────────────────────────────────────
    for chain_key, names in chains.items():
        present = [n for n in names if n in bones]
        if len(present) < 1:
            print(f"  !! chain {chain_key}: no bones present, skip")
            continue
        # VRM springs need ≥1 joint; a useful chain wants ≥2. With one bone we
        # still author a single-joint spring (tip-only) rather than drop it.
        spring = sb.add_spring()
        spring.vrm_name = chain_key
        # center = parent of the chain root so head motion doesn't double-count
        root = bones[present[0]]
        if root.parent:
            spring.center.bone_name = root.parent.name

        profile = _profile_for(chain_key, len(present))
        for bone_name, (stiff, drag, grav, radius) in zip(present, profile):
            joint = spring.add_joint()
            joint.node.bone_name = bone_name
            joint.stiffness = float(stiff)
            joint.drag_force = float(drag)
            joint.gravity_power = float(grav)
            joint.gravity_dir = GRAVITY_DIR
            joint.hit_radius = float(radius)

        # attach collider groups: ears → head, tail → body (+ head so it doesn't
        # whip through the torso into the face on big swings)
        if chain_key.startswith("ear") and g_head is not None:
            ref = spring.add_collider_group()
            ref.collider_group_uuid = g_head.uuid
        if chain_key == "tail":
            if g_body is not None:
                ref = spring.add_collider_group()
                ref.collider_group_uuid = g_body.uuid
            if g_head is not None:
                ref = spring.add_collider_group()
                ref.collider_group_uuid = g_head.uuid

        report["springs"].append({
            "name": chain_key,
            "joints": present,
            "center": spring.center.bone_name,
            "profile": [list(p) for p in profile],
        })
        report["chains"][chain_key] = present
        print(f"  spring '{chain_key}': joints={present} center={spring.center.bone_name}")

    # enable runtime preview when the file is opened interactively
    try:
        sb.enable_animation = True
    except Exception:
        pass

    print(f"spring bones: {len(sb.springs)} springs, {len(sb.colliders)} colliders, "
          f"{len(sb.collider_groups)} groups")
    return report


# ── CLI entry (blender -b --python tools/spring_bones.py -- in out) ───────────
def _cli() -> None:
    import sys, os
    import bpy
    if "--" not in sys.argv:
        return
    argv = sys.argv[sys.argv.index("--") + 1:]
    if not argv:
        return
    SRC = os.path.abspath(argv[0])
    OUT = os.path.abspath(argv[1]) if len(argv) > 1 else SRC
    bpy.ops.wm.open_mainfile(filepath=SRC)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rep = author_spring_bones(arm)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    out_json = os.path.join(os.path.dirname(OUT), "spring_bones_report.json")
    with open(out_json, "w") as f:
        json.dump(rep, f, indent=2)
    print(f"saved {OUT}")
    print(f"report {out_json}")
    print("ok")


if __name__ == "__main__":
    _cli()
# Blender exec: __name__ is not "__main__"; detect by argv.
import sys as _sys
if "--" in _sys.argv and _sys.argv[0].endswith("spring_bones.py"):
    _cli()
