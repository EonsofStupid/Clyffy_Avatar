#!/usr/bin/env python3
"""Point COLOR_0 at the real vertex colours. Pure Python — no Blender.

    python3 tools/vrm_color0_fix.py <file.vrm> [--dry-run]

Exit 0 if the file is correct (already, or after fixing). Exit 1 if it could not be made correct.

═══ THE DEFECT THIS EXISTS FOR ══════════════════════════════════════════════════════════════

`tools/materials.py` authors the muzzle/lip colour as a per-vertex attribute, and the VRM export
DOES carry it — but not where any consumer looks. Measured on the exported file:

    COLOR_0   unsigned byte,  1 unique row     -> (255,255,255,255) for every vertex
    COLOR_1   unsigned short, 1635 unique rows -> the actual tint

glTF and three.js read COLOR_0 as *the* vertex colour. So the delivered VRM carries a white
no-op in the slot everyone reads and the real data in a slot nobody does: Blender renders the
pink muzzle, and the live web renderer shows the old white one. Every gate in this pack would
stay green while the surface the operator actually looks at is unchanged — the same shape as the
stale-bundle bug that shipped for a day (see tools/renderer_check.py).

The VRM addon calls the glTF exporter with `export_vertex_color="MATERIAL"`
(VRM_Addon_for_Blender-release/exporter/vrm1_exporter.py:2873) and emits a dummy white COLOR_0
regardless. Ruled out by experiment, so the cause is not on our side and there is no authoring
workaround:
  - removing the ShaderNodeAttribute nodes (skin_wet / skin_flesh) from the material  -> still two
  - authoring the attribute as BYTE_COLOR on the CORNER domain instead of FLOAT_COLOR -> still two
    (and it quantised 1635 distinct values down to 348, so it is worse as well as ineffective)

So this repoints COLOR_0 at the accessor that has the data. It only ever rewrites the JSON
chunk's attribute mapping — no vertex data is recomputed, moved or reinterpreted, and the
accessor it promotes is already `normalized: true`, which is what COLOR_0 requires.

DELIBERATELY CONSERVATIVE: it refuses to touch a COLOR_0 that is not a uniform-white dummy. If a
future exporter starts putting real data in COLOR_0, this becomes a no-op instead of a corruption.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
COMP = {5120: "i1", 5121: "u1", 5122: "i2", 5123: "u2", 5125: "u4", 5126: "f4"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path: Path):
    raw = path.read_bytes()
    magic, ver, total = struct.unpack_from("<III", raw, 0)
    if magic != GLB_MAGIC:
        raise ValueError(f"{path.name} is not a binary glTF")
    if total != len(raw):
        print(f"  note: header length {total} vs file {len(raw)} — using the file")
    chunks, off = [], 12
    while off + 8 <= len(raw):
        clen, ctype = struct.unpack_from("<II", raw, off)
        data = raw[off + 8: off + 8 + clen]
        chunks.append((ctype, data))
        off += 8 + clen + (-clen % 4)
    js = next(d for t, d in chunks if t == CHUNK_JSON)
    binc = next((d for t, d in chunks if t == CHUNK_BIN), b"")
    others = [(t, d) for t, d in chunks if t not in (CHUNK_JSON, CHUNK_BIN)]
    return ver, json.loads(js.decode("utf-8")), binc, others


def write_glb(path: Path, ver: int, g: dict, binc: bytes, others):
    js = json.dumps(g, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)                     # JSON pads with SPACES per spec
    parts = [(CHUNK_JSON, js)]
    if binc:
        parts.append((CHUNK_BIN, binc + b"\0" * (-len(binc) % 4)))   # BIN pads with ZEROS
    parts += others
    total = 12 + sum(8 + len(d) for _, d in parts)
    out = bytearray(struct.pack("<III", GLB_MAGIC, ver, total))
    for t, d in parts:
        out += struct.pack("<II", len(d), t) + d
    path.write_bytes(bytes(out))
    return total


def accessor_rows(g: dict, binc: bytes, ai: int):
    """Read one accessor as an (count, ncomp) array. Interleaved views are not decoded."""
    ac = g["accessors"][ai]
    if "bufferView" not in ac:
        return None
    bv = g["bufferViews"][ac["bufferView"]]
    nc = NCOMP[ac["type"]]
    stride = bv.get("byteStride")
    itemsize = np.dtype(COMP[ac["componentType"]]).itemsize
    if stride and stride != nc * itemsize:
        return None                                  # interleaved; do not guess
    off = bv.get("byteOffset", 0) + ac.get("byteOffset", 0)
    dt = np.dtype(COMP[ac["componentType"]]).newbyteorder("<")
    n = ac["count"] * nc
    if off + n * itemsize > len(binc):
        return None
    return np.frombuffer(binc, dtype=dt, count=n, offset=off).reshape(ac["count"], nc)


def is_white_dummy(rows) -> bool:
    """A COLOR stream that is one single fully-opaque white value for every vertex."""
    if rows is None or len(rows) == 0:
        return False
    if len(np.unique(rows, axis=0)) != 1:
        return False
    mx = float(np.iinfo(rows.dtype).max) if rows.dtype.kind in "ui" else 1.0
    return bool(np.all(np.isclose(rows[0].astype(float) / mx, 1.0, atol=1e-6)))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    dry = "--dry-run" in sys.argv
    if not path.is_file():
        print(f"MISSING {path}")
        return 1

    ver, g, binc, others = read_glb(path)
    print(f"vrm_color0_fix: {path.name} ({path.stat().st_size} bytes, glTF v{ver})")

    fixed = skipped = already = constant = 0
    had_data = []
    for mi, mesh in enumerate(g.get("meshes", [])):
        for pi, prim in enumerate(mesh.get("primitives", [])):
            at = prim.get("attributes", {})
            if "COLOR_0" not in at:
                continue
            tag = f"mesh{mi}/prim{pi}"
            c0 = accessor_rows(g, binc, at["COLOR_0"])
            if not is_white_dummy(c0):
                uniq = "?" if c0 is None else len(np.unique(c0, axis=0))
                print(f"  {tag}: COLOR_0 already carries data ({uniq} unique) — left alone")
                already += 1
                continue
            spare = sorted(k for k in at if k.startswith("COLOR_") and k != "COLOR_0")
            promoted = None
            for k in spare:
                rows = accessor_rows(g, binc, at[k])
                if rows is not None and len(np.unique(rows, axis=0)) > 1:
                    promoted = k
                    break
            if promoted is None:
                # NOT a defect. These are the constant-colour materials (teeth / tongue /
                # cavity / hoof): they carry no per-vertex tint at all, so a uniform-white
                # COLOR_0 multiplies by exactly 1.0 and changes nothing. Treating this as a
                # failure was my own bug — the first run reported "VERIFY FAILED" on three
                # primitives that were already correct.
                mat = prim.get("material")
                mname = g["materials"][mat].get("name", "?") if mat is not None else "no material"
                print(f"  {tag}: no per-vertex tint anywhere ({mname}) — uniform white "
                      f"COLOR_0 is a correct no-op")
                # Strip the redundant duplicate streams so the file does not carry dead weight.
                for k in spare:
                    if not dry:
                        del at[k]
                if spare:
                    print(f"    dropped redundant {', '.join(spare)}")
                constant += 1
                continue
            acc = at[promoted]
            norm = g["accessors"][acc].get("normalized", False)
            n_uniq = len(np.unique(accessor_rows(g, binc, acc), axis=0))
            print(f"  {tag}: COLOR_0 white dummy -> promoting {promoted} "
                  f"(accessor {acc}, {n_uniq} unique rows, normalized={norm})")
            if not norm and g["accessors"][acc]["componentType"] != 5126:
                # COLOR_0 as an integer type MUST be normalized, or a consumer reads 65535
                # as the number 65535 rather than as 1.0.
                print(f"    marking accessor {acc} normalized (required for integer COLOR_0)")
                if not dry:
                    g["accessors"][acc]["normalized"] = True
            if not dry:
                at["COLOR_0"] = acc
                del at[promoted]
                for k in spare:
                    if k != promoted and k in at:
                        del at[k]
            had_data.append((mi, pi))
            fixed += 1

    print(f"\n  promoted {fixed} | already correct {already} | constant-colour (correctly white) {constant} | undecodable {skipped}")
    if dry:
        print("  --dry-run: nothing written")
        return 1 if skipped else 0
    if fixed:
        total = write_glb(path, ver, g, binc, others)
        print(f"  rewrote {path.name} ({total} bytes)")
        # Re-read and prove it, rather than asserting it worked.
        _, g2, bin2, _ = read_glb(path)
        bad = 0
        for mi, pi in had_data:
            at = g2["meshes"][mi]["primitives"][pi].get("attributes", {})
            rows = accessor_rows(g2, bin2, at.get("COLOR_0", -1)) if "COLOR_0" in at else None
            if rows is None or is_white_dummy(rows):
                print(f"    ! mesh{mi}/prim{pi} still white in COLOR_0")
                bad += 1
            extra = sorted(k for k in at if k.startswith("COLOR_") and k != "COLOR_0")
            if extra:
                print(f"    ! mesh{mi}/prim{pi} leftover {extra}")
                bad += 1
        if bad:
            print(f"  VERIFY FAILED — {bad} problem(s) among the {len(had_data)} promoted")
            return 1
        print(f"  verified by re-reading: all {len(had_data)} promoted primitive(s) carry "
              f"real data in COLOR_0, with no duplicate streams")
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
