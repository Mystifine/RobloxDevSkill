--@use ClipImport, R6OnR15, AnimationInspector
-- Run through studio_mcp.py in Edit mode. Builds its own rigs and clips from made-up data, and destroys them.
-- selene: allow(undefined_variable)
local Import = ClipImport
-- selene: allow(undefined_variable)
local Fake = R6OnR15
-- selene: allow(undefined_variable)
local Inspector = AnimationInspector
local Players = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local temporary = {}
local results = {}
local function own(item)
	table.insert(temporary, item)
	return item
end
local function check(ok, label)
	assert(ok, label)
	table.insert(results, label)
end
local function angle(a, b)
	local _, turn = a:ToObjectSpace(b):ToAxisAngle()
	turn = math.abs(turn) % (2 * math.pi)
	return math.deg(if turn > math.pi then 2 * math.pi - turn else turn)
end
local function numbers(cf)
	return { cf:GetComponents() }
end
local function posesOf(sequence, index)
	local key = sequence:GetKeyframes()[index]
	local out = {}
	for _, item in key:GetDescendants() do
		if item:IsA("Pose") then
			out[item.Name] = item
		end
	end
	return out
end
local function rig(kind)
	local made = Players:CreateHumanoidModelFromDescription(Instance.new("HumanoidDescription"), kind)
	made.Parent = own(Instance.new("Folder"))
	made.Parent.Parent = game.ServerStorage
	return made
end

local ok, failure = pcall(function()
	-- .rbxanim on an R6: the rig's own tree, the numbers as given, each key's easing, unknown parts reported
	local r6 = rig(Enum.HumanoidRigType.R6)
	local raise = CFrame.Angles(0, 0, math.rad(45))
	local data = { t = 2 / 60, kfs = {} }
	for f = 0, 2 do
		table.insert(data.kfs, { t = f / 60, kf = {
			HumanoidRootPart = numbers(CFrame.new(0, -3, 3)),
			Torso = numbers(CFrame.new(0, -0.1 * f, 0)),
			["Right Arm"] = if f == 1 then { numbers(raise), "Constant", "Out" } else numbers(CFrame.Angles(0, 0, math.rad(45 * f))),
			Tail = numbers(CFrame.identity),
		} })
	end
	local sequence, missing = Import.rbxanim(r6, data, { Name = "Raise", Loop = true })
	own(sequence)
	check(#sequence:GetKeyframes() == 3 and sequence.Loop and sequence.Name == "Raise", "rbxanim: one key a frame, the options")
	local poses = posesOf(sequence, 2)
	check(poses.HumanoidRootPart.Weight == 0 and poses.HumanoidRootPart.CFrame == CFrame.identity, "rbxanim: the root's entry only carries the tree")
	check(poses.Torso.Parent == poses.HumanoidRootPart and poses["Right Arm"].Parent == poses.Torso and poses.Head.Parent == poses.Torso, "rbxanim: nested by the rig's joints")
	check(angle(poses["Right Arm"].CFrame, raise) < 1e-3 and poses["Right Arm"].EasingStyle == Enum.PoseEasingStyle.Constant, "rbxanim: numbers and easing kept")
	check(poses.Head.Weight == 0, "rbxanim: a part the clip leaves out overrides nothing")
	check(#missing == 1 and missing[1] == "Tail", "rbxanim: a name the rig lacks is reported")

	-- retarget: Thin = false keeps a key every frame; plantFeet puts each sole where its track says
	local r15 = rig(Enum.HumanoidRigType.R15)
	local map = Fake.map(r15)
	-- an R6 crouch to retarget: the torso lowered 0.3 (the root joint's Z points up the body)
	local source = Import.rbxanim(r6, { t = 0.2, kfs = {
		{ t = 0, kf = { Torso = numbers(CFrame.identity), ["Right Leg"] = numbers(CFrame.identity), ["Left Leg"] = numbers(CFrame.identity) } },
		{ t = 0.2, kf = { Torso = numbers(CFrame.new(0, 0, -0.3)), ["Right Leg"] = numbers(CFrame.identity), ["Left Leg"] = numbers(CFrame.identity) } },
	} }, { Name = "Crouch" })
	own(source)
	local thin = own(Fake.retarget(map, source, { Name = "Thin" }))
	local dense = own(Fake.retarget(map, source, { Name = "Dense", Thin = false }))
	check(#dense:GetKeyframes() == 13 and #thin:GetKeyframes() < 13, "retarget: Thin = false keeps all 13 frames")
	local rest = Fake.world(map, {})
	local track = { Feet = {}, Rest = { ["Left Leg"] = { 0, 0 }, ["Right Leg"] = { 0, 0 } } }
	for _, leg in { "Left Leg", "Right Leg" } do
		track.Feet[leg] = {}
		for f = 0, 12 do
			-- the right foot steps 0.4 forward (z back is +), lifting 0.3 halfway; the left stays put
			local s = f / 12
			track.Feet[leg][f + 1] = if leg == "Right Leg" then { 0, -0.4 * s, 0.3 * math.sin(math.pi * s) } else { 0, 0, 0 }
		end
	end
	local short = Fake.plantFeet(map, dense, track)
	check(short < 0.01, "plantFeet: every foot reaches its target (" .. string.format("%.4f", short) .. ")")
	local function sole(index, leg, foot)
		local p = posesOf(dense, index)
		local pose = { Torso = Fake.fromR15(map, "Torso", p.LowerTorso.CFrame), [leg] = Fake.fromR15(map, leg, p[map.Roles[leg].Joint].CFrame) }
		local at = Fake.world(map, pose)[foot]
		local half = r15[foot].Size / 2
		local low = at.Position.Y - math.abs(at.RightVector.Y) * half.X - math.abs(at.UpVector.Y) * half.Y - math.abs(at.LookVector.Y) * half.Z
		return at.Position, low - map.Floor
	end
	local leftAt, leftLift = sole(13, "Left Leg", "LeftFoot")
	local flat = Vector3.new(1, 0, 1)
	check(math.abs(leftLift) < 0.01 and ((leftAt - rest.LeftFoot.Position) * flat).Magnitude < 0.01, "plantFeet: a planted foot stays on the floor in the crouch")
	local _, midLift = sole(7, "Right Leg", "RightFoot")
	local endAt, endLift = sole(13, "Right Leg", "RightFoot")
	check(math.abs(midLift - 0.3) < 0.01 and math.abs(endLift) < 0.01, "plantFeet: the step lifts as its track says, then lands")
	check(math.abs((endAt.Z - rest.RightFoot.Position.Z) + 0.4) < 0.05, "plantFeet: the step lands 0.4 studs forward")
	local findings = Fake.check(map, dense)
	check(#findings == 0, "plantFeet: the joint policy holds")

	-- deltas: a bone rig (a hip and knee under a part) plus a Motor6D part, from Blender-space world deltas
	local model = own(Instance.new("Model"))
	model.Name = "Creature"
	local root = Instance.new("Part")
	root.Name = "RootPart"
	root.Size = Vector3.new(1, 1, 1)
	root.Anchored = true
	root.CFrame = CFrame.new(0, 3, 0)
	root.Parent = model
	model.PrimaryPart = root
	local hip = Instance.new("Bone")
	hip.Name = "Hip"
	hip.CFrame = CFrame.new(0, 0, 0)
	hip.Parent = root
	local knee = Instance.new("Bone")
	knee.Name = "Knee"
	knee.CFrame = CFrame.new(0, -1, 0)
	knee.Parent = hip
	local lid = Instance.new("Part")
	lid.Name = "Lid"
	lid.Size = Vector3.new(1, 0.2, 1)
	lid.CFrame = CFrame.new(0, 4, 0)
	lid.Parent = model
	local motor = Instance.new("Motor6D")
	motor.Part0, motor.Part1, motor.C0 = root, lid, CFrame.new(0, 1, 0)
	motor.Parent = root
	local controller = Instance.new("AnimationController")
	Instance.new("Animator").Parent = controller
	controller.Parent = model
	model.Parent = game.ServerStorage
	-- Blender space for these: Roblox (x, y, z) -> Blender (-x, z, y), as roblox_rig's exports; the knee turns 90 degrees
	-- about Blender's X axis through its head at (0, 0, 2), and the lid 30 degrees about Blender's Y through (0, 0, 4)
	local function blender(v)
		return { -v.X, v.Z, v.Y }
	end
	-- a world delta as blender_anim.deltas writes it: { x, y, z, w, qx, qy, qz } of (turn about `axis` through `head`)
	local function about(axis, degrees, head)
		local h = Vector3.new(head[1], head[2], head[3])
		local d = CFrame.new(h) * CFrame.fromAxisAngle(axis, math.rad(degrees)) * CFrame.new(-h)
		local half = math.rad(degrees) / 2
		return { d.X, d.Y, d.Z, math.cos(half), axis.X * math.sin(half), axis.Y * math.sin(half), axis.Z * math.sin(half) }
	end
	local deltas = {
		Name = "Fold", Loop = false, Priority = "Action",
		Rest = { Hip = { head = blender(Vector3.new(0, 3, 0)) }, Knee = { head = blender(Vector3.new(0, 2, 0)) }, Lid = { head = blender(Vector3.new(0, 4, 0)) } },
		Samples = {
			{ t = 0, bones = { Hip = about(Vector3.xAxis, 0, { 0, 0, 3 }), Knee = about(Vector3.xAxis, 0, { 0, 0, 2 }), Lid = about(Vector3.yAxis, 0, { 0, 0, 4 }) } },
			{ t = 0.5, bones = { Hip = about(Vector3.xAxis, 0, { 0, 0, 3 }), Knee = about(Vector3.xAxis, 90, { 0, 0, 2 }), Lid = about(Vector3.yAxis, 30, { 0, 0, 4 }) } },
		},
	}
	local folded, fit = Import.deltas(model, deltas)
	own(folded)
	check(fit < 1e-4, "deltas: the axis map lays the rest heads on the bones (" .. string.format("%.5f", fit) .. ")")
	local p = posesOf(folded, 2)
	check(p.Knee and p.Knee.Parent == p.Hip and p.Hip.Parent.Name == "RootPart", "deltas: bones nest under the part that holds them")
	check(math.abs(angle(CFrame.identity, p.Knee.CFrame) - 90) < 0.01 and p.Knee.CFrame.Position.Magnitude < 1e-3, "deltas: the knee turns 90 degrees about its own head")
	check(angle(CFrame.identity, p.Hip.CFrame) < 0.01, "deltas: a still parent stays at identity")
	check(p.Lid and math.abs(angle(CFrame.identity, p.Lid.CFrame) - 30) < 0.01, "deltas: a Motor6D part is posed as its joint")

	-- AnimationInspector Soles: a paw bone a stud above its sole
	local creature = own(Instance.new("Model"))
	local body = Instance.new("Part")
	body.Name = "Body"
	body.Size = Vector3.new(2, 2, 2)
	body.Anchored = true
	body.CFrame = CFrame.new(0, 1, 0)
	body.Parent = creature
	creature.PrimaryPart = body
	local paw = Instance.new("Bone")
	paw.Name = "Paw"
	paw.CFrame = CFrame.new(0.5, 0, 0)
	paw.Parent = body
	local animation = Instance.new("AnimationController")
	Instance.new("Animator").Parent = animation
	animation.Parent = creature
	creature.Parent = game.ServerStorage
	local still = own(Instance.new("KeyframeSequence"))
	for _, t in { 0, 1 } do
		local key = Instance.new("Keyframe")
		key.Time = t
		local top = Instance.new("Pose")
		top.Name = "Body"
		local pose = Instance.new("Pose")
		pose.Name = "Paw"
		pose.CFrame = CFrame.Angles(0, math.rad(10 * t), 0) -- turns about its own up axis: the sole point stays put
		pose.Parent = top
		top.Parent = key
		key.Parent = still
	end
	local without = Inspector.audit(creature, still, { Feet = { "Paw" } }).Text
	local with = Inspector.audit(creature, still, { Feet = { "Paw" }, Soles = { Paw = Vector3.new(0, -1, 0) } }).Text
	check(string.find(without, "[float]", 1, true) ~= nil, "Soles: without them the paw hovers")
	check(string.find(with, "[float]", 1, true) == nil and string.find(with, "Feet: planted", 1, true) ~= nil, "Soles: with them the paw stands on the floor")
end)
for _, item in temporary do
	item:Destroy()
end
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
