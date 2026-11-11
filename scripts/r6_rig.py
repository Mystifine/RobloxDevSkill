"""Aeresei's R6 IK + FK Blender rig V2.22, for R6 clips and for fake-R6 clips carried onto R15 (references/animation/blender.md).

Outside Blender (Python 3, standard library):
    python r6_rig.py fetch [--from DIR]   the rig's .blend and Studio .rbxm (from the author's DevForum attachments) and Cautioned's
                                          Roblox Animations add-on 2.6.3 (its GitHub release) into ~/.roblox-dev/r6-rig
                                          (ROBLOX_DEV_HOME), each checked against its pinned size and SHA-256; --from DIR takes
                                          files already on disk instead, found by hash (another skill's cache)
    python r6_rig.py copy OUT.blend       a working copy of the master: never edit the master; refuses to overwrite
    python r6_rig.py paths                where the cached files are

Inside Blender (open the working copy with Python auto-run off; `import r6_rig as r6`):
    r6.check()                the open file is the pinned rig: its controls, body and five embedded scripts at their hashes
    r6.activate()             runs the rig's panel scripts (Rig Settings, Utilities...) once check() passes; posing, keying
                              and export need none of them: the controls drive the body through constraints
    r6.addon()                registers the add-on from the cached zip after its hash check (exporter: rbxanims_bake_file);
                              uses the user's own install when one is registered
    r6.aim(bone, arm, held)   the shoulder's rotation pointing the arm along `arm` and a held item along `held`
    r6.swing(bone, arm)       a free arm's rotation by the shortest swing from hanging (a fixed roll reference flips the arm
                              over as it passes through that reference: 51 degrees in one frame)
    r6.arc(a, b, s, extra=0, lead=False)   (arm, held) at `s` along a cut from arm `a` to arm `b`, the held item trailing
    r6.ground(arm)            raises or lowers LowerTorso-FK so the lower visible sole touches the floor; on the pose as set,
                              before keying it, with no action assigned (an action re-poses the rig when it is evaluated)
    r6.feet(arm, start, end)  where the IK targets put each foot each frame: R6OnR15.plantFeet's input
    r6.export(arm, path, action=None, markers=None, loop=False, channels=None, parts=None)   .rbxanim through the add-on, plus
                              a .json beside it (Markers in seconds, Loop, Fps, Feet, Rest, Channels, Parts) for clip_import.py; channels
                              {name: (bone, property)} samples a keyed custom property a frame, such as a held weapon's flick
                              ({'Flick': ('RightShoulder', 'flick')}: R6OnR15.keyHeld's degrees)

Directions (aim, swing, arc) are in the torso's frame: +X right, +Y forward, +Z up; the rig faces +Y, the floor is z = 0,
1 Blender unit = 1 stud. At rest an arm hangs (-Z) and a held item points forward (+Y), as R6's grip holds a sword.

Adapted from animate-roblox-characters' fetch_assets.py and authentic_rig.py (MIT; THIRD_PARTY_NOTICES.md); the posing helpers
come from a game's weapon clips, measured there."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

HOME = Path(os.environ.get('ROBLOX_DEV_HOME', Path.home() / '.roblox-dev')) / 'r6-rig'
FILES = {
    'blend': {'name': 'Blender R6 Rig.blend', 'size': 4059368,
              'sha256': 'ff75c44b572d32328b62095141c6ce6255c4e9b772ee63d46d92280de1edcdc8',
              'url': 'https://devforum.roblox.com/secure-uploads/uploads/original/5X/1/d/f/7/1df71ef414c374be5577f41841ec913d509bf70f.blend'},
    'rbxm': {'name': 'Studio R6 Rig.rbxm', 'size': 9434,
             'sha256': 'a85e1ce13b6cb15c2094be8afcf6bd66ab2017e10f42be6ecb95faa20dd93444',
             'url': 'https://devforum.roblox.com/uploads/short-url/wVMj4ZTnEU4Ks2dBlo9dbQphSBG.rbxm'},
    'addon': {'name': 'rbx_anims_v2.6.3.zip', 'size': 208570,
              'sha256': '218b5e43e414fe3fa5d8a42cc5fd162b70e66f4cb82efd73ac5006b63895769a',
              'url': 'https://github.com/Cautioned/Blender-Animations-Plugin/releases/download/v2.6.3/rbx_anims_v2.6.3.zip'},
}
HOSTS = {'devforum.roblox.com', 'devforum-uploads.s3.dualstack.us-east-2.amazonaws.com', 'github.com',
         'objects.githubusercontent.com', 'release-assets.githubusercontent.com'}
SCRIPTS = {  # the rig's embedded Python, audited: no network or process code
    'RigBootstrap.py': '2e87eae515b129b0eac2db0138cd2ec215f101e45c975fe7b1eeaabfe38033e7',
    'RigEvents.py': '01731b7ad8c77ac4160f76a513e740c965aa78a7aa5e4072101024a4783e0211',
    'RigSelector.py': '7deaa1d7c3480896b90b148cde7fc24fa974865de5cff691208d537187194e9f',
    'RigSettings.py': 'e9b334ee31ebc87af15b3e75242fea8249b7ff841a7487f1e4c2221cce590edd',
    'RigUtilities.py': 'dc96f3453e5cdb0bea7a3af3f4c8823a06492c81d90ae5f34190e7ef5332760a',
}
# The controls a clip keys: the torso (location: x right, y up, z back; quaternion), the head, each shoulder (FK arms), each
# foot's IK target (location: x right, y forward, z lift; turning about z). Poles, grab points and LookToPoint stay put unless
# a clip needs them.
CONTROLS = ('LowerTorso-FK', 'Head', 'RightShoulder', 'LeftShoulder', 'LeftLeg-IK', 'RightLeg-IK')
REQUIRED = {'MasterControl', 'LowerTorso-FK', 'Head', 'RightShoulder', 'LeftShoulder', 'LeftLeg-IK', 'RightLeg-IK',
            'LeftArm-IK', 'RightArm-IK', 'LookToPoint'}
PARTS = ('HumanoidRootPart', 'Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg')
FPS = 60


# --------------------------------------------------------------------------------------------------- outside Blender
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _allowed(url):
    p = urllib.parse.urlparse(url)
    if p.scheme != 'https' or p.hostname not in HOSTS:
        raise ValueError(f'not an allowed download host: {p.hostname}')
    return url


class _Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _allowed(urllib.parse.urljoin(req.full_url, newurl)))


def _download(spec, target):
    opener = urllib.request.build_opener(_Redirects)
    request = urllib.request.Request(_allowed(spec['url']), headers={'User-Agent': 'roblox-dev r6_rig.py'})
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        with opener.open(request, timeout=60) as response:
            size = 0
            for block in iter(lambda: response.read(1 << 20), b''):
                size += len(block)
                if size > spec['size']:
                    break
                tmp.write(block)
    tmp_path = Path(tmp.name)
    if size != spec['size'] or sha256(tmp_path) != spec['sha256']:
        tmp_path.unlink(missing_ok=True)
        raise ValueError(f'{spec["name"]}: the download does not match its pin (size {size}): not used')
    tmp_path.replace(target)


def fetch(source=None, home=HOME):
    """Each pinned file into `home`, verified. Keeps a verified copy already there; takes one from `source` (a folder searched
    by hash) before downloading. Returns {key: path}."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    found = {}
    if source:
        for p in Path(source).rglob('*'):
            if p.is_file() and p.stat().st_size in {f['size'] for f in FILES.values()}:
                found.setdefault(sha256(p), p)
    out = {}
    for key, spec in FILES.items():
        target = home / spec['name']
        if target.is_file() and sha256(target) == spec['sha256']:
            out[key] = target
            continue
        if target.exists():
            raise ValueError(f'{target} exists and does not match its pin: move it aside, then fetch again')
        if spec['sha256'] in found:
            shutil.copyfile(found[spec['sha256']], target)
        else:
            _download(spec, target)
        out[key] = target
    return out


def copy(out, home=HOME):
    """A working copy of the verified master."""
    master = Path(home) / FILES['blend']['name']
    if not master.is_file() or sha256(master) != FILES['blend']['sha256']:
        raise ValueError('no verified master: run `python r6_rig.py fetch` first')
    out = Path(out)
    if out.exists():
        raise ValueError(f'{out} exists: pick a new name')
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(master, out)
    return out


# --------------------------------------------------------------------------------------------------- inside Blender
def _bpy():
    import bpy
    return bpy


def check():
    """{'ok', 'errors', 'variant'}: the open file holds the pinned rig, embedded scripts unchanged."""
    bpy = _bpy()
    errors = []
    pa, ia = bpy.data.objects.get('__PrimaryArmature'), bpy.data.objects.get('InternalArmature')
    if pa is None or pa.type != 'ARMATURE' or not pa.get('_Rbx_R6_Rig_'):
        errors.append('no __PrimaryArmature marked _Rbx_R6_Rig_: not the R6 IK + FK rig')
    elif not REQUIRED <= set(pa.pose.bones.keys()):
        errors.append('controls missing: ' + ', '.join(sorted(REQUIRED - set(pa.pose.bones.keys()))))
    if ia is None or not set(PARTS) <= set(ia.data.bones.keys()):
        errors.append('no InternalArmature with the R6 parts (the Motor6D rig the exporter bakes)')
    for name, digest in SCRIPTS.items():
        text = bpy.data.texts.get(name)
        if text is None or hashlib.sha256(text.as_string().encode('utf-8')).hexdigest() != digest:
            errors.append(f'embedded script {name} is missing or changed: do not run it')
    legs = [o.name for o in bpy.data.objects if o.type == 'MESH' and o.visible_get() and o.name.split('_')[0] == 'Left Leg']
    variant = legs[0].split('_', 1)[1] if legs else None
    return {'ok': not errors, 'errors': errors, 'variant': variant}


def activate():
    """The rig's panels: runs its four UI scripts once, after check()."""
    bpy = _bpy()
    report = check()
    if not report['ok']:
        return report
    space = bpy.app.driver_namespace
    if space.get('roblox_dev_r6_panels'):
        return {**report, 'already': True}
    import types
    loaded = []
    try:
        for name in ('RigSelector.py', 'RigSettings.py', 'RigUtilities.py', 'RigEvents.py'):
            module = types.ModuleType('roblox_dev_r6_' + name[:-3].lower())
            module.__file__ = name
            sys.modules[module.__name__] = module
            exec(compile(bpy.data.texts[name].as_string(), name, 'exec'), module.__dict__)
            if callable(getattr(module, 'register', None)):
                module.register()
            loaded.append(module)
    except Exception as exc:  # undo what registered, then report
        for module in reversed(loaded):
            try:
                module.unregister()
            except Exception:
                pass
            sys.modules.pop(module.__name__, None)
        return {**report, 'ok': False, 'errors': [f'panel scripts failed: {exc}']}
    space['roblox_dev_r6_panels'] = [m.__name__ for m in loaded]
    return {**report, 'panels': space['roblox_dev_r6_panels']}


def _exporter():
    bpy = _bpy()
    try:
        bpy.ops.object.rbxanims_bake_file.get_rna_type()
        return True
    except (AttributeError, KeyError, RuntimeError):
        return False


def addon(zip_path=None):
    """Cautioned's Roblox Animations add-on, registered for this session (no OAuth, no live-sync server: those start only from
    its panel). A user's own install counts."""
    if _exporter():
        return {'ok': True, 'already': True}
    path = Path(zip_path) if zip_path else HOME / FILES['addon']['name']
    if not path.is_file() or sha256(path) != FILES['addon']['sha256']:
        return {'ok': False, 'errors': [f'{path}: missing or not the pinned 2.6.3 zip (python r6_rig.py fetch)']}
    root = Path(tempfile.gettempdir()) / f'roblox-dev-rbxanims-{FILES["addon"]["sha256"][:12]}'
    with zipfile.ZipFile(path) as z:
        for member in z.infolist():
            target = (root / member.filename).resolve()
            if root.resolve() not in target.parents and target != root.resolve():
                return {'ok': False, 'errors': [f'unsafe path in the zip: {member.filename}']}
        if not (root / '__init__.py').is_file():
            z.extractall(root)
    import importlib.util
    name = 'roblox_dev_rbxanims_263'
    spec = importlib.util.spec_from_file_location(name, root / '__init__.py', submodule_search_locations=[str(root)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        module.register()
    except Exception as exc:
        sys.modules.pop(name, None)
        return {'ok': False, 'errors': [f'the add-on did not register: {exc}']}
    return {'ok': _exporter(), 'errors': [] if _exporter() else ['registered without its exporter']}


def _vec(v):
    from mathutils import Vector
    return Vector(v)


def _shoulder(bone, rotation):
    rest = bone.bone.matrix_local.to_3x3()
    return (rest.inverted() @ rotation @ rest).to_quaternion()


def aim(bone, arm, held):
    """The shoulder's local rotation pointing the arm along `arm` and the held item along `held` (torso frame)."""
    from mathutils import Matrix, Vector
    d = _vec(arm).normalized()
    b = _vec(held) - d * _vec(held).dot(d)
    if b.length < 1e-4:
        b = Vector((0, 1, 0)) - d * d.y
    b.normalize()
    down, fwd = Vector((0, 0, -1)), Vector((0, 1, 0))
    rest = Matrix((fwd, down, fwd.cross(down))).transposed()
    target = Matrix((b, d, b.cross(d))).transposed()
    return _shoulder(bone, target @ rest.inverted())


def swing(bone, arm):
    """A free arm's local rotation by the shortest swing from hanging to `arm` (torso frame)."""
    return _shoulder(bone, _vec((0, 0, -1)).rotation_difference(_vec(arm).normalized()).to_matrix())


def arc(start, end, s, extra=0.0, lead=False):
    """(arm, held) at `s` (0 start, 1 end, past 1 overshoots) along the great circle from arm `start` to arm `end`, `extra`
    degrees added to the sweep (a cut longer than the short way). The held item trails the arm round the arc, or leads it
    (`lead`: a rising cut, whose trailing blade would point at the floor). A cut is the rigid arm and blade turning about one
    axis through the shoulder: it reads as a whipped slash on a rigid R6 arm."""
    from mathutils import Quaternion, Vector
    a, e = _vec(start).normalized(), _vec(end).normalized()
    axis = a.cross(e)
    axis = axis.normalized() if axis.length > 1e-4 else Vector((0, 0, 1))
    sweep = math.degrees(math.acos(max(-1.0, min(1.0, a.dot(e))))) + extra
    d = Quaternion(axis, math.radians(sweep * s)) @ a
    return tuple(d), tuple(axis.cross(d) if lead else d.cross(axis))


def _legs():
    bpy = _bpy()
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get() and o.name.split('_')[0] in ('Left Leg', 'Right Leg')]


def soles():
    """{visible leg: its lowest point's height} at the current frame (the floor is 0)."""
    bpy = _bpy()
    bpy.context.view_layer.update()
    return {o.name: min((o.matrix_world @ _vec(c)).z for c in o.bound_box) for o in _legs()}


def ground(arm, tolerance=0.001):
    """Moves LowerTorso-FK straight up or down until the lower visible sole touches the floor; returns the move (studs)."""
    bpy = _bpy()
    torso = arm.pose.bones['LowerTorso-FK']
    moved = 0.0
    for _ in range(8):
        low = min(soles().values())
        if abs(low) < tolerance:
            break
        torso.location.y -= low
        moved -= low
        bpy.context.view_layer.update()
    return moved


def feet(arm, start, end):
    """{'Feet': {'Left Leg' | 'Right Leg': [[x, z, lift] a frame]}, 'Rest': {leg: [x, z]}}: the IK targets in the Roblox root's
    terms (studs right and back of the root, lift above the floor). They are where the feet are meant to be: the rigid legs
    miss them in a crouch, so the R15 carry-over reaches each leg for its target instead (R6OnR15.plantFeet)."""
    bpy = _bpy()
    ia = bpy.data.objects['InternalArmature']
    hrp = ia.pose.bones['HumanoidRootPart']
    ik = {'Left Leg': arm.pose.bones['LeftLeg-IK'], 'Right Leg': arm.pose.bones['RightLeg-IK']}
    track = {leg: [] for leg in ik}
    keep = bpy.context.scene.frame_current
    for f in range(int(start), int(end) + 1):
        bpy.context.scene.frame_set(f)
        root = ia.matrix_world @ hrp.head
        for leg, pb in ik.items():
            at = arm.matrix_world @ pb.head - root
            rest_z = (arm.matrix_world @ pb.bone.head_local).z
            lift = (arm.matrix_world @ pb.head).z - rest_z
            track[leg].append([round(at.x, 4), round(-at.y, 4), round(max(0.0, lift), 4)])
    bpy.context.scene.frame_set(keep)
    root = ia.matrix_world @ hrp.bone.head_local
    rest = {leg: [round((arm.matrix_world @ pb.bone.head_local - root).x, 4), round(-(arm.matrix_world @ pb.bone.head_local - root).y, 4)]
            for leg, pb in ik.items()}
    return {'Feet': track, 'Rest': rest}


def channel(action, bone, prop, start, end):
    """A keyed custom property of a pose bone, a value a frame from its curve (0 where it has none)."""
    path = f'pose.bones["{bone}"]["{prop}"]'
    import blender_anim
    curve = next((c for c in blender_anim.curves(action) if c.data_path == path), None)
    return [round(curve.evaluate(f), 4) if curve else 0.0 for f in range(int(start), int(end) + 1)]


def export(arm, path, action=None, markers=None, loop=False, start=None, end=None, channels=None, parts=None):
    """Bakes the action on the controls from InternalArmature (the Motor6D rig) to `path`.rbxanim through the add-on, and writes
    `path`.json beside it: Markers {name: seconds} (from {name: frame}), Loop, Fps, Feet and Rest (feet()), and Channels
    {name: [value a frame]} for `channels` {name: (bone, property)}, and Parts for a layer that keys only some R6 parts (the
    exporter bakes every part; ClipImport keeps these): ('Torso', 'Head', 'Left Arm', 'Right Arm') leaves the legs to the clip
    beneath. The scene's action, frame range and selection are restored."""
    bpy = _bpy()
    ready = addon()
    if not ready['ok']:
        return ready
    ia = bpy.data.objects['InternalArmature']
    act = bpy.data.actions[action] if isinstance(action, str) else (action or arm.animation_data.action)
    sc = bpy.context.scene
    s = int(round(act.frame_range[0] if start is None else start))
    e = int(round(act.frame_range[1] if end is None else end))
    path = Path(path).with_suffix('.rbxanim')
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = (arm.animation_data.action, sc.frame_start, sc.frame_end, sc.frame_current, sc.rbx_anim_settings.rbx_anim_armature,
            list(bpy.context.selected_objects), bpy.context.view_layer.objects.active)
    errors = []
    try:
        arm.animation_data.action = act
        sc.frame_start, sc.frame_end = s, e
        sc.rbx_anim_settings.rbx_anim_armature = ia.name
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        ia.select_set(True)
        bpy.context.view_layer.objects.active = ia
        tmp = path.with_name('.' + path.name + '.tmp')
        result = bpy.ops.object.rbxanims_bake_file(filepath=str(tmp))
        if 'FINISHED' not in result or not tmp.is_file() or tmp.stat().st_size == 0:
            errors.append(f'the exporter returned {sorted(result)} and no file')
        else:
            tmp.replace(path)
            fps = sc.render.fps / sc.render.fps_base
            info = {'Markers': {k: round((v - s) / fps, 4) for k, v in (markers or {}).items()}, 'Loop': bool(loop), 'Fps': fps}
            info.update(feet(arm, s, e))
            if parts:
                info['Parts'] = list(parts)
            if channels:
                info['Channels'] = {name: channel(act, bone, prop, s, e) for name, (bone, prop) in channels.items()}
            path.with_suffix('.json').write_text(json.dumps(info), encoding='utf-8')
    except Exception as exc:
        errors.append(f'export failed: {exc}')
    finally:
        arm.animation_data.action, sc.frame_start, sc.frame_end = keep[0], keep[1], keep[2]
        sc.frame_set(keep[3])
        sc.rbx_anim_settings.rbx_anim_armature = keep[4]
        bpy.ops.object.select_all(action='DESELECT')
        for o in keep[5]:
            o.select_set(True)
        bpy.context.view_layer.objects.active = keep[6]
    return {'ok': not errors, 'errors': errors, 'rbxanim': str(path), 'json': str(path.with_suffix('.json')), 'frames': [s, e]}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--from', dest='source')
    c = sub.add_parser('copy')
    c.add_argument('out')
    sub.add_parser('paths')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'fetch':
            print(json.dumps({k: str(v) for k, v in fetch(a.source).items()}))
        elif a.cmd == 'copy':
            print(copy(a.out))
        else:
            print(json.dumps({k: str(HOME / v['name']) for k, v in FILES.items()}))
    except (OSError, ValueError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
