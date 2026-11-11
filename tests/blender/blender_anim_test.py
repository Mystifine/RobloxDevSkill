"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/blender_anim_test.py
blender_anim.py on a replica R15 (r6_on_r15_fixture.json's rig, built by roblox_rig): keys are checked whole, polish gives
Bezier with sharp keys, the audit passes a clean clip and catches each planted defect, and the review, preview, world-delta
and FBX outputs are written."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import bpy
from mathutils import Quaternion

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import blender_anim as ba
import roblox_rig as rr

FIXTURE = json.loads((HERE / 'r6_on_r15_fixture.json').read_text(encoding='utf-8'))


def quat(axis, degrees):
    return list(Quaternion(axis, math.radians(degrees)))


class Base(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = 60
        self.arm = rr.build(FIXTURE['rig'])['armature']
        for pb in self.arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def wave(self, name='Wave', interpolation='CONSTANT', end=24):
        """The right arm up and back down; the left foot planted."""
        for frame, degrees in ((0, 0), (12, 80), (end, 0)):
            r = ba.key(self.arm, frame, {'RightUpperArm': {'rotation_quaternion': quat((0, 1, 0), degrees)},
                                         'LeftFoot': {'location': [0, 0, 0]}}, interpolation, action=name if frame == 0 else None)
            self.assertTrue(r['ok'], r['errors'])
        return bpy.data.actions[name]


class Keys(Base):
    def test_a_bad_batch_changes_nothing(self):
        r = ba.key(self.arm, 3, {'RightUpperArm': {'rotation_quaternion': [1, 0, 0, 0]}, 'Tail': {'location': [0, 0, 0]}})
        self.assertFalse(r['ok'])
        self.assertIsNone(self.arm.animation_data and self.arm.animation_data.action)

    def test_a_quaternion_key_stays_on_the_previous_keys_side(self):
        ba.key(self.arm, 0, {'Head': {'rotation_quaternion': quat((0, 0, 1), 10)}}, action='Turn')
        flipped = [-v for v in quat((0, 0, 1), 20)]  # the same turn, written the long way
        ba.key(self.arm, 6, {'Head': {'rotation_quaternion': flipped}})
        w = next(c for c in ba.curves(bpy.data.actions['Turn']) if c.data_path.endswith('rotation_quaternion') and c.array_index == 0)
        self.assertGreater(w.keyframe_points[1].co.y, 0)


class Polish(Base):
    def test_bezier_with_vector_handles_on_sharp_frames(self):
        act = self.wave()
        r = ba.polish(self.arm, act, sharp=(12,))
        self.assertTrue(r['ok'])
        kinds = {(round(k.co.x), k.handle_left_type) for c in ba.curves(act) for k in c.keyframe_points}
        self.assertIn((12, 'VECTOR'), kinds)
        self.assertIn((0, 'AUTO_CLAMPED'), kinds)
        self.assertTrue(all(k.interpolation == 'BEZIER' for c in ba.curves(act) for k in c.keyframe_points))


class Audit(Base):
    def test_a_clean_clip_passes_and_reports_its_fastest_turn(self):
        act = self.wave()
        ba.polish(self.arm, act)
        r = ba.audit(self.arm, act, loop=(0, 24), contacts={'LeftFoot': [[0, 24]]})
        self.assertTrue(r['ok'], r['errors'])
        self.assertLess(r['metrics']['fastest']['degrees_per_60fps_frame'], 43)
        self.assertEqual(r['metrics']['drift']['LeftFoot'][0][2], 0.0)

    def test_final_needs_loop_and_contacts_stated(self):
        act = self.wave()
        ba.polish(self.arm, act)
        self.assertFalse(ba.audit(self.arm, act)['ok'])
        self.assertTrue(ba.audit(self.arm, act, loop=False, contacts=False)['ok'])

    def test_blocking_allows_constant_keys_and_final_does_not(self):
        act = self.wave()
        self.assertTrue(ba.audit(self.arm, act, stage='BLOCKING', loop=False, contacts=False)['ok'])
        self.assertIn('Constant', ' '.join(ba.audit(self.arm, act, loop=False, contacts=False)['errors']))

    def test_sparse_linear_keys_fail_and_dense_ones_pass(self):
        act = self.wave(interpolation='LINEAR')
        self.assertIn('mechanical', ' '.join(ba.audit(self.arm, act, loop=False, contacts=False)['errors']))
        for frame in range(0, 25, 2):  # an R6 animator's string: a key every 2 frames
            ba.key(self.arm, frame, {'Head': {'rotation_quaternion': quat((0, 0, 1), 3 * math.sin(frame / 4))}}, 'LINEAR', action='Dense' if frame == 0 else None)
        self.assertTrue(ba.audit(self.arm, 'Dense', loop=False, contacts=False)['ok'])

    def test_a_fast_turn_and_a_pop_are_caught(self):
        ba.key(self.arm, 0, {'RightUpperArm': {'rotation_quaternion': quat((0, 1, 0), 0)}}, 'BEZIER', action='Snap')
        ba.key(self.arm, 2, {'RightUpperArm': {'rotation_quaternion': quat((0, 1, 0), 120)}}, 'BEZIER')
        errors = ' '.join(ba.audit(self.arm, 'Snap', loop=False, contacts=False)['errors'])
        self.assertIn('RightUpperArm turns', errors)

    def test_a_loop_seam_and_a_sliding_foot_are_caught(self):
        act = self.wave()
        ba.polish(self.arm, act)
        for c in ba.curves(act):
            if c.data_path.endswith('location') and 'LeftFoot' in c.data_path and c.array_index == 0:
                c.keyframe_points[-1].co.y += 0.3
                c.update()
        errors = ' '.join(ba.audit(self.arm, act, loop=(0, 24), contacts={'LeftFoot': [[0, 24]]})['errors'])
        self.assertIn('loop seam', errors)
        self.assertIn('LeftFoot slides', errors)

    def test_an_animated_mesh_is_caught(self):
        act = self.wave()
        ba.polish(self.arm, act)
        body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('UpperTorso'))
        body.keyframe_insert('location', frame=0)
        self.assertIn('animated meshes', ' '.join(ba.audit(self.arm, act, loop=False, contacts=False)['errors']))


class Outputs(Base):
    def test_review_preview_deltas_and_fbx_are_written(self):
        act = self.wave()
        ba.polish(self.arm, act)
        review = ba.review(self.arm, self.out, 'up', frame=12)
        self.assertTrue(review['ok'], review['errors'])
        self.assertTrue(all(Path(p).stat().st_size > 0 for p in review['images'].values()))
        preview = ba.preview(self.arm, self.out / 'frames', 'wave', 0, 24, step=4, size=128, exclude_last=True)
        self.assertEqual((preview['ok'], preview['frames'], preview['gif_fps']), (True, 6, 15.0))
        r = ba.deltas(self.arm, self.out / 'wave.json', act, markers={'Peak': 12})
        data = json.loads(Path(r['path']).read_text(encoding='utf-8'))
        self.assertEqual(len(data['Samples']), 25)
        self.assertEqual(data['Markers'], {'Peak': 0.2})
        self.assertEqual(len(data['Samples'][0]['bones']['RightUpperArm']), 7)
        fbx = ba.export_fbx(self.arm, self.out / 'wave', act)
        self.assertTrue(fbx['ok'] and Path(fbx['path']).stat().st_size > 0, fbx['errors'])

    def test_review_asks_which_way_an_unknown_rig_faces(self):
        del self.arm['rig_type']
        self.assertIn('which way', ba.review(self.arm, self.out, 'x')['errors'][0])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        raise RuntimeError('blender_anim regression tests failed')
