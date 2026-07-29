#!/usr/bin/env python3
"""Acceptance gate for pack v0.1-talk-ready (STATUS G3).

    python3 tools/accept.py

Exit 0 = green. Prints FAIL lines and exit 1 on any hard failure.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

PINNED_VISEMES = [
    "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS", "nn", "RR",
    "aa", "E", "I", "O", "U",
]

fails: list[str] = []
warns: list[str] = []


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> None:
    fails.append(msg)
    print(f"FAIL  {msg}")


def warn(msg: str) -> None:
    warns.append(msg)
    print(f"WARN  {msg}")


def main() -> int:
    print("accept: Clyffy Avatar v0.1-talk-ready")
    env = os.environ.copy()
    env["PATH"] = f"/opt/bin:/usr/local/bin:{env.get('PATH', '')}"
    blender = env.get("BLENDER") or "blender"

    # ── Blender version ─────────────────────────────────────────────────────
    try:
        out = subprocess.check_output(
            [blender, "--version"], env=env, text=True, stderr=subprocess.STDOUT
        )
    except Exception as e:
        fail(f"blender not runnable ({e})")
        out = ""
    first = out.splitlines()[0] if out else ""
    if re.search(r"Blender (5\.[2-9]|[6-9])", first):
        ok(first)
    else:
        fail(f"need Blender >= 5.2, got: {first!r}")

    # ── Cycles CUDA GB10 ────────────────────────────────────────────────────
    probe = r"""
import bpy
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "CUDA"
prefs.get_devices()
names = [d.name for d in prefs.devices if d.type == "CUDA"]
print("CUDA_DEVICES=" + ",".join(names))
"""
    try:
        pout = subprocess.check_output(
            [blender, "--background", "--python-expr", probe],
            env=env, text=True, stderr=subprocess.STDOUT,
        )
        m = re.search(r"CUDA_DEVICES=(.*)", pout)
        devs = (m.group(1) if m else "").strip()
        if "GB10" in devs or "NVIDIA" in devs:
            ok(f"Cycles CUDA: {devs or '(named device)'}")
        else:
            fail(f"no CUDA GPU for Cycles: {devs!r}")
    except Exception as e:
        fail(f"Cycles probe failed: {e}")

    # ── Artifacts on disk ───────────────────────────────────────────────────
    body = ROOT / "mesh/canon/body/clyffy_v2_body.blend"
    vrm = ROOT / "mesh/canon/body/clyffy.vrm"
    schema = ROOT / "mesh/canon/body/control/control_surface.schema.json"
    pack = ROOT / "clyffy.pack.toml"
    for p, min_sz in ((body, 1_000_000), (vrm, 1_000_000), (schema, 200), (pack, 200)):
        if p.is_file() and p.stat().st_size >= min_sz:
            ok(f"{p.relative_to(ROOT)} ({p.stat().st_size} bytes)")
        else:
            fail(f"missing or tiny: {p.relative_to(ROOT)}")

    # ── VRM 1.0 conformance (tools/vrm_check.py) ────────────────────────────
    # Byte-size checks cannot see an off-spec export. A VRM that faces the wrong way
    # still weighs 75 MB, still has 22 humanoid bones — and still breaks every
    # real-time consumer. Exports before 2026-07-27 faced 55.1° off +Z and nothing
    # here caught it, so the conformance gate is part of accept from now on.
    if vrm.is_file():
        try:
            r = subprocess.run([sys.executable, str(ROOT / "tools/vrm_check.py"), str(vrm)],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                facing = next((ln.strip() for ln in r.stdout.splitlines() if "facing" in ln), "")
                ok(f"VRM 1.0 conformance ({facing.split('  ')[-1] if facing else 'green'})")
            else:
                for ln in r.stdout.splitlines():
                    if "FAIL" in ln:
                        fail(f"vrm_check: {ln.strip()}")
                if r.returncode != 0 and not any("vrm_check" in f for f in fails):
                    fail(f"vrm_check exited {r.returncode}")
        except Exception as e:
            fail(f"vrm_check could not run: {e}")

    # ── THE SSOT MUST ACTUALLY PARSE ────────────────────────────────────────
    # Found 2026-07-29: clyffy.pack.toml had NEVER been valid TOML. A multi-line inline
    # table at line 111, a basic string spanning four lines, a Python-style
    # `corner_up, corner_down = 0.009, 0.008`, and a duplicate `tongue` key. None of it
    # mattered to this gate, because every check below reads the pack as TEXT and does
    # substring matching — so the file the pack calls "SSOT, wins over tribal knowledge"
    # was unreadable by any tool that tried to consume it properly, and nothing noticed.
    # That is the same class of blind spot as the stale artifacts and the 22-degree jaw:
    # the gate tested what was cheap to test.
    try:
        import tomllib
    except ImportError:                       # py<3.11
        tomllib = None
    if tomllib is not None and pack.is_file():
        try:
            _pd = tomllib.loads(pack.read_text())
            ok(f"pack parses as TOML ({len(_pd)} top-level sections)")
        except Exception as e:
            fail(f"clyffy.pack.toml is NOT valid TOML: {e}")

    # ── POSED CONTAINMENT (tools/pose_check.py) ─────────────────────────────
    # lip_seal.py's containment gate only tests REST — the one pose where the lips are shut
    # and nothing can escape by construction. This runs the same question across every
    # viseme, every expression preset and a jawOpen sweep, against a CAPPED head so that
    # "inside" stays well defined once the mouth opens.
    if body.is_file():
        try:
            r = subprocess.run([blender, "-b", "--python", str(ROOT / "tools/pose_check.py"),
                                "--", str(body), "235.1"],
                               capture_output=True, text=True, timeout=3600, env=env)
            if "pose_check GREEN" in r.stdout:
                line = next((l.strip() for l in r.stdout.splitlines() if "pose_check GREEN" in l), "")
                ok(f"posed containment ({line.split('—')[-1].strip()})")
            else:
                bad = [l.strip() for l in r.stdout.splitlines() if "THROUGH THE SKIN" in l]
                fail(f"pose_check: {len(bad)} posed state(s) with geometry through the skin")
                for l in bad[:4]:
                    print(f"        {l}")
        except Exception as e:
            fail(f"pose_check could not run: {e}")

    # ── THE LIVE BUNDLE (tools/renderer_check.py) ───────────────────────────
    # Every check above stops at the edge of this pack, and the thing the operator actually
    # looks at is one repo further on. Found 2026-07-29: the renderer's BUILT bundle was
    # serving a contract two generations stale — jaw.max_deg 22.0 against the contract's
    # 10.0, and a DD viseme from before the M5 rewrite — while this gate read green.
    # Absent renderer repo is a WARN, not a FAIL: the pack must stay usable standalone.
    bundle = Path("/home/hades/Projects/clyffy/interfaces/clyffy-avatar/renderer/dist")
    if not bundle.is_dir():
        warn(f"live renderer bundle not present at {bundle} — cannot check it")
    else:
        try:
            r = subprocess.run([sys.executable, str(ROOT / "tools/renderer_check.py"), str(bundle)],
                               capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                ok("live renderer bundle is the current face and contract")
            else:
                for ln in r.stdout.splitlines():
                    if ln.startswith("FAIL"):
                        fail(f"renderer_check: {ln[4:].strip()}")
        except Exception as e:
            fail(f"renderer_check could not run: {e}")

    pack_txt = pack.read_text() if pack.is_file() else ""
    if 'version     = "0.1.0-talk-ready"' in pack_txt or '0.1.0-talk-ready' in pack_txt:
        ok("pack version 0.1.0-talk-ready")
    else:
        fail("pack not tagged 0.1.0-talk-ready")
    if 'tts_slot         = "voice.tts"' in pack_txt or "voice.tts" in pack_txt:
        ok("voice.tts slot named in pack")
    else:
        fail("pack [voice] missing voice.tts slot")

    # ── Body blend structure ────────────────────────────────────────────────
    body_probe = r"""
import bpy
ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
keys = [k.name for k in (ob.data.shape_keys.key_blocks if ob.data.shape_keys else [])]
bones = [b.name for b in arm.data.bones] if arm else []
print("N_KEYS=%d" % len(keys))
print("N_MOUTH=%d" % sum(1 for k in keys if k.startswith("mouth")))
print("HAS_JAW=%s" % ("jaw" in bones))
print("HAS_EYE_L=%s" % any(n in bones for n in ("eye_L", "leftEye")))
print("HAS_EYE_R=%s" % any(n in bones for n in ("eye_R", "rightEye")))
"""
    try:
        bout = subprocess.check_output(
            [blender, "--background", str(body), "--python-expr", body_probe],
            env=env, text=True, stderr=subprocess.STDOUT,
        )
        def grab(key: str) -> str:
            m = re.search(rf"{key}=(\S+)", bout)
            return m.group(1) if m else ""

        n_keys = int(grab("N_KEYS") or "0")
        n_mouth = int(grab("N_MOUTH") or "0")
        if n_keys >= 43:
            ok(f"shape keys: {n_keys}")
        else:
            fail(f"shape keys too few: {n_keys} (need >= 43)")
        if n_mouth >= 10:
            ok(f"mouth shape keys: {n_mouth}")
        else:
            fail(f"mouth shape keys too few: {n_mouth}")
        if grab("HAS_JAW") == "True":
            ok("jaw bone present")
        else:
            fail("jaw bone missing")
        if grab("HAS_EYE_L") == "True" and grab("HAS_EYE_R") == "True":
            ok("eye bones present")
        else:
            fail("eye bones missing")
    except Exception as e:
        fail(f"body blend probe failed: {e}")

    # ── Control surface + visemes ───────────────────────────────────────────
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from control_surface import VISEMES, SCHEMA  # type: ignore
        missing = [v for v in PINNED_VISEMES if v not in VISEMES]
        if missing:
            fail(f"VISEMES missing: {missing}")
        else:
            ok(f"VISEMES pinned set ({len(PINNED_VISEMES)})")
        for key in ("gaze_target", "viseme_weights", "expression_state", "rest_loop"):
            if key in SCHEMA.get("inputs", {}):
                ok(f"schema input {key}")
            else:
                fail(f"schema missing input {key}")
    except Exception as e:
        fail(f"import control_surface: {e}")

    if schema.is_file():
        try:
            data = json.loads(schema.read_text())
            vis = data.get("visemes") or {}
            if all(v in vis for v in PINNED_VISEMES):
                ok("schema json includes pinned visemes")
            else:
                warn("schema json stale — run: python3 tools/control_surface.py schema mesh/canon/body/control")
        except Exception as e:
            fail(f"schema json unreadable: {e}")

    # ── Soft artifacts (G4/G5) ──────────────────────────────────────────────
    # ⚠️ EXISTENCE IS NOT FRESHNESS (2026-07-28). These checks only asked whether the files
    # were THERE, so the gate went green on a herosheet four hours older than the body blend
    # it was supposed to depict — after a geometry change, and after present.py had silently
    # produced nothing on a chained invocation. A stale beauty render is exactly the artifact
    # someone reaches for to judge the character, so it is the last one that should be
    # allowed to lie. Every derived artifact is now compared against the mesh it descends
    # from, and a stale one WARNS by name.
    def fresher_than(art: Path, src: Path, label: str) -> None:
        if not art.is_file():
            warn(f"{label} missing")
            return
        if not src.is_file():
            ok(f"{label} present (source {src.name} missing, cannot date-check)")
            return
        age = src.stat().st_mtime - art.stat().st_mtime
        if age > 1.0:
            warn(f"{label} is STALE — {age/60:.0f} min older than {src.name}; re-render it")
        else:
            ok(f"{label} current")

    body_blend = ROOT / "mesh/canon/body/clyffy_v2_body.blend"
    heroes = list((ROOT / "mesh/canon/body/present").glob("hero_*.png"))
    if len(heroes) >= 4:
        ok(f"beauty heroes: {len(heroes)}")
        oldest = min(heroes, key=lambda p: p.stat().st_mtime)
        fresher_than(oldest, body_blend, f"beauty heroes (oldest {oldest.name})")
    else:
        warn(f"beauty heroes sparse ({len(heroes)}) — run present.py")

    fresher_than(ROOT / "mesh/canon/body/present/_herosheet.jpg", body_blend, "hero sheet")
    fresher_than(ROOT / "mesh/canon/body/control/_visemesheet.jpg", body_blend, "viseme sheet")

    frames = ROOT / "mesh/canon/body/drive/drive_frames.jsonl"
    if frames.is_file() and frames.stat().st_size > 10:
        ok("drive_frames.jsonl present")
    else:
        warn("drive_frames.jsonl missing — run avatar_drive.py (G5)")
    # The drive frames encode the CONTRACT (jaw max_deg, viseme mixes), not the mesh — so
    # they are dated against the PUBLISHED SCHEMA, not against control_surface.py. The source
    # file's mtime moves whenever it is touched at all: a revert that restored byte-identical
    # content still tripped this as stale. The schema is regenerated only when the contract
    # is actually re-emitted, which is the dependency that really matters.
    fresher_than(frames, ROOT / "mesh/canon/body/control/control_surface.schema.json",
                 "drive_frames vs the published contract")

    print()
    if warns:
        print(f"{len(warns)} warning(s)")
    if fails:
        print(f"{len(fails)} FAILURE(S) — accept RED")
        return 1
    print("accept GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
