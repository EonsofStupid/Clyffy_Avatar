#!/usr/bin/env python3
"""Would the LIVE RENDERER find every morph the contract can ask for?

    python3 tools/renderer_check.py [bundle_dir]

Exit 0 = every driven key resolves. Exit 1 otherwise.

WHY THIS EXISTS. `accept.py` and `vrm_check.py` both stop at the edge of this pack, and the
thing the operator actually looks at is one repo further on. Found 2026-07-29: the renderer's
BUILT bundle was serving a `control_surface.schema.json` two generations stale — `jaw.max_deg
= 22.0` against the contract's 10.0, and a `DD` viseme of `{jawOpen, mouthClose}` from before
the M5 table rewrite. Every gate in this pack was green the whole time. A stale bundle plus a
green board is worse than a red board.

It mirrors `renderer/src/main.js` EXACTLY — same drivenKeys construction (every non-`jawOpen`
key from VISEMES *and* PRESETS, because `clearMorphs` must reset both layers), then resolves
them against the morph-target names actually present in the delivered VRM. That is line 153
of main.js, computed here without needing WebGL: the 82 MB VRM will not finish parsing under
headless software rendering, so the browser cannot be the gate.

What it deliberately does NOT claim: that the face LOOKS right. That is the operator's VERIFY
gate in POAM A1, and no static check substitutes for it.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "/home/hades/Projects/clyffy/interfaces/clyffy-avatar/renderer/dist")

fails: list[str] = []


def ok(m): print(f"  OK  {m}")
def bad(m): fails.append(m); print(f"FAIL  {m}")


def gltf_json(path: Path) -> dict:
    """First JSON chunk of a binary glTF (a VRM is a .glb)."""
    with path.open("rb") as fh:
        magic, _ver, _len = struct.unpack("<III", fh.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a binary glTF")
        clen, ctype = struct.unpack("<II", fh.read(8))
        if ctype != 0x4E4F534A:
            raise ValueError("first chunk is not JSON")
        return json.loads(fh.read(clen).decode("utf-8"))


def morph_names(g: dict) -> set[str]:
    """Every morph-target name three.js would put in `morphTargetDictionary`."""
    names: set[str] = set()
    for mesh in g.get("meshes", []):
        # glTF puts target names either on the mesh or per-primitive `extras`
        for src in (mesh.get("extras") or {}, ):
            for n in src.get("targetNames", []) or []:
                names.add(n)
        for prim in mesh.get("primitives", []):
            for n in (prim.get("extras") or {}).get("targetNames", []) or []:
                names.add(n)
    return names


def main() -> int:
    print(f"renderer_check: {BUNDLE}")
    vrm = BUNDLE / "clyffy.vrm"
    schema = BUNDLE / "control_surface.schema.json"
    canon_vrm = ROOT / "mesh/canon/body/clyffy.vrm"
    canon_schema = ROOT / "mesh/canon/body/control/control_surface.schema.json"

    for p in (vrm, schema):
        if not p.is_file():
            bad(f"bundle missing {p.name}")
    if fails:
        return 1

    # ── the bundle must BE canon, not a copy that has drifted from it ────────
    for b, c, label in ((vrm, canon_vrm, "clyffy.vrm"),
                        (schema, canon_schema, "control_surface.schema.json")):
        if b.read_bytes() == c.read_bytes():
            ok(f"{label} byte-identical to canon ({b.stat().st_size} bytes)")
        else:
            bad(f"{label} DIFFERS from canon — bundle is stale "
                f"(bundle {b.stat().st_size} vs canon {c.stat().st_size} bytes); rebuild it")

    contract = json.loads(schema.read_text())
    visemes = contract.get("visemes") or {}
    presets = contract.get("presets") or {}
    env = contract.get("envelope") or {}
    jaw = (env.get("jaw") or {}).get("max_deg")

    # The value the LIVE surface will actually drive the jaw at.
    canon_jaw = ((json.loads(canon_schema.read_text()).get("envelope") or {})
                 .get("jaw") or {}).get("max_deg")
    if jaw == canon_jaw:
        ok(f"jaw max_deg served = {jaw}° (matches the contract)")
    else:
        bad(f"jaw max_deg served = {jaw}° but the contract says {canon_jaw}°")

    # ── drivenKeys, exactly as main.js:147-151 builds them ──────────────────
    driven: set[str] = set()
    for w in visemes.values():
        driven |= {k for k in w if k != "jawOpen"}
    for p in presets.values():
        if isinstance(p, dict):
            driven |= {k for k in p if k != "jawOpen"}

    names = morph_names(gltf_json(vrm))
    if not names:
        bad("no morph-target names found in the VRM — three.js would build an EMPTY "
            "morphTargetDictionary and every driven key would silently do nothing")
        return 1
    ok(f"morph targets in the VRM: {len(names)}")

    missing = sorted(driven - names)
    if missing:
        bad(f"{len(missing)} contract key(s) with no morph target: {missing}")
    else:
        ok(f"all {len(driven)} driven contract keys resolve to a morph target")

    # ── vertex colour must be in COLOR_0, the only slot a consumer reads ─────
    # tools/materials.py carries the muzzle and lip bands as a per-vertex tint. The VRM addon
    # exports a uniform-white dummy COLOR_0 and puts the real data in COLOR_1, which glTF and
    # three.js both ignore — so an unrepaired file renders the OLD white muzzle on the live
    # surface while Blender shows the new one. tools/vrm_color0_fix.py repairs it inside
    # vrm_export; this is the gate that proves the repair actually happened.
    # Reads the actual vertex DATA, not the accessor metadata: Blender writes no min/max for
    # colour accessors (verified — every COLOR_n here has min=None, max=None), so a check based
    # on metadata would call a uniform-white dummy "real data" and pass every time.
    # The decoder is imported from vrm_color0_fix rather than reimplemented, so the gate and the
    # repair can never disagree about what the file says.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import vrm_color0_fix as vcf

    _ver, g, binc, _others = vcf.read_glb(vrm)
    tinted = white = extra = 0
    for mesh in g.get("meshes", []):
        for prim in mesh.get("primitives", []):
            at = prim.get("attributes", {})
            if "COLOR_0" not in at:
                continue
            rows = vcf.accessor_rows(g, binc, at["COLOR_0"])
            if vcf.is_white_dummy(rows):
                white += 1
            else:
                tinted += 1
            extra += sum(1 for k in at if k.startswith("COLOR_") and k != "COLOR_0")
    # Is a tint EXPECTED? tools/materials.py writes materials_report.json next to the canon
    # body; its presence is the signal. Without it this is a pre-materials build and demanding
    # COLOR_0 would be a false alarm.
    mat_report = ROOT / "mesh/canon/body/materials_report.json"
    expected = mat_report.is_file()
    if expected:
        try:
            expected = bool(json.loads(mat_report.read_text()).get("requires_color0"))
        except Exception as e:
            bad(f"materials_report.json unreadable ({e})")
            expected = False

    if extra:
        bad(f"{extra} redundant COLOR_n stream(s) beyond COLOR_0 — a consumer reads COLOR_0 and "
            f"would miss the tint; run tools/vrm_color0_fix.py")
    elif tinted:
        ok(f"COLOR_0 carries real vertex colour on {tinted} primitive(s) "
           f"({white} constant-material primitive(s) correctly uniform)")
    elif expected:
        bad("materials_report.json says this pack carries a muzzle tint, but no primitive has "
            "varying COLOR_0 — the tint is a NO-OP in this VRM; run tools/vrm_color0_fix.py")
    else:
        print("  --   no vertex colour in this VRM, and no materials_report.json — this build "
              "predates tools/materials.py, so the muzzle carries no tint (not a failure yet)")

    # The extension morphs are the reason this check was worth writing — a bundle that
    # predates them loads fine and simply never moves the tongue.
    ext = sorted({"tongueUp", "tongueBack", "tongueCurl", "lipTuckLower"} & driven)
    if ext:
        ok(f"tongue/lip extension morphs driven by the served contract: {ext}")
    else:
        bad("the served contract drives NO tongue articulation — it predates 2026-07-29")

    print()
    if fails:
        print(f"{len(fails)} FAILURE(S) — renderer_check RED")
        return 1
    print("renderer_check GREEN — the live bundle is the current face and contract")
    print("  (visual confirmation is still the operator's gate — POAM A1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
