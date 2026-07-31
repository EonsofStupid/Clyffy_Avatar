# MOUTH REFERENCE — and a correction about how it was used

## ⛔ READ THIS FIRST — THESE FRAMES ARE NOT THE COLOUR REFERENCE

The files in this folder are **video frames**, kept for STRUCTURE and MOTION only.
**Do not take colour off them.** The colour reference is:

| role | file |
|---|---|
| **PRIMARY (albedo)** | `canon/base_sheet/Clyffy_BASE-NEUTRAL-v1.png` — 5-view turnaround, NEUTRAL lighting |
| **CROSS-CHECK** | `canon/CLYFFY/DPN/Clyffy_Anchor-Standalone-FINAL.png` — canonical DPN art |

Measure with `tools/_refcolor.py`. Authored into the mesh by `tools/materials.py`.

### Why — this cost a full build cycle

The frames here are graded, and `v1_48a464a0_t4.png` is a blue night scene where **white fur
measures sRGB (113,160,217)**. On top of that, the image display path auto-levels every frame it
renders, so a crop of the muzzle *displays* as bright pink while the pixels say (120,101,137) —
blue-dominant mauve, confirmed by two independent decoders. **Colour here cannot be judged by
looking.**

Worse than the grading: the samples taken off these frames landed on **shaded** muzzle, which was
then used as the albedo of the whole pad.

| source | Y_pad/Y_fur | chroma R:G:B |
|---|---|---|
| canon base sheet, lit pad | 0.80 – 0.89 | 1.31 : 0.92 : 0.83 |
| canon anchor art, lit pad | 0.63 – 0.70 | 1.41 – 1.50 : 0.88 : 0.74 |
| **what these frames gave** | **0.496** | **1.76 : 0.81 : 0.66** |
| canon anchor art, **shaded underside** | 0.373 | **1.76 : 0.81 : 0.62** |

The built value is a dead match for the *shaded underside*. Result: ~40% too dark and ~35% too
saturated — an orange rubber pad instead of a soft pink muzzle.

**Rule: albedo comes from a NEUTRALLY LIT reference. Graded frames are for structure and mood.**

## ⛔ THERE ARE NO LIP BANDS. THE MOUTH IS A SLIT IN THE PAD.

An earlier version of this file claimed:

> *"Three concentric bands, inside to out: salmon-pink inner lip rim → cream/white outer lip band
> → white fur"*

**That was wrong and it is deleted.** It describes a HUMAN vermilion border. It is on neither
canon source. It was never measured — it was written as prose off the low-resolution 4-panel
plate, and then colour was measured *rigorously in service of it*. Measuring carefully does not
make the target correct.

Operator, on seeing the render it produced: **"stop trying to human mouth this."**

What both canon sources actually show: **one continuous muzzle pad, with the mouth cut into it.**
The lips are the pad continuing. The dark lip line is geometry and occlusion, not paint.

## What these frames ARE good for

| file | shows | supplied by |
|---|---|---|
| `v1_48a464a0_t4.png` | extreme muzzle closeup — **pore stipple**, fur feathering over the pad edge, lip crease | operator video |
| `v2_7dca9cea_t4.png` | mouth wide open — interior, dentition, aperture shape | operator video |
| `v2_7dca9cea_t3.png` | open smile | operator video |
| `v2_7dca9cea_t2.png` | closed smile | operator video |
| `MOUTH_TARGET.jpg` · `INTERIOR_TARGET.jpg` · `_ref_grid.jpg` · `_v2_contact.jpg` | working plates I composed from the above | derived |

Structural facts read off them that DID hold up:

1. **The upper cavity reads near-black** — it measures (1,0,0) in `v2_..._t4`. (An earlier note
   called it "warm maroon"; the maroon is the tongue and inner lip tissue.)
2. **The teeth are a continuous cream pad and arch**, with canine nubs only at the corners — cows
   have no upper incisors. Measured: upper canine (176,158,130) and dental pad (170,151,125) are
   **the same colour**, which is why it reads as one ridge rather than as teeth.
3. The tongue is a large dome with a midline groove, **matte with an SSS glow, not glossy**.
4. Open-wide shape is a **wide flat crescent**, not a round hole.
5. The muzzle pad carries **visible pores** and the fur **feathers over its edge** — still TODO;
   the current build has a smooth airbrushed pad boundary.

### ⚠️ Two traps in these clips

- **Goggles:** they show **brass steampunk**. Canon is **clear polycarbonate laboratory safety
  goggles** (`_SPEC.md`, operator ruling 2026-07-25). Known drift baked into the AV art. Take
  MOUTH cues only.
- **Grading:** see the top of this file. Structure and motion, never colour.

## The canon law this is measured against (`CANON.md` §1)

```
Pixar CGI quality × Arcane painterly color grading
Subsurface scattering fur/feathers/skin — NO exceptions
Deep teal shadow pools · Electric amber rim light · Cold steel-blue monitor fill
NO ink outlines · NO cel-shading · NOT 2D cartoon · NOT illustrated/flat
```
