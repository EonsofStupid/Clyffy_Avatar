"""Add teeth and a tongue inside the mouth bag.

    blender -b --python tools/mouth_parts.py -- <eyes.blend> <out_dir> <fwd_deg>

HARD ACCEPTANCE CRITERION: nothing may be visible at REST. The lips are shut (slit
0.0077) and the parts sit behind them inside an opaque head, so containment is checked by
rendering the closed pose, not asserted.

Requires the mouth BAG, not the original flat slot. The first cavity was 0.1846 deep,
0.1445 wide and only 0.0077 TALL -- no room for teeth (~0.009), let alone a tongue.
tools/mouth_open.py now expands the rings vertically to a ~0.050 pocket.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
SRC, OUT, FWD = os.path.abspath(argv[0]), os.path.abspath(argv[1]), float(argv[2])
INSET     = float(argv[3]) if len(argv) > 3 else 0.030   # back from the lip rim
TOOTH_H   = float(argv[4]) if len(argv) > 4 else 0.009
TOOTH_D   = float(argv[5]) if len(argv) > 5 else 0.008
# OVERBITE / OVERJET. A flat shared bite plane contains the teeth perfectly but hides them:
# the upper crown lands level with the upper lip rim, so opening the jaw reveals ~0.0007 of
# tooth and the mouth reads toothless. Real mouths solve this with an OVERBITE — the upper
# crowns hang BELOW the lower ones — and avoid intersecting by an OVERJET, sitting further
# FORWARD. Separation is then horizontal, which the jaw's rotation only ever increases.
OVERBITE  = float(argv[6]) if len(argv) > 6 else 0.0035  # upper crown below the bite plane
OVERJET   = float(argv[7]) if len(argv) > 7 else 0.006   # extra inset on the LOWER band
# INDIVIDUAL TEETH. The band is a single swept solid, so at any real zoom it reads as one
# continuous ridge of enamel rather than teeth — visible across the whole viseme sheet once
# the arches stopped intersecting. Scalloping the crown along the arc gives discrete tips
# without changing the band's topology: still one closed solid, still 4 verts per ring.
TEETH_N   = int(argv[8]) if len(argv) > 8 else 7        # teeth per arch
TEETH_CUT = float(argv[9]) if len(argv) > 9 else 0.34   # crown drop at a gap, as a fraction
                                                        # of tooth height (0 = old flat band)
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
ob = [o for o in bpy.data.objects if o.type == "MESH"][0]
me = ob.data
assert max(abs(x) for x in ob.matrix_world.to_euler()) < 1e-6, "input not canonical"
N0 = len(me.vertices)
co = np.empty((N0, 3)); me.vertices.foreach_get("co", co.ravel())
zmin, zmax = co[:, 2].min(), co[:, 2].max(); H = zmax - zmin
a = math.radians(FWD)
fwd = np.array([math.sin(a), -math.cos(a), 0.0]); lat = np.array([-fwd[1], fwd[0], 0.0])
inward = -fwd

di = [i for i, m in enumerate(me.materials) if m.name.startswith("clyffy_mouth_interior")][0]
cav = {v for p in me.polygons if p.material_index == di for v in p.vertices}
surf = {v for p in me.polygons if p.material_index != di for v in p.vertices}
rim = np.array(sorted(cav & surf))
mouth = co[sorted(cav)].mean(axis=0)
hc = co[co[:, 2] > 0.208].mean(axis=0); lat0 = float(hc @ lat)
print(f"cavity {len(cav)} verts, rim {len(rim)}, bag z[{co[sorted(cav),2].min():+.4f},"
      f"{co[sorted(cav),2].max():+.4f}] height {co[sorted(cav),2].max()-co[sorted(cav),2].min():.4f}")

# ---- walk the rim loop and split at the commissures (same as jaw_rig) ----
ef = {}
for p in me.polygons:
    vs = list(p.vertices)
    for k in range(len(vs)):
        i, j = vs[k], vs[(k+1) % len(vs)]
        ef.setdefault((min(i, j), max(i, j)), []).append(p.material_index == di)
rimset = set(int(x) for x in rim)
adj = {}
for (i, j), mats in ef.items():
    if i in rimset and j in rimset and any(mats) and not all(mats):
        adj.setdefault(i, []).append(j); adj.setdefault(j, []).append(i)
assert set(len(v) for v in adj.values()) == {2}, "rim is not a simple cycle"
start = int(rim[0]); cyc = [start]; prev, cur = None, start
while True:
    nxt = [n for n in adj[cur] if n != prev]
    prev, cur = cur, nxt[0]
    if cur == start: break
    cyc.append(cur)
cyc = np.array(cyc); L = len(cyc)
clat = co[cyc] @ lat - lat0
ci = sorted([int(np.argmin(clat)), int(np.argmax(clat))])
chainA = np.zeros(L, bool); chainA[ci[0]:ci[1]+1] = True
if co[cyc[chainA], 2].mean() > co[cyc[~chainA], 2].mean(): chainA = ~chainA
lower_idx = cyc[chainA]; upper_idx = cyc[~chainA]
print(f"rim cycle {L}, commissures at {ci} -> lower chain {len(lower_idx)}, upper {len(upper_idx)}")

def ordered_chain(mask):
    """chain vertices in loop order, trimmed away from the commissures"""
    order = [int(cyc[k]) for k in range(L) if mask[k]]
    # re-walk so the points are contiguous along the loop
    seq, k0 = [], None
    for k in range(L):
        if mask[k] and (k == 0 or not mask[k-1]): k0 = k
    if k0 is None: k0 = 0
    k = k0
    while mask[k % L]:
        seq.append(int(cyc[k % L])); k += 1
        if len(seq) > L: break
    trim = max(1, len(seq)//10)
    return seq[trim:len(seq)-trim]

def smooth(pts, passes=2):
    P = [Vector(p) for p in pts]
    for _ in range(passes):
        Q = [P[0]] + [(P[i-1] + P[i] + P[i+1])/3.0 for i in range(1, len(P)-1)] + [P[-1]]
        P = Q
    return P

bm = bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

def local_inward(pts):
    """Per-point horizontal inward normal of the lip curve.

    The original swept every ring along the GLOBAL -fwd. On a curved mouth that is only
    correct at the centre: at the commissures the lip runs fore-aft, so a -fwd offset drives
    the band sideways INTO the cheek wall instead of back into the bag. That is what put
    white tooth slivers at both corners in the rest pose — visible in every hero render
    since the teeth were added.
    """
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])
        t.z = 0.0
        if t.length < 1e-9:
            out.append(Vector(inward)); continue
        t.normalize()
        nrm = Vector((-t.y, t.x, 0.0))               # rotate the tangent 90° in plane
        # ORIENT TOWARD THE CAVITY CENTROID, not toward global -fwd. At the commissures the
        # lip runs fore-aft, so the rotated tangent is nearly ±lat and its dot with -fwd is
        # ~0 — the sign test becomes a coin flip and some end rings get an OUTWARD normal,
        # which drives the band out through the cheek past the mouth corner. Measured: 4
        # upper-band verts leaking at arch position 1.43, i.e. wider than the mouth itself,
        # and completely unresponsive to INSET (they were never leaking through the slit).
        # The centroid direction is well-conditioned everywhere on the loop.
        aim = Vector(mouth) - Vector(p); aim.z = 0.0
        if nrm.dot(aim) < 0:
            nrm = -nrm
        out.append(nrm)
    return out


def sweep_band(pts, up_sign, inset, height, depth, z_bite):
    """Sweep a rectangular profile along a polyline -> a closed solid band.

    Both bands terminate on a SHARED BITE PLANE. Building each band off its own lip chain
    instead let them occupy the same space: the chains sit 0.0077 apart while each band was
    `height` (0.009) tall, so the two overlapped by ~0.0068 at rest and stayed interpenetrated
    to ~35% open (measured gap −0.83%H). Two intersecting enamel surfaces is what read as a
    torn white ribbon across ten visemes.

    Height tapers toward the commissures so nothing pokes through where the lip wraps.
    """
    uv = Vector((0, 0, 1))*up_sign
    nrms = local_inward(pts)
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        s = min(i, n - 1 - i) / max(n*0.25, 1e-9)
        s = min(s, 1.0)
        h = height * (0.45 + 0.55*(s*s*(3 - 2*s)))    # smoothstep, 45% at the ends
        # SCALLOP: raised cosine along the arc, one period per tooth. Full height at a tooth
        # centre, cut back by TEETH_CUT at the gap between two teeth. The crown is what the
        # viewer reads, so shaping it is enough — no extra geometry, no seams to keep closed.
        if TEETH_N > 0 and TEETH_CUT > 0 and n > 1:
            arc = i / (n - 1)
            lobe = 0.5 * (1.0 + math.cos(2.0*math.pi*TEETH_N*arc))   # 1 at centre, 0 at gap
            h *= (1.0 - TEETH_CUT) + TEETH_CUT*lobe
        iv = nrms[i]
        b = Vector(p) + iv*inset
        b.z = z_bite - up_sign*h                      # crown lands ON the bite plane
        rings.append([b, b + uv*h, b + iv*depth + uv*h, b + iv*depth])
    grid = [[bm.verts.new(q) for q in ring] for ring in rings]
    faces = []
    for i in range(len(grid)-1):
        A, B = grid[i], grid[i+1]
        for k in range(4):
            k2 = (k+1) % 4
            faces.append(bm.faces.new((A[k], A[k2], B[k2], B[k])))
    faces.append(bm.faces.new(tuple(grid[0][::-1])))
    faces.append(bm.faces.new(tuple(grid[-1])))
    return [v for r in grid for v in r], faces

lower_pts = smooth([co[i] for i in ordered_chain(chainA)])
upper_pts = smooth([co[i] for i in ordered_chain(~chainA)])
# THE BITE PLANE — the one height both arches close onto. Taken as the mid-height of the
# closed lip rim, so at rest the crowns meet and neither band intrudes on the other.
z_bite = float(0.5*(co[lower_idx, 2].mean() + co[upper_idx, 2].mean()))
print(f"bite plane z {z_bite:+.4f} (lower chain {co[lower_idx,2].mean():+.4f}, "
      f"upper {co[upper_idx,2].mean():+.4f}) — both arches close onto it")
lo_v, lo_f = sweep_band(lower_pts, +1, INSET + OVERJET, TOOTH_H, TOOTH_D, z_bite)
up_v, up_f = sweep_band(upper_pts, -1, INSET, TOOTH_H, TOOTH_D, z_bite - OVERBITE)
print(f"  overbite {OVERBITE:.4f} (upper crowns hang below the bite plane), "
      f"overjet {OVERJET:.4f} (lower band sits further back) — separation is HORIZONTAL")
print(f"teeth: lower band {len(lo_f)} faces over {len(lower_pts)} points, "
      f"upper band {len(up_f)} faces over {len(upper_pts)} points")

# ---- tongue: AUTHORED, lofted inside the bag's own measured cross-section ----
# The first tongue was a UV sphere squashed into an ellipsoid. Measured on the delivered
# body blend, its fore-aft profile was a palindrome — width 0.033 / 0.044 / 0.050 / 0.050 /
# 0.044 / 0.033 — i.e. no root, no blade, no tip, no dorsum, the same shape read backwards.
# It was also 5.15%H wide inside a 14.47%H bag (36% of the room), 1.33%H tall inside a
# 5.16%H pocket (26%), and it was parked with its front 9.51%H BEHIND the lip rim, which put
# it further back than the lower teeth themselves.
#
# That last number is the one that mattered, because it is also why `tongueOut` never
# worked. That shape rigidly translated the whole lozenge 4.80%H forward against a 9.31%H
# gap, so the tip finished 5.29%H SHORT of the lip plane — the morph could only ever show a
# red patch through the slit, never a tongue. Its 0.048H constant had been reasoned from the
# TEETH INSET (0.030) instead of from where the tongue actually sat, so it was answering a
# question nobody asked.
#
# So the geometry is the fix, and the morph is downstream of it: put the tongue where a
# tongue is — filling the floor of the bag, tip just behind the lower incisors — and derive
# the envelope from the CAVITY at build time so it keeps fitting if mouth_open's pocket
# changes. Nothing here is a hard-coded size; every dimension is a fraction of measured room.
TONGUE_NS   = 15      # stations, root -> tip
TONGUE_NR   = 16      # ring points around each station
T_FILL_LAT  = 0.62    # of the local bag half-width
T_FILL_UP   = 0.58    # of the local bag height
T_FLOOR     = 0.0010  # stand-off from the bag floor
T_CEIL      = 0.0022  # stand-off from the bag ceiling / upper teeth
T_LIP_CLEAR = 0.0012  # dorsum ducks this far under the lower lip edge (see below)
T_TIP_CLEAR = 0.0040  # tip stands off the lingual face of the lower incisors
T_UNDER     = 0.24    # share of section height that sits BELOW the section centre
T_GROOVE    = 0.20    # midline dorsal groove, as a fraction of local height
T_SECT_N    = 2.5     # cross-section superellipse exponent (2 = ellipse, higher = fuller)
T_TIP_RISE  = 0.16    # tip lifts toward the alveolar ridge, as a fraction of bag height

cavl = np.array(sorted(cav))
_cf = co[cavl] @ fwd
_cl = co[cavl] @ lat
_cz = co[cavl, 2]
f_back, f_front = float(_cf.min()), float(_cf.max())
floor_z = float(_cz.min())

def bag_at(f):
    """Local bag centre-lat, half-width, floor and ceiling at fore-aft position f.

    Sampled from a window of cavity verts rather than a fixed bin, so it never returns an
    empty slice on a sparse part of the pocket — the bag is only 186 verts.
    """
    win = (f_front - f_back) * 0.15
    m = np.abs(_cf - f) <= win
    if int(m.sum()) < 4:
        k = np.argsort(np.abs(_cf - f))[:8]
        m = np.zeros(len(_cf), bool); m[k] = True
    lo, hi = float(_cl[m].min()), float(_cl[m].max())
    return 0.5*(lo + hi), 0.5*(hi - lo), float(_cz[m].min()), float(_cz[m].max())

# The tip's stop is the LOWER INCISORS, measured, not a guess: take the lower band near the
# midline and stand off the back of it. Using the whole band would read its commissure ends,
# which sit much further back and would put the tip in the middle of the mouth again.
_lo_co = np.array([[v.co.x, v.co.y, v.co.z] for v in lo_v])
_lo_f = _lo_co @ fwd
_lo_l = _lo_co @ lat - lat0
_mid = np.abs(_lo_l) < 0.020
if int(_mid.sum()) < 3:
    _mid = np.abs(_lo_l) < 0.040
f_tip  = float(_lo_f[_mid].min()) - T_TIP_CLEAR
f_root = f_back + 0.05 * (f_front - f_back)
assert f_tip > f_root, f"no room for a tongue: tip {f_tip:+.4f} is behind root {f_root:+.4f}"

# Upper band ceiling — the bag's own ceiling does not know the teeth are hanging from it.
_up_co = np.array([[v.co.x, v.co.y, v.co.z] for v in up_v])
_up_f = _up_co @ fwd
_up_z = _up_co[:, 2]

# THE DORSUM DUCKS UNDER THE LIP EDGE AS IT COMES FORWARD, and that is a measured
# constraint, not a stylistic one. First build put the dorsum's high point at z +0.2247 and
# lip_seal's containment gate failed with exactly one visible vertex. Scanning the sealed
# head for where a straight-ahead ray can get out gives the reason precisely: there is a
# PINHOLE through the sealed lips at z [+0.22448, +0.22484] — 0.037%H tall — and that vertex
# was sitting in it. The scan also gives the shape of the constraint:
#
#     station f < 0.055   highest contained z = +0.2320   (rays run into the palate)
#     station f > 0.055   highest contained z = +0.2244   (rays reach the lip slit)
#
# So the ceiling is not the bag's ceiling once you come forward of mid-bag; it is the lower
# lip edge. Deriving it from `rim` rather than hard-coding +0.2244 keeps it true if the lips
# move. It happens to be the right anatomy too — a tongue's dorsum is highest at the back.
# The ramp is deliberately LONG. A short one (0.22 -> 0.38 of the bag) put the whole descent
# inside a single station gap and produced a visible step in the dorsum; the constraint only
# has to be met by f ~ 0.055, so start it early and arrive gradually.
z_rim_lo = float(co[rim, 2].min())
_f_duck0 = f_back + 0.10 * (f_front - f_back)   # start ducking
_f_duck1 = f_back + 0.45 * (f_front - f_back)   # fully under the lip edge

# Shape profiles over s (0 = root, 1 = tip). Width peaks over the blade and tapers hard into
# the tip; height peaks BEHIND that, which is what gives the dorsum its rise — and keeps the
# high point behind the duck zone above, where there is headroom for it.
# The tip control point is 0.38, not the 0.17 of the first build: tapering that hard turned
# the last ring into a needle and the pole cap into a SPEARHEAD — obvious from above in the
# isolated render, and nothing like a tongue. A tongue tip is blunt and rounded, so the
# profile stays full late and the short pole cap does the rounding. Same reasoning at the
# root, which was a cut-off log before.
_S  = np.array([0.00, 0.15, 0.35, 0.60, 0.82, 1.00])
_PW = np.array([0.62, 0.99, 1.00, 0.90, 0.70, 0.38])
_PH = np.array([0.55, 1.00, 0.90, 0.66, 0.42, 0.18])

# The poles cap the loft, so the RINGS stop short of the extremes and the poles land exactly
# on f_root / f_tip. First build had the rings span the whole range and then pushed the poles
# a further 0.004 past them, which silently spent the entire T_TIP_CLEAR budget and put the
# tip pole flush against the lingual face of the incisors.
T_POLE = 0.004
rings = []
_stations = []
for k in range(TONGUE_NS):
    s = k / (TONGUE_NS - 1.0)
    f = (f_root + T_POLE) + ((f_tip - T_POLE) - (f_root + T_POLE)) * s
    c_lat, half, fl, ce_bag = bag_at(f)
    # THE CEILING AND THE THICKNESS ARE DIFFERENT QUESTIONS. First build derived the natural
    # thickness from the already-clamped ceiling, so every restriction was counted TWICE: the
    # duck clamp cut the ceiling, the smaller (ce - fl) then cut the thickness again, and the
    # blade collapsed from 2.13%H to 0.63%H between two adjacent stations — a cliff, not a
    # taper. The tongue read as a thick body with a sheet of paper stuck on the front.
    # So: thickness comes from the BAG's room, and the ceiling only ever CLIPS the result.
    ce_hard = ce_bag
    m = np.abs(_up_f - f) <= 0.010
    if int(m.sum()):
        ce_hard = min(ce_hard, float(_up_z[m].min()))     # duck under the upper teeth
    tt = (f - _f_duck0) / max(_f_duck1 - _f_duck0, 1e-9)
    tt = min(max(tt, 0.0), 1.0); tt = tt*tt*(3.0 - 2.0*tt)
    ce_hard = min(ce_hard, (z_rim_lo - T_LIP_CLEAR)*tt + ce_hard*(1.0 - tt))  # ... and the lip edge
    z_floor = fl + T_FLOOR
    room = max(ce_hard - T_CEIL - z_floor, 1e-4)
    w = T_FILL_LAT * half * float(np.interp(s, _S, _PW))
    h = min(T_FILL_UP * (ce_bag - fl) * float(np.interp(s, _S, _PH)), room)
    rise = T_TIP_RISE * (ce_bag - fl) * (max(0.0, (s - 0.62) / 0.38) ** 2)
    h_dn = T_UNDER * h
    h_up = h - h_dn
    z_ctr = z_floor + h_dn + rise
    ring = []
    for r in range(TONGUE_NR):
        th = 2.0 * math.pi * r / TONGUE_NR
        cu, sv = math.cos(th), math.sin(th)
        su = math.copysign(abs(cu) ** (2.0 / T_SECT_N), cu)
        sl = math.copysign(abs(sv) ** (2.0 / T_SECT_N), sv)
        dz = (h_up if su >= 0 else h_dn) * su
        if su > 0.0:                                  # midline dorsal groove, top only
            dz -= T_GROOVE * h * su * math.exp(-(sl / 0.42) ** 2)
        # fwd and lat are unit, orthogonal and both flat in XY, so (f, lat) is an exact
        # orthonormal basis for the horizontal plane and z carries straight through.
        ll = c_lat + w * sl
        ring.append(bm.verts.new((float(fwd[0]*f + lat[0]*ll),
                                  float(fwd[1]*f + lat[1]*ll),
                                  float(z_ctr + dz))))
    rings.append(ring)
    _stations.append((s, f, 2.0*w, h, z_floor, z_ctr + h_up, ce_hard, h >= room - 1e-9))

_c0, _h0, _fl0, _ce0 = bag_at(f_root)
_c1, _h1, _fl1, _ce1 = bag_at(f_tip)
pole_root = bm.verts.new((float(fwd[0]*f_root + lat[0]*_c0),
                          float(fwd[1]*f_root + lat[1]*_c0),
                          float(_fl0 + T_FLOOR + 0.35*T_FILL_UP*(_ce0 - _fl0))))
pole_tip  = bm.verts.new((float(fwd[0]*f_tip + lat[0]*_c1),
                          float(fwd[1]*f_tip + lat[1]*_c1),
                          float(rings[-1][0].co.z*0.5 + rings[-1][TONGUE_NR//2].co.z*0.5)))

tongue_faces_bm = []
for k in range(TONGUE_NS - 1):
    for r in range(TONGUE_NR):
        r2 = (r + 1) % TONGUE_NR
        tongue_faces_bm.append(bm.faces.new(
            (rings[k][r], rings[k][r2], rings[k+1][r2], rings[k+1][r])))
for r in range(TONGUE_NR):
    r2 = (r + 1) % TONGUE_NR
    tongue_faces_bm.append(bm.faces.new((pole_root, rings[0][r2], rings[0][r])))
    tongue_faces_bm.append(bm.faces.new((pole_tip, rings[-1][r], rings[-1][r2])))

tv = [v for ring in rings for v in ring] + [pole_root, pole_tip]
_tco = np.array([[v.co.x, v.co.y, v.co.z] for v in tv])
_tf, _tl, _tz = _tco @ fwd, _tco @ lat, _tco[:, 2]
print(f"tongue: {len(tv)} verts / {len(tongue_faces_bm)} faces, {TONGUE_NS} stations x "
      f"{TONGUE_NR} ring + 2 poles")
print("  station  s     fwd      width    thick    floor    top      ceiling  clipped")
for (s_, f_, w_, h_, zf_, zt_, ch_, cl_) in _stations:
    print(f"    {s_:4.2f}  {f_:+.4f}  {w_:.4f}  {h_:.4f}  {zf_:+.4f}  {zt_:+.4f}  {ch_:+.4f}"
          f"  {'CLIP' if cl_ else ''}")
print(f"  root f {f_root:+.4f} -> tip f {f_tip:+.4f} (lower incisor lingual face "
      f"{float(_lo_f[_mid].min()):+.4f}, clearance {T_TIP_CLEAR:.4f})")
print(f"  extent lat {np.ptp(_tl):.4f} ({100*np.ptp(_tl)/H:4.2f}%H, bag {100*(_cl.max()-_cl.min())/H:4.2f}%H)"
      f"  fwd {np.ptp(_tf):.4f} ({100*np.ptp(_tf)/H:4.2f}%H)"
      f"  z {np.ptp(_tz):.4f} ({100*np.ptp(_tz)/H:4.2f}%H, bag {100*(_cz.max()-_cz.min())/H:4.2f}%H)")
print(f"  fills bag: lat {100*np.ptp(_tl)/(_cl.max()-_cl.min()):.0f}%  "
      f"fwd {100*np.ptp(_tf)/(f_front-f_back):.0f}%  z {100*np.ptp(_tz)/(_cz.max()-_cz.min()):.0f}%")
_lip_front = float((co[rim] @ fwd).max())
_gap = _lip_front - float(_tf.max())
print(f"  gap tip -> lip rim front: {_gap:+.4f} ({100*_gap/H:+.2f}%H) "
      f"— this is the distance tongueOut has to cover to protrude")

# New bmesh verts get DEFAULT 0 for int layers -- and jaw_rig treats cav_src >= 0 as
# "mouth bag vert, skin it from its rim ancestor". Left at 0 the teeth and tongue would
# be skinned from vertex 0. Mark them as not-bag.
srclay = bm.verts.layers.int.get("cav_src")
if srclay is not None:
    for v in lo_v + up_v + tv: v[srclay] = -1
    print(f"  cav_src set to -1 on {len(lo_v)+len(up_v)+len(tv)} new verts")

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.verts.index_update(); bm.faces.index_update()
part_v = {"teeth_lower": [v.index for v in lo_v],
          "teeth_upper": [v.index for v in up_v],
          "tongue":      [v.index for v in tv]}
tooth_faces = [f.index for f in lo_f + up_f]
# Taken from the faces this script BUILT, not from link_faces on the verts: the tongue now
# shares no vertex with anything else, but deriving the list from what was authored keeps it
# true if that ever stops being the case.
tongue_faces = sorted({f.index for f in tongue_faces_bm})
nm = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
bd = sum(1 for e in bm.edges if e.is_boundary)
print(f"hygiene: verts {len(bm.verts)} faces {len(bm.faces)} | non-manifold {nm} boundary {bd}")
bm.to_mesh(me); bm.free(); me.update()

def mat(name, rgba, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = rgba          # Workbench/solid reads THIS, not the Principled input
    m.roughness = rough
    me.materials.append(m); return len(me.materials)-1
enamel = mat("clyffy_teeth", (0.92, 0.90, 0.84, 1.0), 0.30)
tongue_m = mat("clyffy_tongue", (0.62, 0.20, 0.24, 1.0), 0.55)
for i in tooth_faces:
    if i < len(me.polygons): me.polygons[i].material_index = enamel
for i in tongue_faces:
    if i < len(me.polygons):
        me.polygons[i].material_index = tongue_m
        # SMOOTH-SHADE THE TONGUE. Everything else here is flat by default and should be —
        # enamel reads better faceted — but a flat-shaded tongue is unmistakably a low-poly
        # wedge the moment the mouth opens far enough to see it, which is exactly when it
        # matters. Costs nothing; the fix is per-face, so the teeth keep their facets.
        me.polygons[i].use_smooth = True

# ── CONTAINMENT GATE — measured, not eyeballed ───────────────────────────────
# The docstring calls "nothing visible at REST" a hard acceptance criterion but only ever
# checked it by looking at a render, and it had been FAILING: tooth slivers were poking
# through both commissures in every hero since the parts were added.
#
# Cast a fan of rays outward from each interior vertex. A vertex sitting properly inside the
# closed head always hits skin in every outward direction (the mouth bag is an indentation,
# so a ray leaving it still crosses the front wall). A ray that ESCAPES means that vertex has
# a clear line to the outside — i.e. it is visible.
from mathutils.bvhtree import BVHTree
C2 = np.empty((len(me.vertices), 3)); me.vertices.foreach_get("co", C2.ravel())
part_faces = set(tooth_faces) | set(tongue_faces)
skin_polys = [tuple(p.vertices) for i, p in enumerate(me.polygons) if i not in part_faces]
bvh = BVHTree.FromPolygons([Vector(c) for c in C2], skin_polys, all_triangles=False, epsilon=0.0)
fan = []
for yaw in (-40, -20, 0, 20, 40):
    for pitch in (-30, 0, 30):
        d = (Vector(fwd)*math.cos(math.radians(yaw))
             + Vector(lat)*math.sin(math.radians(yaw)))
        d = d*math.cos(math.radians(pitch)) + Vector((0, 0, 1))*math.sin(math.radians(pitch))
        fan.append(d.normalized())
total_vis = 0
half_span = float(np.abs(co[rim] @ lat - lat0).max())
for name, idx in part_v.items():
    vis = []
    for i in idx:
        o = Vector(C2[i])
        if any(bvh.ray_cast(o + d*(H*1e-4), d, H*0.6)[0] is None for d in fan):
            vis.append(i)
    total_vis += len(vis)
    flag = "  ** VISIBLE AT REST **" if vis else ""
    print(f"  containment {name:<13} {len(vis):>3} of {len(idx)} verts have a clear ray out{flag}")
    if vis:
        # WHERE they leak decides the fix: at the commissures -> trim/taper harder;
        # spread along the arch -> the whole band is too far forward, raise INSET.
        r = np.abs(C2[vis] @ lat - lat0) / max(half_span, 1e-9)
        print(f"       leak position along the arch: {r.min():.2f}–{r.max():.2f} "
              f"(0 = centre of the mouth, 1 = commissure), median {np.median(r):.2f}")
# ADVISORY AT THIS STAGE, NOT A GATE: the lips are still unsealed here — tools/lip_seal.py
# runs next and closes the rest slit (that is the whole reason it exists). Leaks reported at
# the CENTRE of the arch are expected and the seal removes them. Leaks at the COMMISSURES
# (r near 1) are the real defect, because the seal does not reach there; that is what the
# per-point local inward normal fixed. The authoritative gate is in lip_seal.py, post-seal.
if total_vis:
    print(f"   ({total_vis} pre-seal leaks — see the arch positions above. Central leaks are "
          f"the lip slit and lip_seal.py closes them; leaks near 1.0 are a real defect.)")
else:
    print("containment OK even before the seal: nothing has a clear line out")

for name, idx in part_v.items():
    g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    g.add(idx, 1.0, 'REPLACE')
    print(f"  group {name}: {len(idx)} verts")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "clyffy_v2_parts.blend"))
print("saved clyffy_v2_parts.blend")
