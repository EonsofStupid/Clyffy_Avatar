# Clyffy Avatar

Holstein cow character pack: Blender-authored face/body → VRM + offline drive contract for **local voice**.

**Start here:** `STATUS.md` (gates) · `clyffy.pack.toml` (SSOT) · `MAP.md` (tree).

## Requirements

- **Blender 5.2+** with Cycles CUDA (this box: `/opt/blender-5.2.0`, symlinked as `blender` via `/opt/bin`)
- Do **not** use Ubuntu apt `blender` 4.0.2 — no GB10 sm_12x kernels
- Optional: `ffmpeg` for drive mp4 encode

```bash
source tools/blender_env.sh   # optional if /opt/bin is already early on PATH
blender --version             # expect 5.2.0 LTS
```

## Accept (gate G3)

```bash
python3 tools/accept.py
```

## Rebuild (fast path)

Default: refresh schema/examples, verify blender, optionally re-export VRM if body is newer.

```bash
./tools/rebuild.sh
./tools/rebuild.sh --vrm      # force VRM re-export
./tools/rebuild.sh --from-scratch   # prints full stage order; does not auto-run multi-hour mesh chain
```

## Present beauty heroes

```bash
blender -b --python tools/present.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/present 235.1 \
  rest happy surprised talk_aa thinking angry
```

## Control surface (one frame)

```bash
python3 tools/control_surface.py schema mesh/canon/body/control
python3 tools/control_surface.py examples mesh/canon/body/control

blender -b --python tools/control_surface.py -- apply \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/control 235.1 \
  mesh/canon/body/control/state_talk_aa.json talk_aa
```

## Drive (TTS sink — contract v1)

Synth demo:

```bash
blender -b --python tools/avatar_drive.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/drive 235.1 --synth 3.0
```

Real audio (wav/mp3):

```bash
blender -b --python tools/avatar_drive.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/drive 235.1 path/to/line.wav
```

**Outputs (always):**

| File | Role |
|------|------|
| `drive_frames.jsonl` | one control-surface frame per line (voice sink) |
| `drive_report.json` | fps, visemes used, rest hold |
| `alpha_talk.mp4` | offline preview (if ffmpeg available) |
| `front/f_####.png` | frame sequence |
| `clyffy_v2_avatar_drive.blend` | keyed blend |

## Viseme sheet

```bash
blender -b --python tools/viseme_sheet.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/control 235.1
```

## Voice (local `voice.tts`)

Slot: **`voice.tts`**. Backend: OuteTTS via `llama-tts` (`tools/voice_tts.py`).

```bash
# synthesize pack sample_lines
python3 tools/voice_tts.py --from-pack --no-speaker

# one-off
python3 tools/voice_tts.py --text "We are doing this today." \
  --out work/voice/samples/custom.wav --no-speaker

# lipsync drive
blender -b --python tools/avatar_drive.py -- \
  mesh/canon/body/clyffy_v2_body.blend work/voice/drive/custom 235.1 \
  work/voice/samples/custom.wav
```

Index: `work/voice/SAMPLES.md` · report: `work/voice/tts_report.json`

## Laws

- **Rest-state:** every clip ends at rest  
- **jawOpen:** bone only, never a shape key  
- **Visemes:** shared live + episode — edit `VISEMES` in `tools/control_surface.py` only once  
- **No live viewer required** for v0.1 voice gate  
