"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/skin_kit_test.py"""
from pathlib import Path
import sys
import tempfile
import unittest

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import skin_kit as kit


def cube(x=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co.x += x
    return bm


class SkinKitTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

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


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SkinKitTests))
    if not result.wasSuccessful():
        raise RuntimeError('Skin kit regression tests failed')
