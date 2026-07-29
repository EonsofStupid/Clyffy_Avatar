"""VRM 1.0 conformance gate — orientation, humanoid, expressions, springs, morphs.

    python3 tools/vrm_check.py [path/to/clyffy.vrm]

Pure-python GLB/JSON parse. No Blender, no three.js — this is the thing that has to be
true before ANY renderer adapter (three-vrm, Unreal, Unity) can be trusted.

WHY THIS EXISTS
  Exports before 2026-07-27 faced +55.1° off +Z (the Blender authoring yaw, FWD 235.1°,
  was never baked out). Nothing caught it, because every check looked at bone COUNTS.
  Downstream it read as "the avatar renders in 3/4 view" and — the expensive one — a
  consumer rotating the jaw about world X got a pitch/yaw MIX, so the muzzle barely
  opened while the teeth swung sideways out through the lip.

⚠️ FACING IS MEASURED FROM THE EYE BONES, NOT FROM leftUpperLeg/rightUpperLeg.
  This rig's L/R bone names are MIRRORED: body_rig.py comments "-1 left (neg lat)" but
  with lat = [-fwd[1], fwd[0], 0], +lat IS the character's left, so the bones named L sit
  on his right. A forward vector built as cross(leftLeg - rightLeg, up) therefore comes
  out BACKWARDS and will cheerfully report "spec-compliant" while the renderer shows the
  back of the head. The eyes are on the front of the face regardless of naming.
  (The mirroring itself is a separate open defect — see STATUS.md.)
"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

PATH = sys.argv[1] if len(sys.argv) > 1 else "mesh/canon/body/clyffy.vrm"

REQUIRED_HUMAN_BONES = [
    "hips", "spine", "chest", "neck", "head",
    "leftUpperArm", "leftLowerArm", "leftHand",
    "rightUpperArm", "rightLowerArm", "rightHand",
    "leftUpperLeg", "leftLowerLeg", "leftFoot",
    "rightUpperLeg", "rightLowerLeg", "rightFoot",
]
FACING_TOL_DEG = 5.0


def load_gltf_json(path: str) -> dict:
    data = open(path, "rb").read()
    magic, _, _ = struct.unpack("<III", data[:12])
    if data[:4] != b"glTF":
        raise SystemExit(f"not a GLB: {path}")
    off, js = 12, None
    while off < len(data):
        clen, _ = struct.unpack("<II", data[off:off + 8])
        if data[off + 4:off + 8] == b"JSON":
            js = json.loads(data[off + 8:off + 8 + clen])
        off += 8 + clen
    if js is None:
        raise SystemExit("no JSON chunk")
    return js


def world_matrices(nodes: list) -> callable:
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    def trs(n):
        if "matrix" in n:
            return np.array(n["matrix"]).reshape(4, 4).T
        t = n.get("translation", [0, 0, 0])
        x, y, z, w = n.get("rotation", [0, 0, 0, 1])
        s = n.get("scale", [1, 1, 1])
        rot = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ])
        m = np.eye(4)
        m[:3, :3] = rot @ np.diag(s)
        m[:3, 3] = t
        return m

    def world(i):
        chain, cur = [], i
        while cur is not None:
            chain.append(cur)
            cur = parent.get(cur)
        m = np.eye(4)
        for c in reversed(chain):
            m = m @ trs(nodes[c])
        return m

    return world


def main() -> int:
    g = load_gltf_json(PATH)
    ext = g.get("extensions", {})
    vrm = ext.get("VRMC_vrm")
    fails, warns = [], []
    print(f"vrm_check: {PATH}")

    if not vrm:
        print("  FAIL  no VRMC_vrm extension")
        return 1
    spec = vrm.get("specVersion")
    print(f"  {'OK  ' if spec == '1.0' else 'FAIL'}  specVersion {spec}")
    if spec != "1.0":
        fails.append("specVersion")

    hb = vrm.get("humanoid", {}).get("humanBones", {})
    missing = [b for b in REQUIRED_HUMAN_BONES if b not in hb]
    print(f"  {'OK  ' if not missing else 'FAIL'}  humanoid bones {len(hb)}"
          f"{'' if not missing else '  missing: ' + ', '.join(missing)}")
    if missing:
        fails.append("humanoid")

    # ── facing, from the EYES (see module docstring) ────────────────────────
    world = world_matrices(g["nodes"])
    pos = lambda n: world(hb[n]["node"])[:3, 3]  # noqa: E731
    if "head" in hb and "leftEye" in hb and "rightEye" in hb:
        fwd = (pos("leftEye") + pos("rightEye")) / 2 - pos("head")
        fwd[1] = 0.0
        n = np.linalg.norm(fwd)
        if n < 1e-6:
            warns.append("eyes coincide with head; cannot measure facing")
            print("  WARN  eyes coincide with head — facing not measurable")
        else:
            fwd /= n
            yaw = math.degrees(math.atan2(fwd[0], fwd[2]))
            ok = abs(yaw) <= FACING_TOL_DEG
            print(f"  {'OK  ' if ok else 'FAIL'}  facing {yaw:+.2f}° off +Z "
                  f"(head->eyes [{fwd[0]:+.3f} 0 {fwd[2]:+.3f}], tol ±{FACING_TOL_DEG:g}°)")
            if not ok:
                fails.append("facing")
    else:
        warns.append("no eye bones; facing unverified")
        print("  WARN  no eye bones — facing UNVERIFIED")

    exprs = vrm.get("expressions", {}).get("preset", {})
    print(f"  {'OK  ' if exprs else 'WARN'}  expression presets {len(exprs)}")
    if not exprs:
        warns.append("expressions")

    springs = ext.get("VRMC_springBone", {}).get("springs", [])
    print(f"  {'OK  ' if springs else 'WARN'}  spring bones {len(springs)}")
    if not springs:
        warns.append("springs")

    prim = g["meshes"][0]["primitives"][0]
    targets = prim.get("targets", []) or []
    names = g["meshes"][0].get("extras", {}).get("targetNames", []) or []
    ok = len(targets) > 0 and len(names) == len(targets)
    print(f"  {'OK  ' if ok else 'FAIL'}  morph targets {len(targets)} (named {len(names)})")
    if not ok:
        fails.append("morphs")

    # ── THE CONTRACT MUST BE DELIVERABLE ─────────────────────────────────────
    # The renderer resolves viseme/preset keys against the VRM's morphTargetDictionary BY
    # NAME. A key the delivered VRM does not carry is a SILENT no-op: the table looks
    # authored, the face just never moves. control_surface.py gained this check for the
    # Blender path (a viseme naming a missing shape key did nothing); the delivered artifact
    # had no equivalent, which is the half that actually ships.
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import importlib.util
        # NOT `spec` — that name already holds the VRM specVersion above
        _mspec = importlib.util.spec_from_file_location(
            "_cs", Path(__file__).resolve().parent / "control_surface.py")
        cs = importlib.util.module_from_spec(_mspec)
        _mspec.loader.exec_module(cs)
        want = set()
        for tbl in (cs.VISEMES, cs.PRESETS):
            for mix in tbl.values():
                if isinstance(mix, dict):
                    want |= {k for k in mix if k != "jawOpen"}   # jawOpen is the BONE
        ghosts = sorted(want - set(names))
        if ghosts:
            print(f"  FAIL  {len(ghosts)} contract key(s) have NO morph target in this VRM: "
                  f"{', '.join(ghosts)}")
            fails.append("contract-morphs")
        else:
            print(f"  OK    all {len(want)} contract morph keys exist in the VRM")
    except Exception as e:            # never let the extra check mask the conformance result
        print(f"  WARN  could not cross-check the contract against the VRM ({e})")
        warns.append("contract-morphs")

    print()
    if fails:
        print(f"vrm_check FAILED: {', '.join(fails)}")
        return 1
    print("vrm_check GREEN" + (f"  ({len(warns)} warning(s))" if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
