# CLYFFY AVATAR — BUILD LOG

## 2026-07-25 — Step 3 complete: base body mesh generated

### Pipeline position

> **Updated 2026-07-27 — ALPHA mesh+drive.** Historical row below kept; live SSOT is
> the table in the 2026-07-27 ALPHA entry at the end of this file.

| Step | State (as of 2026-07-25) |
|---|---|
| 1. Assets local | ✅ `rclone` scoped pull, 19 files / 79 MB |
| 2. Turnaround reference | ✅ **already existed** — two five-view production sheets |
| 3. Image → mesh | ✅ **base body done** (this entry) |
| 4. Retopology | ⚠️ partially pre-empted — mesh requested as **quad** topology |
| 5. Visemes / blendshapes | ⬜ not started — confirmed absent from the mesh |
| 6. Audio → viseme drive | ⬜ not started |
| 7. Voice model | ⬜ spec exists (`_SPEC.md`: warm confident baritone) |
| 8. Phone surface | ⬜ not started |

### View extraction

`Clyffy_Episodic-Kenny-Protocol.png` (2688×1520, AV canonical) split into five single
views in `work/views/`, label strip cropped, per-panel whitespace trimmed:

```
AV_base_front_000.png      537×1216
AV_base_front34_045.png    538×1341
AV_base_side_090.png       537×1341
AV_base_back34_135.png     538×1341
AV_base_back_180.png       538×1167
```

DPN equivalents in `work/views_dpn/` from `Clyffy_News-Anchor-v1.png` — see caveat below.

### Generation

- **Model:** `tripo_h3_1_multiview_to_3d` (Tripo H3.1)
- **Job:** `22e66de6-933c-4190-ac18-8cffd3ded4e0`
- **Inputs:** 4 views — front 0°, 3/4 front 45°, side 90°, back 180°
- **Params:** `texture=true · pbr=true · quad=true · geometry_quality=detailed ·
  texture_quality=detailed · texture_alignment=original_image · orientation=align_image`
- **Cost:** 16.5 credits

Chosen over Meshy `multi_image_to_3d` (30 credits textured / 20 geometry-only) because it
was cheaper *and* better specified — Meshy's 30-credit option had no PBR.
**Note:** credit balance is not a real constraint — the ultra plan reloads to ~9000 every
2–3 days. Pick on spec, not price.

### Result — `mesh/clyffy_base_av_v1.fbx` (5.8 MB)

**The file is FBX, not GLB.** It downloads from a `.glb` URL with a `model/gltf-binary`
content-type but the magic bytes are `Kaydara FBX Binary, version 7400`. Renamed on disk.
FBX is fine for Blender import; just don't feed it to a glTF-only tool.

Verified by parsing the container:

- **PBR textures embedded** — 4 `Content` nodes, 4 JPEG payloads (Color, Metallic,
  Normal, Roughness). Self-contained; the `/mnt/pfs/...` paths in the file are Tripo's
  server-side originals and are irrelevant because the bytes are baked in.
- **No rig** — `Deformer 0 · Skin 0 · Cluster 0 · BindPose 0 · BlendShape 0`.
  Static mesh only, as ordered.

⚠️ **The source CDN URL carries `x-amz-expiration: Delete after 7 days`** (expires
2026-08-02). The local copy is the only durable one.

### ✅ MESH ASSESSED (Blender 4.0.2, arm64, headless)

Tooling: `sudo apt install blender` (4.0.2 native arm64) + `sudo apt install python3-numpy`
— **the FBX importer hard-requires numpy and this build uses system Python**, so without
that package `import_scene.fbx` dies with `ModuleNotFoundError`.

Scripts: `tools/blender_inspect.py` (report + render), `tools/_turnaround.py` (8-angle
contact sheet), `tools/_topo.py` (loose-part / manifold analysis).
Renders in `mesh/turnaround/`, `mesh/head/`, `mesh/preview/`.
**True front is `a225`** — the FBX imports with a forward axis that is not Blender's −Y.

#### Verdict: excellent static mesh, not yet an avatar

**What's good**

| Metric | Value |
|---|---|
| Triangles / vertices | 93,279 / 46,696 |
| Polygons | 46,652 |
| **Quads** | **46,616 — 99.9%** (only 5 n-gons) |
| Non-manifold edges | **0** |
| UV map | `Retopo_Untitled_NewUVMap` — Tripo ran real retopology |
| Textures | 4 × **4096²** (Color, Metallic, Normal, Roughness), embedded |
| Material graph | `BSDF_PRINCIPLED` + `NORMAL_MAP` + `TEX_IMAGE` |

Silhouette holds across all 8 angles with no view-dependent melting. Horns, ears, tail
with tuft, cloven hooves, brass goggles, lanyard and the CLYFFY badge all survived as real
geometry. Arms and legs are clearly separated from the torso — limbs are riggable.
**99.9% quads + 0 non-manifold means step 4 (retopology) is essentially already paid for.**

**What blocks the talking avatar** — all three confirmed numerically, not eyeballed:

1. **It is ONE welded object.** 12 "loose parts" exist but part 0 holds **99.8%** of verts
   (46,597 / 46,696); the other 11 are 1–27-vert stray fragments (junk to delete).
   One material for everything. ⇒ **The t-shirt is fused to the body.**
   Decision **A2** (base body + swappable garment) *cannot* use this mesh as-is — the
   garment must be separated by hand via edge loops, or modelled fresh and fitted over.
2. **No mouth cavity.** The mouth is sealed with the tongue protruding through a closed
   seam. 155 boundary edges exist but they belong to the stray fragments, not to a mouth.
   ⇒ You cannot open a mouth that has no opening. Visemes need either a cut-and-extrude
   of a real oral cavity, or a jaw-bone + shape-key illusion (viable for stylised
   characters, and cheaper).
3. **No separate eyes.** Eyeballs are welded into the head surface, not spheres.
   ⇒ No eye rotation; blinking has to be shape keys on fused geometry.

Also absent, as ordered: `armature_count 0`, `shape_key_count 0`.

**Scale note:** dimensions are 0.523 × 0.567 × 0.980 — normalised to ~1 unit tall, *not*
real-world metres. Set a real height before rigging (`rigging_height_meters` equivalent).

---

## 2026-07-25 — Step 5 experiment: jaw-rotation-without-cavity — **NEGATIVE RESULT**

**Question:** can a jaw bone + shape keys fake speech on a sealed mouth, skipping the
cavity sculpt? **Answer: no.** Do not spend more time on this route.

Script `tools/jaw_test2.py`, renders in `mesh/jaw2/`, scene `mesh/jaw2/clyffy_jaw2.blend`.

Method: strip the 11 stray fragments (99 verts) → locate the muzzle tip by max radial
distance in the top 30% z-band → derive facing vector → place a jaw hinge behind the
muzzle at mouth height → weight a jaw band with smoothstep falloff → bake a 30° rotation
as a `jaw_open` shape key → render a 0 / 40 / 70 / 100% sweep plus a vertex-colour
weight map.

Final weighting: **1,433 verts (3.1%)**, max displacement **9.3% of model height** — an
anatomically plausible jaw. Verified the shape key stores and evaluates
(`STORED DELTA == EVALUATED DELTA`, 15,562 verts on the first attempt).

**Why it fails:** rotating a sealed jaw *moves* a closed mouth, it does not *open* one.
There is no interior to reveal — no dark cavity, no teeth, no tongue emerging. Across the
whole sweep the lips stay fused; at 100% it reads as the muzzle stretching, not speech.

**Second blocker found:** the tongue is **permanently protruding welded geometry**. It
hangs out of the mouth in every frame and cannot be retracted.

### Consequence — the cavity sculpt is mandatory

Minimum viable work, in Blender:
1. Cut a mouth line along the existing lip seam.
2. Extrude a **shallow** interior pocket — a full throat is not needed; a dark recess
   reads fine at avatar scale.
3. Separate the tongue and reposition it inside the new pocket.
4. *Then* the jaw hinge + weighting from `jaw_test2.py` becomes reusable as-is — the
   hinge placement, facing detection and falloff maths are all still correct and worth
   keeping.

---

## 2026-07-25 — Locating the mouth: texture-driven, not geometry-driven

**Result: the mouth seam is findable. Use `tools/_mouthmask2.py` with `THRESH = 0.09`.**

### The mouth IS real geometry (good news)

`tools/_mouthdiag.py` renders the head textured vs solid-shaded. Solid shading shows a
**modelled lip crease** curving up into the smile, with real lip form — not a painted-on
mouth. So the job is *rip open an existing seam*, not *sculpt a mouth from nothing*.
Same render shows the eyes are smooth bulges with modelled eyelid ridges but **no eyeball
geometry underneath** — spheres must be inserted, not separated.

### What failed: sharp-edge detection

`tools/_seamfind.py` looked for creases by dihedral angle (>34°), found 439 candidate
edges in 58 chains — and **none of them was the mouth**. Every top chain sat *above* the
muzzle tip with a lateral span of 0.011–0.052; those are nostril and eyelid creases.
**Why:** the lip line is a *soft* groove spread across many quads, so no single edge
exceeds an angle threshold. Curvature thresholds are the wrong instrument here.

### What worked: sampling the base-colour texture through the UVs

The artist painted the lip line. Read it back: for each face in the muzzle band, average
its loop UVs, sample `tripo_image_15131013_0` (4096²), compute luminance, threshold.

| Threshold | Faces | Lateral span | Verdict |
|---|---|---|---|
| 0.055 | 19 | 0.188 | Too tight — fragments only |
| **0.09** | **69** | **0.170** | ✅ **Thin ribbon along the lip seam + tongue** |
| 0.16 | 834 | 0.227 | Too greedy — floods the shadowed underside |

Band gate that matters: `tip.z - 0.09H … tip.z + 0.02H` (below the nose only) plus
forward-of-axis `> 0.03H`. Without the upper bound the nostrils get caught.

### Camera convention — fix this once, reuse everywhere

Close-up renders were pointing at the **back of the head**. `rotation_euler` was 180° out.
The working convention (from `_turnaround.py`) is:

```python
a = math.atan2(fwd.x, -fwd.y)          # + offset for 3/4 views
cam.location = (ctr.x + sin(a)*R, ctr.y - cos(a)*R, ctr.z)
cam.rotation_euler = (radians(90), 0, a)
```

Do **not** use `atan2(d.y, d.x) + 90°` — that is the 180°-wrong form that wasted two renders.

### ❌ THE CUT FAILED — root cause: forward-axis detection is 59.6° wrong

`tools/mouth_cut2.py` cut 386 faces and built a 736-face cavity. **It cut the side of the
skull, not the mouth.** Wide renders show jagged torn geometry on the side of the head.

**Root cause** (`tools/_fwdcheck.py`):

| | |
|---|---|
| Head-band centroid | `(+0.0133, +0.0380)` |
| "Muzzle tip" by max-radial | `(-0.1868, -0.0142, +0.3578)` → dir `(-0.968, -0.253)` |
| That direction as turnaround angle | **284.6°** |
| Empirically verified true front | **225°** |
| **Angular error** | **59.6°** |

The heuristic *"muzzle tip = vertex furthest from the head-band centroid in XY"* **does not
work on this character.** The ears, horns and neck drag the centroid off-centre, and the
resulting max-radial vertex sits 55% up the head band — a cheek/ear point, not the nose.

Every downstream computation inherited the error: the mouth mask band, the cut location,
and the jaw hinge. The earlier jaw-rotation test is also suspect for the same reason.

**Source FBX is UNTOUCHED** — `clyffy_base_av_v1.fbx`, md5 `f7803c7440d6182b417718ef11b45c30`,
unmodified since 08:08. Only derived `.blend` files were damaged; they are disposable.

### The fix — and a contract lesson

Do **not** re-derive the forward axis by heuristic on every run. It is a **property of the
asset**, so it belongs in the character-pack manifest as calibrated data:

```
forward_axis: 225°     # verified against the turnaround render
up_axis: +Z
mouth_z: <measured>
scale_m: <real height in metres>
```

Calibrate once, by eye, against a rendered turnaround; store it; every tool reads it.
This is exactly what the pack contract is for — and it is the first concrete requirement
the contract has earned rather than guessed.

**Also still true:** texture-driven mouth masking (multi-sample, `lum<0.11`, dilate 1 ring)
produced 449 faces in a 386-face main cluster. That machinery is sound — it was simply
pointed in the wrong direction.

### Next: the cut (retry, once the axis is calibrated)

Convert the 69-face ribbon into a clean cut curve → `bmesh.ops.split_edges` to rip the
seam → extrude inward for a shallow cavity → separate and retract the tongue.

---

### Debugging note (cost one cycle)

The first attempt (`tools/jaw_test.py`) weighted **32.2%** of the mesh and swung the
torso 19° while moving the jaw only ~3°. Cause: the falloff term *grew* with distance
below the mouth line, so the belly scored higher than the jaw. Fixed by gating hard on a
jaw band (`mouth_z - 0.085H … mouth_z + 0.012H`) instead of an open-ended "below" test.
**Lesson: always render the weight map before judging a deformation** — the first sweep
looked like "nothing happened" when in fact something large was happening off-camera.

### Caveat on the DPN coat views

`work/views_dpn/` is extracted from `Clyffy_News-Anchor-v1.png`, which CANON.md §6 marks
**non-canon** (singed coat in a DPN context, no lanyard, adds a headset). It is still the
*only* multi-view of a coated Clyffy. Its coat is singed — i.e. it is usable as the **AV
singed-garment** reference, not as the DPN clean coat. The canonical DPN
(`Clyffy_Anchor-Standalone-FINAL.png`) is a single hero view only.
Two of its four views are uploaded; **no coat mesh has been generated.**

---

## 2026-07-25 — RE-MESH from the neutral base sheet ✅ `clyffy_base_neutral_v2.fbx`

Source: `work/views_base/BASE_{front_000,front34_045,side_090,back_180}.png`, extracted
from `Clyffy_BASE-NEUTRAL-v1.png` (decision A3). Job `e42889ed-1fef-48da-b49e-2fb13a8558e6`,
`tripo_h3_1_multiview_to_3d`, texture+pbr+quad, detailed geometry & texture. 5.1 MB FBX
(again served from a `.glb` URL — Kaydara FBX 7400).

### Both v1 blockers are GONE
| v1 blocker | v2 |
|---|---|
| Brass goggles modelled into the skull as geometry | **absent — forehead bare** |
| Tongue fused protruding through the lips | **mouth closed, tongue inside, clean lip line** |
| Baked-in goofy performance expression | **neutral** |

### Topology — better than v1 across the board
| Metric | v1 | **v2** |
|---|---|---|
| Quads | 99.9% (5 n-gons) | **100.0% (2 n-gons)** |
| Loose parts | 12 (11 stray fragments) | **1 (100% single component)** |
| Non-manifold edges | 0 | 1 |
| Boundary edges | 155 (stray fragments) | 31 @ z[-0.007,+0.084] |
| Verts / tris | 46,696 / 93,279 | 46,001 / 92,004 |
| Textures | 4 × 4096² | 4 × 4096² |
| Armature / shape keys | 0 / 0 | 0 / 0 |
| Dimensions | 0.523 × 0.567 × 0.980 | 0.573 × 0.668 × 0.978 |

No stray-fragment cleanup needed this time. One non-manifold edge and a small 31-edge
boundary around z≈0..0.08 (lower body) — both minor, worth a look before rigging.

### Axis
Calibration sweep re-run (`tools/calibrate_axis.py`): **front is 225°**, same as v1.
`clyffy.pack.toml [calibration] forward_axis_deg = 225.0` is correct for v2 — verified,
not assumed.

### Next
The mouth mask machinery from `tools/mouth_cut2.py` (multi-sample texture threshold at
`lum<0.11`, dilate 1 ring) is sound — it was only ever aimed wrong by the bad forward
axis. With 225° now calibrated AND a genuinely closed mouth to find, the cut should
target the real lip line.

---

## 2026-07-25 — ⚠️ SUPERSEDED — "MOUTH OPENS. Cut + cavity + jaw, on v2."

> **READ THE NEXT ENTRY FIRST.** This entry was written at 18:10, before the jaw work that
> followed it failed. Two claims below are now known wrong:
> * **The jaw did NOT work.** Three procedural jaw solvers followed this entry and all
>   failed; the operator's report was "the jaw does not open at all, it literally just
>   pulls the right side of the face down."
> * **`forward_axis_deg = 225` is wrong** (true value 235.1) *and* it was being applied in
>   the wrong coordinate space. That is the root cause of every jaw failure, and it also
>   means the cavity described below was extruded ~59° off, into the cheek.
>
> What still stands: the operator's hand-picked seam, the division of labour, and the
> pre-existing-hole bug note. The artefacts under `mesh/v2open/`, `mesh/v2jaw/`,
> `mesh/v2jaw3/` are all superseded by `mesh/canon/`.

**The division of labour that made it work — this is the reusable pattern:**
I could not find the mouth. Luminance thresholding hit a black Holstein neck patch;
sharp-edge detection hit ear creases; three forward-axis solvers were 59.6° / 54.5° / 80°
wrong. The operator could not practically hand-pick a lip loop out of 46,001 verts —
Alt-click loop select failed, so he clicked ~390 verts individually, then refined to 81.
**He scoped, I searched.** Inside his region the confounders vanish and both of my failed
methods immediately agree.

### Operator selection (`mesh/clyffy_v2_SEAM.blend`)
- First pass: 390 verts / 320 faces — the **deformation region** (whole lower jaw),
  z[0.193,0.247]. Not what I asked for, and **more useful** than what I asked for.
- Refined: **81 verts / 129 edges / 49 faces**, z[0.223,0.231] — a 0.008-tall band.
  That is the lip seam.

Verified inside the region: luminance 0.287 darkest / 0.692 median / 0.803 brightest —
no competing dark patch. Sharpest in-region edge 64.4° vs 6.4° median — a real fold.
Both methods agree; neither did when searching the whole head.

### The cut — `tools/mouth_open.py` → `mesh/v2open/clyffy_v2_mouthopen.blend`
Delete the 49 seam faces → 62 new boundary edges → 3-ring inward extrude
(0.40/0.92, 0.75/0.70, 1.0/0.30) at depth 0.055·H → `holes_fill` cap → 188 cavity faces
with a dedicated dark `clyffy_mouth_interior` material. Hole centre z=0.226 matches the
seam at 0.227.

⚠️ **BUG WORTH REMEMBERING:** the first attempt collected *all* boundary edges after the
delete, which swept in v2's **pre-existing 31-edge hole on the lower body** (z[-0.007,
0.084]) and extruded that too — producing a protruding wedge and dragging the hole
centroid to z=0.153. Fix: snapshot boundary edges BEFORE the delete and difference.
Any mesh with pre-existing holes will hit this.

### The jaw — `tools/jaw_v2.py` → `mesh/v2jaw/clyffy_v2_jaw.blend`
Mouth centre derived from the cavity material (not guessed): (+0.062,+0.125,+0.226).
Hinge behind it, 26° rotation, smoothstep falloff. **1,685 verts (3.6%)**, max
displacement 0.046 = **4.7% of height**. Shape key `jaw_open`.

### Verdict: mechanism proven, quality not there yet
The mouth **does** open and the dark cavity **is** revealed — the v1 negative result is
overturned. But:
- The opening is **subtle** — 26° / 4.7% reads as a small parting, not speech.
- **White spike artifacts at the mouth corners** where the cavity extrusion meets the
  lip edge at the seam terminations.

Next: increase rotation, widen the seam laterally so the corners resolve, and clean the
corner geometry. Then visemes on top.

---

## 2026-07-25 (late) — 🔴 ROOT CAUSE: the forward axis was wrong twice over. Rebuilt the chain.

Three jaw solvers failed in a row (`jaw_v2.py`, `jaw_v3.py`, and a first armature attempt).
Each failed differently, so each got a new heuristic. All three shared one cause.

### The bug — a world-space angle applied to local coordinates

The Tripo object `tripo_node_dfcde304` carried a **+69.17° Z rotation at object level**.
`forward_axis_deg = 225` was read off a render sweep, and **renders are WORLD space**.
Every jaw tool then applied that angle to **`v.co`, which is LOCAL**.

| space | head centre → mouth cavity | implied forward axis |
|---|---|---|
| LOCAL (`v.co`) | (+0.0688, +0.1189) | 149.9° |
| WORLD (`matrix_world @ co`) | (−0.0866, +0.1065) | 219.1° |

On top of that the value itself was ~10° off. **Combined error on the hinge axis: ~79°.**
A hinge axis 79° off runs diagonally through the head — one side drops and the other does
not. That is exactly the reported symptom. It also means `mouth_open.py`'s `inward = -fwd`
pushed the cavity ~59° off, into the cheek rather than back into the head.

**The tell was visible for hours and I misread it:** weight symmetry was 10.1:1, and the
previous session blamed the operator's hand-clicked selection for it. That was wrong — his
selection was fine. With the axis corrected the same selection gives **1.04:1**.

### The corrected axis — 235.1°, measured two independent ways

| method | result |
|---|---|
| 3D bilateral-symmetry solve, head only, angle + plane offset (`tools/head_axis.py`) | **233.75°** |
| image mirror-difference scan, parabolic peak (`tools/_mirrorscore.py`) | **235.12°** |

They agree to 1.4°. The mirror-difference curve is clean and unimodal; 225° scores 0.058
against 0.008 at the minimum — **~6× worse**. It still *looked* head-on to me, because the
curve is shallow near its minimum. **Eyeballing a render sweep is not a measurement.**
`tools/calibrate_axis.py`'s docstring — which claimed the symmetry solver was "54.5° wrong"
against the bad 225° ground truth — has been corrected; that note is why I distrusted the
correct answer when it appeared.

### Blender's automatic weights DO NOT WORK on this mesh

`bpy.ops.object.parent_set(type='ARMATURE_AUTO')` (bone heat) returns **zero weights for
every bone**. Verified on the cut mesh AND the original uncut FBX, with hole-filling, with
triangulation, and for every bone subset (`tools/_heatdiag.py`, `tools/_heatfix.py`).
**It reports this as a `Warning`, not an exception, so it silently "succeeds"** — the
first armature attempt looked like it had worked and had an empty jaw group. There is no
scipy in Blender's Python, only numpy 1.26.4.

So the weights are solved directly. Bone heat *is* harmonic diffusion over the surface:
solve `Laplace(w)=0` with `w=1` on the jaw core and `w=0` on the skull/body core, by
conjugate gradient on the graph Laplacian (~120 iters, residual 1e-8).

**Why this is not a fourth Euclidean heuristic:** diffusion travels along **mesh edges**.
The mouth is genuinely cut, so weight cannot cross from lower jaw to upper lip — it has to
go the long way around the corners and decays doing it. The three failed solvers used
distance/projection in space, where the upper lip sits 0.005 from the lower lip.

⚠️ **The cavity re-sealed that gap in the graph.** Built by extruding inward from the whole
boundary ring and capping, upper lip → wall → cap → wall → lower lip is a **4-edge path**.
Open in space, sealed in the graph. The solve runs on the outer surface only; cavity
interior verts are re-attached afterwards from their nearest surface vertex.

### The canonical chain — `mesh/canon/`, build in this order

1. **`tools/canonicalize.py` → `clyffy_v2_canon.blend`**
   Freezes the transform (**identity rotation, world drift 3e-8**) so the space bug cannot
   recur — downstream tools now *assert* it. Bakes the operator's selections as **vertex
   groups** `op_jaw_region` (390) / `op_lip_seam` (81) instead of raw indices; groups
   travel through edits, indices force every step to preserve numbering (which is why the
   old cut used `FACES_ONLY` and left 67 wire edges). Cleans: wire 0, loose 0, boundary
   31 → 19, non-manifold held at 1.
2. **`tools/mouth_open.py` → `clyffy_v2_open.blend`** — 187 cavity faces, z[0.2230,0.2307].
3. **`tools/jaw_rig.py` → `clyffy_v2_rig.blend`** — bones `root`/`skull`/`jaw` + skin.

### Three real defects found and fixed in the cut

* **67 wire edges + 20 loose verts** left inside the cavity by the `FACES_ONLY` delete.
  Fixed by `context='FACES'`, now possible because groups replaced raw indices.
* ⚠️ **The pre-existing-hole guard was broken by that change.** It captured boundary edge
  *indices* before the delete — and **a delete renumbers edges**. The old code only got
  away with indices because `FACES_ONLY` never removed any. It silently re-extruded the
  torso hole (cavity spanned z[−0.0067,+0.2307]). **Fixed with a bmesh tag layer**, which
  survives renumbering. Any bmesh guard that survives a delete must be a tag, not an index.
* **A PINCH POINT in the seam boundary — the source of the "white spike artifacts".**
  The 62-edge mouth boundary had 60 verts of degree 2 and **one of degree 4**: a figure
  eight. The extrude folded through it and welded walls together (3 edges with 4 linked
  faces). Fixed by growing the cut region around the pinch until the boundary is a simple
  cycle — costs 2 extra faces. Cavity non-manifold count is now **0**.
* Also: extrusion copies vertex data, so new cavity verts **inherited** `op_lip_seam`
  membership (group went 81 → 244). Generated geometry must not join operator groups; they
  are now stripped, using the extrude's own returned vert list (a tag layer does not work
  here — extrude copies the tag too).

### Rig state — measured, not asserted

| check | value |
|---|---|
| weight symmetry (was 10.1:1) | **1.04 : 1** |
| jaw verts fully rigid (w > 0.99) | 897 |
| upper lip rim movement at full open | **0.000000** |
| aperture, closed → open @ 22° | 0.0029 → 0.0735 |
| partition of unity (Σw per vert) | \|1 − Σw\| max **8.9e-05** |
| influences per vertex | max **3** (≤ 4, game-engine safe) |

The jaw core is anchored **rigid** so it rotates instead of stretching, and the jaw/skull
boundary follows the **jawline** — a diagonal from the mouth corner back and up toward the
hinge (21.6° below horizontal), not a horizontal cut above the lip. A horizontal cut leaves
the mouth corner rigidly skull exactly where it must give.

### ❌ STILL BROKEN — do not claim the mouth is done

**Light-grey slivers at the mouth corners at large open angles.** Confirmed NOT a material
bug and NOT backfaces (tested with backface culling on). They are the cow's own white
lower-face skin stretched into a thin web at the corners. Current best diagnosis: the
cavity tube does not extend far enough laterally around the corners, so the gap between
cavity wall and outer skin is exposed as the jaw drops. This matches the earlier note
"widen the seam laterally so the corners resolve" — that item was never done.

Separately fixed along the way: the cavity material had its Principled base colour set but
**not `diffuse_color`**, so Workbench/solid shading rendered it default light grey. Some of
what was previously logged as "white spike artifacts" was that shading bug, not geometry.

**Left deliberately unrepaired:** a 19-edge *branching* boundary + 1 three-face non-manifold
edge in the Tripo source at (−0.1134, +0.0772, −0.0064) — torso, z ≈ −0.006. The jaw
deformer is at z > 0.208 so it cannot affect the rig, and an automatic repair risks the
lanyard/shirt geometry. Documented, not hidden.

---

## 2026-07-25 (late, cont.) — ✅ THE MOUTH OPENS CLEANLY. Tearing traced to weight discontinuity.

The corner "slivers" left by the previous entry are fixed. **They were never missing
geometry** — that was a guess, and it was wrong. Measured properly with a stretch map
(`tools/stretch_map.py`: per-edge deformed/rest length ratio), they were the skin being
**torn** by weight discontinuities. Every fix below came from a measurement, not a theory.

### The measurement that broke it open

`edge stretch @ 22 deg: max 27.22x` — and grouping the worst edges showed jaw weight
ranging **0.08 to 0.95 on the SAME EDGE**. Stretch is caused by weight *difference across
an edge*, so the whole problem was restated: **drive `|w0 - w1|` to zero on every real
mesh edge.** `tools/_edgeprobe.py` reports the top edges individually with both endpoint
weights, both endpoint kinds (skin / lip rim / bag interior) and the incident face
materials — that classification is what located each cause.

### Three distinct discontinuities, three fixes

**1. The mouth bag was torn in half (60x).**
Bag interior verts took the weight of their NEAREST SURFACE VERTEX. The bag's two walls
sit ~0.008 apart, so neighbouring bag verts snapped to opposite lips — one w≈1, its
neighbour w≈0. Fix: `tools/mouth_open.py` now records **lineage** (`cav_src`), the lip rim
vert each bag vert was extruded from, and the rig skins the bag from its ancestor. The
lower wall follows the jaw, the upper stays, as one piece.

**2. The bag's back CAP joined the two walls (still 60x, on 0.0006-long edges).**
The bag is a closed tube: lineage alone puts w=1 and w=0 on opposite sides of the cap.
Fix: `cav_depth` (0 at the lip rim → 1 at the cap) and the inherited weight is blended
toward a common 0.5 with depth, so the cap is uniform and the shear spreads through the
bag. Standard mouth-bag skinning.

**3. ⚠️ THE BIG ONE — the lip rim was classified by Z (27x, 25 torn edges).**
The rim is a closed loop; the lower lip (must move) and upper lip (must not) are adjacent
at the commissures. Tapering both toward 0.5 there is correct — but deciding *which lip a
rim vert belongs to* **from its z coordinate** is not. The rim zigzags in z, because the
lip line is not horizontal and the slit is only 0.0077 tall. **23 of 62 rim verts were
classified wrong**, putting w=1.00 next to w=0.00 on cycle-adjacent verts in the MIDDLE of
the mouth. Fix: walk the rim loop, find the two commissures, and classify by **which chain
of the loop** a vert is on — monotonic by construction, so adjacent verts can never flip.

> **The same class of error twice in one build.** The forward axis was an angle used
> without declaring its SPACE. This was a lip classified by a COORDINATE instead of by its
> position in the structure. Both are "a cheap proxy stood in for the real relation."
> Prefer the structural quantity (chain membership, arc distance) over the convenient one.

Note the aperture metric had the identical bug — it split the rim by z too, so it averaged
upper and lower together and read 1.3% instead of 5.6%. **A metric can be wrong in exactly
the way the code is wrong; that is when it is most dangerous.**

### Result — `mesh/canon/`, reproducible end to end

| check | before | after |
|---|---|---|
| max edge stretch @ 22° | 27.22x | **3.85x** |
| edges stretched > 5x | 76 | **0** |
| edges with \|w0−w1\| > 0.5 | 25 | **0** |
| weight symmetry | 1.03 : 1 | 1.03 : 1 |
| upper lip rim movement | — | 0.0101 |
| aperture (closed → open) | — | 0.0014 → 0.0549 (5.6% of height) |
| Σw per vertex | — | \|1−Σw\| max 8.9e-05 |
| influences / vertex | — | max 3 |

### Rejected after measuring — recorded so it is not retried

* **Rim geometry relaxation** (to smooth the stair-stepped cut boundary). Plain Laplacian
  smoothing shrank the loop 4.6% and put **bright specks along the lip line in the REST
  pose**. Taubin (λ/μ) fixed the shrinkage (−0.63%) — and still produced specks, because
  the slit is 0.0077 tall and even a 0.0032 move is ~40% of it. **`RIM_RELAX = 0`.** The
  rest pose is the state the avatar sits in; a staircase visible at 4× zoom on a fully
  open mouth is the lesser defect. The knob is kept for when the lip loop gets denser.
* **Post-solve weight smoothing** (`SMOOTH`). Cut `>2x` edges from 85 to 60 but *raised*
  the max to 4.07x and eroded the rigid core from 742 verts to 560. Left at 0.
* **Large corner relief.** At radius 0.044 it freed most of the upper lip: that lip then
  moved 0.038 and the aperture collapsed to 0.0376. The rim's half-span is only 0.072 —
  the radius has to stay small next to it. Settled at 0.020 (max stretch 3.85x and zero
  edges above 5x, vs 7.16x and 4 at radius 0).

### ⚠️ Known remaining, at 4× zoom only

The cut boundary is a **staircase of quad edges** — the seam was picked per-face, so the
lip outline follows the quad grid rather than a smooth curve. Invisible closed and at
normal viewing distance; visible on a hard zoom into an open corner. The real fix is a
denser/cleaner lip edge loop, not a smoothing pass (see rejected, above).

Still unrepaired by choice: the 19-edge branching boundary + 3-face non-manifold edge in
the Tripo source at torso z ≈ −0.006, well below the jaw deformer.

---

## 2026-07-26 — Target locked: VRM + ARKit-52 + bone lookAt. And the eyes are REAL geometry.

Operator set the actual product target: **waist-up presenter** in a **companion app** —
MFA captured to make two-factor login effortless, then the avatar loads, you chat, and he
has control of this box to do work and present windows of ideas from the discussion.
That reframes the avatar work: arms, hands, and **especially eyes and face expression**.
Legs and hooves leave the rig.

### ✅ CORRECTION — the eyes are modelled geometry, not a painted surface

The v1 assessment in this log says *"No separate eyes. Eyeballs are welded into the head
surface, not spheres. ⇒ No eye rotation."* **That is wrong for v2.**

`tools/_facecheck.py` renders the head in solid shading with the texture stripped — the
same trick that found the modelled lip crease. The eyes are **spherical domes seated in
sockets, each ringed by a distinct rim crease**. The iris and pupil are painted onto the
dome. So separating a dome along its socket rim and **rotating** it moves the gaze
correctly: **gaze is a rotation, not a UV hack**, and the socket rim is a cut seam exactly
like the lip seam was.

Also confirmed modelled, not painted: brow ridges over each eye, real nostrils, ear and
horn forms. On a cow with no eyebrows those brows plus the ears are where expression
lives — which is what `[animation]` already asserts.

⚠️ **BLINK IS THE OPEN ONE.** There is a lid/brow overhang above each dome but nothing
that clearly travels down over it. Either a shape key that pulls the socket rim across, or
model real lids. **This is the eye equivalent of teeth-and-tongue — settle it before
investing in expression work**, or the shapes get authored twice.

### Format re-checked against the 2026 landscape, not assumed

Operator asked whether VRM is still right "for what is trending hard right now". Checked
rather than answered from memory. It is, and more so than when decision A1 was made:

* **Khronos × VRM Consortium are formally collaborating**; VRM is heading for Khronos glTF
  Ratified Extension status and an ISO/IEC path. glTF 2.0 is already ISO/IEC 12113:2022 —
  and VRM *is* glTF plus extensions, so nothing is stranded if the avatar layer moves.
* **OpenUSD is not the competitor it looks like.** AOUSD and Khronos hold a formal liaison
  on the split: USD authors, glTF delivers. BOTH/AND — USD becomes the authoring side if
  DevPulse News ever wants film-grade episode rendering; VRM/glTF stays delivery.
* **Gaussian splatting** (KHR_gaussian_splatting, Feb 2026) is photoreal-plus-3D, not yet
  shippable, and the wrong tool for a stylised character. Rigged is the production answer.
* The companion app is **real-time**. Everything built so far renders offline in Blender —
  right for episodes, insufficient for a desktop companion. Authoring to VRM from here
  avoids a retrofit.

Sources: khronos.org press release (VRM standardization) · news.viverse.com (VRM + Perfect
Sync) · techtimes.com 2026-07-02 (OpenUSD Core Spec / ISO) · forasoft.com (USD-authoring
vs glTF-delivery; 2D-neural and 3D-rigged production-ready, GS not yet).

### ⭐ Two pins added to the manifest — do not author a single shape before reading them

**`[rig.blendshapes]` — ARKit-52 "Perfect Sync", not VRM's native expression set.**
52 shapes downsample cleanly into VRM expression presets; VRM's handful upsamples into
nothing. That is the difference between one authoring pass and two. It also makes any
iPhone able to drive his face live, which *is* the phone surface, free. Two of the 52 are
not authored as shapes here: **`jawOpen` is bone-backed** by the validated jaw rig (driving
it twice would double-transform the jaw), and **`tongueOut` is blocked** until the cavity
has a tongue.

**`[rig.look_at]` — VRM lookAt in BONE mode, not expression mode.** Justified by the eye
finding above. The eight `eyeLook*` entries in the ARKit set become derived from the bone.

Also pinned: `[rig.scope]` (waist-up; VRM's humanoid spec still requires leg bones, so they
are authored and never framed — deliberate, not accidental; hands are the hard part, and
they are currently welded into the single body surface), and `[rig.control_surface]` — what
the app sends the avatar (`gaze_target`, `viseme_weights`, `expression_state`,
`goggle_state`, `rest_loop`). Pinning that contract early lets the app track and the mesh
track proceed independently instead of blocking on each other.

### Sequencing that falls out

1. **Teeth + tongue** — unblocks `tongueOut` and stops visemes being authored against a hole.
2. **Settle blink** — lid shape key vs modelled lids.
3. **ARKit-52 authoring pass** — once, at full resolution.
4. **Eyeball separation + lookAt bone** — the socket-rim cut.
5. **Body rig to VRM humanoid** — spine, shoulders, arms, hands; ear/tail spring bones.
6. **Garments and props** on that rig (goggles are already absent from v2 by design, so
   they arrive as a separate prop rather than needing to be carved off his skull).

### Motion preview banked

`tools/jaw_drive.py` + `mesh/canon/talktest/` — 96 frames, two angles, encoded mp4. The
driver takes a real audio file (ffmpeg → RMS envelope) or a deterministic synthetic
syllable rhythm, so it is not throwaway when a voice exists. **Jaw flap, not lipsync** —
with no visemes every phoneme looks identical. Operator has eyes on it and called it a
promising start.

---

## 2026-07-26 — ✅ BLINK RESOLVED. It is the same job as gaze, not a separate one.

Went after blink because it was the highest-value unknown and it gates the 52-shape
authoring pass — get it wrong and the whole ARKit set gets authored twice.

### Finding the socket rim the same way we found the lip seam

`tools/eye_probe.py` finds the rim as a CREASE (high-dihedral edges in the upper-front
face band) rather than guessing a z-band. Two notes on getting there, both worth keeping:

* A 28° threshold returns each rim as several ARCS, not a ring — inner corner, outer
  corner, brow. Proximity-merging clusters within 0.045 assembles them: **51 and 41 verts,
  symmetric at lateral −0.0421 / +0.0373.** The vertex-colour render shows two clean
  closed loops. That is a cut seam, exactly like the lip seam.
* ⚠️ My first sphere fit reported **"NOT spherical"** and it was an artefact of the fit,
  not a finding. I fitted to a *ball around the rim centroid*, which is mostly surrounding
  skull. Isolating the cap properly — inside the rim AND protruding past the rim plane —
  flips it to **genuine spherical domes: r = 0.0318 / 0.0288, residual 4% / 7% of radius.**
  A measurement taken over the wrong support set is not a measurement.

### The blink test failed, and the failure is the answer

Built a candidate blink as a shape key: collapse the eye region vertically toward its own
midline, 1003 verts across both eyes, smoothstep falloff. Rendered it. **It squashes the
EYEBALL along with the skin** — a distorted, still-visible eye, not a closed lid.

That is unavoidable while the mesh is welded. The dome and the surrounding skin **share
the rim**, so the skin physically cannot slide over the eye: it is attached to it. No
amount of shape-key sculpting fixes that, because the constraint is topological.

### ⭐ Consequence — two roadmap items merge

**Blink and gaze are one job.** Cut the dome free along the socket rim — the same
operation as the lip-seam cut, and we now have that tooling — and then the eyeball is
rigid and ROTATES for gaze, while the skin ring CLOSES OVER it for blink. Neither is
attemptable before the separation, and after it both are straightforward.

Full blink travel measured: **0.0531 (left) / 0.0554 (right)**, ~5.4–5.7% of body height.

### Revised sequencing

1. **Eye separation** — socket-rim cut, both eyes. Unblocks gaze AND blink together.
   (Was step 4, now first; it is a prerequisite for the authoring pass, not a follow-up.)
2. **Teeth + tongue** — unblocks `tongueOut`, stops visemes being authored against a hole.
3. **ARKit-52 authoring pass** — once, at full resolution, against a complete face.
4. **Body rig to VRM humanoid** — spine, shoulders, arms, hands; ear/tail spring bones.
5. **Garments and props.**

Artefacts: `mesh/canon/eyeprobe/` — `rim_front.png` (the detected rims, red/blue),
`blink_000/050/100.png` and `blinkwide_*` (the failed naive blink, kept as the evidence).

---

## 2026-07-26 — ✅ EYES SEPARATED. Gaze rotates and the lid closes.

`tools/eye_open.py` → `mesh/canon/clyffy_v2_eyes.blend`. New stage in the chain, between
the mouth cut and the rig.

### Three attempts at finding the cut boundary — the first two were caught by validation

1. **Crease verts directly.** The socket "rim" from `eye_probe.py` is a BAND, not a loop —
   51 verts but 58 edges and vertex degrees {1, 2, 3}. Splitting along that makes a mess.
   Caught before cutting by a degree check.
2. **Flood fill from the dome apex, crease as a barrier.** The crease band is not
   continuous at 28°, so the fill escaped: **400% of the head**. Caught by a leak check
   comparing the filled region against head vertex count.
3. ✅ **Define the dome as a FACE REGION from the sphere fit, take its boundary.** A face
   region's boundary is a closed loop by construction — the same reasoning that made the
   mouth cut work. Both eyes came out as **closed simple cycles on the first pass**
   (52 edges/52 verts, 44/44), no pinch growth needed.

**The lesson is the same one this build keeps teaching:** validate the boundary BEFORE
cutting. Two wrong approaches cost nothing because neither was allowed to touch geometry.

⚠️ Also: the region map rendered blank the first time because `bm.to_mesh(me)` was called
AFTER writing the colour attribute — the bmesh was unmodified, so it overwrote the mesh and
wiped the attribute. Do not round-trip a bmesh you did not edit.

### The separation

`split_edges` along both loops (96 edges), then each side closed with the same extrude+cap
pattern as the mouth cavity: the **eyeball** shell closed backward into a lens, and the
**skin socket** extruded deeper so the dome can rotate inside without revealing a gap.

Result: **3 connected components — body 45,856 · eye_L 585 · eye_R 397.**
Hygiene: wire 0, loose 0, non-manifold 1 (still only the pre-existing torso defect),
boundary 19 (torso). Vertex groups `eye_L` / `eye_R` written, plus object properties
`eye_{L,R}_center` and `_radius` so bone placement does not have to re-derive them.

### ✅ Gaze — rotation, as predicted

Rotating each dome about its fitted centre carries the painted iris with it. Verified on
render at ±16° yaw and ±12° pitch: both pupils track together and read correctly.

### ✅ Blink — but the naive version fails for a SECOND, different reason

Collapsing the skin toward the eye centre's **z-plane** closes it *behind* the eyeball,
whose apex protrudes a full radius in front of that plane — so the eye pokes through. That
is a different failure from the pre-separation one (where the dome squashed along with the
skin), and it would have been easy to mistake for the same thing.

Correct construction: **rotate each skin vert about the LATERAL axis around the eye centre
until its elevation reaches the midline, holding radius ≥ 1.06·r** so it passes in FRONT of
the dome. The lid slides over the eyeball.

Falloff must be **tight — reach ≈ 1.38 × dome radius**. At 2.1 × radius the brow and cheek
get dragged in and the whole face crumples. At 1.38 the closed pose reads clean and the
half-closed pose is a natural half-lid.

### Chain still builds — verified, not assumed

Re-ran `tools/jaw_rig.py` on the separated mesh. Identical results: symmetry **1.03:1**,
aperture 0.0014 → 0.0549, Σw = 1, max 3 influences, max edge stretch **3.85×**, **0 edges
over 5×**. The eye work did not disturb the jaw rig. `[pipeline]` now reads
canonical → mouth_open → **eyes_open** → rigged.

### What this unblocks

`[rig.look_at]` is fully resolved — bone-mode gaze and lid-over-dome blink both proven on
real geometry. The eight `eyeLook*` entries in the ARKit set are bone-derived, and
`eyeBlinkLeft` / `eyeBlinkRight` now have a construction that works. Step 1 of the revised
sequencing is done; **teeth + tongue** is next, and then the single ARKit-52 authoring pass
against a complete face.

---

## 2026-07-26 — ✅ TEETH + TONGUE. But first the cavity had to become an actual bag.

Planned this before writing any teeth code, and the plan changed on the first measurement.

### ⚠️ The cavity was a flat SLOT, not a bag

`tools/_mouthspace.py`: the mouth interior was **0.1846 deep × 0.1445 wide × 0.0077 TALL**.
`mouth_open.py` extruded the rim straight back while SHRINKING it (0.92 → 0.70 → 0.30),
so the pocket tapered to nothing vertically. There was no room for teeth (~0.009), let
alone a tongue. Building teeth first would have wasted the pass.

**Fix — anisotropic rings.** Profile is now `depthfrac:lateral_scale:half_height`: keep the
forward spread, taper laterally, and EXPAND vertically. A real mouth bag has volume behind
the lips while the lip line stays shut at rest. Result: **bag height 0.0077 → 0.0504**,
comfortably more than the 0.0549 aperture the jaw reaches.

Two bugs on the way there, both caught by the printed bag height rather than by eye:
* **Ring placement compounded.** Each ring was positioned relative to the previous one, so
  dividing by the rim half-height re-scaled an already-scaled z and the inward depth
  double-counted. Measured bag height **0.306** — a third of the whole body. Fixed by
  placing every ring ABSOLUTELY from its rim ancestor.
* The ancestor was first looked up by index with a fallback to `v.co` on a miss, and the
  miss path silently reintroduced the compounding. Fixed by propagating the ancestor
  POSITION alongside the lineage, so no index lookup is on the path at all.

Containment verified by rendering the closed pose from front / three-quarter / side — the
taller bag stays inside the muzzle and the lip line is unchanged.

### The parts — `tools/mouth_parts.py` → `clyffy_v2_parts.blend`

Teeth are **swept bands**, not dropped-in primitives: walk the rim loop, split at the
commissures into upper and lower chains (same chain logic as the jaw weights), smooth,
trim 10% off each end so they stop short of the corners, then sweep a rectangular profile
along the polyline into a closed solid. They follow the real lip curve. Lower band 102
faces, upper 94. Tongue is a flattened ellipsoid (0.052 × 0.075 × 0.013) resting on the
bag floor, 146 verts.

Inset **0.030 back from the rim** — deep enough that the shut lips hide everything.
Materials `clyffy_teeth` / `clyffy_tongue`, both with `diffuse_color` set as well as the
Principled input (the cavity-renders-grey lesson).

⚠️ **New bmesh verts default to 0 on int layers.** `jaw_rig` treats `cav_src >= 0` as "mouth
bag vert, skin it from its rim ancestor" — so left at the default, every tooth and tongue
vert would have been skinned from vertex 0. They are now explicitly set to **-1**.

### Rig integration

Teeth, tongue and eyeballs are **separate connected components**. A component with no
anchor makes `L_FF` singular and the harmonic solve ill-posed, so each is anchored rigidly
instead of being left to the solver: lower teeth + tongue ride the JAW (w=1), upper teeth
and both eyeballs the SKULL (w=0). Recorded in `[jaw_rig].rigid_anchors`.

### Verified — no regression from any of it

| check | value |
|---|---|
| max edge stretch @ 22° | **3.85×** (unchanged) |
| edges > 5× | **0** |
| edges with \|w0−w1\| > 0.5 | **0** |
| weight symmetry | 1.05 : 1 |
| Σw per vertex | \|1−Σw\| max 8.9e-05 |
| influences / vertex | max 3 |
| hygiene | non-manifold 1 (pre-existing torso), boundary 19, wire 0, loose 0 |

**REST POSE CLEAN** — nothing visible with the mouth shut, checked on render. Open pose
shows a dark interior with both tooth bands and the tongue reading clearly, front and 3/4.

`[pipeline]`: canonical → mouth_open → eyes_open → **parts** → rigged.

### Next

`tongueOut` is now authorable (it was `blocked` in `[rig.blendshapes]`). The face is
complete enough for the **single ARKit-52 authoring pass** — the whole reason for doing
eyes, bag, teeth and tongue first.

---

## 2026-07-26 — ✅ MILESTONE A: facial region atlas + first shapes proven from it

Operator set the cadence: **plan → execute → verify**, per milestone, no advancing until
verified. Remaining roadmap: **A** atlas + proof · **B** eye/brow shapes (11) · **C**
mouth/jaw (26) · **D** cheek/nose/tongue (6) · **E** VRM humanoid body rig · **F** VRM
export + control surface.

### Why an atlas before any shape

43 shapes have to be authored (52 minus 8 bone-derived `eyeLook*` minus bone-backed
`jawOpen`). If each one re-derives its own geometry we repeat the failure that has bitten
four times: an angle used without its space, a sphere fitted over the wrong support set, a
lip classified by z instead of by chain, an ancestor looked up by index with a silent
fallback. So regions are detected ONCE, stored as **weighted** vertex groups, and verified.

Weights are smooth falloffs, never binary — a binary region tears at its edge exactly like
the 1.0-next-to-0.0 lip rim did.

### Two defects the verify gate caught

* **`nose` produced 0 verts** and **`cheek` peaked at 0.40 instead of 1.0.** Both seeds
  were computed as offsets from a centroid and landed INSIDE the head, far from any
  vertex. Fixed by snapping seeds to the nearest skin vertex, and by defining the nose as
  a measured landmark — the most-protruding muzzle vert between the lip line and the eyes.
* **The symmetry metric was wrong.** Vertex-count ratios read 1.56:1 and looked like
  misplacement, but the eyeball domes are themselves 585 vs 397 verts: this mesh's density
  is genuinely asymmetric. Replaced with a SPATIAL test — mirror the L weighted centroid
  across the midplane and measure where it lands against R. Worst region is `lip_corner` at
  0.0148, **1.51% of body height**; all pass.

### The framework — `tools/shape_author.py`

Shapes are parameterised deformations over atlas regions. House rules enforced in code:
interior geometry (mouth bag, teeth, tongue) and the rigid eyeballs — **1576 protected
verts** — are never moved by a skin shape, and every shape reports how many protected
verts it touched. `jawOpen` is bone-backed and deliberately not authored.

### Proof: `eyeBlinkLeft` / `eyeBlinkRight`

Built from `eyelid_upper_*` / `eyelid_lower_*` using the validated lid-over-dome
construction (rotate about the lateral axis around the eye centre, hold radius ≥ 1.06r).

| check | eyeBlinkLeft | eyeBlinkRight |
|---|---|---|
| verts moved | 492 | 354 |
| max displacement | 0.0630 (6.44% of height) | 0.0537 (5.49%) |
| **protected verts moved** | **0** | **0** |

Renders confirm: rest unchanged, each blink independent, both together closes both eyes,
and the eyeball stays rigid inside the closing lid. Measured blink travel (5.4–5.7% of
height, BUILD_LOG earlier today) matches the displacement, which is a nice cross-check.

`[pipeline]`: … → parts → **atlas** → **shapes** → rigged.

**MILESTONE A: confirmed 2026-07-26** (operator gate → Grok session).

---

## 2026-07-26 — ✅ MILESTONE B: remaining eye + brow shapes off the same atlas

Nine shapes authored in `tools/shape_author.py` on top of the two blinks from A.
Same framework, same protected-vert gate, same atlas regions — no new geometry derivation.

### Shapes

| shape | verts | max disp | %H | protected |
|---|---:|---:|---:|---:|
| eyeBlinkLeft | 492 | 0.0630 | 6.44 | **0** |
| eyeBlinkRight | 354 | 0.0537 | 5.49 | **0** |
| eyeSquintLeft | 739 | 0.0433 | 4.42 | **0** |
| eyeSquintRight | 575 | 0.0376 | 3.84 | **0** |
| eyeWideLeft | 492 | 0.0380 | 3.89 | **0** |
| eyeWideRight | 354 | 0.0303 | 3.09 | **0** |
| browDownLeft | 241 | 0.0255 | 2.61 | **0** |
| browDownRight | 181 | 0.0255 | 2.61 | **0** |
| browOuterUpLeft | 241 | 0.0257 | 2.62 | **0** |
| browOuterUpRight | 181 | 0.0271 | 2.77 | **0** |
| browInnerUp | 415 | 0.0200 | 2.04 | **0** |

### Construction notes

* **lid_rotate** generalises the blink construction: amount >0 closes toward the midline,
  amount <0 opens away. `hold_front` (radius ≥ 1.06r) only on close so opens don't float.
* **eyeSquint** is lower-lid heavy (0.52) with modest upper (0.20) plus a soft cheek lift.
  First pass (0.36/0.68) read as a near-blink — iris vanished. Tuned so iris stays visible.
* **eyeWide** opens lids away from the midline (upper −0.48 / lower −0.34).
* **brow_move** weights inner/outer via a lateral Gaussian about the eye centre; a little
  outward push on raise keeps the brow from sinking into the skull.
* **browInnerUp** is the single bilateral shape (both inner brows together).

### Verify renders

* `mesh/canon/shapes/_eyesheet.jpg` — REST · blink L/R/both · squint L/R/both · wide L/R/both
* `mesh/canon/shapes/_browsheet.jpg` — REST · down L/R/both · innerUp · outerUp L/R/both
* Blend: `mesh/canon/shapes/clyffy_v2_shapes.blend` — 11 shape keys (+ Basis)

Visual: L/R independent, combos stack cleanly, eyeballs stay rigid, rest pose unchanged.
Squint keeps iris; wide rounds the aperture; brows read as hood / concern / raise on the
fur face even without a painted brow line. L is denser/harder than R throughout — mesh
density asymmetry (585 vs 397 dome verts), not misplacement.

**MILESTONE B: confirmed 2026-07-26** (operator gate).

---

## 2026-07-26 — ✅ MILESTONE C: mouth + jaw shapes (26) off the same atlas

23 mouth + 3 jaw (`jawOpen` stays bone-backed). Full library now **37 authored** shape keys
(+ Basis). Same framework, same atlas regions, plus `op_jaw_region` expanded into a smooth
falloff for the jaw set.

### Defects the gate caught on the first pass

1. **Binary jaw translate tore the lip rim.** Translating `op_jaw_region` (369 verts) left a
   hard 1.0→0.0 edge — same tear mode as the old lip rim. Fixed with `expand_falloff` over
   the lower face (~1320 verts, peak 1.00, cut off below the nose).
2. **Lower teeth / tongue / lower bag stayed frozen** under the global protected-vert rule,
   so even a soft jaw left white spikes and a gray cavity floor behind the moving lip.
   Exception: `jaw*` shapes may ride the jaw-anchored interior (teeth_lower + tongue + lower
   bag = 463 verts). Eyeballs, upper teeth, upper bag stay frozen always.
3. **Stretch / funnel / frown amplitudes too hot** — opened the lip slit onto the cavity.
   Dialled back; smiles (corner-led) were fine first try and stayed.

### C shapes (protected leaks = 0 on every one)

| group | shapes | notes |
|---|---|---|
| jaw | Forward, Left, Right | soft lower-face + jaw-ride interior; Open = bone |
| corners | Smile / Frown / Stretch / Dimple L+R | smile is the star of the set |
| vertical | UpperUp / LowerDown L+R | modest so the slit stays closed |
| press | Press L+R | pinch + slight back |
| bilaterals | Pucker, Funnel, Roll U/L, Shrug U/L, Close, Left, Right | funnel is the only deliberate open |

### Full inventory (A+B+C)

37 authored. Sheets:
- `mesh/canon/shapes/_mouthsheet.jpg` — smile / frown / stretch / dimple
- `mesh/canon/shapes/_mouthsheet2.jpg` — pucker / funnel / rolls / shrugs / L-R / press
- `mesh/canon/shapes/_jawsheet.jpg` — REST · Forward · Left · Right
- eye / brow / blink sheets refreshed under the same face frame

Blend: `mesh/canon/shapes/clyffy_v2_shapes.blend`

Bone-derived / not authored: 8× `eyeLook*`, `jawOpen`.

---

## 2026-07-26 — ✅ FULL HEAD: ARKit-52 face complete (43 authored shapes)

Operator clarified the gate is for the **full head**, not per-milestone. D was
finished in the same pass as C's close-out.

### Completeness

| class | count | notes |
|---|---:|---|
| Authored skin shapes | **43** | all of A+B+C+D |
| Bone-backed | 1 | `jawOpen` |
| Bone-derived (not authored) | 8 | `eyeLook*` via lookAt |
| **ARKit-52 total** | **52** | 43 + 1 + 8 |

### D — cheek / nose / tongue

| shape | verts | max %H | protected |
|---|---:|---:|---:|
| cheekPuff | 697 | 2.44 | 0 |
| cheekSquintLeft | 509 | 2.95 | 0 |
| cheekSquintRight | 436 | 2.53 | 0 |
| noseSneerLeft | 606 | 0.96 | 0 |
| noseSneerRight | 596 | 1.07 | 0 |
| tongueOut | 393 | 4.84 | 0 (tongue is intentionally moved) |

`tongueOut` is the only shape allowed to move the tongue mesh (normally protected).
Lips open just enough that the tongue clears the teeth line (inset 0.030 → push
~0.048H). First pass at 0.028H was invisible behind the sealed muzzle.

### Protect rules (final)

| shape class | may move |
|---|---|
| default skin | nothing in the 1576 protected set |
| `jaw*` | teeth_lower + tongue + lower bag |
| `tongueOut` | tongue only |

### Sheets (full head)

| sheet | content |
|---|---|
| `_headsheet.jpg` | overview strip across families |
| `_blinksheet.jpg` / `_eyesheet.jpg` / `_browsheet.jpg` | eye + brow |
| `_mouthsheet.jpg` / `_mouthsheet2.jpg` / `_jawsheet.jpg` | mouth + jaw |
| `_cheeknosesheet.jpg` | cheek / nose / tongue |
| `clyffy_v2_shapes.blend` | **43** shape keys + Basis |

### Rebuild

```
blender -b --python tools/shape_author.py -- \
  mesh/canon/clyffy_v2_atlas.blend mesh/canon/shapes 235.1
```

### Still outstanding (past the head) — closed below

| step | content |
|---|---|
| **E** | VRM humanoid body rig (waist-up presenter) |
| **F** | VRM export + control surface |

---

## 2026-07-26 — ✅ E: body rig (VRM-humanoid) + glTF export

Operator: gate is the full head (done); continue. Body rig built on the shapes mesh so
the 43 ARKit keys ride the same file as the armature.

### `tools/body_rig.py` → `mesh/canon/body/clyffy_v2_body.blend`

**25 bones:**
```
hips → spine → chest → neck → skull → jaw
                              ├ eye_L / eye_R
                              └ ear_L / ear_R
chest → shoulder_L/R → upper_arm → lower_arm → hand
hips  → upper_leg_L/R → lower_leg → foot   (VRM-required; never framed)
hips  → tail
```

**Weights — not bone heat.** `ARMATURE_AUTO` still returns zeros on this Tripo mesh
(see jaw_rig). Two sources:

1. **Face** — jaw / skull / root transferred by vertex index from the proven
   `clyffy_v2_rig.blend` (topology is byte-identical: 47184 verts, head+tail coords match).
2. **Body** — distance-to-bone-segment smoothstep falloffs, top-4 influences, Σw = 1.

**Head isolation (gate-caught):** first spine bend sheared the skull because body bones
still held residual weight in the head after normalise. Fix: hard fade of every non-face
bone above the neck, plus `face_dom = jaw+skull` kills body competition wherever the
transfer already owns the vert. Hierarchical skull rotation then carries the head cleanly.

### Pose tests

| pose | moved | max %H | note |
|---|---:|---:|---|
| upper_arm_L −55° | 1503 | 13.1 | sleeve lifts, no torso tear |
| upper_arm_R −55° | 1542 | 12.5 | symmetric |
| spine+chest bend | 47173 | 13.6 | skull disp std 0.018 (no shear) |
| jaw 22° | 3600 | 9.0 | face transfer intact |
| eyes +16° yaw | 982 | 1.5 | lookAt bones live |

Skin: `|1−Σw| max 2.2e-16`, max 4 influences/vert. Shape keys preserved: **44** (Basis+43).

### Renders

`mesh/canon/body/_bodysheet.jpg` — REST · arm L/R/both · spine · waist-up REST/arms  
Waist-up framing is the companion-app target.

### F — glTF export (VRM path)

No VRM addon on this Blender. Exported the intermediate that VRM is built on:

```
mesh/canon/body/clyffy_v2_body.glb   (~20 MB)
```

glTF 2.0 with skins + morph targets (the 43 shapes). Full `.vrm` with humanoid bone
mapping needs the VRM addon (`VRM_Addon_for_Blender`) — install when ready; the GLB is
the content, the VRM wrapper is metadata + bone name binding.

### Outstanding (at body-rig time)

| item | note |
|---|---|
| VRM addon → `.vrm` | closed below |
| Per-finger hands | topology is welded mittens; needs a finger cut or re-topo |
| Control surface | gaze_target / viseme_weights / expression_state driver |
| Garments/props | goggles as separate prop |

`[pipeline]` now: … → shapes → **body** (face rig kept as jaw-weight source).

---

## 2026-07-26 — ✅ F: VRM 1.0 export

Installed **VRM Add-on for Blender v4.4.0** (saturday06) into
`~/.config/blender/4.0/scripts/addons/VRM_Addon_for_Blender-release`.

### `tools/vrm_export.py`

1. Renames body_rig bones → VRM humanoid names (`skull`→`head`, `upper_arm_L`→`leftUpperArm`, …)
2. Renames matching vertex groups so the armature still binds
3. Auto-assigns VRM1 humanoid (22 bones)
4. `assign_vrm1_expressions_from_arkit` — VRM presets driven by our ARKit morphs
5. lookAt **bone** mode, offset from head
6. meta: name `Clyffy`, version `0.1.0`

### Artefacts

| file | size | notes |
|---|---:|---|
| `mesh/canon/body/clyffy.vrm` | ~72 MB | VRM 1.0 (`VRMC_vrm`) |
| `mesh/canon/body/clyffy_v2_vrm.blend` | | prepared source (renamed bones) |
| `mesh/canon/body/clyffy_v2_body.glb` | ~20 MB | earlier glTF intermediate |
| `mesh/canon/body/vrm_export_report.json` | | humanoid map dump |

### Verified in-file

- `specVersion` 1.0 · `extensionsUsed: [VRMC_vrm]`
- humanoid bones: 22 (hips→head, arms, legs, jaw, eyes)
- lookAt type `bone`
- mesh morph targets: **43** (full ARKit authored set)
- skins: 1 · joints: 25 (extras: ear_L/R, tail)
- VRM expression presets: 18 (aa/blink/happy/… — the VRM downsample; raw morphs still 43)
- Round-trip `import_scene.vrm` loads

### Not yet in the VRM (at first export)

- **Spring bones** — closed below
- **Per-finger** humanoid bones (hands are mittens)
- Control-surface live drivers (app-side contract still pinned in pack.toml)

---

## 2026-07-26 — ✅ Spring bones (VRMC_springBone) methodically authored

### Why this was its own pass

First VRM export had ear/tail as single bones and no spring extension. A single bone
cannot carry a spring joint *chain*. Also the addon's humanoid structure-search
auto-assign confuses ear/tail chains with limbs (`leftEye→ear_L`, `leftUpperLeg→tail`)
and cancels export — so humanoid mapping had to be forced explicitly and auto-assign
disabled.

### Body rig changes (`tools/body_rig.py`)

Multi-segment chains spanning the **surface** (tip = free edge on mesh, base = snapped
attachment toward skull/hips — fabricated tips past the mesh left mid/tip weights empty):

| chain | bones | weights (verts >0.05) |
|---|---|---|
| ear_L | ear_L → ear_L_2 → ear_L_3 | ~450 / 304 / 227 |
| ear_R | ear_R → ear_R_2 → ear_R_3 | ~420 / 272 / 202 |
| tail  | tail → tail_2 → tail_3 → tail_4 | ~393 / 431 / 579 / 796 |

Chain weights: envelope by distance to the polyline, partitioned with overlapping
Gaussians along the base→tip parameter. Ear chains exempt from the head face-lock so
the skull transfer cannot swallow them. Armature custom prop `spring_chains` records
the map for the exporter.

**32 bones** total on `clyffy_v2_body.blend`.

### Spring authoring (`tools/spring_bones.py`)

Idempotent: clears previous springs/colliders, then builds:

| spring | joints | center | collider groups | profile |
|---|---|---|---|---|
| ear_L | 3 | head | head | stiff 1.8→0.55, light gravity |
| ear_R | 3 | head | head | same |
| tail  | 4 | hips | body + head | stiff 1.4→0.25, heavier gravity |

Colliders (spheres):
- `col_head` + `col_muzzle` on `head` (ears don't swing through the skull/face)
- `col_hips` on `hips` (tail doesn't fold into the pelvis)

Joint params ease tipward (stiffness↓, hit_radius↑, gravity_power↑) — free end leads.

### Export path (`tools/vrm_export.py`)

1. Rename humanoid bones (skull→head, upper_arm_L→leftUpperArm, …)
2. **Force** humanoid map via `HumanBoneName` enum; clear optional junk; set
   `initial_automatic_bone_assignment = False`
3. ARKit expressions + lookAt bone
4. `author_spring_bones(arm)`
5. Force humanoid again (structure search can re-taint candidates)
6. Export → `FINISHED`

### Verified in `clyffy.vrm`

```
extensionsUsed: [VRMC_vrm, VRMC_springBone]
VRMC_springBone spec 1.0
  springs: ear_L (3), ear_R (3), tail (4)
  colliders: 3   colliderGroups: head, body
humanoid leftEye/leftUpperLeg/head correctly assigned (not ears/tail)
morph targets: 43   lookAt: bone
```

Rebuild:
```
blender -b --python tools/body_rig.py -- \
  mesh/canon/shapes/clyffy_v2_shapes.blend mesh/canon/clyffy_v2_rig.blend \
  mesh/canon/body 235.1
blender -b --python tools/vrm_export.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/clyffy.vrm
```

---

## 2026-07-26 — Mouth rest seal + jaw-open re-verify

Operator caught that fully-open looked wrong and rest showed teeth — should have
been gated on the shapes head. Investigation, then a fix pass.

### Diagnosis

* Rest mesh coords were **byte-identical** across parts → shapes → body. Not a
  body-rig drift problem.
* Jaw bone + jaw weights on body match the proven `clyffy_v2_rig` (max weight
  error ~0.04; open max disp both ~0.088–0.090).
* Rest teeth peek was a **viewing tunnel**: lip-rim gap median **0.0065** (0.66%H),
  mostly forward not vertical. Teeth sit ~0.025 behind the rim but the camera
  still saw them through the slit.
* First seal (amount 0.90, rim only) closed the gap but left a **bright white
  crease** under studio light. Dimming teeth materials did not remove it — that
  line is specular on the sealed edge, not enamel.

### Fix — `tools/lip_seal.py`

Run on parts (SSOT), then rebuild atlas → shapes → body → jaw_rig → vrm.

| step | value |
|---|---|
| Close gap toward midplane | amount **0.85** |
| Forward bulk on both lip chains | **0.25%H** (thick flesh pad, not knife-edge) |
| Soft skin falloff | **1.8%H** reach, 179 verts |
| Teeth inset along −fwd | **0.8%H** extra depth |
| Post-seal gap median | **0.0011** (0.11%H) — **83% reduction** |

Shape keys re-authored on sealed rest (43 shapes, 0 protected leaks).

### Verify (body after full rebuild)

| pose | note |
|---|---|
| REST | slit mostly closed; residual bright crease under Workbench studio is the
|  | sealed edge, not teeth (confirmed by dimming teeth mats) |
| jaw 22° open | dark bag + tooth bands + tongue; max disp **0.090** (9.2%H); matches
|  | re-run jaw_rig on sealed parts |

Sheets: `mesh/canon/shapes/mouthdiag/cmp_{shapes,body,jawrig}_{REST,OPEN22p}.png`

### Rebuild after seal

```
blender -b --python tools/lip_seal.py -- \
  mesh/canon/clyffy_v2_parts.blend mesh/canon/clyffy_v2_parts.blend 235.1 0.85 0.0025
blender -b --python tools/face_atlas.py -- mesh/canon/clyffy_v2_parts.blend mesh/canon 235.1
blender -b --python tools/shape_author.py -- mesh/canon/clyffy_v2_atlas.blend mesh/canon/shapes 235.1
blender -b --python tools/body_rig.py -- \
  mesh/canon/shapes/clyffy_v2_shapes.blend mesh/canon/clyffy_v2_rig.blend mesh/canon/body 235.1
blender -b --python tools/jaw_rig.py -- mesh/canon/clyffy_v2_parts.blend mesh/canon 235.1
blender -b --python tools/vrm_export.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/clyffy.vrm
```

### Remaining cosmetic

Workbench studio lighting still paints a thin highlight on the sealed lip crease.
Product lighting / a slightly softer seal amount can tune that further; geometry
and teeth depth are now correct for rest vs open.

---

## 2026-07-27 — ✅ ALPHA: control surface + ARKit drive

Mouth rest seal accepted as alpha-good. Remaining mesh/VRM work parked; control
surface and drive implemented so the companion app has a real contract to target.

### Alpha status

| layer | state | artifact |
|---|---|---|
| Mesh pipeline | ✅ sealed parts → atlas → 43 ARKit shapes | `shapes/clyffy_v2_shapes.blend` |
| Body rig | ✅ 32 bones (VRM humanoid + ear/tail chains) | `body/clyffy_v2_body.blend` |
| Spring bones | ✅ ears L/R + tail | in VRM |
| VRM 1.0 export | ✅ humanoid 22 + morphs 43 + lookAt bone | `body/clyffy.vrm` |
| Control surface | ✅ JSON contract + apply | `tools/control_surface.py` |
| Avatar drive | ✅ jaw bone + ARKit visemes + gaze | `tools/avatar_drive.py` |
| Per-finger hands | ⏸ alpha skip (welded mittens) | — |
| Goggle prop mesh | ⏸ alpha skip (state logged only) | — |
| Voice model | ⏸ out of avatar-mesh track | — |
| Phone surface | ⏸ out of avatar-mesh track | — |

### Control surface (`tools/control_surface.py`)

Pinned inputs from `[rig.control_surface]`:

| input | alpha binding |
|---|---|
| `gaze_target` | eye_L/R bones (yaw/pitch deg or world point) |
| `viseme_weights` | ARKit mouth keys + **jawOpen → jaw BONE** (never a shape key) |
| `expression_state` | named presets (happy/sad/angry/surprised/thinking/talk) or raw weights |
| `goggle_state` | logged only — prop mesh not authored |
| `rest_loop` | zeros all drives (rest-state law) |

```
python3 tools/control_surface.py examples mesh/canon/body/control
blender -b --python tools/control_surface.py -- apply \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/control 235.1 \
  mesh/canon/body/control/state_surprised.json surprised
```

Sheet: `mesh/canon/body/control/_controlsheet.jpg`  
(rest · happy+lookL · surprised · talk aa)

### Drive (`tools/avatar_drive.py`)

Replaces jaw-only flap with viseme schedule + jaw bone + gaze drift + rest hold.

```
blender -b --python tools/avatar_drive.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/drive 235.1 --synth 3.0
```

Demo: `mesh/canon/body/drive/alpha_talk.mp4` (72 frames @ 24fps, rest-hold last 0.4s)

Visemes (shared live + episode): sil PP FF TH DD kk CH SS nn RR aa E I O U  
→ ARKit mixes in `control_surface.VISEMES`.

### Alpha deferred (explicit)

1. **Fingers** — topology is welded mittens; needs cut/re-topo before per-finger bones.
2. **Goggles prop** — state machine is specified; mesh prop is not.
3. **True phoneme lipsync** — drive is envelope + viseme rhythm, not ASR phonemes.
4. **Lip crease specular** under Workbench studio — product lighting / softer seal.

---

## 2026-07-27 — Presentable beauty pass (leave Workbench behind)

Operator: diagnostic Workbench stills are not alpha-presentable. Added
`tools/present.py` — EEVEE beauty with canon lighting.

### Look
* Engine: **EEVEE** 128 TAA (Cycles CUDA kernels fail to compile on this GB10)
* Lights: warm key · steel-blue fill · amber rim · teal bounce
* World: near-black DPN studio
* Materials: mild SSS on body, polished teeth, dark cavity
* Color: Filmic Medium Contrast, exposure −0.35
* Frame: 1080×1350 (4:5 waist-up companion)

### Heroes
`mesh/canon/body/present/`
* `hero_rest.png` · `hero_happy.png` · `hero_surprised.png`
* `hero_talk_aa.png` · `hero_thinking.png` · `hero_angry.png`
* `_herosheet.jpg` — contact sheet

```
blender -b --python tools/present.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/present 235.1 \
  rest happy surprised talk_aa thinking angry
```

## 2026-07-27 — Blender 5.2.0 LTS on GB10 (Cycles CUDA fixed)

### Problem
Ubuntu package `blender` 4.0.2 aarch64 cannot compile Cycles CUDA kernels for
**sm_121** (NVIDIA GB10). That was a Blender age problem, not a broken CUDA stack
(vLLM / torch already use this GPU fine).

### Fix
Installed **Blender 5.2.0 LTS** unofficial aarch64 build built for DGX Spark / GB10
(CUDA + OptiX):

* Source: CoconutMacaroon/blender-arm64 release `v14-5.2.0`
* Install root: `/opt/blender-5.2.0/`
* Wrapper (sets `LD_LIBRARY_PATH` for `libExt`): `/opt/blender-5.2.0/blender-wrapper.sh`
* PATH: `/opt/bin/blender`, `/usr/local/bin/blender` → wrapper
* System deps: `libgflags2.2`, `libmetis5`, `libgoogle-glog0v6t64`
* Fixed broken bundled numpy: reinstalled manylinux wheel `numpy==2.2.6` into
  Blender's Python 3.13 (`ensurepip` + `pip install`)
* VRM addon linked into `~/.config/blender/5.2/scripts/addons/` and enabled

### Verified
```
$ blender --version
Blender 5.2.0 LTS

$ # Cycles sees CUDA_NVIDIA GB10; 256² / 32 spp render OK in ~0.5s
Cycles CUDA device: NVIDIA GB10
```

Kernel present: `kernel_sm_120.cubin.zst` (Blackwell family; GB10 compute 12.1).

### Pipeline
* `tools/present.py` now **prefers Cycles CUDA**, falls back to EEVEE
* `clyffy.pack.toml` `[rig.present]` engine = `CYCLES`, blender path recorded
* Project helper: `source tools/blender_env.sh` (optional; `/opt/bin` already early in PATH)

Ubuntu apt blender 4.0.2 remains at `/usr/bin/blender` but is **not** on the default
`which blender` path.

### Beauty re-render (Cycles CUDA, 2026-07-27)
Full hero set rebuilt on Blender 5.2 / GB10 Cycles+OptiX denoise (~18s total):

`mesh/canon/body/present/`
* hero_rest / happy / surprised / talk_aa / thinking / angry (1080×1350 PNG)
* `_herosheet.jpg` contact sheet

```
blender -b --python tools/present.py -- \
  mesh/canon/body/clyffy_v2_body.blend mesh/canon/body/present 235.1 \
  rest happy surprised talk_aa thinking angry
```

## 2026-07-27 — Pack v0.1-talk-ready (voice-open gate)

Established offline talk-ready pack so local `voice.tts` can start without inventing a face API.

### Operator pins
* Voice gate = offline freeze + drive contract only (no live VRM viewer first)
* First voice home = local GB10 TTS slot (`voice.tts`)

### Delivered
* `clyffy.pack.toml` `[pack] version = "0.1.0-talk-ready"` · expanded `[voice]` · drive contract v1 notes
* `STATUS.md` · `MAP.md` · `README.md`
* `tools/rebuild.sh` · `tools/accept.py` · `tools/viseme_sheet.py`
* `tools/avatar_drive.py` always writes `drive_frames.jsonl` + mp4
* Viseme sheet: `mesh/canon/body/control/_visemesheet.jpg` (15 VISEMES)
* Drive: `drive_frames.jsonl` · `alpha_talk.mp4` (synth) · `audio_proof.mp4` (wav path)
* VRM re-export on Blender 5.2 OK (~75 MB); humanoid + spring bones intact
  (Blender process may crash on *exit* after export; file still written — watch `/tmp/blender.crash.txt`)

### Gate
```
python3 tools/accept.py   # GREEN
```
G1–G7 green → **local voice job open**.

## 2026-07-27 — Phase V: local voice.tts (OuteTTS scaffold)

### Backend
* Binary: `/home/hades/llama-cpp-roce/build/bin/llama-tts`
* LLM: `work/voice/models/OuteTTS-0.2-500M-Q5_K_M.gguf`
* Vocoder: `work/voice/models/WavTokenizer-Large-75-F16.gguf`
* Speaker: llama-tts built-in en_male_1 (external json unavailable in current OuteTTS tree)
* Adapter: `tools/voice_tts.py` (slot name `voice.tts`)

### Samples (pack sample_lines)
`work/voice/samples/00_…` … `04_…` — mono 24 kHz wav  
Each driven: `work/voice/drive/<slug>/alpha_talk.mp4` + `drive_frames.jsonl`

```
python3 tools/voice_tts.py --from-pack --no-speaker
```

### Status
v0 **scaffold** for operator A/B — not a trained identity clone. Platform clone still gated.

### Go pass — audio mux (same day)
* `avatar_drive.py` muxes source wav into `alpha_talk.mp4` (h264+aac) when not `--synth`
* Re-muxed all five voice drives; pack demo = signature line with audio
* Reel: `work/voice/drive/_all_lines.mp4`


## 2026-07-27 — Full-body framing (+ a corrected false finding)

### Operator ask
"due to the simplicity of clyffys shape we can go ahead and probably have his alpha include legs"

### What was actually wrong
**Nothing in the mesh.** Clyffy already had legs and cloven hooves, in geometry AND rig.

My first probe measured lateral separation along **world X** and found none — concluding
the lower body was a fused blob. That probe was invalid: the character is canonicalized at
**FWD = 235.1°**, so the lateral axis is `lat = [-fwd[1], fwd[0], 0] = [-0.573, -0.820, 0]`.
Projecting onto world X folds the fore-aft depth into the measurement and welds the two
legs into one apparent mass.

Re-probed on `lat`, `clyffy_v2_body.blend`:

| frac of height | span | max gap | |
|---|---|---|---|
| 0.78 | 0.3048 | 0.0041 | fused |
| 0.80 | 0.2922 | 0.0057 | fused |
| 0.85 | 0.2513 | 0.0299 | **SPLIT** |
| 0.90 | 0.2263 | 0.0790 | **SPLIT** |
| 0.94 | 0.2540 | 0.0819 | **SPLIT** |

Canon (`Clyffy_BASE-NEUTRAL-v1.png`, front view, gridded) puts the crotch at ~0.78 and the
hoof line at 0.94. The mesh agrees. The pack's `"legs authored ... never framed"` was
literally accurate — geometry and bones existed; only the camera never showed them.

**Discarded:** a `tools/legs.py` stage written against the false premise. It reshaped
correct legs into thinner ones. Deleted along with its `clyffy_v2_legs.blend` output.
No frozen pipeline artifact was modified.

### Delivered — framing only
* `tools/present.py --full` — focus at body centre, `dist = 2.80H` (85mm on 36mm sensor →
  23.9° vertical FOV, so 1.12H needs 2.64H; 2.80H adds clearance). Writes `full_*.png`
  and `_fullsheet.jpg`. Default waist-up path untouched and verified unregressed.
* `tools/avatar_drive.py --full` — `ortho_scale 1.12H`, centre at body mid, renders
  `front_full/`, and the mp4 mux now follows the render tag instead of hardcoding `front`.
  `--full` is stripped before positional parsing, since the audio positional may itself
  be the literal `--synth`.

### Open, accepted as a starting point
* **F1** `present.py` light POSITIONS are still face-anchored (only `focus` moved) → legs
  underlit at full-body, amber rim does not reach the hooves.
* **F2** leg weights hips-dominated: `hips` max 0.850 / 32856 verts vs `upper_leg_L` 0.315,
  `lower_leg_L` 0.481, `foot_L` 0.389. Never posed or tested. Blocks leg animation.
* **F3** voice take C (Mark, speech_rate +18 / loudness +14 / pitch +1) driven and
  reviewed, but it is a PLATFORM voice against `tts_target = "local-gb10-first"`.
  Commitment level not yet recorded.

### Method note
Probe any lateral/bilateral property on `lat`, never on world X. The 235.1° canonical
transform makes axis-aligned reasoning silently wrong rather than obviously wrong.

## 2026-07-27 — F1 / F2 / F3 worked methodically (operator directive)

### F1 — full-body light rig
**Corrected diagnosis.** First call was "lights are face-anchored". They were not — the
rig is built from `face = Vector(focus)` and already tracked focus to body centre. The
real cause was SCALE: the rig was tuned against the waist-up crop, so with the hooves
~0.5H below focus the key (at `focus.z + 0.40H`) fell off down the legs, while the teal
bounce that should lift them ran at 6.0 against the key's 28.0.

Fix — scale the rig to the framing in `present.py`:
* `LR = 1.60` (FULL) / `1.00` — rig radius and source sizes
* `EN = LR²` — inverse-square compensation so exposure holds
* `TEAL_BOOST = 2.5` — teal is the light nearest the legs
* `RIM_Z 0.30 → 0.12`, `RIM_SZ 0.70 → 1.30` — amber rim reaches the hooves

Measured: legs p90 **160** vs head/chest 135 (falloff inverted, legs now at least as lit).
Waist-up regression vs the FROZEN `hero_rest.png`: mean **0.003/255**, max 1, **0.00%** of
pixels differ by >4 — denoiser noise. `LR=1.0` restores the original constants exactly.

### F2 — leg weights (structural)
Root cause, `body_rig.py`:
```
W["hips"] = np.maximum(W.get("hips", ...), w_root * 0.85 * (1.0 - head_hard))
```
`w_root` is the jaw_rig group *"body remainder under the head"* — which **includes the
legs**. hips got a blanket 0.85 claim over the whole leg chain and outvoted every leg
bone after normalisation.

Fix — gate the fold off below the hip joint using the same smoothstep idiom as
`head_hard`, leaving hips' own Gaussian segment (`SEG["hips"]`) intact:
```
leg_soft  = smoothstep(clip((hips_z - z) / (H*0.06), 0, 1))
root_fold = w_root * (1 - head_hard) * (1 - leg_soft)
```

| metric | frozen | F2 |
|---|---|---|
| `upper_leg_L` max | 0.315 | **1.000** |
| `lower_leg_L` max | 0.481 | **1.000** |
| `foot_L` max | 0.389 | **1.000** |
| hips coverage | 32856 verts | 28780 verts |
| thigh +35°, leg mean disp | 0.70 %H | **2.26 %H** |
| thigh +35°, leg max disp | 11.0 %H | **19.3 %H** |
| torso bleed | 0.00 %H | 0.00 %H |

Weights are not the proof — motion is. Torso bleed stayed at zero, `Σw = 1.000000`,
max 4 influences/vert.

**Promoted** to `mesh/canon/body/`. Rollback: `clyffy_v2_body.bak.blend`, `clyffy.vrm.bak`.
VRM re-exported: humanoid `correctly_assigned=True n=22`, springs `ear_L/ear_R/tail` intact.
`accept.py` GREEN.

### F3 — voice commitment
Operator picked take **C** (seed_audio, preset Mark, `speech_rate +18 / loudness_rate +14 /
pitch_rate +1`) and pinned its meaning: **reference target for the local GB10 slot, not the
backend**. `tts_target = "local-gb10-first"` unchanged; no clone of `voice:VOICE-CORPUS (redacted)`
created or authorised. Recorded in pack `[voice].identity_ref` and `work/voice/SAMPLES.md`.

Note: Higgsfield presets cannot be blended, so "Mark with Zane energy" was realised as Mark
driven on tuning params; a straight Zane take (`D_zane_ref.wav`) is kept so the intended
energy stays auditable.

## 2026-07-27 — Live window: working iteration (+ a spec violation fixed at the source)

### The VRM was NOT VRM-conformant, and had never been
`clyffy.vrm` faced **+55.1° off +Z** — the Blender authoring yaw (`FWD 235.1°`) was never
baked out at export. Every `accept.py` check passed anyway, because they all measured
byte sizes and bone COUNTS. An off-spec VRM still weighs 75 MB and still has 22 bones.

Downstream it read as two separate-looking bugs that were one root cause:
1. the avatar rendered in **3/4 view** instead of front-on, and
2. a consumer rotating the jaw about world X got a **pitch/yaw mix**, so the muzzle barely
   opened while the **teeth swung sideways out through the lip**.

Fixed in `tools/vrm_export.py`: yaw the rig by `-FWD` about Blender Z before export
(the mesh is parented to the armature, so the exporter bakes it into the root node TRS —
no destructive transform-apply on a 44-shape-key mesh).

### ⚠️ L/R BONE NAMES ARE MIRRORED — open defect, cost an export cycle
`body_rig.py:126` comments `# side: -1 left (neg lat), +1 right`, but with
`lat = [-fwd[1], fwd[0], 0]`, **+lat IS the character's left**. So `leg_chain(-1)` — named
`L` — sits on his RIGHT. Consequences:
* `leftUpperLeg` / `leftFoot` / `leftHand` etc. are on the wrong side in the VRM humanoid.
  Any consumer that mirrors or retargets animation gets it backwards.
* A forward vector built as `cross(leftLeg - rightLeg, up)` comes out **inverted**. My
  first orientation probe did exactly that, reported "SPEC-COMPLIANT ✓" at `facing 0.00°`,
  and the renderer showed **the back of his head**. One wasted export cycle.

**Measure facing from the EYE bones, never from L/R legs.** That is now enforced in
`tools/vrm_check.py`. The mirroring itself is NOT fixed — see STATUS.md.

### tools/vrm_check.py — new conformance gate, wired into accept.py
specVersion · 17 required humanoid bones · **facing from head→eyes, ±5°** · expression
presets · spring bones · named morph targets. Pure-python GLB parse, no Blender.

```
vrm_check GREEN   facing -2.89° off +Z (head->eyes [-0.050 0 +0.999])
```

### Renderer (interfaces/clyffy-avatar in the clyffy repo)
* `VRMUtils.removeUnnecessaryVertices` / `combineSkeletons` **disabled** — they rewrite
  vertex/joint indices, and with the teeth on their own primitive that detached them from
  the jaw. This was a real contributing cause, found before the orientation bug.
* Removed the `vrm.scene.rotation.y = Math.PI` hack — it was compensating for the off-spec
  export, and rotating the SCENE never fixes the BONE axes, which was the actual damage.
* `?autoplay=1` + peak witnesses in `document.title` so the drive can be verified from a
  screen capture without depending on click timing.

### Verified — live, on the real GPU
```
clyffy — live face | peakEnv=0.88 peakJaw=0.79 visemes=aa,O,E
```
`peakJaw` tracks the contract's `aa` jawOpen (0.85) scaled by envelope. Front-on framing,
mouth articulates across the utterance, **teeth stay inside the mouth**, 60 fps.

### Method note
Isolate rig-vs-renderer before touching either: `tools/control_surface.py apply` with
`jawOpen=0.85` rendered CLEAN in Blender, which proved the rig was fine and the fault was
downstream. That one render saved rewriting the jaw rig.

## 2026-07-27 — L1 CLOSED: L/R bone names were mirrored

### Confirmed before changing anything
The defect was found by accident (a facing probe built on L/R legs reported a false
"spec-compliant"), so it was verified independently before touching the rig — sign of each
humanoid pair's X against the EYE-derived facing on the shipped VRM:

```
facing (from eyes) = [-0.050 0 +0.999]   => model faces +Z => model's LEFT is +X
  leftUpperLeg  x=-0.0617   rightUpperLeg  x=+0.0752   MIRRORED
  leftUpperArm  x=-0.1908   rightUpperArm  x=+0.1873   MIRRORED
  leftEye       x=-0.0260   rightEye       x=+0.0389   MIRRORED
  leftFoot      x=-0.0617   rightFoot      x=+0.0752   MIRRORED
  leftShoulder  x=-0.0624   rightShoulder  x=+0.0700   MIRRORED
=> 5/6 pairs mirrored
```

Root cause: `lat = [-fwd[1], fwd[0], 0]` is fwd rotated +90° about Z, which IS the
character's left (face north, west is your left). `body_rig.py` used `side = -1` for "L"
— its own comment said `-1 left (neg lat)` — so every `_L` bone was authored on his RIGHT.

### Fix — labels, not geometry
`SIDE_L, SIDE_R = +1, -1` applied at all four side helpers (`shoulder`, `hand_tip`,
`leg_chain`, `ear`), plus the upstream mirrored eye custom-props swapped at the point of
consumption. **Nothing upstream of `body_rig` was regenerated** — the mesh was always
correct, only the naming was wrong, so the 43 ARKit shapes and the jaw rig are untouched.

### Verified
* all 6 humanoid pairs correctly sided (`leftUpperLeg +0.0752` vs `rightUpperLeg -0.0617`)
* blend-level: pure swap — `hand_L` lateral `-0.2868 → +0.2544`, weights following (563↔585),
  both inside the mesh lateral extent `-0.3018 .. +0.2663`
* `Σw = 1.000000`, max 4 influences/vert; arm-raise displacements traded sides (1503↔1542)
* `vrm_check` GREEN, `accept.py` GREEN
* renderer re-verified live: `peakEnv=1.00 peakJaw=0.85 visemes=aa,O,E,nn,sil`, front-on,
  teeth contained, no regression

Promoted. Rollback: `clyffy_v2_body.pre-l1.blend`, `clyffy.vrm.pre-l1`.

### Unresolved measurement quirk (not an asset defect)
My VRM-space node walk puts the hands at ±0.38 while the blend has them at ±0.26; legs and
arms agree between the two. The L/R ORDERING the check relies on is a sign comparison and
is unaffected, and the blend is authoritative — but the absolute VRM hand figure should not
be trusted until the node walk is reconciled (likely bone-direction reorientation applied
by the VRM addon on export).

### Harness note
Two stale Chromium windows accumulated across capture cycles and `xdotool ... | tail -1`
picked the OLD one — three "no speech" results were driving a dead window with a stale
build. Always `head -1` after killing, or match on window geometry.

## 2026-07-27 — L2: the state channel (clyffyd -> live face)

### Built — `interfaces/clyffyd/src/avatar.rs` (clyffy repo)
* `AvatarState` serialises to EXACTLY the contract's state keys (`expression_state`,
  `gaze_target`, `rest_loop`, `goggle_state`). `viseme_weights` is absent BY DESIGN — the
  renderer owns it. A unit test asserts the key set so the split cannot rot.
* Broadcast channel **with a retained value**: avatar state is a CONDITION, not a log, so
  the current value is replayed to every new subscriber. Without it a face that connects
  between transitions holds a stale expression for an unbounded time.
* `WorkGuard` — RAII. `begin_work()` lowers the goggles; the guard is MOVED into the SSE
  response stream so it drops on completion AND on client disconnect. A dropped connection
  must not strand the face mid-work. Refcounted, so two overlapping jobs do not pop the
  goggles up when the first finishes.
* Canon honoured: `[animation.goggles]` — goggles down IS the commit-to-work transition, so
  work needs no spinner. `[animation] law` — `rest_loop` true whenever not working.

`GET /avatar/state` (SSE) sits beside `/healthz`, outside the auth layer: it carries no user
content, only four fields describing whether clyffy is busy.

Brain readiness PUSHES to the face — the channel is created before the actor spawns and
threaded into `brain_actor`/`brain_loop`, so `Ready` → `Listening` and boot/ring failure →
`Unavailable` emit frames instead of waiting for an unrelated transition.

### Renderer
Applies the contract's **layering** in its documented order: `expression_state` base →
`viseme_weights` max-merge → `rest_loop` zeros all. Local audio overrides `rest_loop` (if it
is speaking it is not resting). Daemon gaze honoured with idle drift on top. No daemon →
HUD reads `no daemon`, idle stand-in takes over, `EventSource` reconnects itself.

### Verified
* `cargo check -p clyffyd` — **zero warnings**, zero errors
* `cargo test -p clyffyd avatar::` — **7/7 green**
* renderer vs a mock emitter on :8788 — HUD tracked the 3s toggle exactly:
  `linked/rest/on-face` → `linked/thinking/lowered` → `linked/rest/on-face` → `linked/thinking/lowered`

### NOT verified — and why
The RUNNING clyffyd (PID 2758055, brain ready on the ring at :8091) is the PRE-CHANGE
binary: `/avatar/state` returns 404. End-to-end needs a rebuild and a restart of the
operator's live brain service — not something to do unasked. The mock emits byte-identical
frames to `avatar.rs`, so the consumer half is proven; the producer half is proven by unit
tests, not by a live socket.

### Warnings are signal, not noise
Two `dead_code` warnings appeared and BOTH were real incomplete work: `Activity::Unavailable`
was never constructed (fixed by actually wiring brain readiness), and `frame_json` was
test-only (deleted; the test serialises directly). Neither was silenced.

## 2026-07-27 — L2 verified END-TO-END on the live stack (+ a real outage, worked and recovered)

Operator authorised bringing the ring down (pre-release). Rebuilt clyffyd, restarted it with
the running instance's own env captured from `/proc` (never echoed into a command), and
verified the state channel against the real 120B.

### Verified on real infrastructure
```
avatar state during a REAL /code job on the 120B:
  on connect    expression=rest      goggles=on-face  rest_loop=True   gaze_pitch=0.0
  job started   expression=thinking  goggles=lowered  rest_loop=False  gaze_pitch=-4.0
  job ended     expression=rest      goggles=on-face  rest_loop=True   gaze_pitch=0.0
```
Renderer HUD against the live daemon: `linked / rest / on-face` → `linked / thinking /
lowered` while the 120B generated → back to rest when it finished. Real generation
confirmed (`event: answer  data: ready`).

### OUTAGE — the 120B ring went down, and why
The first real `/code` request killed the ring. Root cause was NOT the request:
```
RuntimeError: Worker failed with error
'[gloo/transport/tcp/pair.cc:538] Read error [100.110.101.39]:23690: Connection reset by peer'
```
A cross-node worker link dropped on the gloo control plane → `EngineCore_DP0` died →
`ApiServer_1` died. The request was the workload that exercised a fragile inter-node link.

**The restart then failed** with `NCCL error: unhandled system error` during DP group
formation. Cause was D38 GID drift — measured, not guessed:
```
clyffy-01  rocep1s0f1    idx3 = 0000:...:0000   NULL   <-- hole
clyffy-01  roceP2p1s0f1  idx3 = 0000:...:0000   NULL   <-- hole
clyffy-02  rocep1s0f1    idx3 = NULL
clyffy-02  roceP2p1s0f1  idx3 = NULL
clyffy-03  all four rails OK
```
`NCCL_IB_GID_INDEX=3` must be RoCEv2-IPv4 on EVERY rail. Ran
`clyffy-roce-gidfix.service` on 01 and 02 (03 was clean) → all 12 rails RoCE v2 → trio
restarted → **:8091 up after ~400s, 0 QP failures**, real generation working.

This is the third recorded instance of D38 drift. It happens during OPERATION, not just at
boot, and the boot-time unit does not catch it. A periodic verify (or a pre-flight check in
the trio unit's ExecStartPre) would turn a 20-minute debug into an automatic repair.

### CORS — a gap the mock had hidden
The renderer showed `no daemon` against the real daemon while working perfectly against the
mock. The mock set `Access-Control-Allow-Origin: *`; clyffyd did not. The face is always
cross-origin (renderer origin vs `:8787`), so `EventSource` was blocked. Added the header to
`/avatar/state` — `*` is right here: no user content, no credentials, already outside the
auth layer. **Lesson: a mock that is more permissive than production hides integration bugs.**

### Harness note
Chromium accumulated stale windows again and `xdotool | head -1` picked a dead one, which
produced a misleading `no daemon` capture BEFORE the CORS fix was even in. Kill all windows
and assert the count is 0 before capturing.

### Secret hygiene
`CLYFFY_CONNECTOME_PASS` was printed into the session transcript while reading the running
daemon's environment. The env file used for the restart was shredded afterwards, but the
value is in the transcript — **rotate it.**

## 2026-07-28 — L3: the desktop companion window

Tauri 2 shell at `interfaces/clyffy-avatar/shell`. Installed the Linux prerequisites
(`libwebkit2gtk-4.1-dev` 2.52.3 + gtk/appindicator/rsvg/patchelf).

**Window contract** — the shell owns placement and nothing else:
transparent · frameless · `alwaysOnTop` · `skipTaskbar` · `focus:false` (appearing must
never steal focus from what the operator is typing) · bottom-right computed at RUNTIME from
the current monitor in physical pixels, so it survives a resolution or monitor change.

**Excluded from the cargo workspace** (`Cargo.toml` `exclude`) — Tauri pulls ~500 crates and
nothing depends on this leaf; making it a member would tax every root `cargo check`.

### Two failures worth recording
1. **Empty transparent window.** WebKitGTK's DMABUF renderer failed with
   `DRM_IOCTL_MODE_CREATE_DUMB: Permission denied` / `Failed to create GBM buffer`, and the
   result renders as a fully transparent hole — visually identical to "the app never
   started". Checked before assuming: ACLs DO grant this user rw on `/dev/dri/card0` AND
   `renderD128`, so it is not a plain permission problem but the known WebKitGTK-on-NVIDIA
   DMABUF path. `WEBKIT_DISABLE_DMABUF_RENDERER=1` fixes it and is now set BY THE SHELL
   before WebKit initialises — a required env var that lives only in shell history is a bug.
2. **`devUrl` beat `frontendDist`.** With both set, `tauri-build` did not embed the frontend
   (4.15 MB binary) and the webview tried the dead vite server: "Could not connect to
   127.0.0.1: Connection refused". Removing `devUrl` embedded the assets (14.4 MB) and it
   loaded offline.

### Verified
* window composited on the desktop, wallpaper/icons visible THROUGH it
* `_NET_WM_STATE_ABOVE, _NET_WM_STATE_SKIP_TASKBAR, _NET_WM_STATE_SKIP_PAGER`
* `0` GPU errors
* live SSE link: `WebKitNetworkPr ESTAB 127.0.0.1:xxxxx -> 127.0.0.1:8787`
* self-configuring — launched with NO env var set by hand and rendered correctly

## 2026-07-28 — Lipsync: text-driven visemes + coarticulation (the "robotic" fix)

### Measured the problem before touching anything
```
shipped drive (energy buckets):
  distinct visemes used : 4  of 15 pinned
  NEVER FIRED           : PP FF TH DD kk CH SS RR I U
  distinct morphs driven: 6
```
The mouth could only open and close. No lip closures (PP/FF), no sibilants (SS/CH), no
rounding (U), no spreading (I). **The rig was never the problem** — the derivation was.
Energy has no idea what sound is being made; it only knows how loud it is.

### Fix — two parts, both in the contract SSOT
1. **`GRAPHEME_VISEMES` + `text_to_visemes()`** in `control_surface.py`. When the line is
   scripted (episodes, demos) or the text is known before TTS speaks it (clyffy writes the
   words, then voices them), text is a far better source than energy. Longest-match digraphs
   first ("sh" must not read as s+h); doubled letters collapse (the mouth holds, it does not
   re-articulate). Per-viseme relative durations so vowels carry the syllable and stops stay
   brief. Contract v1 anticipated exactly this: "Phoneme/ASR later plugs the same
   viseme_weights field — no schema fork."
2. **`ENVELOPE.coartic`** — attack 45ms / release 75ms / carry 0.28, asymmetric on purpose
   (lips reach a target faster than they leave it). Spans contribute trapezoids that
   MAX-merge, and `carry` bleeds the neighbouring shape in — which is what coarticulation
   physically IS: the lips are already moving toward the next sound before the current ends.
   Without this the face steps discretely between shapes and reads robotic no matter how
   good the shapes are.

`avatar_drive.py --text "..."` lays the viseme sequence over the envelope's VOICED runs
(not real forced alignment — no phoniser here; it is a deliberate approximation for a
stylised muzzle at 24fps). Without `--text` the old energy path runs unchanged.

### Result on the same audio
| | before | after |
|---|---|---|
| distinct visemes | 4 | **14** |
| distinct morphs driven | 6 | **11** |
| viseme spans | — | 91 |
| frames at rest | 40.4% | 37.5% |

All 14 non-sil visemes fire: `CH DD E FF I O PP RR SS TH U aa kk nn`.

### ⚠️ HANDS — measured, NOT fixed (operator flagged them for a redo)
```
hand_L   verts>0.01=585  max weight=0.436  bone_len=2.7%H
hand_R   verts>0.01=563  max weight=0.443  bone_len=2.8%H
pose test: hand_L +40deg -> 266 verts moved, max disp 1.30%H  (effectively immobile)
```
**Same defect F2 fixed for the legs, still present on the arms.** F2 gated the `root->hips`
fold below the HIP JOINT (`leg_soft`); arms and hands sit ABOVE the hips, so they still get
the blanket 0.85 hips claim and no hand vertex is majority-owned by its own bone.

Geometry is canon in CONCEPT (canon: "two arms ending in dark cloven hooves") but the shapes
are soft undefined blobs — the cleft barely reads — and there is no wrist distinct from the
hoof. Pack already records `fingers: single hand bone for now (topology is welded)`.

Redo scope, in order of cost: (a) extend the F2 root-fold gate to ALL limb chains, not just
legs — cheap, same proven pattern; (b) define the hoof geometry + a real wrist; (c) split
the welded topology if per-digit articulation is ever wanted.

## 2026-07-28 — M1: why the mouth reads as a hole in a static muzzle

### Measured first (three passes, two of them negative results)

**Pass 1 — is the jaw carrying the face?** Classified verts by MATERIAL so "the mouth
opened" could be told from "the face opened", then posed jawOpen=1.0 (22°):
```
GRP clyffy_mouth_interior  n=  220  moved=204  mean=2.82%H
GRP clyffy_teeth           n=  200  moved=104  mean=3.58%H
GRP clyffy_tongue          n=  146  moved=146  mean=5.05%H
GRP tripo_mat (exterior)   n=46618  moved=2421 mean=0.17%H
LOWER MUZZLE (exterior, below lip line): 6443 verts, only 34.5% move, mean 1.35%H
```
The jaw drove the cavity, teeth and tongue — and a thin collar of ~1500 verts around the
lip opening. Two thirds of the chin/jowl mass never moved.

**Pass 2 — FLOOR_DROP (negative result).** `floor_z = chin_bottom - BAND` hard-anchors
everything below the operator's 390-vert `op_jaw_region` to w=0. Lowering it did NOT help:
verts>0.01 went 3673→5818 but "fully rigid" stayed at 998 and mean weight FELL 0.540→0.441.
It widened the falloff and diluted it. Moving a w=0 boundary only lengthens the gradient.

**Pass 3 — CORE_DROP (real, but not sufficient).** The chin has to be ANCHORED to the jaw,
not interpolated toward it. Extending the rigid core downward:

| | rigid core | lower-muzzle moving | mean disp | throat bleed |
|---|---|---|---|---|
| current | 998 | 34.3% | 1.35%H | 0.1% |
| CORE_DROP 0.05 | 1988 | **61.9%** | 2.87%H | 0.4% |
| CORE_DROP 0.10 | 2977 | 62.5% | 3.42%H | 0.7% |

`along > BAND` keeps the throat out — bleed stays ≤0.7%. Coverage nearly doubles.
**But the render barely changes.** Front AND 3/4 views are visually near-identical.

### The actual root cause — GEOMETRY, not weights
```
pure cavity verts : 186          (the whole mouth interior)
shell thickness   : mean 1.29%H, MEDIAN 0.84%H   (cavity wall -> exterior)
cavity depth      : 5.2%H  (z 0.208..0.259)
```
The mouth is a **shallow 186-vertex pocket behind a sub-1% wall**. There is no mandible
volume — the "lower jaw" is a thin lip shelf. That is why:
* opening it reveals a shallow dark pocket → reads as a HOLE, not a cavity
* the 200-vert teeth are flat slabs filling that shallow pocket
* there is no mass to swing, so the silhouette cannot change however good the weights are

No weighting fixes this. It is upstream in `mouth_open.py` / `mouth_parts.py`.

### State
`FLOOR_DROP` and `CORE_DROP` are parameterised in `jaw_rig.py`, both defaulting to the
PREVIOUS behaviour — nothing promoted, the frozen alpha is untouched. Candidate rigs are in
`work/m1_fd*`, `work/m1_cd*`.

---

## M2 (2026-07-28) — the cavity was never the problem. The JAW TRAVEL is.

Re-measured before cutting any geometry. Two of M1's headline numbers were wrong, and the
correction moves the whole diagnosis.

### Correction to M1
`cavity depth 5.2%H (z 0.208..0.259)` was the bag **HEIGHT**, not its depth — that z-range
is a vertical extent. Measured properly, from the lip-rim centroid along `fwd`/`lat`/`z`
(`m2_probe.py`, BVH ray-casts against the exterior shell only):

```
BAG      n=186   depth 15.96%H   width 14.47%H   height  5.16%H
LIP RIM  n= 62   depth  3.71%H   width 14.52%H   height  0.69%H
TEETH    n=200   depth  7.24%H   width 12.55%H   height  1.95%H
TONGUE   n=146   depth 14.92%H   width  5.15%H   height  1.33%H
```

**The cavity is 15.96%H deep — three times the 5.2%H it was recorded as.** Solid head
behind and above it: palate 10.85%H, back-of-bag 18.99%H. `M1's 0.84%H median wall` was
measured over the 248-vert cavity set INCLUDING the 62 rim verts, which sit ON the exterior
surface and score ~0 by construction. Over the 186 pure-cavity verts the nearest-surface
median is **2.61%H**, and the mandible floor→down median is **2.44%H**.

Deepening the cavity would have been wasted work.

### The real constraint — arithmetic, and it does not close
```
chin depth, lip line -> jaw-region floor      3.38 %H     (z 0.2257 -> 0.1927)
jaw drop at the shipped 22 deg                7.41 %H
aperture at 22 deg (rigid block)              7.69 %H
chin bottom after a 22 deg swing              z 0.1927 -> 0.1346
visible neck, chin bottom -> shirt collar    ~2    %H
```
**The jaw travels more than twice the depth of the chin it is supposed to carry.** At full
open the lower lip finishes ~4%H BELOW where the chin bottom started, so there is no chin
left under the mouth — the aperture eats it. That is what "reads as a hole punched in a
rigid muzzle" actually is. It is a proportion failure, not a cavity failure.

### Weights ceiling — measured, so it stops being an opinion
`m2_ceiling.py` skips the rig entirely: builds the map an ideal hand-painting would give
(rigid block below the jawline / forward of the hinge, smoothstep falloff over a band below
a sweepable floor, bag skinned from `cav_src` lineage) and rotates it. At FLOOR 0.120H the
block is 3263 rigid / 5487 moving verts — 3× what the shipped solve reaches — and the chin
still lands at z 0.1346, inside the collar, with the throat dragged into the shirt.

**Confirms M1's verdict, with the right reason:** no weight map fixes this, because the
travel is larger than the anatomy. (First run of this probe was wrong — it used the full
`op_jaw_region`, which spans 2.2%H ABOVE the lip line, so the upper lip welded to the jaw
and the whole muzzle smeared down with the mouth still shut. `jaw_rig.py` filters `REG` by
`co[REG,2] < seam_lo`; the probe now does too.)

### Where it actually breaks — fine angle ladder
`jaw_rig.py` only ever rendered 0 / 50 / 100 % of 22°, so the failure point between them
had never been looked at. `m2_ladder.py` renders 0/6/9/12/15/18/22° front and 3/4 on
jaw_rig's own cameras → `work/m2_ladder/_ladder_front.jpg`, `_ladder_q50.jpg`.

| angle | reads as |
|---|---|
| 0–9° | closed → parting. Chin band intact. |
| **12–15°** | **a mouth.** Chin present under the lip, teeth banded, corners curved. |
| 18° | chin nearly consumed; going rectangular |
| 22° (shipped) | rectangular hole, no chin |

**The geometry already supports a good-looking talking mouth. It is being driven ~60% past
what it can absorb.** `ENVELOPE.jaw.max_deg = 22.0` in `tools/control_surface.py` is the
single value setting that.

### Two defects found while measuring
* **`wmap_*.png` has been blind the whole time.** `jaw_rig.py` writes a `jawmap` colour
  attribute then renders Workbench `color_type='VERTEX'`, but the attribute is never made
  active — every weight map ever produced is flat grey. Every weight judgment so far was
  made without seeing the map.
* Rim splitting by `z` instead of by CHAIN under-reports the aperture ~10× (0.67 vs 7.69%H
  at 22°). `jaw_rig.py` documents this trap and avoids it; `m2_ladder.py` reproduced it.

### State
Nothing promoted. Frozen alpha untouched. Probes in the session scratchpad, renders in
`work/m2_ladder/`, `work/m2_ceil_f0.000|f0.060|f0.120/`.

### M2 PROMOTED (2026-07-28) — moderate chin + 13° cap

Operator picked "moderate chin + ~13° cap". Executed.

* `tools/chin_mass.py` at `DEPTH 0.028`, inserted after `mouth_open`. 1302 verts moved,
  max 2.64%H, edge stretch max 2.92×. Vertex count unchanged at 47184 — index-compatible
  with everything downstream.
* `ENVELOPE.jaw.max_deg` **22.0 → 13.0** in `tools/control_surface.py`, with the collar
  arithmetic written at the call site so it is not raised again by accident. The renderer
  and `avatar_drive.py` both read the contract at runtime, so the cap propagates with no
  code change on either surface.
* Full chain rebuilt into `work/m6/`, gates run, then promoted. `accept.py` **GREEN**,
  `vrm_check.py` **GREEN** (facing −2.49° off +Z, 22 humanoid bones, 43 morphs, 3 springs).
  Deform partition of unity **exact** (min = max = 1.000000), max 4 influences.
* Registered: `clyffy.pack.toml` `[pipeline].chin_mass` + a full `[chin_mass]` block,
  `[jaw_rig].angle_deg = 13.0`, `MAP.md` pipeline table, `rebuild.sh --from-scratch`.
* Re-rendered the stale G4 artifacts (heroes + viseme sheet) — geometry changed.

Two operational gotchas recorded so the next chain run does not lose an hour:

* **`eye_open.py` is validate-only without `--cut`.** The first chain run silently produced
  no `clyffy_v2_eyes.blend` and every later stage then failed on a missing input.
* **`vrm_export.py` segfaults on exit AFTER writing the VRM** (Blender teardown, "Found 4
  unreleased ID's"). Check for the output file, not the exit status — `set -e` aborts a
  chain that actually succeeded.

**Result:** the rectangular hole is gone. The mouth reads as a mouth, the jaw carries a
visible chin through the full open pose, and the jaw owns nearly double the rigid mass.

**Next defect is now unmistakable in `_visemesheet.jpg`: THE TEETH.** They read as torn
white ribbons in TH/DD/kk/CH/SS/nn/RR/E/I/U — 200-vert flat slabs that were built for the
old shallow pocket. That is M3.

---

## Session close — 2026-07-28

**Shipped:** M2. Diagnosed, built, gated, promoted.

The session's real work was diagnostic. M1 had concluded "the cavity is a shallow pocket
with no mandible volume — rebuild it", and that premise was wrong in a way that would have
cost a full mesh-surgery cycle. Re-measuring first showed the cavity was already 15.96%H
deep with 10.85%H of palate above it; M1's "5.2%H depth" was the bag's HEIGHT and its
"0.84%H wall" was averaged over 62 rim verts that sit ON the exterior and score ~0 by
construction. Nothing needed deepening.

What was actually wrong was proportion: the jaw dropped 7.41%H at 22° while the chin was
4.5%H deep, so the aperture ate the chin. And the ceiling on fixing that turned out not to
be the chin at all but the SHIRT COLLAR — texture on the same continuous surface, 9.00%H
below the lip line, bounding chin and neck together. That inverts the intuition: growing the
chin trades against gape one-for-one, so the shipped chin depth was already optimal and no
geometry makes 22° work.

Both surviving levers were then measured rather than argued: an ideal hand-painted weight
map (3× the rigid core the solver reaches) still put the chin inside the collar, and a fine
angle ladder — which had never been rendered, because jaw_rig only ever shot 0/50/100% —
put the readable range at 12–15°. Two unrelated measurements landing on ~13° is the answer.

Operator chose to build chin mass; the collar arithmetic was surfaced when it contradicted
that, and the landing was moderate chin + 13° cap.

**Also fixed:** the `jawmap` weight-map render, blind since it was written (colour attribute
created but never made active) — every M1 weight judgment was made without seeing the map.

**Next:** M3, the teeth. The re-rendered viseme sheet shows them as torn white ribbons
across ten visemes — 200 flat slab verts built for the old shallow pocket. Owner is
`tools/mouth_parts.py`. The hands remain the other known-broken area.

**Carried, unchanged from before this session:** L4 phone surface · L5 Unreal adapter ·
hands redo · rotate `CLYFFY_CONNECTOME_PASS` · D38 RoCE GID drift wants an `ExecStartPre`
rail check on `clyffy-trio.service` (bitten 3×, operator call, not implemented).

---

## M3 (2026-07-28) — teeth. Three real defects, all measured.

The viseme sheet showed the teeth as torn white ribbons across ten visemes. They were not
"flat slabs" — measured, both bands already arched correctly (centre sits +2.48%H forward of
the ends). Three separate defects were producing the tearing.

### 1. The two arches were INTERSECTING
`sweep_band` built each band off its OWN lip chain: the chains sit 0.0077 apart while each
band is `TOOTH_H` (0.009) tall, so the bands overlapped by ~0.0068 at rest and stayed
interpenetrated to ~35% open (**measured gap −0.83%H**). Two intersecting enamel surfaces
z-fighting is what read as a torn ribbon.

**Fix — a shared BITE PLANE** at the mid-height of the closed rim (z +0.2257, between the
lower chain +0.2250 and upper +0.2264). Both arches now close onto it.

### 2. The inward offset used a GLOBAL direction
Every ring was inset along the global −fwd. That is only correct at the centre of the mouth:
at the commissures the lip runs fore-aft, so a −fwd offset drives the band sideways INTO the
cheek instead of back into the bag. This is what put white tooth slivers at both corners in
the rest pose — present in every hero render since the parts were added.

**Fix — a per-point local inward normal** (tangent rotated 90° in plane). And it must be
oriented toward the **cavity centroid**, not toward global −fwd: at the commissures the
rotated tangent is nearly ±lat, so its dot with −fwd is ~0 and the sign test becomes a coin
flip. Some end rings got an OUTWARD normal and the band left the mouth entirely — measured
at arch position **1.43**, wider than the mouth itself, and completely unresponsive to INSET
because it was never leaking through the slit at all.

### 3. The teeth could not be seen
A flat shared bite plane contains the teeth perfectly and hides them: the upper crown lands
level with the upper lip rim, so opening the jaw revealed 0.0007 of tooth and the mouth read
toothless. Real mouths solve this with an **overbite** — upper crowns hang below the lower —
avoiding intersection with an **overjet**, sitting further forward. Separation becomes
HORIZONTAL, which the jaw's rotation only ever increases. `OVERBITE 0.0035`, `OVERJET 0.006`.

### Containment is now a GATE, not a hope
`mouth_parts.py` called "nothing visible at rest" a hard acceptance criterion but only ever
checked it by eye — and it had been failing the whole time. Now measured, by casting a fan
of 15 rays outward from every interior vertex: a vertex properly inside the closed head hits
skin in every direction, because the mouth bag is an INDENTATION, not a hole. A ray that
escapes means a clear line to the outside.

The authoritative gate lives in **`lip_seal.py`**, which is the stage that owns the sealed
rest pose. The copy in `mouth_parts.py` is advisory and pre-seal: central leaks there are the
open lip slit and the seal closes them, while leaks near arch position 1.0 are the real
defect. Distinguishing the two is what located defect #2.

| | teeth_lower | teeth_upper | tongue |
|---|---|---|---|
| before | slivers at both commissures | slivers at both commissures | — |
| after (sealed rest) | **0 of 104 visible** | **0 of 96 visible** | **0 of 146** |

### Separation across the open ladder (3D distance, not a z-gap)
A z-gap is the wrong measure once there is an overbite — the crowns overlap vertically ON
PURPOSE. Minimum pairwise 3D distance:

| jaw | before | after |
|---|---|---|
| 0.35 × 13° | **−0.83%H (interpenetrating)** | 1.15%H |
| 0.70 × 13° | +0.16%H | 2.57%H |
| 1.00 × 13° | +0.96%H | 3.82%H |

### Promoted
Full chain rebuilt (`mouth_parts → lip_seal → face_atlas → shape_author → jaw_rig(13°) →
body_rig → vrm_export`). `accept.py` **GREEN**, `vrm_check.py` **GREEN** (facing −2.79° off
+Z), 43 shapes with **0 protected leaks**, Σw exact. Heroes, viseme sheet and the talking
demo re-rendered. Rollbacks: `.pre-m3` siblings.

`[mouth_parts]` in the pack now carries `overbite`, `overjet` and the bite-plane rule.

---

## M5 (2026-07-28) — viseme table rewritten, and a rig limit found

Rewrote `VISEMES` in `tools/control_surface.py`: **10 → 21 distinct morphs driven**, of the
32 the mesh carries.

### Weights are now scaled to MEASURED range
Per-morph max displacement on this mesh (%H), so a "0.5" on one shape and a "0.5" on another
are not silently different amounts of face:

```
mouthSmile*   3.55   mouthStretch* 2.38   mouthFunnel 2.25   mouthPucker  1.95
mouthUpperUp* 1.58   jawForward    1.43   mouthRoll*  1.39   mouthShrugUp 1.28
mouthLowerDwn 1.27   mouthPress*   1.27   mouthDimple 1.08   mouthShrugLo 1.02
mouthClose    0.45  <-- the WEAKEST shape on the mesh
```

`mouthClose` was carrying PP, DD, SS and nn at up to 0.4 while moving 0.45%H — which is why
those four read almost identically. `mouthStretch*` (2.38%H) was unused entirely.

### Phonetic corrections
Several entries were wrong for their sound. **FF** is labiodental — the lower lip tucks under
the upper teeth (`mouthRollLower`); it does not funnel, funnel is /w/-/oo/ rounding. **PP** is
bilabial closure (`mouthPress*`), not a pucker. **CH/SH** protrudes the jaw (`jawForward`),
which the table never touched.

Measured effect (lip aperture, %H, same 7 labels):

| | PP | FF | SS | I | E | O | aa |
|---|---|---|---|---|---|---|---|
| old | 0.24 | 0.49 | 0.49 | 0.96 | 1.50 | 2.02 | 3.04 |
| new | **0.05** | **0.35** | **0.42** | 0.93 | 1.57 | 2.04 | 3.04 |

PP now actually closes. Mean pairwise lip-shape distance over the same 7 visemes:
**0.0912 → 0.0983 (+7.8%)** — the shapes are more distinguishable.

### ⛔ CORRECTION — lip morphs CANNOT recover the gape lost to the 13° cap

That was the stated reason for adding `mouthUpperUp*` / `mouthLowerDown*` to `aa`, and it is
**wrong**. `aa` aperture measured 3.04%H before and 3.04%H after — no change at all.

Cause: **not one of the 43 authored shape keys moves a single lip-rim vertex.**

```
MORPH mouthUpperUpLeft     rim_moved 0/62   bag_moved 0/186
MORPH mouthLowerDownLeft   rim_moved 0/62   bag_moved 0/186
MORPH mouthStretchLeft     rim_moved 0/62   bag_moved 0/186
MORPH mouthSmileLeft       rim_moved 0/62   bag_moved 0/186
MORPH mouthFunnel / Pucker rim_moved 0/62   bag_moved 0/186
```

The 62-vert lip rim and the 186-vert bag are inside `shape_author.py`'s 1576-vert protected
set (`[atlas.protected]`). Mouth morphs move the skin AROUND the lips; the lip edge itself is
frozen. **The aperture is therefore 100% jaw-driven, and the jaw is capped by the collar.**

The protection is sound for the BAG — its verts are bone-driven from their rim ancestor via
`cav_src`, and moving them independently would tear it in half (the failure `jaw_rig.py`
documents). Whether it is right for the RIM is a live question: the house rule "vertical lip
separation past ~1%H opens the cavity onto unmoved upper teeth" was written when the teeth
were the old broken ones, and M3 replaced those with a properly seated, skull-anchored upper
arch. Unfreezing the rim would need `shape_author.py` to propagate rim deltas into the bag by
the SAME lineage law jaw_rig uses. Operator's call — not taken.

### Also added
`control_surface.py` now validates every morph name in `VISEMES`/`PRESETS` against the mesh
at apply time. A viseme naming a key the mesh does not carry did nothing, silently — the
entry looked authored and the face just never moved. All 38 names verified present.

### State
Table + validation promoted, viseme sheet re-rendered, `accept.py` GREEN. No mesh change —
this stage is contract-only, so there was nothing to roll back.

---

## Lip rim unfreeze (2026-07-28) — operator ruling, and it took THREE fixes

Operator chose to unfreeze the lip rim so the aperture could come from the lips rather than
the jaw — which is the only thing that breaks the chin-vs-gape trade, since that trade exists
only because gape came from jaw rotation.

It was frozen in more places than the one I found.

**1. `shape_author.py` protect mask.** `CAVITY` (248 verts) was protected wholesale. Split
into `RIM` (62, the lip EDGE — skin, not interior) and `BAG` (186, genuinely bone-driven).
The bag stays protected and now FOLLOWS the rim by its `cav_src` lineage, full at the rim
decaying to zero at the back cap — the displacement form of the weighting law jaw_rig already
uses. Verified no tearing: cavity edge stretch ≤2.95× (the rig's accepted max is 3.85×).

**2. `face_atlas.py` excluded the rim from every region.** A second, independent freeze:
`interior = cav | parts` gave all 62 rim verts ZERO weight in lip_upper/lip_lower/corners.
Freeing only the protect mask changed nothing — mouthUpperUpLeft still moved exactly 121
verts. Two freezes, one symptom.

**3. Euclidean falloff cannot tell the lips apart.** With the rim included, lip_upper AND
lip_lower both had mean weight ~0.99 over all 62 rim verts — the chains sit 0.0077 apart
against a 0.030H reach. "Raise the upper lip" raised both, so the aperture still did not
move: full-strength mouthUpperUp* + mouthLowerDown* opened the mouth **0.042%H** against the
jaw's 3.5%H.

Fixed with a **geodesic** falloff (multi-source Dijkstra over mesh edges, never pathing
through the bag). The mouth is genuinely cut, so upper→lower must travel around a
commissure. Cross-talk 0.99 → 0.157, and lip-driven aperture **0.042 → 1.86%H (44×)**.

### Operator ruling: the hand-picked selection is the DOMAIN
The regions were still bounded by a blind H*0.030 radius. Measured against the operator's
selection: the derived regions sat almost entirely INSIDE it (**251 of 258** verts), while
the selection covered **118** verts they never reached — nearly all BELOW the lip (7.56%H
down vs the radius' 1.79%H) and further back. Dropping the lower lip really does pull the
chin, so that reach is right.

Lip regions are now bounded by `op_jaw_region ∩ skin` (260 verts) with a generous 0.090H
reach — the SELECTION limits them, not a magic number, so a lip shape can never bleed into
cheek or nose.

**Answering the operator's standing question ("should I have only done the lips, I definitely
over-selected"): no.** It is not over-selected — it is a JAW map, and that is exactly how the
pipeline consumes it (jaw_rig's rigid core, shape_author's jaw falloff). `op_lip_seam` is the
lip line proper, and the rim chains that seed these falloffs descend from it.

**A partition step was then required.** Widening the reach let weight travel the short way
around a commissure and back onto the opposite lip — cross-talk 0.159 → 0.454. Each lip now
keeps only the share of a vertex it is closer to (`w·w/(w_up+w_lo)`), asserted below 0.25.
Final cross-talk 0.187 / 0.200.

| | frozen rim | geodesic, 0.030H radius | operator domain + partition |
|---|---|---|---|
| lip-driven aperture | 0.042%H | **1.86%H** | **1.18%H** |
| cross-talk | n/a | 0.157 | 0.187 |
| map | magic number | magic number | **operator intent** |

The operator-bounded map is more faithful but currently yields ~35% less aperture, because
the partition scales weights down in the overlap and the wider region dilutes the peak at the
rim. That is an AMPLITUDE knob in `shape_author.py`'s lip shapes, not a redesign.

### Chin — candidate built, NOT promoted
`chin_mass` DEPTH 0.028 → 0.045 with the jaw at 10°. Full chain green (containment GREEN,
43 shapes, 0 protected leaks). It is a visible silhouette change — a heavier lower jaw and
less neck — so it is the operator's call, same as the first chin decision.

### Negative results — three chin-depth metrics, all failed
Recorded so nobody rebuilds them: **lowest midline vertex** measures the THROAT (~12%H
regardless); **biggest backward silhouette step** MOVES as the notch fills (reported
3.50 → 2.50%H for a chin that had visibly grown); **lowest point within 3%H of the front**
keys off the lip line and was flat across every DEPTH. The extent of the grown mass
(`amp > 0.5`) is monotone in DEPTH but includes the jaw underside sweeping back, which the
collar does not constrain. **Validate the chin by posed render and collision, not a scalar.**

### PROMOTED (2026-07-28) — deeper chin + freed lips

Operator pushed back on being handed the same decision repeatedly. Fair: they had already
chosen "unfreeze it, then redo the chin". Called it and shipped it.

* `chin_mass` **DEPTH 0.028 → 0.045** — the chin is finally defined rather than pinned at the
  `min(D, 9−D)` optimum.
* `ENVELOPE.jaw.max_deg` **13 → 10**. The jaw gives up 3° to buy that chin depth, and the
  freed lips pay it back: `aa` now drives mouthUpperUp*/mouthLowerDown* at 0.9/0.95 instead
  of 0.55/0.6.
* Lip regions bounded by the operator's `op_jaw_region ∩ skin`, geodesic falloff, partitioned
  so the two lips compete instead of overlapping.

22° → 13° → 10° each got paid for: 13 by the collar arithmetic, 10 by lip-driven aperture.

`accept.py` GREEN · `vrm_check.py` GREEN (facing −2.42° off +Z, 22 bones, 43 morphs, 3
springs) · containment GREEN · 43 shapes, 0 protected leaks. Heroes, viseme sheet and the
talking demo re-rendered. Rollbacks: `.pre-lips` siblings alongside `.pre-m3` and `.pre-m2`.

---

## Hands + hooves (2026-07-28) — smaller than it looked, twice over

Operator picked the hands and offered hand-selection work. Grounding it first shrank the job
twice.

### It was never "per-finger hands"
`clyffy.pack.toml [layers].base_body` lists **cloven-hooves**, and the base sheet shows a
white furred forearm ending in dark toes. No fingers. `alpha_deferred` had carried
"per-finger hands" as a target it never should have been; removed.

### And the toe count was nearly got wrong — MY error, caught by the operator
A first read of the base sheet said THREE toes. It came from a crop window
(`crop=280:300:180:430`) that **straddled two panels of the turnaround**, stitching one
pose's hand beside another's. The operator spotted it immediately: *"you mixed the two hands
on that second image, you are blending two separate poses."*

Panels are 1668/5 = **333.6 px**; crop INSIDE one. Re-cropped cleanly, front and 3/4 agree:
**two toes**. Cloven means split in two — the word itself was the check I skipped.

**Which means the mesh already had the right toe count** — the two soft lobes ARE the toes.
No topology work. I had been one message away from sending the operator to hand-select finger
splits for a hand that doesn't have fingers.

### Defect: the F2 leg defect, again, on the arms
F2 gated the blanket root fold off the legs by HEIGHT. **The arms escape that gate entirely**
— they hang beside the torso and share its z range, so the remainder still outvoted every arm
bone.

```
before:  hand_L max 0.436   hand_R max 0.443   majority-owned verts: 0
after:   hand_L max 0.852   hand_R max 0.874   majority-owned verts: 152 / 171
```

Height cannot separate an arm from the ribs, so the gate is **distance to the arm chain**,
using the same segments and radii the arm bones are built from (3867 verts gated). Verified
by POSING, because bound is not poseable — that is the whole lesson of F2:

| rotate | before | after |
|---|---|---|
| `lower_arm_L` +35° | 1.73%H | **3.12%H** |
| `hand_L` +35° | 0.44%H | **0.81%H** |
| torso bleed | 0.000%H | **0.000%H** |

### `tools/hoof.py` — the dark hoof
Material on the distal faces, the same play `mouth_parts.py` uses for teeth and tongue. The
body is one texture, so the hoof needs its own material. 595 verts / 529 faces, dark warm
grey (not black — black reads as a hole). **No geometry change**, so it is safe after
`body_rig`: vertex count, indices, weights and all 43 shape keys untouched.

The tool prefers an **`op_hoof`** vertex group if the mesh carries one — the operator's pick
beats a derived styling line. `frac = 0.38` is only the fallback.

### Promoted
`accept.py` GREEN · `vrm_check.py` GREEN (facing −2.42° off +Z, 22 bones, 43 morphs, 3
springs, 5 glTF primitives). Heroes re-rendered. Rollbacks: `.pre-hoof`.

⚠️ `present.py` silently produced nothing on one chained invocation and left an 4-hour-stale
`_herosheet.jpg` in place — `accept.py` only checks that heroes EXIST, never that they are
current. Re-ran standalone and confirmed by timestamp. Check mtimes after any geometry change.

---

## Gate hardening (2026-07-28) — the checks were passing on things they never looked at

Two silent-failure classes closed, both found by the work rather than by review.

### 1. `accept.py` — existence is not freshness
The soft artifact checks (G4/G5) only asked whether files were THERE. So the gate went green
on a `_herosheet.jpg` **four hours older than the body blend it depicts**, after a geometry
change, and after `present.py` had silently produced nothing on a chained invocation. A stale
beauty render is the artifact someone reaches for to judge the character — the last one that
should be allowed to lie.

Every derived artifact is now dated against the mesh (or contract) it descends from. It found
two real staleness bugs the moment it ran:

* `hero_angry.png` / `hero_thinking.png` were **30 hours** stale — `present.py` defaults to
  four states while six hero files exist, so two were never being refreshed. Now rendered
  explicitly; all six current.
* `mesh/canon/body/drive/drive_frames.jsonl` was **26 hours** stale — the pack's signature G5
  artifact still encoded the **22° jaw contract**, three contract revisions behind.
  Regenerated.

`accept.py` now reports **zero warnings**.

### 2. `vrm_check.py` — the contract was never checked against the delivered artifact
The renderer resolves viseme and preset keys against the VRM's `morphTargetDictionary` **by
name**. A key the VRM does not carry is a silent no-op: the table looks authored and the face
simply never moves. `control_surface.py` gained this check for the Blender path earlier today;
the DELIVERED artifact — the half that actually ships — had no equivalent.

`vrm_check` now cross-checks every non-`jawOpen` key in VISEMES + PRESETS against the VRM's
`targetNames`. All **38 contract morph keys** verified present.

### Negative-tested, because an assertion that has never fired is not known to work
Injected a bogus `mouthNotARealMorph` key into the real contract and ran the real gates:

```
vrm_check  -> FAIL  1 contract key(s) have NO morph target: mouthNotARealMorph   exit 1
accept.py  -> exit 1
reverted   -> both exit 0, contract clean (sil = {}, jaw max_deg = 10.0)
```

Exit codes propagate correctly through `accept.py`, which is what any CI would key on. Worth
noting the trap in measuring it: `python3 … | tail -5; echo $?` reports **tail's** status, not
python's, and showed a reassuring 0 for a run that had actually failed.

### Live surface — verified wired, not assumed
`interfaces/clyffy-avatar/renderer/public/` symlinks `clyffy.vrm` and
`control_surface.schema.json` **directly into this pack**, so today's chin, teeth, hoof,
jaw-cap and viseme changes reach the live window with no copy step and no stale asset. The
renderer resolves morphs by raw ARKit name and already surfaces missing keys in its own HUD.

### One more thing the negative test exposed
The freshness check originally dated `drive_frames.jsonl` against `tools/control_surface.py`.
Reverting the injected key restored byte-identical content but moved the file's mtime, and the
gate cried stale. That was a modelling error, not noise: the drive frames depend on the
PUBLISHED SCHEMA, which is only re-emitted when the contract actually changes. Re-pointed at
`control_surface.schema.json`.

**Final state: `accept.py` GREEN with ZERO warnings · `vrm_check.py` GREEN with all 38
contract morph keys verified against the delivered VRM.**

---

## Mouth polish (2026-07-28) — PROMOTED

### Lip amplitude was the real ceiling
`_upper_up` / `_lower_down` shifted 0.012H / 0.010H. Those numbers were chosen while the lip
rim was still WELDED — when no amplitude could move the lip edge at all and they only had to
look sane. With the rim freed they became the binding constraint on how far the mouth opens.

Doubled, and measured rather than eyeballed:

| | lip-driven aperture | cavity edge stretch | edges >2x |
|---|---|---|---|
| shipped (0.012/0.010) | 1.18%H | — | — |
| **2x (0.024/0.020)** | **2.35%H** | 1.18x | 0 |
| 3x (0.036/0.030) | 3.52%H | 1.27x | 0 |

**3x was rejected by the RENDER, not by the numbers** — it measured fine (the rig accepts
3.85x stretch) but the upper lip lifted far enough to drag the muzzle pad and the whole face
distorted. Worth recording as a rule: the mesh limit and the character limit are different
limits, and here the character's was tighter. Numbers can only rule things OUT.

### Teeth scalloped into individual teeth
The band was one swept solid — a continuous ridge of enamel. A raised cosine along the arc,
one period per tooth, scallops the crown: discrete tips, no topology change, still a closed
solid at 4 verts per ring. `TEETH_N = 7`, `TEETH_CUT = 0.34`.

Honest limit: 26 ring points over 7 teeth is **~3.7 samples per scallop**, which is coarse.
Judged alone at jaw-only framing the difference was marginal — but that framing exposes very
little tooth. It reads at the aperture the 2x lips now open, which is the pose that matters.
Going finer needs more ring points, not a bigger cut.

### Not done: the tongue
Still the flattened UV sphere `mouth_parts.py` creates. Visible only in `TH` and `tongueOut`.
Left rather than half-done.

### Promoted
Full chain from `mouth_parts` down. `accept.py` GREEN zero warnings · `vrm_check.py` GREEN
38/38 contract keys · containment GREEN · 43 shapes, 0 protected leaks. Heroes, viseme sheet
and drive frames all re-rendered and dated after the mesh. Rollbacks: `.pre-polish`.

## Tongue (2026-07-29) — PROMOTED. Plus a contract bug in three renderers.

Closes the "not done" item from the Mouth-polish entry above.

### The old tongue could not have worked, and the measurement says why

Measured on the delivered body blend before touching anything:

| | old | bag |
|---|---|---|
| fore-aft profile (width by station) | 0.033 / 0.044 / 0.050 / 0.050 / 0.044 / 0.033 | — |
| lat extent | 5.15%H (**36%** of the bag) | 14.47%H |
| height | 1.33%H (**26%**) | 5.16%H |
| front face → lip rim front | **9.51%H BEHIND** | — |

That profile is a **palindrome** — the same shape read backwards. No root, no blade, no tip,
no dorsum. It was a UV sphere squashed into an ellipsoid, and it sat further back than the
lower teeth.

The last row is the one that mattered. `tongueOut` translated the whole lozenge **rigidly**
4.80%H forward against a **9.31%H** gap, so the tip finished **5.29%H SHORT of the lip
plane** — the morph could never protrude, only show a red patch through the slit. Its 0.048H
constant had been reasoned from the *teeth inset* (0.030) rather than from where the tongue
actually was. It was answering a question nobody had asked.

### Authored, and derived from the cavity rather than hard-coded

13→15 stations × 12→16 ring points + 2 poles, lofted. Every dimension is a fraction of
MEASURED room (`bag_at(f)` samples the cavity walls per station), so it keeps fitting if
`mouth_open`'s pocket changes. Tip stop is the **lingual face of the lower incisors**, taken
from the band near the midline — using the whole band reads its commissure ends, which sit
far further back and would park the tip mid-mouth again.

| | old | new |
|---|---|---|
| verts | 146 | 242 |
| fills bag lat / fwd / z | 36% / 52% / 26% | **58% / 75% / 55%** |
| profile | palindrome | 0.0209 / 0.0239 / 0.0236 / 0.0158 / 0.0092 / 0.0037 |
| `tongueOut` tip vs lip | **−5.29%H (behind)** | **+1.71%H (PAST)** |
| containment at rest | 0/146 | **0/242** |

### Three defects found by building it, each measured

**1. A PINHOLE through the sealed lips.** First build failed containment with exactly one
vertex. Rather than nudge a constant, scanned the sealed head for where a straight-ahead ray
can escape: there is a **0.037%H window at z [+0.22448, +0.22484]** and that vertex was
sitting in it. The scan also gave the shape of the constraint —

```
station f < 0.055   highest contained z = +0.2320   (rays run into the palate)
station f > 0.055   highest contained z = +0.2244   (rays reach the lip slit)
```

— so forward of mid-bag the ceiling is the **lower lip edge**, not the bag ceiling. Derived
from `rim` rather than hard-coding +0.2244. It is also correct anatomy: a tongue's dorsum is
highest at the back.

**2. The ceiling was counted TWICE.** Thickness was derived from the already-clamped
ceiling, so the duck clamp cut the ceiling and the smaller `(ce − fl)` then cut the thickness
again. The blade collapsed **2.13%H → 0.63%H between two adjacent stations** — a cliff, not
a taper, reading as a thick body with a sheet of paper stuck on the front. Thickness now
comes from the bag's room and the ceiling only ever CLIPS the result.

**3. A SPEARHEAD, and flat shading.** Tapering the width profile to 0.17 at the tip turned
the last ring into a needle and the pole cap into a spearhead — obvious from above in the
isolated render and nothing like a tongue. Profile now holds 0.38 at the tip and the short
pole cap does the rounding. The tongue is also **smooth-shaded per-face**, so the teeth keep
their facets; flat-shaded it was unmistakably a low-poly wedge the moment the mouth opened.

Also fixed: the tip pole was pushed 0.004 PAST the last ring, silently spending the entire
`T_TIP_CLEAR` budget and landing flush on the incisors. Rings now stop short; poles land on
`f_root` / `f_tip` exactly.

`tongueOut` is now a **deformation, not a slab**: travel is measured every build from the
actual tip→lip gap, and ramps from a root that stays anchored in the floor of the mouth
(`TONGUE_ROOT_HOLD = 0.12`). A rigid slide would drag the root out and leave a hole behind it.

### ⚠️ A CONTRACT BUG — three renderers posed at 22° against a 10° envelope

Found while building the tongue sheet. `ENVELOPE["jaw"]["max_deg"]` has been **10.0** since
the collar arithmetic, but:

* `viseme_sheet.py` — `MAXDEG = 22.0`. **The G4 sheet the character is JUDGED from had been
  drawing every viseme at 2.2× the jaw angle the rig is driven at.**
* `present.py` — `math.radians(22.0)`. Every beauty hero, same.
* `control_surface.py` — its own `set_jaw_open()` used a 22.0 literal, *inside the file that
  publishes the envelope*, with a docstring still reading "max 22 deg". Anything driving the
  rig through the control surface got 22°.

All three now read `ENVELOPE["jaw"]["max_deg"]`. Heroes, viseme sheet and drive frames
re-rendered at the honest angle. `jaw_rig.py`'s `ANGDEG = 22.0` is left alone — it is a
post-build stress pose for validation, not the runtime envelope — but STATUS's claim of
"jaw_rig(13°)" is stale.

This is the **third** gate blind spot in two days (stale artifacts, then jaw angle, now
rest-only containment below). The pattern is worth naming: the gates test what is cheap to
test, not the states the character is actually seen in.

### Pre-existing mesh defects — classified, NOT introduced

`hygiene` reports **1 non-manifold edge, 19 boundary edges**. Verified identical in the
pre-change parts blend, so not mine. The 19 boundary edges form **one hole, 0.13%H across,
at mid-torso (50.7%H from the top)**; verts 85 / 817–822 / 45985–45991. Inherited from the
Tripo mesh. Invisible at any demo framing; matters if the VRM is handed to anyone else.

### Found, NOT fixed — the posed containment gap

`lip_seal.py`'s containment gate only ever tests **rest**. The beauty heroes show a white
tooth sliver breaking the lip at the left commissure in `talk_aa`, another speck at the right
corner in `happy`, and jagged eyelid seams around both eyes in `surprised`/`angry`/`talk_aa`.
All green on every gate. A posed gate is needed (signed distance to the nearest EXTERIOR skin
point along its outward normal — positive = poking through) across visemes and presets.

### Promoted

Full chain `mouth_parts` → `lip_seal` → `face_atlas` → `shape_author` → `jaw_rig` →
`body_rig` → `hoof` → `vrm_export`. `accept.py` **GREEN zero warnings** · `vrm_check.py`
**GREEN 38/38** · containment GREEN · 43 shapes, 0 protected leaks · Σw = 1.000000.
Rollbacks: `.pre-tongue`. New tool `tools/tongue_sheet.py` (mouth closeups from the contract's
own viseme table + an isolated pass with the head hidden).

## Viseme distinguishability (2026-07-29) — measured for the first time

`tools/viseme_distinct.py`. The pack had always asked "does each viseme render" and never
"can a viewer TELL THEM APART". Poses through the contract's own path, then RMS displacement
over the 4264-vert mouth region between every pair.

**Healthy:** no dead visemes, median pairwise separation **0.58%H**, only 3 of 105 pairs
below 0.25%H. `aa` is strongly distinct (1.73%H travel, 1.79%H from `PP`). Vowels separate.

**THE FINDING — the consonants collapse toward silence:**

| pair | separation | |
|---|---|---|
| `DD` vs `kk` | **0.17%H** | indistinguishable |
| `CH` vs `RR` | **0.23%H** | indistinguishable |
| `SS` vs `nn` | **0.25%H** | indistinguishable |
| `sil` vs `FF` | **0.25%H** | "f/v" is the same shape as saying nothing |
| `sil` vs `SS` | 0.27%H | |
| `sil` vs `PP` | 0.29%H | |

Look at what those pairs share. `DD` vs `kk` is tongue-tip vs tongue-back. `SS`/`nn`/`CH`/`RR`
are tongue-position consonants. `FF` is lower-lip-to-upper-teeth.

**We just built a good tongue and gave it exactly ONE morph.** `tongueOut` cannot go tip-up,
back-up, or tuck, so every consonant a real mouth distinguishes *with the tongue* has nothing
to distinguish it with and collapses onto silence. The vowels survive because the jaw and
lips carry them.

Consequence for the demo, stated plainly: **a talking demo on these visemes reads as a cow
mouthing vowels** — audio saying "f" over a face doing nothing. Voice alone does not produce
a solid alpha; it produces good audio over a face that cannot keep up with it.

## Tongue articulation (2026-07-29) — PROMOTED. The consonants now have somewhere to go.

Fixes the collapse measured in the entry above. Four new shapes, authored as a documented
**extension beyond ARKit-52** — ARKit ships `tongueOut` and no other tongue control.
Additive: the 43 ARKit keys are untouched, a consumer that only knows ARKit ignores these
and gets exactly what it had before. Shapes 43 → **47**.

| shape | verts | peak | what it buys |
|---|---|---|---|
| `tongueUp` | 177 | 1.70%H | tip to the alveolar ridge — /d/ /t/ /n/ /l/ /s/ |
| `tongueBack` | 129 | 2.78%H | velar hump — /k/ /g/ |
| `tongueCurl` | 242 | 3.46%H | blade raise — /ʃ/ /tʃ/ /r/ |
| `lipTuckLower` | 384 | 1.94%H | lower lip behind the upper teeth — /f/ /v/ |

**Every magnitude is DERIVED, not asserted.** This cavity is shallow at the front (the bag
converges on the lip slit), so a hard-coded lift that looked right at the root would drive
the tip through the palate. Each vertex moves a fraction of ITS OWN measured headroom to the
local ceiling (`_cavity_ceiling` samples the bag and ducks under the upper teeth, the same
windowed sampling `mouth_parts` uses to fit the tongue). Measured headroom max **4.85%H**.

### Result — 105 pairs, before and after

| pair | before | after | |
|---|---|---|---|
| `DD`/`kk` | 0.17%H | **0.35%H** | tip-vs-back now separates |
| `sil`/`FF` | 0.25%H | **0.45%H** | "f/v" is no longer silence |
| `CH`/`RR` | 0.23%H | **0.29%H** | |
| `SS`/`nn` | 0.25%H | **0.45%H travel, off the closest list** | |

**Pairs failing threshold: 3 → 0.** RMS median 0.58 → 0.65%H, min 0.17 → 0.28%H.

### Two wrong answers on the way, both caught by the tool

**`nn` was wrong twice.** First pass gave it `tongueUp 0.8` — the same morph SS uses at
almost the same strength — so it separated from DD/kk and stayed welded to SS at 0.25%H.
Second pass closed it to `jawOpen 0.04` with press + rolls, which collapsed `PP`/`nn` to
**0.19%H**: that is a BILABIAL seal, i.e. /m/, not /n/. For /n/ only the TONGUE seals; the
lips stay relaxed and slightly parted. Third answer (`jawOpen 0.14`, no press, no roll) is
the one that holds.

**The weak viseme was `SS`, not `nn`.** It travelled 0.28%H from silence — nearly a closed
mouth — because the spread was driven at only 0.5. /s/ is one of the most readable shapes on
a real face and the wide corners ARE the cue. Driven properly (stretch 0.9, dimple 0.45,
smile 0.25) it travels **0.45%H** and the collision disappears.

### The metric was unfair, and that is now stated in the tool

RMS over a FIXED region is dominated by how MANY verts move, not by how distinctive the
shape is. A jaw drop moves thousands of verts a little and scores high; a sibilant's spread
lips move ~230 verts a lot and score low, though a viewer reads the second one instantly.
`viseme_distinct.py` now reports **RMS *and* P95** (95th-percentile per-vertex displacement)
and only calls a pair indistinguishable when it fails BOTH. P95 median 1.54%H.

Also written into the tool: **not every pair should separate.** Lipreading groups phonemes
into viseme classes because /p,b,m/ genuinely look alike on a real face, as do /k,g,ŋ/. The
standard is "pairs a human distinguishes should separate", not "all 105 separate" — chasing
the latter would be fitting the metric.

### Containment held, checked at full strength

Raising the tongue toward the palate is exactly the change that pokes through, so it was
measured rather than assumed:

```
rest            0/242      tongueUp@1      0/242      tongueBack@1  0/242
tongueCurl@1    0/242      all three @1    0/242  (z max +0.2552)
```

Tongue visible only when the jaw is open — DD 52/242, TH 87/242 — which is correct and
wanted. Nothing escapes with the mouth closed.

### Promoted
`accept.py` GREEN zero warnings · `vrm_check.py` GREEN, **47 morph targets, 42/42 contract
keys** · 47 shapes, 0 protected leaks · Σw = 1.000000. Heroes, viseme sheet, schema,
examples and drive frames all re-rendered. Rollbacks: `.pre-artic`.

## Posed containment, the fold hunt, and mesh hygiene (2026-07-29) — PROMOTED

### `tools/pose_check.py` — and it took THREE tests to get right

`lip_seal.py` only ever tested REST, the one pose where the lips are shut and nothing can
escape by construction. The new gate asks the same question across 30 states: rest, all 15
visemes, all 7 presets, a jawOpen sweep, and the corner shapes driven alone.

**Two wrong tests first, both kept in the docstring so neither is retried:**

1. **Signed distance to the nearest exterior-skin point.** Reported 109 failures — but with
   the mouth OPEN the exterior surface has a hole in it, so a tongue sitting correctly in the
   aperture has its nearest point on the lip rim and scores "outside" by up to **5.6%H**.
2. **Ray fan + aperture polygon** (escape is legal only through the mouth). Right in
   principle, wrong in practice: the lip rim spans 5.85%H fore-aft and is strongly
   NON-PLANAR, so fitting a plane gives a self-intersecting polygon and the even-odd test is
   meaningless. Reported **1516** failures, almost all at the mouth CENTRE — the one place it
   was supposed to permit.

Both failed identically: clustered where the mouth OPENS, not where it breaks.

**What works: CAP THE MOUTH, then ask inside-or-out.** Build a membrane across the lip rim
(triangle fan from its centroid), add it to the exterior skin, and the head becomes a closed
volume whose interior INCLUDES the cavity. Parity test, voted over three ray directions
(the base mesh carries defects that can flip a single ray). Visible-through-the-opening is
then irrelevant, which is correct — teeth SHOULD show in an open mouth.

### It immediately found a real one — and not the shape I blamed

`viseme PP`, one upper-tooth vertex outside. My first guess was `mouthRollUpper` and halving
it **changed nothing**. Isolated by component instead:

```
press only (0.7)     1 outside      rollUpper only   0
press + close        0 outside      rollLower only   0
full PP              1 outside      close only       0
```

`mouthPress` at 0.7 takes the upper lip BEHIND the incisors; `mouthClose` actually rescues
it, which is why the combination matters. Swept: 0.55 and 0.60 clean, 0.65 fails. **PP press
0.7 → 0.60**, a 0.05 margin. `sil`/`PP` is now RMS 0.24 (below threshold) but P95 0.82 —
flagged "close overall, real local difference", which is phonetically honest: /p b m/ IS a
closed mouth. Still **0 of 105 pairs failing both metrics**.

### The upper-lip notch — DIAGNOSED, and the fix REJECTED on the render

Rendering the open mouth at demo framing showed jagged black notches torn along the upper
lip. Measuring the SKIN (previous work only ever measured the CAVITY) found the cause —
**face normals inverting**, i.e. the surface folding through itself:

```
preset happy  3.69x stretch, 34 edges >2x, 26 NORMAL FLIPS
viseme aa     3.02x,          16 >2x,       24 flips
rest          1.00x,           0,            0
```

Per shape, ALONE at 1.0: `lipTuckLower` 23 · `mouthUpperUpRight` 22 · `mouthPucker` 21 ·
`mouthUpperUpLeft` 17 · `mouthFunnel` 15 · `mouthShrugUpper` 14. **Not stacking** — each
folds on its own.

Tried: relax the displacement field over the mesh graph (a fold is a high-frequency feature
of that field). **Rejected, measured:**
* Unbounded, it drives every fold to zero and takes the shape with it — `eyeBlinkLeft`
  43→0 flips while keeping **33%** of its travel (6.41%H → 2.12%H), i.e. an eye that no
  longer closes.
* Peak-restoration to claw the amplitude back made things WORSE (`mouthSmileRight` 13 → 25
  flips): scaling a smoothed field uniformly pushes mid-field verts past where they started.
* With an 85% amplitude floor the big shapes refuse to unfold at all, and rendered
  before/after at demo framing the "after" was **not better** — smaller aperture, no less
  ragged.

**MOST FLIPS ARE NOT DEFECTS.** A closing eyelid folds because that is what an eyelid does.
The genuinely bad one is a TOPOLOGY limit: there are not enough edge loops across the lip to
absorb a 2.4%H lift without the surface crossing itself. The real fix is a retopology pass
adding loops at the lip and eyelid — which changes vertex count and rebuilds the whole chain.
That is a scoped job, not a tuning knob. `face_flips()` now REPORTS per shape; `unfold()` is
kept, documented, and deliberately **not called**.

### `tools/mesh_patch.py` — the inherited hole, closed

The 19 boundary edges were the SYMPTOM. Diagnosed: the single non-manifold edge (v818–v85)
carried THREE faces, one a triangle of area **7.0e-08** — 0.3% of the median face — stitched
across an otherwise open chain. Filling first only ever got 19 → 5.

Order that works: remove the sliver → `holes_fill` → sweep the wire edge the deletion leaves
behind. **boundary 19 → 0, non-manifold 1 → 0.** Runs LAST and adds faces only (47178 →
47179), so vertex count, indices, weights and all 47 shape keys are untouched — `body_rig`
transfers face weights BY INDEX and asserts equal counts, so anything that moves vertex count
invalidates the chain.

### Promoted
`accept.py` **GREEN zero warnings**, now including posed containment and a TOML parse of the
pack · `vrm_check.py` GREEN 47 targets, 42/42 contract keys · `pose_check.py` GREEN across 30
states · 0 of 105 viseme pairs failing both metrics · mesh watertight. Rollbacks
`.pre-patch`.

## Lip densification (2026-07-29) — PROMOTED. And it exposed a density-biased rig.

The fold entry above concluded the upper-lip tear was a TOPOLOGY limit and that a smoother
could not fix it. This is that conclusion acted on.

### The measurement that located the problem

```
lip-region median edge, canon (pre-cut) : 0.00373  = 0.73x the global median
lip-region median edge, final body      : 0.00691  = 1.35x the global median
```

The lip starts FINER than the rest of the head and ends up 35% COARSER. `mouth_open` opens
the pocket by stretching the rings it already has rather than adding any, so by the time the
shapes ask the lip to move 2.4%H there is nothing left to absorb it.

### `tools/densify.py` — and WHERE it runs took three attempts

**Attempt 1, after `canonicalize` (the obvious place): broke the eye cut.** At reach 0.085 the
left dome boundary picked up a degree-4 pinch vertex and `eye_open` refused to cut. Backing
off to 0.070 cut, but produced **5 connected components** [47348, 640, 425, 102, 42] instead
of 3; at 0.060 still 4. `eye_open` requires EXACTLY 2 eyeball components and **silently skips
writing** `eye_L_center` / `eye_L_radius` / `eye_R_center` / `eye_R_radius` otherwise — which
then kills `face_atlas` four stages later with a bare `KeyError`. (I briefly concluded no tool
wrote those props at all; wrong — `eye_open` writes them via an f-string, `ob[f"{name}_center"]`,
which a literal grep misses.)

**Attempt 2 — relocated to run AFTER `eye_open --cut`.** The eye topology is then already
resolved and untouched. Also restricted to SKIN: `cav_src` is an INT layer recording each bag
vertex's lip-rim ancestor, and subdividing a cavity edge would hand the new vertex a
meaningless average of two ancestor INDICES. Eyeballs and the sockets are withheld explicitly.

Result: verts 46838 → 47778 (+940), lip-region median edge **0.00561 → 0.00380 (0.75x global,
was 1.35x)**. `op_jaw_region` 369 → 785 by interpolation, `op_lip_seam` and both eyeball groups
untouched. The script REFUSES TO SAVE if any group loses members — the operator's hand
selections are not reproducible.

### ⚠️ IT THEN EXPORTED THE CHARACTER FACING BACKWARDS — and the cause was not the densify

`vrm_check` FAILED: **facing -179.79° off +Z**. Eye bones were byte-identical; the SKULL bone
had moved, (-0.0623, 0.0353) → (-0.1034, 0.0641).

`body_rig.spine_point()` took **`co[m].mean(axis=0)`** — an unweighted mean over the vertices
in a z-slab. That is not a geometric centre; it is pulled toward wherever the mesh is finest.
The lip sits 0.045H from the neck slab and fell inside it, so 940 new loops dragged the neck
sample sideways and the skull with it.

Replaced with the **midpoint of the slab's fore-aft EXTENT**, which is density-independent.
Proof it is the right estimator — the same rig built on both meshes:

```
canon      skull head (-0.0389, 0.0190, 0.2696)
densified  skull head (-0.0389, 0.0191, 0.2696)
```

Identical to four decimals. It also made the export MORE accurate on the canon mesh:
**facing -2.10° → -0.26° off +Z**, because the biased mean had been skewing it all along.

Every other check stayed green through this — 22 humanoid bones, 47 morphs, 3 spring chains,
Σw = 1.000000. Only `vrm_check`'s facing test caught it. That test was added on 2026-07-27
after the VRM shipped 55.1° off-axis; this is the second time it has been the only gate
looking in the right direction.

### Result

| | canon | densified |
|---|---|---|
| pose_check | GREEN | **GREEN** |
| viseme RMS median | 0.65%H | **0.73%H** |
| viseme P95 median | 1.54%H | **1.65%H** |
| `sil`/`PP` | 0.24 | **0.31** |
| pairs failing both metrics | 0 | **0** |
| VRM facing | -2.10° | **-0.26°** |
| verts | 47280 | 48220 (+2.0%) |

Rendered A/B at demo framing: the upper-lip tear on the character's left is **substantially
reduced**. Honest limits — small notches remain at both commissures, and there is new fine
scalloping along the lower lip edge. An improvement, not a cure; the eyelid folds are
untouched because the eye sockets are deliberately withheld from the patch.

### Promoted
`accept.py` GREEN zero warnings · `vrm_check.py` GREEN 47/42 · `pose_check.py` GREEN 30 states
· mesh watertight · voice reel re-driven on this face (`work/voice/drive_v2/_all_lines.mp4`,
5 lines, 9.19s). Rollbacks `.pre-dense`.

## Eyelid densification (2026-07-29) — TRIED, MEASURED, REJECTED. Canon untouched.

The lip densification worked, so the obvious next move was to do the same to the eyelids and
close out the remaining fold artifact. It does not work, and the reason is worth keeping.

First, a cheap correction to my own earlier caution: the eye sockets were withheld from the
lip patch out of worry about the eye cut, and that worry was **unnecessary** — by the time
`densify` runs, the cut has already happened and cannot be affected. Verified before
extending: the eyes blend reports boundary 19, which is only the inherited torso hole, so the
separation leaves BOTH pieces closed and there is no open socket for `mesh_patch` to fill.

Enabled at 2.2x eyeball radius: **46838 → 50865 verts (+4027 with the lip)**. Eyeball shells,
`op_lip_seam` and both eye groups untouched.

**Fold rate per moved vertex — the metric that is fair when the face count changes:**

```
eyeBlinkLeft    43/489  = 0.088  ->  177/1920 = 0.092   WORSE
eyeSquintLeft   40/735  = 0.054  ->  137/2288 = 0.060   WORSE
eyeWideLeft     34/489  = 0.070  ->  127/1920 = 0.066   ~same
```

**And the render agrees.** Side by side at identical framing, the denser lid is slightly
WORSE: the fold does not go away, it resolves into finer and more visible creasing. Clearest
on `eyeBlinkLeft`'s upper lid.

**Why the lip and the eyelid are NOT the same problem.** The lip was measurably STRETCHED by
the pipeline — `mouth_open` opens the pocket without adding rings, leaving the lip at 1.35x
the global median edge — so it was genuinely short of mesh and loops helped. The eyelid was
never stretched; it folds because **a closing eyelid folds**, which is what an eyelid does.
Resolution cannot fix a fold that is not a resolution deficit. Assuming the two cases were the
same problem was the error; measuring told me otherwise before anything was promoted.

`EYE_MULT` now defaults to **0.0** in `tools/densify.py` with the numbers recorded at the call
site. Verified the shipped defaults reproduce the promoted canon exactly: 47778 verts / 47624
faces, identical hygiene.

## POAM A1 — the live bundle was two contract generations stale (2026-07-29)

`POAM.md` A1. Writing the plan is what surfaced this: every gate in this pack stops at the
pack boundary, and the surface the operator actually looks at is one repo further on.

### What was wrong

`clyffy/interfaces/clyffy-avatar/renderer/` keeps `public/clyffy.vrm` and
`public/control_surface.schema.json` as **symlinks into canon** — correct, the dev server
tracks the current face automatically. But `dist/` is a vite BUILD OUTPUT, and it had not been
rebuilt since 2026-07-28. `dist/` is what the Tauri shell ships.

Checking CONTENT rather than mtimes is what made it real:

```
                          stale dist            canon
clyffy.vrm                75,197,660 bytes      82,054,972 bytes
control_surface.schema     5,006 bytes           7,696 bytes
jaw.max_deg                22.0                  10.0
DD viseme                  {jawOpen, mouthClose} {jawOpen, tongueUp, mouthLowerDown L/R, mouthStretch L/R}
```

`jaw.max_deg = 22.0` is the value that was fixed on 2026-07-29 in three renderers — the live
surface had it too, and had been opening the jaw **2.2x the contract**. The `DD` viseme is
from before the M5 table rewrite (2026-07-28), so the live surface was **two generations**
behind, not one.

**The renderer code was never at fault.** `main.js:46-52` fetches the schema at runtime and
reads `VISEMES` and `ENVELOPE.jaw.max_deg` from it; there are no hardcoded constants. The seam
law held. Only the built artifact had drifted.

### Fix and proof

`npm run build` — vite re-copies `public/` (symlinks resolve to canon) into `dist/`. After it:
`clyffy.vrm` and `control_surface.schema.json` are **byte-identical to canon**, served
`jaw.max_deg = 10.0`, and `DD`/`kk`/`FF` carry `tongueUp`/`tongueBack`/`lipTuckLower`.

### `tools/renderer_check.py` — a gate that crosses the repo boundary

Mirrors `main.js:147-153` exactly: build `drivenKeys` from every non-`jawOpen` key in VISEMES
**and** PRESETS (both layers, because `clearMorphs` must reset both), then resolve them against
the morph-target names actually in the delivered VRM, parsed straight out of the .glb JSON
chunk. Wired into `accept.py`; a missing renderer repo WARNS rather than fails, so this pack
stays usable standalone.

```
OK  clyffy.vrm byte-identical to canon (82054972 bytes)
OK  control_surface.schema.json byte-identical to canon (7696 bytes)
OK  jaw max_deg served = 10.0° (matches the contract)
OK  morph targets in the VRM: 47
OK  all 42 driven contract keys resolve to a morph target
OK  tongue/lip extension morphs driven: lipTuckLower, tongueBack, tongueCurl, tongueUp
```

**Negative-tested against the bundle that was actually shipping** — 4 FAILURES, exit 1: stale
VRM, stale schema, `jaw max_deg 22.0° vs 10.0°`, and "the served contract drives NO tongue
articulation — it predates 2026-07-29".

### Why the browser is NOT the gate

Driven headlessly, chromium boots the app correctly (HUD, controls and framing all render) but
the **82 MB VRM will not finish parsing under software WebGL** — it sits at `loading vrm…`
through a 400s virtual-time budget. So the static check above is the gate, and it asserts
exactly what `main.js` asserts. What it deliberately does NOT claim is that the face LOOKS
right: that is the operator's VERIFY gate, and no static check substitutes for it.

**A1 status: BUILT** (bundle correct and gated) — **VERIFIED pending the operator seeing it.**

## Demo reel (2026-07-29) — `tools/demo_reel.sh`

Operator asked for a video playable on another machine (this box has no speakers connected
yet) and specifically for proof it is the LATEST build. So the reel carries its own
**provenance card**, read live from the delivered artifacts rather than typed in: build
timestamp off `clyffy_v2_body.blend`, morph-target count and glTF vertex count parsed from the
`.glb` JSON chunk, `jaw.max_deg` from the published schema, gate state.

It also **REFUSES TO BUILD** if `work/voice/drive_v2/_all_lines.mp4` is older than the body
blend it depicts — a demo reel that lies about its own freshness is the same failure as the
stale renderer bundle, one layer further out.

32.4s · 720x900 · 24 fps · h264 + aac 48 kHz stereo · 1.33 MB · 23 segments:
provenance card (4s) → 5 talking lines WITH AUDIO (9.2s) → all 15 visemes, each named (10.8s)
→ 6 expression presets (8.4s).

**Verified, not assumed:** audio energy measured per window — talking `mean −24.5 dB / peak
−3.9 dB` (real speech), stills window `−91.0 dB` (silent as intended). Streams confirmed
h264 + aac stereo.

### ⚠️ ffmpeg drawtext EATS CHARACTERS AFTER AN ESCAPED MULTIBYTE CHAR
First build rendered `avatar — live face pa`, `62212 glTF vert`, `(contract` and
`pose_check GRE`. Cause: I backslash-escaped the unicode separators (`\—` `\·` `\°`), and
drawtext's parser consumes the following UTF-8 continuation bytes, silently swallowing real
characters. Not a width or centring problem — the glyphs were never drawn. **ASCII only in
drawtext**; the reason is recorded at the `esc()` helper so it is not reintroduced.

## SSOT merge + cleanup (2026-07-29)

Repo is live at `github.com/EonsofStupid/Clyffy_Avatar` (public, source+tools, 116 files /
77.3 MB). With version control in place the docs had to actually agree with each other, so this
is an audit pass, not a feature.

### Drift found and corrected

| where | was | now |
|---|---|---|
| `clyffy.pack.toml` | `count_authored = 43` | **47** (ARKit-43 + 4 extensions) |
| `clyffy.pack.toml` | `shape_keys = 44` | **48** (Basis + 47) |
| `clyffy.pack.toml` | `47280` verts | **48220** |
| `STATUS.md` chain line | missing `densify` **and** `mesh_patch`; claimed `jaw_rig(13°)` | full 14-stage chain; note that `jaw_rig`'s `ANGDEG = 22.0` is a post-build STRESS pose, not the runtime envelope |
| `STATUS.md` | `0 of 146` tongue containment | flagged — the tongue is 242 verts since 2026-07-29 |
| `STATUS.md` | G1–G7 gate table dated 2026-07-27 | marked **SUPERSEDED**, points at the RESUME block |
| `MAP.md` | 24 tools absent from the map | **every** non-`_` script classified |

### `MAP.md` — every tool classified, none left ambiguous

An unclassified file is indistinguishable from incomplete work, so the tools table now splits
into **CHAIN** (14 stages, in order) · **GATES** (6) · **CONTRACT/PRESENT/VOICE** · **DIAGNOSTIC**
(produced a number the SSOT cites) · **SUPERSEDED** (kept for provenance).

**Deliberately did NOT rename the superseded ones** to the `_*.py` probe convention: live code
and `clyffy.pack.toml` cite `jaw_drive.py`, `head_axis.py`, `stretch_map.py` and `eye_probe.py`
as the provenance of recorded measurements. Verified those four references are **comments, not
code calls** — `avatar_drive.py:6` literally says *"Replaces jaw-only flap (tools/jaw_drive.py)"*.
Tidying a filename at the cost of breaking a provenance link is a bad trade.

### ⚠️ I HAD MISREAD THE REFERENCE — corrected

Finding the wide-open interior frames (dense-sampled at 4 fps, then inspected; a warm-dark
heuristic I wrote first was picking up the kitchen lighting and had to be thrown away) fixed two
errors in my own first pass:

* The upper cavity reads **NEAR-BLACK**, not "warm maroon". The maroon is the TONGUE and the
  inner LIP RIM.
* **The teeth are a CONTINUOUS cream dental pad + arch** with canine nubs only at the corners.
  Cows have no upper incisors.

**The second one contradicts shipped work.** On 2026-07-28 I scalloped both arches into
individual teeth (`TEETH_N = 7`, `TEETH_CUT = 0.34`) precisely because they "read as one
continuous ridge of enamel". **Canon IS a continuous ridge.** Recorded in A7 as something to
reconsider against the reference rather than defend because it is recent.

Also recorded: the reference clips show **brass steampunk goggles**, which is known drift —
canon is clear polycarbonate lab safety goggles. They are a MOUTH reference only.

### POA&M
A9 added and **VERIFIED** (the repo itself). A8 **unblocked** — operator ruled the web fork lives
as a branch of `Clyffy_Avatar`, so the renderer being untracked in `clyffy` no longer blocks it.
A7 rewritten around the corrected reference. Board: **A0 ✅ · A9 ✅ · A1 BUILT · A2–A8 SPEC.**

## 2026-07-29 — A7 steps 1–3: materials authored (muzzle pad · lip bands · SSS · roughness)

NOT PROMOTED TO CANON. Built and verified on a scratch copy; the operator's beauty verdict on
`work/mouth_ab/A7_material_ab.png` gates promotion.

**Two canon violations measured, not assumed.** `_matstate.py` on the delivered blend: SSS = 0.0
on all five materials, one material over 97.6% of the face. `_lipbands.py`: the baked atlas
paints the WHOLE muzzle near-white — inner lip rim sRGB (209,200,196) vs outer band (227,217,214),
a difference of **6.9 out of 441**. So `CANON.md`'s "Broad pink muzzle" was absent as well as
"SSS — NO exceptions", and a material pass had to carry COLOUR, not just surface response.

**`present.py` was flattering the build.** Its `polish_materials()` set SSS at render time, in
RAM, and never saved — so every hero PNG showed subsurface the delivered VRM did not have. That
is why SSS = 0.0 went unnoticed for a week while the pictures looked fine. It now stands down
automatically when the mesh carries authored materials, which also makes the A/B honest: the
"before" side is exactly what had been shipping.

**Colour cannot be matched by looking, and I proved that the hard way.** The reference muzzle that
LOOKS salmon measures sRGB (120,101,137) — blue-dominant mauve, confirmed by PIL and an
independent ffmpeg decode. The image display path auto-levels every frame it renders, so a crop of
that mauve region is DISPLAYED as bright pink. It misled me twice: once on the muzzle, once when I
called the cavity "too light" — measured, its darkest quartile is (22,10,10). `_refcolor.py` works
in ratios to the fur white point instead; chroma is trusted, and luminance only where two
differently-graded frames agree independently (muzzle Y/Y_fur = 0.487 and 0.496, within 2%).

**Result, measured against the reference rather than asserted:**

| | Y_pad/Y_fur | chroma R:G:B |
|---|---|---|
| before | 0.548 | 1.39 : 0.91 : 0.77 |
| **after** | **0.461** | **1.80 : 0.80 : 0.63** |
| reference target | 0.496 | 1.76 : 0.81 : 0.66 |

Chroma lands on target; the pad is 7% darker than the reference. Reported, not chased.

**Three bugs my own diagnostics caught before the operator saw them:**
1. Dividing the atlas out per vertex clamped on **29448 verts (61% of the mesh)** — it would have
   flattened the Holstein black patches and crushed the bright fur toward mean grey. Replaced with
   ratios relative to fur, so fur stays exactly 1.0 and the atlas keeps all its variation:
   2910 verts tinted instead of 29448.
2. Re-anchoring the interior materials' LEVEL to the atlas fur made enamel mid-grey (155,150,143),
   which inside an unlit cavity would double-count the darkening and make the teeth vanish — the
   same double-counting that collapsed the tongue blade earlier. Now only HUE is rotated onto the
   measurement; the tuned luminance is kept. The cavity is the one level deliberately moved.
3. The first render showed a chain of pale scalloped lobes along the lip. **I nearly blamed the
   scalloped teeth.** They are pale, so they were the cream band itself: the skin edge at the lip
   is 0.0038–0.008 while the inner band is 0.0045, so the band is **0.89 edges wide** and its
   iso-contour festooned along the topology. Fixed by Laplacian-smoothing the distance field
   (8 passes) and by ending the pad below the mouth on GEODESIC distance so it follows the lip
   curve instead of cutting a horizontal z-line. The stage now reports band width in edge-lengths
   every build, and says outright that a crisper rim needs lip loops, not a material change.

**A silent no-op caught on the way out — the export.** The VRM addon emits a uniform-white dummy
`COLOR_0` and puts the real vertex colours in `COLOR_1`, which glTF and three.js both ignore. The
delivered VRM would have rendered the OLD white muzzle on the live surface while Blender showed
the new one — every gate green, reality unchanged, the same shape as the stale-bundle bug. Ruled
out by experiment: removing the `ShaderNodeAttribute` nodes (still two streams) and authoring as
`BYTE_COLOR`/CORNER (still two, and it quantised 1635 distinct values to 348). `vrm_color0_fix.py`
repoints `COLOR_0` at the accessor holding the data, runs automatically inside `vrm_export`, is
idempotent, and `vrm_check` passes on the rewritten file. `renderer_check.py` gained the gate that
proves it — reading vertex DATA, because colour accessors carry no `min`/`max` and a
metadata-based check would have passed every time.

Also fixed while here: my first version of that gate called three primitives FAILED that were
already correct (constant-colour materials legitimately have uniform white COLOR_0), and
`rebuild.sh --from-scratch` was still printing a 12-stage chain missing `densify`, `hoof`,
`mesh_patch` and `materials`, and citing jaw 13° instead of the 22° stress pose.

**Gates:** accept GREEN (27 checks) · vrm_check GREEN · renderer_check GREEN · materials.py's own
geometry gate asserts vertices, faces, shape keys and all 51 vertex groups byte-identical.

**Open for the operator:** the scallop. `TEETH_N=7`/`TEETH_CUT=0.34` reads as a white sawtooth
with the mouth open, and the reference measures the upper canine (176,158,130) and dental pad
(170,151,125) as the SAME colour — one continuous cream ridge, no per-tooth differentiation.
Evidence now favours reverting it. That is a geometry change and shipped work, so it is their call.

## 2026-07-30 — A7 REALIGNED to the canon art, then PROMOTED

Operator on the first version: **"stop trying to human mouth this what the hell happened to my
references"** — then, after realignment, **"looks good"**. Promoted to canon.

**I was using the wrong reference, and it was my own choice, not a missing file.** I measured
colour off `canon/mouth_ref/v1_*.png` / `v2_*.png` — frames I had extracted from the operator's
VIDEOS. One is a blue night scene where white fur measures (113,160,217). The neutral, purpose-
built modelling reference was on disk the whole time and I never opened it:
`canon/base_sheet/Clyffy_BASE-NEUTRAL-v1.png`, a 5-view turnaround under even lighting.

| source | Y_pad/Y_fur | chroma R:G:B |
|---|---|---|
| canon base sheet, lit pad | 0.80–0.89 | 1.31 : 0.92 : 0.83 |
| canon anchor art, lit pad | 0.63–0.70 | 1.41–1.50 : 0.88 : 0.74 |
| what I built | 0.496 | 1.76 : 0.81 : 0.66 |
| canon anchor art, **shaded underside** | 0.373 | **1.76 : 0.81 : 0.62** |

My value is a dead match for the SHADED UNDERSIDE. I sampled shadow out of graded video and used
it as the albedo of the entire pad — 40% too dark, 35% too saturated. **Rule now in the pack:
albedo comes from a neutrally lit reference; graded frames are for structure and motion only.**

**The lip bands were my invention, not a measurement.** "Three concentric bands: salmon inner rim
→ cream outer band → fur" is HUMAN vermilion-border anatomy. It is on neither canon source. I
wrote it as prose into `canon/mouth_ref/README.md` off a low-resolution plate, and then measured
colour *rigorously in service of it*. Every number was right and the target was invented. The
mouth is a SLIT IN THE PAD; the lips are the pad continuing, and the dark lip line is geometry and
occlusion, not paint. Deleted, with `lip_bands = false` recorded so it does not come back.

Deleted with it: the `skin_wet` gloss ring at the lip, which was the specular half of the same
mistake — removed rather than left unused, since an unused attribute is indistinguishable from
unfinished work.

**Also corrected:** the lateral anchor was "56% of face width", but face width is ambiguous on this
character — the mesh measurement included the ears, so the phrase meant two different things in the
art and in the mesh. Now anchored to EYE SEPARATION, which is exact in both (the art shows it, the
mesh publishes `eye_L_center` / `eye_R_center`).

**Delivered, measured:** rendered pad Y 0.624, chroma 1.54:0.87:0.73 — inside the anchor art's
bracket. Residuals stated in POAM A7 and the pack: ~17% more saturated and ~25% darker than the
neutral sheet (SSS pushes red; the rest is the light rig), and the pad boundary is a smooth
gradient where the reference shows pore stipple and fur feathering over the edge.

**Promotion:** materials → VRM re-export (vrm_color0_fix promoted COLOR_0 on 2 primitives,
verified by re-read) → 6 heroes + hero sheet + viseme sheet re-rendered → live bundle refreshed in
BOTH `dist/` and `public/` (public/ is the same inode as canon, so it cannot drift).
**accept GREEN (27) · vrm_check GREEN · renderer_check GREEN.**
Rollback: `clyffy_v2_body.blend.pre-mat`, `clyffy.vrm.pre-mat`.

**Correction to the 2026-07-29 entry below:** everything it records about the three-band lip
structure describes work that has since been deleted as wrong. The measurement discipline in it
still stands; the target it was aimed at does not.

## 2026-07-31 — A10 B0: reference motion breakdown (PARTIAL — 1 of 3 shots measured)

Operator: *"the snout does nothing and the bottom has so [no] wiggle… ears need to be able to have
some wobble… quality not speed… work it through each beat as a true senior artist would."*

**The root diagnosis first, and it is not what I assumed.** The ears do not wobble because
**nothing ever moves the head.** `renderer/src/main.js` `idle()` touches only `eyeL/eyeR.rotation`
and the blink morphs. The spring chains ARE authored (ears + tail) and ARE simulated
(`vrm.update(dt)`) — they have zero excitation, so the simulation faithfully computes no motion.
I would have spent a day tuning stiffness on a rig that was already correct.

**Measured, valid (ruler stable to 3.1%, 40 frames, confirmed by eye):**

| quantity | reference | ours |
|---|---|---|
| pad HEIGHT varies | **24.0%** | pad p90 travel 0.05–1.65 %H, all at the lip edge |
| pad WIDTH varies | **3.1%** | — |
| pad AREA varies | **42.1%** | — |
| nostril area varies | **42.9%** | `noseSneer` moves **0%** of pad verts past 1 %H |
| aperture hold, median / p90 | **62.5 / 187.5 ms** | live path writes weights straight to target: ~42 ms, no hold |

Height varies ~8× more than width: the snout **squashes vertically and holds its width** — a soft
mass. Ours is a rigid plate on a hinge.

**NOT measured, and B1/B2 are blocked on it:** head sway amplitude/rate needs a longer, wider
shot than the closeup; ear lag needs an ear-visible shot (`ear_frames = 0` in the only valid one).
Two of three declared shots failed their ruler gate — a camera push-in in one (real scale change,
not tracker error) and muzzle/neck flip-flop in the other. **Recorded as unmeasured rather than
estimated.**

**THE EXPENSIVE LESSON — complexity was the bug.** The measurement worked on the FIRST attempt:
tight hand-chosen crop, plain absolute pink rule, raw min/max bbox → 3.8% stability. I then
"improved" it four times — coarse-grid mode seeking, robust percentile bounds, a white-balanced
hue test, ROI mean-shift — and every addition made it strictly worse: 3.8% → 30% → 67% → 81%.
Reverting to the naive version restored 3.1%. Every addition was solving a problem the CROP had
already solved. Two sub-lessons kept in the tool: a whole-head crop makes the detector lock onto
the **brass steampunk goggles** (warmest thing on the head — crop below the eyes instead of
out-clevering it), and a fixed `R > B` hue rule inverts under the blue night grade where the
muzzle measures (120,101,137).

Five successive auto-detectors were also the wrong instinct outright. An artist picks the take by
LOOKING; `tools/ref_motion.py` now carries an explicit shot manifest — clip, frame range, crop —
chosen off gridded overlays and validated against a debug contact sheet every run.

Deliverables: `tools/ref_motion.py`, `work/ref_motion/REFERENCE_SHEET.md`, `ref_motion.json`,
per-shot curve plots and `_track_*.png` validation sheets. **No authoring; the avatar is untouched.**

## 2026-07-31 (later) — A10 B0: operator supplied a clean reference; B1 unblocked

Operator: *"what about these for reference instead of risking you grabbing wrong characters or
wrong scenes which seem to keep happening"* — supplying `6f675283`: ONE character, isolated on
pure black, ears visible throughout, 8 s of continuous performance.

**That was the correct call and it fixed the problem at the source.** Measured: background
5th-percentile luminance 0.0, only two framing changes in the clip, so frames 0–191 are one
unbroken take. With a black background the silhouette IS the character — there is nothing to
mistake it for. Five auto-detectors and four "improvements" had been spent fighting clutter that
this clip simply does not contain. **The fix was better FOOTAGE, not a better detector**, and I
should have asked for it instead of building a fifth tracker.

**B1 targets now measured** (crown of the silhouette — a rigid skull point needing no anatomy
segmentation; ruler = silhouette height 349 px, stable to 6.9%, 100% tracked over 192 frames):

| quantity | reference | ours |
|---|---|---|
| crown X peak-to-peak | **0.437** body-heights | **0.000** |
| crown X rms | **0.084** | 0.000 |
| crown Y peak-to-peak | **0.069** | 0.000 |
| dominant rate | **0.375 Hz** X / **0.25 Hz** Y | — |
| median per-frame crown movement | **0.0031** | 0.000 |

The head is never still: it moves every frame, sways ~6× more horizontally than vertically, on a
slow 2.7–4 s rhythm rather than a jitter. Ours never moves, which is simultaneously why it reads
robotic and why the ear springs — correctly authored, genuinely simulated every frame — produce
exactly zero wobble. **B1 is the prerequisite for B2, not a parallel nicety.**

B4 targets stand from the earlier valid shot (pad height 24.0%, width 3.1%, area 42.1%, nostril
42.9%). B3 hold times stand (aperture hold median 62.5 ms, p90 187.5 ms); rise times remain
flagged as a single excursion, not yet a distribution.

**B2 (ear lag) still not measured** — `ear_extent` looks for dark flaps against light and the
polarity is inverted on this clip. The footage is right (ears visible in all 192 frames, clearly
swinging); what is needed is ear TIPS from the silhouette outline, then ear-tip motion minus crown
motion. One measurement away on footage that already works.

`tools/ref_motion.py` now carries both methods — `silhouette` for black-background clips and
`crop` for the muzzle closeup — with the shot manifest, frame ranges and crops declared and
validated against a `_track_*.png` contact sheet every run. No authoring; the avatar is untouched.

## 2026-07-31 (B0 closed) — ear motion measured; lag deliberately left open

Ears now tracked in **all 192 frames** of the isolated clip, via the silhouette outline in a band
8–20% of figure height below the crown. 20 frames rejected where raised arms exceeded the ears
laterally and would have read as ear motion.

**The usable B2 target — ear reach rms 0.0926 / 0.0958 body-heights against crown rms 0.0841, i.e.
the ears travel ~1.1× as far as the head translates.** A ratio, so it transfers to our rig at any
scale, and it is what spring stiffness and drag get tuned against.

**Lag came out 0 frames on both ears and I am NOT reporting that as a finding.** The outline's
sideways reach responds to ear swing AND to head rotation, so a head turning in place moves the
signal with no ear dynamics at all — lag-0 is the signature of a pose-dominated measurement, not
evidence that the ears do not trail. The settle figure from the same signal (median 42 ms, p90
83 ms) inherits the contamination and is recorded as an upper bound, not a target.

Isolating true spring lag needs the ear tip in the SKULL's frame, which needs head orientation —
more than the crown gives. Left open on purpose: B1 is the prerequisite for ANY ear motion (the
springs are authored and simulated correctly and produce zero wobble solely because the head never
moves), and the amplitude ratio is sufficient to tune against. Revisit only if B2 looks wrong once
B1 lands.

**B0 is CLOSED.** Targets in `work/ref_motion/REFERENCE_SHEET.md`: B1 head motion (solid), B4 snout
deformation (solid), B3 hold times (solid; rise times still a single excursion), B2 amplitude
(solid) with lag/settle explicitly unestablished. No authoring — the avatar is untouched.

## 2026-08-01 — A10 B1 SHIPPED: the head and body move; idle_check GREEN

`control_surface.IDLE` + `idle_pose()` is the SSOT (emitted into the schema); the web renderer
consumes it via `applyIdlePose()`, and `tools/idle_check.py` verifies it against the measured
reference. **idle_check GREEN: crown X rms 0.0166 vs target 0.0168 (0.99x), Y 0.0110 vs 0.0101
(1.09x).** accept GREEN · vrm_check GREEN · renderer_check GREEN.

**A measurement definition was wrong on BOTH sides, and fixing it changed two beats.** "Crown" was
the topmost silhouette rows — which are horn TIPS. Rolling the head raises one horn and lowers the
other, so a tip centroid partly cancels: it **under-reported lateral motion by ~6×** (target read
0.0383 when the truth is 0.0168). Switching both `ref_motion.py` and `idle_check.py` to the
HEAD-MASS centroid (mean over the top 12% of the figure) fixed it — and gave the skull a clean
rigid reference, which **also separated the ear lag that B0 had recorded as unmeasurable: 166.7 ms,
4 frames.** The earlier lag-0 was an artefact of the reference point, exactly as suspected; noting
it as untrustworthy rather than publishing it turned out to be the right call.

Targets are **idle-specific**, from the six quietest 2 s windows (X rms 0.0168), not the whole take
(0.0818, which includes pointing/leaning/arms-crossed). Building idle to the whole-take number
would read as drunk.

**Four bugs found by measuring rather than assuming:**
1. `pose_bone.matrix` silently discards translation on CONNECTED bones — spine/chest/neck/skull are
   all connected, so every rotation except hips (the one unconnected bone) did nothing. Calibration
   reported exactly 0.00000 for six of seven drivers while a depsgraph read showed the same
   rotations moving the crown 0.18 units. Replaced with `matrix_basis` conjugation.
2. The calibration MEASURED via a render and read stale/blank results. Rewritten to read the
   evaluated mesh — the camera is orthographic and aligned to lat/up, so projecting the mesh IS
   what a render would measure, ~50× faster and with no rendering pipeline in the error budget.
3. `pose_bone.location` is already in SCENE units; dividing by `bone.length` (0.0196) overshot the
   vertical bob ~50×, putting crown Y rms at 0.66 against a target of 0.0101.
4. `set_bone_rotation` assigns `matrix_basis` wholesale, so the hips translation had to be applied
   AFTER the rotations or it was silently wiped.

**Amplitudes are derived, not guessed.** `idle_check --calibrate` measures crown displacement per
degree per driver: head_roll 0.01246, spine_roll 0.00452, hips_roll 0.00418 lateral; head_pitch
0.00061, chest_pitch -0.00057 vertical. Head ROLL is the strongest lateral driver (3× the spine)
because the crown is the horn tips. The spine still carries the bulk of the amplitude because that
is where a real weight shift originates. Vertical bob is authored as a hips TRANSLATION because
rotation cannot produce it — for small angles height changes by (1-cos t), which vanishes.

Reported honestly: dominant-frequency readout (0.125 Hz vs 0.375 Hz target) is an FFT RESOLUTION
artefact — an 8 s window has 0.125 Hz bins, so a 0.19 Hz term lands in the 0.125 bin. Not gated.

**NOT verifiable here: ear wobble.** VRM spring bones are simulated by the web renderer
(`vrm.update(dt)`), not by Blender. This gate proves the head MOVES — the excitation the springs
were missing. The wobble itself is the operator's eye on the live surface, and `idle_check` says so
in its own output rather than implying coverage it does not have.

Renderer rebuilt (`vite build` → `index-Cf1xjuTk.js`) because dist/ serves a BUILT bundle and a
source edit alone would not have shipped. `public/` are symlinks to canon and cannot drift.
`drive_frames.jsonl` re-driven after the schema changed, clearing the staleness warning.

## 2026-08-03 — canon restructured to ONE reference; first PROFILE measurement in the project

**Reference.** Operator: *"use and do this one, move the rest to archive … so we only have this,
this is perfect."* `canon/reference/` is now the single authoritative face reference — three
flat-lit 2k sheets (front / 3-4 / TRUE 90° profile, mouth closed; the same three mouth open; muzzle
close-up in profile) generated from a new higgsfield element built off the operator's own clip, so
it is that exact character rather than a lookalike. Four superseded sets moved to `canon/_archive/`,
dated, each with a stated reason; git recorded every move as a rename.

**THIS IS THE FIRST REFERENCE SET WITH A PROFILE.** Every proportion failure in this build — snout
projection, head length, lip curve, chin — is a profile problem, and every measurement taken before
today was front-on. `canon/base_sheet/` has had a 90° side view since 2026-07-25 and it was never
opened. Single biggest process miss of the project.

**First profile numbers** (`tools/head_metrics.py`, identical pipeline both sides):

| | reference | ours |
|---|---|---|
| snout projection forward of the forehead, ÷ head depth | **0.144** | **0.347** |
| head height ÷ head depth | 0.868 | 0.777 |

**Our snout projects ~2.4x too far forward, while head height/depth is within 10%.** That
CONTRADICTS what I concluded from the front view, where the pad reads flat and I assumed it needed
to come forward. Both can be true at once and the distinction matters: the muzzle protrudes too far
as a MASS, while the pink PAD on its surface is too flat and undefined. Front-on measurement cannot
tell those apart, which is exactly why the snout work kept missing.

**Segmentation had to be rebuilt to get there.** The reference sheets put WHITE FUR (225,220,217)
on a grey field (208-223) carrying a gradient, so colour distance either eats the fur or keeps the
background — the first attempt produced a fragmented mask and read the snout tip off a neighbouring
panel bleeding into frame. Replaced with: flood-fill the background from every border pixel (the
field is connected, the character is an island), keep the component containing the centroid, fill
interior holes so the brown patches do not notch the outline. Verified by eye before any number was
quoted, because the first version's numbers looked plausible and were nonsense.

Also fixed en route: an ad-hoc H/D of 1.360 vs 0.943 that was including the coat on the reference
side only. The tool's own crown/chin detection gives 0.868 vs 0.777 — a 10% difference, not a 40%
one. Mismatched extents again; that is the fourth time this session.

No geometry authored yet. `tools/head_proportion.py` is built and gated but its parameters are
still driven visually, because its ASPECT readout remains untrustworthy for the same
definition-mismatch reason and is labelled as such in the source.

---

## 2026-08-03 — the proportion pass shipped, and the 2.4x figure it was built on was WRONG

The entry above this one is retained as written because it records a real process improvement, but
**its headline number is retracted.** "Our snout projects ~2.4x too far forward" was measured with a
brow row placed at a fraction of crown-to-CHIN, and on the reference sheet the chin is set by the
**LAB COAT**. That dropped the brow row onto the muzzle itself, so `x_brow` came out nearly equal to
`x_snout` and the reference's own projection collapsed to a third of its true value. Our render has
no coat, so the two sides were measuring different rows of different animals.

Reproduced live rather than argued: the same reference panel measured **0.404, then 0.070**, purely
from where the chin landed. Segmentation was NOT the cause — the old flood-fill scores 0.488 on the
corrected metric against the new path's 0.455.

**The front view had been right the whole time. The muzzle needed to come FORWARD.**

### The metric that replaced it

`tools/profile_shot.py` (new) renders a true 90 degree side view; `head_metrics.snout_projection`
measures it and the reference panel through ONE function. Anchored on **crown and snout tip only** —
two landmarks that are unambiguously head on both sides — so nothing below the muzzle can enter it.

| | reference | before | after |
|---|---|---|---|
| snout past brow ÷ skull behind brow | **0.455** | 0.401 (0.88x) | **0.454 (1.00x)** |
| muzzle depth ÷ crown-to-snout-tip | **0.635** | 0.547 (0.86x) | **0.642 (1.01x)** |

Shipped at **`--snout 1.15 --muzzle 1.35`**. Verified on the FINAL body after all twelve downstream
stages, not on the reshape stage alone. `tools/run_chain.sh` (new) encodes the whole order.

### Five defects found on the way, each of which produced a confident wrong answer

1. **The snout band had no lower edge.** `wz` was 1 for every vertex below its cutoff — **39141 of
   46001 verts, 85% of the body, down to the hooves at z=-0.489.** Only the `ahead` gate kept the
   chest from being dragged backwards; it worked by accident. The band is now MEASURED: for each
   horizontal slice of the head, how far it reaches past the brow plane. That profile is the muzzle,
   bounded at both ends by measurement.
2. **`ahead` was 40% longer than the entire snout.** Ramp `0.35 x head depth` = 0.1204 against a
   projection of 0.0859, so the whole muzzle sat inside the fade, **`w_sn` peaked at 0.714 with zero
   verts above 0.9**, and the pullback floored at 71% for any `--snout`. That was the saturation
   chased for hours.
3. **A weight sampled by BIN INDEX, not interpolated.** `pzn[bi]` was piecewise-constant over 64
   slabs ~0.0037 units thick — comparable to an edge length — so every bin boundary was a normal
   discontinuity, i.e. a real crease. At `--muzzle 1.35` it multiplied crease edges in the upper
   face **99 -> 325** and fused the two eye-socket rims (25 and 21 verts) into one 240-vertex band
   across the midline: `eye_open` reported *"expected 2 eye rims, got 1"*. Now `np.interp`.
4. **All 48 shape keys are SAVED AT VALUE 1.0** from `shape_author` onward. The render shows the
   evaluated mesh, so every ARKit blendshape was stacked at full strength — the muzzle measured
   0.454 -> 0.270 across that stage and the face LOOKED torn and shattered. It was not; the rest
   shape was simply never being displayed. **The shipped canon body carries the same state**, so
   this is pre-existing and worth a separate look, not a regression.
5. **Thin polygon slivers around the mouth corner** set `x_snout`, an extreme point. One 1-px spike
   60px forward of the muzzle dragged the tip row 175px down the face and reported **0.123 against
   0.455** — a 0.27x "regression" that was one stray sliver. `head_metrics.opening()` now removes
   structures thinner than the kernel before any landmark is taken.

`blender -b --python` **returns 0 even when the script raised**, so the first chain run sailed past
the eye-rim assertion and ran eleven more stages against files that were never written. Every stage
in `run_chain.sh` now declares the artefact it must produce and the chain stops when it is missing.

### Mismatched extents, the project's signature failure, twice more

`profile_shot` cut the head at `z_hi - 0.30*H` — a fraction of FIGURE height. The neck compression
moves the head down, so the same formula cut at 0.1957 on the canon body and 0.1706 on the reshaped
one and the two "head-only" silhouettes were not the same anatomy. Now anchored to `op_lip_seam`,
an operator group carried through every stage. Facing was likewise assumed at FWD=235.1 and is now
measured from the lip seam (all chain blends read 233.0-233.7; `body_rig` does NOT reorient, which
disproved the hypothesis that it did).

That is the fifth and sixth instance. Every one had the same shape: two definitions that agreed with
each other while both were wrong about the world.

### Counts after the reshape

`densify` subdivides by edge length, so a reshaped head changes what it does: **+1128 verts** (was
+940). Chain totals **48254 verts / 48127 faces** (were 48220 / 48077). `mesh_patch` GREEN —
watertight, 0 non-manifold, 0 boundary. `vrm_check` GREEN. `accept.py` GREEN.

Backup of the pre-reshape canon artefacts: `mesh/_prev_2026-08-03_pre_proportion/`.
