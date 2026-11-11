--!strict
-- Blender clips as KeyframeSequences on the real rig, in Edit (references/animation/blender.md). clip_import.py sends the data,
-- builds, audits and saves; call these directly for anything else.
--
--   rbxanim(rig, data, options) -> (KeyframeSequence, { string })
--       a .rbxanim (Cautioned's exporter, r6_rig.export): each part's 12 numbers are its joint's Transform (a Pose's CFrame),
--       nested by the rig's own joint tree (Motor6D or AnimationConstraint). Returns the names the rig lacks (their motion is
--       dropped). The root part's entry is its fixed axis change and is left out: its Pose only carries the tree.
--   deltas(rig, data, options) -> (KeyframeSequence, number)
--       a bone rig's clip (blender_anim.deltas: each deform bone's world delta, posed x rest^-1 in Blender space, a sample).
--       The Blender-to-Roblox map is the signed axis permutation that lays the Blender rest heads on the imported bones; the
--       second return is how far the worst head lands (studs): over 0.05 means the rig is not the one the clip was made on.
--       A joint's Transform undoes its parent's delta and applies its own in its rest frame, so no bone roll or axis
--       convention has to match. Bones that Roblox's importer turned into MeshParts on Motor6Ds (a bone named like a mesh
--       object) are posed as those joints, at Part0.CFrame * C0.
--
-- data: decoded JSON. options: Name, Loop, Priority, Parent. Markers: AnimationInspector.setMarker.

local ClipImport = {}

export type Options = { Name: string?, Loop: boolean?, Priority: Enum.AnimationPriority?, Parent: Instance? }

local function newSequence(options: Options?, name: string?, loop: boolean?): KeyframeSequence
	local settings: Options = options or {}
	local sequence = Instance.new("KeyframeSequence")
	sequence.Name = settings.Name or name or "Clip"
	sequence.Loop = if settings.Loop ~= nil then settings.Loop else loop == true
	sequence.Priority = settings.Priority or Enum.AnimationPriority.Action
	return sequence
end

-- The rig's joints as parent part -> child parts, and its root part.
local function jointTree(rig: Model): (BasePart, { [BasePart]: { BasePart } })
	local children: { [BasePart]: { BasePart } } = {}
	local hasParent: { [BasePart]: boolean } = {}
	local function link(part0: BasePart?, part1: BasePart?)
		if part0 and part1 then
			children[part0] = children[part0] or {}
			table.insert(children[part0], part1)
			hasParent[part1] = true
		end
	end
	for _, item in rig:GetDescendants() do
		if item:IsA("Motor6D") then
			link(item.Part0, item.Part1)
		elseif item:IsA("AnimationConstraint") then
			local a0, a1 = item.Attachment0, item.Attachment1
			link(if a0 and a0.Parent and a0.Parent:IsA("BasePart") then a0.Parent else nil, if a1 and a1.Parent and a1.Parent:IsA("BasePart") then a1.Parent else nil)
		end
	end
	local root = rig:FindFirstChild("HumanoidRootPart") or rig.PrimaryPart
	if not (root and root:IsA("BasePart")) then
		root = nil
		for part in children do
			if not hasParent[part] then
				root = part
				break
			end
		end
	end
	assert(root and root:IsA("BasePart"), "the rig has no root part with joints")
	return root, children
end

local function numbers(value: any): ({ number }, string?, string?)
	if type(value[1]) == "table" then
		return value[1], value[2], value[3]
	end
	return value, nil, nil
end

function ClipImport.rbxanim(rig: Model, data: any, options: Options?): (KeyframeSequence, { string })
	local root, children = jointTree(rig)
	local known: { [string]: boolean } = { [root.Name] = true }
	for _, list in children do
		for _, part in list do
			known[part.Name] = true
		end
	end
	local missing: { [string]: boolean } = {}
	local sequence = newSequence(options, data.Name, data.Loop)
	for _, frame in data.kfs do
		local key = Instance.new("Keyframe")
		key.Time = frame.t
		for name in frame.kf do
			if not known[name] then
				missing[name] = true
			end
		end
		local function pose(part: BasePart, parent: Instance)
			local p = Instance.new("Pose")
			p.Name = part.Name
			local value = frame.kf[part.Name]
			if value and part ~= root then
				local n, style, direction = numbers(value)
				p.CFrame = CFrame.new(table.unpack(n, 1, 12))
				p.EasingStyle = (Enum.PoseEasingStyle :: any)[style or "Linear"] or Enum.PoseEasingStyle.Linear
				p.EasingDirection = (Enum.PoseEasingDirection :: any)[direction or "Out"] or Enum.PoseEasingDirection.Out
			else
				p.Weight = 0 -- carries the tree only
			end
			p.Parent = parent
			for _, child in children[part] or {} do
				pose(child, p)
			end
		end
		pose(root, key)
		key.Parent = sequence
	end
	local names = {}
	for name in missing do
		table.insert(names, name)
	end
	table.sort(names)
	sequence.Parent = (options or {}).Parent
	return sequence, names
end

local function vector(t: { number }): Vector3
	return Vector3.new(t[1], t[2], t[3])
end

function ClipImport.deltas(rig: Model, data: any, options: Options?): (KeyframeSequence, number)
	local bones: { [string]: Bone } = {}
	for _, item in rig:GetDescendants() do
		if item:IsA("Bone") then
			bones[item.Name] = item
		end
	end
	-- the Blender -> Roblox map: of the 24 proper signed axis permutations, the one that lays the rest heads on the bones
	local axes = { Vector3.xAxis, Vector3.yAxis, Vector3.zAxis }
	local best, worst = CFrame.identity, math.huge
	for i = 1, 3 do
		for j = 1, 3 do
			if j ~= i then
				local k = 6 - i - j
				for _, sx in { 1, -1 } do
					for _, sy in { 1, -1 } do
						for _, sz in { 1, -1 } do
							local cx, cy, cz = axes[i] * sx, axes[j] * sy, axes[k] * sz
							if cx:Cross(cy):Dot(cz) > 0 then
								local turn = CFrame.fromMatrix(Vector3.zero, cx, cy, cz)
								local sum, count = Vector3.zero, 0
								for name, info in data.Rest do
									if bones[name] then
										sum += bones[name].WorldPosition - turn * vector(info.head)
										count += 1
									end
								end
								if count > 0 then
									local shift = sum / count
									local err = 0
									for name, info in data.Rest do
										if bones[name] then
											err = math.max(err, (turn * vector(info.head) + shift - bones[name].WorldPosition).Magnitude)
										end
									end
									if err < worst then
										best, worst = CFrame.new(shift) * turn, err
									end
								end
							end
						end
					end
				end
			end
		end
	end
	assert(worst < math.huge, "no bone of the clip is on this rig")
	local inverse = best:Inverse()
	local rest: { [string]: CFrame } = {}
	local motors: { [Instance]: { BasePart } } = {}
	for name, bone in bones do
		rest[name] = bone.WorldCFrame
	end
	for _, item in rig:GetDescendants() do
		if item:IsA("Motor6D") and item.Part0 and item.Part1 then
			rest[item.Part1.Name] = item.Part0.CFrame * item.C0
			motors[item.Part0] = motors[item.Part0] or {}
			table.insert(motors[item.Part0], item.Part1)
		end
	end
	local rootPart: Instance? = rig.PrimaryPart or rig:FindFirstChild("HumanoidRootPart")
	if not rootPart then
		for name, info in data.Rest do
			if info.parent == nil and bones[name] then
				rootPart = bones[name].Parent
				break
			end
		end
	end
	assert(rootPart and rootPart:IsA("BasePart"), "no root part: set the rig's PrimaryPart")
	local sequence = newSequence(options, data.Name, data.Loop)
	if data.Priority and not (options and options.Priority) then
		sequence.Priority = (Enum.AnimationPriority :: any)[data.Priority] or sequence.Priority
	end
	for _, sample in data.Samples do
		local key = Instance.new("Keyframe")
		key.Time = sample.t
		local delta: { [string]: CFrame } = {}
		for name, v in sample.bones do
			delta[name] = best * CFrame.new(v[1], v[2], v[3], v[5], v[6], v[7], v[4]) * inverse
		end
		local top = Instance.new("Pose")
		top.Name = rootPart.Name
		top.Weight = 0
		local function build(joint: Instance, parent: Instance, parentDelta: CFrame)
			local own = delta[joint.Name] or parentDelta
			local p = Instance.new("Pose")
			p.Name = joint.Name
			p.CFrame = (parentDelta * rest[joint.Name]):Inverse() * (own * rest[joint.Name])
			p.EasingStyle = Enum.PoseEasingStyle.Linear
			p.Parent = parent
			for _, child in joint:GetChildren() do
				if child:IsA("Bone") then
					build(child, p, own)
				end
			end
			for _, part in motors[joint] or {} do
				build(part, p, own)
			end
		end
		for _, child in rootPart:GetChildren() do
			if child:IsA("Bone") then
				build(child, top, CFrame.identity)
			end
		end
		for _, part in motors[rootPart] or {} do
			build(part, top, CFrame.identity)
		end
		top.Parent = key
		key.Parent = sequence
	end
	sequence.Parent = (options or {}).Parent
	return sequence, worst
end

return ClipImport
