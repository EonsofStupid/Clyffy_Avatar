# Clyffy_Avatar — MAP

Filetree-first map for this project only. **SSOT values live in `clyffy.pack.toml`.**  
Does not register monorepo crates; Avatar is a character pack + Blender tool chain.

## Top level

| Path | Owns |
|------|------|
| `clyffy.pack.toml` | Character pack SSOT (calibration, pipeline, rig, voice, animation) |
| `POAM.md` | **Plan of Action & Milestones** — the sequenced build plan, A0–A6, each with a VERIFY gate |
| `STATUS.md` | Freeze version, gates G1–G7, deferred, voice checklist |
| `CANON.md` | Visual / show identity distillation from Drive |
| `BUILD_LOG.md` | Chronological build decisions and commands |
| `README.md` | How to run tools (operator entry) |
| `pull-canon.sh` | rclone pull of Drive canon assets |
| `canon/` | Pulled show docs / reference (not the live mesh) |
| `mesh/` | All geometry + exports |
| `tools/` | Blender / pure-Python pipeline scripts |
| `work/` | Scratch, voice refs, non-canon experiments |

## mesh/

| Path | Owns |
|------|------|
| `mesh/canon/*.blend` | Frozen pipeline stages (canon → open → eyes → parts → atlas → rig) |
| `mesh/canon/shapes/` | ARKit shape authoring + diagnostic sheets |
| `mesh/canon/body/` | Body rig, VRM, control, drive, present |
| `mesh/canon/body/clyffy_v2_body.blend` | **Primary offline drive target** (shapes + armature) |
| `mesh/canon/body/clyffy.vrm` | Real-time delivery format (post-voice viewer) |
| `mesh/canon/body/control/` | Schema, example states, control/viseme sheets |
| `mesh/canon/body/drive/` | Timed drive: mp4, jsonl frames, report |
| `mesh/canon/body/present/` | Beauty heroes (Cycles) |
| `work/voice/` | Local TTS / reference audio (optional) |

## tools/ (pipeline order)

| Script | Stage |
|--------|-------|
| `canonicalize.py` | freeze transform |
| `mouth_open.py` | lip seam + cavity |
| `chin_mass.py` | mandible growth (displacement only — vertex indices preserved) |
| `eye_open.py` | separate eye domes |
| `mouth_parts.py` | teeth + tongue |
| `lip_seal.py` | rest lip seal |
| `face_atlas.py` | weighted face regions |
| `shape_author.py` | ARKit shapes |
| `jaw_rig.py` | jaw / skull / root |
| `body_rig.py` | VRM-humanoid body + face weights |
| `hoof.py` | dark cloven hoof material — runs AFTER body_rig (material only, no geometry) |
| `vrm_export.py` | VRM 1.0 + springs |
| `spring_bones.py` | used by vrm_export |
| `control_surface.py` | schema / examples / apply one frame |
| `avatar_drive.py` | time series + **drive_frames.jsonl** |
| `present.py` | beauty heroes (Cycles preferred) |
| `rebuild.sh` | fast verify / schema / optional VRM re-export |
| `accept.py` | gate checks G3 |
| `blender_env.sh` | PATH pin for Blender 5.2 |
| `viseme_sheet.py` | render pinned VISEMES contact sheet |

Diagnostic `_*.py` helpers are workbench probes — not the product path.

## pack.toml sections → meaning

| Section | Meaning |
|---------|---------|
| `[pack]` | version freeze + blender pin |
| `[calibration]` | forward axis 235.1° |
| `[pipeline]` | blend path chain |
| `[shapes]` / `[rig.*]` | ARKit + VRM + control surface |
| `[voice]` | character voice brief + `voice.tts` slot |
| `[animation]` | rest-state law, dual surface |
| `[generation]` | image/video fabric (not avatar rig) |

## External (cite, do not fork here)

| Thing | Home |
|-------|------|
| `voice.tts` model slot | clyffy / WiredFront model slot table — **slot name only** |
| Show voice token | Drive registry `voice:VOICE-CORPUS (redacted)` |
| Roadmap E2 Avatar mode | `clyffy/docs/CLYFFY_ROADMAP.md` |
