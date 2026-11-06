"""The R15 motion engine: runs inside Blender's Python (mathutils), and owes nothing to the viewport. r15_rig.py shows
and stores its result on a real armature; the clips (a project's clip files; example_clips.py) are written against this file.

Frames: everything is in Roblox's axes, x to the character's right, y up, z behind it (it faces -z). "Ground" space has its origin on the
floor under the root; a joint's Transform is Roblox's own (Part1 = Part0 * C0 * Transform * C1:Inverse()). The rig is the real one dumped
from Studio (<project>/animation/r15_rig.json, from `pipeline.py dump`).

How a clip becomes motion, 120 times a second:
  1. Tracks (sparse keys, auto-clamped cubic through the poses) give each channel's target.
  2. Layers add what no one keys by hand: breath, weight shift, tremble, a gait's bob and swing.
  3. Spring chains follow the targets, each segment in world space from its parent's result, so the head drags behind the chest, the
     forearm behind the upper arm and the hand behind the forearm: overlap, follow-through and settle, with continuous velocity.
  4. Exact two-bone IK puts the feet where their tracks say: a planted foot does not move at all, whatever the body does.
The result is sampled at 60 fps and thinned per joint to a tolerance too small to see (thin()).
"""
import bisect
import json
import math
import os
import random

from mathutils import Matrix, Quaternion, Vector

FPS = 60
SUB = 2  # physics steps per frame
# How lively every clip is:
LIVELY = 1.14  # the torso's and head's keyed turns, past what the key says
LIVELY_LIFE = 1.4  # how far a held body sways and shifts its weight (life())
LIVELY_BREATH = 1.25  # and how deep it breathes
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.environ.get("R15_MOTION_PROJECT") or os.getcwd()  # r15_rig.use_project sets it
RIG_PATH = os.path.join(PROJECT, "animation", "r15_rig.json")

JOINTS = [
    "LowerTorso", "UpperTorso", "Head",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
]
PARENT_OF = {
    "LowerTorso": "HumanoidRootPart", "UpperTorso": "LowerTorso", "Head": "UpperTorso",
    "LeftUpperArm": "UpperTorso", "LeftLowerArm": "LeftUpperArm", "LeftHand": "LeftLowerArm",
    "RightUpperArm": "UpperTorso", "RightLowerArm": "RightUpperArm", "RightHand": "RightLowerArm",
    "LeftUpperLeg": "LowerTorso", "LeftLowerLeg": "LeftUpperLeg", "LeftFoot": "LeftLowerLeg",
    "RightUpperLeg": "LowerTorso", "RightLowerLeg": "RightUpperLeg", "RightFoot": "RightLowerLeg",
}
ID = Quaternion((1, 0, 0, 0))
UP = Vector((0, 1, 0))


def qx(d):
    return Quaternion((1, 0, 0), math.radians(d))


def qy(d):
    return Quaternion((0, 1, 0), math.radians(d))


def qz(d):
    return Quaternion((0, 0, 1), math.radians(d))


def turn(pitch=0.0, yaw=0.0, roll=0.0):
    """A body's turn: pitch tips it forward, yaw turns it to its left, roll leans it to its left."""
    return qy(yaw) @ qx(-pitch) @ qz(roll)


def from_look_up(look, up):
    """A rotation from a Roblox CFrame's LookVector and UpVector (root space)."""
    z = -Vector(look).normalized()
    x = Vector(up).cross(z).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed().to_quaternion()


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def smoother(u):
    u = clamp(u)
    return u * u * u * (u * (u * 6 - 15) + 10)


def mix(a, b, u):
    return a + (b - a) * u


def arc(a, b):
    """The shortest turn taking direction a to direction b."""
    a, b = a.normalized(), b.normalized()
    d = a.dot(b)
    if d > 0.999999:
        return ID.copy()
    if d < -0.999999:
        axis = Vector((1, 0, 0)) if abs(a.x) < 0.9 else Vector((0, 0, 1))
        axis = a.cross(axis).normalized()
        return Quaternion(axis, math.pi)
    axis = a.cross(b)
    q = Quaternion((1 + d, axis.x, axis.y, axis.z))
    q.normalize()
    return q


class Rig:
    """The real R15's proportions."""

    def __init__(self, path=None):
        with open(path or RIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.raw = data
        self.floor = data["Floor"]
        self.c0, self.c1 = {}, {}
        for child, joint in data["Joints"].items():
            self.c0[child] = Vector(joint["C0"][:3])
            self.c1[child] = Vector(joint["C1"][:3])
            for c in (joint["C0"], joint["C1"]):
                if abs(c[3] - 1) > 1e-3 or abs(c[7] - 1) > 1e-3:
                    raise ValueError("a joint with a turned rest frame: " + child)
        self.size = {k: Vector(v["Size"]) for k, v in data["Parts"].items()}
        self.limbs = {}
        for side, s in (("L", "Left"), ("R", "Right")):
            self.limbs["arm" + side] = dict(
                upper=s + "UpperArm", lower=s + "LowerArm", tip=s + "Hand",
                U=self.c0[s + "LowerArm"] - self.c1[s + "UpperArm"],
                F=self.c0[s + "Hand"] - self.c1[s + "LowerArm"],
            )
            self.limbs["leg" + side] = dict(
                upper=s + "UpperLeg", lower=s + "LowerLeg", tip=s + "Foot",
                U=self.c0[s + "LowerLeg"] - self.c1[s + "UpperLeg"],
                F=self.c0[s + "Foot"] - self.c1[s + "LowerLeg"],
            )
        foot = self.size["LeftFoot"]
        self.ankle_height = self.c1["LeftFoot"].y + foot.y / 2  # the ankle above a flat sole
        self.foot_half = foot.z / 2 * 0.96
        self.hand_offset = self.c1["LeftHand"]  # the wrist in the hand's frame
        self.hip_height = self.c0["LowerTorso"].y - self.floor  # the pelvis pivot above the floor at rest

    def fk(self, pose):
        """pose: { joint: (quaternion, offset or None) }. Returns { part: (rotation, position) } in root space, the root at the origin."""
        out = {"HumanoidRootPart": (ID.copy(), Vector((0, 0, 0)))}
        for name in JOINTS:
            q, p = pose[name]
            pr, pp = out[PARENT_OF[name]]
            at = self.c0[name] if p is None else self.c0[name] + p
            r = pr @ q
            out[name] = (r, pp + pr @ at - r @ self.c1[name])
        return out


def two_bone(S, W, pole, U, F, flex):
    """The limb from joint S reaching W, its bend toward pole. flex: +1 an elbow (a positive turn about X), -1 a knee. Returns the upper
    segment's rotation in root space, the hinge's angle in degrees (signed) and how far short of W it stops."""
    d = W - S
    D = max(d.length, 1e-5)
    Fy = F.y
    c = 2 * U.y * Fy
    base = U.length_squared + F.length_squared
    Dmax = math.sqrt(base + c)
    soft = Dmax * 0.985  # lengthen less and less near full stretch: no pop as a limb locks out
    reach = D
    if D > soft:
        span = Dmax - soft
        reach = soft + span * (1 - math.exp(-(D - soft) / span))
    cos_theta = clamp((reach * reach - base) / c, -1.0, 1.0)
    theta = flex * math.acos(cos_theta)
    V = U + Vector((0, Fy * math.cos(theta), Fy * math.sin(theta)))
    a = V.normalized()
    x = Vector((1, 0, 0))
    b = (x - a * x.dot(a)).normalized()
    dn = d / D
    if flex > 0:
        h = pole.cross(dn)
    else:
        h = dn.cross(pole)
    if h.length < 1e-4:
        h = Vector((1, 0, 0)) - dn * dn.x
    h.normalize()
    world = Matrix((h, dn, h.cross(dn))).transposed()
    local = Matrix((b, a, b.cross(a))).transposed()
    return (world @ local.transposed()).to_quaternion(), math.degrees(theta), D - reach


# ---------------------------------------------------------------------------------------------------------------------- tracks


class Track:
    """Sparse keys through which a channel runs. A key's `ease` shapes the way TO it: "smooth" (the auto-clamped cubic: flat where the
    motion turns back or holds, carrying speed through a breakdown), "out" (fast start, long soft landing), "in" (slow start, hard
    arrival), "snap" (out, more so), "linear", "hold"."""

    def __init__(self, kind):
        self.kind = kind  # "quat", "vec" or "num"
        self.t, self.v, self.ease = [], [], []
        self.m = []
        self.period = None

    def add(self, t, value, ease="smooth"):
        value = tuple(value) if self.kind != "num" else (float(value),)
        i = bisect.bisect_left(self.t, t)
        if i < len(self.t) and abs(self.t[i] - t) < 1e-6:
            self.v[i], self.ease[i] = value, ease
        else:
            self.t.insert(i, t)
            self.v.insert(i, value)
            self.ease.insert(i, ease)

    def build(self, period=None):
        self.period = period
        n = len(self.t)
        if self.kind == "quat":
            for i in range(1, n):
                if sum(a * b for a, b in zip(self.v[i - 1], self.v[i])) < 0:
                    self.v[i] = tuple(-a for a in self.v[i])
        self.m = [None] * n
        if n < 2:
            self.m = [tuple(0.0 for _ in self.v[0])] * n if n else []
            return self
        dim = len(self.v[0])
        for i in range(n):
            if period is not None and (i == 0 or i == n - 1):
                # across the seam: the last key repeats the first
                dt0 = self.t[-1] - self.t[-2]
                dt1 = self.t[1] - self.t[0]
                prev, here, nxt = self.v[-2], self.v[0], self.v[1]
                if self.kind == "quat" and sum(a * b for a, b in zip(prev, here)) < 0:
                    prev = tuple(-a for a in prev)
            elif i == 0 or i == n - 1:
                self.m[i] = tuple(0.0 for _ in range(dim))
                continue
            else:
                dt0 = self.t[i] - self.t[i - 1]
                dt1 = self.t[i + 1] - self.t[i]
                prev, here, nxt = self.v[i - 1], self.v[i], self.v[i + 1]
            d0 = [(here[k] - prev[k]) / dt0 for k in range(dim)]
            d1 = [(nxt[k] - here[k]) / dt1 for k in range(dim)]
            if sum(a * b for a, b in zip(d0, d1)) <= 0:
                self.m[i] = tuple(0.0 for _ in range(dim))
                continue
            m = [(d0[k] * dt1 + d1[k] * dt0) / (dt0 + dt1) for k in range(dim)]
            size = math.sqrt(sum(a * a for a in m))
            limit = 3 * min(math.sqrt(sum(a * a for a in d0)), math.sqrt(sum(a * a for a in d1)))
            if size > limit > 0:
                m = [a * limit / size for a in m]
            self.m[i] = tuple(m)
        return self

    def at(self, t):
        ts = self.t
        n = len(ts)
        if n == 0:
            return None
        if self.period is not None:
            t = t % self.period
        if n == 1 or t <= ts[0]:
            return self._out(self.v[0])
        if t >= ts[-1]:
            return self._out(self.v[-1])
        i = bisect.bisect_right(ts, t) - 1
        t0, t1 = ts[i], ts[i + 1]
        h = t1 - t0
        u = (t - t0) / h
        ease = self.ease[i + 1]
        a, b = self.v[i], self.v[i + 1]
        if ease == "hold":
            return self._out(a)
        if ease == "smooth":
            ma, mb = self.m[i], self.m[i + 1]
            u2 = u * u
            u3 = u2 * u
            h00 = 2 * u3 - 3 * u2 + 1
            h10 = (u3 - 2 * u2 + u) * h
            h01 = -2 * u3 + 3 * u2
            h11 = (u3 - u2) * h
            return self._out(tuple(h00 * a[k] + h10 * ma[k] + h01 * b[k] + h11 * mb[k] for k in range(len(a))))
        if ease == "out":
            w = 1 - (1 - u) ** 2.4
        elif ease == "snap":
            w = 1 - (1 - u) ** 4.5
        elif ease == "in":
            w = u ** 2.4
        else:
            w = u
        return self._out(tuple(a[k] + (b[k] - a[k]) * w for k in range(len(a))))

    def _out(self, v):
        if self.kind == "quat":
            q = Quaternion(v)
            q.normalize()
            return q
        if self.kind == "vec":
            return Vector(v)
        return v[0]


# ---------------------------------------------------------------------------------------------------------------------- poses


def arm(dir=None, elbow=12.0, twist=0.0, hand=(0, 0, 0), reach=None, frame="chest", pole=None, handw=None, girdle=(0, 0, 0)):
    """An arm in a pose.
    Forward: dir (where the upper arm points, in the chest's space: x right, y up, z back), elbow (degrees of bend), twist (degrees it turns
    in about itself: positive brings a bent forearm across the body), hand (pitch, yaw, roll of the hand from the forearm).
    Inverse: reach (where the hand's centre goes), frame ("chest", "hip", "head", "root" or "ground"), pole (where the elbow points, in root
    space), handw (the hand's turn in root space instead of `hand`).
    Either: girdle (how far the shoulder itself comes in, up and forward, studs: a real shoulder moves, and a wide torso needs it)."""
    return dict(dir=dir, elbow=elbow, twist=twist, hand=hand, reach=reach, frame=frame, pole=pole, handw=handw, girdle=girdle)


def pose(hip=None, hipr=None, spine=None, neck=None, head=None, armL=None, armR=None, knees=None):
    """A key pose. Anything left out keeps its own channel's motion. hip: the pelvis's move from rest, studs (x right, y up, z back). hipr,
    spine, neck: (pitch forward, yaw left, roll left) in degrees; neck is from the chest; head instead gives the head's turn in root
    space, whatever the chest is doing. armL, armR: arm(). knees: (x, y, z) added to where both knees point."""
    return dict(hip=hip, hipr=hipr, spine=spine, neck=neck, head=head, armL=armL, armR=armR, knees=knees)


def mirror(a):
    """An arm() for the other side."""
    m = dict(a)
    for field in ("dir", "reach", "pole"):
        d = a.get(field)
        if d is not None:
            m[field] = (-d[0], d[1], d[2])
    for field in ("hand", "handw"):
        h = a.get(field)
        if h is not None and not isinstance(h, Quaternion):
            m[field] = (h[0], -h[1], -h[2])
    return m


class Foot:
    """Where a foot is, in ground space, over time. A planted foot is exactly still. The ankle sits above the sole; a step rolls off the
    toe, swings on a smooth arc and lands on the heel."""

    def __init__(self, rig, side):
        self.rig = rig
        self.side = side
        self.segs = []  # (t0, t1, f(t) -> (position, rotation)), in time order
        self.start = None
        self.contact = None

    def _flat(self, x, z, yaw):
        return Vector((x, self.rig.ankle_height, z)), qy(yaw)

    def plant(self, x, z, yaw=0.0, t=None):
        """Stands the foot flat at (x, z). With t, it jumps there at that moment (keep that for clips looping through it)."""
        state = self._flat(x, z, yaw)
        if t is None:
            self.start = state
        else:
            self.segs.append((t, t, lambda _t, s=state: s))
        self.contact = (x, z, yaw)
        return self

    def state(self, t):
        best = None
        for seg in self.segs:
            if seg[0] <= t:
                best = seg
            else:
                break
        if best is None:
            return self.start
        return best[2](min(t, best[1]))

    def _roll(self, x, z, yaw, pitch, pivot):
        """The foot turned `pitch` degrees toe-up about its heel (pivot +1), or toe-down about its toe (pivot -1), that edge on the floor."""
        h = self.rig.foot_half
        local = Vector((0, -self.rig.ankle_height, h * pivot))
        yq = qy(yaw)
        rot = yq @ qx(pitch)
        on_floor = Vector((x, 0, z)) + yq @ Vector((0, 0, h * pivot))
        return on_floor - rot @ local, rot

    def step(self, t0, t1, x, z, yaw=None, lift=0.3, heel=14.0, toe=28.0, peel=0.12, land=0.1, trail=1.0):
        """Lifts at t0 (the heel starts up `peel` before it), lands on its heel at t1, flat `land` after, at (x, z). trail above 1 keeps the foot
        behind longer before it comes through, as a runner's does."""
        x0, z0, yaw0 = self.contact
        yaw1 = yaw0 if yaw is None else yaw
        if peel > 0:
            a = t0 - peel

            def peel_f(t):
                u = (t - a) / peel
                return self._roll(x0, z0, yaw0, -toe * u * u, -1)

            self.segs.append((a, t0, peel_f))
            A0, _ = self._roll(x0, z0, yaw0, -toe, -1)
            before, _ = self._roll(x0, z0, yaw0, -toe * ((peel - 1 / 120) / peel) ** 2, -1)
            V0 = (A0 - before) * 120
            pitch0 = -toe
        else:
            A0, _ = self._flat(x0, z0, yaw0)
            V0 = Vector((0, 0, 0))
            pitch0 = 0.0
        if land > 0:
            A1, _ = self._roll(x, z, yaw1, heel, 1)
            V1 = Vector((0, -0.4, 0))
            pitch1 = heel
        else:
            A1, _ = self._flat(x, z, yaw1)
            V1 = Vector((0, 0, 0))
            pitch1 = 0.0
        h = t1 - t0

        def swing(t):
            u = clamp((t - t0) / h)
            v = u ** trail
            v2 = v * v
            v3 = v2 * v
            p = A0 * (2 * v3 - 3 * v2 + 1) + V0 * ((v3 - 2 * v2 + v) * h) + A1 * (-2 * v3 + 3 * v2) + V1 * ((v3 - v2) * h)
            if trail != 1.0:
                u2 = u * u
                u3 = u2 * u
                p.y = A0.y * (2 * u3 - 3 * u2 + 1) + V0.y * ((u3 - 2 * u2 + u) * h) + A1.y * (-2 * u3 + 3 * u2) + V1.y * ((u3 - u2) * h)
            # the lift peaks a little early: the toe clears, then the leg reaches
            p = p + Vector((0, lift * math.sin(math.pi * u ** 0.8) ** 2, 0))
            s = smooth(u)
            return p, qy(mix(yaw0, yaw1, s)) @ qx(mix(pitch0, pitch1, s))

        self.segs.append((t0, t1, swing))
        if land > 0:

            def land_f(t):
                u = (t - t1) / land
                return self._roll(x, z, yaw1, heel * (1 - u) ** 2, 1)

            self.segs.append((t1, t1 + land, land_f))
        self.contact = (x, z, yaw1)
        return self

    def move(self, t0, t1, pos, rot=(0, 0, 0), ease=smooth):
        """A free move to an ankle position (ground space) and a foot turn (toe-up pitch, yaw, roll), for kneeling and the like."""
        A0, R0 = self.state(t0)
        A1 = Vector(pos)
        R1 = qy(rot[1]) @ qx(rot[0]) @ qz(rot[2])

        def f(t):
            u = ease((t - t0) / (t1 - t0))
            return A0.lerp(A1, u), R0.slerp(R1, u)

        self.segs.append((t0, t1, f))
        self.contact = (A1.x, A1.z, rot[1])
        return self

    def fn(self, f):
        """The whole track from a function: f(t) -> (position, rotation). For gaits."""
        self.segs = [(-1e9, 1e9, f)]
        return self


# ---------------------------------------------------------------------------------------------------------------------- feel


class Feel:
    """Each segment's spring: (frequency in Hz, damping ratio). Lower frequency is heavier; lower damping overshoots further. None
    follows the target exactly."""

    def __init__(self, hip=(7.0, 0.85), pelvis=(7.0, 0.8), chest=(5.0, 0.72), head=(4.2, 0.62), upper=(4.6, 0.6), lower=(5.5, 0.52), hand=(7.5, 0.5)):
        self.hip, self.pelvis, self.chest, self.head, self.upper, self.lower, self.hand = hip, pelvis, chest, head, upper, lower, hand

    def scaled(self, k=1.0, damp=1.0):
        out = Feel()
        for name in ("hip", "pelvis", "chest", "head", "upper", "lower", "hand"):
            v = getattr(self, name)
            setattr(out, name, None if v is None else (v[0] * k, min(1.0, v[1] * damp)))
        return out


# (damped a little under what looks settled: each segment overshoots and swings back, so motion follows through and lands with a bounce)
NATURAL = Feel(hip=(6.6, 0.8), pelvis=(6.6, 0.74), chest=(4.6, 0.62), head=(3.9, 0.52), upper=(4.2, 0.5), lower=(5.0, 0.44), hand=(7.0, 0.4))
HEAVY = Feel(hip=(4.8, 0.8), pelvis=(4.8, 0.74), chest=(3.5, 0.62), head=(3.0, 0.52), upper=(3.2, 0.52), lower=(3.9, 0.46), hand=(5.6, 0.42))
CRISP = Feel(hip=(9.5, 0.8), pelvis=(9.5, 0.76), chest=(7.4, 0.62), head=(6.0, 0.5), upper=(7.4, 0.52), lower=(8.8, 0.46), hand=(11.0, 0.42))


def _lead(s):
    return 0.0 if s is None else 2 * s[1] / (2 * math.pi * s[0])


class QSpring:
    """A rotation following a target, in world space."""

    __slots__ = ("q", "w", "k", "c", "free")

    def __init__(self, spec, q):
        self.q = q.copy()
        self.w = Vector((0, 0, 0))
        self.free = spec is None
        if spec is not None:
            om = 2 * math.pi * spec[0]
            self.k, self.c = om * om, 2 * spec[1] * om

    def follow(self, target, dt):
        if self.free:
            self.q = target
            return target
        e = target @ self.q.conjugated()
        if e.w < 0:
            e = Quaternion((-e.w, -e.x, -e.y, -e.z))
        sin_half = math.sqrt(e.x * e.x + e.y * e.y + e.z * e.z)
        if sin_half > 1e-7:
            angle = 2 * math.atan2(sin_half, e.w)
            scale = angle / sin_half
            ex, ey, ez = e.x * scale, e.y * scale, e.z * scale
        else:
            ex, ey, ez = 2 * e.x, 2 * e.y, 2 * e.z
        w = self.w
        w.x += dt * (self.k * ex - self.c * w.x)
        w.y += dt * (self.k * ey - self.c * w.y)
        w.z += dt * (self.k * ez - self.c * w.z)
        size = w.length
        if size > 1e-7:
            self.q = Quaternion(w / size, size * dt) @ self.q
            self.q.normalize()
        return self.q


class VSpring:
    __slots__ = ("p", "v", "k", "c", "free")

    def __init__(self, spec, p):
        self.p = p.copy()
        self.v = Vector((0, 0, 0))
        self.free = spec is None
        if spec is not None:
            om = 2 * math.pi * spec[0]
            self.k, self.c = om * om, 2 * spec[1] * om

    def follow(self, target, dt):
        if self.free:
            self.p = target
            return target
        self.v += ((target - self.p) * self.k - self.v * self.c) * dt
        self.p = self.p + self.v * dt
        return self.p


# ---------------------------------------------------------------------------------------------------------------------- clip


class Clip:
    def __init__(self, rig, name, seconds, loop=False, priority="Action4", feel=NATURAL, only=None, stance=(0.5, 0.5), toe_out=6.0, ignore=(), audit=None, lively=LIVELY):
        self.rig, self.name, self.seconds, self.loop = rig, name, seconds, loop
        self.lively = lively
        self.priority, self.feel, self.only = priority, feel, only
        self.ignore, self.audit = list(ignore), audit or {}
        self.tracks = {
            "hip": Track("vec"), "hipr": Track("quat"), "spine": Track("quat"), "neck": Track("quat"),
            "shL": Track("quat"), "shR": Track("quat"), "elL": Track("num"), "elR": Track("num"),
            "wrL": Track("quat"), "wrR": Track("quat"), "knees": Track("vec"), "gL": Track("vec"), "gR": Track("vec"),
        }
        self.feet = {"L": Foot(rig, "L").plant(-stance[0], 0, toe_out), "R": Foot(rig, "R").plant(stance[1], 0, -toe_out)}
        self.layers = []
        self.keys = []  # (t, pose, ease, lag)
        self.markers = []
        self.path = None  # f(t) -> (position in ground space, yaw): the root's own travel, made by the game, not this clip
        self.handfn = {}  # side -> f(t, hip, pelvis, chest) -> (hand centre in root space, turn in root space, elbow pole, weight)

    # authoring ------------------------------------------------------------------------------------------------------
    def key(self, t, p, ease="smooth", lag=None):
        """Puts pose p at t seconds. lag: { "hip" | "spine" | "neck" | "armL" | "armR": seconds } moves that part of it later or earlier."""
        self.keys.append((t, p, ease, lag or {}))
        return self

    def layer(self, f):
        self.layers.append(f)
        return self

    def marker(self, name, t):
        self.markers.append((name, t))
        return self

    def foot(self, side):
        return self.feet[side]

    # building -------------------------------------------------------------------------------------------------------
    def _turn(self, angles):
        """A keyed body turn, pushed a little past itself (LIVELY)."""
        k = self.lively
        return turn(*(a * k for a in angles))

    def _resolve_keys(self):
        order = sorted(self.keys, key=lambda k: k[0])
        tr = self.tracks
        period = self.seconds if self.loop else None
        for t, p, ease, lag in order:
            if p.get("hip") is not None:
                x, y, z = p["hip"]
                tr["hip"].add(t + lag.get("hip", 0.0), (x * self.lively, y, z * self.lively), ease)
            if p.get("hipr") is not None:
                tr["hipr"].add(t + lag.get("hip", 0.0), self._turn(p["hipr"]), ease)
            if p.get("spine") is not None:
                tr["spine"].add(t + lag.get("spine", 0.0), self._turn(p["spine"]), ease)
            if p.get("knees") is not None:
                tr["knees"].add(t, p["knees"], ease)
        for name in ("hip", "hipr", "spine", "knees"):
            if not tr[name].t:
                tr[name].add(0, Vector((0, 0, 0)) if name in ("hip", "knees") else ID)
            tr[name].build(period)
        for t, p, ease, lag in order:
            chest = self._chest_at(t)
            if p.get("neck") is not None:
                tr["neck"].add(t + lag.get("neck", 0.0), self._turn(p["neck"]), ease)
            elif p.get("head") is not None:
                tr["neck"].add(t + lag.get("neck", 0.0), chest[0].conjugated() @ self._turn(p["head"]), ease)
        if not tr["neck"].t:
            tr["neck"].add(0, ID)
        tr["neck"].build(period)
        for t, p, ease, lag in order:
            for side, key in (("L", "armL"), ("R", "armR")):
                a = p.get(key)
                if a is None:
                    continue
                sh, el, wr = self._solve_arm(side, a, t)
                at = t + lag.get(key, 0.0)
                tr["sh" + side].add(at, sh, ease)
                tr["el" + side].add(at, el, ease)
                tr["wr" + side].add(at, wr, ease)
                tr["g" + side].add(at, self._girdle(side, a), ease)
        for name in ("shL", "shR", "elL", "elR", "wrL", "wrR", "gL", "gR"):
            if not tr[name].t:
                tr[name].add(0, 8.0 if tr[name].kind == "num" else Vector((0, 0, 0)) if tr[name].kind == "vec" else ID)
            tr[name].build(period)

    def _chest_at(self, t):
        """The chest's rotation and position in root space at t, from the keyed torso alone (then the pelvis's)."""
        rig = self.rig
        hq = self.tracks["hipr"].at(t)
        hp = self.tracks["hip"].at(t)
        chest_r = hq @ self.tracks["spine"].at(t)
        pelvis_p = rig.c0["LowerTorso"] + hp - hq @ rig.c1["LowerTorso"]
        waist = pelvis_p + hq @ rig.c0["UpperTorso"]
        return chest_r, waist - chest_r @ rig.c1["UpperTorso"], hq, pelvis_p

    def _frame(self, a, t):
        chest_r, chest_p, hip_r, hip_p = self._chest_at(t)
        frame = a["frame"]
        if frame == "chest":
            return chest_r, chest_p
        if frame == "hip":
            return hip_r, hip_p
        if frame == "head":
            r = chest_r @ self.tracks["neck"].at(t)
            at = chest_p + chest_r @ self.rig.c0["Head"]
            return r, at - r @ self.rig.c1["Head"]
        if frame == "ground":
            return ID, Vector((0, self.rig.floor, 0))
        if frame == "root":
            return ID, Vector((0, 0, 0))
        raise ValueError(frame)

    @staticmethod
    def _hand_turn(a):
        h = a["handw"]
        return h if isinstance(h, Quaternion) else turn(*h)

    @staticmethod
    def _girdle(side, a):
        g = a.get("girdle") or (0, 0, 0)
        return Vector((g[0] if side == "L" else -g[0], g[1], -g[2]))

    def _solve_arm(self, side, a, t):
        rig = self.rig
        sgn = -1 if side == "L" else 1
        names = rig.limbs["arm" + side]
        chest_r, chest_p, _, _ = self._chest_at(t)
        if a.get("reach") is None:
            d = Vector(a["dir"]).normalized()
            if d.dot(UP) > 0.9999:
                d = Vector((sgn * 0.01, 1, -0.01)).normalized()
            sh = arc(Vector((0, -1, 0)), d) @ qy(sgn * a.get("twist", 0.0))
            el = a.get("elbow", 12.0)
            lower_r = chest_r @ sh @ qx(el)
            if a.get("handw") is not None:
                wr = lower_r.conjugated() @ self._hand_turn(a)
            else:
                wr = turn(*a.get("hand", (0, 0, 0)))
            return sh, el, wr
        fr, fp = self._frame(a, t)
        target = fp + fr @ Vector(a["reach"])
        pole = Vector(a["pole"]) if a.get("pole") is not None else Vector((sgn * 0.6, -0.5, 0.7))
        shoulder = chest_p + chest_r @ rig.c0[names["upper"]]
        wrist = target.copy()
        extra = self._girdle(side, a)
        slide = extra.copy()
        sh, el, wr = ID, 0.0, ID
        for _ in range(3):
            S = shoulder + chest_r @ slide
            upper_r, el, _short = two_bone(S, wrist, pole, names["U"], names["F"], 1)
            sh = chest_r.conjugated() @ upper_r
            lower_r = upper_r @ qx(el)
            if a.get("handw") is not None:
                hand_r = self._hand_turn(a)
                wr = lower_r.conjugated() @ hand_r
            else:
                wr = turn(*a.get("hand", (0, 0, 0)))
                hand_r = lower_r @ wr
            wrist = target + hand_r @ rig.hand_offset
            slide = self._slide(sh, sgn) + extra
        return sh, el, wr

    @staticmethod
    def _slide(sh, sgn):
        """The shoulder girdle: a raised arm's shoulder lifts and slides out, which also keeps a block arm out of the head (an R15 shoulder
        turns about the arm's inner face). A forward arm's shoulder comes forward."""
        d = sh @ Vector((0, -1, 0))
        e = smooth((d.y + 0.35) / 1.3)
        return Vector((sgn * 0.42 * e, 0.14 * e, -0.10 * max(0.0, -d.z) * (1 - e)))

    def targets(self, t):
        f = self.feel
        tr = self.tracks
        S = {
            "hip": tr["hip"].at(t + _lead(f.hip)),
            "hipr": tr["hipr"].at(t + _lead(f.pelvis)),
            "spine": tr["spine"].at(t + _lead(f.chest)),
            "neck": tr["neck"].at(t + _lead(f.head)),
            "shL": tr["shL"].at(t + _lead(f.upper)), "shR": tr["shR"].at(t + _lead(f.upper)),
            "elL": tr["elL"].at(t + _lead(f.lower)), "elR": tr["elR"].at(t + _lead(f.lower)),
            "wrL": tr["wrL"].at(t + _lead(f.hand)), "wrR": tr["wrR"].at(t + _lead(f.hand)),
            "knees": tr["knees"].at(t),
            "gL": tr["gL"].at(t + _lead(f.upper)), "gR": tr["gR"].at(t + _lead(f.upper)),
        }
        for layer in self.layers:
            layer(t, S)
        return S


def scan_timing(clip):
    """A keyed value runs from the last key that set it, so a pose that leaves a channel out lets that channel start moving long before its
    beat: an arm drifting for ten seconds, or a "snap" that fires a second early. Lists the segments that look like it (the clip's keys must be
    resolved). Each is either meant, or wants a hold key where the move should start."""

    def size(track, a, b):
        if track.kind == "quat":
            return math.degrees(2 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, b))))))
        if track.kind == "num":
            return abs(a[0] - b[0])
        return 100 * math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    found = []
    for name, track in clip.tracks.items():
        for i in range(len(track.t) - 1):
            span = track.t[i + 1] - track.t[i]
            ease = track.ease[i + 1]
            move = size(track, track.v[i], track.v[i + 1])
            if (ease in ("snap", "out", "in") and span > 0.7 and move > 6) or (ease == "smooth" and span > 1.6 and move > 15):
                found.append("%s %.2f-%.2f %s %.0f" % (name, track.t[i], track.t[i + 1], ease, move))
    return found


def thin(values, angle_tol=0.12, pos_tol=0.0025, max_gap=12):
    """Per-joint Douglas-Peucker over frames: the fewest keys whose straight lines stay within tolerance, as Roblox plays them."""
    n = len(values)
    keep = {0, n - 1}
    stack = [(0, n - 1)]
    cos_tol = 1 - math.cos(math.radians(angle_tol) / 2)
    while stack:
        a, b = stack.pop()
        span = b - a
        if span < 2:
            continue
        qa, pa = values[a]
        qb, pb = values[b]
        worst, at = -1.0, None
        for i in range(a + 1, b):
            u = (i - a) / span
            q, p = values[i]
            err = (1 - abs(qa.slerp(qb, u).dot(q))) / cos_tol
            if p is not None:
                err = max(err, (pa.lerp(pb, u) - p).length / pos_tol)
            if err > worst:
                worst, at = err, i
        if worst > 1.0 or span > max_gap:
            if worst <= 1.0:
                at = a + span // 2
            keep.add(at)
            stack.append((a, at))
            stack.append((at, b))
    return sorted(keep)


def bake(clip):
    """Runs the clip. Returns { Name, Fps, Frames, Loop, Priority, Length, Joints: { joint: [per-frame (q, p or None)] }, ... }."""
    rig = clip.rig
    clip._resolve_keys()
    feel = clip.feel
    frames = int(round(clip.seconds * FPS))
    dt = 1.0 / (FPS * SUB)
    S = clip.targets(0.0)

    # the state at the start
    hipp = VSpring(feel.hip, S["hip"])
    pelvis = QSpring(feel.pelvis, S["hipr"])
    chest = QSpring(feel.chest, S["hipr"] @ S["spine"])
    head = QSpring(feel.head, chest.q @ S["neck"])
    upper, lower, hand = {}, {}, {}
    for side in "LR":
        upper[side] = QSpring(feel.upper, chest.q @ S["sh" + side])
        lower[side] = QSpring(feel.lower, upper[side].q @ qx(S["el" + side]))
        hand[side] = QSpring(feel.hand, lower[side].q @ S["wr" + side])

    out = {j: [] for j in JOINTS}
    warm = int(round(2 * clip.seconds * FPS * SUB)) if clip.loop else 0
    total = frames * SUB
    hip_mid = rig.c1["LowerTorso"]
    side_names = {"L": "Left", "R": "Right"}
    short, short_at = 0.0, 0.0
    for step in range(-warm, total + 1):
        t = step * dt
        tw = t % clip.seconds if clip.loop else max(t, 0.0)
        S = clip.targets(tw)
        hp = hipp.follow(S["hip"], dt)
        pq = pelvis.follow(S["hipr"], dt)
        cq = chest.follow(pq @ S["spine"], dt)
        hq = head.follow(cq @ S["neck"], dt)
        for side in "LR":
            fn = clip.handfn.get(side)
            sh_t, el_t, wr_t = S["sh" + side], S["el" + side], S["wr" + side]
            if fn is not None:
                sh_t, el_t, wr_t = _hand_ik(clip, side, fn, tw, hp, pq, cq, sh_t, el_t, wr_t)
            u = upper[side].follow(cq @ sh_t, dt)
            l = lower[side].follow(u @ qx(el_t), dt)
            hand[side].follow(l @ wr_t, dt)
        if step < 0 or step % SUB:
            continue

        # the frame's joints
        out["LowerTorso"].append((pq.copy(), hp.copy()))
        out["UpperTorso"].append((pq.conjugated() @ cq, None))
        out["Head"].append((cq.conjugated() @ hq, None))
        for side in "LR":
            s = side_names[side]
            sgn = -1 if side == "L" else 1
            sh = cq.conjugated() @ upper[side].q
            out[s + "UpperArm"].append((sh, Clip._slide(sh, sgn) + S["g" + side]))
            el = upper[side].q.conjugated() @ lower[side].q
            bent = _hinge(el)
            out[s + "LowerArm"].append((bent, None))
            # (the hand from the forearm as it is kept, not as the spring left it)
            out[s + "Hand"].append(((upper[side].q @ bent).conjugated() @ hand[side].q, None))

        # the legs, exactly
        rq = ID
        rp = Vector((0, 0, 0))
        if clip.path is not None:
            rp, ryaw = clip.path(tw)
            rq = qy(-ryaw)
        pelvis_p = rig.c0["LowerTorso"] + hp - pq @ hip_mid
        for side in "LR":
            s = side_names[side]
            names = rig.limbs["leg" + side]
            A, R = clip.feet[side].state(tw)
            ankle = rq @ (A - rp) + Vector((0, rig.floor, 0))
            foot_r = rq @ R
            hipj = pelvis_p + pq @ rig.c0[names["upper"]]
            fwd = foot_r @ Vector((0, 0, -1))
            fwd.y = 0
            # (a foot pointing nearly straight up or down has no forward of its own: flat, its forward swaps ends as it turns over, which
            # would swap the knee in one frame, so the pelvis's forward takes over there)
            own = min(1.0, fwd.length / 0.4)
            hf = pq @ Vector((0, 0, -1))
            pole = fwd.normalized() * 0.65 * own + hf * 0.35 + S["knees"]
            ur, theta, sh = two_bone(hipj, ankle, pole, names["U"], names["F"], -1)
            if sh > short:
                short, short_at = sh, tw
            out[s + "UpperLeg"].append((pq.conjugated() @ ur, None))
            knee = qx(theta)
            out[s + "LowerLeg"].append((knee, None))
            out[s + "Foot"].append(((ur @ knee).conjugated() @ foot_r, None))
    return dict(
        Name=clip.name, Fps=FPS, Frames=frames, Loop=clip.loop, Priority=clip.priority, Length=frames / FPS,
        Joints=out, Only=clip.only, Ignore=clip.ignore, Audit=clip.audit,
        Markers=[(n, round(t * FPS)) for n, t in clip.markers], Short=short, ShortAt=short_at, Timing=scan_timing(clip),
    )


def _hinge(q):
    """An elbow's turn, kept nearly a hinge: its bend about X, never backward, with only a little of the spring's sideways give."""
    sin_half, w = q.x, q.w
    if w < 0:
        w, sin_half = -w, -sin_half
    angle = 2 * math.atan2(sin_half, w)
    bend = qx(max(0.0, math.degrees(angle)))
    rest = bend.conjugated() @ q
    if rest.w < 0:
        rest = Quaternion((-rest.w, -rest.x, -rest.y, -rest.z))
    return bend @ ID.slerp(rest, 0.35)


def _hand_ik(clip, side, fn, t, hp, pq, cq, sh_t, el_t, wr_t):
    rig = clip.rig
    place = fn(t, hp, pq, cq)
    if place is None:
        return sh_t, el_t, wr_t
    target, hand_r, pole, weight = place
    if weight <= 0:
        return sh_t, el_t, wr_t
    sgn = -1 if side == "L" else 1
    names = rig.limbs["arm" + side]
    pelvis_p = rig.c0["LowerTorso"] + hp - pq @ rig.c1["LowerTorso"]
    waist = pelvis_p + pq @ rig.c0["UpperTorso"]
    chest_p = waist - cq @ rig.c1["UpperTorso"]
    shoulder = chest_p + cq @ rig.c0[names["upper"]]
    wrist = target + hand_r @ rig.hand_offset
    slide = Clip._slide(sh_t, sgn)
    sh, el, ur = sh_t, el_t, cq @ sh_t
    for _ in range(2):
        S = shoulder + cq @ slide
        ur, el, _short = two_bone(S, wrist, pole, names["U"], names["F"], 1)
        sh = cq.conjugated() @ ur
        slide = Clip._slide(sh, sgn)
    wr = (ur @ qx(el)).conjugated() @ hand_r
    if weight >= 1:
        return sh, el, wr
    return sh_t.slerp(sh, weight), mix(el_t, el, weight), wr_t.slerp(wr, weight)


# ---------------------------------------------------------------------------------------------------------------------- layers


def noise(seed, low=0.15, high=0.6, count=4, period=None):
    """Sums of sines: smooth, unrepeating and, with a period, seamless. Stays within -1..1."""
    rng = random.Random(seed)
    terms = []
    for i in range(count):
        f = low * (high / low) ** (i / max(1, count - 1)) * rng.uniform(0.85, 1.15)
        if period:
            f = max(1, round(f * period)) / period
        terms.append((2 * math.pi * f, rng.uniform(0, 2 * math.pi), 1 / (1 + i * 0.6)))
    size = sum(a for _, _, a in terms)
    terms = [(w, ph, a / size) for w, ph, a in terms]

    def f(t):
        total = 0.0
        for w, ph, a in terms:
            total += a * math.sin(w * t + ph)
        return total

    return f


def life(seed=1, breath=4.2, depth=1.0, sway=1.0, period=None, envelope=None):
    """What a living body does while it holds still: breathing through the chest and shoulders, a slow shift of weight, a head that is never
    quite still. depth and sway scale it; envelope(t) fades it (a 0-to-1 function)."""
    if period:
        breath = period / max(1, round(period / breath))
    nx = noise(seed * 11 + 1, 0.11, 0.42, 4, period)
    nz = noise(seed * 11 + 2, 0.09, 0.38, 4, period)
    ny = noise(seed * 11 + 3, 0.13, 0.5, 3, period)
    nyaw = noise(seed * 11 + 4, 0.1, 0.33, 3, period)
    hp = noise(seed * 11 + 5, 0.2, 0.9, 4, period)
    hy = noise(seed * 11 + 6, 0.15, 0.7, 4, period)
    hr = noise(seed * 11 + 7, 0.17, 0.6, 3, period)
    al = noise(seed * 11 + 8, 0.2, 0.8, 3, period)
    ar = noise(seed * 11 + 9, 0.2, 0.8, 3, period)

    def layer(t, S):
        e = 1.0 if envelope is None else envelope(t)
        if e <= 0:
            return
        # breathing in is quicker than breathing out
        ph = (t / breath) % 1.0
        b = (1 - math.cos(math.pi * ph / 0.42)) / 2 if ph < 0.42 else (1 + math.cos(math.pi * (ph - 0.42) / 0.58)) / 2
        b *= depth * e * LIVELY_BREATH
        s = sway * e * LIVELY_LIFE
        S["hip"] = S["hip"] + Vector((nx(t) * 0.05 * s, (b - 0.5 * depth * e * LIVELY_BREATH) * 0.006 + ny(t) * 0.008 * s, nz(t) * 0.035 * s))
        S["hipr"] = S["hipr"] @ turn(nz(t) * 0.5 * s, nyaw(t) * 0.7 * s, -nx(t) * 0.6 * s)
        S["spine"] = S["spine"] @ turn(-b * 1.1 + ny(t) * 0.4 * s, -nyaw(t) * 0.5 * s, nx(t) * 0.5 * s)
        # the head holds its line against the chest's breath, and wanders a little
        S["neck"] = S["neck"] @ turn(b * 0.7 + hp(t) * 0.9 * s, hy(t) * 1.2 * s, hr(t) * 0.5 * s)
        # shoulders ride up on the breath; the arms hang and drift
        S["shL"] = turn(0, 0, b * 0.5) @ S["shL"] @ turn(al(t) * 0.7 * s, 0, al(t + 3.1) * 0.5 * s)
        S["shR"] = turn(0, 0, -b * 0.5) @ S["shR"] @ turn(ar(t) * 0.7 * s, 0, ar(t + 3.1) * 0.5 * s)
        S["elL"] = S["elL"] + al(t + 1.7) * 1.2 * s
        S["elR"] = S["elR"] + ar(t + 1.7) * 1.2 * s

    return layer


def tremble(seed, amount, envelope, speed=9.0):
    """A shudder running through the body: amount in degrees, envelope(t) from 0 to 1."""
    a, b, c, d = (noise(seed * 7 + i, speed * 0.6, speed * 1.4, 4) for i in range(4))

    def layer(t, S):
        e = envelope(t)
        if e <= 0:
            return
        k = amount * e
        S["spine"] = S["spine"] @ turn(a(t) * k, b(t) * k * 0.6, c(t) * k * 0.5)
        S["neck"] = S["neck"] @ turn(c(t) * k * 0.5, d(t) * k * 0.5, a(t) * k * 0.3)
        S["shL"] = S["shL"] @ turn(b(t) * k * 0.5, 0, d(t) * k * 0.4)
        S["shR"] = S["shR"] @ turn(d(t) * k * 0.5, 0, b(t) * k * 0.4)
        S["hip"] = S["hip"] + Vector((c(t) * k * 0.004, a(t) * k * 0.003, b(t) * k * 0.003))

    return layer


def window(t0, t1, fade_in=0.15, fade_out=0.25):
    """An envelope: 1 between t0 and t1, easing up and down at its ends."""

    def f(t):
        return smooth((t - t0) / fade_in) * (1 - smooth((t - t1) / fade_out))

    return f


# ---------------------------------------------------------------------------------------------------------------------- export


def check_points(rig, result, count=7):
    """Where forward kinematics puts every part at a few frames: Studio plays the clip and must agree (import_clip.luau)."""
    frames = result["Frames"]
    out = []
    for i in range(count):
        f = round(i * frames / (count - 1))
        posed = rig.fk({j: result["Joints"][j][f] for j in JOINTS})
        out.append(dict(F=f, P={j: list(posed[j][1]) for j in JOINTS}))
    return out


def encode(result, rig=None):
    """The clip for Studio (import_clip.luau): thinned, quaternions and offsets as numbers."""
    joints = {}
    count = 0
    for name, values in result["Joints"].items():
        if result["Only"] and name not in result["Only"]:
            continue
        needs_p = any(p is not None for _, p in values)
        frames = thin(values)
        count += len(frames)
        q, p = [], []
        for f in frames:
            qv, pv = values[f]
            q += [qv.x, qv.y, qv.z, qv.w]
            if needs_p:
                p += list(pv)
        joints[name] = {"F": frames, "Q": q, "P": p if needs_p else None}
    return dict(
        Name=result["Name"], Fps=result["Fps"], Frames=result["Frames"], Loop=result["Loop"], Priority=result["Priority"],
        Joints=joints, Markers=result["Markers"], Keys=count, Ignore=result["Ignore"], Audit=result["Audit"],
        Check=check_points(rig, result) if rig and not result["Only"] else [],
    )
