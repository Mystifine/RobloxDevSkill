"""Run in an isolated headless Blender: blender -b --factory-startup --python-exit-code 1 -P tests/blender/r15_motion_test.py
The R15 engine (scripts/r15_motion) on the default R15's proportions (r15_rig_fixture.json, what `pipeline.py dump` writes, without its meshes):
planted feet stay exactly still, the legs reach, a body turning over does not flip a leg, and a baked clip encodes for Studio."""
from pathlib import Path
import math
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1] / 'scripts' / 'r15_motion')]
import example_clips
import motion

RIG = motion.Rig(str(HERE / 'r15_rig_fixture.json'))
SIDES = ('LeftUpperLeg', 'RightUpperLeg', 'LeftLowerLeg', 'RightLowerLeg', 'LeftFoot', 'RightFoot')


def turned(a, b):
    """The angle between two rotations (a quaternion and its negative are the same one)."""
    angle = a.rotation_difference(b).angle
    return min(angle, math.tau - angle)


def pose_at(result, frame):
    return {joint: result['Joints'][joint][frame] for joint in result['Joints']}


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wave = motion.bake(example_clips.wave(RIG))
        cls.flip = motion.bake(example_clips.flip(RIG))

    def test_a_clip_lasts_its_seconds_at_60_fps(self):
        self.assertEqual(self.wave['Frames'], 180)
        self.assertEqual(self.wave['Fps'], 60)

    def test_a_planted_foot_does_not_move_at_all(self):
        for foot in ('LeftFoot', 'RightFoot'):
            places = [RIG.fk(pose_at(self.wave, frame))[foot][1] for frame in range(0, self.wave['Frames'], 5)]
            drift = max((place - places[0]).length for place in places)
            self.assertLess(drift, 0.002, foot)

    def test_the_legs_reach_their_feet(self):
        self.assertLess(self.wave['Short'], 0.01)

    def test_the_arm_keeps_its_springs_moving(self):
        turns = [self.wave['Joints']['RightUpperArm'][frame][0] for frame in range(0, self.wave['Frames'], 10)]
        self.assertGreater(max(turned(turns[0], turn) for turn in turns), math.radians(60), 'the wave raises the arm')

    def test_a_body_turning_over_never_flips_a_leg(self):
        for joint in SIDES:
            frames = self.flip['Joints'][joint]
            worst = max(turned(a[0], b[0]) for a, b in zip(frames, frames[1:]))
            self.assertLess(worst, math.radians(45), joint)

    def test_a_baked_clip_encodes_for_studio(self):
        data = motion.encode(self.wave, RIG)
        self.assertEqual(data['Name'], 'Wave')
        self.assertGreater(data['Keys'], 0)
        self.assertEqual(set(data['Joints']), set(self.wave['Joints']))


suite = unittest.defaultTestLoader.loadTestsFromTestCase(Engine)
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    sys.exit(1)
