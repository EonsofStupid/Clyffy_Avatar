"""
Headless mesh inspection + turnaround render.

    blender --background --python tools/blender_inspect.py -- <mesh_file> <out_dir>

Imports an FBX/GLB/OBJ, prints a structural report to stdout, and renders four
orthographic-ish views so the mesh can actually be LOOKED at rather than guessed about.

Written for Blender 4.0.2 (Ubuntu noble arm64). No add-ons required.
"""
import bpy, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 1:
    print("usage: ... -- <mesh_file> [out_dir]"); sys.exit(1)
MESH = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(os.path.dirname(MESH), "preview")
os.makedirs(OUT, exist_ok=True)

# clean default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

ext = os.path.splitext(MESH)[1].lower()
if ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=MESH)
elif ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=MESH)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=MESH)
else:
    print(f"unsupported extension {ext}"); sys.exit(1)

report = {"file": MESH, "objects": [], "materials": [], "images": [],
          "armatures": [], "shape_keys": [], "totals": {}}

tris = verts = 0
minv = Vector((1e9,)*3); maxv = Vector((-1e9,)*3)

for ob in bpy.data.objects:
    entry = {"name": ob.name, "type": ob.type}
    if ob.type == "MESH":
        me = ob.data
        me.calc_loop_triangles()
        ntri, nvert, npoly = len(me.loop_triangles), len(me.vertices), len(me.polygons)
        quads = sum(1 for p in me.polygons if len(p.vertices) == 4)
        ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)
        tris += ntri; verts += nvert
        entry.update(tris=ntri, verts=nvert, polys=npoly, quads=quads, ngons=ngons,
                     quad_pct=round(100*quads/npoly, 1) if npoly else 0,
                     uv_layers=[l.name for l in me.uv_layers],
                     materials=[m.name for m in me.data.materials if m] if hasattr(me,'data') else
                               [ms.material.name for ms in ob.material_slots if ms.material])
        if me.shape_keys:
            names = [k.name for k in me.shape_keys.key_blocks]
            entry["shape_keys"] = names
            report["shape_keys"].extend(names)
        for c in ob.matrix_world.to_translation(), :
            pass
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            minv = Vector((min(minv[i], w[i]) for i in range(3)))
            maxv = Vector((max(maxv[i], w[i]) for i in range(3)))
    elif ob.type == "ARMATURE":
        bones = [b.name for b in ob.data.bones]
        entry["bones"] = bones
        report["armatures"].append({"name": ob.name, "bone_count": len(bones), "bones": bones})
    report["objects"].append(entry)

for m in bpy.data.materials:
    nodes = [n.type for n in m.node_tree.nodes] if m.use_nodes and m.node_tree else []
    report["materials"].append({"name": m.name, "nodes": sorted(set(nodes))})
for im in bpy.data.images:
    if im.name != "Render Result":
        report["images"].append({"name": im.name, "size": list(im.size), "channels": im.channels})

dims = (maxv - minv) if tris else Vector((0,0,0))
report["totals"] = {"triangles": tris, "vertices": verts,
                    "bbox_min": [round(v,4) for v in minv] if tris else None,
                    "bbox_max": [round(v,4) for v in maxv] if tris else None,
                    "dimensions": [round(v,4) for v in dims],
                    "armature_count": len(report["armatures"]),
                    "shape_key_count": len(report["shape_keys"])}

print("\n===== MESH REPORT =====")
print(json.dumps(report, indent=2))

# ---- render a turnaround so a human/agent can SEE it ----
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_WORKBENCH"
scene.render.resolution_x = 800
scene.render.resolution_y = 1000
scene.render.film_transparent = False

world = bpy.data.worlds.new("W"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.87, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.2

center = (minv + maxv) / 2
radius = max(dims) if max(dims) else 1.0

cam_data = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam); scene.camera = cam
cam_data.type = "ORTHO"; cam_data.ortho_scale = radius * 1.25

light_data = bpy.data.lights.new("Key", type="SUN"); light_data.energy = 3.0
light = bpy.data.objects.new("Key", light_data); scene.collection.objects.link(light)
light.rotation_euler = (math.radians(55), 0, math.radians(35))

for label, ang in [("front", 0), ("side", 90), ("back", 180), ("three_quarter", 45)]:
    a = math.radians(ang)
    cam.location = (center.x + math.sin(a)*radius*3,
                    center.y - math.cos(a)*radius*3,
                    center.z)
    cam.rotation_euler = (math.radians(90), 0, a)
    scene.render.filepath = os.path.join(OUT, f"view_{label}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {scene.render.filepath}")

with open(os.path.join(OUT, "report.json"), "w") as f:
    json.dump(report, f, indent=2)
print(f"\nreport written to {os.path.join(OUT,'report.json')}")
