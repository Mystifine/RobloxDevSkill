"""Blender side of skins (references/rigs.md, Skins). Run inside Blender 4.2+ (bpy):

    import roblox_rig as rr
    dump = rr.load(r"rig.json")                # the JSON from RigSkin.dump(rig) in Studio
    rig = rr.build(dump, colors={'Body': '#E9BE2C'})  # the body as it looks in game (solid, colored) + an armature
    # ... model the skin around the replica body, which stays visible (references/rigs.md: build around the body); name
    # each piece after its body part ("LeftUpperArm", "Left Arm", "Head__Halo" for more than one) ...
    rr.export_pieces([pieces...], r"skin.fbx")   # welded skin: RigSkin.apply(rig, skin) in Studio
    rr.rigid_weights(mesh, rig, blend=0.08)      # skinned skin: weight each vertex to the body part it sits in
    rr.export_skinned(mesh, rig["armature"], r"skin_skinned.fbx")   # RigSkin.bind(rig, skinned) in Studio

Space: Roblox root-relative (x, y, z) -> Blender (-x, z, y + rootHeight): the ground at 0, the character facing -Y,
its left at +X. Roblox's FBX importer maps Blender (x, y, z) back to (-x, z, y) for meshes whose origin is the scene
origin, which both exports use (checked 2026-10-29: 1 Blender unit = 1 stud, facing -Z, maps kept; an object's own
transform is dropped)."""
import json
import math
import bpy
from mathutils import Matrix, Vector

M = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))  # Roblox axes -> Blender axes (a proper rotation)


def load(path_or_text):
    text = path_or_text if path_or_text.lstrip().startswith('{') else open(path_or_text, encoding='utf-8').read()
    return json.loads(text)


def to_blender(cframe, root_height):
    """A Roblox root-relative CFrame (12 components) -> a Blender world matrix."""
    x, y, z, *r = cframe
    rot = M @ Matrix((r[0:3], r[3:6], r[6:9])) @ M.inverted()
    mat = rot.to_4x4()
    mat.translation = Vector((-x, z, y + root_height))
    return mat


def _collection(name):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    return col


# BodyColors groups and the parts each colors (as in RigSkin.color).
GROUPS = {'Head': ['Head'], 'Torso': ['Torso', 'UpperTorso', 'LowerTorso'],
          'LeftArm': ['Left Arm', 'LeftUpperArm', 'LeftLowerArm', 'LeftHand'], 'RightArm': ['Right Arm', 'RightUpperArm', 'RightLowerArm', 'RightHand'],
          'LeftLeg': ['Left Leg', 'LeftUpperLeg', 'LeftLowerLeg', 'LeftFoot'], 'RightLeg': ['Right Leg', 'RightUpperLeg', 'RightLowerLeg', 'RightFoot']}


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)) if isinstance(c, str) else tuple(c)


def _body_material(part, color):
    m = bpy.data.materials.new('RIG_M_' + part); m.use_nodes = True
    bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (*[x ** 2.2 for x in color], 1); bs.inputs['Roughness'].default_value = .6
    m.diffuse_color = (*[x ** 2.2 for x in color], 1)  # the clay check's material color
    return m


def _head_mesh(me, sx, sy, sz, sides=32):
    """A classic head: an upright cylinder with rounded top and bottom edges."""
    rx, rz, h = sx / 2, sz / 2, sy / 2; e = min(rx, rz, h) * .35; verts, faces = [], []
    rings = [(-h, .55), (-h + e * .3, .85), (-h + e, 1.0), (h - e, 1.0), (h - e * .3, .85), (h, .55)]
    for z, k in rings:
        for i in range(sides):
            a = i * math.tau / sides; verts.append((math.cos(a) * rx * k, math.sin(a) * rz * k, z))
    for j in range(len(rings) - 1):
        for i in range(sides):
            a, b = j * sides + i, j * sides + (i + 1) % sides; faces.append((a, b, b + sides, a + sides))
    for j, d in ((0, -1), (len(rings) - 1, 1)):
        c = len(verts); verts.append((0, 0, rings[j][0])); s = j * sides
        faces += [((s + i, s + (i + 1) % sides, c) if d > 0 else (s + (i + 1) % sides, s + i, c)) for i in range(sides)]
    me.from_pydata(verts, [], faces)


def build(dump, name=None, colors=None):
    """Replica of the dumped rig as it looks in game: one solid part per body part (RIG_<part>: a box, or a rounded
    classic head), colored by `colors` ({BodyColors group, part name or 'Body': '#rrggbb' or (r, g, b)}; default the
    dumped colors), visible in renders; the root is a wire box. Plus an armature (RIG_Armature) with one bone per body
    part, its head at the joint that attaches the part to its parent. Returns {"armature", "boxes", "pivots"}."""
    h = dump['rootHeight']; col = _collection(name or 'RIG_' + dump['rigType'])
    colors = colors or {}; group_of = {p: g for g, parts in GROUPS.items() for p in parts}
    boxes = {}
    for part, info in dump['parts'].items():
        sx, sy, sz = info.get('visual', info['size'])
        me = bpy.data.meshes.new('RIG_' + part)
        if info.get('shape') == 'head':
            _head_mesh(me, sx, sy, sz)
        else:
            verts = [(a * sx / 2, c * sz / 2, b * sy / 2) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
            faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
            me.from_pydata(verts, [], faces)
        for poly in me.polygons:
            poly.use_smooth = info.get('shape') == 'head'
        ob = bpy.data.objects.new('RIG_' + part, me); col.objects.link(ob)
        ob.matrix_world = to_blender(info['cframe'], h); ob['roblox_part'] = part
        if part == 'HumanoidRootPart':
            ob.display_type = 'WIRE'; ob.hide_render = True
        else:
            c = colors.get(part) or colors.get(group_of.get(part)) or colors.get('Body') or info.get('color') or (.64, .64, .64)
            ob.data.materials.append(_body_material(part, _rgb(c)))
        boxes[part] = ob
    # A body part's bone starts at the joint whose Part1 it is (the root's at its centre).
    parent_of, pivots = {}, {}
    for joint in dump['joints'].values():
        parent_of[joint['part1']] = joint['part0']
        pivots[joint['part1']] = to_blender(joint['frame'], h).translation
    arm_data = bpy.data.armatures.new('RIG_Armature'); arm = bpy.data.objects.new('RIG_Armature', arm_data)
    col.objects.link(arm); arm['rig_type'] = dump['rigType']; arm['root_height'] = h
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bones = {}
    for part, box in boxes.items():
        head = pivots.get(part, box.matrix_world.translation.copy())
        centre = box.matrix_world.translation
        tail = head + (centre - head) * 2 if (centre - head).length > 1e-3 else head + Vector((0, 0, .5))
        b = arm_data.edit_bones.new(part); b.head = head; b.tail = tail
        bones[part] = b
    for part, b in bones.items():
        if parent_of.get(part) in bones:
            b.parent = bones[parent_of[part]]
    bpy.ops.object.mode_set(mode='OBJECT')
    return {'armature': arm, 'boxes': boxes, 'pivots': pivots}


def _inside(box, point, margin):
    local = box.matrix_world.inverted() @ point
    half = Vector([max(abs(v.co[i]) for v in box.data.vertices) for i in range(3)])
    return max(abs(local[i]) - half[i] for i in range(3)) - margin


def rigid_weights(mesh, rig, blend=0.0, exclude=('HumanoidRootPart',)):
    """Vertex groups named after body parts: each vertex goes to the body part it sits in (or is nearest to). With
    blend > 0 (studs), vertices within `blend` of a neighbouring part share their weight with it, so joints bend
    smoothly instead of hinging. Adds an Armature modifier and parents the mesh to the armature."""
    boxes = {p: b for p, b in rig['boxes'].items() if p not in exclude}
    for part in boxes:
        if part not in mesh.vertex_groups:
            mesh.vertex_groups.new(name=part)
    groups = {p: mesh.vertex_groups[p] for p in boxes}
    bpy.context.view_layer.update()
    world = mesh.matrix_world
    for v in mesh.data.vertices:
        p = world @ v.co
        dist = sorted((_inside(b, p, 0), part) for part, b in boxes.items())
        weights = {dist[0][1]: 1.0}
        if blend > 0:
            for d, part in dist[1:3]:
                if d - dist[0][0] < blend:
                    weights[part] = 1 - (d - dist[0][0]) / blend
        total = sum(weights.values())
        for part, w in weights.items():
            groups[part].add([v.index], w / total, 'REPLACE')
    mod = mesh.modifiers.get('Armature') or mesh.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig['armature']
    mesh.parent = rig['armature']; mesh.matrix_parent_inverse = rig['armature'].matrix_world.inverted()


def _fbx(path, objects, types, **extra):
    # The view layer's list can hold empty entries after objects are removed in the same session.
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    # Roblox: FBX unit scale, textures embedded, no leaf bones, no animation (blender-export-pipelines' roblox preset).
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types=set(types), apply_scale_options='FBX_SCALE_UNITS',
                             path_mode='COPY', embed_textures=True, add_leaf_bones=False, bake_anim=False, use_tspace=False, **extra)


def export_pieces(pieces, path):
    """Welded skin: each piece keeps its name (its body part) and has its transform applied, its origin at the scene
    origin. Roblox's importer keeps a mesh's vertices relative to its object's origin but drops the object's own
    transform (checked 2026-10-29: pieces with their origins at their centres all imported at the file origin), so
    only the scene origin puts every piece where it was modeled. The MeshPart sits at its centre; RigSkin.apply moves
    its pivot there too."""
    bpy.context.view_layer.update()  # matrix_world lags a script's location changes until the next update
    for ob in pieces:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.transform(ob.matrix_world); ob.matrix_world = Matrix.Identity(4)
    _fbx(path, pieces, {'MESH'})


def export_skinned(mesh, armature, path):
    """Skinned skin: the mesh and its armature (bones named after body parts) in one FBX; Roblox imports it as a skinned
    MeshPart with Bone instances, which RigSkin.bind moves onto the rig."""
    _fbx(path, [armature, mesh], {'ARMATURE', 'MESH'}, use_armature_deform_only=True)
