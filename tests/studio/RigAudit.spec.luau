--@use RigAudit, RigSkin, AnimationInspector
-- Run through studio_mcp.py in Edit mode: RigAudit.controller on generated R6 and R15 rigs (the Humanoid swapped for an
-- AnimationController) and the audit rules for rigs with no Humanoid. Creates and destroys its own rigs.
-- selene: allow(undefined_variable)
local Audit = RigAudit
-- selene: allow(undefined_variable)
local Skin = RigSkin
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
-- An audit's findings by rule, and its error count.
local function audit(model)
	local found, errors = {}, 0
	for _, f in (Audit.audit(model)) do
		found[f.Rule] = f.Detail
		errors += if f.Severity == "error" then 1 else 0
	end
	return found, errors
end
-- A clip audit's findings as a set of "severity rule path" lines.
local function findings(rig, clip)
	local set = {}
	for _, f in Inspector.audit(rig, clip).Findings do
		set[f.Severity .. " " .. f.Rule .. " " .. f.Path] = true
	end
	return set
end
local function same(a, b)
	for k in a do
		if not b[k] then
			return false
		end
	end
	for k in b do
		if not a[k] then
			return false
		end
	end
	return true
end

local WALK = { R6 = 180426354, R15 = 507777826 }
local ok, failure = pcall(function()
	local desc = own(Instance.new("HumanoidDescription"))
	desc.HeadColor = Color3.new(1, 0, 0)
	for _, rigType in { Enum.HumanoidRigType.R6, Enum.HumanoidRigType.R15 } do
		local kind = rigType.Name
		local function rig()
			local model = own(Players:CreateHumanoidModelFromDescription(desc, rigType))
			Audit.clean(model)
			return model
		end
		local bare = rig()
		local humanoid = bare:FindFirstChildOfClass("Humanoid") :: Humanoid
		local stood = if kind == "R15" then humanoid.HipHeight + 1 else 3
		local model = rig()
		Audit.controller(model)
		local controller = model:FindFirstChildOfClass("AnimationController")
		check(not model:FindFirstChildOfClass("Humanoid") and controller ~= nil and controller:FindFirstChildOfClass("Animator") ~= nil,
			kind .. ": the Humanoid is replaced by an AnimationController holding an Animator")
		check(math.abs(model:GetAttribute("RootHeight") - stood) < 1e-3, kind .. string.format(": RootHeight is where the Humanoid stood the root (%.2f)", stood))
		local root = model:FindFirstChild("HumanoidRootPart") :: BasePart
		check(root.Anchored and model.PrimaryPart == root, kind .. ": the root is anchored and the PrimaryPart")
		local dump, bareDump = HttpService:JSONDecode(Skin.dump(model)), HttpService:JSONDecode(Skin.dump(bare))
		check(dump.rigType == kind and math.abs(dump.rootHeight - bareDump.rootHeight) < 1e-3, kind .. ": RigSkin.dump reads the same rig without the Humanoid")
		local found, errors = audit(model)
		check(errors == 0 and not found.standing and not found.untinted and not found.clothing, kind .. ": the converted rig audits with 0 errors and no Humanoid warnings")
		check(string.find(Audit.controller(model), "no Humanoid", 1, true) ~= nil, kind .. ": converting again does nothing")
		check(same(findings(model, WALK[kind]), findings(bare, WALK[kind])), kind .. ": a stock walk audits the same with and without the Humanoid")
		local head = model:FindFirstChild("Head") :: BasePart
		if head:IsA("MeshPart") and head.TextureID ~= "" then
			local look = head:FindFirstChildOfClass("SurfaceAppearance")
			-- ColorMap reads back as rbxassetid://<id>, TextureID as an assetdelivery URL ending in the same id
			check(look ~= nil and look.AlphaMode == Enum.AlphaMode.Overlay and string.match(look.ColorMap, "%d+$") == string.match(head.TextureID, "%d+$"),
				kind .. ": the dynamic head is tinted by an Overlay SurfaceAppearance")
			look:Destroy()
			check(audit(model).untinted ~= nil, kind .. ": an untinted textured head is caught")
		end

		-- AddAccessory's joint comes a few frames late, and differs by rig: the audit and seat must find both kinds.
		local worn = rig()
		worn.Parent = workspace
		local accessory = Instance.new("Accessory")
		local handle = Instance.new("Part")
		handle.Name, handle.Size, handle.Anchored = "Handle", Vector3.new(1, 1, 1), false
		handle.Parent = accessory
		Instance.new("Attachment", handle).Name = "HairAttachment"
		;(worn:FindFirstChildOfClass("Humanoid") :: Humanoid):AddAccessory(accessory)
		local joint
		for _ = 1, 120 do
			joint = handle:FindFirstChild("AccessoryWeld") or handle:FindFirstChild("AccessoryRigidConstraint")
			if joint then
				break
			end
			task.wait()
		end
		local expected = if kind == "R6" then "Weld" else "RigidConstraint"
		check(joint ~= nil and joint:IsA(expected), kind .. ": AddAccessory joins the handle with a " .. expected)
		-- In Edit a joint snaps its handle in when it is made or re-parented, so only the generator leaves one off its seat.
		local wornFound = audit(worn)
		check(wornFound.unwelded == nil and wornFound.unseated == nil and Audit.seat(worn) == 0, kind .. ": the audit and seat find the " .. expected)
		worn.Parent = nil

		local loose = rig()
		Audit.controller(loose, { Anchored = false })
		check(audit(loose).standing ~= nil, kind .. ": an unanchored root with nothing holding it is caught")
		local attachment = Instance.new("Attachment")
		attachment.Parent = loose:FindFirstChild("HumanoidRootPart")
		local align = Instance.new("AlignPosition")
		align.Mode = Enum.PositionAlignmentMode.OneAttachment
		align.Attachment0 = attachment
		align.Parent = attachment.Parent
		check(audit(loose).standing == nil, kind .. ": a root held by AlignPosition passes")
		Instance.new("Shirt").Parent = loose
		check(audit(loose).clothing ~= nil, kind .. ": classic clothing without a Humanoid is caught")
	end
end)
for _, item in temporary do
	item:Destroy()
end
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
