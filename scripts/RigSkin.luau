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
--                               around the replica; options.looks styles each piece by the name after "__",
--                               options.colors colors the body, options.face sets its face, and options.hide (a design
--                               choice, rarely) hides the body parts it covers. Weld attachments left by deleted pieces
--                               are removed first, so a rig can be dressed again (bind too)
--   color(rig, colors)          body colors by BodyColors group (Head, Torso, LeftArm, RightArm, LeftLeg, RightLeg, or
--                               Body for all), on the parts and in the rig's BodyColors
--   bind(rig, skinned, options) a skinned MeshPart whose Bones are named after body parts: each Bone moves under its body
--                               part, so the mesh bends with the rig's joints; the mesh is welded to the root
--   equip(rig, gear, options)   a weapon or shield, its own model, on a Motor6D, so animations can move it: at the hand by
--                               default, its origin at the grip, seated inside the fist (options.seat); or anywhere on a
--                               body part (options.part, options.at)
--   doubleSided(root)           DoubleSided on every MeshPart under root (apply, bind and equip do it for what they touch)
--   audit(rig)                  findings: pieces unwelded, off their weld, astray from their part, anchored or collidable,
--                               Bones left unbound or astray, hidden body parts (with or without skin over them), weld
--                               attachments left by deleted pieces, MeshParts not double sided, gear off its Motor6D, a held
--                               weapon that does not fit the hand, read from its mesh and the skin's (needs a mesh this
--                               place may read, as its own uploads are)
--
-- A dynamic head (a MeshPart Head with FaceControls, as on a generated R15) maps a decal through its UV atlas: a face
-- came out magnified and offset, its mouth showing as a dark line (seen 2026-10-30). There `face` puts the decal on a
-- classic head piece ("Head__Face", sized to the head, welded like any piece) and hides the dynamic head, which stays
-- the hitbox and keeps the Neck.
--
-- Insert the skin asset and call apply or bind before moving it: the pieces carry the coordinates of the Blender scene
-- (ground at 0, the root at rootHeight, facing -Z). Everything is measured on the rig's rest pose (its joints without
-- the animation's Transform), so a player's character can be dressed on the server mid-animation. Load as SKILL.md
-- (Scripts) describes, or require it from ServerScriptService in a game.

local AssetService = game:GetService("AssetService")
local HttpService = game:GetService("HttpService")

local RigSkin = {}

export type Finding = { Severity: "error" | "warn", Path: string, Rule: string, Detail: string }
export type Options = {
	origin: CFrame?, -- where the root sat in the skin's file (default: CFrame.new(0, rootHeight, 0))
	map: { [string]: string }?, -- piece or bone name -> body part name, for names that do not follow the convention
	colors: { [string]: Color3 }?, -- body colors by BodyColors group, or Body for all (see color)
	looks: { [string]: { [string]: any } }?, -- name after "__" -> properties for those pieces, e.g. { Gold = { Color = c, Material = Enum.Material.Metal } }: imported MeshParts arrive gray Plastic; an Instance value (a SurfaceAppearance made in Studio) is cloned into each piece, replacing one of its class
	face: string?, -- an image for the head's face decal (rbxassetid://<image id>); a dynamic head gets a classic head piece for it
	hide: boolean?, -- hide the body parts the skin covers (and their decals, such as the face): only when the design replaces them
	hideAccessories: boolean?, -- hide the rig's own accessories (a player's hats would float over the skin's head)
}
export type Gear = {
	side: string?, -- "Right" (default) or "Left": the hand it is held in
	seat: number?, -- studs from the hand's end up to the handle's axis (default SEAT)
	part: string?, -- a body part instead of a hand, for gear worn on the arm or back
	at: CFrame?, -- with part: where the gear's origin sits, in the skin's file space (ground at 0, the root at rootHeight)
	name: string?, -- the gear's name, which is also its joint's: what an animation keys
}

local SEATED = 0.05 -- studs a piece may sit from where its weld holds it
local SKIN = "Skin" -- the folder under the rig that holds the pieces
local WELD = "SkinWeld" -- the RigidConstraint that holds a piece (its attachments: SkinWeld_<piece> on the body part, SkinWeldAttachment on the piece)
local FACE = "Head__Face" -- the classic head piece that carries the face on a dynamic head
local GEAR = "Gear" -- the folder under the rig that holds weapons and shields
-- A held weapon against the hand, as skin_kit.grip_fit measures it in Blender (references/rigs.md, Gear).
local SEAT = 0.16 -- studs from the hand's end up to the handle's axis: inside the fist, not along its underside
local HANDLE = 0.13 -- the widest a handle may be and stay inside the fist
local CLEAR = 0.05 -- what the guard and the butt stand clear of the fist
local WRIST = 0.3 -- how far above the hand's end the fist goes on
local ARM = 2 -- how far above the hand's end nothing but the handle may go: the arm's length on R6

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
	local named = bodyParts(rig)
	local out = {
		rigType = if humanoid then humanoid.RigType.Name elseif named.UpperTorso then "R15" elseif named.Torso then "R6" else "custom",
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

-- Weld attachments on the body parts whose RigidConstraint is gone: a Skin folder or piece deleted, or a dressing cut
-- off midway (a Studio call's reply can be lost while its code still runs).
local function stale(rig: Model): { Attachment }
	local used = {}
	for _, d in rig:GetDescendants() do
		if d:IsA("RigidConstraint") and d.Name == WELD and d.Attachment0 then
			used[d.Attachment0] = true
		end
	end
	local found = {}
	for _, part in bodyParts(rig) do
		for _, c in part:GetChildren() do
			if c:IsA("Attachment") and string.sub(c.Name, 1, #WELD + 1) == WELD .. "_" and not used[c] then
				table.insert(found, c)
			end
		end
	end
	return found
end

local function prune(rig: Model)
	for _, a in stale(rig) do
		a:Destroy()
	end
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
	local folder = rig:FindFirstChild(SKIN)
	local standIn = folder and folder:FindFirstChild(FACE)
	if standIn and standIn:IsA("BasePart") and (colors.Head or colors.Body) then
		standIn.Color = colors.Head or colors.Body
	end
	return count
end

-- The part that shows the face: the head, or on a dynamic head a classic head piece welded to it (see the header).
local function faceHolder(rig: Model, pose: { [BasePart]: CFrame }): (BasePart, boolean)
	local head = bodyParts(rig).Head
	assert(head, rig:GetFullName() .. " has no Head")
	if not (head:IsA("MeshPart") and head:FindFirstChildOfClass("FaceControls")) then
		return head, false
	end
	local folder = skinFolder(rig)
	local found = folder:FindFirstChild(FACE)
	if found and found:IsA("BasePart") then
		return found, true
	end
	local piece = Instance.new("Part")
	piece.Name = FACE
	piece.Size = Vector3.new(2, 1, 1) -- as an R6 head, whose face decals map as drawn
	piece.Color, piece.Material = head.Color, head.Material
	piece.TopSurface, piece.BottomSurface = Enum.SurfaceType.Smooth, Enum.SurfaceType.Smooth
	local mesh = Instance.new("SpecialMesh")
	mesh.MeshType = Enum.MeshType.Head
	mesh.Scale = head.Size / 0.96 -- a classic head is about 0.96 studs per unit of its scale
	mesh.Parent = piece
	local rest = root(rig).CFrame * pose[head]
	piece.CFrame = rest
	piece.Parent = folder
	weld(piece, head, rest)
	hide(head)
	return piece, true
end

local function setFace(rig: Model, image: string, pose: { [BasePart]: CFrame }, keepHead: boolean): boolean
	local holder, standIn = bodyParts(rig).Head, false
	if not keepHead then
		holder, standIn = faceHolder(rig, pose)
	end
	assert(holder, rig:GetFullName() .. " has no Head")
	local found = holder:FindFirstChild("face")
	local face: Decal = if found and found:IsA("Decal") then found else Instance.new("Decal")
	face.Name = "face"
	face.Face = Enum.NormalId.Front
	face.Texture = image
	face.Transparency = 0
	face.Parent = holder
	return standIn
end

-- The body's colors and face, before anything is hidden. With options.hide the face stays on the head, to be hidden too.
local function paintBody(rig: Model, pose: { [BasePart]: CFrame }, options: Options?): string
	local notes = {}
	if options and options.colors then
		table.insert(notes, RigSkin.color(rig, options.colors) .. " body parts colored")
	end
	if options and options.face then
		local standIn = setFace(rig, options.face, pose, options.hide == true)
		table.insert(notes, if standIn then "face set on a classic head piece (dynamic head hidden)" else "face set")
	end
	return if #notes > 0 then "; " .. table.concat(notes, ", ") else ""
end

-- A look's Instance values are cloned in: game scripts cannot set or read a SurfaceAppearance's maps (they lack the
-- Plugin capability), but can clone one made in Studio, maps and all (seen 2026-10-30).
local function style(piece: BasePart, options: Options?): boolean
	local looks = options and options.looks
	local look = looks and looks[(string.split(piece.Name, "__"))[2] or ""]
	if look then
		for property, value in look do
			if typeof(value) == "Instance" then
				local template = value :: Instance
				local old = piece:FindFirstChildOfClass(template.ClassName)
				if old then
					old:Destroy()
				end
				template:Clone().Parent = piece
			else
				(piece :: any)[property] = value
			end
		end
	end
	return look ~= nil
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

function RigSkin.doubleSided(model: Instance): number
	local count = 0
	local function set(item: Instance)
		if item:IsA("MeshPart") then
			-- Guarded because apply also runs in game scripts, which may lack the capability: a template made in Studio already has it.
			local done = pcall(function()
				if not item.DoubleSided then
					item.DoubleSided = true
					count += 1
				end
			end)
			if not done then
				return
			end
		end
	end
	set(model)
	for _, d in model:GetDescendants() do
		set(d)
	end
	return count
end

-- A weapon or shield stays its own model, one MeshPart outside the skin: it swaps without touching the skin, and its Motor6D is
-- a joint like any other, so an animation can key it. By default it is held at the base of the arm, perpendicular to the arm:
-- a gear's file origin is its grip, its length along -Z (the way the rig faces), so the same asset fits R6 and R15. The grip
-- attachment sits on the hand's end face, where a handle would run along the outside of the fist, so the handle is seated
-- above it. The joint's rotation stays at the rig's own, whichever way the grip attachment turns. Part1's name is what
-- animations address.
function RigSkin.equip(rig: Model, gear: BasePart, options: Gear?): Motor6D
	local parts, pose = bodyParts(rig), restPose(rig)
	local opts: Gear = options or {}
	local side = opts.side or "Right"
	local part = parts[opts.part or (side .. "Hand")] or parts[side .. " Arm"]
	assert(part, rig:GetFullName() .. " has no " .. (opts.part or side .. " hand"))
	local c0: CFrame
	if opts.at then
		local origin = CFrame.new(0, rootHeight(rig, pose), 0)
		c0 = pose[part]:ToObjectSpace(origin:Inverse() * opts.at)
	else
		local grip = part:FindFirstChild(side .. "GripAttachment")
		assert(grip and grip:IsA("Attachment"), part:GetFullName() .. " has no " .. side .. "GripAttachment")
		c0 = CFrame.new(grip.Position + Vector3.new(0, opts.seat or SEAT, 0))
	end
	local c1 = gear.CFrame:Inverse() -- the file's origin, in the gear's own space: its grip
	local found = rig:FindFirstChild(GEAR)
	local folder: Folder = if found and found:IsA("Folder") then found else Instance.new("Folder")
	folder.Name = GEAR
	folder.Parent = rig
	gear.Name = opts.name or gear.Name
	local old = folder:FindFirstChild(gear.Name)
	if old then
		old:Destroy()
	end
	local stale_ = part:FindFirstChild(gear.Name)
	if stale_ and stale_:IsA("Motor6D") then
		stale_:Destroy()
	end
	gear.Anchored, gear.Massless = false, true
	gear.CanCollide, gear.CanTouch, gear.CanQuery = false, false, false
	gear.PivotOffset = c1
	gear.CFrame = part.CFrame * c0 * c1:Inverse()
	gear.Parent = folder
	RigSkin.doubleSided(gear)
	local joint = Instance.new("Motor6D")
	joint.Name = gear.Name
	joint.Part0, joint.Part1 = part, gear
	joint.C0, joint.C1 = c0, c1
	joint.Parent = part
	return joint
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
	prune(rig)
	local pose, r = restPose(rig), root(rig)
	place(rig, pose, pieces, options)
	local folder, covered, unmatched, styled = skinFolder(rig), {}, {}, 0
	for _, piece in pieces do
		local target = parts[targetOf(piece.Name, options)]
		if target then
			piece.Parent = folder
			piece.PivotOffset = CFrame.identity -- imported pieces pivot at the file origin
			weld(piece, target, r.CFrame * pose[target])
			covered[target] = true
			styled += if style(piece, options) then 1 else 0
		else
			table.insert(unmatched, piece.Name)
		end
	end
	local painted = paintBody(rig, pose, options)
	RigSkin.doubleSided(rig)
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
	return string.format("%s: %d pieces welded (%d styled)%s; %d body parts and %d accessories hidden%s", rig.Name, #pieces - #unmatched, styled, painted, hidden,
		accessories, if #unmatched > 0 then "; no body part for: " .. table.concat(unmatched, ", ") else "")
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
	prune(rig)
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
	local painted = paintBody(rig, pose, options)
	RigSkin.doubleSided(rig)
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

-- A MeshPart's triangle edges, at its size, in its own space; nil for a mesh this place may not read.
local function meshEdges(part: MeshPart): { { Vector3 } }?
	local ok, mesh: any = pcall(function()
		return AssetService:CreateEditableMeshAsync(part.MeshContent)
	end)
	if not ok then
		return nil
	end
	local scale, edges = part.Size / part.MeshSize, {}
	for _, face in mesh:GetFaces() do
		local ids = mesh:GetFaceVertices(face)
		for i, id in ids do
			table.insert(edges, { mesh:GetPosition(id) * scale, mesh:GetPosition(ids[i % #ids + 1]) * scale })
		end
	end
	mesh:Destroy()
	return edges
end

-- The stretch of segment a..b inside the box lo..hi, or nothing.
local function clip(a: Vector3, b: Vector3, lo: Vector3, hi: Vector3): { Vector3 }
	local t0, t1 = 0, 1
	for _, axis in { "X", "Y", "Z" } do
		local from, step = (a :: any)[axis], (b :: any)[axis] - (a :: any)[axis]
		local low, high = (lo :: any)[axis], (hi :: any)[axis]
		if math.abs(step) < 1e-9 then
			if from < low or from > high then
				return {}
			end
		else
			local enter, leave = (low - from) / step, (high - from) / step
			t0, t1 = math.max(t0, math.min(enter, leave)), math.min(t1, math.max(enter, leave))
			if t0 > t1 then
				return {}
			end
		end
	end
	return { a:Lerp(b, t0), a:Lerp(b, t1) }
end

-- The hand's grip attachment when a joint holds its gear there, not worn elsewhere on the part.
local function gripOf(joint: Motor6D): Attachment?
	local part = joint.Part0
	for _, side in { "Right", "Left" } do
		local grip = part and part:FindFirstChild(side .. "GripAttachment")
		if grip and grip:IsA("Attachment") and (joint.C0.Position - grip.Position).Magnitude <= 0.5 then
			return grip
		end
	end
	return nil
end

-- How far the hand and the skin on it reach around the grip, in the hand's space: ahead, behind and to the side.
local function fistOf(rig: Model, part: BasePart, grip: Vector3): (number, number, number)
	local half = part.Size / 2
	local ahead, behind, side = half.Z, half.Z, half.X
	local folder = rig:FindFirstChild(SKIN)
	local lo, hi = Vector3.new(-math.huge, grip.Y, -math.huge), Vector3.new(math.huge, grip.Y + WRIST, math.huge)
	for _, piece in if folder then folder:GetDescendants() else {} do
		local rigid = piece:FindFirstChild(WELD)
		local a0 = rigid and rigid:IsA("RigidConstraint") and rigid.Attachment0
		if piece:IsA("MeshPart") and a0 and a0.Parent == part then
			local offset = part.CFrame:ToObjectSpace(piece.CFrame)
			for _, edge in meshEdges(piece) or {} do
				-- Edges, not vertices: a coarse glove can have none at the fist's height
				for _, p in clip(offset * edge[1], offset * edge[2], lo, hi) do
					ahead, behind, side = math.max(ahead, -p.Z), math.max(behind, p.Z), math.max(side, math.abs(p.X))
				end
			end
		end
	end
	return ahead, behind, side
end

-- A held weapon against the hand: the handle sits inside the fist, nothing else enters it, the handle comes out the back, and
-- the weapon runs forward and clears the ground at rest.
local function checkHold(rig: Model, item: MeshPart, joint: Motor6D, grip: Vector3, add: (string, string, string, string) -> ())
	local path = item:GetFullName()
	local edges = meshEdges(item)
	if not edges then
		add("warn", path, "unread", "its mesh cannot be read here, so its fit in the hand is unmeasured: look at the hand from below")
		return
	end
	local part = joint.Part0 :: BasePart
	local axis = joint.C0.Position
	if axis.Y - grip.Y < HANDLE then
		add("error", path, "seat", string.format("the handle's axis is %.2f above the hand's end, so it runs along the outside of the fist: equip seats it at %.2f", axis.Y - grip.Y, SEAT))
	end
	local ahead, behind, side = fistOf(rig, part, grip)
	local lo = Vector3.new(-side - CLEAR, grip.Y, -ahead - CLEAR)
	local hi = Vector3.new(side + CLEAR, grip.Y + ARM, behind + CLEAR)
	local held = joint.C0 * joint.C1:Inverse()
	local pose = restPose(rig)
	local ground, lowest = -rootHeight(rig, pose), math.huge
	local inAhead, inBehind = math.huge, math.huge
	local low, high = Vector3.one * math.huge, Vector3.one * -math.huge
	for _, edge in edges do
		local a, b = held * edge[1], held * edge[2]
		low, high = low:Min(a), high:Max(a)
		lowest = math.min(lowest, pose[part]:PointToWorldSpace(a).Y)
		for _, p in clip(a, b, lo, hi) do
			if Vector2.new(p.X - axis.X, p.Y - axis.Y).Magnitude > HANDLE + 1e-3 then
				if p.Z < axis.Z then
					inAhead = math.min(inAhead, axis.Z - p.Z)
				else
					inBehind = math.min(inBehind, p.Z - axis.Z)
				end
			end
		end
	end
	if inAhead < math.huge then
		add("error", path, "fist", string.format("wider than the handle %.2f ahead of the grip, inside the fist: start the guard and blade past %.2f", inAhead, ahead + CLEAR))
	end
	if inBehind < math.huge then
		add("error", path, "fist", string.format("wider than the handle %.2f behind the grip, inside the fist: start the pommel past %.2f", inBehind, behind + CLEAR))
	end
	if high.Z - axis.Z < behind + CLEAR then
		add("error", path, "handle", string.format("the handle ends %.2f behind the grip, inside the fist: it runs past %.2f", high.Z - axis.Z, behind + CLEAR))
	end
	local size = high - low
	if axis.Z - low.Z <= high.Z - axis.Z or size.Z < math.max(size.X, size.Y) then
		add("error", path, "facing", string.format("%.2f ahead of the grip and %.2f behind it, %.2f long: its length runs forward from the hand", axis.Z - low.Z, high.Z - axis.Z, size.Z))
	end
	if lowest < ground then
		add("warn", path, "floor", string.format("%.2f studs under the floor at rest", ground - lowest))
	end
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
	local standIn = folder and folder:FindFirstChild(FACE)
	for name, part in parts do
		-- a dynamic head hidden under its classic head piece is by design (see the header)
		if name ~= "HumanoidRootPart" and part.Transparency >= 1 and not (name == "Head" and standIn) then
			if not dressed[part] and not boundMesh then
				add("warn", part:GetFullName(), "bare", "hidden with no skin welded to it: that limb is invisible")
			else
				add("warn", part:GetFullName(), "hidden", "a hidden body part: fine only when the design replaces it; otherwise show it and color it to fit")
			end
		end
	end
	for _, a in stale(rig) do
		add("warn", a:GetFullName(), "stale", "a weld attachment left by a deleted piece: apply or bind removes it")
	end
	for _, d in rig:GetDescendants() do
		if d:IsA("MeshPart") and not d.DoubleSided then
			add("warn", d:GetFullName(), "single-sided", "every MeshPart stays DoubleSided: doubleSided(rig) sets them")
		end
	end
	local gear = rig:FindFirstChild(GEAR)
	if gear then
		local held: { [BasePart]: Motor6D } = {}
		for _, d in rig:GetDescendants() do
			if d:IsA("Motor6D") and d.Part1 then
				held[d.Part1] = d
			end
		end
		for _, item in gear:GetChildren() do
			if item:IsA("BasePart") then
				local joint = held[item]
				local grip = joint and gripOf(joint)
				if not joint then
					add("error", item:GetFullName(), "gear", "no Motor6D to the rig: animations cannot move it (equip makes one)")
				elseif grip and item:IsA("MeshPart") then
					checkHold(rig, item, joint, grip.Position, add)
				end
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
