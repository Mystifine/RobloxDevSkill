"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/skin_kit_test.py"""
import math
from pathlib import Path
import sys
import tempfile
import unittest

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import skin_kit as kit


def cube(x=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x += x
    return bm


def closed(bm):
    return all(len(e.link_faces) == 2 for e in bm.edges)


def extent(bm, axis=0):
    values = [v.co[axis] for v in bm.verts]
    return min(values), max(values)


def limb(part, x):
    """An R6 limb's replica box at x, 1 wide, its faces touching the next box."""
    me = bpy.data.meshes.new(part)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.z *= 2
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('RIG_' + part, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, 0, 1)
    ob['roblox_part'] = part
    bpy.context.view_layer.update()
    return ob


class SkinKitTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_hoop_runs_round_its_outline_without_a_jump(self):
        hoop = kit.Hoop(1.0, .5, .15)
        steps = 400
        points = [hoop.at(hoop.L * i / steps)[0] for i in range(steps + 1)]
        self.assertLess(max((a - b).length for a, b in zip(points, points[1:])), hoop.L / steps * 1.5)
        self.assertLess((points[0] - points[-1]).length, 1e-6)
        self.assertAlmostEqual(hoop.at(.3)[0].x, -hoop.at(-.3)[0].x)
        self.assertAlmostEqual(hoop.at(0)[0].y, -.5)
        self.assertAlmostEqual(hoop.at(hoop.L / 2)[0].y, .5)

    def test_form_interpolates_between_its_hoops(self):
        form = kit.Form(1, 2, [(0, 1, 1, .1), (2, 2, 1, .1)])
        self.assertAlmostEqual(form.hoop(1).w, 1.5)
        p, n = form.S(0, 1, .1)
        self.assertAlmostEqual(p.y, 2 - 1.1)
        self.assertEqual(tuple(n), (0, -1, 0))

    def test_band_and_stack_face_outward_and_cut_at_each_joint(self):
        form = kit.Form(0, 0, [(0, 1, 1, .2), (2, 1, 1, .2)])
        t = kit.stack(form, form.around())
        face = max(t.faces, key=lambda f: f.calc_area())
        self.assertGreater(face.normal.dot(face.calc_center_median() - Vector((0, 0, face.calc_center_median().z))), 0)
        pieces = kit.Pieces()
        pieces.cut([('Upper', 1, 99), ('Lower', -99, 1)], 'Gold', t, .03)
        obs = pieces.objects({'Gold': '#C9A23A'})
        self.assertEqual(sorted(o.name for o in obs), ['Lower__Gold', 'Upper__Gold'])
        tops = {o.name: max(v.co.z for v in o.data.vertices) for o in obs}
        bottoms = {o.name: min(v.co.z for v in o.data.vertices) for o in obs}
        self.assertLess(tops['Lower__Gold'], 1)
        self.assertGreater(bottoms['Upper__Gold'], 1)

    def test_sections_cut_at_the_joints_and_keep_one_part_on_r6(self):
        r15 = {'upper': 'U', 'lower': 'L', 'hand': 'H', 'elbow': 3, 'wrist': 2}
        self.assertEqual(kit.sections(r15), [('U', 3, 99), ('L', 2, 3), ('H', -99, 2)])
        r6 = {'upper': 'Arm', 'lower': 'Arm', 'hand': 'Arm', 'elbow': 3, 'wrist': 2}
        self.assertEqual(kit.sections(r6), [('Arm', -99, 99)])
        self.assertEqual(kit.sections({'chest': 'T', 'hip': 'T', 'waist': 2}), [('T', -99, 99)])

    def test_mirrored_ribbons_meeting_on_the_centre_line_stay_flat(self):
        form = kit.Form(0, 0, [(0, 1, .5, .15), (3, 1, .5, .15)])
        pieces = kit.Pieces()
        for side, m in (('Left', 1), ('Right', -1)):
            path = [(m * .004, .4), (m * .3, 1.3), (m * .9, 1.8)]
            pieces.put(side, 'Gold', kit.ribbon(form.S, path, .044, flat_ends=True), False)
        obs = pieces.objects({'Gold': '#C9A23A'})
        self.assertEqual(kit.folds(obs), {})
        self.assertEqual(kit.coplanar(obs), {})

    def test_ribbon_plate_gem_and_blade_are_closed(self):
        form = kit.Form(0, 0, [(0, 1, .5, .15), (3, 1, .5, .15)])
        for t in (kit.ribbon(form.S, [(0, 1), (.5, 2)], .03), kit.plate(form.S, [(-.2, 1), (.2, 1), (0, 1.3)]),
                  kit.gem(form.S, 0, 1, .05), kit.blade([Vector((0, 0, 0)), Vector((0, 0, 1)), Vector((.1, 0, 2))], [.1, .1, 0], lambda p: kit.Y)):
            self.assertTrue(closed(t))
            t.free()

    def test_split_at_keeps_the_path_and_cuts_where_it_crosses(self):
        above, below = kit.split_at([(0, 3), (0, 1)], 2)
        self.assertEqual(above, [(0, 3), (0.0, 2)])
        self.assertEqual(below, [(0.0, 2), (0, 1)])

    def test_pokes_finds_a_box_corner_through_a_round_wrap(self):
        rig = {'boxes': {'Left Leg': limb('Left Leg', 0)}}
        for r, poking in ((.2, True), (.08, False)):
            form = kit.Form(0, 0, [(.2, .555, .555, r), (1.8, .555, .555, r)])
            pieces = kit.Pieces()
            pieces.put('Left Leg', 'Gold', kit.shell(kit.stack(form, form.around(3, 2, 6)), .03))
            obs = pieces.objects({'Gold': '#C9A23A'})
            self.assertEqual(bool(kit.pokes(rig, obs)), poking, r)
            for ob in obs:
                bpy.data.objects.remove(ob)

    def test_coplanar_gives_where_two_pieces_lie_on_each_other(self):
        pieces = kit.Pieces()
        pieces.put('A', 'Gold', kit.box((0, 0, 0), (1, 1, 1), 0))
        pieces.put('B', 'Gold', kit.box((.2, .2, 1), (.8, .8, 2), 0))
        pieces.put('C', 'Gold', kit.box((.2, .2, 0), (.8, .8, .5), 0))
        obs = pieces.objects({'Gold': '#C9A23A'})
        found = kit.coplanar(obs)
        self.assertIn(('A__Gold', 'C__Gold'), found)
        self.assertEqual(found[('A__Gold', 'C__Gold')][1][2], 0.0)
        self.assertNotIn(('A__Gold', 'B__Gold'), found)  # back to back, facing away from each other

    def test_a_bob_in_two_shells_is_closed_and_passes_hair_check(self):
        head = {'part': 'Head', 'c': Vector((0, 0, 4.6)), 'r': .6, 'h': .6}
        H = kit.Hair(head, rise=.2, side=.2, back=.28, front=.15, round_=2.7)
        span = 47
        under = H.points(span, [-.1, -.24, -.05, -.26, -.12, -.2, -.06], .2) + [(span + 2, -.25), (span + 6, -.72)]
        under += H.teeth(span + 10, 350 - span, 17, -.8, -.98) + [(354 - span, -.72), (358 - span, -.25)]
        over = H.points(40, [.14, .03, .2, .06, .17], .36) + [(43, .02), (49, -.3)] + H.teeth(55, 305, 13, -.32, -.54, 2) + [(311, -.3), (317, .02)]
        pieces = kit.Pieces()
        pieces.put('Head', 'Dark', H.shell(under, stop=.62, rows=6), True)
        t = H.shell(over, off=.035, rows=8)
        self.assertTrue(closed(t))
        pieces.put('Head', 'Hair', t, True)
        obs = pieces.objects({})
        self.assertEqual(kit.hair_check(head, obs), {})
        self.assertEqual(kit.folds(obs), {})
        self.assertLess(sum(len(p.vertices) - 2 for o in obs for p in o.data.polygons), 4800)

    def test_render_frames_a_weapon_that_lies_along_y(self):
        pieces = kit.Pieces()
        pieces.put('Sword', 'Gold', kit.box((-.05, -5, -.05), (.05, 1, .05), 0))
        pieces.objects({'Gold': '#C9A23A'})
        with tempfile.TemporaryDirectory() as tmp:
            paths = kit.render(tmp, 'sword', views={'right': kit.VIEWS['right']}, res=(120, 60))
            self.assertTrue(Path(paths[0]).exists())
            image = bpy.data.images.load(paths[0])
            px = list(image.pixels)
            w, h = image.size
            sword = [x for y in range(h) for x in range(w) if abs(px[(y * w + x) * 4 + 2] - px[2]) > .1]
            self.assertGreater(max(sword) - min(sword), w * .6)   # most of the frame, and not cut off at its edges
            self.assertGreater(min(sword), 0)
            self.assertLess(max(sword), w - 1)

    def piece(self):
        pieces = kit.Pieces()
        pieces.put('Head', 'Gold', cube())
        return pieces.objects({'Gold': '#C9A23A'})[0]

    def test_touching_ornaments_remain_closed_separate_components(self):
        pieces = kit.Pieces()
        pieces.put('Head', 'Gold', cube())
        pieces.put('Head', 'Gold', cube(1))
        ob = pieces.objects({'Gold': '#C9A23A'})[0]
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        self.assertEqual(len(bm.verts), 16)
        self.assertEqual(len(bm.faces), 24)
        self.assertTrue(all(len(e.link_faces) == 2 for e in bm.edges))
        # Each disconnected cube stays a closed ornament; sharing a plane is a
        # separate geometry QA concern and must never weld their topologies.
        remaining = set(bm.verts)
        components = 0
        while remaining:
            components += 1
            todo = [remaining.pop()]
            while todo:
                v = todo.pop()
                for e in v.link_edges:
                    other = e.other_vert(v)
                    if other in remaining:
                        remaining.remove(other)
                        todo.append(other)
        self.assertEqual(components, 2)
        bm.free()

    def test_tuck_closes_a_ring_and_keeps_the_wall_gap_clear(self):
        lo, hi = Vector((1, -.5, 0)), Vector((2, .5, 2))
        tucked = kit.wrap(lo, hi, .07, gap=.03, tuck='-x')
        self.assertTrue(closed(tucked))
        self.assertAlmostEqual(extent(tucked)[0], .97, 3)  # the side touching the neighbour reaches gap past the limb
        self.assertAlmostEqual(extent(tucked)[1], 2.1, 3)  # the free side keeps the full wall
        tucked.free()
        both = kit.wrap(Vector((-1, -.5, 0)), Vector((1, .5, 2)), .07, gap=.03, tuck='x')
        self.assertAlmostEqual(extent(both)[0], -1.03, 3)
        self.assertAlmostEqual(extent(both)[1], 1.03, 3)
        both.free()

    def test_open_side_still_leaves_the_wall_out(self):
        open_ = kit.wrap(Vector((1, -.5, 0)), Vector((2, .5, 2)), .07, gap=.03, open_side='-x')
        self.assertGreater(extent(open_)[0], 1)  # no wall past the limb on that side
        self.assertFalse(closed(open_) and extent(open_)[0] < 1)
        open_.free()

    def test_a_tucked_walls_back_stays_off_the_plane_the_limb_shares(self):
        # thick == gap once put the wall's back exactly on the plane the arm shares with the torso, which QA failed.
        for thick, gap in ((.03, .03), (.05, .03), (.02, .03), (.04, .03)):
            for tuck, limb_face, s in (('-x', 1, 1), ('+x', 2, -1)):
                t = kit.wrap(Vector((1, -.5, 0)), Vector((2, .5, 2)), thick, gap=gap, tuck=tuck)
                near = [abs(v.co.x - limb_face) for f in t.faces if abs(f.normal.x) > .99 for v in f.verts if s * (v.co.x - 1.5) < 0]
                self.assertGreaterEqual(min(near), .0199, (thick, gap, tuck))
                t.free()

    def test_a_tucked_ring_stops_short_of_the_end_a_neighbour_shares(self):
        # An R6 arm ends level with the torso: a ring reaching that height overlapped the torso's underside in one plane.
        t = kit.wrap(Vector((1, -.5, 2)), Vector((2, .5, 4)), .03, gap=.03, tuck='-x')
        self.assertAlmostEqual(extent(t, 2)[0], 2.01, 3)
        self.assertAlmostEqual(extent(t, 2)[1], 3.99, 3)
        t.free()

    def test_legs_tucked_together_share_no_flat_front(self):
        left = kit.wrap(Vector((0, -.5, 0)), Vector((1, .5, 2)), .03, gap=.03, tuck='-x')
        right = kit.wrap(Vector((-1, -.5, 0)), Vector((0, .5, 2)), .03, gap=.03, tuck='+x')

        def flat_front(t):
            front = min(v.co.y for v in t.verts)
            return [v.co.x for f in t.faces if f.normal.y < -.99 for v in f.verts if abs(v.co.y - front) < 1e-5]
        self.assertGreater(min(flat_front(left)), 0)  # the walls curve away before the seam, so nothing overlaps there
        self.assertLess(max(flat_front(right)), 0)
        left.free()
        right.free()

    def wrapped(self, tuck=None, open_side=None):
        rig = {'boxes': {'Left Arm': limb('Left Arm', 1.5)}}
        pieces = kit.Pieces()
        pieces.put('Left Arm', 'Scale', kit.wrap(Vector((1, -.5, .5)), Vector((2, .5, 1.5)), .07, gap=.03, tuck=tuck, open_side=open_side))
        return rig, pieces.objects({'Scale': '#4F7A3A'})

    def test_gaps_reports_the_side_a_wrap_leaves_bare(self):
        rig, pieces = self.wrapped(open_side='-x')
        found = kit.gaps(rig, pieces)
        self.assertEqual(set(found), {'Left Arm'})
        self.assertEqual(set(found['Left Arm']), {'-x'})
        z0, z1 = found['Left Arm']['-x']
        self.assertGreater(z0, .5)
        self.assertLess(z1, 1.5)

    def test_gaps_is_empty_for_a_closed_wrap(self):
        self.assertEqual(kit.gaps(*self.wrapped(tuck='-x')), {})

    def test_gaps_accepts_a_side_the_design_leaves_open(self):
        rig, pieces = self.wrapped(open_side='-x')
        self.assertEqual(kit.gaps(rig, pieces, {'Left Arm': '-x'}), {})
        self.assertEqual(kit.gaps(rig, pieces, {'Left Arm': 'x'}), {})
        self.assertIn('-x', kit.gaps(rig, pieces, {'Left Arm': '+x'})['Left Arm'])

    def test_gaps_passes_a_one_sided_piece(self):
        rig = {'boxes': {'Left Arm': limb('Left Arm', 1.5)}}
        pieces = kit.Pieces()
        pieces.put('Left Arm', 'Wing', kit.box(Vector((2.03, -.5, .2)), Vector((2.1, .5, 1.8))))  # a plate on the outer side
        self.assertEqual(kit.gaps(rig, pieces.objects({'Wing': '#A39A5A'})), {})

    def test_gaps_ignores_a_neighbours_pieces(self):
        # The other leg's wall stands right beside this side at rest, but it leaves when the leg swings.
        rig = {'boxes': {'Left Leg': limb('Left Leg', .5), 'Right Leg': limb('Right Leg', -.5)}}
        pieces = kit.Pieces()
        pieces.put('Left Leg', 'Scale', kit.wrap(Vector((0, -.5, .5)), Vector((1, .5, 1.5)), .07, gap=.03, open_side='-x'))
        pieces.put('Right Leg', 'Scale', kit.wrap(Vector((-1, -.5, .5)), Vector((0, .5, 1.5)), .07, gap=.03))
        self.assertEqual(set(kit.gaps(rig, pieces.objects({'Scale': '#4F7A3A'}))), {'Left Leg'})

    def test_apart_bares_the_inner_sides_and_restores_the_scene(self):
        boxes = [limb('Left Arm', 1.5), limb('Right Arm', -1.5), limb('Torso', 0)]
        pieces = kit.Pieces()
        pieces.put('Left Arm', 'Scale', kit.box(Vector((1, -.6, .5)), Vector((2, .6, 1.5))))
        objs = pieces.objects({'Scale': '#4F7A3A'})
        before = [ob.location.copy() for ob in boxes + objs]
        seen = []
        handler = lambda scene, _=None: seen.append(sorted(round(ob.matrix_world.translation.x, 2) for ob in boxes))
        bpy.app.handlers.render_pre.append(handler)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                paths = kit.render(tmp, 'apart', views=kit.INNER, apart=1.5, res=(32, 32))
                self.assertEqual(len(paths), 2)
                for path in paths:
                    self.assertGreater(Path(path).stat().st_size, 64)
        finally:
            bpy.app.handlers.render_pre.remove(handler)
        self.assertEqual(seen[0], [-3.0, 0.0, 3.0])  # limbs pulled out, the torso left where it is
        self.assertEqual([ob.location.copy() for ob in boxes + objs], before)

    def test_empty_slot_fails_before_mutating_valid_objects_or_scene(self):
        valid = self.piece()
        bad = valid.copy()
        bad.data = valid.data.copy()
        bad.name = 'BadSkin'
        bpy.context.scene.collection.objects.link(bad)
        bad.data.materials.append(None)
        material = valid.material_slots[0].material
        engine = bpy.context.scene.render.engine
        counts = len(bpy.data.materials), len(bpy.data.images)
        with self.assertRaisesRegex(ValueError, 'BadSkin material slot 1 is empty'):
            kit.bake([valid, bad], {'Gold': dict(base='#C9A23A', metal=1, rough=.4)}, '.', 'unused')
        self.assertEqual(valid.material_slots[0].material, material)
        self.assertEqual(bpy.context.scene.render.engine, engine)
        self.assertEqual((len(bpy.data.materials), len(bpy.data.images)), counts)

    def test_unknown_look_and_missing_parameters_fail_before_bake(self):
        ob = self.piece()
        with self.assertRaisesRegex(ValueError, "no PBR look 'Gold'"):
            kit.bake([ob], {}, '.', 'unused')
        with self.assertRaisesRegex(ValueError, 'missing metal, rough'):
            kit.bake([ob], {'Gold': {'base': '#C9A23A'}}, '.', 'unused')
        with self.assertRaisesRegex(ValueError, 'no skin objects'):
            kit.bake([], {}, '.', 'unused')

    def test_valid_batch_bakes_four_nonempty_maps(self):
        ob = self.piece()
        kit.unwrap([ob])
        with tempfile.TemporaryDirectory() as tmp:
            maps = kit.bake([ob], {'Gold': dict(base='#C9A23A', metal=1, rough=.4)}, tmp, 'test', size=32, samples=1)
            self.assertEqual(set(maps), {'color', 'normal', 'metal', 'rough'})
            for path in maps.values():
                self.assertGreater(Path(path).stat().st_size, 64)
                image = bpy.data.images.load(path, check_existing=False)
                self.assertEqual(tuple(image.size), (32, 32))
                self.assertGreater(max(list(image.pixels)[::4]), 0)


    def test_paint_makes_a_full_pbr_set_at_the_requested_size(self):
        ob = self.piece()
        kit.sharpen([ob])
        kit.unwrap([ob])
        looks = {'Gold': dict(base='#E8B83A', shade='#A06A10', rough=.4, metal=.2)}
        with tempfile.TemporaryDirectory() as tmp:
            maps = kit.paint([ob], looks, tmp, 'test', size=64, samples=1)
            self.assertEqual(set(maps), {'color', 'normal', 'metal', 'rough'})
            for path in maps.values():
                image = bpy.data.images.load(path, check_existing=False)
                self.assertEqual(tuple(image.size), (64, 64))
            self.assertEqual({p.name for p in Path(tmp).iterdir()}, {f'test_{k}.png' for k in maps})

    def test_paint_checks_its_looks_before_it_starts(self):
        ob = self.piece()
        kit.unwrap([ob])
        with self.assertRaisesRegex(ValueError, 'needs base and shade'):
            kit.paint([ob], {'Gold': {'base': '#E8B83A'}}, '.', 'unused')

    def test_a_curve_passes_through_its_points_and_fills_between(self):
        pts = [(0, 0, 1), (10, 0, 1), (10, 10, 1)]
        curve = kit._curve(pts, 1.5)
        self.assertGreater(len(curve), 10)
        self.assertEqual(curve[0][:2], (0, 0))
        self.assertEqual(curve[-1][:2], (10, 10))
        self.assertTrue(any(abs(c[0] - 10) < 1e-6 and abs(c[1]) < 1e-6 for c in curve))

    def test_sharpen_marks_a_box_edge_and_leaves_a_shallow_one(self):
        ob = self.piece()
        kit.sharpen([ob], 40)
        t = bmesh.new(); t.from_mesh(ob.data)
        hard = [e for e in t.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > 1.2]
        self.assertTrue(hard)
        self.assertFalse(any(e.smooth for e in hard))
        t.free()

    def test_regions_splits_a_rig_into_four_texture_sets(self):
        names = ('Head__Skin', 'Torso__Skin', 'Left Arm__Skin', 'RightHand__Skin', 'LeftUpperLeg__Skin', 'RightFoot__Skin', 'UpperTorso__Skin')
        obs = [type('Ob', (), {'name': n}) for n in names]
        got = {k: sorted(o.name for o in v) for k, v in kit.regions(obs).items()}
        self.assertEqual(got, {'Head': ['Head__Skin'], 'Torso': ['Torso__Skin', 'UpperTorso__Skin'],
                               'Arms': ['Left Arm__Skin', 'RightHand__Skin'], 'Legs': ['LeftUpperLeg__Skin', 'RightFoot__Skin']})

    def test_clips_finds_a_cut_and_clear_of_moves_out_of_it(self):
        def box(name, x, scale=1.0):
            t = cube(x)
            for v in t.verts:
                v.co.x = x + (v.co.x - x) * scale
                v.co.y *= scale; v.co.z *= scale
            me = bpy.data.meshes.new(name); t.to_mesh(me); t.free()
            ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
            return ob
        wall, gear = box('Wall', 0), box('Gear', .4, .8)  # smaller, so its faces really cross the wall's
        bpy.context.view_layer.update()
        self.assertTrue(kit.clips(gear, [wall]))

        def place(ob, d):
            ob.location.x = d
            bpy.context.view_layer.update()
        d = kit.clear_of(place, gear, [wall], start=0, stop=4, step=.02, pad=.08)
        self.assertGreater(d, .5)  # the boxes part at .5: pad keeps a margin beyond that
        self.assertFalse(kit.clips(gear, [wall], .08))
        place(gear, .52)
        self.assertFalse(kit.clips(gear, [wall]))
        self.assertTrue(kit.clips(gear, [wall], .08))  # 0.02 clear of it: inside the margin
        place(gear, 0)
        with self.assertRaises(ValueError):
            kit.clear_of(place, gear, [wall], start=0, stop=.1, step=.1)

    def test_clips_finds_a_mesh_inside_another_with_no_surfaces_crossing(self):
        def box(name, scale):
            t = cube(0)
            for v in t.verts:
                v.co *= scale
            me = bpy.data.meshes.new(name); t.to_mesh(me); t.free()
            ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
            return ob
        outer, inner = box('Outer', 2.0), box('Inner', .3)
        bpy.context.view_layer.update()
        self.assertTrue(kit.clips(inner, [outer]))
        self.assertTrue(kit.clips(outer, [inner]))

    def weapon(self, *boxes):
        """One object of boxes, each (x half, y from, y to, z from, z to), around the grip at the origin."""
        bm = bmesh.new()
        for x, y0, y1, z0, z1 in boxes:
            r = bmesh.ops.create_cube(bm, size=1)
            for v in r['verts']:
                v.co = Vector(((v.co.x + .5) * 2 * x - x, y0 + (v.co.y + .5) * (y1 - y0), z0 + (v.co.z + .5) * (z1 - z0)))
        me = bpy.data.meshes.new('Sword')
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new('Sword', me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    HANDLE = (.08, -.7, .75, -.08, .08)
    BLADE = (.05, -3.5, -.75, -.3, .3)
    GUARD = (.1, -.75, -.68, -.5, .5)
    POMMEL = (.12, .68, .9, -.12, .12)

    def test_grip_fit_passes_a_weapon_built_to_the_fist(self):
        self.assertEqual(kit.grip_fit([self.weapon(self.HANDLE, self.BLADE, self.GUARD, self.POMMEL)]), {})

    def test_grip_fit_finds_a_guard_and_blade_in_the_hand(self):
        """A sword whose guard and blade began 0.3 studs ahead of the grip."""
        sword = self.weapon((.08, -.3, .75, -.08, .08), (.05, -3.5, -.28, -.3, .3), (.1, -.33, -.27, -.5, .5))
        found = kit.grip_fit([sword])
        self.assertEqual(set(found), {'front'})
        self.assertIn('0.27 ahead', found['front'])

    def test_grip_fit_finds_a_pommel_in_the_hand(self):
        self.assertEqual(set(kit.grip_fit([self.weapon(self.HANDLE, self.BLADE, (.12, .4, .9, -.12, .12))])), {'back'})

    def test_grip_fit_finds_a_handle_that_stops_inside_the_fist(self):
        found = kit.grip_fit([self.weapon((.08, -.7, .5, -.08, .08), self.BLADE)])
        self.assertEqual(set(found), {'butt'})
        self.assertIn('0.50 behind', found['butt'])

    def test_grip_fit_finds_a_thick_shaft_with_no_vertex_in_the_fist(self):
        shaft = self.weapon((.2, -3, 2, -.2, .2))
        self.assertEqual({v.co.y for v in shaft.data.vertices} & {y / 10 for y in range(-6, 7)}, set())
        self.assertEqual(set(kit.grip_fit([shaft])), {'front', 'back'})

    def test_grip_fit_finds_a_weapon_off_the_handle_axis(self):
        self.assertEqual(set(kit.grip_fit([self.weapon((.08, -3, 1, .2, .36))])), {'front', 'back'})

    def test_grip_fit_finds_a_weapon_facing_the_wrong_way(self):
        backward = self.weapon((.08, -.75, .7, -.08, .08), (.05, .75, 3.5, -.3, .3))
        self.assertEqual(set(kit.grip_fit([backward])), {'facing'})
        upright = self.weapon((.08, -.8, .8, -.08, .08), (.08, -.1, .1, .75, 3))
        self.assertIn('facing', kit.grip_fit([upright]))

    def test_grip_fit_allows_a_knuckle_bow_below_the_hand(self):
        bow = (.05, -.75, .75, -.34, -.24)
        self.assertEqual(kit.grip_fit([self.weapon(self.HANDLE, self.BLADE, self.GUARD, self.POMMEL, bow)]), {})
        self.assertEqual(set(kit.grip_fit([self.weapon(self.HANDLE, self.BLADE, self.GUARD, self.POMMEL, (.05, -.3, .3, -.2, -.1))])), {'front', 'back'})

    def test_grip_fit_takes_a_bulky_gloves_fist(self):
        sword = self.weapon(self.HANDLE, self.BLADE, self.GUARD, self.POMMEL)
        self.assertEqual(set(kit.grip_fit([sword], fist=.75)), {'front', 'back'})

    def test_fist_measures_the_glove_at_the_hand_only(self):
        arm = {'lo': Vector((1, -.5, 2)), 'hi': Vector((2, .5, 4)), 'wrist': 2.3, 'hand': 'Right Arm'}
        ring = lambda half, z0, z1: self.named_box('Right Arm__Gold', 1.5, half, z0, z1)
        self.assertAlmostEqual(kit.fist(arm, [ring(.59, 2, 2.2), ring(.8, 3, 3.2)]), .59, places=5)
        self.assertAlmostEqual(kit.fist(arm, []), .5)
        self.assertAlmostEqual(kit.fist(arm, [self.named_box('Left Arm__Gold', 1.5, .9, 2, 2.2)]), .5)
        # A glove with no vertex at the fist's height: from below the hand's end to above the wrist.
        self.assertAlmostEqual(kit.fist(arm, [ring(.7, 1.9, 2.5)]), .7, places=5)

    def named_box(self, name, x, half, z0, z1):
        ob = self.weapon((half, -half, half, z0, z1))
        ob.name = name
        ob.location.x = x
        bpy.context.view_layer.update()
        return ob

    HEAD = {'part': 'Head', 'c': Vector((0, 0, 4.5)), 'r': .6, 'h': .6}  # the classic R6 head, 1.2 tall

    def test_hair_volume_stands_clear_of_the_head(self):
        H = kit.Hair(self.HEAD)
        top = H.at(0, 99)
        self.assertAlmostEqual(top.z - 4.5 - .6, .42, 3)  # the dome's rise over the head's top
        for lam in (0, 45, 90, 180, 270):
            for z in (3.9, 4.5, 4.9):
                p = H.at(lam, z)
                self.assertAlmostEqual(H.F(p), 1, 4)
                self.assertGreater((p - Vector((0, 0, z))).length, .6 + .05)
        far = H.project(Vector((3, 2, 6)))
        self.assertAlmostEqual(H.F(far), 1, 4)
        self.assertAlmostEqual((H.at(90, 4.5, .1) - H.at(90, 4.5)).length, .1, 3)

    def test_a_lock_is_a_closed_flat_blade_with_a_point(self):
        H = kit.Hair(self.HEAD)
        t = H.lock(H.hang(180, 5.1, 3.2, drift=0), .4)  # straight down the back: X across it, Y out from it
        self.assertTrue(closed(t))
        tip = min(t.verts, key=lambda v: v.co.z)
        self.assertEqual(len({e.other_vert(tip) for e in tip.link_edges}), 4)  # one vertex: a point, not a blunt end
        mid = [v.co for v in t.verts if 3.6 < v.co.z < 4.4]
        xs, ys = [p.x for p in mid], [p.y for p in mid]
        self.assertGreater(max(xs) - min(xs), 2.5 * (max(ys) - min(ys)))  # broad across the back, thin out from it
        t.free()

    def hair(self, H, *bms):
        pieces = kit.Pieces()
        for t in bms:
            pieces.put('Head', 'Hair', t, True)
        return pieces.objects({'Hair': '#7D6BC4'})

    def built_hair(self):
        H = kit.Hair(self.HEAD)
        return self.hair(H, H.cap(), *H.bangs(), *H.layer(95, 265, 9, 5.2, 3.0, drift=.1),
                         *[H.lock(H.hang(s * 75, 5.0, 3.9), .4) for s in (-1, 1)])

    def test_hair_check_passes_hair_built_to_the_references(self):
        self.assertEqual(kit.hair_check(self.HEAD, self.built_hair()), {})

    def test_hair_check_finds_a_helmet_and_a_comb(self):
        """Monster hair: a cap 0.09 off the head and 0.13 over it, 11 bangs ending at one height."""
        H = kit.Hair(self.HEAD, rise=.13, side=.09, back=.09, front=.09, round_=3.4)
        found = kit.hair_check(self.HEAD, self.hair(H, H.cap(), *H.bangs(n=11, span=116, tips=[.4] * 11, sweep=0),
                                                    *H.layer(144, 216, 7, 4.7, 3.0)))
        self.assertTrue({'rise', 'standoff', 'fringe'} <= set(found), found)
        self.assertIn('0.1', found['rise'])

    def test_hair_check_finds_a_bare_nape_unless_the_design_leaves_it(self):
        H = kit.Hair(self.HEAD)
        crop = self.hair(H, H.cap(nape=.2), *H.bangs())
        self.assertIn('nape', kit.hair_check(self.HEAD, crop))
        self.assertNotIn('nape', kit.hair_check(self.HEAD, crop, leave=('nape',)))

    def crescent(self, inner_end):
        """An outline whose inner arc runs to inner_end degrees. At 72 it ends where it meets the outer arc; at 50 it runs past it."""
        outer = [(.15 * math.cos(math.radians(d)), .15 * math.sin(math.radians(d))) for d in range(50, 311, 13)]
        inner = [(.06 + .12 * math.cos(math.radians(d)), .12 * math.sin(math.radians(d))) for d in range(360 - inner_end, inner_end - 1, -13)]
        return outer + inner

    def folded(self, size=1):
        """Two triangles sharing an edge, one lying over the other in the same plane."""
        me = bpy.data.meshes.new('Head__Skin')
        me.from_pydata([(0, 0, 0), (size, 0, 0), (size / 2, 0, size), (size / 2, 0, size / 2)], [], [(0, 1, 2), (1, 0, 3)])
        ob = bpy.data.objects.new('Head__Skin', me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def test_prism_refuses_an_outline_that_crosses_itself(self):
        with self.assertRaisesRegex(ValueError, 'crosses itself'):
            kit.prism(self.crescent(50), kit.X * 0, kit.X, kit.Z, -kit.Y, 0, .05)

    def test_prism_keeps_a_concave_outline_without_folding_it(self):
        pieces = kit.Pieces()
        pieces.put('Head', 'Gold', kit.prism(self.crescent(72), kit.X * 0, kit.X, kit.Z, -kit.Y, 0, .05, b=.012))
        self.assertEqual(kit.folds(pieces.objects({'Gold': '#C9A23A'})), {})

    def test_folds_finds_a_mesh_overlapping_itself(self):
        found = kit.folds([self.folded()])
        self.assertEqual(list(found), ['Head__Skin'])
        self.assertGreater(found['Head__Skin'][0], 0)

    def test_folds_leaves_separate_islands_that_touch(self):
        pieces = kit.Pieces()
        pieces.put('Head', 'Gold', cube())
        pieces.put('Head', 'Gold', cube(1))
        self.assertEqual(kit.folds(pieces.objects({'Gold': '#C9A23A'})), {})

    def test_folds_leaves_a_fold_nothing_can_see(self):
        ob = self.folded()
        pieces = kit.Pieces()
        pieces.put('Torso', 'Gold', kit.box((-1, .1, -1), (2, .4, 2), 0, 1))
        pieces.put('Torso', 'Gold', kit.box((-1, -.4, -1), (2, -.1, 2), 0, 1))
        pieces.objects({'Gold': '#C9A23A'})
        self.assertEqual(kit.folds([ob]), {})

    def test_folds_leaves_a_speck(self):
        self.assertEqual(kit.folds([self.folded(.05)]), {})

    def test_exports_refuse_a_mesh_overlapping_itself(self):
        ob = self.folded()
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'skin.fbx')
            with self.assertRaisesRegex(ValueError, 'overlaps itself'):
                kit.rr.export_pieces([ob], path)
            with self.assertRaisesRegex(ValueError, 'overlaps itself'):
                kit.rr.export_skinned(ob, None, path)
            self.assertFalse(Path(path).exists())


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SkinKitTests))
    if not result.wasSuccessful():
        raise RuntimeError('Skin kit regression tests failed')
