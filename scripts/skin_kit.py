"""Shapes and layout for modeling a welded skin around roblox_rig's replica (references/rigs.md, Skins). Blender 4.2+:

    import roblox_rig as rr, skin_kit as kit
    dump = rr.load(path); rig = rr.build(dump, colors={...})
    L = kit.layout(dump, rig)                 # the same keys on R6 and R15 (below)
    P = kit.Pieces()
    a = L['arms']['Left']                     # a gauntlet from the wrist to the elbow, open toward the torso:
    lo, hi = a['lo'].copy(), a['hi'].copy(); lo.z, hi.z = a['wrist'] + .08, a['elbow'] - .1
    P.put(a['lower'], 'Navy', kit.wrap(lo, hi, 0.07, gap=0.03, open_side=a['inner']))
    pieces = P.objects({'Navy': '#2B5AA6', 'Gold': '#E8B83A'})   # '<Part>__<Look>' objects, triangulated
    kit.render(out_dir, 'clay', clay=True)    # front, right, back and three-quarter views beside the reference
    # Geometry QA with the replica body before UVs/bakes (references/rigs.md, step 4).
    # PBR (the default, references/modeling.md), after the clay check:
    skins, glow = kit.merge(pieces, emissive={'Glow'})   # one '<Part>__Skin' per body part; glow stays Neon
    kit.unwrap(skins); kit.unwrap(glow)       # one atlas, one texel density
    maps = kit.bake(skins, PBR, out_dir, 'MyStand_R6')   # color, normal, metal, rough PNGs at 1024
    kit.preview(skins, maps); kit.render(out_dir, 'pbr', pbr=True)
    # Final geometry + UV QA before export, then verify the FBX by re-importing.
    rr.export_pieces(skins + glow, fbx_path)  # then RigSkin.apply(rig, skin, { looks = ... }) in Studio

PBR: {look: {'base': '#rrggbb', 'metal': 0 or 1, 'rough': 0..1, 'rough_var': 0.08, 'edge': '#rrggbb' or None (worn
edges), 'edge_amount': 0.5, 'grime': 0.35 (AO multiply), 'bump': 0.05 (fine surface relief), 'brushed': bool}}. bake()
builds a procedural Cycles material per look (edge wear from a bevel-vs-true-normal mask, grime from AO, roughness noise,
bevelled normals) and bakes NORMAL, ROUGHNESS and, through an emission, the albedo and metalness (Cycles' diffuse colour
is black on metal). An R6 skin baked in about 45 s on CPU (2026-10-30).

Space as roblox_rig: the ground at 0, facing -Y, the character's left at +X, 1 unit = 1 stud. Every shape returns a
bmesh in world space; Pieces.put merges it into the object for its body part and look (one MeshPart each in Roblox,
styled by RigSkin's `looks`). Leave 0.03 studs between faces that look the same way (references/modeling.md).

layout(dump, rig) -> {
  'head':  {'part', 'c' (centre), 'r' (radius), 'h' (half height)},
  'torso': {'lo', 'hi', 'waist', 'chest', 'hip'}                        R15: UpperTorso x/y, LowerTorso bottom
  'arms':  {'Left'|'Right': {'lo', 'hi', 'out', 'inner', 'elbow', 'wrist', 'upper', 'lower', 'hand'}}
  'legs':  {'Left'|'Right': {'lo', 'hi', 'out', 'inner', 'knee', 'ankle', 'upper', 'lower', 'foot'}}}
lo/hi are box corners (Vectors); joint heights come from the dump's pivots on R15, and on R6 (one part per limb) sit at
the elbow/knee 1 stud above the limb's bottom, the wrist 0.3, the ankle 0.32 and the waist 0.45 above the torso's
bottom. `out` is +1 on the left (+X), -1 on the right; `inner` is the wrap side that faces the torso or the other leg;
upper/lower/hand (foot) name the body part that owns each segment (all the same part on R6). owner(seg, z) picks it
for a height.

Shapes: box(lo, hi, b) bevelled; wrap(lo, hi, thick, gap, open_side, corner, flare, inset) walls around a limb, open on
the side that would cut into the torso or the other leg; revolve(center, prof, sides, sx, sy, keep, n, tilt) a surface
of revolution (n > 2: a squircle that hugs a box; keep(angle, z, x, y) drops faces); shell(t, thick, outward) gives an
open surface thickness; prism(outline, origin, u, v, n, d0, d1) an extruded outline; cyl(center, axis, r, d0, d1);
text(body, height, depth, origin, u, v, n, d0, shear, font) extruded lettering; head_profile(r, h, off, zmin) the
classic head's outline grown by `off`, for a helmet that hugs it.

Checks: folds(objs) where a mesh overlaps itself in one plane, which both rr exports refuse."""
import math
import os
import bmesh
import bpy
from mathutils import Matrix, Vector
import roblox_rig as rr

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
folds = rr.folds  # a check, kept in roblox_rig so its exports can refuse a fold


def _box_of(dump, name):
    info = dump['parts'][name]
    c = rr.to_blender(info['cframe'], dump['rootHeight']).translation
    sx, sy, sz = info.get('visual', info['size'])
    s = Vector((sx, sz, sy))
    return c - s / 2, c + s / 2


def layout(dump, rig):
    piv = {k: v.copy() for k, v in rig['pivots'].items()}
    r15 = dump['rigType'] == 'R15'
    lo, hi = _box_of(dump, 'Head')
    head = {'part': 'Head', 'c': (lo + hi) / 2, 'r': (hi.x - lo.x) / 2, 'h': (hi.z - lo.z) / 2}
    if r15:
        ut, lt = _box_of(dump, 'UpperTorso'), _box_of(dump, 'LowerTorso')
        torso = {'lo': Vector((ut[0].x, ut[0].y, lt[0].z)), 'hi': ut[1].copy(), 'waist': piv['UpperTorso'].z, 'chest': 'UpperTorso', 'hip': 'LowerTorso'}
    else:
        t = _box_of(dump, 'Torso')
        torso = {'lo': t[0], 'hi': t[1], 'waist': t[0].z + 0.45, 'chest': 'Torso', 'hip': 'Torso'}
    arms, legs = {}, {}
    for side in ('Left', 'Right'):
        out = 1 if side == 'Left' else -1
        inner = '-x' if out > 0 else '+x'
        if r15:
            ua, hd = _box_of(dump, side + 'UpperArm'), _box_of(dump, side + 'Hand')
            arms[side] = {'lo': Vector((ua[0].x, ua[0].y, hd[0].z)), 'hi': ua[1].copy(), 'elbow': piv[side + 'LowerArm'].z,
                          'wrist': piv[side + 'Hand'].z, 'upper': side + 'UpperArm', 'lower': side + 'LowerArm', 'hand': side + 'Hand'}
            ul, ft = _box_of(dump, side + 'UpperLeg'), _box_of(dump, side + 'Foot')
            legs[side] = {'lo': Vector((ul[0].x, ul[0].y, ft[0].z)), 'hi': ul[1].copy(), 'knee': piv[side + 'LowerLeg'].z,
                          'ankle': piv[side + 'Foot'].z, 'upper': side + 'UpperLeg', 'lower': side + 'LowerLeg', 'foot': side + 'Foot'}
        else:
            a, l_ = _box_of(dump, side + ' Arm'), _box_of(dump, side + ' Leg')
            arms[side] = {'lo': a[0], 'hi': a[1], 'elbow': a[0].z + 1.0, 'wrist': a[0].z + 0.3,
                          'upper': side + ' Arm', 'lower': side + ' Arm', 'hand': side + ' Arm'}
            legs[side] = {'lo': l_[0], 'hi': l_[1], 'knee': l_[0].z + 1.0, 'ankle': l_[0].z + 0.32,
                          'upper': side + ' Leg', 'lower': side + ' Leg', 'foot': side + ' Leg'}
        arms[side].update(out=out, inner=inner); legs[side].update(out=out, inner=inner)
    return {'head': head, 'torso': torso, 'arms': arms, 'legs': legs}


def owner(seg, z):
    """The body part that owns height z of an arm, leg or the torso layout entry."""
    if 'waist' in seg:
        return seg['chest'] if z > seg['waist'] else seg['hip']
    if 'elbow' in seg:
        return seg['upper'] if z > seg['elbow'] else seg['lower'] if z > seg['wrist'] else seg['hand']
    return seg['upper'] if z > seg['knee'] else seg['lower'] if z > seg['ankle'] else seg['foot']


class Pieces:
    """Geometry gathered per (body part, look); objects() makes one '<Part>__<Look>' object for each."""

    def __init__(self):
        self.acc = {}

    def put(self, part, look, t, smooth=False):
        """Gather bmesh t (freed); weld within this input only, never between separate ornaments.
        smooth=None keeps its faces' own shading."""
        bmesh.ops.remove_doubles(t, verts=t.verts[:], dist=1e-5)
        if smooth is not None:
            for f in t.faces:
                f.smooth = smooth
        me = bpy.data.meshes.new('tmp'); t.to_mesh(me); t.free()
        acc = self.acc.setdefault((part, look), bmesh.new()); acc.from_mesh(me); bpy.data.meshes.remove(me)

    def objects(self, colors, collection='SKIN'):
        """Triangulated objects in `collection`, each with a preview material in its look's color ('#rrggbb')."""
        col = bpy.data.collections.get(collection) or bpy.data.collections.new(collection)
        if col.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(col)
        mats, out = {}, []
        for (part, look), t in sorted(self.acc.items()):
            bmesh.ops.triangulate(t, faces=t.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
            name = f'{part}__{look}'
            me = bpy.data.meshes.new(name); t.to_mesh(me); t.free()
            if look not in mats:
                mats[look] = bpy.data.materials.new('M_' + look)
                mats[look].diffuse_color = (*[x ** 2.2 for x in rr._rgb(colors.get(look, '#A3A2A5'))], 1)
            me.materials.append(mats[look])
            ob = bpy.data.objects.new(name, me); col.objects.link(ob); out.append(ob)
        self.acc = {}
        return out


def _cube(lo, hi):
    t = bmesh.new(); bmesh.ops.create_cube(t, size=1.0)
    for v in t.verts:
        v.co = Vector(tuple(lo[i] + (v.co[i] + .5) * (hi[i] - lo[i]) for i in range(3)))
    t.normal_update()
    return t


def bevel(t, off, seg=2, edges=None):
    if off > 0:
        bmesh.ops.bevel(t, geom=edges if edges is not None else t.edges[:], offset=off, offset_type='OFFSET', segments=seg,
                        profile=0.5, affect='EDGES', clamp_overlap=True)
    return t


def box(lo, hi, b=0.03, seg=2):
    return bevel(_cube(Vector(lo), Vector(hi)), b, seg)


def _solidify_sign():
    t = _cube(Vector((-1, -1, -1)), Vector((1, 1, 1)))
    bmesh.ops.delete(t, geom=[f for f in t.faces if abs(f.normal.z) > .5], context='FACES')
    bmesh.ops.solidify(t, geom=t.faces[:], thickness=0.1)
    m = max(abs(v.co.x) for v in t.verts); t.free()
    return 1 if m > 1.05 else -1  # +1: a positive thickness grows outward


_SOLID = None


def shell(t, thick, outward=False):
    """Thickness for an open surface: inward from its outer side (default) or outward."""
    global _SOLID
    if _SOLID is None:
        _SOLID = _solidify_sign()
    t.normal_update()
    bmesh.ops.solidify(t, geom=t.faces[:], thickness=thick * (_SOLID if outward else -_SOLID))
    bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
    return t


def wrap(lo, hi, thick, gap=0.02, open_side=None, corner=0.05, flare=0.0, inset=0.04):
    """Walls around a limb or the torso (x/y of lo..hi, z from lo.z to hi.z), `gap` clear of it and `thick` thick.
    open_side '+x', '-x' or 'x' (both) leaves out the walls that would cut into the torso, an arm or the other leg; the
    remaining walls end `inset` inside the body. flare widens the bottom by that much."""
    lo, hi = Vector(lo), Vector(hi)
    a, b = lo - Vector((gap, gap, 0)), hi + Vector((gap, gap, 0))
    if open_side in ('-x', 'x'):
        a.x = lo.x + inset
    if open_side in ('+x', 'x'):
        b.x = hi.x - inset
    t = _cube(a, b)
    dels = [f for f in t.faces if abs(f.normal.z) > .5]
    if open_side:
        s = {'+x': 1, '-x': -1, 'x': 0}[open_side]
        dels += [f for f in t.faces if (f.normal.x * s > .5 if s else abs(f.normal.x) > .5)]
    bmesh.ops.delete(t, geom=dels, context='FACES')
    if flare:
        c = (a + b) / 2
        for v in t.verts:
            if v.co.z < c.z:
                v.co.y = c.y + (v.co.y - c.y) * (1 + flare / ((b.y - a.y) / 2))
                if not open_side or (open_side == '-x' and v.co.x > c.x) or (open_side == '+x' and v.co.x < c.x):
                    v.co.x = c.x + (v.co.x - c.x) * (1 + flare / ((b.x - a.x) / 2))
    bevel(t, corner, 2, [e for e in t.edges if len(e.link_faces) == 2])
    return shell(t, thick, outward=True)


def revolve(center, prof, sides=32, sx=1.0, sy=1.0, keep=None, n=2.0, tilt=None):
    """Surface of revolution around z through `center`: prof [(radius, z)] bottom to top, radius 0 a pole; the cross
    section is an ellipse (sx, sy), or a squircle for n > 2. tilt (a 3x3 Matrix) turns it about `center`. keep(angle_deg,
    z, x, y) on face centres relative to `center` (angle 0 at the front, -Y) drops the faces it rejects. Open: shell()."""
    t = bmesh.new(); rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([t.verts.new(center + Vector((0, 0, z)))])
        else:
            ring = []
            for a in (i * math.tau / sides for i in range(sides)):
                k = (abs(math.sin(a)) ** n + abs(math.cos(a)) ** n) ** (-1 / n)
                ring.append(t.verts.new(center + Vector((math.sin(a) * r * sx * k, -math.cos(a) * r * sy * k, z))))
            rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(A) == 1:
                t.faces.new((A[0], B[j], B[i]))
            elif len(B) == 1:
                t.faces.new((A[i], A[j], B[0]))
            else:
                t.faces.new((A[i], A[j], B[j], B[i]))
    if tilt:
        bmesh.ops.rotate(t, cent=center, matrix=tilt, verts=t.verts[:])
    t.normal_update()
    if keep:
        drop = []
        for f in t.faces:
            p = f.calc_center_median() - center
            if not keep(math.degrees(math.atan2(p.x, -p.y)), p.z, p.x, p.y):
                drop.append(f)
        bmesh.ops.delete(t, geom=drop, context='FACES')
    return t


def head_profile(r, h, off, zmin, round_=0.58):
    """A classic head's outline (radius r, half height h, top edge rounded by round_ * min(r, h)) grown by `off`, from
    zmin up to the pole, as (radius, z) for revolve(); 7 rings up the side so a keep() band can cut anywhere."""
    e = min(r, h) * round_
    p = [(r + off, zmin + (h - e - zmin) * k / 6) for k in range(7)]
    for k in range(1, 8):
        a = math.radians(90 * k / 8)
        p.append((r - e + (e + off) * math.cos(a), h - e + (e + off) * math.sin(a)))
    return p + [((r - e) * .5, h + off), (0, h + off)]


def _crossing(outline):
    """Two edges of the closed outline [(a, c)] that cross, or None. Outlines that only touch at a shared point pass."""
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    n = len(outline)
    for i in range(n):
        p, q = outline[i], outline[(i + 1) % n]
        for j in range(i + 2, n - (i == 0)):
            r, s = outline[j], outline[(j + 1) % n]
            if side(p, q, r) * side(p, q, s) < 0 and side(r, s, p) * side(r, s, q) < 0:
                return (p, q), (r, s)
    return None


def prism(outline, origin, u, v, n, d0, d1, b=0.015):
    """Polygon [(a, c)] in the plane origin + a*u + c*v, extruded along n from d0 to d1. Concave is fine; an outline that crosses
    itself is refused, because its cap would fold over itself (references/modeling.md): end two arcs where they meet."""
    crossed = _crossing(outline)
    if crossed:
        raise ValueError(f'prism: the outline crosses itself, between edges {crossed[0]} and {crossed[1]}')
    t = bmesh.new()
    lo = [t.verts.new(origin + a * u + c * v + d0 * n) for a, c in outline]
    hi = [t.verts.new(origin + a * u + c * v + d1 * n) for a, c in outline]
    t.faces.new(lo); t.faces.new(hi)
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        t.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
    return bevel(t, b, 1)


def cyl(center, axis, r, d0, d1, sides=20, b=0.015):
    """A capped cylinder on `axis` through center, from d0 to d1 along it; smooth sides, bevelled caps."""
    t = bmesh.new()
    bmesh.ops.create_cone(t, cap_ends=True, cap_tris=False, segments=sides, radius1=r, radius2=r, depth=d1 - d0)
    ax = axis.normalized()
    rot = Z.rotation_difference(ax).to_matrix().to_4x4()
    bmesh.ops.transform(t, matrix=Matrix.Translation(center + ax * (d0 + d1) / 2) @ rot, verts=t.verts[:])
    t.normal_update()
    bevel(t, b, 1, [e for e in t.edges if any(abs(f.normal.dot(ax)) > .9 for f in e.link_faces)])
    for f in t.faces:
        f.smooth = abs(f.normal.dot(ax)) < .5
    return t


_FONTS = {}


def text(body, height, depth, origin, u, v, n, d0=0.0, shear=0.18, offset=0.0, font=None):
    """Extruded lettering `height` tall, centred on origin in the plane (u right, v up), from d0 to d0 + depth along n.
    font: a .ttf path (Blender's built-in font when None). To read from behind, pass u = -X; on a +X side, u = +Y."""
    cu = bpy.data.curves.new('txt', 'FONT'); cu.body = body
    if font:
        if font not in _FONTS:
            _FONTS[font] = bpy.data.fonts.load(font)
        cu.font = _FONTS[font]
    cu.shear = shear; cu.offset = offset; cu.extrude = 0.5
    ob = bpy.data.objects.new('txt', cu); bpy.context.scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    t = bmesh.new(); t.from_mesh(me)
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu); bpy.data.meshes.remove(me)
    xs, ys = [p.co.x for p in t.verts], [p.co.y for p in t.verts]
    k = height / (max(ys) - min(ys)); cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    for p in t.verts:
        x, y, z = p.co
        p.co = origin + (x - cx) * k * u + (y - cy) * k * v + (d0 + (z + 0.5) * depth) * n
    t.normal_update()
    return t


VIEWS = {'front': (0, -1, 0), 'right': (-1, 0, 0), 'back': (0, 1, 0), 'threeq': (0.62, -1, 0.18)}


def _pbr_lights(sc):
    """A sky-to-ground gradient world and a sun, so metal reflects as it will in game."""
    w = bpy.data.worlds.new('KIT_PBR_WORLD'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tc, mp, gr, ramp = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeMapping'), nt.nodes.new('ShaderNodeTexGradient'), nt.nodes.new('ShaderNodeValToRGB')
    mp.inputs['Rotation'].default_value = (0, math.radians(-90), 0)
    ramp.color_ramp.elements[0].color = (0.45, 0.42, 0.40, 1); ramp.color_ramp.elements[1].color = (0.75, 0.85, 1.0, 1)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector'])
    nt.links.new(gr.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    if not bpy.data.objects.get('KIT_SUN'):
        sun = bpy.data.lights.new('KIT_SUN', 'SUN'); sun.energy = 3.0
        so = bpy.data.objects.new('KIT_SUN', sun); sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(50), 0, math.radians(30))


def render(out_dir, tag, clay=False, views=VIEWS, res=(520, 800), pbr=False, samples=32):
    """Stills of every visible object (the replica body and the skin) from `views` (name: direction from the character
    to the camera; orthographic, the three-quarter view perspective), saved as <out_dir>/<tag>_<view>.png. Workbench by
    default (clay=True: one gray, for the clay check); pbr=True renders the baked maps in Cycles under a sky and a sun.
    Give out_dir as an absolute path: a relative one is not resolved against the script's folder."""
    sc = bpy.context.scene
    if pbr:
        sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
        _pbr_lights(sc)
    else:
        sc.render.engine = 'BLENDER_WORKBENCH'
        sh = sc.display.shading
        sh.light, sh.color_type, sh.single_color = 'STUDIO', 'SINGLE' if clay else 'MATERIAL', (.6, .6, .6)
        sh.show_cavity, sh.cavity_type = True, 'BOTH'
        sh.show_object_outline, sh.object_outline_color = True, (0, 0, 0)
        sc.world = sc.world or bpy.data.worlds.new('W'); sc.world.color = (.9, .9, .88)
    sc.render.resolution_x, sc.render.resolution_y = res
    top = max((ob.matrix_world @ Vector(c)).z for ob in sc.objects if ob.type == 'MESH' and not ob.hide_render for c in ob.bound_box)
    cam_d = bpy.data.cameras.new('kit_cam'); cam = bpy.data.objects.new('kit_cam', cam_d)
    sc.collection.objects.link(cam); sc.camera = cam
    mid = Vector((0, 0, top / 2))
    paths = []
    for name, d in views.items():
        d = Vector(d).normalized()
        if name == 'threeq':
            cam_d.type, cam_d.lens = 'PERSP', 50
            cam.location = mid + d * top * 1.75
        else:
            cam_d.type, cam_d.ortho_scale = 'ORTHO', top * 1.12
            cam.location = mid + d * 20
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out_dir, f'{tag}_{name}.png')
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cam_d)
    return paths


# ---------------------------------------------------------------- PBR stage


def merge(pieces, emissive=()):
    """Join each body part's pieces into one '<Part>__Skin' object (a material slot per look); pieces whose look is in
    `emissive` stay apart, for Neon in Roblox. Returns (skins, emissive pieces)."""
    by_part, glow = {}, []
    for ob in pieces:
        part, look = ob.name.split('__', 1)
        if look in emissive:
            glow.append(ob)
        else:
            by_part.setdefault(part, []).append(ob)
    skins = []
    for part, obs in sorted(by_part.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = f'{part}__Skin'
        skins.append(ob)
    return skins, glow


def unwrap(objs, margin=0.004):
    """Smart-project every object into one shared 0-1 atlas at one texel density."""
    if not objs:
        return
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def _lin(hexc):
    return tuple(x ** 2.2 for x in rr._rgb(hexc)) + (1.0,)


def _pbr_material(name, p):
    m = bpy.data.materials.new('PBR_' + name); m.use_nodes = True
    nt = m.node_tree; N, Lk = nt.nodes, nt.links
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    bs, geo = N.new('ShaderNodeBsdfPrincipled'), N.new('ShaderNodeNewGeometry')
    bev = N.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = 0.014; bev.samples = 8
    dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    Lk.new(bev.outputs['Normal'], dot.inputs[0]); Lk.new(geo.outputs['Normal'], dot.inputs[1])
    edge = N.new('ShaderNodeMath'); edge.operation = 'SUBTRACT'; edge.inputs[0].default_value = 1.0
    Lk.new(dot.outputs['Value'], edge.inputs[1])
    mask = N.new('ShaderNodeMath'); mask.operation = 'MULTIPLY'; mask.use_clamp = True; mask.inputs[1].default_value = 9.0
    Lk.new(edge.outputs[0], mask.inputs[0])  # edge mask: where the bevelled normal leaves the true one
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 16; ao.inputs['Distance'].default_value = 0.25
    tc, mp = N.new('ShaderNodeTexCoord'), N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1, 1, 28) if p.get('brushed') else (1, 1, 1)
    Lk.new(tc.outputs['Object'], mp.inputs['Vector'])
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 24.0; noise.inputs['Detail'].default_value = 6.0
    Lk.new(mp.outputs['Vector'], noise.inputs['Vector'])
    mix_e = N.new('ShaderNodeMix'); mix_e.data_type = 'RGBA'  # worn edges
    mix_e.inputs[6].default_value = _lin(p['base']); mix_e.inputs[7].default_value = _lin(p.get('edge') or p['base'])
    fe = N.new('ShaderNodeMath'); fe.operation = 'MULTIPLY'; fe.inputs[1].default_value = p.get('edge_amount', 0.5)
    Lk.new(mask.outputs[0], fe.inputs[0]); Lk.new(fe.outputs[0], mix_e.inputs[0])
    mix_g = N.new('ShaderNodeMix'); mix_g.data_type = 'RGBA'; mix_g.blend_type = 'MULTIPLY'  # grime in the AO
    mix_g.inputs[0].default_value = p.get('grime', 0.35)
    Lk.new(mix_e.outputs[2], mix_g.inputs[6]); Lk.new(ao.outputs['Color'], mix_g.inputs[7])
    Lk.new(mix_g.outputs[2], bs.inputs['Base Color'])
    var = p.get('rough_var', 0.08)  # roughness: base + noise - polished edges + grime
    r1 = N.new('ShaderNodeMath'); r1.operation = 'MULTIPLY_ADD'; r1.inputs[1].default_value = var; r1.inputs[2].default_value = p['rough'] - var / 2
    Lk.new(noise.outputs['Fac'], r1.inputs[0])
    r2 = N.new('ShaderNodeMath'); r2.operation = 'MULTIPLY_ADD'; r2.inputs[1].default_value = -0.12
    Lk.new(mask.outputs[0], r2.inputs[0]); Lk.new(r1.outputs[0], r2.inputs[2])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    r3 = N.new('ShaderNodeMath'); r3.operation = 'MULTIPLY_ADD'; r3.use_clamp = True; r3.inputs[1].default_value = 0.25
    Lk.new(ao.outputs['AO'], inv.inputs[1]); Lk.new(inv.outputs[0], r3.inputs[0]); Lk.new(r2.outputs[0], r3.inputs[2])
    Lk.new(r3.outputs[0], bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value = p['metal']
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = p.get('bump', 0.05); bump.inputs['Distance'].default_value = 0.02
    Lk.new(noise.outputs['Fac'], bump.inputs['Height']); Lk.new(bev.outputs['Normal'], bump.inputs['Normal'])
    Lk.new(bump.outputs['Normal'], bs.inputs['Normal'])
    Lk.new(bs.outputs['BSDF'], out.inputs['Surface'])
    m['metal'] = p['metal']
    return m


def bake(objs, looks, out_dir, prefix, size=1024, samples=16):
    """Bake the merged skin's four SurfaceAppearance maps into <out_dir>/<prefix>_{color,normal,metal,rough}.png
    (Cycles, CPU). `looks` maps each look (the 'M_<Look>' preview material from Pieces.objects) to PBR parameters."""
    # Validate the whole batch before changing materials, render settings or images.
    if not objs:
        raise ValueError('bake: no skin objects')
    slots = []
    for ob in objs:
        if ob.type != 'MESH' or not ob.material_slots:
            raise ValueError(f'bake: {ob.name} needs a mesh with assigned materials')
        for index, slot in enumerate(ob.material_slots):
            if slot.material is None:
                raise ValueError(f'bake: {ob.name} material slot {index} is empty; assign a material or remove the unused slot')
            look = slot.material.name.split('M_', 1)[-1].split('.')[0]
            if look not in looks:
                raise ValueError(f'bake: {ob.name} material {slot.material.name!r} has no PBR look {look!r}')
            missing = {'base', 'metal', 'rough'} - looks[look].keys()
            if missing:
                raise ValueError(f'bake: look {look!r} is missing {", ".join(sorted(missing))}')
            slots.append((slot, look))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = False
    sc.render.bake.margin = 8; sc.render.bake.target = 'IMAGE_TEXTURES'; sc.render.bake.use_clear = True
    mats = {}
    for slot, look in slots:
        if look not in mats:
            mats[look] = _pbr_material(look, looks[look])
        slot.material = mats[look]
    mats = list(mats.values())
    imgs = {}
    for key, cs in (('color', 'sRGB'), ('normal', 'Non-Color'), ('metal', 'Non-Color'), ('rough', 'Non-Color')):
        imgs[key] = bpy.data.images.new(f'{prefix}_{key}', size, size, alpha=False)
        imgs[key].colorspace_settings.name = cs
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    def target(img):
        for m in mats:
            node = m.node_tree.nodes.get('BAKE') or m.node_tree.nodes.new('ShaderNodeTexImage')
            node.name = 'BAKE'; node.image = img; m.node_tree.nodes.active = node

    def emit(source):  # route a socket, or a constant colour, into an emission shader for an EMIT bake
        saved = []
        for m in mats:
            nt = m.node_tree; out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
            bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); em = nt.nodes.new('ShaderNodeEmission')
            src = source(m, bs)
            if isinstance(src, tuple):
                em.inputs['Color'].default_value = src
            else:
                nt.links.new(src, em.inputs['Color'])
            nt.links.new(em.outputs['Emission'], out.inputs['Surface']); saved.append((nt, out, bs, em))
        return saved

    def restore(saved):
        for nt, out, bs, em in saved:
            nt.nodes.remove(em); nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])

    target(imgs['normal']); bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
    target(imgs['rough']); bpy.ops.object.bake(type='ROUGHNESS')
    saved = emit(lambda m, bs: bs.inputs['Base Color'].links[0].from_socket)
    target(imgs['color']); bpy.ops.object.bake(type='EMIT'); restore(saved)
    saved = emit(lambda m, bs: (m['metal'], m['metal'], m['metal'], 1.0))
    target(imgs['metal']); bpy.ops.object.bake(type='EMIT'); restore(saved)
    paths = {}
    for key, img in imgs.items():
        paths[key] = os.path.join(out_dir, f'{prefix}_{key}.png')
        img.filepath_raw = paths[key]; img.file_format = 'PNG'; img.save()
    return paths


def preview(objs, maps):
    """Give the merged skin one material that reads the baked maps, as Roblox's SurfaceAppearance will (render pbr=True)."""
    m = bpy.data.materials.new('SKIN_BAKED'); m.use_nodes = True
    nt = m.node_tree; bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    def tex(key, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(maps[key], check_existing=True)
        n.image.colorspace_settings.name = cs
        return n
    nt.links.new(tex('color', 'sRGB').outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(tex('metal', 'Non-Color').outputs['Color'], bs.inputs['Metallic'])
    nt.links.new(tex('rough', 'Non-Color').outputs['Color'], bs.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex('normal', 'Non-Color').outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    for ob in objs:
        ob.data.materials.clear(); ob.data.materials.append(m)
