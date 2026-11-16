--@use ColourCode, AnimationInspector
-- Run through studio_mcp.py in Edit mode: ColourCode's review colours on generated R6 and R15 rigs and on a plain build, its
-- restore, and AnimationInspector.sheet coding only its posed copies. Creates and destroys its own rigs.
-- selene: allow(undefined_variable)
local Code = ColourCode
-- selene: allow(undefined_variable)
local Inspector = AnimationInspector
local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
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
-- BasePart.Color keeps 8 bits a channel
local function near(a: Color3, b: Color3?): boolean
	return b ~= nil and math.abs(a.R - b.R) < 0.005 and math.abs(a.G - b.G) < 0.005 and math.abs(a.B - b.B) < 0.005
end
local function rig(kind)
	local description = Instance.new("HumanoidDescription")
	local model = own(Players:CreateHumanoidModelFromDescription(description, kind))
	description:Destroy()
	for _, item in model:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			item:Destroy()
		end
	end
	model:PivotTo(CFrame.new(0, 900, -300))
	model.Parent = workspace
	return model
end

local ok, failure = pcall(function()
	local leftArm, upperArm = Code.body("Left Arm"), Code.body("LeftUpperArm")
	check(leftArm ~= nil and leftArm == upperArm, "R6 and R15 names of one limb share a colour")
	local hRight = (Code.body("RightUpperArm") :: Color3):ToHSV()
	local hLeft = (Code.body("LeftUpperArm") :: Color3):ToHSV()
	check(math.min(hRight, 1 - hRight) < 0.01 and math.abs(hLeft - 4 / 6) < 0.01, "the right arm is red and the left arm blue")
	local _, _, vUpper = (Code.body("LeftUpperArm") :: Color3):ToHSV()
	local _, _, vLower = (Code.body("LeftLowerArm") :: Color3):ToHSV()
	local _, sHand = (Code.body("LeftHand") :: Color3):ToHSV()
	check(vLower < vUpper - 0.2 and sHand < 0.6, "a limb's segments step down its hue")
	check(Code.body("Handle") == nil and Code.body("HumanoidRootPart") == nil, "other names have no body colour")

	local r15 = rig(Enum.HumanoidRigType.R15)
	local shirt = Instance.new("Shirt")
	shirt.Parent = r15
	local sword = Instance.new("Part")
	sword.Name, sword.Color, sword.Material = "Blade", Color3.fromRGB(10, 200, 30), Enum.Material.Metal
	sword.Parent = r15
	local arm = r15:FindFirstChild("LeftUpperArm") :: MeshPart
	local before = { arm.Color, arm.Material, arm.TextureID }
	local face = r15.Head:FindFirstChild("face")
	local handle = Code.apply(r15)
	check(near(arm.Color, upperArm) and arm.Material == Enum.Material.SmoothPlastic, "a coded body takes its review colours")
	check(sword.Color == Color3.fromRGB(215, 215, 220), "other parts on a body turn grey")
	check(shirt.Parent == nil and (face == nil or face.Parent ~= nil), "clothing comes off while coded; the face stays")
	check(#handle.Legend >= 16, "the legend lists every coded part")
	handle.Restore()
	check(arm.Color == before[1] and arm.Material == before[2] and arm.TextureID == before[3], "restore puts a part back")
	check(shirt.Parent == r15 and sword.Color == Color3.fromRGB(10, 200, 30) and sword.Material == Enum.Material.Metal,
		"restore puts clothing and other parts back")

	local build = own(Instance.new("Model"))
	for i = 1, 5 do
		local part = Instance.new("Part")
		part.Name = "Piece" .. i
		part.Parent = build
	end
	local pieces = Code.apply(build)
	local hues = {}
	for _, entry in pieces.Legend do
		hues[entry.Colour] = true
	end
	local distinct = 0
	for _ in hues do
		distinct += 1
	end
	check(distinct == 5, "a build's pieces take distinct hues")
	pieces.Restore()

	local r6 = rig(Enum.HumanoidRigType.R6)
	local original = (r6:FindFirstChild("Left Arm") :: BasePart).Color
	local coded = 0
	Inspector.sheet(r6, 180426354, { Times = { 0, 0.3 }, Views = { "front" }, Trails = false, Recolour = function(copy)
		coded += 1
		return Code.apply(copy)
	end })
	local stage = workspace:FindFirstChild("__AnimInspect")
	local sheet = stage and stage:FindFirstChild("__Sheet")
	local copy = sheet and sheet:FindFirstChildWhichIsA("Model")
	local copyArm = copy and copy:FindFirstChild("Left Arm") :: BasePart?
	check(coded == 2 and copyArm ~= nil and near(copyArm.Color, leftArm), "a sheet codes each posed copy")
	check((r6:FindFirstChild("Left Arm") :: BasePart).Color == original, "the rig itself keeps its colours")
end)
Inspector.clear()
for _, item in temporary do
	item:Destroy()
end
assert(not workspace:FindFirstChild("__AnimInspect"), "review stage leaked")
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
