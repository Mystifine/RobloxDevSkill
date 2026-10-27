--!strict
-- Animation inspection for Studio MCP, Edit mode. A clone of the rig is posed at exact times (a stopped track,
-- TimePosition, Animator:StepAnimations) and measured by forward kinematics from its joints, never played in real
-- time, so every number and every picture is for one exact moment. Cheapest first:
--
--   audit(rig, clip, options)  text, instant: length, keys, markers, a motion sparkline and findings (unmatched poses,
--                              pops, loop seam, feet, floor, end offset, knee/elbow hyperextension, key grid, easing,
--                              missing markers, a marker away from the tip's fastest moment)
--   sheet(rig, clip, options)  one picture: the key poses side by side in rows (side and front) with motion trails;
--                              parks the camera and returns the legend, then screen_capture with no camera arguments
--   closeLoop / snapKeys / setMarker   repairs on an editable KeyframeSequence; audit again afterwards
--   clear()                    removes the sheet and restores the camera
--
-- rig: a Model with a Humanoid or AnimationController (R15, R6 or custom; Motor6D or AnimationConstraint joints; Bones
-- are followed). clip: a KeyframeSequence, an Animation or an asset id. The rig itself is never changed.
-- Load in Edit: loadstring(game:GetService("HttpService"):GetAsync(url, true))(), or a temporary ModuleScript.
-- Status (2026-10-27): not yet run in Studio. On first use, confirm a known-good clip audits with 0 errors and the sheet
-- reads, then retune any threshold that misfires; remove this note once it has passed.

local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")

local Inspector = {}

export type Finding = { Severity: "error" | "warn", Path: string, Rule: string, Detail: string }
export type Options = {
	Fps: number?, -- key grid to check (default 60; a project may author some rigs at 30)
	Feet: { string }?, -- parts or bones that plant (default R15/R6 feet; custom rigs: names with Foot, Paw, Hoof or Toe)
	Tip: string?, -- attachment, part or bone whose path times the swing (default RightGripAttachment when present)
	Markers: { string }?, -- markers the clip must have; the first is compared with the tip's fastest moment
	Ignore: { string }?, -- rules to skip, say { "end-offset" } for a death or knockback clip
	Looped: boolean?, -- overrides the clip's own Looped
	Hinges: { { Upper: string, Lower: string, End: string, Bend: string } }?, -- custom knees (Bend "back"), elbows ("front")
}
export type SheetOptions = Options & {
	Times: { number }?, -- exact columns (default: start, end, markers, peak, the stillest key poses, evenly filled)
	Count: number?, -- columns when Times is not given (default 8)
	Views: { string }?, -- rows, top to bottom: "side" (faces right), "front", "back", "three" (default { "side", "front" })
	Trails: boolean?, -- last column: the peak pose with hand, foot, head and tip paths (default true)
	Dark: boolean?, -- dark backdrop (default light, which makes the silhouette read)
	Fov: number?, -- camera field of view (default 20: nearly flat, little perspective)
}
export type Report = {
	Findings: { Finding },
	Text: string,
	Length: number,
	Looped: boolean,
	Markers: { { Name: string, Time: number } },
	Peak: number, -- seconds of the most motion
	GroundSpeed: number?, -- studs/s the planted feet travel back in an in-place locomotion clip
	Tip: { Name: string, From: number, To: number, Fastest: number }?,
}

local RATE = 60 -- samples per second
local HOLD = "__AnimInspect"
local CONTACT = 0.15 -- a foot within this many studs of the floor is planted
local SPARK = { "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█" }
local R15 = {
	Feet = { "LeftFoot", "RightFoot" },
	Trails = { "LeftHand", "RightHand", "LeftFoot", "RightFoot", "Head" },
	Hinges = {
		{ Upper = "LeftUpperLeg", Lower = "LeftLowerLeg", End = "LeftFoot", Bend = "back" },
		{ Upper = "RightUpperLeg", Lower = "RightLowerLeg", End = "RightFoot", Bend = "back" },
		{ Upper = "LeftUpperArm", Lower = "LeftLowerArm", End = "LeftHand", Bend = "front" },
		{ Upper = "RightUpperArm", Lower = "RightLowerArm", End = "RightHand", Bend = "front" },
	},
}
local R6 = { Feet = { "Left Leg", "Right Leg" }, Trails = { "Left Arm", "Right Arm", "Left Leg", "Right Leg", "Head" } }

type Link = { Part: BasePart, Parent: BasePart, C0: CFrame, C1: CFrame, Joint: Instance?, Reversed: boolean }
type Rig = {
	Model: Model,
	Name: string, -- the source rig's name
	Kind: string,
	Root: BasePart,
	Rest: CFrame, -- the root's fixed frame: upright, facing -Z
	Links: { Link }, -- breadth first from the root
	Loose: { [BasePart]: CFrame }, -- parts no joint reaches, kept at their offset from the root
	Bones: { Bone },
	ByName: { [string]: Instance },
	Animator: Animator,
	Ground: number, -- world Y of the floor the rig stands on
	Descendants: { Instance }, -- for mapping snapshot clones back to the subject
}
type Frame = { T: number, World: { [BasePart]: CFrame }, Pivot: { [BasePart]: Vector3 }, Bone: { [Bone]: CFrame }, BoneT: { [Bone]: CFrame } }
type Clip = {
	Rig: Rig, Track: AnimationTrack, Sequence: KeyframeSequence?, Name: string, Length: number, Looped: boolean, Frames: { Frame },
	Moved: boolean, -- some joint or bone left its rest transform at least once (else nothing applied)
}
type Extra = { Energy: { number }, Planted: { [string]: { boolean } }, Trails: { string }, Tip: string? }

local function listed(list: { string }?, name: string): boolean
	for _, item in list or {} do
		if item == name then
			return true
		end
	end
	return false
end

local function holder(): Folder
	local folder = workspace:FindFirstChild(HOLD)
	if not folder then
		folder = Instance.new("Folder")
		folder.Name = HOLD
		folder.Parent = workspace
	end
	return folder :: Folder
end

local function seconds(t: number): string
	return string.format("%.2f s", t)
end

-- Rotation angle (radians, 0..pi) between two frames.
local function turn(a: CFrame, b: CFrame): number
	local _, angle = (a:Inverse() * b):ToAxisAngle()
	angle = math.abs(angle) % (2 * math.pi)
	return if angle > math.pi then 2 * math.pi - angle else angle
end

-- Lowest world Y of a box.
local function bottom(cf: CFrame, size: Vector3): number
	local half = size / 2
	return cf.Position.Y - math.abs(cf.RightVector.Y) * half.X - math.abs(cf.UpVector.Y) * half.Y - math.abs(cf.LookVector.Y) * half.Z
end

-- Part0, Part1, C0, C1 and the animated joint (nil for rigid welds, whose rest offset is kept).
local function edge(item: Instance): (BasePart?, BasePart?, CFrame, CFrame, Instance?)
	if item:IsA("Motor6D") then
		if item.Enabled and item.Part0 and item.Part1 then
			return item.Part0, item.Part1, item.C0, item.C1, item
		end
	elseif item:IsA("AnimationConstraint") then
		local a0, a1 = item.Attachment0, item.Attachment1
		if item.Enabled and a0 and a1 and a0.Parent and a1.Parent and a0.Parent:IsA("BasePart") and a1.Parent:IsA("BasePart") then
			return a0.Parent :: BasePart, a1.Parent :: BasePart, a0.CFrame, a1.CFrame, item
		end
	elseif item:IsA("JointInstance") or item:IsA("WeldConstraint") then
		local p0: BasePart?, p1: BasePart? = (item :: any).Part0, (item :: any).Part1
		if p0 and p1 then
			return p0, p1, p0.CFrame:ToObjectSpace(p1.CFrame), CFrame.identity, nil
		end
	elseif item:IsA("RigidConstraint") then
		local a0, a1 = item.Attachment0, item.Attachment1
		if a0 and a1 and a0.Parent and a1.Parent and a0.Parent:IsA("BasePart") and a1.Parent:IsA("BasePart") then
			local p0, p1 = a0.Parent :: BasePart, a1.Parent :: BasePart
			return p0, p1, p0.CFrame:ToObjectSpace(p1.CFrame), CFrame.identity, nil
		end
	end
	return nil, nil, CFrame.identity, CFrame.identity, nil
end

-- A scriptless clone of `source`, upright and facing -Z with its root at `at`, inside the holder.
local function build(source: Model, at: Vector3): Rig
	local archivable = source.Archivable
	source.Archivable = true
	local model = source:Clone()
	source.Archivable = archivable
	model.Name = "__Subject"
	for _, item in model:GetDescendants() do
		if item:IsA("LuaSourceContainer") then
			item:Destroy()
		end
	end
	local parts: { BasePart } = {}
	local bones: { Bone } = {}
	local edges = {}
	for _, item in model:GetDescendants() do
		if item:IsA("BasePart") then
			table.insert(parts, item)
		elseif item:IsA("Bone") then
			table.insert(bones, item)
		else
			local p0, p1, c0, c1, joint = edge(item)
			if p0 and p1 and p0:IsDescendantOf(model) and p1:IsDescendantOf(model) then
				table.insert(edges, { P0 = p0, P1 = p1, C0 = c0, C1 = c1, Joint = joint })
			end
		end
	end
	local root = (model:FindFirstChild("HumanoidRootPart") or model.PrimaryPart) :: BasePart?
	if not root then
		local moved = {}
		for _, e in edges do
			if e.Joint then
				moved[e.P1] = true
			end
		end
		for _, part in parts do
			if not moved[part] then
				root = part
				break
			end
		end
	end
	assert(root, "the rig has no parts")
	local base = root :: BasePart
	-- upright, facing -Z, root at `at`
	local look = base.CFrame.LookVector
	local yaw = math.atan2(-look.X, -look.Z)
	local move = CFrame.new(at) * (CFrame.new(base.Position) * CFrame.Angles(0, yaw, 0)):Inverse()
	model:PivotTo(move * model:GetPivot())
	base.Anchored = true

	local adjacency: { [BasePart]: { any } } = {}
	for _, e in edges do
		adjacency[e.P0] = adjacency[e.P0] or {}
		adjacency[e.P1] = adjacency[e.P1] or {}
		table.insert(adjacency[e.P0], e)
		table.insert(adjacency[e.P1], e)
	end
	local links: { Link } = {}
	local seen = { [base] = true }
	local queue = { base }
	local head = 1
	while head <= #queue do
		local part = queue[head]
		head += 1
		for _, e in adjacency[part] or {} do
			local other = if e.P0 == part then e.P1 else e.P0
			if not seen[other] then
				seen[other] = true
				table.insert(links, { Part = other, Parent = part, C0 = e.C0, C1 = e.C1, Joint = e.Joint, Reversed = e.P0 ~= part })
				table.insert(queue, other)
			end
		end
	end
	local loose: { [BasePart]: CFrame } = {}
	for _, part in parts do
		if not seen[part] then
			loose[part] = base.CFrame:ToObjectSpace(part.CFrame)
		end
	end

	local humanoid = model:FindFirstChildOfClass("Humanoid")
	local kind = if model:FindFirstChild("UpperTorso") and model:FindFirstChild("LowerTorso") then "R15"
		elseif model:FindFirstChild("Torso") and model:FindFirstChild("Left Leg") then "R6"
		else "custom"
	local ground = math.huge
	if humanoid and kind == "R15" and base.Name == "HumanoidRootPart" then
		ground = base.Position.Y - base.Size.Y / 2 - humanoid.HipHeight
	else
		for _, part in parts do
			if part.Transparency < 1 then
				ground = math.min(ground, bottom(part.CFrame, part.Size))
			end
		end
		if ground == math.huge then
			ground = base.Position.Y - base.Size.Y / 2
		end
	end

	local controller: Instance? = humanoid or model:FindFirstChildOfClass("AnimationController")
	if not controller then
		local made = Instance.new("AnimationController")
		made.Parent = model
		controller = made
	end
	local animator = (controller :: Instance):FindFirstChildOfClass("Animator")
	if not animator then
		local made = Instance.new("Animator")
		made.Parent = controller
		animator = made
	end
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	end

	local byName: { [string]: Instance } = {}
	for _, pass in { "BasePart", "Bone", "Attachment" } do
		for _, item in model:GetDescendants() do
			if item:IsA(pass) and byName[item.Name] == nil then
				byName[item.Name] = item
			end
		end
	end
	model.Parent = holder()
	return {
		Model = model, Name = source.Name, Kind = kind, Root = base, Rest = base.CFrame, Links = links, Loose = loose, Bones = bones,
		ByName = byName, Animator = animator :: Animator, Ground = ground, Descendants = model:GetDescendants(),
	}
end

-- Animation id, the KeyframeSequence when it can be read, and a display name.
local function resolve(clip: any): (string, KeyframeSequence?, string)
	if typeof(clip) == "Instance" and clip:IsA("KeyframeSequence") then
		return KeyframeSequenceProvider:RegisterKeyframeSequence(clip), clip, clip.Name
	end
	local id, name
	if typeof(clip) == "Instance" and clip:IsA("Animation") then
		id, name = clip.AnimationId, clip.Name
	else
		local text = tostring(clip)
		id, name = if string.find(text, "://", 1, true) then text else "rbxassetid://" .. text, text
	end
	local ok, sequence = pcall(function()
		return KeyframeSequenceProvider:GetKeyframeSequenceAsync(id)
	end)
	return id, if ok and typeof(sequence) == "Instance" and sequence:IsA("KeyframeSequence") then sequence else nil, name
end

local function open(source: Model, clip: any, settings: Options): Clip
	local rig = build(source, Vector3.new(0, 1150, -120))
	local id, sequence, name = resolve(clip)
	local animation = Instance.new("Animation")
	animation.AnimationId = id
	local track = rig.Animator:LoadAnimation(animation)
	local waited = 0
	while track.Length <= 0 and waited < 10 do
		waited += task.wait()
	end
	if track.Length <= 0 then
		rig.Model:Destroy()
		error("the clip did not load: check the id and its owner (an animation plays only in its creator's experiences), or pass the KeyframeSequence", 0)
	end
	local looped = if settings.Looped ~= nil then settings.Looped elseif sequence then sequence.Loop else track.Looped
	track.Looped = false -- sample right up to the end without wrapping
	track:Play(0, 1, 0)
	return { Rig = rig, Track = track, Sequence = sequence, Name = name, Length = track.Length, Looped = looped, Frames = {}, Moved = false }
end

-- Poses the subject at `t` and measures it: part frames by forward kinematics, joint pivots, bone frames.
local function pose(clip: Clip, t: number): Frame
	local rig = clip.Rig
	clip.Track.TimePosition = t
	rig.Animator:StepAnimations(0.001)
	local world: { [BasePart]: CFrame } = { [rig.Root] = rig.Rest }
	local pivot: { [BasePart]: Vector3 } = {}
	for _, link in rig.Links do
		local transform = if link.Joint then (link.Joint :: any).Transform :: CFrame else CFrame.identity
		clip.Moved = clip.Moved or transform ~= CFrame.identity
		local base = world[link.Parent]
		if link.Reversed then
			world[link.Part] = base * link.C1 * transform:Inverse() * link.C0:Inverse()
			pivot[link.Part] = (base * link.C1).Position
		else
			world[link.Part] = base * link.C0 * transform * link.C1:Inverse()
			pivot[link.Part] = (base * link.C0).Position
		end
	end
	for part, offset in rig.Loose do
		world[part] = rig.Rest * offset
	end
	local boneWorld: { [Bone]: CFrame } = {}
	local boneT: { [Bone]: CFrame } = {}
	for _, bone in rig.Bones do -- descendant order: a parent bone comes before its children
		local parent = bone.Parent
		local base = if parent and parent:IsA("Bone") then boneWorld[parent] elseif parent and parent:IsA("BasePart") then world[parent] else nil
		if base then
			boneT[bone] = bone.Transform
			boneWorld[bone] = base * bone.CFrame * bone.Transform
			clip.Moved = clip.Moved or bone.Transform ~= CFrame.identity
		end
	end
	return { T = t, World = world, Pivot = pivot, Bone = boneWorld, BoneT = boneT }
end

local function sample(clip: Clip)
	local count = math.max(2, math.ceil(clip.Length * RATE))
	for index = 0, count do
		table.insert(clip.Frames, pose(clip, math.min(clip.Length * index / count, clip.Length - 1e-4)))
	end
end

-- A function giving the world frame of a named part, bone or attachment in a measured frame.
local function locator(rig: Rig, name: string): ((Frame) -> CFrame?)?
	local item = rig.ByName[name]
	if not item then
		return nil
	end
	if item:IsA("BasePart") then
		return function(frame: Frame)
			return frame.World[item]
		end
	elseif item:IsA("Bone") then
		return function(frame: Frame)
			return frame.Bone[item]
		end
	elseif item:IsA("Attachment") then
		local parent = item.Parent
		return function(frame: Frame)
			local base = if parent and parent:IsA("Bone") then frame.Bone[parent] elseif parent and parent:IsA("BasePart") then frame.World[parent] else nil
			return if base then base * item.CFrame else nil
		end
	end
	return nil
end

local function feetOf(rig: Rig, settings: Options): { string }
	if settings.Feet then
		return settings.Feet
	elseif rig.Kind == "R15" then
		return R15.Feet
	elseif rig.Kind == "R6" then
		return R6.Feet
	end
	local found = {}
	for name, item in rig.ByName do
		if (item:IsA("BasePart") or item:IsA("Bone")) and (string.find(string.lower(name), "foot") or string.find(string.lower(name), "paw")
			or string.find(string.lower(name), "hoof") or string.find(string.lower(name), "toe")) then
			table.insert(found, name)
		end
	end
	table.sort(found)
	return found
end

local function analyse(clip: Clip, settings: Options): (Report, Extra)
	local rig, frames = clip.Rig, clip.Frames
	local findings: { Finding } = {}
	local lines: { string } = {}
	local function add(severity: string, path: string, rule: string, detail: string)
		if not listed(settings.Ignore, rule) then
			table.insert(findings, { Severity = severity :: any, Path = path, Rule = rule, Detail = detail })
		end
	end
	if not clip.Moved then -- not ignorable: every other result would describe the rest pose, a false pass
		table.insert(findings, { Severity = "error", Path = clip.Name, Rule = "rest-only", Detail = string.format(
			"the rig never left its rest pose in %d samples, so the clip did not apply and every other result is void: check the id and the joint names, or park the camera near the subject (tracks far from the camera may not play)",
			#frames) })
	end
	local step = frames[2].T - frames[1].T
	local animated: { Link } = {}
	for _, link in rig.Links do
		if link.Joint then
			table.insert(animated, link)
		end
	end
	table.insert(lines, string.format("%s on %s (%s, %d animated joints, %d bones): %s, %s", clip.Name, rig.Name,
		rig.Kind, #animated, #rig.Bones, seconds(clip.Length), if clip.Looped then "looped" else "one-shot"))

	-- keys, easing, unmatched poses, markers
	local markers: { { Name: string, Time: number } } = {}
	local sequence = clip.Sequence
	if sequence then
		local keyframes = sequence:GetKeyframes() :: { any }
		table.sort(keyframes, function(a, b)
			return a.Time < b.Time
		end)
		local fps = settings.Fps or 60
		local offGrid, styles, moving, unmatched = 0, {} :: { [string]: number }, 0, {} :: { [string]: boolean }
		for _, keyframe in keyframes do
			local frame = keyframe.Time * fps
			if math.abs(frame - math.floor(frame + 0.5)) > 0.02 then
				offGrid += 1
			end
			for _, marker in keyframe:GetMarkers() do
				table.insert(markers, { Name = marker.Name, Time = keyframe.Time })
			end
			if keyframe.Name ~= "Keyframe" and keyframe.Name ~= "" then
				table.insert(markers, { Name = keyframe.Name, Time = keyframe.Time })
			end
			for _, item in keyframe:GetDescendants() do
				if item:IsA("Pose") then
					if not rig.ByName[item.Name] then
						unmatched[item.Name] = true
					end
					if item.Weight > 0 then
						moving += 1
						styles[item.EasingStyle.Name] = (styles[item.EasingStyle.Name] or 0) + 1
					end
				end
			end
		end
		local share = {}
		for style, count in styles do
			table.insert(share, { style, count })
		end
		table.sort(share, function(a, b)
			return a[2] > b[2]
		end)
		local easing = {}
		for _, entry in share do
			table.insert(easing, string.format("%s %d%%", entry[1], math.floor(entry[2] / math.max(moving, 1) * 100 + 0.5)))
		end
		local spacing = clip.Length * fps / math.max(#keyframes - 1, 1)
		table.insert(lines, string.format("Keys %d at %d fps (%s), %.1f frames apart; easing %s", #keyframes, fps,
			if offGrid == 0 then "on grid" else offGrid .. " off grid", spacing, if #easing > 0 then table.concat(easing, ", ") else "none"))
		if offGrid > 0 then
			add("warn", sequence.Name, "grid", string.format("%d of %d keys fall between %d fps frames: snapKeys(sequence, %d)", offGrid, #keyframes, fps, fps))
		end
		if spacing > 3 and (styles.Linear or 0) > moving / 2 then
			add("warn", sequence.Name, "easing", string.format("%d%% of poses ease Linear with keys %.1f frames apart: motion reads mechanical; use Cubic or CubicV2 on key poses, or add breakdowns",
				math.floor((styles.Linear or 0) / moving * 100 + 0.5), spacing))
		end
		local missing = {}
		for name in unmatched do
			table.insert(missing, name)
		end
		table.sort(missing)
		if #missing > 0 then
			add("error", sequence.Name, "unmatched", "poses with no part or bone of that name, so their motion is dropped: " .. table.concat(missing, ", "))
		end
	else
		table.insert(lines, "Keys: not readable (published clip without access); key, easing and marker checks skipped")
	end
	table.sort(markers, function(a, b)
		return a.Time < b.Time
	end)
	if #markers > 0 then
		local list = {}
		for _, marker in markers do
			table.insert(list, marker.Name .. " " .. seconds(marker.Time))
		end
		lines[#lines] ..= "; markers " .. table.concat(list, ", ")
	end
	for _, expected in settings.Markers or {} do
		local present = false
		for _, marker in markers do
			present = present or marker.Name == expected
		end
		if not present and sequence then
			add("error", clip.Name, "marker", "no '" .. expected .. "' marker: add it at the moment the gameplay event lands (setMarker)")
		end
	end

	-- motion energy: how much the body moves per second, as a sparkline
	local energy = table.create(#frames, 0) :: { number }
	for index = 2, #frames do
		local sum = 0
		for _, link in animated do
			sum += (frames[index].World[link.Part].Position - frames[index - 1].World[link.Part].Position).Magnitude
		end
		for bone, cf in frames[index].Bone do
			local before = frames[index - 1].Bone[bone]
			if before then
				sum += (cf.Position - before.Position).Magnitude
			end
		end
		energy[index] = sum / math.max(frames[index].T - frames[index - 1].T, 1e-4)
	end
	energy[1] = energy[2] or 0
	local top, peak = 0, 0
	for index, value in energy do
		if value > top then
			top, peak = value, frames[index].T
		end
	end
	local width = math.min(40, #frames)
	local spark, ticks = {}, {}
	for column = 1, width do
		local from = math.floor((column - 1) * #frames / width) + 1
		local to = math.max(from, math.floor(column * #frames / width))
		local high = 0
		for index = from, to do
			high = math.max(high, energy[index])
		end
		table.insert(spark, SPARK[math.clamp(math.ceil(high / math.max(top, 1e-6) * 8), 1, 8)])
		local mark = " "
		for _, marker in markers do
			if marker.Time >= frames[from].T - step / 2 and marker.Time <= frames[to].T + step / 2 then
				mark = "^"
			end
		end
		table.insert(ticks, mark)
	end
	local still, start = {}, nil :: number?
	for index, value in energy do
		local quiet = value < top * 0.1
		if quiet and not start then
			start = frames[index].T
		elseif (not quiet or index == #energy) and start then
			local stop = frames[index].T
			if stop - start >= 0.1 then
				table.insert(still, string.format("%.2f-%.2f", start, stop))
			end
			start = nil
		end
	end
	table.insert(lines, string.format("Motion %s  peak %s%s", table.concat(spark), seconds(peak), if #still > 0 then "; still " .. table.concat(still, ", ") else ""))
	if #markers > 0 then
		table.insert(lines, "       " .. table.concat(ticks) .. "  ^ markers")
	end

	-- the tip: when the swing happens and its fastest moment
	local tipName = settings.Tip or (if rig.ByName.RightGripAttachment then "RightGripAttachment" else nil)
	local tipReport = nil
	local tip = if tipName then locator(rig, tipName) else nil
	local speeds, positions, fastest, at = { 0 }, {}, 0, 2
	if tipName and tip then
		for index, frame in frames do
			local cf = tip(frame)
			positions[index] = if cf then cf.Position else Vector3.zero
		end
		for index = 2, #frames do
			speeds[index] = (positions[index] - positions[index - 1]).Magnitude / math.max(frames[index].T - frames[index - 1].T, 1e-4)
			if speeds[index] > fastest then
				fastest, at = speeds[index], index
			end
		end
		if fastest <= 0 then
			table.insert(lines, "Tip " .. tipName .. ": does not move")
		end
	end
	if tipName and tip and fastest > 0 then
		local from, to = at, at
		while from > 2 and speeds[from - 1] >= fastest / 2 do
			from -= 1
		end
		while to < #frames and speeds[to + 1] >= fastest / 2 do
			to += 1
		end
		local arc = 0
		for index = from, to do
			arc += (positions[index] - positions[index - 1]).Magnitude
		end
		local when = (frames[at].T + frames[at - 1].T) / 2
		tipReport = { Name = tipName, From = frames[from - 1].T, To = frames[to].T, Fastest = when }
		table.insert(lines, string.format("Tip %s: swing %.2f-%.2f s, fastest %s (%.0f studs/s), arc %.1f studs", tipName, tipReport.From, tipReport.To, seconds(when), fastest, arc))
		local sync = settings.Markers and settings.Markers[1]
		if sync then
			for _, marker in markers do
				if marker.Name == sync and math.abs(marker.Time - when) > 0.1 then
					add("warn", clip.Name, "hit-sync", string.format("'%s' at %s but the tip is fastest at %s: move the marker (setMarker) or the effect and damage land %s",
						sync, seconds(marker.Time), seconds(when), if marker.Time > when then "late" else "early"))
				end
			end
		end
	end

	-- feet: a planted foot sits on the floor (no float, no clip); planted drift (in place) or travel speed (locomotion)
	local feet = feetOf(rig, settings)
	local planted: { [string]: { boolean } } = {}
	local stanceSpeeds, drifts, levels, rests = {}, {}, {}, {}
	local lowest, lowestName, lowestTime, everPlanted, measured = math.huge, "", 0, false, 0
	for _, name in feet do
		local find = locator(rig, name)
		local item = rig.ByName[name]
		if find and item then
			measured += 1
			local flags, heights, flat, centre = {}, {}, {}, {}
			for index, frame in frames do
				local cf = find(frame) or rig.Rest
				heights[index] = (if item:IsA("BasePart") then bottom(cf, item.Size) else cf.Position.Y) - rig.Ground
				flat[index] = Vector3.new(cf.Position.X, 0, cf.Position.Z)
				centre[index] = cf.Position
				flags[index] = heights[index] <= CONTACT
				if heights[index] < lowest then
					lowest, lowestName, lowestTime = heights[index], name, frame.T
				end
				everPlanted = everPlanted or flags[index]
			end
			planted[name] = flags
			-- a still foot a little above the floor: meant to stand on it, or lifted on purpose
			local function resting(k: number): boolean
				return k > 1 and heights[k] > CONTACT and heights[k] <= 0.6
					and (centre[k] - centre[k - 1]).Magnitude / math.max(frames[k].T - frames[k - 1].T, 1e-4) < 2
			end
			local rested = false
			local index = 1
			while index <= #frames do
				local stop = index
				if flags[index] then
					while stop < #frames and flags[stop + 1] do
						stop += 1
					end
					if stop - index >= 3 then
						local span = frames[stop].T - frames[index].T
						local travel = flat[stop] - flat[index]
						table.insert(stanceSpeeds, { Name = name, Speed = travel.Z / math.max(span, 1e-4), From = index, To = stop, Flat = flat, Span = span })
						local drift, sorted = 0, {}
						for k = index, stop do
							drift = math.max(drift, (flat[k] - flat[index]).Magnitude)
							table.insert(sorted, heights[k])
						end
						table.sort(sorted)
						table.insert(drifts, { Name = name, Drift = drift, Time = frames[index].T })
						table.insert(levels, { Name = name, Level = sorted[math.ceil(#sorted / 2)], Time = frames[index].T })
					end
				elseif resting(index) then
					while stop < #frames and resting(stop + 1) do
						stop += 1
					end
					if not rested and frames[stop].T - frames[index].T >= 0.15 then
						rested = true
						table.insert(rests, { Name = name, Height = heights[index], Time = frames[index].T })
					end
				end
				index = stop + 1
			end
		end
	end
	local high, low = nil, nil -- the planted contacts furthest above and below the floor
	for _, level in levels do
		if not high or level.Level > high.Level then
			high = level
		end
		if not low or level.Level < low.Level then
			low = level
		end
	end
	local levelText = if high and low then string.format("; planted %+.2f to %+.2f from the floor", low.Level, high.Level) else ""
	local groundSpeed = nil
	if measured == 0 then
		table.insert(lines, "Feet: none found" .. (if #feet > 0 then " (" .. table.concat(feet, ", ") .. " are not on the rig)" else "") .. "; pass Feet = { ... } to check ground contact")
	else
		local back, total = 0, 0
		for _, stance in stanceSpeeds do
			total += 1
			if stance.Speed > 2 then
				back += 1
			end
		end
		if total > 0 and back == total then
			-- in-place locomotion: planted feet travel back at the speed the character moves forward
			local sum = 0
			for _, stance in stanceSpeeds do
				sum += stance.Speed
				local pace = {}
				local a = stance.From + math.floor((stance.To - stance.From) * 0.2)
				local b = stance.To - math.floor((stance.To - stance.From) * 0.2)
				for k = a + 1, b do
					table.insert(pace, (stance.Flat[k].Z - stance.Flat[k - 1].Z) / math.max(frames[k].T - frames[k - 1].T, 1e-4))
				end
				if #pace >= 3 then
					local mean, spread = 0, 0
					for _, v in pace do
						mean += v / #pace
					end
					for _, v in pace do
						spread += (v - mean) ^ 2 / #pace
					end
					if mean > 0 and math.sqrt(spread) / mean > 0.25 then
						add("warn", stance.Name, "stride", string.format("planted speed varies %.0f%% around %.1f studs/s from %s: the foot skates; keep a planted foot moving back evenly",
							math.sqrt(spread) / mean * 100, mean, seconds(frames[stance.From].T)))
					end
				end
			end
			groundSpeed = sum / total
			table.insert(lines, string.format("Feet: in-place locomotion, planted feet travel back %.1f studs/s (play at WalkSpeed / %.1f to stop sliding)%s",
				groundSpeed, groundSpeed, levelText))
		else
			local worst, worstName, worstTime = 0, "", 0
			for _, drift in drifts do
				if drift.Drift > worst then
					worst, worstName, worstTime = drift.Drift, drift.Name, drift.Time
				end
			end
			table.insert(lines, string.format("Feet: %s, planted drift %.2f studs%s%s; lowest %+.2f", if total > 0 then "planted" else "never planted",
				worst, if worst > 0 then " (" .. worstName .. ")" else "", levelText, if lowest == math.huge then 0 else lowest))
			if worst > 0.05 then
				add(if worst > 0.15 then "error" else "warn", worstName, "slide", string.format("planted foot slides %.2f studs from %s: keep planted feet still (IK lock in Blender)", worst, seconds(worstTime)))
			end
		end
		-- a foot meant to meet the floor sits on it: within 0.05 studs while planted, never through it
		if high and high.Level > 0.05 then
			add(if high.Level > 0.12 then "error" else "warn", high.Name, "float", string.format("planted from %s but hovers %.2f studs above the floor: lower it onto the floor (root height or leg)",
				seconds(high.Time), high.Level))
		end
		if low and low.Level < -0.05 then
			add(if low.Level < -0.12 then "error" else "warn", low.Name, "clip", string.format("planted from %s but sunk %.2f studs into the floor: raise it onto the floor",
				seconds(low.Time), -low.Level))
		end
		if lowest < -0.1 and (not low or lowest < low.Level - 0.05) then
			add(if lowest < -0.3 then "error" else "warn", lowestName, "clip", string.format("dips %.2f studs into the floor at %s: a toe or heel goes through the ground", -lowest, seconds(lowestTime)))
		end
		for _, rest in rests do
			add("warn", rest.Name, "float", string.format("rests %.2f studs above the floor from %s without touching it: lower it if it should stand there (Ignore 'float' if it is lifted on purpose)",
				rest.Height, seconds(rest.Time)))
		end
		if not everPlanted and #rests == 0 then
			add("warn", table.concat(feet, ", "), "float", string.format("no foot reaches the floor (lowest %+.2f): check the root offset or HipHeight", lowest))
		end
	end

	-- pops: a joint turning far more in one sample than around it (a flip, a missing key)
	for _, link in animated do
		local angles, moves = {}, {}
		for index = 2, #frames do
			local a = frames[index - 1].World[link.Parent]:ToObjectSpace(frames[index - 1].World[link.Part])
			local b = frames[index].World[link.Parent]:ToObjectSpace(frames[index].World[link.Part])
			angles[index] = turn(a, b)
			moves[index] = (b.Position - a.Position).Magnitude
		end
		local worst, worstAt, around = 0, 0, 0
		for index = 2, #frames do
			local near = {}
			for k = index - 3, index + 3 do
				if k ~= index and angles[k] then
					table.insert(near, angles[k])
				end
			end
			table.sort(near)
			local median = near[math.max(1, math.ceil(#near / 2))] or 0
			if angles[index] > math.rad(15) and angles[index] > 4 * median and angles[index] > worst then
				worst, worstAt, around = angles[index], index, median
			end
		end
		if worst > 0 then
			add(if worst > math.rad(30) then "error" else "warn", link.Part.Name, "pop", string.format("turns %.0f° in one frame at %s (%.0f° around it): a flip or a missing key",
				math.deg(worst), seconds(frames[worstAt].T), math.deg(around)))
		end
		local jump, jumpAt = 0, 0
		for index = 2, #frames do
			local near = {}
			for k = index - 3, index + 3 do
				if k ~= index and moves[k] then
					table.insert(near, moves[k])
				end
			end
			table.sort(near)
			local median = near[math.max(1, math.ceil(#near / 2))] or 0
			if moves[index] > 0.4 and moves[index] > 4 * median and moves[index] > jump then
				jump, jumpAt = moves[index], index
			end
		end
		if jump > 0 then
			add("error", link.Part.Name, "pop", string.format("jumps %.2f studs in one frame at %s", jump, seconds(frames[jumpAt].T)))
		end
	end

	-- loop seam: the last frame must meet the first in pose and in velocity
	if clip.Looped then
		local first, second, before, last = frames[1], frames[2], frames[#frames - 1], frames[#frames]
		local worst, worstName, gap, gapName, hitch, hitchName = 0, "", 0, "", 0, ""
		for _, link in animated do
			local function rel(frame: Frame): CFrame
				return frame.World[link.Parent]:ToObjectSpace(frame.World[link.Part])
			end
			local angle = turn(rel(first), rel(last))
			if angle > worst then
				worst, worstName = angle, link.Part.Name
			end
			local offset = (rel(first).Position - rel(last).Position).Magnitude
			if offset > gap then
				gap, gapName = offset, link.Part.Name
			end
			local function spin(a: CFrame, b: CFrame, dt: number): Vector3
				local axis, angle2 = (a:Inverse() * b):ToAxisAngle()
				return axis * angle2 / math.max(dt, 1e-4)
			end
			local v0 = spin(rel(first), rel(second), second.T - first.T)
			local v1 = spin(rel(before), rel(last), last.T - before.T)
			local change = (v1 - v0).Magnitude
			if change > math.max(4, 0.6 * math.max(v0.Magnitude, v1.Magnitude)) and change > hitch then
				hitch, hitchName = change, link.Part.Name
			end
		end
		table.insert(lines, string.format("Loop seam: %.1f° (%s), %.2f studs", math.deg(worst), worstName, gap))
		if worst > math.rad(1) or gap > 0.05 then
			add(if worst > math.rad(3) or gap > 0.15 then "error" else "warn", if worst > math.rad(1) then worstName else gapName, "seam",
				string.format("the last frame misses the first by %.1f° and %.2f studs: the loop jumps (closeLoop)", math.deg(worst), gap))
		elseif hitch > 0 then
			add("warn", hitchName, "seam-speed", string.format("matches the first pose but changes speed across the loop (%.1f rad/s): match the tangents at the seam", hitch))
		end
	else
		-- one-shot: animation never moves the HumanoidRootPart, so the body snaps back when the clip ends
		local body = nil
		for _, link in animated do
			if link.Parent == rig.Root then
				body = link.Part
				break
			end
		end
		if body then
			local a, b = frames[1].World[body].Position, frames[#frames].World[body].Position
			local flat = Vector3.new(b.X - a.X, 0, b.Z - a.Z).Magnitude
			if flat > 0.5 or math.abs(b.Y - a.Y) > 0.75 then
				add("warn", body.Name, "end-offset", string.format("ends %.1f studs away and %+.1f up from its start: the root does not follow, so the body snaps back when the clip ends (move the character in code; ignore for death or knockback clips)",
					flat, b.Y - a.Y))
			end
		end
	end

	-- knees and elbows must not bend backwards
	local hinges = settings.Hinges or (if rig.Kind == "R15" then R15.Hinges else {})
	for _, hinge in hinges do
		local upper, lower, ending = rig.ByName[hinge.Upper], rig.ByName[hinge.Lower], rig.ByName[hinge.End]
		if upper and lower and ending and upper:IsA("BasePart") and lower:IsA("BasePart") and ending:IsA("BasePart") then
			local worst, worstAt = 0, 0
			for _, frame in frames do
				local hip, knee, ankle = frame.Pivot[upper], frame.Pivot[lower], frame.Pivot[ending]
				if hip and knee and ankle then
					local a, b = knee - hip, ankle - knee
					if a.Magnitude > 1e-3 and b.Magnitude > 1e-3 then
						local angle = math.acos(math.clamp(a.Unit:Dot(b.Unit), -1, 1))
						local side = a:Cross(b):Dot(frame.World[upper].RightVector)
						local natural = if hinge.Bend == "back" then side < 0 else side > 0
						if not natural and angle > worst then
							worst, worstAt = angle, frame.T
						end
					end
				end
			end
			if worst > math.rad(5) then
				add(if worst > math.rad(15) then "error" else "warn", hinge.Lower, "hyperextend", string.format("bends %.0f° the wrong way at %s", math.deg(worst), seconds(worstAt)))
			end
		end
	end

	local errors = 0
	for _, finding in findings do
		errors += if finding.Severity == "error" then 1 else 0
		table.insert(lines, string.format("%s [%s] %s: %s", string.upper(finding.Severity), finding.Rule, finding.Path, finding.Detail))
	end
	table.insert(lines, string.format("%d findings (%d errors)", #findings, errors))
	local trails = if rig.Kind == "R15" then table.clone(R15.Trails) elseif rig.Kind == "R6" then table.clone(R6.Trails) else {}
	for _, name in feet do
		if not table.find(trails, name) then
			table.insert(trails, name)
		end
	end
	if rig.Kind == "custom" and rig.ByName.Head then
		table.insert(trails, "Head")
	end
	return {
		Findings = findings, Text = table.concat(lines, "\n"), Length = clip.Length, Looped = clip.Looped, Markers = markers,
		Peak = peak, GroundSpeed = groundSpeed, Tip = tipReport,
	}, { Energy = energy, Planted = planted, Trails = trails, Tip = if tip then tipName else nil }
end

-- Measures `clip` played on a copy of `rig` and reports. Edit mode. Fix every ERROR; read the sparkline for timing.
function Inspector.audit(rig: Model, clip: any, options: Options?): Report
	local settings = options or {}
	local opened = open(rig, clip, settings)
	local ok, report = pcall(function()
		sample(opened)
		return (analyse(opened, settings))
	end)
	opened.Rig.Model:Destroy()
	if not ok then
		error(report, 0)
	end
	return report :: Report
end

-- Columns worth seeing: start, end, markers, the peak, the stillest moments (key poses), then evenly spaced fill.
local function pick(report: Report, extra: Extra, frames: { Frame }, count: number): { { T: number, Why: string } }
	local picks: { { T: number, Why: string } } = {}
	local function add(t: number, why: string): boolean
		for _, existing in picks do
			if math.abs(existing.T - t) < 1 / 30 then
				if why ~= "" and not string.find(existing.Why, why, 1, true) then
					existing.Why = if existing.Why == "" then why else existing.Why .. ", " .. why
				end
				return false
			end
		end
		if #picks >= count then
			return false
		end
		table.insert(picks, { T = t, Why = why })
		return true
	end
	add(0, "start")
	add(report.Length, "end")
	for _, marker in report.Markers do
		add(marker.Time, marker.Name)
	end
	add(report.Peak, "peak")
	local minima = {}
	for index = 2, #extra.Energy - 1 do
		local e = extra.Energy
		if e[index] <= e[index - 1] and e[index] < e[index + 1] then
			table.insert(minima, index)
		end
	end
	table.sort(minima, function(a, b)
		return extra.Energy[a] < extra.Energy[b]
	end)
	for _, index in minima do
		if #picks >= math.ceil(count * 0.75) then
			break
		end
		add(frames[index].T, "key pose")
	end
	for slot = 1, count * 3 do
		if #picks >= count then
			break
		end
		add(report.Length * (slot % count) / count, "")
	end
	table.sort(picks, function(a, b)
		return a.T < b.T
	end)
	return picks
end

local FACING = { side = Vector3.xAxis, front = Vector3.zAxis, back = -Vector3.zAxis, three = Vector3.new(1, 0, 1).Unit }
local LABEL = { side = "side (faces right)", front = "front (faces you)", back = "back", three = "three-quarter" }

-- A copy of the subject frozen in `frame`, placed so the subject's root lands on `place`. Joints and animators removed.
local function snapshot(rig: Rig, frame: Frame, place: CFrame): Model
	local model = rig.Model:Clone()
	local items = model:GetDescendants()
	for _, item in items do
		if item:IsA("JointInstance") or item:IsA("Constraint") or item:IsA("WeldConstraint") or item:IsA("NoCollisionConstraint") or item:IsA("Animator") then
			item:Destroy()
		end
	end
	local originals: { Instance? } = {}
	if #items == #rig.Descendants then
		originals = rig.Descendants
	else -- something was not Archivable: match by path instead of by position
		local byPath: { [string]: Instance } = {}
		local prefix = #rig.Model:GetFullName() + 2
		for _, original in rig.Descendants do
			if original.Parent then
				byPath[string.sub(original:GetFullName(), prefix)] = original
			end
		end
		local mine = #model:GetFullName() + 2
		for index, item in items do
			originals[index] = byPath[string.sub(item:GetFullName(), mine)]
		end
	end
	for index, item in items do
		local original = originals[index]
		if item:IsA("BasePart") then
			item.Anchored, item.CanCollide, item.CanQuery, item.CanTouch, item.CastShadow = true, false, false, false, false
			local cf = if original and original:IsA("BasePart") then frame.World[original] else nil
			if cf then
				item.CFrame = place * rig.Rest:ToObjectSpace(cf)
			end
		elseif item:IsA("Bone") and original and original:IsA("Bone") then
			local transform = frame.BoneT[original]
			if transform then
				item.Transform = transform
			end
		end
	end
	model.Name = string.format("t=%.2f", frame.T)
	return model
end

-- Builds the contact sheet high above the map: rows of posed copies (side and front by default) on floor strips in front
-- of a plain backdrop, a trails column, and parks the camera on it. Edit mode. Then screen_capture with no camera
-- arguments and read the returned legend. Call clear() when done (a new sheet clears the last one).
function Inspector.sheet(rig: Model, clip: any, options: SheetOptions?): { Legend: string, Report: Report, Camera: { number }, LookAt: { number } }
	local settings: SheetOptions = options or {}
	Inspector.clear()
	local opened = open(rig, clip, settings)
	local ok, result = pcall(function()
		sample(opened)
		local report, extra = analyse(opened, settings)
		local frames = opened.Frames
		local subject = opened.Rig
		local picks: { { T: number, Why: string } } = {}
		if settings.Times then
			for _, t in settings.Times do
				table.insert(picks, { T = math.clamp(t, 0, opened.Length), Why = "" })
			end
		else
			picks = pick(report, extra, frames, settings.Count or 8)
		end
		local views = settings.Views or { "side", "front" }
		local trails = settings.Trails ~= false

		-- extents over the whole clip: how far any part reaches from the root, and how high
		local radius, top = 1, 1
		for _, frame in frames do
			for part, cf in frame.World do
				local offset = cf.Position - subject.Rest.Position
				local reach = part.Size.Magnitude / 2
				radius = math.max(radius, Vector3.new(offset.X, 0, offset.Z).Magnitude + reach)
				top = math.max(top, cf.Position.Y + reach - subject.Ground)
			end
		end
		local spacing = radius * 2 + 1
		local rowHeight = top + 1.5
		local columns = #picks + (if trails then 1 else 0)
		local origin = Vector3.new(0, 1200, 0)
		local folder = holder()
		local sheet = Instance.new("Model")
		sheet.Name = "__Sheet"
		local function plate(name: string, size: Vector3, position: Vector3, color: Color3)
			local part = Instance.new("Part")
			part.Name, part.Size, part.Position, part.Color = name, size, position, color
			part.Anchored, part.CanCollide, part.CanQuery, part.CanTouch, part.CastShadow = true, false, false, false, false
			part.Material = Enum.Material.SmoothPlastic
			part.Parent = sheet
		end
		local width = columns * spacing
		local height = #views * rowHeight
		local middleX = origin.X + (columns - 1) * spacing / 2
		plate("Backdrop", Vector3.new(width + 8, height + 8, 0.4), Vector3.new(middleX, origin.Y + height / 2 - 1, origin.Z - radius - 3),
			if settings.Dark then Color3.fromRGB(28, 28, 34) else Color3.fromRGB(232, 232, 236))
		sheet.Parent = folder

		local lift = subject.Rest.Position.Y - subject.Ground
		local peakFrame = frames[1]
		for _, frame in frames do
			if math.abs(frame.T - report.Peak) < math.abs(peakFrame.T - report.Peak) then
				peakFrame = frame
			end
		end
		local planted = settings.Dark and Color3.new(1, 1, 1) or Color3.new(0, 0, 0)
		for row, view in views do
			local floorY = origin.Y + (#views - row) * rowHeight
			plate("Floor" .. row, Vector3.new(width + 2, 0.2, radius * 2 + 2), Vector3.new(middleX, floorY - 0.1, origin.Z), Color3.fromRGB(70, 70, 78))
			local facing = CFrame.lookAt(Vector3.zero, FACING[view] or Vector3.zAxis)
			for column, chosen in picks do
				local place = CFrame.new(origin.X + (column - 1) * spacing, floorY + lift, origin.Z) * facing
				local copy = snapshot(subject, pose(opened, math.min(chosen.T, opened.Length - 1e-4)), place)
				copy.Parent = sheet
				task.wait()
			end
			if trails then
				local place = CFrame.new(origin.X + #picks * spacing, floorY + lift, origin.Z) * facing
				local copy = snapshot(subject, peakFrame, place)
				local names = table.clone(extra.Trails)
				if extra.Tip then
					table.insert(names, extra.Tip)
				end
				for _, name in names do
					local find = locator(subject, name)
					if find then
						local stride = math.max(1, math.floor(#frames / 45))
						for index = 1, #frames, stride do
							local cf = find(frames[index])
							if cf then
								local dot = Instance.new("Part")
								dot.Shape = Enum.PartType.Ball
								local still = extra.Planted[name] and extra.Planted[name][index]
								dot.Size = Vector3.one * (if still then 0.32 else 0.2)
								dot.Color = if still then planted else Color3.fromHSV(0.66 * (1 - frames[index].T / opened.Length), 0.9, 0.95)
								dot.Anchored, dot.CanCollide, dot.CanQuery, dot.CanTouch, dot.CastShadow = true, false, false, false, false
								dot.Material = Enum.Material.SmoothPlastic
								dot.Position = place:PointToWorldSpace(subject.Rest:PointToObjectSpace(cf.Position))
								dot.Parent = copy
							end
						end
					end
				end
				copy.Parent = sheet
				task.wait()
			end
		end

		-- park the camera: straight on, narrow lens, the whole sheet in frame
		local camera = workspace.CurrentCamera
		if folder:GetAttribute("Fov") == nil then
			folder:SetAttribute("Fov", camera.FieldOfView)
		end
		local fov = settings.Fov or 20
		local center = Vector3.new(middleX, origin.Y + height / 2 - 0.5, origin.Z)
		local viewport = camera.ViewportSize
		local aspect = viewport.X / math.max(viewport.Y, 1)
		local slope = math.tan(math.rad(fov) / 2)
		local distance = math.max((height / 2 + 1) / slope, (width / 2 + 1) / (slope * aspect)) * 1.05
		local eye = center + Vector3.zAxis * distance
		camera.FieldOfView = fov
		camera.CFrame = CFrame.lookAt(eye, center)

		local columnText = {}
		for column, chosen in picks do
			table.insert(columnText, string.format("%d %s%s", column, seconds(chosen.T), if chosen.Why ~= "" then " " .. chosen.Why else ""))
		end
		if trails then
			table.insert(columnText, string.format("%d trails at %s", columns, seconds(peakFrame.T)))
		end
		local rowText = {}
		for _, view in views do
			table.insert(rowText, LABEL[view] or view)
		end
		local legend = table.concat({
			string.format("Sheet: %d rows x %d columns; camera parked, so screen_capture without camera arguments", #views, columns),
			"Rows, top to bottom: " .. table.concat(rowText, "; "),
			"Columns: " .. table.concat(columnText, " | "),
			if trails then string.format("Trails: blue at the start to red at the end; %s dots are a planted foot (a smear is sliding)", if settings.Dark then "white" else "black") else nil,
		} :: { string }, "\n")
		return {
			Legend = legend, Report = report,
			Camera = { eye.X, eye.Y, eye.Z }, LookAt = { center.X, center.Y, center.Z },
		}
	end)
	opened.Rig.Model:Destroy()
	if not ok then
		error(result, 0)
	end
	return result :: any
end

-- Removes the sheet and restores the camera's field of view.
function Inspector.clear()
	local folder = workspace:FindFirstChild(HOLD)
	if folder then
		local fov = folder:GetAttribute("Fov")
		if typeof(fov) == "number" and workspace.CurrentCamera then
			workspace.CurrentCamera.FieldOfView = fov
		end
		folder:Destroy()
	end
end

local function ordered(sequence: KeyframeSequence): { Keyframe }
	local keyframes = sequence:GetKeyframes() :: { any }
	table.sort(keyframes, function(a, b)
		return a.Time < b.Time
	end)
	return keyframes
end

-- Makes a looping clip seamless: the last keyframe takes copies of the first keyframe's poses.
function Inspector.closeLoop(sequence: KeyframeSequence): string
	local keyframes = ordered(sequence)
	if #keyframes < 2 then
		return "nothing to close: fewer than two keyframes"
	end
	local first, last = keyframes[1], keyframes[#keyframes]
	for _, child in last:GetChildren() do
		if child:IsA("Pose") then
			child:Destroy()
		end
	end
	for _, child in first:GetChildren() do
		if child:IsA("Pose") then
			child:Clone().Parent = last
		end
	end
	return string.format("the keyframe at %s now repeats the first pose", seconds(last.Time))
end

-- Moves every keyframe onto the `fps` grid (default 60). Two keys that would share a frame are left alone and listed.
function Inspector.snapKeys(sequence: KeyframeSequence, fps: number?): string
	local rate = fps or 60
	local taken: { [number]: boolean } = {}
	local moved, clashes = 0, {}
	for _, keyframe in ordered(sequence) do
		local frame = math.floor(keyframe.Time * rate + 0.5)
		if taken[frame] then
			table.insert(clashes, seconds(keyframe.Time))
		else
			taken[frame] = true
			if math.abs(keyframe.Time - frame / rate) > 1e-6 then
				keyframe.Time = frame / rate
				moved += 1
			end
		end
	end
	return string.format("%d keys moved onto %d fps%s", moved, rate, if #clashes > 0 then "; left (frame taken): " .. table.concat(clashes, ", ") else "")
end

-- Puts the marker `name` at `time` (one only: older ones of that name are removed), on a keyframe there or a new empty one.
function Inspector.setMarker(sequence: KeyframeSequence, name: string, time: number): string
	for _, keyframe in ordered(sequence) do
		for _, marker in keyframe:GetMarkers() do
			if marker.Name == name then
				marker:Destroy()
			end
		end
	end
	local target: Keyframe? = nil
	for _, keyframe in ordered(sequence) do
		if math.abs(keyframe.Time - time) < 1e-3 then
			target = keyframe
		end
	end
	if not target then
		local made = Instance.new("Keyframe")
		made.Time = time
		made.Parent = sequence
		target = made
	end
	local marker = Instance.new("KeyframeMarker")
	marker.Name = name
	marker.Parent = target
	return string.format("marker '%s' at %s", name, seconds(time))
end

return Inspector
