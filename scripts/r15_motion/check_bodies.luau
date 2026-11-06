--@use AnimationInspector
--# selene: allow(undefined_variable) -- (the --@use line above makes it a local)
-- The clips on other bodies (a pose must read on wide, tall and blocky ones): each clip already imported into
-- ServerStorage.R15ClipImports (pipeline.py import), audited on an avatar of each shape. Edit mode. Prints how far planted feet sit from the
-- floor and any finding. Run: python pipeline.py bodies
local Players = game:GetService("Players")
local ServerStorage = game:GetService("ServerStorage")

local BODIES = {
	{ Name = "Tall", HeightScale = 1.05, WidthScale = 0.75, DepthScale = 0.85, HeadScale = 0.95 },
	{ Name = "Wide", HeightScale = 0.9, WidthScale = 1.0, DepthScale = 1.0, HeadScale = 1.0 },
	{ Name = "Rthro", HeightScale = 1.05, WidthScale = 0.9, DepthScale = 0.9, HeadScale = 0.95, BodyTypeScale = 1, ProportionScale = 1 },
	{ Name = "Small", HeightScale = 0.9, WidthScale = 0.7, DepthScale = 0.8, HeadScale = 1.0, BodyTypeScale = 0, ProportionScale = 0 },
}

local folder = ServerStorage:FindFirstChild("R15ClipImports")
if not folder then
	return "import the clips first"
end
local lines = {}
for _, body in BODIES do
	local description = Instance.new("HumanoidDescription")
	for field, value in body do
		if field ~= "Name" then
			(description :: any)[field] = value
		end
	end
	local rig = Players:CreateHumanoidModelFromDescription(description, Enum.HumanoidRigType.R15)
	rig.Name = "ClipImportRig"
	local animate = rig:FindFirstChild("Animate")
	if animate then
		animate:Destroy()
	end
	rig:PivotTo(CFrame.new(0, 200, 0))
	rig.Parent = workspace
	local humanoid = rig:FindFirstChildOfClass("Humanoid") :: Humanoid
	humanoid:BuildRigFromAttachments()
	for _, part in rig:GetDescendants() do
		if part:IsA("BasePart") then
			part.Anchored = true
		end
	end
	for _, sequence in folder:GetChildren() do
		local name = sequence.Name
		if sequence:IsA("KeyframeSequence") then
			local report = AnimationInspector.audit(rig, sequence, { Fps = 60, Looped = sequence.Loop, Locomotion = if name == "walk" or name == "run" then true else nil, Ignore = { "slide", "stride", "end-offset" } })
			local feet = string.match(report.Text, "planted [^\n]*") or "(no planted feet measured)"
			local findings = {}
			for _, finding in report.Findings do
				table.insert(findings, string.format("%s %s", finding.Rule, finding.Level or ""))
			end
			table.insert(lines, string.format("%s %s: %s; %s", body.Name, name, feet, if #findings > 0 then table.concat(findings, ", ") else "clean"))
		end
		task.wait()
	end
	rig:Destroy()
end
return table.concat(lines, "\n")
