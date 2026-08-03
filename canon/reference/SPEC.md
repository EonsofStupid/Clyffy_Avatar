# CLYFFY — FACE REFERENCE SPEC

**This folder is the single authoritative visual reference for the avatar's head.**
Everything superseded lives in `canon/_archive/`. If a measurement, tool or document cites a
reference that is not in this folder, it is stale.

Operator ruling 2026-08-03: *"can we use and do this one, move the rest to archive … so we only
have this, this is perfect."*

## The set

| file | views | use |
|---|---|---|
| `modelsheet_neutral.png` | front · 3/4 · **true 90° side profile**, mouth CLOSED | head proportion, snout projection, lip line, chin |
| `modelsheet_open.png` | the same three views, mouth WIDE OPEN | oral cavity depth, jaw drop, dentition, tongue |
| `detail_muzzle_profile.png` | muzzle close-up, true side profile | pad projection, lip roll, nostril, pore texture |
| `_element_source.png` | the frame the character element was built from | provenance only, not a measurement source |

2752×1536 and 2528×1696. Flat even neutral studio lighting, plain light-grey seamless background,
no rim light and no colour grade.

## Provenance

Generated 2026-08-03 on higgsfield from reference element **`Clyffy-BROWN-avatar-target`**
(`1c6d9749-87fe-4cec-8e8e-77f33216d2b4`), which was built from frame 20 of the operator's
isolated clip `6f675283`. Using an element rather than a text prompt is what keeps this the same
character across all three sheets instead of three lookalikes.

## Two rules this set exists to enforce

**1. MEASURE ALBEDO FROM FLAT LIGHT.** The archived video frames are dim and blue-graded — the
muzzle that *looks* salmon measures sRGB (120,101,137), blue-dominant. Measuring them as albedo
produced a pad 40% too dark and 35% too saturated, and cost a full build cycle. Reference shot for
measurement must be lit for measurement.

**2. PROFILE IS NOT OPTIONAL.** Every proportion failure in this project — snout projection, head
length, lip curve, chin — is a profile problem, and every measurement taken before this set was
front-on. A front view cannot show any of them.

## What this set already settles

* The **snout projects forward as a distinct rounded mass**, with the lip line running back from it
  in a long shallow curve and a soft lower-lip roll beneath the pad. Ours is close to flat.
* **The teeth are CONTINUOUS cream bands, upper and lower** — no separated teeth. This is the
  fourth independent confirmation that the 2026-07-28 scallop (`TEETH_N = 7`, `TEETH_CUT = 0.34`)
  is wrong against canon.
* The **open mouth is a large rounded aperture**, not a slit, with the tongue as a soft mass
  filling the floor and the cavity dark but not black.
* Coat is **WHITE with warm CHOCOLATE BROWN patches** — not black. See the conflict note below.

## ⚠️ OPEN CONFLICT — colour, unresolved in the documents

This set is **brown-and-white**. `canon/CLYFFY/_SPEC.md` and the older canonical elements say
**Holstein black-and-white**. The operator selected this set as the target, so the mesh's patch
browning (`tools/materials.py`, `PATCH_CHROMA`) follows THIS, and `_SPEC.md` is the stale document
— but that is a show-bible file and has not been formally changed. Do not "fix" one to match the
other without the operator saying which wins.

## Known limits

* The eye renders oddly in the profile view. The silhouette is clean, which is what proportion work
  needs, but do not read eye shape from that panel.
* The sheets carry small burned-in view labels ("FRONT", "3/4 VIEW", …). Harmless; crop them out
  before any pixel measurement that samples near the frame edge.
* This character reads slightly slimmer in the muzzle than the operator's original still. Flagged by
  the operator and accepted: *"slightly skinnier then my original but that is solid."*
