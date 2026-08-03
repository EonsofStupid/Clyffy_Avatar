# FACE REFERENCE — the head, aligned to the operator's clip

Operator, 2026-08-01: *"lets first get the head right … the whole point is getting the face
actually built and aligned to my references i just provided clean back background and the
proper face"*

| file | what |
|---|---|
| `FACE_REF_front.png` | frame 20 of `6f675283` — most front-on clean frame, whole head, no steam or hands |
| `FACE_REF_threequarter.png` | frame 60 — same character, 3/4 |

Chosen from the 192-frame continuous take by silhouette left/right symmetry, then confirmed by
eye. Source clip is ONE character on pure black, which is why it is the reference: there is no
other character or scene element to mistake it for.

## MEASURED DELTA — head patch colour

Sampled from our BAKED ATLAS (no lighting in the way) against the reference frame, both as a
ratio of the dark patch to the white fur so the comparison survives lighting:

| | patch/fur luminance | chroma R:G:B |
|---|---|---|
| **reference** | **0.036** | **1.47 : 0.86 : 1.00** — warm, red-shifted = BROWN |
| **ours** | 0.126 | 0.99 : 1.00 : 0.99 — dead neutral = GREY |

**Ours is 3.5× too LIGHT and has no warmth at all.** The reference's Holstein patches are a dark
chocolate brown; ours are a mid grey. This is the single most visible mismatch on the head and it
is pure colour — no geometry involved.

## NOT YET MEASURED CLEANLY

* **Muzzle prominence.** Visibly flatter and less bulbous than the reference, but an automatic
  pink detector fails here: the reference's BROWN FUR passes a "warm" test, so the muzzle mask
  covered the whole head (top 0.03 to bottom 0.99 of head height). Needs landmarks read by eye,
  not a detector — the same lesson as `work/ref_motion/REFERENCE_SHEET.md`.
* **Head aspect.** Ours reads taller-for-its-width, but the reference and our render were cut at
  different places, so the numbers are not comparable yet. Define the head consistently (horn tips
  to chin) before quoting a ratio.
