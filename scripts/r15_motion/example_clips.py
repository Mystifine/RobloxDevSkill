"""Two clips to copy from: a clip is sparse key poses on channels, and motion.py does the rest. CLIPS is what r15_rig.make reads.
A project keeps its own file like this one, on Blender's sys.path beside this folder."""
from clips_common import RELAX_L, RELAX_R, swing_over
from motion import CRISP, NATURAL, Clip, arm, life, pose


def wave(r):
    """Stands easy, raises the right arm and waves twice; each foot stays planted, exactly."""
    c = Clip(r, "Wave", 3.0, feel=NATURAL)
    c.foot("L").plant(-0.5, 0.05, 8)
    c.foot("R").plant(0.5, -0.05, -8)
    easy = dict(hip=(0, -0.1, 0), hipr=(1, 0, 0), spine=(1, 0, 0), neck=(4, 0, 0))
    c.key(0, pose(armL=RELAX_L, armR=RELAX_R, **easy))
    c.key(0.5, pose(armL=RELAX_L, armR=RELAX_R, **easy))
    up = arm(dir=(0.5, 0.9, -0.1), elbow=35, twist=-10)
    across = arm(dir=(0.35, 0.95, -0.1), elbow=55, twist=-10)
    c.key(0.9, pose(armR=up, spine=(-1, -3, -2), neck=(2, 6, 0)), ease="out")
    for i, at in enumerate((1.15, 1.4, 1.65, 1.9)):
        c.key(at, pose(armR=across if i % 2 == 0 else up))
    c.key(2.6, pose(armL=RELAX_L, armR=RELAX_R, **easy))
    c.key(3.0, pose(armL=RELAX_L, armR=RELAX_R, **easy))
    c.layer(life(seed=5, breath=3.6, sway=0.5))
    return c


def flip(r):
    """A body turning over on the spot, head-first and back, airborne: the cutscene or the game carries the root. Its legs go round the hips (swing_over)."""
    c = Clip(r, "Flip", 3.0, feel=CRISP, ignore=["float", "end-offset", "clip", "slide", "stride"])
    ankle = r.ankle_height
    c.foot("L").plant(-0.5, 0.05, 8)
    c.foot("R").plant(0.5, -0.05, -8)
    upright = dict(hip=(0, -0.1, 0), hipr=(2, 0, 0), spine=(1, 0, 0), neck=(4, 0, 0), armL=RELAX_L, armR=RELAX_R)
    over = dict(hip=(0, 1.5, 0), hipr=(114, 0, 0), spine=(7, 0, 0), neck=(-38, 0, 0), armL=RELAX_L, armR=RELAX_R)
    feet_up = (((-0.5, 5.1, 0.55), (150, 0, 0)), ((0.5, 5.6, 1.15), (165, 0, 0)))
    feet_down = (((-0.5, ankle, 0.05), (0, 8, 0)), ((0.5, ankle, -0.05), (0, -8, 0)))
    c.key(0, pose(**upright))
    c.key(0.5, pose(**upright))
    swing_over(c, 0.5, 1.0, 2.6, feet_up)
    c.key(1.0, pose(**over))
    c.key(1.8, pose(**over))
    swing_over(c, 1.8, 2.4, 2.6, feet_down)
    c.key(2.4, pose(**upright))
    c.key(3.0, pose(**upright))
    return c


CLIPS = {"Wave": wave, "Flip": flip}
