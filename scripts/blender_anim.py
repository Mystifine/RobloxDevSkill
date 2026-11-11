"""Keying, reviewing, auditing and exporting Roblox clips in Blender (references/animation/blender.md). Run inside Blender 4.5+
(tested on 5.1) through Blender MCP or headless: `import sys; sys.path.insert(0, SCRIPTS); import blender_anim as ba`.

    ba.session()                         the Blender itself: background or not, the file, unsaved changes, the frame rate
    ba.inspect(armature=None)            armatures (bones, parents, rotation modes, constraints), actions, animated meshes
    ba.key(arm, frame, bones, interpolation='CONSTANT', action=None)
                                         keys one pose batch, checked whole before anything changes: bones = { name: {
                                         'location': [x, y, z], 'rotation_degrees': [x, y, z] (in the bone's own order) or
                                         'rotation_quaternion': [w, x, y, z], 'scale': [x, y, z] } }; a quaternion is kept on the
                                         side of the bone's previous key (no long way round between keys)
    ba.review(arm, folder, label, frame=None, front=None)   front and side PNGs of one pose (Workbench, orthographic)
    ba.polish(arm, action=None, sharp=(), loop=None)        every key Bezier: auto-clamped handles, VECTOR at the `sharp`
                                         frames (a release, an impact), quaternions on one side, a loop's ends matched and cycled
    ba.audit(arm, action=None, stage='FINAL', loop=..., contacts=..., ...)   the checks below; FINAL needs `loop` and `contacts`
                                         stated (False or a value), so a check is never skipped by leaving it out
    ba.preview(arm, folder, prefix, start, end, step=2)    PNG frames for gif_preview.py (three-quarter front, fixed framing)
    ba.deltas(arm, path, action=None, ...)   a bone rig's clip as world deltas a sample (JSON), for ClipImport.deltas in Studio
    ba.export_fbx(arm, path, action=None)    one action, deform bones only, Roblox's FBX settings (for Studio's own importer)

Every call returns a dict: 'ok', 'errors', 'warnings' and its own fields. Distances are in studs: pass `studs` (Blender units
per stud) for a rig not at 1:1 (the R6 rig and roblox_rig replicas are 1:1).

audit() checks, each an error unless noted:
  curves      only pose-bone curves on the action; no animated mesh (a control rig's custom shapes are skipped)
  keys        BLOCKING allows Constant keys; FINAL allows none, and Linear only between keys 1-3 frames apart (an R6
              animator's dense string of poses; sparse Linear keys read mechanical)
  turn        (FINAL) no joint of `measure` (default: the armature that is exported) turns over `turn` degrees (43) in a 1/60 s frame,
              or 15+ degrees and 4 times more than every frame within two of it (a pop: an Euler flip or a missing key);
              AnimationInspector errors at 45 in Studio, and a bake or a retarget can add a degree or two
  loop        (start, end): end pose = start pose within 0.0001 units, 0.1 degrees and 0.0001 scale (evaluated, constraints
              included); end tangents within 0.001 value a frame (a warning while BLOCKING)
  contacts    { bone or mesh object: [[start, end], ...] }: a planted bone's head and tail (an object's origin) drift at most
              `drift` studs (0.02)
  soles       mesh objects whose lowest point must not sink below `floor` + -0.05 at any frame (a warning: an R6 rig's rigid
              legs sink in a crouch; the R15 carry-over plants them, an R6 game needs r6_rig.ground)

Adapted from animate-roblox-characters' animation_tools.py (MIT; THIRD_PARTY_NOTICES.md)."""
import json
import math
from pathlib import Path
import re

try:
    import bpy
    from mathutils import Vector
except ImportError:  # plain Python: check_pose and turn_findings still work (tests/python)
    bpy = Vector = None

FPS = 60
TRANSFORMS = {'location', 'rotation_degrees', 'rotation_quaternion', 'scale'}
EULER = {'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'}
DENSE = 3  # frames: Linear keys this close read as an R6 animator's pose string, not mechanical motion
R6_RIG = ('__PrimaryArmature', 'InternalArmature')  # Aeresei's R6 IK + FK rig (r6_rig.py): faces +Y


def _result(ok=None, errors=None, warnings=None, **fields):
    errors, warnings = errors or [], warnings or []
    return {'ok': (not errors) if ok is None else bool(ok and not errors), 'errors': errors, 'warnings': warnings, **fields}


def _armature(arm):
    if isinstance(arm, str):
        found = bpy.data.objects.get(arm)
        if found is None or found.type != 'ARMATURE':
            raise ValueError(f'no armature named {arm}')
        return found
    if arm is None:
        found = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
        if len(found) != 1:
            raise ValueError('name the armature: ' + ', '.join(o.name for o in found))
        return found[0]
    return arm


def _action(arm, action=None):
    if isinstance(action, str):
        found = bpy.data.actions.get(action)
        if found is None:
            raise ValueError(f'no action named {action}')
        return found
    if action is not None:
        return action
    if arm.animation_data and arm.animation_data.action:
        return arm.animation_data.action
    raise ValueError(f'{arm.name} has no action')


def curves(action):
    """An action's F-curves, legacy or layered (Blender 4.4+ slotted actions)."""
    legacy = getattr(action, 'fcurves', None)
    if legacy is not None:
        return list(legacy)
    out = []
    for layer in getattr(action, 'layers', ()):
        for strip in getattr(layer, 'strips', ()):
            for bag in getattr(strip, 'channelbags', ()):
                out.extend(bag.fcurves)
    return out


def _bone_of(path):
    m = re.match(r'^pose\.bones\["((?:\\.|[^"\\])*)"\]', path)
    if not m:
        return None
    try:
        return json.loads(f'"{m.group(1)}"')
    except json.JSONDecodeError:
        return None


def _front(arm, front):
    if front is not None:
        v = Vector(tuple(float(x) for x in front))
        v.z = 0
        if v.length < 1e-6:
            raise ValueError('front needs a horizontal direction')
        return v.normalized()
    if arm.name in R6_RIG:
        return Vector((0, 1, 0))
    if arm.get('rig_type'):  # a roblox_rig replica faces -Y
        return Vector((0, -1, 0))
    raise ValueError(f'which way does {arm.name} face? Look at it, then pass front=(x, y, 0)')


# ---------------------------------------------------------------------------------------------------------------------------
def session():
    """Where this runs. Warns when the file has unsaved work (save a copy or ask before changing it) and when the scene is
    not at 60 fps."""
    sc = bpy.context.scene
    warnings = []
    if bpy.data.is_dirty and bpy.data.filepath:
        warnings.append('the open file has unsaved changes: ask before changing it, or work on a copy')
    if sc.render.fps != FPS or sc.render.fps_base != 1.0:
        warnings.append(f'the scene runs at {sc.render.fps / sc.render.fps_base:g} fps; clips are authored at 60')
    return _result(warnings=warnings, blender='.'.join(map(str, bpy.app.version)), background=bpy.app.background,
                   file=bpy.data.filepath or None, dirty=bpy.data.is_dirty, fps=sc.render.fps / sc.render.fps_base,
                   frames=[sc.frame_start, sc.frame_end], unit_scale=sc.unit_settings.scale_length,
                   auto_exec=bpy.context.preferences.filepaths.use_scripts_auto_execute)


def inspect(armature=None):
    """The scene's armatures and actions; the named (or only) armature in detail."""
    arms = sorted((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), key=lambda o: o.name)
    out = {'armatures': {o.name: len(o.data.bones) for o in arms}, 'actions': sorted(a.name for a in bpy.data.actions),
           'animated_meshes': _animated_meshes()}
    try:
        arm = _armature(armature)
    except ValueError as exc:
        return _result(warnings=[str(exc)], **out)
    out['armature'] = arm.name
    out['action'] = arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None
    out['bones'] = {pb.name: {'parent': pb.parent.name if pb.parent else None, 'mode': pb.rotation_mode,
                              'deform': pb.bone.use_deform, 'constraints': [c.type for c in pb.constraints]}
                    for pb in arm.pose.bones}
    return _result(**out)


def _animated_meshes():
    shapes = {pb.custom_shape for o in bpy.context.scene.objects if o.type == 'ARMATURE' for pb in o.pose.bones if pb.custom_shape}
    found = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH' or o in shapes:
            continue
        for owner, label in ((o, o.name), (o.data, o.name + '.data'), (getattr(o.data, 'shape_keys', None), o.name + '.keys')):
            data = getattr(owner, 'animation_data', None)
            if data and ((data.action and curves(data.action)) or any(t.strips for t in data.nla_tracks)):
                found.append(label)
    return sorted(found)


# ---------------------------------------------------------------------------------------------------------------------------
def _triplet(value, label):
    if isinstance(value, (str, bytes)):
        raise ValueError(f'{label}: three numbers')
    items = [float(v) for v in value]
    if len(items) != 3 or not all(math.isfinite(v) for v in items):
        raise ValueError(f'{label}: three finite numbers')
    return items


def check_pose(frame, bones, available, interpolation='CONSTANT'):
    """The whole batch checked and normalised before anything is keyed (no bpy needed)."""
    if isinstance(frame, bool) or not math.isfinite(float(frame)) or float(frame) != int(float(frame)):
        raise ValueError('frame: a whole number')
    if not isinstance(bones, dict) or not bones:
        raise ValueError('bones: { name: changes }')
    missing = sorted(set(bones) - set(available))
    if missing:
        raise ValueError('no such bones: ' + ', '.join(missing))
    interpolation = str(interpolation).upper()
    if interpolation not in {'CONSTANT', 'BEZIER', 'LINEAR'}:
        raise ValueError('interpolation: CONSTANT, BEZIER or LINEAR')
    out = {}
    for name, changes in bones.items():
        if not isinstance(changes, dict):
            raise ValueError(f'{name}: a mapping')
        extra = set(changes) - TRANSFORMS - {'rotation_mode'}
        if extra or not TRANSFORMS & set(changes):
            raise ValueError(f'{name}: use ' + ', '.join(sorted(TRANSFORMS)))
        if {'rotation_degrees', 'rotation_quaternion'} <= set(changes):
            raise ValueError(f'{name}: one rotation, not two')
        n = {k: _triplet(changes[k], f'{name}.{k}') for k in ('location', 'rotation_degrees', 'scale') if k in changes}
        if 'rotation_quaternion' in changes:
            q = [float(v) for v in changes['rotation_quaternion']]
            size = math.sqrt(sum(v * v for v in q)) if len(q) == 4 and all(math.isfinite(v) for v in q) else 0
            if size < 1e-9:
                raise ValueError(f'{name}.rotation_quaternion: four finite numbers, w first, not zero')
            n['rotation_quaternion'] = [v / size for v in q]
        if 'rotation_mode' in changes:
            if 'rotation_degrees' not in changes or str(changes['rotation_mode']).upper() not in EULER:
                raise ValueError(f'{name}.rotation_mode: an Euler order, with rotation_degrees')
            n['rotation_mode'] = str(changes['rotation_mode']).upper()
        out[str(name)] = n
    return int(float(frame)), out, interpolation


def _previous_quaternion(action, bone, frame):
    """The bone's quaternion at its last key before `frame`, or None."""
    path = f'pose.bones["{bone}"].rotation_quaternion'
    values, at = [None] * 4, None
    for c in curves(action):
        if c.data_path == path:
            keys = [k for k in c.keyframe_points if k.co.x < frame - 1e-6]
            if keys:
                values[c.array_index] = keys[-1].co.y
                at = keys[-1].co.x
    return values if at is not None and None not in values else None


def key(arm, frame, bones, interpolation='CONSTANT', action=None):
    arm = _armature(arm)
    try:
        frame, changes, interpolation = check_pose(frame, bones, arm.pose.bones.keys(), interpolation)
        for name, c in changes.items():
            mode = arm.pose.bones[name].rotation_mode
            if 'rotation_degrees' in c and 'rotation_mode' not in c:
                if mode not in EULER:
                    raise ValueError(f'{name} turns by {mode}: pass rotation_quaternion')
                c['rotation_mode'] = mode
    except ValueError as exc:
        return _result(errors=[str(exc)])
    if arm.animation_data is None:
        arm.animation_data_create()
    if action:
        arm.animation_data.action = bpy.data.actions.get(action) or bpy.data.actions.new(action)
    elif arm.animation_data.action is None:
        arm.animation_data.action = bpy.data.actions.new(arm.name + 'Clip')
    act = arm.animation_data.action
    bpy.context.scene.frame_set(frame)
    keyed = []
    for name, c in changes.items():
        pb = arm.pose.bones[name]
        if 'location' in c:
            pb.location = c['location']
            pb.keyframe_insert('location', frame=frame, group=name)
            keyed.append(name + '.location')
        if 'rotation_degrees' in c:
            pb.rotation_mode = c['rotation_mode']
            pb.rotation_euler = [math.radians(v) for v in c['rotation_degrees']]
            pb.keyframe_insert('rotation_euler', frame=frame, group=name)
            keyed.append(name + '.rotation_euler')
        if 'rotation_quaternion' in c:
            q = c['rotation_quaternion']
            before = _previous_quaternion(act, name, frame)
            if before and sum(a * b for a, b in zip(before, q)) < 0:
                q = [-v for v in q]  # the same turn, on the previous key's side: Blender blends the four channels apart
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=frame, group=name)
            keyed.append(name + '.rotation_quaternion')
        if 'scale' in c:
            pb.scale = c['scale']
            pb.keyframe_insert('scale', frame=frame, group=name)
            keyed.append(name + '.scale')
    for c in curves(act):
        if _bone_of(c.data_path) in changes:
            for k in c.keyframe_points:
                if abs(k.co.x - frame) < 1e-6:
                    k.interpolation = interpolation
    bpy.context.view_layer.update()
    heads = {n: [round(v, 4) for v in arm.matrix_world @ arm.pose.bones[n].head] for n in changes}
    return _result(action=act.name, frame=frame, keyed=keyed, heads=heads)


# ---------------------------------------------------------------------------------------------------------------------------
def _driven(arm):
    out = []
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and o.visible_get() and not o.hide_render and (
                o.parent in (arm, *[a for a in bpy.data.objects if a.name in R6_RIG])
                or any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)
                or any(getattr(c, 'target', None) is not None and c.target.name in R6_RIG for c in o.constraints)):
            out.append(o)
    return out


def _bounds(arm, frames=None):
    sc = bpy.context.scene
    now = sc.frame_current
    pts = []
    for f in frames or [now]:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for o in _driven(arm):
            e = o.evaluated_get(dg)
            pts += [e.matrix_world @ Vector(c) for c in e.bound_box]
        if not pts:
            pts += [arm.matrix_world @ p for pb in arm.pose.bones for p in (pb.head, pb.tail)]
    sc.frame_set(now)
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def _review_collection():
    col = bpy.data.collections.get('Review') or bpy.data.collections.new('Review')
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    return col


def _camera(name, at, target, scale):
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        _review_collection().objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = scale
    cam.location = at
    cam.rotation_euler = (target - at).to_track_quat('-Z', 'Y').to_euler()
    return cam


def _render(paths_and_cameras, size):
    """Renders each (path, camera) with Workbench: studio light, textures, outlines. Restores the scene's settings."""
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage,
            sc.render.engine, sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.film_transparent)
    shading = sc.display.shading
    keep_shading = (shading.light, shading.color_type, shading.show_object_outline)
    errors = []
    try:
        sc.render.engine = 'BLENDER_WORKBENCH'
        shading.light = 'STUDIO'
        shading.color_type = 'TEXTURE' if any(i.source == 'FILE' for i in bpy.data.images) else 'MATERIAL'
        shading.show_object_outline = True
        sc.render.resolution_x = sc.render.resolution_y = size
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGB'
        sc.render.film_transparent = False
        for path, cam, frame in paths_and_cameras:
            if frame is not None:
                sc.frame_set(frame)
            sc.camera = cam
            sc.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            if not Path(path).is_file():
                errors.append(f'no image at {path}')
    except Exception as exc:  # render failures are reported, not raised
        errors.append(f'render failed: {exc}')
    finally:
        (sc.camera, sc.render.filepath, sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage,
         sc.render.engine, sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.film_transparent) = keep
        shading.light, shading.color_type, shading.show_object_outline = keep_shading
    return errors


def review(arm, folder, label, frame=None, front=None, size=512):
    """Front and side views of one pose, framed on the body: judge them, not the numbers (blender.md, Review)."""
    arm = _armature(arm)
    try:
        forward = _front(arm, front)
    except ValueError as exc:
        return _result(errors=[str(exc)])
    if frame is not None:
        bpy.context.scene.frame_set(int(frame))
    lo, hi = _bounds(arm)
    centre, dims = (lo + hi) / 2, hi - lo
    scale = max(dims.z * 1.18, dims.x * 1.45, dims.y * 1.45, 4.0)
    far = max(10.0, scale * 1.8)
    side = Vector((forward.y, -forward.x, 0))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^A-Za-z0-9_-]+', '-', label).strip('-') or 'pose'
    f = bpy.context.scene.frame_current
    shots = {v: folder / f'{safe}-f{f:04d}-{v}.png' for v in ('front', 'side')}
    errors = _render([(shots['front'], _camera('Review_Front', centre + forward * far, centre, scale), None),
                      (shots['side'], _camera('Review_Side', centre + side * far, centre, scale), None)], size)
    return _result(errors=errors, images={k: str(v) for k, v in shots.items()}, frame=f)


# ---------------------------------------------------------------------------------------------------------------------------
def _hemisphere(action):
    """Negates quaternion keys that sit on the far side of the bone's previous key (all four channels together)."""
    groups = {}
    for c in curves(action):
        if c.data_path.endswith('.rotation_quaternion'):
            groups.setdefault(c.data_path, {})[c.array_index] = c
    flipped = 0
    for chans in groups.values():
        if len(chans) != 4:
            continue
        frames = sorted({round(k.co.x, 4) for c in chans.values() for k in c.keyframe_points})
        prev = None
        for f in frames:
            keys = [next((k for k in chans[i].keyframe_points if abs(k.co.x - f) < 1e-4), None) for i in range(4)]
            if None in keys:
                prev = None
                continue
            q = [k.co.y for k in keys]
            if prev is not None and sum(a * b for a, b in zip(prev, q)) < 0:
                for k in keys:
                    k.co.y = -k.co.y
                    k.handle_left.y = -k.handle_left.y
                    k.handle_right.y = -k.handle_right.y
                q = [-v for v in q]
                flipped += 1
            prev = q
    return flipped


def polish(arm, action=None, sharp=(), loop=None):
    """Bezier everywhere: auto-clamped handles, VECTOR at `sharp` frames (where the motion changes direction hard: a coil's
    release, the middle of a whip, an impact: the sweep through them stays even instead of bursting into the next key).
    `loop` (start, end): each curve's end key takes its first key's value, and a Cycles modifier makes the handles meet
    across the seam."""
    arm = _armature(arm)
    try:
        act = _action(arm, action)
    except ValueError as exc:
        return _result(errors=[str(exc)])
    sharp = {round(float(f)) for f in sharp}
    flipped = _hemisphere(act)
    count, other = 0, []
    for c in curves(act):
        if _bone_of(c.data_path) is None:
            other.append(f'{c.data_path}[{c.array_index}]')
            continue
        if loop:
            first = next((k for k in c.keyframe_points if abs(k.co.x - loop[0]) < 1e-4), None)
            last = next((k for k in c.keyframe_points if abs(k.co.x - loop[1]) < 1e-4), None)
            if first and last:
                last.co.y = first.co.y
            if not any(m.type == 'CYCLES' for m in c.modifiers):
                c.modifiers.new('CYCLES')
        for k in c.keyframe_points:
            k.interpolation = 'BEZIER'
            kind = 'VECTOR' if round(k.co.x) in sharp else 'AUTO_CLAMPED'
            k.handle_left_type = k.handle_right_type = kind
            count += 1
        c.update()
    return _result(errors=[f'curves that are not pose bones: {other[:5]}'] if other else [], keys=count, flipped=flipped)


# ---------------------------------------------------------------------------------------------------------------------------
def _degrees(a, b):
    """The turn between two rotations the short way (a quaternion and its negative are the same turn)."""
    d = math.degrees(a.rotation_difference(b).angle) % 360.0
    return min(d, 360.0 - d)


def _local_rotations(arm, frames):
    """{bone: [parent-relative rotation quaternion a frame]} from the evaluated pose (constraints included)."""
    sc = bpy.context.scene
    out = {pb.name: [] for pb in arm.pose.bones}
    for f in frames:
        sc.frame_set(f)
        e = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for pb in e.pose.bones:
            m = pb.matrix if pb.parent is None else pb.parent.matrix.inverted() @ pb.matrix
            out[pb.name].append(m.to_quaternion())
    return out


def turn_findings(series, fps, limit):
    """Per-frame turn findings for {bone: [degrees turned since the previous frame]}: over `limit` (in 1/60 s), or a pop."""
    errors, worst = [], (0.0, '', 0)
    for name, steps in series.items():
        per60 = [a * fps / FPS for a in steps]
        for i, a in enumerate(per60):
            if a > worst[0]:
                worst = (a, name, i + 1)
            near = [per60[j] for j in range(max(0, i - 2), min(len(per60), i + 3)) if j != i]
            if a > limit:
                errors.append(f'{name} turns {a:.0f} degrees in one 60 fps frame at frame {i + 1} (limit {limit:g}): '
                              'spread the turn over another frame, or make the key before it sharp')
            elif a >= 15 and near and a >= 4 * max(near):
                errors.append(f'{name} pops {a:.0f} degrees at frame {i + 1}: a flip or a missing key')
    return errors, worst


def _seam(arm, act, start, end):
    sc = bpy.context.scene
    names = sorted({_bone_of(c.data_path) for c in curves(act)} - {None} | {pb.name for pb in arm.pose.bones if pb.bone.use_deform})
    names = [n for n in names if n in arm.pose.bones]
    snaps = {}
    for f in (start, end):
        sc.frame_set(f)
        e = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        snaps[f] = {n: e.pose.bones[n].matrix.copy() for n in names}
    loc = rot = scl = 0.0
    for n in names:
        a, b = snaps[start][n].decompose(), snaps[end][n].decompose()
        loc = max(loc, (a[0] - b[0]).length)
        rot = max(rot, _degrees(a[1], b[1]))
        scl = max(scl, (a[2] - b[2]).length)
    slope, missing = 0.0, []
    for c in curves(act):
        if _bone_of(c.data_path) is None:
            continue
        first = next((k for k in c.keyframe_points if abs(k.co.x - start) < 1e-4), None)
        last = next((k for k in c.keyframe_points if abs(k.co.x - end) < 1e-4), None)
        if first is None or last is None:
            missing.append(f'{c.data_path}[{c.array_index}]')
            continue

        def d(k, h):
            dx = h.x - k.co.x
            return (h.y - k.co.y) / dx if abs(dx) > 1e-8 else 0.0
        slope = max(slope, abs(d(first, first.handle_right) - d(last, last.handle_left)))
    return {'location': loc, 'degrees': rot, 'scale': scl, 'slope': slope, 'missing': missing}


def _drift(arm, contacts, studs):
    sc = bpy.context.scene
    out, errors = {}, []
    for name, spans in contacts.items():
        target = arm.pose.bones.get(name) or bpy.data.objects.get(name)
        if target is None:
            errors.append(f'contact {name}: no such bone or object')
            continue
        for s, e in spans:
            points = []
            for f in range(int(s), int(e) + 1):
                sc.frame_set(f)
                dg = bpy.context.evaluated_depsgraph_get()
                if isinstance(target, bpy.types.PoseBone):
                    ea = arm.evaluated_get(dg)
                    pb = ea.pose.bones[name]
                    points.append((ea.matrix_world @ pb.head, ea.matrix_world @ pb.tail))
                else:
                    points.append((target.evaluated_get(dg).matrix_world.translation.copy(),))
            worst = max(max((p[i] - points[0][i]).length for i in range(len(p))) for p in points) / studs
            out.setdefault(name, []).append([int(s), int(e), round(worst, 4)])
    return out, errors


def _sinks(objects, frames, floor, studs):
    sc = bpy.context.scene
    worst = {}
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for o in objects:
            e = o.evaluated_get(dg)
            low = min((e.matrix_world @ Vector(c)).z for c in e.bound_box)
            depth = (floor - low) / studs
            if depth > worst.get(o.name, (0.0, 0))[0]:
                worst[o.name] = (round(depth, 3), f)
    return worst


def audit(arm, action=None, stage='FINAL', loop=None, contacts=None, studs=1.0, drift=0.02, turn=43.0, measure=None,
          soles=None, floor=0.0, start=None, end=None):
    """The clip's checks (module docstring). `measure`: the armature whose joints are exported (default: the R6 rig's
    InternalArmature for its controls, else `arm`). `soles`: mesh objects or names (default: the R6 rig's visible legs)."""
    arm = _armature(arm)
    stage = str(stage).upper()
    try:
        act = _action(arm, action)
        if stage not in {'BLOCKING', 'FINAL'}:
            raise ValueError('stage: BLOCKING or FINAL')
        if stage == 'FINAL' and (loop is None or contacts is None):
            raise ValueError('FINAL: state loop=(start, end) or False and contacts={...} or False')
        if not (studs > 0 and math.isfinite(studs)):
            raise ValueError('studs: Blender units per stud, above 0')
    except ValueError as exc:
        return _result(errors=[str(exc)])
    errors, warnings, m = [], [], {'action': act.name, 'stage': stage}
    cs = curves(act)
    if not cs:
        errors.append('the action has no curves')
    names = set(arm.pose.bones.keys())
    other = [f'{c.data_path}[{c.array_index}]' for c in cs if _bone_of(c.data_path) not in names]
    if other:
        errors.append(f'curves that are not this armature\'s pose bones: {other[:5]}')
    meshes = _animated_meshes()
    if meshes:
        errors.append(f'animated meshes (key the armature, never a mesh): {meshes[:5]}')
    kinds = {'BEZIER': 0, 'LINEAR': 0, 'CONSTANT': 0}
    sparse = []
    for c in cs:
        ks = list(c.keyframe_points)
        for i, k in enumerate(ks):
            kinds[k.interpolation] = kinds.get(k.interpolation, 0) + 1
            if k.interpolation == 'LINEAR' and i + 1 < len(ks) and ks[i + 1].co.x - k.co.x > DENSE + 1e-6:
                sparse.append(f'{_bone_of(c.data_path)} at {k.co.x:g}')
    m['keys'] = kinds
    if stage == 'FINAL':
        if kinds['CONSTANT']:
            errors.append(f'{kinds["CONSTANT"]} Constant keys left from blocking: polish() them')
        if sparse:
            errors.append(f'Linear keys more than {DENSE} frames apart read mechanical ({len(sparse)}, first {sparse[0]}): '
                          'Bezier, or a key every 1-3 frames')
    odd = sum(v for k, v in kinds.items() if k not in {'BEZIER', 'LINEAR', 'CONSTANT'})
    if odd:
        errors.append(f'{odd} keys use other interpolation (elastic, bounce...): key the motion instead')

    sc = bpy.context.scene
    fps = sc.render.fps / sc.render.fps_base
    first, last = act.frame_range
    s = int(round(first if start is None else start))
    e = int(round(last if end is None else end))
    if not arm.animation_data:
        arm.animation_data_create()
    keep_action, keep_frame = arm.animation_data.action, sc.frame_current
    muted = [(t, t.mute) for t in arm.animation_data.nla_tracks]
    try:
        arm.animation_data.action = act
        for t, _ in muted:
            t.mute = True
        target = measure or (bpy.data.objects.get('InternalArmature') if arm.name == '__PrimaryArmature' else arm)
        target = _armature(target)
        rots = _local_rotations(target, range(s, e + 1))
        steps = {n: [_degrees(a, b) for a, b in zip(qs, qs[1:])] for n, qs in rots.items()}
        found, worst = turn_findings(steps, fps, turn)
        m['fastest'] = {'degrees_per_60fps_frame': round(worst[0], 1), 'bone': worst[1], 'frame': s + worst[2]}
        if stage == 'FINAL':  # blocking keys jump on purpose
            errors += found[:8] + ([f'... {len(found) - 8} more turn findings'] if len(found) > 8 else [])
        if loop:
            seam = _seam(arm, act, int(loop[0]), int(loop[1]))
            m['seam'] = {k: (round(v, 5) if isinstance(v, float) else v[:5]) for k, v in seam.items()}
            if seam['location'] > 1e-4 or seam['degrees'] > 0.1 or seam['scale'] > 1e-4:
                errors.append(f'loop seam: the end pose misses the start by {seam["location"]:.4f} units, {seam["degrees"]:.2f} '
                              'degrees: match the end keys to the first (polish(loop=...))')
            if seam['missing']:
                errors.append(f'curves without a key at both loop ends: {seam["missing"][:5]}')
            if seam['slope'] > 1e-3:
                (errors if stage == 'FINAL' else warnings).append(
                    f'loop seam speed: the curves change slope by {seam["slope"]:.4f} a frame across the seam (polish(loop=...))')
        elif loop is False:
            pass
        else:
            warnings.append('loop not checked')
        if contacts:
            found, bad = _drift(arm, contacts, studs)
            m['drift'] = found
            errors += bad
            for name, spans in found.items():
                for a, b, d in spans:
                    if d > drift:
                        errors.append(f'{name} slides {d:.3f} studs while planted (frames {a}-{b}; limit {drift:g})')
        elif contacts is False:
            pass
        else:
            warnings.append('contacts not checked')
        if soles is None and arm.name in R6_RIG:
            soles = [o for o in _driven(arm) if o.name.split('_')[0] in ('Left Leg', 'Right Leg')]
        if soles:
            objs = [bpy.data.objects[o] if isinstance(o, str) else o for o in soles]
            sinks = _sinks(objs, range(s, e + 1), floor, studs)
            m['sink'] = sinks
            for name, (depth, f) in sinks.items():
                if depth > 0.05:
                    warnings.append(f'{name} sinks {depth:.2f} studs below the floor at frame {f} '
                                    '(rigid legs in a crouch: an R6 game needs r6_rig.ground; R6OnR15.plantFeet fixes R15)')
    except Exception as exc:  # sampling errors are findings, never a silent pass
        errors.append(f'sampling failed: {exc}')
    finally:
        arm.animation_data.action = keep_action
        for t, mute in muted:
            t.mute = mute
        sc.frame_set(keep_frame)
    return _result(errors=errors, warnings=warnings, metrics=m)


# ---------------------------------------------------------------------------------------------------------------------------
def preview(arm, folder, prefix, start, end, step=2, size=512, front=None, camera=None, target=None, scale=None, exclude_last=False):
    """PNG frames for gif_preview.py, after export: one fixed three-quarter-front view framing the whole clip. `step` 2 shows a
    60 fps clip at 30 (pass --fps 30 to the GIF). `exclude_last` leaves out a loop's closing frame (it repeats the first).
    The R6 rig's view is the proven one: camera (6.8, 8.8, 4.8), target (0, 0, 2.55), scale 6.4."""
    arm = _armature(arm)
    frames = list(range(int(start), int(end) + 1, max(1, int(step))))
    if exclude_last and frames and frames[-1] == int(end):
        frames = frames[:-1]
    if camera is None and arm.name in R6_RIG:
        camera, target, scale = (6.8, 8.8, 4.8), (0, 0, 2.55), scale or 6.4
    if camera is None:
        try:
            forward = _front(arm, front)
        except ValueError as exc:
            return _result(errors=[str(exc)])
        lo, hi = _bounds(arm, frames[::max(1, len(frames) // 8)])
        centre, dims = (lo + hi) / 2, hi - lo
        scale = scale or max(dims.z * 1.15, (dims.x ** 2 + dims.y ** 2) ** 0.5 * 1.15, 4.0)
        side = Vector((forward.y, -forward.x, 0))
        camera, target = centre + (forward * 0.8 + side * 0.6).normalized() * 12 + Vector((0, 0, 4)), centre
    cam = _camera('Review_GIF', Vector(camera), Vector(target), float(scale))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^A-Za-z0-9_-]+', '-', prefix).strip('-') or 'clip'
    shots = [(folder / f'{safe}_{f:04d}.png', cam, f) for f in frames]
    keep = bpy.context.scene.frame_current
    errors = _render(shots, size)
    bpy.context.scene.frame_set(keep)
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base / max(1, int(step))
    return _result(errors=errors, frames=len(shots), folder=str(folder), glob=f'{safe}_*.png', gif_fps=fps)


# ---------------------------------------------------------------------------------------------------------------------------
def deltas(arm, path, action=None, start=None, end=None, step=1, markers=None, loop=False, priority='Action', name=None):
    """A bone rig's clip for ClipImport.deltas: each deform bone's world delta (posed x rest^-1, Blender space) a sample, plus
    the bones' rest heads, which Studio lays on the imported bones to find the axis map. No bone roll or axis convention has
    to match Roblox's (fits to 0.0000 studs). Markers: { name: frame }."""
    arm = _armature(arm)
    act = _action(arm, action)
    sc = bpy.context.scene
    fps = sc.render.fps / sc.render.fps_base
    s = int(round(act.frame_range[0] if start is None else start))
    e = int(round(act.frame_range[1] if end is None else end))
    bones = [pb for pb in arm.pose.bones if pb.bone.use_deform]
    rest = {pb.name: {'head': list(arm.matrix_world @ pb.bone.head_local), 'parent': pb.parent.name if pb.parent else None}
            for pb in bones}
    keep_action, keep_frame = arm.animation_data.action, sc.frame_current
    samples = []
    try:
        arm.animation_data.action = act
        for f in range(s, e + 1, max(1, int(step))):
            sc.frame_set(f)
            ea = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
            row = {}
            for pb in bones:
                posed = ea.matrix_world @ ea.pose.bones[pb.name].matrix
                d = posed @ (arm.matrix_world @ pb.bone.matrix_local).inverted()
                q = d.to_quaternion()
                t = d.translation
                row[pb.name] = [round(v, 6) for v in (t.x, t.y, t.z, q.w, q.x, q.y, q.z)]
            samples.append({'t': round((f - s) / fps, 6), 'bones': row})
    finally:
        arm.animation_data.action = keep_action
        sc.frame_set(keep_frame)
    data = {'Name': name or act.name, 'Loop': bool(loop), 'Priority': priority, 'Fps': fps, 'Rest': rest, 'Samples': samples,
            'Markers': {k: round((v - s) / fps, 4) for k, v in (markers or {}).items()}}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    return _result(path=str(path), samples=len(samples), bones=len(bones))


def export_fbx(arm, path, action=None, start=None, end=None):
    """One action and its deform bones to FBX, baked a sample a frame with no simplifying, no leaf bones, no NLA or other
    actions, FBX unit scale, for Studio's own animation importer. Axes as roblox_rig's tested exports: Blender's default
    -Z forward and Y up, the character facing -Y in Blender. A Motor6D rig exports .rbxanim instead (r6_rig.export)."""
    arm = _armature(arm)
    act = _action(arm, action)
    sc = bpy.context.scene
    path = Path(path).with_suffix('.fbx')
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = (arm.animation_data.action, sc.frame_start, sc.frame_end, sc.frame_current, list(bpy.context.selected_objects),
            bpy.context.view_layer.objects.active)
    muted = [(t, t.mute) for t in arm.animation_data.nla_tracks]
    errors = []
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        for t, _ in muted:
            t.mute = True
        arm.animation_data.action = act
        sc.frame_start = int(round(act.frame_range[0] if start is None else start))
        sc.frame_end = int(round(act.frame_range[1] if end is None else end))
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        for o in _driven(arm):
            o.select_set(True)
        bpy.context.view_layer.objects.active = arm
        wanted = dict(filepath=str(path), check_existing=False, use_selection=True, object_types={'ARMATURE', 'MESH'},
                      apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
                      add_leaf_bones=False, use_armature_deform_only=True, bake_anim=True, bake_anim_use_all_bones=True,
                      bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
                      bake_anim_step=1.0, bake_anim_simplify_factor=0.0, path_mode='AUTO')
        have = set(bpy.ops.export_scene.fbx.get_rna_type().properties.keys())
        result = bpy.ops.export_scene.fbx(**{k: v for k, v in wanted.items() if k in have})
        if 'FINISHED' not in result or not path.is_file():
            errors.append(f'FBX exporter returned {sorted(result)}')
    except Exception as exc:
        errors.append(f'FBX export failed: {exc}')
    finally:
        for t, mute in muted:
            t.mute = mute
        arm.animation_data.action, sc.frame_start, sc.frame_end = keep[0], keep[1], keep[2]
        sc.frame_set(keep[3])
        bpy.ops.object.select_all(action='DESELECT')
        for o in keep[4]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = keep[5]
    return _result(errors=errors, path=str(path), action=act.name)
