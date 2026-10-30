--!strict
-- Skins for R6 and R15 characters in Studio, Edit mode (references/rigs.md, Skins). A skin dresses a standard rig and
-- never replaces it: the rig keeps its parts, joints, cages, scaling and hitboxes, and its body stays visible, colored to
-- fit; the art is built around it.
--
--   dump(rig)                   JSON for building the rig's replica in Blender (scripts/roblox_rig.py): body parts (size,
--                               CFrame), joint frames and attachments, all relative to the HumanoidRootPart, plus
--                               rootHeight (studs from the ground to the root's centre)
--   apply(rig, skin, options)   welds every part of `skin` to the body part it is named after ("LeftUpperArm",
--                               "Left Arm", or "Head__Halo" for several pieces on one part), placed as it was modeled
--                               around the replica; options.colors colors the body, options.face sets its face, and
--                               options.hide (a design choice, rarely) hides the body parts it covers
--   color(rig, colors)          body colors by BodyColors group (Head, Torso, LeftArm, RightArm, LeftLeg, RightLeg, or
--                               Body for all), on the parts and in the rig's BodyColors
--   bind(rig, skinned, options) a skinned MeshPart whose Bones are named after body parts: each Bone moves under its body
--                               part, so the mesh bends with the rig's joints; the mesh is welded to the root
--   audit(rig)                  findings: pieces unwelded, off their weld, astray from their part, anchored or collidable,
--                               Bones left unbound or astray, hidden body parts (with or without skin over them)
--
-- Insert the skin asset and call apply or bind before moving it: the pieces carry the coordinates of the Blender scene
-- (ground at 0, the root at rootHeight, facing -Z). Everything is measured on the rig's rest pose (its joints without
-- the animation's Transform), so a player's character can be dressed on the server mid-animation. Load as SKILL.md
-- (Scripts) describes, or require it from ServerScriptService in a game.

local HttpService = game:GetService("HttpService")

local RigSkin = {}

export type Finding = { Severity: "error" | "warn", Path: string, Rule: string, Detail: string }
export type Options = {
	origin: CFrame?, -- where the root sat in the skin's file (default: CFrame.new(0, rootHeight, 0))
	map: { [string]: string }?, -- piece or bone name -> body part name, for names that do not follow the convention
	colors: { [string]: Color3 }?, -- body colors by BodyColors group, or Body for all (see color)
	face: string?, -- an image for the head's face decal (rbxassetid://<image id>)
	hide: boolean?, -- hide the body parts the skin covers (and their decals, such as the face): only when the design replaces them
	hideAccessories: boolean?, -- hide the rig's own accessories (a player's hats would float over the skin's head)
}

local SEATED = 0.05 -- studs a piece may sit from where its weld holds it
local SKIN = "Skin" -- the folder under the rig that holds the pieces
local WELD = "SkinWeld" -- the RigidConstraint that holds a piece (its attachments: SkinWeld_<piece> on the body part, SkinWeldAttachment on the piece)

local function root(rig: Model): BasePart
	local r = rig:FindFirstChild("HumanoidRootPart")
	assert(r and r:IsA("BasePart"), rig:GetFullName() .. " has no HumanoidRootPart")
	return r
end

-- Body parts: BaseParts directly under the rig (not accessory handles or skin pieces).
local function bodyParts(rig: Model): { [string]: BasePart }
	local parts = {}
	for _, child in rig:GetChildren() do
		if child:IsA("BasePart") then
			parts[child.Name] = child
		end
	end
	return parts
end

-- Each body part's CFrame relative to the root with every joint at rest: Motor6D (Part1 = Part0 * C0 * Transform *
-- C1^-1) and AnimationConstraint (Part1 = Part0 * Attachment0 * Transform * Attachment1^-1), Transform left out.
-- Parts no joint reaches keep where they are.
local function restPose(rig: Model): { [BasePart]: CFrame }
	local r = root(rig)
	local links: { [BasePart]: { { child: BasePart, offset: CFrame } } } = {}
	local function link(parent: Instance?, child: Instance?, offset: CFrame)
		if parent and child and parent:IsA("BasePart") and child:IsA("BasePart") then
			links[parent] = links[parent] or {}
			table.insert(links[parent], { child = child, offset = offset })
		end
	end
	for _, d in rig:GetDescendants() do
		if d:IsA("Motor6D") then
			link(d.Part0, d.Part1, d.C0 * d.C1:Inverse())
		elseif d:IsA("AnimationConstraint") and d.Attachment0 and d.Attachment1 then
			link(d.Attachment0.Parent, d.Attachment1.Parent, d.Attachment0.CFrame * d.Attachment1.CFrame:Inverse())
		end
	end
	local pose: { [BasePart]: CFrame } = { [r] = CFrame.identity }
	local queue = { r }
	while #queue > 0 do
		local parent = table.remove(queue, 1) :: BasePart
		local children = links[parent]
		if children then
			for _, l in children do
				if not pose[l.child] then
					pose[l.child] = pose[parent] * l.offset
					table.insert(queue, l.child)
				end
			end
		end
	end
	for _, part in bodyParts(rig) do
		pose[part] = pose[part] or r.CFrame:ToObjectSpace(part.CFrame)
	end
	return pose
end

-- Studs from the ground (the lowest body-part bottom) up to the root's centre, at rest.
local function rootHeight(rig: Model, pose: { [BasePart]: CFrame }): number
	local lowest = 0
	for _, part in bodyParts(rig) do
		local half = part.Size / 2
		for _, x in { -half.X, half.X } do
			for _, y in { -half.Y, half.Y } do
				for _, z in { -half.Z, half.Z } do
					lowest = math.min(lowest, pose[part]:PointToWorldSpace(Vector3.new(x, y, z)).Y)
				end
			end
		end
	end
	return -lowest
end

local function components(c: CFrame): { number }
	local t = { c:GetComponents() }
	for i, v in t do
		t[i] = math.round(v * 1e5) / 1e5
	end
	return t
end

function RigSkin.dump(rig: Model): string
	local pose = restPose(rig)
	local humanoid = rig:FindFirstChildOfClass("Humanoid")
	local out = {
		rigType = if humanoid then humanoid.RigType.Name else "custom",
		rootHeight = rootHeight(rig, pose),
		parts = {},
		joints = {},
	}
	for name, part in bodyParts(rig) do
		local attachments = {}
		for _, c in part:GetChildren() do
			if c:IsA("Attachment") then
				attachments[c.Name] = components(c.CFrame)
			end
		end
		local entry = { size = { part.Size.X, part.Size.Y, part.Size.Z }, cframe = components(pose[part]), attachments = attachments,
			color = { part.Color.R, part.Color.G, part.Color.B } } :: { [string]: any }
		-- A classic head is rounded: on R6 a SpecialMesh about 0.96 studs per unit of its scale, on R15 a MeshPart its size.
		local mesh = part:FindFirstChildOfClass("SpecialMesh")
		if mesh and mesh.MeshType == Enum.MeshType.Head then
			entry.shape, entry.visual = "head", { mesh.Scale.X * .96, mesh.Scale.Y * .96, mesh.Scale.Z * .96 }
		elseif name == "Head" then
			entry.shape, entry.visual = "head", entry.size
		end
		out.parts[name] = entry
	end
	for _, d in rig:GetDescendants() do
		if d:IsA("Motor6D") then
			local p0, p1 = d.Part0, d.Part1
			if p0 and p1 and pose[p0] then
				out.joints[d.Name] = { part0 = p0.Name, part1 = p1.Name, frame = components(pose[p0] * d.C0) }
			end
		elseif d:IsA("AnimationConstraint") then
			local a0, a1 = d.Attachment0, d.Attachment1
			local p0 = a0 and a0.Parent
			if a0 and a1 and p0 and p0:IsA("BasePart") and pose[p0] then
				local p1 = a1.Parent
				out.joints[d.Name] = { part0 = p0.Name, part1 = if p1 then p1.Name else "", frame = components(pose[p0] * a0.CFrame) }
			end
		end
	end
	return HttpService:JSONEncode(out)
end

local function targetOf(name: string, options: Options?): string
	local mapped = options and options.map and options.map[name]
	if mapped then
		return mapped
	end
	return (string.split(name, "__"))[1]
end

local function skinFolder(rig: Model): Folder
	local found = rig:FindFirstChild(SKIN)
	if found and found:IsA("Folder") then
		return found
	end
	local folder = Instance.new("Folder")
	folder.Name = SKIN
	folder.Parent = rig
	return folder
end

-- Holds a piece placed against the rest pose (`rest`: where `to` sits at rest, in world space) on `to`, and moves it
-- onto `to` as it is posed now. A RigidConstraint, because a Humanoid's death (BreakJointsOnDeath) breaks every Weld
-- and WeldConstraint in the character, which drops the pieces through the floor; the RigidConstraint keeps each piece
-- on its limb as the body falls apart (tested in Play on R6, Rig Builder R15 and avatar R15).
local function weld(piece: BasePart, to: BasePart, rest: CFrame)
	local old = piece:FindFirstChild(WELD)
	if old and old:IsA("RigidConstraint") then
		for _, a in { old.Attachment0, old.Attachment1 } do
			if a then
				a:Destroy()
			end
		end
	end
	if old then
		old:Destroy()
	end
	local a0 = Instance.new("Attachment")
	a0.Name = WELD .. "_" .. piece.Name
	a0.CFrame = rest:ToObjectSpace(piece.CFrame)
	a0.Parent = to
	local a1 = Instance.new("Attachment")
	a1.Name = WELD .. "Attachment"
	a1.Parent = piece
	local w = Instance.new("RigidConstraint")
	w.Name = WELD
	w.Attachment0 = a0
	w.Attachment1 = a1
	piece.CFrame = to.CFrame * a0.CFrame
	w.Parent = piece
	piece.Anchored = false
	piece.CanCollide = false
	piece.CanTouch = false
	piece.CanQuery = false
	piece.Massless = true
end

local function hide(part: BasePart)
	part.Transparency = 1
	for _, c in part:GetChildren() do
		if c:IsA("Decal") then
			c.Transparency = 1
		end
	end
end

-- BodyColors groups and the R6 and R15 body parts each one colors.
local GROUPS: { [string]: { string } } = {
	Head = { "Head" },
	Torso = { "Torso", "UpperTorso", "LowerTorso" },
	LeftArm = { "Left Arm", "LeftUpperArm", "LeftLowerArm", "LeftHand" },
	RightArm = { "Right Arm", "RightUpperArm", "RightLowerArm", "RightHand" },
	LeftLeg = { "Left Leg", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot" },
	RightLeg = { "Right Leg", "RightUpperLeg", "RightLowerLeg", "RightFoot" },
}

function RigSkin.color(rig: Model, colors: { [string]: Color3 }): number
	for key in colors do
		assert(key == "Body" or GROUPS[key], "color: unknown group " .. key .. " (Head, Torso, LeftArm, RightArm, LeftLeg, RightLeg or Body)")
	end
	local parts = bodyParts(rig)
	local found = rig:FindFirstChildOfClass("BodyColors")
	local body: BodyColors = if found then found else Instance.new("BodyColors")
	body.Parent = rig
	local count = 0
	for group, names in GROUPS do
		local color = colors[group] or colors.Body
		if color then
			(body :: any)[group .. "Color3"] = color
			for _, name in names do
				local part = parts[name]
				if part then
					part.Color = color
					count += 1
				end
			end
		end
	end
	return count
end

local function setFace(rig: Model, image: string)
	local head = bodyParts(rig).Head
	assert(head, rig:GetFullName() .. " has no Head")
	local found = head:FindFirstChild("face")
	local face: Decal = if found and found:IsA("Decal") then found else Instance.new("Decal")
	face.Name = "face"
	face.Face = Enum.NormalId.Front
	face.Texture = image
	face.Transparency = 0
	face.Parent = head
end

-- The body's colors and face, before anything is hidden.
local function paintBody(rig: Model, options: Options?): string
	local notes = {}
	if options and options.colors then
		table.insert(notes, RigSkin.color(rig, options.colors) .. " body parts colored")
	end
	if options and options.face then
		setFace(rig, options.face)
		table.insert(notes, "face set")
	end
	return if #notes > 0 then "; " .. table.concat(notes, ", ") else ""
end

local function hideAccessories(rig: Model): number
	local count = 0
	for _, child in rig:GetChildren() do
		if child:IsA("Accessory") then
			for _, d in child:GetDescendants() do
				if d:IsA("BasePart") then
					hide(d)
				end
			end
			count += 1
		end
	end
	return count
end

-- Moves the skin's parts from file space onto the rig at rest: file space * origin^-1 * root.
local function place(rig: Model, pose: { [BasePart]: CFrame }, items: { BasePart }, options: Options?)
	local origin = (options and options.origin) or CFrame.new(0, rootHeight(rig, pose), 0)
	local toRig = root(rig).CFrame * origin:Inverse()
	for _, item in items do
		item.CFrame = toRig * item.CFrame
	end
end

function RigSkin.apply(rig: Model, skin: Instance, options: Options?): string
	local parts = bodyParts(rig)
	local pieces: { BasePart } = {}
	for _, d in skin:GetDescendants() do
		if d:IsA("BasePart") then
			table.insert(pieces, d)
		end
	end
	if skin:IsA("BasePart") then
		table.insert(pieces, skin)
	end
	local pose, r = restPose(rig), root(rig)
	place(rig, pose, pieces, options)
	local folder, covered, unmatched = skinFolder(rig), {}, {}
	for _, piece in pieces do
		local target = parts[targetOf(piece.Name, options)]
		if target then
			piece.Parent = folder
			piece.PivotOffset = CFrame.identity -- imported pieces pivot at the file origin
			weld(piece, target, r.CFrame * pose[target])
			covered[target] = true
		else
			table.insert(unmatched, piece.Name)
		end
	end
	local painted = paintBody(rig, options)
	local hidden = 0
	if options and options.hide then
		for part in covered do
			hide(part)
			hidden += 1
		end
	end
	local accessories = if options and options.hideAccessories then hideAccessories(rig) else 0
	if skin.Parent and #skin:GetChildren() == 0 then
		skin:Destroy()
	end
	return string.format("%s: %d pieces welded%s; %d body parts and %d accessories hidden%s", rig.Name, #pieces - #unmatched, painted, hidden, accessories,
		if #unmatched > 0 then "; no body part for: " .. table.concat(unmatched, ", ") else "")
end

function RigSkin.bind(rig: Model, skinned: Instance, options: Options?): string
	local mesh = if skinned:IsA("MeshPart") then skinned else skinned:FindFirstChildWhichIsA("MeshPart", true)
	assert(mesh, "bind: no skinned MeshPart in " .. skinned:GetFullName())
	local bones: { Bone } = {}
	for _, d in skinned:GetDescendants() do
		if d:IsA("Bone") then
			table.insert(bones, d)
		end
	end
	local pose, r = restPose(rig), root(rig)
	place(rig, pose, { mesh }, options)
	-- Bones follow their parent; record where each sits before moving any.
	local world = {}
	for _, bone in bones do
		world[bone] = bone.WorldCFrame
	end
	local parts, bound, loose = bodyParts(rig), 0, {}
	mesh.Parent = skinFolder(rig)
	weld(mesh, r, r.CFrame)
	for _, bone in bones do
		local target = parts[targetOf(bone.Name, options)]
		if target then
			bone.Parent = target
			bone.CFrame = (r.CFrame * pose[target]):ToObjectSpace(world[bone])
			bound += 1
		else
			table.insert(loose, bone.Name)
		end
	end
	local painted = paintBody(rig, options)
	if options and options.hide then
		for name, part in parts do
			if name ~= "HumanoidRootPart" then
				hide(part)
			end
		end
	end
	if options and options.hideAccessories then
		hideAccessories(rig)
	end
	if skinned ~= mesh and skinned.Parent then
		skinned:Destroy()
	end
	return string.format("%s: %d bones bound to body parts%s%s", rig.Name, bound, painted,
		if #loose > 0 then "; left on the mesh (rigid): " .. table.concat(loose, ", ") else "")
end

function RigSkin.audit(rig: Model): ({ Finding }, string)
	local findings: { Finding } = {}
	local function add(severity: "error" | "warn", path: string, rule: string, detail: string)
		table.insert(findings, { Severity = severity, Path = path, Rule = rule, Detail = detail })
	end
	local parts = bodyParts(rig)
	local folder = rig:FindFirstChild(SKIN)
	local dressed = {}
	if folder then
		for _, piece in folder:GetDescendants() do
			if piece:IsA("BasePart") then
				local path = piece:GetFullName()
				local w = piece:FindFirstChild(WELD)
				local rigid = if w and w:IsA("RigidConstraint") and w.Enabled then w else nil
				local a0, a1 = rigid and rigid.Attachment0, rigid and rigid.Attachment1
				local holder = a0 and a0.Parent
				local part = if holder and holder:IsA("BasePart") and parts[holder.Name] == holder then holder else nil
				if not (a0 and a1 and a1.Parent == piece and part) then
					add("error", path, "unwelded", "no SkinWeld (RigidConstraint) to a body part: RigSkin.apply (or bind) makes one")
				else
					local held = a0.WorldCFrame * a1.CFrame:Inverse()
					if (held.Position - piece.Position).Magnitude > SEATED then
						add("error", path, "unseated", string.format("%.2f studs from where its weld holds it", (held.Position - piece.Position).Magnitude))
					end
					local gap = (piece.Position - part.Position).Magnitude
					if gap > (piece.Size.Magnitude + part.Size.Magnitude) / 2 then
						add("error", path, "astray", string.format("%.2f studs from %s, clear of it: exported with its origin off the scene origin (roblox_rig.export_pieces), or named after the wrong part", gap, part.Name))
					end
					dressed[part] = true
				end
				if piece.Anchored then
					add("error", path, "anchored", "anchored pieces pin the rig: unanchor it")
				end
				if piece.CanCollide or piece.CanTouch or piece.CanQuery then
					add("warn", path, "collision", "the body parts are the hitbox: turn off CanCollide, CanTouch and CanQuery")
				end
				if not piece.Massless then
					add("warn", path, "mass", "set Massless so the skin does not change how the rig moves")
				end
			elseif piece:IsA("Bone") then
				local p = piece.Parent
				if p and p:IsA("BasePart") and parts[piece.Name] and p ~= parts[piece.Name] then
					add("warn", piece:GetFullName(), "unbound", "a Bone named after a body part still sits on the mesh: RigSkin.bind moves it")
				end
			end
		end
	end
	for _, d in rig:GetDescendants() do
		if d:IsA("Bone") and d.Parent and parts[d.Parent.Name] == d.Parent then
			local part = d.Parent :: BasePart
			dressed[part] = true
			if d.Position.Magnitude > part.Size.Magnitude / 2 + SEATED then
				add("error", d:GetFullName(), "astray", string.format("%.2f studs from the centre of %s, outside it: the skinned mesh was placed with the wrong origin", d.Position.Magnitude, part.Name))
			end
		end
	end
	local boundMesh = folder and folder:FindFirstChildWhichIsA("MeshPart", true)
	for name, part in parts do
		if name ~= "HumanoidRootPart" and part.Transparency >= 1 then
			if not dressed[part] and not boundMesh then
				add("warn", part:GetFullName(), "bare", "hidden with no skin welded to it: that limb is invisible")
			else
				add("warn", part:GetFullName(), "hidden", "a hidden body part: fine only when the design replaces it; otherwise show it and color it to fit")
			end
		end
	end
	local errors = 0
	for _, f in findings do
		if f.Severity == "error" then
			errors += 1
		end
	end
	local lines = { string.format("%s skin: %d findings (%d errors)", rig.Name, #findings, errors) }
	for _, f in findings do
		table.insert(lines, string.format("%s [%s] %s: %s", string.upper(f.Severity), f.Rule, f.Path, f.Detail))
	end
	return findings, table.concat(lines, "\n")
end

return RigSkin
