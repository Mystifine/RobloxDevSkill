"""Blender's side of the R15 pipeline: a scene with the real R15 (its meshes and joints from <project>/animation/r15_rig.json, `pipeline.py dump`)
on an armature whose bones are its joints. Every clip the engine bakes (motion.py) is stored there as an Action of that armature, keyed the way
Roblox plays it, so what you scrub here is what ships. Run from Blender:

    import sys; sys.path[:0] = [r"<skill>/scripts/r15_motion", r"<the folder of your clip files>"]
    import r15_rig; r15_rig.use_project(r"<project>"); r15_rig.setup()
    r15_rig.make("example_clips", "Wave")   # bakes, stores the Action, writes <project>/animation/baked/Wave.json
"""
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import motion  # noqa: E402

SCENE = "R15Anim"
ARMATURE = "R15"
M = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))  # Roblox axes -> Blender axes (a proper rotation), as the skill's roblox_rig.py
MQ = M.to_quaternion()
COLORS = {
    "Head": (0.96, 0.78, 0.60, 1), "UpperTorso": (0.75, 0.16, 0.18, 1), "LowerTorso": (0.45, 0.10, 0.12, 1),
    "LeftUpperArm": (0.20, 0.45, 0.85, 1), "LeftLowerArm": (0.30, 0.55, 0.95, 1), "LeftHand": (0.96, 0.78, 0.60, 1),
    "RightUpperArm": (0.90, 0.55, 0.15, 1), "RightLowerArm": (0.98, 0.68, 0.25, 1), "RightHand": (0.96, 0.78, 0.60, 1),
    "LeftUpperLeg": (0.15, 0.30, 0.65, 1), "LeftLowerLeg": (0.20, 0.38, 0.75, 1), "LeftFoot": (0.10, 0.12, 0.22, 1),
    "RightUpperLeg": (0.75, 0.40, 0.10, 1), "RightLowerLeg": (0.85, 0.48, 0.12, 1), "RightFoot": (0.22, 0.12, 0.08, 1),
}
LINEAR = bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value


def use_project(path):
    """Where animation/r15_rig.json is read from and baked clips go."""
    os.environ["R15_MOTION_PROJECT"] = os.path.abspath(path)
    importlib.reload(motion)


def rig():
    return motion.Rig()


def _to_b(p, floor):
    v = M @ Vector(p)
    v.z -= floor
    return v


def _head_mesh(size):
    """The head's mesh cannot be read (Studio refuses that asset): a rounded block of its exact size, with eyes to show where it looks."""
    verts, faces = [], []
    rings, sides = 10, 24
    sx, sy, sz = size.x / 2, size.y / 2, size.z / 2
    for i in range(rings + 1):
        v = -1 + 2 * i / rings
        lat = (1 - abs(v) ** 5) ** (1 / 3.0)
        for j in range(sides):
            a = 2 * math.pi * j / sides
            c, s = math.cos(a), math.sin(a)
            k = (abs(c) ** 4 + abs(s) ** 4) ** (-1 / 4.0)
            verts.append((sx * lat * c * k, sy * v, sz * lat * s * k))
    for i in range(rings):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(sides - 1, -1, -1)))
    faces.append(tuple(rings * sides + j for j in range(sides)))
    for ex in (-0.24, 0.24):
        n = len(verts)
        for dx, dy in ((-0.07, -0.11), (0.07, -0.11), (0.07, 0.11), (-0.07, 0.11)):
            verts.append((ex + dx, 0.12 + dy, -sz - 0.012))
        faces.append((n, n + 1, n + 2, n + 3))
    return verts, faces


def setup(rebuild=False):
    """Makes the R15Anim scene (the other scenes in this file are left alone)."""
    scene = bpy.data.scenes.get(SCENE)
    if scene is None:
        scene = bpy.data.scenes.new(SCENE)
    elif rebuild:
        for ob in list(scene.collection.all_objects):
            bpy.data.objects.remove(ob)
    bpy.context.window.scene = scene
    scene.render.fps, scene.render.fps_base = motion.FPS, 1.0
    if ARMATURE in scene.objects:
        return scene.objects[ARMATURE]

    r = rig()
    data = r.raw
    arm = bpy.data.armatures.new(ARMATURE)
    ob = bpy.data.objects.new(ARMATURE, arm)
    scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    # bones: head at the joint, in the joint's rest position; a Roblox Transform reaches a bone's axes by conjugation (_conj)
    fk = r.fk({j: (motion.ID, None) for j in motion.JOINTS})
    edit = {}
    root = arm.edit_bones.new("HumanoidRootPart")
    root.head = _to_b((0, 0, 0), r.floor)
    root.tail = _to_b((0, 0.5, 0), r.floor)
    edit["HumanoidRootPart"] = root
    children = {}
    for j in motion.JOINTS:
        children.setdefault(motion.PARENT_OF[j], []).append(j)
    for j in motion.JOINTS:
        b = arm.edit_bones.new(j)
        q, p = fk[j]
        joint = p + r.c1[j]
        kids = [k for k in children.get(j, []) if k not in ("LeftUpperArm", "RightUpperArm")]
        if kids:
            end = fk[kids[0]][1] + r.c1[kids[0]]
        else:
            end = joint + Vector((0, -0.3 if j != "Head" else 0.8, 0))
        if (end - joint).length < 0.05:
            end = joint + Vector((0, -0.3, 0))
        b.head = _to_b(joint, r.floor)
        b.tail = _to_b(end, r.floor)
        b.roll = 0
        edit[j] = b
    for j in motion.JOINTS:
        edit[j].parent = edit[motion.PARENT_OF[j]]
        edit[j].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"

    # the body: one rigidly weighted mesh per part, so nothing here is keyed but the bones
    body = bpy.data.collections.new("R15Body")
    scene.collection.children.link(body)
    for name in motion.JOINTS:
        info = data["Meshes"].get(name, {})
        size = Vector(data["Parts"][name]["Size"])
        q, p = fk[name]
        if info.get("Verts"):
            ms = Vector(info["MeshSize"])
            scale = Vector((size.x / ms.x, size.y / ms.y, size.z / ms.z))
            vs = info["Verts"]
            verts = [_to_b(p + q @ Vector((vs[i] * scale.x, vs[i + 1] * scale.y, vs[i + 2] * scale.z)), r.floor) for i in range(0, len(vs), 3)]
            ts = info["Tris"]
            faces = [tuple(ts[i : i + 3]) for i in range(0, len(ts), 3)]
        else:
            vs, faces = _head_mesh(size)
            verts = [_to_b(p + q @ Vector(v), r.floor) for v in vs]
        me = bpy.data.meshes.new("R15_" + name)
        me.from_pydata([tuple(v) for v in verts], [], faces)
        me.update()
        mat = bpy.data.materials.new("R15_" + name)
        mat.diffuse_color = COLORS[name]
        me.materials.append(mat)
        m = bpy.data.objects.new("Body_" + name, me)
        body.objects.link(m)
        group = m.vertex_groups.new(name=name)
        group.add(list(range(len(verts))), 1.0, "REPLACE")
        mod = m.modifiers.new("Rig", "ARMATURE")
        mod.object = ob

    # the floor, for the eye
    me = bpy.data.meshes.new("R15_Floor")
    s = 12
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("R15_Floor", me)
    fm = bpy.data.materials.new("R15_Floor")
    fm.diffuse_color = (0.35, 0.36, 0.40, 1)
    me.materials.append(fm)
    scene.collection.objects.link(fl)
    return ob


def _conj():
    """Each bone's axes from the Roblox axes: a Roblox Transform becomes a pose bone's local value by conjugating with it."""
    ob = bpy.data.scenes[SCENE].objects[ARMATURE]
    out = {}
    for b in ob.data.bones:
        out[b.name] = b.matrix_local.to_quaternion().conjugated() @ MQ
    return ob, out


def store(result):
    """Keeps a baked clip as an Action on the armature, thinned and linear between its keys: exactly what Roblox will play."""
    ob, conj = _conj()
    name = "R15_" + result["Name"]
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    slot = action.slots.new(id_type="OBJECT", name=ob.name)
    layer = action.layers.new("Baked")
    strip = layer.strips.new(type="KEYFRAME")
    bag = strip.channelbag(slot, ensure=True)
    for joint, values in result["Joints"].items():
        if result["Only"] and joint not in result["Only"]:
            continue
        keep = motion.thin(values)
        K = conj[joint]
        Ki = K.conjugated()
        path = 'pose.bones["%s"]' % joint
        qs = []
        prev = None
        for f in keep:
            q = K @ values[f][0] @ Ki
            if prev is not None and prev.dot(q) < 0:
                q = Quaternion((-q.w, -q.x, -q.y, -q.z))
            prev = q
            qs.append(q)
        for i in range(4):
            fc = bag.fcurves.new(path + ".rotation_quaternion", index=i, group_name=joint)
            fc.keyframe_points.add(len(keep))
            flat = []
            for f, q in zip(keep, qs):
                flat += [f + 1, q[i]]
            fc.keyframe_points.foreach_set("co", flat)
            fc.keyframe_points.foreach_set("interpolation", [LINEAR] * len(keep))
            fc.update()
        if values[0][1] is not None:
            for i in range(3):
                fc = bag.fcurves.new(path + ".location", index=i, group_name=joint)
                fc.keyframe_points.add(len(keep))
                flat = []
                for f in keep:
                    flat += [f + 1, (K @ values[f][1])[i]]
                fc.keyframe_points.foreach_set("co", flat)
                fc.keyframe_points.foreach_set("interpolation", [LINEAR] * len(keep))
                fc.update()
    return action


def show(name, frame=1):
    """Puts a stored clip on the armature and sets the scene's range to it."""
    scene = bpy.data.scenes[SCENE]
    bpy.context.window.scene = scene
    ob = scene.objects[ARMATURE]
    for pb in ob.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    action = bpy.data.actions["R15_" + name]
    ob.animation_data_create()
    ob.animation_data.action = action
    ob.animation_data.action_slot = action.slots[0]
    scene.frame_start = 1
    scene.frame_end = int(action.frame_range[1])
    scene.frame_set(frame)
    return scene.frame_end


def write(result, r=None):
    baked = os.path.join(motion.PROJECT, "animation", "baked")
    os.makedirs(baked, exist_ok=True)
    path = os.path.join(baked, result["Name"] + ".json")
    data = motion.encode(result, r or rig())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    return path, data["Keys"]


def make(module, names=None):
    """Bakes a module's clips (all, or the names given), stores and writes each. Returns a line per clip."""
    setup()
    mod = importlib.import_module(module)
    importlib.reload(motion)
    importlib.reload(mod)
    r = rig()
    lines = []
    wanted = [names] if isinstance(names, str) else names
    for name, builder in mod.CLIPS.items():
        if wanted and name not in wanted:
            continue
        clip = builder(r)
        result = motion.bake(clip)
        store(result)
        _, keys = write(result, r)
        lines.append("%s: %.2f s, %d poses (of %d at full rate), legs short by at most %.3f at %.2f s%s" % (name, result["Length"], keys, (result["Frames"] + 1) * 15, result["Short"], result["ShortAt"], "; timing: " + ", ".join(result["Timing"]) if result["Timing"] else ""))
    return "\n".join(lines)
