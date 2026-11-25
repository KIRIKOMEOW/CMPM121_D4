# /// script
# requires-python = "==3.13.*"
# dependencies = ["bpy==5.2.*"]
# ///
"""Blender as a library: build the kit, art/dragon_kit.glb and art/dragon_kit.blend.

deno task art      uses Blender 5.2 (the header above)
deno task art:lts  uses Blender 4.5 LTS, for Intel Macs, which Blender 5 dropped
deno task blender  opens art/dragon_kit.blend in the Blender app, to look around

Every piece fills one 1x1 grid cell and is made by a builder function listed in
PIECES (the dragon) or TILES (the ground). The starter's builders all use voxels(),
but a builder can make any geometry: swap one out and the game picks it up by name.

Conventions the game relies on (Blender coordinates, Z up):
  - A cell spans x and y from -0.5 to 0.5. +Y is the direction of travel.
  - Openings must match Kit.OPENINGS in core/kit.gd: the head and tail join the
    body at the back and front, the turn joins the back and the right side.
  - Floors lie with their top at z = 0; everything else stands on z = 0.

Editing by hand in Blender instead:
  The game loads only art/dragon_kit.glb, never the .blend. After editing a .blend in
  Blender, export it yourself with File > Export > glTF 2.0 (.glb/.gltf):
    Format: glTF Binary (.glb)        File: art/dragon_kit.glb
    Include: no Limit to boxes ticked; Cameras and Punctual Lights unticked
    Transform: +Y Up ticked           Mesh: Apply Modifiers ticked
  and keep the object names (head, straight, turn, tail, floor, wall, ...).
  WARNING: deno task art rewrites BOTH art/dragon_kit.blend and art/dragon_kit.glb,
  erasing hand edits. Before editing, File > Save As a copy such as art/my_kit.blend
  (deno task blender art/my_kit.blend reopens it). The tradeoff: from then on the
  kit lives in that file, not in this script, so a change here no longer reaches it
  unless you redo it by hand, and a .blend is hard to review in a diff.
"""

from pathlib import Path

import bpy  # first: importing bpy is what makes bmesh and mathutils available
import bmesh
from mathutils import Matrix

# Paths from this file, not the current directory, so the script works from anywhere.
# Build them with pathlib rather than gluing strings together, as Blender's gotchas advise:
# https://docs.blender.org/api/current/info_gotchas_file_paths_and_encoding.html
ART = Path(__file__).resolve().parent.parent / "art"
GLB = ART / "dragon_kit.glb"
BLEND = ART / "dragon_kit.blend"

MATERIALS = []  # every material, in order; a face's material_index points into this list
PALETTE = {}  # finish name -> index in MATERIALS; filled in by make_materials()


def reset_scene():
    """Start from an empty file, so nothing from Blender's default scene (cube, camera,
    light) or an earlier run leaks into the kit."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


# --- Materials ------------------------------------------------------------------


def pbr_material(name, color, metallic=0.0, roughness=0.5, emission=None, strength=1.0):
    """A Principled BSDF using only inputs glTF keeps. Returns its index in MATERIALS.
    Emission above about 1 blooms in the game, because the stage has glow switched on."""
    material = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0):  # 4.x starts without nodes; 5.x always has them and deprecates use_nodes
        material.use_nodes = True
    # Find the node by type, not by its name, which a non-English Blender may translate:
    # https://terminalskills.io/skills/blender-scripting (section 9, Assign materials)
    bsdf = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = srgb(color)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:  # glTF keeps a color up to 1 plus a strength (KHR_materials_emissive_strength)
        bsdf.inputs["Emission Color"].default_value = srgb(emission)
        bsdf.inputs["Emission Strength"].default_value = strength
    material.diffuse_color = srgb(color)  # the viewport's solid color, for the GUI
    MATERIALS.append(material)
    return len(MATERIALS) - 1


def srgb(hex_code):
    """A hex color as Blender wants it: linear RGBA."""
    channels = [int(hex_code.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels) + (1.0,)


def make_materials():
    PALETTE.update({
        "chassis": pbr_material("Graphite", "#263341", metallic=0.65, roughness=0.44),
        "armor": pbr_material("Copper armor", "#e68a42", metallic=0.55, roughness=0.30),
        "steel": pbr_material("Steel", "#819cab", metallic=0.65, roughness=0.38),
        "sensor": pbr_material("Optic", "#8effed", emission="#44ffe4", strength=1.5),
        "food": pbr_material("Food", "#53b7ff", roughness=0.15, emission="#53b7ff", strength=2.5),
        "deck": pbr_material("Deck", "#354251", metallic=0.25, roughness=0.65),
    })


def finish(verts, surface):
    for face in {face for vertex in verts for face in vertex.link_faces}:
        face.material_index = PALETTE[surface]


def box(bm, center, size, surface):
    transform = Matrix.Translation(center) @ Matrix.Diagonal((*size, 1))
    verts = bmesh.ops.create_cube(bm, size=1, matrix=transform)["verts"]
    finish(verts, surface)


def plate(bm, outline, bottom, top, surface):
    """Extrude a counterclockwise XY outline."""
    lower = [bm.verts.new((x, y, bottom)) for x, y in outline]
    upper = [bm.verts.new((x, y, top)) for x, y in outline]
    faces = [bm.faces.new(lower[::-1]), bm.faces.new(upper)]
    for i in range(len(lower)):
        faces.append(bm.faces.new((lower[i-1], lower[i], upper[i], upper[i-1])))
    for face in faces:
        face.material_index = PALETTE[surface]


def socket(bm, dx, dy):
    """Extend a graphite coupling to the center of a cell edge."""
    box(bm, (0.25 * dx, 0.25 * dy, 0.20),
        (0.50 if dx else 0.24, 0.50 if dy else 0.24, 0.18), "chassis")
    box(bm, (0.38 * dx, 0.38 * dy, 0.20),
        (0.09 if dx else 0.32, 0.09 if dy else 0.32, 0.22), "steel")


def build_head(bm):
    socket(bm, 0, -1)
    outline = [(-0.27,-0.32), (0.27,-0.32), (0.37,-0.12), (0.28,0.28),
               (0.14,0.46), (-0.14,0.46), (-0.28,0.28), (-0.37,-0.12)]
    plate(bm, outline, 0.10, 0.27, "chassis")
    plate(bm, [(0.96*x, 0.96*y) for x,y in outline], 0.27, 0.37, "armor")
    box(bm, (0, 0.16, 0.39), (0.46, 0.14, 0.04), "chassis")
    for x in (-0.14, 0.14):
        box(bm, (x, 0.16, 0.42), (0.09, 0.075, 0.02), "sensor")


def servo(bm):
    hub = bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.29,
                                radius2=0.25, depth=0.24, matrix=Matrix.Translation((0, 0, 0.22)))
    finish(hub["verts"], "armor")
    box(bm, (0, 0, 0.36), (0.23, 0.18, 0.04), "steel")


def build_straight(bm):
    socket(bm, 0, -1)
    socket(bm, 0, 1)
    servo(bm)


def build_turn(bm):
    socket(bm, 0, -1)
    socket(bm, 1, 0)
    servo(bm)


def build_tail(bm):
    socket(bm, 0, 1)
    plate(bm, [(-0.045,-0.43), (0.045,-0.43), (0.21,-0.04), (0.19,0.26),
               (-0.19,0.26), (-0.21,-0.04)], 0.12, 0.30, "armor")
    box(bm, (0, 0, 0.32), (0.09, 0.26, 0.04), "chassis")


def build_food(bm):
    food = bmesh.ops.create_uvsphere(
        bm,
        u_segments=16,
        v_segments=8,
        radius=0.22,
        matrix=Matrix.Translation((0, 0, 0.22)),
    )
    finish(food["verts"], "food")


def build_floor(bm):
    box(bm, (0, 0, -0.10), (1, 1, 0.12), "chassis")
    plate(bm, [(-0.41,-0.48), (0.41,-0.48), (0.48,-0.41), (0.48,0.41),
               (0.41,0.48), (-0.41,0.48), (-0.48,0.41), (-0.48,-0.41)],
          -0.04, 0, "deck")


def build_wall(bm):
    build_floor(bm)
    box(bm, (0, 0, 0.18), (0.95, 0.95, 0.36), "chassis")
    box(bm, (0, 0, 0.39), (0.85, 0.85, 0.06), "steel")
    for x in (-0.25, 0.25):
        box(bm, (x, 0, 0.43), (0.12, 0.77, 0.02), "armor")


PIECES = {  # the dragon kit; the game finds each mesh by these names
    "head": build_head,
    "straight": build_straight,
    "turn": build_turn,
    "tail": build_tail,
}
TILES = {  # one entry per kind in core/board.gd's TILES; a new kind is one builder and one line
    "floor": build_floor,
    "wall": build_wall,
}
PROPS = {
    "food": build_food,
}


# --- Objects and layout ---------------------------------------------------------


def make_object(scene, name, build, location=(0, 0, 0)):
    """Run a builder on a fresh bmesh and turn the result into a mesh object called name.
    The game uses only the mesh; location just spreads the kit out for model viewers."""
    bm = bmesh.new()
    build(bm)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    # Keep only the materials this object uses, renumbering faces to match.
    used = sorted({p.material_index for p in mesh.polygons})
    mesh.polygons.foreach_set("material_index", [used.index(p.material_index) for p in mesh.polygons])
    for index in used:
        mesh.materials.append(MATERIALS[index])
    # bpy.data creates the object directly; bpy.ops.mesh.primitive_*_add would depend on
    # the active object and selection, which an operator reads from the context:
    # https://docs.blender.org/api/current/info_gotchas_operators.html
    obj = bpy.data.objects.new(name, mesh)
    # Blender quietly changes a name that is too long or already taken, and the game
    # finds pieces by name, so fail loudly instead:
    # https://docs.blender.org/api/current/info_gotchas_internal_data_and_python_objects.html
    if obj.name != name:
        raise ValueError(f"Blender renamed {name!r} to {obj.name!r}; pick a shorter, unique name")
    obj.location = location
    scene.collection.objects.link(obj)


def lay_out_kit(scene):
    """One row per registry, so a GLB viewer shows a tidy catalog instead of every piece
    stacked on the origin. Each mesh is still modeled around its own cell's center."""
    spacing = 1.5
    for row, registry in enumerate([PIECES, TILES, PROPS]):
        for column, (name, build) in enumerate(registry.items()):
            make_object(scene, name, build, location=(column * spacing, -row * spacing, 0))


# --- Export ---------------------------------------------------------------------


def export():
    """Write the .glb the game loads, then the .blend for the Blender app.
    glTF export has no data API, only an operator, so every option that could depend
    on what is selected or active is spelled out. These match the steps in the docstring.
    Enum values such as 'GLB' get single quotes, Blender's own style:
    https://docs.blender.org/api/current/info_best_practice.html"""
    bpy.ops.export_scene.gltf(
        filepath=str(GLB),
        export_format='GLB',
        use_selection=False,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    # No art/dragon_kit.blend1 backup: the script is the backup, and the next run rewrites this.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def main():
    reset_scene()
    make_materials()
    lay_out_kit(bpy.context.scene)
    export()
    print(f"Built {GLB.name} and {BLEND.name} with Blender {bpy.app.version_string}")


# Run only as a script, not when another file imports this one for its builders:
# https://docs.python.org/3/library/__main__.html
if __name__ == "__main__":
    main()
