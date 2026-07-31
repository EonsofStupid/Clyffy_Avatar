#!/usr/bin/env bash
# Fast pack maintenance for v0.1-talk-ready.
# Default: verify Blender, regenerate control schema/examples, accept.
# --vrm: re-export VRM from body blend on Blender 5.2.
# --from-scratch: print full mesh pipeline order only (does not auto-run).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "$ROOT/tools/blender_env.sh" 2>/dev/null || true
export PATH="/opt/bin:/usr/local/bin:${PATH:-}"

BLENDER="${BLENDER:-blender}"
FWD=235.1
BODY="mesh/canon/body/clyffy_v2_body.blend"
VRM="mesh/canon/body/clyffy.vrm"
CTRL="mesh/canon/body/control"
DO_VRM=0
FROM_SCRATCH=0

for arg in "$@"; do
  case "$arg" in
    --vrm) DO_VRM=1 ;;
    --from-scratch) FROM_SCRATCH=1 ;;
    -h|--help)
      echo "Usage: $0 [--vrm] [--from-scratch]"
      exit 0
      ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [[ "$FROM_SCRATCH" -eq 1 ]]; then
  cat <<'EOF'
Full mesh chain (manual / long). Values from clyffy.pack.toml [pipeline]:

  1. canonicalize → clyffy_v2_canon.blend
  2. mouth_open    → clyffy_v2_open.blend
  3. chin_mass     → clyffy_v2_chin.blend      (M2; eye_open reads THIS, not open)
  4. eye_open      → clyffy_v2_eyes.blend      (needs --cut; default is validate-only)
  5. densify       → lip-skin edge loops       (AFTER eye_open --cut; skin only)
  6. mouth_parts   → clyffy_v2_parts.blend
  7. lip_seal      → (parts in place)           + rest-pose containment gate
  8. face_atlas    → clyffy_v2_atlas.blend
  9. shape_author  → shapes/clyffy_v2_shapes.blend
 10. jaw_rig       → clyffy_v2_rig.blend       (22 deg STRESS pose; the contract envelope is 10 deg)
 11. body_rig      → body/clyffy_v2_body.blend
 12. hoof          → hoof material             (material only, no geometry)
 13. mesh_patch    → close the inherited hole   (adds faces only)
 14. materials     → muzzle pad / lip bands / SSS  (colour only, asserts geometry unchanged)
 15. vrm_export    → body/clyffy.vrm            (runs vrm_color0_fix automatically)
 16. control_surface schema + examples
 17. avatar_drive / present as needed

ORDER IS LOAD-BEARING, not cosmetic: densify must follow eye_open --cut (it broke the eye cut
at three reaches when run before it), materials must follow mesh_patch (which changes face
indices), and anything that changes VERTEX COUNT invalidates body_rig, which transfers face
weights BY INDEX and asserts equal counts.

vrm_export SEGFAULTS ON EXIT after the VRM is written (Blender teardown, "Found 4
unreleased ID's"). The file is complete and passes vrm_check — check for the output, not
for exit status.

v0.1 freeze uses cached blends; re-run stages only when mesh rules change.
EOF
  exit 0
fi

echo "== blender =="
"$BLENDER" --version | head -1
ver="$("$BLENDER" --version | head -1)"
if ! echo "$ver" | grep -qE 'Blender 5\.[2-9]|Blender [6-9]'; then
  echo "ERROR: need Blender >= 5.2 (got: $ver)" >&2
  echo "  pin: /opt/blender-5.2.0/blender-wrapper.sh" >&2
  exit 1
fi

echo "== control schema + examples =="
python3 tools/control_surface.py schema "$CTRL"
python3 tools/control_surface.py examples "$CTRL"

if [[ "$DO_VRM" -eq 1 ]]; then
  echo "== VRM re-export =="
  if [[ ! -f "$BODY" ]]; then
    echo "ERROR: missing $BODY" >&2
    exit 1
  fi
  "$BLENDER" -b --python tools/vrm_export.py -- "$BODY" "$VRM"
fi

echo "== accept =="
python3 tools/accept.py

echo "rebuild ok"
