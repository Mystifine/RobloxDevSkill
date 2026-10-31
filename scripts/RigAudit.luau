--!strict
-- Character model check for Studio (Edit mode), R15 and R6 (references/rigs.md):
--
--   audit(model)          findings: missing parts or joints, the root and PrimaryPart, anchored limbs, accessories off
--                         their welds (they float in anchored models, viewports and previews), unmatched attachments,
--                         layered clothing without cages, leftover scripts, TouchInterests, a default face under a face
--                         accessory; with no Humanoid, a root nothing holds up, classic clothing and untinted textures
--   seat(model)           puts every accessory handle where its weld holds it; returns how many moved
--   clean(model, keep?)   removes generated scripts (unless keep.Scripts), the handles' TouchInterests and the default
--                         face under a face accessory, and makes the root the PrimaryPart; returns what it did
--   controller(model, options?)  replaces the Humanoid with an AnimationController holding its Animator, keeping what
--                         the Humanoid did for the rig (see controller); anchors the root unless options.Anchored is
--                         false; returns what it did. Studio only, last, once accessories are on
--
-- Load as SKILL.md (Scripts) describes.

local RigAudit = {}

export type Finding = { Severity: "error" | "warn", Path: string, Rule: string, Detail: string }

local PARTS = {
	R15 = { "Head", "UpperTorso", "LowerTorso", "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
		"LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot" },
	R6 = { "Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg" },
}
local SEATED = 0.05 -- studs a handle may sit from where its weld holds it

local function rigType(model: Model): string
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	if humanoid then
		return humanoid.RigType.Name
	end
	return if model:FindFirstChild("UpperTorso") then "R15" elseif model:FindFirstChild("Torso") then "R6" else "custom"
end

-- Where the accessory's weld holds its handle (a Weld, or a RigidConstraint between two attachments).
local function seatOf(handle: BasePart): CFrame?
	local weld = handle:FindFirstChild("AccessoryWeld")
	if weld and weld:IsA("Weld") and weld.Part0 and weld.Part1 then
		return if weld.Part0 == handle then (weld.Part1 :: BasePart).CFrame * weld.C1 * weld.C0:Inverse() else (weld.Part0 :: BasePart).CFrame * weld.C0 * weld.C1:Inverse()
	elseif weld and weld:IsA("RigidConstraint") and weld.Attachment0 and weld.Attachment1 then
		local mine, other = weld.Attachment0, weld.Attachment1
		if mine.Parent ~= handle then
			mine, other = other, mine
		end
		return other.WorldCFrame * mine.CFrame:Inverse()
	end
	return nil
end

local function accessories(model: Model): { { Accessory: Accessory, Handle: BasePart? } }
	local list = {}
	for _, child in model:GetChildren() do
		if child:IsA("Accessory") then
			local handle = child:FindFirstChild("Handle")
			table.insert(list, { Accessory = child, Handle = if handle and handle:IsA("BasePart") then handle else nil })
		end
	end
	return list
end

local function wearsFace(model: Model): boolean
	for _, item in accessories(model) do
		if item.Accessory.AccessoryType == Enum.AccessoryType.Face then
			return true
		end
	end
	return false
end

function RigAudit.audit(model: Model): ({ Finding }, string)
	local findings: { Finding } = {}
	local function add(severity: string, path: string, rule: string, detail: string)
		table.insert(findings, { Severity = severity :: any, Path = path, Rule = rule, Detail = detail })
	end
	local kind = rigType(model)
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	local controller = model:FindFirstChildOfClass("AnimationController")
	local root = model:FindFirstChild("HumanoidRootPart") :: BasePart?
	local animates = humanoid or controller
	if not animates then
		add("error", model.Name, "rig", "no Humanoid or AnimationController")
	elseif not animates:FindFirstChildOfClass("Animator") then
		add("warn", animates.Name, "rig", "no Animator: add one so animations load and replicate")
	end
	for _, name in PARTS[kind] or {} do
		if not model:FindFirstChild(name) then
			add("error", name, "parts", "missing " .. kind .. " body part")
		end
	end
	if not root then
		add("error", model.Name, "root", "no HumanoidRootPart")
	else
		if model.PrimaryPart ~= root then
			add("warn", model.Name, "root", "PrimaryPart is " .. (if model.PrimaryPart then model.PrimaryPart.Name else "unset") .. ": make it the HumanoidRootPart (clean)")
		end
		if root.Transparency < 1 then
			add("warn", root.Name, "root", "the root is visible: Transparency 1")
		end
		if not humanoid and not root.Anchored and not model:FindFirstChildWhichIsA("AlignPosition", true) then
			add("warn", root.Name, "standing", "no Humanoid holds it up and its legs do not collide, so it sinks about 2 studs: anchor the root and move it by CFrame, or hold it with AlignPosition and AlignOrientation")
		end
	end

	-- every body part hangs from the root through animated joints (Motor6D or AnimationConstraint)
	local body: { [BasePart]: boolean } = {}
	for _, child in model:GetChildren() do
		if child:IsA("BasePart") then
			body[child] = true
			if child.Anchored and child ~= root then
				add("warn", child.Name, "anchored", "an anchored body part cannot animate: anchor only the root (a display, or a rig with no Humanoid)")
			end
			if not humanoid and child:IsA("MeshPart") and child.TextureID ~= "" and child.Transparency < 1 and not child:FindFirstChildOfClass("SurfaceAppearance") then
				add("warn", child.Name, "untinted", "its texture shows untinted with no Humanoid (a dynamic head turns white): controller gives it an Overlay SurfaceAppearance")
			end
		elseif child:IsA("Clothing") and not humanoid then
			add("warn", child.Name, "clothing", "classic Shirt and Pants show only on a rig with a Humanoid: use layered clothing or a skin, or the Humanoid build")
		end
	end
	local links: { [BasePart]: { BasePart } } = {}
	local function link(a: Instance?, b: Instance?)
		if a and b and a:IsA("BasePart") and b:IsA("BasePart") and body[a] and body[b] then
			links[a] = links[a] or {}
			links[b] = links[b] or {}
			table.insert(links[a], b)
			table.insert(links[b], a)
		end
	end
	for _, item in model:GetDescendants() do
		if item:IsA("Motor6D") and item.Enabled then
			link(item.Part0, item.Part1)
		elseif item:IsA("AnimationConstraint") and item.Enabled and item.Attachment0 and item.Attachment1 then
			link(item.Attachment0.Parent, item.Attachment1.Parent)
		end
	end
	if root then
		local reached = { [root] = true }
		local queue = { root }
		local index = 1
		while index <= #queue do
			for _, other in (links[queue[index]] or {}) :: { BasePart } do
				if not reached[other] then
					reached[other] = true
					table.insert(queue, other)
				end
			end
			index += 1
		end
		for part in body do
			if not reached[part] then
				add("error", part.Name, "joint", "not joined to the root by a Motor6D or AnimationConstraint: it falls off or never animates (R15: Humanoid:BuildRigFromAttachments())")
			end
		end
	end

	-- accessories: welded, seated, attachable, and layered clothing with cages to wrap
	local points: { [string]: boolean } = {}
	local cages = false
	for part in body do
		for _, child in part:GetChildren() do
			if child:IsA("Attachment") then
				points[child.Name] = true
			elseif child:IsA("WrapTarget") then
				cages = true
			end
		end
	end
	for _, item in accessories(model) do
		local name = item.Accessory.Name
		local handle = item.Handle
		if not handle then
			add("error", name, "unwelded", "no Handle")
			continue
		end
		local seat = seatOf(handle)
		if not seat then
			add("error", name, "unwelded", "no AccessoryWeld: Humanoid:AddAccessory(accessory) makes one")
		elseif (seat.Position - handle.Position).Magnitude > SEATED then
			add("error", name, "unseated", string.format("handle sits %.2f studs from its weld: it floats in anchored models, viewports and previews (seat)",
				(seat.Position - handle.Position).Magnitude))
		end
		local matched, named = false, false
		for _, child in handle:GetChildren() do
			if child:IsA("Attachment") then
				named = true
				matched = matched or points[child.Name] == true
			elseif child:IsA("TouchTransmitter") then
				add("warn", name, "touch", "TouchInterest on the handle: remove it unless the game listens for Touched on accessories (clean)")
			end
		end
		if named and not matched then
			add("warn", name, "unmatched", "no body attachment shares the handle's attachment name, so it cannot be re-attached or rescaled")
		end
		if handle:FindFirstChildOfClass("WrapLayer") and not cages then
			add("error", name, "layered", if kind == "R6" then "layered clothing needs R15" else "WrapLayer but no WrapTarget cage on the body")
		end
	end

	local head = model:FindFirstChild("Head")
	if head and wearsFace(model) and (head:FindFirstChildOfClass("Decal") or (head:IsA("MeshPart") and head.TextureID ~= "")) then
		add("warn", "Head", "default-face", "the default face (head decal or head texture) shows through the face accessory (clean)")
	end
	for _, item in model:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			add("warn", item:GetFullName():sub(#model:GetFullName() + 2), "script", "generated script: remove it when the project animates characters itself (clean)")
		end
	end

	local lines, errors = {}, 0
	for _, finding in findings do
		errors += if finding.Severity == "error" then 1 else 0
		table.insert(lines, string.format("%s [%s] %s: %s", string.upper(finding.Severity), finding.Rule, finding.Path, finding.Detail))
	end
	table.insert(lines, string.format("%s %s%s: %d findings (%d errors)", model.Name, kind, if humanoid then "" else " (no Humanoid)", #findings, errors))
	return findings, table.concat(lines, "\n")
end

function RigAudit.seat(model: Model): number
	local moved = 0
	for _, item in accessories(model) do
		local handle = item.Handle
		local seat = if handle then seatOf(handle) else nil
		if handle and seat and (seat.Position - handle.Position).Magnitude > 1e-4 then
			handle.CFrame = seat
			moved += 1
		end
	end
	return moved
end

function RigAudit.clean(model: Model, keep: { Scripts: boolean? }?): string
	local done = {}
	local scripts, touches = 0, 0
	for _, item in model:GetDescendants() do
		if item:IsA("LuaSourceContainer") and not (keep and keep.Scripts) then
			item:Destroy()
			scripts += 1
		elseif item:IsA("TouchTransmitter") and item.Parent and item.Parent.Name == "Handle" and item.Parent.Parent and item.Parent.Parent:IsA("Accessory") then
			item:Destroy()
			touches += 1
		end
	end
	table.insert(done, scripts .. " scripts and " .. touches .. " TouchInterests removed")
	local head = model:FindFirstChild("Head")
	if head and wearsFace(model) then
		for _, child in head:GetChildren() do
			if child:IsA("Decal") then
				child:Destroy()
				table.insert(done, "head decal removed")
			end
		end
		if head:IsA("MeshPart") and head.TextureID ~= "" then
			head.TextureID = ""
			table.insert(done, "default head texture cleared")
		end
	end
	local root = model:FindFirstChild("HumanoidRootPart")
	if root and root:IsA("BasePart") and model.PrimaryPart ~= root then
		model.PrimaryPart = root
		table.insert(done, "PrimaryPart set to the root")
	end
	return table.concat(done, "; ")
end

-- A Humanoid costs every frame; a rig that only animates plays the same clips through an AnimationController. Kept from
-- the Humanoid (on generated R6 and R15):
--   - the height it stood the root at, as the RootHeight attribute (studs from the floor to the root's centre: R15
--     HipHeight plus half the root, R6 on its legs): place the root there, since nothing else holds it up;
--   - the skin color under a body part's texture: without a Humanoid a dynamic head showed its texture untinted (white
--     skin) though its Color was unchanged. An Overlay SurfaceAppearance on the texture shows the Color through it again,
--     as the Humanoid did. Game scripts cannot set its map (they lack the Plugin capability), so convert in Studio.
-- Removed with it: the Animate and Health scripts (they wait for a Humanoid), Status, the scale values and the
-- HumanoidDescription. Accessories keep their welds and layered clothing still wraps; classic Shirt and Pants stop showing.
function RigAudit.controller(model: Model, options: { Anchored: boolean? }?): string
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	if not humanoid then
		return model.Name .. ": no Humanoid to replace"
	end
	local root = model:FindFirstChild("HumanoidRootPart")
	assert(root and root:IsA("BasePart"), model:GetFullName() .. " has no HumanoidRootPart")
	local done = {}
	local leg = model:FindFirstChild("Left Leg")
	local height = if humanoid.RigType == Enum.HumanoidRigType.R6 and leg and leg:IsA("BasePart") then leg.Size.Y + root.Size.Y / 2
		else humanoid.HipHeight + root.Size.Y / 2
	model:SetAttribute("RootHeight", height)
	table.insert(done, string.format("Humanoid replaced by an AnimationController; RootHeight %.2f", height))

	local controller = Instance.new("AnimationController")
	local animator = humanoid:FindFirstChildOfClass("Animator") or Instance.new("Animator")
	animator.Parent = controller
	controller.Parent = model
	humanoid:Destroy()
	for _, name in { "Animate", "Health" } do
		local script = model:FindFirstChild(name)
		if script and script:IsA("LuaSourceContainer") then
			script:Destroy()
			table.insert(done, name .. " script removed")
		end
	end

	local tinted, untinted = 0, 0
	for _, part in model:GetChildren() do
		if part:IsA("MeshPart") and part.TextureID ~= "" and not part:FindFirstChildOfClass("SurfaceAppearance") then
			local made = pcall(function()
				local look = Instance.new("SurfaceAppearance")
				look.AlphaMode = Enum.AlphaMode.Overlay
				look.ColorMap = part.TextureID
				look.Parent = part
			end)
			tinted += if made then 1 else 0
			untinted += if made then 0 else 1
		end
	end
	if tinted > 0 then
		table.insert(done, tinted .. " textured body parts tinted by their Color (Overlay SurfaceAppearance)")
	end
	if untinted > 0 then
		table.insert(done, untinted .. " textured body parts left untinted: no Plugin capability here, so convert in Studio")
	end

	root.Anchored = not (options and options.Anchored == false)
	model.PrimaryPart = root
	table.insert(done, if root.Anchored then "root anchored" else "root left unanchored: hold it with AlignPosition and AlignOrientation")
	local clothing = 0
	for _, child in model:GetChildren() do
		clothing += if child:IsA("Clothing") then 1 else 0
	end
	if clothing > 0 then
		table.insert(done, clothing .. " classic Shirt/Pants no longer show")
	end
	return model.Name .. ": " .. table.concat(done, "; ")
end

return RigAudit
