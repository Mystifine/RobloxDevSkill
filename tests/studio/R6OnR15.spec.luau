--@use R6OnR15, AnimationInspector
-- Run through studio_mcp.py in Edit mode. Creates and destroys its own rigs and clips; needs the default R6 and R15 clips to load.
-- selene: allow(undefined_variable)
local Fake = R6OnR15
-- selene: allow(undefined_variable)
local Inspector = AnimationInspector
local Players = game:GetService("Players")
local Provider = game:GetService("KeyframeSequenceProvider")
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
local function near(a, b, tolerance)
	return math.abs(a - b) <= (tolerance or 1e-3)
end
local function angle(a, b)
	local _, turn = a:ToObjectSpace(b):ToAxisAngle()
	turn = math.abs(turn) % (2 * math.pi)
	return math.deg(if turn > math.pi then 2 * math.pi - turn else turn)
end
local function same(a, b)
	return (a.Position - b.Position).Magnitude < 1e-3 and angle(a, b) < 0.01
end

-- Plays `tracks` on a copy of the rig and returns each joint's Transform as the engine evaluates it.
local function evaluate(rig, tracks, time)
	rig.Archivable = true
	local copy = own(rig:Clone())
	for _, item in copy:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			item:Destroy()
		end
	end
	copy.HumanoidRootPart.Anchored = true
	copy:PivotTo(CFrame.new(0, 1100, 0))
	copy.Parent = workspace
	local animator = copy:FindFirstChildOfClass("Humanoid"):FindFirstChildOfClass("Animator")
	local loaded = {}
	for _, item in tracks do
		local animation = Instance.new("Animation")
		animation.AnimationId = if typeof(item) == "Instance" then Provider:RegisterKeyframeSequence(item) else "rbxassetid://" .. item
		local track = animator:LoadAnimation(animation)
		local waited = 0
		while track.Length <= 0 and waited < 10 do
			waited += task.wait()
		end
		assert(track.Length > 0, "a clip did not load")
		track.Looped = false
		track:Play(0, 1, 0)
		table.insert(loaded, track)
	end
	for _, track in loaded do
		track.TimePosition = math.min(time, track.Length - 1e-4)
	end
	animator:StepAnimations(0.001)
	local out = {}
	for _, item in copy:GetDescendants() do
		if item:IsA("AnimationConstraint") then
			out[item.Attachment1.Parent.Name] = item.Transform
		elseif item:IsA("Motor6D") then
			out[item.Part1.Name] = item.Transform
		end
	end
	copy:Destroy()
	return out
end

-- The parts in the root's space from joints' Transforms, by forward kinematics.
local function chain(map, transforms)
	local world = { HumanoidRootPart = CFrame.identity }
	local function of(name)
		if world[name] then
			return world[name]
		end
		local joint = map.Joints[name]
		world[name] = of(joint.Parent) * joint.C0 * (transforms[name] or CFrame.identity) * joint.C1:Inverse()
		return world[name]
	end
	for name in map.Joints do
		of(name)
	end
	return world
end

local ok, failure = pcall(function()
	local desc = own(Instance.new("HumanoidDescription"))
	local r15 = own(Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15))
	local r6 = own(Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R6))

	check(not pcall(Fake.map, r6), "an R6 is refused")
	local map = Fake.map(r15)
	local arm, leg = map.Roles["Right Arm"], map.Roles["Right Leg"]
	check(arm.Pivot.Y < arm.Frame.Position.Y - 0.1, "the shoulder turns at R6's pivot, below the R15 joint")
	check(leg.Pivot.X > leg.Frame.Position.X + 0.3, "the hip turns at R6's pivot, on the leg's outer face")

	-- FK
	local raise = CFrame.Angles(0, 0, math.rad(100)) * CFrame.new(0, 0.1, 0.2)
	check(same(Fake.fromR15(map, "Right Arm", Fake.toR15(map, "Right Arm", raise)), raise), "R6 to R15 and back gives the same Transform")
	check(same(Fake.toR15(map, "Left Leg", CFrame.identity), CFrame.identity), "R6's rest is R15's rest")
	local pose = { Torso = CFrame.Angles(math.rad(12), 0, 0), Head = CFrame.Angles(0, math.rad(20), 0), ["Right Arm"] = raise }
	local joints = Fake.fk(map, pose)
	check(joints.RightLowerArm == CFrame.identity and joints.RightHand == CFrame.identity and joints.UpperTorso == CFrame.identity, "fk holds the locked joints at identity")
	check(joints.LeftUpperArm == nil, "fk leaves a limb the pose leaves out")

	-- The same R6 Transform turns R6's block and R15's block the same way, about the same place on the body.
	local turned = Fake.world(map, { ["Right Arm"] = CFrame.Angles(0, 0, math.rad(180)) })
	local tip = turned.RightHand * (map.Rest.RightHand:Inverse() * arm.Tip)
	check(near(tip.Y, arm.Pivot.Y + (arm.Pivot.Y - arm.Tip.Y)), "a full raise lifts the hand as far above the shoulder as it hung below")

	-- FK through the engine.
	local still = own(Fake.clip(map, { { Frame = 0, Pose = pose }, { Frame = 30, Pose = pose } }, { Name = "pose" }))
	local played = evaluate(r15, { still }, 0.25)
	check(same(played.UpperTorso, CFrame.identity) and same(played.RightLowerArm, CFrame.identity) and same(played.RightHand, CFrame.identity), "the engine holds the locks")
	check(same(played.RightUpperArm, joints.RightUpperArm) and same(played.LowerTorso, joints.LowerTorso), "the engine plays the fk Transforms")
	check(same(chain(map, played).RightHand, Fake.world(map, pose).RightHand), "world agrees with the engine's forward kinematics")

	-- IK
	local goal = Vector3.new(1.2, 1.4, -1.6)
	local transform, missed, slide = Fake.reach(map, "Right Arm", goal)
	check(missed < 1e-3 and slide ~= 0, "reach puts the tip on a target the arm's length alone would miss, by sliding")
	local at = Fake.world(map, { ["Right Arm"] = transform }).RightHand * (map.Rest.RightHand:Inverse() * arm.Tip)
	check((at - goal).Magnitude < 1e-3, "world finds the tip on the target")
	local _, aimOnly = Fake.reach(map, "Right Arm", goal, { Slide = 0 })
	check(aimOnly > 0.01, "Slide 0 only aims")
	local _, far = Fake.reach(map, "Right Arm", Vector3.new(0, 20, -20))
	check(far > 1, "a target out of reach is reported, not reached by a torn-off arm")

	local lean = CFrame.Angles(math.rad(25), 0, 0) * CFrame.new(0, 0.3, -0.2)
	local leaned = Fake.reach(map, "Left Arm", Vector3.new(-1.1, 0.8, -1.8), { Torso = lean })
	local leanedAt = Fake.world(map, { Torso = lean, ["Left Arm"] = leaned }).LeftHand * (map.Rest.LeftHand:Inverse() * map.Roles["Left Arm"].Tip)
	check((leanedAt - Vector3.new(-1.1, 0.8, -1.8)).Magnitude < 1e-3, "reach holds its target with the torso moved")

	local fromFk = CFrame.Angles(0, math.rad(30), 0)
	local twisted = Fake.reach(map, "Right Arm", goal, { From = fromFk })
	check(not same(twisted, transform), "From sets the limb's roll")
	local rolled = Fake.reach(map, "Right Arm", goal, { Twist = math.rad(40) })
	local rolledAt = Fake.world(map, { ["Right Arm"] = rolled }).RightHand * (map.Rest.RightHand:Inverse() * arm.Tip)
	check((rolledAt - goal).Magnitude < 1e-3, "Twist rolls the limb without moving its tip")

	local looked = Fake.reach(map, "Head", Vector3.new(4, 3, -6))
	local face = Fake.world(map, { Head = looked }).Head.LookVector
	check(angle(CFrame.lookAlong(Vector3.zero, face), CFrame.lookAlong(Vector3.zero, Vector3.new(4, 3, -6) - map.Roles.Head.Pivot)) < 0.5, "reaching with the head looks at the target")

	local floor = map.Floor
	local function lowest(world, foot)
		local half, part = map.Sizes[foot] / 2, world[foot]
		return part.Position.Y - math.abs(part.RightVector.Y) * half.X - math.abs(part.UpVector.Y) * half.Y - math.abs(part.LookVector.Y) * half.Z
	end
	local step = Fake.plant(map, "Left Leg", Vector3.new(-0.5, 0, -1.3))
	local planted = Fake.world(map, { ["Left Leg"] = step })
	check(near(lowest(planted, "LeftFoot"), floor), "plant rests the foot's lowest corner on the floor")
	local crouch = CFrame.new(0, 0, -0.5) -- R6's root joint has its Z up the body
	local crouched = Fake.plant(map, "Right Leg", Vector3.new(0.5, 0, 0.4), { Torso = crouch })
	check(near(lowest(Fake.world(map, { Torso = crouch, ["Right Leg"] = crouched }), "RightFoot"), floor), "plant holds the floor with the torso moved")

	local swing = { ["Left Leg"] = CFrame.Angles(0, 0, math.rad(35)), ["Right Leg"] = CFrame.Angles(0, 0, math.rad(35)) }
	local settled = Fake.settle(map, swing)
	local settledAt = Fake.world(map, settled)
	check(near(math.min(lowest(settledAt, "LeftFoot"), lowest(settledAt, "RightFoot")), floor), "settle brings the lowest foot down to the floor")
	check(settled["Left Leg"] == swing["Left Leg"], "settle moves only the torso")

	-- IK through the engine: what a clip of those Transforms really does.
	local reached = own(Fake.clip(map, { { Frame = 0, Pose = { ["Right Arm"] = transform } }, { Frame = 30, Pose = { ["Right Arm"] = transform } } }, { Name = "reach" }))
	local reachedWorld = chain(map, evaluate(r15, { reached }, 0.25))
	check((reachedWorld.RightHand * (map.Rest.RightHand:Inverse() * arm.Tip) - goal).Magnitude < 1e-2, "the engine plays the IK onto its target")

	-- Retargeting, from the engine's own evaluation of the R6 source.
	local walk = own(Fake.retarget(map, 180426354, { Name = "walk" }))
	check(walk.Loop and walk.Priority == Enum.AnimationPriority.Core, "a retarget keeps the source's loop and priority")
	check(#(Fake.check(map, walk)) == 0, "a retargeted walk passes the joint policy")
	local verified = Fake.verify(map, r15, 180426354, walk)
	check(verified.Degrees < 0.5 and verified.Studs < 0.01 and verified.Locked < 1e-3, string.format("the engine's R15 walk matches the R6 source (%.2f deg, %.4f studs)", verified.Degrees, verified.Studs))
	for _, key in walk:GetKeyframes() do
		assert(near(key.Time * 60, math.round(key.Time * 60)), "a key is off the 60 fps grid")
	end
	table.insert(results, "every key sits on the 60 fps grid")
	local audit = Inspector.audit(r15, walk, { Locomotion = true })
	check(audit.GroundSpeed and audit.GroundSpeed > 12, "the inspector reads it as locomotion")

	-- A full-body stock R15 clip bends knees and elbows; a clip that merely omitted them would let that through.
	local stockWalk = 913402848
	local alone = evaluate(r15, { stockWalk }, 0.2)
	check(angle(alone.RightLowerLeg, CFrame.identity) > 1, "stock R15 walk bends a knee, so the next check means something")
	local action = own(walk:Clone())
	action.Priority = Enum.AnimationPriority.Action
	local over = evaluate(r15, { stockWalk, action }, 0.2)
	for _, part in { "UpperTorso", "LeftLowerArm", "LeftHand", "RightLowerArm", "RightHand", "LeftLowerLeg", "LeftFoot", "RightLowerLeg", "RightFoot" } do
		assert(same(over[part], CFrame.identity), part .. " moved under a locking clip")
	end
	table.insert(results, "the nine locks hold over a stock R15 clip")

	-- Clips that key part of the body must leave the rest to what plays beneath, as R6's do.
	local toolnone = own(Fake.retarget(map, 182393478, { Name = "toolnone" }))
	local names = {}
	for _, item in toolnone:GetDescendants() do
		if item:IsA("Pose") then
			names[item.Name] = true
		end
	end
	check(names.RightUpperArm and names.RightLowerArm and names.RightHand, "toolnone keys the arm and holds its locks")
	check(not names.LeftUpperArm and not names.LeftUpperLeg and not names.RightUpperLeg and not names.Head, "toolnone leaves the other limbs alone")
	local blended = evaluate(r15, { walk, toolnone }, 0.2)
	local walkAlone = evaluate(r15, { walk }, 0.2)
	check(same(blended.LeftUpperLeg, walkAlone.LeftUpperLeg), "a walk keeps playing beneath toolnone")
	check(not same(blended.RightUpperArm, walkAlone.RightUpperArm), "toolnone takes the arm from the walk")
	local armOnly = own(Fake.clip(map, { { Frame = 0, Pose = { ["Right Arm"] = raise } }, { Frame = 30, Pose = { ["Right Arm"] = raise } } }, { Name = "armOnly" }))
	local underArm = evaluate(r15, { walk, armOnly }, 0.2)
	check(same(underArm.LowerTorso, walkAlone.LowerTorso) and same(underArm.Head, walkAlone.Head), "poses that only carry the tree down to a limb override nothing")
	local slash = own(Fake.retarget(map, 129967390, { Name = "toolslash" }))
	local slashTop = {}
	for _, child in slash:GetKeyframes()[1]:GetChildren() do
		if child:IsA("Pose") then
			table.insert(slashTop, child.Name)
		end
	end
	check(#slashTop == 1 and slashTop[1] == "LowerTorso", "a clip with no root pose, like toolslash, binds no root joint")

	-- A stock R15 clip is articulated, so the policy must catch it.
	local stock = own(game:GetService("AnimationClipProvider"):GetAnimationClipAsync("rbxassetid://" .. stockWalk):Clone())
	local caught = false
	for _, finding in Fake.check(map, stock) do
		caught = caught or (finding.Rule == "locked" and string.find(finding.Detail, "LowerLeg", 1, true) ~= nil)
	end
	check(caught, "the policy catches an articulated clip")

	-- The whole set.
	local holder = own(Instance.new("Folder"))
	local set = Fake.defaults(map, holder)
	local count = 0
	for _ in set do
		count += 1
	end
	check(count == #Fake.DEFAULTS and count == 23, "defaults builds all 23 of Roblox's R6 clips")
	for name, sequence in set do
		assert(#(Fake.check(map, sequence)) == 0, name .. " breaks the joint policy")
	end
	table.insert(results, "all 23 pass the joint policy")

	-- Wiring into Animate.
	local copy = own(r15:Clone())
	local filled = Fake.wire(copy:FindFirstChild("Animate"), { walk = 111, idle = 222, dance1b = 333 })
	local animate = copy:FindFirstChild("Animate")
	check(animate.walk:FindFirstChildOfClass("Animation").AnimationId == "rbxassetid://111", "wire fills the walk slot")
	check(animate.run:FindFirstChildOfClass("Animation").AnimationId == "rbxassetid://111", "wire gives run the walk's clip, as R6 has")
	check(animate.swim:FindFirstChildOfClass("Animation").AnimationId == "rbxassetid://111" and animate.swimidle:FindFirstChildOfClass("Animation").AnimationId == "rbxassetid://222", "wire swims on the walk and idle, as R6 does")
	check(#filled == 9, "wire names what it filled and retuned")
	for _, line in filled do
		assert(not string.find(line, "not found", 1, true), "this Studio's Animate changed: " .. line)
	end
	check(string.find(animate.Source, "local normalizedRunSpeed = 1.1328", 1, true) and string.find(animate.Source, "local scale = 12.0", 1, true), "wire retunes Animate to R6's speeds")
	local untouched = own(r15:Clone())
	local before = untouched.Animate.Source
	check(#Fake.wire(untouched.Animate, { walk = 111 }, { R6Tempo = false }) == 3 and untouched.Animate.Source == before, "R6Tempo false leaves the source alone")

	-- A retarget leaves the providers' shared clips whole.
	check(#Provider:GetKeyframeSequenceAsync("rbxassetid://180426354"):GetKeyframes() > 0, "the provider's cached source survives")
	check(workspace:FindFirstChild("__R6OnR15") == nil, "nothing is left in the workspace")
end)
for _, item in temporary do
	item:Destroy()
end
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
