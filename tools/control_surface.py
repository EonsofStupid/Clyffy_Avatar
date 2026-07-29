"""Control surface — apply companion-app state to the body-rigged avatar.

    # Apply one state frame and render a still
    blender -b --python tools/control_surface.py -- apply \
        <body.blend> <out_dir> <fwd_deg> <state.json> [tag]

    # Emit the alpha contract schema + example states
    python3 tools/control_surface.py schema
    python3 tools/control_surface.py examples <out_dir>

Contract (clyffy.pack.toml [rig.control_surface]):
  gaze_target       world-ish look point, or {yaw, pitch} degrees
  viseme_weights    ARKit mouth/jaw shape key → 0..1  (jawOpen is BONE, not a key)
  expression_state  named expression preset or raw ARKit weights
  goggle_state      on-face | pushed-up | resting-on-desk | in-hand  (alpha: logged only)
  rest_loop         true → zero everything to rest

jawOpen is driven via the jaw BONE (never a shape key — double-transform).
eyeLook* are driven via eye_L / eye_R bones (lookAt bone mode).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

# ── Pure-python side (schema / examples — no bpy) ─────────────────────────────

SCHEMA = {
    "version": 1,
    "description": "Companion-app → Clyffy avatar control surface (alpha)",
    "inputs": {
        "gaze_target": {
            "oneOf": [
                {"type": "object", "props": {"yaw_deg": "float", "pitch_deg": "float"},
                 "note": "degrees; +yaw = character's left, +pitch = up"},
                {"type": "object", "props": {"x": "float", "y": "float", "z": "float"},
                 "note": "world-space look-at point (local==world on canonical mesh)"},
            ],
            "default": {"yaw_deg": 0.0, "pitch_deg": 0.0},
        },
        "viseme_weights": {
            "type": "object",
            "keys": "ARKit shape key names (mouth*/jaw* except jawOpen) → 0..1",
            "special": {
                "jawOpen": "0..1 → jaw BONE rotation (max 22 deg), NOT a shape key",
            },
        },
        "expression_state": {
            "oneOf": [
                {"type": "string", "enum": [
                    "rest", "happy", "sad", "angry", "surprised", "thinking", "talk"
                ]},
                {"type": "object", "keys": "ARKit shape key names → 0..1"},
            ],
        },
        "goggle_state": {
            "type": "string",
            "enum": ["on-face", "pushed-up", "resting-on-desk", "in-hand"],
            "alpha": "logged only — goggle mesh prop not yet authored",
        },
        "rest_loop": {
            "type": "boolean",
            "note": "true zeros all drives (rest-state law)",
        },
    },
}

# Named expression presets → ARKit weights (alpha, hand-tuned for the cow face)
PRESETS: dict[str, dict[str, float]] = {
    "rest": {},
    "happy": {
        "mouthSmileLeft": 0.85, "mouthSmileRight": 0.85,
        "cheekSquintLeft": 0.35, "cheekSquintRight": 0.35,
        "eyeSquintLeft": 0.25, "eyeSquintRight": 0.25,
    },
    "sad": {
        "mouthFrownLeft": 0.7, "mouthFrownRight": 0.7,
        "browInnerUp": 0.55, "browDownLeft": 0.2, "browDownRight": 0.2,
        "eyeBlinkLeft": 0.15, "eyeBlinkRight": 0.15,
    },
    "angry": {
        "browDownLeft": 0.9, "browDownRight": 0.9,
        "mouthFrownLeft": 0.4, "mouthFrownRight": 0.4,
        "noseSneerLeft": 0.45, "noseSneerRight": 0.45,
        "eyeSquintLeft": 0.4, "eyeSquintRight": 0.4,
    },
    "surprised": {
        "eyeWideLeft": 0.9, "eyeWideRight": 0.9,
        "browOuterUpLeft": 0.7, "browOuterUpRight": 0.7, "browInnerUp": 0.5,
        "jawOpen": 0.45, "mouthFunnel": 0.25,
    },
    "thinking": {
        "browInnerUp": 0.4, "browDownLeft": 0.35,
        "mouthPressLeft": 0.3, "mouthPressRight": 0.3,
        "eyeSquintLeft": 0.2,
    },
    "talk": {
        # baseline mid-syllable; real talk uses viseme_weights over time
        "jawOpen": 0.35, "mouthClose": 0.1,
    },
}

# Viseme labels (alpha) → ARKit mix. Shared live + episode — do not fork.
#
# ── M5 REWRITE, 2026-07-28 ───────────────────────────────────────────────────
# The old table drove 10 of the 32 mouth morphs the mesh carries, and leaned on shapes that
# barely move. MEASURED per-morph range on this mesh (max vertex displacement, %H) — weights
# below are scaled against it, so a "0.5" on a strong shape and a "0.5" on a weak one are not
# silently different amounts of face:
#
#   mouthSmile*    3.55    mouthStretch*  2.38    mouthFunnel    2.25    mouthPucker   1.95
#   mouthUpperUp*  1.58    jawForward     1.43    mouthRoll*     1.39    mouthShrugUp  1.28
#   mouthLowerDown 1.27    mouthPress*    1.27    mouthDimple*   1.08    mouthShrugLo  1.02
#   mouthClose     0.45  <-- the WEAKEST shape on the mesh
#
# `mouthClose` was carrying PP, DD, SS and nn at up to 0.4 while moving 0.45%H — which is why
# those four read almost identically. The strong shapes (mouthStretch*, 2.38%H) were unused
# entirely.
#
# TWO THINGS DRIVE THIS TABLE:
#
# 1. PHONETICS. Several entries were simply wrong for their sound. FF is labiodental — the
#    lower lip tucks under the upper teeth (mouthRollLower), it does not funnel; funnel is
#    an /w/-/oo/ rounding. PP is bilabial closure (mouthPress*), not a pucker. CH/SH pushes
#    the jaw forward (jawForward), which the table never touched.
#
# 2. RECOVERING THE GAPE LOST TO THE 13° CAP. The jaw is capped by the shirt collar (see
#    ENVELOPE["jaw"]), so apparent openness has to come from the LIPS. mouthUpperUp* (1.58%H)
#    lifts the upper lip and mouthLowerDown* (1.27%H) drops the lower: together ~2.85%H of
#    extra aperture against the jaw's 3.5%H at 13°, nearly doubling how open `aa` reads —
#    and none of it costs collar clearance, because no jaw rotation is involved.
VISEMES: dict[str, dict[str, float]] = {
    "sil": {},
    # bilabial closure — lips PRESSED, rolled slightly in. Not a pucker.
    # ⚠️ CAUGHT BY tools/pose_check.py, and it was NOT the shape I first blamed. Pressing the
    # lips at 0.7 takes the upper lip BEHIND the upper incisors and puts one tooth vertex
    # outside the head. Isolated by component: press alone fails, the rolls alone do not, and
    # `mouthClose` actually rescues it — so halving the roll first (my first guess) changed
    # nothing. Swept: 0.55 and 0.60 are clean, 0.65 fails. 0.60 with a 0.05 margin.
    "PP":  {"jawOpen": 0.0, "mouthPressLeft": 0.6, "mouthPressRight": 0.6,
            "mouthRollUpper": 0.15, "mouthRollLower": 0.25, "mouthClose": 0.5},
    # ⚠️ THE CONSONANTS BELOW NOW DRIVE TONGUE ARTICULATION (2026-07-29).
    # tools/viseme_distinct.py measured every pinned pair for the first time and found them
    # collapsing onto silence — DD/kk 0.17%H, CH/RR 0.23%H, SS/nn 0.25%H, sil/FF 0.25%H.
    # Every one of those is a tongue-position or lip-to-teeth distinction, and the rig had
    # nothing to express it with: one tongue morph (`tongueOut`, forward only) and a
    # symmetric lip roll. The four extension morphs (tongueUp / tongueBack / tongueCurl /
    # lipTuckLower) exist to give these phonemes somewhere to actually go. Re-measure with
    # the same tool after ANY edit here — that is the whole point of having it.

    # labiodental — lower lip tucks UNDER the upper teeth, upper lip lifts clear.
    # mouthRollLower alone rolls BOTH lips symmetrically and measured 0.25%H from silence.
    "FF":  {"jawOpen": 0.08, "lipTuckLower": 0.85, "mouthRollLower": 0.25,
            "mouthUpperUpLeft": 0.3, "mouthUpperUpRight": 0.3,
            "mouthPressLeft": 0.2, "mouthPressRight": 0.2},
    # interdental — tongue tip between the teeth, lower lip drops away from it
    "TH":  {"jawOpen": 0.22, "tongueOut": 0.3, "tongueUp": 0.35, "mouthShrugLower": 0.2,
            "mouthLowerDownLeft": 0.3, "mouthLowerDownRight": 0.3},
    # alveolar stop — TIP TO THE RIDGE. This is what separates it from kk.
    "DD":  {"jawOpen": 0.3, "tongueUp": 0.9,
            "mouthStretchLeft": 0.15, "mouthStretchRight": 0.15,
            "mouthLowerDownLeft": 0.2, "mouthLowerDownRight": 0.2},
    # velar — BACK of the tongue humps to the soft palate. The tightest collapsed pair
    # (0.17%H vs DD) was tip-vs-back, and nothing was using the back at all.
    "kk":  {"jawOpen": 0.38, "tongueBack": 0.9,
            "mouthStretchLeft": 0.2, "mouthStretchRight": 0.2,
            "mouthUpperUpLeft": 0.15, "mouthUpperUpRight": 0.15},
    # postalveolar — rounded AND protruded; jawForward is what makes "sh" read.
    # The blade raise is what separates it from RR, which is otherwise the same lip shape.
    "CH":  {"jawOpen": 0.22, "tongueCurl": 0.85, "mouthFunnel": 0.45,
            "mouthPucker": 0.25, "jawForward": 0.4},
    # sibilant — teeth nearly together, lips SPREAD WIDE, tongue tip high and grooved.
    # The spread was driven at only 0.5 and SS travelled 0.28%H from silence — nearly a
    # closed mouth, which is why it kept colliding with nn. /s/ is one of the most readable
    # shapes on a real face; the wide corners ARE the cue, so drive them like it.
    "SS":  {"jawOpen": 0.08, "tongueUp": 0.7,
            "mouthStretchLeft": 0.9, "mouthStretchRight": 0.9,
            "mouthDimpleLeft": 0.45, "mouthDimpleRight": 0.45,
            "mouthSmileLeft": 0.25, "mouthSmileRight": 0.25,
            "mouthPressLeft": 0.15, "mouthPressRight": 0.15},
    # nasal — the mouth is SHUT and the tongue seals at the ridge; air goes through the nose.
    # This sat at jawOpen 0.18 with the same tongueUp strength as SS, so the first articulation
    # pass separated both from DD/kk but left SS/nn on top of each other at 0.25%H. A nasal is
    # a CLOSED mouth: the distinction from a sibilant is aperture, not tongue.
    # ⚠️ TWO WRONG ANSWERS BEFORE THIS ONE, both caught by viseme_distinct.py:
    #   jawOpen 0.18 + tongueUp 0.8 + press  -> SS/nn 0.25%H (same tongue morph as SS)
    #   jawOpen 0.04 + close 0.75 + press    -> PP/nn 0.19%H — that is a BILABIAL seal, i.e.
    #                                            /m/, not /n/. Only the TONGUE seals for /n/.
    # The lips stay relaxed and slightly parted, which is what separates it from PP (pressed
    # shut) and from SS (spread wide). No press, no roll.
    "nn":  {"jawOpen": 0.14, "tongueUp": 0.9, "mouthClose": 0.25,
            "mouthShrugLower": 0.15},
    # rhotic — bunched/retroflex: blade up AND back, which is what distinguishes it from CH
    "RR":  {"jawOpen": 0.28, "tongueCurl": 0.5, "tongueBack": 0.45,
            "mouthFunnel": 0.3, "mouthPucker": 0.2, "jawForward": 0.25},
    # THE open vowel. Lip lift + lip drop carry the aperture the capped jaw cannot — and
    # since the lip rim was unfrozen (2026-07-28) they genuinely do: full-strength
    # mouthUpperUp* + mouthLowerDown* now open the mouth 1.18%H on their own, against 0.042%H
    # while the rim was welded. Driven near full here, because the jaw gave up 3 degrees to
    # buy chin depth and this is what pays it back.
    "aa":  {"jawOpen": 0.85,
            "mouthUpperUpLeft": 0.9, "mouthUpperUpRight": 0.9,
            "mouthLowerDownLeft": 0.95, "mouthLowerDownRight": 0.95,
            "mouthStretchLeft": 0.2, "mouthStretchRight": 0.2},
    "E":   {"jawOpen": 0.42, "mouthStretchLeft": 0.45, "mouthStretchRight": 0.45,
            "mouthSmileLeft": 0.3, "mouthSmileRight": 0.3,
            "mouthDimpleLeft": 0.2, "mouthDimpleRight": 0.2,
            "mouthLowerDownLeft": 0.5, "mouthLowerDownRight": 0.5},
    "I":   {"jawOpen": 0.24, "mouthStretchLeft": 0.6, "mouthStretchRight": 0.6,
            "mouthSmileLeft": 0.4, "mouthSmileRight": 0.4,
            "mouthDimpleLeft": 0.3, "mouthDimpleRight": 0.3},
    "O":   {"jawOpen": 0.55, "mouthFunnel": 0.7, "mouthPucker": 0.25,
            "mouthShrugUpper": 0.25, "mouthShrugLower": 0.25, "jawForward": 0.15},
    "U":   {"jawOpen": 0.3, "mouthPucker": 0.8, "mouthFunnel": 0.35,
            "mouthShrugUpper": 0.3, "mouthShrugLower": 0.3, "jawForward": 0.2},
}

# ── ENVELOPE PIPELINE (drive contract v1) ────────────────────────────────────
# Audio → viseme derivation, defined ONCE and published in the schema.
#
# WHY THIS IS HERE AND NOT INLINE IN avatar_drive.py:
# The live surface derives viseme_weights LOCALLY from the audio it is playing
# (operator decision 2026-07-27: state from clyffyd, visemes local), while the
# offline path derives them in avatar_drive.py. Two implementations of the same
# mapping WILL drift, and the failure is silent — the offline mp4 and the live
# window would lipsync differently on identical audio. Publishing the constants
# in control_surface.schema.json makes every renderer read one definition instead
# of copying literals. Any renderer adapter (three-vrm now, Unreal later) reads
# this block; none of them re-derive it.
ENVELOPE: dict = {
    "sample_rate": 16000,          # analysis rate; audio is downmixed to mono at this
    "fps": 24,                     # frame rate of the emitted control-surface timeline
    "rms_gamma": 0.6,              # env = rms_normalised ** gamma  (perceptual lift)
    "smooth_kernel": [0.15, 0.7, 0.15],   # 3-tap convolution over the env track
    "rest_hold_s": 0.4,            # rest-state law: hold rest for this long at the tail
    # Energy → viseme class. Ordered; FIRST bucket whose `max` exceeds env wins.
    # Alpha lipsync is envelope-only; a phoneme/ASR track replaces `classes`
    # without touching viseme_weights or the schema (drive contract v1).
    "classes": [
        {"max": 0.08, "viseme": "sil"},
        {"max": 0.25, "viseme": "nn"},
        {"max": 0.45, "viseme": "E"},
        {"max": 0.65, "viseme": "O"},
        {"max": 1.01, "viseme": "aa"},
    ],
    # coarticulation — mouths do not SNAP between shapes. Without this the face steps
    # discretely from viseme to viseme and reads as robotic no matter how good the shapes are.
    # Attack/release are asymmetric on purpose: lips reach a target faster than they leave it.
    "coartic": {
        "attack_s": 0.045,     # time to reach a new viseme's target
        "release_s": 0.075,    # time to fall away from the previous one
        "carry": 0.28,         # how much of the neighbouring viseme bleeds in
    },
    # jawOpen is ALWAYS the jaw BONE, never a shape key (contract v1).
    "jaw": {
        # ⚠️ 22.0 -> 13.0, measured 2026-07-28. This ONE value was driving the open mouth
        # ~60% past what the character's anatomy can absorb, and it is what made a wide
        # vowel read as a rectangular hole punched in the muzzle.
        #
        # The shirt is texture on the same continuous surface, so the collar is a hard
        # ceiling: it sits 9.00%H below the lip line (sampled from the base-colour image),
        # and that is the WHOLE budget for chin plus neck. With a chin of depth D and a jaw
        # drop d, at full open the visible chin is D and the chin underside is D+d, which
        # must stay above the collar — so d < 9.0 - D. The chin ships at ~4.5%H, which is
        # already the optimum of min(D, 9-D), giving d <= 4.5%H ~ 13 deg. Growing the chin
        # does NOT buy gape; it trades against it one-for-one (see tools/chin_mass.py).
        #
        # An independent angle ladder (work/m2_ladder) agreed by eye: 12-15 deg reads as a
        # mouth, 18 starts eating the chin, 22 is a rectangle.
        #
        # Raising this again without moving the collar down will reintroduce the defect.
        "max_deg": 10.0,
        "scale_base": 0.35,        # jaw = viseme_jawOpen * (scale_base + scale_env*env)
        "scale_env": 0.65,
        "env_floor": 0.15,         # jaw = max(jaw, env_floor*env) so silence stays shut
    },
    # non-jaw viseme weights scale with envelope so quiet speech under-articulates
    "weight_scale": {"base": 0.4, "env": 0.6},
}


# ── GRAPHEME → VISEME (drive contract v1, text-driven lipsync) ───────────────
# WHY: envelope-only derivation uses FIVE energy buckets (sil/nn/E/O/aa). Measured on the
# shipped drive, 10 of the 15 pinned VISEMES NEVER FIRED — no lip closures (PP/FF), no
# sibilants (SS/CH), no rounding (U), no wide (I). The mouth could only open and close, which
# is exactly what "robotic" looks like. The rig was never the problem.
#
# When the line is SCRIPTED (episodes, demos) or the text is known before TTS speaks it
# (clyffy generates the words, then voices them), the text is a far better source than
# energy. Contract v1 anticipated this: "Phoneme/ASR later plugs the same viseme_weights
# field — no schema fork." This is that, without pulling in a phoniser.
#
# This is grapheme-level, NOT a real G2P — English spelling lies (though/through/tough).
# It is deliberately a good-enough approximation for a stylised cow muzzle at 24fps, and it
# is published here so the live renderer can use the identical table when it is given text.
# Digraphs are matched FIRST (longest-match), or "sh" would read as s + h.
GRAPHEME_VISEMES: dict = {
    "digraphs": {
        "ch": "CH", "sh": "CH", "th": "TH", "ph": "FF", "wh": "U",
        "ng": "nn", "ck": "kk", "qu": "kk", "oo": "U", "ee": "I",
        "ou": "O", "ow": "O", "ai": "E", "ay": "E", "oa": "O", "ea": "I",
    },
    "single": {
        "p": "PP", "b": "PP", "m": "PP",
        "f": "FF", "v": "FF",
        "t": "DD", "d": "DD", "l": "DD",
        "k": "kk", "g": "kk", "c": "kk", "x": "kk", "q": "kk",
        "j": "CH",
        "s": "SS", "z": "SS",
        "n": "nn",
        "r": "RR",
        "a": "aa", "e": "E", "i": "I", "o": "O", "u": "U", "y": "I",
        "w": "U", "h": "aa",
    },
    # Relative duration weights. Vowels carry the syllable; stops are brief. Used to lay
    # visemes out inside a voiced run — without this every letter gets equal time and the
    # mouth machine-guns through consonants.
    "durations": {
        "aa": 2.0, "E": 1.8, "I": 1.6, "O": 1.9, "U": 1.7,
        "PP": 0.7, "FF": 0.9, "TH": 0.9, "DD": 0.7, "kk": 0.7,
        "CH": 1.0, "SS": 1.1, "nn": 0.9, "RR": 1.0, "sil": 1.0,
    },
}


def text_to_visemes(text: str) -> list[str]:
    """Grapheme sequence → viseme tokens. Word boundaries emit a brief `sil`.

    Longest-match on digraphs first; unknown characters are skipped rather than guessed.
    """
    di = GRAPHEME_VISEMES["digraphs"]
    si = GRAPHEME_VISEMES["single"]
    out: list[str] = []
    for word in "".join(c.lower() if (c.isalpha() or c.isspace()) else " " for c in text).split():
        i = 0
        prev = None
        while i < len(word):
            v = None
            if i + 1 < len(word) and word[i:i + 2] in di:
                v = di[word[i:i + 2]]
                i += 2
            elif word[i] in si:
                v = si[word[i]]
                i += 1
            else:
                i += 1
                continue
            # collapse doubled shapes ("ll", "tt") — the mouth holds, it does not re-articulate
            if v != prev:
                out.append(v)
            prev = v
        out.append("sil")   # inter-word closure
    return out


def write_schema(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "control_surface.schema.json")
    with open(path, "w") as f:
        json.dump({"schema": SCHEMA, "presets": PRESETS, "visemes": VISEMES,
                   "envelope": ENVELOPE, "grapheme_visemes": GRAPHEME_VISEMES}, f, indent=2)
    print(f"wrote {path}")


def write_examples(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    examples = {
        "rest": {"rest_loop": True, "goggle_state": "on-face"},
        "happy_look_left": {
            "expression_state": "happy",
            "gaze_target": {"yaw_deg": -18.0, "pitch_deg": 4.0},
            "goggle_state": "on-face",
        },
        "surprised": {
            "expression_state": "surprised",
            "gaze_target": {"yaw_deg": 0.0, "pitch_deg": 8.0},
            "goggle_state": "pushed-up",
        },
        "talk_aa": {
            "viseme_weights": VISEMES["aa"],
            "gaze_target": {"yaw_deg": 5.0, "pitch_deg": -2.0},
            "goggle_state": "on-face",
        },
        "angry_thinking": {
            "expression_state": "thinking",
            "viseme_weights": {"mouthPressLeft": 0.2, "mouthPressRight": 0.2},
            "gaze_target": {"yaw_deg": 12.0, "pitch_deg": -6.0},
            "goggle_state": "down" if False else "on-face",
        },
    }
    for name, state in examples.items():
        path = os.path.join(out_dir, f"state_{name}.json")
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        print(f"wrote {path}")


# ── Blender side ──────────────────────────────────────────────────────────────

def _bpy_apply(rig_path: str, out_dir: str, fwd_deg: float, state: dict, tag: str) -> None:
    import bpy
    import numpy as np
    from mathutils import Vector, Matrix, Euler

    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=rig_path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    ob = max(meshes, key=lambda o: len(o.data.vertices))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    me = ob.data
    N = len(me.vertices)
    co = np.empty((N, 3)); me.vertices.foreach_get("co", co.ravel())
    H = float(co[:, 2].max() - co[:, 2].min())
    a = math.radians(fwd_deg)
    fwd = np.array([math.sin(a), -math.cos(a), 0.0])
    lat = np.array([-fwd[1], fwd[0], 0.0])
    up = np.array([0.0, 0.0, 1.0])

    # bone name resolution (body_rig names OR VRM names)
    def bone(*names):
        for n in names:
            if n in arm.pose.bones:
                return arm.pose.bones[n]
        return None

    jaw_b = bone("jaw")
    eye_L = bone("eye_L", "leftEye")
    eye_R = bone("eye_R", "rightEye")
    kb = me.shape_keys.key_blocks if me.shape_keys else None

    # A viseme or preset naming a shape key the mesh does not carry does NOTHING, silently —
    # the entry looks authored, the face just never moves. Every name in the tables is
    # checked against the mesh once, up front, rather than failing invisibly per frame.
    if kb:
        have = {k.name for k in kb}
        want: set[str] = set()
        for tbl in (VISEMES, PRESETS):
            for mix in tbl.values():
                want |= {n for n in mix if n != "jawOpen"}
        ghosts = sorted(want - have)
        if ghosts:
            print(f"!! {len(ghosts)} drive target(s) are NOT shape keys on this mesh and will "
                  f"do nothing: {', '.join(ghosts)}")
        else:
            print(f"drive targets OK: all {len(want)} morph names in VISEMES/PRESETS exist "
                  f"on the mesh")

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

    def set_shape(name: str, value: float) -> None:
        if not kb or name not in kb or name == "Basis":
            return
        kb[name].value = float(max(0.0, min(1.0, value)))

    def set_jaw_open(amount: float) -> None:
        """amount 0..1 → jaw bone rotation about the lateral axis, capped by the CONTRACT.

        This read 22.0 as a literal — inside the very file that publishes
        ENVELOPE["jaw"]["max_deg"], and after that value had been taken to 13 and then 10 for
        measured reasons (the shirt collar). Anything driving the rig through this helper was
        opening the jaw 2.2x past the contract it had just been handed.
        """
        if jaw_b is None:
            print("!! no jaw bone"); return
        amount = float(max(0.0, min(1.0, amount)))
        hinge = Vector(jaw_b.bone.head_local)
        lat_v = Vector(lat)
        ang = math.radians(ENVELOPE["jaw"]["max_deg"]) * amount
        R = (Matrix.Translation(hinge)
             @ Matrix.Rotation(ang, 4, lat_v)
             @ Matrix.Translation(-hinge))
        jaw_b.matrix = R @ jaw_b.bone.matrix_local

    def set_gaze(yaw_deg: float, pitch_deg: float) -> None:
        """Rotate both eye bones. yaw/pitch in degrees, character-local."""
        # eye bones aim along their local Y or the bone axis; use euler XYZ
        for eb in (eye_L, eye_R):
            if eb is None:
                continue
            eb.rotation_mode = "XYZ"
            # map: pitch about lateral, yaw about up — approximate for alpha
            eb.rotation_euler = (
                math.radians(pitch_deg),
                0.0,
                math.radians(yaw_deg),
            )

    def apply_weights(weights: dict[str, float]) -> None:
        jaw_amt = 0.0
        for name, val in weights.items():
            if name == "jawOpen":
                jaw_amt = max(jaw_amt, float(val))
            else:
                set_shape(name, float(val))
        if jaw_amt > 0:
            set_jaw_open(jaw_amt)

    # ── interpret state ───────────────────────────────────────────────────────
    zero_all()
    report: dict[str, Any] = {"tag": tag, "goggle_state": state.get("goggle_state", "on-face")}

    if state.get("rest_loop"):
        report["mode"] = "rest_loop"
    else:
        # expression first, then visemes layer on top (max)
        weights: dict[str, float] = {}
        expr = state.get("expression_state")
        if isinstance(expr, str):
            weights.update(PRESETS.get(expr, {}))
            report["expression"] = expr
        elif isinstance(expr, dict):
            weights.update({k: float(v) for k, v in expr.items()})
            report["expression"] = "custom"
        vis = state.get("viseme_weights") or {}
        if isinstance(vis, str):
            vis = VISEMES.get(vis, {})
        for k, v in vis.items():
            weights[k] = max(weights.get(k, 0.0), float(v))
        apply_weights(weights)
        report["weights"] = {k: round(v, 3) for k, v in weights.items() if v > 0.01}

        gaze = state.get("gaze_target") or {}
        if "yaw_deg" in gaze or "pitch_deg" in gaze:
            yaw = float(gaze.get("yaw_deg", 0.0))
            pitch = float(gaze.get("pitch_deg", 0.0))
            set_gaze(yaw, pitch)
            report["gaze"] = {"yaw_deg": yaw, "pitch_deg": pitch}
        elif all(k in gaze for k in ("x", "y", "z")):
            # convert look-at point to yaw/pitch relative to head
            target = np.array([gaze["x"], gaze["y"], gaze["z"]], float)
            # eye mid
            el = np.array(ob.get("eye_L_center", (0, 0, 0.35)))
            er = np.array(ob.get("eye_R_center", (0, 0, 0.35)))
            mid = 0.5 * (el + er)
            d = target - mid
            # project
            df, dl, du = float(d @ fwd), float(d @ lat), float(d @ up)
            yaw = math.degrees(math.atan2(dl, max(df, 1e-6)))
            pitch = math.degrees(math.atan2(du, max(math.hypot(df, dl), 1e-6)))
            set_gaze(yaw, pitch)
            report["gaze"] = {"yaw_deg": round(yaw, 2), "pitch_deg": round(pitch, 2), "from_point": True}

    if state.get("goggle_state"):
        # alpha: no goggle mesh yet — record only
        report["goggle_state"] = state["goggle_state"]
        print(f"goggle_state={state['goggle_state']} (alpha: prop not authored)")

    bpy.context.view_layer.update()

    # ── render ────────────────────────────────────────────────────────────────
    sc = bpy.context.scene
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
    # waist-up framing
    cd.ortho_scale = H * 0.72
    hc = co[co[:, 2] > 0.208].mean(0)
    face_z = float(hc[2] - H * 0.05)
    Rr = H * 4.5
    cam.location = (hc[0] + math.sin(a) * Rr, hc[1] - math.cos(a) * Rr, face_z)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = os.path.join(out_dir, f"ctrl_{tag}.png")
    bpy.ops.render.render(write_still=True)

    # save posed blend for inspection
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, f"ctrl_{tag}.blend"))
    with open(os.path.join(out_dir, f"ctrl_{tag}.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"applied → ctrl_{tag}.png  {report}")
    print("ok")


def main(argv: list[str]) -> None:
    if not argv or argv[0] in ("schema", "help", "-h", "--help"):
        write_schema(argv[1] if len(argv) > 1 else "mesh/canon/body/control")
        return
    if argv[0] == "examples":
        out = argv[1] if len(argv) > 1 else "mesh/canon/body/control"
        write_schema(out)
        write_examples(out)
        return
    if argv[0] == "apply":
        # apply <body.blend> <out_dir> <fwd_deg> <state.json> [tag]
        _, rig, out, fwd, state_path = argv[:5]
        tag = argv[5] if len(argv) > 5 else Path(state_path).stem.replace("state_", "")
        with open(state_path) as f:
            state = json.load(f)
        _bpy_apply(os.path.abspath(rig), os.path.abspath(out), float(fwd), state, tag)
        return
    raise SystemExit(f"unknown command: {argv[0]}  (schema|examples|apply)")


if __name__ == "__main__":
    # blender: sys.argv has -- separator; pure python: no blender wrapper
    if "--" in sys.argv:
        main(sys.argv[sys.argv.index("--") + 1:])
    else:
        main(sys.argv[1:])
