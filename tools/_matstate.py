#!/usr/bin/env python3
"""MEASURE the material state actually stored in a blend. Read-only.

    blender -b <file.blend> --python tools/_matstate.py

A7 step 0. The POA&M records "SSS = 0.0 on all five materials", but that was measured
before I knew present.py rewrites materials at RENDER time (polish_materials, present.py:61).
So there are two different truths in play and I need to know which one the delivered
artifacts carry:

  - what is SAVED in the blend  -> what vrm_export sees, what the web renderer gets
  - what present.py sets in RAM -> what the hero PNGs show, and nothing else

If those disagree, the hero renders are flattering the build.
"""
import bpy, numpy as np

me = None
for o in bpy.data.objects:
    if o.type == "MESH" and len(o.data.polygons) > 1000:
        if me is None or len(o.data.polygons) > len(me.polygons):
            me = o.data
            ob = o
print(f"object: {ob.name}  verts {len(me.vertices)}  faces {len(me.polygons)}")

mi = np.empty(len(me.polygons), dtype=np.int32)
me.polygons.foreach_get("material_index", mi)

print(f"\nmaterial slots: {len(me.materials)}")
for i, m in enumerate(me.materials):
    n = int((mi == i).sum())
    if m is None:
        print(f"  [{i}] <EMPTY>  faces {n}")
        continue
    bsdf = None
    if m.use_nodes:
        bsdf = next((x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED"), None)

    def g(key, *alts):
        if bsdf is None:
            return None
        s = bsdf.inputs.get(key)
        for a in alts:
            if s is None:
                s = bsdf.inputs.get(a)
        if s is None:
            return None
        if s.is_linked:
            return f"<linked:{s.links[0].from_node.type}>"
        v = s.default_value
        try:
            return tuple(round(float(x), 4) for x in v)
        except TypeError:
            return round(float(v), 4)

    print(f"  [{i}] {m.name}   faces {n} ({100.0*n/len(me.polygons):.1f}%)")
    print(f"        base={g('Base Color')} rough={g('Roughness')}")
    print(f"        SSS weight={g('Subsurface Weight', 'Subsurface')} "
          f"radius={g('Subsurface Radius')} scale={g('Subsurface Scale')}")
    print(f"        sheen={g('Sheen Weight', 'Sheen')} coat={g('Coat Weight')} "
          f"spec={g('Specular IOR Level', 'Specular')}")

print(f"\nfaces with no assigned slot in range: "
      f"{int((mi >= max(len(me.materials),1)).sum())}")
print(f"UV layers: {[l.name for l in me.uv_layers]}")
print(f"images: {[i.name for i in bpy.data.images if i.name != 'Render Result']}")
print(f"vertex groups on {ob.name}: {len(ob.vertex_groups)}")
print(f"attributes: {[(a.name, a.data_type, a.domain) for a in me.attributes]}")
print(f"shape keys: {len(me.shape_keys.key_blocks) if me.shape_keys else 0}")
