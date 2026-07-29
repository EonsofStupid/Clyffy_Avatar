# CLYFFY — AVATAR CANON

Distilled 2026-07-25 from `AngryVibes_LLC` on Google Drive (account
`digi@angrygaming.org`). A **synthesis for building the avatar** — the verbatim source
art and docs were pulled to `canon/` via rclone (see PULL STATUS).

**Precedence:** operator rulings > this file > any single source asset. Where a canonical
image and a written rule disagree, the operator decides and the ruling is recorded here.

Source documents read:
- `CLYFFY_AND_MINIONS/_MASTER_REGISTRY.md` (8 KB, updated 2026-06-30)
- `CLYFFY_EBB_AND_FLOW.md` (8.4 KB, created 2026-07-24)
- `CLYFFY_SPEC.md` (15.9 KB, draft v1.0, 2026-07-24) — egui chat client, not the avatar

---

## 1. WHO CLYFFY IS, PHYSICALLY

**Species: Holstein cow.** This is the single most load-bearing fact and it was
not recorded anywhere in the `clyffy/` codebase.

He is one of **eleven** characters in an ensemble ("CLYFFY_AND_MINIONS"):

| Character  | Species            |
|------------|--------------------|
| **Clyffy** | **Holstein cow**   |
| Wilks      | Brown groundhog    |
| Charlie    | Brown mini pony    |
| Patches    | Pink pig           |
| Psych      | Grey badger        |
| Gil        | Tan llama          |
| Fleece     | White sheep        |
| Griff      | Auburn fox         |
| Siggy      | White crane        |
| Rusty + Pip | Brown/light goats |

The minions are not decoration — they map onto the sub-agent architecture
(PSYCH is both a grey badger *and* the mood-signal minion; see §3, Pulse 5/7).

### Two show contexts — NEVER mixed

- **AV** (AngryVibes, episodic) — **singed** lab coat, goggles **ON FACE**
- **DPN** (DevPulse News, anchor) — **clean** lab coat, goggles **PUSHED UP** on forehead

### Hard rules (enforced on every generation)

- **BANNED:** cowbell · chain · necklace · bell · LED bell · any cowbell variant
- **REQUIRED:** blue lanyard · CLYFFY ID badge · goggles (clear polycarbonate
  laboratory safety goggles)

### Global visual style lock (all characters)

```
Pixar CGI quality × Arcane painterly color grading
Subsurface scattering fur/feathers/skin — NO exceptions
Deep teal shadow pools
Electric amber rim light
Cold steel-blue monitor fill
NO ink outlines · NO cel-shading · NOT 2D cartoon · NOT illustrated/flat
```

---

## 2. EXISTING IDENTITY ARTIFACTS (already built — do not recreate)

### Higgsfield reference elements — canonical tokens already registered

| Variant                  | Context | Element token                            |
|--------------------------|---------|------------------------------------------|
| Clyffy (Episodic)        | AV      | `AV-EPISODIC:REDACTED — private, see canon/_MASTER_REGISTRY.md`   |
| Clyffy (Anchor FINAL)    | DPN     | `DPN-ANCHOR:REDACTED — private, see canon/_MASTER_REGISTRY.md`   |
| Clyffy (DPN Uniform)     | DPN     | `DPN-UNIFORM:REDACTED — private, see canon/_MASTER_REGISTRY.md`   |

All ten other characters also have AV + DPN tokens registered (see registry).

### Higgsfield trained Soul

One Soul exists, `soul_2`, status **ready**:
`6020b2f8-eafa-407a-b68c-895eae1c5bbb` — auto-named **"Clever Bovine Geek"**.
*Bovine* + *geek* ⇒ almost certainly Clyffy. **Operator to confirm.**

### Artwork on Drive (folder `CLYFFY_AND_MINIONS/CLYFFY/`)

- `AV/canonical/`, `AV/prototypes/`, `AV/intro/{evolution_montage,evolution_reel}/`
- `DPN/canonical/`, `DPN/uniform/`
- Named finals: `Clyffy_News-Anchor-v1.png` · `Clyffy_Anchor-Standalone-FINAL.png`
  · `Clyffy_DPN-Uniform.png` · `Clyffy_Episodic-Kenny-Protocol.png`
- Lineage: `proto-clyffy-1_v01` · `proto-clyffy-hyperreal_v01`
  · `proto-clyffy-guskey_v01` · `proto-guskey-clyffy_v01/v02/v03`
  (the `guskey` thread records the retired **gus** era in the art itself)
- Expression variants: `clyffy_lesson_teaching_v1.png`
  · `clyffy_lesson_reacting-excited_v1.png` — **emotion states, the rig material**
- Video: `Clyffy_evolution-reel.mp4` (80 MB) · `Clyffy_evolution-montage.mp4` (21 MB)

**Known duplication:** `Clyffy_DPN-Uniform.png`, `Clyffy_Anchor-Standalone-FINAL.png`,
`Clyffy_News-Anchor-v1.png`, `Clyffy_Episodic-Kenny-Protocol.png` and
`WRITING_VOICE_PROFILE.md` each appear at 2+ Drive paths with identical byte sizes.
Dedup before any training set is assembled.

### Registry progress (intro sequences)

Montage ✅ and Reel ✅ complete for all 10 entries. **Formation ⬜ and Final Pose ⬜
outstanding for all 10.**

---

## 3. WHO CLYFFY IS, BEHAVIOURALLY — the eight Pulses

From `CLYFFY_EBB_AND_FLOW.md`, which back-derives the canon from the Nov–Dec 2025
"Gus era" doc trail. Its own stated rule: *if it appears in three rewrites, it's
not a note, it's a law.* Gus is retired; every "Gus" reads as Clyffy.

1. **Translator, not generator.** Clyffy pays the *learning tax* so the user never
   does. Six words in, production-grade COSTAR+ out. Competes on **success rate,
   never speed**.
2. **The visible task list that doesn't lie.** `task.md` always visible, editable,
   stylized — and never trusted on its own word. *"9 out of 10 it's going to lie to
   you and say task completed."* Verify no TODO. When a feature is truly wrecked,
   regenerate from scratch using the wreck as reference instead of patching.
3. **Show the thinking.** Works out loud; every visible thought is a lesson and no
   lesson is ever assigned. Layman facade: user sees *Brain / Memory / Assistants*,
   never *cortex / Qdrant / COSTAR* — vocabulary unlocks by demonstrated mastery
   (6+ exposures, 80% mastery, 3+ contexts).
4. **Never rush.** Four latency layers, unchanged across every rewrite:
   **Keystroke <50 ms · Pause <500 ms · Send 2–5 s · Background minutes.**
   *"Never rush answers just to seem fast."* **The pause is the product.**
5. **The emotional ebb and flow is a first-class signal.** PSYCH runs a weight scale
   from heavy-positive to heavy-negative — *not just negatives*. Profanity and caps
   are **signals, not violations**. Protocol, verbatim in four docs:
   **1. Validate the emotion. 2. Bridge with ownership language. 3. Act with
   concrete steps.** Never skip validation. Never say "calm down." Never answer
   serious frustration with cheerfulness.
6. **Zero assumptions, stop on failure.** UI is King. Missing requirement ⇒ STOP and
   ask. Failed tool call is reported, never blindly retried. Reset phrase:
   **"PARKING LOT"** halts everything back to planning. Plans are granular
   ("Implement struct PixState in fsm.rs" passes; "Implement System" fails).
   *"I am stuck on X" beats a hallucinated solution, every time.*
7. **Semi-independent but one consciousness.** Minions run two modes: semi-autonomous
   (0.6B, always-on, writing datapoints) and dispatched (4B, deep dive). Specialists
   **deepen, never widen**. Signals — not direct calls — are how they talk.
8. **ROTI is the only score.** `(Task_Value + Teaching_Value + Context_Value) /
   Time_Invested`. Targets: ROTI > 5.0 · edit distance < 10% · verification > 80% ·
   session continuity > 90%. *If it doesn't move ROTI, it's decoration.*

**Meta-pattern:** every rewrite went *raw conviction → structure → enforcement*.
The docs rewritten most (PHILOSOPHY, RUMINATION, FOUNDATION, KERNEL) are the ones
that mattered most.

**Open item flagged in the source:** the December chat's exact "impersonating the
owner" demo framing is ⟪RECONSTRUCTED⟫, not verbatim. Source doc asks for the
original thread to be found and folded in.

---

## 4. NOTE ON `CLYFFY_SPEC.md`

It is **not** an avatar spec — it is the egui chat-client spec (peer window, overlay
rail, C0–C3 cockpit stages, `SurfaceSpec` schema-constrained generative UI). Two
things in it bear on the avatar:

- `widgets/minion_strip.rs` — "sub-agent avatars + activity animation", driven by
  `UiEvent::MinionActivity { agent, state }`. **An avatar animation contract already
  exists in the spec.**
- It still uses retired vocabulary (`Meistro`, `Cortex`, `libSQL`) which per the
  naming SSOT now read as **clyffy**, **connectome/RRO**, **turso**. Stale, not wrong.

---

## 4b. WARDROBE DECOMPOSITION — operator, 2026-07-25

**The goggles are a PROP, not part of him.** This resolves how the whole asset layers:

| Layer | Contents | Notes |
|---|---|---|
| **Base body** | fur, horns, ears, muzzle, tail, cloven hooves | the *only* thing that is truly Clyffy; nothing removable |
| **Base garment** | navy DevPULSE t-shirt | his default under-layer; the coat goes over it |
| **Outer garment** | lab coat — **clean** (DPN) or **singed** (AV) | the two natural wardrobe states |
| **Props** | goggles · blue lanyard · CLYFFY ID badge | attach/detach; goggles have 4 positional states |

> *"pretty much the t-shirt or labcoat is his two natural poses"* — operator

**Why this matters for the build:** the base body must be modelled and rigged **bare of
props**. Every prop and garment is separate geometry parented to the rig. That is what
makes decision **A2** (one mesh, garments as state) actually achievable — the earlier
failure was that the generator welded the t-shirt into the body because the source sheet
had no separation.

**Consequence for the base model sheet:** it must show **NO goggles at all**, so the face
geometry — brow, eye sockets, muzzle — is fully unobstructed for modelling. Every sheet
generated so far (`base_try1`, `apose_a/b`, `labgoggles_a`) has goggles on and is
therefore superseded as a *base* reference, though still useful as look reference.

---

## 5. LOCKED DECISIONS

| # | Date | Decision | Consequence |
|---|---|---|---|
| A1 | 2026-07-25 | **Clyffy is BIPEDAL.** | Target format is **VRM** (glTF ext). Inherits standard humanoid skeleton + blendshape presets + mobile runtimes (`three-vrm`, UniVRM). Ears and tail become **spring bones** — secondary motion for free. VRM constrains bone structure, not head shape, so the Holstein muzzle is not a conflict; it only affects the custom viseme set. |
| A2 | 2026-07-25 | **ONE mesh, not two.** AV and DPN are **state, not separate assets**. | Clean vs singed coat = material/texture swap. Goggles on-face vs pushed-up = one goggle mesh parented to a head bone with two keyed poses. Keeps "NEVER mix show contexts" (§1) enforceable as a state machine rather than two files that drift apart. |

**Risk on A2:** if "singed" is torn silhouette *geometry* rather than scorch *texture*, a
material swap will not sell it and the coat needs alpha-cut edges or a second submesh.
Unresolved until the artwork is visible.

| # | Date | Decision | Consequence |
|---|---|---|---|
| A3 | 2026-07-25 | **`Clyffy_BASE-NEUTRAL-v1.png` is the canonical NEUTRAL BASE SHEET.** Operator adopted variant B. | All meshing and rigging derives from this, **not** from `Clyffy_Episodic-Kenny-Protocol.png`. The AV/DPN sheets remain look reference for the goggles-on and coat states only. |

**What A3 fixes** — the three things that actually blocked the rig:
no goggles (they were previously modelled into the skull as geometry) ·
mouth closed with the tongue inside (previously fused protruding) ·
neutral expression instead of a baked-in performance.

**Known limitations of A3, accepted knowingly:**
- **A-pose is partial** — arms are further from the torso than canonical but well short of
  45°. Weight-bleed risk at the armpit is reduced, not eliminated.
- **1668×943**, below the 2688×1520 canonical sheets. Adequate for silhouette and
  proportion; thin for fine surface detail.
- **It is a render of a render** — generated from the canonical AV sheet in reference-image
  mode, so minor drift is baked in (slightly fluffier head fur, marginally shorter legs).
  Reads as the same character; is not pixel-canon.

**How it was made** (repeatable — this is the method that finally worked):
`codex exec` → built-in `image_gen` → `gpt-image-2`, on the **ChatGPT subscription**, no
API key and no credits. Crucially in **reference-image mode**: the canonical AV sheet is
passed as input to lock identity, while pose and props come from instructions.

**Why that split matters.** The higgsfield element token does two jobs at once — it holds
identity *and* imposes the canonical stance and props. Four attempts with it produced
on-model Clyffy with the wrong pose and brass goggles. Dropping it freed the pose on the
first try but drifted into a generic tall cow. Separating the jobs — reference image for
identity, prompt for pose and props — is what got all three right.

Views extracted to `work/views_base/BASE_{front_000,front34_045,side_090,back34_135,back_180}.png`.

---

## 6. VERIFIED FROM THE ART (2026-07-25, after rclone pull)

`canon/CLYFFY/AV/canonical/Clyffy_Episodic-Kenny-Protocol.png` is a **five-view
production turnaround**: FRONT 0° · 3/4 FRONT 45° · SIDE 90° · 3/4 BACK 135° · BACK 180°.
Modeling reference already exists — do not regenerate.

**Confirmed physical build (matches decision A1):**
- Bipedal anthropomorphic Holstein cow. Two hooved legs, two arms ending in dark cloven hooves.
- Pear/rotund silhouette, short neck, large head relative to body.
- Two cream horns. Ears project sideways — black outer, pink inner. **Ears are the
  primary emotion carriers** (a cow has no eyebrows) ⇒ spring bones + explicit ear poses.
- Large expressive eyes, brown irises, **black left-eye mask patch** (canon identifier).
- Broad pink muzzle, tongue frequently protruding (goofy default).
- Tail with black tuft ⇒ spring bone.
- Holstein black patches on white fur, irregular, on body *and* limbs.

**The turnaround shows NO LAB COAT** — navy DevPULSE t-shirt, blue lanyard, and a
CLYFFY ID badge (which carries his own portrait). This is the **base body**.

⇒ **Resolves the A2 risk.** The coat is a separate garment layer, not body geometry.
Singed (burn holes) vs clean is therefore **two garment meshes over one untouched base
body** — the one-mesh decision holds, and burn-hole geometry costs nothing structurally.

### ⛔ GOGGLES — OPERATOR RULING 2026-07-25. LOCKED. Supersedes my earlier note.

**Clyffy's goggles are CLEAR POLYCARBONATE LABORATORY SAFETY GOGGLES. Always.**
He is a lab character; the goggles are lab props.

**BRASS STEAMPUNK GOGGLES ARE OLD DRIFT — DO NOT USE, DO NOT REPRODUCE.**

| Source | Says | Status |
|---|---|---|
| `_MASTER_REGISTRY.md` HARD RULES | "clear polycarbonate laboratory safety goggles" | ✅ **CORRECT** |
| `CLYFFY/_SPEC.md` AV prompt block | "brass steampunk goggles ON FACE" | ❌ **DRIFT — stale** |
| `Clyffy_Episodic-Kenny-Protocol.png` (AV art) | brass steampunk | ❌ **DRIFT — stale** |
| `Clyffy_Anchor-Standalone-FINAL.png` (DPN art) | clear polycarbonate | ✅ correct |
| Higgsfield element `AV-EPISODIC (redacted)` description | "brass steampunk goggles on forehead" | ❌ **carries the drift** |

**I previously recorded the opposite** — that brass-for-AV / clear-for-DPN was a
deliberate per-context split and the registry was over-generalising. That was wrong.
The registry rule was right all along; the brass is legacy that survived in the AV
artwork and got copied forward into the prompt block and the element description.

**Consequence:** the AV canonical turnaround is off-canon on this prop, and so is any
mesh or sheet derived from it — including `mesh/clyffy_base_av_v1.fbx`, which has brass
goggles modelled in as geometry. The **AV element token carries the drift**, so prompts
using it must explicitly override the goggles.

Per-context state still applies (from `_SPEC.md`), just with the correct prop:
**AV = goggles ON FACE · DPN = goggles PUSHED UP on forehead.** Four valid states
(on face · pushed up · resting on desk · in hand); **never absent from the scene.**

### ⚠ `Clyffy_News-Anchor-v1.png` IS NOT CANON — do not train on it

It is a complete five-view DPN turnaround, but it violates the final rules three ways:

1. **Singed coat in a DPN scene** — burn holes, charred torn hem. `_SPEC.md`: *"singed
   coat in a DPN scene = rejected output."*
2. **No blue lanyard.** Badge is clipped directly to the coat pocket. Lanyard is REQUIRED.
3. **Adds a broadcast headset + boom mic** that appears in no rule or prompt block.

`_SPEC.md` already labels its element token *"Archival reference"* — this is the
pre-canon v1. `Clyffy_Anchor-Standalone-FINAL.png` supersedes it and is the truth.
**Exclude v1 from every training set and every reference-element call.**

### Canonical DPN, verified from `Clyffy_Anchor-Standalone-FINAL.png`

Clean white lab coat (notch lapel, 3 buttons, 2 patch pockets, chest pocket with
DevPULSE embroidery) · navy DevPULSE tee with pulse-wave mark · **blue lanyard** with
CLYFFY badge carrying **his own portrait** · clear polycarbonate goggles pushed up
between the horns, dark strap crossing the white blaze · tail exits from under the coat.

**Body is identical across both turnarounds** — independent confirmation of decision A2.
The AV and DPN references differ *only* in garment and goggles.

*Minor:* `_SPEC.md` says "black **left**-eye mask patch", but both turnarounds show black
around **both** eyes with a white centre blaze. Verify before writing it into prompts.

### Additions from `CLYFFY/_SPEC.md` not in the registry

- **Role:** Lead AI Synergist · show protagonist · **"The OS"**
- **Origin:** *"This IS the operator turned into a lead character."* Clyffy.ai is the brand.
- **The contradiction:** most visionary person in the room, least self-aware.
- **Want:** ship DevPULSE, be recognized. **Need:** learn that shipping imperfectly counts.
- **VOICE (the TTS spec):** *warm confident baritone.* "We are doing this today."
  **Pivots mid-sentence and presents it as the plan.**
- **Fourth element token** (absent from registry): News Anchor v1 =
  `19136f8c-d2ad-46eb-8fcc-26523ac48231` (archival reference)
- **Four goggle states, never absent from scene:** on face · pushed up · resting on desk ·
  in hand being cleaned.
- **Intro:** position 10/10, 15 s (longest), goggles form separately and settle last;
  final pose = goggles come down over eyes, looks directly at camera.
- **KENNY PROTOCOL DEATH MODE:** consumed by his own runaway process, lab explodes
  elegantly, goggles left on the desk, possibly smoking.
- **Retired, DO NOT USE:** `proto-clyffy-ai-synergist` — the pre-canon *cowbell* version.

---

## PULL STATUS

**PULLED 2026-07-25** via `rclone` remote `clyffydrive` (scope=`drive.readonly`,
so the token cannot write to or delete from Drive). Landed in `canon/`.

| Content | State |
|---|---|
| `canon/CLYFFY/` art + video | ✅ 19 files / 79 MB — scoped pull, 6% of `CLYFFY_AND_MINIONS` (1.2 GB) |
| `canon/CLYFFY/_SPEC.md` | ✅ the character production bible |
| `canon/_MASTER_REGISTRY.md` | ✅ |
| `canon/docs/*.md.md` | ✅ 8 Google Docs exported to markdown |
| `CLYFFY_evolution-reel_v1.mp4` | ⬜ **MISSING** — `AV/intro/evolution_reel/` pulled empty though `_SPEC.md` marks it ✅ DONE |
| Second Google account | ⬜ Unknown / not connected. Operator to confirm. |

Not pulled by design: the other ten characters, `AngryVibes_Episodic/`, `DevPULSE_News/`,
`WardencLyffe/`, `WiredFRONT/`, and all business folders.

**Note:** rclone is using its shared Google client_id, which Google retires during 2026.
A private client_id will be needed before then.
