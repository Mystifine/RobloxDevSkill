"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/r6_rig_test.py
r6_rig.py on a copy of the pinned R6 IK + FK rig (`python scripts/r6_rig.py fetch` first; skipped without it): the check, the
add-on's exporter, grounding, the feet's IK targets and the .rbxanim export with its sidecar, read back as clip_import reads it."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import bpy
from mathutils import Quaternion, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import blender_anim as ba
import clip_import
import r6_rig as r6

MASTER = r6.HOME / r6.FILES['blend']['name']
READY = MASTER.is_file() and r6.sha256(MASTER) == r6.FILES['blend']['sha256']


@unittest.skipUnless(READY, 'the pinned rig is not cached: python scripts/r6_rig.py fetch')
class Rig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        work = r6.copy(Path(cls.tmp.name) / 'work.blend')
        bpy.ops.wm.open_mainfile(filepath=str(work), load_ui=False, use_scripts=False)
        bpy.context.scene.render.fps = 60
        cls.arm = bpy.data.objects['__PrimaryArmature']

    @classmethod
    def tearDownClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cls.tmp.cleanup()

    def setUp(self):
        if self.arm.animation_data:
            self.arm.animation_data.action = None
        for pb in self.arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()

    def test_the_pinned_rig_passes_its_check_and_a_changed_script_fails(self):
        self.assertTrue(r6.check()['ok'])
        text = bpy.data.texts['RigEvents.py']
        original = text.as_string()
        text.write('\n# changed')
        try:
            self.assertIn('RigEvents.py', ' '.join(r6.check()['errors']))
        finally:
            text.clear()
            text.write(original)

    def test_aiming_points_the_arm_and_the_held_item(self):
        visible = next(o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get() and o.name.startswith('Right Arm'))

        def extent():
            bpy.context.view_layer.update()
            corners = [visible.matrix_world @ Vector(c) for c in visible.bound_box]
            return [max(c[i] for c in corners) - min(c[i] for c in corners) for i in range(3)], sum(corners, Vector()) / 8

        (_, _, tall), hanging = extent()
        pb = self.arm.pose.bones['RightShoulder']
        pb.rotation_quaternion = r6.aim(pb, (0, 1, 0), (0, 0, 1))  # straight ahead, the blade up
        (_, deep, high), ahead = extent()
        self.assertGreater(tall, 1.9)  # hanging: the 2-stud arm runs down
        self.assertTrue(deep > 1.9 and high < 1.1, (deep, high))  # aimed: it runs forward
        # (R6 turns an arm a quarter of the way down it: its centre swings from 0.5 below the pivot to 0.5 ahead of it)
        self.assertGreater(ahead.y - hanging.y, 0.45)
        self.assertGreater(ahead.z - hanging.z, 0.45)
        free = self.arm.pose.bones['LeftShoulder']
        free.rotation_quaternion = r6.swing(free, (0, 0, -1))
        self.assertLess(Quaternion(free.rotation_quaternion).angle, 1e-4)  # hanging is rest

    def test_a_crouch_sinks_the_rigid_legs_until_grounded(self):
        self.arm.pose.bones['LowerTorso-FK'].location.y = -0.5
        bpy.context.view_layer.update()
        self.assertLess(min(r6.soles().values()), -0.2)
        moved = r6.ground(self.arm)
        self.assertAlmostEqual(min(r6.soles().values()), 0.0, places=2)
        self.assertGreater(moved, 0.2)

    def test_a_clip_exports_with_its_markers_and_feet(self):
        self.assertTrue(r6.addon()['ok'])
        for frame, degrees in ((0, 0), (10, 70), (20, 0)):
            q = list(Quaternion((1, 0, 0), math.radians(degrees)))
            r = ba.key(self.arm, frame, {'RightShoulder': {'rotation_quaternion': q}, 'LeftLeg-IK': {'location': [0, 0, 0.3 * (frame == 10)]}},
                       'BEZIER', action='Lift' if frame == 0 else None)
            self.assertTrue(r['ok'], r['errors'])
        audit = ba.audit(self.arm, 'Lift', loop=(0, 20), contacts={'RightLeg-IK': [[0, 20]]})
        self.assertTrue(audit['ok'], audit['errors'])
        out = r6.export(self.arm, Path(self.tmp.name) / 'Lift', 'Lift', markers={'Peak': 10}, loop=True)
        self.assertTrue(out['ok'], out['errors'])
        data = clip_import.rbxanim_data(out['rbxanim'])
        info = json.loads(Path(out['json']).read_text(encoding='utf-8'))
        self.assertEqual(len(data['kfs']), 21)
        self.assertTrue({'Torso', 'Head', 'Right Arm', 'Left Arm', 'Right Leg', 'Left Leg'} <= set(data['kfs'][10]['kf']))
        self.assertEqual((info['Markers'], info['Loop'], len(info['Feet']['Left Leg'])), ({'Peak': round(10 / 60, 4)}, True, 21))
        self.assertAlmostEqual(info['Feet']['Left Leg'][10][2], 0.3, places=3)
        self.assertEqual(info['Feet']['Right Leg'][10][2], 0.0)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        raise RuntimeError('R6 rig regression tests failed')
