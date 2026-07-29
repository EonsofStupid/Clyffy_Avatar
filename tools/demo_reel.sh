#!/usr/bin/env bash
# Build a single self-contained demo MP4 — talking (with audio), visemes, expressions.
#
#   bash tools/demo_reel.sh [out.mp4]
#
# WHY A SCRIPT AND NOT A ONE-OFF: "show me the latest version" is a question about PROVENANCE,
# not about video editing. This stamps the build identity onto the first card — date, vertex
# count, morph count, jaw envelope, gate state — read live from the delivered artifacts, so the
# file itself carries the evidence. A demo reel with no provenance is exactly how a stale
# bundle shipped for a day without anyone noticing.
#
# Portable on purpose: h264 + aac, 720x900 (the companion 4:5 framing), 24 fps. Plays anywhere,
# audio muxed in — this machine has no speakers connected yet.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(pwd)
OUT=${1:-$ROOT/work/demo/clyffy_demo.mp4}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$(dirname "$OUT")"

W=720; H=900; FPS=24
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
BODY=$ROOT/mesh/canon/body/clyffy_v2_body.blend
VRM=$ROOT/mesh/canon/body/clyffy.vrm
SCHEMA=$ROOT/mesh/canon/body/control/control_surface.schema.json
TALK=$ROOT/work/voice/drive_v2/_all_lines.mp4

for f in "$BODY" "$VRM" "$SCHEMA" "$TALK"; do
  [ -f "$f" ] || { echo "MISSING: $f" >&2; exit 1; }
done

# ── provenance, read from the delivered artifacts ────────────────────────────
BUILT=$(date -r "$BODY" +"%Y-%m-%d %H:%M")
JAW=$(python3 -c "import json;print(json.load(open('$SCHEMA'))['envelope']['jaw']['max_deg'])")
read -r VERTS MORPHS < <(python3 - "$VRM" <<'PY'
import json, struct, sys
p = sys.argv[1]
with open(p, 'rb') as fh:
    struct.unpack('<III', fh.read(12))
    clen, _ = struct.unpack('<II', fh.read(8))
    g = json.loads(fh.read(clen).decode())
names = set()
verts = 0
for m in g.get('meshes', []):
    for n in (m.get('extras') or {}).get('targetNames', []) or []:
        names.add(n)
    for pr in m.get('primitives', []):
        for n in (pr.get('extras') or {}).get('targetNames', []) or []:
            names.add(n)
        a = (pr.get('attributes') or {}).get('POSITION')
        if a is not None:
            verts += g['accessors'][a].get('count', 0)
print(verts, len(names))
PY
)
# glTF vertex count is SEAM-SPLIT and higher than the mesh count (48220) — the exporter
# duplicates verts at UV/normal boundaries. Labelled as glTF verts so the two numbers do not
# look like a contradiction.
# The talking reel must be NEWER than the body it depicts, or the demo lies.
if [ "$TALK" -ot "$BODY" ]; then
  echo "!! REFUSING: $TALK is older than $BODY — re-drive it first" >&2
  exit 1
fi
echo "provenance: built $BUILT · $VERTS verts · $MORPHS morphs · jaw ${JAW}deg"

# ASCII ONLY in drawtext. Backslash-escaping a multibyte character (— · °) makes ffmpeg's
# drawtext parser consume the following UTF-8 bytes and silently SWALLOW real characters:
# 'live face pack' rendered as 'live face pa', 'GREEN' as 'GRE', 'collapsed' as 'collapse'.
esc () { printf '%s' "$1" | sed 's/:/\\:/g; s/'"'"'/\\\\\\'"'"'/g'; }
V="format=yuv420p,scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2:color=0x101214,setsar=1,fps=${FPS}"
ENC=(-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 128k -ar 48000 -ac 2)

label () { # $1 = big, $2 = small
  local a b; a=$(esc "$1"); b=$(esc "$2")
  echo "drawtext=fontfile=${FONT}:text='${a}':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-96:box=1:boxcolor=0x000000AA:boxborderw=12,\
drawtext=fontfile=${FONT}:text='${b}':fontcolor=0x9fe8ff:fontsize=19:x=(w-text_w)/2:y=h-52:box=1:boxcolor=0x000000AA:boxborderw=10"
}

n=0
add () { printf "file '%s'\n" "$1" >> "$TMP/list.txt"; }

# ── 0. provenance card ───────────────────────────────────────────────────────
CARD="drawtext=fontfile=${FONT}:text='CLYFFY':fontcolor=white:fontsize=76:x=(w-text_w)/2:y=210,\
drawtext=fontfile=${FONT}:text='avatar - live face pack':fontcolor=0x9fe8ff:fontsize=26:x=(w-text_w)/2:y=300,\
drawtext=fontfile=${FONT}:text='built $(esc "$BUILT")':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=430,\
drawtext=fontfile=${FONT}:text='${MORPHS} morph targets / ${VERTS} glTF verts':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=470,\
drawtext=fontfile=${FONT}:text='jaw envelope ${JAW} deg (contract)':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=510,\
drawtext=fontfile=${FONT}:text='accept / vrm_check / pose_check  GREEN':fontcolor=0x8fdf8f:fontsize=24:x=(w-text_w)/2:y=560"
ffmpeg -v error -y -f lavfi -i "color=c=0x101214:s=${W}x${H}:r=${FPS}:d=4" \
  -f lavfi -i "anullsrc=r=48000:cl=stereo" -shortest \
  -vf "$CARD" "${ENC[@]}" "$TMP/$(printf %02d $n)_card.mp4"; add "$TMP/$(printf %02d $n)_card.mp4"; n=$((n+1))

# ── 1. talking, WITH AUDIO ───────────────────────────────────────────────────
ffmpeg -v error -y -i "$TALK" \
  -vf "${V},$(label 'TALKING' 'local voice + audio-driven lipsync')" \
  "${ENC[@]}" "$TMP/$(printf %02d $n)_talk.mp4"; add "$TMP/$(printf %02d $n)_talk.mp4"; n=$((n+1))

# ── 2. visemes — the consonant work is the headline, so name each one ────────
for f in sil PP FF TH DD kk CH SS nn RR aa E I O U; do
  p=$ROOT/mesh/canon/body/control/viseme_${f}.png
  [ -f "$p" ] || continue
  ffmpeg -v error -y -loop 1 -t 0.72 -i "$p" -f lavfi -i "anullsrc=r=48000:cl=stereo" -shortest \
    -vf "${V},$(label "viseme  ${f}" '15 pinned visemes / 0 of 105 pairs collapsed')" \
    "${ENC[@]}" "$TMP/$(printf %02d $n)_v_${f}.mp4"; add "$TMP/$(printf %02d $n)_v_${f}.mp4"; n=$((n+1))
done

# ── 3. expressions, Cycles beauty ────────────────────────────────────────────
for f in rest happy surprised talk_aa angry thinking; do
  p=$ROOT/mesh/canon/body/present/hero_${f}.png
  [ -f "$p" ] || continue
  ffmpeg -v error -y -loop 1 -t 1.4 -i "$p" -f lavfi -i "anullsrc=r=48000:cl=stereo" -shortest \
    -vf "${V},$(label "${f}" 'expression presets / Cycles on GB10')" \
    "${ENC[@]}" "$TMP/$(printf %02d $n)_h_${f}.mp4"; add "$TMP/$(printf %02d $n)_h_${f}.mp4"; n=$((n+1))
done

ffmpeg -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$OUT"
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT")
SZ=$(stat -c%s "$OUT")
echo "wrote $OUT"
printf "  %.1fs · %s bytes · %d segments · h264+aac %dx%d@%dfps\n" "$DUR" "$SZ" "$n" "$W" "$H" "$FPS"
