"""Shared by the clip files: the body language every clip draws on (relaxed arms, tense arms, gait layers, kneeling)."""
import math

from mathutils import Vector

from motion import arm, clamp, mirror, qx, smooth, turn

# ---------------------------------------------------------------------------------------------------------------- arms

RELAX_L = arm(dir=(-0.07, -1, 0.02), elbow=12, twist=8, hand=(-8, 0, 0))
RELAX_R = mirror(RELAX_L)
HANG_L = arm(dir=(-0.04, -1, 0.05), elbow=7, twist=4, hand=(-4, 0, 0))  # dead weight
HANG_R = mirror(HANG_L)
TENSE_L = arm(dir=(-0.16, -1, -0.08), elbow=26, twist=14, hand=(-4, 0, 0))  # fists at the sides, ready
TENSE_R = mirror(TENSE_L)
WIDE_L = arm(dir=(-0.3, -1, 0.04), elbow=16, twist=6, hand=(-6, 0, 0))  # big, a little away from the body
WIDE_R = mirror(WIDE_L)


def folded(upper="R", lift=0.0):
    """Arms folded on the chest. The R15's torso is wide and its arms are short, so the shoulders come forward and in, as they really do when
    folding arms, and the forearms cross on the chest's front, one above the other. Returns (armL, armR)."""
    top = dict(reach=(-0.42, 0.10 + lift, -1.12), frame="chest", pole=(0.95, -0.3, 0.35), handw=None, hand=(0, 8, 0), girdle=(0.30, 0.04, 0.26))
    low = dict(reach=(0.38, -0.40 + lift, -1.04), frame="chest", pole=(-0.95, -0.3, 0.35), handw=None, hand=(0, -8, 0), girdle=(0.30, 0.0, 0.26))
    a_top = arm(**top)
    a_low = arm(**low)
    if upper == "R":
        return a_low, a_top
    return mirror(a_top), mirror(a_low)


def hip_hand(side="R", out=1.12, up=0.16, back=-0.05):
    """A fist on the hip, the elbow out."""
    a = arm(reach=(out, up, back), frame="hip", pole=(1, -0.1, 0.5), hand=(-10, 0, 0))
    return a if side == "R" else mirror(a)


# ---------------------------------------------------------------------------------------------------------------- gait


def swing_layer(cycle, t_left=0.0, envelope=None, hip_y=0.05, hip_y_phase=0.0, hip_x=0.07, hip_yaw=7.0, hip_roll=3.0, chest_yaw=9.0, chest_roll=3.2, arm_l=24.0, arm_r=24.0, arm_phase=0.04, elbow_base=0.0, elbow_gain=16.0, bob_pitch=0.8, head_keep=0.7):
    """The upper body's answer to the legs, for a left heel landing at t_left and every `cycle` after it. The pelvis drops at each landing, rides to
    the standing foot and turns with the stride; the chest counters it; the head keeps looking where it is going; each arm goes forward
    with the opposite leg, its elbow bending as it does."""
    tau = 2 * math.pi

    def layer(t, S):
        e = 1.0 if envelope is None else envelope(t)
        if e <= 0:
            return
        ph = (t - t_left) / cycle
        c1, s1 = math.cos(tau * ph), math.sin(tau * ph)
        two = math.cos(2 * tau * (ph - hip_y_phase))
        S["hip"] = S["hip"] + Vector((-hip_x * s1 * e, -hip_y * two * e, 0))
        S["hipr"] = S["hipr"] @ turn(bob_pitch * two * e, -hip_yaw * c1 * e, -hip_roll * s1 * e)
        S["spine"] = S["spine"] @ turn(-bob_pitch * 0.6 * two * e, chest_yaw * math.cos(tau * (ph - 0.03)) * e, chest_roll * math.sin(tau * (ph - 0.02)) * e)
        S["neck"] = S["neck"] @ turn(bob_pitch * 0.4 * two * e, -(chest_yaw - hip_yaw) * head_keep * c1 * e, -(chest_roll - hip_roll) * head_keep * s1 * e)
        sw = math.cos(tau * (ph - arm_phase))
        S["shL"] = qx(-arm_l * sw * e) @ S["shL"]
        S["shR"] = qx(arm_r * sw * e) @ S["shR"]
        S["elL"] = S["elL"] + (elbow_base + elbow_gain * max(0.0, -sw) ** 1.5) * e
        S["elR"] = S["elR"] + (elbow_base + elbow_gain * max(0.0, sw) ** 1.5) * e

    return layer


def walk_steps(clip, landings, along, ahead=0.9, width=0.48, toe_out=6.0, lift=0.14, heel=16.0, toe=34.0, peel=0.2, land=0.08, swing=None):
    """Steps across the ground while the root travels `along(t)` studs forward. landings: [(side, time)] in time order; each foot lands `ahead` of
    the root at its time, and lifts `swing` seconds before."""
    for side, t in landings:
        foot = clip.foot(side)
        sgn = -1 if side == "L" else 1
        sw = swing if swing is not None else 0.34
        foot.step(t - sw, t, sgn * width, -(along(t) + ahead), yaw=-sgn * toe_out, lift=lift, heel=heel, toe=toe, peel=peel, land=land)


def linear_path(t0, t1, distance, then=None):
    """The root's forward travel, f(t) in studs, for a straight constant-speed move (`then`: more of them after)."""

    def along(t):
        s = distance * clamp((t - t0) / (t1 - t0))
        if then:
            s += then(t)
        return s

    return along


def smooth_path(t0, t1, distance):
    return lambda t: distance * smooth((t - t0) / (t1 - t0))


def root_path(along, yaw=None):
    """A clip's path function from forward travel: the root's place in the ground frame, and its yaw."""
    return lambda t: (Vector((0, 0, -along(t))), 0.0 if yaw is None else yaw(t))


# ---------------------------------------------------------------------------------------------------------------- kneeling

KNEE_FOOT_Y = 0.5  # an ankle with the shin along the floor (the block leg is about a stud thick)
TOES_DOWN = (-42, 0, 0)  # the foot's turn with its toes on the floor behind


def kneel_both(clip, t0, t1, width=0.55, back=1.02, t_second=None, x_shift=(0, 0)):
    """Both feet go back and onto their toes as the body comes down, the second a beat after the first."""
    t2 = t_second if t_second is not None else t0
    clip.foot("L").move(t0, t1, (-width + x_shift[0], KNEE_FOOT_Y, back), TOES_DOWN)
    clip.foot("R").move(t2, t1 + (t2 - t0), (width + x_shift[1], KNEE_FOOT_Y, back), TOES_DOWN)


# ------------------------------------------------------------------------------------------------------------ turning over

def swing_over(clip, t0, t1, mid_y, ends):
    """The feet through a body turning over in the air: both swing out behind the hips at the halfway point, toes down, the way the body is turning. The
    straight way from above the hips to below them runs through the hips, and the legs flip there. mid_y: the hips' height off the floor at
    the halfway point. ends: (left, right), each (ankle position, foot turn)."""
    mid = (t0 + t1) / 2
    linear = lambda u: u  # (no stop at the halfway point)
    for side, sgn, (pos, rot) in (("L", -1, ends[0]), ("R", 1, ends[1])):
        foot = clip.foot(side)
        foot.move(t0, mid, (sgn * 0.5, mid_y, 2.0), (-90, 0, 0), ease=linear)
        foot.move(mid, t1, pos, rot, ease=linear)
