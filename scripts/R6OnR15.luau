--!strict
-- R6-like animation on a real R15 rig ("fake R6", "R6 on R15", "R15 R6 animation"): every part and proportion stays R15, but
-- only six joints move, and each limb moves as one rigid block about R6's pivot, so FK, IK and clips behave as they do on an R6.
-- Everything here speaks R6: a pose is { [R6 part name] = that joint's R6 Transform }, the same numbers an R6 clip holds.
-- Run in Edit (references/animation/r6-on-r15.md):
--
--   map(rig)                    reads an R15's joints and body; everything below takes this map
--   toR15 / fromR15             one joint's R6 Transform <-> the R15 Transform that moves its block the same way
--   fk(map, pose)               a pose -> { [R15 part] = Transform }, the locked joints held at identity
--   reach(map, limb, target)    IK: the limb's Transform that puts its tip on a point: an aim, then a slide along the limb
--   plant(map, leg, at)         IK: a leg's Transform with its foot's lowest corner on the floor at x, z
--   settle(map, pose, legs)     body IK: the pose with the torso raised or lowered onto the floor
--   world(map, pose)            where each R15 part ends up, in the root's space
--   clip(map, keys, options)    keys of poses -> a KeyframeSequence on the 60 fps grid
--   retarget(map, source)       an R6 clip -> its R15 KeyframeSequence, sampled from the engine
--   plantFeet(map, sequence, track)   every key's legs reach for where a Blender clip's foot IK targets were (r6_rig.feet)
--   defaults(map, parent)       Roblox's whole default R6 set (DEFAULTS), retargeted
--   verify(map, rig, source, sequence)   plays both through the engine and measures how far R15 strays from the R6 source
--   check(map, sequence)        the joint policy: six joints move, the nine locked ones stay at identity
--   dump(map)                   the body's R6 pivots and tips as plain data, for r6_on_r15.py in Blender
--   wire(animate, ids, options) published clip ids into an R15 Animate script's slots and animNames, retuned to R6's speeds
--
-- retarget, defaults and verify step the engine by hand, which Studio allows only in Edit. A clip fits the proportions of the rig
-- it was built on: it plays on any R15 with the same turns, but rebuild it for an exact fit where a limb slides far.

local AnimationClipProvider = game:GetService("AnimationClipProvider")
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")
local Players = game:GetService("Players")

local R6OnR15 = {}

export type Pose = { [string]: CFrame } -- R6 part name -> R6 Transform
type Joint = { Item: any, Parent: string, C0: CFrame, C1: CFrame }
export type Role = {
	Joint: string, -- the R15 part whose joint plays this R6 joint
	Locked: { string }, -- the R15 parts carried rigidly, their joints held at identity
	Frame: CFrame, -- the R15 joint's frame at rest, in the root's space
	Turn: CFrame, -- R6's joint axes (the rotation of its C0, which its C1 shares)
	Pivot: Vector3, -- where R6 turns this block, on this body, in the root's space
	Scale: number, -- R15 studs per R6 stud for this joint's slides
	Tip: Vector3, -- the limb's working end at rest: a hand's end, a sole's centre
}
export type Map = {
	Rig: Model,
	Joints: { [string]: Joint },
	Rest: { [string]: CFrame }, -- each part at rest, in the root's space
	Sizes: { [string]: Vector3 },
	Roles: { [string]: Role },
	Floor: number, -- the floor's height in the root's space
}
export type Key = { Time: number?, Frame: number?, Pose: Pose, Style: Enum.PoseEasingStyle?, Direction: Enum.PoseEasingDirection? }
export type ClipOptions = { Name: string?, Loop: boolean?, Priority: Enum.AnimationPriority?, Parent: Instance?, Fps: number? }
export type ReachOptions = {
	Torso: CFrame?, -- the torso's R6 Transform in this pose
	From: CFrame?, -- the joint's own Transform to start from: the swing is the smallest from it, so it sets the limb's roll
	Tip: Vector3?, -- the point on the limb to place, at rest in the root's space (default its tip)
	Slide: number?, -- how far the limb may slide along itself to reach (default: as far as R6's stock clips go; 0 only aims)
	Twist: number?, -- radians about the limb, after the aim
	Floor: number?, -- plant: the floor's height (default the map's)
}
export type RetargetOptions = {
	R6: Model?, -- a scriptless R6 to sample on, to reuse across clips
	Name: string?,
	Parent: Instance?,
	Fps: number?, -- key grid (default 60)
	Degrees: number?, -- how far a thinned curve may stray in rotation (default 0.2)
	Studs: number?, -- and in position (default 0.003)
	Thin: boolean?, -- false keeps a key every frame: needed before editing keys afterwards (plantFeet), since thinning judges
	-- the R6 source alone and dropped a quick step's lifted frame, which planting then turned into a 0.65-stud slide
}
-- A Blender clip's feet (r6_rig.feet): each leg's IK target a frame from 0, { x, z, lift } in studs right and back of the
-- root and above the floor; Rest the targets' { x, z } at rest; Fps the frames' rate (default 60).
export type FootTrack = { Feet: { [string]: { { number } } }, Rest: { [string]: { number } }, Fps: number? }
export type Finding = { Rule: string, Detail: string }

local FPS = 60
local HOLD = "__R6OnR15" -- the folder that holds sampling rigs while they work
local R6_LEFT, R6_RIGHT = CFrame.new(0, 0, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), CFrame.new(0, 0, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0)
local R6_BODY = CFrame.new(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)
local PARTS = {
	Torso = { Joint = "LowerTorso", Locked = { "UpperTorso" }, Turn = R6_BODY },
	Head = { Joint = "Head", Locked = {}, Turn = R6_BODY },
	["Left Arm"] = { Joint = "LeftUpperArm", Locked = { "LeftLowerArm", "LeftHand" }, Turn = R6_LEFT, Side = -1, Slide = 1 },
	["Right Arm"] = { Joint = "RightUpperArm", Locked = { "RightLowerArm", "RightHand" }, Turn = R6_RIGHT, Side = 1, Slide = 1 },
	["Left Leg"] = { Joint = "LeftUpperLeg", Locked = { "LeftLowerLeg", "LeftFoot" }, Turn = R6_LEFT, Side = -1, Slide = 1.6 },
	["Right Leg"] = { Joint = "RightUpperLeg", Locked = { "RightLowerLeg", "RightFoot" }, Turn = R6_RIGHT, Side = 1, Slide = 1.6 },
}
local R6_HEIGHT = 2 -- an R6 limb or torso, in studs
local FEET = { ["Left Leg"] = "LeftFoot", ["Right Leg"] = "RightFoot" }

-- Roblox's default R6 Animate script, slot by slot: { name, asset id, the R15 Animate group, the slot's place in that group }.
R6OnR15.DEFAULTS = {
	{ Name = "idle", Id = 180435571, Group = "idle", Slot = 1, Weight = 9 },
	{ Name = "idle2", Id = 180435792, Group = "idle", Slot = 2, Weight = 1 },
	{ Name = "walk", Id = 180426354, Group = "walk", Slot = 1 }, -- also its run: R6 has no run clip of its own
	{ Name = "jump", Id = 125750702, Group = "jump", Slot = 1 },
	{ Name = "fall", Id = 180436148, Group = "fall", Slot = 1 },
	{ Name = "climb", Id = 180436334, Group = "climb", Slot = 1 },
	{ Name = "sit", Id = 178130996, Group = "sit", Slot = 1 },
	{ Name = "toolnone", Id = 182393478, Group = "toolnone", Slot = 1 },
	{ Name = "toolslash", Id = 129967390, Group = "toolslash", Slot = 1 },
	{ Name = "toollunge", Id = 129967478, Group = "toollunge", Slot = 1 },
	{ Name = "wave", Id = 128777973, Group = "wave", Slot = 1 },
	{ Name = "point", Id = 128853357, Group = "point", Slot = 1 },
	{ Name = "dance1", Id = 182435998, Group = "dance", Slot = 1 },
	{ Name = "dance1b", Id = 182491037, Group = "dance", Slot = 2 },
	{ Name = "dance1c", Id = 182491065, Group = "dance", Slot = 3 },
	{ Name = "dance2", Id = 182436842, Group = "dance2", Slot = 1 },
	{ Name = "dance2b", Id = 182491248, Group = "dance2", Slot = 2 },
	{ Name = "dance2c", Id = 182491277, Group = "dance2", Slot = 3 },
	{ Name = "dance3", Id = 182436935, Group = "dance3", Slot = 1 },
	{ Name = "dance3b", Id = 182491368, Group = "dance3", Slot = 2 },
	{ Name = "dance3c", Id = 182491423, Group = "dance3", Slot = 3 },
	{ Name = "laugh", Id = 129423131, Group = "laugh", Slot = 1 },
	{ Name = "cheer", Id = 129423030, Group = "cheer", Slot = 1 },
}

local function readJoints(model: Model): { [string]: Joint }
	local found: { [string]: Joint } = {}
	for _, item in model:GetDescendants() do
		if item:IsA("Motor6D") and item.Part0 and item.Part1 then
			found[(item.Part1 :: BasePart).Name] = { Item = item, Parent = (item.Part0 :: BasePart).Name, C0 = item.C0, C1 = item.C1 }
		elseif item:IsA("AnimationConstraint") then
			local a0, a1 = item.Attachment0, item.Attachment1
			if a0 and a1 and a0.Parent and a1.Parent and a0.Parent:IsA("BasePart") and a1.Parent:IsA("BasePart") then
				found[a1.Parent.Name] = { Item = item, Parent = a0.Parent.Name, C0 = a0.CFrame, C1 = a1.CFrame }
			end
		end
	end
	return found
end

-- The box around some parts at rest, in the root's space, as its centre and size.
local function box(rest: { [string]: CFrame }, sizes: { [string]: Vector3 }, names: { string }): (Vector3, Vector3)
	local low, high = Vector3.one * math.huge, -Vector3.one * math.huge
	for _, name in names do
		local half = sizes[name] / 2
		for _, x in { -1, 1 } do
			for _, y in { -1, 1 } do
				for _, z in { -1, 1 } do
					local corner = rest[name] * Vector3.new(half.X * x, half.Y * y, half.Z * z)
					low, high = low:Min(corner), high:Max(corner)
				end
			end
		end
	end
	return (low + high) / 2, high - low
end

function R6OnR15.map(rig: Model): Map
	local joints = readJoints(rig)
	local rootPart = (rig:FindFirstChild("HumanoidRootPart") or rig.PrimaryPart) :: BasePart?
	assert(rootPart, "the rig has no HumanoidRootPart")
	local rootName = (rootPart :: BasePart).Name
	local missing = {}
	for _, part in PARTS do
		for _, name in { part.Joint, table.unpack(part.Locked) } do
			if not joints[name] then
				table.insert(missing, name)
			end
		end
	end
	assert(#missing == 0, "not an R15 with all 15 joints; missing: " .. table.concat(missing, ", "))

	local rest: { [string]: CFrame } = { [rootName] = CFrame.identity }
	local sizes: { [string]: Vector3 } = { [rootName] = (rootPart :: BasePart).Size }
	local function restOf(name: string): CFrame
		local known = rest[name]
		if known then
			return known
		end
		local joint = joints[name]
		assert(joint, "no joint reaches " .. name)
		local value = restOf(joint.Parent) * joint.C0 * joint.C1:Inverse()
		rest[name] = value
		return value
	end
	for name in joints do
		restOf(name)
		local part = rig:FindFirstChild(name)
		assert(part and part:IsA("BasePart"), "no part named " .. name)
		sizes[name] = (part :: BasePart).Size
	end

	local torsoCentre, torsoSize = box(rest, sizes, { "LowerTorso", "UpperTorso" })
	local function jointFrame(name: string): CFrame
		local joint = joints[name]
		return rest[joint.Parent] * joint.C0
	end
	local roles: { [string]: Role } = {}
	local legScale = 1
	for _, name in { "Left Leg", "Right Leg", "Left Arm", "Right Arm", "Head", "Torso" } do
		local part = PARTS[name]
		local frame = jointFrame(part.Joint)
		local parts = { part.Joint, table.unpack(part.Locked) }
		-- The head's tip is a point in front of the face: reaching for a target makes it look there.
		local pivot, scale, tip = frame.Position, torsoSize.Y / R6_HEIGHT, frame.Position - Vector3.zAxis
		if name == "Torso" then
			pivot, scale = torsoCentre, legScale -- by the legs' scale, so a crouch that keeps R6's feet down keeps these down
		elseif name == "Left Leg" or name == "Right Leg" then
			local centre, size = box(rest, sizes, parts)
			local bottom = centre.Y - size.Y / 2
			-- R6's hip sits on the leg's outer face, at the torso's underside: spreading a leg lowers its foot.
			pivot = Vector3.new(centre.X + (part.Side :: number) * size.X / 2, frame.Position.Y, frame.Position.Z)
			tip = Vector3.new(centre.X, bottom, centre.Z)
			scale = (frame.Position.Y - bottom) / R6_HEIGHT
			legScale = scale
		elseif name == "Left Arm" or name == "Right Arm" then
			local centre, size = box(rest, sizes, parts)
			-- R6's shoulder sits on the arm's inner face, a quarter of the way down: a raised hand stops where R6's does.
			pivot = Vector3.new(centre.X - (part.Side :: number) * size.X / 2, centre.Y + size.Y / 4, centre.Z)
			tip = Vector3.new(centre.X, centre.Y - size.Y / 2, centre.Z)
			scale = size.Y / R6_HEIGHT
		end
		roles[name] = { Joint = part.Joint, Locked = part.Locked, Frame = frame, Turn = part.Turn, Pivot = pivot, Scale = scale, Tip = tip }
	end

	local humanoid = rig:FindFirstChildOfClass("Humanoid")
	local lowest = math.huge
	for _, foot in { "LeftFoot", "RightFoot" } do
		local centre, size = box(rest, sizes, { foot })
		lowest = math.min(lowest, centre.Y - size.Y / 2)
	end
	local floor = if humanoid then -(sizes[rootName].Y / 2 + humanoid.HipHeight) else lowest
	return { Rig = rig, Joints = joints, Rest = rest, Sizes = sizes, Roles = roles, Floor = floor }
end

-- An R6 Transform as the motion it makes in the body's axes: a turn about R6's pivot and a shift.
local function motion(role: Role, transform: CFrame): (CFrame, Vector3)
	local body = role.Turn * transform * role.Turn:Inverse()
	return body.Rotation, body.Position
end

local function transformOf(role: Role, turn: CFrame, shift: Vector3): CFrame
	return role.Turn:Inverse() * (CFrame.new(shift) * turn) * role.Turn
end

-- The block's motion in the torso's rest space (the root's, for the torso): the same turn, about this body's R6 pivot.
local function blockMotion(role: Role, transform: CFrame): CFrame
	local turn, shift = motion(role, transform)
	return CFrame.new(role.Pivot + shift * role.Scale) * turn * CFrame.new(-role.Pivot)
end

function R6OnR15.toR15(map: Map, name: string, transform: CFrame): CFrame
	local role = assert(map.Roles[name], "not an R6 part: " .. name)
	return role.Frame:Inverse() * blockMotion(role, transform) * role.Frame
end

function R6OnR15.fromR15(map: Map, name: string, transform: CFrame): CFrame
	local role = assert(map.Roles[name], "not an R6 part: " .. name)
	local moved = role.Frame * transform * role.Frame:Inverse()
	local turn = moved.Rotation
	return transformOf(role, turn, (moved.Position - role.Pivot + turn * role.Pivot) / role.Scale)
end

function R6OnR15.fk(map: Map, pose: Pose): { [string]: CFrame }
	local out: { [string]: CFrame } = {}
	for name, transform in pose do
		local role = assert(map.Roles[name], "not an R6 part: " .. name)
		out[role.Joint] = R6OnR15.toR15(map, name, transform)
		for _, locked in role.Locked do
			out[locked] = CFrame.identity
		end
	end
	return out
end

-- Each R15 part in the root's space for a pose; parts of limbs the pose leaves out stay at rest on the torso.
function R6OnR15.world(map: Map, pose: Pose): { [string]: CFrame }
	local torso = if pose.Torso then blockMotion(map.Roles.Torso, pose.Torso) else CFrame.identity
	local out: { [string]: CFrame } = {}
	for name, role in map.Roles do
		local block = if name == "Torso" then torso elseif pose[name] then torso * blockMotion(role, pose[name]) else torso
		out[role.Joint] = block * map.Rest[role.Joint]
		for _, locked in role.Locked do
			out[locked] = block * map.Rest[locked]
		end
	end
	return out
end

-- The smallest turn taking unit vector a to unit vector b.
local function between(a: Vector3, b: Vector3): CFrame
	local dot = math.clamp(a:Dot(b), -1, 1)
	if dot > 1 - 1e-9 then
		return CFrame.identity
	end
	if dot < -1 + 1e-9 then
		local helper = if math.abs(a.X) < 0.9 then Vector3.xAxis else Vector3.yAxis
		return CFrame.fromAxisAngle(a:Cross(helper).Unit, math.pi)
	end
	return CFrame.fromAxisAngle(a:Cross(b).Unit, math.acos(dot))
end

-- IK for a rigid limb. It has one joint and no bend, so it aims about R6's pivot, then slides along itself for the distance an
-- aim cannot cover, which is how R6's own clips fake a knee or an elbow. `target` is in the root's space. Returns the R6
-- Transform, how far the tip stopped from the target, and the slide used.
function R6OnR15.reach(map: Map, limb: string, target: Vector3, options: ReachOptions?): (CFrame, number, number)
	local settings: ReachOptions = options or {}
	local role = assert(map.Roles[limb], "not an R6 part: " .. limb)
	assert(limb ~= "Torso", "the torso is not a limb: use settle")
	local torso = if settings.Torso then blockMotion(map.Roles.Torso, settings.Torso) else CFrame.identity
	local goal = torso:Inverse() * target
	local tip = settings.Tip or role.Tip
	local seedTurn = motion(role, settings.From or CFrame.identity)
	local start = seedTurn * (tip - role.Pivot)
	local wanted = goal - role.Pivot
	if wanted.Magnitude < 1e-6 or start.Magnitude < 1e-6 then
		return settings.From or CFrame.identity, (goal - (role.Pivot + start)).Magnitude, 0
	end
	local axis = wanted.Unit
	local turn = between(start.Unit, axis) * seedTurn
	if settings.Twist then
		turn = CFrame.fromAxisAngle(axis, settings.Twist) * turn
	end
	local limit = settings.Slide or (PARTS[limb].Slide :: number?) or 0
	local slide = math.clamp(wanted.Magnitude - start.Magnitude, -limit, limit)
	local shift = axis * slide
	local missed = (goal - (role.Pivot + shift + turn * (tip - role.Pivot))).Magnitude
	return transformOf(role, turn, shift / role.Scale), missed, slide
end

-- The lowest corner of a leg's foot under a block's motion.
local function footLow(map: Map, leg: string, block: CFrame): number
	local foot = FEET[leg]
	local half, at = map.Sizes[foot] / 2, block * map.Rest[foot]
	return at.Position.Y - math.abs(at.RightVector.Y) * half.X - math.abs(at.UpVector.Y) * half.Y - math.abs(at.LookVector.Y) * half.Z
end

-- IK onto the floor: a rigid leg tips with its hip, so its foot rests on one corner, not flat. Puts the sole's centre over `at`
-- (x and z in the root's space; y is ignored) with that lowest corner on the floor.
function R6OnR15.plant(map: Map, leg: string, at: Vector3, options: ReachOptions?): (CFrame, number, number)
	assert(FEET[leg], "not an R6 leg: " .. leg)
	local settings: ReachOptions = options or {}
	local floor = settings.Floor or map.Floor
	local role = map.Roles[leg]
	local torso = if settings.Torso then blockMotion(map.Roles.Torso, settings.Torso) else CFrame.identity
	local height, transform, missed, slide = floor, CFrame.identity, 0, 0
	for _ = 1, 6 do
		transform, missed, slide = R6OnR15.reach(map, leg, Vector3.new(at.X, height, at.Z), settings)
		height += floor - footLow(map, leg, torso * blockMotion(role, transform))
	end
	return transform, missed, slide
end

-- Body IK: the pose with its torso moved straight up or down so the lowest of `legs` (default both) meets the floor, keeping
-- each foot's height from the torso. A shared height seats one foot: plant the other for both.
function R6OnR15.settle(map: Map, pose: Pose, legs: { string }?, floor: number?): Pose
	local role = map.Roles.Torso
	local torso = if pose.Torso then blockMotion(role, pose.Torso) else CFrame.identity
	local lowest = math.huge
	for _, leg in legs or { "Left Leg", "Right Leg" } do
		local limb = if pose[leg] then blockMotion(map.Roles[leg], pose[leg]) else CFrame.identity
		lowest = math.min(lowest, footLow(map, leg, torso * limb))
	end
	local turn, shift = motion(role, pose.Torso or CFrame.identity)
	local out = table.clone(pose)
	out.Torso = transformOf(role, turn, shift + Vector3.yAxis * ((floor or map.Floor) - lowest) / role.Scale)
	return out
end

-- Writes one keyframe's pose tree. `root`: whether the tree may start at the root part: a clip without one, such as R6's
-- toolslash, binds no root joint, so whatever plays beneath keeps moving the body.
local function writeKey(map: Map, sequence: KeyframeSequence, time: number, joints: { [string]: CFrame }, root: boolean, style: Enum.PoseEasingStyle?, direction: Enum.PoseEasingDirection?)
	local key = Instance.new("Keyframe")
	key.Time = time
	local made: { [string]: Pose } = {}
	local function ensure(name: string): Instance
		local existing = made[name]
		if existing then
			return existing
		end
		local joint = map.Joints[name]
		local parent: Instance = if joint and (root or map.Joints[joint.Parent]) then ensure(joint.Parent) else key
		local pose = Instance.new("Pose")
		pose.Name = name
		pose.CFrame = joints[name] or CFrame.identity
		pose.Weight = if joints[name] then 1 else 0
		pose.EasingStyle = style or Enum.PoseEasingStyle.Linear
		pose.EasingDirection = direction or Enum.PoseEasingDirection.In
		pose.Parent = parent
		made[name] = pose
		return pose
	end
	for name in joints do
		ensure(name)
	end
	key.Parent = sequence
end

local function newSequence(options: ClipOptions): KeyframeSequence
	local sequence = Instance.new("KeyframeSequence")
	sequence.Name = options.Name or "R6OnR15"
	sequence.Loop = options.Loop == true
	sequence.Priority = options.Priority or Enum.AnimationPriority.Action
	return sequence
end

-- Hand-authored keys in R6's language. Each key has `Frame` (on the 60 fps grid) or `Time`, and a `Pose`; a joint a key leaves out
-- is interpolated between the keys that have it. Locked joints are held for every limb the clip touches.
function R6OnR15.clip(map: Map, keys: { Key }, options: ClipOptions?): KeyframeSequence
	local settings: ClipOptions = options or {}
	local rate = settings.Fps or FPS
	local sequence = newSequence(settings)
	for _, key in keys do
		local time = if key.Frame then key.Frame / rate else assert(key.Time, "a key needs Frame or Time")
		writeKey(map, sequence, time, R6OnR15.fk(map, key.Pose), true, key.Style, key.Direction)
	end
	sequence.Parent = settings.Parent
	return sequence
end

local function holder(): Instance
	local existing = workspace:FindFirstChild(HOLD)
	if existing then
		return existing
	end
	local folder = Instance.new("Folder")
	folder.Name = HOLD
	folder.Parent = workspace
	return folder
end

local function dispose(model: Model)
	model:Destroy()
	local folder = workspace:FindFirstChild(HOLD)
	if folder and #folder:GetChildren() == 0 then
		folder:Destroy()
	end
end

local function scriptless(model: Model): Model
	for _, item in model:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			item:Destroy()
		end
	end
	local root = (model:FindFirstChild("HumanoidRootPart") or model.PrimaryPart) :: BasePart
	root.Anchored = true
	model:PivotTo(CFrame.new(0, 1150, -240))
	model.Parent = holder()
	return model
end

local function r6Rig(): Model
	local description = Instance.new("HumanoidDescription")
	local rig = Players:CreateHumanoidModelFromDescription(description, Enum.HumanoidRigType.R6)
	description:Destroy()
	return scriptless(rig)
end

-- A copy to change. What the providers return is cached and shared: destroying it empties that id for the rest of the session.
local function sourceSequence(source: any): KeyframeSequence
	if typeof(source) == "Instance" and (source :: Instance):IsA("KeyframeSequence") then
		return (source :: KeyframeSequence):Clone()
	end
	local text = tostring(source)
	local id = if string.find(text, "://", 1, true) then text else "rbxassetid://" .. text
	local clip = AnimationClipProvider:GetAnimationClipAsync(id)
	assert(clip:IsA("KeyframeSequence"), "not a KeyframeSequence: " .. id)
	return (clip :: KeyframeSequence):Clone()
end

-- Every joint's Transform at each time, as the engine evaluates it, so easing and partly keyed joints need no reimplementing.
local function sample(model: Model, sequence: KeyframeSequence, times: { number }): { { [string]: CFrame } }
	local humanoid = model:FindFirstChildOfClass("Humanoid") :: Instance?
	local controller = humanoid or model:FindFirstChildOfClass("AnimationController")
	assert(controller, "the rig has no Humanoid or AnimationController")
	local animator = (controller :: Instance):FindFirstChildOfClass("Animator") :: Animator?
	if not animator then
		local made = Instance.new("Animator")
		made.Parent = controller
		animator = made
	end
	local active = animator :: Animator
	local animation = Instance.new("Animation")
	animation.AnimationId = KeyframeSequenceProvider:RegisterKeyframeSequence(sequence)
	local track = active:LoadAnimation(animation)
	local waited = 0
	while track.Length <= 0 and waited < 10 do
		waited += task.wait()
	end
	assert(track.Length > 0, "the clip did not load")
	track.Looped = false
	track:Play(0, 1, 0)
	local joints = readJoints(model)
	local frames = {}
	for index, t in times do
		track.TimePosition = math.min(t, track.Length - 1e-4)
		active:StepAnimations(0.001)
		local frame: { [string]: CFrame } = {}
		for name, joint in joints do
			frame[name] = joint.Item.Transform
		end
		frames[index] = frame
	end
	track:Stop(0)
	track:Destroy()
	animation:Destroy()
	return frames
end

local function lastTime(sequence: KeyframeSequence): number
	local last = 0
	for _, key in sequence:GetKeyframes() do
		last = math.max(last, (key :: Keyframe).Time)
	end
	return last
end

-- The R6 parts a clip keys at all: only these get R15 poses, so what it leaves out keeps playing from the clips beneath.
local function keyed(sequence: KeyframeSequence): ({ [string]: boolean }, boolean)
	local names: { [string]: boolean } = {}
	local root = false
	for _, item in sequence:GetDescendants() do
		if item:IsA("Pose") then
			if PARTS[item.Name] then
				names[item.Name] = true
			elseif item.Name == "HumanoidRootPart" then
				root = true
			end
		end
	end
	return names, root
end

local function angleBetween(a: CFrame, b: CFrame): number
	local _, angle = (a:ToObjectSpace(b)):ToAxisAngle()
	angle = math.abs(angle) % (2 * math.pi)
	return if angle > math.pi then 2 * math.pi - angle else angle
end

-- Which frames a linear curve needs so no joint strays from the samples by more than the tolerances.
local function thin(series: { { [string]: CFrame } }, joints: { string }, degrees: number, studs: number): { number }
	local keep = { [1] = true, [#series] = true }
	local tolerance = math.rad(degrees)
	local function split(a: number, b: number)
		local worst, at = 1, nil
		for f = a + 1, b - 1 do
			local alpha = (f - a) / (b - a)
			for _, name in joints do
				local curve = series[a][name]:Lerp(series[b][name], alpha)
				local actual = series[f][name]
				local err = math.max(angleBetween(curve, actual) / tolerance, (curve.Position - actual.Position).Magnitude / studs)
				if err > worst then
					worst, at = err, f
				end
			end
		end
		if at then
			keep[at] = true
			split(a, at)
			split(at, b)
		end
	end
	split(1, #series)
	local frames = {}
	for f in keep do
		table.insert(frames, f)
	end
	table.sort(frames)
	return frames
end

-- An R6 clip as an R15 KeyframeSequence, with the source's length, loop and priority. The R6 motion comes from the engine at
-- every frame of the grid, then keys only where the curve needs them. Rotation keeps R6's numbers; pivots and slides come from
-- this body.
function R6OnR15.retarget(map: Map, source: any, options: RetargetOptions?): KeyframeSequence
	local settings: RetargetOptions = options or {}
	local rate = settings.Fps or FPS
	local copy = sourceSequence(source)
	local rig = settings.R6 or r6Rig()
	local length = lastTime(copy)
	local count = math.max(1, math.round(length * rate))
	local times = {}
	for f = 0, count do
		times[f + 1] = length * f / count
	end
	local samples = sample(rig, copy, times)
	local names, root = keyed(copy)
	local series: { { [string]: CFrame } } = {}
	local moving: { string } = {}
	for name in names do
		table.insert(moving, map.Roles[name].Joint)
	end
	for f, frame in samples do
		local joints: { [string]: CFrame } = {}
		for name in names do
			joints[map.Roles[name].Joint] = R6OnR15.toR15(map, name, frame[name] or CFrame.identity)
		end
		series[f] = joints
	end
	-- A loop's closing frame is its first: the engine reads the last key at the very end, which is then the wrap.
	if copy.Loop then
		series[#series] = series[1]
	end
	local sequence = newSequence({ Name = settings.Name or copy.Name, Loop = copy.Loop, Priority = copy.Priority })
	local frames = if settings.Thin == false then {} else thin(series, moving, settings.Degrees or 0.2, settings.Studs or 0.003)
	if settings.Thin == false then
		for f = 1, #series do
			frames[f] = f
		end
	end
	for index, f in frames do
		local joints = table.clone(series[f])
		for name in names do
			local role = map.Roles[name]
			-- The waist sits between the torso and every arm, so it has a pose at every key. The others need one at each end:
			-- identity to identity holds them at identity all through, over anything playing beneath.
			for _, locked in role.Locked do
				if index == 1 or index == #frames or locked == "UpperTorso" then
					joints[locked] = CFrame.identity
				end
			end
		end
		writeKey(map, sequence, (f - 1) / rate, joints, root)
	end
	copy:Destroy()
	if not settings.R6 then
		dispose(rig)
	end
	sequence.Parent = settings.Parent
	return sequence
end

-- The foot targets at `time`, between the frames either side.
local function trackAt(track: { { number } }, time: number, fps: number): (number, number, number)
	local at = math.clamp(time * fps, 0, #track - 1)
	local i = math.floor(at)
	local a, b = track[i + 1], track[math.min(i + 1, #track - 1) + 1]
	local f = at - i
	return a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f
end

-- After retarget (Thin = false): each key's legs reach for their IK targets (plant: aimed from the hip and slid along the leg,
-- R6's fake knee), the sole that far off the floor. An R6 rig's legs are rigid, so in a crouch they miss their targets and the
-- soles sink 0.2-0.5 studs; switching a floor fix on and off by contact spans popped legs 34-51 degrees at every step, and
-- planting every key toward the targets gave no slide and no pop. The targets are measured from the R6 rig's rest; the R15's
-- feet stand where this body puts them. Returns the furthest any foot stopped short of its target (studs).
function R6OnR15.plantFeet(map: Map, sequence: KeyframeSequence, track: FootTrack): number
	local fps = track.Fps or FPS
	local rest = R6OnR15.world(map, {})
	local worst = 0
	for _, key in sequence:GetKeyframes() do
		local poses: { [string]: Pose } = {}
		for _, item in key:GetDescendants() do
			if item:IsA("Pose") then
				poses[item.Name] = item
			end
		end
		local lower = poses[map.Roles.Torso.Joint]
		local body = if lower then R6OnR15.fromR15(map, "Torso", lower.CFrame) else CFrame.identity
		for leg, foot in FEET do
			local hip = poses[map.Roles[leg].Joint]
			local feet, from = track.Feet[leg], track.Rest[leg]
			if hip and feet and from then
				local x, z, lift = trackAt(feet, (key :: Keyframe).Time, fps)
				local home = rest[foot].Position
				local at = Vector3.new(home.X + x - from[1], 0, home.Z + z - from[2])
				local planted, missed = R6OnR15.plant(map, leg, at, { Torso = body, From = R6OnR15.fromR15(map, leg, hip.CFrame), Floor = map.Floor + lift })
				hip.CFrame = R6OnR15.toR15(map, leg, planted)
				worst = math.max(worst, missed)
			end
		end
	end
	return worst
end

-- Roblox's whole default R6 set, retargeted: { [DEFAULTS name] = KeyframeSequence }, each named after its slot.
function R6OnR15.defaults(map: Map, parent: Instance?): { [string]: KeyframeSequence }
	local rig = r6Rig()
	local out: { [string]: KeyframeSequence } = {}
	for _, entry in R6OnR15.DEFAULTS do
		out[entry.Name] = R6OnR15.retarget(map, entry.Id, { R6 = rig, Name = entry.Name, Parent = parent })
		task.wait()
	end
	dispose(rig)
	return out
end

-- Plays the R6 source on an R6 and the sequence on a copy of `rig`, both through the engine at every frame, and reads the R15's
-- joints back as R6 numbers. Returns the worst differences: Degrees of turn and Studs of slide (in R6 studs), with the joint and
-- moment, and Locked, the largest turn any locked joint made.
function R6OnR15.verify(map: Map, rig: Model, source: any, sequence: KeyframeSequence, options: RetargetOptions?): { [string]: any }
	local settings: RetargetOptions = options or {}
	local rate = settings.Fps or FPS
	local copy = sourceSequence(source)
	local r6 = settings.R6 or r6Rig()
	local archivable = rig.Archivable
	rig.Archivable = true
	local target = scriptless(rig:Clone())
	rig.Archivable = archivable
	local length, ownLength = lastTime(copy), lastTime(sequence)
	local count = math.max(1, math.round(length * rate))
	-- The closing frame is skipped: a loop's closes by design, on the first pose.
	local sourceTimes, ownTimes = {}, {}
	for f = 0, count - 1 do
		sourceTimes[f + 1] = length * f / count
		ownTimes[f + 1] = ownLength * f / count
	end
	local before, after = sample(r6, copy, sourceTimes), sample(target, sequence, ownTimes)
	local names = keyed(copy)
	local report: { [string]: any } = { Degrees = 0, Studs = 0, Locked = 0, DegreesAt = "", StudsAt = "" }
	for f in before do
		for name in names do
			local role = map.Roles[name]
			local wanted, got = before[f][name], R6OnR15.fromR15(map, name, after[f][role.Joint])
			local degrees = math.deg(angleBetween(wanted, got))
			local studs = (wanted.Position - got.Position).Magnitude
			if degrees > report.Degrees then
				report.Degrees, report.DegreesAt = degrees, string.format("%s at %.3f s", name, sourceTimes[f])
			end
			if studs > report.Studs then
				report.Studs, report.StudsAt = studs, string.format("%s at %.3f s", name, sourceTimes[f])
			end
			for _, locked in role.Locked do
				report.Locked = math.max(report.Locked, math.deg(angleBetween(after[f][locked], CFrame.identity)), (after[f][locked].Position).Magnitude)
			end
		end
	end
	copy:Destroy()
	if not settings.R6 then
		dispose(r6)
	end
	dispose(target)
	return report
end

-- The joint policy, read from a sequence's own poses: nothing but the six joints moves, and no pose scales or names a part the rig
-- lacks. Returns the findings and a line of text.
function R6OnR15.check(map: Map, sequence: KeyframeSequence): ({ Finding }, string)
	local allowed: { [string]: boolean } = {}
	for _, role in map.Roles do
		allowed[role.Joint] = true
	end
	local locked: { [string]: boolean } = {}
	local unknown: { [string]: boolean } = {}
	local moved: { [string]: boolean } = {}
	for _, key in sequence:GetKeyframes() do
		for _, item in key:GetDescendants() do
			if item:IsA("Pose") then
				local name, cf = item.Name, item.CFrame
				if not map.Rest[name] then
					unknown[name] = true
				elseif allowed[name] then
					moved[name] = moved[name] or cf ~= CFrame.identity
				elseif map.Joints[name] and (cf.Position.Magnitude > 1e-3 or angleBetween(cf, CFrame.identity) > math.rad(0.01)) then
					locked[name] = true
				end
			end
		end
	end
	local findings: { Finding } = {}
	for name in locked do
		table.insert(findings, { Rule = "locked", Detail = name .. " left identity" })
	end
	for name in unknown do
		table.insert(findings, { Rule = "unknown", Detail = name .. " is not on this rig" })
	end
	table.sort(findings, function(a, b)
		return a.Detail < b.Detail
	end)
	local count = 0
	for _, did in moved do
		count += if did then 1 else 0
	end
	return findings, string.format("%s: %d of 6 joints move, %d problems", sequence.Name, count, #findings)
end

-- The map's R6 pivots and tips as plain data (HttpService:JSONEncode it for r6_on_r15.py), in the root's space.
function R6OnR15.dump(map: Map): { [string]: any }
	local roles: { [string]: any } = {}
	for name, role in map.Roles do
		roles[name] = {
			joint = role.Joint,
			locked = role.Locked,
			pivot = { role.Pivot.X, role.Pivot.Y, role.Pivot.Z },
			tip = { role.Tip.X, role.Tip.Y, role.Tip.Z },
			scale = role.Scale,
		}
	end
	return { rootHeight = -map.Floor, roles = roles }
end

-- Published ids into an R15 Animate script's slots: `ids` is { [DEFAULTS name] = id }. R6 has one locomotion clip, so run takes the
-- walk's id, and it swims with its walk and idle. R15's Animate tunes its speeds to its own clips (locomotion at speed * 1.25 / 16
-- with a walk-to-run blend, climbing at speed / 5), which runs R6's walk about 13% fast and its climb over twice as fast, so its
-- source is retuned to R6's speed / 14.5 and speed / 12. That takes effect when the script next starts: wire a copy that has not
-- started yet (StarterCharacterScripts, in Edit). `R6Tempo = false` leaves the tempo alone.
-- Animate reads its slots only while StarterPlayer.AllowCustomAnimations is true (Avatar animations: Player Choice); under
-- Standard it plays the animNames table in its source instead. So every group it fills is written there too, copied from the
-- slots with their Weight values (1 where a slot has none, as Animate reads it): Standard then plays the same clips. Returns what
-- it filled, retuned and rewrote.
local function slotsOf(value: Instance): { Animation }
	local slots = {}
	for _, child in value:GetChildren() do
		if child:IsA("Animation") then
			table.insert(slots, child)
		end
	end
	table.sort(slots, function(a, b)
		return a.Name < b.Name
	end)
	return slots
end

local function writeAnimNames(script: any, groups: { [string]: boolean }): string
	local source = script.Source
	local _, head = string.find(source, "local animNames%s*=%s*")
	local open, close = string.find(source, "%b{}", (head or 0) + 1)
	if not head or open ~= head + 1 then
		return "not found: animNames"
	end
	local written = {}
	local block = string.gsub(string.sub(source, open, close), "(\n%s*)([%w_]+)(%s*=%s*)(%b{})", function(indent, name, equals, body)
		local value = groups[name] and script:FindFirstChild(name)
		if not value then
			return indent .. name .. equals .. body
		end
		local lines = {}
		for _, animation in slotsOf(value) do
			local weight = animation:FindFirstChild("Weight")
			table.insert(lines, string.format('%s\t{ id = "%s", weight = %s }', indent, animation.AnimationId, tostring(if weight then (weight :: any).Value else 1)))
		end
		table.insert(written, name)
		return indent .. name .. equals .. "{" .. table.concat(lines, ",") .. indent .. "}"
	end)
	script.Source = string.sub(source, 1, open - 1) .. block .. string.sub(source, close + 1)
	table.sort(written)
	return "animNames: " .. table.concat(written, ", ")
end

function R6OnR15.wire(animate: Instance, ids: { [string]: any }, options: { R6Tempo: boolean? }?): { string }
	local filled = {}
	local groups = {}
	local function fill(group: string, slot: number, id: any)
		local value = animate:FindFirstChild(group)
		if not value then
			return
		end
		local animation = slotsOf(value)[slot]
		if animation then
			-- A bare number is an asset id; anything else is whole already, such as RegisterKeyframeSequence's id for a test.
			animation.AnimationId = if tonumber(id) then "rbxassetid://" .. tostring(id) else tostring(id)
			table.insert(filled, group .. "/" .. animation.Name)
			groups[group] = true
		end
	end
	for _, entry in R6OnR15.DEFAULTS do
		local id = ids[entry.Name]
		if id then
			fill(entry.Group, entry.Slot, id)
			if entry.Name == "walk" then
				fill("run", 1, id)
				fill("swim", 1, id)
			elseif entry.Name == "idle" then
				fill("swimidle", 1, id)
			end
		end
	end
	if not (options and options.R6Tempo == false) then
		local tempo = string.format("%.4f", 1.25 * 14.5 / 16)
		local script = animate :: any
		local source = script.Source
		local edits = {
			{ "local normalizedWalkSpeed%s*=%s*[%d%.]+", "local normalizedWalkSpeed = " .. tempo },
			{ "local normalizedRunSpeed%s*=%s*[%d%.]+", "local normalizedRunSpeed = " .. tempo },
			{ "local scale = 5%.0", "local scale = 12.0" },
		}
		for _, edit in edits do
			local done
			source, done = string.gsub(source, edit[1], edit[2])
			table.insert(filled, (if done == 1 then "retuned " else "not found: ") .. edit[2])
		end
		script.Source = source
	end
	table.insert(filled, writeAnimNames(animate, groups))
	return filled
end

return R6OnR15
