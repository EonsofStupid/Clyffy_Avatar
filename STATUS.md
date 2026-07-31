# Clyffy Avatar — STATUS

**Pack version:** `0.1.0-talk-ready` (see `clyffy.pack.toml` `[pack]`)  
**Frozen:** 2026-07-27  
**Toolchain:** Blender **5.2.0 LTS** aarch64 at `/opt/blender-5.2.0` (Cycles CUDA / OptiX on NVIDIA GB10)  
**SSOT:** `clyffy.pack.toml` — every tool and path listed there wins over tribal knowledge.

---

## ▶ THE BUILD PLAN IS `POAM.md`
Milestones **A0–A6**, each with a VERIFY gate and a status (SPEC → BUILT → VERIFIED). This file
is current TRUTH; `POAM.md` is the sequenced PLAN; `BUILD_LOG.md` is the chronological record.
**A1 DONE (BUILT) 2026-07-29** — the renderer's built bundle was serving a contract **two
generations stale**: `jaw.max_deg 22.0` against the contract's 10.0, and a `DD` viseme from
before the M5 rewrite. `public/` was correctly symlinked to canon; `dist/` (what the Tauri
shell ships) had not been rebuilt since 2026-07-28. Rebuilt, now byte-identical to canon, and
**gated** by `tools/renderer_check.py` wired into `accept.py` — negative-tested against the
bundle that was actually shipping (4 failures, exit 1).
**A1 → VERIFIED needs the operator to look at it:**
`cd /home/hades/Projects/clyffy/interfaces/clyffy-avatar/renderer && npm run dev`

## ▶ RESUME HERE — written 2026-07-28 for a fresh context

**Read this, then `BUILD_LOG.md` from "M2 (2026-07-28)" down. Do not re-derive M1 or M2.**

### State: M2 is DONE and PROMOTED. `accept.py` GREEN, `vrm_check.py` GREEN.
The open mouth no longer reads as a rectangular hole. `tools/chin_mass.py` (new stage after
`mouth_open`) grew a mandible, and `ENVELOPE.jaw.max_deg` went **22.0 → 13.0**. Rollbacks
for every promoted artifact are the `.pre-m2` siblings in `mesh/canon/`.

### M3 (teeth) also DONE and PROMOTED, same day.
Three measured defects: the two arches were **intersecting** (−0.83%H at 35% open), the
inward offset used a **global −fwd** so the bands drove into the cheek at the commissures,
and its sign test was **ill-conditioned at the corners** so some end rings flipped OUTWARD
(teeth at arch position 1.43, wider than the mouth). Fixed with a shared bite plane, a
per-point local normal oriented toward the cavity centroid, and an overbite/overjet so the
teeth actually read. Containment is now a **measured gate** in `lip_seal.py` (15-ray fan):
0 of 104 / 0 of 96 / 0 of 146 visible at rest (the tongue is 242 verts since 2026-07-29). Rollbacks: `.pre-m3`.

### M5, the lip rim, the chin redo, the hands and the gates — ALL DONE, same day.
* **M5** — viseme table rewritten, 10 → 21 morphs driven, weights scaled to each shape's
  MEASURED range (`mouthClose` moves 0.45%H and was carrying four visemes).
* **Lip rim UNFROZEN** — it was frozen in TWO places (`face_atlas` excluded it from every
  region; `shape_author` protected it with the bag) and a third fix was needed because
  Euclidean falloff cannot separate lips 0.0077 apart. Now geodesic, bounded by the
  operator's `op_jaw_region`, partitioned so the lips compete. Lip-driven aperture
  **0.042 → 1.18%H**. The bag follows by `cav_src` lineage and does not tear.
* **Chin redone** — `chin_mass` 0.028 → 0.045, jaw 13° → 10°. Each cut was paid for: 13 by
  the collar arithmetic, 10 by lip-driven aperture.
* **Hands** — canon is CLOVEN HOOVES (two toes), never fingers; the mesh already had the
  toe count. `tools/hoof.py` adds the dark material (no geometry change, runs after
  `body_rig`). The F2 leg defect was present on the ARMS too — gated by height, which arms
  escape — fixed by distance to the arm chain: `hand_L` 0.436 → 0.852, 0 → 152 verts
  majority-owned, `lower_arm_L` +35° travel 1.73 → 3.12%H.
* **Gates hardened** — `accept.py` now checks artifact FRESHNESS (it was green on a
  4-hour-stale herosheet and 26-hour-stale drive frames encoding the 22° contract);
  `vrm_check.py` now verifies every contract morph key exists in the delivered VRM. Both
  negative-tested with an injected bogus key: exit 1 propagates through `accept.py`.

### TONGUE done and PROMOTED (2026-07-29). Read `BUILD_LOG.md` "Tongue (2026-07-29)".
The tongue is no longer a UV sphere. Authored loft (15 stations × 16 ring + 2 poles, 242
verts), every dimension derived from the CAVITY at build time, tip stopping at the lingual
face of the lower incisors. Fills the bag 58/75/55% (was 36/52/26). **`tongueOut` now
protrudes PAST the lip plane (+1.71%H); it used to finish 5.29%H short and could not work.**
Containment GREEN 0/242. Rollbacks: `.pre-tongue`. New tool `tools/tongue_sheet.py`.

### ⚠️ A CONTRACT BUG was found and fixed the same day — check for more of these.
`viseme_sheet.py`, `present.py` and `control_surface.py`'s own `set_jaw_open()` all posed the
jaw at a hard-coded **22.0°** while `ENVELOPE["jaw"]["max_deg"]` has been **10.0** since the
collar arithmetic. The G4 viseme sheet — the artifact the character is judged from — had been
flattering the rig by 2.2× for its entire life. All three now read the envelope. Heroes,
viseme sheet and drive frames re-rendered at the honest angle.

**Current: `accept.py` GREEN with ZERO warnings · `vrm_check.py` GREEN, 47 morph targets,
42/42 contract keys.** `accept.py` also now PARSES the pack as TOML — see the blind-spot note
below. Rollbacks: `.pre-m2`, `.pre-m3`, `.pre-lips`, `.pre-hoof`, `.pre-tongue`, `.pre-artic`.

### ⚠️ A FOURTH BLIND SPOT — the SSOT had never been machine-readable.
`clyffy.pack.toml` was **not valid TOML** and never had been: a multi-line inline table, a
basic string spanning four lines, a Python-style `corner_up, corner_down = 0.009, 0.008`, and
a duplicate `tongue` key. It never surfaced because `accept.py` reads the pack as TEXT and
substring-matches, so the file that calls itself "SSOT — wins over tribal knowledge" could not
be consumed by any tool that read it properly. Now fixed, parsed, and gated in `accept.py`;
negative-tested (injected error → accept RED exit 1, reverted → 0).

### TONGUE ARTICULATION done and PROMOTED (2026-07-29) — the consonant collapse is CLOSED.
Four new shapes as a documented **extension beyond ARKit-52** (additive; ARKit's 43 keys
untouched, a consumer that only knows ARKit is unaffected). Shapes **43 → 47**, contract
morph keys 38 → 42, all verified present in the VRM.

`tongueUp` (tip to ridge) · `tongueBack` (velar) · `tongueCurl` (blade) · `lipTuckLower` (/f/).
Every magnitude **derived from measured headroom** (4.85%H max), not asserted — this cavity is
shallow at the front and a hard-coded lift would drive the tip through the palate.

| pair | before | after |
|---|---|---|
| `DD`/`kk` | 0.17%H | **0.35%H** |
| `sil`/`FF` | 0.25%H | **0.45%H** |
| `CH`/`RR` | 0.23%H | **0.29%H** |
| `SS`/`nn` | 0.25%H | off the closest list (SS travel 0.28 → 0.45) |

**Pairs failing threshold 3 → 0.** `viseme_distinct.py` now reports RMS **and** P95, because
RMS over a fixed region is dominated by how many verts move, not how distinctive the shape
is. Containment measured at full strength: **0/242 for every articulation morph with the
mouth closed.** Rollbacks: `.pre-artic`.

### P3/P4/P5 DONE and PROMOTED (2026-07-29). `accept.py` GREEN incl. posed containment.

**`tools/pose_check.py`** — 30 posed states (rest + 15 visemes + 7 presets + jawOpen sweep +
corner shapes alone), wired into `accept.py`. Method: **cap the mouth with a membrane across
the lip rim, then parity-test inside/outside**, so visible-through-the-opening is correctly
irrelevant. TWO WRONG TESTS FIRST — signed-distance (109 false findings) and ray-fan+aperture
polygon (1516) — both documented in the docstring so neither is retried.
Found one real defect: **`PP` press 0.7 → 0.60** (the press takes the upper lip behind the
incisors; it was NOT the rolls, and `mouthClose` rescues it).

**`tools/mesh_patch.py`** — the inherited Tripo hole is CLOSED. boundary 19 → 0,
non-manifold 1 → 0. The sliver face (area 7.0e-08) was the cause, the hole its symptom.
Runs LAST, adds faces only (47178 → 47179), vertex count untouched.

**⚠️ THE UPPER-LIP NOTCH IS A TOPOLOGY LIMIT — do not re-attempt a smoother.**
Face normals invert (`happy` 26 flips, `aa` 24; per shape alone `lipTuckLower` 23,
`mouthUpperUpRight` 22, `mouthPucker` 21). Relaxing the displacement field was tried and
REJECTED on the render: unbounded it keeps 33% of `eyeBlinkLeft`'s travel (an eye that no
longer closes), peak-restoration made it worse, and an 85% floor changes nothing visible.
**Most flips are not defects — a closing eyelid folds.** Real fix = retopology loops at the
lip and eyelid, which changes vertex count and rebuilds the whole chain. Scoped job.

### ⚠️ THE VOICE WAS DONE ON 2026-07-27. Do not treat it as open work.
Phase V closed V1–V5 that day: OuteTTS 0.2 500M Q5_K_M + WavTokenizer under
`work/voice/models/`, `tools/voice_tts.py`, 5 sample lines rendered, identity reference locked
(`higgsfield` preset Mark + tuning). **The ONLY open item is V6 — the operator's A/B.**
I mis-scoped this on 2026-07-29 and offered "build voice" as a phase. It was not one.

### What 2026-07-29 actually did: RE-RENDERED THE FACE, not the voice.
Every drive mp4 dated 2026-07-27, i.e. the voice playing over a face that predated the tongue,
the four articulation morphs, the jaw-angle fix and the mesh patch — so a demo built on them
would show the OLD mouth. Same five wavs, current face. **No audio was synthesized, no models
touched, and `work/voice/drive/` is intact.**

**Review reel: `work/voice/drive_v2/_all_lines.mp4`** — 5 lines, 9.19s, h264+aac.
Old `work/voice/drive/` kept for A/B.

### LIP DENSIFICATION done and PROMOTED (2026-07-29) — `tools/densify.py`.
Acts on the fold conclusion above. Lip-region median edge **1.35x global → 0.75x**
(+940 verts). **RUNS AFTER `eye_open --cut`, NOT after `canonicalize`** — running it earlier
breaks the eye cut (5 connected components instead of 3; `eye_open` needs exactly 2 eyeball
components and SILENTLY skips writing the `eye_*_center` props otherwise, killing
`face_atlas` four stages later). Skin only: `cav_src` is an INT lineage layer and cannot be
interpolated. Refuses to save if any operator group loses members.

### ⚠️ IT EXPORTED THE CHARACTER FACING BACKWARDS — and the cause was `body_rig`, not densify.
`vrm_check` FAILED at **-179.79° off +Z**. `spine_point()` used an unweighted MEAN over slab
vertices — density-biased, not a geometric centre — so 940 new lip loops dragged the neck
sample and the SKULL bone with it. Replaced with the midpoint of the slab's fore-aft EXTENT.
Proof: canon skull head `(-0.0389, 0.0190)` vs densified `(-0.0389, 0.0191)` — identical.
It also made the canon export MORE accurate: **facing -2.10° → -0.26°**.
Every other check stayed green; only `vrm_check`'s facing test saw it. Second time that test
has been the only gate looking the right way.

**Honest limits:** small notches remain at both commissures and there is new fine scalloping
on the lower lip edge.

### EYELID densification — TRIED, MEASURED, REJECTED. `eye_mult = 0.0`.
The obvious follow-on does not work. At 2.2x eyeball radius it costs +3087 verts and the fold
RATE per moved vertex gets WORSE (`eyeBlinkLeft` 0.088 → 0.092, `eyeSquintLeft` 0.054 →
0.060), and side by side at identical framing the denser lid RENDERS slightly worse — the
fold resolves into finer, more visible creasing instead of going away.
**The lip and the eyelid are not the same problem.** The lip was measurably STRETCHED by
`mouth_open` (1.35x the global median edge) and was short of mesh. The eyelid was never
stretched — it folds because a closing eyelid folds. Resolution cannot fix a fold that is not
a resolution deficit. Canon was never touched; the shipped defaults reproduce it exactly
(47778 verts / 47624 faces).

### ▶ NEXT
1. **Operator A/B on the voice** — `work/voice/SAMPLES.md` checkboxes. This is the one thing
   only the operator can close; the scaffold is a built-in OuteTTS male default, NOT a Clyffy
   clone.
2. ~~Goggles~~ — **NOT IN SCOPE. OPERATOR RULING: "those are separate props."** The canon
   `required` / `goggles_absent_ok = false` flags describe the SHOW, not this asset pack.
   `goggle_state` stays a logged-only contract input. Do not build goggle geometry here.
3. **Retopology** (lip + eyelid loops) — the only remaining fix for the fold artifacts.
4. **L4** phone/assistant surface · **L5** Unreal adapter.

### The three things that will bite a fresh context
1. **`eye_open.py` does NOTHING without `--cut`** — it is validate-only by default. A chain
   run without it silently produces no eyes blend and every later stage fails on a missing
   input.
2. **`vrm_export.py` SEGFAULTS on exit AFTER writing a complete VRM** ("Found 4 unreleased
   ID's"). Check for the OUTPUT FILE, not the exit status. `set -e` will abort a chain that
   actually succeeded.
3. **The collar is a hard geometric ceiling** — see the boxed section in the M-phase below.
   `max_deg` cannot be raised past ~13° without moving the shirt collar down. Do not
   relitigate it; the arithmetic is at the call site in `tools/control_surface.py`.

### Measurement rules that have each already cost a cycle
* Measure bilateral things on **`lat`**, never world X (the 235.1° transform makes X wrong).
* Measure VRM facing from the **eye bones**, never L/R legs (they were mirrored — L1).
* Split the lip rim by **CHAIN**, never by z — a z-split under-reports aperture ~10×.
* `body_rig` transfers face weights **by vertex index** and asserts equal counts, so any new
  mesh stage must preserve vertex count. `chin_mass.py` is displacement-only for this reason.
* Warnings are signal. The `jawmap` render was flat grey for its entire life because the
  colour attribute was never made active — every M1 weight judgment was made blind.

### Full chain (staged, then promoted only on green)
```bash
# stage into work/<name>/, never straight into mesh/canon
canonicalize → mouth_open → chin_mass → eye_open --cut → densify → mouth_parts → lip_seal
  → face_atlas → shape_author → jaw_rig → body_rig → hoof → mesh_patch → materials → vrm_export
  # materials (2026-07-30) authors the muzzle pad + SSS + roughness. Colour and surface
  # response ONLY — it asserts verts/faces/shape-keys/vertex-groups byte-identical. It must
  # follow mesh_patch, which changes face indices. vrm_export then runs vrm_color0_fix
  # automatically, without which the tint is a silent no-op in the delivered VRM.
  # ⚠️ densify and mesh_patch were MISSING from this line until 2026-07-29. jaw_rig's own
  # ANGDEG default is 22.0 and is a post-build STRESS pose, not the runtime envelope — the
  # contract is ENVELOPE["jaw"]["max_deg"] = 10.0 in tools/control_surface.py.
python3 tools/accept.py && python3 tools/vrm_check.py mesh/canon/body/clyffy.vrm
```
Re-render `present.py` heroes and `viseme_sheet.py` after ANY geometry OR MATERIAL change —
they go stale silently. `accept.py` does check they are newer than the body blend.

---

## What this freeze is

Talk-ready **offline** asset pack: Holstein Clyffy, waist-up, ARKit-52 face, VRM 1.0 delivery, control-surface drive contract. Established so **local GB10 voice** (`voice.tts` slot) can be built without inventing a second face API.

## Voice-open gate (G1–G7)

| # | Criterion | How to check |
|---|-----------|--------------|
| G1 | Pack tagged talk-ready + this STATUS | `[pack].version` · this file |
| G2 | Rebuild path exists | `tools/rebuild.sh` |
| G3 | Acceptance green | `tools/accept.py` |
| G4 | Viseme + expression beauty current | `mesh/canon/body/present/`, `control/_visemesheet.jpg` |
| G5 | Audio → frames + mp4 | `mesh/canon/body/drive/drive_frames.jsonl` + `alpha_talk.mp4` |
| G6 | Drive contract v1 documented | pack `[rig.control_surface]` |
| G7 | Voice brief + local TTS slot | pack `[voice]` |

**Open local voice job only when accept is green and G4–G5 artifacts exist.**

### Gate status (2026-07-27) — ⚠️ SUPERSEDED, see the RESUME block at the top of this file

| # | Status |
|---|--------|
| G1 | **green** — pack `0.1.0-talk-ready` + this file |
| G2 | **green** — `tools/rebuild.sh` |
| G3 | **green** — `python3 tools/accept.py` |
| G4 | **green** — present heroes + `control/_visemesheet.jpg` |
| G5 | **green** — `drive/drive_frames.jsonl` + `alpha_talk.mp4` (+ `audio_proof.mp4`) |
| G6 | **green** — pack `[rig.control_surface]` contract v1 |
| G7 | **green** — pack `[voice]` + `voice.tts` local-first |

**Voice-open gate: READY for operator go on local GB10 TTS.**

### Phase V — local voice (2026-07-27) **DONE (v0 scaffold)**

| # | Status |
|---|--------|
| V1 | **green** — OuteTTS Q5_K_M + WavTokenizer under `work/voice/models/` |
| V2 | **green** — `tools/voice_tts.py` |
| V3 | **green** — 5 pack `sample_lines` → `work/voice/samples/*.wav` |
| V4 | **green** — each line driven under `work/voice/drive/*/alpha_talk.mp4` + jsonl |
| V5 | **green** — pack `[voice]` backend paths recorded |
| V6 | **operator** — listen + watch; checkboxes in `work/voice/SAMPLES.md` |

```bash
python3 tools/voice_tts.py --from-pack --no-speaker
# review: work/voice/samples/ + work/voice/drive/*/alpha_talk.mp4
```

**Note:** This is a **scaffold** (OuteTTS built-in male default), not a trained Clyffy clone. Identity lock is operator A/B.

### Go pass (2026-07-27)
* Drive mp4s now **mux audio** (`avatar_drive.py` + re-mux of existing frames)
* Review reel: `work/voice/drive/_all_lines.mp4`
* Pack signature demo: `mesh/canon/body/drive/alpha_talk.mp4` (line 00 + audio)

### Framing — full-body added (2026-07-27) **operator-accepted, starting point**

Waist-up stays the **default** on both surfaces. `--full` frames the whole figure.

```bash
blender -b --python tools/present.py -- \
  mesh/canon/body/clyffy_v2_body.blend work/full_check 235.1 --full rest talk_aa
blender -b --python tools/avatar_drive.py -- \
  mesh/canon/body/clyffy_v2_body.blend <out> 235.1 <audio.wav> --full
```

`present.py --full` → `full_*.png` + `_fullsheet.jpg` · `avatar_drive.py --full` → `front_full/` + muxed mp4.

**Legs were never missing.** Geometry and bones both already existed; only the camera
never showed them. An early probe along **world X** wrongly read the legs as one fused
mass — the character sits at 235.1°, so splits must be measured on the lateral axis.

### F1–F3 — worked and closed (2026-07-27)

| # | Gap | Resolution | Evidence |
|---|-----|-----------|----------|
| F1 | Full-body lighting fell off down the legs | Light rig now **scales to the framing** (`LR=1.60`, energies ×`LR²`, teal ×2.5, rim dropped to reach hooves). Cause was scale, not anchoring — lights already tracked `focus`. | legs p90 **160** vs head/chest 135; waist-up diff vs frozen hero **0.003/255**, 0 px >4 |
| F2 | Leg weights hips-dominated → legs unposeable | `body_rig.py` root→hips fold now gated below the hip joint by a smoothstep (`leg_soft`). `w_root` = "body remainder under the head" had included the legs. | `upper_leg_L` max **0.315 → 1.000**; thigh +35° moves leg mean **0.70 → 2.26 %H**, torso bleed 0.00%H |
| F3 | Voice pick C vs `local-gb10-first` pin | C recorded as the **reference target** the local slot tunes toward, **not** the backend. `tts_target` unchanged; no platform clone created. | pack `[voice].identity_ref`, `work/voice/SAMPLES.md` |

F2 promoted over the frozen alpha; rollback kept at `mesh/canon/body/clyffy_v2_body.bak.blend`
and `clyffy.vrm.bak`. VRM re-exported — humanoid `correctly_assigned=True n=22`, 3 spring
bones intact. `tools/accept.py` **GREEN**.

### Live window — WORKING ITERATION (2026-07-27)

Renderer lives in the **clyffy** repo at `interfaces/clyffy-avatar/` (COSTAR-gated,
`MAP.md` row, roadmap E2). This pack stays the SSOT — assets are symlinked, never copied.

```bash
cd /home/hades/Projects/clyffy/interfaces/clyffy-avatar/renderer && npm run dev
```

Verified live on the GB10 at 60 fps, front-on, mouth articulating, teeth contained:
`peakEnv=0.88 peakJaw=0.79 visemes=aa,O,E` (peakJaw tracks the contract's `aa` jawOpen).

**Fixed at the source — the VRM was never spec-conformant.** `clyffy.vrm` faced
**+55.1° off +Z** (the Blender `FWD 235.1°` authoring yaw was never baked out). Size and
bone-count checks all passed regardless. `tools/vrm_export.py` now yaws by `-FWD`, and the
new **`tools/vrm_check.py`** gate (wired into `accept.py`) measures conformance properly.

| # | Open defect | Impact |
|---|-------------|--------|
| ~~L1~~ | ~~L/R bone names mirrored~~ — **CLOSED 2026-07-27.** `body_rig.py` now defines `SIDE_L, SIDE_R = +1, -1` (`+lat` IS the character's left) and swaps the upstream mirrored eye custom-props at the point of consumption. Labels swapped, **geometry untouched** — nothing upstream of `body_rig` regenerated, so the 43 shapes and jaw rig are unchanged. Verified: all 6 humanoid pairs correctly sided (was 5/6 mirrored); `Σw = 1.000000`; arm-raise displacements traded sides exactly as expected. Promoted; rollback at `clyffy_v2_body.pre-l1.blend` / `clyffy.vrm.pre-l1`. | — |
| ~~L2~~ | ~~`applyState()` unwired~~ — **BUILT 2026-07-27.** clyffyd gained `avatar.rs` + `GET /avatar/state` (SSE) carrying the state half of contract v1; the renderer consumes it and applies the contract's layering (`expression_state` base → `viseme_weights` max-merge → `rest_loop` zeros all). Goggles track real work via a `WorkGuard` that drops on completion **and** on client disconnect. 7 unit tests green, zero warnings. **VERIFIED END-TO-END on the live stack** (operator authorised the restart): renderer `linked` → real `/code` job on the 120B → `thinking`/`lowered` → back to `rest`/`on-face`. Required a CORS header on `/avatar/state` (the face is always cross-origin; the mock had masked it). | — |
| ~~L3~~ | ~~No desktop shell~~ — **DONE 2026-07-28.** Tauri 2 shell at `interfaces/clyffy-avatar/shell`: transparent, frameless, `alwaysOnTop`, `skipTaskbar`, `focus:false`, parked bottom-right from the CURRENT monitor at runtime. Verified composited on the desktop with `_NET_WM_STATE_ABOVE`, 0 GPU errors, and a live SSE link to clyffyd. Excluded from the cargo workspace (Tauri drags ~500 crates). Needed `WEBKIT_DISABLE_DMABUF_RENDERER=1` — now set by the shell itself. | — |
| L4 | Phone / assistant-app surface not built | the second consumer the web stack was chosen for |
| L5 | Unreal adapter not built | operator flagged Epic as likely; the contract seam is in place for it |

**Rule learned:** measure VRM facing from the **eye bones**, never from L/R legs — enforced
in `vrm_check.py`.

### ⚠️ Infra finding — RoCE GID drift (3rd occurrence)

Bringing the ring back after an unrelated crash failed with `NCCL error: unhandled system
error`. Cause was **D38 GID drift**: `NCCL_IB_GID_INDEX=3` must be RoCEv2-IPv4 on every
rail, and four rails across clyffy-01/02 had **null GIDs**. `clyffy-roce-gidfix.service`
repaired them; trio came up in ~400s with **0 QP failures**.

Drift happens during OPERATION, not only at boot, so the boot-time unit does not catch it.
A pre-flight rail check (`ExecStartPre` on `clyffy-trio.service`) or a periodic verify would
turn this from a 20-minute debug into an automatic repair. **Not implemented — operator call.**

## M-phase — MOUTH REBUILD (build plan, authored 2026-07-28)

**Operator go given.** The face is the product (the head is oversized on purpose), so the
mouth gets a proper pass before the phone surface (L4) or Unreal (L5). Phone/Unreal are
delivery surfaces for the SAME renderer + VRM — every mouth fix propagates to them free,
and neither improves the mouth. Order is settled.

### What is ALREADY MEASURED — do not re-derive

⚠️ **M1's two headline numbers were WRONG. Corrected 2026-07-28 (`m2_probe.py`) — the
diagnosis moved with them.** "cavity depth 5.2%H" was the bag HEIGHT; the 0.84%H median
wall was measured over the 248-vert set INCLUDING the 62 rim verts, which sit ON the
exterior and score ~0 by construction.

| finding | number |
|---|---|
| pure cavity verts | **186** |
| cavity **depth** (lip rim → back cap, along `fwd`) | **15.96%H** — three times what M1 recorded |
| cavity width / height | 14.47%H / 5.16%H |
| wall, 186 pure verts, nearest surface | **median 2.61%H** (mandible floor→down 2.44%H) |
| solid head behind / above the bag | 18.99%H / 10.85%H |
| teeth verts | 200 (flat slabs, 1.95%H tall) |
| lower-muzzle exterior verts | 6443, only **34.3%** move at jawOpen=1.0 |

**Root cause (corrected): jaw TRAVEL, not cavity depth.**

```
chin depth, lip line -> jaw-region floor   3.38 %H
jaw drop at the shipped 22 deg             7.41 %H
aperture at 22 deg                         7.69 %H
visible neck below the chin               ~2    %H
```

**The jaw travels more than twice the depth of the chin it carries.** At full open the
lower lip finishes ~4%H below where the chin bottom started, so no chin remains under the
mouth — the aperture eats it, and the swing lands the chin inside the shirt collar. This is
a proportion failure. Deepening the cavity would have been wasted work.

Weights cannot fix it — now measured rather than asserted. `m2_ceiling.py` builds the map
an ideal hand-painting would give (3263 rigid / 5487 moving verts, 3× the shipped solve) and
the chin still lands at z 0.1346, dragging the throat into the shirt.

### Where it breaks — fine angle ladder (`work/m2_ladder/_ladder_front.jpg`)

`jaw_rig.py` only ever rendered 0/50/100% of 22°, so the failure point between them had
never been looked at. 0–9° parting · **12–15° reads as a mouth** · 18° chin nearly
consumed · 22° rectangular hole.

**The geometry already supports a good-looking talking mouth; it is being driven ~60% past
what it can absorb.** One value sets that: `ENVELOPE.jaw.max_deg = 22.0` in
`tools/control_surface.py`.

### ⚠️ `wmap_*.png` has been BLIND the whole time
`jaw_rig.py` writes a `jawmap` colour attribute, then renders Workbench
`color_type='VERTEX'` — but never makes the attribute active. Every weight map it has ever
produced is flat grey. Every weight judgment to date was made without seeing the map.

### Negative results — do NOT repeat these
* **`FLOOR_DROP` (lowering the w=0 anchor) does nothing.** verts>0.01 3673→5818 but rigid
  core stayed 998 and mean weight FELL 0.540→0.441. Moving a zero-boundary only lengthens
  the gradient. Parameter exists in `jaw_rig.py` argv[8], default 0.030 = old behaviour.
* **`CORE_DROP` works numerically but not visually.** Anchoring the chin INTO the rigid core
  took lower-muzzle coverage 34.3% → **61.9%** (throat bleed 0.4%, `along > BAND` keeps the
  neck out). Renders front + 3/4 are near-identical. Keep it — it is a real improvement —
  but it is NOT the fix. `jaw_rig.py` argv[9], default 0.0 = old behaviour.

### ⛔ THE COLLAR IS THE BINDING CONSTRAINT (settled 2026-07-28 — do not relitigate)

There is **no separate shirt mesh**. The navy t-shirt is texture on the one continuous body
surface, so displacing geometry under it drags the collar. Sampled from the base-colour
image, the midline collar sits at **z +0.1377 = 9.00%H below the lip line** — the entire
budget for chin *and* neck.

With chin depth `D` and jaw drop `d`, at full open the visible chin is `D` and the chin
underside is `D + d`, which must stay above the collar:

```
    d < 9.0 %H - D
```

**Growing the chin trades against gape one-for-one.** D=4.5%H (as shipped) → d ≤ 4.5%H
(~13°). D=7%H → d ≤ 2%H (~6°). The chin is already at the optimum of `min(D, 9−D)`.
**No chin geometry makes 22° work.** The only change that raises this ceiling is moving the
collar DOWN — a far larger canon change than the chin, and not taken.

Finding the collar: scan **down** from the lip for the first band that turns navy. Do NOT
use `max(navy z)` — the lanyard is blue too and reports z +0.3527, above the mouth.

### Build order

| # | stage | goal | gate |
|---|-------|------|------|
| ~~M2~~ | `chin_mass.py` | **DONE 2026-07-28, promoted.** New stage after `mouth_open`; grows a mandible as a smooth DISPLACEMENT FIELD — no new geometry, vertex indices preserved (`body_rig` transfers by index and asserts equal counts). Rigid jaw core **742 → 1316**, mean jaw weight 0.506 → 0.601, edge stretch max 2.92×. Contract capped: `ENVELOPE.jaw.max_deg` **22.0 → 13.0**. | `accept.py` GREEN · `vrm_check.py` GREEN · Σw = 1.000000 exact, ≤4 influences |
| M3 | `mouth_parts.py` | Rebuild teeth as ARCS fitting the new cavity (currently 200-vert flat slabs that float at full open) | jawOpen ladder 0.35/0.70/1.00 shows teeth seated |
| M4 | `jaw_rig.py` | Re-run with **`CORE_DROP 0.05`** folded in | lower-muzzle coverage ≥60%, throat bleed ≤1% |
| M5 | VISEMES table | Wire the **20 unused mouth morphs** — `mouthRollLower/Upper` (makes FF/PP read), `mouthPress*`, `mouthStretch*`, `jawForward`. Table drives 10 of 30 available. | viseme sheet shows distinct lip shapes |
| M6 | full chain | `parts → lip_seal → atlas → shapes → jaw_rig → body_rig → vrm_export` | `accept.py` GREEN + `vrm_check.py` GREEN |
| M7 | talking demo | re-render vs `work/talk_v2/alpha_talk.mp4` | operator A/B |

### Commands (verified working)

```bash
# stage under test
blender -b --python tools/jaw_rig.py -- mesh/canon/clyffy_v2_parts.blend <out> 235.1 \
        22.0 0.75 0.30 0.020 0 <FLOOR_DROP> <CORE_DROP>
blender -b --python tools/body_rig.py -- mesh/canon/shapes/clyffy_v2_shapes.blend \
        <rig.blend> <out> 235.1
blender -b --python tools/vrm_export.py -- <body.blend> <out.vrm> 235.1
# talking demo (text-driven lipsync)
blender -b --python tools/avatar_drive.py -- <body.blend> <out> 235.1 <audio.wav> --text "..."
# gates
python3 tools/accept.py && python3 tools/vrm_check.py
```

### Rules that already bit us — carry them forward
* Measure bilateral things on **`lat`**, never world X (235.1° transform makes X silently wrong).
* Measure VRM facing from the **eye bones**, never L/R legs (they were mirrored — L1).
* `body_rig` transfers jaw/skull/root **by vertex index** and asserts equal counts, so
  `shapes.blend` and `rig.blend` must both descend from the same `parts.blend`.
* Warnings are signal. Two `dead_code` warnings in clyffyd were both real incomplete work.
* Kill ALL chromium windows before capturing — stale ones served old builds three times.

### Promotion state (2026-07-28)

**M2 IS PROMOTED.** Full chain rebuilt through `chin_mass → eye_open → mouth_parts →
lip_seal → face_atlas → shape_author → jaw_rig(13°) → body_rig → vrm_export`, staged in
`work/m6/` and copied into `mesh/canon/` only after the gates passed. Heroes and the viseme
sheet re-rendered (geometry changed, so the old ones were stale).

Rollbacks: every promoted artifact has a `.pre-m2` sibling — `clyffy_v2_{eyes,parts,atlas,
rig}.blend`, `shapes/clyffy_v2_shapes.blend`, `body/clyffy_v2_{body,vrm}.blend`,
`body/clyffy.vrm`. Older rollbacks kept: `.bak` (pre-F2), `.pre-l1` (pre-L1).

M1 candidates in `work/m1_fd*`, `work/m1_cd*`; M2 evidence in `work/m2_*`; the A/B talking
demo in `work/_m7_ab.mp4`.

⚠️ **`vrm_export.py` SEGFAULTS ON EXIT** ("Found 4 unreleased ID's", Blender teardown) —
*after* the VRM is fully written. The file is complete and passes `vrm_check`. Any script
driving the chain must check for the OUTPUT FILE, not the exit status; `set -e` will
otherwise abort a chain that actually succeeded.

## Alpha complete (do not rebuild unless breaking)

| Artifact | Path |
|----------|------|
| Body rig + shapes | `mesh/canon/body/clyffy_v2_body.blend` |
| VRM 1.0 + springs | `mesh/canon/body/clyffy.vrm` |
| Control schema | `mesh/canon/body/control/control_surface.schema.json` |
| Expression heroes | `mesh/canon/body/present/hero_*.png` · `_herosheet.jpg` |
| Drive demo | `mesh/canon/body/drive/` |

Pipeline stages (see pack `[pipeline]`): canon → open → eyes → parts → lip_seal → atlas → shapes → jaw_rig → body → VRM → control → drive → present.

## Deferred (explicitly out of v0.1)

- Per-finger hands  
- Goggle prop mesh (goggle_state logged only)  
- ASR / phoneme lipsync (envelope + Oculus visemes only)  
- Live VRM companion window  
- Roadmap E2 Avatar mode (clyffy product)  
- Platform voice clone of `voice:VOICE-CORPUS (redacted)` (local TTS first)

## Voice creation checklist (after G1–G7)

1. Confirm `tools/accept.py` exit 0.  
2. Optional: pull reference `work/voice/clyffy-blend1-voice.mp3` from Drive.  
3. Synthesize / design samples on GB10 via **`voice.tts` slot** (no hardcoded model name).  
4. Use pack `[voice].sample_lines` as minimum line set.  
5. Export **wav mono 24k or 48k**.  
6. For each sample:  
   `blender -b --python tools/avatar_drive.py -- mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/drive 235.1 sample.wav`  
7. Review mouth motion + rest hold; retune `VISEMES` only if the muzzle fails.  
8. Platform clone only on explicit operator go.

## Rest-state law

Every drive ends in rest (loop or freeze). Rumination is a rest pool, not a spinner.
