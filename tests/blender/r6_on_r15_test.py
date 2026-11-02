"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/r6_on_r15_test.py
Checks Blender's controls against Studio's numbers for the same body and poses (tests/studio/R6OnR15.fixture.luau writes them)."""
import json
from pathlib import Path
import sys
import unittest

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import r6_on_r15 as r6
import roblox_rig as rr

FIXTURE = json.loads((HERE / 'r6_on_r15_fixture.json').read_text(encoding='utf-8'))
HEIGHT = FIXTURE['roles']['rootHeight']
TIP = {'Left Arm': 'LeftHand', 'Right Arm': 'RightHand', 'Left Leg': 'LeftFoot', 'Right Leg': 'RightFoot'}


def motion_in_blender(world, part):
    """How Studio says a part moved from rest, in Blender's space."""
    return rr.to_blender(world[part], HEIGHT) @ rr.to_blender(FIXTURE['rest'][part], HEIGHT).inverted()


def motion_of(arm, bone):
    pb = arm.pose.bones[bone]
    return pb.matrix @ pb.bone.matrix_local.inverted()


class Base(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.rig = rr.build(FIXTURE['rig'])
        self.arm = self.rig['armature']
        r6.add_controls(self.arm, FIXTURE['roles'])
        self.roles = FIXTURE['roles']['roles']

    def assertMatches(self, world, parts=None, places=3):
        bpy.context.view_layer.update()
        for part in parts or world:
            if part not in self.arm.pose.bones:
                continue
            got, wanted = motion_of(self.arm, part), motion_in_blender(world, part)
            off = max(abs(a - b) for ra, rb in zip(got, wanted) for a, b in zip(ra, rb))
            self.assertLess(off, 10 ** -places, f'{part} is {off:.5f} from Studio')


class Controls(Base):
    def test_rest_is_rest(self):
        for part in FIXTURE['rest']:
            if part in self.arm.pose.bones:
                # 0.0003 is float noise in the rest matrix of a bone along Blender's -Y: no turn, and the limit the Studio checks use.
                self.assertLess(max(abs(v) for row in motion_of(self.arm, part) - Matrix.Identity(4) for v in row), 1e-3, part)

    def test_refuses_an_incomplete_armature(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        data = bpy.data.armatures.new('X')
        arm = bpy.data.objects.new('X', data)
        bpy.context.scene.collection.objects.link(arm)
        with self.assertRaises(ValueError):
            r6.add_controls(arm, FIXTURE['roles'])

    def test_controls_sit_at_r6_pivots_not_r15_joints(self):
        shoulder = self.arm.data.bones['R6_Arm.R']
        pivot = rr.to_blender([*self.roles['Right Arm']['pivot'], 1, 0, 0, 0, 1, 0, 0, 0, 1], HEIGHT).translation
        self.assertLess((shoulder.head_local - pivot).length, 1e-4)
        self.assertGreater((shoulder.head_local - self.arm.data.bones['RightUpperArm'].head_local).length, 0.2)

    def test_new_bones_do_not_deform(self):
        for bone in self.arm.data.bones:
            if bone.name.startswith(('R6_', 'MCH_', 'FOL_')):
                self.assertFalse(bone.use_deform, bone.name)

    def test_locked_bones_refuse_poses(self):
        self.assertTrue(all(self.arm.pose.bones['RightLowerLeg'].lock_rotation))
        self.assertTrue(all(self.arm.pose.bones['UpperTorso'].lock_location))


class Fk(Base):
    def test_fk_matches_studio(self):
        for case in FIXTURE['fk']:
            for bone in self.arm.pose.bones:
                if bone.name in r6.BLOCKS.values():
                    bone.matrix_basis = Matrix.Identity(4)
            bpy.context.view_layer.update()
            for part in ('Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg'):
                if part in case['pose']:
                    r6.pose_r6(self.arm, part, case['pose'][part])
            self.assertMatches(case['world'])
            self.assertEqual(r6.check_locks(self.arm), [])


class Ik(Base):
    def test_ik_matches_studio(self):
        for case in FIXTURE['ik']:
            self.setUp()
            if case.get('torso'):
                r6.pose_r6(self.arm, 'Torso', case['torso'])
            r6.place_target(self.arm, case['limb'], case['target'])
            r6.use_ik(self.arm, case['limb'], 1, slide=1)
            self.assertMatches(case['world'], parts=[TIP[case['limb']], self.roles[case['limb']]['joint']])
            self.assertEqual(r6.check_locks(self.arm), [])

    def test_slide_zero_only_aims_as_studio_does(self):
        case = FIXTURE['aimOnly']
        r6.place_target(self.arm, case['limb'], case['target'])
        r6.use_ik(self.arm, case['limb'], 1, slide=0)
        self.assertMatches(case['world'], parts=['RightHand', 'RightUpperArm'])

    def test_ik_zero_is_fk(self):
        case = FIXTURE['ik'][0]
        r6.place_target(self.arm, case['limb'], case['target'])
        r6.use_ik(self.arm, case['limb'], 0)
        off = max(abs(v) for row in motion_of(self.arm, 'RightHand') - Matrix.Identity(4) for v in row)
        self.assertLess(off, 1e-4)

    def test_target_stays_put_when_the_torso_moves(self):
        case = FIXTURE['ik'][2]
        r6.place_target(self.arm, case['limb'], case['target'])
        r6.use_ik(self.arm, case['limb'], 1)
        tip = self.arm.pose.bones['MCH_R6_Leg.R'].tail.copy()
        self.arm.pose.bones['R6_Torso'].location.z += .3
        bpy.context.view_layer.update()
        self.assertLess((self.arm.pose.bones['MCH_R6_Leg.R'].tail - tip).length, 1e-3)


class Bake(Base):
    def test_bake_keeps_the_motion_on_the_r15_bones(self):
        scene = bpy.context.scene
        arm_control = self.arm.pose.bones['R6_Arm.R']
        scene.frame_set(1)
        arm_control.keyframe_insert('rotation_quaternion')
        scene.frame_set(11)
        r6.pose_r6(self.arm, 'Right Arm', FIXTURE['fk'][0]['pose']['Right Arm'])
        arm_control.keyframe_insert('rotation_quaternion')
        arm_control.keyframe_insert('location')
        controls = self.arm.animation_data.action
        self.assertMatches(FIXTURE['fk'][0]['world'])
        baked = r6.bake(self.arm, 1, 11, name='Test')
        self.assertEqual(self.arm.animation_data.action, baked)
        self.assertEqual(baked.name, 'Test')
        scene.frame_set(11)
        self.assertTrue(all(c.mute for c in self.arm.pose.bones['RightUpperArm'].constraints))
        self.assertMatches(FIXTURE['fk'][0]['world'])
        self.assertEqual(r6.check_locks(self.arm), [])
        r6.edit(self.arm)
        self.assertEqual(self.arm.animation_data.action, controls)
        self.assertFalse(any(c.mute for c in self.arm.pose.bones['RightUpperArm'].constraints))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        raise RuntimeError('R6 on R15 regression tests failed')
