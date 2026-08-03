# GENERATED MODELLING REFERENCE — the views the build was missing

Generated 2026-08-03 on higgsfield at the operator's instruction, from the canonical element
`Clyffy-—-Anchor-Standalone-FINAL` (`5b967335-…`) so the character is the same one, not a
lookalike.

| file | what it gives the build |
|---|---|
| `HEAD_turnaround_closed.png` | front / 3-4 / near-profile, mouth closed, flat even light |
| `HEAD_turnaround_open.png` | the same three views MOUTH WIDE OPEN — cavity, dental pad, arch, tongue |
| `MUZZLE_profile_closeup.png` | the snout in profile: projection, lip curve, nostril, chin |

## WHY THESE AND NOT MORE FRONT SHOTS

Every measurement in this project until now was taken **front-on**, and every proportion failure
— how far the snout projects, how long the head is, the lip line's curve, the chin — is a
**profile** problem. A front view cannot show any of them. `canon/base_sheet/` has had a side
view all along and it was never used; that is the single biggest process miss of the build.

## WHAT THEY ALREADY SETTLE

1. **The snout projects forward and is ROUNDED, and the lip line curves back from it.**
   `MUZZLE_profile_closeup.png` shows the pad standing proud of the fur with a soft roll into the
   lip and a defined lower lip beneath. Our current pad is close to flat.
2. **The teeth are a CONTINUOUS cream band, upper and lower.** `HEAD_turnaround_open.png` shows an
   unbroken dental pad above and an unbroken arch below — no per-tooth separation. This is the
   third independent confirmation that the 2026-07-28 scallop (`TEETH_N = 7`, `TEETH_CUT = 0.34`)
   is wrong against canon.
3. **The open mouth is a large rounded aperture**, not a slit, and the tongue is a big pink mass
   filling the floor of it.
4. **The cavity is dark but not black**, and the tongue reads clearly inside it.

## HOW THEY WERE SHOT, AND WHY IT MATTERS

Flat even neutral lighting, plain light grey seamless background, no rim light and no colour
grade — requested explicitly. The operator's earlier clips were dim and blue-graded, which cost a
full build cycle: shadowed muzzle was measured as albedo and the result came out 40% too dark and
35% too saturated. Reference shot for measurement has to be lit for measurement.

## KNOWN LIMITS OF THESE IMAGES

* The third view in both turnarounds is roughly **60-70 degrees, not a true 90 degree profile**.
  Good enough for the muzzle's projection; a true orthographic side would be better.
* Generated at **1k** (1376x768). Fine for proportion and structure; a 2k/4k pass would help for
  pore and lip detail.
* These are **black-and-white Holstein**, per `canon/CLYFFY/_SPEC.md` and the canonical element.
  The operator's recent clip `6f675283` is **brown-and-white**. Those disagree, and the patch
  browning already applied to the mesh follows the CLIP, not this. That has to be settled before
  more colour work — matching proportion to one target and colour to another is its own trap.
