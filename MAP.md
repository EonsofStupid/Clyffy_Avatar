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

## tools/ — every non-diagnostic script, classified

**Convention:** `_*.py` are workbench probes (42 of them) — never the product path. The table
below classifies every OTHER script, because an unclassified file is indistinguishable from
incomplete work. Names of SUPERSEDED tools are deliberately NOT renamed: live code and
`clyffy.pack.toml` cite several of them as the provenance of recorded measurements, and
breaking those citations to tidy a filename would lose more than it gains.

### CHAIN — the 13-stage build, in order
| Script | Stage |
|--------|-------|
| `canonicalize.py` | freeze transform (locks FWD 235.1°) |
| `mouth_open.py` | lip seam + cavity; writes the `cav_src` / `cav_depth` INT lineage |
| `chin_mass.py` | mandible growth (displacement only — vertex indices preserved) |
| `eye_open.py` | separate eye domes; **needs `--cut`**, validate-only by default; publishes `eye_*_center/radius` |
| `densify.py` | **lip-skin edge loops** — runs AFTER `eye_open --cut`, skin only (`cav_src` cannot interpolate) |
| `mouth_parts.py` | teeth + authored tongue (15 stations × 16 ring + 2 poles) |
| `lip_seal.py` | rest lip seal **+ the rest-pose containment gate** |
| `face_atlas.py` | weighted face regions (geodesic, bounded by `op_jaw_region`) |
| `shape_author.py` | 47 shapes = ARKit-43 + 4 documented extensions |
| `jaw_rig.py` | jaw / skull / root (harmonic solve; bone heat fails on this mesh) |
| `body_rig.py` | VRM-humanoid body + face weights transferred BY INDEX |
| `hoof.py` | dark cloven-hoof material — after `body_rig` (material only, no geometry) |
| `mesh_patch.py` | close the inherited Tripo hole — LAST, adds faces only |
| `vrm_export.py` | VRM 1.0 + springs. **SEGFAULTS ON EXIT after writing a valid file** — check the output, not the exit code |
| `spring_bones.py` | used by `vrm_export` |

### GATES — nothing promotes without these
| Script | Checks |
|--------|--------|
| `accept.py` | the umbrella gate: 27 checks incl. artifact freshness, a TOML parse of the SSOT, posed containment, and the cross-repo live-bundle check |
| `vrm_check.py` | VRM 1.0 conformance, humanoid bones, morph targets, **facing measured from the EYE bones**, every contract morph key present |
| `pose_check.py` | posed containment across 30 states — caps the mouth, then parity-tests inside/outside |
| `renderer_check.py` | the LIVE renderer bundle is the current face + contract (crosses the repo boundary) |
| `viseme_distinct.py` | are the visemes actually distinguishable — RMS **and** P95 |
| `lip_seal.py` | (also a chain stage) rest-pose containment |

### CONTRACT · PRESENTATION · VOICE
| Script | Owns |
|--------|------|
| `control_surface.py` | **drive contract v1** — the SEAM. Emits the schema every renderer reads |
| `avatar_drive.py` | audio → time series + `drive_frames.jsonl` + muxed mp4 |
| `present.py` | beauty heroes (Cycles on GB10) |
| `viseme_sheet.py` | pinned-VISEME contact sheet (G4) |
| `tongue_sheet.py` | mouth closeups + an isolated pass with the head hidden |
| `demo_reel.sh` | self-contained demo mp4 with a **provenance card** read from the artifacts |
| `voice_tts.py` | local OuteTTS + WavTokenizer (Phase V) |
| `rebuild.sh` · `blender_env.sh` | fast verify / schema / optional VRM re-export · Blender 5.2 PATH pin |

### DIAGNOSTIC — produced a recorded number; cited by the SSOT, not run in the chain
| Script | Produced |
|--------|----------|
| `eye_probe.py` | the socket-rim + lid-closure finding (cited in `pack.toml`, `eye_open.py`) |
| `head_axis.py` | the 3D bilateral-symmetry solve → 233.75° candidate (cited in `pack.toml`) |
| `stretch_map.py` | `max_edge_stretch = 3.85` (cited in `pack.toml`) |

### SUPERSEDED — kept for provenance, NOT the product path
| Script | Superseded by | Why kept |
|--------|---------------|----------|
| `jaw_drive.py` | `avatar_drive.py` | `avatar_drive.py:6` cites it explicitly as what it replaced |
| `find_axis.py` · `calibrate_axis.py` | `canonicalize.py` | the lineage that established FWD = 235.1°, now a locked canon value |
| `mouth_cut.py` · `mouth_cut2.py` · `mouth_cut3.py` | `mouth_open.py` | three attempts at the cavity before the ring-expansion approach worked |
| `jaw_test.py` · `jaw_test2.py` · `jaw_v2.py` · `jaw_v3.py` | `jaw_rig.py` | rig iterations; `jaw_rig` is the harmonic solve that shipped |
| `overlay.py` · `blender_inspect.py` | — | ad-hoc inspection helpers |

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
