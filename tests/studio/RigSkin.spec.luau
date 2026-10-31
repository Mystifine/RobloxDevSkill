--@use RigSkin
-- Run through studio_mcp.py in Edit mode: how RigSkin.equip seats a held weapon and what RigSkin.audit says about its fit in
-- the hand. Creates and destroys its own rigs and meshes.
-- selene: allow(undefined_variable)
local Skin = RigSkin
local AssetService = game:GetService("AssetService")
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

-- A MeshPart of boxes {x half, z from, z to, y from, y to}, centred on its bounds and placed where its centre was in the file
-- (the importer does the same to an upload). For a weapon the file's origin is its grip, its length along -Z.
local function boxes(name, list)
	local lo, hi = Vector3.one * math.huge, Vector3.one * -math.huge
	for _, b in list do
		lo = lo:Min(Vector3.new(-b[1], b[4], b[2]))
		hi = hi:Max(Vector3.new(b[1], b[5], b[3]))
	end
	local centre = (lo + hi) / 2
	local mesh = own(AssetService:CreateEditableMesh())
	for _, b in list do
		local ids = {}
		for i = 0, 7 do
			local p = Vector3.new(if i % 2 == 0 then -b[1] else b[1], if (i // 2) % 2 == 0 then b[4] else b[5], if i // 4 == 0 then b[2] else b[3])
			ids[i] = mesh:AddVertex(p - centre)
		end
		for _, q in { { 0, 2, 3, 1 }, { 4, 5, 7, 6 }, { 0, 1, 5, 4 }, { 2, 6, 7, 3 }, { 0, 4, 6, 2 }, { 1, 3, 7, 5 } } do
			mesh:AddTriangle(ids[q[1]], ids[q[2]], ids[q[3]])
			mesh:AddTriangle(ids[q[1]], ids[q[3]], ids[q[4]])
		end
	end
	local part = own(AssetService:CreateMeshPartAsync(Content.fromObject(mesh)))
	part.Name = name
	part.CFrame = CFrame.new(centre)
	return part
end

local HANDLE = { .08, -.7, .75, -.08, .08 }
local BLADE = { .05, -3.5, -.75, -.3, .3 }
local GUARD = { .1, -.75, -.68, -.5, .5 }
local POMMEL = { .12, .68, .9, -.12, .12 }
local FITS = { HANDLE, BLADE, GUARD, POMMEL }

-- The gear findings of an audit, by rule.
local function gear(rig)
	local found = {}
	for _, f in (Skin.audit(rig)) do
		if string.find(f.Path, ".Gear.", 1, true) then
			found[f.Rule] = f.Detail
		end
	end
	return found
end
local function none(found)
	return next(found) == nil
end

local ok, failure = pcall(function()
	local desc = own(Instance.new("HumanoidDescription"))
	for _, rigType in { Enum.HumanoidRigType.R6, Enum.HumanoidRigType.R15 } do
		local kind = rigType.Name
		local function rig()
			return own(Players:CreateHumanoidModelFromDescription(desc, rigType))
		end
		local function holding(list, options)
			local r = rig()
			return r, Skin.equip(r, boxes("Sword", list), options or { name = "Sword" })
		end
		local r, joint = holding(FITS)
		local grip = joint.Part0:FindFirstChild("RightGripAttachment") :: Attachment
		check(math.abs(joint.C0.Position.Y - grip.Position.Y - .16) < 1e-4, kind .. ": equip seats the handle 0.16 above the hand's end")
		check(none(gear(r)), kind .. ": a sword built to the fist passes")
		local bow = table.clone(FITS)
		table.insert(bow, { .05, -.75, .75, -.34, -.24 })
		check(none(gear((holding(bow)))), kind .. ": a knuckle bow under the hand passes")
		local inHand = gear((holding({ { .08, -.3, .75, -.08, .08 }, { .05, -3.5, -.28, -.3, .3 }, { .1, -.33, -.27, -.5, .5 }, POMMEL })))
		check(inHand.fist and string.find(inHand.fist, "0.27 ahead", 1, true) ~= nil, kind .. ": a guard and blade in the hand are caught")
		local pommel = gear((holding({ HANDLE, BLADE, GUARD, { .12, .4, .9, -.12, .12 } })))
		check(pommel.fist and string.find(pommel.fist, "behind", 1, true) ~= nil, kind .. ": a pommel in the hand is caught")
		check(gear((holding({ { .08, -.7, .5, -.08, .08 }, BLADE, GUARD }))).handle ~= nil, kind .. ": a handle ending in the fist is caught")
		check(gear((holding({ { .08, -.75, .7, -.08, .08 }, { .05, .75, 3.5, -.3, .3 } }))).facing ~= nil, kind .. ": a weapon facing backward is caught")
		check(gear((holding(FITS, { name = "Sword", seat = 0 }))).seat ~= nil, kind .. ": a handle along the outside of the fist is caught")

		-- A glove 1.5 studs across makes the fist bigger: the same sword's guard and pommel are now in it.
		-- Stood in the skin's file space (facing -Z, the ground at 0), so the glove is modeled where the hand is.
		local gloved = rig()
		local root = gloved:FindFirstChild("HumanoidRootPart") :: BasePart
		local at = CFrame.new(0, HttpService:JSONDecode(Skin.dump(gloved)).rootHeight, 0)
		gloved:PivotTo(at * root.CFrame:ToObjectSpace(gloved:GetPivot())) -- the root, not the model's pivot, goes there
		local hand = (gloved:FindFirstChild("RightHand") or gloved:FindFirstChild("Right Arm")) :: BasePart
		local bottom = hand.Position.Y - hand.Size.Y / 2
		local glove = boxes(hand.Name .. "__Glove", { { .75, -.75, .75, bottom - .02, bottom + .3 } })
		glove.CFrame += Vector3.new(hand.Position.X, 0, hand.Position.Z)
		local skin = own(Instance.new("Model"))
		glove.Parent = skin
		Skin.apply(gloved, skin)
		Skin.equip(gloved, boxes("Sword", FITS), { name = "Sword" })
		local found = gear(gloved)
		check(found.fist ~= nil and string.find(found.fist, "past 0.80", 1, true) ~= nil, kind .. ": the fist is measured around the glove")
	end
end)
for _, item in temporary do
	item:Destroy()
end
assert(ok, tostring(failure) .. "; checks completed: " .. table.concat(results, ", "))
return HttpService:JSONEncode({ passed = #results, checks = results })
