import bpy, numpy as np

def teeth_w(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    ob = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
    gi = {g.name: g.index for g in ob.vertex_groups}
    N = len(ob.data.vertices)

    def W(n):
        w = np.zeros(N)
        if n not in gi:
            return w
        idx = gi[n]
        for v in ob.data.vertices:
            for g in v.groups:
                if g.group == idx:
                    w[v.index] = g.weight
        return w

    def idxs(n):
        if n not in gi:
            return np.array([], int)
        idx = gi[n]
        return np.array([v.index for v in ob.data.vertices
                         for g in v.groups if g.group == idx and g.weight > 0.5])

    tl, tu = idxs("teeth_lower"), idxs("teeth_upper")
    print("===", path)
    print(" teeth_lower n", len(tl), "teeth_upper n", len(tu))
    for label, ids in [("lower", tl), ("upper", tu)]:
        if len(ids) == 0:
            continue
        print(f" {label}:")
        for bn in sorted(gi.keys()):
            w = W(bn)
            if w[ids].max() < 0.01:
                continue
            print(f"   {bn:14s} mean={w[ids].mean():.3f} min={w[ids].min():.3f} max={w[ids].max():.3f}")

teeth_w("mesh/canon/clyffy_v2_rig.blend")
teeth_w("mesh/canon/body/clyffy_v2_body.blend")
