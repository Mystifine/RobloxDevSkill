--@use R6OnR15, RigSkin
-- Writes what tests/blender/r6_on_r15_test.py checks Blender against: Studio's own numbers for a classic R15's body, and for FK and
-- IK poses on it. From the skill's folder:
--   python scripts/studio_mcp.py luau tests/studio/R6OnR15.fixture.luau --studio "PLACE NAME" --output tests/blender/r6_on_r15_fixture.json
-- selene: allow(undefined_variable)
local Fake = R6OnR15
-- selene: allow(undefined_variable)
local Skin = RigSkin
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")

local description = Instance.new("HumanoidDescription")
description.BodyTypeScale, description.ProportionScale = 0, 0
local rig = Players:CreateHumanoidModelFromDescription(description, Enum.HumanoidRigType.R15)
description:Destroy()
local map = Fake.map(rig)

local function numbers(cf: CFrame): { number }
	return { cf:GetComponents() }
end
local function worldOf(pose: { [string]: CFrame }): { [string]: { number } }
	local out = {}
	for part, cf in Fake.world(map, pose) do
		out[part] = numbers(cf)
	end
	return out
end
local function poseOf(pose: { [string]: CFrame }): { [string]: { number } }
	local out = {}
	for part, cf in pose do
		out[part] = numbers(cf)
	end
	return out
end

local rest = {}
for part, cf in map.Rest do
	rest[part] = numbers(cf)
end

local poses = {
	{ ["Right Arm"] = CFrame.Angles(0, 0, math.rad(100)) },
	{ ["Left Leg"] = CFrame.Angles(math.rad(25), 0, math.rad(-20)) * CFrame.new(0, 0.5, 0) },
	{ Torso = CFrame.Angles(math.rad(15), 0, math.rad(10)) * CFrame.new(0, 0.2, -0.4), Head = CFrame.Angles(0, 0, math.rad(30)), ["Left Arm"] = CFrame.Angles(0, 0, math.rad(-60)) },
}
local fk = {}
for _, pose in poses do
	table.insert(fk, { pose = poseOf(pose), world = worldOf(pose) })
end

local goals = {
	{ limb = "Right Arm", target = Vector3.new(1.2, 1.4, -1.6) },
	{ limb = "Left Arm", target = Vector3.new(-1.1, 0.8, -1.8), torso = CFrame.Angles(math.rad(25), 0, 0) * CFrame.new(0, 0.3, -0.2) },
	{ limb = "Right Leg", target = Vector3.new(0.5, -2.6, -1.4) },
	{ limb = "Left Leg", target = Vector3.new(-0.5, -2.2, 1.2), torso = CFrame.new(0, 0, -0.5) },
}
local ik = {}
for _, goal in goals do
	local transform, missed, slide = Fake.reach(map, goal.limb, goal.target, { Torso = goal.torso })
	assert(missed < 1e-3, "a fixture target is out of reach")
	local pose = { [goal.limb] = transform }
	if goal.torso then
		pose.Torso = goal.torso
	end
	table.insert(ik, {
		limb = goal.limb,
		target = { goal.target.X, goal.target.Y, goal.target.Z },
		torso = if goal.torso then numbers(goal.torso) else nil,
		slide = slide,
		world = worldOf(pose),
	})
end

local aimOnlyGoal = Vector3.new(1.2, 1.4, -1.6)
local aimOnly = Fake.reach(map, "Right Arm", aimOnlyGoal, { Slide = 0 })

local data = HttpService:JSONEncode({
	rig = HttpService:JSONDecode(Skin.dump(rig)),
	roles = Fake.dump(map),
	rest = rest,
	fk = fk,
	ik = ik,
	aimOnly = { limb = "Right Arm", target = { aimOnlyGoal.X, aimOnlyGoal.Y, aimOnlyGoal.Z }, world = worldOf({ ["Right Arm"] = aimOnly }) },
})
rig:Destroy()
return data
