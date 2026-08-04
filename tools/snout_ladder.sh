#!/usr/bin/env bash
# Snout ladder: reshape -> true-profile render -> measure, one rung per --snout value.
#
# Every rung goes through the SAME render and the SAME measurement as the reference panel, which
# is the only reason the numbers are comparable at all. Do not measure a rung off the mesh: the
# mesh-level ratio normalises by head depth, which the edit itself changes, so it cancels.
set -euo pipefail
cd "$(dirname "$0")/.."
BL=/opt/blender-5.2.0/blender-wrapper.sh
SRC=mesh/canon/clyffy_v2_canon.blend
OUT=work/face_ab
mkdir -p "$OUT"

# Each rung is "SNOUT,MUZZLE" (MUZZLE optional, defaults to 1.00).
for RUNG in "$@"; do
    S="${RUNG%%,*}"
    M="${RUNG#*,}"; [ "$M" = "$RUNG" ] && M=1.00
    D="work/ladder_s${S}_m${M}"
    "$BL" -b --python tools/head_proportion.py -- "$SRC" "$D" --snout "$S" --muzzle "$M" \
        2>&1 | grep -E "snout band|weighted verts|snout x|muzzle x|max displacement|verts .* -> " || true
    "$BL" -b --python tools/profile_shot.py -- "$D/clyffy_v2_prop.blend" \
        "$OUT/prof_s${S}_m${M}.png" >/dev/null 2>&1
    echo "  rung snout=$S muzzle=$M rendered"
done
