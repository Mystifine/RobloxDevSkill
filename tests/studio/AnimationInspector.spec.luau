--@use AnimationInspector, RigAudit
-- Run through studio_mcp.py in Edit mode. Creates and destroys its own rigs and clips.
-- selene: allow(undefined_variable)
local Inspector = AnimationInspector
-- selene: allow(undefined_variable)
local Audit = RigAudit
local Players = game:GetService("Players")
local Provider = game:GetService("KeyframeSequenceProvider")
local HttpService = game:GetService("HttpService")
local temporary = {}
local results = {}
local function own(item)
	table.insert(temporary, item)
	return item
end
local function has(report, rule)
	for _, finding in report.Findings do
		if finding.Rule == rule then
			return true
		end
	end
	return false
end
local function check(ok, label)
	assert(ok, label)
	table.insert(results, label)
end
local ok, failure = pcall(function()
	local desc = own(Instance.new("HumanoidDescription"))
	local r6 = own(Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R6))
	local r15 = own(Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15))
	Audit.clean(r6)
	Audit.clean(r15)
	local sequence = own(Provider:GetKeyframeSequenceAsync("rbxassetid://180426354"):Clone())
	local walk = Inspector.audit(r6, 180426354)
	check(walk.GroundSpeed ~= nil and walk.GroundSpeed > 2, "stock R6 walk infers locomotion")
	check(not has(walk, "slide"), "stock R6 walk does not report stationary sliding")
	local explicit = Inspector.audit(r6, 180426354, { Locomotion = true })
	check(explicit.GroundSpeed ~= nil and not has(explicit, "slide"), "explicit locomotion measures backward stances")
	local stationary = Inspector.audit(r6, 180426354, { Locomotion = false })
	check(stationary.GroundSpeed == nil and has(stationary, "slide"), "stationary override retains slide checks")
	local r15Walk = Inspector.audit(r15, 507777826)
	check(r15Walk.GroundSpeed ~= nil and not has(r15Walk, "slide"), "stock R15 walk still detects locomotion")
	local idle = Inspector.audit(r15, 507766666)
	check(idle.GroundSpeed == nil and not has(idle, "slide"), "stock idle stays stationary")
	local function defect(sink)
		local clip = own(sequence:Clone())
		clip.Name = "InspectorRegression_" .. HttpService:GenerateGUID(false)
		clip.Parent = game:GetService("ServerStorage")
		local rootJoint = r6.HumanoidRootPart:FindFirstChildWhichIsA("Motor6D")
		assert(rootJoint, "R6 root joint missing")
		local keys = clip:GetKeyframes()
		local length = 0
		for _, key in keys do
			length = math.max(length, key.Time)
		end
		for _, key in keys do
			for _, pose in key:GetDescendants() do
				if pose:IsA("Pose") then
					local offset = rootJoint.C0:VectorToObjectSpace(Vector3.new(.35 * math.sin(2 * math.pi * key.Time / length), sink, 0))
					pose.CFrame = if pose.Name == "Torso" then CFrame.new(offset) else CFrame.identity
				end
			end
		end
		return clip
	end
	local sliding = Inspector.audit(r6, defect(0))
	check(sliding.GroundSpeed == nil and has(sliding, "slide"), "sideways planted sliding is still caught")
	local sinking = Inspector.audit(r6, defect(-.4))
	check(has(sinking, "clip"), "sunk feet are still caught")
	local sheetCount = 0
	for _, pair in { { r6, 180426354 }, { r15, 507777826 } } do
		local started = os.clock()
		local sheet = Inspector.sheet(pair[1], pair[2], { Times = { 0, .17 }, Views = { "front", "side" }, Trails = false })
		check(os.clock() - started >= .7, "sheet yields for redraw " .. pair[1].Humanoid.RigType.Name)
		local stage = workspace:FindFirstChild("__AnimInspect")
		check(stage ~= nil and stage:FindFirstChild("__Sheet") ~= nil and #sheet.Camera == 3, "sheet stage and camera are ready")
		sheetCount += 1
	end
	check(sheetCount == 2, "consecutive sheets replace the previous stage")
end)
Inspector.clear()
for _, item in temporary do
	item:Destroy()
end
assert(not workspace:FindFirstChild("__AnimInspect"), "review stage leaked")
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
