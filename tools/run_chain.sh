#!/usr/bin/env bash
# Full mesh chain from the canonical blend through the VRM, with the head_proportion
# reshape inserted at position 1.5.
#
#     tools/run_chain.sh <out_root> [--snout K] [--muzzle K] [--neck K]
#
# ORDER IS LOAD-BEARING, not cosmetic (clyffy.pack.toml [pipeline] and BUILD_LOG):
#   * head_proportion must run BEFORE shape_author. All 47 shape keys are DELTAS authored
#     against the geometry underneath them; reshaping afterwards leaves every delta scaled
#     wrong for its new neighbourhood. Same reason chin_mass sits at position 3.
#   * densify must run AFTER eye_open --cut. Run before, it hands the eye boundary a degree-4
#     pinch vertex, eye_open refuses to cut, and it SILENTLY SKIPS writing eye_*_center /
#     eye_*_radius — which then kills face_atlas four stages later with a bare KeyError.
#   * eye_open reads clyffy_v2_chin.blend, not clyffy_v2_open.blend.
#   * materials must follow mesh_patch, which changes face indices.
#   * anything that changes VERTEX COUNT invalidates body_rig, which transfers face weights
#     BY INDEX and asserts equal counts.
#
# vrm_export SEGFAULTS ON EXIT after the VRM is written (Blender teardown, "Found 4 unreleased
# ID's"). The file is complete and passes vrm_check — check for the OUTPUT, not the exit status.
set -euo pipefail
cd "$(dirname "$0")/.."

BL="${BLENDER:-/opt/blender-5.2.0/blender-wrapper.sh}"
FWD=235.1
SRC="mesh/canon/clyffy_v2_canon.blend"

OUT="${1:?usage: run_chain.sh <out_root> [--snout K] [--muzzle K] [--neck K]}"; shift
SNOUT=1.00; MUZZLE=1.00; NECK=0.55
while [ $# -gt 0 ]; do
    case "$1" in
        --snout)  SNOUT="$2"; shift 2 ;;
        --muzzle) MUZZLE="$2"; shift 2 ;;
        --neck)   NECK="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done
mkdir -p "$OUT/shapes" "$OUT/body"
LOG="$OUT/chain.log"; : > "$LOG"

# Every stage's full output goes to the log UNFILTERED — warnings and asserts included. The
# console gets a trimmed view. Nothing is suppressed; grep the log if a stage looks wrong.
#
# EXIT STATUS IS NOT A GATE HERE. `blender -b --python` returns 0 even when the script raised:
# the first run of this chain sailed past `AssertionError: expected 2 eye rims, got 1` and ran
# eleven more stages against files that were never written, burying the one real failure under
# fifty lines of "No such file or directory". Each stage therefore declares the artefact it must
# produce, and the chain stops the moment that artefact is missing or stale.
run() {
    local name="$1" want="$2"; shift 2
    local before after
    before=$(wc -l < "$LOG")
    [ -f "$want" ] && before_ts=$(stat -c%Y "$want") || before_ts=0
    echo "── $name" | tee -a "$LOG"
    "$@" >>"$LOG" 2>&1 || true
    after=$(wc -l < "$LOG")

    # only THIS stage's output, never a stale line from an earlier one
    sed -n "$((before+1)),${after}p" "$LOG" \
        | grep -aiE "wrote|verts [0-9]+ ->|warn|error|assert|Traceback" | tail -4 || true

    if [ ! -f "$want" ] || [ "$(stat -c%Y "$want")" -le "$before_ts" ]; then
        echo "   ✗ $name did not produce $want" >&2
        echo "   last 25 lines of its output:" >&2
        sed -n "$((before+1)),${after}p" "$LOG" | tail -25 >&2
        exit 1
    fi
}

run head_proportion "$OUT/clyffy_v2_prop.blend" "$BL" -b --python tools/head_proportion.py -- \
    "$SRC" "$OUT" "$FWD" --neck "$NECK" --snout "$SNOUT" --muzzle "$MUZZLE"
run mouth_open "$OUT/clyffy_v2_open.blend"   "$BL" -b --python tools/mouth_open.py   -- "$OUT/clyffy_v2_prop.blend"  "$OUT" "$FWD"
run chin_mass "$OUT/clyffy_v2_chin.blend"    "$BL" -b --python tools/chin_mass.py    -- "$OUT/clyffy_v2_open.blend"  "$OUT" "$FWD"
run eye_open "$OUT/clyffy_v2_eyes.blend"     "$BL" -b --python tools/eye_open.py     -- "$OUT/clyffy_v2_chin.blend"  "$OUT" "$FWD" --cut
run densify "$OUT/clyffy_v2_eyes.blend"      "$BL" -b --python tools/densify.py      -- "$OUT/clyffy_v2_eyes.blend"  "$OUT" "$FWD"
run mouth_parts "$OUT/clyffy_v2_parts.blend"  "$BL" -b --python tools/mouth_parts.py  -- "$OUT/clyffy_v2_eyes.blend"  "$OUT" "$FWD"
run lip_seal "$OUT/clyffy_v2_parts.blend"     "$BL" -b --python tools/lip_seal.py     -- "$OUT/clyffy_v2_parts.blend" \
                                                             "$OUT/clyffy_v2_parts.blend" "$FWD" 0.85 0.0025
run face_atlas "$OUT/clyffy_v2_atlas.blend"   "$BL" -b --python tools/face_atlas.py   -- "$OUT/clyffy_v2_parts.blend" "$OUT" "$FWD"
run shape_author "$OUT/shapes/clyffy_v2_shapes.blend" "$BL" -b --python tools/shape_author.py -- "$OUT/clyffy_v2_atlas.blend" "$OUT/shapes" "$FWD"
run jaw_rig "$OUT/clyffy_v2_rig.blend"      "$BL" -b --python tools/jaw_rig.py      -- "$OUT/clyffy_v2_parts.blend" "$OUT" "$FWD"
run body_rig "$OUT/body/clyffy_v2_body.blend"     "$BL" -b --python tools/body_rig.py     -- "$OUT/shapes/clyffy_v2_shapes.blend" \
                                                             "$OUT/clyffy_v2_rig.blend" "$OUT/body" "$FWD"
run hoof "$OUT/body/clyffy_v2_body.blend"         "$BL" -b --python tools/hoof.py         -- "$OUT/body/clyffy_v2_body.blend" "$OUT/body" "$FWD"
run mesh_patch "$OUT/body/clyffy_v2_body.blend"   "$BL" -b --python tools/mesh_patch.py   -- "$OUT/body/clyffy_v2_body.blend" "$OUT/body" "$FWD"
run materials "$OUT/body/clyffy_v2_body.blend"    "$BL" -b --python tools/materials.py    -- "$OUT/body/clyffy_v2_body.blend" "$OUT/body" "$FWD"
run vrm_export "$OUT/body/clyffy.vrm"   "$BL" -b --python tools/vrm_export.py   -- "$OUT/body/clyffy_v2_body.blend" "$OUT/body/clyffy.vrm"

echo
if [ -f "$OUT/body/clyffy.vrm" ]; then
    echo "CHAIN OK  ->  $OUT/body/clyffy.vrm  ($(stat -c%s "$OUT/body/clyffy.vrm") bytes)"
else
    echo "CHAIN INCOMPLETE — no VRM written; see $LOG" >&2; exit 1
fi
echo "warnings in this run:"
grep -icE "warning|WARN" "$LOG" | sed 's/^/  count: /'
