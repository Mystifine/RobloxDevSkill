"""Shapes and layout for modeling a welded skin around roblox_rig's replica (references/rigs.md, Skins). Blender 4.2+:

    import roblox_rig as rr, skin_kit as kit
    dump = rr.load(path); rig = rr.build(dump, colors={...})
    L = kit.layout(dump, rig)                 # the same keys on R6 and R15 (below)
    P = kit.Pieces()
    a = L['arms']['Left']                     # a gauntlet from the wrist to the elbow, closed around the arm:
    lo, hi = a['lo'].copy(), a['hi'].copy(); lo.z, hi.z = a['wrist'] + .08, a['elbow'] - .1
    P.put(a['lower'], 'Navy', kit.wrap(lo, hi, 0.07, gap=0.03, tuck=a['inner']))
    pieces = P.objects({'Navy': '#2B5AA6', 'Gold': '#E8B83A'})   # '<Part>__<Look>' objects, triangulated
    kit.render(out_dir, 'clay', clay=True)    # front, right, back and three-quarter views beside the reference
    print(kit.gaps(rig, pieces))              # {}, or the sides a wrap leaves bare (references/rigs.md, Skins)
    kit.render(out_dir, 'apart', views=kit.INNER, apart=1.5, res=(900, 900))   # those sides, limbs pulled clear
    # Geometry QA with the replica body before UVs/textures (references/rigs.md, step 4).
    # Anime-ink skin fallback, only when selected by SKILL.md's style precedence; 1024x1024 PBR after the clay check:
    kit.sharpen(pieces)                       # crisp rims: a plate shaded smooth looks inflated
    skins, glow = kit.merge(pieces, emissive={'Glow'})   # one '<Part>__Skin' per body part; glow stays Neon
    for region, obs in kit.regions(skins).items():   # a 1024 map for each of head, torso, arms and legs
        kit.unwrap(obs)                       # one texel density, hollow islands split, hidden faces given little of it
        maps = kit.paint(obs, LOOKS, out_dir, f'MyStand_R6_{region}', strokes=P.strokes)
        kit.preview(obs, maps)
    kit.render(out_dir, 'paint', pbr=True)
    # A realistic material instead, when selected: maps = kit.bake(skins, PBR, out_dir, 'MyStand_R6').
    # Final geometry + UV QA before export, then verify the FBX by re-importing.
    rr.export_pieces(skins + glow, fbx_path)  # then RigSkin.apply(rig, skin, { looks = ... }) in Studio
    # A weapon or shield is its own model, built the same way in its own scene: references/rigs.md, Gear. A held one:
    print(kit.grip_fit(gear_pieces))          # {}, or what stops a hand holding it

LOOKS (kit.paint): {look: {'base': '#rrggbb', 'shade': '#rrggbb' (its shadow tone), 'light': '#rrggbb' (highlights and lit edges;
default a tint of base), 'rough': 0..1 (0.7), 'metal': 0..1 (0: painted metal reads flat, and bright sky washes out a full 1),
'gloss': 0..1 (the highlight's strength, 0.5), 'edge': 0..1 (lit edges, 0.25), 'pleat': 0..1 (soft
streaks in the shadow shape, for cloth, read by 'folds' flow: 'drape' falls, 'wrinkle' crosses), 'line': studs (the ink's
width, 0.022; less on small ornaments), 'folds': {'n': fans per square stud, 'flow': 'drape' (from the top) | 'wrinkle' (from both
ends, sideways), 'fan': strokes in a fan (4), 'spread', 'gather', 'len': (lo, hi) studs, 'width': studs} for cloth, leather and
hair, 'tone': '#rrggbb' (default a deep tone of its shade, never black)}}. kit.DRAPE and kit.WRINKLE are sparse specs to start from;
dense fans of strokes clump into marks that read as claw scratches, so leave 'folds' off small pieces, hair and a chest, and
off the whole look when the reference is clean. Ink follows sharp edges, open edges and the borders between looks; folds are traced
over the surface. Pieces.ink adds a stroke of your own (muscle, stitching, a seam the mesh does not have, a crease placed by
hand). Metal stays free of scratches: its detail is panel lines.

PBR: {look: {'base': '#rrggbb', 'metal': 0 or 1, 'rough': 0..1, 'rough_var': 0.08, 'edge': '#rrggbb' or None (worn
edges), 'edge_amount': 0.5, 'grime': 0.35 (AO multiply), 'bump': 0.05 (fine surface relief), 'brushed': bool}}. bake()
builds a procedural Cycles material per look (edge wear from a bevel-vs-true-normal mask, grime from AO, roughness noise,
bevelled normals) and bakes NORMAL, ROUGHNESS and, through an emission, the albedo and metalness (Cycles' diffuse colour
is black on metal). An R6 skin baked in about 45 s on CPU.

Space as roblox_rig: the ground at 0, facing -Y, the character's left at +X, 1 unit = 1 stud. Every shape returns a
bmesh in world space; Pieces.put merges it into the object for its body part and look (one MeshPart each in Roblox,
styled by RigSkin's `looks`). Leave 0.03 studs between faces that look the same way (references/modeling.md).

layout(dump, rig) -> {
  'head':  {'part', 'c' (centre), 'r' (radius), 'h' (half height)},
  'torso': {'lo', 'hi', 'waist', 'chest', 'hip'}                        R15: UpperTorso x/y, LowerTorso bottom
  'arms':  {'Left'|'Right': {'lo', 'hi', 'out', 'inner', 'elbow', 'wrist', 'upper', 'lower', 'hand'}}
  'legs':  {'Left'|'Right': {'lo', 'hi', 'out', 'inner', 'hip', 'knee', 'ankle', 'upper', 'lower', 'foot'}}}
lo/hi are box corners (Vectors); joint heights come from the dump's pivots on R15, and on R6 (one part per limb) sit at
the elbow/knee 1 stud above the limb's bottom, the wrist 0.3, the ankle 0.32 and the waist 0.45 above the torso's
bottom. `out` is +1 on the left (+X), -1 on the right; `inner` is the side that touches the torso or the other leg at
rest, for wrap's tuck; upper/lower/hand (foot) name the body part that owns each segment (all the same part on R6). A generated R15's
upper leg box runs 0.2 studs above its joint, into the lower torso, so scale a design from a leg's 'hip', never its 'hi'.
owner(seg, z) picks the part for a height; sections(seg) gives [(part, z low, z high)] cut at the joints, for Pieces.cut.

Shapes: box(lo, hi, b) bevelled; wrap(lo, hi, thick, gap, open_side, corner, flare, inset, tuck) walls around a limb or
the torso, closed by tuck on a side that touches a neighbour at rest, open only where the design is; revolve(center,
prof, sides, sx, sy, keep, n, tilt) a surface of revolution (n > 2: a squircle that hugs a box; keep(angle, z, x, y) drops faces); shell(t, thick, outward) gives an
open surface thickness; prism(outline, origin, u, v, n, d0, d1) an extruded outline; cyl(center, axis, r, d0, d1);
text(body, height, depth, origin, u, v, n, d0, shear, font) extruded lettering; head_profile(r, h, off, zmin) the
classic head's outline grown by `off`, for a helmet that hugs it. Hair(L['head'], rise, side, back, front) the hair's
volume, with cap(), lock(), hang(), bangs(), layer() and spike(), or shell() for a style drawn as one sheet (references/rigs.md, Hair):
    H = kit.Hair(L['head']); c, h = L['head']['c'], L['head']['h']
    for t in [H.cap(), *H.bangs(n=4, part=-20), *H.layer(95, 265, 9, c.z + 1.2 * h, c.z - 2 * h, drift=.1)]:
        P.put('Head', 'Hair', t, True)

Surfaces, for armor that follows a body with trims and plates lying on it. Form(x, y, rows) is a stack of rounded rectangles and
form.S(s, z, off) -> (point, normal) a place on it (s along the outline from the front centre, -s mirrors):
    coat = kit.Form(0, 0, [(z0, w0, d0, r0), (z1, w1, d1, r1)])
    t = kit.band(coat, coat.around(front=8), hi, hem, rows=10)       # hi(s) and hem(s) heights, for a V hem or teeth
    P.cut(kit.sections(L['torso']), 'Red', t, .025)                  # cut at the joints while open, then thickness
    P.put(L['torso']['chest'], 'Gold', kit.ribbon(coat.S, [(s, z), ...], .02), False)    # trim; plate() and gem() likewise
band, ledged and stack make the surface; lid closes an end; lifted(S, d) and plane(o, u, v, n) make surfaces to lay on; blade() is a
tapered claw, fin or feather; split_at cuts a strip's path at the waist. Leave 0.03 between visible faces, and keep hidden ones
from landing on each other: a shell's thickness never equal to its gap, each overlapping plate its own `base`.

Checks: folds(objs) where a mesh overlaps itself in one plane, which both rr exports refuse; gaps(rig, pieces, open_sides,
reach, rows, across) the sides a wrap leaves bare; pokes(rig, pieces) box corners through a rounded wrap; coplanar(objs) faces lying
on each other, with positions; hair_check(head, obs, leave)
what makes hair read as a helmet or a comb; render(..., views=INNER,
apart=1.5) shows them; clips(ob, others, pad) whether a mesh cuts into others, for gear on armor; clear_of(place, ob, others,
start, stop, step, pad) the first placement that does not; grip_fit(obs, fist, handle, clear) what stops a hand holding a
weapon, with fist(arm, pieces) measuring a bulky glove (references/rigs.md, Gear)."""
import json
import math
import os
import random
import shutil
import subprocess
import bmesh
import bpy
from bpy_extras import bmesh_utils
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree
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
                          'hip': piv[side + 'UpperLeg'].z, 'ankle': piv[side + 'Foot'].z, 'upper': side + 'UpperLeg', 'lower': side + 'LowerLeg', 'foot': side + 'Foot'}
        else:
            a, l_ = _box_of(dump, side + ' Arm'), _box_of(dump, side + ' Leg')
            arms[side] = {'lo': a[0], 'hi': a[1], 'elbow': a[0].z + 1.0, 'wrist': a[0].z + 0.3,
                          'upper': side + ' Arm', 'lower': side + ' Arm', 'hand': side + ' Arm'}
            legs[side] = {'lo': l_[0], 'hi': l_[1], 'hip': l_[1].z, 'knee': l_[0].z + 1.0, 'ankle': l_[0].z + 0.32,
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


def sections(seg):
    """[(part, z low, z high)] of an arm, leg or torso layout entry, cut at its joints; one entry on R6, where a limb is one part."""
    if 'waist' in seg:
        return [(seg['chest'], -99, 99)] if seg['chest'] == seg['hip'] else [(seg['chest'], seg['waist'], 99), (seg['hip'], -99, seg['waist'])]
    a, b, end = ('elbow', 'wrist', 'hand') if 'elbow' in seg else ('knee', 'ankle', 'foot')
    if seg['upper'] == seg[end]:
        return [(seg['upper'], -99, 99)]
    return [(seg['upper'], seg[a], 99), (seg['lower'], seg[b], seg[a]), (seg[end], -99, seg[b])]


class Pieces:
    """Geometry gathered per (body part, look); objects() makes one '<Part>__<Look>' object for each."""

    def __init__(self):
        self.acc = {}
        self.strokes = []

    def ink(self, part, points, width=.03):
        """A hand-placed ink stroke, for kit.paint: points on or just off the surface of `part`'s skin."""
        self.strokes.append((part, [Vector(p) for p in points], width))

    def put(self, part, look, t, smooth=False):
        """Gather bmesh t (freed); weld within this input only, never between separate ornaments.
        smooth=None keeps its faces' own shading."""
        bmesh.ops.remove_doubles(t, verts=t.verts[:], dist=1e-5)
        if smooth is not None:
            for f in t.faces:
                f.smooth = smooth
        me = bpy.data.meshes.new('tmp'); t.to_mesh(me); t.free()
        acc = self.acc.setdefault((part, look), bmesh.new()); acc.from_mesh(me); bpy.data.meshes.remove(me)

    def cut(self, secs, look, t, thick, smooth=True, out=False):
        """Thickness on open surface t (freed), one piece per section [(part, z low, z high)]. Rims stop a hair short of each joint: two cut
        in one plane would lie on each other."""
        for part, lo, hi in secs:
            c = clip(t.copy(), lo + .002, hi - .002)
            if c.faces:
                self.put(part, look, shell(c, thick, outward=out), smooth)
            else:
                c.free()
        t.free()

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


def wrap(lo, hi, thick, gap=0.02, open_side=None, corner=0.05, flare=0.0, inset=0.04, tuck=None):
    """Walls around a limb or the torso (x/y of lo..hi, z from lo.z to hi.z), `gap` clear of it and `thick` thick.
    tuck '+x', '-x' or 'x' (both) closes a side that touches a neighbour at rest (a limb's `inner`, the torso's 'x'): that
    wall stands `gap` clear with its thickness run back into the limb. It may clip the neighbour (the limb is moving
    when that side shows); tucking is for the rest pose, where a full wall would lie in the same plane as the
    neighbour's and flicker. Wraps tucked against each other (the legs) keep corner above gap, so they curve apart at
    the seam.
    open_side (the same values) leaves those walls out, only for a side the design leaves open (references/rigs.md,
    Skins); the remaining walls end `inset` inside the body. flare widens the bottom by that much, and the x sides only
    where neither applies."""
    lo, hi = Vector(lo), Vector(hi)
    a, b = lo - Vector((gap, gap, 0)), hi + Vector((gap, gap, 0))
    if open_side in ('-x', 'x'):
        a.x = lo.x + inset
    if open_side in ('+x', 'x'):
        b.x = hi.x - inset
    if tuck in ('-x', 'x'):  # its back stays off the plane the limb shares with the neighbour, where it would flicker
        a.x = lo.x - .02 if abs(a.x + thick - lo.x) < .02 else a.x + thick
    if tuck in ('+x', 'x'):
        b.x = hi.x + .02 if abs(b.x - thick - hi.x) < .02 else b.x - thick
    if tuck:  # the ring now crosses the neighbour's outline, so it stops short of the end an R6 arm shares with the torso
        a.z += .01; b.z -= .01
    t = _cube(a, b)
    dels = [f for f in t.faces if abs(f.normal.z) > .5]
    if open_side:
        s = {'+x': 1, '-x': -1, 'x': 0}[open_side]
        dels += [f for f in t.faces if (f.normal.x * s > .5 if s else abs(f.normal.x) > .5)]
    bmesh.ops.delete(t, geom=dels, context='FACES')
    if flare:
        c = (a + b) / 2; held = open_side or tuck
        for v in t.verts:
            if v.co.z < c.z:
                v.co.y = c.y + (v.co.y - c.y) * (1 + flare / ((b.y - a.y) / 2))
                if not held or (held == '-x' and v.co.x > c.x) or (held == '+x' and v.co.x < c.x):
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


# ---------------------------------------------------------------- surfaces that armor, trims and plates lie on


class Hoop:
    """A rounded rectangle, half sizes w and d, corner radius r. at(s) -> (point, outward normal), s from the front centre."""

    def __init__(self, w, d, r):
        r = min(r, w * .98, d * .98)
        self.w, self.d, self.r = w, d, r
        self.fw, self.fd = w - r, d - r
        arc = r * math.pi / 2
        self.legs = [self.fw, arc, 2 * self.fd, arc, 2 * self.fw, arc, 2 * self.fd, arc, self.fw]
        self.L = sum(self.legs)

    def at(self, s):
        s %= self.L
        for i, length in enumerate(self.legs):
            if s <= length or i == 8:
                break
            s -= length
        w, d, r, fw, fd = self.w, self.d, self.r, self.fw, self.fd
        a = s / r
        ca, sa = math.cos(a), math.sin(a)
        return {0: (Vector((s, -d, 0)), Vector((0, -1, 0))),
                1: (Vector((fw + r * sa, -fd - r * ca, 0)), Vector((sa, -ca, 0))),
                2: (Vector((w, -fd + s, 0)), Vector((1, 0, 0))),
                3: (Vector((fw + r * ca, fd + r * sa, 0)), Vector((ca, sa, 0))),
                4: (Vector((fw - s, d, 0)), Vector((0, 1, 0))),
                5: (Vector((-fw - r * sa, fd + r * ca, 0)), Vector((-sa, ca, 0))),
                6: (Vector((-w, fd - s, 0)), Vector((-1, 0, 0))),
                7: (Vector((-fw - r * ca, -fd - r * sa, 0)), Vector((-ca, -sa, 0))),
                8: (Vector((-fw + s, -d, 0)), Vector((0, -1, 0)))}[i]


class Form:
    """A stack of Hoops around a vertical axis at (x, y): rows [(z, w, d, r)], any order. S(s, z, off) -> (point, normal) is a place on
    it, s in studs along the outline from the front centre, positive toward +X, so -s mirrors; form.L is the outline's length, so
    L / 4 is the +X side and L / 2 the back. bulge(x, z, hoop) pushes the front out."""

    def __init__(self, x, y, rows, bulge=None):
        self.o = Vector((x, y, 0))
        self.rows = sorted(rows)
        self.ref = Hoop(*self.rows[len(self.rows) // 2][1:])
        self.L = self.ref.L
        self.bulge = bulge

    def hoop(self, z):
        r = self.rows
        if z <= r[0][0]:
            return Hoop(*r[0][1:])
        if z >= r[-1][0]:
            return Hoop(*r[-1][1:])
        for a, b in zip(r, r[1:]):
            if z <= b[0]:
                u = (z - a[0]) / (b[0] - a[0])
                return Hoop(*[p + (q - p) * u for p, q in zip(a[1:], b[1:])])

    def S(self, s, z, off=0.0):
        h = self.hoop(z)
        p, n = h.at(s * h.L / self.L)
        if self.bulge and p.y < 0:
            p = p - Vector((0, self.bulge(p.x, z, h), 0))
        q = self.o + p + n * off
        q.z = z
        return q, n

    def around(self, front=4, side=2, corner=3):
        """Places s around the whole form, closed: flats need few, corners keep their curve."""
        h = self.ref
        arc = h.legs[1]
        out, s = [], 0.0
        for length, m in ((h.fw, front), (arc, corner), (2 * h.fd, side), (arc, corner), (2 * h.fw, 2 * front),
                          (arc, corner), (2 * h.fd, side), (arc, corner), (h.fw, front)):
            out += [s + length * i / m for i in range(m)]
            s += length
        return out


def lifted(S, d):
    """Surface S raised by d, for something that sits on something already on S."""
    return lambda s, z, off=0.0: S(s, z, off + d)


def plane(o, u, v, n):
    """A flat surface for plates, S(a, c, off)."""
    return lambda a, c, off=0.0: (o + u * a + v * c + n * off, n)


def grid_mesh(rows, closed=True):
    """A quad surface through rows of points, all the same length."""
    t = bmesh.new()
    vs = [[t.verts.new(p) for p in row] for row in rows]
    n = len(rows[0])
    for A, B in zip(vs, vs[1:]):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            t.faces.new((A[i], A[j], B[j], B[i]))
    return t


def outward(t, axis):
    """Faces an open surface away from a vertical axis through `axis`."""
    t.normal_update()
    score = 0.0
    for f in t.faces:
        d = f.calc_center_median() - axis
        d.z = 0
        score += f.normal.dot(d) * f.calc_area()
    if score < 0:
        bmesh.ops.reverse_faces(t, faces=t.faces[:])
        t.normal_update()
    return t


def band(form, ss, hi, lo, rows=2, off=0.0, closed=True):
    """The surface between heights hi(s) and lo(s) at places ss, for a hem or a tooth that varies around the form. off is a number, or
    off(v) with v 0 at hi and 1 at lo."""
    grid = []
    for j in range(rows):
        v = j / (rows - 1)
        o = off(v) if callable(off) else off
        grid.append([form.S(s, hi(s) + (lo(s) - hi(s)) * v, o)[0] for s in ss])
    return outward(grid_mesh(grid, closed), form.o)


def ledged(form, ss, hi, lo, lip=.02, closed=True):
    """A band with its top and bottom rims turned in: a hoop or plate with a chamfered edge."""
    grid = [[form.S(s, hi(s), -lip)[0] for s in ss], [form.S(s, hi(s) - lip)[0] for s in ss],
            [form.S(s, lo(s) + lip)[0] for s in ss], [form.S(s, lo(s), -lip)[0] for s in ss]]
    return outward(grid_mesh(grid, closed), form.o)


def stack(form, ss):
    """A closed surface with one row at each of the form's own hoops, so its kinks land where they were designed."""
    grid = [[form.S(s, row[0])[0] for s in ss] for row in reversed(form.rows)]
    return outward(grid_mesh(grid), form.o)


def lid(t, low=True):
    """Closes a surface's open end, for the crown of a dome or the sole of a boot."""
    edges = [e for e in t.edges if e.is_boundary]
    z = (min if low else max)(v.co.z for e in edges for v in e.verts)
    bmesh.ops.holes_fill(t, edges=[e for e in edges if all(abs(v.co.z - z) < 1e-4 for v in e.verts)], sides=0)
    t.normal_update()
    return t


def clip(t, lo, hi):
    """Keeps z between lo and hi of an open surface, adding no lids."""
    for z, n in ((lo, (0, 0, 1)), (hi, (0, 0, -1))):
        if abs(z) < 90:
            bmesh.ops.bisect_plane(t, geom=t.verts[:] + t.edges[:] + t.faces[:], plane_co=(0, 0, z), plane_no=n, clear_inner=True, dist=1e-6)
    return t


def ribbon(S, path, w, h=.03, base=-.012, seg=.08, flat_ends=False):
    """A closed raised strip along polyline `path` [(s, z)] on surface S: trim, piping, a seam. w is its half width, a number or one per
    path point; corners are mitred. flat_ends squares the ends to vertical and keeps the strip on its own side of them, for two
    halves that meet on the centre line. A strip right round a form stops just short of its own start, or its ends fuse."""
    ws = list(w) if isinstance(w, (list, tuple)) else [w] * len(path)
    pts, wid = [], []
    for i in range(len(path) - 1):
        a, b = Vector(path[i]), Vector(path[i + 1])
        n = max(1, math.ceil((b - a).length / seg))
        for k in range(n):
            pts.append(a.lerp(b, k / n))
            wid.append(ws[i] + (ws[i + 1] - ws[i]) * k / n)
    pts.append(Vector(path[-1]))
    wid.append(ws[-1])
    rings = []
    last = len(pts) - 1
    lo_s, hi_s = min(p[0] for p in path), max(p[0] for p in path)
    for i, q in enumerate(pts):
        d0 = (q - pts[i - 1]).normalized() if i else (pts[1] - q).normalized()
        d1 = (pts[i + 1] - q).normalized() if i < last else d0
        d = d0 + d1
        d = d.normalized() if d.length > 1e-6 else d0
        perp = Vector((-d.y, d.x))
        mitre = 1 / max(.45, perp.dot(Vector((-d0.y, d0.x))))
        if flat_ends and i in (0, last):
            # Keeps its side: flipped, the end ring twists against the next on a mirrored strip. No taller than that ring, or the rail
            # doubles back along the centre line.
            perp, mitre = Vector((0, 1 if perp.y >= 0 else -1)), 1.0
        ring = []
        for a, up in ((-1, base), (-.8, h), (.8, h), (1, base)):
            e = q + perp * (wid[i] * a * mitre)
            ring.append(S(max(lo_s, min(hi_s, e.x)) if flat_ends else e.x, e.y, up)[0])
        rings.append(ring)
    t = bmesh.new()
    vs = [[t.verts.new(p) for p in r] for r in rings]
    for A, B in zip(vs, vs[1:]):
        for k in range(4):
            j = (k + 1) % 4
            t.faces.new((A[k], A[j], B[j], B[k]))
    t.faces.new(vs[0])
    t.faces.new(list(reversed(vs[-1])))
    bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
    return t


def _fine(outline, seg):
    out = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        a, b = Vector(a), Vector(b)
        n = max(1, math.ceil((b - a).length / seg))
        out += [a.lerp(b, k / n) for k in range(n)]
    return out


def plate(S, outline, h=.03, base=-.012, rim=.014, rings=1, seg=.14, c=None):
    """A closed plate on surface S: an outline [(s, z)] every point of which sees `c` (by default its centre), its rim turned down to
    `base`, its face at `h`. rings adds circles of vertices, so a wide plate follows a curved surface. Overlapping plates each take
    their own `base`, since undersides at one depth lie on each other."""
    edge = _fine(outline, seg)
    centre = Vector(c) if c else sum((Vector(p) for p in outline), Vector((0, 0))) / len(outline)
    reach = sum((p - centre).length for p in edge) / len(edge)
    k = min(.5, rim / max(reach, 1e-6))
    t = bmesh.new()
    low = [t.verts.new(S(p.x, p.y, base)[0]) for p in edge]
    loops = [low]
    for i in range(rings + 1):
        f = k + (1 - k) * .7 * i / max(1, rings) if rings else k
        loops.append([t.verts.new(S(*(p.lerp(centre, f)), h)[0]) for p in edge])
    n = len(edge)
    for A, B in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            t.faces.new((A[i], A[j], B[j], B[i]))
    top, under = t.verts.new(S(centre.x, centre.y, h)[0]), t.verts.new(S(centre.x, centre.y, base)[0])
    for i in range(n):
        j = (i + 1) % n
        t.faces.new((loops[-1][i], loops[-1][j], top))
        t.faces.new((low[j], low[i], under))
    bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
    return t


def gem(S, s, z, rx, rz=None, n=4, h=.05, base=-.012, spin=0.0):
    """A small n-sided stud or lozenge on S."""
    rz = rz or rx
    outline = [(s + rx * math.cos(spin + math.tau * i / n), z + rz * math.sin(spin + math.tau * i / n)) for i in range(n)]
    return plate(S, outline, h=h, base=base, rim=min(rx, rz) * .3, rings=0)


def blade(points, widths, up, thick=.3, steps=8, ridge=.6):
    """A closed tapered blade through 3D `points`, for claws, fins, feathers and swords: half widths [per point], a width of 0 a true point.
    Its thickness lies along up(p), a diamond section whose ridge stands outward. Two blades can share a path, a sleeve of one
    look over the other, for a silver claw with a gold tip."""
    n = len(points) - 1
    path = _spline(points, steps)
    t = bmesh.new()
    rings = []
    for i, p in enumerate(path):
        q = i * n / (steps - 1)
        j = min(int(q), n - 1)
        w = widths[j] + (widths[j + 1] - widths[j]) * (q - j)
        d = (path[min(i + 1, steps - 1)] - path[max(i - 1, 0)]).normalized()
        u = up(p)
        b = d.cross(u).normalized()
        u = b.cross(d).normalized()
        if w < 1e-4:
            rings.append([t.verts.new(p)])
            continue
        th = w * thick * 2
        rings.append([t.verts.new(p + b * x + u * y) for x, y in ((w, 0), (0, th * ridge), (-w, 0), (0, -th * (1 - ridge)))])
    for A, B in zip(rings, rings[1:]):
        m = max(len(A), len(B))
        for k in range(m):
            if len(A) == 1:
                t.faces.new((A[0], B[k], B[(k + 1) % m]))
            elif len(B) == 1:
                t.faces.new((A[k], A[(k + 1) % m], B[0]))
            else:
                t.faces.new((A[k], A[(k + 1) % m], B[(k + 1) % m], B[k]))
    if len(rings[0]) > 1:
        t.faces.new(rings[0])
    if len(rings[-1]) > 1:
        t.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
    return t


def split_at(path, z):
    """Polyline [(s, z)] cut where it crosses height z, (the stretch above, the stretch below): a strip that spans the waist."""
    above, below = [], []
    for a, b in zip(path, path[1:]):
        (above if a[1] >= z else below).append(a)
        if (a[1] - z) * (b[1] - z) < 0:
            u = (z - a[1]) / (b[1] - a[1])
            q = (a[0] + (b[0] - a[0]) * u, z)
            above.append(q)
            below.append(q)
    (above if path[-1][1] >= z else below).append(path[-1])
    return above, below


def tris(objects):
    """{object name: triangles}."""
    return {ob.name: sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in objects}


VIEWS = {'front': (0, -1, 0), 'right': (-1, 0, 0), 'back': (0, 1, 0), 'threeq': (0.62, -1, 0.18)}
INNER = {'inner_left': (-0.8, -1, -0.2), 'inner_right': (0.8, -1, -0.2)}  # each side's limbs from the torso, a little low


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


def _out(ob):
    """+1 for a left limb's replica box or welded piece, -1 for a right one's, 0 for anything else."""
    part = ob.get('roblox_part', ob.name)
    return 1 if part.startswith('Left') else -1 if part.startswith('Right') else 0


def render(out_dir, tag, clay=False, views=VIEWS, res=(520, 800), pbr=False, samples=32, apart=0.0):
    """Stills of every visible object (the replica body and the skin) from `views` (name: direction from the character
    to the camera; orthographic, the three-quarter view perspective), saved as <out_dir>/<tag>_<view>.png. Workbench by
    default (clay=True: one gray, for the clay check); pbr=True renders the baked maps in Cycles under a sky and a sun.
    apart pulls the limbs that many studs out along X for the renders, baring the sides the rest pose hides (welded
    pieces; a skinned mesh stays put, so pose its armature instead).
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
    pts = [ob.matrix_world @ Vector(c) for ob in sc.objects if ob.type == 'MESH' and not ob.hide_render for c in ob.bound_box]
    lo, hi = (Vector([f(p[i] for p in pts) for i in range(3)]) for f in (min, max))
    # Framed on what is there, its longest side: a weapon lies along Y around its own origin, not up from the ground.
    top = max(hi - lo)
    cam_d = bpy.data.cameras.new('kit_cam'); cam = bpy.data.objects.new('kit_cam', cam_d)
    sc.collection.objects.link(cam); sc.camera = cam
    mid = (lo + hi) / 2
    limbs = [ob for ob in sc.objects if ob.type == 'MESH' and _out(ob)]
    for ob in limbs:
        ob.location.x += _out(ob) * apart
    paths = []
    for name, d in views.items():
        d = Vector(d).normalized()
        if name == 'threeq':
            cam_d.type, cam_d.lens = 'PERSP', 50
            cam.location = mid + d * top * 1.75
        else:
            cam_d.type, cam_d.ortho_scale = 'ORTHO', (top + 2 * apart) * 1.12
            cam.location = mid + d * 20
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out_dir, f'{tag}_{name}.png')
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    for ob in limbs:
        ob.location.x -= _out(ob) * apart
    bpy.data.objects.remove(cam); bpy.data.cameras.remove(cam_d)
    return paths


def gaps(rig, pieces, open_sides=None, reach=0.5, rows=16, across=5):
    """The sides a skin leaves bare around a part it wraps, as {part: {side: (z0, z1)}}, side '-x', '+x', '-y' (front) or
    '+y'; {} when every wrap closes. Rays from each side of the part's replica box look for that part's own pieces,
    `reach` studs out (a neighbour's pieces leave when the joint swings). A height wraps where they cover the front and
    back, or three sides, and any other side there is bare (two rows at least: a single one is a piece's edge). A
    one-sided piece (a wing, a plate) wraps nothing, so it passes. open_sides {part: side, or 'x' for both} lists sides
    the design leaves open (references/rigs.md, Skins). Welded pieces only; the head is skipped, since nothing touches
    its sides."""
    verts, polys = {}, {}
    for ob in pieces:
        part = ob.name.split('__')[0]
        vs, ps = verts.setdefault(part, []), polys.setdefault(part, [])
        ps += [[len(vs) + i for i in p.vertices] for p in ob.data.polygons]
        vs += [ob.matrix_world @ v.co for v in ob.data.vertices]
    sides = {'-x': -X, '+x': X, '-y': -Y, '+y': Y}
    open_sides, found = open_sides or {}, {}
    for part, box in rig['boxes'].items():
        if part not in verts or part == 'Head':
            continue
        tree = BVHTree.FromPolygons(verts[part], polys[part])
        pts = [box.matrix_world @ Vector(c) for c in box.bound_box]
        lo, hi = (Vector([f(p[i] for p in pts) for i in range(3)]) for f in (min, max))

        def covered(n, z):
            hits = 0
            for j in range(across):
                f = (j + .5) / across
                x = hi.x if n.x > 0 else lo.x if n.x < 0 else lo.x + f * (hi.x - lo.x)
                y = hi.y if n.y > 0 else lo.y if n.y < 0 else lo.y + f * (hi.y - lo.y)
                hits += tree.ray_cast(Vector((x, y, z)), n, reach)[0] is not None
            return hits >= across * .6
        for k in range(rows):
            z = round(lo.z + (k + .5) / rows * (hi.z - lo.z), 2)
            on = {s for s, n in sides.items() if covered(n, z)}
            if len(on) >= 3 or {'-y', '+y'} <= on:
                for s in sides.keys() - on:
                    if open_sides.get(part) not in (s, s[1]):
                        found.setdefault(part, {}).setdefault(s, []).append(z)
    bare = {p: {s: (zs[0], zs[-1]) for s, zs in v.items() if len(zs) > 1} for p, v in found.items()}
    return {p: v for p, v in bare.items() if v}


def pokes(rig, pieces, rows=16):
    """Where a corner of a body part's box stands out through the wrap around it, as {part: (z0, z1)}; {} when none does. A rounded wrap
    clears the box only if w - 0.293 * r is more than the box's half size: past that the body shows as a hairline down each corner,
    which gaps cannot see, since all four sides are covered. A corner a neighbour's piece covers at rest still counts."""
    verts, polys = {}, {}
    for ob in pieces:
        part = ob.name.split('__')[0]
        vs, ps = verts.setdefault(part, []), polys.setdefault(part, [])
        ps += [[len(vs) + i for i in p.vertices] for p in ob.data.polygons]
        vs += [ob.matrix_world @ v.co for v in ob.data.vertices]
    found = {}
    for part, box in rig['boxes'].items():
        if part not in verts or part == 'Head':
            continue
        tree = BVHTree.FromPolygons(verts[part], polys[part])
        pts = [box.matrix_world @ Vector(c) for c in box.bound_box]
        lo, hi = (Vector([f(p[i] for p in pts) for i in range(3)]) for f in (min, max))
        mid = (lo + hi) / 2
        for k in range(rows):
            z = round(lo.z + (k + .5) / rows * (hi.z - lo.z), 2)
            centre = Vector((mid.x, mid.y, z))
            if sum(tree.ray_cast(centre, d, 2.0)[0] is not None for d in (X, -X, Y, -Y)) < 3:
                continue
            for sx in (-1, 1):
                for sy in (-1, 1):
                    corner = Vector((hi.x if sx > 0 else lo.x, hi.y if sy > 0 else lo.y, z))
                    if tree.ray_cast(corner, Vector((sx, sy, 0)).normalized(), 1.0)[0] is None:
                        found.setdefault(part, []).append(z)
    return {p: (min(zs), max(zs)) for p, zs in found.items() if len(set(zs)) > 1}


def coplanar(objs, eps=.001):
    """Faces that look the same way, lie within eps of each other and overlap, as {(object, object): (pairs, low corner, high corner)}; {}
    when none do. The test blender-asset-qa runs for z-fighting, with the positions it leaves out. objs are checked against every
    mesh in the scene, so keep the replica body in it; a replica part against a replica part is left out, since its joints overlap
    by design, and so are a piece's own triangles that share a vertex. Hidden faces count: cut rims, a shell's inner face on the
    body's, plate undersides at one depth."""
    bpy.context.view_layer.update()
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render and o.name != 'RIG_HumanoidRootPart']
    obs += [o for o in objs if o not in obs]
    names, verts, tris_, normals = [], [], [], []
    for ob in obs:
        t = bmesh.new()
        t.from_mesh(ob.data)
        t.transform(ob.matrix_world)
        bmesh.ops.triangulate(t, faces=t.faces[:])
        t.normal_update()
        base = len(verts)
        verts += [v.co.copy() for v in t.verts]
        for f in t.faces:
            tris_.append([base + v.index for v in f.verts])
            normals.append(f.normal.copy())
            names.append(ob.name)
        t.free()
    tree = BVHTree.FromPolygons(verts, tris_, epsilon=0.0)
    shared = [set(x) for x in tris_]
    wanted = {o.name for o in objs}
    found = {}

    def inside(q, a, b, c, n):
        return (b - a).cross(q - a).dot(n) >= 0 and (c - b).cross(q - b).dot(n) >= 0 and (a - c).cross(q - c).dot(n) >= 0
    for i, tri in enumerate(tris_):
        n = normals[i]
        if n.length < .5:
            continue
        a, b, c = (verts[v] for v in tri)
        middle = (a + b + c) / 3
        for p in (middle, middle.lerp(a, .6), middle.lerp(b, .6), middle.lerp(c, .6)):
            for _, _, j, _ in tree.find_nearest_range(p, eps):
                if j is None or j == i or shared[i] & shared[j] or n.dot(normals[j]) < .999:
                    continue
                key = tuple(sorted((names[i], names[j])))
                if not wanted & set(key) or (key[0].startswith('RIG_') and key[1].startswith('RIG_')):
                    continue
                a2, b2, c2 = (verts[v] for v in tris_[j])
                m = normals[j]
                if inside(p - m * m.dot(p - a2), a2, b2, c2, m):
                    found.setdefault(key, []).append(p.copy())
    return {k: (len(v), tuple(round(min(p[i] for p in v), 2) for i in range(3)), tuple(round(max(p[i] for p in v), 2) for i in range(3))) for k, v in found.items()}


def clips(ob, others, pad=0.0):
    """True when mesh `ob` cuts into any of `others`, or comes within `pad` studs of one. For rigid gear against armor, where a
    render from the front hides it (a gauntlet showing through a shield's face)."""
    def tree(o, eps=0.0):
        return BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [p.vertices for p in o.data.polygons], epsilon=eps)

    def inside(t, o):
        """Whether a point of `o` lies within closed mesh t, by counting crossings; surfaces that never cross miss this case."""
        at, crossed = o.matrix_world @ o.data.vertices[0].co, 0
        while True:
            hit = t.ray_cast(at, Z, 200.0)[0]
            if hit is None:
                return crossed % 2 == 1
            crossed += 1
            at = hit + Z * 1e-4
    def near(t, o):
        """Whether a vertex of `o` is within pad of t. BVHTree.overlap only finds real crossings, whatever its epsilon."""
        return pad > 0 and any(t.find_nearest(o.matrix_world @ v.co, pad)[0] is not None for v in o.data.vertices)
    mine = tree(ob)
    for o in others:
        theirs = tree(o)
        if mine.overlap(theirs) or inside(theirs, ob) or inside(mine, o) or near(theirs, ob) or near(mine, o):
            return True
    return False


def clear_of(place, ob, others, start=0.0, stop=1.0, step=0.02, pad=0.05):
    """The smallest d in start..stop where `ob`, after place(ob, d), does not clip `others`. Raises when none does."""
    d = start
    while d <= stop + 1e-6:
        place(ob, d)
        bpy.context.view_layer.update()
        if not clips(ob, others, pad):
            return d
        d += step
    raise ValueError(f'{ob.name} still clips at {stop}')


# A held weapon against a Roblox hand: a block about a stud deep, which a handle passes through. In studs, from the weapon's
# origin, the middle of the handle on its axis (references/rigs.md, Gear).
SEAT = 0.16    # from the hand's end up to the handle's axis, as RigSkin.equip seats it
HANDLE = 0.13  # the widest a handle may be and stay inside the fist
FIST = 0.62    # half a fist, along the handle and across it: half a hand and a glove up to 0.1 thick
CLEAR = 0.05   # what the guard and the butt stand clear of the fist


def fist(arm, pieces):
    """Half the fist's size, measured from the pieces on the hand of layout arm `arm`: grip_fit's `fist` for a bulky glove."""
    c = (arm['lo'] + arm['hi']) / 2
    half = max(arm['hi'].x - c.x, arm['hi'].y - c.y)
    lo, hi = Vector((-1e9, -1e9, arm['lo'].z)), Vector((1e9, 1e9, arm['wrist']))
    for ob in pieces:
        if ob.name.split('__')[0] == arm['hand']:
            verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
            for e in ob.data.edges:
                # Edges, not vertices: a coarse glove can have none at the fist's height
                for p in _clip(verts[e.vertices[0]], verts[e.vertices[1]], lo, hi) or ():
                    half = max(half, abs(p.x - c.x), abs(p.y - c.y))
    return half


def _clip(a, b, lo, hi):
    """The stretch of segment a..b inside the box lo..hi, or None."""
    t0, t1 = 0.0, 1.0
    for i in range(3):
        step = b[i] - a[i]
        if abs(step) < 1e-9:
            if not lo[i] <= a[i] <= hi[i]:
                return None
            continue
        enter, leave = sorted(((lo[i] - a[i]) / step, (hi[i] - a[i]) / step))
        t0, t1 = max(t0, enter), min(t1, leave)
        if t0 > t1:
            return None
    return a.lerp(b, t0), a.lerp(b, t1)


def grip_fit(obs, fist=FIST, handle=HANDLE, clear=CLEAR):
    """What stops a hand holding a weapon, {} when nothing does. `obs` are its pieces in its own scene, its origin on the handle's
    axis in the middle of the hand, its length along -Y. Only the handle may enter the fist, from the hand's end up, so a guard,
    blade or pommel there is reported, while a knuckle bow below the hand or a ring around it is not. Keys: 'front' and 'back'
    (what enters the fist on that side), 'butt' (the handle stops inside the fist), 'facing' (it does not run forward)."""
    bpy.context.view_layer.update()
    reach = fist + clear
    lo, hi = Vector((-reach, -reach, -SEAT)), Vector((reach, reach, 2.0))
    near, points = {}, []
    for ob in obs:
        verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        points += verts
        for e in ob.data.edges:
            inside = _clip(verts[e.vertices[0]], verts[e.vertices[1]], lo, hi)
            # The distance from the axis is convex along an edge, so the stretch's ends show its widest.
            for p in inside or ():
                if math.hypot(p.x, p.z) > handle + 1e-3:
                    side = 'front' if p.y < 0 else 'back'
                    near[side] = min(near.get(side, reach), abs(p.y))
    found = {}
    if 'front' in near:
        found['front'] = f"{near['front']:.2f} ahead of the grip, inside the fist: start the guard and blade past {reach:.2f}"
    if 'back' in near:
        found['back'] = f"{near['back']:.2f} behind the grip, inside the fist: start the pommel past {reach:.2f}"
    size = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
    ahead, behind = -min(p.y for p in points), max(p.y for p in points)
    if behind < reach:
        found['butt'] = f'the handle ends {behind:.2f} behind the grip, inside the fist: run it past {reach:.2f}'
    if size[1] < max(size[0], size[2]) or ahead <= behind:
        found['facing'] = f'{ahead:.2f} ahead of the grip and {behind:.2f} behind it, {size[1]:.2f} long: its length runs forward, along -Y'
    return found


# ---------------------------------------------------------------- hair (references/rigs.md, Hair)
# Read from 48 anime hair meshes on the classic head, in studs for a head 1.2 tall: the hair is a dome whose
# top stands 0.42 above the head's (median; at least 0.2), 0.22 off the scalp, 0.33 out behind and 0.14 at the temples.


def _spline(points, steps):
    """Catmull-Rom through points, `steps` samples from the first to the last."""
    p = [Vector(v) for v in points]
    out = []
    for i in range(steps):
        q = i * (len(p) - 1) / (steps - 1)
        j = min(int(q), len(p) - 2); u = q - j
        a, b, c, d = p[max(0, j - 1)], p[j], p[j + 1], p[min(len(p) - 1, j + 2)]
        out.append(.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (3 * b - a - 3 * c + d) * u ** 3))
    return out


class Hair:
    """The hair's volume around layout()'s head: a dome `rise` above the head's top, `side` past its sides at the temples,
    `back` behind it and `front` before the forehead; a straight wall below the head's centre. round_ shapes the dome (2
    is an ellipse; higher is squarer, toward a helmet). Defaults follow the references' medians; with front much under
    0.15 the cap cuts into the head's top corners at the forehead.
    at(lam, z, off) the surface point at angle lam (degrees: 0 the front, -Y; 90 the character's left, +X) and height z,
    off studs out along normal(p); project(p, off) the surface point nearest the axis through p.
    cap(hairline, temple, nape, thick) the shell over the crown, its lower edge at those heights above the head's centre
    (front, at +-70 degrees, back); locks hide that edge. lock(points, width, ...) a flat blade along a path: a flattened
    diamond in cross-section, thickness along the volume's normal, widest `widest` of the way down and pointed at the tip.
    hang(lam, z, tip, ...) a path that hugs the volume down to height `tip`. bangs(...), layer(...) and spike(...) place
    locks; each returns bmeshes for Pieces.put('Head', 'Hair', ...). hair_check() measures the result."""

    def __init__(self, head, rise=0.42, side=0.14, back=0.33, front=0.15, round_=2.3):
        self.c, self.r, self.h = head['c'].copy(), head['r'], head['h']
        k = self.h / 0.6  # the measurements were taken on a head 1.2 tall
        self.rx, self.ryf, self.ryb = self.r + side * k, self.r + front * k, self.r + back * k
        self.top, self.p, self.k = self.h + rise * k, round_, k

    def _s(self, dx, dy):
        return math.hypot(dx / self.rx, dy / (self.ryb if dy > 0 else self.ryf))

    def F(self, p):
        """1 on the surface, below 1 inside; scales with distance from the axis, so project() is exact."""
        s, dz = self._s(p.x - self.c.x, p.y - self.c.y), p.z - self.c.z
        return s if dz <= 0 else (s ** self.p + (dz / self.top) ** self.p) ** (1 / self.p)

    def normal(self, p, e=1e-4):
        g = Vector([self.F(p + d * e) - self.F(p - d * e) for d in (X, Y, Z)])
        return g.normalized() if g.length > 1e-9 else Z.copy()

    def project(self, p, off=0.0):
        p = Vector(p); a = Vector((self.c.x, self.c.y, min(p.z, self.c.z)))
        f = self.F(p)
        q = a + (p - a) / f if f > 1e-9 else Vector((self.c.x, self.c.y, self.c.z + self.top))
        return q + self.normal(q) * off

    def at(self, lam, z, off=0.0):
        a = math.radians(lam); d = Vector((math.sin(a), -math.cos(a), 0))
        dz = max(0.0, z - self.c.z)
        rho = max(0.0, 1 - min(1.0, dz / self.top) ** self.p) ** (1 / self.p) / self._s(d.x, d.y)
        q = Vector((self.c.x, self.c.y, min(z, self.c.z + self.top))) + d * rho
        return q + self.normal(q) * off

    def cap(self, hairline=0.55, temple=0.1, nape=-0.85, thick=0.03, cols=32, rows=8):
        """The shell over the crown down to its lower edge (in head half-heights above the head's centre: the front, at
        +-70 degrees, and the back), thickness inward. Locks cover that edge; hair_check measures what shows."""
        def zb(lam):
            a = abs((lam + 180) % 360 - 180)
            e = hairline + (temple - hairline) * (1 - math.cos(math.pi * a / 70)) / 2 if a < 70 else \
                temple + (nape - temple) * (1 - math.cos(math.pi * (a - 70) / 110)) / 2
            return self.c.z + e * self.h
        ztop = self.c.z + self.top
        t = bmesh.new(); grid = []
        for j in range(cols):
            lam = 360 * j / cols; z0 = zb(lam)
            grid.append([t.verts.new(self.at(lam, z0 + (ztop - z0) * math.sin(math.pi / 2 * i / rows) * .985)) for i in range(rows)])
        pole = t.verts.new(Vector((self.c.x, self.c.y, ztop)))
        for j in range(cols):
            A, B = grid[j], grid[(j + 1) % cols]
            for i in range(rows - 1):
                t.faces.new((A[i], B[i], B[i + 1], A[i + 1]))  # wound outward: lam runs counterclockwise seen from above
            t.faces.new((A[-1], B[-1], pole))
        return shell(t, thick)

    def bob(self, lam, z, puff=.17, tuck=.13, cheek=.2, opening=47):
        """Studs a bob's shell stands off the volume at (lam, z): out as it falls and in again at the hem, back toward the forehead at the
        fringe so it does not hang in front of the face decal, and against the cheeks at the sides of the face's opening (`opening`
        degrees either side of the front), or the face sits in a dark hood."""
        d = (self.c.z - z) / self.h
        a = abs((lam + 180) % 360 - 180)
        out = puff * self.k * math.sin(min(1.0, d / 1.15) * math.pi * .62) if d > 0 else 0.0
        reach = opening + 3
        forehead = tuck * self.k * (.5 + .5 * math.cos(math.pi * min(a, reach) / reach)) * max(0.0, min(1.0, (d + .6) / .5)) if d < .5 else 0.0
        side = cheek * self.k * max(0.0, 1 - abs(a - reach) / 34) * max(0.0, min(1.0, (d + .3) / .4))
        return out - max(forehead, side)

    def shell(self, edge, off=0.0, stop=None, rows=7, thick=.03, lift=None):
        """One smooth sheet of hair with a toothed lower edge, for a style drawn as a single volume (a bob, a blunt cut), where separate locks
        read as a comb of teeth around a dome. edge [(degrees, height in half-heads above the head's centre)] runs in order round the
        head and closes on itself; points() and teeth() make its stretches. off stands it clear of the shell under it (0.035 for two
        tones, the outer one shorter). stop (in half-heads) leaves its top open under that outer shell; without it the sheet closes at the
        crown. lift(lam, z) moves it off the volume, bob() by default."""
        lift = lift or self.bob
        ztop = self.c.z + self.top
        end = self.c.z + stop * self.h if stop else ztop
        t = bmesh.new()
        grid = []
        for lam, e in edge:
            z0 = self.c.z + e * self.h
            col = []
            for i in range(rows):
                z = z0 + (end - z0) * math.sin(math.pi / 2 * i / rows) * (1 if stop else .985)
                col.append(t.verts.new(self.at(lam, z, off + lift(lam, z))))
            grid.append(col)
        n = len(grid)
        for j in range(n):
            A, B = grid[j], grid[(j + 1) % n]
            for i in range(rows - 1):
                t.faces.new((A[i], B[i], B[i + 1], A[i + 1]))
        if not stop:
            pole = t.verts.new(Vector((self.c.x, self.c.y, ztop + off)))
            for j in range(n):
                t.faces.new((grid[j][-1], grid[(j + 1) % n][-1], pole))
        t.normal_update()
        return shell(t, thick)

    @staticmethod
    def points(span, tips, valley):
        """A fringe's edge for shell(): one point per entry of tips (heights, as in shell), across span degrees either side of the front."""
        n, out = len(tips), []
        for i, tip in enumerate(tips):
            if i:
                out.append((-span + 2 * span * i / n, valley))
            out.append((-span + 2 * span * (i + .5) / n, tip))
        return out

    @staticmethod
    def teeth(a, b, n, valley, tip, seed=1):
        """A hem's edge for shell(): n teeth of uneven depth from a to b degrees."""
        out = []
        for i in range(n):
            out.append((a + (b - a) * i / n, valley + .05 * ((i * 7 + seed) % 3 - 1)))
            out.append((a + (b - a) * (i + .5) / n, tip - .09 * ((i * 5 + seed) % 3)))
        return out

    def lock(self, points, width, thick=None, widest=0.2, hold=0.6, root=0.8, taper=1.0, ridge=0.65, sides=4, steps=None):
        """A blade along points (root first): `root` of `width` at the root, full width from `widest` to `hold` of the way
        down, then narrowing to a point (taper > 1 thins it sooner). A flowing lock keeps its width and points only at the
        end; a spike or leaf blade (hold = widest) tapers from near its root. thick defaults to 0.25 of the width; `ridge`
        of it stands outward, so the outer face has a crease down the middle. sides 4 is faceted, 6 rounder. Closed: the
        root ends in a short point inside the volume. Width is what reads: narrow locks read as noodles."""
        pts = [Vector(p) for p in points]
        length = sum((b - a).length for a, b in zip(pts, pts[1:]))
        n = steps or max(6, min(16, int(length / .07) + 2))
        path = _spline(pts, n)
        thick = width * .25 if thick is None else thick
        t = bmesh.new(); rings = []; tan = (path[1] - path[0]).normalized()
        for i, p in enumerate(path):
            u = i / (n - 1)
            k = root + (1 - root) * math.sin(math.pi / 2 * u / widest) if u < widest else 1.0 if u <= hold else \
                ((1 - u) / (1 - hold)) ** taper
            step = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
            tan = step.normalized() if step.length > 1e-9 else tan
            up = self.normal(p)
            if abs(up.dot(tan)) > .95:  # a spike runs along the normal: take the thickness across it
                up = Z if abs(tan.z) < .9 else -Y
            b = tan.cross(up).normalized(); up = b.cross(tan).normalized()
            w, o, i_ = width * k / 2, thick * k * ridge, thick * k * (1 - ridge)
            if i == n - 1 or w < 1e-4:
                rings.append([t.verts.new(p)]); continue
            prof = [(w, 0), (0, o), (-w, 0), (0, -i_)] if sides == 4 else \
                [(w, 0), (w * .5, o * .85), (-w * .5, o * .85), (-w, 0), (-w * .5, -i_ * .85), (w * .5, -i_ * .85)]
            rings.append([t.verts.new(p + b * x + up * y) for x, y in prof])
        tan0 = (path[1] - path[0]).normalized()
        rings.insert(0, [t.verts.new(path[0] - tan0 * min(width * .3, .05))])
        for A, B in zip(rings, rings[1:]):
            m = max(len(A), len(B))
            for j in range(m):
                if len(A) == 1:
                    t.faces.new((A[0], B[j], B[(j + 1) % m]))
                elif len(B) == 1:
                    t.faces.new((A[j], A[(j + 1) % m], B[0]))
                else:
                    t.faces.new((A[j], A[(j + 1) % m], B[(j + 1) % m], B[j]))
        bmesh.ops.recalc_face_normals(t, faces=t.faces[:])
        return t

    def hang(self, lam, z, tip, lift=0.03, sweep=0.0, flick=0.0, drift=0.12, steps=8):
        """Path points from the volume at (lam, z) down its surface to height `tip`, `lift` clear of it; sweep turns it that
        many degrees by the tip (bangs sweep away from the part), drift moves it outward per stud below the head's centre
        (an A-line), flick bends the last third out (+) or under (-)."""
        pts, p, lam_k, step = [], self.at(lam, z, lift), lam, .05 * self.k
        for _ in range(400):
            pts.append(p)
            if p.z <= tip:
                break
            n = self.normal(p); down = (n * n.dot(Z) - Z)
            down = down.normalized() if down.length > 1e-6 else -Z
            q = p + down * step
            frac = min(1.0, (z - q.z) / max(z - tip, 1e-6))
            a = math.radians(lam + sweep * frac - lam_k); lam_k = lam + sweep * frac
            rel = q - self.c; q = self.c + Vector((rel.x * math.cos(a) - rel.y * math.sin(a), rel.x * math.sin(a) + rel.y * math.cos(a), rel.z))
            p = self.project(q, lift + drift * max(0.0, self.c.z - q.z))
        if len(pts) < 3:
            pts = [pts[0], pts[0].lerp(p - Z * .05, .5), p - Z * .05]
        steps = min(steps, len(pts))
        keep = [pts[round(i * (len(pts) - 1) / (steps - 1))] for i in range(steps)]
        if flick:
            for i in range(steps):
                u = i / (steps - 1)
                if u > .66:
                    keep[i] = keep[i] + self.normal(keep[i]) * flick * ((u - .66) / .34) ** 2
        return keep

    def bangs(self, n=4, part=-20, span=110, width=0.42, low=0.25, high=0.55, sweep=22, seed=1, tips=None, flick=-0.02, **kw):
        """n locks over the front, rooted high on the dome (as hair flows from the crown) and spread across `span`
        degrees, sweeping away from the part (`part` degrees; 0 a centre part), widths varied around `width` and
        overlapping, tips between `low` and `high` head half-heights above the head's centre (or `tips`, one per lock),
        one lock reaching the lowest; flick < 0 turns the tips in toward the face. Keep the eyes clear: the references'
        tips spread 0.3 to 0.6 studs, and gaps between them reach well up."""
        rng = random.Random(seed); out = []
        heights = tips or [low + (high - low) * rng.random() for _ in range(n)]
        if not tips:
            heights[min(range(n), key=lambda i: abs(-span / 2 + span * (i + .5) / n - part - 12))] = low
        z_root = self.c.z + self.h + (self.top - self.h) * .6
        for i in range(n):
            lam = -span / 2 + span * (i + .5) / n + rng.uniform(-.15, .15) * span / n
            away = math.copysign(1, lam - part) * min(1.0, abs(lam - part) / (span / 2))
            path = self.hang(lam - sweep * away * .5, z_root, self.c.z + heights[i] * self.h, lift=(.03 + .025 * (i % 2)) * self.k,
                             sweep=sweep * away, drift=0, flick=flick * self.k)
            out.append(self.lock(path, width * self.k * rng.uniform(.8, 1.2), **{'hold': .45, **kw}))
        return out

    def layer(self, lam0, lam1, n, z, tip, width=None, jitter=0.15, seed=2, **hang):
        """n hanging locks across lam0..lam1 (degrees), rooted at height z, ending around `tip` (alternately longer and
        shorter by up to `jitter`, a zigzag hem). Each is 1.6 times its spacing wide, so neighbours overlap like shingles
        and no scalp shows between them; alternate locks stand a little further out."""
        rng = random.Random(seed); out = []
        arc = math.radians(abs(lam1 - lam0)) * (self.rx + self.ryb) / 2 / max(1, n)
        lift = hang.pop('lift', .03 * self.k)
        for i in range(n):
            lam = lam0 + (lam1 - lam0) * (i + .5) / n
            end = tip - jitter * self.k * (.5 + .5 * rng.random()) * (i % 2) + jitter * self.k * .3 * rng.random()
            path = self.hang(lam, z, end, lift=lift + .02 * self.k * (i % 2), **hang)
            out.append(self.lock(path, (width or arc * 1.6) * rng.uniform(.85, 1.15)))
        return out

    def spike(self, lam, z, length, width, up=1.0, back=0.6, out=0.3, thick=None):
        """A leaf-blade spike rooted in the volume at (lam, z), leaving it along the normal and curving toward `up` and
        `back` (a flame: anime spikes sweep up and back, hug the volume and overlap; they never stick straight out like a
        sea urchin or splay sideways like wings). Measured: about 0.7 long and 0.4 wide at the root. Build
        them broad, in offset rows from the top of the dome to the nape, `up` falling and `back` rising row by row."""
        root = self.at(lam, z, -.04 * self.k); n = self.normal(root)
        d = (n * out + Z * up + Y * back).normalized()
        mid = root + n * .3 * length + d * .3 * length
        return self.lock([root, mid, mid + d * .7 * length], width, thick=width * .5 if thick is None else thick,
                         widest=.15, hold=.15, root=.9, ridge=.55)


HAIR = {'rise': 0.18, 'standoff': 0.10, 'spiky': 0.4, 'back': 0.15, 'crown': 95, 'back_upper': 90, 'side_upper': 55, 'nape': 70, 'fringe': 0.15}


def hair_check(head, obs, leave=(), mins=HAIR):
    """What makes hair read as a helmet or a comb, {} when nothing does. obs: the hair's objects (world space) on
    layout()'s head. Keys: 'rise' (the dome over the top, median), 'standoff' (median gap between scalp and hair over the
    crown, back and upper sides; not asked of spiky hair, whose spikes rise past 'spiky' from a base that hugs the head),
    'back' (bulge behind the head), coverage of 'crown', 'back_upper', 'nape' and 'side_upper' (percent of the head's
    surface there with hair over it), and 'fringe' (the bangs' tips all at one height, when they cover the forehead).
    Checked on 48 references: the minimums pass all but the design exceptions below, for a head 1.2 tall
    (scaled with it); the skill's monster hair failed rise, standoff and fringe (0.14, 0.06 and 0.04). leave lists what
    the design leaves bare or straight on purpose: 'nape' (a crop: 9 of the 46), 'back' (a ponytail or slicked-back
    hair), 'fringe' (a straight-cut fringe or a headband's edge), any other key."""
    bpy.context.view_layer.update()
    c, r, h = head['c'], head['r'], head['h']; k = h / .6
    verts, polys = [], []
    for ob in obs:
        polys += [[len(verts) + i for i in p.vertices] for p in ob.data.polygons]
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    tree = BVHTree.FromPolygons(verts, polys)

    def outer(o, d, reach=4.0):
        hit = tree.ray_cast(o + d * reach, -d, reach)
        return None if hit[0] is None else reach - hit[3]
    regions, gaps = {}, []
    for i in range(48):
        a = i * 360 / 48; d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0)); fa = abs((a + 180) % 360 - 180)
        for j in range(12):
            z = c.z + h * (-.85 + 1.6 * (j + .5) / 12)
            rg = ('back_upper' if z > c.z else 'nape') if fa >= 120 else 'side_upper' if fa >= 60 and z > c.z + .1 * h else \
                'forehead' if fa < 40 and z > c.z + .35 * h else None
            if rg:
                hit = tree.ray_cast(Vector((c.x, c.y, z)) + d * r, d, 1.5 * k)
                regions.setdefault(rg, []).append(hit[0] is not None)
                if hit[0] is not None and rg != 'forehead' and rg != 'nape':
                    gaps.append(hit[3])
    rises = []
    for x in range(-3, 4):
        for y in range(-3, 4):
            o = Vector((c.x + x * .16 * r, c.y + y * .16 * r, c.z + h))
            hit = tree.ray_cast(o, Z, 1.5 * k)
            regions.setdefault('crown', []).append(hit[0] is not None)
            if hit[0] is not None:
                gaps.append(hit[3])
            top = outer(Vector((o.x, o.y, c.z)), Z)
            if top is not None:
                rises.append(top - h)
    found = {}
    rise = sorted(rises)[len(rises) // 2] if rises else 0.0
    if rise < mins['rise'] * k and 'rise' not in leave:
        found['rise'] = f"the hair rises {rise:.2f} over the head's top: raise its dome to {mins['rise'] * k:.2f} or more (the references: {.42 * k:.2f})"
    gap = sorted(gaps)[len(gaps) // 2] if gaps else 0.0
    if gap < mins['standoff'] * k and rise < mins['spiky'] * k and 'standoff' not in leave:
        found['standoff'] = f"the hair sits {gap:.2f} off the scalp: at least {mins['standoff'] * k:.2f} (the references: {.22 * k:.2f}), or it reads as a helmet"
    bulge = max((b for b in (outer(Vector((c.x, c.y, c.z + f * h)), Y) for f in (0, .33, .67)) if b is not None), default=r) - r
    if bulge < mins['back'] * k and 'back' not in leave:
        found['back'] = f"the hair stands {bulge:.2f} out behind the head: at least {mins['back'] * k:.2f} (the references: {.33 * k:.2f})"
    for rg in ('crown', 'back_upper', 'nape', 'side_upper'):
        hits = regions.get(rg, [])
        pct = 100 * sum(hits) / max(1, len(hits))
        if pct < mins[rg] and rg not in leave:
            found[rg] = f'{pct:.0f}% of the head is covered at the {rg.replace("_", " ")}: at least {mins[rg]}%' + \
                (", or leave=('nape',) for a crop or an updo" if rg == 'nape' else '')
    fore = regions.get('forehead', [])
    if 'fringe' not in leave and fore and sum(fore) / len(fore) >= .5:
        low = []
        for i in range(15):
            x = c.x + r * (-.7 + 1.4 * i / 14); z, lowest = c.z + h, None
            while z > c.z - h:
                hit = tree.ray_cast(Vector((x, c.y - 3, z)), Y, 3)
                if hit[0] is not None and hit[0].y < c.y - .9 * r:
                    lowest = z
                z -= .02
            if lowest is not None:
                low.append(lowest)
        if low and max(low) - min(low) < mins['fringe'] * k:
            found['fringe'] = (f'the bangs all end within {max(low) - min(low):.2f} of one height: vary their lengths by '
                               f"{mins['fringe'] * k:.2f} or more and let the gaps between them reach up (the references: 0.3 to 0.6), "
                               "or leave=('fringe',) for a straight-cut fringe")
    return found


# ---------------------------------------------------------------- the anime ink paint recipe


def _hexlin(c):
    return tuple(x ** 2.2 for x in rr._rgb(c)) + (1.0,)


def _paint_material(name, p):
    """A painted look as one emission: flat local color, a soft-edged shadow shape, a highlight and lit edges. Light comes from
    above and in front, as in a drawing; none of it depends on the engine's lights. Line work stays out of this bake: thresholded
    ambient occlusion makes a noisy, jagged edge. Lines are drawn as strokes instead."""
    m = bpy.data.materials.new('PAINT_' + name); m.use_nodes = True
    nt = m.node_tree; N, Lk = nt.nodes, nt.links
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL':
            N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')

    def math_(op, a, b=None, clamp=False):
        n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                Lk.new(v, n.inputs[i])
        return n.outputs[0]

    def steps(v, lo, hi):
        n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'
        Lk.new(v, n.inputs['Value']); n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi
        return n.outputs[0]

    def mix(a, b, f):
        n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'
        for sock, v in ((n.inputs[6], a), (n.inputs[7], b)):
            if isinstance(v, tuple):
                sock.default_value = v
            else:
                Lk.new(v, sock)
        Lk.new(f, n.inputs[0])
        return n.outputs[2]
    geo = N.new('ShaderNodeNewGeometry')
    # The same light on the back as on the front, as a drawing has: with one light in front, everything facing backward falls into the
    # shadow tone and a white back reads gray.
    split = N.new('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Normal'], split.inputs[0])
    mirrored = N.new('ShaderNodeCombineXYZ')
    Lk.new(split.outputs['X'], mirrored.inputs['X']); Lk.new(split.outputs['Z'], mirrored.inputs['Z'])
    Lk.new(math_('MULTIPLY', math_('ABSOLUTE', split.outputs['Y']), -1.0), mirrored.inputs['Y'])
    d = N.new('ShaderNodeVectorMath'); d.operation = 'DOT_PRODUCT'
    Lk.new(mirrored.outputs[0], d.inputs[0]); d.inputs[1].default_value = Vector((-.3, -.55, .78)).normalized()
    lit = d.outputs['Value']
    wide = N.new('ShaderNodeAmbientOcclusion'); wide.samples = 8; wide.inputs['Distance'].default_value = .5
    tc = N.new('ShaderNodeTexCoord')
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3.5; noise.inputs['Detail'].default_value = 2.0
    Lk.new(tc.outputs['Object'], noise.inputs['Vector'])
    brush = math_('SUBTRACT', noise.outputs['Fac'], .5)
    # The shadow shape: where the form turns from the light, and where neighbours crowd it, with a hand-wobbled soft edge.
    form = math_('SUBTRACT', .5, lit)
    crowd = math_('MULTIPLY', math_('SUBTRACT', 1.0, wide.outputs['AO']), 1.1)
    shape = math_('ADD', math_('ADD', math_('MULTIPLY', form, .8), crowd), math_('MULTIPLY', brush, .3))
    if p.get('pleat'):
        # Soft streaks that run the way the cloth hangs, so its folds are shapes before they are lines.
        falls = (p.get('folds') or {}).get('flow') != 'wrinkle'
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3.6, 3.6, .55) if falls else (.9, .9, 3.6)
        Lk.new(tc.outputs['Object'], mp.inputs['Vector'])
        streak = N.new('ShaderNodeTexNoise'); streak.inputs['Scale'].default_value = 1.0; streak.inputs['Detail'].default_value = 0.0
        Lk.new(mp.outputs['Vector'], streak.inputs['Vector'])
        shape = math_('ADD', shape, math_('MULTIPLY', math_('SUBTRACT', steps(streak.outputs['Fac'], .38, .68), .42), p['pleat'] * 1.3))
    base, shade = _hexlin(p['base']), _hexlin(p['shade'])
    light = _hexlin(p['light']) if p.get('light') else tuple(min(1, c * 1.5 + .12) for c in base[:3]) + (1.0,)
    col = mix(base, shade, steps(shape, .26, .46))
    if p.get('pleat'):  # the lit crest of each fold
        col = mix(col, light, math_('MULTIPLY', steps(math_('SUBTRACT', 0.0, shape), .12, .3), .45))
    deep = tuple(c * .55 for c in shade[:3]) + (1.0,)
    col = mix(col, deep, math_('MULTIPLY', steps(crowd, .5, .85), .7))
    # A highlight on what faces the light, broken up by the same brush; lit edges on what turns sharply.
    gloss = math_('MULTIPLY', steps(math_('ADD', lit, math_('MULTIPLY', brush, .35)), .78, .92), p.get('gloss', .5))
    col = mix(col, light, gloss)
    bev = N.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = .016; bev.samples = 4
    e = N.new('ShaderNodeVectorMath'); e.operation = 'DOT_PRODUCT'
    Lk.new(bev.outputs['Normal'], e.inputs[0]); Lk.new(geo.outputs['Normal'], e.inputs[1])
    edge = math_('MULTIPLY', steps(math_('MULTIPLY', math_('SUBTRACT', 1.0, e.outputs['Value']), 9.0, True), .35, .8), steps(wide.outputs['AO'], .7, .95))
    col = mix(col, light, math_('MULTIPLY', edge, p.get('edge', .25)))
    em = N.new('ShaderNodeEmission'); Lk.new(col, em.inputs['Color'])
    Lk.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


def _curve(points, spacing):
    """Catmull-Rom through 2D `points` [(x, y, r)], resampled about every `spacing` pixels, so a line drawn over mesh edges comes out
    as one curve instead of a chain of straight segments."""
    if len(points) < 2:
        return points
    out = []
    pts = [points[0]] + points + [points[-1]]
    for i in range(1, len(pts) - 2):
        a, b, c, d = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(1, int(math.hypot(c[0] - b[0], c[1] - b[1]) / spacing))
        for k in range(n):
            u = k / n
            out.append(tuple(.5 * ((2 * b[j]) + (-a[j] + c[j]) * u + (2 * a[j] - 5 * b[j] + 4 * c[j] - d[j]) * u * u + (-a[j] + 3 * b[j] - 3 * c[j] + d[j]) * u ** 3) for j in range(3)))
    out.append(points[-1])
    return out


def _pressure(rnd, length, s):
    """A brush's width along a stroke, 0..1: tapered at both ends, swelling slowly as a hand does. Fast changes read as a rough
    line, not a drawn one."""
    taper = min(.09, length * .3)
    ends = min(1.0, (s / taper) ** .7, (max(length - s, 0) / taper) ** .7)
    return max(.14, ends) * (.86 + .14 * math.sin(s * rnd[0] + rnd[1]))


def _edge_strokes(ob, looks, hidden, weight, size, rng, ink):
    """Ink along sharp edges, open edges and the borders between looks. Each line is followed through the mesh, cut where it leaves a
    UV island, and laid down as one curve on each island it touches."""
    t = bmesh.new(); t.from_mesh(ob.data); t.edges.ensure_lookup_table(); t.faces.ensure_lookup_table()
    uv = t.loops.layers.uv.active
    limit = math.radians(55)
    slots = [s.material.name.split('M_', 1)[-1].split('.')[0] if s.material else '' for s in ob.material_slots]

    def inked(e):
        faces = e.link_faces
        if all(f.index in hidden for f in faces):
            return False
        return len(faces) != 2 or faces[0].material_index != faces[1].material_index or e.calc_face_angle(0.0) > limit
    picked = {e.index for e in t.edges if inked(e)}
    seen = set()
    for first in sorted(picked):
        if first in seen:
            continue
        # The line as a walk (edge, from vertex, to vertex), carried on through vertices with no hard turn.
        e0 = t.edges[first]; seen.add(first)
        walk = [(e0, e0.verts[0], e0.verts[1])]
        for forward in (True, False):
            while True:
                e, a, b = walk[-1] if forward else walk[0]
                v = b if forward else a
                here = (v.co - (a if forward else b).co).normalized()
                nxt = [o for o in v.link_edges if o.index in picked and o.index not in seen]
                nxt = [o for o in nxt if here.dot((o.other_vert(v).co - v.co).normalized()) > .6]
                if not nxt:
                    break
                o = nxt[0]; seen.add(o.index); w = o.other_vert(v)
                if forward:
                    walk.append((o, v, w))
                else:
                    walk.insert(0, (o, w, v))
        length = sum(e.calc_length() for e, _, _ in walk) or 1e-6
        rnd = (rng.uniform(2.0, 4.5), rng.uniform(0, 6))
        s = 0.0
        open_runs, runs = [], []
        for e, a, b in walk:
            ln = e.calc_length(); s0, s1 = s, s + ln; s = s1
            still = []
            for f in e.link_faces:
                if f.index in hidden:
                    continue
                for lp in f.loops:
                    if lp.edge != e:
                        continue
                    u0, u1 = (lp[uv].uv, lp.link_loop_next[uv].uv) if lp.vert == a else (lp.link_loop_next[uv].uv, lp[uv].uv)
                    run = next((r for r in open_runs if (r['pts'][-1][0] - u0).length < 1e-5), None)
                    if run is None:
                        other = lp.link_loop_radial_next
                        seam = len(e.link_faces) == 1 or (other[uv].uv - lp.link_loop_next[uv].uv).length > 1e-5
                        look = looks.get(slots[f.material_index], {}) if f.material_index < len(slots) else {}
                        run = {'pts': [(u0.copy(), s0)], 'line': look.get('line', .022), 'seam': seam, 'uv': 0.0, 'd3': 0.0}
                        runs.append(run)
                    else:
                        open_runs.remove(run)
                    run['pts'].append((u1.copy(), s1)); run['uv'] += (u1 - u0).length; run['d3'] += ln
                    still.append(run)
            open_runs = still
        for run in runs:
            scale = run['uv'] * weight / max(run['d3'], 1e-6)
            r = run['line'] * scale * (1.6 if run['seam'] else 1.0) / 2
            pts = [(q.x * size, (1 - q.y) * size, r * _pressure(rnd, length, d)) for q, d in run['pts']]
            ink.append([v for p in _curve(pts, 1.5) for v in p])
    t.free()


class _Surface:
    """An object's triangles with their UVs, for walking on its surface."""

    def __init__(self, ob):
        me = ob.data; me.calc_loop_triangles()
        self.me, self.tris = me, me.loop_triangles
        self.co = [ob.matrix_world @ v.co for v in me.vertices]
        self.tree = BVHTree.FromPolygons(self.co, [t.vertices for t in self.tris])
        self.uvs = me.uv_layers.active.data

    def uv(self, p, i):
        t = self.tris[i]
        a, b, c = (self.co[v] for v in t.vertices)
        u0, u1, u2 = (self.uvs[lp].uv for lp in t.loops)
        q = geometry.barycentric_transform(p, a, b, c, Vector((u0.x, u0.y, 0)), Vector((u1.x, u1.y, 0)), Vector((u2.x, u2.y, 0)))
        return Vector((q.x, q.y))

    def density(self, i):
        t = self.tris[i]
        a, b, c = (self.co[v] for v in t.vertices)
        u0, u1, u2 = (self.uvs[lp].uv for lp in t.loops)
        area3 = (b - a).cross(c - a).length
        area2 = abs((u1 - u0).x * (u2 - u0).y - (u1 - u0).y * (u2 - u0).x)
        return (area2 / area3) ** .5 if area3 > 1e-9 else 0.0


def _lay(surface, path, widths, size, ink, shadow, light, side=1):
    """A stroke along 3D `path` onto the texture, split where it crosses a seam; a fold's soft shadow and light go beside it."""
    runs, run, last = [], [], None
    for p, w in zip(path, widths):
        hit = surface.tree.find_nearest(p)
        if hit[0] is None:
            continue
        uv, i = surface.uv(hit[0], hit[2]), hit[2]
        scale = surface.density(i) * size
        if last is not None and (uv - last[0]).length * size > max(8.0, (hit[0] - last[1]).length * scale * 3):
            runs.append(run); run = []
        run.append((uv, w * scale / 2))
        last = (uv, hit[0])
    runs.append(run)
    for run in runs:
        if len(run) < 2:
            continue
        curve = _curve([(uv.x * size, (1 - uv.y) * size, r) for uv, r in run], 1.5)
        ink.append([v for p in curve for v in p])
        if shadow is None:
            continue
        beside = []
        for j, (x, y, r) in enumerate(curve):
            ax, ay = curve[max(j - 1, 0)][:2]; bx, by = curve[min(j + 1, len(curve) - 1)][:2]
            d = math.hypot(bx - ax, by - ay) or 1.0
            beside.append((x, y, -(by - ay) / d * side, (bx - ax) / d * side, r))
        shadow.append([v for x, y, nx, ny, r in beside for v in (x + nx * r * 2.4, y + ny * r * 2.4, r * 3.6)])
        light.append([v for x, y, nx, ny, r in beside for v in (x - nx * r * 2.6, y - ny * r * 2.6, r * .9)])


DRAPE = {'n': .3, 'flow': 'drape', 'fan': 2, 'spread': .2, 'gather': .1, 'len': (.6, 1.1), 'width': .015}
WRINKLE = {'n': .5, 'flow': 'wrinkle', 'fan': 2, 'spread': .35, 'gather': .1, 'len': (.2, .45), 'width': .014}


def _folds(ob, surface, looks, hidden, size, rng, tones, shadow, light):
    """Folds as they fall on cloth: a fan of strokes from each pinch, at the top of a drape or at both ends of a sleeve, thick where
    they start and running out to a point. Random strokes read as scratches."""
    polys, slots = ob.data.polygons, [s.material.name.split('M_', 1)[-1].split('.')[0] if s.material else '' for s in ob.material_slots]
    mw = ob.matrix_world
    for index, look in enumerate(slots):
        spec = looks.get(look, {}).get('folds')
        if not spec:
            continue
        tone = spec.get('tone') or '#%02x%02x%02x' % tuple(int(c * 255 * .55) for c in rr._rgb(looks[look]['shade']))
        ink = tones.setdefault(tone, [])
        faces = [p for p in polys if p.material_index == index and p.index not in hidden]
        if not faces:
            continue
        cum, total = [], 0.0
        for f in faces:
            total += f.area; cum.append(total)
        zs = [(mw @ f.center).z for f in faces]
        zlo, zhi = min(zs), max(zs)

        def sample():
            r = rng.uniform(0, total)
            lo, hi = 0, len(cum) - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cum[mid] < r:
                    lo = mid + 1
                else:
                    hi = mid
            f = faces[lo]
            w = [rng.random() for _ in f.vertices]
            return sum((mw @ ob.data.vertices[v].co * k for v, k in zip(f.vertices, w)), Vector()) / sum(w)
        flow, spread, per = spec.get('flow', 'mixed'), spec.get('spread', .55), spec.get('fan', 4)
        for _ in range(max(1, round(total * spec.get('n', 2)))):
            # A pinch sits near the region's ends: where cloth gathers under a hem, a belt or a joint.
            p = sample()
            for _ in range(10):
                f_z = (p.z - zlo) / max(zhi - zlo, 1e-6)
                if (flow == 'drape' and f_z > .62) or (flow != 'drape' and (f_z > .7 or f_z < .3)):
                    break
                p = sample()
            f_z = (p.z - zlo) / max(zhi - zlo, 1e-6)
            down = flow == 'drape' or f_z > .5
            hit = surface.tree.find_nearest(p)
            if hit[0] is None:
                continue
            across = hit[1].cross(Z)
            if across.length < .1:
                continue
            across.normalize()
            count = rng.randint(max(1, per - 1), per + 1)
            lean = rng.choice((-1, 1)) * .6 if flow != 'drape' else 0.0  # a whole fan leans one way, or its strokes cross
            for j in range(count):
                k = (j / max(1, count - 1) - .5) * 2 if count > 1 else 0.0
                turn = lean + k * spread + rng.uniform(-.08, .08)
                start = p + across * k * spec.get('gather', .07)
                length = rng.uniform(*spec.get('len', (.3, .8))) * (1 - abs(k) * .35)
                step = .05
                path = [start]
                for _ in range(max(3, int(length / step))):
                    near = surface.tree.find_nearest(path[-1])
                    if near[0] is None:
                        break
                    n = near[1]
                    base = -Z if down else Z
                    d = base + n.cross(base) * turn
                    d -= n * d.dot(n)
                    if d.length < 1e-4:
                        break
                    turn *= 1.04
                    path.append(near[0] + d.normalized() * step)
                if len(path) < 3:
                    continue
                width = spec.get('width', .04) * rng.uniform(.75, 1.15)
                m = len(path) - 1
                widths = [width * (max(.15, min(1.0, i / max(1, m * .12))) * (1 - i / m) ** .8) for i in range(m + 1)]
                _lay(surface, path, widths, size, ink, shadow, light, 1 if k >= 0 else -1)


def paint(objs, looks, out_dir, prefix, size=1024, samples=24, strokes=None, seed=1, line_scale=1.0):
    """Anime-ink PBR recipe (see LOOKS above). Paints each look, inks it, then bakes the
    relief of the line work and folds into the normal map, and each look's roughness and metalness. Writes
    <out_dir>/<prefix>_{color,normal,metal,rough}.png at `size` and returns their paths, for a SurfaceAppearance. Materials are
    the 'M_<Look>' previews from Pieces.objects; strokes come from Pieces.ink. line_scale thins the ink on something small and
    detailed, such as a weapon. Needs Pillow in a `python` on the PATH (skin_ink.py)."""
    if not objs:
        raise ValueError('paint: no skin objects')
    slots = []
    for ob in objs:
        if ob.type != 'MESH' or not ob.material_slots or not ob.data.uv_layers:
            raise ValueError(f'paint: {ob.name} needs a mesh with materials and UVs')
        for slot in ob.material_slots:
            look = slot.material.name.split('M_', 1)[-1].split('.')[0] if slot.material else ''
            if look not in looks or not {'base', 'shade'} <= looks[look].keys():
                raise ValueError(f'paint: {ob.name} look {look!r} needs base and shade')
            slots.append((slot, look))
    python = shutil.which('python') or shutil.which('python3')
    if not python:
        raise ValueError('paint: no python on the PATH for skin_ink.py')
    hidden, rng = _hidden(objs), random.Random(seed)
    ink, shadow, light, tones = [], [], [], {}
    for ob in objs:  # read the look names while the slots still hold the preview materials
        surface = _Surface(ob)
        _edge_strokes(ob, looks, hidden[ob.name], size * line_scale, size, rng, ink)
        _folds(ob, surface, looks, hidden[ob.name], size, rng, tones, shadow, light)
    for part, points, width in strokes or []:
        ob = next((o for o in objs if o.name.split('__')[0] == part), None)
        if ob:
            m = len(points) - 1
            _lay(_Surface(ob), points, [width * max(.15, math.sin(math.pi * i / max(1, m))) for i in range(m + 1)], size, ink, None, None)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = False
    sc.render.bake.margin = 8; sc.render.bake.target = 'IMAGE_TEXTURES'; sc.render.bake.use_clear = True
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    def bake(key, colorspace, material, kind='EMIT', **options):
        """One map: `material(look)` on every slot, baked to <prefix>_<key>.png."""
        img = bpy.data.images.new(f'{prefix}_{key}', size, size, alpha=False); img.colorspace_settings.name = colorspace
        done = {}
        for slot, look in slots:
            done.setdefault(look, material(look))
            slot.material = done[look]
        for m in done.values():
            node = m.node_tree.nodes.new('ShaderNodeTexImage'); node.image = img; m.node_tree.nodes.active = node
        bpy.ops.object.bake(type=kind, **options)
        path = os.path.join(out_dir, f'{prefix}_{key}.png')
        img.filepath_raw = path; img.file_format = 'PNG'; img.save()
        return path

    def flat(field, default):
        def make(look):
            m = bpy.data.materials.new(f'FLAT_{field}_{look}'); m.use_nodes = True
            nt = m.node_tree; o = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
            for n in list(nt.nodes):
                if n.type != 'OUTPUT_MATERIAL':
                    nt.nodes.remove(n)
            em = nt.nodes.new('ShaderNodeEmission'); v = looks[look].get(field, default)
            em.inputs['Color'].default_value = (v, v, v, 1); nt.links.new(em.outputs['Emission'], o.inputs['Surface'])
            return m
        return make
    base = bake('paint', 'sRGB', lambda look: _paint_material(look, looks[look]))
    data = os.path.join(out_dir, prefix + '_strokes.json')
    with open(data, 'w', encoding='utf-8') as f:
        json.dump({'ink': ink, 'shadow': shadow, 'light': light, 'tones': [{'color': [int(c * 255) for c in rr._rgb(k)], 'strokes': v} for k, v in tones.items()]}, f)
    maps = {key: os.path.join(out_dir, f'{prefix}_{key}.png') for key in ('color', 'height')}
    subprocess.run([python, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skin_ink.py'), base, data, maps['color'], maps['height']], check=True)
    os.remove(data); os.remove(base)
    sc.cycles.samples = 4
    relief = bpy.data.images.load(maps['height']); relief.colorspace_settings.name = 'Non-Color'

    def relief_material(look):
        m = bpy.data.materials.new('RELIEF_' + look); m.use_nodes = True
        nt = m.node_tree; bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = relief
        bev = nt.nodes.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = .012; bev.samples = 4
        bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .9; bump.inputs['Distance'].default_value = .012
        nt.links.new(tex.outputs['Color'], bump.inputs['Height']); nt.links.new(bev.outputs['Normal'], bump.inputs['Normal'])
        nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
        return m
    maps['normal'] = bake('normal', 'Non-Color', relief_material, 'NORMAL', normal_space='TANGENT')
    sc.cycles.samples = 1
    maps['rough'] = bake('rough', 'Non-Color', flat('rough', .7))
    maps['metal'] = bake('metal', 'Non-Color', flat('metal', 0.0))
    os.remove(maps.pop('height'))
    return maps


# ---------------------------------------------------------------- PBR stage, when asked


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


def sharpen(objs, angle=40):
    """Mark edges sharper than `angle` degrees, so plates keep crisp rims. Smooth shading across a shell's rim bends the normals
    over the whole plate, which reads as inflated plastic."""
    for ob in objs:
        t = bmesh.new(); t.from_mesh(ob.data)
        limit = math.radians(angle)
        for e in t.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < limit
        t.to_mesh(ob.data); t.free()


REGIONS = {'Head': ('Head',), 'Torso': ('Torso', 'UpperTorso', 'LowerTorso'), 'Arms': ('Arm', 'Hand'), 'Legs': ('Leg', 'Foot')}


def regions(objs):
    """{region: skin objects}, one texture for each. One map across a whole character leaves a chest about 50 pixels a stud; four
    use the memory of one PBR set, at twice the sharpness. Glow and gear keep their own."""
    out = {}
    for ob in objs:
        part = ob.name.split('__')[0]
        name = next((r for r, keys in REGIONS.items() if any(part == k or part.endswith(k) for k in keys)), 'Torso')
        out.setdefault(name, []).append(ob)
    return out


def _tree(objs):
    verts, polys = [], []
    for ob in objs:
        polys += [[len(verts) + i for i in p.vertices] for p in ob.data.polygons]
        verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    return BVHTree.FromPolygons(verts, polys)


def _hidden(objs, reach=0.12):
    """{object name: indices of faces with something right in front of them}: a shell's inner side, a base pressed on a plate."""
    around = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_render and o not in objs and o.name != 'RIG_HumanoidRootPart']
    tree, out = _tree(objs + around), {}
    for ob in objs:
        rot, found = ob.matrix_world.to_3x3(), set()
        for p in ob.data.polygons:
            n = (rot @ p.normal).normalized()
            if tree.ray_cast(ob.matrix_world @ p.center + n * .004, n, reach)[0] is not None:
                found.add(p.index)
        out[ob.name] = found
    return out


def _shrink_hidden(objs, keep):
    """Scale UV islands that are nearly all hidden by `keep`, leaving their texels to what shows: a shell spends half its area
    on an inner side no one sees. Tiny ornaments (rivets, a stud's rim) carry no paint worth a full share, so they get a little less."""
    hidden = _hidden(objs)
    for ob in objs:
        t = bmesh.new(); t.from_mesh(ob.data); t.faces.ensure_lookup_table()
        uv = t.loops.layers.uv.active
        for island in bmesh_utils.bmesh_linked_uv_islands(t, uv):
            area = sum(f.calc_area() for f in island) or 1
            scale = keep if sum(f.calc_area() for f in island if f.index in hidden[ob.name]) / area >= .85 else .55 if area < .02 else 1.0
            if scale == 1.0:
                continue
            loops = [lp for f in island for lp in f.loops]
            c = sum((lp[uv].uv for lp in loops), Vector((0, 0))) / len(loops)
            for lp in loops:
                lp[uv].uv = c + (lp[uv].uv - c) * scale
        t.to_mesh(ob.data); t.free()


def _break_rings(objs, sectors=8):
    """Split hollow UV islands into sectors. Smart projection lays a band's rim out as one ring around nothing, and packing
    keeps the hole: fifteen rims left the chest 30 pixels a stud on a 1024 map."""
    for ob in objs:
        t = bmesh.new(); t.from_mesh(ob.data); t.faces.ensure_lookup_table()
        uv = t.loops.layers.uv.active
        for island in bmesh_utils.bmesh_linked_uv_islands(t, uv):
            pts = [lp[uv].uv for f in island for lp in f.loops]
            lo, hi = Vector((min(p.x for p in pts), min(p.y for p in pts))), Vector((max(p.x for p in pts), max(p.y for p in pts)))
            box = (hi.x - lo.x) * (hi.y - lo.y)
            filled = 0.0
            for f in island:
                q = [lp[uv].uv for lp in f.loops]
                filled += abs(sum(q[i].x * q[(i + 1) % len(q)].y - q[(i + 1) % len(q)].x * q[i].y for i in range(len(q)))) / 2
            if len(island) < 8 or box <= 0 or filled / box > .4:
                continue
            c = (lo + hi) / 2
            for f in island:
                m = sum((lp[uv].uv for lp in f.loops), Vector((0, 0))) / len(f.loops)
                sector = int((math.atan2(m.y - c.y, m.x - c.x) + math.pi) / math.tau * sectors) % sectors
                for lp in f.loops:
                    lp[uv].uv = lp[uv].uv + Vector((sector * 1e-3, 0))
        t.to_mesh(ob.data); t.free()


def unwrap(objs, margin=0.004, hidden=0.1):
    """Smart-project every object into one shared 0-1 atlas at one texel density, hollow islands split so packing can fill the
    map. Islands that never show get `hidden` of it; 1 turns that off."""
    if not objs:
        return

    def pick():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
    pick()
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    if hidden < 1:
        _shrink_hidden(objs, hidden)
    _break_rings(objs)
    pick()
    bpy.ops.uv.select_all(action='SELECT')
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
    if 'metal' in maps:
        nt.links.new(tex('metal', 'Non-Color').outputs['Color'], bs.inputs['Metallic'])
        nt.links.new(tex('rough', 'Non-Color').outputs['Color'], bs.inputs['Roughness'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tex('normal', 'Non-Color').outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    else:
        bs.inputs['Roughness'].default_value = .7
    for ob in objs:
        ob.data.materials.clear(); ob.data.materials.append(m)
