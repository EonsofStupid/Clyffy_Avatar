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

**Convention:** `_*.py` are workbench probes (45 of them) — never the product path. The table
below classifies every OTHER script, because an unclassified file is indistinguishable from
incomplete work. Names of SUPERSEDED tools are deliberately NOT renamed: live code and
`clyffy.pack.toml` cite several of them as the provenance of recorded measurements, and
breaking those citations to tidy a filename would lose more than it gains.

### CHAIN — the 15-stage build, in order
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
| `mesh_patch.py` | close the inherited Tripo hole — adds faces only |
| `head_proportion.py` | **stage 1.5** — reshape the head to canon proportions. Displacement ONLY; asserts vertex/face counts and both operator groups unchanged. Runs after `canonicalize`, before `mouth_open`, because the 47 shape keys are deltas against current geometry |
| `materials.py` | **muzzle pad + patch browning + SSS + roughness.** Colour and surface response ONLY — asserts vertices, faces, shape keys and every vertex group are byte-identical. After `mesh_patch` (which changes face indices), before `vrm_export`. Writes `materials_report.json` |
| `vrm_export.py` | VRM 1.0 + springs. **SEGFAULTS ON EXIT after writing a valid file** — check the output, not the exit code |
| `spring_bones.py` | used by `vrm_export` |
| `vrm_color0_fix.py` | used by `vrm_export` — promotes the real vertex colours into `COLOR_0`. The VRM addon emits a uniform-white dummy `COLOR_0` and hides the data in `COLOR_1`, which every glTF consumer ignores; without this the authored muzzle tint is a silent NO-OP in the delivered file |

### GATES — nothing promotes without these
| Script | Checks |
|--------|--------|
| `accept.py` | the umbrella gate: 27 checks incl. artifact freshness, a TOML parse of the SSOT, posed containment, and the cross-repo live-bundle check |
| `vrm_check.py` | VRM 1.0 conformance, humanoid bones, morph targets, **facing measured from the EYE bones**, every contract morph key present |
| `pose_check.py` | posed containment across 30 states — caps the mouth, then parity-tests inside/outside |
| `renderer_check.py` | the LIVE renderer bundle is the current face + contract (crosses the repo boundary); also that `COLOR_0` carries the real tint, reading vertex DATA because colour accessors have no `min`/`max` to check |
| `viseme_distinct.py` | are the visemes actually distinguishable — RMS **and** P95 |
| `lip_seal.py` | (also a chain stage) rest-pose containment |

### CONTRACT · PRESENTATION · VOICE
| Script | Owns |
|--------|------|
| `control_surface.py` | **drive contract v1** — the SEAM. Emits the schema every renderer reads |
| `avatar_drive.py` | audio → time series + `drive_frames.jsonl` + muxed mp4 |
| `present.py` | beauty heroes (Cycles on GB10). Its render-time `polish_materials()` is SUPERSEDED by `materials.py` and stands down automatically when the mesh carries authored materials — it only runs for blends that predate that stage, which is what keeps the A/B honest |
| `viseme_sheet.py` | pinned-VISEME contact sheet (G4) |
| `tongue_sheet.py` | mouth closeups + an isolated pass with the head hidden |
| `demo_reel.sh` | self-contained demo mp4 with a **provenance card** read from the artifacts |
| `voice_tts.py` | local OuteTTS + WavTokenizer (Phase V) |
| `rebuild.sh` · `blender_env.sh` | fast verify / schema / optional VRM re-export · Blender 5.2 PATH pin |

### REFERENCE — `canon/`, restructured 2026-08-03
| path | what |
|--------|------|
| `canon/reference/` | **THE single authoritative face reference.** 3 flat-lit 2k sheets with a true 90° profile + `SPEC.md`. Operator: *"we only have this, this is perfect."* |
| `canon/_archive/` | every superseded set, dated by when it was replaced, with a README saying why. Kept because `pack.toml` / `BUILD_LOG.md` cite their numbers |
| `canon/CLYFFY/` · `canon/docs/` · `canon/_MASTER_REGISTRY.md` | show bible — gitignored, untouched |

`tools/head_metrics.py` measures head proportions from a SILHOUETTE, applying ONE function to the
reference and to our render alike — written because three earlier attempts compared a mesh to a
photo with different definitions and produced numbers that contradicted what was plainly visible.

### DIAGNOSTIC — produced a recorded number; cited by the SSOT, not run in the chain
| Script | Produced |
|--------|----------|
| `eye_probe.py` | the socket-rim + lid-closure finding (cited in `pack.toml`, `eye_open.py`) |
| `head_axis.py` | the 3D bilateral-symmetry solve → 233.75° candidate (cited in `pack.toml`) |
| `stretch_map.py` | `max_edge_stretch = 3.85` (cited in `pack.toml`) |
| `_matstate.py` | the material state actually SAVED in a blend — found SSS = 0.0 on all five materials, and that `present.py` was adding it at render time only |
| `_lipbands.py` | that the baked atlas paints the whole muzzle near-white (inner lip vs outer band = 6.9/441), so a material pass has to carry COLOUR, not just SSS |
| `_refcolor.py` | ⛔ SUPERSEDED — reads the ARCHIVED graded frames. The reference target colours, as ratios to the fur white point. Absolute sampling is invalid here: the frames are dim and blue-graded, and the image display path auto-levels, so colour cannot be matched by looking |

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
