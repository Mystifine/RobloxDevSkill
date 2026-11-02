"""R6-like FK and IK on an R15 armature in Blender: the Blender side of R6OnR15.luau (references/animation/r6-on-r15.md).
Run inside Blender 4.2+ (bpy):

    import r6_on_r15 as r6
    roles = r6.load(r"roles.json")             # HttpService:JSONEncode(R6OnR15.dump(R6OnR15.map(rig))) from Studio
    r6.add_controls(armature, roles)           # the controls below; the R15 bones follow them and stop taking poses
    r6.use_ik(armature, 'Right Arm', 1)        # 0 is FK, 1 is IK; keyable, as the `ik` property on its target
    r6.pose_r6(armature, 'Right Arm', cframe)  # or pose by hand; an R6 Transform's 12 numbers, as a clip holds them
    r6.bake(armature, 1, 41)                   # keys the R15 bones from the controls, for the rig's exporter; r6.edit returns

The controls, in the armature's space, turning about R6's pivots on this body:
    FK   R6_Torso, R6_Head, R6_Arm.L/.R, R6_Leg.L/.R: rotate to turn the block, move to slide it. Each sits at its pivot and points
         at its tip. Moving a limb along itself is how R6 fakes a knee or an elbow.
    IK   R6_Arm_IK.L/.R, R6_Leg_IK.L/.R, R6_Head_IK: targets on the root, not the torso, so a planted foot stays planted as the
         body moves. Each has `ik` (0 to 1) and, on limbs, `slide` (0 aims only, 1 slides along the limb to reach the target).
         The roll comes from the FK control, so FK under IK sets it.

The 15 R15 bones keep their names, rest and parents; the nine locked ones are never posed. `space` maps Roblox root space to the
armature's where it is not roblox_rig's: facing -Y, ground at 0, one unit per stud. `names` maps R15 part names to bone names."""
import json

import bpy
from mathutils import Matrix, Vector

import roblox_rig as rr

BLOCKS = {'Torso': 'R6_Torso', 'Head': 'R6_Head', 'Left Arm': 'R6_Arm.L', 'Right Arm': 'R6_Arm.R', 'Left Leg': 'R6_Leg.L', 'Right Leg': 'R6_Leg.R'}
TARGETS = {'Head': 'R6_Head_IK', 'Left Arm': 'R6_Arm_IK.L', 'Right Arm': 'R6_Arm_IK.R', 'Left Leg': 'R6_Leg_IK.L', 'Right Leg': 'R6_Leg_IK.R'}
# R6's joint axes, the rotation of each C0, in Roblox's axes.
R6_BODY = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))
R6_LEFT = Matrix(((0, 0, -1), (0, 1, 0), (1, 0, 0)))
R6_RIGHT = Matrix(((0, 0, 1), (0, 1, 0), (-1, 0, 0)))
TURNS = {'Torso': R6_BODY, 'Head': R6_BODY, 'Left Arm': R6_LEFT, 'Right Arm': R6_RIGHT, 'Left Leg': R6_LEFT, 'Right Leg': R6_RIGHT}
ROOT = 'HumanoidRootPart'
FOLLOW = 'R6 follow'


def load(path_or_text):
    return rr.load(path_or_text)


def _roblox_to_armature(root_height, space):
    if space is not None:
        return space
    mat = rr.M.to_4x4()
    mat.translation = Vector((0, 0, root_height))
    return mat


def _bone(edit, name, head, tail, parent=None, deform=False):
    b = edit.new(name)
    b.head, b.tail = head, tail
    b.use_deform = deform
    b.parent = parent
    return b


def _copy(pb, arm, subtarget, space):
    c = pb.constraints.new('COPY_TRANSFORMS')
    c.name, c.target, c.subtarget = FOLLOW, arm, subtarget
    c.owner_space = c.target_space = space
    return c


def _drive(con, arm, target, expression):
    d = con.driver_add('influence').driver
    d.type, d.expression = 'SCRIPTED', expression
    for prop in ('ik', 'slide'):
        if prop in expression:
            v = d.variables.new()
            v.name, v.type = prop, 'SINGLE_PROP'
            t = v.targets[0]
            t.id_type, t.id, t.data_path = 'OBJECT', arm, f'pose.bones["{target}"]["{prop}"]'


def add_controls(arm, roles, names=None, space=None):
    """Adds the FK and IK controls to `arm`, whose bones are named for R15's parts (or through `names`). Returns the map from each
    R6 part to its FK control. Run it once on a rig; the action you key belongs to the controls."""
    names = names or {}
    bone_of = lambda part: names.get(part, part)  # noqa: E731
    info = roles['roles']
    to_arm = _roblox_to_armature(roles['rootHeight'], space)
    point = lambda xyz: to_arm @ Vector(xyz)  # noqa: E731
    missing = [p for r in info.values() for p in [r['joint'], *r['locked']] if bone_of(p) not in arm.data.bones]
    if missing:
        raise ValueError('not an R15 armature; missing bones: ' + ', '.join(missing))

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    edit = arm.data.edit_bones
    root = edit.get(bone_of(ROOT))
    torso_at = point(info['Torso']['pivot'])
    torso = _bone(edit, BLOCKS['Torso'], torso_at, torso_at + (to_arm.to_3x3() @ Vector((0, 1, 0))), root)
    lengths = {}
    for part, control in BLOCKS.items():
        role = info[part]
        real = edit[bone_of(role['joint'])]
        driver = control
        if part != 'Torso':
            at, tip = point(role['pivot']), point(role['tip'])
            lengths[part] = (tip - at).length
            _bone(edit, control, at, tip, torso)
            driver = 'MCH_' + control
            _bone(edit, driver, at, tip, torso)
            target = TARGETS[part]
            _bone(edit, target, tip, tip + (to_arm.to_3x3() @ Vector((0, 0.5, 0))), root)
        # Follows the driver rigidly: the R15 bone's own head, tail and roll, so it can copy it in world space.
        follower = _bone(edit, 'FOL_' + bone_of(role['joint']), real.head, real.tail, edit[driver])
        follower.matrix = real.matrix.copy()
    bpy.ops.object.mode_set(mode='OBJECT')

    pose = arm.pose.bones
    for part, control in BLOCKS.items():
        role = info[part]
        real = pose[bone_of(role['joint'])]
        _copy(real, arm, 'FOL_' + bone_of(role['joint']), 'WORLD')
        for name in role['locked']:
            bone = pose[bone_of(name)]
            bone.lock_location = bone.lock_rotation = bone.lock_scale = (True, True, True)
            bone.lock_rotation_w = True
        if part == 'Torso':
            continue
        target = pose[TARGETS[part]]
        target['ik'] = 0.0
        target['slide'] = 1.0
        target.id_properties_ui('ik').update(min=0.0, max=1.0)
        target.id_properties_ui('slide').update(min=0.0, max=1.0)
        driver = pose['MCH_' + control]
        _copy(driver, arm, control, 'LOCAL')
        if part != 'Head':
            # On the line to the target, one limb's length from it: the slide. Then aiming lands the tip exactly on the target.
            reach = driver.constraints.new('LIMIT_DISTANCE')
            reach.target, reach.subtarget = arm, TARGETS[part]
            reach.limit_mode, reach.distance = 'LIMITDIST_ONSURFACE', lengths[part]
            reach.owner_space = reach.target_space = 'POSE'
            _drive(reach, arm, TARGETS[part], 'ik * slide')
        aim = driver.constraints.new('DAMPED_TRACK')
        aim.target, aim.subtarget, aim.track_axis = arm, TARGETS[part], 'TRACK_Y'
        _drive(aim, arm, TARGETS[part], 'ik')
    arm['r6_roles'] = json.dumps(roles)
    arm['r6_names'] = json.dumps(names)
    bpy.context.view_layer.update()
    return dict(BLOCKS)


def use_ik(arm, part, amount, slide=None):
    """Blends a limb, or the head's look target, between FK (0) and IK (1); `slide` from aim only (0) to reaching (1)."""
    target = arm.pose.bones[TARGETS[part]]
    target['ik'] = float(amount)
    if slide is not None:
        target['slide'] = float(slide)
    arm.update_tag()
    bpy.context.view_layer.update()


def place_target(arm, part, roblox_xyz, space=None):
    """Puts a limb's IK target on a point given in Roblox root space."""
    roles = json.loads(arm['r6_roles'])
    pb = arm.pose.bones[TARGETS[part]]
    wanted = _roblox_to_armature(roles['rootHeight'], space) @ Vector(roblox_xyz)
    pb.matrix = Matrix.Translation(wanted) @ pb.bone.matrix_local.to_3x3().to_4x4()
    bpy.context.view_layer.update()


def pose_r6(arm, part, cframe, space=None):
    """Poses a block's FK control with an R6 Transform: x, y, z and the nine rotation numbers of a Roblox CFrame, as an R6 clip's Pose
    holds them. The torso's motion is the parent's, so pose it first."""
    roles = json.loads(arm['r6_roles'])
    to_arm = _roblox_to_armature(roles['rootHeight'], space).to_3x3()
    x, y, z, *r = cframe
    axes = TURNS[part]
    turn = to_arm @ (axes @ Matrix((r[0:3], r[3:6], r[6:9])) @ axes.inverted()) @ to_arm.inverted()
    shift = to_arm @ (axes @ Vector((x, y, z))) * roles['roles'][part]['scale']
    pb = arm.pose.bones[BLOCKS[part]]
    at = pb.bone.head_local
    moved = Matrix.Translation(at + shift) @ turn.to_4x4() @ Matrix.Translation(-at) @ pb.bone.matrix_local
    parent = pb.parent
    pb.matrix = (parent.matrix @ parent.bone.matrix_local.inverted() @ moved) if parent else moved
    bpy.context.view_layer.update()


def _r15_bones(arm):
    roles = json.loads(arm['r6_roles'])['roles']
    names = json.loads(arm['r6_names'])
    return [names.get(p, p) for r in roles.values() for p in [r['joint'], *r['locked']]]


def bake(arm, start, end, step=1, name='R6OnR15'):
    """Keys the 15 R15 bones on a new action from what the controls do, frame by frame, and stops them following, so they export as
    keyed. The controls' action is kept for `edit`. Returns the baked action."""
    controls = arm.animation_data.action if arm.animation_data else None
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    wanted = set(_r15_bones(arm))
    for pb in arm.pose.bones:
        if hasattr(pb, 'select'):  # on the pose bone from Blender 5, on the bone before it
            pb.select = pb.name in wanted
        else:
            pb.bone.select = pb.name in wanted
    bpy.ops.nla.bake(frame_start=start, frame_end=end, step=step, only_selected=True, visual_keying=True, clear_constraints=False,
                     use_current_action=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm.animation_data.action
    baked.name = name
    arm['r6_controls_action'] = controls.name if controls else ''
    _follow(arm, False)
    return baked


def edit(arm):
    """Back to the controls after `bake`: the R15 bones follow them again, on the action they were keyed on."""
    _follow(arm, True)
    name = arm.get('r6_controls_action')
    arm.animation_data.action = bpy.data.actions.get(name) if name else None
    bpy.context.view_layer.update()


def _follow(arm, on):
    for name in _r15_bones(arm):
        for c in arm.pose.bones[name].constraints:
            if c.name == FOLLOW:
                c.mute = not on
    arm.update_tag()
    bpy.context.view_layer.update()


def check_locks(arm, tolerance=1e-4):
    """The locked bones that left their rest pose relative to their parents, [] when none did: the joint policy on the evaluated rig."""
    roles = json.loads(arm['r6_roles'])['roles']
    names = json.loads(arm['r6_names'])
    moved = []
    for role in roles.values():
        for part in role['locked']:
            pb = arm.pose.bones[names.get(part, part)]
            if pb.parent is None:
                continue
            local = pb.bone.matrix_local.inverted() @ pb.parent.bone.matrix_local @ pb.parent.matrix.inverted() @ pb.matrix
            off = (local - Matrix.Identity(4))
            if max(abs(v) for row in off for v in row) > tolerance:
                moved.append(part)
    return moved
